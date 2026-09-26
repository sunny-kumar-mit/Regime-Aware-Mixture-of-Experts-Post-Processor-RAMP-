import React, { useEffect, useState } from 'react';
import {
  CloudRain,
  ShieldCheck,
  Cpu,
  Layers,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
} from 'lucide-react';
import { fetchHealth } from '../api/client';
import { HealthResponse } from '../types/api';

export const DashboardPage: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    fetchHealth()
      .then((h) => setHealth(h))
      .catch((e) => console.error('Failed to load dashboard data:', e));
  }, []);

  const pipelineStages = [
    { title: 'NWP Ingestion', desc: 'NCUM, NEPS, GFS, GEFS & IMD Observation Bundles', status: 'Ready' },
    { title: 'Harmonisation', desc: '0.25° Common India Grid (6.5°-38.5°N, 66.5°-100.5°E)', status: 'Ready' },
    { title: 'Feature Engine', desc: '23 Atmospheric variables (LLJ, MTMI, Shear, CAPE, DEM)', status: 'Contracted' },
    { title: 'Regime Classifier', desc: '7-Class Soft Probability Distribution (LightGBM)', status: 'Design Locked' },
    { title: 'MoE Combiner', desc: 'Per-Regime Bias Correction Expert Mixture', status: 'Design Locked' },
    { title: 'Extreme Calibrator', desc: 'Exceedance Probability (64.5, 115.6, 204.5 mm)', status: 'Design Locked' },
    { title: 'Verification', desc: 'RMSE, CSI, POD, FAR, ETS, FSS vs IMD Gridded Obs', status: 'Design Locked' },
  ];

  return (
    <div className="space-y-6">
      {/* Welcome Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-slate-850 to-monsoon-950 p-6 md:p-8 border border-slate-800 shadow-2xl">
        <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-monsoon-500/10 border border-monsoon-500/30 text-monsoon-300 text-xs font-medium">
              <span className="w-2 h-2 rounded-full bg-monsoon-400 animate-ping" />
              <span>Phase 1 Foundation Active</span>
            </div>
            <h2 className="text-2xl md:text-3xl font-bold text-white tracking-tight">
              Regime-Aware Mixture-of-Experts Post-Processor (RAMP)
            </h2>
            <p className="text-slate-300 text-sm leading-relaxed">
              Targeted meteorological AI post-processing designed for NCMRWF/MoES. Dynamically conditions rainfall
              bias corrections on 7 distinct Indian monsoon weather regimes and calibrates heavy precipitation risks.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-3">
            <div className="px-4 py-3 rounded-xl bg-slate-900/80 border border-slate-800 text-center min-w-[140px]">
              <div className="text-xs text-slate-400 font-medium">Backend Health</div>
              <div className="text-lg font-bold text-emerald-400 flex items-center justify-center space-x-1 mt-0.5">
                <CheckCircle2 className="w-4 h-4" />
                <span>{health?.status === 'healthy' ? 'Operational' : 'Connecting'}</span>
              </div>
            </div>

            <div className="px-4 py-3 rounded-xl bg-slate-900/80 border border-slate-800 text-center min-w-[140px]">
              <div className="text-xs text-slate-400 font-medium">Data Integrity Mode</div>
              <div className="text-sm font-bold text-amber-400 font-mono mt-1">
                {health?.data_mode || 'SYNTHETIC_DEMO'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-card rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Configured Regimes</span>
            <CloudRain className="w-5 h-5 text-monsoon-400" />
          </div>
          <div className="text-3xl font-bold text-white">7 Regimes</div>
          <p className="text-xs text-slate-400">Soft probabilistic classification, no hard labels</p>
        </div>

        <div className="glass-card rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Atmospheric Features</span>
            <Layers className="w-5 h-5 text-indigo-400" />
          </div>
          <div className="text-3xl font-bold text-white">23 Inputs</div>
          <p className="text-xs text-slate-400">Dynamic, thermodynamic, moisture & terrain variables</p>
        </div>

        <div className="glass-card rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">IMD Rain Thresholds</span>
            <AlertTriangle className="w-5 h-5 text-amber-400" />
          </div>
          <div className="text-3xl font-bold text-white">3 Tiers</div>
          <p className="text-xs text-slate-400">≥64.5 mm (Heavy), ≥115.6 (Very Heavy), ≥204.5 (Extremely)</p>
        </div>

        <div className="glass-card rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Benchmark Baselines</span>
            <TrendingUp className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="text-3xl font-bold text-white">5 Models</div>
          <p className="text-xs text-slate-400">raw_nwp, mean_bias, qmap, global_ml vs RAMP</p>
        </div>
      </div>

      {/* Pipeline Stage Architecture Overview */}
      <div className="glass-panel rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-white flex items-center space-x-2">
            <Cpu className="w-5 h-5 text-monsoon-400" />
            <span>End-to-End RAMP Pipeline Architecture</span>
          </h3>
          <span className="text-xs text-slate-400">Sequential Execution Guarantee</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-7 gap-3 pt-2">
          {pipelineStages.map((stage, idx) => (
            <div
              key={idx}
              className="bg-slate-900/60 rounded-xl p-3.5 border border-slate-800 flex flex-col justify-between space-y-2 hover:border-slate-700 transition-colors"
            >
              <div>
                <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 mb-1">
                  <span>Stage 0{idx + 1}</span>
                  <span className="text-monsoon-400 font-semibold text-[10px] bg-monsoon-950/60 px-1 rounded">
                    {stage.status}
                  </span>
                </div>
                <div className="text-sm font-semibold text-slate-200">{stage.title}</div>
                <p className="text-[11px] text-slate-400 mt-1 leading-snug">{stage.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Scientific Integrity Notice */}
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 flex items-start space-x-3.5">
        <ShieldCheck className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-1 text-xs text-slate-300">
          <span className="font-semibold text-amber-300">Phase 1 Scientific Integrity Guarantee:</span>
          <p className="text-slate-400">
            Per SIH26080 guidelines, this phase initializes the system contracts, interfaces, endpoints, and UI shell.
            No fake ML outputs or fabricated forecast accuracy metrics are presented. Machine learning weights and
            regime routing will be introduced in subsequent model training phases.
          </p>
        </div>
      </div>
    </div>
  );
};
