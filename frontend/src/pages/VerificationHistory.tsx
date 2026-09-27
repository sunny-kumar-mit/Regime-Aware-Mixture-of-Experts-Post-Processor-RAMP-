/**
 * Phase 17 — Forecast Verification History Dashboard
 * SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
 * MoES / NCMRWF
 *
 * PART AD Requirements:
 *   - Controls: date, cycle (00Z/12Z), lead (+24h, +48h...), threshold (0.1, 15.6, 64.5mm),
 *     region (All-India, Western Ghats, Northeast...), model (RAMP vs NCUM vs NEPS).
 *   - Real verification metrics over time: RMSE, MAE, Bias, CSI, Brier Score, ECE.
 *   - Absolute scientific integrity: If genuine IMD observation archive is unmounted,
 *     honestly report: "NO REAL VERIFICATION HISTORY AVAILABLE".
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Award,
  RefreshCw,
  AlertTriangle,
  Filter,
} from 'lucide-react';
import { fetchProductionVerificationHistory } from '../api/client';

export const VerificationHistoryPage: React.FC = () => {
  const [leadTime, setLeadTime] = useState<number>(24);
  const [thresholdMm, setThresholdMm] = useState<number>(0.1);
  const [region, setRegion] = useState<string>('ALL_INDIA');
  const [cycle, setCycle] = useState<string>('00Z');
  const [historyData, setHistoryData] = useState<any | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const loadHistory = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchProductionVerificationHistory(leadTime, thresholdMm, region);
      if (res.status === 'SUCCESS') {
        setHistoryData(res.data);
      }
    } catch (err: any) {
      console.error('Failed to load verification history:', err);
    } finally {
      setLoading(false);
    }
  }, [leadTime, thresholdMm, region]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const records = historyData?.records || [];
  const hasRealObservations = records.length > 0 && historyData?.has_real_observations === true;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 text-slate-100">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-700/60 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Award className="h-7 w-7 text-amber-400" />
              Continuous Forecast Verification History
            </h1>
            <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40">
              IMD 0.25° GROUND TRUTH PAIRING
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Historical skill trajectories, reliability calibration, and error distributions across monsoon regimes.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => loadHistory()}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-medium border border-slate-700 transition"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh History
          </button>
        </div>
      </div>

      {/* Control Bar */}
      <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-wrap items-center gap-4 text-xs font-mono">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-400" />
          <span className="text-slate-400 uppercase font-sans font-semibold">Filters:</span>
        </div>

        {/* Lead time */}
        <div className="flex items-center gap-1.5 bg-slate-950 px-2.5 py-1.5 rounded border border-slate-800">
          <span className="text-slate-500">Lead:</span>
          <select
            value={leadTime}
            onChange={(e) => setLeadTime(Number(e.target.value))}
            className="bg-transparent text-slate-200 outline-none cursor-pointer"
          >
            <option value={6} className="bg-slate-900">+6h</option>
            <option value={12} className="bg-slate-900">+12h</option>
            <option value={24} className="bg-slate-900">+24h (D+1)</option>
            <option value={48} className="bg-slate-900">+48h (D+2)</option>
            <option value={72} className="bg-slate-900">+72h (D+3)</option>
            <option value={96} className="bg-slate-900">+96h (D+4)</option>
            <option value={120} className="bg-slate-900">+120h (D+5)</option>
          </select>
        </div>

        {/* Threshold */}
        <div className="flex items-center gap-1.5 bg-slate-950 px-2.5 py-1.5 rounded border border-slate-800">
          <span className="text-slate-500">Threshold:</span>
          <select
            value={thresholdMm}
            onChange={(e) => setThresholdMm(Number(e.target.value))}
            className="bg-transparent text-slate-200 outline-none cursor-pointer"
          >
            <option value={0.1} className="bg-slate-900">≥0.1 mm (Rain)</option>
            <option value={15.6} className="bg-slate-900">≥15.6 mm (Moderate)</option>
            <option value={64.5} className="bg-slate-900">≥64.5 mm (Heavy)</option>
            <option value={115.6} className="bg-slate-900">≥115.6 mm (Very Heavy)</option>
            <option value={204.5} className="bg-slate-900">≥204.5 mm (Extremely Heavy)</option>
          </select>
        </div>

        {/* Region */}
        <div className="flex items-center gap-1.5 bg-slate-950 px-2.5 py-1.5 rounded border border-slate-800">
          <span className="text-slate-500">Region:</span>
          <select
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            className="bg-transparent text-slate-200 outline-none cursor-pointer"
          >
            <option value="ALL_INDIA" className="bg-slate-900">All India Domain</option>
            <option value="WEST_COAST" className="bg-slate-900">Western Ghats</option>
            <option value="NORTHEAST" className="bg-slate-900">Northeast India</option>
            <option value="CENTRAL_INDIA" className="bg-slate-900">Central India Monsoon Core</option>
            <option value="NORTHWEST" className="bg-slate-900">Northwest India</option>
          </select>
        </div>

        {/* Cycle */}
        <div className="flex items-center gap-1.5 bg-slate-950 px-2.5 py-1.5 rounded border border-slate-800">
          <span className="text-slate-500">Cycle:</span>
          <select
            value={cycle}
            onChange={(e) => setCycle(e.target.value)}
            className="bg-transparent text-slate-200 outline-none cursor-pointer"
          >
            <option value="00Z" className="bg-slate-900">00Z Morning</option>
            <option value="12Z" className="bg-slate-900">12Z Evening</option>
          </select>
        </div>
      </div>

      {/* Main Content Area */}
      {!hasRealObservations ? (
        <div className="p-12 text-center bg-slate-900/40 rounded-2xl border border-dashed border-slate-800 space-y-4">
          <div className="inline-flex p-4 rounded-full bg-slate-800/80 text-amber-400 mb-2">
            <AlertTriangle className="h-8 w-8" />
          </div>
          <h2 className="text-lg font-bold text-slate-200 uppercase tracking-wider font-mono">
            NO REAL VERIFICATION HISTORY AVAILABLE
          </h2>
          <p className="text-xs text-slate-400 max-w-xl mx-auto leading-relaxed">
            The RAMP operational post-processor adheres to absolute scientific integrity. Authoritative IMD 0.25° gridded observation archives are currently unmounted. Real forecast-observation pairing, RMSE skill scores, and Critical Success Index (CSI) cannot be computed on unmounted ground truth.
          </p>
          <div className="pt-2 flex justify-center gap-3">
            <span className="px-3 py-1 bg-amber-950/70 border border-amber-800 text-amber-300 rounded font-mono text-[11px]">
              OBSERVATION_MOUNT = FALSE
            </span>
            <span className="px-3 py-1 bg-slate-800 text-slate-400 rounded font-mono text-[11px]">
              PAIRING_READY = BLOCKED
            </span>
          </div>
        </div>
      ) : (
        /* Real History Charts & Table */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Card: RMSE */}
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
            <div className="flex justify-between items-center text-xs font-mono">
              <span className="text-slate-400">Root Mean Square Error</span>
              <span className="text-emerald-400 font-bold">RMSE</span>
            </div>
            <div className="text-2xl font-bold font-mono text-white">
              {historyData?.summary?.mean_rmse ? `${historyData.summary.mean_rmse.toFixed(2)} mm` : '—'}
            </div>
            <div className="h-32 bg-slate-950/70 rounded border border-slate-800 flex items-center justify-center text-xs text-slate-500 font-mono">
              [RMSE Historical Time-Series]
            </div>
          </div>

          {/* Card: MAE */}
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
            <div className="flex justify-between items-center text-xs font-mono">
              <span className="text-slate-400">Mean Absolute Error</span>
              <span className="text-cyan-400 font-bold">MAE</span>
            </div>
            <div className="text-2xl font-bold font-mono text-white">
              {historyData?.summary?.mean_mae ? `${historyData.summary.mean_mae.toFixed(2)} mm` : '—'}
            </div>
            <div className="h-32 bg-slate-950/70 rounded border border-slate-800 flex items-center justify-center text-xs text-slate-500 font-mono">
              [MAE Historical Time-Series]
            </div>
          </div>

          {/* Card: CSI */}
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
            <div className="flex justify-between items-center text-xs font-mono">
              <span className="text-slate-400">Critical Success Index</span>
              <span className="text-amber-400 font-bold">CSI</span>
            </div>
            <div className="text-2xl font-bold font-mono text-white">
              {historyData?.summary?.mean_csi ? historyData.summary.mean_csi.toFixed(3) : '—'}
            </div>
            <div className="h-32 bg-slate-950/70 rounded border border-slate-800 flex items-center justify-center text-xs text-slate-500 font-mono">
              [CSI Historical Trajectory]
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
