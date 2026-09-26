import React, { useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Database,
  CloudSun,
  CloudRain,
  AlertTriangle,
  Award,
  Sparkles,
  Info,
  Menu,
  X,
  Server,
  Activity,
  CheckCircle2,
  AlertOctagon,
  ExternalLink,
  Layers,
  Compass,
  Trophy
} from 'lucide-react';
import { fetchHealth } from '../../api/client';
import { HealthResponse } from '../../types/api';

interface ShellProps {
  children: React.ReactNode;
}

const navItems = [
  { name: 'RAMP MoE Engine', path: '/ramp', icon: Layers },
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Data Feeds & Feats', path: '/data', icon: Database },
  { name: 'Weather Regimes', path: '/regime', icon: CloudSun },
  { name: 'Baselines & Benchmarks', path: '/baseline', icon: CloudRain },
  { name: 'Extreme Rainfall', path: '/extreme', icon: AlertTriangle },
  { name: 'Operational Verification', path: '/operational', icon: CheckCircle2 },
  { name: 'Spatial Forecast', path: '/spatial', icon: Compass },
  { name: 'Verification & Scores', path: '/verification', icon: Award },
  { name: 'Explainability (XAI)', path: '/explainability', icon: Sparkles },
  { name: 'Jury Demo', path: '/jury-demo', icon: Trophy },
  { name: 'System Info & MoES', path: '/about', icon: Info },
];

export const Shell: React.FC<ShellProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const location = useLocation();

  useEffect(() => {
    let isMounted = true;
    const checkHealth = async () => {
      try {
        const data = await fetchHealth();
        if (isMounted) {
          setHealth(data);
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setHealth(null);
          setLoading(false);
        }
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  // Close mobile sidebar on route change
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  const isSynthetic = health?.data_mode === 'SYNTHETIC_DEMO' || !health;

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-72 bg-slate-900/95 border-r border-slate-800/80 flex flex-col transition-transform duration-300 ease-in-out lg:static lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-0 -translate-x-full'
        }`}
      >
        {/* Branding header */}
        <div className="h-20 flex items-center px-6 border-b border-slate-800/80 justify-between bg-slate-950/40">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-monsoon-500 to-indigo-700 flex items-center justify-center shadow-lg shadow-monsoon-600/30">
              <CloudRain className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg tracking-wider text-white">RAMP</span>
                <span className="text-[10px] bg-monsoon-500/20 text-monsoon-300 font-mono px-1.5 py-0.5 rounded border border-monsoon-500/30">
                  SIH26080
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-medium tracking-tight">
                MoES • NCMRWF Post-Processor
              </p>
            </div>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation items */}
        <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
          <div className="px-3 pb-2 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            Operational Modules
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={`flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-monsoon-600/20 text-monsoon-300 border border-monsoon-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-monsoon-400' : 'text-slate-400'}`} />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Sidebar Footer / System Badge */}
        <div className="p-4 border-t border-slate-800/80 bg-slate-950/40">
          <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400 flex items-center space-x-1.5">
                <Server className="w-3.5 h-3.5" />
                <span>Backend Core</span>
              </span>
              <span className="flex items-center space-x-1.5">
                <span
                  className={`w-2 h-2 rounded-full ${
                    health?.status === 'healthy' ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'
                  }`}
                />
                <span className="text-[11px] font-mono text-slate-300">
                  {loading ? 'Checking...' : health?.status === 'healthy' ? 'Active' : 'Standby'}
                </span>
              </span>
            </div>

            <div className="flex items-center justify-between text-[11px] pt-1 border-t border-slate-800/60">
              <span className="text-slate-400">Data Mode</span>
              <span
                className={`px-1.5 py-0.5 rounded font-mono text-[10px] font-semibold ${
                  isSynthetic
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                    : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                }`}
              >
                {health?.data_mode || 'SYNTHETIC_DEMO'}
              </span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Navbar */}
        <header className="h-20 bg-slate-900/70 backdrop-blur-md border-b border-slate-800/80 px-6 flex items-center justify-between z-10">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
            >
              <Menu className="w-6 h-6" />
            </button>
            <div>
              <h1 className="text-lg font-semibold text-white tracking-tight flex items-center space-x-2">
                <span>Regime-Aware Mixture-of-Experts Post-Processor (RAMP)</span>
              </h1>
              <p className="text-xs text-slate-400 hidden sm:block">
                National Centre for Medium Range Weather Forecasting (NCMRWF) • MoES
              </p>
            </div>
          </div>

          {/* Right Header Badges */}
          <div className="flex items-center space-x-3">
            {/* Scientific Integrity Mode Badge */}
            <div
              className={`hidden md:flex items-center space-x-2 px-3 py-1.5 rounded-lg border text-xs font-medium ${
                isSynthetic
                  ? 'bg-amber-950/40 border-amber-600/40 text-amber-300'
                  : 'bg-emerald-950/40 border-emerald-600/40 text-emerald-300'
              }`}
            >
              {isSynthetic ? (
                <AlertOctagon className="w-4 h-4 text-amber-400" />
              ) : (
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              )}
              <span>Mode: {health?.data_mode || 'SYNTHETIC_DEMO'}</span>
            </div>

            {/* API Docs Link */}
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/80 text-xs text-slate-300 transition-colors"
            >
              <Activity className="w-3.5 h-3.5 text-monsoon-400" />
              <span className="hidden sm:inline">FastAPI Docs</span>
              <ExternalLink className="w-3 h-3 text-slate-400" />
            </a>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8 space-y-6">
          {children}
        </main>

        {/* Global Footer */}
        <footer className="h-12 border-t border-slate-800/80 bg-slate-950/80 px-6 flex items-center justify-between text-xs text-slate-400">
          <span>Smart India Hackathon 2026 — MoES / NCMRWF (Problem SIH26080)</span>
          <span className="font-mono text-[11px] text-slate-400">
            RAMP v{health?.version || '0.1.0'} [Phase 1 Foundation]
          </span>
        </footer>
      </div>
    </div>
  );
};
