import React from 'react';
import {
  LayoutDashboard,
  ListOrdered,
  PlusCircle,
  Server,
  Layers,
  AlertOctagon,
  ShieldAlert,
  Users,
  Cpu,
  BarChart3,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface Props {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onOpenSubmit: () => void;
}

export const Sidebar: React.FC<Props> = ({ activeTab, setActiveTab, onOpenSubmit }) => {
  const { isAdmin } = useAuth();

  const userNav = [
    { id: 'dashboard', label: 'My Dashboard', icon: <LayoutDashboard className="w-4 h-4" /> },
    { id: 'my-jobs', label: 'My Jobs', icon: <ListOrdered className="w-4 h-4" /> },
  ];

  const adminNav = [
    { id: 'admin-dashboard', label: 'System Overview', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'admin-all-jobs', label: 'All Global Jobs', icon: <Layers className="w-4 h-4" /> },
    { id: 'admin-workers', label: 'Worker Fleet', icon: <Server className="w-4 h-4" /> },
    { id: 'admin-dlq', label: 'Dead-Letter Queue', icon: <AlertOctagon className="w-4 h-4" /> },
    { id: 'admin-users', label: 'User Directory', icon: <Users className="w-4 h-4" /> },
    { id: 'admin-audit', label: 'Audit Trail', icon: <ShieldAlert className="w-4 h-4" /> },
  ];

  return (
    <aside className="w-64 bg-slate-950 border-r border-slate-800 flex flex-col shrink-0 min-h-screen">
      {/* Brand */}
      <div className="h-16 px-6 flex items-center gap-3 border-b border-slate-800">
        <div className="p-2 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-600 text-white shadow-lg shadow-indigo-600/30">
          <Cpu className="w-5 h-5" />
        </div>
        <div>
          <h1 className="font-bold text-white text-sm tracking-tight">Distributed Jobs</h1>
          <p className="text-[10px] text-slate-400 font-mono tracking-wider uppercase">
            Async Queue Platform
          </p>
        </div>
      </div>

      {/* Submit Button */}
      <div className="p-4">
        <button
          onClick={onOpenSubmit}
          className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:scale-[0.98] text-white font-semibold text-xs shadow-lg shadow-indigo-600/25 flex items-center justify-center gap-2 transition-all duration-150"
        >
          <PlusCircle className="w-4 h-4" />
          <span>Submit New Job</span>
        </button>
      </div>

      {/* Nav List */}
      <div className="flex-1 px-3 space-y-6 overflow-y-auto">
        <div>
          <div className="px-3 mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
            Workspace
          </div>
          <div className="space-y-1">
            {userNav.map((item) => (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                  activeTab === item.id
                    ? 'bg-slate-800 text-white font-semibold shadow-inner border border-slate-700/60'
                    : 'text-slate-400 hover:text-white hover:bg-slate-900'
                }`}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            ))}
          </div>
        </div>

        {isAdmin && (
          <div>
            <div className="px-3 mb-2 text-[10px] font-bold uppercase tracking-wider text-rose-400/80 flex items-center justify-between">
              <span>Admin Center</span>
              <span className="px-1.5 py-0.2 rounded bg-rose-500/10 text-[9px] text-rose-400 border border-rose-500/20">
                RBAC
              </span>
            </div>
            <div className="space-y-1">
              {adminNav.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    activeTab === item.id
                      ? 'bg-indigo-950/40 border border-indigo-500/30 text-indigo-300 font-semibold'
                      : 'text-slate-400 hover:text-white hover:bg-slate-900'
                  }`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-slate-900 bg-slate-950/40 text-[11px] text-slate-500 font-mono">
        <div>FastAPI + Redis + Workers</div>
        <div className="text-[10px] text-slate-600 mt-0.5">Prometheus /metrics enabled</div>
      </div>
    </aside>
  );
};
