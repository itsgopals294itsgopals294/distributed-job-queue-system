from fastapi import APIRouter, Response, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

from app.database import get_db
from app.services.job_service import JobService
from app.core.queue_manager import QueueManager
from app.models.worker import WorkerNode
from sqlalchemy import select

router = APIRouter(prefix="/metrics", tags=["Metrics"])

# Prometheus Metrics Definitions
JOB_SUBMISSIONS = Counter(
    "job_submissions_total",
    "Total number of submitted jobs",
    ["job_type", "priority"]
)

JOB_EXECUTIONS = Counter(
    "job_executions_total",
    "Total number of job executions",
    ["job_type", "status"]
)

QUEUE_SIZE = Gauge(
    "queue_size",
    "Current number of jobs waiting in queue",
    ["priority"]
)

ACTIVE_WORKERS = Gauge(
    "active_workers_count",
    "Current count of active online worker nodes"
)

JOB_DURATION = Histogram(
    "job_duration_seconds",
    "Duration of job executions in seconds",
    ["job_type"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0]
)


@router.get("/prometheus")
@router.get("/")
async def prometheus_metrics(db: AsyncSession = Depends(get_db)):
    """Prometheus exposition format for scraping."""
    # Update queue gauges
    q_lengths = await QueueManager.get_queue_lengths()
    QUEUE_SIZE.labels(priority="high").set(q_lengths["high"])
    QUEUE_SIZE.labels(priority="medium").set(q_lengths["medium"])
    QUEUE_SIZE.labels(priority="low").set(q_lengths["low"])
    QUEUE_SIZE.labels(priority="delayed").set(q_lengths["delayed"])
    QUEUE_SIZE.labels(priority="dead_letter").set(q_lengths["dead_letter"])

    # Update active workers gauge
    w_stmt = select(WorkerNode).where(WorkerNode.status == "ONLINE")
    w_res = await db.execute(w_stmt)
    ACTIVE_WORKERS.set(len(w_res.scalars().all()))

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
