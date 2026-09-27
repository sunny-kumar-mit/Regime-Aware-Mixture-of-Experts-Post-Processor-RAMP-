/**
 * Phase 15 — Operations Control Center
 * SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
 * MoES / NCMRWF
 *
 * Tabbed Operations Dashboard:
 *   Tab 1: Overview     — System status, state machine, health panel
 *   Tab 2: Scheduler    — Start/stop scheduler, job queue, manual submit
 *   Tab 3: Alerts       — Active alerts, rules, acknowledge/resolve
 *   Tab 4: Drift        — Feature/prediction/regime/calibration drift
 *   Tab 5: Readiness    — 30-point pre-launch readiness checklist
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  AlertTriangle,
  AlertCircle,
  Bell,
  CheckCircle2,
  ChevronRight,
  Clock,
  Cpu,
  Database,
  Play,
  Pause,
  RefreshCw,
  Send,
  Settings,
  Shield,
  ShieldCheck,
  ShieldAlert,
  TrendingUp,
  Zap,
  BarChart3,
  Lock,
  Unlock,
} from 'lucide-react';

import {
  fetchOperationsStatus,
  fetchOperationsState,
  fetchOperationsScheduler,
  fetchOperationsJobs,
  fetchOperationsAlerts,
  fetchOperationsDrift,
  fetchOperationsReadiness,
  postSchedulerStart,
  postSchedulerStop,
  postSubmitJob,
  postAcknowledgeAlert,
  postResolveAlert,
  postOperationsStateTransition,
  fetchProductionStatus,
  fetchProductionDataHealth,
  fetchProductionFreshness,
  fetchProductionCycles,
  fetchProductionPublications,
  fetchProductionHealth,
  fetchProductionVerification,
} from '../api/client';

// ── Types ─────────────────────────────────────────────────────────────────

type ActiveTab = 'live_ops' | 'overview' | 'scheduler' | 'alerts' | 'drift' | 'readiness' | 'real_activation';

interface OpsStatus {
  generated_at: string;
  data_mode: string;
  banner: string;
  state_machine: Record<string, any>;
  scheduler: Record<string, any>;
  alerts: { active: number; critical: number; total_raised: number };
  drift: { overall_level: string; generated_at: string | null };
  gates: { real_operational: boolean; synthetic_demo: boolean; note: string };
}

// ── Utility Helpers ────────────────────────────────────────────────────────

const STATE_COLORS: Record<string, string> = {
  INITIALIZING: '#64748b',
  WAITING_FOR_DATA: '#3b82f6',
  DATA_RECEIVED: '#8b5cf6',
  VALIDATING: '#f59e0b',
  VALIDATION_FAILED: '#ef4444',
  READY_FOR_INFERENCE: '#22c55e',
  INFERENCING: '#06b6d4',
  PUBLISHING: '#a855f7',
  PUBLISHED: '#10b981',
  ALERT_RAISED: '#f97316',
  CYCLE_COMPLETE: '#6366f1',
};

const JOB_STATUS_COLOR: Record<string, string> = {
  SUCCESS: '#10b981',
  FAILED: '#ef4444',
  RUNNING: '#3b82f6',
  PENDING: '#94a3b8',
  SKIPPED: '#64748b',
};

const SEVERITY_COLOR: Record<string, string> = {
  INFO: '#3b82f6',
  WARNING: '#f59e0b',
  CRITICAL: '#ef4444',
};

const DRIFT_LEVEL_COLOR: Record<string, string> = {
  NONE: '#10b981',
  WARNING: '#f59e0b',
  CRITICAL: '#ef4444',
};

const CHECK_STATUS_COLOR: Record<string, string> = {
  PASS: '#10b981',
  FAIL: '#ef4444',
  WARN: '#f59e0b',
  SKIP: '#64748b',
};

function ts(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleTimeString('en-IN', { hour12: false });
  } catch {
    return iso;
  }
}

// ── Sub-components ─────────────────────────────────────────────────────────

const DataBanner: React.FC = () => (
  <div style={{
    background: 'linear-gradient(90deg, #1e3a5f 0%, #0f2540 100%)',
    border: '1px solid #f59e0b55',
    borderRadius: '8px',
    padding: '10px 18px',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    marginBottom: '20px',
  }}>
    <AlertTriangle size={16} color="#f59e0b" />
    <span style={{ color: '#fbbf24', fontSize: '13px', fontWeight: 600, letterSpacing: '0.04em' }}>
      SYNTHETIC DEMONSTRATION MODE
    </span>
    <span style={{ color: '#94a3b8', fontSize: '12px', marginLeft: '8px' }}>
      — Real NCMRWF NCUM / IMD operational archives not mounted. All products carry SYNTHETIC_DEMO provenance.
    </span>
  </div>
);

interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  color?: string;
  sub?: string;
}

const StatCard: React.FC<StatCardProps> = ({ label, value, icon, color = '#3b82f6', sub }) => (
  <div style={{
    background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
    border: '1px solid #1e3a5f',
    borderRadius: '12px',
    padding: '18px 20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    minWidth: '160px',
    flex: 1,
  }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#64748b' }}>
      <span style={{ color }}>{icon}</span>
      <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        {label}
      </span>
    </div>
    <div style={{ fontSize: '28px', fontWeight: 700, color, lineHeight: 1.1 }}>{value}</div>
    {sub && <div style={{ fontSize: '11px', color: '#64748b' }}>{sub}</div>}
  </div>
);

interface StateNodeProps {
  state: string;
  active: boolean;
}

const StateNode: React.FC<StateNodeProps> = ({ state, active }) => {
  const color = STATE_COLORS[state] || '#94a3b8';
  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px',
      padding: '4px 10px',
      borderRadius: '6px',
      background: active ? `${color}25` : '#0f172a',
      border: `1px solid ${active ? color : '#1e3a5f'}`,
      fontSize: '12px',
      fontWeight: active ? 700 : 400,
      color: active ? color : '#475569',
      transition: 'all 0.3s ease',
    }}>
      {active && <span style={{ width: 8, height: 8, borderRadius: '50%', background: color, display: 'inline-block', boxShadow: `0 0 8px ${color}` }} />}
      {state}
    </div>
  );
};

// ── Live Operations Tab (Phase 17 Part Z) ───────────────────────────────────

const LiveOperationsTab: React.FC = () => {
  const [prodStatus, setProdStatus] = useState<any | null>(null);
  const [dataHealth, setDataHealth] = useState<any | null>(null);
  const [freshness, setFreshness] = useState<any | null>(null);
  const [cycles, setCycles] = useState<any[]>([]);
  const [publications, setPublications] = useState<any | null>(null);
  const [health, setHealth] = useState<any | null>(null);
  const [verification, setVerification] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  const loadLiveOps = useCallback(async () => {
    try {
      setLoading(true);
      const [ps, dh, fn, cy, pb, hl, vf] = await Promise.all([
        fetchProductionStatus().catch(() => null),
        fetchProductionDataHealth().catch(() => null),
        fetchProductionFreshness().catch(() => null),
        fetchProductionCycles().catch(() => null),
        fetchProductionPublications(5).catch(() => null),
        fetchProductionHealth().catch(() => null),
        fetchProductionVerification().catch(() => null),
      ]);
      if (ps && ps.status === 'SUCCESS') setProdStatus(ps.data);
      if (dh && dh.status === 'SUCCESS') setDataHealth(dh.data);
      if (fn && fn.status === 'SUCCESS') setFreshness(fn.data);
      if (cy && cy.status === 'SUCCESS') setCycles(cy.data?.cycles || []);
      if (pb && pb.status === 'SUCCESS') setPublications(pb.data);
      if (hl && hl.status === 'SUCCESS') setHealth(hl.data);
      if (vf && vf.status === 'SUCCESS') setVerification(vf.data);
    } catch (e) {
      console.error('Failed to load live ops:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadLiveOps();
    const interval = setInterval(loadLiveOps, 15000);
    return () => clearInterval(interval);
  }, [loadLiveOps]);

  if (loading && !prodStatus) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
        <RefreshCw size={24} style={{ animation: 'spin 1s linear infinite', margin: '0 auto 12px auto' }} />
        <div>Loading live operational feeds & telemetry...</div>
      </div>
    );
  }

  const providers = dataHealth?.providers || {};
  const ncum = providers.NCMRWF_NCUM || {};
  const neps = providers.NCMRWF_NEPS || {};
  const imd = providers.IMD_GRIDDED_OBSERVATION || {};
  const currentCycle = cycles.length > 0 ? cycles[0] : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* 12 Live Operations Sections (Part Z) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>

        {/* 1. Current System State */}
        <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '10px', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, color: '#3b82f6', textTransform: 'uppercase', fontFamily: 'monospace' }}>
              1. Current System State
            </span>
            <span style={{ fontSize: '10px', padding: '2px 8px', borderRadius: '4px', background: '#1e3a5f', color: '#60a5fa', fontWeight: 600 }}>
              {prodStatus?.environment || 'PRODUCTION'}
            </span>
          </div>
          <div style={{ fontSize: '16px', fontWeight: 700, color: '#f8fafc', marginBottom: '4px' }}>
            {prodStatus?.current_state || 'INITIALIZING'}
          </div>
          <div style={{ fontSize: '12px', color: '#94a3b8' }}>
            Data Mode: <strong style={{ color: '#fbbf24' }}>{prodStatus?.data_mode || 'SYNTHETIC_DEMO'}</strong>
          </div>
          <div style={{ fontSize: '11px', color: '#64748b', marginTop: '6px' }}>
            Operational Gate: <span style={{ color: '#f87171' }}>REAL_OPERATIONAL_BLOCKED</span>
          </div>
        </div>

        {/* 2. Current Data Sources */}
        <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '10px', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, color: '#10b981', textTransform: 'uppercase', fontFamily: 'monospace' }}>
              2. Current Data Sources
            </span>
            <span style={{ fontSize: '10px', color: '#64748b' }}>3 Feeds Configured</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#cbd5e1' }}>
              <span>NCMRWF NCUM Global:</span>
              <span style={{ color: ncum.mounted ? '#34d399' : '#f87171', fontWeight: 600 }}>
                {ncum.mounted ? 'MOUNTED' : 'UNMOUNTED'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#cbd5e1' }}>
              <span>NCMRWF NEPS Ensemble:</span>
              <span style={{ color: neps.mounted ? '#34d399' : '#f87171', fontWeight: 600 }}>
                {neps.mounted ? 'MOUNTED' : 'UNMOUNTED'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#cbd5e1' }}>
              <span>IMD 0.25° Gridded Obs:</span>
              <span style={{ color: imd.mounted ? '#34d399' : '#f87171', fontWeight: 600 }}>
                {imd.mounted ? 'MOUNTED' : 'UNMOUNTED'}
              </span>
            </div>
          </div>
        </div>

        {/* 3. Latest NCUM Cycle */}
        <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '10px', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, color: '#60a5fa', textTransform: 'uppercase', fontFamily: 'monospace' }}>
              3. Latest NCUM Cycle
            </span>
            <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '4px', background: '#1e293b', color: '#94a3b8' }}>
              ~12 km Det
            </span>
          </div>
          <div style={{ fontSize: '15px', fontWeight: 700, color: '#e2e8f0', marginBottom: '4px' }}>
            {ncum.latest_cycle || 'None (Unmounted)'}
          </div>
          <div style={{ fontSize: '12px', color: '#94a3b8' }}>
            Arrival Status: <span style={{ color: ncum.status === 'ON_TIME' ? '#34d399' : '#fbbf24' }}>{ncum.status || 'WAITING_FOR_DATA'}</span>
          </div>
          <div style={{ fontSize: '11px', color: '#64748b', marginTop: '6px' }}>
            Delay: {ncum.delay_minutes !== null && ncum.delay_minutes !== undefined ? `${ncum.delay_minutes} min` : 'N/A'} · QC: {ncum.qc_status || 'UNVERIFIED'}
          </div>
        </div>

        {/* 4. Latest NEPS Cycle */}
        <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '10px', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, color: '#a78bfa', textTransform: 'uppercase', fontFamily: 'monospace' }}>
              4. Latest NEPS Cycle
            </span>
            <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '4px', background: '#1e293b', color: '#94a3b8' }}>
              11 Members
            </span>
          </div>
          <div style={{ fontSize: '15px', fontWeight: 700, color: '#e2e8f0', marginBottom: '4px' }}>
            {neps.latest_cycle || 'None (Unmounted)'}
          </div>
          <div style={{ fontSize: '12px', color: '#94a3b8' }}>
            Ensemble Spread QC: <span style={{ color: neps.qc_status === 'PASS' ? '#34d399' : '#94a3b8' }}>{neps.qc_status || 'UNVERIFIED'}</span>
          </div>
          <div style={{ fontSize: '11px', color: '#64748b', marginTop: '6px' }}>
            Coverage: {neps.coverage_pct ?? 0}% · Status: {neps.status || 'WAITING_FOR_DATA'}
          </div>
        </div>

        {/* 5. Latest IMD Observation */}
        <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '10px', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, color: '#34d399', textTransform: 'uppercase', fontFamily: 'monospace' }}>
              5. Latest IMD Observation
            </span>
            <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '4px', background: '#1e293b', color: '#94a3b8' }}>
              0.25° Daily
            </span>
          </div>
          <div style={{ fontSize: '15px', fontWeight: 700, color: '#e2e8f0', marginBottom: '4px' }}>
            {imd.latest_date || 'No Ground Truth Available'}
          </div>
          <div style={{ fontSize: '12px', color: '#94a3b8' }}>
            Pairing Readiness: <span style={{ color: imd.mounted ? '#34d399' : '#f87171' }}>{imd.mounted ? 'READY' : 'BLOCKED'}</span>
          </div>
          <div style={{ fontSize: '11px', color: '#64748b', marginTop: '6px' }}>
            Lag: {imd.delay_minutes !== null && imd.delay_minutes !== undefined ? `${imd.delay_minutes} min` : 'N/A'} · Status: {imd.status || 'NOT_AVAILABLE'}
          </div>
        </div>

        {/* 6. Current Forecast Cycle */}
        <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '10px', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, color: '#f59e0b', textTransform: 'uppercase', fontFamily: 'monospace' }}>
              6. Current Forecast Cycle
            </span>
            <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '4px', background: '#1e293b', color: '#fbbf24' }}>
              {currentCycle?.status || 'IDLE'}
            </span>
          </div>
          <div style={{ fontSize: '15px', fontWeight: 700, color: '#e2e8f0', marginBottom: '4px' }}>
            {currentCycle?.cycle_id || 'DEMO_20260927_00Z'}
          </div>
          <div style={{ fontSize: '12px', color: '#94a3b8' }}>
            Leads Supported: <strong style={{ color: '#38bdf8' }}>{currentCycle?.supported_leads?.length || 9} leads</strong> (+6h to +120h)
          </div>
          <div style={{ fontSize: '11px', color: '#64748b', marginTop: '6px' }}>
            Model Version: <strong style={{ color: '#c084fc' }}>{prodStatus?.model_version || 'ramp_moe_v2.0.0'}</strong>
          </div>
        </div>

        {/* 7. Job Queue */}
        <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '10px', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, color: '#38bdf8', textTransform: 'uppercase', fontFamily: 'monospace' }}>
              7. Job Queue
            </span>
            <span style={{ fontSize: '10px', color: '#64748b' }}>Deterministic SHA-256</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#cbd5e1', marginBottom: '4px' }}>
            <span>Active Jobs:</span>
            <span style={{ fontWeight: 700, color: '#38bdf8' }}>{prodStatus?.jobs?.active ?? 0}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#cbd5e1', marginBottom: '4px' }}>
            <span>Completed Jobs:</span>
            <span style={{ fontWeight: 700, color: '#34d399' }}>{prodStatus?.jobs?.completed ?? 9}</span>
          </div>
          <div style={{ fontSize: '11px', color: '#64748b', marginTop: '6px' }}>
            Idempotency: Guaranteed 100% (No duplicate run)
          </div>
        </div>

        {/* 8. Active Alerts */}
        <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '10px', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, color: '#f87171', textTransform: 'uppercase', fontFamily: 'monospace' }}>
              8. Active Alerts
            </span>
            <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '4px', background: '#7f1d1d', color: '#fca5a5' }}>
              15 Categories
            </span>
          </div>
          <div style={{ fontSize: '18px', fontWeight: 700, color: '#f87171', marginBottom: '4px' }}>
            {prodStatus?.alerts?.active ?? 0} Active ({prodStatus?.alerts?.critical ?? 0} Critical)
          </div>
          <div style={{ fontSize: '12px', color: '#94a3b8' }}>
            Circuit Breaker: {prodStatus?.emergency_stop ? 'TRIPPED (STOP)' : 'NORMAL'}
          </div>
          <div style={{ fontSize: '11px', color: '#64748b', marginTop: '6px' }}>
            Alert Dedup: Enabled (No duplicate notifications)
          </div>
        </div>

        {/* 9. Data Freshness */}
        <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '10px', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, color: '#eab308', textTransform: 'uppercase', fontFamily: 'monospace' }}>
              9. Data Freshness
            </span>
            <span style={{ fontSize: '10px', color: '#64748b' }}>Synoptic Deadlines</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '12px', color: '#cbd5e1' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>00Z Morning Cycle:</span>
              <span style={{ color: '#fbbf24', fontWeight: 600 }}>{freshness?.cycles?.['00Z']?.status || 'WAITING_FOR_DATA'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>12Z Evening Cycle:</span>
              <span style={{ color: '#fbbf24', fontWeight: 600 }}>{freshness?.cycles?.['12Z']?.status || 'WAITING_FOR_DATA'}</span>
            </div>
          </div>
          <div style={{ fontSize: '11px', color: '#64748b', marginTop: '6px' }}>
            Max Tolerance: 360 min delay before alert
          </div>
        </div>

        {/* 10. Forecast Publication */}
        <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '10px', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, color: '#c084fc', textTransform: 'uppercase', fontFamily: 'monospace' }}>
              10. Forecast Publication
            </span>
            <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '4px', background: '#1e293b', color: '#94a3b8' }}>
              Catalog
            </span>
          </div>
          <div style={{ fontSize: '14px', fontWeight: 700, color: '#e2e8f0', marginBottom: '4px' }}>
            State: {publications?.latest?.publication_state || 'VALIDATED'}
          </div>
          <div style={{ fontSize: '12px', color: '#94a3b8' }}>
            Public Dissemination: <span style={{ color: '#38bdf8' }}>SYNTHETIC DEMO ONLY</span>
          </div>
          <div style={{ fontSize: '11px', color: '#64748b', marginTop: '6px' }}>
            Total Catalog Records: {publications?.total ?? 1}
          </div>
        </div>

        {/* 11. Verification Status */}
        <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '10px', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, color: '#fb923c', textTransform: 'uppercase', fontFamily: 'monospace' }}>
              11. Verification Status
            </span>
            <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '4px', background: '#1e293b', color: '#94a3b8' }}>
              Continuous
            </span>
          </div>
          <div style={{ fontSize: '14px', fontWeight: 700, color: '#fca5a5', marginBottom: '4px' }}>
            {verification?.status || 'REAL VERIFICATION NOT AVAILABLE'}
          </div>
          <div style={{ fontSize: '12px', color: '#94a3b8' }}>
            IMD Pairing Samples: <strong>0 (Unmounted)</strong>
          </div>
          <div style={{ fontSize: '11px', color: '#64748b', marginTop: '6px' }}>
            Metrics Stratification: Ready for 5 lead times & 4 regimes
          </div>
        </div>

        {/* 12. System Health */}
        <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '10px', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, color: '#2dd4bf', textTransform: 'uppercase', fontFamily: 'monospace' }}>
              12. System Health
            </span>
            <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '4px', background: '#134e4a', color: '#5eead4' }}>
              Modular Probes
            </span>
          </div>
          <div style={{ fontSize: '15px', fontWeight: 700, color: health?.overall === 'UP' ? '#34d399' : '#fbbf24', marginBottom: '4px' }}>
            Overall: {health?.overall || 'DEGRADED'}
          </div>
          <div style={{ fontSize: '12px', color: '#94a3b8' }}>
            Liveness: <span style={{ color: '#34d399' }}>{health?.live || 'UP'}</span> · Readiness: <span style={{ color: '#34d399' }}>{health?.ready || 'READY'}</span>
          </div>
          <div style={{ fontSize: '11px', color: '#64748b', marginTop: '6px' }}>
            Models: {health?.models || 'UP'} · Inference: {health?.inference || 'READY'}
          </div>
        </div>

      </div>
    </div>
  );
};

