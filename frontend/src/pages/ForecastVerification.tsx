/**
 * Phase 16 — Operational Forecast Quality & Real Verification Dashboard
 * SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
 * MoES / NCMRWF
 *
 * PART Y & PART U Requirements:
 *   - Cycle, Lead Time, Valid Time, Coverage, Sample Count.
 *   - Standard WMO/IMD Continuous & Categorical Verification Metrics:
 *     MAE, RMSE, Bias, Correlation, POD, FAR, CSI, ETS, Brier Score, BSS.
 *   - Threshold selector: 0.1 mm, 64.5 mm, 115.6 mm, 204.5 mm.
 *   - Model selector / comparison: Raw NWP, Simple Bias Correction, Global ML, RAMP MoE.
 *   - Factual integrity: If observations absent, displays "VERIFICATION NOT AVAILABLE".
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Award,
  RefreshCw,
  AlertCircle,
  BarChart3,
  Calendar,
  Clock,
  Info,
  Sliders,
  Filter,
} from 'lucide-react';

import { fetchRealVerification } from '../api/client';

export const ForecastVerificationPage: React.FC = () => {
  const [refreshing, setRefreshing] = useState(false);
  const [report, setReport] = useState<any>(null);
  const [cycle, setCycle] = useState('00Z');
  const [leadTime, setLeadTime] = useState(24);
  const [threshold, setThreshold] = useState(0.1);

  const loadVerification = useCallback(async () => {
    try {
      setRefreshing(true);
      const data = await fetchRealVerification(cycle, leadTime, threshold);
      setReport(data);
    } catch (err: any) {
      console.error('Failed to load real verification report:', err);
    } finally {
      setRefreshing(false);
    }
  }, [cycle, leadTime, threshold]);

  useEffect(() => {
    loadVerification();
  }, [loadVerification]);

  const thresholds = [
    { value: 0.1, label: '0.1 mm (Rain Occurrence)' },
    { value: 64.5, label: '64.5 mm (Heavy Rain)' },
    { value: 115.6, label: '115.6 mm (Very Heavy)' },
    { value: 204.5, label: '204.5 mm (Extremely Heavy)' },
  ];

  const models = [
    { id: 'raw_nwp', name: 'Raw NWP (NCUM)', type: 'Deterministic Numerical Baseline' },
    { id: 'bias_corrected', name: 'Simple Bias Correction', type: 'Empirical Quantile Mapping' },
    { id: 'global_ml', name: 'Global ML Baseline', type: 'Unified LightGBM Model' },
    { id: 'ramp_moe', name: 'RAMP MoE (Candidate)', type: 'Regime-Aware Mixture-of-Experts' },
  ];

  const isVerified = report?.verification_status === 'VERIFIED';

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 text-slate-100">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-700/60 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Award className="h-7 w-7 text-amber-400" />
              Real Operational Forecast Verification
            </h1>
            <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/40">
              IMD GROUND TRUTH BENCHMARK
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Factual verification against IMD 0.25° gridded daily rainfall observations. Zero fabricated scores.
          </p>
        </div>

        <button
          onClick={loadVerification}
          disabled={refreshing}
          className="flex items-center gap-2 px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-600 rounded-lg text-sm font-medium transition self-start md:self-auto"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin text-amber-400' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Control Bar: Cycle, Lead Time, Threshold */}
      <div className="bg-slate-900 border border-slate-700/80 rounded-xl p-4 shadow-lg flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-4 text-xs">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-cyan-400" />
            <span className="text-slate-400">Synoptic Cycle:</span>
            <select
              value={cycle}
              onChange={(e) => setCycle(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-amber-500"
            >
              <option value="00Z">00Z Cycle</option>
              <option value="12Z">12Z Cycle</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-indigo-400" />
            <span className="text-slate-400">Lead Time:</span>
            <select
              value={leadTime}
              onChange={(e) => setLeadTime(Number(e.target.value))}
              className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-amber-500"
            >
              <option value={24}>T+24 Hours (Day 1)</option>
              <option value={48}>T+48 Hours (Day 2)</option>
              <option value={72}>T+72 Hours (Day 3)</option>
              <option value={96}>T+96 Hours (Day 4)</option>
              <option value={120}>T+120 Hours (Day 5)</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-amber-400" />
            <span className="text-slate-400">Precipitation Threshold:</span>
            <select
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-amber-500"
            >
              {thresholds.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="text-slate-400">
            Obs Source:{' '}
            <span className="text-slate-200 font-semibold">
              {report?.observation_source || 'IMD_GRIDDED_RAINFALL'}
            </span>
          </div>
          <div className="text-slate-400">
            Samples:{' '}
            <span className="text-amber-400 font-semibold">
              {report?.sample_count || 0} / 10 min
            </span>
          </div>
        </div>
      </div>

      {/* Factual Integrity Banner */}
      {!isVerified && (
        <div className="bg-amber-950/30 border border-amber-500/50 rounded-xl p-5 shadow-lg flex items-start gap-4">
          <AlertCircle className="h-6 w-6 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h3 className="font-bold text-amber-200 text-sm tracking-wide">
              VERIFICATION NOT AVAILABLE
            </h3>
            <p className="text-xs text-amber-300/80 leading-relaxed">
              Authoritative IMD 0.25° gridded rainfall ground truth observations are not currently mounted for this forecast cycle.
              In accordance with the RAMP Absolute Scientific Integrity Rule, no verification scores or skill comparisons are fabricated.
              Scores will compute automatically once corresponding IMD observations are ingested and paired.
            </p>
          </div>
        </div>
      )}

      {/* Baseline Comparison Table (PART U) */}
      <div className="bg-slate-900 border border-slate-700/80 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-indigo-400" />
              Factual Model Baseline Comparison Table (Part U)
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Side-by-side performance metrics at {threshold} mm threshold.
            </p>
          </div>
          <span className="text-xs font-mono text-slate-400">WMO-Compliant Scores</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[10px]">
                <th className="py-2.5 px-3">Model</th>
                <th className="py-2.5 px-3">MAE (mm)</th>
                <th className="py-2.5 px-3">RMSE (mm)</th>
                <th className="py-2.5 px-3">Mean Bias</th>
                <th className="py-2.5 px-3">Pearson R</th>
                <th className="py-2.5 px-3">POD</th>
                <th className="py-2.5 px-3">FAR</th>
                <th className="py-2.5 px-3">CSI</th>
                <th className="py-2.5 px-3">ETS</th>
                <th className="py-2.5 px-3">Brier Score</th>
                <th className="py-2.5 px-3">BSS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
              {models.map((m) => {
                const metrics = report?.model_comparisons?.[m.id];
                return (
                  <tr key={m.id} className="hover:bg-slate-800/30">
                    <td className="py-3 px-3 font-sans">
                      <div className="font-semibold text-slate-200">{m.name}</div>
                      <div className="text-[10px] text-slate-500">{m.type}</div>
                    </td>
                    <td className="py-3 px-3">{metrics?.mae !== undefined ? metrics.mae : '—'}</td>
                    <td className="py-3 px-3">{metrics?.rmse !== undefined ? metrics.rmse : '—'}</td>
                    <td className="py-3 px-3">{metrics?.bias !== undefined ? metrics.bias : '—'}</td>
                    <td className="py-3 px-3">{metrics?.correlation !== undefined ? metrics.correlation : '—'}</td>
                    <td className="py-3 px-3">{metrics?.categorical_by_threshold?.pod ?? '—'}</td>
                    <td className="py-3 px-3">{metrics?.categorical_by_threshold?.far ?? '—'}</td>
                    <td className="py-3 px-3">{metrics?.categorical_by_threshold?.csi ?? '—'}</td>
                    <td className="py-3 px-3">{metrics?.categorical_by_threshold?.ets ?? '—'}</td>
                    <td className="py-3 px-3">{metrics?.brier_score !== undefined ? metrics.brier_score : '—'}</td>
                    <td className="py-3 px-3">{metrics?.brier_skill_score !== undefined ? metrics.brier_skill_score : '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Stratification & Methodology Notes */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-slate-900 border border-slate-700/80 rounded-xl p-4 shadow-lg space-y-2 text-xs">
          <h3 className="font-bold text-white flex items-center gap-2">
            <Sliders className="h-4 w-4 text-cyan-400" />
            Verification Stratification Parameters
          </h3>
          <ul className="space-y-1.5 text-slate-400 text-[11px]">
            <li>• <strong className="text-slate-200">Temporal Lead Time:</strong> Day 1 through Day 5 (24h to 120h).</li>
            <li>• <strong className="text-slate-200">Precipitation Thresholds:</strong> 0.1 mm (Rain), 64.5 mm (Heavy), 115.6 mm (Very Heavy), 204.5 mm (Extremely Heavy).</li>
            <li>• <strong className="text-slate-200">Atmospheric Regimes:</strong> Active Monsoon, Break Monsoon, Monsoon Depressions, Western Disturbances.</li>
            <li>• <strong className="text-slate-200">Regional Sub-Domains:</strong> Western Ghats, Central India, Northeast, Northwest Plains.</li>
          </ul>
        </div>

        <div className="bg-slate-900 border border-slate-700/80 rounded-xl p-4 shadow-lg space-y-2 text-xs">
          <h3 className="font-bold text-white flex items-center gap-2">
            <Info className="h-4 w-4 text-emerald-400" />
            WMO / IMD Verification Protocol
          </h3>
          <p className="text-slate-400 text-[11px] leading-relaxed">
            Continuous metrics quantify mean error magnitude and linear correlation. Categorical scores evaluate event detection at critical flood thresholds.
            Probabilistic calibration assesses reliability and skill relative to climatology via Brier Skill Score.
          </p>
        </div>
      </div>
    </div>
  );
};

export default ForecastVerificationPage;
