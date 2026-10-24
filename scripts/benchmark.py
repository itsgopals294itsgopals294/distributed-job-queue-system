import sys
import time
import asyncio
import statistics
import random
from typing import List
import httpx

BASE_URL = "http://localhost:8000"


async def run_benchmark(total_jobs: int = 100, concurrency: int = 10):
    print("=" * 60)
    print(f"DISTRIBUTED JOB QUEUE BENCHMARK")
    print(f"Target: {BASE_URL}")
    print(f"Total Jobs to Submit: {total_jobs} | Concurrency: {concurrency}")
    print("=" * 60)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Check health
        try:
            h = await client.get("/health")
            if h.status_code != 200:
                print(f"Backend unhealthy: {h.status_code}")
                return
        except Exception as e:
            print(f"Cannot connect to backend at {BASE_URL}: {e}")
            print("Please ensure the FastAPI backend is running.")
            return

        # Login as Admin or Seed User
        auth_res = await client.post("/api/auth/login", json={
            "email": "admin@jobqueue.io",
            "password": "Admin@123456"
        })
        if auth_res.status_code != 200:
            print("Admin login failed, creating benchmark user...")
            bench_email = f"bench_{int(time.time())}@bench.com"
            reg = await client.post("/api/auth/register", json={
                "email": bench_email,
                "password": "BenchmarkPassword123!",
                "full_name": "Benchmark Agent"
            })
            token = (await client.post("/api/auth/login", json={
                "email": bench_email,
                "password": "BenchmarkPassword123!"
            })).json()["access_token"]
        else:
            token = auth_res.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}
        print("Authenticated successfully. Starting submission benchmark...\n")

        sem = asyncio.Semaphore(concurrency)
        latencies: List[float] = []
        job_ids: List[str] = []
        job_types = ["custom_calc", "data_export", "image_resize", "email_dispatch"]
        priorities = ["high", "medium", "low"]

        async def submit_single(idx: int):
            async with sem:
                start = time.perf_counter()
                payload = {
                    "job_type": random.choice(job_types),
                    "priority": random.choice(priorities),
                    "payload": {"n": 20, "index": idx, "batch": "benchmark"},
                    "max_retries": 2
                }
                res = await client.post("/api/jobs/", json=payload, headers=headers)
                elapsed = (time.perf_counter() - start) * 1000
                latencies.append(elapsed)
                if res.status_code in [200, 201]:
                    job_ids.append(res.json()["id"])
                else:
                    print(f"Failed submission #{idx}: {res.status_code} - {res.text}")

        bench_start = time.perf_counter()
        tasks = [submit_single(i) for i in range(total_jobs)]
        await asyncio.gather(*tasks)
        total_time = time.perf_counter() - bench_start

        # Statistics
        rps = len(latencies) / total_time
        avg_lat = statistics.mean(latencies)
        p50 = statistics.median(latencies)
        sorted_lat = sorted(latencies)
        p90 = sorted_lat[int(len(sorted_lat) * 0.90)]
        p99 = sorted_lat[int(len(sorted_lat) * 0.99)]

        print("--- BENCHMARK SUBMISSION RESULTS ---")
        print(f"Total Submitted:     {len(job_ids)} / {total_jobs}")
        print(f"Total Duration:      {total_time:.2f} s")
        print(f"Throughput:          {rps:.1f} submissions/sec")
        print(f"Avg Latency:         {avg_lat:.2f} ms")
        print(f"Median (p50):        {p50:.2f} ms")
        print(f"90th Percentile:     {p90:.2f} ms")
        print(f"99th Percentile:     {p99:.2f} ms")
        print("-" * 60)

        # Monitor execution completion
        print("\nMonitoring asynchronous execution by background workers...")
        start_wait = time.time()
        completed = 0
        while time.time() - start_wait < 60:
            stats_res = await client.get("/api/admin/stats", headers=headers)
            if stats_res.status_code == 200:
                s = stats_res.json().get("job_stats", {})
                completed = s.get("completed", 0)
                queued = s.get("queued", 0)
                running = s.get("running", 0)
                print(f"[Elapsed {(time.time()-start_wait):.1f}s] Queued: {queued} | Running: {running} | Completed: {completed}")
                if queued == 0 and running == 0:
                    print("All jobs have been processed by workers!")
                    break
            await asyncio.sleep(2.0)


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    concurr = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    asyncio.run(run_benchmark(count, concurr))
