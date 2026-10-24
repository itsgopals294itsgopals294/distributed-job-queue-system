import React, { useEffect, useState } from 'react';
import {
  Clock,
  Play,
  CheckCircle2,
  AlertTriangle,
  Layers,
  PlusCircle,
  Eye,
  RefreshCw,
} from 'lucide-react';
import { Job, JobStats } from '../types';
import { api } from '../services/api';
import { StatsCard } from '../components/StatsCard';
import { JobStatusBadge } from '../components/JobStatusBadge';
import { PriorityBadge } from '../components/PriorityBadge';
import { useAuth } from '../context/AuthContext';

interface Props {
  onOpenSubmit: () => void;
  onInspectJob: (jobId: string) => void;
  onViewAllJobs: () => void;
}

export const Dashboard: React.FC<Props> = ({
  onOpenSubmit,
  onInspectJob,
  onViewAllJobs,
}) => {
  const { user } = useAuth();
  const [stats, setStats] = useState<JobStats | null>(null);
  const [recentJobs, setRecentJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadData = async () => {
    try {
      const [s, jobs] = await Promise.all([
        api.getMyJobStats(),
        api.getMyJobs({}),
      ]);
      setStats(s);
      setRecentJobs(jobs.slice(0, 8));
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      {/* Top Welcome Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-indigo-900/30 via-slate-900 to-slate-900 border border-slate-800">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">
            Welcome back, {user?.full_name || user?.email.split('@')[0]}
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Asynchronous background workers are listening on Redis priority queues.
          </p>
        </div>
        <button
          onClick={onOpenSubmit}
          className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:scale-[0.98] text-white font-semibold text-xs shadow-lg shadow-indigo-600/30 flex items-center gap-2 transition-all shrink-0"
        >
          <PlusCircle className="w-4 h-4" />
          <span>Dispatch New Task</span>
        </button>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3.5">
        <StatsCard
          title="Total Jobs"
          value={stats?.total_jobs ?? 0}
          subtitle="Lifetime submissions"
          icon={<Layers className="w-4 h-4" />}
          color="indigo"
        />
        <StatsCard
          title="Queued"
          value={stats?.queued ?? 0}
          subtitle="Waiting in Redis"
          icon={<Clock className="w-4 h-4" />}
          color="amber"
        />
        <StatsCard
          title="Running"
          value={stats?.running ?? 0}
          subtitle="Active execution"
          icon={<Play className="w-4 h-4" />}
          color="sky"
        />
        <StatsCard
          title="Completed"
          value={stats?.completed ?? 0}
          subtitle="Processed successfully"
          icon={<CheckCircle2 className="w-4 h-4" />}
          color="emerald"
        />
        <StatsCard
          title="Dead-Letter"
          value={stats?.dead_letter ?? 0}
          subtitle="Exceeded max retries"
          icon={<AlertTriangle className="w-4 h-4" />}
          color="rose"
        />
      </div>

      {/* Recent Jobs Table */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur-sm">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-white">Recent Background Jobs</h2>
            <p className="text-xs text-slate-400 mt-0.5">Live status of your submitted tasks</p>
          </div>
          <button
            onClick={onViewAllJobs}
            className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
          >
            View all jobs &rarr;
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/60 text-slate-400 border-b border-slate-800 uppercase tracking-wider font-semibold">
              <tr>
                <th className="py-3 px-4">Job Type</th>
                <th className="py-3 px-4">Priority</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Worker</th>
                <th className="py-3 px-4">Attempts</th>
                <th className="py-3 px-4">Submitted</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {recentJobs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500">
                    {isLoading ? (
                      <span className="flex items-center justify-center gap-2">
                        <RefreshCw className="w-4 h-4 animate-spin text-indigo-500" />
                        Fetching jobs...
                      </span>
                    ) : (
                      'No jobs submitted yet. Click "Dispatch New Task" above to get started!'
                    )}
                  </td>
                </tr>
              ) : (
                recentJobs.map((job) => (
                  <tr key={job.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4 font-mono font-medium text-white">
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
                      <button
                        onClick={() => onInspectJob(job.id)}
                        className="px-2.5 py-1 rounded-lg bg-slate-850 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-700/60 font-medium inline-flex items-center gap-1 transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5 text-indigo-400" />
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
