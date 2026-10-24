export type UserRole = 'USER' | 'ADMIN';

export type JobStatus =
  | 'SUBMITTED'
  | 'QUEUED'
  | 'RUNNING'
  | 'COMPLETED'
  | 'RETRY_WAIT'
  | 'DEAD_LETTER'
  | 'CANCELLED';

export type JobPriority = 'high' | 'medium' | 'low';

export interface User {
  id: number;
  email: string;
  full_name?: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  email: string;
  role: UserRole;
  full_name?: string;
}

export interface JobExecution {
  id: number;
  attempt_number: number;
  worker_id: string;
  status: string;
  error?: string;
  logs?: string;
  started_at: string;
  finished_at?: string;
  duration_ms?: number;
}

export interface Job {
  id: string;
  user_id: number;
  job_type: string;
  priority: JobPriority;
  status: JobStatus;
  idempotency_key?: string;
  payload?: Record<string, any>;
  result?: Record<string, any>;
  error_message?: string;
  logs?: string;
  retry_count: number;
  max_retries: number;
  run_timeout_seconds: number;
  worker_id?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  executions?: JobExecution[];
}

export interface JobStats {
  total_jobs: number;
  submitted: number;
  queued: number;
  running: number;
  completed: number;
  retry_wait: number;
  dead_letter: number;
  cancelled: number;
}

export interface QueueStats {
  high_priority_queue: number;
  medium_priority_queue: number;
  low_priority_queue: number;
  delayed_queue: number;
  dead_letter_queue: number;
  total_in_queue: number;
}

export interface WorkerNode {
  worker_id: string;
  hostname: string;
  status: 'ONLINE' | 'DRAINING' | 'STOPPED' | 'OFFLINE';
  current_job_id?: string;
  jobs_completed: number;
  jobs_failed: number;
  started_at: string;
  last_heartbeat: string;
}

export interface AuditLog {
  id: number;
  user_id?: number;
  action: string;
  target_type: string;
  target_id?: string;
  details?: Record<string, any>;
  ip_address?: string;
  created_at: string;
}
