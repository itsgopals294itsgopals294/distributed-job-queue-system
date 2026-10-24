import React from 'react';
import { JobStatus } from '../types';

interface Props {
  status: JobStatus;
}

export const JobStatusBadge: React.FC<Props> = ({ status }) => {
  const styles: Record<JobStatus, { bg: string; text: string; border: string; dot: string; pulse?: boolean }> = {
    SUBMITTED: {
      bg: 'bg-sky-500/10',
      text: 'text-sky-400',
      border: 'border-sky-500/20',
      dot: 'bg-sky-400',
    },
    QUEUED: {
      bg: 'bg-amber-500/10',
      text: 'text-amber-400',
      border: 'border-amber-500/20',
      dot: 'bg-amber-400',
    },
    RUNNING: {
      bg: 'bg-indigo-500/10',
      text: 'text-indigo-400',
      border: 'border-indigo-500/30',
      dot: 'bg-indigo-400',
      pulse: true,
    },
    COMPLETED: {
      bg: 'bg-emerald-500/10',
      text: 'text-emerald-400',
      border: 'border-emerald-500/20',
      dot: 'bg-emerald-400',
    },
    RETRY_WAIT: {
      bg: 'bg-purple-500/10',
      text: 'text-purple-400',
      border: 'border-purple-500/20',
      dot: 'bg-purple-400',
      pulse: true,
    },
    DEAD_LETTER: {
      bg: 'bg-rose-500/10',
      text: 'text-rose-400',
      border: 'border-rose-500/20',
      dot: 'bg-rose-400',
    },
    CANCELLED: {
      bg: 'bg-slate-500/10',
      text: 'text-slate-400',
      border: 'border-slate-500/20',
      dot: 'bg-slate-400',
    },
  };

  const current = styles[status] || styles.SUBMITTED;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${current.bg} ${current.text} ${current.border}`}
    >
      <span className="relative flex h-2 w-2">
        {current.pulse && (
          <span
            className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${current.dot}`}
          />
        )}
        <span className={`relative inline-flex rounded-full h-2 w-2 ${current.dot}`} />
      </span>
      {status.replace('_', ' ')}
    </span>
  );
};
