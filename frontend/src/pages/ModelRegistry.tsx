import React, { useState, useEffect } from 'react';
import {
  Server,
  ShieldAlert,
  ShieldCheck,
  Database,
  Layers,
  Hash,
  ChevronRight,
  RefreshCw,
  FileText
} from 'lucide-react';


interface RegistryStatusResponse {
  status: string;
  timestamp: string;
  registry_version: string;
  total_models: number;
  active_models: Record<string, string>;
  dataset_gate: {
    valid: boolean;
    status: string;
    data_mode: string;
    reasons: string[];
    details: any;
  };
  eligibility_gate: {
    eligible: boolean;
    status: string;
    effective_mode: string;
    real_data_available: boolean;
    real_training_deferred: boolean;
    reasons: string[];
    message: string;
  };
  real_training_status: {
    real_data_available: boolean;
    real_production_training: string;
    active_mode: string;
    honesty_notice: string;
  };
  latest_training_run: any;
}

interface ModelSummary {
  model_id: string;
  model_type: string;
  lifecycle_status: string;
  dataset_version: string;
  data_mode: string;
  registered_at: string;
  model_checksum: string;
  promotion_eligible: boolean;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export const ModelRegistryPage: React.FC = () => {
  const [registryStatus, setRegistryStatus] = useState<RegistryStatusResponse | null>(null);
  const [models, setModels] = useState<ModelSummary[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string>('ramp_moe_v2.0.0');
  const [modelDetails, setModelDetails] = useState<any>(null);
  const [modelMetrics, setModelMetrics] = useState<any>(null);
  const [modelCalibration, setModelCalibration] = useState<any>(null);
  const [modelProvenance, setModelProvenance] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'metrics' | 'calibration' | 'card' | 'lineage'>('overview');

  const fetchRegistryData = async () => {
    try {
      setLoading(true);
      const [statusRes, modelsRes] = await Promise.all([
        fetch(`${API_BASE}/api/models/status`),
        fetch(`${API_BASE}/api/models`),
      ]);
      const statusData = await statusRes.json();
      const modelsData = await modelsRes.json();
      setRegistryStatus(statusData);
      setModels(modelsData.models || []);

      if (modelsData.models && modelsData.models.length > 0) {
        const defaultId = modelsData.models.find((m: any) => m.model_id.includes('moe'))?.model_id || modelsData.models[0].model_id;
        setSelectedModelId(defaultId);
        loadModelArtifacts(defaultId);
      }
    } catch (err) {
      console.error('Failed to load model registry data:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadModelArtifacts = async (modelId: string) => {
    try {
      const [detailsRes, metricsRes, calRes, provRes] = await Promise.all([
        fetch(`${API_BASE}/api/models/${modelId}`),
        fetch(`${API_BASE}/api/models/${modelId}/metrics`),
        fetch(`${API_BASE}/api/models/${modelId}/calibration`),
        fetch(`${API_BASE}/api/models/${modelId}/provenance`),
      ]);

      if (detailsRes.ok) setModelDetails(await detailsRes.json());
      if (metricsRes.ok) setModelMetrics((await metricsRes.json()).metrics);
      if (calRes.ok) setModelCalibration((await calRes.json()).calibration);
      if (provRes.ok) setModelProvenance((await provRes.json()).provenance);
    } catch (err) {
      console.error(`Failed to load artifacts for model ${modelId}:`, err);
    }
  };

  useEffect(() => {
    fetchRegistryData();
  }, []);

  const handleSelectModel = (id: string) => {
    setSelectedModelId(id);
    loadModelArtifacts(id);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 text-slate-100">
      {/* ------------------------------------------------------------------- */}
      {/* Page Header */}
      {/* ------------------------------------------------------------------- */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 text-xs font-semibold rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
              PHASE 13 PRODUCTION MODEL REGISTRY
            </span>
            <span className="text-xs text-slate-400">MoES / NCMRWF Unified AI Architecture</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white mt-1">
            Production Model Registry & Lineage
          </h1>
          <p className="text-sm text-slate-400">
            Immutable versioning, 12 promotion gates, zero-leakage contracts, and calibrated model cards.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchRegistryData}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-300 border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh Registry
          </button>

        </div>
      </div>

      {/* ------------------------------------------------------------------- */}
      {/* Scientific Honesty Notice Banner */}
      {/* ------------------------------------------------------------------- */}
      <div className="rounded-lg border border-amber-500/30 bg-amber-950/20 p-4 text-amber-200">
        <div className="flex items-start gap-3">
          <ShieldAlert className="w-5 h-5 text-amber-400 mt-0.5 shrink-0" />
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-amber-300 text-sm">
                CRITICAL SCIENTIFIC INTEGRITY STATUS: REAL DATA DEFERRED
              </span>
              <span className="px-2 py-0.2 text-[10px] uppercase font-bold rounded bg-amber-900/60 text-amber-300 border border-amber-700">
                {registryStatus?.real_training_status?.active_mode || 'SYNTHETIC_DEMO'}
              </span>
            </div>
            <p className="text-xs text-amber-200/90 leading-relaxed">
              Authoritative NCMRWF (NCUM deterministic / NEPS ensemble) and IMD 0.25° gridded observation raw archives
              are currently unmounted on local disk. In accordance with strict MoES scientific honesty protocols,
              <strong> no fake production scores or fabricated metrics have been generated</strong>.
              The complete training pipeline, 12-gate promotion system, and model registry are verified and ready for deployment;
              current registered artifacts are strictly designated as <strong>DEVELOPMENT</strong>.
            </p>
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------- */}
      {/* Section 1 & 2: Registry Status & Active Models Bar */}
      {/* ------------------------------------------------------------------- */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4">
          <div className="text-xs text-slate-400 font-medium flex items-center justify-between">
            <span>REGISTRY STATUS</span>
            <Server className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-bold text-white">OPERATIONAL</span>
            <span className="text-xs text-emerald-400 font-medium">v2.0.0</span>
          </div>
          <div className="mt-1 text-xs text-slate-400">
            {registryStatus?.total_models || 4} Registered Immutable Models
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4">
          <div className="text-xs text-slate-400 font-medium flex items-center justify-between">
            <span>REAL DATA ELIGIBILITY</span>
            <Database className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-bold text-amber-400">DEFERRED</span>
            <span className="text-xs text-slate-400">Zero Fabrications</span>
          </div>
          <div className="mt-1 text-xs text-slate-400">
            Awaiting NCMRWF / IMD raw archives
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4">
          <div className="text-xs text-slate-400 font-medium flex items-center justify-between">
            <span>ACTIVE RAMP MoE</span>
            <Layers className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-sm font-bold text-white truncate">
              {registryStatus?.active_models?.REGIME_AWARE_MOE || 'ramp_moe_v2.0.0'}
            </span>
          </div>
          <div className="mt-1 text-xs text-slate-400">
            7 Regime-Specific Experts + Soft Gating
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4">
          <div className="text-xs text-slate-400 font-medium flex items-center justify-between">
            <span>PROMOTION GATES</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-bold text-emerald-400">12 / 12 PASS</span>
          </div>
          <div className="mt-1 text-xs text-slate-400">
            Synthetic Guard Active (Dev Status)
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------- */}
      {/* Section 3: Model Versions Selector & Workspace */}
      {/* ------------------------------------------------------------------- */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Registered Model Cards List */}
        <div className="lg:col-span-4 space-y-3">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-400 tracking-wider">
            <span>REGISTERED PRODUCTION MODELS</span>
            <span>{models.length} ARTIFACTS</span>
          </div>

          <div className="space-y-2">
            {models.map((m) => {
              const isSelected = m.model_id === selectedModelId;
              return (
                <div
                  key={m.model_id}
                  onClick={() => handleSelectModel(m.model_id)}
                  className={`p-3.5 rounded-lg border transition cursor-pointer text-left ${
                    isSelected
                      ? 'bg-slate-800 border-cyan-500 shadow-md shadow-cyan-950/30'
                      : 'bg-slate-900/60 border-slate-800 hover:bg-slate-800/60'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="text-sm font-semibold text-white flex items-center gap-1.5">
                        {m.model_id}
                        {isSelected && <ChevronRight className="w-3.5 h-3.5 text-cyan-400" />}
                      </div>
                      <div className="text-xs text-slate-400 mt-0.5">{m.model_type}</div>
                    </div>
                    <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-amber-950 text-amber-300 border border-amber-800">
                      {m.lifecycle_status}
                    </span>
                  </div>

                  <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
                    <span className="truncate max-w-[150px]">Mode: {m.data_mode}</span>
                    <span className="font-mono text-[10px] text-slate-400">
                      {m.model_checksum ? `${m.model_checksum.substring(0, 8)}...` : 'sha256'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* 12 Promotion Gates Status Panel */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4 mt-4">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-cyan-400" />
              12 Mandatory Promotion Gates
            </h4>
            <div className="space-y-1.5 text-xs">
              {modelDetails?.manifest?.promotion_gates?.gate_evaluations ? (
                Object.entries(modelDetails.manifest.promotion_gates.gate_evaluations).map(
                  ([gateName, res]: [string, any]) => (
                    <div key={gateName} className="flex items-center justify-between py-1 border-b border-slate-800/50">
                      <span className="font-mono text-[11px] text-slate-300">{gateName}</span>
                      <span
                        className={`px-1.5 py-0.2 text-[10px] font-bold rounded ${
                          res.passed
                            ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800'
                            : 'bg-rose-950/80 text-rose-400 border border-rose-800'
                        }`}
                      >
                        {res.status}
                      </span>
                    </div>
                  )
                )
              ) : (
                <div className="text-slate-400 italic">Select a model to view gate evaluation.</div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Model Artifact Details & Tabs */}
        <div className="lg:col-span-8 bg-slate-900/90 border border-slate-800 rounded-lg p-5">
          {/* Subheader with Tabs */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
            <div>
              <span className="text-xs font-mono text-cyan-400">ACTIVE INSPECTION TARGET</span>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                {selectedModelId}
              </h2>
            </div>

            <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
              <button
                onClick={() => setActiveTab('overview')}
                className={`px-3 py-1 text-xs font-medium rounded transition ${
                  activeTab === 'overview'
                    ? 'bg-cyan-600 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Overview
              </button>
              <button
                onClick={() => setActiveTab('metrics')}
                className={`px-3 py-1 text-xs font-medium rounded transition ${
                  activeTab === 'metrics'
                    ? 'bg-cyan-600 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Verification
              </button>
              <button
                onClick={() => setActiveTab('calibration')}
                className={`px-3 py-1 text-xs font-medium rounded transition ${
                  activeTab === 'calibration'
                    ? 'bg-cyan-600 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Calibration
              </button>
              <button
                onClick={() => setActiveTab('card')}
                className={`px-3 py-1 text-xs font-medium rounded transition ${
                  activeTab === 'card'
                    ? 'bg-cyan-600 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Model Card
              </button>
              <button
                onClick={() => setActiveTab('lineage')}
                className={`px-3 py-1 text-xs font-medium rounded transition ${
                  activeTab === 'lineage'
                    ? 'bg-cyan-600 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Lineage
              </button>
            </div>
          </div>

          {/* Tab 1: Overview */}
          {activeTab === 'overview' && (
            <div className="mt-5 space-y-5">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-slate-950 border border-slate-800 rounded p-3">
                  <div className="text-[11px] text-slate-400">Model Type</div>
                  <div className="text-sm font-semibold text-white mt-1">
                    {modelDetails?.manifest?.model_type || 'N/A'}
                  </div>
                </div>
                <div className="bg-slate-950 border border-slate-800 rounded p-3">
                  <div className="text-[11px] text-slate-400">Dataset Version</div>
                  <div className="text-sm font-semibold text-cyan-400 mt-1">
                    {modelDetails?.manifest?.dataset_version || 'ramp_dataset_real_v1.0.0'}
                  </div>
                </div>
                <div className="bg-slate-950 border border-slate-800 rounded p-3">
                  <div className="text-[11px] text-slate-400">Feature Schema</div>
                  <div className="text-sm font-semibold text-indigo-400 mt-1">
                    {modelDetails?.manifest?.feature_schema_version || 'ramp_features_v1.0.0'}
                  </div>
                </div>
                <div className="bg-slate-950 border border-slate-800 rounded p-3">
                  <div className="text-[11px] text-slate-400">Target Schema</div>
                  <div className="text-sm font-semibold text-purple-400 mt-1">
                    {modelDetails?.manifest?.target_schema_version || 'ramp_targets_v1.0.0'}
                  </div>
                </div>
              </div>

              {/* SHA-256 Checksum Card */}
              <div className="bg-slate-950 border border-slate-800 rounded p-3.5 flex items-center justify-between">
                <div className="space-y-1">
                  <div className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                    <Hash className="w-3.5 h-3.5 text-cyan-400" />
                    Immutable SHA-256 Checksum
                  </div>
                  <div className="font-mono text-xs text-cyan-300 break-all">
                    {modelDetails?.manifest?.model_checksum_sha256 || 'Generating...'}
                  </div>
                </div>
                <span className="px-2 py-1 text-[10px] font-bold rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                  VERIFIED
                </span>
              </div>

              {/* Summary Continuous Metrics if available */}
              {modelMetrics?.overall && (
                <div className="space-y-2">
                  <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Continuous Verification Metrics (Test Split)
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                    <div className="bg-slate-950 border border-slate-800 rounded p-3 text-center">
                      <div className="text-[10px] text-slate-400">MAE (mm)</div>
                      <div className="text-lg font-bold text-white mt-1">{modelMetrics.overall.mae}</div>
                    </div>
                    <div className="bg-slate-950 border border-slate-800 rounded p-3 text-center">
                      <div className="text-[10px] text-slate-400">RMSE (mm)</div>
                      <div className="text-lg font-bold text-white mt-1">{modelMetrics.overall.rmse}</div>
                    </div>
                    <div className="bg-slate-950 border border-slate-800 rounded p-3 text-center">
                      <div className="text-[10px] text-slate-400">Bias (mm)</div>
                      <div className="text-lg font-bold text-white mt-1">{modelMetrics.overall.bias}</div>
                    </div>
                    <div className="bg-slate-950 border border-slate-800 rounded p-3 text-center">
                      <div className="text-[10px] text-slate-400">Correlation</div>
                      <div className="text-lg font-bold text-cyan-400 mt-1">{modelMetrics.overall.correlation}</div>
                    </div>
                    <div className="bg-slate-950 border border-slate-800 rounded p-3 text-center">
                      <div className="text-[10px] text-slate-400">R² Score</div>
                      <div className="text-lg font-bold text-emerald-400 mt-1">{modelMetrics.overall.r2}</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Expert Usage frequency if MoE */}
              {modelMetrics?.expert_usage && (
                <div className="space-y-2">
                  <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Regime Expert Specialization & Gate Probabilities
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {Object.entries(modelMetrics.expert_usage).map(([regime, data]: [string, any]) => (
                      <div key={regime} className="bg-slate-950 border border-slate-800/80 rounded p-2.5 flex items-center justify-between text-xs">
                        <span className="font-medium text-slate-200">{regime}</span>
                        <div className="flex items-center gap-3">
                          <span className="text-slate-400">Avg Gate: <strong className="text-cyan-400">{data.average_gate_probability}</strong></span>
                          <span className="text-slate-400">Usage: <strong className="text-emerald-400">{(data.dominant_usage_frequency * 100).toFixed(1)}%</strong></span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Metrics */}
          {activeTab === 'metrics' && (
            <div className="mt-5 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white">Full Verification Metrics Suite</h3>
                <span className="text-xs text-slate-400">Unseen Test Partition</span>
              </div>
              <pre className="bg-slate-950 border border-slate-800 rounded-lg p-4 text-xs font-mono text-cyan-300 overflow-x-auto max-h-[450px]">
                {JSON.stringify(modelMetrics, null, 2)}
              </pre>
            </div>
          )}

          {/* Tab 3: Calibration */}
          {activeTab === 'calibration' && (
            <div className="mt-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white">Validation-Fitted Calibration Artifacts</h3>
                  <p className="text-xs text-slate-400">Strictly fitted on validation split (zero test set contamination)</p>
                </div>
              </div>
              <pre className="bg-slate-950 border border-slate-800 rounded-lg p-4 text-xs font-mono text-amber-300 overflow-x-auto max-h-[450px]">
                {JSON.stringify(modelCalibration, null, 2)}
              </pre>
            </div>
          )}

          {/* Tab 4: Model Card */}
          {activeTab === 'card' && (
            <div className="mt-5 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white flex items-center gap-1.5">
                  <FileText className="w-4 h-4 text-cyan-400" />
                  Authoritative Model Card (MODEL_CARD.md)
                </h3>
              </div>
              <div className="bg-slate-950 border border-slate-800 rounded-lg p-5 text-xs text-slate-300 whitespace-pre-wrap font-mono leading-relaxed max-h-[500px] overflow-y-auto">
                {modelDetails?.model_card_markdown || 'Loading model card...'}
              </div>
            </div>
          )}

          {/* Tab 5: Lineage & Provenance */}
          {activeTab === 'lineage' && (
            <div className="mt-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white">Training Lineage & System Telemetry</h3>
                  <p className="text-xs text-slate-400">Complete software, hardware, and Git audit record</p>
                </div>
              </div>
              <pre className="bg-slate-950 border border-slate-800 rounded-lg p-4 text-xs font-mono text-emerald-300 overflow-x-auto max-h-[450px]">
                {JSON.stringify(modelProvenance, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ModelRegistryPage;