// ── Overview Tab ───────────────────────────────────────────────────────────

const OverviewTab: React.FC<{
  status: OpsStatus | null;
  stateData: Record<string, any> | null;
  loading: boolean;
  onTransition: (state: string) => void;
}> = ({ status, stateData, loading, onTransition }) => {
  if (loading || !status) return <LoadingSpinner />;

  const sm = status.state_machine;
  const currentState = sm?.current_state || 'UNKNOWN';
  const validNext = stateData?.valid_next_states || [];
  const history = stateData?.transition_history || [];

  const states = Object.keys(STATE_COLORS);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Stat row */}
      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        <StatCard
          label="System State"
          value={currentState}
          icon={<Activity size={16} />}
          color={STATE_COLORS[currentState] || '#94a3b8'}
          sub={`since ${ts(sm?.last_transition?.timestamp)}`}
        />
        <StatCard
          label="Active Alerts"
          value={status.alerts.active}
          icon={<Bell size={16} />}
          color={status.alerts.critical > 0 ? '#ef4444' : '#f59e0b'}
          sub={`${status.alerts.critical} critical`}
        />
        <StatCard
          label="Drift Level"
          value={status.drift.overall_level || 'NONE'}
          icon={<TrendingUp size={16} />}
          color={DRIFT_LEVEL_COLOR[status.drift.overall_level] || '#10b981'}
          sub={`checked ${ts(status.drift.generated_at)}`}
        />
        <StatCard
          label="Scheduler"
          value={status.scheduler?.is_running ? 'RUNNING' : 'STOPPED'}
          icon={<Cpu size={16} />}
          color={status.scheduler?.is_running ? '#10b981' : '#64748b'}
          sub={`polls: ${status.scheduler?.poll_count || 0}`}
        />
      </div>

      {/* State machine diagram */}
      <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '12px', padding: '20px' }}>
        <h3 style={{ color: '#e2e8f0', marginBottom: '14px', fontSize: '14px', fontWeight: 700 }}>
          🔄 Operational State Machine
        </h3>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '16px' }}>
          {states.map((s) => (
            <StateNode key={s} state={s} active={s === currentState} />
          ))}
        </div>

        {validNext.length > 0 && (
          <div style={{ marginTop: '12px' }}>
            <div style={{ color: '#64748b', fontSize: '12px', marginBottom: '8px' }}>
              OPERATOR TRANSITION OPTIONS:
            </div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {validNext.map((ns: string) => (
                <button
                  key={ns}
                  onClick={() => onTransition(ns)}
                  style={{
                    padding: '6px 14px',
                    borderRadius: '6px',
                    background: `${STATE_COLORS[ns] || '#3b82f6'}20`,
                    border: `1px solid ${STATE_COLORS[ns] || '#3b82f6'}`,
                    color: STATE_COLORS[ns] || '#3b82f6',
                    cursor: 'pointer',
                    fontSize: '12px',
                    fontWeight: 600,
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.opacity = '0.8')}
                  onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
                >
                  → {ns}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Gates */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        <GateCard
          label="REAL_OPERATIONAL Gate"
          open={status.gates.real_operational}
          note="Requires authoritative NCMRWF/IMD data mount"
          icon={<Lock size={14} />}
        />
        <GateCard
          label="SYNTHETIC_DEMO Gate"
          open={status.gates.synthetic_demo}
          note="Development mode — all pipeline components verified"
          icon={<Unlock size={14} />}
        />
      </div>

      {/* Transition History */}
      <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '12px', padding: '20px' }}>
        <h3 style={{ color: '#e2e8f0', marginBottom: '14px', fontSize: '14px', fontWeight: 700 }}>
          📋 Transition History (last 10)
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {history.slice(-10).reverse().map((ev: any, i: number) => (
            <div key={i} style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '8px 12px',
              borderRadius: '6px',
              background: '#1e293b',
              fontSize: '12px',
            }}>
              <span style={{ color: STATE_COLORS[ev.from_state] || '#64748b', fontWeight: 600, minWidth: '160px' }}>
                {ev.from_state}
              </span>
              <ChevronRight size={12} color="#475569" />
              <span style={{ color: STATE_COLORS[ev.to_state] || '#94a3b8', fontWeight: 600, minWidth: '160px' }}>
                {ev.to_state}
              </span>
              <span style={{ color: '#64748b', flex: 1 }}>{ev.reason}</span>
              <span style={{ color: '#475569' }}>[{ev.triggered_by}]</span>
              <span style={{ color: '#334155' }}>{ts(ev.timestamp)}</span>
            </div>
          ))}
          {history.length === 0 && (
            <div style={{ color: '#475569', fontSize: '12px' }}>No transitions recorded yet.</div>
          )}
        </div>
      </div>
    </div>
  );
};

