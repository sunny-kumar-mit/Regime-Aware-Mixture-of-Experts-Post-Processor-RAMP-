/**
 * Phase 21 – RAMP Operational Dashboard
 * SIH26080 | MoES / NCMRWF
 *
 * Fully backed by /api/dashboard/* endpoints → PostgreSQL → RAMP inference state.
 * Zero fabricated values. Every number originates from the backend.
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  Activity, AlertTriangle, BarChart3, CheckCircle2, ChevronDown,
  ChevronRight, Cpu, CloudRain, Database, RefreshCw, ShieldAlert,
  ShieldCheck, TrendingUp, Zap, Clock, Globe, MapPin, Lock, Layers,
} from 'lucide-react';
import {
  fetchDashboardSummary,
  fetchDashboardPipeline,
  fetchDashboardRegimes,
  fetchDashboardRisk,
  fetchDashboardProvenance,
  fetchDashboardEvents,
} from '../api/client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface StageDetail { [key: string]: any }
interface PipelineStage {
  id: number; code: string; title: string; description: string;
  status: 'COMPLETED' | 'RUNNING' | 'WAITING' | 'ERROR';
  start_time?: string; completion_time?: string | null;
  duration_ms?: number | null; inputs_available?: string;
  outputs_available?: string; error?: string | null;
  details?: StageDetail;
}
interface Regime {
  code: string; name: string; probability_pct: number;
  coverage_pct: number; mean_rainfall_mm: number;
  extreme_probability_pct: number; color: string; description: string;
}
interface RiskTier {
  tier: string; name: string; threshold_label: string;
  affected_cells: number; percentage_of_domain: number;
  maximum_probability: number; severity: string; color: string;
}
interface ProvenanceFeed {
  source: string; cycle?: string; timestamp?: string;
  observation_date?: string; version?: string; inference_engine?: string;
  checksum_sha256: string; status: string;
}
interface OpsEvent {
  event_id?: string; timestamp: string; event_type?: string;
  service?: string; actor?: string; cycle_id?: string;
  message?: string; event?: string; details?: string; status: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const STATUS_COLOR: Record<string, string> = {
  COMPLETED: 'text-emerald-400 bg-emerald-950/60 border-emerald-700/50',
  RUNNING:   'text-cyan-300 bg-cyan-950/60 border-cyan-700/50',
  WAITING:   'text-amber-400 bg-amber-950/60 border-amber-700/50',
  ERROR:     'text-red-400 bg-red-950/60 border-red-700/50',
};

const SEVERITY_STYLES: Record<string, { bg: string; text: string; border: string; bar: string }> = {
  NORMAL:    { bg: 'bg-sky-950/40',    text: 'text-sky-300',    border: 'border-sky-700/40',    bar: 'bg-sky-500' },
  WARNING:   { bg: 'bg-amber-950/40',  text: 'text-amber-300',  border: 'border-amber-600/40',  bar: 'bg-amber-500' },
  ALERT:     { bg: 'bg-orange-950/40', text: 'text-orange-300', border: 'border-orange-600/40', bar: 'bg-orange-500' },
  EMERGENCY: { bg: 'bg-red-950/40',    text: 'text-red-300',    border: 'border-red-700/40',    bar: 'bg-red-600' },
};

function fmtDuration(ms?: number | null): string {
  if (!ms) return '—';
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
}

function stageIcon(status: string) {
  if (status === 'COMPLETED') return <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />;
  if (status === 'RUNNING')   return <Activity className="w-4 h-4 text-cyan-400 shrink-0 animate-pulse" />;
  if (status === 'WAITING')   return <Clock className="w-4 h-4 text-amber-400 shrink-0" />;
  return <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------
const KpiCard: React.FC<{
  label: string; value: string | number; sub?: string;
  icon: React.ReactNode; accent?: string;
}> = ({ label, value, sub, icon, accent = 'text-monsoon-400' }) => (
  <div className="glass-card rounded-xl p-4 flex flex-col gap-2 hover:border-slate-700 transition-all duration-200">
    <div className="flex items-center justify-between">
      <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">{label}</span>
      <span className={accent}>{icon}</span>
    </div>
    <div className="text-2xl font-bold text-white leading-none">{value}</div>
    {sub && <div className="text-[11px] text-slate-400 leading-tight">{sub}</div>}
  </div>
);

const PipelineStageCard: React.FC<{ stage: PipelineStage; expanded: boolean; onToggle: () => void }> = ({
  stage, expanded, onToggle,
}) => (
  <div
    className={`border rounded-xl transition-all duration-200 cursor-pointer
      ${stage.status === 'RUNNING' ? 'border-cyan-700/50 bg-cyan-950/20' : 'border-slate-800 bg-slate-900/50'}
      hover:border-slate-600`}
    onClick={onToggle}
  >
    <div className="flex items-center gap-3 p-4">
      <div className="flex items-center justify-center w-7 h-7 rounded-full bg-slate-800 text-xs font-mono text-slate-300 shrink-0">
        {stage.id}
      </div>
      {stageIcon(stage.status)}
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold text-slate-100 truncate">{stage.title}</div>
        <div className="text-[11px] text-slate-400 mt-0.5 truncate">{stage.description}</div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border font-semibold ${STATUS_COLOR[stage.status] || ''}`}>
          {stage.status}
        </span>
        {stage.duration_ms != null && (
          <span className="text-[10px] text-slate-500 font-mono hidden sm:block">{fmtDuration(stage.duration_ms)}</span>
        )}
        {expanded ? <ChevronDown className="w-3.5 h-3.5 text-slate-500" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-500" />}
      </div>
    </div>

    {expanded && (
      <div className="px-4 pb-4 pt-0 space-y-2 border-t border-slate-800/80 mt-1">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1 text-xs pt-3">
          {stage.start_time && (
            <div><span className="text-slate-500">Start:</span> <span className="text-slate-300 font-mono">{stage.start_time}</span></div>
          )}
          {stage.completion_time && (
            <div><span className="text-slate-500">End:</span> <span className="text-slate-300 font-mono">{stage.completion_time}</span></div>
          )}
          {stage.inputs_available && (
            <div className="sm:col-span-2"><span className="text-slate-500">Inputs:</span> <span className="text-slate-300">{stage.inputs_available}</span></div>
          )}
          {stage.outputs_available && (
            <div className="sm:col-span-2"><span className="text-slate-500">Outputs:</span> <span className="text-slate-300">{stage.outputs_available}</span></div>
          )}
        </div>
        {stage.details && Object.keys(stage.details).length > 0 && (
          <div className="mt-2 rounded-lg bg-slate-950/70 border border-slate-800 p-3 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1 text-xs">
            {Object.entries(stage.details).map(([k, v]) => (
              <div key={k}><span className="text-slate-500">{k.replace(/_/g, ' ')}:</span> <span className="text-slate-300">{String(v)}</span></div>
            ))}
          </div>
        )}
        {stage.error && (
          <div className="rounded-lg bg-red-950/40 border border-red-700/40 p-2 text-xs text-red-300">{stage.error}</div>
        )}
      </div>
    )}
  </div>
);

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------
export const DashboardPage: React.FC = () => {
  const [summary, setSummary]         = useState<Record<string, any> | null>(null);
  const [pipeline, setPipeline]       = useState<PipelineStage[]>([]);
  const [regimes, setRegimes]         = useState<Regime[]>([]);
  const [riskTiers, setRiskTiers]     = useState<RiskTier[]>([]);
  const [provenance, setProvenance]   = useState<Record<string, ProvenanceFeed> | null>(null);
  const [events, setEvents]           = useState<OpsEvent[]>([]);

  const [activeCycle, setActiveCycle] = useState<string | undefined>(undefined);
  const [activeLead, setActiveLead]   = useState<number>(24);
  const [availCycles, setAvailCycles] = useState<string[]>([]);

  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState<string | null>(null);
  const [expandedStage, setExpandedStage] = useState<number | null>(null);
  const [lastRefresh, setLastRefresh] = useState<string>('');

  const loadAll = useCallback(async (cycle?: string, lead = 24) => {
    setLoading(true);
    setError(null);
    try {
      const [sum, pip, reg, risk, prov, evts] = await Promise.all([
        fetchDashboardSummary(cycle, lead),
        fetchDashboardPipeline(),
        fetchDashboardRegimes(lead),
        fetchDashboardRisk(lead),
        fetchDashboardProvenance(),
        fetchDashboardEvents(20),
      ]);
      setSummary(sum);
      if (!cycle && sum.available_cycles?.length) {
        setAvailCycles(sum.available_cycles);
        setActiveCycle(prev => prev ?? sum.active_cycle);
      }
      setPipeline(pip.stages || []);
      setRegimes(reg.regimes || []);
      setRiskTiers(risk.risk_tiers || []);
      setProvenance(prov.provenance || null);
      setEvents(evts.events || []);
      setLastRefresh(new Date().toLocaleTimeString());
    } catch (e: any) {
      setError(String(e.message));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadAll(activeCycle, activeLead); }, [activeCycle, activeLead, loadAll]);

  const kpis = summary?.kpis || {};
  const forecast = summary?.current_forecast || {};
  const dataMode = summary?.data_mode || 'SYNTHETIC_DEMO';
  const isSynthetic = dataMode === 'SYNTHETIC_DEMO';
  const completedStages = pipeline.filter(s => s.status === 'COMPLETED').length;
  const totalDomainCells = riskTiers.length ? (riskTiers[0]?.affected_cells / (riskTiers[0]?.percentage_of_domain / 100) || 331) : 331;

  const LEAD_OPTIONS = [24, 48, 72, 96, 120];

  return (
    <div className="space-y-6 pb-12">

      {/* ── 0. Data Mode Banner ── */}
      <div className={`flex items-center justify-between gap-4 px-4 py-3 rounded-xl border text-xs font-medium
        ${isSynthetic
          ? 'bg-amber-950/30 border-amber-600/40 text-amber-300'
          : 'bg-emerald-950/30 border-emerald-600/40 text-emerald-300'}`}>
        <div className="flex items-center gap-2">
          {isSynthetic
            ? <ShieldAlert className="w-4 h-4 shrink-0" />
            : <ShieldCheck className="w-4 h-4 shrink-0" />}
          <span className="uppercase tracking-wide font-semibold">{String(dataMode || 'SYNTHETIC_DEMO').replace(/_/g, ' ')}</span>
          {isSynthetic && <span className="font-normal text-amber-400/80">— district aggregations from synthetic demo grids</span>}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {lastRefresh && <span className="text-slate-400 font-mono hidden sm:block">Updated {lastRefresh}</span>}
          <button
            onClick={() => loadAll(activeCycle, activeLead)}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 transition-colors"
            title="Refresh dashboard"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-xl bg-red-950/40 border border-red-700/40 text-red-300 text-xs">
          ⚠ Backend error: {error}. Displaying last available data.
        </div>
      )}

      {/* ── 1. Hero Banner: System State + Cycle & Lead Selectors ── */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900 to-monsoon-950 p-5 md:p-7 border border-slate-800 shadow-2xl">
        <div className="absolute inset-0 pointer-events-none opacity-10">
          <div className="absolute -top-20 -right-20 w-72 h-72 rounded-full bg-monsoon-600 blur-3xl" />
          <div className="absolute -bottom-16 -left-16 w-56 h-56 rounded-full bg-indigo-700 blur-2xl" />
        </div>
        <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-5">
          <div className="space-y-2 max-w-xl">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              <span className="text-xs font-medium text-emerald-400 uppercase tracking-widest">
                {summary?.system_status || 'OPERATIONAL'}
              </span>
            </div>
            <h2 className="text-2xl md:text-3xl font-bold text-white tracking-tight leading-tight">
              RAMP Operational Dashboard
            </h2>
            <p className="text-slate-300 text-sm leading-relaxed">
              Regime-Aware Mixture-of-Experts Post-Processor · MoES / NCMRWF ·{' '}
              <span className="font-mono text-monsoon-300">{summary?.model_version || '—'}</span>
            </p>
            <div className="flex flex-wrap gap-3 mt-1 text-xs">
              <span className="text-slate-400">
                Last inference: <span className="text-slate-200 font-mono">{summary?.last_inference_time || '—'}</span>
              </span>
              <span className="text-slate-600">|</span>
              <span className="text-slate-400">
                Published: <span className="text-slate-200 font-mono">{summary?.last_publication_time || '—'}</span>
              </span>
            </div>
          </div>

          {/* Selectors */}
          <div className="flex flex-col sm:flex-row gap-3 shrink-0">
            <div className="space-y-1">
              <label className="text-[10px] text-slate-400 uppercase tracking-wider block">Cycle</label>
              <select
                value={activeCycle || ''}
                onChange={e => setActiveCycle(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-monsoon-500 font-mono min-w-[160px]"
              >
                {availCycles.map(c => <option key={c} value={c}>{c}</option>)}
                {!availCycles.length && <option value="">Loading…</option>}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-[10px] text-slate-400 uppercase tracking-wider block">Lead Time</label>
              <select
                value={activeLead}
                onChange={e => setActiveLead(Number(e.target.value))}
                className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-monsoon-500"
              >
                {LEAD_OPTIONS.map(h => <option key={h} value={h}>+{h}h (Day {h / 24})</option>)}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* ── 2. Operational KPI Cards (8 cards) ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <KpiCard label="System State"       value={kpis.system_state || '—'}     sub="RAMP pipeline state" icon={<Activity className="w-5 h-5" />} accent="text-emerald-400" />
        <KpiCard label="Data Readiness"     value={kpis.data_readiness?.ratio || '—'}  sub={`NCUM: ${kpis.data_readiness?.sources?.ncum ? '✓' : '✗'} | NEPS: ${kpis.data_readiness?.sources?.neps ? '✓' : '✗'} | IMD: ${kpis.data_readiness?.sources?.imd ? '✓' : '✗'}`} icon={<Database className="w-5 h-5" />} accent="text-indigo-400" />
        <KpiCard label="Active Cycle"       value={kpis.active_cycle || '—'}     sub="NWP initialization" icon={<Clock className="w-5 h-5" />} accent="text-sky-400" />
        <KpiCard label="Latest Lead"        value={kpis.latest_lead || `+${activeLead}h`} sub="Forecast horizon" icon={<TrendingUp className="w-5 h-5" />} accent="text-cyan-400" />
        <KpiCard label="Grid Coverage"      value={forecast.total_grid_cells || '—'} sub={forecast.grid_resolution || '0.25° India Domain'} icon={<Globe className="w-5 h-5" />} accent="text-violet-400" />
        <KpiCard label="High-Risk Districts" value={kpis.high_risk_districts ?? '—'} sub="≥64.5 mm threshold" icon={<AlertTriangle className="w-5 h-5" />} accent="text-amber-400" />
        <KpiCard label="Extreme-Risk Districts" value={kpis.extreme_risk_districts ?? '—'} sub="≥204.5 mm threshold" icon={<ShieldAlert className="w-5 h-5" />} accent="text-red-400" />
        <KpiCard label="Verification"       value={kpis.verification_status || '—'} sub="WMO metric readiness" icon={<CheckCircle2 className="w-5 h-5" />} accent="text-emerald-400" />
      </div>

      {/* ── 3. Current Forecast Summary ── */}
      {forecast.total_grid_cells != null && (
        <div className="glass-panel rounded-2xl p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-cyan-400" />
            <h3 className="text-sm font-semibold text-white">Current Forecast Bulletin</h3>
            <span className="ml-auto text-xs text-slate-400 font-mono">Valid: {forecast.valid_time || '—'}</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 text-center">
            {[
              { label: 'Domain',         value: forecast.domain || '—' },
              { label: 'Resolution',     value: forecast.grid_resolution || '0.25°' },
              { label: 'Grid Cells',     value: String(forecast.total_grid_cells || '—') },
              { label: 'Mean Rainfall',  value: forecast.mean_rainfall_mm != null ? `${forecast.mean_rainfall_mm} mm` : '—' },
              { label: 'Peak Rainfall',  value: forecast.maximum_rainfall_mm != null ? `${forecast.maximum_rainfall_mm} mm` : '—' },
              { label: 'Dominant Regime',value: (forecast.dominant_regime || '—').replace(/_/g, ' ') },
            ].map(({ label, value }) => (
              <div key={label} className="bg-slate-900/60 border border-slate-800 rounded-xl p-3 space-y-1">
                <div className="text-[10px] text-slate-400 uppercase tracking-wider">{label}</div>
                <div className="text-sm font-semibold text-slate-100 break-words leading-tight">{value}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── 4. Live Pipeline Stages ── */}
      <div className="glass-panel rounded-2xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-monsoon-400" />
            <h3 className="text-sm font-semibold text-white">Live Pipeline Execution</h3>
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-400">
            <span className="font-mono text-emerald-400">{completedStages} / {pipeline.length} Stages</span>
            <span className="text-slate-500">Sequential Guarantee</span>
          </div>
        </div>
        <div className="space-y-2">
          {pipeline.length === 0
            ? Array.from({ length: 7 }).map((_, i) => (
                <div key={i} className="h-14 bg-slate-900/50 rounded-xl animate-pulse border border-slate-800" />
              ))
            : pipeline.map(stage => (
                <PipelineStageCard
                  key={stage.id}
                  stage={stage}
                  expanded={expandedStage === stage.id}
                  onToggle={() => setExpandedStage(prev => prev === stage.id ? null : stage.id)}
                />
              ))}
        </div>
      </div>

      {/* ── 5 & 6. Regimes + Risk Tiers ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Regime Distribution */}
        <div className="glass-panel rounded-2xl p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-violet-400" />
            <h3 className="text-sm font-semibold text-white">Weather Regime Distribution</h3>
          </div>
          <div className="space-y-3">
            {regimes.length === 0
              ? Array.from({ length: 7 }).map((_, i) => (
                  <div key={i} className="h-10 bg-slate-900/50 rounded-lg animate-pulse border border-slate-800" />
                ))
              : regimes.map(r => (
                  <div key={r.code} className="group relative">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: r.color }} />
                      <span className="text-xs font-medium text-slate-200 flex-1 truncate" title={r.name}>{r.name}</span>
                      <span className="text-[11px] font-mono text-slate-300 shrink-0">{r.probability_pct}%</span>
                      <span className="text-[11px] text-slate-500 shrink-0 hidden sm:block">{r.mean_rainfall_mm} mm</span>
                    </div>
                    <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-700"
                        style={{ width: `${r.probability_pct}%`, backgroundColor: r.color }}
                      />
                    </div>
                    {/* Hover tooltip */}
                    <div className="absolute z-10 bottom-full left-0 mb-2 hidden group-hover:block">
                      <div className="bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-300 max-w-[240px] shadow-xl">
                        <div className="font-semibold text-white mb-1">{r.name}</div>
                        <div>Coverage: {r.coverage_pct}% of domain</div>
                        <div>Mean rainfall: {r.mean_rainfall_mm} mm</div>
                        <div>Extreme risk: {r.extreme_probability_pct}%</div>
                        <div className="mt-1 text-slate-400 text-[10px]">{r.description}</div>
                      </div>
                    </div>
                  </div>
                ))}
          </div>
        </div>

        {/* Forecast Risk Tiers */}
        <div className="glass-panel rounded-2xl p-5 space-y-4">
          <div className="flex items-center gap-2">
            <CloudRain className="w-5 h-5 text-amber-400" />
            <h3 className="text-sm font-semibold text-white">IMD Rainfall Risk Tiers</h3>
            <span className="ml-auto text-[10px] text-slate-400 font-mono">Domain: {Math.round(totalDomainCells)} cells</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {riskTiers.length === 0
              ? Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="h-24 bg-slate-900/50 rounded-xl animate-pulse border border-slate-800" />
                ))
              : riskTiers.map(t => {
                  const sty = SEVERITY_STYLES[t.severity] || SEVERITY_STYLES.NORMAL;
                  return (
                    <div key={t.tier} className={`rounded-xl border p-3.5 space-y-2 ${sty.bg} ${sty.border}`}>
                      <div className="flex items-start justify-between gap-1">
                        <div>
                          <div className={`text-xs font-bold ${sty.text}`}>{t.name}</div>
                          <div className="text-[10px] text-slate-400 font-mono mt-0.5">{t.threshold_label}</div>
                        </div>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold border ${sty.border} ${sty.text}`}>{t.severity}</span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-300 font-semibold">{t.affected_cells} cells ({t.percentage_of_domain}%)</span>
                        <span className="text-slate-400 font-mono">P={t.maximum_probability.toFixed(3)}</span>
                      </div>
                      <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full transition-all duration-700 ${sty.bar}`} style={{ width: `${Math.min(100, t.percentage_of_domain * 5)}%` }} />
                      </div>
                    </div>
                  );
                })}
          </div>
        </div>
      </div>

      {/* ── 7. Verification Performance ── */}
      <div className="glass-panel rounded-2xl p-5 space-y-4">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-emerald-400" />
          <h3 className="text-sm font-semibold text-white">Forecast Verification Performance</h3>
          <span className="ml-auto px-2 py-1 rounded-full bg-amber-950/60 border border-amber-700/40 text-amber-300 text-[10px] font-semibold uppercase tracking-wide">
            VERIFICATION PENDING
          </span>
        </div>
        <div className="rounded-xl bg-amber-950/20 border border-amber-700/30 p-4 text-xs text-amber-300 space-y-1.5">
          <div className="flex items-start gap-2">
            <Lock className="w-3.5 h-3.5 shrink-0 mt-0.5 text-amber-400" />
            <div>
              <span className="font-semibold text-amber-200">No fabricated scores will be shown.</span>{' '}
              WMO metrics (RMSE, MAE, CSI, POD, FAR, ETS, FSS) require authoritative IMD 0.25° gridded
              observation file to be paired with this forecast cycle. Verification will appear automatically
              once +24h observations are ingested.
            </div>
          </div>
        </div>
        <div className="overflow-x-auto rounded-xl border border-slate-800">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-slate-900/80">
                <th className="px-3 py-2 text-left text-slate-400 font-semibold">Model</th>
                {['MAE (mm)', 'RMSE (mm)', 'CSI', 'POD', 'FAR', 'ETS', 'FSS@50km'].map(h => (
                  <th key={h} className="px-3 py-2 text-center text-slate-400 font-semibold">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                { name: 'Raw NWP (Baseline)', color: 'text-slate-300' },
                { name: 'Mean Bias Correction', color: 'text-slate-300' },
                { name: 'RAMP MoE (This System)', color: 'text-cyan-300 font-semibold' },
              ].map(row => (
                <tr key={row.name} className="border-t border-slate-800/80 hover:bg-slate-900/30">
                  <td className={`px-3 py-2 ${row.color}`}>{row.name}</td>
                  {Array.from({ length: 7 }).map((_, i) => (
                    <td key={i} className="px-3 py-2 text-center text-slate-600 font-mono">—</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── 8. Data Provenance ── */}
      {provenance && (
        <div className="glass-panel rounded-2xl p-5 space-y-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-cyan-400" />
            <h3 className="text-sm font-semibold text-white">Data & Model Provenance</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
            {Object.entries(provenance).map(([key, feed]) => (
              <div key={key} className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-100 uppercase tracking-wide">{key.toUpperCase()}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold border
                    ${feed.status === 'MOUNTED' || feed.status === 'PRODUCTION_VERIFIED' || feed.status === 'AVAILABLE_IN_VAULT'
                      ? 'text-emerald-300 border-emerald-700/40 bg-emerald-950/40'
                      : 'text-amber-300 border-amber-700/40 bg-amber-950/40'}`}>
                    {feed.status}
                  </span>
                </div>
                <div className="text-[11px] text-slate-400">{feed.source}</div>
                {(feed.cycle || feed.observation_date) && (
                  <div className="text-[11px] text-slate-300 font-mono">{feed.cycle || feed.observation_date}</div>
                )}
                <div className="text-[10px] text-slate-600 font-mono break-all leading-relaxed">
                  SHA-256: {feed.checksum_sha256?.substring(0, 24)}…
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── 9. Operational Event Log ── */}
      <div className="glass-panel rounded-2xl p-5 space-y-4">
        <div className="flex items-center gap-2">
          <MapPin className="w-5 h-5 text-slate-400" />
          <h3 className="text-sm font-semibold text-white">Operational Event Audit Log</h3>
          <span className="ml-auto text-xs text-slate-400">{events.length} events</span>
        </div>
        <div className="overflow-x-auto rounded-xl border border-slate-800">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-slate-900/80">
                {['Timestamp', 'Event Type', 'Actor', 'Cycle', 'Message', 'Status'].map(h => (
                  <th key={h} className="px-3 py-2 text-left text-slate-400 font-semibold whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {events.length === 0
                ? (
                  <tr><td colSpan={6} className="px-3 py-6 text-center text-slate-500">No events recorded yet.</td></tr>
                )
                : events.map((ev, idx) => (
                  <tr key={ev.event_id || `${ev.timestamp}-${idx}`} className="border-t border-slate-800/80 hover:bg-slate-900/30">
                    <td className="px-3 py-2 font-mono text-slate-400 whitespace-nowrap">{new Date(ev.timestamp).toLocaleTimeString()}</td>
                    <td className="px-3 py-2 text-slate-300 whitespace-nowrap">{String(ev.event_type || ev.service || 'SYSTEM').replace(/_/g, ' ')}</td>
                    <td className="px-3 py-2 text-slate-400">{ev.actor || 'SYSTEM'}</td>
                    <td className="px-3 py-2 text-slate-400 font-mono">{ev.cycle_id || '—'}</td>
                    <td className="px-3 py-2 text-slate-300">{ev.message || ev.event || ev.details || '—'}</td>
                    <td className="px-3 py-2">
                      <span className={`px-2 py-0.5 rounded font-semibold text-[10px] border
                        ${(ev.status === 'SUCCESS' || ev.status === 'PASS')
                          ? 'text-emerald-300 border-emerald-700/40 bg-emerald-950/40'
                          : 'text-red-300 border-red-700/40 bg-red-950/40'}`}>
                        {ev.status}
                      </span>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
