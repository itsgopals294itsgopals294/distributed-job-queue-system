import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_job_submission_and_idempotency(async_client: AsyncClient, user_token: str):
    headers = {"Authorization": f"Bearer {user_token}"}
    payload = {
        "job_type": "email_dispatch",
        "priority": "high",
        "payload": {"to": "customer@test.com", "subject": "Order Confirmed"},
        "idempotency_key": "unique-order-key-1001",
        "max_retries": 3
    }

    # 1. First submission
    res1 = await async_client.post("/api/jobs/", json=payload, headers=headers)
    assert res1.status_code == 201
    job1 = res1.json()
    assert job1["job_type"] == "email_dispatch"
    assert job1["priority"] == "high"
    assert job1["status"] == "QUEUED"

    # 2. Duplicate submission with same idempotency_key must return existing job
    res2 = await async_client.post("/api/jobs/", json=payload, headers=headers)
    assert res2.status_code == 201
    job2 = res2.json()
    assert job2["id"] == job1["id"]


@pytest.mark.asyncio
async def test_job_cancellation_and_rbac(
    async_client: AsyncClient,
    user_token: str,
    admin_token: str
):
    headers_user = {"Authorization": f"Bearer {user_token}"}
    headers_admin = {"Authorization": f"Bearer {admin_token}"}

    # Submit job as user
    sub_res = await async_client.post("/api/jobs/", json={
        "job_type": "data_export",
        "priority": "medium",
        "payload": {"format": "csv", "record_count": 100}
    }, headers=headers_user)
    assert sub_res.status_code == 201
    job_id = sub_res.json()["id"]

    # Cancel job
    cancel_res = await async_client.post(f"/api/jobs/{job_id}/cancel", headers=headers_user)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    # Retry cancelled job
    retry_res = await async_client.post(f"/api/jobs/{job_id}/retry", headers=headers_user)
    assert retry_res.status_code == 200
    assert retry_res.json()["status"] == "QUEUED"

    # Admin can view all jobs
    admin_jobs_res = await async_client.get("/api/admin/jobs", headers=headers_admin)
    assert admin_jobs_res.status_code == 200
    ids = [j["id"] for j in admin_jobs_res.json()]
    assert job_id in ids
