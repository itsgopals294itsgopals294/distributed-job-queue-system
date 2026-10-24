import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class JobPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class JobStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    RETRY_WAIT = "RETRY_WAIT"
    DEAD_LETTER = "DEAD_LETTER"
    CANCELLED = "CANCELLED"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    
    job_type = Column(String(100), nullable=False, index=True)
    priority = Column(Enum(JobPriority, native_enum=False), default=JobPriority.MEDIUM, nullable=False, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    
    status = Column(Enum(JobStatus, native_enum=False), default=JobStatus.SUBMITTED, nullable=False, index=True)
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    logs = Column(Text, nullable=True, default="")
    
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    run_timeout_seconds = Column(Integer, default=120, nullable=False)
    
    worker_id = Column(String(100), nullable=True, index=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="jobs")
    executions = relationship("JobExecution", back_populates="job", cascade="all, delete-orphan", order_by="JobExecution.attempt_number")


class JobExecution(Base):
    __tablename__ = "job_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_number = Column(Integer, nullable=False)
    worker_id = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    error = Column(Text, nullable=True)
    logs = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Float, nullable=True)

    job = relationship("Job", back_populates="executions")