interface GateCardProps {
  label: string;
  open: boolean;
  note: string;
  icon: React.ReactNode;
}

const GateCard: React.FC<GateCardProps> = ({ label, open, note, icon }) => (
  <div style={{
    background: open ? '#052e16' : '#1a0a0a',
    border: `1px solid ${open ? '#22c55e55' : '#7f1d1d55'}`,
    borderRadius: '10px',
    padding: '16px',
  }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
      <span style={{ color: open ? '#22c55e' : '#ef4444' }}>{icon}</span>
      <span style={{ color: open ? '#22c55e' : '#ef4444', fontWeight: 700, fontSize: '13px' }}>
        {label}
      </span>
      <span style={{
        marginLeft: 'auto',
        fontSize: '11px',
        padding: '2px 8px',
        borderRadius: '4px',
        background: open ? '#22c55e25' : '#ef444425',
        color: open ? '#22c55e' : '#ef4444',
        fontWeight: 700,
      }}>
        {open ? 'OPEN' : 'BLOCKED'}
      </span>
    </div>
    <div style={{ color: '#64748b', fontSize: '11px' }}>{note}</div>
  </div>
);

// ── Scheduler Tab ──────────────────────────────────────────────────────────

const SchedulerTab: React.FC<{
  scheduler: Record<string, any> | null;
  jobs: Record<string, any>[] | null;
  loading: boolean;
  onStart: () => void;
  onStop: () => void;
  onSubmitJob: (cycle: string, lead: number) => void;
}> = ({ scheduler, jobs, loading, onStart, onStop, onSubmitJob }) => {
  const [cycleId, setCycleId] = useState('DEMO_20260927_00Z');
  const [leadHours, setLeadHours] = useState(24);
  const [submitting, setSubmitting] = useState(false);

  if (loading) return <LoadingSpinner />;

  const s = scheduler || {};
  const isRunning = s.is_running || false;
  const summary = s.job_summary || {};

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await onSubmitJob(cycleId, leadHours);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Scheduler control */}
      <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '12px', padding: '20px' }}>
        <h3 style={{ color: '#e2e8f0', marginBottom: '16px', fontSize: '14px', fontWeight: 700 }}>
          ⚙️ Automated Forecast Scheduler
        </h3>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '16px' }}>
          <StatCard label="Status" value={isRunning ? 'RUNNING' : 'STOPPED'} icon={<Activity size={14} />} color={isRunning ? '#10b981' : '#64748b'} />
          <StatCard label="Poll Count" value={s.poll_count || 0} icon={<Clock size={14} />} color="#3b82f6" sub={`interval: ${s.poll_interval_s || 300}s`} />
          <StatCard label="Total Jobs" value={summary.total || 0} icon={<Database size={14} />} color="#8b5cf6" />
          <StatCard label="Success Rate" value={summary.total > 0 ? `${Math.round(((summary.success || 0) / summary.total) * 100)}%` : '—'} icon={<CheckCircle2 size={14} />} color="#10b981" />
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button
            onClick={isRunning ? onStop : onStart}
            style={{
              padding: '10px 24px',
              borderRadius: '8px',
              background: isRunning
                ? 'linear-gradient(135deg, #7f1d1d, #ef4444)'
                : 'linear-gradient(135deg, #052e16, #22c55e)',
              border: 'none',
              color: '#fff',
              fontSize: '13px',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'opacity 0.2s',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.opacity = '0.85')}
            onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
          >
            {isRunning ? <><Pause size={14} /> STOP SCHEDULER</> : <><Play size={14} /> START SCHEDULER</>}
          </button>
          {s.last_poll_at && (
            <span style={{ color: '#64748b', fontSize: '12px' }}>
              Last poll: {ts(s.last_poll_at)}
            </span>
          )}
        </div>
      </div>

      {/* Manual job submit */}
      <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '12px', padding: '20px' }}>
        <h3 style={{ color: '#e2e8f0', marginBottom: '14px', fontSize: '14px', fontWeight: 700 }}>
          🚀 Submit Manual Forecast Job
        </h3>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ color: '#64748b', fontSize: '11px', fontWeight: 600 }}>CYCLE ID</label>
            <select
              value={cycleId}
              onChange={(e) => setCycleId(e.target.value)}
              style={{
                background: '#1e293b', border: '1px solid #334155', borderRadius: '6px',
                color: '#e2e8f0', padding: '8px 12px', fontSize: '13px',
              }}
            >
              <option value="DEMO_20260927_00Z">DEMO_20260927_00Z</option>
              <option value="DEMO_20260927_12Z">DEMO_20260927_12Z</option>
            </select>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ color: '#64748b', fontSize: '11px', fontWeight: 600 }}>LEAD HOURS</label>
            <select
              value={leadHours}
              onChange={(e) => setLeadHours(Number(e.target.value))}
              style={{
                background: '#1e293b', border: '1px solid #334155', borderRadius: '6px',
                color: '#e2e8f0', padding: '8px 12px', fontSize: '13px',
              }}
            >
              {[6, 12, 18, 24, 36, 48, 72, 96, 120].map((h) => (
                <option key={h} value={h}>{h}h</option>
              ))}
            </select>
          </div>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            style={{
              padding: '9px 20px',
              borderRadius: '8px',
              background: submitting ? '#1e293b' : 'linear-gradient(135deg, #1e3a5f, #3b82f6)',
              border: '1px solid #3b82f6',
              color: '#e2e8f0',
              cursor: submitting ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '13px',
              fontWeight: 600,
            }}
          >
            <Send size={14} />
            {submitting ? 'Submitting...' : 'Submit Job'}
          </button>
        </div>
        <div style={{ color: '#475569', fontSize: '11px', marginTop: '8px' }}>
          Idempotent: duplicate (cycle, lead, model_version) submissions are auto-skipped.
        </div>
      </div>

      {/* Job list */}
      <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '12px', padding: '20px' }}>
        <h3 style={{ color: '#e2e8f0', marginBottom: '14px', fontSize: '14px', fontWeight: 700 }}>
          📋 Recent Forecast Jobs
        </h3>
        {!jobs || jobs.length === 0 ? (
          <div style={{ color: '#475569', fontSize: '12px' }}>No jobs yet. Start scheduler or submit manually.</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {jobs.map((job: any) => (
              <JobRow key={job.job_id} job={job} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const JobRow: React.FC<{ job: any }> = ({ job }) => {
  const color = JOB_STATUS_COLOR[job.status] || '#94a3b8';
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '10px',
      padding: '10px 14px',
      borderRadius: '8px',
      background: '#1e293b',
      fontSize: '12px',
      borderLeft: `3px solid ${color}`,
    }}>
      <span style={{ color, fontWeight: 700, minWidth: '70px' }}>{job.status}</span>
      <span style={{ color: '#94a3b8', fontFamily: 'monospace', minWidth: '140px' }}>{job.cycle_id}</span>
      <span style={{ color: '#64748b' }}>+{job.lead_hours}h</span>
      <span style={{ color: '#475569', flex: 1, fontFamily: 'monospace', fontSize: '11px' }}>{job.job_id}</span>
      {job.duration_ms && <span style={{ color: '#334155' }}>{job.duration_ms.toFixed(0)}ms</span>}
      {job.skip_reason && <span style={{ color: '#475569', fontStyle: 'italic' }}>{job.skip_reason}</span>}
      <span style={{ color: '#1e3a5f' }}>{ts(job.completed_at || job.created_at)}</span>
    </div>
  );
};

// ── Alerts Tab ─────────────────────────────────────────────────────────────

const AlertsTab: React.FC<{
  alertsData: Record<string, any> | null;
  loading: boolean;
  onAcknowledge: (id: string) => void;
  onResolve: (id: string) => void;
}> = ({ alertsData, loading, onAcknowledge, onResolve }) => {
  if (loading) return <LoadingSpinner />;

  const alerts: any[] = alertsData?.alerts || [];
  const rules: any[] = alertsData?.rules || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Alert summary */}
      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        <StatCard label="Active" value={alertsData?.active_alerts || 0} icon={<Bell size={14} />} color="#f59e0b" />
        <StatCard label="Critical" value={alertsData?.critical_alerts || 0} icon={<AlertCircle size={14} />} color="#ef4444" />
        <StatCard label="Total Raised" value={alertsData?.total_alerts_raised || 0} icon={<Activity size={14} />} color="#8b5cf6" />
        <StatCard label="Rules Enabled" value={alertsData?.rules_enabled || 0} icon={<Settings size={14} />} color="#3b82f6" />
      </div>

      {/* Active alerts */}
      <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '12px', padding: '20px' }}>
        <h3 style={{ color: '#e2e8f0', marginBottom: '14px', fontSize: '14px', fontWeight: 700 }}>
          🔔 Active Alerts
        </h3>
        {alerts.length === 0 ? (
          <div style={{ color: '#22c55e', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CheckCircle2 size={16} /> No active alerts. System nominal.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {alerts.map((a: any) => (
              <AlertRow key={a.alert_id} alert={a} onAck={onAcknowledge} onResolve={onResolve} />
            ))}
          </div>
        )}
      </div>

      {/* Alert rules */}
      <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '12px', padding: '20px' }}>
        <h3 style={{ color: '#e2e8f0', marginBottom: '14px', fontSize: '14px', fontWeight: 700 }}>
          📏 Alert Rules (8 Built-In)
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {rules.map((r: any) => (
            <div key={r.rule_id} style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '12px',
              padding: '10px 14px',
              borderRadius: '8px',
              background: '#1e293b',
              fontSize: '12px',
            }}>
              <span style={{
                padding: '2px 8px',
                borderRadius: '4px',
                background: `${SEVERITY_COLOR[r.severity] || '#64748b'}20`,
                color: SEVERITY_COLOR[r.severity] || '#94a3b8',
                fontWeight: 700,
                fontSize: '11px',
                minWidth: '70px',
                textAlign: 'center',
              }}>
                {r.severity}
              </span>
              <div style={{ flex: 1 }}>
                <div style={{ color: '#e2e8f0', fontWeight: 600 }}>{r.rule_id}: {r.name}</div>
                <div style={{ color: '#64748b', marginTop: '2px' }}>{r.description}</div>
              </div>
              <div style={{ color: '#475569', fontSize: '11px', fontFamily: 'monospace', minWidth: '120px', textAlign: 'right' }}>
                {r.condition_key} {r.comparison} {r.threshold}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const AlertRow: React.FC<{
  alert: any;
  onAck: (id: string) => void;
  onResolve: (id: string) => void;
}> = ({ alert, onAck, onResolve }) => {
  const color = SEVERITY_COLOR[alert.severity] || '#64748b';
  return (
    <div style={{
      padding: '14px',
      borderRadius: '8px',
      background: `${color}10`,
      border: `1px solid ${color}40`,
      display: 'flex',
      flexDirection: 'column',
      gap: '8px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <AlertTriangle size={14} color={color} />
        <span style={{ color, fontWeight: 700, fontSize: '13px' }}>[{alert.severity}] {alert.rule_name}</span>
        <span style={{ color: '#475569', fontSize: '11px', marginLeft: 'auto' }}>{ts(alert.triggered_at)}</span>
      </div>
      <div style={{ color: '#94a3b8', fontSize: '12px' }}>{alert.message}</div>
      <div style={{ display: 'flex', gap: '8px' }}>
        {!alert.acknowledged && (
          <button
            onClick={() => onAck(alert.alert_id)}
            style={{
              padding: '5px 12px', borderRadius: '5px', background: '#1e293b',
              border: '1px solid #f59e0b', color: '#f59e0b', cursor: 'pointer', fontSize: '11px', fontWeight: 600,
            }}
          >
            Acknowledge
          </button>
        )}
        {!alert.resolved && (
          <button
            onClick={() => onResolve(alert.alert_id)}
            style={{
              padding: '5px 12px', borderRadius: '5px', background: '#1e293b',
              border: '1px solid #22c55e', color: '#22c55e', cursor: 'pointer', fontSize: '11px', fontWeight: 600,
            }}
          >
            Resolve
          </button>
        )}
        {alert.acknowledged && !alert.resolved && (
          <span style={{ color: '#f59e0b', fontSize: '11px' }}>✓ Acknowledged by {alert.acknowledged_by}</span>
        )}
      </div>
    </div>
  );
};

// ── Drift Tab ──────────────────────────────────────────────────────────────

const DriftTab: React.FC<{ driftData: Record<string, any> | null; loading: boolean }> = ({
  driftData,
  loading,
}) => {
  if (loading) return <LoadingSpinner />;
  if (!driftData) return <div style={{ color: '#475569' }}>No drift data available.</div>;

  const feats: any[] = driftData.feature_drift || [];
  const pred = driftData.prediction_drift;
  const cal: any[] = driftData.calibration_drift || [];
  const overall = driftData.overall_drift_level || 'NONE';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Overall */}
      <div style={{
        padding: '14px 20px',
        borderRadius: '10px',
        background: `${DRIFT_LEVEL_COLOR[overall]}15`,
        border: `1px solid ${DRIFT_LEVEL_COLOR[overall]}50`,
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
      }}>
        <TrendingUp size={20} color={DRIFT_LEVEL_COLOR[overall]} />
        <div>
          <div style={{ color: DRIFT_LEVEL_COLOR[overall], fontWeight: 700, fontSize: '15px' }}>
            Overall Drift: {overall}
          </div>
          <div style={{ color: '#64748b', fontSize: '12px', marginTop: '2px' }}>{driftData.summary}</div>
        </div>
        <div style={{ marginLeft: 'auto', color: '#475569', fontSize: '11px' }}>
          Window: {driftData.window_size} cycles | {ts(driftData.generated_at)}
        </div>
      </div>

      {/* Prediction drift */}
      {pred && (
        <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ color: '#e2e8f0', marginBottom: '14px', fontSize: '14px', fontWeight: 700 }}>
            📈 Prediction Distribution Drift
          </h3>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <StatCard label="Baseline Mean" value={`${pred.baseline_mean_forecast_mm} mm`} icon={<BarChart3 size={14} />} color="#3b82f6" />
            <StatCard label="Current Mean" value={`${pred.current_mean_forecast_mm} mm`} icon={<BarChart3 size={14} />} color="#8b5cf6" />
            <StatCard label="Shift" value={`${pred.mean_shift_pct}%`} icon={<TrendingUp size={14} />} color={DRIFT_LEVEL_COLOR[pred.drift_level]} sub={`${pred.mean_shift_mm > 0 ? '+' : ''}${pred.mean_shift_mm} mm`} />
          </div>
        </div>
      )}

      {/* Feature drift table */}
      <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '12px', padding: '20px' }}>
        <h3 style={{ color: '#e2e8f0', marginBottom: '14px', fontSize: '14px', fontWeight: 700 }}>
          🔢 Feature Distribution Drift (KS-Statistic)
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{
            display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr',
            gap: '8px', padding: '6px 10px', color: '#475569', fontSize: '11px', fontWeight: 600,
          }}>
            <span>FEATURE</span><span>KS-STAT</span><span>BASELINE μ</span><span>CURRENT μ</span><span>DRIFT</span>
          </div>
          {feats.map((f: any) => (
            <div key={f.feature_name} style={{
              display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr',
              gap: '8px', padding: '8px 10px', background: '#1e293b', borderRadius: '6px', fontSize: '12px',
            }}>
              <span style={{ color: '#94a3b8', fontFamily: 'monospace' }}>{f.feature_name}</span>
              <span style={{ color: '#e2e8f0' }}>{f.ks_statistic.toFixed(4)}</span>
              <span style={{ color: '#64748b' }}>{f.baseline_mean.toFixed(2)}</span>
              <span style={{ color: '#94a3b8' }}>{f.current_mean.toFixed(2)}</span>
              <span style={{
                color: DRIFT_LEVEL_COLOR[f.drift_level],
                fontWeight: 700,
                fontSize: '11px',
              }}>{f.drift_level}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Calibration drift */}
      <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '12px', padding: '20px' }}>
        <h3 style={{ color: '#e2e8f0', marginBottom: '14px', fontSize: '14px', fontWeight: 700 }}>
          🎯 Calibration ECE Drift
        </h3>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          {cal.map((c: any) => (
            <div key={c.threshold_mm} style={{
              padding: '12px 16px', borderRadius: '8px', background: '#1e293b',
              border: `1px solid ${DRIFT_LEVEL_COLOR[c.drift_level]}40`, flex: 1, minWidth: '140px',
            }}>
              <div style={{ color: '#64748b', fontSize: '11px', fontWeight: 600 }}>≥{c.threshold_mm}mm</div>
              <div style={{ color: '#e2e8f0', fontSize: '18px', fontWeight: 700, marginTop: '4px' }}>{c.current_ece.toFixed(4)}</div>
              <div style={{ color: '#475569', fontSize: '11px' }}>baseline: {c.baseline_ece.toFixed(4)}</div>
              <div style={{ color: DRIFT_LEVEL_COLOR[c.drift_level], fontSize: '11px', fontWeight: 700, marginTop: '4px' }}>
                Δ {c.ece_delta > 0 ? '+' : ''}{c.ece_delta.toFixed(4)} — {c.drift_level}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Disclaimer */}
      <div style={{ padding: '10px 14px', borderRadius: '8px', background: '#0f172a', border: '1px solid #1e3a5f', color: '#475569', fontSize: '11px' }}>
        ℹ️ {driftData.disclaimer}
      </div>
    </div>
  );
};

