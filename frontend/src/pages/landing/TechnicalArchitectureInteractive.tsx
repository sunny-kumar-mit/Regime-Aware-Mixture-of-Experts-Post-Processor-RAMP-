import React, { useState } from 'react';
import { CheckCircle2, Layers, Cpu, ShieldCheck } from 'lucide-react';
import { ARCHITECTURE_LAYERS, ArchitectureLayer } from './landingData';

export const TechnicalArchitectureInteractive: React.FC = () => {
  const [activeLayer, setActiveLayer] = useState<ArchitectureLayer>(ARCHITECTURE_LAYERS[1]); // Default to Feature Engine (Layer 02)

  return (
    <div className="space-y-8">
      {/* Layer Step Selector Bar */}
      <div className="flex items-center space-x-2 overflow-x-auto pb-2 border-b border-slate-800">
        {ARCHITECTURE_LAYERS.map((layer) => {
          const isActive = activeLayer.id === layer.id;
          return (
            <button
              key={layer.id}
              onClick={() => setActiveLayer(layer)}
              className={`px-4 py-2.5 rounded-xl text-xs font-mono transition-all flex items-center space-x-2.5 whitespace-nowrap border ${
                isActive
                  ? 'bg-cyan-950/80 text-cyan-300 border-cyan-500/60 font-bold shadow-lg shadow-cyan-950/50 -translate-y-0.5'
                  : 'bg-slate-900/60 text-slate-400 border-slate-800/80 hover:text-slate-200 hover:border-slate-700'
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-cyan-400 animate-ping' : 'bg-slate-600'}`} />
              <span className="opacity-75">{layer.number}</span>
              <span>{layer.name}</span>
            </button>
          );
        })}
      </div>

      {/* Layer Deep Dive Architectural Schematic */}
      <div className="p-8 rounded-3xl bg-gradient-to-b from-[#081224] to-[#060D1A] border border-cyan-900/50 shadow-2xl relative overflow-hidden">
        {/* Ambient Top Glow */}
        <div className="absolute top-0 right-0 w-80 h-80 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

        {/* Layer Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-8 pb-6 border-b border-slate-800">
          <div>
            <div className="flex items-center space-x-2 mb-1">
              <span className="text-xs font-mono text-cyan-400 font-bold bg-cyan-950/80 px-2.5 py-0.5 rounded border border-cyan-800/60">
                LAYER {activeLayer.number}
              </span>
              <span className="text-xs font-mono text-slate-500">ID: {activeLayer.id}</span>
            </div>
            <h3 className="text-2xl sm:text-3xl font-extrabold text-white mt-1">
              {activeLayer.name}
            </h3>
            <p className="text-sm text-slate-300 mt-1 max-w-2xl leading-relaxed">
              {activeLayer.tagline}
            </p>
          </div>

          <div className="px-4 py-2 rounded-xl bg-slate-900/90 border border-slate-700/80 text-xs font-mono text-cyan-300 flex items-center space-x-2 shadow-sm">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>QC &amp; Performance: {activeLayer.metricsOrQC}</span>
          </div>
        </div>

        {/* Data Flow Architecture Grid: Ingested Inputs -> Governing Logic -> Emitted Outputs */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          {/* Column 1: Ingested Inputs (4 cols) */}
          <div className="lg:col-span-4 p-5 rounded-2xl bg-slate-950/70 border border-slate-800/80 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-bold flex items-center space-x-1.5">
                  <Layers className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Ingested Inputs</span>
                </h4>
                <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950 px-1.5 py-0.5 rounded">
                  {activeLayer.inputs.length} Streams
                </span>
              </div>
              <ul className="space-y-2.5">
                {activeLayer.inputs.map((inp, idx) => (
                  <li key={idx} className="flex items-start space-x-2.5 text-xs text-slate-300 bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/60">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 mt-1.5 flex-shrink-0" />
                    <span className="leading-relaxed">{inp}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-800/60 text-[10px] font-mono text-slate-500">
              Validated with schema contracts
            </div>
          </div>

          {/* Column 2: Governing Mathematical Logic & Scientific Purpose (4 cols) */}
          <div className="lg:col-span-4 space-y-4 flex flex-col justify-between">
            <div className="p-5 rounded-2xl bg-slate-950/70 border border-cyan-950/60 flex-1">
              <h4 className="text-xs font-mono uppercase tracking-wider text-cyan-400 font-bold mb-2 flex items-center space-x-1.5">
                <Cpu className="w-3.5 h-3.5 text-cyan-400" />
                <span>Scientific Purpose</span>
              </h4>
              <p className="text-xs text-slate-300 leading-relaxed">
                {activeLayer.scientificPurpose}
              </p>
            </div>

            <div className="p-5 rounded-2xl bg-slate-950/70 border border-cyan-950/60 flex-1">
              <h4 className="text-xs font-mono uppercase tracking-wider text-cyan-400 font-bold mb-2">
                Governing Numerical Logic
              </h4>
              <p className="text-xs text-slate-300 leading-relaxed font-mono text-[11px] bg-slate-900/80 p-2.5 rounded-xl border border-slate-800">
                {activeLayer.governingLogic}
              </p>
            </div>
          </div>

          {/* Column 3: Emitted Outputs (4 cols) */}
          <div className="lg:col-span-4 p-5 rounded-2xl bg-slate-950/70 border border-slate-800/80 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-xs font-mono uppercase tracking-wider text-emerald-400 font-bold flex items-center space-x-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Emitted Outputs</span>
                </h4>
                <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950 px-1.5 py-0.5 rounded">
                  {activeLayer.outputs.length} Artifacts
                </span>
              </div>
              <ul className="space-y-2.5">
                {activeLayer.outputs.map((out, idx) => (
                  <li key={idx} className="flex items-start space-x-2.5 text-xs text-emerald-200 bg-emerald-950/20 p-2.5 rounded-xl border border-emerald-900/30">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
                    <span className="leading-relaxed">{out}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-800/60 text-[10px] font-mono text-emerald-500/80">
              Immutable provenance verified
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
export default TechnicalArchitectureInteractive;
