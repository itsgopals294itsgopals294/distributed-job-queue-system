import {
  AuthResponse,
  User,
  Job,
  JobStats,
  QueueStats,
  WorkerNode,
  AuditLog,
  JobPriority,
  JobStatus,
} from '../types';

const API_BASE = '/api';

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (res.status === 401) {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login';
    throw new Error('Unauthorized session expired');
  }

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorBody.detail || 'An error occurred during API request');
  }

  return res.json();
}

export const api = {
  // Authentication
  async login(email: string, password: string): Promise<AuthResponse> {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    return handleResponse<AuthResponse>(res);
  },

  async register(email: string, password: string, full_name?: string): Promise<User> {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, full_name }),
    });
    return handleResponse<User>(res);
  },

  async getMe(): Promise<User> {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<User>(res);
  },

  // Jobs
  async submitJob(payload: {
    job_type: string;
    priority: JobPriority;
    payload: Record<string, any>;
    idempotency_key?: string;
    max_retries?: number;
    run_timeout_seconds?: number;
  }): Promise<Job> {
    const res = await fetch(`${API_BASE}/jobs/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse<Job>(res);
  },

  async getMyJobs(params?: {
    job_type?: string;
    status?: JobStatus;
    priority?: JobPriority;
  }): Promise<Job[]> {
    const searchParams = new URLSearchParams();
    if (params?.job_type) searchParams.append('job_type', params.job_type);
    if (params?.status) searchParams.append('status', params.status);
    if (params?.priority) searchParams.append('priority', params.priority);

    const query = searchParams.toString();
    const res = await fetch(`${API_BASE}/jobs/${query ? `?${query}` : ''}`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<Job[]>(res);
  },

  async getJobDetail(jobId: string): Promise<Job> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<Job>(res);
  },

  async cancelJob(jobId: string): Promise<Job> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/cancel`, {
      method: 'POST',
      headers: { ...getAuthHeader() },
    });
    return handleResponse<Job>(res);
  },

  async retryJob(jobId: string): Promise<Job> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/retry`, {
      method: 'POST',
      headers: { ...getAuthHeader() },
    });
    return handleResponse<Job>(res);
  },

  async getMyJobStats(): Promise<JobStats> {
    const res = await fetch(`${API_BASE}/jobs/stats`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<JobStats>(res);
  },

  // Admin APIs
  async getAllJobs(params?: {
    job_type?: string;
    status?: JobStatus;
    priority?: JobPriority;
  }): Promise<Job[]> {
    const searchParams = new URLSearchParams();
    if (params?.job_type) searchParams.append('job_type', params.job_type);
    if (params?.status) searchParams.append('status', params.status);
    if (params?.priority) searchParams.append('priority', params.priority);

    const query = searchParams.toString();
    const res = await fetch(`${API_BASE}/admin/jobs${query ? `?${query}` : ''}`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<Job[]>(res);
  },

  async getAdminStats(): Promise<{ job_stats: JobStats; queue_stats: QueueStats }> {
    const res = await fetch(`${API_BASE}/admin/stats`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<{ job_stats: JobStats; queue_stats: QueueStats }>(res);
  },

  async getDLQ(): Promise<Array<{ job_id: string; moved_at: number; metadata: any }>> {
    const res = await fetch(`${API_BASE}/admin/dlq`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<Array<{ job_id: string; moved_at: number; metadata: any }>>(res);
  },

  async retryDLQJob(jobId: string): Promise<Job> {
    const res = await fetch(`${API_BASE}/admin/dlq/${jobId}/retry`, {
      method: 'POST',
      headers: { ...getAuthHeader() },
    });
    return handleResponse<Job>(res);
  },

  async purgeDLQ(): Promise<{ message: string }> {
    const res = await fetch(`${API_BASE}/admin/dlq/purge`, {
      method: 'POST',
      headers: { ...getAuthHeader() },
    });
    return handleResponse<{ message: string }>(res);
  },

  async getWorkers(): Promise<WorkerNode[]> {
    const res = await fetch(`${API_BASE}/workers/`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<WorkerNode[]>(res);
  },

  async drainWorker(workerId: string): Promise<{ message: string }> {
    const res = await fetch(`${API_BASE}/workers/${workerId}/drain`, {
      method: 'POST',
      headers: { ...getAuthHeader() },
    });
    return handleResponse<{ message: string }>(res);
  },

  async getUsers(): Promise<User[]> {
    const res = await fetch(`${API_BASE}/admin/users`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<User[]>(res);
  },

  async toggleUserStatus(userId: number, is_active: boolean): Promise<User> {
    const res = await fetch(`${API_BASE}/admin/users/${userId}/status`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify({ is_active }),
    });
    return handleResponse<User>(res);
  },

  async updateUserRole(userId: number, role: 'USER' | 'ADMIN'): Promise<User> {
    const res = await fetch(`${API_BASE}/admin/users/${userId}/role`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify({ role }),
    });
    return handleResponse<User>(res);
  },

  async getAuditLogs(): Promise<AuditLog[]> {
    const res = await fetch(`${API_BASE}/admin/audit-logs`, {
      headers: { ...getAuthHeader() },
    });
    return handleResponse<AuditLog[]>(res);
  },
};
