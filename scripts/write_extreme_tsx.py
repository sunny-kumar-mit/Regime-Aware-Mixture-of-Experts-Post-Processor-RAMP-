#!/usr/bin/env python3
"""
Script to write ExtremeRainfall.tsx for Phase 7.
Run from project root: python scripts/write_extreme_tsx.py
"""

import pathlib

CONTENT = r'''/**
 * Phase 7 Extreme Rainfall Probability Engine Dashboard
 * SIH26080 | RAMP - Regime-Aware Mixture-of-Experts Post-Processor
 * MoES / NCMRWF
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  fetchExtremeStatus,
  fetchExtremeModels,
  fetchExtremeDemo,
  fetchExtremeMetrics,
  fetchExtremeCalibration,
  fetchExtremeBrierScores,
  fetchExtremePRCurves,
  fetchExtremeFeatureImportance,
  fetchExtremeMonotonicity,
} from '../api/client';
import type {
  ExtremeEngineStatus,
  ExtremeModelMeta,
  ExtremePredictionRecord,
  ExtremeMetric,
  CalibrationBin,
  BrierScoreRow,
  PRCurveDataPoint,
  ExtremeFeatureImportance,
  MonotonicityReport,
} from '../types/api';

const IMD_COLOURS: Record<string, { bg: string; border: string; text: string; glow: string }> = {
  NONE:   { bg: '#1e293b', border: '#3b82f6', text: '#93c5fd', glow: '#3b82f640' },
  YELLOW: { bg: '#1c1700', border: '#f59e0b', text: '#fcd34d', glow: '#f59e0b40' },
  ORANGE: { bg: '#1c0e00', border: '#f97316', text: '#fdba74', glow: '#f9731640' },
  RED:    { bg: '#1c0000', border: '#dc2626', text: '#fca5a5', glow: '#dc262640' },
};

const THRESHOLD_META = [
  { mm: 0.1,   label: 'Occurrence', sub: '> 0.1 mm',   warning: 'NONE',   key: 'p_trace'      },
  { mm: 64.5,  label: 'Heavy',      sub: '> 64.5 mm',  warning: 'YELLOW', key: 'p_heavy'      },
  { mm: 115.6, label: 'Very Heavy', sub: '> 115.6 mm', warning: 'ORANGE', key: 'p_very_heavy' },
  { mm: 204.5, label: 'Extreme',    sub: '> 204.5 mm', warning: 'RED',    key: 'p_extreme'    },
];

const RISK_COLOURS: Record<string, { bg: string; text: string }> = {
  LOW:      { bg: '#0f3460', text: '#93c5fd' },
  MODERATE: { bg: '#14532d', text: '#86efac' },
  HIGH:     { bg: '#713f12', text: '#fcd34d' },
  SEVERE:   { bg: '#7c2d12', text: '#fdba74' },
  EXTREME:  { bg: '#450a0a', text: '#fca5a5' },
};

const SyntheticBanner: React.FC = () => (
  <div className="mb-6 flex items-center gap-3 rounded-xl border border-amber-500/40 bg-amber-900/20 px-5 py-3">
    <span className="text-xl">&#9888;&#65039;</span>
    <div>
      <p className="text-sm font-semibold text-amber-400">SYNTHETIC DEMONSTRATION ONLY</p>
      <p className="text-xs text-amber-300/70">
        REAL TRAINING DATA: NOT AVAILABLE. All probability outputs are illustrative only.
        Engine trained on synthetic data for demonstration purposes.
      </p>
    </div>
  </div>
);

const SectionHeader: React.FC<{ title: string; subtitle?: string; badge?: string }> = ({ title, subtitle, badge }) => (
  <div className="mb-6 flex items-start justify-between gap-4">
    <div>
      <h2 className="text-xl font-bold text-white">{title}</h2>
      {subtitle && <p className="mt-1 text-sm text-slate-400">{subtitle}</p>}
    </div>
    {badge && (
      <span className="shrink-0 rounded-full border border-cyan-500/40 bg-cyan-900/30 px-3 py-1 text-xs font-semibold text-cyan-400">
        {badge}
      </span>
    )}
  </div>
);

const MetricCard: React.FC<{ label: string; value: string | number; sub?: string; colour?: string }> = ({
  label, value, sub, colour = '#38bdf8'
}) => (
  <div className="rounded-xl border border-slate-700 bg-slate-800/60 p-4">
    <p className="mb-1 text-xs font-medium uppercase tracking-widest text-slate-400">{label}</p>
    <p className="text-2xl font-bold" style={{ color: colour }}>{value}</p>
    {sub && <p className="mt-0.5 text-xs text-slate-500">{sub}</p>}
  </div>
);

const Spinner: React.FC<{ label?: string }> = ({ label = 'Loading...' }) => (
  <div className="flex h-40 items-center justify-center gap-3 text-slate-400">
    <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
    <span className="text-sm">{label}</span>
  </div>
);

const ErrCard: React.FC<{ msg: string }> = ({ msg }) => (
  <div className="flex gap-3 rounded-xl border border-red-500/40 bg-red-900/20 px-5 py-4 text-sm text-red-300">
    <span>{msg}</span>
  </div>
);

// ---- Hero ----

const HeroSection: React.FC<{ status: ExtremeEngineStatus | null; loading: boolean }> = ({ status, loading }) => {
  if (loading) return <Spinner label="Loading engine status..." />;
  const cards = [
    { label: 'Engine Version', value: status?.engine_version ?? '-',    colour: '#38bdf8' },
    { label: 'RAMP Source',    value: status?.ramp_source_version ?? '-', colour: '#a78bfa' },
    { label: 'Thresholds',     value: status?.n_thresholds ?? 4,          colour: '#34d399' },
    { label: 'Calibration',    value: status?.calibration_applied ? 'Platt Sigmoid' : 'None', colour: '#fb923c' },
    { label: 'Monotonicity',   value: status?.monotonicity_enforced ? 'PAV Enforced' : 'N/A', colour: '#4ade80' },
    { label: 'Operational',    value: status?.operational ? 'Ready' : 'Demo Mode',
      colour: status?.operational ? '#4ade80' : '#f87171' },
  ];
  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <div className={`h-3 w-3 rounded-full ${status?.operational ? 'animate-pulse bg-green-400' : 'bg-amber-400'}`} />
          <span className="text-sm font-semibold text-slate-300">
            {status?.operational ? 'Engine Operational' : 'Synthetic Demo Mode'}
          </span>
        </div>
        <span className="rounded-full bg-slate-700 px-3 py-0.5 text-xs text-slate-300">
          Data Mode: {status?.data_mode ?? 'SYNTHETIC_DEMO'}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {cards.map((c) => <MetricCard key={c.label} {...c} />)}
      </div>
      {status?.warnings && status.warnings.length > 0 && (
        <div className="mt-4 space-y-2">
          {status.warnings.map((w, i) => (
            <div key={i} className="rounded-lg border border-amber-600/30 bg-amber-900/20 px-4 py-2 text-xs text-amber-300">{w}</div>
          ))}
        </div>
      )}
    </div>
  );
};

// ---- Interactive Predictor ----

const InteractivePredictor: React.FC = () => {
  const [rampPred, setRampPred] = useState(85);
  const [regime, setRegime] = useState('ACTIVE_MONSOON');
  const [lead, setLead] = useState(48);
  const [result, setResult] = useState<ExtremePredictionRecord | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const REGIMES = ['ACTIVE_MONSOON','BREAK_MONSOON','LOW_DEPRESSION','COASTAL','OROGRAPHIC','WESTERN_DISTURBANCE','TRANSITION_OTHER'];

  const run = useCallback(async () => {
    setLoading(true); setError(null);
    try { setResult(await fetchExtremeDemo(rampPred, regime, lead)); }
    catch (e) { setError(String(e)); }
    finally { setLoading(false); }
  }, [rampPred, regime, lead]);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { run(); }, []);

  const probs = result ? [result.p_trace, result.p_heavy, result.p_very_heavy, result.p_extreme] : [0,0,0,0];

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-800/50 p-6">
      <SectionHeader title="Interactive Probability Predictor"
        subtitle="Adjust RAMP forecast and regime - live exceedance probability prediction"
        badge="Live Demo" />
      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-400">
            RAMP Prediction: <strong className="text-white">{rampPred} mm</strong>
          </label>
          <input type="range" min={0} max={250} step={5} value={rampPred}
            onChange={(e) => setRampPred(Number(e.target.value))} className="w-full accent-cyan-500" />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-400">Atmospheric Regime</label>
          <select value={regime} onChange={(e) => setRegime(e.target.value)}
            className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white">
            {REGIMES.map((r) => <option key={r} value={r}>{r.replace(/_/g,' ')}</option>)}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-400">
            Lead Time: <strong className="text-white">{lead}h</strong>
          </label>
          <input type="range" min={24} max={120} step={24} value={lead}
            onChange={(e) => setLead(Number(e.target.value))} className="w-full accent-purple-500" />
        </div>
      </div>
      <button onClick={run} disabled={loading}
        className="mb-6 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 px-6 py-2.5 text-sm font-bold text-white shadow-lg transition hover:brightness-110 disabled:opacity-50">
        {loading ? 'Computing...' : 'Run Prediction'}
      </button>
      {error && <ErrCard msg={error} />}
      {result && (
        <>
          <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {THRESHOLD_META.map((t, i) => {
              const pct = Math.round(probs[i] * 100);
              const col = IMD_COLOURS[t.warning];
              return (
                <div key={t.mm} className="overflow-hidden rounded-xl border p-5 text-center"
                  style={{ borderColor: col.border, backgroundColor: col.bg, boxShadow: `0 0 20px ${col.glow}` }}>
                  <p className="mb-1 text-xs font-semibold uppercase tracking-widest" style={{ color: col.text }}>{t.label}</p>
                  <p className="text-xs opacity-60" style={{ color: col.text }}>{t.sub}</p>
                  <div className="my-3 text-5xl font-black" style={{ color: col.text }}>
                    {pct}<span className="text-2xl">%</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-slate-700">
                    <div className="h-full rounded-full transition-all duration-700"
                      style={{ width: `${pct}%`, backgroundColor: col.border }} />
                  </div>
                  <span className="mt-2 inline-block rounded-full px-2 py-0.5 text-xs font-bold"
                    style={{ backgroundColor: col.border + '33', color: col.text }}>
                    {t.warning === 'NONE' ? 'No Warning' : `${t.warning} ALERT`}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            {(() => {
              const rc = RISK_COLOURS[result.risk_category] ?? RISK_COLOURS.LOW;
              return (<>
                <div className="rounded-xl border border-slate-600 p-4 text-center" style={{ backgroundColor: rc.bg }}>
                  <p className="text-xs font-medium text-slate-400">Risk Category</p>
                  <p className="mt-1 text-2xl font-black" style={{ color: rc.text }}>{result.risk_category}</p>
                </div>
                <div className="rounded-xl border border-slate-600 bg-slate-800 p-4 text-center">
                  <p className="text-xs font-medium text-slate-400">Composite Risk Index</p>
                  <p className="mt-1 text-2xl font-black text-amber-400">{(result.composite_risk_index * 100).toFixed(1)}%</p>
                </div>
                <div className="rounded-xl border border-slate-600 bg-slate-800 p-4 text-center">
                  <p className="text-xs font-medium text-slate-400">IMD Warning</p>
                  <p className="mt-1 text-2xl font-black"
                     style={{ color: IMD_COLOURS[result.imd_warning_recommendation]?.text ?? '#94a3b8' }}>
                    {result.imd_warning_recommendation}
                  </p>
                </div>
              </>);
            })()}
          </div>
          <div className="mt-4">
            <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold border
              ${result.monotonicity_satisfied
                ? 'bg-green-900/40 text-green-400 border-green-600/40'
                : 'bg-red-900/40 text-red-400 border-red-600/40'}`}>
              Monotonicity {result.monotonicity_satisfied ? 'Satisfied' : 'Violated'}
              {result.monotonicity_corrections_applied > 0 && ` (${result.monotonicity_corrections_applied} PAV corrections)`}
            </span>
          </div>
        </>
      )}
    </div>
  );
};

// ---- Monotonicity ----

const MonotonicitySection: React.FC = () => {
  const [report, setReport] = useState<MonotonicityReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchExtremeMonotonicity(500).then(setReport).catch((e) => setError(String(e))).finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner label="Running monotonicity verification..." />;
  if (error) return <ErrCard msg={error} />;
  if (!report) return null;

  const steps = [
    { sub: 'P(R > 0.1)', colour: '#3b82f6' },
    { sub: 'P(R > 64.5)', colour: '#f59e0b' },
    { sub: 'P(R > 115.6)', colour: '#f97316' },
    { sub: 'P(R > 204.5)', colour: '#dc2626' },
  ];

  return (
    <div>
      <SectionHeader title="Monotonicity Invariant Verification"
        subtitle={report.monotonicity_invariant}
        badge={report.invariant_satisfied ? 'GUARANTEED' : 'VIOLATED'} />
      <div className="mb-6 flex items-center justify-center gap-0 overflow-x-auto py-4">
        {steps.map((s, i) => (
          <React.Fragment key={i}>
            <div className="flex min-w-24 flex-col items-center gap-1">
              <div className="flex h-14 w-14 items-center justify-center rounded-full text-lg font-black text-white"
                style={{ backgroundColor: s.colour + '33', border: `2px solid ${s.colour}` }}>
                P{i + 1}
              </div>
              <p className="text-center text-xs text-slate-400">{s.sub}</p>
            </div>
            {i < steps.length - 1 && (
              <div className="flex flex-col items-center px-2">
                <span className="text-lg font-bold text-green-400">&ge;</span>
                <span className="text-xs text-slate-500">always</span>
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Algorithm" value={report.reconciliation_algorithm} colour="#38bdf8" />
        <MetricCard label="Violation Rate Before"
          value={`${(report.violation_rate_before_reconciliation * 100).toFixed(1)}%`}
          sub="Before PAV" colour="#f87171" />
        <MetricCard label="Violation Rate After"
          value={`${(report.violation_rate_after_reconciliation * 100).toFixed(3)}%`}
          sub="After PAV" colour="#4ade80" />
        <MetricCard label="PAV Corrections" value={report.total_corrections_applied}
          sub={`across ${report.n_samples_checked} vectors`} colour="#fb923c" />
      </div>
      <div className="mt-4 rounded-lg border border-green-600/30 bg-green-900/20 px-5 py-3 text-xs text-green-300">
        <strong>Guarantee:</strong> {report.guarantee}
      </div>
    </div>
  );
};

// ---- Models ----

const ModelsSection: React.FC = () => {
  const [models, setModels] = useState<ExtremeModelMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchExtremeModels().then((r) => setModels(r.models ?? [])).catch((e) => setError(String(e))).finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner label="Loading classifier models..." />;
  if (error) return <ErrCard msg={error} />;

  return (
    <div>
      <SectionHeader title="Threshold Classifier Models"
        subtitle="One LightGBM binary classifier per threshold. Calibration via Platt sigmoid on VALIDATION data only."
        badge="4 Models" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {models.map((m) => {
          const meta = THRESHOLD_META.find((t) => t.mm === m.threshold_mm);
          const col = IMD_COLOURS[meta?.warning ?? 'NONE'];
          return (
            <div key={m.threshold_mm} className="rounded-xl border p-5 transition hover:brightness-110"
              style={{ borderColor: col.border + '60', backgroundColor: col.bg }}>
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <p className="font-bold" style={{ color: col.text }}>{meta?.label ?? 'Unknown'}</p>
                  <p className="text-xs opacity-60" style={{ color: col.text }}>{meta?.sub}</p>
                </div>
              </div>
              <div className="space-y-1.5 text-xs">
                {([
                  ['Model', m.model_type], ['Calibration', m.calibration_method],
                  ['Fitted', m.is_fitted ? 'Yes' : 'No'], ['Train Events', m.train_n_events],
                  ['Event Rate', (m.train_event_rate * 100).toFixed(2) + '%'],
                  ['Val ROC-AUC', m.val_roc_auc.toFixed(3)], ['Val PR-AUC', m.val_pr_auc.toFixed(3)],
                  ['Val Brier', m.val_brier_score.toFixed(4)], ['Val ECE', m.val_ece.toFixed(4)],
                  ['Features', m.feature_count],
                ] as [string, string | number][]).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-1">
                    <span className="text-slate-500">{k}</span>
                    <span className="font-medium text-slate-200">{String(v)}</span>
                  </div>
                ))}
              </div>
              {m.sample_size_warning && (
                <div className="mt-3 rounded bg-amber-900/40 px-2 py-1 text-xs text-amber-400">
                  Fewer than 50 training events
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ---- Metrics ----

const MetricsSection: React.FC = () => {
  const [metrics, setMetrics] = useState<ExtremeMetric[]>([]);
  const [notes, setNotes] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchExtremeMetrics().then((r) => { setMetrics(r.metrics ?? []); setNotes(r.notes ?? []); })
      .catch((e) => setError(String(e))).finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner label="Loading evaluation metrics..." />;
  if (error) return <ErrCard msg={error} />;

  return (
    <div>
      <SectionHeader title="Evaluation Metrics"
        subtitle="Primary metric: PR-AUC (for rare-event imbalanced classification)"
        badge="SYNTHETIC_DEMO" />
      <div className="overflow-x-auto rounded-xl border border-slate-700">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 bg-slate-800">
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">Threshold</th>
              {['ROC-AUC','PR-AUC','Brier','BSS','ECE','Events','Rate'].map((c) => (
                <th key={c} className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-400">{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {metrics.map((m, i) => {
              const meta = THRESHOLD_META.find((t) => t.mm === m.threshold_mm);
              const col = IMD_COLOURS[meta?.warning ?? 'NONE'];
              return (
                <tr key={m.threshold_mm}
                  className={`border-b border-slate-700/50 ${i % 2 === 0 ? 'bg-slate-900/40' : 'bg-slate-800/30'} hover:bg-slate-700/30 transition`}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="h-3 w-3 rounded-full" style={{ backgroundColor: col.border }} />
                      <div>
                        <p className="font-medium text-white">{m.threshold_label}</p>
                        {m.sample_size_warning && <p className="text-xs text-amber-400">Small sample</p>}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right font-mono font-semibold text-blue-300">{m.roc_auc.toFixed(3)}</td>
                  <td className="px-4 py-3 text-right font-mono font-semibold text-purple-300">{m.pr_auc.toFixed(3)}</td>
                  <td className="px-4 py-3 text-right font-mono text-slate-300">{m.brier_score.toFixed(4)}</td>
                  <td className="px-4 py-3 text-right font-mono">
                    <span className={m.brier_skill_score > 0 ? 'text-green-400' : 'text-red-400'}>
                      {m.brier_skill_score > 0 ? '+' : ''}{m.brier_skill_score.toFixed(3)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-cyan-300">{m.expected_calibration_error.toFixed(4)}</td>
                  <td className="px-4 py-3 text-right font-mono text-slate-300">{m.train_n_events}</td>
                  <td className="px-4 py-3 text-right font-mono text-slate-400">{(m.train_event_rate * 100).toFixed(2)}%</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {notes.length > 0 && (
        <ul className="mt-4 space-y-1">
          {notes.map((n, i) => <li key={i} className="text-xs text-slate-500">- {n}</li>)}
        </ul>
      )}
    </div>
  );
};

// ---- Brier Skill Score ----

const BrierSection: React.FC = () => {
  const [bss, setBss] = useState<BrierScoreRow[]>([]);
  const [interp, setInterp] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchExtremeBrierScores().then((r) => { setBss(r.bss_ladder ?? []); setInterp(r.interpretation ?? ''); })
      .catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner label="Loading BSS ladder..." />;
  const maxBSS = Math.max(...bss.map((b) => b.brier_skill_score), 0.01);

  return (
    <div>
      <SectionHeader title="Brier Skill Score Ladder"
        subtitle="BSS > 0 = better than climatological reference. Higher is better." badge="BSS" />
      <div className="space-y-4">
        {bss.map((b) => {
          const meta = THRESHOLD_META.find((t) => t.mm === b.threshold_mm);
          const col = IMD_COLOURS[meta?.warning ?? 'NONE'];
          const pct = Math.round((b.brier_skill_score / maxBSS) * 100);
          return (
            <div key={b.threshold_mm} className="rounded-xl border border-slate-700 bg-slate-800/50 p-4">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full" style={{ backgroundColor: col.border }} />
                  <p className="font-medium text-white">{b.threshold_label}</p>
                </div>
                <div className="flex flex-wrap gap-3 text-xs text-slate-400">
                  <span>Brier: <strong className="text-slate-200">{b.brier_score.toFixed(4)}</strong></span>
                  <span>BSS: <strong className={b.brier_skill_score > 0 ? 'text-green-400' : 'text-red-400'}>
                    {b.brier_skill_score > 0 ? '+' : ''}{b.brier_skill_score.toFixed(3)}
                  </strong></span>
                  <span>vs Raw NWP: <strong className="text-cyan-400">+{b.skill_vs_raw_nwp.toFixed(3)}</strong></span>
                </div>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-slate-700">
                <div className="h-full rounded-full transition-all duration-700"
                  style={{ width: `${pct}%`, backgroundColor: col.border }} />
              </div>
            </div>
          );
        })}
      </div>
      {interp && <p className="mt-4 text-xs text-slate-500">{interp}</p>}
    </div>
  );
};

// ---- PR Curves ----

const PRCurvesSection: React.FC = () => {
  const [curves, setCurves] = useState<PRCurveDataPoint[]>([]);
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(0);

  useEffect(() => {
    fetchExtremePRCurves().then((r) => { setCurves(r.curves ?? []); setNote(r.note ?? ''); })
      .catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner label="Loading PR curves..." />;
  const cur = curves[selected];
  if (!cur) return <ErrCard msg="No PR curve data" />;

  const W = 400, H = 280, PAD = { t: 20, r: 20, b: 40, l: 50 };
  const plotW = W - PAD.l - PAD.r, plotH = H - PAD.t - PAD.b;
  const meta = THRESHOLD_META[selected];
  const col = IMD_COLOURS[meta?.warning ?? 'NONE'];
  const toX = (r: number) => PAD.l + r * plotW;
  const toY = (p: number) => PAD.t + plotH - p * plotH;
  const pts = cur.recall.map((r, i) => `${toX(r)},${toY(cur.precision[i])}`);
  const path = 'M ' + pts.join(' L ');
  const baseY = toY(cur.baseline_precision);

  return (
    <div>
      <SectionHeader title="Precision-Recall Curves"
        subtitle={note || 'PR-AUC is the primary metric for rare-event binary classification'}
        badge="PR-AUC" />
      <div className="mb-5 flex flex-wrap gap-2">
        {THRESHOLD_META.map((t, i) => {
          const c = IMD_COLOURS[t.warning];
          return (
            <button key={t.mm} onClick={() => setSelected(i)}
              className="rounded-full px-4 py-1.5 text-xs font-semibold transition"
              style={{ backgroundColor: selected === i ? c.border : c.bg, color: selected === i ? '#000' : c.text, border: `1.5px solid ${c.border}` }}>
              {t.label} ({t.sub})
            </button>
          );
        })}
      </div>
      <div className="flex flex-col gap-5 lg:flex-row">
        <div className="flex-1 rounded-xl border border-slate-700 bg-slate-900 p-4">
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
            {[0, 0.25, 0.5, 0.75, 1.0].map((v) => (
              <g key={v}>
                <line x1={PAD.l} x2={W - PAD.r} y1={toY(v)} y2={toY(v)} stroke="#334155" strokeWidth={0.5} />
                <text x={PAD.l - 4} y={toY(v) + 4} fill="#64748b" fontSize={9} textAnchor="end">{v.toFixed(2)}</text>
              </g>
            ))}
            {[0, 0.25, 0.5, 0.75, 1.0].map((v) => (
              <g key={v}>
                <line x1={toX(v)} x2={toX(v)} y1={PAD.t} y2={H - PAD.b} stroke="#334155" strokeWidth={0.5} />
                <text x={toX(v)} y={H - PAD.b + 14} fill="#64748b" fontSize={9} textAnchor="middle">{v.toFixed(2)}</text>
              </g>
            ))}
            <line x1={toX(0)} x2={toX(1)} y1={baseY} y2={baseY} stroke="#64748b" strokeWidth={1} strokeDasharray="4,4" />
            <path d={path} fill="none" stroke={col.border} strokeWidth={2.5} />
            {pts.length > 0 && (
              <path d={`M ${pts[0]} L ${pts.join(' L ')} L ${toX(cur.recall[cur.recall.length-1])},${toY(0)} L ${toX(cur.recall[0])},${toY(0)} Z`}
                fill={col.border} fillOpacity={0.12} />
            )}
            <text x={W/2} y={H-5} fill="#94a3b8" fontSize={10} textAnchor="middle">Recall</text>
            <text x={10} y={H/2} fill="#94a3b8" fontSize={10} textAnchor="middle" transform={`rotate(-90, 10, ${H/2})`}>Precision</text>
          </svg>
        </div>
        <div className="w-full space-y-3 lg:w-52">
          <div className="rounded-xl border p-4 text-center" style={{ borderColor: col.border, backgroundColor: col.bg }}>
            <p className="text-xs font-medium" style={{ color: col.text }}>PR-AUC</p>
            <p className="mt-1 text-3xl font-black" style={{ color: col.text }}>{cur.pr_auc.toFixed(3)}</p>
          </div>
          <MetricCard label="Baseline Precision" value={(cur.baseline_precision * 100).toFixed(2) + '%'} sub="event rate" colour="#64748b" />
          <MetricCard label="Skill vs Random" value={'+' + (cur.skill_vs_random * 100).toFixed(1) + '%'} colour="#4ade80" />
        </div>
      </div>
    </div>
  );
};

// ---- Calibration ----

const CalibrationSection: React.FC = () => {
  const [bins, setBins] = useState<CalibrationBin[]>([]);
  const [calMethod, setCalMethod] = useState('');
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(0);

  useEffect(() => {
    fetchExtremeCalibration().then((r) => { setBins(r.thresholds ?? []); setCalMethod(r.calibration_method ?? ''); })
      .catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner label="Loading calibration data..." />;
  const bin = bins[selected];
  if (!bin) return <ErrCard msg="No calibration data" />;

  const W = 360, H = 260, PAD = { t: 20, r: 20, b: 40, l: 50 };
  const plotW = W - PAD.l - PAD.r, plotH = H - PAD.t - PAD.b;
  const meta = THRESHOLD_META[selected];
  const col = IMD_COLOURS[meta?.warning ?? 'NONE'];
  const toX = (c: number) => PAD.l + c * plotW;
  const toY = (a: number) => PAD.t + plotH - a * plotH;

  return (
    <div>
      <SectionHeader title="Reliability Diagrams"
        subtitle={`Calibration: ${calMethod}. Fitted on VALIDATION data only.`}
        badge="ECE" />
      <div className="mb-5 flex flex-wrap gap-2">
        {THRESHOLD_META.map((t, i) => {
          const c = IMD_COLOURS[t.warning];
          return (
            <button key={t.mm} onClick={() => setSelected(i)}
              className="rounded-full px-4 py-1.5 text-xs font-semibold transition"
              style={{ backgroundColor: selected === i ? c.border : c.bg, color: selected === i ? '#000' : c.text, border: `1.5px solid ${c.border}` }}>
              {t.label}
            </button>
          );
        })}
      </div>
      <div className="flex flex-col gap-5 lg:flex-row">
        <div className="flex-1 rounded-xl border border-slate-700 bg-slate-900 p-4">
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
            {[0, 0.25, 0.5, 0.75, 1.0].map((v) => (
              <g key={v}>
                <line x1={PAD.l} x2={W - PAD.r} y1={toY(v)} y2={toY(v)} stroke="#334155" strokeWidth={0.5} />
                <text x={PAD.l - 4} y={toY(v) + 4} fill="#64748b" fontSize={9} textAnchor="end">{v.toFixed(2)}</text>
                <line x1={toX(v)} x2={toX(v)} y1={PAD.t} y2={H - PAD.b} stroke="#334155" strokeWidth={0.5} />
                <text x={toX(v)} y={H - PAD.b + 14} fill="#64748b" fontSize={9} textAnchor="middle">{v.toFixed(2)}</text>
              </g>
            ))}
            <line x1={toX(0)} x2={toX(1)} y1={toY(0)} y2={toY(1)} stroke="#4ade80" strokeWidth={1} strokeDasharray="5,3" />
            {bin.bin_confidence.map((conf, i) => {
              const acc = bin.bin_accuracy[i];
              return (
                <g key={i}>
                  <circle cx={toX(conf)} cy={toY(acc)} r={6} fill={col.border} fillOpacity={0.8} />
                  <line x1={toX(conf)} x2={toX(conf)} y1={toY(conf)} y2={toY(acc)}
                    stroke={acc > conf ? '#4ade80' : '#f87171'} strokeWidth={1.5} strokeDasharray="2,2" />
                </g>
              );
            })}
            <text x={W/2} y={H-5} fill="#94a3b8" fontSize={10} textAnchor="middle">Forecast Probability</text>
            <text x={10} y={H/2} fill="#94a3b8" fontSize={10} textAnchor="middle" transform={`rotate(-90, 10, ${H/2})`}>Observed Frequency</text>
          </svg>
        </div>
        <div className="w-full space-y-3 lg:w-48">
          <div className="rounded-xl border p-4 text-center" style={{ borderColor: col.border, backgroundColor: col.bg }}>
            <p className="text-xs" style={{ color: col.text }}>ECE</p>
            <p className="mt-1 text-3xl font-black" style={{ color: col.text }}>{bin.ece.toFixed(4)}</p>
          </div>
          <MetricCard label="N Bins" value={bin.bin_confidence.length} colour="#94a3b8" />
          <div className="rounded-lg border border-green-600/30 bg-green-900/20 px-3 py-2 text-xs text-green-400">
            Green dashed = perfect calibration diagonal
          </div>
        </div>
      </div>
    </div>
  );
};

// ---- Feature Importance ----

const FeatureImportanceSection: React.FC = () => {
  const [data, setData] = useState<ExtremeFeatureImportance[]>([]);
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(0);

  useEffect(() => {
    fetchExtremeFeatureImportance(12).then((r) => { setData(r.thresholds ?? []); setNote(r.note ?? ''); })
      .catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner label="Loading feature importance..." />;
  const item = data[selected];
  if (!item) return <ErrCard msg="No feature importance data" />;

  const feats = Object.entries(item.top_features).sort(([,a],[,b]) => b - a);
  const maxVal = feats[0]?.[1] ?? 1;
  const meta = THRESHOLD_META[selected];
  const col = IMD_COLOURS[meta?.warning ?? 'NONE'];

  return (
    <div>
      <SectionHeader title="Feature Importance" subtitle={note} badge="Gain" />
      <div className="mb-5 flex flex-wrap gap-2">
        {THRESHOLD_META.map((t, i) => {
          const c = IMD_COLOURS[t.warning];
          return (
            <button key={t.mm} onClick={() => setSelected(i)}
              className="rounded-full px-4 py-1.5 text-xs font-semibold transition"
              style={{ backgroundColor: selected === i ? c.border : c.bg, color: selected === i ? '#000' : c.text, border: `1.5px solid ${c.border}` }}>
              {t.label}
            </button>
          );
        })}
      </div>
      <div className="space-y-2">
        {feats.map(([fname, importance]) => {
          const pct = Math.round((importance / maxVal) * 100);
          return (
            <div key={fname} className="flex items-center gap-3">
              <div className="w-48 shrink-0 text-right text-xs text-slate-300 font-mono truncate">{fname}</div>
              <div className="flex-1 rounded-full bg-slate-700 h-5 overflow-hidden">
                <div className="h-full rounded-full flex items-center justify-end pr-2 text-xs font-bold text-black transition-all duration-700"
                  style={{ width: `${pct}%`, backgroundColor: col.border }}>
                  {pct > 15 ? `${(importance * 100).toFixed(1)}%` : ''}
                </div>
              </div>
              <span className="w-12 text-right text-xs font-mono text-slate-400">{(importance * 100).toFixed(1)}%</span>
            </div>
          );
        })}
      </div>
      <p className="mt-4 text-xs text-slate-500">
        {item.n_total_features} total features. Showing top {feats.length} by normalized gain.
      </p>
    </div>
  );
};

// ---- Main Page ----

export const ExtremeRainfallPage: React.FC = () => {
  const [status, setStatus] = useState<ExtremeEngineStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);

  useEffect(() => {
    fetchExtremeStatus().then(setStatus).catch(() => {}).finally(() => setStatusLoading(false));
  }, []);

  const sectionNav = [
    { id: 'hero',         label: 'Status' },
    { id: 'predictor',   label: 'Interactive' },
    { id: 'monotonicity',label: 'Monotonicity' },
    { id: 'models',      label: 'Models' },
    { id: 'metrics',     label: 'Metrics' },
    { id: 'brier',       label: 'Brier Scores' },
    { id: 'prcurves',    label: 'PR Curves' },
    { id: 'calibration', label: 'Calibration' },
    { id: 'importance',  label: 'Features' },
  ];

  return (
    <div className="min-h-screen bg-slate-950 px-4 py-8 text-white">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8">
          <div className="mb-2 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-red-500 to-orange-500 text-xl shadow-lg shadow-red-500/30">
              &#127783;
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tight text-white">
                Extreme Rainfall Probability Engine
              </h1>
              <p className="text-sm text-slate-400">
                Phase 7 | RAMP &#8594; Calibrated P(R &gt; T) | 4 IMD Thresholds | PAV Monotonicity
              </p>
            </div>
          </div>
          <SyntheticBanner />
          <div className="flex flex-wrap gap-2">
            {sectionNav.map((s) => (
              <button key={s.id}
                onClick={() => document.getElementById(s.id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
                className="rounded-full border border-slate-700 bg-slate-800/60 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:border-slate-500 hover:text-white">
                {s.label}
              </button>
            ))}
          </div>
        </div>
        <div className="space-y-10">
          <section id="hero" className="rounded-2xl border border-slate-700 bg-slate-900/50 p-6">
            <SectionHeader title="Engine Status" subtitle="Phase 7 operational metadata" badge="Phase 7" />
            <HeroSection status={status} loading={statusLoading} />
          </section>
          <section id="predictor"><InteractivePredictor /></section>
          <section id="monotonicity" className="rounded-2xl border border-slate-700 bg-slate-900/50 p-6">
            <MonotonicitySection />
          </section>
          <section id="models" className="rounded-2xl border border-slate-700 bg-slate-900/50 p-6">
            <ModelsSection />
          </section>
          <section id="metrics" className="rounded-2xl border border-slate-700 bg-slate-900/50 p-6">
            <MetricsSection />
          </section>
          <section id="brier" className="rounded-2xl border border-slate-700 bg-slate-900/50 p-6">
            <BrierSection />
          </section>
          <section id="prcurves" className="rounded-2xl border border-slate-700 bg-slate-900/50 p-6">
            <PRCurvesSection />
          </section>
          <section id="calibration" className="rounded-2xl border border-slate-700 bg-slate-900/50 p-6">
            <CalibrationSection />
          </section>
          <section id="importance" className="rounded-2xl border border-slate-700 bg-slate-900/50 p-6">
            <FeatureImportanceSection />
          </section>
          <div className="rounded-xl border border-slate-800 bg-slate-900/30 px-6 py-5 text-xs text-slate-500">
            <p className="mb-2 font-semibold text-slate-400">Phase 7 Scientific Architecture</p>
            <div className="grid gap-1 sm:grid-cols-2 lg:grid-cols-4">
              <p>4 independent LightGBM binary classifiers</p>
              <p>Platt sigmoid calibration on VALIDATION only</p>
              <p>Pool Adjacent Violators monotonicity reconciliation</p>
              <p>RAMP v1.0.0 frozen as deterministic input</p>
              <p>Strict leakage guard enforced</p>
              <p>Brier Score / PR-AUC / ROC-AUC / ECE evaluation</p>
              <p>BSS relative to climatological event rates</p>
              <p>All outputs tagged SYNTHETIC_DEMO</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
'''

out = pathlib.Path('D:/SIH26080/frontend/src/pages/ExtremeRainfall.tsx')
out.write_text(CONTENT, encoding='utf-8')
print(f'Written {len(CONTENT)} chars to {out}')
