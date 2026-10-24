import React, { useEffect, useState } from 'react';
import {
  Server,
  Layers,
  AlertOctagon,
  Clock,
  Activity,
  Zap,
  TrendingUp,
  RotateCcw,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';
import { api } from '../services/api';
import { JobStats, QueueStats, WorkerNode } from '../types';
import { StatsCard } from '../components/StatsCard';

interface Props {
  onNavigateToDLQ: () => void;
  onNavigateToWorkers: () => void;
  onNavigateToAllJobs: () => void;
}

export const AdminDashboard: React.FC<Props> = ({
  onNavigateToDLQ,
  onNavigateToWorkers,
  onNavigateToAllJobs,
}) => {
  const [jobStats, setJobStats] = useState<JobStats | null>(null);
  const [queueStats, setQueueStats] = useState<QueueStats | null>(null);
  const [workers, setWorkers] = useState<WorkerNode[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadAdminData = async () => {
    try {
      const [sys, w] = await Promise.all([
        api.getAdminStats(),
        api.getWorkers(),
      ]);
      setJobStats(sys.job_stats);
      setQueueStats(sys.queue_stats);
      setWorkers(w);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAdminData();
    const interval = setInterval(loadAdminData, 3000);
    return () => clearInterval(interval);
  }, []);

  const activeWorkersCount = workers.filter((w) => w.status === 'ONLINE').length;

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-white tracking-tight">System Infrastructure Overview</h1>
            <span className="px-2 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold">
              Live Redis Streams
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Cluster-wide monitoring, distributed worker fleet, and priority queue backlogs
          </p>
        </div>
        <div className="flex items-center gap-2">
          <a
            href="http://localhost:3000"
            target="_blank"
            rel="noreferrer"
            className="px-3.5 py-2 rounded-xl bg-slate-850 hover:bg-slate-800 border border-slate-700/80 text-slate-300 hover:text-white text-xs font-semibold inline-flex items-center gap-1.5 transition-colors"
          >
            <span>Grafana Dashboards</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
          <button
            onClick={loadAdminData}
            className="p-2 rounded-xl bg-slate-850 hover:bg-slate-800 border border-slate-700/80 text-slate-300 hover:text-white transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Primary KPI Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Active Workers"
          value={`${activeWorkersCount} / ${workers.length}`}
          subtitle="Online background nodes"
          icon={<Server className="w-4 h-4" />}
          color="indigo"
        />
        <StatsCard
          title="Total In Queue"
          value={queueStats?.total_in_queue ?? 0}
          subtitle="High + Med + Low"
          icon={<Clock className="w-4 h-4" />}
          color="amber"
        />
        <StatsCard
          title="Retry Delayed"
          value={queueStats?.delayed_queue ?? 0}
          subtitle="Waiting for backoff timer"
          icon={<RotateCcw className="w-4 h-4" />}
          color="sky"
        />
        <StatsCard
          title="Dead-Letter Backlog"
          value={queueStats?.dead_letter_queue ?? 0}
          subtitle="Requiring administrator review"
          icon={<AlertOctagon className="w-4 h-4" />}
          color="rose"
        />
      </div>

      {/* Queue Backlogs Card & Worker Fleet Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Redis Priority Queues Breakdown */}
        <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 backdrop-blur-sm space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" />
              Redis Priority Queues
            </h2>
            <span className="text-xs text-slate-500 font-mono">BRPOP Priority</span>
          </div>

          <div className="space-y-3">
            {/* High Priority */}
            <div>
              <div className="flex justify-between text-xs mb-1.5 font-medium">
                <span className="text-red-400">queue:high</span>
                <span className="text-white font-mono">{queueStats?.high_priority_queue ?? 0} jobs</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-red-500 rounded-full transition-all duration-300"
                  style={{ width: `${Math.min(100, (queueStats?.high_priority_queue ?? 0) * 10)}%` }}
                />
              </div>
            </div>

            {/* Medium Priority */}
            <div>
              <div className="flex justify-between text-xs mb-1.5 font-medium">
                <span className="text-amber-400">queue:medium</span>
                <span className="text-white font-mono">{queueStats?.medium_priority_queue ?? 0} jobs</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-amber-500 rounded-full transition-all duration-300"
                  style={{ width: `${Math.min(100, (queueStats?.medium_priority_queue ?? 0) * 10)}%` }}
                />
              </div>
            </div>

            {/* Low Priority */}
            <div>
              <div className="flex justify-between text-xs mb-1.5 font-medium">
                <span className="text-blue-400">queue:low</span>
                <span className="text-white font-mono">{queueStats?.low_priority_queue ?? 0} jobs</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full transition-all duration-300"
                  style={{ width: `${Math.min(100, (queueStats?.low_priority_queue ?? 0) * 10)}%` }}
                />
              </div>
            </div>

            {/* Delayed & DLQ quick row */}
            <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
              <span>Delayed Sorted Set (ZSET):</span>
              <span className="font-mono text-purple-400 font-semibold">{queueStats?.delayed_queue ?? 0}</span>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Dead-Letter Queue (DLQ):</span>
              <button
                onClick={onNavigateToDLQ}
                className="font-mono text-rose-400 font-semibold hover:underline flex items-center gap-1"
              >
                <span>{queueStats?.dead_letter_queue ?? 0} jobs</span>
                &rarr;
              </button>
            </div>
          </div>
        </div>

        {/* Worker Fleet Snapshot */}
        <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 backdrop-blur-sm space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Server className="w-4 h-4 text-indigo-400" />
              Active Worker Pool
            </h2>
            <button
              onClick={onNavigateToWorkers}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
            >
              Manage Fleet &rarr;
            </button>
          </div>

          <div className="space-y-2.5">
            {workers.length === 0 ? (
              <div className="text-center py-8 text-slate-500 text-xs">
                No workers currently registered. Start a background worker process.
              </div>
            ) : (
              workers.slice(0, 4).map((w) => (
                <div
                  key={w.worker_id}
                  className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-center justify-between"
                >
                  <div className="flex items-center gap-2.5">
                    <span
                      className={`w-2.5 h-2.5 rounded-full ${
                        w.status === 'ONLINE'
                          ? 'bg-emerald-400 animate-pulse'
                          : w.status === 'DRAINING'
                          ? 'bg-amber-400'
                          : 'bg-slate-600'
                      }`}
                    />
                    <div>
                      <div className="text-xs font-mono font-semibold text-white">
                        {w.worker_id}
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono">{w.hostname}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs font-mono text-emerald-400 font-medium">
                      {w.jobs_completed} completed
                    </div>
                    <div className="text-[10px] text-slate-400">
                      {w.jobs_failed} errors
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
