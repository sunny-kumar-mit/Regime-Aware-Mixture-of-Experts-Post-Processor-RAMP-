/**
 * Phase 17 — Data Health & Connectivity Dashboard
 * SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
 * MoES / NCMRWF
 *
 * PART AC Requirements:
 *   - Monitor NCMRWF NCUM, NCMRWF NEPS, IMD 0.25° Gridded Rainfall.
 *   - Display: availability, freshness, coverage, QC, checksum, latest cycle, delay, status.
 *   - Strict scientific integrity: Reflect unmounted state truthfully (WAITING_FOR_AUTHORITATIVE_DATA).
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Database,
  RefreshCw,
  AlertTriangle,
  Server,
  CloudRain,
  Activity,
} from 'lucide-react';
import {
  fetchProductionDataHealth,
  fetchProductionFreshness,
  fetchDataHealthSources,
  fetchDataHealthFreshness,
} from '../api/client';

export const DataHealthPage: React.FC = () => {
  const [dataHealth, setDataHealth] = useState<any | null>(null);
  const [freshness, setFreshness] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [healthRes, freshRes] = await Promise.all([
        fetchProductionDataHealth().catch(() => fetchDataHealthSources().catch(() => null)),
        fetchProductionFreshness().catch(() => fetchDataHealthFreshness().catch(() => null)),
      ]);
      if (healthRes && (healthRes.status === 'SUCCESS' || healthRes.status === 'success')) {
        setDataHealth(healthRes.data || healthRes);
      }
      if (freshRes && (freshRes.status === 'SUCCESS' || freshRes.status === 'success')) {
        setFreshness(freshRes.data || freshRes);
      }
    } catch (err: any) {
      console.error('Failed to load data health:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, [loadData]);


  const providers = dataHealth?.providers || {
    NCMRWF_NCUM: {
      mounted: false,
      reachable: false,
      status: 'NOT_AVAILABLE',
      latest_cycle: null,
      delay_minutes: null,
      coverage_pct: 0,
      qc_status: 'UNVERIFIED',
    },
    NCMRWF_NEPS: {
      mounted: false,
      reachable: false,
      status: 'NOT_AVAILABLE',
      latest_cycle: null,
      delay_minutes: null,
      coverage_pct: 0,
      qc_status: 'UNVERIFIED',
    },
    IMD_GRIDDED_OBSERVATION: {
      mounted: false,
      reachable: false,
      status: 'NOT_AVAILABLE',
      latest_date: null,
      delay_minutes: null,
      coverage_pct: 0,
      qc_status: 'UNVERIFIED',
    },
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'AVAILABLE':
      case 'ON_TIME':
      case 'MOUNTED':
      case 'UP':
        return 'text-emerald-400 bg-emerald-950/70 border-emerald-800/80';
      case 'DELAYED':
      case 'PARTIAL':
        return 'text-amber-400 bg-amber-950/70 border-amber-800/80';
      case 'STALE':
      case 'MISSING':
        return 'text-orange-400 bg-orange-950/70 border-orange-800/80';
      case 'BLOCKED':
      case 'NOT_AVAILABLE':
      case 'UNMOUNTED':
      default:
        return 'text-rose-400 bg-rose-950/70 border-rose-800/80';
    }
  };

  const allMounted = Boolean(
    (providers.NCMRWF_NCUM?.mounted || providers.NCMRWF_NCUM?.status === 'AVAILABLE') &&
    (providers.NCMRWF_NEPS?.mounted || providers.NCMRWF_NEPS?.status === 'AVAILABLE') &&
    (providers.IMD_GRIDDED_OBSERVATION?.mounted || providers.IMD_GRIDDED_OBSERVATION?.status === 'AVAILABLE')
  );

  const rec00Z = (freshness?.freshness_records || []).find((r: any) => r.cycle_type === '00Z') || freshness?.cycles?.['00Z'];
  const rec12Z = (freshness?.freshness_records || []).find((r: any) => r.cycle_type === '12Z') || freshness?.cycles?.['12Z'];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 text-slate-100">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-700/60 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Database className="h-7 w-7 text-emerald-400" />
              Meteorological Data Health & Freshness
            </h1>
            <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
              NCMRWF & IMD ARCHIVE TELEMETRY
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Real-time feed connectivity, arrival delays, spatial coverage, and CF-1.8 metadata compliance.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => loadData()}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-medium border border-slate-700 transition"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Scientific Integrity Status Banner */}
      <div className={`p-4 rounded-xl bg-slate-900/90 border flex items-center justify-between ${
        allMounted ? 'border-emerald-500/40' : 'border-amber-500/40'
      }`}>
        <div className="flex items-center gap-3">
          <AlertTriangle className={`h-5 w-5 ${allMounted ? 'text-emerald-400' : 'text-amber-400'}`} />
          <div>
            <div className={`text-xs font-bold uppercase tracking-wider font-mono ${allMounted ? 'text-emerald-300' : 'text-amber-300'}`}>
              Scientific Integrity Mandate
            </div>
            <div className="text-xs text-slate-300">
              {allMounted
                ? 'Authoritative NCMRWF HPC archives and IMD gridded directories are mounted and verified. Real operational pipeline active.'
                : 'Authoritative NCMRWF HPC archives and IMD gridded directories are currently unmounted. System reports WAITING_FOR_AUTHORITATIVE_DATA. Zero data fabricated.'}
            </div>
          </div>
        </div>
        <span className={`px-3 py-1 rounded text-xs font-mono font-semibold ${
          allMounted
            ? 'bg-emerald-950/80 border border-emerald-800 text-emerald-300'
            : 'bg-amber-950/80 border border-amber-800 text-amber-300'
        }`}>
          {allMounted ? 'REAL_OPERATIONAL_OPEN' : 'REAL_OPERATIONAL_BLOCKED'}
        </span>
      </div>


      {/* Provider Health Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Card 1: NCUM */}
        <div className="bg-slate-900/60 rounded-xl border border-slate-800 p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Server className="h-5 w-5 text-blue-400" />
              <div>
                <h3 className="text-sm font-bold text-white">NCMRWF NCUM</h3>
                <span className="text-[10px] text-slate-500 font-mono">Deterministic Global (~12 km)</span>
              </div>
            </div>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${getStatusBadge(
                providers.NCMRWF_NCUM?.status || 'NOT_AVAILABLE'
              )}`}
            >
              {providers.NCMRWF_NCUM?.status || 'NOT_AVAILABLE'}
            </span>
          </div>

          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between text-slate-400">
              <span>Filesystem Mount:</span>
              <span className={providers.NCMRWF_NCUM?.mounted ? 'text-emerald-400' : 'text-rose-400'}>
                {providers.NCMRWF_NCUM?.mounted ? 'MOUNTED' : 'UNMOUNTED'}
              </span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Expected Cycles:</span>
              <span className="text-slate-200">00Z, 12Z Synoptic</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Latest Discovered:</span>
              <span className="text-slate-200">{providers.NCMRWF_NCUM?.latest_cycle || 'None'}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Arrival Delay:</span>
              <span className="text-slate-200">
                {providers.NCMRWF_NCUM?.delay_minutes !== null
                  ? `${providers.NCMRWF_NCUM?.delay_minutes} min`
                  : 'N/A'}
              </span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>QC Validation:</span>
              <span className="text-slate-200">{providers.NCMRWF_NCUM?.qc_status || 'UNVERIFIED'}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Coverage:</span>
              <span className="text-slate-200">{providers.NCMRWF_NCUM?.coverage_pct ?? 0}%</span>
            </div>
          </div>
        </div>

        {/* Card 2: NEPS */}
        <div className="bg-slate-900/60 rounded-xl border border-slate-800 p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-purple-400" />
              <div>
                <h3 className="text-sm font-bold text-white">NCMRWF NEPS</h3>
                <span className="text-[10px] text-slate-500 font-mono">Ensemble Prediction (~12 km, 11 mbrs)</span>
              </div>
            </div>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${getStatusBadge(
                providers.NCMRWF_NEPS?.status || 'NOT_AVAILABLE'
              )}`}
            >
              {providers.NCMRWF_NEPS?.status || 'NOT_AVAILABLE'}
            </span>
          </div>

          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between text-slate-400">
              <span>Filesystem Mount:</span>
              <span className={providers.NCMRWF_NEPS?.mounted ? 'text-emerald-400' : 'text-rose-400'}>
                {providers.NCMRWF_NEPS?.mounted ? 'MOUNTED' : 'UNMOUNTED'}
              </span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Expected Cycles:</span>
              <span className="text-slate-200">00Z, 12Z Synoptic</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Latest Discovered:</span>
              <span className="text-slate-200">{providers.NCMRWF_NEPS?.latest_cycle || 'None'}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Arrival Delay:</span>
              <span className="text-slate-200">
                {providers.NCMRWF_NEPS?.delay_minutes !== null
                  ? `${providers.NCMRWF_NEPS?.delay_minutes} min`
                  : 'N/A'}
              </span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>QC Validation:</span>
              <span className="text-slate-200">{providers.NCMRWF_NEPS?.qc_status || 'UNVERIFIED'}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Coverage:</span>
              <span className="text-slate-200">{providers.NCMRWF_NEPS?.coverage_pct ?? 0}%</span>
            </div>
          </div>
        </div>

        {/* Card 3: IMD Ground Truth */}
        <div className="bg-slate-900/60 rounded-xl border border-slate-800 p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <CloudRain className="h-5 w-5 text-emerald-400" />
              <div>
                <h3 className="text-sm font-bold text-white">IMD Observations</h3>
                <span className="text-[10px] text-slate-500 font-mono">0.25° Daily Gridded Rainfall</span>
              </div>
            </div>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${getStatusBadge(
                providers.IMD_GRIDDED_OBSERVATION?.status || 'NOT_AVAILABLE'
              )}`}
            >
              {providers.IMD_GRIDDED_OBSERVATION?.status || 'NOT_AVAILABLE'}
            </span>
          </div>

          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between text-slate-400">
              <span>Filesystem Mount:</span>
              <span className={providers.IMD_GRIDDED_OBSERVATION?.mounted ? 'text-emerald-400' : 'text-rose-400'}>
                {providers.IMD_GRIDDED_OBSERVATION?.mounted ? 'MOUNTED' : 'UNMOUNTED'}
              </span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Temporal Resolution:</span>
              <span className="text-slate-200">Daily Cumulative (03:00Z)</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Latest Date:</span>
              <span className="text-slate-200">
                {providers.IMD_GRIDDED_OBSERVATION?.latest_date || 'None'}
              </span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Delay (Lag):</span>
              <span className="text-slate-200">
                {providers.IMD_GRIDDED_OBSERVATION?.delay_minutes !== null
                  ? `${providers.IMD_GRIDDED_OBSERVATION?.delay_minutes} min`
                  : 'N/A'}
              </span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Pairing Readiness:</span>
              <span className="text-slate-200">
                {providers.IMD_GRIDDED_OBSERVATION?.mounted ? 'READY' : 'BLOCKED'}
              </span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Spatial Coverage:</span>
              <span className="text-slate-200">{providers.IMD_GRIDDED_OBSERVATION?.coverage_pct ?? 0}%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Synoptic Arrival Freshness Schedule */}
      <div className="bg-slate-900/60 rounded-xl border border-slate-800 p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider font-mono">
          Synoptic Cycle Freshness & Arrival Deadlines
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded-lg bg-slate-950/60 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-200 font-mono">00Z Synoptic Forecast Cycle</span>
              <span className="text-xs px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800 font-mono">
                Morning Cycle
              </span>
            </div>
            <div className="text-xs text-slate-400 space-y-1">
              <div>Initialization Time: 00:00 UTC (05:30 IST)</div>
              <div>Expected Delivery: ~03:30 UTC (09:00 IST)</div>
              <div>
                Arrival Delay:{' '}
                <span className="text-slate-200">
                  {rec00Z?.delay_minutes !== undefined && rec00Z?.delay_minutes !== null
                    ? `${rec00Z.delay_minutes} min`
                    : 'N/A'}
                </span>
              </div>
              <div className="pt-1 font-mono">
                Status:{' '}
                <span
                  className={
                    rec00Z?.sla_status === 'ON_TIME'
                      ? 'text-emerald-400 font-semibold'
                      : rec00Z?.sla_status === 'DELAYED'
                      ? 'text-amber-400 font-semibold'
                      : 'text-slate-400'
                  }
                >
                  {rec00Z?.sla_status || rec00Z?.status || 'WAITING_FOR_DATA'}
                </span>
              </div>
            </div>
          </div>

          <div className="p-4 rounded-lg bg-slate-950/60 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-200 font-mono">12Z Synoptic Forecast Cycle</span>
              <span className="text-xs px-2 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800 font-mono">
                Evening Cycle
              </span>
            </div>
            <div className="text-xs text-slate-400 space-y-1">
              <div>Initialization Time: 12:00 UTC (17:30 IST)</div>
              <div>Expected Delivery: ~15:30 UTC (21:00 IST)</div>
              <div>
                Arrival Delay:{' '}
                <span className="text-slate-200">
                  {rec12Z?.delay_minutes !== undefined && rec12Z?.delay_minutes !== null
                    ? `${rec12Z.delay_minutes} min`
                    : 'N/A'}
                </span>
              </div>
              <div className="pt-1 font-mono">
                Status:{' '}
                <span
                  className={
                    rec12Z?.sla_status === 'ON_TIME'
                      ? 'text-emerald-400 font-semibold'
                      : rec12Z?.sla_status === 'DELAYED'
                      ? 'text-amber-400 font-semibold'
                      : 'text-slate-400'
                  }
                >
                  {rec12Z?.sla_status || rec12Z?.status || 'WAITING_FOR_DATA'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
