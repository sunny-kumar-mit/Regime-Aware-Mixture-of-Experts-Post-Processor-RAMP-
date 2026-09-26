import React, { useState, useEffect } from 'react';
import {
  Sparkles, BarChart2, Layers, AlertTriangle, RefreshCw,
  ChevronRight, Eye, Shield, Zap, Activity
} from 'lucide-react';
import {
  fetchScientificExplainability,
  fetchScientificFeatures,
  fetchScientificExperts,
} from '../api/client';

const REGIME_COLORS: Record<string, string> = {
  ACTIVE_MONSOON: '#22c55e',
  BREAK_MONSOON: '#64748b',
  LOW_DEPRESSION: '#ef4444',
  COASTAL: '#0ea5e9',
  OROGRAPHIC: '#8b5cf6',
  WESTERN_DISTURBANCE: '#f59e0b',
  TRANSITION_OTHER: '#6b7280',
};

const FEATURE_GROUP_COLORS: Record<string, string> = {
  NWP_METEOROLOGY: '#22c55e',
  REGIME_FEATURES: '#8b5cf6',
  SPATIAL_CONTEXT: '#0ea5e9',
  TEMPORAL_CONTEXT: '#f59e0b',
  DERIVED_ATMOSPHERIC: '#06b6d4',
  UNKNOWN: '#64748b',
};

function SyntheticBanner() {
  return (
    <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 px-4 py-3 flex items-start space-x-3">
      <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
      <div className="text-xs text-amber-400/80">
        <span className="font-semibold text-amber-300">SYNTHETIC DEMONSTRATION — </span>
        Attribution derived from synthetic test partition. SHAP_NOT_AVAILABLE — graceful fallback to LightGBM
        gain importance. No observed labels used (leakage-free).
      </div>
    </div>
  );
}

