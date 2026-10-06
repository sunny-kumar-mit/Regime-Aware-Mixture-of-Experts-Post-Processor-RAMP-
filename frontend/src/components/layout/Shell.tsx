import React, { useState, useEffect, useRef } from 'react';
import { NavLink, useLocation, Link } from 'react-router-dom';
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
  CheckCircle2,
  ExternalLink,
  Layers,
  Compass,
  Trophy,
  ChevronDown,
  RefreshCw,
  ShieldCheck,
  Clock,
  ArrowLeft,
} from 'lucide-react';
import { useOperationalStatus } from '../../hooks/useOperationalStatus';

interface ShellProps {
  children: React.ReactNode;
}

// ---------------------------------------------------------------------------
// Sidebar Navigation Grouping (Section B10)
// ---------------------------------------------------------------------------
interface NavGroup {
  group: string;
  items: {
    name: string;
    path: string;
    icon: React.ComponentType<{ className?: string }>;
  }[];
}

const navGroups: NavGroup[] = [
  {
    group: 'Operations',
    items: [
      { name: 'Real Data Lab', path: '/real-data', icon: Sparkles },
      { name: 'Production Status', path: '/production', icon: Server },
      { name: 'Acceptance Scorecard', path: '/acceptance', icon: ShieldCheck },
      { name: 'Real Data Cases', path: '/forecast/cases', icon: Compass },
      { name: 'Operational Forecast', path: '/forecast', icon: Compass },
      { name: 'Operations Control', path: '/operations', icon: RefreshCw },
      { name: 'Operational Cycles', path: '/operations/cycles', icon: Clock },
      { name: 'Data Health & Feed', path: '/operations/data-health', icon: Database },
      { name: 'Real Activation', path: '/activation', icon: ShieldCheck },
      { name: 'Data Ingestion', path: '/data/ingestion', icon: Database },
      { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
      { name: 'Spatial Forecast', path: '/spatial', icon: Layers },
    ],
  },
  {
    group: 'RAMP AI',
    items: [
      { name: 'Weather Regimes', path: '/regime', icon: CloudSun },
      { name: 'RAMP MoE Engine', path: '/ramp', icon: Layers },
      { name: 'Extreme Rainfall', path: '/extreme', icon: AlertTriangle },
      { name: 'Explainability (XAI)', path: '/explainability', icon: Sparkles },
    ],
  },
  {
    group: 'Verification',
    items: [
      { name: 'Forecast Quality', path: '/forecast/verification', icon: Award },
      { name: 'Verification History', path: '/forecast/verification/history', icon: CheckCircle2 },
      { name: 'Baselines & Benchmarks', path: '/baseline', icon: CloudRain },
      { name: 'Operational Verification', path: '/operational', icon: CheckCircle2 },
      { name: 'Verification & Scores', path: '/verification', icon: Award },
    ],
  },
  {
    group: 'Data & System',
    items: [
      { name: 'Data Feeds & Feats', path: '/data', icon: Database },
      { name: 'Model Registry', path: '/models', icon: Server },
      { name: 'Model Training', path: '/training', icon: Sparkles },
      { name: 'System Info & MoES', path: '/about', icon: Info },
    ],
  },
  {
    group: 'Jury',
    items: [
      { name: 'Jury Demo', path: '/jury-demo', icon: Trophy },
    ],
  },
];

// Context Title Resolver for Center Zone
function getRouteContextTitle(pathname: string): string {
  if (pathname === '/acceptance') return 'INSTITUTIONAL ACCEPTANCE SCORECARD';
  if (pathname === '/forecast/cases') return 'OPERATIONAL CASE REPLAY & ERROR ANALYSIS';
  if (pathname === '/production') return 'PRODUCTION DEPLOYMENT & STATE';
  if (pathname === '/operations/cycles') return 'OPERATIONAL CYCLE MANAGER';
  if (pathname === '/operations/data-health') return 'DATA HEALTH & FRESHNESS';
  if (pathname === '/forecast/verification/history') return 'VERIFICATION HISTORY';
  if (pathname === '/activation') return 'REAL-DATA ACTIVATION GATE';
  if (pathname === '/data/ingestion') return 'DATA INGESTION PIPELINE';
  if (pathname === '/forecast/verification') return 'FORECAST QUALITY & VERIFICATION';
  if (pathname === '/' || pathname === '/forecast' || pathname.startsWith('/forecast')) return 'OPERATIONS / FORECAST';
  if (pathname === '/operations') return 'OPERATIONS CONTROL CENTER';
  if (pathname === '/dashboard') return 'OVERVIEW';
  if (pathname.startsWith('/models')) return 'MODEL REGISTRY';
  if (pathname.startsWith('/training')) return 'MODEL TRAINING';
  if (pathname.startsWith('/data')) return 'DATA OPERATIONS';
  if (pathname.startsWith('/regime')) return 'ATMOSPHERIC REGIMES';
  if (pathname.startsWith('/baseline')) return 'BENCHMARKS';
  if (pathname.startsWith('/extreme')) return 'EXTREME PRECIPITATION';
  if (pathname.startsWith('/spatial')) return 'SPATIAL FORECAST';
  if (pathname.startsWith('/operational')) return 'OPERATIONAL VERIFICATION';
  if (pathname.startsWith('/verification')) return 'SCIENTIFIC VERIFICATION';
  if (pathname.startsWith('/ramp')) return 'RAMP MOE ENGINE';
  if (pathname.startsWith('/explainability')) return 'EXPLAINABILITY (XAI)';
  if (pathname.startsWith('/jury-demo')) return 'JURY DEMONSTRATION';
  if (pathname.startsWith('/about')) return 'SYSTEM & MOES INFO';
  return 'METEOROLOGICAL PLATFORM';
}



export const Shell: React.FC<ShellProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [popoverOpen, setPopoverOpen] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);
  const location = useLocation();

  const { availability, health, dataMode, loading, lastScanTime, refresh } = useOperationalStatus(35000);

  // Close popover when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        setPopoverOpen(false);
      }
    }
    if (popoverOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [popoverOpen]);

  // Close mobile sidebar on route change
  useEffect(() => {
    setSidebarOpen(false);
    setPopoverOpen(false);
  }, [location.pathname]);

  const isReal = dataMode === 'REAL' || dataMode === 'REAL_OPERATIONAL' || dataMode === 'REAL_ARCHIVE';
  const isProxy = dataMode === 'PUBLIC_PROXY';

  const modeBadgeColor = isReal
    ? 'bg-emerald-950/70 text-emerald-300 border-emerald-500/40'
    : isProxy
    ? 'bg-cyan-950/70 text-cyan-300 border-cyan-500/40'
    : 'bg-amber-950/70 text-amber-300 border-amber-500/40';

  const modeDotColor = isReal
    ? 'bg-emerald-400 shadow-sm shadow-emerald-400'
    : isProxy
    ? 'bg-cyan-400 shadow-sm shadow-cyan-400'
    : 'bg-amber-400 shadow-sm shadow-amber-400';

  const routeContext = getRouteContextTitle(location.pathname);

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-slate-900/95 border-r border-slate-800/80 flex flex-col transition-transform duration-300 ease-in-out lg:static lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Sidebar Brand header */}
        <div className="h-16 flex items-center px-5 border-b border-slate-800/80 justify-between bg-slate-950/60">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-monsoon-500 to-indigo-700 flex items-center justify-center shadow-md shadow-monsoon-600/30">
              <CloudRain className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-1.5">
                <span className="font-bold text-base tracking-wider text-white">RAMP</span>
                <span className="text-[10px] bg-monsoon-500/20 text-monsoon-300 font-mono px-1.5 py-0.2 rounded border border-monsoon-500/30">
                  SIH26080
                </span>
              </div>
              <p className="text-[10px] text-slate-400 font-medium tracking-tight">
                MoES • NCMRWF Post-Processor
              </p>
            </div>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            aria-label="Close sidebar navigation"
            className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation items grouped by category (Section B10) */}
        <nav className="flex-1 px-3 py-4 space-y-5 overflow-y-auto">
          {navGroups.map((group) => (
            <div key={group.group} className="space-y-1">
              <div className="px-3 pb-1 text-[10px] font-semibold text-slate-500 uppercase tracking-wider font-mono">
                {group.group}
              </div>
              {group.items.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={`flex items-center space-x-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-all duration-150 ${
                      isActive
                        ? 'bg-monsoon-600/25 text-monsoon-300 border border-monsoon-500/30 shadow-sm font-semibold'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                    }`}
                  >
                    <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-monsoon-400' : 'text-slate-400'}`} />
                    <span className="truncate">{item.name}</span>
                  </NavLink>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Sidebar Footer / Compact Core Status */}
        <div className="p-3 border-t border-slate-800/80 bg-slate-950/60">
          <div className="p-2.5 rounded-lg bg-slate-900/90 border border-slate-800 space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400 flex items-center space-x-1.5 text-[11px]">
                <Server className="w-3.5 h-3.5" />
                <span>Backend Core</span>
              </span>
              <span className="flex items-center space-x-1.5">
                <span
                  className={`w-2 h-2 rounded-full ${
                    health?.status === 'healthy' ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
                  }`}
                />
                <span className="text-[10px] font-mono text-slate-300">
                  {loading ? '...' : health?.status === 'healthy' ? 'Active' : 'Standby'}
                </span>
              </span>
            </div>
            <div className="flex items-center justify-between text-[10px] pt-1 border-t border-slate-800/60 text-slate-400">
              <span>Scan:</span>
              <span className="font-mono text-slate-300">{lastScanTime}</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* =========================================================================
            Fixed Top Header (64px) — Redesigned into THREE primary zones (B2-B9)
            LEFT: Brand (RAMP SIH26080 | MoES • NCMRWF)
            CENTER: Operational Context (e.g. SPATIAL FORECAST)
            RIGHT: DATA [● NCUM] [● NEPS] [● IMD] [● RAMP] + Mode Badge + API Docs ↗
           ========================================================================= */}
        <header className="h-16 bg-slate-900/90 backdrop-blur-md border-b border-slate-800/80 px-4 sm:px-6 flex items-center justify-between z-20 shrink-0">
          {/* ZONE 1: LEFT BRAND AREA (Section B3) */}
          <div className="flex items-center space-x-3 shrink-0">
            <button
              onClick={() => setSidebarOpen(true)}
              aria-label="Open navigation sidebar"
              className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
            >
              <Menu className="w-5 h-5" />
            </button>

            {/* Back to Landing Page Button */}
            <Link
              to="/"
              className="group flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-slate-950/80 hover:bg-cyan-950/60 border border-slate-800 hover:border-cyan-500/50 text-slate-300 hover:text-cyan-300 text-xs font-mono transition-all duration-200 shadow-sm"
              title="Return to Landing Page"
            >
              <ArrowLeft className="w-3.5 h-3.5 text-cyan-400 transition-transform group-hover:-translate-x-1" />
              <span className="font-semibold hidden sm:inline">Back to Landing Page</span>
              <span className="font-semibold sm:hidden">Landing Page</span>
            </Link>
          </div>

          {/* ZONE 2: CENTER OPERATIONAL CONTEXT (Section B4) */}
          <div className="hidden md:flex items-center justify-center flex-1 px-4">
            <div className="flex items-center space-x-2 px-3.5 py-1 rounded-full bg-slate-950/70 border border-slate-800/90 shadow-inner">
              <span className="w-1.5 h-1.5 rounded-full bg-monsoon-400 animate-pulse" />
              <span className="font-mono text-[11px] font-bold tracking-widest text-slate-200 uppercase">
                {routeContext}
              </span>
            </div>
          </div>

          {/* ZONE 3: RIGHT SYSTEM STATUS & ACTIONS (Section B5-B8) */}
          <div className="flex items-center space-x-2.5 shrink-0 relative" ref={popoverRef}>
            {/* Compact DATA Status Button (Section B5) */}
            <div className="relative">
              <button
                onClick={() => setPopoverOpen(!popoverOpen)}
                aria-label="Toggle Data Status popover"
                aria-expanded={popoverOpen}
                className="flex items-center space-x-2 px-2.5 py-1.5 rounded-lg bg-slate-950/80 border border-slate-800 hover:border-slate-700 transition text-xs group"
                title="Click to view detailed meteorological data source availability"
              >
                <span className="font-mono text-[11px] font-bold text-slate-300 group-hover:text-white">
                  DATA
                </span>
                <span className="flex items-center space-x-1">
                  {/* NCUM */}
                  <span
                    title="NCUM Deterministic"
                    className={`w-2 h-2 rounded-full ${
                      availability?.ncmrwf_ncum ? 'bg-emerald-400 shadow-sm shadow-emerald-400' : 'bg-rose-500/80'
                    }`}
                  />
                  {/* NEPS */}
                  <span
                    title="NEPS Ensemble"
                    className={`w-2 h-2 rounded-full ${
                      availability?.ncmrwf_neps ? 'bg-emerald-400 shadow-sm shadow-emerald-400' : 'bg-rose-500/80'
                    }`}
                  />
                  {/* IMD OBS */}
                  <span
                    title="IMD 0.25° Obs"
                    className={`w-2 h-2 rounded-full ${
                      availability?.imd_obs ? 'bg-emerald-400 shadow-sm shadow-emerald-400' : 'bg-rose-500/80'
                    }`}
                  />
                  {/* RAMP MODEL */}
                  <span
                    title="RAMP Model Readiness"
                    className={`w-2 h-2 rounded-full ${
                      availability?.ramp_model ? 'bg-emerald-400 shadow-sm shadow-emerald-400' : 'bg-amber-400'
                    }`}
                  />
                </span>
                <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${popoverOpen ? 'rotate-180' : ''}`} />
              </button>

              {/* Status Popover (Requirement 7) */}
              {popoverOpen && (
                <div className="absolute right-0 mt-2 w-80 rounded-xl bg-slate-900 border border-slate-800 shadow-2xl p-4 text-xs space-y-3 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <div>
                      <span className="font-semibold text-white tracking-wide text-xs block">
                        DATA SOURCE STATUS
                      </span>
                      <span className="text-[10px] text-slate-400">Live operational & experiment readiness</span>
                    </div>
                    <button
                      onClick={() => { refresh(); }}
                      title="Refresh Operational Scan"
                      className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* Status Rows */}
                  <div className="space-y-2.5 font-mono text-[11px]">
                    <div className="p-2 rounded bg-slate-950/80 border border-slate-800/80">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-200">NCUM Deterministic</span>
                        <span className="flex items-center space-x-1.5">
                          <span className={`w-2 h-2 rounded-full ${availability?.ncmrwf_ncum ? 'bg-emerald-400 shadow-sm shadow-emerald-400' : 'bg-rose-500'}`} />
                          <span className={availability?.ncmrwf_ncum ? 'text-emerald-300 font-bold' : 'text-slate-400'}>
                            {availability?.ncmrwf_ncum ? 'ACTIVE' : 'NOT AVAILABLE'}
                          </span>
                        </span>
                      </div>
                      {availability?.ncmrwf_ncum && (
                        <div className="text-[10px] text-slate-400 mt-1 flex items-center justify-between">
                          <span>{availability?.ncum_details?.date || '2026-09-27'} {availability?.ncum_details?.cycle || '00Z'} (+{availability?.ncum_details?.lead_hours || 24}h)</span>
                          <span className="text-indigo-300 font-semibold">{availability?.ncum_details?.features_contract || '18/18 features valid'}</span>
                        </div>
                      )}
                    </div>

                    <div className="p-2 rounded bg-slate-950/80 border border-slate-800/80">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-200">NEPS Ensemble (23 Mem)</span>
                        <span className="flex items-center space-x-1.5">
                          <span className={`w-2 h-2 rounded-full ${availability?.ncmrwf_neps ? 'bg-emerald-400 shadow-sm shadow-emerald-400' : 'bg-amber-400'}`} />
                          <span className={availability?.ncmrwf_neps ? 'text-emerald-300 font-bold' : 'text-amber-400'}>
                            {availability?.ncmrwf_neps ? 'ACTIVE' : 'NOT IMPORTED'}
                          </span>
                        </span>
                      </div>
                    </div>

                    <div className="p-2 rounded bg-slate-950/80 border border-slate-800/80">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-200">IMD Gridded Obs</span>
                        <span className="flex items-center space-x-1.5">
                          <span className={`w-2 h-2 rounded-full ${availability?.imd_obs ? 'bg-emerald-400 shadow-sm shadow-emerald-400' : 'bg-rose-500'}`} />
                          <span className={availability?.imd_obs ? 'text-emerald-300 font-bold' : 'text-slate-400'}>
                            {availability?.imd_obs ? 'ACTIVE' : 'NOT AVAILABLE'}
                          </span>
                        </span>
                      </div>
                      {availability?.imd_obs && (
                        <div className="text-[10px] text-slate-400 mt-1 flex items-center justify-between">
                          <span>Date: {availability?.imd_details?.date || '2026-09-27'}</span>
                          <span className="text-cyan-300 font-semibold">Res: {availability?.imd_details?.resolution || '0.25°'}</span>
                        </div>
                      )}
                    </div>

                    <div className="p-2 rounded bg-slate-950/80 border border-slate-800/80">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-200">RAMP Model Engine</span>
                        <span className="flex items-center space-x-1.5">
                          <span className={`w-2 h-2 rounded-full ${availability?.ramp_model ? 'bg-emerald-400 shadow-sm shadow-emerald-400' : 'bg-amber-400'}`} />
                          <span className={availability?.ramp_model ? 'text-emerald-300 font-bold' : 'text-amber-300'}>
                            {availability?.ramp_model ? 'READY' : 'NOT READY'}
                          </span>
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-400 mt-1 flex items-center justify-between">
                        <span>Version: {availability?.model_details?.version || 'v2.0.0 (FROZEN)'}</span>
                        <span className="text-purple-300 font-semibold">7-Regime MoE</span>
                      </div>
                    </div>
                  </div>

                  {/* Context Metadata */}
                  <div className="pt-2 border-t border-slate-800 space-y-1.5 text-[11px]">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Data Mode</span>
                      <span className="font-mono font-semibold text-emerald-300 bg-emerald-950/40 px-1.5 py-0.5 rounded border border-emerald-500/30 text-[10px]">
                        {dataMode}
                      </span>
                    </div>
                    {availability?.active_experiment_dataset && (
                      <div className="flex items-center justify-between text-slate-400 text-[10px]">
                        <span>Active Exp</span>
                        <span className="font-mono text-slate-300 truncate max-w-[170px]" title={availability.active_experiment_dataset}>
                          {availability.active_experiment_dataset}
                        </span>
                      </div>
                    )}
                    <div className="flex items-center justify-between text-slate-400 text-[10px]">
                      <span>Last Scan</span>
                      <span className="font-mono text-slate-300">{lastScanTime}</span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-slate-800">
                    <NavLink
                      to="/real-data"
                      onClick={() => setPopoverOpen(false)}
                      className="w-full block py-2 text-center text-xs font-bold uppercase tracking-wider rounded bg-indigo-600 hover:bg-indigo-500 text-white transition shadow-sm"
                    >
                      View Data Sources &amp; Vault
                    </NavLink>
                  </div>
                </div>
              )}
            </div>

            {/* Compact Scientific Mode Indicator (Section B7) */}
            <div
              className={`flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-mono font-medium ${modeBadgeColor}`}
              title="Current scientific data integrity mode"
              aria-label={`Current data integrity mode: ${dataMode || 'SYNTHETIC_DEMO'}`}
            >
              <span className={`w-2 h-2 rounded-full ${modeDotColor}`} />
              <span className="text-[11px] hidden sm:inline">
                {(!dataMode || dataMode === 'SYNTHETIC_DEMO') ? 'SYNTHETIC DEMO' : (typeof dataMode === 'string' ? dataMode.replace(/_/g, ' ') : 'DEMO')}
              </span>
            </div>

            {/* Subtle API Docs Link (Section B8) */}
            <a
              href={import.meta.env.VITE_API_BASE_URL ? `${import.meta.env.VITE_API_BASE_URL}/docs` : '/docs'}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Open FastAPI documentation in a new tab"
              className="hidden sm:flex items-center space-x-1 text-slate-400 hover:text-slate-200 px-2.5 py-1.5 rounded-lg hover:bg-slate-800/80 transition text-xs border border-transparent hover:border-slate-800"
              title="Open OpenAPI / FastAPI Documentation"
            >
              <span>API Docs</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </header>

        {/* Dynamic Page Container */}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Shell;
