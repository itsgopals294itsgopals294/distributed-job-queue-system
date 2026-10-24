from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict
from app.models.user import UserRole
from app.schemas.auth import UserResponse


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserRoleUpdate(BaseModel):
    role: UserRole


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    action: str
    target_type: str
    target_id: Optional[str] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkerNodeResponse(BaseModel):
    worker_id: str
    hostname: str
    status: str
    current_job_id: Optional[str] = None
    jobs_completed: int
    jobs_failed: int
    started_at: datetime
    last_heartbeat: datetime

    model_config = ConfigDict(from_attributes=True)
