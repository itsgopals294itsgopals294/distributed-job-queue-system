from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.job import JobStatus, JobPriority
from app.schemas.job import (
    JobCreate,
    JobResponse,
    JobDetailResponse,
    JobStatsResponse,
)
from app.services.job_service import JobService
from app.core.dependencies import get_current_user, check_rate_limit

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(check_rate_limit)])
async def submit_job(
    job_in: JobCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit a new background job to the queue."""
    return await JobService.submit_job(db=db, user=current_user, job_in=job_in)


@router.get("/", response_model=List[JobResponse])
async def list_my_jobs(
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    status: Optional[JobStatus] = Query(None, description="Filter by status"),
    priority: Optional[JobPriority] = Query(None, description="Filter by priority"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List jobs submitted by the current user."""
    jobs, _ = await JobService.list_jobs(
        db=db,
        user=current_user,
        job_type=job_type,
        status_filter=status,
        priority=priority,
        skip=skip,
        limit=limit
    )
    return jobs


@router.get("/stats", response_model=JobStatsResponse)
async def get_my_job_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve job metrics and breakdown for current user."""
    return await JobService.get_stats(db=db, user=current_user)


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job_detail(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve complete job execution details, payload, result, and logs."""
    return await JobService.get_job_by_id(db=db, job_id=job_id, user=current_user)


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel an active or pending job."""
    return await JobService.cancel_job(db=db, job_id=job_id, user=current_user)


@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually retry a failed, dead-letter, or cancelled job."""
    return await JobService.retry_job(db=db, job_id=job_id, user=current_user)
