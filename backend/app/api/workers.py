from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.worker import WorkerNode
from app.models.user import User
from app.schemas.user import WorkerNodeResponse
from app.core.dependencies import get_current_user, get_current_admin
from app.services.audit_service import AuditService

router = APIRouter(prefix="/workers", tags=["Workers"])


class WorkerHeartbeatRequest(BaseModel):
    worker_id: str
    hostname: str
    status: str = "ONLINE"
    current_job_id: Optional[str] = None
    jobs_completed: int = 0
    jobs_failed: int = 0


@router.get("/", response_model=List[WorkerNodeResponse])
async def list_workers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all registered worker nodes and their state."""
    stmt = select(WorkerNode).order_by(desc(WorkerNode.last_heartbeat))
    res = await db.execute(stmt)
    workers = res.scalars().all()
    
    # Auto mark inactive workers as OFFLINE if no heartbeat in 45 seconds
    now = datetime.now(timezone.utc)
    for w in workers:
        hb = w.last_heartbeat
        if hb:
            if hb.tzinfo is None:
                hb = hb.replace(tzinfo=timezone.utc)
            if (now - hb).total_seconds() > 45 and w.status == "ONLINE":
                w.status = "OFFLINE"
    await db.commit()
    
    return workers


@router.post("/heartbeat")
async def worker_heartbeat(
    req: WorkerHeartbeatRequest,
    db: AsyncSession = Depends(get_db)
):
    """Heartbeat endpoint invoked by background worker processes."""
    stmt = select(WorkerNode).where(WorkerNode.worker_id == req.worker_id)
    res = await db.execute(stmt)
    worker = res.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if not worker:
        worker = WorkerNode(
            worker_id=req.worker_id,
            hostname=req.hostname,
            status=req.status,
            current_job_id=req.current_job_id,
            jobs_completed=req.jobs_completed,
            jobs_failed=req.jobs_failed,
            started_at=now,
            last_heartbeat=now
        )
        db.add(worker)
    else:
        # If admin commanded drain, maintain draining status
        if worker.status != "DRAINING":
            worker.status = req.status
        worker.hostname = req.hostname
        worker.current_job_id = req.current_job_id
        worker.jobs_completed = req.jobs_completed
        worker.jobs_failed = req.jobs_failed
        worker.last_heartbeat = now

    await db.commit()
    return {"status": worker.status}


@router.post("/{worker_id}/drain")
async def drain_worker(
    worker_id: str,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Admin command to flag a worker node to gracefully drain and stop picking up new jobs."""
    stmt = select(WorkerNode).where(WorkerNode.worker_id == worker_id)
    res = await db.execute(stmt)
    worker = res.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker node not found")

    worker.status = "DRAINING"
    await db.commit()

    await AuditService.log_action(
        db=db,
        user_id=admin_user.id,
        action="WORKER_DRAIN_REQUESTED",
        target_type="WORKER",
        target_id=worker_id
    )

    return {"message": f"Worker {worker_id} set to DRAINING"}


@router.post("/{worker_id}/activate")
async def activate_worker(
    worker_id: str,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Admin command to re-activate a worker node."""
    stmt = select(WorkerNode).where(WorkerNode.worker_id == worker_id)
    res = await db.execute(stmt)
    worker = res.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker node not found")

    worker.status = "ONLINE"
    await db.commit()

    await AuditService.log_action(
        db=db,
        user_id=admin_user.id,
        action="WORKER_ACTIVATED",
        target_type="WORKER",
        target_id=worker_id
    )

    return {"message": f"Worker {worker_id} set to ONLINE"}
