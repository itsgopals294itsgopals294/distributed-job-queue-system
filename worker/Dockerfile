FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy worker and backend dependencies
COPY . /app/worker
COPY ../backend /app/backend

WORKDIR /app/worker

CMD ["python", "worker.py"]
