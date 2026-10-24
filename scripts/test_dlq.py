import urllib.request
import json
import time

base = "http://127.0.0.1:8000/api"

# 1. Login
login_data = json.dumps({"email": "admin@jobqueue.io", "password": "Admin@123456"}).encode()
req = urllib.request.Request(f"{base}/auth/login", data=login_data, headers={"Content-Type": "application/json"})
auth = json.loads(urllib.request.urlopen(req).read().decode())
token = auth["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# 2. Submit a failing job with max_retries=1 so it goes straight to DLQ after 1 retry
failing_job = {
    "job_type": "webhook_delivery",
    "priority": "high",
    "payload": {"url": "https://flaky-partner.io/webhook", "simulate_fail": True},
    "max_retries": 1
}

req = urllib.request.Request(f"{base}/jobs/", data=json.dumps(failing_job).encode(), headers=headers)
sub = json.loads(urllib.request.urlopen(req).read().decode())
job_id = sub["id"]
print(f"Submitted failing job: {job_id}")

# Wait for worker
time.sleep(2)

# Check status
req = urllib.request.Request(f"{base}/jobs/{job_id}", headers=headers)
job_info = json.loads(urllib.request.urlopen(req).read().decode())
print(f"Status after worker execution: {job_info['status']}")
print(f"Retry count: {job_info['retry_count']} / {job_info['max_retries']}")
print(f"Error message: {job_info.get('error_message')}")

# Inspect DLQ
req = urllib.request.Request(f"{base}/admin/dlq", headers=headers)
dlq = json.loads(urllib.request.urlopen(req).read().decode())
print(f"\nDLQ items count: {len(dlq)}")
matching = [x for x in dlq if x.get("job_id") == job_id]
if matching:
    print(f"Found job in DLQ! Metadata: {matching[0].get('metadata')}")

# Retry job from DLQ
req = urllib.request.Request(f"{base}/admin/dlq/{job_id}/retry", data=b"{}", headers=headers)
requeued = json.loads(urllib.request.urlopen(req).read().decode())
print(f"Requeued status: {requeued['status']}")
