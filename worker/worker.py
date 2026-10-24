import os
import sys
import uuid
import socket
import asyncio
import logging
import random
import signal
from datetime import datetime, timezone
from typing import Optional

# Ensure backend modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import AsyncSessionLocal, init_db
from app.models.job import Job, JobExecution, JobStatus
from app.models.worker import WorkerNode
from app.core.queue_manager import QueueManager
from app.core.redis import RedisClient
from runner import TaskRunner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Worker] %(message)s"
)
logger = logging.getLogger("jobqueue.worker")


class DistributedWorker:
    def __init__(self, worker_id: Optional[str] = None):
        self.hostname = socket.gethostname()
        self.worker_id = worker_id or f"worker-{self.hostname}-{uuid.uuid4().hex[:6]}"
        self.is_running = True
        self.status = "ONLINE"  # ONLINE, DRAINING, STOPPED
        self.current_job_id: Optional[str] = None
        self.jobs_completed = 0
        self.jobs_failed = 0
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def start(self):
        logger.info(f"Starting worker process: {self.worker_id} on {self.hostname}")
        # Initialize DB and Redis connection
        await init_db()
        await RedisClient.get_client()

        # Start periodic heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # Main worker execution loop
        await self._worker_loop()

    async def stop(self):
        logger.info(f"Initiating graceful shutdown for worker {self.worker_id}...")
        self.status = "DRAINING"
        self.is_running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        
        # Mark worker stopped in DB
        try:
            async with AsyncSessionLocal() as session:
                res = await session.execute(select(WorkerNode).where(WorkerNode.worker_id == self.worker_id))
                node = res.scalar_one_or_none()
                if node:
                    node.status = "STOPPED"
                    node.current_job_id = None
                    await session.commit()
        except Exception as e:
            logger.error(f"Error marking worker stopped: {e}")

        logger.info(f"Worker {self.worker_id} stopped cleanly.")

    async def _heartbeat_loop(self):
        """Periodically reports worker heartbeat and renews job lease."""
        while self.is_running:
            try:
                now = datetime.now(timezone.utc)
                async with AsyncSessionLocal() as session:
                    res = await session.execute(select(WorkerNode).where(WorkerNode.worker_id == self.worker_id))
                    node = res.scalar_one_or_none()
                    if not node:
                        node = WorkerNode(
                            worker_id=self.worker_id,
                            hostname=self.hostname,
                            status=self.status,
                            current_job_id=self.current_job_id,
                            jobs_completed=self.jobs_completed,
                            jobs_failed=self.jobs_failed,
                            started_at=now,
                            last_heartbeat=now
                        )
                        session.add(node)
                    else:
                        if node.status == "DRAINING":
                            self.status = "DRAINING"
                        node.status = self.status
                        node.current_job_id = self.current_job_id
                        node.jobs_completed = self.jobs_completed
                        node.jobs_failed = self.jobs_failed
                        node.last_heartbeat = now
                    await session.commit()

                # Renew active job lease in Redis if executing
                if self.current_job_id:
                    await QueueManager.renew_lease(
                        job_id=self.current_job_id,
                        worker_id=self.worker_id,
                        ttl_seconds=settings.LEASE_TIMEOUT_SECONDS
                    )
            except Exception as e:
                logger.warning(f"Heartbeat iteration error: {e}")

            await asyncio.sleep(settings.WORKER_HEARTBEAT_INTERVAL_SECONDS)

    async def _worker_loop(self):
        logger.info(f"Worker {self.worker_id} is waiting for jobs (High -> Medium -> Low)...")
        while self.is_running:
            if self.status == "DRAINING":
                logger.info("Worker is in DRAINING mode. Exiting loop.")
                break

            try:
                pop_result = await QueueManager.pop_job(timeout=2)
                if not pop_result:
                    await asyncio.sleep(0.5)
                    continue

                queue_name, job_id = pop_result
                logger.info(f"Worker {self.worker_id} popped job {job_id} from {queue_name}")
                await self._process_job(job_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in worker loop: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _process_job(self, job_id: str):
        # 1. Check if job was cancelled while queued
        if await QueueManager.is_cancelled(job_id):
            logger.info(f"Job {job_id} was cancelled before execution. Skipping.")
            return

        # 2. Acquire execution lease to avoid duplicate worker runs
        lease_acquired = await QueueManager.acquire_lease(
            job_id=job_id,
            worker_id=self.worker_id,
            ttl_seconds=settings.LEASE_TIMEOUT_SECONDS
        )
        if not lease_acquired:
            logger.warning(f"Could not acquire lease for job {job_id}. Already claimed by another worker.")
            return

        self.current_job_id = job_id
        start_time = datetime.now(timezone.utc)

        try:
            # 3. Retrieve and update job state in DB
            async with AsyncSessionLocal() as session:
                res = await session.execute(
                    select(Job)
                    .options(selectinload(Job.executions))
                    .where(Job.id == job_id)
                )
                job = res.scalar_one_or_none()
                if not job:
                    logger.error(f"Job {job_id} not found in database! Dropping.")
                    return

                # If job was marked cancelled in DB
                if job.status == JobStatus.CANCELLED:
                    logger.info(f"Job {job_id} status is CANCELLED in DB. Aborting.")
                    return

                job.status = JobStatus.RUNNING
                job.worker_id = self.worker_id
                job.started_at = start_time
                await session.commit()
                await session.refresh(job)

                job_type = job.job_type
                payload = job.payload or {}
                timeout_sec = job.run_timeout_seconds or 120
                attempt_num = job.retry_count + 1

            # 4. Execute the task
            logger.info(f"Executing job {job_id} (Attempt #{attempt_num}, Type: {job_type})...")
            success, result_dict, err_msg, logs, duration_ms = await TaskRunner.run(
                job_type=job_type,
                payload=payload,
                timeout_seconds=timeout_sec
            )

            # 5. Check if cancelled during execution
            is_canc = await QueueManager.is_cancelled(job_id)

            # 6. Record result in DB
            async with AsyncSessionLocal() as session:
                res = await session.execute(
                    select(Job)
                    .options(selectinload(Job.executions))
                    .where(Job.id == job_id)
                )
                job = res.scalar_one_or_none()
                if not job:
                    return

                # Record execution attempt
                exec_status = "CANCELLED" if is_canc else ("SUCCESS" if success else "FAILED")
                execution = JobExecution(
                    job_id=job.id,
                    attempt_number=attempt_num,
                    worker_id=self.worker_id,
                    status=exec_status,
                    error=err_msg if not is_canc else "Job was cancelled during execution",
                    logs=logs,
                    started_at=start_time,
                    finished_at=datetime.now(timezone.utc),
                    duration_ms=duration_ms
                )
                session.add(execution)

                # Append logs to job cumulative log
                existing_logs = job.logs or ""
                job.logs = f"{existing_logs}\n--- Attempt #{attempt_num} ---\n{logs}".strip()

                if is_canc:
                    job.status = JobStatus.CANCELLED
                    job.completed_at = datetime.now(timezone.utc)
                    job.error_message = "Cancelled during execution"
                    logger.info(f"Job {job_id} marked CANCELLED.")
                elif success:
                    job.status = JobStatus.COMPLETED
                    job.result = result_dict
                    job.completed_at = datetime.now(timezone.utc)
                    job.error_message = None
                    self.jobs_completed += 1
                    logger.info(f"Job {job_id} COMPLETED successfully.")

                    # Real-world Webhook Callback dispatch
                    webhook_url = payload.get("webhook_url")
                    if webhook_url:
                        try:
                            import httpx
                            async with httpx.AsyncClient(timeout=4.0) as client:
                                await client.post(webhook_url, json={
                                    "event": "job.completed",
                                    "job_id": job.id,
                                    "status": "COMPLETED",
                                    "result": result_dict,
                                    "duration_ms": duration_ms,
                                    "worker_id": self.worker_id
                                })
                            logger.info(f"Dispatched completion webhook to: {webhook_url}")
                        except Exception as we:
                            logger.warning(f"Webhook notification to {webhook_url} failed: {we}")
                else:
                    # Failure handling & retry logic
                    self.jobs_failed += 1
                    job.retry_count += 1
                    job.error_message = err_msg

                    if job.retry_count < job.max_retries:
                        # Exponential backoff: base * (2^(attempt-1)) + jitter
                        backoff = settings.RETRY_BACKOFF_BASE_SECONDS * (2 ** (job.retry_count - 1))
                        jitter = random.uniform(0.5, 2.0)
                        delay = backoff + jitter
                        
                        job.status = JobStatus.RETRY_WAIT
                        await session.commit()

                        # Schedule in Redis delayed sorted set
                        await QueueManager.schedule_delayed_job(job.id, delay)
                        logger.warning(
                            f"Job {job_id} failed attempt {attempt_num}/{job.max_retries}. "
                            f"Scheduled for retry in {delay:.1f}s"
                        )
                    else:
                        # Max retries reached -> Dead-Letter Queue
                        job.status = JobStatus.DEAD_LETTER
                        job.completed_at = datetime.now(timezone.utc)
                        await session.commit()

                        await QueueManager.push_dead_letter(
                            job_id=job.id,
                            metadata={
                                "job_type": job.job_type,
                                "attempts": job.retry_count,
                                "last_error": err_msg,
                                "worker_id": self.worker_id
                            }
                        )
                        logger.critical(
                            f"Job {job_id} exceeded max retries ({job.max_retries}). Moved to Dead-Letter Queue (DLQ)."
                        )

                await session.commit()

        except Exception as e:
            logger.error(f"Critical error processing job {job_id}: {e}", exc_info=True)
        finally:
            self.current_job_id = None
            await QueueManager.release_lease(job_id=job_id, worker_id=self.worker_id)


async def main():
    worker = DistributedWorker()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(worker.stop()))
        except NotImplementedError:
            # Signal handlers not implemented on Windows event loop for add_signal_handler
            pass

    try:
        await worker.start()
    except (KeyboardInterrupt, asyncio.CancelledError):
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
