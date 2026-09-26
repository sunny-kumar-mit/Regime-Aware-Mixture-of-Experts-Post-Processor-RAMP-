import React, { useState, useEffect } from 'react';
import {
  Award, Activity, Target, BarChart2, GitBranch,
  Clock, AlertTriangle, RefreshCw, Shield
} from 'lucide-react';
import {
  fetchScientificVerification,
  fetchScientificThresholds,
  fetchScientificRegimes,
  fetchScientificLeadTime,
  fetchScientificBootstrap,
  fetchScientificCalibration,
  fetchScientificFailures,
} from '../api/client';

const MODEL_COLORS: Record<string, string> = {
  RAW_NWP: '#64748b',
  MEAN_BIAS: '#0ea5e9',
  QUANTILE_MAPPING: '#8b5cf6',
  GLOBAL_ML: '#f59e0b',
  RAMP_MOE: '#22c55e',
  RAMP_EXTREME: '#06b6d4',
};

const MODEL_LABELS: Record<string, string> = {
  RAW_NWP: 'Raw NWP',
  MEAN_BIAS: 'Mean Bias',
  QUANTILE_MAPPING: 'Quantile Map',
  GLOBAL_ML: 'Global ML',
  RAMP_MOE: 'RAMP MoE',
  RAMP_EXTREME: 'RAMP+Extreme',
};

function SyntheticBanner() {
  return (
    <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 px-4 py-3 flex items-start space-x-3">
      <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
      <div>
        <div className="text-xs font-semibold text-amber-300">SYNTHETIC DEMONSTRATION DATA</div>
        <div className="text-xs text-amber-400/80 mt-0.5">
          Real IMD/NCMRWF observational archives are NOT currently mounted. All metrics are
          derived from synthetic test partition and labeled SYNTHETIC_DEMO. Operational accuracy
          cannot be claimed from these figures.
        </div>
      </div>
    </div>
  );
}

function MetricBar({ label, value, max, color, n }: { label: string; value: number | null; max: number; color: string; n?: number }) {
  if (value == null) return (
    <div className="flex items-center space-x-3">
      <div className="w-24 text-xs text-slate-400 truncate">{MODEL_LABELS[label] || label}</div>
      <div className="flex-1 h-2 bg-slate-800 rounded-full" />
      <div className="text-xs text-slate-600 w-16 text-right">N/A</div>
    </div>
  );
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="flex items-center space-x-3">
      <div className="w-24 text-xs text-slate-300 truncate">{MODEL_LABELS[label] || label}</div>
      <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <div className="text-xs font-mono text-slate-200 w-16 text-right">
        {value.toFixed(2)} {n !== undefined && <span className="text-slate-500">(n={n})</span>}
      </div>
    </div>
  );
}

function SectionHeader({ icon: Icon, title, subtitle }: { icon: any; title: string; subtitle?: string }) {
  return (
    <div className="flex items-center space-x-3">
      <div className="p-2 rounded-lg bg-monsoon-500/10 border border-monsoon-500/20">
        <Icon className="w-4 h-4 text-monsoon-400" />
      </div>
      <div>
        <div className="text-sm font-semibold text-white">{title}</div>
        {subtitle && <div className="text-xs text-slate-400 mt-0.5">{subtitle}</div>}
      </div>
    </div>
  );
}


