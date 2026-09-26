import React, { useState, useEffect } from 'react';
import {
  Trophy, ChevronRight, ChevronDown, CloudRain, Layers,
  MapPin, Zap, Sparkles, Award, Activity,
  AlertTriangle, CheckCircle2, RefreshCw, Play, ArrowRight
} from 'lucide-react';
import { fetchScientificJuryDemo, fetchScientificCase } from '../api/client';

const STAGE_ICONS: Record<number, any> = {
  1: AlertTriangle,
  2: CloudRain,
  3: Activity,
  4: Layers,
  5: Zap,
  6: MapPin,
  7: Sparkles,
  8: Award,
};

const STAGE_COLORS: Record<number, string> = {
  1: '#64748b', 2: '#0ea5e9', 3: '#8b5cf6',
  4: '#22c55e', 5: '#f59e0b', 6: '#06b6d4',
  7: '#a855f7', 8: '#10b981',
};

const MODEL_LABELS: Record<string, string> = {
  RAW_NWP: 'Raw NWP',
  MEAN_BIAS: 'Mean Bias',
  QUANTILE_MAPPING: 'Quantile Map',
  GLOBAL_ML: 'Global ML',
  RAMP_MOE: 'RAMP MoE',
  RAMP_EXTREME: 'RAMP+Extreme',
};

const CASE_COLORS: Record<string, string> = {
  ACTIVE_MONSOON: '#22c55e',
  BREAK_MONSOON: '#64748b',
  LOW_DEPRESSION: '#ef4444',
  COASTAL_EVENT: '#0ea5e9',
  OROGRAPHIC_EVENT: '#8b5cf6',
  WESTERN_DISTURBANCE: '#f59e0b',
};

function SyntheticBanner() {
  return (
    <div className="rounded-xl border border-amber-500/40 bg-amber-500/5 px-4 py-3 flex items-start space-x-3">
      <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
      <div className="text-xs text-amber-400/80">
        <span className="font-bold text-amber-300 uppercase tracking-wide">SYNTHETIC DEMONSTRATION ONLY — </span>
        Real IMD/NCMRWF observational archives are NOT currently mounted. This demonstration uses
        synthetic test-partition data. Operational forecast accuracy cannot be claimed.
      </div>
    </div>
  );
}