function GateBar({ regime, weight, contribution }: { regime: string; weight: number; contribution: number }) {
  const color = REGIME_COLORS[regime] || '#666';
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="font-mono text-slate-300 text-[11px]">{regime}</span>
        <span className="font-mono text-slate-400">{(weight * 100).toFixed(1)}%</span>
      </div>
      <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${weight * 100}%`, backgroundColor: color }} />
      </div>
      <div className="text-[10px] text-slate-500 text-right">contribution: {contribution.toFixed(2)} mm</div>
    </div>
  );
}

function FeatureImportanceBar({ name, group, importance, rank }: { name: string; group: string; importance: number; rank: number }) {
  const color = FEATURE_GROUP_COLORS[group] || '#666';
  const pct = Math.min(importance * 100 / 0.3, 100);
  return (
    <div className="flex items-center space-x-3 group">
      <div className="w-5 text-[10px] text-slate-500 text-right font-mono">{rank}</div>
      <div className="w-32 text-xs text-slate-300 truncate" title={name}>{name}</div>
      <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-700 group-hover:opacity-80" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <div className="w-12 text-xs font-mono text-slate-200 text-right">{(importance * 100).toFixed(1)}%</div>
      <div className="w-20 text-[10px] text-slate-500 text-right truncate">{group.replace(/_/g, ' ')}</div>
    </div>
  );
}

export const ExplainabilityPage: React.FC = () => {
  const [explainData, setExplainData] = useState<any>(null);
  const [featureData, setFeatureData] = useState<any>(null);
  const [expertData, setExpertData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'prediction' | 'features' | 'experts' | 'matrix'>('prediction');

  const load = async () => {
    setLoading(true);
    try {
      const [exp, feat, expt] = await Promise.allSettled([
        fetchScientificExplainability(),
        fetchScientificFeatures(),
        fetchScientificExperts(),
      ]);
      if (exp.status === 'fulfilled') setExplainData(exp.value);
      if (feat.status === 'fulfilled') setFeatureData(feat.value);
      if (expt.status === 'fulfilled') setExpertData(expt.value);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const explanation = explainData?.data || {};
  const gateWeights: Record<string, number> = explanation.gate_weights || {};
  const weightedContribs: Record<string, number> = explanation.weighted_contributions || {};
  const features = featureData?.data?.feature_importances || [];
  const groupSummary: Record<string, number> = featureData?.data?.group_summary || {};
  const expertMatrix = expertData?.data?.matrix?.matrix || {};
  const expertSummaryTable = expertData?.data?.summary_table || [];

  const sortedRegimes = Object.entries(gateWeights).sort(([, a], [, b]) => b - a);
  const topFeatures = features.slice(0, 20);

  const tabs = [
    { id: 'prediction', label: 'Prediction Breakdown', icon: Eye },
    { id: 'features', label: 'Feature Attribution', icon: BarChart2 },
    { id: 'experts', label: 'Expert Gating', icon: Layers },
    { id: 'matrix', label: 'Regime × Expert', icon: Activity },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center space-x-2">
            <Sparkles className="w-5 h-5 text-monsoon-400" />
            <span>RAMP Explainability (XAI)</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Transparent, scientifically honest explanation of RAMP forecast decisions.
            Feature attribution, expert gating decomposition, and Regime × Expert matrix.
          </p>
        </div>
        <button
          id="xai-refresh-btn"
          onClick={load}
          disabled={loading}
          className="flex items-center space-x-2 text-xs text-slate-400 hover:text-white transition px-3 py-2 rounded-lg border border-slate-700"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>{loading ? 'Loading…' : 'Refresh'}</span>
        </button>
      </div>

      <SyntheticBanner />

      {/* Tabs */}
      <div className="flex space-x-1 p-1 bg-slate-900/60 rounded-xl border border-slate-800 overflow-x-auto">
        {tabs.map(tab => (
          <button
            key={tab.id}
            id={`xai-tab-${tab.id}`}
            onClick={() => setActiveTab(tab.id as any)}
            className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
              activeTab === tab.id
                ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <tab.icon className="w-3.5 h-3.5" />
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Prediction Breakdown */}
      {activeTab === 'prediction' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Input */}
            <div className="glass-card rounded-xl p-5 border border-slate-800 space-y-3">
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center space-x-2">
                <span>Input</span><ChevronRight className="w-3.5 h-3.5" />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-xs text-slate-400">Raw NWP</span>
                  <span className="font-mono text-base font-bold text-slate-200">{explanation.raw_nwp_mm ?? '—'} mm</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-slate-400">Lead Time</span>
                  <span className="font-mono text-sm text-slate-300">{explanation.lead_time_hours ?? '—'}h</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-slate-400">Dominant Regime</span>
                  <span className="font-mono text-sm text-monsoon-300">{explanation.dominant_regime || '—'}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-slate-400">Entropy</span>
                  <span className="font-mono text-sm text-slate-300">{explanation.regime_entropy ?? '—'}</span>
                </div>
              </div>
            </div>

            {/* RAMP Output */}
            <div className="glass-card rounded-xl p-5 border border-emerald-500/30 space-y-3">
              <div className="text-xs font-semibold text-emerald-400 uppercase tracking-wider flex items-center space-x-2">
                <Zap className="w-3.5 h-3.5" />
                <span>RAMP MoE Output</span>
              </div>
              <div className="text-3xl font-bold text-emerald-400 font-mono">
                {explanation.ramp_prediction_mm ?? '—'} mm
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Global ML</span>
                  <span className="font-mono text-slate-300">{explanation.global_ml_prediction_mm ?? '—'} mm</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Top Expert</span>
                  <span className="font-mono text-purple-300 text-[11px]">{explanation.top_expert || '—'}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Expert Weight</span>
                  <span className="font-mono text-slate-300">{explanation.top_expert_weight != null ? (explanation.top_expert_weight * 100).toFixed(1) + '%' : '—'}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Fallback Used</span>
                  <span className={`font-mono text-[11px] px-2 py-0.5 rounded ${explanation.fallback_used ? 'bg-amber-500/10 text-amber-400' : 'bg-emerald-500/10 text-emerald-400'}`}>
                    {explanation.fallback_used ? 'YES' : 'NO'}
                  </span>
                </div>
              </div>
            </div>

            {/* Probabilities */}
            <div className="glass-card rounded-xl p-5 border border-slate-800 space-y-3">
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Extreme Probabilities</div>
              <div className="space-y-3">
                {[
                  { label: '≥0.1 mm Rain', value: explanation.rain_probability, color: '#22c55e' },
                  { label: '≥64.5 mm Heavy', value: explanation.heavy_probability, color: '#f59e0b' },
                  { label: '≥115.6 mm V.Heavy', value: explanation.very_heavy_probability, color: '#ef4444' },
                  { label: '≥204.5 mm Extreme', value: explanation.extreme_probability, color: '#dc2626' },
                ].map(p => (
                  <div key={p.label} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-400">{p.label}</span>
                      <span className="font-mono text-slate-200">{p.value != null ? (p.value * 100).toFixed(1) + '%' : 'N/A'}</span>
                    </div>
                    <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${(p.value || 0) * 100}%`, backgroundColor: p.color }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Gate weights */}
          <div className="glass-panel rounded-2xl p-5 space-y-4">
            <div className="text-xs font-semibold text-white">Expert Gate Weights & Contributions</div>
            <p className="text-xs text-slate-400">
              RAMP = Σ p_k × Expert_k — soft mixture of 7 regime experts. Gate weights = regime probabilities.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {sortedRegimes.map(([regime, weight]) => (
                <GateBar
                  key={regime}
                  regime={regime}
                  weight={weight}
                  contribution={weightedContribs[regime] || 0}
                />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Feature Attribution */}
      {activeTab === 'features' && (
        <div className="space-y-4">
          {/* Group summary */}
          <div className="glass-panel rounded-2xl p-5 space-y-4">
            <div className="text-xs font-semibold text-white">Feature Group Summary</div>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
              {Object.entries(groupSummary).map(([group, importance]) => (
                <div key={group} className="glass-card rounded-xl p-3 border border-slate-800 text-center space-y-1">
                  <div className="w-3 h-3 rounded-full mx-auto" style={{ backgroundColor: FEATURE_GROUP_COLORS[group] || '#666' }} />
                  <div className="text-lg font-bold font-mono" style={{ color: FEATURE_GROUP_COLORS[group] || '#666' }}>
                    {((importance as number) * 100).toFixed(1)}%
                  </div>
                  <div className="text-[10px] text-slate-400 leading-tight">{group.replace(/_/g, ' ')}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Feature importance list */}
          <div className="glass-panel rounded-2xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-xs font-semibold text-white">Top 20 Feature Importances (Gain)</div>
              <div className="flex items-center space-x-1.5">
                <Shield className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-[10px] text-emerald-400 font-semibold">LEAKAGE GUARD ACTIVE</span>
              </div>
            </div>
            <div className="space-y-2.5">
              {topFeatures.map((f: any) => (
                <FeatureImportanceBar
                  key={f.feature_name}
                  name={f.feature_name}
                  group={f.feature_group}
                  importance={f.gain_importance || 0}
                  rank={f.rank_gain || 0}
                />
              ))}
            </div>
            <div className="mt-2 text-[11px] text-slate-500 space-y-1">
              <p>Method: <span className="font-mono text-slate-400">LightGBM GAIN importance</span></p>
              <p>SHAP: <span className="font-mono text-amber-400">SHAP_NOT_AVAILABLE</span> — install <code>shap</code> package for TreeExplainer values</p>
              <p>Leakage Guard: All features validated against LEAKAGE_FEATURES registry before attribution.</p>
            </div>
          </div>
        </div>
      )}

      {/* Expert Gating */}
      {activeTab === 'experts' && (
        <div className="glass-panel rounded-2xl p-5 space-y-4">
          <div className="text-xs font-semibold text-white">Regime → Top Expert Assignments</div>
          <p className="text-xs text-slate-400">
            For each weather regime, shows which expert receives the highest mean gating weight.
            Expected behavior: each regime activates its own expert most strongly (diagonal-dominant matrix).
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-800">
                  {['Regime', 'Top Expert', 'Weight', 'n Samples', 'Gate Entropy'].map(h => (
                    <th key={h} className="px-4 py-2.5 text-left text-slate-400 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {expertSummaryTable.map((row: any, i: number) => (
                  <tr key={row.regime} className={`border-b border-slate-800/50 ${i % 2 === 0 ? 'bg-slate-900/30' : ''}`}>
                    <td className="px-4 py-2.5 font-mono text-monsoon-300 text-[11px]">{row.regime}</td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center space-x-2">
                        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: REGIME_COLORS[row.top_expert] || '#666' }} />
                        <span className="font-mono text-slate-200 text-[11px]">{row.top_expert}</span>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 font-mono text-slate-200">{((row.top_weight || 0) * 100).toFixed(1)}%</td>
                    <td className="px-4 py-2.5 text-slate-400">{row.n_samples}</td>
                    <td className="px-4 py-2.5 font-mono text-slate-400">{(row.gate_entropy || 0).toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-[11px] text-slate-500 italic">
            ⓘ Higher gate entropy = more uncertainty in regime assignment. Expected: TRANSITION_OTHER has highest entropy.
          </p>
        </div>
      )}

      {/* Regime × Expert Matrix */}
      {activeTab === 'matrix' && (
        <div className="space-y-4">
          <div className="glass-panel rounded-2xl p-5 space-y-4 overflow-x-auto">
            <div className="text-xs font-semibold text-white">Regime × Expert Mean Gate Weight Matrix</div>
            <p className="text-xs text-slate-400">
              Rows = observed forecast-time regime. Columns = expert activated.
              Diagonal dominance expected: each regime should mostly activate its own expert.
            </p>
            <div className="min-w-max">
              <table className="text-xs border-collapse">
                <thead>
                  <tr>
                    <th className="p-2 text-left text-slate-400 text-[10px] border border-slate-800 bg-slate-900">Regime ↓ | Expert →</th>
                    {Object.keys(expertMatrix[Object.keys(expertMatrix)[0]] || {}).map((expert) => (
                      <th key={expert} className="p-2 text-center text-slate-400 text-[10px] border border-slate-800 bg-slate-900 font-mono"
                          style={{ minWidth: 90 }}>
                        {expert.replace(/_/g, '_').substring(0, 14)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(expertMatrix).map(([regime, experts]) => (
                    <tr key={regime}>
                      <td className="p-2 font-mono text-monsoon-300 text-[10px] border border-slate-800 bg-slate-900/50">{regime}</td>
                      {Object.entries(experts as Record<string, number>).map(([expert, weight]) => {
                        const isDiag = expert === regime;
                        const bg = isDiag
                          ? `rgba(34, 197, 94, ${weight * 0.7})`
                          : `rgba(139, 92, 246, ${weight * 0.5})`;
                        return (
                          <td key={expert} className="p-2 text-center font-mono text-[10px] border border-slate-800"
                              style={{ backgroundColor: bg, color: weight > 0.2 ? '#fff' : '#94a3b8' }}>
                            {(weight * 100).toFixed(1)}%
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-[11px] text-slate-500 italic">
              Green = diagonal (self-activation). Purple = cross-regime activation. Values = mean gate weight.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