export const VerificationPage: React.FC = () => {
  const [verifData, setVerifData] = useState<any>(null);
  const [threshData, setThreshData] = useState<any>(null);
  const [regimeData, setRegimeData] = useState<any>(null);
  const [ltData, setLtData] = useState<any>(null);
  const [bootData, setBootData] = useState<any>(null);
  const [calibData, setCalibData] = useState<any>(null);
  const [failData, setFailData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'continuous' | 'threshold' | 'regime' | 'lead-time' | 'calibration' | 'bootstrap' | 'failures'>('continuous');
  const [selectedThreshold, setSelectedThreshold] = useState<string>('0.1');

  const load = async () => {
    setLoading(true);
    try {
      const [verif, thresh, reg, lt, boot, calib, fail] = await Promise.allSettled([
        fetchScientificVerification(),
        fetchScientificThresholds(),
        fetchScientificRegimes(),
        fetchScientificLeadTime(),
        fetchScientificBootstrap(),
        fetchScientificCalibration(),
        fetchScientificFailures(),
      ]);
      if (verif.status === 'fulfilled') setVerifData(verif.value);
      if (thresh.status === 'fulfilled') setThreshData(thresh.value);
      if (reg.status === 'fulfilled') setRegimeData(reg.value);
      if (lt.status === 'fulfilled') setLtData(lt.value);
      if (boot.status === 'fulfilled') setBootData(boot.value);
      if (calib.status === 'fulfilled') setCalibData(calib.value);
      if (fail.status === 'fulfilled') setFailData(fail.value);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const continuousRows: any[] = verifData?.data || [];
  const threshRows: any[] = threshData?.data || [];
  const regimeRows: any[] = regimeData?.data || [];
  const ltRows: any[] = ltData?.data || [];
  const bootRows: any[] = bootData?.data || [];
  const failSummary = failData?.data || {};

  // Lead-time: group by model
  const ltByModel: Record<string, any[]> = {};
  for (const row of ltRows) {
    if (!ltByModel[row.model]) ltByModel[row.model] = [];
    ltByModel[row.model].push(row);
  }

  // Threshold: filter by selected
  const thr = parseFloat(selectedThreshold);
  const filteredThresh = threshRows.filter((r: any) => r.threshold_mm === thr);

  // Bootstrap: RMSE comparisons only
  const rmseBoots = bootRows.filter((r: any) => r.metric === 'rmse');

  const maxRMSE = Math.max(...continuousRows.map((r: any) => r.rmse || 0), 20);
  const maxMAE = Math.max(...continuousRows.map((r: any) => r.mae || 0), 15);

  const tabs = [
    { id: 'continuous', label: 'Continuous', icon: Activity },
    { id: 'threshold', label: 'Thresholds', icon: Target },
    { id: 'regime', label: 'Regimes', icon: GitBranch },
    { id: 'lead-time', label: 'Lead Time', icon: Clock },
    { id: 'calibration', label: 'Calibration', icon: BarChart2 },
    { id: 'bootstrap', label: 'Bootstrap', icon: Shield },
    { id: 'failures', label: 'Failures', icon: AlertTriangle },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center space-x-2">
            <Award className="w-5 h-5 text-monsoon-400" />
            <span>Scientific Verification & Benchmark</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Phase 10 — Transparent, reproducible verification across 6 forecast systems.
            Factual metric labels only. No subjective rankings.
          </p>
        </div>
        <button
          id="verif-refresh-btn"
          onClick={load}
          disabled={loading}
          className="flex items-center space-x-2 text-xs text-slate-400 hover:text-white transition px-3 py-2 rounded-lg border border-slate-700 hover:border-slate-600"
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
            id={`verif-tab-${tab.id}`}
            onClick={() => setActiveTab(tab.id as any)}
            className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
              activeTab === tab.id
                ? 'bg-monsoon-500/20 text-monsoon-300 border border-monsoon-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <tab.icon className="w-3.5 h-3.5" />
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Continuous */}
      {activeTab === 'continuous' && (
        <div className="space-y-4">
          <div className="glass-panel rounded-2xl p-6 space-y-4">
            <SectionHeader icon={Activity} title="Continuous Metrics" subtitle="RMSE, MAE, Bias, Pearson r" />
            {loading ? (
              <div className="space-y-2">
                {[1,2,3,4,5,6].map(i => <div key={i} className="h-5 bg-slate-800 rounded animate-pulse" />)}
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="space-y-3">
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">RMSE (mm) — Lower is factually smaller error</div>
                  {continuousRows.map((r: any) => (
                    <MetricBar key={r.model} label={r.model} value={r.rmse} max={maxRMSE} color={MODEL_COLORS[r.model] || '#666'} n={r.n_samples} />
                  ))}
                </div>
                <div className="space-y-3">
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">MAE (mm)</div>
                  {continuousRows.map((r: any) => (
                    <MetricBar key={r.model} label={r.model} value={r.mae} max={maxMAE} color={MODEL_COLORS[r.model] || '#666'} n={r.n_samples} />
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="glass-card rounded-xl border border-slate-800 overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-800 text-xs font-semibold text-slate-400 uppercase tracking-wider">Full Metric Table</div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-800">
                    {['Model', 'RMSE', 'MAE', 'Bias', 'Pearson r', 'n', 'Availability'].map(h => (
                      <th key={h} className="px-4 py-2.5 text-left text-slate-400 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {continuousRows.map((r: any, i: number) => (
                    <tr key={r.model} className={`border-b border-slate-800/50 ${i % 2 === 0 ? 'bg-slate-900/30' : ''}`}>
                      <td className="px-4 py-2.5">
                        <div className="flex items-center space-x-2">
                          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: MODEL_COLORS[r.model] || '#666' }} />
                          <span className="font-medium text-white">{MODEL_LABELS[r.model] || r.model}</span>
                        </div>
                      </td>
                      <td className="px-4 py-2.5 font-mono text-slate-200">{r.rmse ?? 'N/A'}</td>
                      <td className="px-4 py-2.5 font-mono text-slate-200">{r.mae ?? 'N/A'}</td>
                      <td className={`px-4 py-2.5 font-mono ${(r.bias ?? 0) < 0 ? 'text-blue-400' : 'text-orange-400'}`}>{r.bias != null ? (r.bias > 0 ? '+' : '') + r.bias : 'N/A'}</td>
                      <td className="px-4 py-2.5 font-mono text-slate-200">{r.pearson_r ?? 'N/A'}</td>
                      <td className="px-4 py-2.5 text-slate-400">{r.n_samples ?? 0}</td>
                      <td className="px-4 py-2.5">
                        <span className={`text-[10px] px-2 py-0.5 rounded font-mono ${
                          r.availability === 'AVAILABLE' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'
                        }`}>{r.availability || r.data_mode}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Threshold */}
      {activeTab === 'threshold' && (
        <div className="space-y-4">
          <div className="glass-panel rounded-2xl p-5 space-y-4">
            <SectionHeader icon={Target} title="Threshold Verification" subtitle="POD / FAR / CSI / ETS per IMD threshold" />
            <div className="flex space-x-2">
              {['0.1', '64.5', '115.6', '204.5'].map(t => (
                <button
                  key={t}
                  id={`threshold-btn-${t}`}
                  onClick={() => setSelectedThreshold(t)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all ${
                    selectedThreshold === t
                      ? 'bg-monsoon-500/20 text-monsoon-300 border border-monsoon-500/30'
                      : 'bg-slate-800 text-slate-400 border border-slate-700 hover:border-slate-600'
                  }`}
                >
                  ≥{t} mm
                </button>
              ))}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-800">
                    {['Model', 'Threshold', 'Events', 'POD', 'FAR', 'CSI', 'ETS', 'Bias Score', 'Status'].map(h => (
                      <th key={h} className="px-3 py-2.5 text-left text-slate-400 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filteredThresh.map((r: any, i: number) => (
                    <tr key={r.model} className={`border-b border-slate-800/50 ${i % 2 === 0 ? 'bg-slate-900/30' : ''}`}>
                      <td className="px-3 py-2.5">
                        <div className="flex items-center space-x-2">
                          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: MODEL_COLORS[r.model] || '#666' }} />
                          <span className="font-medium text-white">{MODEL_LABELS[r.model] || r.model}</span>
                        </div>
                      </td>
                      <td className="px-3 py-2.5 font-mono text-slate-300">{r.threshold_name}</td>
                      <td className="px-3 py-2.5 text-slate-400">{r.n_events ?? 0}</td>
                      <td className="px-3 py-2.5 font-mono text-slate-200">{r.pod ?? 'N/A'}</td>
                      <td className="px-3 py-2.5 font-mono text-slate-200">{r.far ?? 'N/A'}</td>
                      <td className="px-3 py-2.5 font-mono text-emerald-400">{r.csi ?? 'N/A'}</td>
                      <td className="px-3 py-2.5 font-mono text-blue-400">{r.ets ?? 'N/A'}</td>
                      <td className="px-3 py-2.5 font-mono text-slate-200">{r.bias_score ?? 'N/A'}</td>
                      <td className="px-3 py-2.5">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                          r.availability_status === 'AVAILABLE' ? 'bg-emerald-500/10 text-emerald-400'
                          : r.availability_status === 'NO_EVENTS_IN_DOMAIN' ? 'bg-slate-800 text-slate-500'
                          : 'bg-amber-500/10 text-amber-400'
                        }`}>{r.availability_status}</span>
                      </td>
                    </tr>
                  ))}
                  {filteredThresh.length === 0 && !loading && (
                    <tr>
                      <td colSpan={9} className="px-4 py-8 text-center text-slate-500 text-xs">
                        No data available for threshold ≥{selectedThreshold} mm
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Regime */}
      {activeTab === 'regime' && (
        <div className="glass-panel rounded-2xl p-5 space-y-4">
          <SectionHeader icon={GitBranch} title="Regime-Stratified Verification" subtitle="RAMP MoE performance per weather regime (forecast-time only)" />
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-800">
                  {['Regime', 'RMSE', 'MAE', 'Bias', 'Pearson r', 'Heavy CSI', 'Heavy POD', 'n', 'Status'].map(h => (
                    <th key={h} className="px-3 py-2.5 text-left text-slate-400 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {regimeRows.map((r: any, i: number) => (
                  <tr key={r.regime} className={`border-b border-slate-800/50 ${i % 2 === 0 ? 'bg-slate-900/30' : ''}`}>
                    <td className="px-3 py-2.5 font-mono text-monsoon-300 text-[11px]">{r.regime}</td>
                    <td className="px-3 py-2.5 font-mono text-slate-200">{r.rmse ?? 'N/A'}</td>
                    <td className="px-3 py-2.5 font-mono text-slate-200">{r.mae ?? 'N/A'}</td>
                    <td className={`px-3 py-2.5 font-mono ${(r.bias ?? 0) < 0 ? 'text-blue-400' : 'text-orange-400'}`}>{r.bias != null ? (r.bias > 0 ? '+' : '') + r.bias : 'N/A'}</td>
                    <td className="px-3 py-2.5 font-mono text-slate-200">{r.pearson_r ?? 'N/A'}</td>
                    <td className="px-3 py-2.5 font-mono text-emerald-400">{r.heavy_csi ?? 'N/A'}</td>
                    <td className="px-3 py-2.5 font-mono text-slate-200">{r.heavy_pod ?? 'N/A'}</td>
                    <td className="px-3 py-2.5 text-slate-400">{r.n_samples}</td>
                    <td className="px-3 py-2.5">
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                        r.availability_status === 'AVAILABLE' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'
                      }`}>{r.availability_status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-[11px] text-slate-500 italic">
            ⓘ Uses Phase 4 forecast-time regime assignments only. Future observed regimes are never used (leakage prevention).
          </p>
        </div>
      )}

      {/* Lead-time */}
      {activeTab === 'lead-time' && (
        <div className="glass-panel rounded-2xl p-5 space-y-4">
          <SectionHeader icon={Clock} title="Lead-Time Verification" subtitle="Day 1–5 performance degradation curves" />
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-800">
                  {['Model', 'Day', 'Lead (h)', 'RMSE', 'MAE', 'Bias', 'CSI', 'POD', 'FAR', 'n'].map(h => (
                    <th key={h} className="px-3 py-2.5 text-left text-slate-400 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ltRows.filter((r: any) => ['RAMP_MOE', 'RAW_NWP'].includes(r.model)).map((r: any, i: number) => (
                  <tr key={`${r.model}-${r.lead_time_hours}`} className={`border-b border-slate-800/50 ${i % 2 === 0 ? 'bg-slate-900/30' : ''}`}>
                    <td className="px-3 py-2.5">
                      <div className="flex items-center space-x-2">
                        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: MODEL_COLORS[r.model] || '#666' }} />
                        <span className="font-medium text-white text-[11px]">{MODEL_LABELS[r.model] || r.model}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-slate-300">{r.lead_time_name}</td>
                    <td className="px-3 py-2.5 font-mono text-slate-400">{r.lead_time_hours}h</td>
                    <td className="px-3 py-2.5 font-mono text-slate-200">{r.rmse ?? 'N/A'}</td>
                    <td className="px-3 py-2.5 font-mono text-slate-200">{r.mae ?? 'N/A'}</td>
                    <td className="px-3 py-2.5 font-mono text-slate-200">{r.bias ?? 'N/A'}</td>
                    <td className="px-3 py-2.5 font-mono text-emerald-400">{r.csi ?? 'N/A'}</td>
                    <td className="px-3 py-2.5 font-mono text-slate-200">{r.pod ?? 'N/A'}</td>
                    <td className="px-3 py-2.5 font-mono text-slate-200">{r.far ?? 'N/A'}</td>
                    <td className="px-3 py-2.5 text-slate-400">{r.n_samples}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-[11px] text-slate-500 italic">Showing RAMP MoE and Raw NWP for clarity. All 6 models available in /api/scientific/lead-time.</p>
        </div>
      )}

      {/* Calibration */}
      {activeTab === 'calibration' && (
        <div className="space-y-4">
          <div className="glass-panel rounded-2xl p-5 space-y-4">
            <SectionHeader icon={BarChart2} title="Probability Calibration" subtitle="Brier Score, ECE, BSS for Phase 7 exceedance probabilities" />
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {Object.entries(calibData?.data || {}).map(([thr, metrics]: any) => (
                <div key={thr} className="glass-card rounded-xl p-4 border border-slate-800 space-y-3">
                  <div className="text-xs font-semibold text-slate-400 uppercase">≥ {thr} mm</div>
                  <div className={`text-[10px] font-mono px-2 py-0.5 rounded inline-block ${
                    metrics.availability_status === 'AVAILABLE' ? 'bg-emerald-500/10 text-emerald-400'
                    : 'bg-slate-800 text-slate-500'
                  }`}>{metrics.availability_status}</div>
                  {metrics.brier != null ? (
                    <div className="space-y-1.5 text-xs">
                      <div className="flex justify-between"><span className="text-slate-400">Brier</span><span className="font-mono text-slate-200">{metrics.brier}</span></div>
                      <div className="flex justify-between"><span className="text-slate-400">BSS</span><span className="font-mono text-slate-200">{metrics.bss ?? 'N/A'}</span></div>
                      <div className="flex justify-between"><span className="text-slate-400">ECE</span><span className="font-mono text-slate-200">{metrics.ece}</span></div>
                      <div className="flex justify-between"><span className="text-slate-400">MCE</span><span className="font-mono text-slate-200">{metrics.mce}</span></div>
                      <div className="flex justify-between"><span className="text-slate-400">Log Loss</span><span className="font-mono text-slate-200">{metrics.log_loss}</span></div>
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500 italic">Insufficient events in synthetic domain for this threshold.</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Bootstrap */}
      {activeTab === 'bootstrap' && (
        <div className="glass-panel rounded-2xl p-5 space-y-4">
          <SectionHeader icon={Shield} title="Paired Bootstrap Significance" subtitle="300 bootstrap samples, seed=42, 95% CI — RMSE comparisons vs RAW_NWP" />
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-800">
                  {['Model A', 'vs', 'Metric', 'Δ', 'CI Lower', 'CI Upper', 'p-value', 'n', 'Conclusion'].map(h => (
                    <th key={h} className="px-3 py-2.5 text-left text-slate-400 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rmseBoots.map((r: any, i: number) => (
                  <tr key={`${r.model_a}-${r.metric}-${i}`} className={`border-b border-slate-800/50 ${i % 2 === 0 ? 'bg-slate-900/30' : ''}`}>
                    <td className="px-3 py-2.5">
                      <div className="flex items-center space-x-1.5">
                        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: MODEL_COLORS[r.model_a] || '#666' }} />
                        <span className="text-white font-medium">{MODEL_LABELS[r.model_a] || r.model_a}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-slate-500">vs</td>
                    <td className="px-3 py-2.5 font-mono text-slate-400 uppercase">{r.metric}</td>
                    <td className={`px-3 py-2.5 font-mono ${(r.difference ?? 0) < 0 ? 'text-emerald-400' : 'text-orange-400'}`}>
                      {r.difference != null ? (r.difference > 0 ? '+' : '') + r.difference : 'N/A'}
                    </td>
                    <td className="px-3 py-2.5 font-mono text-slate-400">{r.ci_lower ?? 'N/A'}</td>
                    <td className="px-3 py-2.5 font-mono text-slate-400">{r.ci_upper ?? 'N/A'}</td>
                    <td className="px-3 py-2.5 font-mono text-slate-300">{r.p_value_approx ?? 'N/A'}</td>
                    <td className="px-3 py-2.5 text-slate-400">{r.n_samples}</td>
                    <td className="px-3 py-2.5">
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                        r.conclusion === 'LOWER_RMSE' ? 'bg-emerald-500/10 text-emerald-400'
                        : r.conclusion === 'NOT_SIGNIFICANT' ? 'bg-slate-700 text-slate-400'
                        : 'bg-orange-500/10 text-orange-400'
                      }`}>{r.conclusion}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-[11px] text-slate-500 italic">
            ⓘ Labels are factual only: LOWER_RMSE, NOT_SIGNIFICANT, SAMPLE_LIMITED. No model is ranked 'best'.
          </p>
        </div>
      )}

      {/* Failures */}
      {activeTab === 'failures' && (
        <div className="space-y-4">
          <div className="glass-panel rounded-2xl p-5 space-y-4">
            <SectionHeader icon={AlertTriangle} title="Failure Analysis" subtitle="Missed events, false alarms, underpredictions" />
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
              {[
                { label: 'Underpredictions', value: failSummary?.n_underprediction, color: 'text-orange-400' },
                { label: 'Overpredictions', value: failSummary?.n_overprediction, color: 'text-red-400' },
                { label: 'Missed Heavy', value: failSummary?.n_miss_heavy, color: 'text-rose-400' },
                { label: 'False Alarms', value: failSummary?.n_false_alarm_heavy, color: 'text-amber-400' },
                { label: 'Large Divergence', value: failSummary?.n_large_divergence, color: 'text-purple-400' },
              ].map(item => (
                <div key={item.label} className="glass-card rounded-xl p-4 border border-slate-800 text-center space-y-1">
                  <div className={`text-2xl font-bold ${item.color}`}>{item.value ?? '—'}</div>
                  <div className="text-[11px] text-slate-400">{item.label}</div>
                </div>
              ))}
            </div>
            <div className="mt-2">
              <div className="text-xs text-slate-400 mb-3 font-semibold">Synthetic Failure Case Catalog</div>
              <div className="space-y-2">
                {(failSummary?.failure_cases || []).map((c: any) => (
                  <div key={c.case_id} className="glass-card rounded-lg p-3 border border-slate-800 flex items-center justify-between">
                    <div className="space-y-0.5">
                      <div className="text-xs font-semibold text-white">{c.district}, {c.state}</div>
                      <div className="text-[11px] text-slate-400 font-mono">{c.regime} | LT {c.lead_time_hours}h</div>
                    </div>
                    <div className="text-right space-y-0.5">
                      <div className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                        c.failure_type === 'MISS_HEAVY' ? 'bg-rose-500/10 text-rose-400'
                        : c.failure_type === 'FALSE_ALARM_HEAVY' ? 'bg-amber-500/10 text-amber-400'
                        : c.failure_type === 'UNDERPREDICTION' ? 'bg-orange-500/10 text-orange-400'
                        : 'bg-slate-700 text-slate-400'
                      }`}>{c.failure_type}</div>
                      <div className="text-[10px] text-slate-500">RAMP: {c.ramp_prediction_mm} mm</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <p className="text-[11px] text-slate-500 italic">
              ⓘ Observed errors (ramp_error_mm) are NULL in SYNTHETIC_DEMO mode. Real archives required for observed error analysis.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
