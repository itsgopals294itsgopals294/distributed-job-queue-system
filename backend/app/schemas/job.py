from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from app.models.job import JobPriority, JobStatus


class JobCreate(BaseModel):
    job_type: str = Field(..., description="Type of job (e.g. email_dispatch, data_export, image_resize, ml_inference, webhook_delivery, custom_calc)")
    priority: JobPriority = Field(default=JobPriority.MEDIUM)
    payload: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary task payload")
    idempotency_key: Optional[str] = Field(None, max_length=255, description="Unique key to avoid duplicate jobs")
    max_retries: Optional[int] = Field(3, ge=0, le=10)
    run_timeout_seconds: Optional[int] = Field(120, ge=5, le=3600)


class JobExecutionResponse(BaseModel):
    id: int
    attempt_number: int
    worker_id: str
    status: str
    error: Optional[str] = None
    logs: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_ms: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class JobResponse(BaseModel):
    id: str
    user_id: int
    job_type: str
    priority: JobPriority
    status: JobStatus
    idempotency_key: Optional[str] = None
    retry_count: int
    max_retries: int
    run_timeout_seconds: int
    worker_id: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class JobDetailResponse(JobResponse):
    payload: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    logs: Optional[str] = None
    executions: List[JobExecutionResponse] = []


class JobStatsResponse(BaseModel):
    total_jobs: int
    submitted: int
    queued: int
    running: int
    completed: int
    retry_wait: int
    dead_letter: int
    cancelled: int


class QueueStatsResponse(BaseModel):
    high_priority_queue: int
    medium_priority_queue: int
    low_priority_queue: int
    delayed_queue: int
    dead_letter_queue: int
    total_in_queue: int
