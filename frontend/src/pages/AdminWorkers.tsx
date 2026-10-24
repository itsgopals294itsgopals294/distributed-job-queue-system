import React, { useEffect, useState } from 'react';
import { Server, RefreshCw, PowerOff, ShieldAlert, Cpu } from 'lucide-react';
import { WorkerNode } from '../types';
import { api } from '../services/api';

export const AdminWorkers: React.FC = () => {
  const [workers, setWorkers] = useState<WorkerNode[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actingWorker, setActingWorker] = useState<string | null>(null);

  const fetchWorkers = async () => {
    setIsLoading(true);
    try {
      const data = await api.getWorkers();
      setWorkers(data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkers();
    const interval = setInterval(fetchWorkers, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleDrain = async (workerId: string) => {
    if (!confirm(`Are you sure you want to drain worker '${workerId}'? It will complete its current task and exit.`)) {
      return;
    }
    setActingWorker(workerId);
    try {
      await api.drainWorker(workerId);
      await fetchWorkers();
    } catch (err: any) {
      alert(err.message || 'Failed to drain worker');
    } finally {
      setActingWorker(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Worker Fleet Infrastructure</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time status of distributed background worker nodes, leases, and throughput
          </p>
        </div>
        <button
          onClick={fetchWorkers}
          className="p-2 rounded-xl bg-slate-850 hover:bg-slate-800 border border-slate-700/80 text-slate-300 hover:text-white transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="bg-slate-900/70 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 uppercase tracking-wider font-semibold">
              <tr>
                <th className="py-3 px-4">Worker ID</th>
                <th className="py-3 px-4">Hostname / Node</th>
                <th className="py-3 px-4">State</th>
                <th className="py-3 px-4">Active Lease Job</th>
                <th className="py-3 px-4">Processed</th>
                <th className="py-3 px-4">Last Heartbeat</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {workers.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-14 text-center text-slate-500 font-sans">
                    No worker nodes currently active or detected.
                  </td>
                </tr>
              ) : (
                workers.map((w) => {
                  const isOnline = w.status === 'ONLINE';
                  const isDraining = w.status === 'DRAINING';

                  return (
                    <tr key={w.worker_id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3 px-4 font-bold text-white">
                        <div className="flex items-center gap-2">
                          <Cpu className="w-4 h-4 text-indigo-400 shrink-0" />
                          <span>{w.worker_id}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-slate-400">{w.hostname}</td>
                      <td className="py-3 px-4 font-sans">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold border ${
                            isOnline
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                              : isDraining
                              ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                              : 'bg-slate-700/20 text-slate-400 border-slate-700'
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              isOnline ? 'bg-emerald-400 animate-pulse' : isDraining ? 'bg-amber-400' : 'bg-slate-500'
                            }`}
                          />
                          {w.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-300">
                        {w.current_job_id ? (
                          <span className="text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                            {w.current_job_id.substring(0, 8)}...
                          </span>
                        ) : (
                          <span className="text-slate-500">Idle</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-slate-300">
                        <span className="text-emerald-400">{w.jobs_completed}</span> /{' '}
                        <span className="text-rose-400">{w.jobs_failed} err</span>
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {new Date(w.last_heartbeat).toLocaleTimeString()}
                      </td>
                      <td className="py-3 px-4 text-right font-sans">
                        {isOnline && (
                          <button
                            onClick={() => handleDrain(w.worker_id)}
                            disabled={actingWorker === w.worker_id}
                            className="px-2.5 py-1 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-400 text-xs font-semibold inline-flex items-center gap-1 transition-colors"
                          >
                            <PowerOff className="w-3.5 h-3.5" />
                            Drain
                          </button>
                        )}
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
