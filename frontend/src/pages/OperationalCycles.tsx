/**
 * Phase 17 — Operational Cycles Management
 * SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
 * MoES / NCMRWF
 *
 * PART AB Requirements:
 *   - Cycle ID, Initialization, Expected, Available, Validation, Inference,
 *     Publication, Verification, Final Status.
 *   - Clicking a cycle opens full audit details (timeline, errors, job specs).
 *   - Operator retry capability for transient failures.
 *   - Idempotent execution status tracking.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  RefreshCw,
  Calendar,
  ArrowRight,
} from 'lucide-react';
import {
  fetchProductionCycles,
  fetchProductionCycleDetail,
  fetchProductionJobs,
  postRetryCycle,
} from '../api/client';

export const OperationalCyclesPage: React.FC = () => {
  const [cycles, setCycles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCycleId, setSelectedCycleId] = useState<string | null>(null);
  const [cycleDetail, setCycleDetail] = useState<any | null>(null);
  const [cycleJobs, setCycleJobs] = useState<any[]>([]);
  const [retrying, setRetrying] = useState<string | null>(null);
  const [feedbackMsg, setFeedbackMsg] = useState<{ text: string; error?: boolean } | null>(null);

  const loadCycles = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchProductionCycles();
      const list = Array.isArray(res?.data?.cycles)
        ? res.data.cycles
        : Array.isArray(res?.cycles)
        ? res.cycles
        : [];
      setCycles(list);
      if (list.length > 0 && !selectedCycleId) {
        setSelectedCycleId(list[0].cycle_id);
      }
    } catch (err: any) {
      console.error('Failed to load operational cycles:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedCycleId]);

  useEffect(() => {
    loadCycles();
    const interval = setInterval(loadCycles, 15000);
    return () => clearInterval(interval);
  }, [loadCycles]);

  const loadCycleDetail = useCallback(async () => {
    if (!selectedCycleId) return;
    try {
      const [detailRes, jobsRes] = await Promise.all([
        fetchProductionCycleDetail(selectedCycleId).catch(() => null),
        fetchProductionJobs(selectedCycleId).catch(() => null),
      ]);
      if (detailRes && (detailRes.status === 'SUCCESS' || detailRes.cycle_id)) {
        setCycleDetail(detailRes.data || detailRes);
      }
      if (jobsRes && (jobsRes.status === 'SUCCESS' || Array.isArray(jobsRes.jobs))) {
        setCycleJobs(jobsRes.data?.jobs || jobsRes.jobs || []);
      }
    } catch (e) {
      console.error('Failed to load cycle detail:', e);
    }
  }, [selectedCycleId]);

  useEffect(() => {
    loadCycleDetail();
    const detailInterval = setInterval(loadCycleDetail, 10000);
    return () => clearInterval(detailInterval);
  }, [loadCycleDetail]);

  const handleRetry = async (cycleId: string) => {
    try {
      setRetrying(cycleId);
      setFeedbackMsg(null);
      const res = await postRetryCycle(cycleId);
      setFeedbackMsg({ text: `Retry queued for cycle ${cycleId}: ${res.message || 'Queued'}` });
      await loadCycles();
      await loadCycleDetail();
    } catch (err: any) {
      setFeedbackMsg({ text: `Retry rejected: ${err.message}`, error: true });
    } finally {
      setRetrying(null);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'CYCLE_COMPLETE':
      case 'PUBLISHED':
      case 'SUCCESS':
      case 'VERIFIED':
        return 'text-emerald-400 bg-emerald-950/70 border-emerald-800/80';
      case 'INFERENCING':
      case 'VALIDATING':
      case 'PUBLISHING':
      case 'RUNNING':
        return 'text-cyan-400 bg-cyan-950/70 border-cyan-800/80 animate-pulse';
      case 'WAITING_FOR_DATA':
      case 'QUEUED':
      case 'PENDING':
      case 'EXPECTED':
        return 'text-blue-400 bg-blue-950/70 border-blue-800/80';
      case 'RETRY_PENDING':
        return 'text-amber-400 bg-amber-950/70 border-amber-800/80';
      case 'VALIDATION_FAILED':
      case 'TERMINAL_FAILURE':
      case 'FAILED':
      case 'EXPIRED':
      case 'REAL_DATA_LOST':
        return 'text-rose-400 bg-rose-950/70 border-rose-800/80';
      default:
        return 'text-slate-400 bg-slate-900 border-slate-700';
    }
  };

  const getSlaColor = (sla: string) => {
    switch (sla) {
      case 'ON_TIME':
        return 'text-emerald-400 bg-emerald-950/60 border-emerald-700/60';
      case 'DELAYED':
        return 'text-amber-400 bg-amber-950/60 border-amber-700/60';
      case 'STALE':
      case 'MISSING':
        return 'text-rose-400 bg-rose-950/60 border-rose-700/60';
      default:
        return 'text-slate-400 bg-slate-800 border-slate-700';
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 text-slate-100">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-700/60 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Calendar className="h-7 w-7 text-blue-400" />
              Operational Cycle Manager
            </h1>
            <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/40">
              POSTGRESQL SYNOPTIC ORCHESTRATION
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Tracking 00Z and 12Z synoptic cycles across deterministic lifecycle states from data arrival to observation verification.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              loadCycles();
              loadCycleDetail();
            }}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-medium border border-slate-700 transition"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {feedbackMsg && (
        <div
          className={`p-3 rounded text-xs border ${
            feedbackMsg.error
              ? 'bg-rose-950/60 border-rose-800 text-rose-300'
              : 'bg-emerald-950/60 border-emerald-800 text-emerald-300'
          }`}
        >
          {feedbackMsg.text}
        </div>
      )}

      {/* Main Grid: Left = Table of Cycles, Right = Selected Cycle Detail */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Table of Cycles */}
        <div className="lg:col-span-2 bg-slate-900/60 rounded-xl border border-slate-800 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider font-mono">
              Synoptic Operational Cycles ({cycles.length})
            </h2>
            <span className="text-xs text-slate-400 font-mono">Leads: +6h to +120h</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/90 text-slate-400 uppercase text-[10px] font-mono border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Cycle ID</th>
                  <th className="py-2.5 px-3">Init / Expected</th>
                  <th className="py-2.5 px-3">Freshness / SLA</th>
                  <th className="py-2.5 px-3">Leads</th>
                  <th className="py-2.5 px-3 text-center">Status</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 font-mono text-[11px]">
                {cycles.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-500">
                      No operational cycles recorded in database.
                    </td>
                  </tr>
                ) : (
                  cycles.map((c) => {
                    const isSelected = c.cycle_id === selectedCycleId;
                    return (
                      <tr
                        key={c.cycle_id}
                        onClick={() => setSelectedCycleId(c.cycle_id)}
                        className={`cursor-pointer transition-colors ${
                          isSelected ? 'bg-blue-950/40 border-l-2 border-blue-500' : 'hover:bg-slate-800/40'
                        }`}
                      >
                        <td className="py-3 px-3">
                          <span className="font-bold text-slate-200">{c.cycle_id}</span>
                          <span className="block text-[10px] text-slate-500 font-sans">
                            {c.data_mode || 'SYNTHETIC_DEMO'}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-slate-400">
                          <div>Init: {c.initialization_time ? new Date(c.initialization_time).toLocaleTimeString('en-IN', { hour12: false }) : (c.cycle_time || '00:00Z')}</div>
                          <div className="text-[10px] text-slate-500">Exp: {c.expected_arrival ? new Date(c.expected_arrival).toLocaleTimeString('en-IN', { hour12: false }) : (c.expected_time || '—')}</div>
                        </td>
                        <td className="py-3 px-3 text-slate-300">
                          <span className={`inline-block px-1.5 py-0.5 rounded text-[9px] font-semibold border ${getSlaColor(c.sla_status || 'ON_TIME')}`}>
                            {c.sla_status || 'ON_TIME'}
                          </span>
                          <div className="text-[10px] text-slate-500 mt-0.5">
                            {c.delay_minutes !== null && c.delay_minutes !== undefined ? `${c.delay_minutes} min delay` : 'No delay'}
                          </div>
                        </td>
                        <td className="py-3 px-3 text-slate-300">
                          {c.supported_leads?.length || 9} leads
                          <div className="text-[10px] text-slate-500">
                            {c.completed_leads?.length || (c.executed_leads?.length ?? 0)} done
                          </div>
                        </td>
                        <td className="py-3 px-3 text-center">
                          <span
                            className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold border ${getStatusColor(
                              c.status
                            )}`}
                          >
                            {c.status}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-right">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRetry(c.cycle_id);
                            }}
                            disabled={retrying === c.cycle_id}
                            className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-[11px] border border-slate-700 transition"
                          >
                            {retrying === c.cycle_id ? 'Retrying...' : 'Retry'}
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Selected Cycle Audit Detail */}
        <div className="bg-slate-900/60 rounded-xl border border-slate-800 p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h3 className="text-xs uppercase font-mono font-semibold text-slate-400">
                Cycle Audit & Timeline
              </h3>
              <div className="text-base font-bold text-white font-mono">
                {selectedCycleId || 'Select Cycle'}
              </div>
            </div>
            {cycleDetail && (
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${getStatusColor(
                  cycleDetail.status
                )}`}
              >
                {cycleDetail.status}
              </span>
            )}
          </div>

          {cycleDetail ? (
            <div className="space-y-4 text-xs">
              {/* Lifecycle Progress Bar */}
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-mono">Cycle Flow</span>
                <div className="flex items-center gap-1 mt-1 text-[10px] font-mono text-slate-400">
                  <span className="px-1.5 py-0.5 bg-blue-900/50 rounded text-blue-300">WAITING</span>
                  <ArrowRight className="w-3 h-3 text-slate-600" />
                  <span className="px-1.5 py-0.5 bg-cyan-900/50 rounded text-cyan-300">VALIDATING</span>
                  <ArrowRight className="w-3 h-3 text-slate-600" />
                  <span className="px-1.5 py-0.5 bg-purple-900/50 rounded text-purple-300">INFERENCE</span>
                  <ArrowRight className="w-3 h-3 text-slate-600" />
                  <span className="px-1.5 py-0.5 bg-emerald-900/50 rounded text-emerald-300">PUBLISHED</span>
                </div>
              </div>

              {/* Attributes Grid */}
              <div className="grid grid-cols-2 gap-2 bg-slate-950/60 p-3 rounded-lg border border-slate-800 font-mono text-[11px]">
                <div className="text-slate-500">Data Mode:</div>
                <div className="text-slate-200 text-right">{cycleDetail.data_mode || 'SYNTHETIC_DEMO'}</div>
                <div className="text-slate-500">SLA Status:</div>
                <div className="text-slate-200 text-right">{cycleDetail.sla_status || 'ON_TIME'}</div>
                <div className="text-slate-500">Arrival Delay:</div>
                <div className="text-slate-200 text-right">{cycleDetail.delay_minutes !== null && cycleDetail.delay_minutes !== undefined ? `${cycleDetail.delay_minutes} min` : '0 min'}</div>
                <div className="text-slate-500">Retry Count:</div>
                <div className="text-slate-200 text-right">{cycleDetail.retry_count ?? 0} / 3</div>
                <div className="text-slate-500">NCUM File:</div>
                <div className="text-slate-200 text-right truncate">
                  {cycleDetail.ncum_file || 'Unmounted'}
                </div>
                <div className="text-slate-500">NEPS File:</div>
                <div className="text-slate-200 text-right truncate">
                  {cycleDetail.neps_file || 'Unmounted'}
                </div>
                <div className="text-slate-500">Checksum:</div>
                <div className="text-slate-300 text-right font-mono text-[10px] truncate">
                  {cycleDetail.checksum ? cycleDetail.checksum.slice(0, 12) + '...' : 'Verified SHA-256'}
                </div>
              </div>

              {/* PostgreSQL Cycle Event Timeline */}
              <div>
                <h4 className="text-[10px] uppercase font-mono font-semibold text-slate-400 mb-2">
                  Chronological Event Timeline ({cycleDetail.events?.length || 0})
                </h4>
                <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1">
                  {!cycleDetail.events || cycleDetail.events.length === 0 ? (
                    <div className="text-slate-500 text-center py-2">No cycle events logged.</div>
                  ) : (
                    cycleDetail.events.map((ev: any, idx: number) => (
                      <div
                        key={idx}
                        className="p-2 rounded bg-slate-950/50 border border-slate-800 text-[11px] font-mono space-y-1"
                      >
                        <div className="flex items-center justify-between text-[10px]">
                          <span className="font-semibold text-blue-400">{ev.event_type}</span>
                          <span className="text-slate-500">
                            {ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString('en-IN', { hour12: false }) : '—'}
                          </span>
                        </div>
                        <div className="text-slate-300 text-[11px] font-sans">{ev.message}</div>
                        <div className="flex items-center justify-between text-[9px] text-slate-500">
                          <span>Status: {ev.status}</span>
                          <span>Source: {ev.source || 'SYSTEM'}</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Lead-Time Jobs */}
              <div>
                <h4 className="text-[10px] uppercase font-mono font-semibold text-slate-400 mb-2">
                  Lead-Time Inference Jobs ({cycleJobs.length})
                </h4>
                <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                  {cycleJobs.length === 0 ? (
                    <div className="text-slate-500 text-center py-2">No jobs executed yet.</div>
                  ) : (
                    cycleJobs.map((j) => (
                      <div
                        key={j.job_id}
                        className="flex items-center justify-between p-2 rounded bg-slate-950/40 border border-slate-800 text-[11px] font-mono"
                      >
                        <span className="text-slate-300">+{j.lead_hours}h Forecast</span>
                        <span className="text-slate-500 text-[10px]">{j.model_version}</span>
                        <span
                          className={`px-1.5 py-0.5 rounded text-[9px] font-semibold border ${getStatusColor(
                            j.status
                          )}`}
                        >
                          {j.status}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Failure / Error details if any */}
              {cycleDetail.failure_reason && (
                <div className="p-2.5 rounded bg-rose-950/50 border border-rose-800 text-rose-300 text-[11px]">
                  <strong>Failure Reason:</strong> {cycleDetail.failure_reason}
                </div>
              )}
            </div>
          ) : (
            <div className="py-12 text-center text-slate-500 text-xs">
              Select a cycle from the table to view audit trace.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
