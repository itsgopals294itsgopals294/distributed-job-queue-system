import os
import sys
import time
import asyncio
import logging
from datetime import datetime, timezone, timedelta

# Ensure backend modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from sqlalchemy import select
from app.database import AsyncSessionLocal, init_db
from app.models.job import Job, JobStatus
from app.models.worker import WorkerNode
from app.core.queue_manager import QueueManager
from app.core.redis import RedisClient
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Reaper] %(message)s"
)
logger = logging.getLogger("jobqueue.reaper")


class WatchdogReaper:
    def __init__(self):
        self.is_running = True

    async def start(self):
        logger.info("Starting Watchdog Reaper Service (Delayed Retry Scheduler & Crash Recovery)...")
        await init_db()
        await RedisClient.get_client()

        while self.is_running:
            try:
                # 1. Process delayed retry jobs whose epoch time has arrived
                await self._process_delayed_retries()

                # 2. Reclaim abandoned jobs from crashed or dead workers
                await self._reclaim_abandoned_jobs()

            except Exception as e:
                logger.error(f"Error in Watchdog loop: {e}", exc_info=True)

            await asyncio.sleep(1.0)

    async def _process_delayed_retries(self):
        """Pops due jobs from queue:delayed and enqueues them into priority queues."""
        ready_job_ids = await QueueManager.pop_ready_delayed_jobs(limit=50)
        if not ready_job_ids:
            return

        async with AsyncSessionLocal() as session:
            for job_id in ready_job_ids:
                res = await session.execute(select(Job).where(Job.id == job_id))
                job = res.scalar_one_or_none()
                if not job:
                    continue

                if job.status == JobStatus.RETRY_WAIT:
                    job.status = JobStatus.QUEUED
                    job.updated_at = datetime.now(timezone.utc)
                    await session.commit()
                    
                    # Push into priority queue
                    await QueueManager.push_job(job.id, job.priority)
                    logger.info(f"Re-enqueued retry job {job.id} (Priority: {job.priority.value})")

    async def _reclaim_abandoned_jobs(self):
        """Detects jobs stuck in RUNNING with dead workers or expired execution leases."""
        now = datetime.now(timezone.utc)
        stale_threshold = now - timedelta(seconds=settings.DEFAULT_JOB_TIMEOUT_SECONDS + 30)

        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(Job).where(
                    Job.status == JobStatus.RUNNING,
                    Job.started_at < stale_threshold
                )
            )
            stale_jobs = res.scalars().all()

            for job in stale_jobs:
                logger.warning(f"Detected orphaned running job {job.id} (Worker: {job.worker_id}). Reclaiming...")
                job.retry_count += 1
                job.error_message = f"Execution timeout or worker failure: worker {job.worker_id} heartbeat lost."

                if job.retry_count < job.max_retries:
                    job.status = JobStatus.QUEUED
                    job.worker_id = None
                    job.updated_at = now
                    await session.commit()
                    await QueueManager.push_job(job.id, job.priority)
                    logger.info(f"Reclaimed and re-queued job {job.id}")
                else:
                    job.status = JobStatus.DEAD_LETTER
                    job.completed_at = now
                    await session.commit()
                    await QueueManager.push_dead_letter(
                        job.id,
                        {"reason": "Worker crash or unhandled timeout", "last_worker": job.worker_id}
                    )
                    logger.critical(f"Orphaned job {job.id} exceeded retries. Moved to Dead-Letter Queue.")


if __name__ == "__main__":
    reaper = WatchdogReaper()
    try:
        asyncio.run(reaper.start())
    except KeyboardInterrupt:
        logger.info("Watchdog Reaper stopped.")
