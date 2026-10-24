from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.user import User, UserRole
from app.models.job import JobStatus, JobPriority, Job
from app.models.audit import AuditLog
from app.schemas.job import JobResponse, JobDetailResponse, JobStatsResponse, QueueStatsResponse
from app.schemas.user import UserResponse, UserStatusUpdate, UserRoleUpdate, AuditLogResponse
from app.services.job_service import JobService
from app.services.audit_service import AuditService
from app.core.dependencies import get_current_admin
from app.core.queue_manager import QueueManager

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(get_current_admin)])


@router.get("/jobs", response_model=List[JobResponse])
async def list_all_jobs(
    job_type: Optional[str] = Query(None),
    status: Optional[JobStatus] = Query(None),
    priority: Optional[JobPriority] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """Admin view: list all jobs across all users."""
    jobs, _ = await JobService.list_jobs(
        db=db,
        user=None,  # None means all users
        job_type=job_type,
        status_filter=status,
        priority=priority,
        skip=skip,
        limit=limit
    )
    return jobs


@router.get("/stats", response_model=Dict[str, Any])
async def get_system_stats(db: AsyncSession = Depends(get_db)):
    """Admin view: system-wide jobs and queue lengths."""
    job_stats = await JobService.get_stats(db=db, user=None)
    q_lengths = await QueueManager.get_queue_lengths()
    
    return {
        "job_stats": job_stats,
        "queue_stats": {
            "high_priority_queue": q_lengths["high"],
            "medium_priority_queue": q_lengths["medium"],
            "low_priority_queue": q_lengths["low"],
            "delayed_queue": q_lengths["delayed"],
            "dead_letter_queue": q_lengths["dead_letter"],
            "total_in_queue": q_lengths["total"]
        }
    }


@router.get("/dlq", response_model=List[Dict[str, Any]])
async def get_dead_letter_queue(
    start: int = Query(0, ge=0),
    count: int = Query(50, ge=1, le=100)
):
    """Inspect jobs currently inside Dead-Letter Queue."""
    return await QueueManager.get_dead_letter_jobs(start=start, count=count)


@router.post("/dlq/{job_id}/retry", response_model=JobResponse)
async def retry_dead_letter_job(
    job_id: str,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Admin action: requeue a dead-letter job."""
    return await JobService.retry_job(db=db, job_id=job_id, user=admin_user)


@router.post("/dlq/purge")
async def purge_dead_letter_queue(
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Admin action: purge all items from Dead-Letter Queue."""
    purged_count = await QueueManager.purge_dead_letter()
    await AuditService.log_action(
        db=db,
        user_id=admin_user.id,
        action="DLQ_PURGED",
        target_type="QUEUE",
        target_id="dead_letter",
        details={"purged_count": purged_count}
    )
    return {"message": f"Purged {purged_count} jobs from Dead-Letter Queue"}


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Admin view: list registered users."""
    stmt = select(User).order_by(desc(User.created_at)).offset(skip).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.patch("/users/{user_id}/status", response_model=UserResponse)
async def toggle_user_status(
    user_id: int,
    status_update: UserStatusUpdate,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Admin action: activate or suspend a user account."""
    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    target_user = res.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    target_user.is_active = status_update.is_active
    await db.commit()
    await db.refresh(target_user)

    await AuditService.log_action(
        db=db,
        user_id=admin_user.id,
        action="USER_STATUS_UPDATED",
        target_type="USER",
        target_id=str(target_user.id),
        details={"new_active_status": target_user.is_active}
    )
    return target_user


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    role_update: UserRoleUpdate,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Admin action: change a user's role (USER or ADMIN)."""
    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    target_user = res.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    target_user.role = role_update.role
    await db.commit()
    await db.refresh(target_user)

    await AuditService.log_action(
        db=db,
        user_id=admin_user.id,
        action="USER_ROLE_UPDATED",
        target_type="USER",
        target_id=str(target_user.id),
        details={"new_role": target_user.role.value}
    )
    return target_user


@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Admin view: inspect security and operational audit logs."""
    stmt = select(AuditLog).order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()
