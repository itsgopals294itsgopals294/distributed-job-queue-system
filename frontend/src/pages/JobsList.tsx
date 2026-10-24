import React, { useEffect, useState } from 'react';
import {
  Search,
  Filter,
  RefreshCw,
  Eye,
  Ban,
  RotateCcw,
  Sparkles,
} from 'lucide-react';
import { Job, JobPriority, JobStatus } from '../types';
import { api } from '../services/api';
import { JobStatusBadge } from '../components/JobStatusBadge';
import { PriorityBadge } from '../components/PriorityBadge';

interface Props {
  isAdminMode?: boolean;
  onInspectJob: (jobId: string) => void;
  onOpenSubmit?: () => void;
}

export const JobsList: React.FC<Props> = ({
  isAdminMode = false,
  onInspectJob,
  onOpenSubmit,
}) => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState<JobStatus | ''>('');
  const [priorityFilter, setPriorityFilter] = useState<JobPriority | ''>('');

  const fetchJobs = async () => {
    setIsLoading(true);
    try {
      const data = isAdminMode
        ? await api.getAllJobs({
            job_type: typeFilter || undefined,
            status: statusFilter || undefined,
            priority: priorityFilter || undefined,
          })
        : await api.getMyJobs({
            job_type: typeFilter || undefined,
            status: statusFilter || undefined,
            priority: priorityFilter || undefined,
          });
      setJobs(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 4000);
    return () => clearInterval(interval);
  }, [isAdminMode, typeFilter, statusFilter, priorityFilter]);

  const filteredJobs = jobs.filter((j) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      j.id.toLowerCase().includes(term) ||
      j.job_type.toLowerCase().includes(term) ||
      (j.worker_id && j.worker_id.toLowerCase().includes(term))
    );
  });

  const handleCancel = async (jobId: string) => {
    try {
      await api.cancelJob(jobId);
      fetchJobs();
    } catch (err: any) {
      alert(err.message || 'Failed to cancel');
    }
  };

  const handleRetry = async (jobId: string) => {
    try {
      await api.retryJob(jobId);
      fetchJobs();
    } catch (err: any) {
      alert(err.message || 'Failed to retry');
    }
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">
            {isAdminMode ? 'All Global Jobs' : 'My Background Jobs'}
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            {isAdminMode
              ? 'Complete multi-tenant job stream with administrative controls'
              : 'Tasks submitted under your personal user account'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchJobs}
            className="p-2 rounded-xl bg-slate-850 hover:bg-slate-800 border border-slate-700/80 text-slate-300 hover:text-white transition-colors"
            title="Refresh List"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          {!isAdminMode && onOpenSubmit && (
            <button
              onClick={onOpenSubmit}
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs shadow-lg shadow-indigo-600/30 flex items-center gap-1.5 transition-all"
            >
              <Sparkles className="w-4 h-4" />
              <span>Submit Task</span>
            </button>
          )}
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-wrap items-center gap-3">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px]">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search by Job ID, Type, or Worker..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {/* Status Filter */}
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as any)}
          className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
        >
          <option value="">All Statuses</option>
          <option value="QUEUED">QUEUED</option>
          <option value="RUNNING">RUNNING</option>
          <option value="COMPLETED">COMPLETED</option>
          <option value="RETRY_WAIT">RETRY_WAIT</option>
          <option value="DEAD_LETTER">DEAD_LETTER</option>
          <option value="CANCELLED">CANCELLED</option>
        </select>

        {/* Priority Filter */}
        <select
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value as any)}
          className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
        >
          <option value="">All Priorities</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      {/* Jobs Table */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 uppercase tracking-wider font-semibold">
              <tr>
                <th className="py-3 px-4">Job ID</th>
                <th className="py-3 px-4">Job Type</th>
                <th className="py-3 px-4">Priority</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Worker</th>
                <th className="py-3 px-4">Retries</th>
                <th className="py-3 px-4">Submitted</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredJobs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-14 text-center text-slate-500">
                    {isLoading ? 'Loading jobs...' : 'No jobs matched your filter criteria.'}
                  </td>
                </tr>
              ) : (
                filteredJobs.map((job) => {
                  const canCancel = ['SUBMITTED', 'QUEUED', 'RUNNING'].includes(job.status);
                  const canRetry = ['DEAD_LETTER', 'CANCELLED', 'RETRY_WAIT'].includes(job.status);

                  return (
                    <tr key={job.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-slate-300">
                        {job.id.substring(0, 8)}...
                      </td>
                      <td className="py-3 px-4 font-mono font-semibold text-white">
                        {job.job_type}
                      </td>
                      <td className="py-3 px-4">
                        <PriorityBadge priority={job.priority} />
                      </td>
                      <td className="py-3 px-4">
                        <JobStatusBadge status={job.status} />
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-400">
                        {job.worker_id || '-'}
                      </td>
                      <td className="py-3 px-4 text-slate-300">
                        {job.retry_count} / {job.max_retries}
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {new Date(job.created_at).toLocaleTimeString()}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => onInspectJob(job.id)}
                            className="px-2.5 py-1 rounded-lg bg-slate-850 hover:bg-slate-800 text-slate-200 border border-slate-700/60 font-medium inline-flex items-center gap-1 transition-colors"
                            title="Inspect Details & Logs"
                          >
                            <Eye className="w-3.5 h-3.5 text-indigo-400" />
                            <span>Inspect</span>
                          </button>

                          {canCancel && (
                            <button
                              onClick={() => handleCancel(job.id)}
                              className="p-1 rounded-lg hover:bg-rose-500/10 text-slate-400 hover:text-rose-400 transition-colors"
                              title="Cancel Job"
                            >
                              <Ban className="w-3.5 h-3.5" />
                            </button>
                          )}

                          {canRetry && (
                            <button
                              onClick={() => handleRetry(job.id)}
                              className="p-1 rounded-lg hover:bg-indigo-500/10 text-slate-400 hover:text-indigo-400 transition-colors"
                              title="Retry Job"
                            >
                              <RotateCcw className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
