import React, { useState } from 'react';
import { X, Sparkles, AlertCircle, RefreshCw } from 'lucide-react';
import { api } from '../services/api';
import { JobPriority } from '../types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSubmitted: () => void;
}

const TEMPLATES: Record<string, { payload: any; description: string }> = {
  email_dispatch: {
    description: 'Sends templated transactional or marketing emails via SMTP simulator',
    payload: {
      to: 'customer@example.com',
      subject: 'Your Weekly Digest',
      simulate_fail: false,
    },
  },
  data_export: {
    description: 'Compresses and exports warehouse tables to CSV, JSON, or Parquet',
    payload: {
      format: 'csv',
      record_count: 5000,
      simulate_fail: false,
    },
  },
  image_resize: {
    description: 'Transcodes image assets into web-optimized responsive thumbnails',
    payload: {
      image_url: 'https://images.unsplash.com/photo-1579783902614-a3fb3927b675',
      dimensions: ['thumb_150x150', 'card_400x300', 'retina_1200x800'],
      simulate_fail: false,
    },
  },
  ml_inference: {
    description: 'Performs batch sentiment scoring with simulated GPU acceleration',
    payload: {
      model: 'transformer-sentiment-xl',
      inputs: [
        'Exceptional throughput and seamless background processing!',
        'A slight hiccup during retry backoff, but recovered automatically.',
      ],
      simulate_fail: false,
    },
  },
  webhook_delivery: {
    description: 'Reliable webhook event dispatcher with cryptographic signatures',
    payload: {
      url: 'https://api.partner.com/v1/webhooks',
      event: 'order.completed',
      simulate_fail: false,
    },
  },
  custom_calc: {
    description: 'Heavy mathematical and Fibonacci sequence evaluation',
    payload: {
      n: 35,
      simulate_fail: false,
    },
  },
};

export const SubmitJobModal: React.FC<Props> = ({ isOpen, onClose, onSubmitted }) => {
  const [jobType, setJobType] = useState('email_dispatch');
  const [priority, setPriority] = useState<JobPriority>('medium');
  const [payloadText, setPayloadText] = useState(
    JSON.stringify(TEMPLATES.email_dispatch.payload, null, 2)
  );
  const [idempotencyKey, setIdempotencyKey] = useState('');
  const [maxRetries, setMaxRetries] = useState(3);
  const [timeoutSec, setTimeoutSec] = useState(120);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleTemplateChange = (type: string) => {
    setJobType(type);
    if (TEMPLATES[type]) {
      setPayloadText(JSON.stringify(TEMPLATES[type].payload, null, 2));
    }
  };

  const generateIdempotencyKey = () => {
    setIdempotencyKey(`idemp_${Math.random().toString(36).substring(2, 11)}_${Date.now()}`);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    let parsedPayload: Record<string, any>;
    try {
      parsedPayload = JSON.parse(payloadText);
    } catch (err) {
      setError('Invalid JSON syntax in payload. Please fix syntax errors.');
      return;
    }

    setIsSubmitting(true);
    try {
      await api.submitJob({
        job_type: jobType,
        priority,
        payload: parsedPayload,
        idempotency_key: idempotencyKey.trim() || undefined,
        max_retries: maxRetries,
        run_timeout_seconds: timeoutSec,
      });
      onSubmitted();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to submit job');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl p-6 text-slate-100">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Submit New Background Job</h2>
              <p className="text-xs text-slate-400">
                Dispatches a task to Redis priority queues for distributed execution
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
              Job Type Template
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {Object.keys(TEMPLATES).map((type) => (
                <button
                  type="button"
                  key={type}
                  onClick={() => handleTemplateChange(type)}
                  className={`p-2.5 rounded-lg border text-left transition-all ${
                    jobType === type
                      ? 'bg-indigo-600/20 border-indigo-500 text-white font-medium shadow-sm'
                      : 'bg-slate-850 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                  }`}
                >
                  <div className="text-xs capitalize">{type.replace('_', ' ')}</div>
                </button>
              ))}
            </div>
            <p className="text-xs text-slate-500 mt-1.5">
              {TEMPLATES[jobType]?.description}
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                Queue Priority
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as JobPriority)}
                className="w-full bg-slate-850 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors"
              >
                <option value="high">High (queue:high) - Realtime & critical</option>
                <option value="medium">Medium (queue:medium) - Standard async</option>
                <option value="low">Low (queue:low) - Bulk & background</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                Max Retries
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  min={0}
                  max={10}
                  value={maxRetries}
                  onChange={(e) => setMaxRetries(Number(e.target.value))}
                  className="w-full bg-slate-850 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
                <span className="text-xs text-slate-400 whitespace-nowrap">
                  (DLQ if exceeded)
                </span>
              </div>
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                Idempotency Key (Optional)
              </label>
              <button
                type="button"
                onClick={generateIdempotencyKey}
                className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
              >
                <RefreshCw className="w-3 h-3" /> Auto-generate
              </button>
            </div>
            <input
              type="text"
              placeholder="e.g. order-invoice-10492-retry-token"
              value={idempotencyKey}
              onChange={(e) => setIdempotencyKey(e.target.value)}
              className="w-full bg-slate-850 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 font-mono"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                Task Payload (JSON)
              </label>
              <span className="text-xs text-slate-500">
                Tip: Set "simulate_fail": true to test DLQ & retries
              </span>
            </div>
            <textarea
              rows={6}
              value={payloadText}
              onChange={(e) => setPayloadText(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-emerald-400 font-mono focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 text-sm font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-semibold shadow-lg shadow-indigo-600/30 transition-all flex items-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Submitting...
                </>
              ) : (
                'Submit Job'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
