import React from 'react';
import { CloudRain, MapPin, Grid, Layers, ShieldCheck, Compass } from 'lucide-react';

export const ForecastCorrectionPage: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-white flex items-center space-x-2">
          <CloudRain className="w-5 h-5 text-monsoon-400" />
          <span>Regime-Aware Rainfall Forecast Correction</span>
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Post-processing grid space, lead-time staging, and baseline comparative architecture.
        </p>
      </div>

      {/* Scientific Integrity Staging Notice */}
      <div className="rounded-xl border border-monsoon-500/40 bg-monsoon-950/30 p-5 space-y-2">
        <div className="flex items-center space-x-2 text-monsoon-300 font-semibold text-sm">
          <ShieldCheck className="w-5 h-5 text-monsoon-400" />
          <span>Phase 1 Inference Staging Area</span>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed">
          Per SIH26080 constraints, <strong>no fake ML predictions or simulated rainfall fields are fabricated</strong> in Phase 1.
          This interface is structured to consume real MLflow model artifacts once trained in Phase 3.
          The grid specifications, geographic projection, and lead-time contracts are formally locked below.
        </p>
      </div>

      {/* Grid Domain Specifications */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass-card rounded-xl p-5 space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase">
            <span>India Domain Extent</span>
            <MapPin className="w-4 h-4 text-monsoon-400" />
          </div>
          <div className="text-xl font-bold text-white font-mono">6.5°N – 38.5°N</div>
          <div className="text-xl font-bold text-white font-mono">66.5°E – 100.5°E</div>
          <p className="text-[11px] text-slate-400 pt-1">Standard IMD & NCMRWF Indian landmass & coastal bounding box</p>
        </div>

        <div className="glass-card rounded-xl p-5 space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase">
            <span>Harmonised Grid Spec</span>
            <Grid className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">0.25° × 0.25°</div>
          <div className="text-sm font-semibold text-slate-300">129 × 137 Points = 17,673 Cells</div>
          <p className="text-[11px] text-slate-400 pt-1">Bilinear interpolation with land-sea conservative masking</p>
        </div>

        <div className="glass-card rounded-xl p-5 space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase">
            <span>Target Lead Times</span>
            <Layers className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">Day 1 to Day 5</div>
          <div className="text-sm font-semibold text-slate-300">24h, 48h, 72h, 96h, 120h</div>
          <p className="text-[11px] text-slate-400 pt-1">Accumulated daily rainfall ending at 08:30 IST (03:00 UTC)</p>
        </div>
      </div>

      {/* Model Baselines Comparison Matrix */}
      <div className="glass-panel rounded-2xl p-6 space-y-4">
        <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
          <Compass className="w-4 h-4 text-monsoon-400" />
          <span>Post-Processing Pipeline Comparison Tiers</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {[
            { tag: 'raw_nwp', name: 'Raw NWP', desc: 'Uncorrected model forecast directly from NCUM/GFS numerical integration.' },
            { tag: 'mean_bias', name: 'Mean Bias', desc: 'Stationary spatial bias subtractive correction based on rolling historical climatology.' },
            { tag: 'qmap', name: 'Quantile Mapping', desc: 'Empirical cumulative distribution function (ECDF) matching per grid cell.' },
            { tag: 'global_ml', name: 'Global ML (No Regimes)', desc: 'Single monolithic gradient boosted regressor unaware of atmospheric regimes.' },
            { tag: 'ramp', name: 'RAMP (Ours)', desc: 'Regime-Aware Mixture-of-Experts dynamically routed via soft probability vectors.' },
          ].map((m) => (
            <div key={m.tag} className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 space-y-2">
              <div className="text-[11px] font-mono text-monsoon-400 font-semibold">{m.tag}</div>
              <div className="text-xs font-semibold text-white">{m.name}</div>
              <p className="text-[11px] text-slate-400 leading-snug">{m.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
