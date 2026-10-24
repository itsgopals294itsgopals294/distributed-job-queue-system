import React, { useEffect, useState } from 'react';
import {
  X,
  Play,
  RotateCcw,
  Ban,
  Clock,
  Cpu,
  Terminal,
  FileCode,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';
import { Job, JobExecution } from '../types';
import { api } from '../services/api';
import { JobStatusBadge } from './JobStatusBadge';
import { PriorityBadge } from './PriorityBadge';

interface Props {
  jobId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onActionComplete?: () => void;
}

export const JobDetailModal: React.FC<Props> = ({
  jobId,
  isOpen,
  onClose,
  onActionComplete,
}) => {
  const [job, setJob] = useState<Job | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isActing, setIsActing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchJob = async (id: string) => {
    try {
      const data = await api.getJobDetail(id);
      setJob(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch job');
    }
  };

  useEffect(() => {
    if (isOpen && jobId) {
      setIsLoading(true);
      fetchJob(jobId).finally(() => setIsLoading(false));

      // Poll every 2 seconds if job is active
      const interval = setInterval(() => {
        if (job?.status === 'QUEUED' || job?.status === 'RUNNING' || job?.status === 'RETRY_WAIT') {
          fetchJob(jobId);
        }
      }, 2000);

      return () => clearInterval(interval);
    } else {
      setJob(null);
    }
  }, [isOpen, jobId, job?.status]);

  if (!isOpen || !jobId) return null;

  const handleCancel = async () => {
    if (!job) return;
    setIsActing(true);
    try {
      await api.cancelJob(job.id);
      await fetchJob(job.id);
      onActionComplete?.();
    } catch (err: any) {
      alert(err.message || 'Failed to cancel job');
    } finally {
      setIsActing(false);
    }
  };

  const handleRetry = async () => {
    if (!job) return;
    setIsActing(true);
    try {
      await api.retryJob(job.id);
      await fetchJob(job.id);
      onActionComplete?.();
    } catch (err: any) {
      alert(err.message || 'Failed to retry job');
    } finally {
      setIsActing(false);
    }
  };

  const canCancel = job && ['SUBMITTED', 'QUEUED', 'RUNNING'].includes(job.status);
  const canRetry = job && ['DEAD_LETTER', 'CANCELLED', 'RETRY_WAIT'].includes(job.status);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden text-slate-100">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/90">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-slate-800 text-indigo-400 border border-slate-700">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white font-mono">
                  {job?.job_type || 'Job Details'}
                </h2>
                {job && <JobStatusBadge status={job.status} />}
                {job && <PriorityBadge priority={job.priority} />}
              </div>
              <p className="text-xs text-slate-400 font-mono mt-0.5">ID: {jobId}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {canCancel && (
              <button
                onClick={handleCancel}
                disabled={isActing}
                className="px-3 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 hover:bg-rose-500/20 text-xs font-semibold flex items-center gap-1.5 transition-colors"
              >
                <Ban className="w-3.5 h-3.5" />
                Cancel
              </button>
            )}
            {canRetry && (
              <button
                onClick={handleRetry}
                disabled={isActing}
                className="px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 hover:bg-indigo-500/20 text-xs font-semibold flex items-center gap-1.5 transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Retry
              </button>
            )}
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors ml-2"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {isLoading && !job ? (
            <div className="flex items-center justify-center py-20 text-slate-400">
              <RefreshCw className="w-6 h-6 animate-spin mr-2 text-indigo-500" />
              Loading job details...
            </div>
          ) : job ? (
            <>
              {/* Metadata Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800/80">
                  <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
                    Worker Node
                  </span>
                  <p className="text-xs font-mono font-medium text-white mt-1 truncate">
                    {job.worker_id || 'Unassigned'}
                  </p>
                </div>
                <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800/80">
                  <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
                    Retries
                  </span>
                  <p className="text-xs font-medium text-white mt-1">
                    {job.retry_count} / {job.max_retries} attempts
                  </p>
                </div>
                <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800/80">
                  <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
                    Execution Timeout
                  </span>
                  <p className="text-xs font-medium text-white mt-1">
                    {job.run_timeout_seconds}s
                  </p>
                </div>
                <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800/80">
                  <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
                    Submitted At
                  </span>
                  <p className="text-xs font-medium text-white mt-1 truncate">
                    {new Date(job.created_at).toLocaleTimeString()}
                  </p>
                </div>
              </div>

              {job.error_message && (
                <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
                  <div className="font-semibold flex items-center gap-1.5 mb-1 text-rose-400">
                    <AlertTriangle className="w-4 h-4" /> Last Execution Error
                  </div>
                  <pre className="font-mono whitespace-pre-wrap">{job.error_message}</pre>
                </div>
              )}

              {/* Payload & Result Section */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-950/50">
                  <div className="px-4 py-2 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                      <FileCode className="w-3.5 h-3.5 text-indigo-400" />
                      Input Payload
                    </span>
                  </div>
                  <pre className="p-4 text-xs font-mono text-emerald-400 overflow-x-auto max-h-48">
                    {JSON.stringify(job.payload, null, 2)}
                  </pre>
                </div>

                <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-950/50">
                  <div className="px-4 py-2 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      Output Result
                    </span>
                  </div>
                  <pre className="p-4 text-xs font-mono text-cyan-400 overflow-x-auto max-h-48">
                    {job.result ? JSON.stringify(job.result, null, 2) : '// No result generated yet'}
                  </pre>
                </div>
              </div>

              {/* Execution Attempts Timeline */}
              {job.executions && job.executions.length > 0 && (
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2.5">
                    Execution Attempts History ({job.executions.length})
                  </h3>
                  <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-950/40">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800">
                        <tr>
                          <th className="py-2.5 px-3">Attempt</th>
                          <th className="py-2.5 px-3">Worker Node</th>
                          <th className="py-2.5 px-3">Outcome</th>
                          <th className="py-2.5 px-3">Duration</th>
                          <th className="py-2.5 px-3">Finished At</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono">
                        {job.executions.map((exec) => (
                          <tr key={exec.id} className="hover:bg-slate-800/30">
                            <td className="py-2 px-3 font-semibold text-white">
                              #{exec.attempt_number}
                            </td>
                            <td className="py-2 px-3 text-slate-300">{exec.worker_id}</td>
                            <td className="py-2 px-3">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                  exec.status === 'SUCCESS'
                                    ? 'bg-emerald-500/10 text-emerald-400'
                                    : 'bg-rose-500/10 text-rose-400'
                                }`}
                              >
                                {exec.status}
                              </span>
                            </td>
                            <td className="py-2 px-3 text-slate-400">
                              {exec.duration_ms ? `${exec.duration_ms.toFixed(1)} ms` : '-'}
                            </td>
                            <td className="py-2 px-3 text-slate-400">
                              {exec.finished_at
                                ? new Date(exec.finished_at).toLocaleTimeString()
                                : '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Live Terminal Logs */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <Terminal className="w-4 h-4 text-indigo-400" /> Worker Execution Console Logs
                  </h3>
                </div>
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 font-mono text-xs text-slate-300 overflow-x-auto max-h-56 leading-relaxed">
                  {job.logs ? (
                    <pre className="whitespace-pre-wrap">{job.logs}</pre>
                  ) : (
                    <span className="text-slate-600 italic">No logs recorded yet.</span>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="text-center py-12 text-slate-400">Job not found</div>
          )}
        </div>
      </div>
    </div>
  );
};
