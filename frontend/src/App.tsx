import React, { useState } from 'react';
import { useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { SubmitJobModal } from './components/SubmitJobModal';
import { JobDetailModal } from './components/JobDetailModal';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { JobsList } from './pages/JobsList';
import { AdminDashboard } from './pages/AdminDashboard';
import { AdminWorkers } from './pages/AdminWorkers';
import { AdminDeadLetterQueue } from './pages/AdminDeadLetterQueue';
import { AdminUsers } from './pages/AdminUsers';
import { AdminAuditLogs } from './pages/AdminAuditLogs';
import { RefreshCw } from 'lucide-react';

export const App: React.FC = () => {
  const { user, isLoading } = useAuth();
  const [authView, setAuthView] = useState<'login' | 'register'>('login');
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [isSubmitOpen, setIsSubmitOpen] = useState(false);
  const [inspectedJobId, setInspectedJobId] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        <RefreshCw className="w-8 h-8 animate-spin text-indigo-500 mb-2" />
      </div>
    );
  }

  if (!user) {
    if (authView === 'register') {
      return <Register onSwitchToLogin={() => setAuthView('login')} />;
    }
    return <Login onSwitchToRegister={() => setAuthView('register')} />;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex">
      {/* Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenSubmit={() => setIsSubmitOpen(true)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Navbar />

        <main className="flex-1 p-6 lg:p-8 max-w-7xl w-full mx-auto overflow-y-auto">
          {activeTab === 'dashboard' && (
            <Dashboard
              onOpenSubmit={() => setIsSubmitOpen(true)}
              onInspectJob={(id) => setInspectedJobId(id)}
              onViewAllJobs={() => setActiveTab('my-jobs')}
            />
          )}

          {activeTab === 'my-jobs' && (
            <JobsList
              isAdminMode={false}
              onInspectJob={(id) => setInspectedJobId(id)}
              onOpenSubmit={() => setIsSubmitOpen(true)}
            />
          )}

          {activeTab === 'admin-dashboard' && (
            <AdminDashboard
              onNavigateToDLQ={() => setActiveTab('admin-dlq')}
              onNavigateToWorkers={() => setActiveTab('admin-workers')}
              onNavigateToAllJobs={() => setActiveTab('admin-all-jobs')}
            />
          )}

          {activeTab === 'admin-all-jobs' && (
            <JobsList
              isAdminMode={true}
              onInspectJob={(id) => setInspectedJobId(id)}
            />
          )}

          {activeTab === 'admin-workers' && <AdminWorkers />}

          {activeTab === 'admin-dlq' && (
            <AdminDeadLetterQueue onInspectJob={(id) => setInspectedJobId(id)} />
          )}

          {activeTab === 'admin-users' && <AdminUsers />}

          {activeTab === 'admin-audit' && <AdminAuditLogs />}
        </main>
      </div>

      {/* Modals */}
      <SubmitJobModal
        isOpen={isSubmitOpen}
        onClose={() => setIsSubmitOpen(false)}
        onSubmitted={() => {
          // Trigger reload if needed
        }}
      />

      <JobDetailModal
        jobId={inspectedJobId}
        isOpen={Boolean(inspectedJobId)}
        onClose={() => setInspectedJobId(null)}
      />
    </div>
  );
};
