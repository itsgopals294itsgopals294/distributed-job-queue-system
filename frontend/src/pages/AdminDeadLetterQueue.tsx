import React, { useEffect, useState } from 'react';
import {
  AlertOctagon,
  RefreshCw,
  RotateCcw,
  Trash2,
  Eye,
  AlertTriangle,
} from 'lucide-react';
import { api } from '../services/api';

interface Props {
  onInspectJob: (jobId: string) => void;
}

export const AdminDeadLetterQueue: React.FC<Props> = ({ onInspectJob }) => {
  const [dlqItems, setDlqItems] = useState<Array<{ job_id: string; moved_at: number; metadata: any }>>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actingId, setActingId] = useState<string | null>(null);

  const fetchDLQ = async () => {
    setIsLoading(true);
    try {
      const data = await api.getDLQ();
      setDlqItems(data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDLQ();
    const interval = setInterval(fetchDLQ, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleRetryJob = async (jobId: string) => {
    setActingId(jobId);
    try {
      await api.retryDLQJob(jobId);
      await fetchDLQ();
    } catch (err: any) {
      alert(err.message || 'Failed to requeue job from DLQ');
    } finally {
      setActingId(null);
    }
  };

  const handlePurge = async () => {
    if (!confirm('Are you sure you want to permanently purge all items from the Dead-Letter Queue?')) {
      return;
    }
    try {
      await api.purgeDLQ();
      await fetchDLQ();
    } catch (err: any) {
      alert(err.message || 'Failed to purge DLQ');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-white tracking-tight">Dead-Letter Queue (DLQ)</h1>
            <span className="px-2 py-0.5 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-semibold">
              {dlqItems.length} Failed Tasks
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Jobs that exceeded max bounded retries or encountered unrecoverable task exceptions
          </p>
        </div>

        <div className="flex items-center gap-2">
          {dlqItems.length > 0 && (
            <button
              onClick={handlePurge}
              className="px-3 py-1.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-400 text-xs font-semibold flex items-center gap-1.5 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Purge DLQ
            </button>
          )}
          <button
            onClick={fetchDLQ}
            className="p-2 rounded-xl bg-slate-850 hover:bg-slate-800 border border-slate-700/80 text-slate-300 hover:text-white transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="bg-slate-900/70 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 uppercase tracking-wider font-semibold">
              <tr>
                <th className="py-3 px-4">Job ID</th>
                <th className="py-3 px-4">Task Type</th>
                <th className="py-3 px-4">Failure Reason / Error</th>
                <th className="py-3 px-4">Moved To DLQ At</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {dlqItems.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-14 text-center text-slate-500 font-sans">
                    Dead-Letter Queue is empty. No unrecoverable job failures.
                  </td>
                </tr>
              ) : (
                dlqItems.map((item, idx) => {
                  const errorMsg =
                    item.metadata?.last_error || item.metadata?.reason || 'Max retries exhausted';
                  const jobType = item.metadata?.job_type || 'Unknown';

                  return (
                    <tr key={item.job_id || idx} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3 px-4 font-bold text-white">
                        {item.job_id}
                      </td>
                      <td className="py-3 px-4 text-slate-300 font-sans font-medium">
                        {jobType}
                      </td>
                      <td className="py-3 px-4 text-rose-300 max-w-md truncate font-sans">
                        <span className="flex items-center gap-1.5">
                          <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                          <span>{errorMsg}</span>
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {item.moved_at
                          ? new Date(item.moved_at * 1000).toLocaleTimeString()
                          : 'Recent'}
                      </td>
                      <td className="py-3 px-4 text-right font-sans">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => onInspectJob(item.job_id)}
                            className="px-2.5 py-1 rounded-lg bg-slate-850 hover:bg-slate-800 text-slate-200 border border-slate-700/60 font-medium inline-flex items-center gap-1 transition-colors"
                          >
                            <Eye className="w-3.5 h-3.5 text-indigo-400" />
                            Inspect
                          </button>
                          <button
                            onClick={() => handleRetryJob(item.job_id)}
                            disabled={actingId === item.job_id}
                            className="px-2.5 py-1 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 text-indigo-400 text-xs font-semibold inline-flex items-center gap-1 transition-colors"
                          >
                            <RotateCcw className="w-3.5 h-3.5" />
                            Requeue
                          </button>
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
