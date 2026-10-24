# Distributed Job Queue System

A production-inspired, fault-tolerant distributed job processing platform built with **FastAPI**, **Redis**, **PostgreSQL**, **Python Background Workers**, **React 19 + TypeScript**, and **Prometheus / Grafana**.

---

## 1. System Architecture

```
                    ┌─────────────────────────┐
                    │      USER / ADMIN       │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │     REACT FRONTEND      │
                    │   (Vite + TailwindCSS)  │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │     FASTAPI BACKEND     │
                    │   (JWT + RBAC + CORS)   │
                    └──────┬───────────┬──────┘
                           │           │
            ┌──────────────┘           └──────────────┐
            ▼                                         ▼
┌───────────────────────┐                 ┌───────────────────────┐
│  POSTGRESQL DATABASE  │                 │      REDIS QUEUE      │
│  - Users & Roles      │                 │  - queue:high         │
│  - Job Records        │                 │  - queue:medium       │
│  - Execution History  │                 │  - queue:low          │
│  - Worker Fleet Node  │                 │  - queue:delayed      │
│  - Audit Logs         │                 │  - queue:dead_letter  │
└───────────────────────┘                 └───────────┬───────────┘
            ▲                                         │
            │           ┌─────────────────────────────┤
            │           ▼                             ▼
            │ ┌───────────────────┐         ┌───────────────────┐
            │ │ BACKGROUND WORKER │         │  WATCHDOG REAPER  │
            │ │   (Worker Pool)   │         │ (Delayed Retries) │
            │ └─────────┬─────────┘         └─────────┬─────────┘
            └───────────┴─────────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  PROMETHEUS + GRAFANA   │
                    │  (/metrics Observability│
                    └─────────────────────────┘
```

---

## 2. Job Lifecycle State Machine

```
      [SUBMITTED]
           │
           ▼
        [QUEUED] ◄────────────────────────────────┐
           │                                      │
           ▼ (Popped by Worker)                   │
       [RUNNING]                                  │
      /    │    \                                 │
     /     │     \                                │
    /      │      \ (Retryable failure)           │
   /       │       ▼                              │
  /        │    [RETRY_WAIT]                      │
 /         │       │ (Exponential Backoff + Jitter)
│          │       └──────────────────────────────┘
▼          ▼
[COMPLETED] [CANCELLED]
           │
           ▼ (Max Retries Exceeded)
      [DEAD_LETTER]
```

---

## 3. Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS, Lucide React |
| **Backend API** | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 Async, PyJWT |
| **Database** | PostgreSQL 16 (with SQLite auto-fallback for zero-friction local dev) |
| **Queue & Cache** | Redis 7 (Priority Lists, Delayed ZSETs, Leases, Dead-Letter Queue) |
| **Workers** | Python Async Worker Pool with Heartbeats & Lease Renewal |
| **Watchdog** | Reaper service reclaiming crashed worker leases & scheduling delayed retries |
| **Deployment** | Docker & Docker Compose |
| **Observability** | Prometheus client (`/metrics`) and Pre-provisioned Grafana Dashboards |

---

## 4. Key Engineering Features

1. **Strict Priority Queuing**: Workers evaluate queues in strict order (`queue:high` $\rightarrow$ `queue:medium` $\rightarrow$ `queue:low`).
2. **Crash Recovery & Distributed Leases**: Every executing job acquires an exclusive lease in Redis with periodic heartbeats. If a worker dies, the Reaper watchdog automatically recovers orphaned jobs.
3. **Idempotency Guarantees**: Submit jobs with an `idempotency_key` to prevent duplicate side effects.
4. **Exponential Backoff Retries**: Failed jobs enter `RETRY_WAIT` with exponential backoff:
   $$\text{Delay} = \text{base} \times 2^{\text{attempt} - 1} + \text{jitter}$$
5. **Dead-Letter Queue (DLQ)**: When `retry_count >= max_retries`, jobs are isolated in DLQ with stack traces and error metadata. Admins can inspect and re-enqueue them with a single click.
6. **Role-Based Access Control (RBAC)**:
   - **Users**: Submit jobs, view execution logs, cancel active jobs, and retry failed jobs for their own tasks.
   - **Admins**: Cross-tenant visibility, DLQ management, worker drain commands, user account suspension, and security audit logs.
7. **Built-in Task Types**:
   - `email_dispatch`: SMTP transaction simulator with TLS handshake logs.
   - `data_export`: CSV, JSON, and Parquet data warehouse extraction.
   - `image_resize`: Multi-resolution responsive image generator.
   - `ml_inference`: GPU sentiment analysis simulator.
   - `webhook_delivery`: Cryptographically signed HTTP webhook dispatcher.
   - `custom_calc`: Fibonacci and prime sequence computation.

---

## 5. Live Interactive Interfaces & Real-World Integration

