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
print(f"Logged in successfully as {auth['email']} ({auth['role']})")

# 2. Submit jobs
jobs = [
    {"job_type": "email_dispatch", "priority": "high", "payload": {"to": "vip@client.com", "subject": "Live Demo"}},
    {"job_type": "custom_calc", "priority": "medium", "payload": {"n": 25}},
    {"job_type": "data_export", "priority": "low", "payload": {"format": "csv", "record_count": 1000}}
]

created_ids = []
for j in jobs:
    req = urllib.request.Request(f"{base}/jobs/", data=json.dumps(j).encode(), headers=headers)
    res = json.loads(urllib.request.urlopen(req).read().decode())
    created_ids.append((res["id"], res["job_type"], res["priority"]))
    print(f"Submitted {res['job_type']} ({res['priority']}) -> ID: {res['id']}")

# 3. Wait for background worker processing
print("\nWaiting 4 seconds for background worker to process queue...")
time.sleep(4)

# 4. Check results
for jid, jtype, priority in created_ids:
    req = urllib.request.Request(f"{base}/jobs/{jid}", headers=headers)
    detail = json.loads(urllib.request.urlopen(req).read().decode())
    print(f"\n--- Job: {jtype} [{priority}] ---")
    print(f"Status:    {detail.get('status')}")
    print(f"Worker:    {detail.get('worker_id')}")
    print(f"Result:    {detail.get('result')}")
    print(f"Logs:\n{detail.get('logs')}")

# 5. Check Prometheus metrics
req = urllib.request.Request("http://127.0.0.1:8000/metrics")
metrics_data = urllib.request.urlopen(req).read().decode()
active_workers_line = [line for line in metrics_data.splitlines() if "active_workers_count" in line and not line.startswith("#")]
print("\n--- Prometheus Live Metrics ---")
print("\n".join(active_workers_line))