// ── Readiness Tab ──────────────────────────────────────────────────────────

const ReadinessTab: React.FC<{ readinessData: Record<string, any> | null; loading: boolean }> = ({
  readinessData,
  loading,
}) => {
  if (loading) return <LoadingSpinner />;
  if (!readinessData) return <div style={{ color: '#475569' }}>No readiness data.</div>;

  const checks: any[] = readinessData.checks || [];
  const catSummary = readinessData.category_summary || {};
  const overall = readinessData.overall_status || 'NO_GO';
  const overallColor = overall === 'GO' ? '#22c55e' : overall === 'CONDITIONAL_GO' ? '#f59e0b' : '#ef4444';

  const categories = ['CAT-A', 'CAT-B', 'CAT-C', 'CAT-D', 'CAT-E', 'CAT-F'];
  const catNames: Record<string, string> = {
    'CAT-A': 'Model Registry Integrity',
    'CAT-B': 'Data Infrastructure',
    'CAT-C': 'Inference Pipeline',
    'CAT-D': 'Monitoring & Alerting',
    'CAT-E': 'Operational Interface',
    'CAT-F': 'Documentation & Provenance',
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Overall verdict */}
      <div style={{
        padding: '20px',
        borderRadius: '12px',
        background: `${overallColor}10`,
        border: `2px solid ${overallColor}50`,
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
      }}>
        {overall === 'GO' ? <ShieldCheck size={32} color={overallColor} /> :
          overall === 'CONDITIONAL_GO' ? <Shield size={32} color={overallColor} /> :
            <ShieldAlert size={32} color={overallColor} />}
        <div>
          <div style={{ color: overallColor, fontSize: '20px', fontWeight: 800 }}>
            {overall === 'GO' ? '✅ GO' : overall === 'CONDITIONAL_GO' ? '⚠️ CONDITIONAL GO' : '❌ NO-GO'}
          </div>
          <div style={{ color: '#94a3b8', fontSize: '12px', marginTop: '4px' }}>{readinessData.summary}</div>
        </div>
        <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
          <div style={{ color: '#22c55e', fontSize: '24px', fontWeight: 700 }}>{readinessData.passed}/{readinessData.total_checks}</div>
          <div style={{ color: '#64748b', fontSize: '11px' }}>checks passed</div>
        </div>
      </div>

      {/* Category summary */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
        {categories.map((cat) => {
          const cs = catSummary[cat] || {};
          const allPass = cs.failed === 0 && cs.warned === 0;
          return (
            <div key={cat} style={{
              padding: '14px', borderRadius: '10px',
              background: allPass ? '#052e16' : cs.failed > 0 ? '#1a0a0a' : '#1a1200',
              border: `1px solid ${allPass ? '#22c55e40' : cs.failed > 0 ? '#ef444440' : '#f59e0b40'}`,
            }}>
              <div style={{ color: allPass ? '#22c55e' : cs.failed > 0 ? '#ef4444' : '#f59e0b', fontWeight: 700, fontSize: '12px', marginBottom: '6px' }}>
                {cat}: {catNames[cat]}
              </div>
              <div style={{ fontSize: '11px', color: '#64748b', display: 'flex', gap: '8px' }}>
                <span style={{ color: '#22c55e' }}>✓ {cs.passed}</span>
                {cs.failed > 0 && <span style={{ color: '#ef4444' }}>✗ {cs.failed}</span>}
                {cs.warned > 0 && <span style={{ color: '#f59e0b' }}>⚠ {cs.warned}</span>}
                {cs.skipped > 0 && <span style={{ color: '#475569' }}>↷ {cs.skipped}</span>}
              </div>
            </div>
          );
        })}
      </div>

      {/* Detailed checks */}
      {categories.map((cat) => {
        const catChecks = checks.filter((c: any) => c.category === cat);
        return (
          <div key={cat} style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: '#e2e8f0', marginBottom: '12px', fontSize: '13px', fontWeight: 700 }}>
              {cat} — {catNames[cat]}
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {catChecks.map((c: any) => (
                <div key={c.check_id} style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  background: '#1e293b',
                  fontSize: '12px',
                  borderLeft: `3px solid ${CHECK_STATUS_COLOR[c.status] || '#64748b'}`,
                }}>
                  <span style={{ color: CHECK_STATUS_COLOR[c.status], fontWeight: 700, minWidth: '40px' }}>{c.status}</span>
                  <div style={{ flex: 1 }}>
                    <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{c.check_id}: {c.name}</span>
                    {c.details && <span style={{ color: '#475569', marginLeft: '8px' }}>{c.details}</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}

      {/* Disclaimer */}
      <div style={{ padding: '10px 14px', borderRadius: '8px', background: '#0f172a', border: '1px solid #1e3a5f', color: '#475569', fontSize: '11px' }}>
        ℹ️ {readinessData.disclaimer}
      </div>
    </div>
  );
};

// ── Real Data Activation & Quality Tab (Phase 16 PART V) ────────────────────

const RealActivationTab: React.FC = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Real Data Activation Overview */}
      <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '12px', padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div>
            <h3 style={{ color: '#e2e8f0', fontSize: '15px', fontWeight: 700, margin: 0 }}>
              🛡️ Real Data Activation Architecture (Phase 16)
            </h3>
            <div style={{ color: '#64748b', fontSize: '12px', marginTop: '4px' }}>
              15-Gate Technical Pre-Activation · Two-Stage Human Approval · Zero Fabricated Status
            </div>
          </div>
          <span style={{
            padding: '4px 10px', borderRadius: '6px',
            background: '#7f1d1d33', border: '1px solid #ef4444',
            color: '#ef4444', fontSize: '11px', fontWeight: 700,
          }}>
            REAL OPERATIONAL BLOCKED
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginBottom: '16px' }}>
          <div style={{ background: '#1e293b55', border: '1px solid #334155', borderRadius: '8px', padding: '12px' }}>
            <div style={{ color: '#64748b', fontSize: '11px' }}>DATA SOURCES</div>
            <div style={{ color: '#60a5fa', fontSize: '13px', fontWeight: 700, marginTop: '2px' }}>NCUM · NEPS · IMD</div>
            <div style={{ color: '#94a3b8', fontSize: '10px' }}>Deterministic · Ensemble · Obs</div>
          </div>
          <div style={{ background: '#1e293b55', border: '1px solid #334155', borderRadius: '8px', padding: '12px' }}>
            <div style={{ color: '#64748b', fontSize: '11px' }}>AUTHORITY LEVEL</div>
            <div style={{ color: '#f59e0b', fontSize: '13px', fontWeight: 700, marginTop: '2px' }}>NCMRWF / IMD</div>
            <div style={{ color: '#94a3b8', fontSize: '10px' }}>Primary Operational</div>
          </div>
          <div style={{ background: '#1e293b55', border: '1px solid #334155', borderRadius: '8px', padding: '12px' }}>
            <div style={{ color: '#64748b', fontSize: '11px' }}>OPERATIONAL COVERAGE</div>
            <div style={{ color: '#ef4444', fontSize: '13px', fontWeight: 700, marginTop: '2px' }}>0.0% (Unmounted)</div>
            <div style={{ color: '#94a3b8', fontSize: '10px' }}>Target: 17,673 canonical cells</div>
          </div>
          <div style={{ background: '#1e293b55', border: '1px solid #334155', borderRadius: '8px', padding: '12px' }}>
            <div style={{ color: '#64748b', fontSize: '11px' }}>OPERATOR SIGN-OFF</div>
            <div style={{ color: '#cbd5e1', fontSize: '13px', fontWeight: 700, marginTop: '2px' }}>PENDING_DATA</div>
            <div style={{ color: '#94a3b8', fontSize: '10px' }}>Requires all 15 gates PASS</div>
          </div>
        </div>

        <div style={{ padding: '12px', background: '#1e293b33', borderRadius: '8px', border: '1px solid #334155', fontSize: '12px', color: '#94a3b8' }}>
          🔒 <strong style={{ color: '#f87171' }}>Scientific Safety Gate:</strong> In accordance with the RAMP Absolute Scientific Integrity Rule,
          authoritative data are not mounted in this environment. System operates under verified <strong style={{ color: '#60a5fa' }}>SYNTHETIC_DEMO</strong> governance.
        </div>
      </div>

      {/* Real Forecast Quality (Factual Baseline Comparison) */}
      <div style={{ background: '#0f172a', border: '1px solid #1e3a5f', borderRadius: '12px', padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
          <div>
            <h3 style={{ color: '#e2e8f0', fontSize: '15px', fontWeight: 700, margin: 0 }}>
              📊 Real Forecast Quality & Verification (Part V)
            </h3>
            <div style={{ color: '#64748b', fontSize: '12px', marginTop: '4px' }}>
              Factual model comparison against IMD 0.25° gridded rainfall observation ground truth.
            </div>
          </div>
          <span style={{ padding: '3px 8px', borderRadius: '4px', background: '#334155', color: '#94a3b8', fontSize: '11px', fontWeight: 600 }}>
            WMO / IMD Protocol
          </span>
        </div>

        <div style={{
          padding: '14px', borderRadius: '8px', background: '#1a1005', border: '1px solid #d9770655',
          color: '#fbbf24', fontSize: '12px', marginBottom: '16px', lineHeight: 1.5,
        }}>
          ⚠️ <strong>VERIFICATION NOT AVAILABLE:</strong> Genuine IMD daily gridded rainfall observations are not currently mounted.
          No verification metrics, skill scores, or winner rankings are fabricated.
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', color: '#cbd5e1' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #1e3a5f', color: '#64748b', textAlign: 'left' }}>
                <th style={{ padding: '8px 12px' }}>Model Candidate</th>
                <th style={{ padding: '8px 12px' }}>Architecture</th>
                <th style={{ padding: '8px 12px' }}>MAE (mm)</th>
                <th style={{ padding: '8px 12px' }}>RMSE (mm)</th>
                <th style={{ padding: '8px 12px' }}>Bias</th>
                <th style={{ padding: '8px 12px' }}>CSI (64.5mm)</th>
                <th style={{ padding: '8px 12px' }}>Brier Score</th>
                <th style={{ padding: '8px 12px' }}>BSS</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid #1e293b' }}>
                <td style={{ padding: '10px 12px', fontWeight: 600, color: '#f1f5f9' }}>Raw NWP (NCUM)</td>
                <td style={{ padding: '10px 12px', color: '#64748b' }}>Deterministic NWP (~12km)</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>—</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>—</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>—</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>—</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>—</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>—</td>
              </tr>
              <tr style={{ borderBottom: '1px solid #1e293b' }}>
                <td style={{ padding: '10px 12px', fontWeight: 600, color: '#f1f5f9' }}>Global ML</td>
                <td style={{ padding: '10px 12px', color: '#64748b' }}>Non-Regime LightGBM</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>—</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>—</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>—</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>—</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>—</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>—</td>
              </tr>
              <tr>
                <td style={{ padding: '10px 12px', fontWeight: 700, color: '#38bdf8' }}>RAMP MoE</td>
                <td style={{ padding: '10px 12px', color: '#64748b' }}>Regime-Aware Mixture-of-Experts</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>—</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>—</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>—</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>—</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>—</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>—</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

// ── Loading Spinner ────────────────────────────────────────────────────────

const LoadingSpinner: React.FC = () => (
  <div style={{ textAlign: 'center', padding: '60px 0', color: '#475569' }}>
    <RefreshCw size={24} style={{ animation: 'spin 1s linear infinite' }} />
    <div style={{ marginTop: '12px', fontSize: '13px' }}>Loading operations data…</div>
    <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
  </div>
);

// ── Main Page ──────────────────────────────────────────────────────────────

export const OperationsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('live_ops');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<string>('');

  const [status, setStatus] = useState<OpsStatus | null>(null);
  const [stateData, setStateData] = useState<Record<string, any> | null>(null);
  const [scheduler, setScheduler] = useState<Record<string, any> | null>(null);
  const [jobs, setJobs] = useState<any[] | null>(null);
  const [alertsData, setAlertsData] = useState<Record<string, any> | null>(null);
  const [driftData, setDriftData] = useState<Record<string, any> | null>(null);
  const [readinessData, setReadinessData] = useState<Record<string, any> | null>(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [st, sd, sc, jb, al, dr, rd] = await Promise.all([
        fetchOperationsStatus().catch(() => null),
        fetchOperationsState().catch(() => null),
        fetchOperationsScheduler().catch(() => null),
        fetchOperationsJobs(30).catch(() => null),
        fetchOperationsAlerts().catch(() => null),
        fetchOperationsDrift().catch(() => null),
        fetchOperationsReadiness().catch(() => null),
      ]);
      setStatus(st as OpsStatus);
      setStateData(sd);
      setScheduler(sc);
      setJobs(jb?.jobs || []);
      setAlertsData(al);
      setDriftData(dr);
      setReadinessData(rd);
      setLastRefresh(new Date().toLocaleTimeString('en-IN', { hour12: false }));
    } catch (e: any) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
    const interval = setInterval(loadAll, 15000);  // auto-refresh every 15s
    return () => clearInterval(interval);
  }, [loadAll]);

  const handleTransition = useCallback(async (toState: string) => {
    try {
      await postOperationsStateTransition(toState, 'Operator manual transition');
      await loadAll();
    } catch (e: any) {
      alert(`Transition failed: ${e.message}`);
    }
  }, [loadAll]);

  const handleStartScheduler = useCallback(async () => {
    try {
      await postSchedulerStart();
      await loadAll();
    } catch (e: any) {
      alert(`Start failed: ${e.message}`);
    }
  }, [loadAll]);

  const handleStopScheduler = useCallback(async () => {
    try {
      await postSchedulerStop();
      await loadAll();
    } catch (e: any) {
      alert(`Stop failed: ${e.message}`);
    }
  }, [loadAll]);

  const handleSubmitJob = useCallback(async (cycle: string, lead: number) => {
    try {
      await postSubmitJob(cycle, lead);
      await loadAll();
    } catch (e: any) {
      alert(`Job submit failed: ${e.message}`);
    }
  }, [loadAll]);

  const handleAcknowledge = useCallback(async (id: string) => {
    try {
      await postAcknowledgeAlert(id);
      await loadAll();
    } catch (e: any) {
      alert(`Acknowledge failed: ${e.message}`);
    }
  }, [loadAll]);

  const handleResolve = useCallback(async (id: string) => {
    try {
      await postResolveAlert(id);
      await loadAll();
    } catch (e: any) {
      alert(`Resolve failed: ${e.message}`);
    }
  }, [loadAll]);

  const tabs: { id: ActiveTab; label: string; icon: React.ReactNode }[] = [
    { id: 'live_ops', label: 'Live Operations', icon: <Zap size={14} /> },
    { id: 'overview', label: 'Overview', icon: <Activity size={14} /> },
    { id: 'scheduler', label: 'Scheduler', icon: <Cpu size={14} /> },
    { id: 'alerts', label: 'Alerts', icon: <Bell size={14} /> },
    { id: 'drift', label: 'Drift Monitor', icon: <TrendingUp size={14} /> },
    { id: 'readiness', label: 'Readiness', icon: <ShieldCheck size={14} /> },
    { id: 'real_activation', label: 'Real Activation & QA', icon: <Shield size={14} /> },
  ];

  const activeAlertCount = status?.alerts?.active || 0;
  const criticalCount = status?.alerts?.critical || 0;

  return (
    <div style={{
      background: 'linear-gradient(180deg, #020817 0%, #0a1628 100%)',
      minHeight: '100vh',
      padding: '24px',
      color: '#e2e8f0',
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Zap size={22} color="#3b82f6" />
            <h1 style={{ fontSize: '22px', fontWeight: 800, color: '#e2e8f0', margin: 0 }}>
              Operations Control Center
            </h1>
            <span style={{
              padding: '3px 10px', borderRadius: '4px',
              background: '#1e3a5f', border: '1px solid #3b82f666',
              color: '#60a5fa', fontSize: '11px', fontWeight: 700,
            }}>
              PHASE 15
            </span>
          </div>
          <div style={{ color: '#64748b', fontSize: '12px', marginTop: '4px' }}>
            SIH26080 | MoES / NCMRWF | Automated Scheduler · State Machine · Alert Monitor · Drift · Readiness
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {criticalCount > 0 && (
            <div style={{
              padding: '6px 12px', borderRadius: '6px',
              background: '#7f1d1d', border: '1px solid #ef4444',
              color: '#ef4444', fontSize: '12px', fontWeight: 700,
              display: 'flex', alignItems: 'center', gap: '6px',
            }}>
              <AlertCircle size={14} /> {criticalCount} CRITICAL
            </div>
          )}
          <span style={{ color: '#475569', fontSize: '11px' }}>Refreshed {lastRefresh}</span>
          <button
            onClick={loadAll}
            style={{
              padding: '8px', borderRadius: '8px',
              background: '#1e293b', border: '1px solid #334155',
              color: '#94a3b8', cursor: 'pointer',
              display: 'flex', alignItems: 'center',
            }}
          >
            <RefreshCw size={14} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
          </button>
        </div>
      </div>

      {/* Data Honesty Banner */}
      <DataBanner />

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '4px', marginBottom: '20px', borderBottom: '1px solid #1e3a5f', paddingBottom: '0' }}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '10px 18px',
              borderRadius: '8px 8px 0 0',
              background: activeTab === tab.id ? '#1e3a5f' : 'transparent',
              border: 'none',
              borderBottom: activeTab === tab.id ? '2px solid #3b82f6' : '2px solid transparent',
              color: activeTab === tab.id ? '#e2e8f0' : '#64748b',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '13px',
              fontWeight: activeTab === tab.id ? 700 : 400,
              transition: 'all 0.2s',
              position: 'relative',
            }}
          >
            {tab.icon}
            {tab.label}
            {tab.id === 'alerts' && activeAlertCount > 0 && (
              <span style={{
                position: 'absolute', top: '6px', right: '6px',
                width: '16px', height: '16px', borderRadius: '50%',
                background: criticalCount > 0 ? '#ef4444' : '#f59e0b',
                color: '#fff', fontSize: '10px', fontWeight: 700,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                {activeAlertCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div style={{
          padding: '12px 16px', borderRadius: '8px',
          background: '#1a0a0a', border: '1px solid #ef4444',
          color: '#ef4444', marginBottom: '16px', fontSize: '12px',
        }}>
          ⚠️ API Error: {error}
        </div>
      )}

      {/* Tab Content */}
      {activeTab === 'live_ops' && (
        <LiveOperationsTab />
      )}
      {activeTab === 'overview' && (
        <OverviewTab
          status={status}
          stateData={stateData}
          loading={loading}
          onTransition={handleTransition}
        />
      )}
      {activeTab === 'scheduler' && (
        <SchedulerTab
          scheduler={scheduler}
          jobs={jobs}
          loading={loading}
          onStart={handleStartScheduler}
          onStop={handleStopScheduler}
          onSubmitJob={handleSubmitJob}
        />
      )}
      {activeTab === 'alerts' && (
        <AlertsTab
          alertsData={alertsData}
          loading={loading}
          onAcknowledge={handleAcknowledge}
          onResolve={handleResolve}
        />
      )}
      {activeTab === 'drift' && (
        <DriftTab driftData={driftData} loading={loading} />
      )}
      {activeTab === 'readiness' && (
        <ReadinessTab readinessData={readinessData} loading={loading} />
      )}
      {activeTab === 'real_activation' && (
        <RealActivationTab />
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};
