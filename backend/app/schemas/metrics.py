from typing import Dict, List
from pydantic import BaseModel
from app.schemas.job import QueueStatsResponse, JobStatsResponse
from app.schemas.user import WorkerNodeResponse


class SystemMetricsResponse(BaseModel):
    job_stats: JobStatsResponse
    queue_stats: QueueStatsResponse
    active_workers_count: int
    total_workers_count: int
    workers: List[WorkerNodeResponse]
    throughput_per_minute: float
    failure_rate_percent: float
