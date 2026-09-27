/**
 * Phase 16 — Real Data Activation Dashboard
 * SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
 * MoES / NCMRWF
 *
 * Visual 5-Stage Progression:
 *   Stage 1: REAL_DATA_DETECTED
 *   Stage 2: REAL_DATA_VALIDATED
 *   Stage 3: REAL_DATA_ELIGIBLE
 *   Stage 4: REAL_OPERATIONAL_READY (Pending Operator Approval)
 *   Stage 5: REAL_OPERATIONAL_ACTIVE (Production Live)
 *
 * Current Status: WAITING_FOR_AUTHORITATIVE_DATA (BLOCKED)
 * No fake bypass buttons; human authorization gate strictly enforced.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldCheck,
  Shield,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Lock,
  Unlock,
  FileCheck,
  Activity,
  UserCheck,
  Send,
} from 'lucide-react';

import {
  fetchActivationStatus,
  fetchActivationValidation,
  fetchActivationAudit,
  postActivationRequest,
  postActivationApprove,
  postActivationReject,
} from '../api/client';

export const ActivationPage: React.FC = () => {
  const [refreshing, setRefreshing] = useState(false);
  const [statusReport, setStatusReport] = useState<any>(null);
  const [gates, setGates] = useState<any[]>([]);
  const [auditTrail, setAuditTrail] = useState<any[]>([]);
  const [selectedCycle, setSelectedCycle] = useState('00Z');
  const selectedSource = 'NCMRWF_NCUM';

  // Form states
  const [operatorId, setOperatorId] = useState('OP_NCMRWF_01');
  const [signature, setSignature] = useState('');
  const [reason, setReason] = useState('00Z synoptic cycle launch');
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setRefreshing(true);
      const [statusRes, valRes, auditRes] = await Promise.all([
        fetchActivationStatus(selectedCycle, selectedSource),
        fetchActivationValidation(selectedCycle, selectedSource),
        fetchActivationAudit(),
      ]);
      setStatusReport(statusRes);
      setGates(valRes.gates || []);
      setAuditTrail(auditRes || []);
      setActionError(null);
    } catch (err: any) {
      console.error('Failed to load activation data:', err);
    } finally {
      setRefreshing(false);
    }
  }, [selectedCycle, selectedSource]);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleRequest = async () => {
    try {
      setActionMessage(null);
      setActionError(null);
      const res = await postActivationRequest(operatorId, selectedSource, selectedCycle, reason);
      setActionMessage(res.message);
      await loadData();
    } catch (err: any) {
      setActionError(err.message);
    }
  };

  const handleApprove = async () => {
    if (!signature.trim()) {
      setActionError('Signature token is required for production authorization.');
      return;
    }
    try {
      setActionMessage(null);
      setActionError(null);
      const res = await postActivationApprove(operatorId, signature);
      setActionMessage(res.message);
      await loadData();
    } catch (err: any) {
      setActionError(err.message);
    }
  };

  const handleReject = async () => {
    try {
      setActionMessage(null);
      setActionError(null);
      const res = await postActivationReject(operatorId, reason || 'Operator abort');
      setActionMessage(res.message);
      await loadData();
    } catch (err: any) {
      setActionError(err.message);
    }
  };

  const stages = [
    { id: 1, name: 'REAL_DATA_DETECTED', label: '1. Data Detected' },
    { id: 2, name: 'REAL_DATA_VALIDATED', label: '2. Data Validated' },
    { id: 3, name: 'REAL_DATA_ELIGIBLE', label: '3. Technical Eligible' },
    { id: 4, name: 'REAL_OPERATIONAL_READY', label: '4. Ready for Approval' },
    { id: 5, name: 'REAL_OPERATIONAL_ACTIVE', label: '5. Operational Active' },
  ];

  const currentStageIndex = () => {
    if (!statusReport) return 0;
    const stage = statusReport.stage;
    if (stage === 'REAL_OPERATIONAL_ACTIVE') return 5;
    if (stage === 'REAL_OPERATIONAL_READY') return 4;
    if (stage === 'REAL_DATA_ELIGIBLE') return 3;
    if (stage === 'REAL_DATA_VALIDATED') return 2;
    if (stage === 'REAL_DATA_DETECTED') return 1;
    return 0; // WAITING_FOR_AUTHORITATIVE_DATA or BLOCKED
  };

  const passedGatesCount = gates.filter((g) => g.is_passed).length;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 text-slate-100">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-700/60 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <ShieldCheck className="h-7 w-7 text-emerald-400" />
              Real-Data Operational Activation Gate
            </h1>
            <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40">
              PHASE 16 GOVERNANCE
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Two-stage 15-gate verification, cryptographic integrity, and human operator authorization for NCMRWF/IMD streams.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedCycle}
            onChange={(e) => setSelectedCycle(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            <option value="00Z">00Z Synoptic Cycle</option>
            <option value="12Z">12Z Synoptic Cycle</option>
          </select>

          <button
            onClick={loadData}
            disabled={refreshing}
            className="flex items-center gap-2 px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-600 rounded-lg text-sm font-medium transition"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin text-emerald-400' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Primary Status Banner */}
      <div className="bg-slate-900 border border-slate-700/80 rounded-xl p-5 shadow-lg">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-slate-400">
              <Activity className="h-3.5 w-3.5 text-cyan-400" />
              Current Operational Status
            </div>
            <div className="flex items-center gap-3">
              <span className="text-2xl font-black tracking-wide text-rose-400">
                {statusReport?.stage || 'WAITING_FOR_AUTHORITATIVE_DATA'}
              </span>
              <span className="px-3 py-0.5 text-xs font-semibold rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/40">
                REAL OPERATIONAL BLOCKED
              </span>
              <span className="px-3 py-0.5 text-xs font-semibold rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/40">
                SYNTHETIC DEMO ACTIVE
              </span>
            </div>
            <p className="text-xs text-slate-400">
              {statusReport?.disclaimer ||
                'Authoritative NCMRWF NCUM/NEPS or IMD gridded files are not mounted. Operational real mode is permanently gated.'}
            </p>
          </div>

          <div className="flex items-center gap-6 bg-slate-800/80 border border-slate-700/50 rounded-lg px-4 py-3">
            <div>
              <div className="text-xs text-slate-400">Technical Gates</div>
              <div className="text-lg font-bold text-white">
                <span className={passedGatesCount === 15 ? 'text-emerald-400' : 'text-amber-400'}>
                  {passedGatesCount}
                </span>{' '}
                / 15
              </div>
            </div>
            <div className="h-8 w-px bg-slate-700" />
            <div>
              <div className="text-xs text-slate-400">Data Mode</div>
              <div className="text-sm font-semibold text-cyan-300">
                {statusReport?.data_mode || 'SYNTHETIC_DEMO'}
              </div>
            </div>
            <div className="h-8 w-px bg-slate-700" />
            <div>
              <div className="text-xs text-slate-400">Operator Sign-Off</div>
              <div className="text-sm font-semibold text-slate-300">
                {statusReport?.operator_approval?.status || 'PENDING_DATA'}
              </div>
            </div>
          </div>
        </div>

        {/* 5-Stage Visual Progression */}
        <div className="mt-6 pt-5 border-t border-slate-800">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Operational Lifecycle Progression
          </div>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            {stages.map((stage) => {
              const activeIdx = currentStageIndex();
              const isPast = activeIdx >= stage.id;
              const isCurrent = activeIdx === stage.id;

              return (
                <div
                  key={stage.id}
                  className={`p-3 rounded-lg border text-xs transition ${
                    isCurrent
                      ? 'bg-emerald-950/40 border-emerald-500 text-emerald-200'
                      : isPast
                      ? 'bg-slate-800/80 border-slate-600 text-slate-200'
                      : 'bg-slate-900/50 border-slate-800 text-slate-500'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold">{stage.label}</span>
                    {isPast ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    ) : (
                      <Lock className="h-3.5 w-3.5 text-slate-500" />
                    )}
                  </div>
                  <div className="text-[10px] text-slate-400">
                    {stage.id <= 3 ? 'Automated Technical Gate' : 'Human Operator Gate'}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* 15 Gates Checklist */}
      <div className="bg-slate-900 border border-slate-700/80 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <FileCheck className="h-5 w-5 text-cyan-400" />
            15-Gate Operational Pre-Activation Verification
          </h2>
          <span className="text-xs text-slate-400">
            All 15 gates must PASS before operator approval can be requested.
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {gates.map((g) => (
            <div
              key={g.gate_id}
              className={`p-3.5 rounded-lg border transition ${
                g.is_passed
                  ? 'bg-slate-800/50 border-emerald-500/30 hover:border-emerald-500/60'
                  : 'bg-slate-800/50 border-rose-500/30 hover:border-rose-500/60'
              }`}
            >
              <div className="flex items-start justify-between gap-2 mb-1.5">
                <span className="text-xs font-mono font-bold text-slate-300">{g.gate_id}</span>
                <span
                  className={`px-2 py-0.5 text-[10px] font-bold rounded-full ${
                    g.is_passed
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                      : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                  }`}
                >
                  {g.status}
                </span>
              </div>
              <div className="text-xs font-semibold text-slate-100">{g.name}</div>
              <div className="text-[11px] text-slate-400 mt-0.5 line-clamp-1">{g.description}</div>
              <div className="text-[10px] text-slate-500 mt-2 font-mono bg-slate-900/60 px-2 py-1 rounded">
                {g.details}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Operator Authorization Control Section */}
      <div className="bg-slate-900 border border-slate-700/80 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <UserCheck className="h-5 w-5 text-amber-400" />
              Human Operator Authorization Gate (Part P)
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Production cutover strictly requires dual operator authentication. Frontend bypass is blocked.
            </p>
          </div>
          <span className="text-xs font-mono text-slate-400">NCMRWF Duty Officer Console</span>
        </div>

        {actionMessage && (
          <div className="p-3 bg-emerald-950/40 border border-emerald-500/60 rounded-lg text-xs text-emerald-300 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" />
            {actionMessage}
          </div>
        )}

        {actionError && (
          <div className="p-3 bg-rose-950/40 border border-rose-500/60 rounded-lg text-xs text-rose-300 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            {actionError}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Operator ID</label>
            <input
              type="text"
              value={operatorId}
              onChange={(e) => setOperatorId(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              placeholder="e.g. OP_NCMRWF_01"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Authorization Signature / Token</label>
            <input
              type="password"
              value={signature}
              onChange={(e) => setSignature(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              placeholder="Required for approval"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Operational Justification</label>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              placeholder="e.g. 00Z Monsoon synoptic cycle launch"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 pt-2">
          <button
            onClick={handleRequest}
            disabled={!statusReport?.can_request_activation}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition ${
              statusReport?.can_request_activation
                ? 'bg-blue-600 hover:bg-blue-500 text-white'
                : 'bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed'
            }`}
          >
            <Send className="h-3.5 w-3.5" />
            Request Activation (Stage 4)
          </button>

          <button
            onClick={handleApprove}
            disabled={!statusReport?.can_approve_activation}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition ${
              statusReport?.can_approve_activation
                ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-900/30'
                : 'bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed'
            }`}
          >
            <Unlock className="h-3.5 w-3.5" />
            Authorize Production Cutover (Stage 5)
          </button>

          <button
            onClick={handleReject}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-rose-950 border border-slate-700 hover:border-rose-700 rounded-lg text-xs font-semibold text-rose-300 transition"
          >
            <XCircle className="h-3.5 w-3.5" />
            Reject / Abort
          </button>

          <span className="text-[11px] text-slate-500 ml-auto italic">
            * Activation buttons are active only when all 15 technical gates pass with authoritative data.
          </span>
        </div>
      </div>

      {/* Immutable Activation Audit Trail */}
      <div className="bg-slate-900 border border-slate-700/80 rounded-xl p-5 shadow-lg space-y-3">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <Shield className="h-4 w-4 text-cyan-400" />
          Immutable Operational Activation Audit Trail (Part Q)
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[10px]">
                <th className="py-2 px-3">Activation ID</th>
                <th className="py-2 px-3">Timestamp (UTC)</th>
                <th className="py-2 px-3">Action</th>
                <th className="py-2 px-3">Operator</th>
                <th className="py-2 px-3">Status</th>
                <th className="py-2 px-3">Data Mode</th>
                <th className="py-2 px-3">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
              {auditTrail.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-4 text-center text-slate-500 italic">
                    No activation audit records registered yet.
                  </td>
                </tr>
              ) : (
                auditTrail.map((rec) => (
                  <tr key={rec.activation_id} className="hover:bg-slate-800/30">
                    <td className="py-2 px-3 text-cyan-400">{rec.activation_id}</td>
                    <td className="py-2 px-3 text-slate-400">{rec.timestamp?.slice(0, 19)}</td>
                    <td className="py-2 px-3 font-semibold text-amber-300">{rec.action}</td>
                    <td className="py-2 px-3 text-slate-200">{rec.operator}</td>
                    <td className="py-2 px-3">
                      <span className="px-2 py-0.5 rounded-full text-[10px] bg-slate-800 border border-slate-700 text-slate-300">
                        {rec.readiness_status}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-xs">{rec.data_mode}</td>
                    <td className="py-2 px-3 font-sans text-slate-400 text-[11px] truncate max-w-xs">
                      {rec.notes}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default ActivationPage;
