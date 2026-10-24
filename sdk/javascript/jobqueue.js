/**
 * Nexus Distributed Job Queue - Official Node.js / JavaScript Client SDK
 * Drop-in client library for Express, Next.js, Fastify, and Node microservices.
 */

class JobQueue {
  constructor(options = {}) {
    this.baseUrl = (options.baseUrl || 'http://127.0.0.1:8000').replace(/\/$/, '');
    this.apiKey = options.apiKey || 'jq_live_enterprise_secret_key';
    this.headers = {
      'Content-Type': 'application/json',
      'X-API-Key': this.apiKey,
    };
  }

  /**
   * Dispatches a background job to the queue.
   */
  async dispatch(jobType, payload, options = {}) {
    const taskPayload = { ...payload };
    if (options.webhookUrl) {
      taskPayload.webhook_url = options.webhookUrl;
    }

    const body = {
      job_type: jobType,
      priority: options.priority || 'medium', // 'high' | 'medium' | 'low'
      payload: taskPayload,
      idempotency_key: options.idempotencyKey,
      max_retries: options.maxRetries ?? 3,
      run_timeout_seconds: options.runTimeoutSeconds ?? 120,
    };

    const res = await fetch(`${this.baseUrl}/api/jobs/`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(`Queue Dispatch Error: ${err.detail || res.statusText}`);
    }

    return res.json();
  }

  /**
   * Retrieves the live status and execution results of a job.
   */
  async getStatus(jobId) {
    const res = await fetch(`${this.baseUrl}/api/jobs/${jobId}`, {
      headers: this.headers,
    });
    if (!res.ok) throw new Error(`Fetch error: ${res.statusText}`);
    return res.json();
  }

  /**
   * Polls until the worker completes execution.
   */
  async waitForCompletion(jobId, pollIntervalMs = 500, timeoutMs = 60000) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      const info = await this.getStatus(jobId);
      if (['COMPLETED', 'DEAD_LETTER', 'CANCELLED'].includes(info.status)) {
        return info;
      }
      await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
    }
    throw new Error(`Job ${jobId} timed out after ${timeoutMs}ms`);
  }
}

module.exports = { JobQueue };
