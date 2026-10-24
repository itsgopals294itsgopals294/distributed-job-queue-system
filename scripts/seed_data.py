import os
import sys
import asyncio
import uuid
from datetime import datetime, timezone, timedelta

# Ensure backend modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlalchemy import select
from app.database import AsyncSessionLocal, init_db
from app.models.user import User, UserRole
from app.models.job import Job, JobExecution, JobStatus, JobPriority
from app.models.worker import WorkerNode
from app.core.security import hash_password
from app.core.queue_manager import QueueManager
from app.core.redis import RedisClient


async def seed():
    print("Connecting to database & Redis...")
    await init_db()
    await RedisClient.get_client()

    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        # 1. Create Admin & Test Users
        users_data = [
            ("admin@jobqueue.io", "Admin@123456", "System Administrator", UserRole.ADMIN),
            ("alice@company.com", "Password123!", "Alice Engineer", UserRole.USER),
            ("bob@company.com", "Password123!", "Bob DataScientist", UserRole.USER),
            ("carol@company.com", "Password123!", "Carol Designer", UserRole.USER),
        ]

        created_users = {}
        for email, pwd, name, role in users_data:
            res = await session.execute(select(User).where(User.email == email))
            existing = res.scalar_one_or_none()
            if not existing:
                u = User(
                    email=email,
                    hashed_password=hash_password(pwd),
                    full_name=name,
                    role=role,
                    is_active=True,
                    created_at=now
                )
                session.add(u)
                await session.commit()
                await session.refresh(u)
                created_users[email] = u
                print(f"Created user: {email} ({role.value})")
            else:
                created_users[email] = existing

        alice = created_users["alice@company.com"]
        bob = created_users["bob@company.com"]

        # 2. Register sample workers
        workers_data = [
            ("worker-node-alpha-01", "compute-cluster-us-east-1", "ONLINE", 142, 3),
            ("worker-node-beta-02", "compute-cluster-us-east-2", "ONLINE", 98, 1),
            ("worker-node-gamma-03", "compute-cluster-eu-west-1", "ONLINE", 64, 0),
        ]
        for wid, hname, stat, comp, fail in workers_data:
            res = await session.execute(select(WorkerNode).where(WorkerNode.worker_id == wid))
            if not res.scalar_one_or_none():
                wn = WorkerNode(
                    worker_id=wid,
                    hostname=hname,
                    status=stat,
                    jobs_completed=comp,
                    jobs_failed=fail,
                    started_at=now - timedelta(hours=8),
                    last_heartbeat=now
                )
                session.add(wn)
        await session.commit()
        print("Registered worker nodes.")

        # 3. Create Sample Jobs in various lifecycle states
        sample_jobs = [
            # Completed Email Job
            {
                "user_id": alice.id,
                "job_type": "email_dispatch",
                "priority": JobPriority.HIGH,
                "payload": {"to": "investor@venture.com", "subject": "Q3 Financial Highlights"},
                "status": JobStatus.COMPLETED,
                "result": {"status": "delivered", "message_id": "msg_9012384"},
                "logs": "[2026-10-24 10:00:00] Task 'email_dispatch' execution started.\nSMTP connection TLS 1.3 verified.\nEmail delivered.",
                "duration": 420.5
            },
            # Completed Data Export Job
            {
                "user_id": bob.id,
                "job_type": "data_export",
                "priority": JobPriority.MEDIUM,
                "payload": {"format": "parquet", "record_count": 50000},
                "status": JobStatus.COMPLETED,
                "result": {"exported_records": 50000, "file_size_bytes": 14200000, "download_url": "https://exports.internal.io/files/export_50k.parquet"},
                "logs": "Extracting 50k records from warehouse.\nOptimizing column encodings.\nCompression completed.",
                "duration": 1850.0
            },
            # Running ML Inference Job
            {
                "user_id": bob.id,
                "job_type": "ml_inference",
                "priority": JobPriority.HIGH,
                "payload": {"model": "llama-summarizer", "inputs": ["The customer was delighted with fast resolution."]},
                "status": JobStatus.RUNNING,
                "worker_id": "worker-node-alpha-01",
                "started_at": now - timedelta(seconds=12),
                "logs": "Loaded model weights into VRAM.\nEvaluating input tokens...",
                "duration": None
            },
            # Queued Image Resize
            {
                "user_id": alice.id,
                "job_type": "image_resize",
                "priority": JobPriority.MEDIUM,
                "payload": {"image_url": "https://assets.example.com/banner-hero.png", "dimensions": ["thumb_100", "hd_1080"]},
                "status": JobStatus.QUEUED,
                "logs": None,
                "duration": None
            },
            # Dead Letter Queue Job
            {
                "user_id": alice.id,
                "job_type": "webhook_delivery",
                "priority": JobPriority.LOW,
                "payload": {"url": "https://unreachable-partner-api.com/webhooks", "simulate_fail": True},
                "status": JobStatus.DEAD_LETTER,
                "error_message": "RemoteHostError: HTTP 500 Internal Server Error (Exceeded 3 retries)",
                "retry_count": 3,
                "max_retries": 3,
                "logs": "Attempt 1 failed: Connection refused.\nAttempt 2 failed: 504 Gateway Timeout.\nAttempt 3 failed: 500 Internal Server Error.",
                "duration": 950.0
            }
        ]

        for sj in sample_jobs:
            jid = str(uuid.uuid4())
            dur = sj.pop("duration", None)
            logs = sj.pop("logs", "")
            j = Job(
                id=jid,
                user_id=sj["user_id"],
                job_type=sj["job_type"],
                priority=sj["priority"],
                payload=sj["payload"],
                status=sj["status"],
                result=sj.get("result"),
                error_message=sj.get("error_message"),
                logs=logs,
                retry_count=sj.get("retry_count", 0),
                max_retries=sj.get("max_retries", 3),
                worker_id=sj.get("worker_id"),
                started_at=sj.get("started_at"),
                completed_at=now if sj["status"] in [JobStatus.COMPLETED, JobStatus.DEAD_LETTER] else None,
                created_at=now - timedelta(minutes=15)
            )
            session.add(j)
            await session.commit()

            # Record execution attempt if completed or failed
            if sj["status"] in [JobStatus.COMPLETED, JobStatus.DEAD_LETTER]:
                session.add(JobExecution(
                    job_id=jid,
                    attempt_number=1,
                    worker_id="worker-node-alpha-01",
                    status="SUCCESS" if sj["status"] == JobStatus.COMPLETED else "FAILED",
                    logs=logs,
                    error=sj.get("error_message"),
                    started_at=now - timedelta(minutes=14),
                    finished_at=now - timedelta(minutes=14) + timedelta(seconds=2),
                    duration_ms=dur
                ))
                await session.commit()

            # If queued, also enqueue in Redis
            if sj["status"] == JobStatus.QUEUED:
                await QueueManager.push_job(jid, sj["priority"])
            elif sj["status"] == JobStatus.DEAD_LETTER:
                await QueueManager.push_dead_letter(jid, {"reason": sj.get("error_message")})

        print("Seeded sample jobs successfully.")
    print("Seed complete!")


if __name__ == "__main__":
    asyncio.run(seed())
