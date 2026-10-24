from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base


class WorkerNode(Base):
    __tablename__ = "worker_nodes"

    worker_id = Column(String(100), primary_key=True)
    hostname = Column(String(255), nullable=False)
    status = Column(String(50), default="ONLINE", nullable=False)  # ONLINE, DRAINING, STOPPED, OFFLINE
    current_job_id = Column(String(36), nullable=True)
    jobs_completed = Column(Integer, default=0, nullable=False)
    jobs_failed = Column(Integer, default=0, nullable=False)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_heartbeat = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
