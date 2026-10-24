import json
import time
import logging
from typing import Optional, List, Dict, Any, Tuple
from app.config import settings
from app.core.redis import RedisClient
from app.models.job import JobPriority

logger = logging.getLogger(__name__)

# Redis Key Constants
QUEUE_HIGH = "queue:high"
QUEUE_MEDIUM = "queue:medium"
QUEUE_LOW = "queue:low"
QUEUE_DELAYED = "queue:delayed"
QUEUE_DEAD_LETTER = "queue:dead_letter"
JOBS_CANCELLED = "jobs:cancelled"
LEASE_PREFIX = "job:lease:"
WORKER_HASH = "workers:registry"
IDEMPOTENCY_PREFIX = "idempotency:"


class QueueManager:
    @classmethod
    def get_queue_name_for_priority(cls, priority: JobPriority | str) -> str:
        if isinstance(priority, JobPriority):
            val = priority.value.lower()
        elif hasattr(priority, "value"):
            val = str(priority.value).lower()
        else:
            val = str(priority).lower()

        if "high" in val:
            return QUEUE_HIGH
        elif "low" in val:
            return QUEUE_LOW
        return QUEUE_MEDIUM

    @classmethod
    async def push_job(cls, job_id: str, priority: JobPriority | str) -> int:
        """Pushes a job ID into the appropriate priority queue."""
        redis = await RedisClient.get_client()
        queue_name = cls.get_queue_name_for_priority(priority)
        result = await redis.rpush(queue_name, job_id)
        logger.info(f"Pushed job {job_id} to {queue_name}")
        return result

    @classmethod
    async def pop_job(cls, timeout: int = 2) -> Optional[Tuple[str, str]]:
        """Pops a job ID prioritizing high > medium > low queues."""
        redis = await RedisClient.get_client()
        # BRPOP evaluates queues in order of list
        queues = [QUEUE_HIGH, QUEUE_MEDIUM, QUEUE_LOW]
        result = await redis.brpop(queues, timeout=timeout)
        if result:
            queue_name, job_id = result
            return queue_name, job_id
        return None

    @classmethod
    async def schedule_delayed_job(cls, job_id: str, delay_seconds: float) -> bool:
        """Adds a job to the delayed sorted set with epoch execution time."""
        redis = await RedisClient.get_client()
        execute_at = time.time() + delay_seconds
        await redis.zadd(QUEUE_DELAYED, {job_id: execute_at})
        logger.info(f"Scheduled job {job_id} for retry in {delay_seconds:.1f}s")
        return True

    @classmethod
    async def pop_ready_delayed_jobs(cls, limit: int = 50) -> List[str]:
        """Retrieves and removes jobs whose scheduled execution time has passed."""
        redis = await RedisClient.get_client()
        now = time.time()
        # Get elements with score <= now
        ready_jobs = await redis.zrangebyscore(QUEUE_DELAYED, 0, now)
        if ready_jobs:
            to_process = ready_jobs[:limit]
            await redis.zrem(QUEUE_DELAYED, *to_process)
            return to_process
        return []

    @classmethod
    async def push_dead_letter(cls, job_id: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Pushes a failed job to the Dead-Letter Queue."""
        redis = await RedisClient.get_client()
        entry = {
            "job_id": job_id,
            "moved_at": time.time(),
            "metadata": metadata or {}
        }
        result = await redis.rpush(QUEUE_DEAD_LETTER, json.dumps(entry))
        logger.warning(f"Job {job_id} moved to Dead-Letter Queue (DLQ)")
        return result

    @classmethod
    async def get_dead_letter_jobs(cls, start: int = 0, count: int = 50) -> List[Dict[str, Any]]:
        """Returns items from the DLQ."""
        redis = await RedisClient.get_client()
        end = start + count - 1
        raw_items = await redis.lrange(QUEUE_DEAD_LETTER, start, end)
        results = []
        for item in raw_items:
            try:
                results.append(json.loads(item))
            except Exception:
                results.append({"job_id": item, "moved_at": None, "metadata": {}})
        return results

    @classmethod
    async def remove_from_dead_letter(cls, job_id: str) -> bool:
        """Removes a specific job from DLQ."""
        redis = await RedisClient.get_client()
        items = await redis.lrange(QUEUE_DEAD_LETTER, 0, -1)
        for item in items:
            try:
                parsed = json.loads(item)
                if parsed.get("job_id") == job_id:
                    await redis.lrem(QUEUE_DEAD_LETTER, 1, item)
                    return True
            except Exception:
                if item == job_id:
                    await redis.lrem(QUEUE_DEAD_LETTER, 1, item)
                    return True
        return False

    @classmethod
    async def purge_dead_letter(cls) -> int:
        """Clears all jobs from DLQ."""
        redis = await RedisClient.get_client()
        total = await redis.llen(QUEUE_DEAD_LETTER)
        await redis.delete(QUEUE_DEAD_LETTER)
        return total

    @classmethod
    async def mark_cancelled(cls, job_id: str) -> bool:
        """Marks a job as cancelled so workers abort it immediately."""
        redis = await RedisClient.get_client()
        await redis.sadd(JOBS_CANCELLED, job_id)
        # Also remove from queues if still queued
        for q in [QUEUE_HIGH, QUEUE_MEDIUM, QUEUE_LOW]:
            await redis.lrem(q, 0, job_id)
        await redis.zrem(QUEUE_DELAYED, job_id)
        return True

    @classmethod
    async def is_cancelled(cls, job_id: str) -> bool:
        """Checks if a job has been flagged as cancelled."""
        redis = await RedisClient.get_client()
        return await redis.sismember(JOBS_CANCELLED, job_id)

    @classmethod
    async def clear_cancelled_flag(cls, job_id: str):
        redis = await RedisClient.get_client()
        await redis.srem(JOBS_CANCELLED, job_id)

    @classmethod
    async def acquire_lease(cls, job_id: str, worker_id: str, ttl_seconds: int = 30) -> bool:
        """Acquires an exclusive execution lease for a job."""
        redis = await RedisClient.get_client()
        lease_key = f"{LEASE_PREFIX}{job_id}"
        success = await redis.set(lease_key, worker_id, ex=ttl_seconds, nx=True)
        return bool(success)

    @classmethod
    async def renew_lease(cls, job_id: str, worker_id: str, ttl_seconds: int = 30) -> bool:
        """Heartbeat to renew an existing lease."""
        redis = await RedisClient.get_client()
        lease_key = f"{LEASE_PREFIX}{job_id}"
        current = await redis.get(lease_key)
        if current == worker_id:
            await redis.expire(lease_key, ttl_seconds)
            return True
        return False

    @classmethod
    async def release_lease(cls, job_id: str, worker_id: str):
        """Releases the lease when execution completes or terminates."""
        redis = await RedisClient.get_client()
        lease_key = f"{LEASE_PREFIX}{job_id}"
        current = await redis.get(lease_key)
        if current == worker_id:
            await redis.delete(lease_key)

    @classmethod
    async def set_idempotency_key(cls, key: str, job_id: str, ttl_seconds: int = 86400) -> bool:
        """Sets idempotency key. Returns True if fresh, False if already exists."""
        redis = await RedisClient.get_client()
        idemp_key = f"{IDEMPOTENCY_PREFIX}{key}"
        return bool(await redis.set(idemp_key, job_id, ex=ttl_seconds, nx=True))

    @classmethod
    async def get_idempotent_job_id(cls, key: str) -> Optional[str]:
        redis = await RedisClient.get_client()
        idemp_key = f"{IDEMPOTENCY_PREFIX}{key}"
        return await redis.get(idemp_key)

    @classmethod
    async def get_queue_lengths(cls) -> Dict[str, int]:
        """Returns lengths of all queues."""
        redis = await RedisClient.get_client()
        high = await redis.llen(QUEUE_HIGH)
        med = await redis.llen(QUEUE_MEDIUM)
        low = await redis.llen(QUEUE_LOW)
        delayed = await redis.zcard(QUEUE_DELAYED)
        dlq = await redis.llen(QUEUE_DEAD_LETTER)
        return {
            "high": high,
            "medium": med,
            "low": low,
            "delayed": delayed,
            "dead_letter": dlq,
            "total": high + med + low
        }
