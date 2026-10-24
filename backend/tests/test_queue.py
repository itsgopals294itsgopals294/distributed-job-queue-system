import pytest
import asyncio
from app.core.queue_manager import QueueManager
from app.models.job import JobPriority


@pytest.mark.asyncio
async def test_priority_queue_order():
    # Push low, medium, high in reverse order
    await QueueManager.push_job("job_low", JobPriority.LOW)
    await QueueManager.push_job("job_med", JobPriority.MEDIUM)
    await QueueManager.push_job("job_high", JobPriority.HIGH)

    # First pop must be HIGH
    popped1 = await QueueManager.pop_job(timeout=1)
    assert popped1 is not None
    assert popped1[1] == "job_high"

    # Second pop must be MEDIUM
    popped2 = await QueueManager.pop_job(timeout=1)
    assert popped2 is not None
    assert popped2[1] == "job_med"

    # Third pop must be LOW
    popped3 = await QueueManager.pop_job(timeout=1)
    assert popped3 is not None
    assert popped3[1] == "job_low"


@pytest.mark.asyncio
async def test_delayed_queue_and_dlq():
    # Schedule delayed job with 0.5s delay
    await QueueManager.schedule_delayed_job("retry_job_99", 0.5)

    # Immediately check: should not be ready yet
    ready_immediate = await QueueManager.pop_ready_delayed_jobs()
    assert "retry_job_99" not in ready_immediate

    # Wait 0.6 seconds
    await asyncio.sleep(0.6)
    ready_after = await QueueManager.pop_ready_delayed_jobs()
    assert "retry_job_99" in ready_after

    # Test Dead-Letter Queue
    await QueueManager.push_dead_letter("dead_job_1", {"error": "Exceeded retries"})
    dlq_items = await QueueManager.get_dead_letter_jobs(start=0, count=10)
    assert any(item.get("job_id") == "dead_job_1" for item in dlq_items)

    # Purge DLQ
    purged = await QueueManager.purge_dead_letter()
    assert purged >= 1
    dlq_after = await QueueManager.get_dead_letter_jobs()
    assert len(dlq_after) == 0
