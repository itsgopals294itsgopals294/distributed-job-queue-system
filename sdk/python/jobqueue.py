"""
Nexus Distributed Job Queue - Official Python Client SDK
Drop-in client library for any Python application (Django, Flask, FastAPI, scripts).
"""

import time
import requests
from typing import Dict, Any, Optional


class JobQueue:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        api_key: str = "jq_live_enterprise_secret_key"
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }

    def dispatch(
        self,
        job_type: str,
        payload: Dict[str, Any],
        priority: str = "medium",  # "high", "medium", "low"
        idempotency_key: Optional[str] = None,
        max_retries: int = 3,
        run_timeout_seconds: int = 120,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submits an asynchronous background task to the distributed queue.
        Returns the created job metadata immediately.
        """
        task_payload = dict(payload)
        if webhook_url:
            task_payload["webhook_url"] = webhook_url

        body = {
            "job_type": job_type,
            "priority": priority,
            "payload": task_payload,
            "idempotency_key": idempotency_key,
            "max_retries": max_retries,
            "run_timeout_seconds": run_timeout_seconds
        }

        url = f"{self.base_url}/api/jobs/"
        res = requests.post(url, json=body, headers=self.headers, timeout=10.0)
        res.raise_for_status()
        return res.json()

    def get_status(self, job_id: str) -> Dict[str, Any]:
        """Retrieves real-time status, result, and logs for a job."""
        url = f"{self.base_url}/api/jobs/{job_id}"
        res = requests.get(url, headers=self.headers, timeout=10.0)
        res.raise_for_status()
        return res.json()

    def wait_for_completion(
        self,
        job_id: str,
        poll_interval_seconds: float = 0.5,
        timeout_seconds: float = 60.0
    ) -> Dict[str, Any]:
        """
        Polls until the background worker finishes the task.
        Returns the completed result dictionary.
        """
        start = time.time()
        while time.time() - start < timeout_seconds:
            status = self.get_status(job_id)
            state = status.get("status")
            if state in ["COMPLETED", "DEAD_LETTER", "CANCELLED"]:
                return status
            time.sleep(poll_interval_seconds)
        raise TimeoutError(f"Job {job_id} did not complete within {timeout_seconds}s")


# --- Quick Usage Example ---
if __name__ == "__main__":
    queue = JobQueue()
    print("Dispatching background task from Python SDK...")
    job = queue.dispatch(
        job_type="email_dispatch",
        priority="high",
        payload={"to": "client@realworld.com", "subject": "Welcome to our Service!"}
    )
    print(f"Task accepted in {job['id']}. Waiting for worker...")
    result = queue.wait_for_completion(job["id"])
    print(f"Task finished with status: {result['status']}")
    print(f"Result: {result['result']}")
