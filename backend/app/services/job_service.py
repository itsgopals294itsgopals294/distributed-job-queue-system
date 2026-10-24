import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.job import Job, JobExecution, JobStatus, JobPriority
from app.models.user import User, UserRole
from app.schemas.job import JobCreate, JobStatsResponse
from app.core.queue_manager import QueueManager
from app.services.audit_service import AuditService


class JobService:
    @staticmethod
    async def submit_job(db: AsyncSession, user: User, job_in: JobCreate) -> Job:
        # Idempotency verification
        if job_in.idempotency_key:
            existing_job_id = await QueueManager.get_idempotent_job_id(job_in.idempotency_key)
            if existing_job_id:
                # Return already created job
                stmt = select(Job).where(Job.id == existing_job_id)
                res = await db.execute(stmt)
                existing_job = res.scalar_one_or_none()
                if existing_job:
                    return existing_job

            # Also check DB unique constraint for idempotency key
            stmt = select(Job).where(Job.idempotency_key == job_in.idempotency_key)
            res = await db.execute(stmt)
            existing_job = res.scalar_one_or_none()
            if existing_job:
                await QueueManager.set_idempotency_key(job_in.idempotency_key, existing_job.id)
                return existing_job

        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            user_id=user.id,
            idempotency_key=job_in.idempotency_key,
            job_type=job_in.job_type,
            priority=job_in.priority,
            payload=job_in.payload,
            status=JobStatus.QUEUED,
            retry_count=0,
            max_retries=job_in.max_retries or 3,
            run_timeout_seconds=job_in.run_timeout_seconds or 120,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        # Set idempotency key in Redis cache
        if job_in.idempotency_key:
            await QueueManager.set_idempotency_key(job_in.idempotency_key, job.id)

        # Enqueue into Redis priority queue
        await QueueManager.push_job(job.id, job.priority)

        # Audit log
        await AuditService.log_action(
            db=db,
            user_id=user.id,
            action="JOB_SUBMITTED",
            target_type="JOB",
            target_id=job.id,
            details={"job_type": job.job_type, "priority": job.priority.value}
        )

        return job

    @staticmethod
    async def get_job_by_id(
        db: AsyncSession,
        job_id: str,
        user: Optional[User] = None
    ) -> Job:
        stmt = (
            select(Job)
            .options(selectinload(Job.executions))
            .where(Job.id == job_id)
        )
        res = await db.execute(stmt)
        job = res.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

        # Permission check: regular user can only access their own jobs
        if user and user.role != UserRole.ADMIN and job.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this job")

        return job

    @staticmethod
    async def cancel_job(db: AsyncSession, job_id: str, user: User) -> Job:
        job = await JobService.get_job_by_id(db, job_id, user)

        if job.status in [JobStatus.COMPLETED, JobStatus.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel job in status '{job.status.value}'"
            )

        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.now(timezone.utc)
        job.error_message = f"Cancelled by user {user.email}"
        await db.commit()
        await db.refresh(job)

        # Signal queue and active workers
        await QueueManager.mark_cancelled(job.id)

        await AuditService.log_action(
            db=db,
            user_id=user.id,
            action="JOB_CANCELLED",
            target_type="JOB",
            target_id=job.id
        )

        return job

    @staticmethod
    async def retry_job(db: AsyncSession, job_id: str, user: User) -> Job:
        job = await JobService.get_job_by_id(db, job_id, user)

        if job.status not in [JobStatus.DEAD_LETTER, JobStatus.CANCELLED, JobStatus.RETRY_WAIT]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only failed, dead-letter, or cancelled jobs can be manually retried (current status: '{job.status.value}')"
            )

        # Clear cancelled flag if previously cancelled
        await QueueManager.clear_cancelled_flag(job.id)
        # Remove from DLQ if it was there
        await QueueManager.remove_from_dead_letter(job.id)

        job.status = JobStatus.QUEUED
        job.error_message = None
        job.worker_id = None
        job.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(job)

        # Push back into priority queue
        await QueueManager.push_job(job.id, job.priority)

        await AuditService.log_action(
            db=db,
            user_id=user.id,
            action="JOB_RETRIED",
            target_type="JOB",
            target_id=job.id
        )

        return job

    @staticmethod
    async def list_jobs(
        db: AsyncSession,
        user: Optional[User] = None,
        job_type: Optional[str] = None,
        status_filter: Optional[JobStatus] = None,
        priority: Optional[JobPriority] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Job], int]:
        filters = []
        if user and user.role != UserRole.ADMIN:
            filters.append(Job.user_id == user.id)
        if job_type:
            filters.append(Job.job_type == job_type)
        if status_filter:
            filters.append(Job.status == status_filter)
        if priority:
            filters.append(Job.priority == priority)

        # Total count
        count_stmt = select(func.count(Job.id)).where(and_(*filters) if filters else True)
        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one()

        # Query items
        stmt = (
            select(Job)
            .where(and_(*filters) if filters else True)
            .order_by(desc(Job.created_at))
            .offset(skip)
            .limit(limit)
        )
        res = await db.execute(stmt)
        jobs = res.scalars().all()

        return list(jobs), total

    @staticmethod
    async def get_stats(db: AsyncSession, user: Optional[User] = None) -> JobStatsResponse:
        filters = []
        if user and user.role != UserRole.ADMIN:
            filters.append(Job.user_id == user.id)

        stmt = (
            select(Job.status, func.count(Job.id))
            .where(and_(*filters) if filters else True)
            .group_by(Job.status)
        )
        res = await db.execute(stmt)
        counts = {status: count for status, count in res.all()}

        total = sum(counts.values())
        return JobStatsResponse(
            total_jobs=total,
            submitted=counts.get(JobStatus.SUBMITTED, 0),
            queued=counts.get(JobStatus.QUEUED, 0),
            running=counts.get(JobStatus.RUNNING, 0),
            completed=counts.get(JobStatus.COMPLETED, 0),
            retry_wait=counts.get(JobStatus.RETRY_WAIT, 0),
            dead_letter=counts.get(JobStatus.DEAD_LETTER, 0),
            cancelled=counts.get(JobStatus.CANCELLED, 0),
        )
