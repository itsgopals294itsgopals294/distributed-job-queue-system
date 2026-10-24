import React from 'react';
import { JobPriority } from '../types';

interface Props {
  priority: JobPriority;
}

export const PriorityBadge: React.FC<Props> = ({ priority }) => {
  const styles: Record<JobPriority, { bg: string; text: string; border: string }> = {
    high: {
      bg: 'bg-red-500/10',
      text: 'text-red-400',
      border: 'border-red-500/20',
    },
    medium: {
      bg: 'bg-amber-500/10',
      text: 'text-amber-400',
      border: 'border-amber-500/20',
    },
    low: {
      bg: 'bg-blue-500/10',
      text: 'text-blue-400',
      border: 'border-blue-500/20',
    },
  };

  const current = styles[priority] || styles.medium;

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold uppercase tracking-wider border ${current.bg} ${current.text} ${current.border}`}
    >
      {priority}
    </span>
  );
};