function PipelineStageCard({
  stage, title, description, color, status, outputs
}: {
  stage: number; title: string; description: string; color: string; status?: string; outputs?: Record<string, any>;
}) {
  const [open, setOpen] = useState(false);
  const Icon = STAGE_ICONS[stage] || Activity;
  return (
    <div className="glass-card rounded-xl border border-slate-800 overflow-hidden">
      <button
        id={`jury-stage-${stage}`}
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center space-x-3 p-4 hover:bg-slate-800/30 transition text-left"
      >
        <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
             style={{ backgroundColor: color + '20', border: `1px solid ${color}40` }}>
          <Icon className="w-4 h-4" style={{ color }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-semibold text-white">Stage {stage}: {title}</div>
          <div className="text-[11px] text-slate-400 mt-0.5 truncate">{description}</div>
        </div>
        {status && (
          <span className={`text-[10px] font-mono px-2 py-0.5 rounded flex-shrink-0 ${
            status === 'COMPLETE' ? 'bg-emerald-500/10 text-emerald-400'
            : status === 'NOT_AVAILABLE' ? 'bg-slate-700 text-slate-500'
            : 'bg-amber-500/10 text-amber-400'
          }`}>{status}</span>
        )}
        {open ? <ChevronDown className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />}
      </button>
      {open && outputs && (
        <div className="border-t border-slate-800 p-4 space-y-2">
          {Object.entries(outputs).filter(([_, v]) => v != null).map(([k, v]) => (
            <div key={k} className="flex items-center justify-between text-xs">
              <span className="text-slate-400 font-mono">{k}</span>
              <span className="font-mono text-slate-200">{typeof v === 'boolean' ? (v ? 'true' : 'false') : String(v)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export const JuryDemoPage: React.FC = () => {
  const [demoData, setDemoData] = useState<any>(null);
  const [caseData, setCaseData] = useState<any>(null);
  const [selectedCase, setSelectedCase] = useState<string>('CASE_001');
  const [loading, setLoading] = useState(true);
  const [caseLoading, setCaseLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const data = await fetchScientificJuryDemo();
      setDemoData(data);
    } catch {}
    setLoading(false);
  };

  const loadCase = async (caseId: string) => {
    setCaseLoading(true);
    try {
      const data = await fetchScientificCase(caseId);
      setCaseData(data);
    } catch {}
    setCaseLoading(false);
  };

  useEffect(() => { load(); }, []);
  useEffect(() => { loadCase(selectedCase); }, [selectedCase]);

  const demo = demoData?.data || {};
  const stages = demo.stages || [];
  const benchmarkSummary = demo.benchmark_summary || [];
  const cases = demo.case_studies || [];
  const explanation = demo.example_explanation || {};
  const regimeExpert = demo.regime_expert_matrix || [];
  const caseDetail = caseData?.data || {};
  const pipelineStages = caseDetail.pipeline_stages || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center space-x-2">
            <Trophy className="w-5 h-5 text-yellow-400" />
            <span>Jury Demonstration — RAMP Phase 10</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Interactive demonstration of the full RAMP pipeline from raw NWP → verified district forecast.
            SIH26080 | Ministry of Earth Sciences | NCMRWF
          </p>
        </div>
        <button
          id="jury-refresh-btn"
          onClick={load}
          disabled={loading}
          className="flex items-center space-x-2 text-xs text-slate-400 hover:text-white transition px-3 py-2 rounded-lg border border-slate-700"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>{loading ? 'Loading…' : 'Refresh'}</span>
        </button>
      </div>

      <SyntheticBanner />

      {/* Pipeline Overview — Interactive Stages */}
      <div className="glass-panel rounded-2xl p-6 space-y-4">
        <div className="flex items-center space-x-3">
          <Play className="w-4 h-4 text-monsoon-400" />
          <div className="text-sm font-semibold text-white">RAMP Pipeline Architecture</div>
        </div>
        <p className="text-xs text-slate-400">
          8-stage end-to-end forecasting pipeline: NWP input through to verified district product.
          Click any stage to explore its inputs and outputs.
        </p>
        <div className="flex flex-wrap items-center gap-2">
          {stages.map((s: any, i: number) => (
            <React.Fragment key={s.stage}>
              <div
                id={`jury-pipeline-stage-${s.stage}`}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium cursor-default"
                style={{
                  backgroundColor: STAGE_COLORS[s.stage] + '15',
                  border: `1px solid ${STAGE_COLORS[s.stage]}30`,
                  color: STAGE_COLORS[s.stage],
                }}
              >
                {React.createElement(STAGE_ICONS[s.stage] || Activity, { className: 'w-3.5 h-3.5' })}
                <span>{s.title}</span>
              </div>
              {i < stages.length - 1 && (
                <ArrowRight className="w-3.5 h-3.5 text-slate-600 flex-shrink-0" />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Benchmark Table */}
      <div className="glass-panel rounded-2xl p-5 space-y-4">
        <div className="flex items-center space-x-3">
          <Award className="w-4 h-4 text-monsoon-400" />
          <div className="text-sm font-semibold text-white">Benchmark Summary (Synthetic Test Partition)</div>
        </div>
        <p className="text-xs text-slate-400">
          Factual comparison of 6 forecast systems. Labels: LOWER_RMSE, NOT_SIGNIFICANT. No model is ranked 'best'.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-800">
                {['Model', 'Version', 'RMSE', 'MAE', 'Bias', 'CSI (Rain)', 'n', 'Availability'].map(h => (
                  <th key={h} className="px-3 py-2.5 text-left text-slate-400 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {benchmarkSummary.map((r: any, i: number) => (
                <tr key={r.model} className={`border-b border-slate-800/50 ${i % 2 === 0 ? 'bg-slate-900/30' : ''}`}>
                  <td className="px-3 py-2.5">
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 rounded-full bg-monsoon-500" />
                      <span className="font-medium text-white">{MODEL_LABELS[r.model] || r.model}</span>
                    </div>
                  </td>
                  <td className="px-3 py-2.5 font-mono text-slate-500 text-[10px]">{r.model_version}</td>
                  <td className="px-3 py-2.5 font-mono text-slate-200">{r.rmse ?? 'N/A'}</td>
                  <td className="px-3 py-2.5 font-mono text-slate-200">{r.mae ?? 'N/A'}</td>
                  <td className={`px-3 py-2.5 font-mono ${(r.bias ?? 0) < 0 ? 'text-blue-400' : 'text-orange-400'}`}>
                    {r.bias != null ? (r.bias > 0 ? '+' : '') + r.bias : 'N/A'}
                  </td>
                  <td className="px-3 py-2.5 font-mono text-emerald-400">{r.csi_rain ?? 'N/A'}</td>
                  <td className="px-3 py-2.5 text-slate-400">{r.n_samples ?? 0}</td>
                  <td className="px-3 py-2.5">
                    <span className={`text-[10px] px-2 py-0.5 rounded font-mono ${
                      r.availability === 'AVAILABLE' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'
                    }`}>{r.availability || 'SYNTHETIC_DEMO'}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Case Studies */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Case selector */}
        <div className="space-y-3">
          <div className="text-sm font-semibold text-white flex items-center space-x-2">
            <MapPin className="w-4 h-4 text-monsoon-400" />
            <span>Case Studies</span>
          </div>
          <div className="space-y-2">
            {cases.map((c: any) => (
              <button
                key={c.case_id}
                id={`jury-case-${c.case_id}`}
                onClick={() => setSelectedCase(c.case_id)}
                className={`w-full text-left px-4 py-3 rounded-xl border transition-all space-y-1 ${
                  selectedCase === c.case_id
                    ? 'border-monsoon-500/40 bg-monsoon-500/10'
                    : 'border-slate-800 bg-slate-900/40 hover:border-slate-700'
                }`}
              >
                <div className="text-xs font-semibold text-white">{c.case_id}</div>
                <div className="text-[11px] text-slate-400 leading-tight">{c.case_label.replace('SYNTHETIC CASE STUDY — ', '')}</div>
                <div className="flex items-center space-x-2 mt-1">
                  <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: CASE_COLORS[c.case_type] || '#666' }} />
                  <span className="text-[10px] font-mono text-slate-500">{c.district}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Case detail */}
        <div className="lg:col-span-2 space-y-4">
          {caseLoading ? (
            <div className="glass-panel rounded-2xl p-6 animate-pulse space-y-3">
              <div className="h-4 bg-slate-700 rounded w-1/2" />
              <div className="h-3 bg-slate-800 rounded w-2/3" />
              <div className="h-24 bg-slate-800 rounded" />
            </div>
          ) : caseDetail.case_id ? (
            <>
              {/* Case header */}
              <div className="glass-panel rounded-2xl p-5 space-y-4">
                <div>
                  <div className="text-xs font-semibold text-amber-400 uppercase tracking-wide">{caseDetail.case_label}</div>
                  <div className="text-sm font-bold text-white mt-1">{caseDetail.district}, {caseDetail.state}</div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    {caseDetail.date} | LT: {caseDetail.lead_time_hours}h | Regime: {caseDetail.regime}
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: 'Raw NWP', value: caseDetail.nwp_rainfall_mm, unit: 'mm', color: '#64748b' },
                    { label: 'RAMP MoE', value: caseDetail.ramp_prediction_mm, unit: 'mm', color: '#22c55e' },
                    { label: 'P(Extreme)', value: caseDetail.extreme_probability != null ? (caseDetail.extreme_probability * 100).toFixed(1) + '%' : 'N/A', unit: '', color: '#ef4444' },
                  ].map(item => (
                    <div key={item.label} className="glass-card rounded-xl p-3 border border-slate-800 text-center">
                      <div className="text-xs text-slate-400">{item.label}</div>
                      <div className="text-lg font-bold font-mono mt-1" style={{ color: item.color }}>
                        {item.value}{item.unit}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="flex items-center space-x-3">
                  <div className={`flex items-center space-x-1.5 text-xs px-2 py-1 rounded ${
                    caseDetail.hotspot_detected ? 'bg-red-500/10 text-red-400' : 'bg-emerald-500/10 text-emerald-400'
                  }`}>
                    {caseDetail.hotspot_detected ? <AlertTriangle className="w-3 h-3" /> : <CheckCircle2 className="w-3 h-3" />}
                    <span>{caseDetail.hotspot_detected ? 'Hotspot Detected' : 'No Hotspot'}</span>
                  </div>
                  <div className="text-xs text-slate-500 font-mono">obs: NOT_AVAILABLE (SYNTHETIC_DEMO)</div>
                </div>
              </div>

              {/* Pipeline stages */}
              <div className="space-y-2">
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Full Pipeline Replay</div>
                {pipelineStages.map((s: any) => (
                  <PipelineStageCard
                    key={s.stage}
                    stage={Object.values({ NWP_INPUT: 1, REGIME_DETECTION: 2, BASELINE_CORRECTION: 3, RAMP_MOE: 4, EXTREME_PROBABILITY: 5, SPATIAL_DISTRICT_PRODUCT: 6, HOTSPOT_DETECTION: 7, VERIFICATION: 8, AUDIT_MANIFEST: 9 })[Object.keys({ NWP_INPUT: 1, REGIME_DETECTION: 2, BASELINE_CORRECTION: 3, RAMP_MOE: 4, EXTREME_PROBABILITY: 5, SPATIAL_DISTRICT_PRODUCT: 6, HOTSPOT_DETECTION: 7, VERIFICATION: 8, AUDIT_MANIFEST: 9 }).indexOf(s.stage)] as number || 1}
                    title={s.stage.replace(/_/g, ' ')}
                    description={s.notes}
                    color={STAGE_COLORS[pipelineStages.indexOf(s) + 1] || '#666'}
                    status={s.status}
                    outputs={s.outputs}
                  />
                ))}
              </div>
            </>
          ) : null}
        </div>
      </div>

      {/* Explainability highlight */}
      {explanation.sample_id && (
        <div className="glass-panel rounded-2xl p-5 space-y-4">
          <div className="flex items-center space-x-3">
            <Sparkles className="w-4 h-4 text-purple-400" />
            <div className="text-sm font-semibold text-white">Forecast Explainability Demo — {explanation.sample_id}</div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
            <div className="space-y-1.5">
              <div className="text-slate-400 font-semibold uppercase tracking-wide text-[10px]">Input</div>
              <div className="flex justify-between"><span className="text-slate-400">Raw NWP</span><span className="font-mono text-white">{explanation.raw_nwp_mm} mm</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Regime</span><span className="font-mono text-monsoon-300 text-[11px]">{explanation.dominant_regime}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Lead Time</span><span className="font-mono text-white">{explanation.lead_time_hours}h</span></div>
            </div>
            <div className="space-y-1.5">
              <div className="text-slate-400 font-semibold uppercase tracking-wide text-[10px]">RAMP Output</div>
              <div className="text-2xl font-bold text-emerald-400 font-mono">{explanation.ramp_prediction_mm} mm</div>
              <div className="flex justify-between"><span className="text-slate-400">Top Expert</span><span className="font-mono text-purple-300 text-[11px]">{explanation.top_expert}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Weight</span><span className="font-mono text-white">{explanation.top_expert_weight != null ? (explanation.top_expert_weight * 100).toFixed(1) + '%' : 'N/A'}</span></div>
            </div>
            <div className="space-y-1.5">
              <div className="text-slate-400 font-semibold uppercase tracking-wide text-[10px]">Probabilities</div>
              {[
                { label: 'Rain', v: explanation.rain_probability },
                { label: 'Heavy', v: explanation.heavy_probability },
                { label: 'V. Heavy', v: explanation.very_heavy_probability },
                { label: 'Extreme', v: explanation.extreme_probability },
              ].map(p => (
                <div key={p.label} className="flex justify-between">
                  <span className="text-slate-400">{p.label}</span>
                  <span className="font-mono text-white">{p.v != null ? (p.v * 100).toFixed(1) + '%' : 'N/A'}</span>
                </div>
              ))}
            </div>
            <div className="space-y-1.5">
              <div className="text-slate-400 font-semibold uppercase tracking-wide text-[10px]">Top Features</div>
              {(explanation.top_features || []).slice(0, 4).map((f: any) => (
                <div key={f.feature_name} className="flex justify-between">
                  <span className="text-slate-400 truncate max-w-[100px]" title={f.feature_name}>{f.feature_name}</span>
                  <span className="font-mono text-white">{((f.gain_importance || 0) * 100).toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Regime × Expert summary */}
      {regimeExpert.length > 0 && (
        <div className="glass-panel rounded-2xl p-5 space-y-4">
          <div className="flex items-center space-x-3">
            <Layers className="w-4 h-4 text-monsoon-400" />
            <div className="text-sm font-semibold text-white">Regime → Expert Activation</div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
            {regimeExpert.map((row: any) => (
              <div key={row.regime} className="glass-card rounded-xl p-3 border border-slate-800 text-center space-y-1.5">
                <div className="text-[9px] font-mono text-slate-400 leading-tight">{row.regime.replace(/_/g, ' ')}</div>
                <div className="text-[10px] font-mono text-monsoon-300 truncate" title={row.top_expert}>
                  {row.top_expert?.replace(/_/g, ' ').substring(0, 12)}
                </div>
                <div className="text-xs font-bold text-white">{((row.top_weight || 0) * 100).toFixed(0)}%</div>
                <div className="text-[9px] text-slate-500">n={row.n_samples}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