### A. Nexus Queue Matrix Dashboard (`http://127.0.0.1:8000/`)
A unified live control center serving real-time queue telemetry:
- **4-Lane Live Kanban Matrix**: Visualizes jobs moving in real time through `1. QUEUE BACKLOG` $\rightarrow$ `2. WORKER EXECUTING` $\rightarrow$ `3. COMMITTED` $\rightarrow$ `4. DEAD-LETTER QUEUE`.
- **One-Click Presets & Chaos Simulation**: Ingest high-priority emails, data warehouse exports, neural inference tasks, or trigger network timeouts to observe automated DLQ quarantining.
- **Worker Cluster Fleet Monitor**: Real-time worker node health, active task leases, and heartbeat renewals.
- **Autopilot Traffic Generator**: Automatically fires realistic customer traffic bursts to demo high-concurrency queue processing.

### B. Nexus Gear E-Commerce Storefront Demo (`http://127.0.0.1:5000/`)
A realistic e-commerce web application (`examples/sample_store_app.py`) demonstrating how external apps integrate with the queue via our Python SDK:
- **1-Click Checkout**: Immediately acknowledges orders in `< 50ms` while delegating heavy tasks (`email_dispatch`, `data_export`) to the background queue.
- **Real-Time Order Lifecycle Timeline**: Visually tracks the order from creation to queue dispatch, worker pickup, and customer delivery.
- **Flash Sale Simulation**: Sends concurrent bursts of customer orders and monitors non-blocking throughput.
- **Failure Injection**: Simulates SMTP downtime to demonstrate resilient retries and automatic Dead-Letter Queue quarantining without crashing the checkout process.

### C. Official Client SDKs
Drop-in client libraries for integrating any external system with Nexus Distributed Job Queue:
- **Python SDK**: [sdk/python/jobqueue.py](file:///G:/My%20Drive/antigravity/distributed-job-queue-system/sdk/python/jobqueue.py) (`from sdk.python.jobqueue import JobQueue`)
- **JavaScript SDK**: [sdk/javascript/jobqueue.js](file:///G:/My%20Drive/antigravity/distributed-job-queue-system/sdk/javascript/jobqueue.js) (`const { JobQueue } = require('./sdk/javascript/jobqueue');`)

---

## 6. Quickstart with Docker Compose

To start the entire cluster (PostgreSQL, Redis, Backend, 2 Workers, Reaper, Frontend, Prometheus, Grafana):

```bash
# Clone and enter the directory
cd "G:\My Drive\antigravity\distributed-job-queue-system"

# Start all 9 services
docker compose up --build
```

### Service URLs & Port Mappings:

| Service | URL | Default Credentials |
|---|---|---|
| **React Web Dashboard** | `http://localhost:3000` | Demo buttons on login page |
| **FastAPI Backend & Docs**| `http://localhost:8000/docs` | `admin@jobqueue.io` / `Admin@123456` |
| **Prometheus Metrics** | `http://localhost:9090` | None |
| **Grafana Dashboards** | `http://localhost:3001` | `admin` / `admin` |
| **PostgreSQL** | `localhost:5432` | `postgres` / `postgrespassword` |
| **Redis** | `localhost:6379` | None |

---

## 7. Running Locally (Without Docker)

You can run the backend, worker, watchdog, and storefront directly on your machine.

### Step 1: Backend API & Matrix Dashboard
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # On Windows
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Open **Nexus Matrix Control Center**: `http://127.0.0.1:8000/`

### Step 2: Start Background Worker
In a new terminal:
```bash
cd worker
python worker.py
```

### Step 3: Start Watchdog Reaper (Crash Recovery & Retries)
In a new terminal:
```bash
cd worker
python reaper.py
```

### Step 4: Start Nexus Gear Storefront App
In a new terminal:
```bash
cd examples
python sample_store_app.py
```
Open **Nexus Gear E-Commerce Store**: `http://127.0.0.1:5000/`

### Step 5: (Optional) Standalone React 19 Frontend
In a new terminal:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 8. Running Automated Tests

Run the test suite covering authentication, RBAC, priority queuing, delayed retries, and cancellation:

```bash
cd backend
pytest -v
```

---

## 9. High-Throughput Concurrency Benchmark

Run the automated load test script to benchmark submission throughput, latencies, and worker execution turnaround:

```bash
# Submit 100 jobs across 10 concurrent async connections
python scripts/benchmark.py 100 10
```

---

## 10. Pre-configured Demo Accounts

| Role | Email | Password | Permissions |
|---|---|---|---|
| **Admin** | `admin@jobqueue.io` | `Admin@123456` | Full system access, all jobs, DLQ, audit logs, worker controls |
| **User (Alice)** | `alice@company.com` | `Password123!` | Standard user, personal job dashboard |
| **User (Bob)** | `bob@company.com` | `Password123!` | Standard user, personal job dashboard |

*(Or click "Quick Fill Demo Accounts" on the login screen!)*
