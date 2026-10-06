import React, { useState, useEffect, useRef } from 'react';
import {
  Database,
  Cpu,
  Layers,
  GitBranch,
  CloudRain,
  MapPin,
  CheckCircle2,
  ArrowRight,
  Play,
  Pause,
  Sparkles,
  ChevronRight,
  Clock
} from 'lucide-react';
import { ARCHITECTURE_LAYERS, ArchitectureLayer } from './landingData';

const STAGE_ICONS = [
  Database,   // Stage 01: Data Ingestion & QC
  Cpu,        // Stage 02: Feature Engine
  Layers,     // Stage 03: Regime Classifier
  GitBranch,  // Stage 04: MoE
  CloudRain,  // Stage 05: Extreme Rainfall Engine
  MapPin,     // Stage 06: Spatial Aggregation
  CheckCircle2 // Stage 07: Verification
];

export const SolutionPipelineInteractive: React.FC = () => {
  const [activeStageIdx, setActiveStageIdx] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const cycleTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Auto-cycle through the 7 stages every 4 seconds
  useEffect(() => {
    if (!isPlaying) return;

    cycleTimerRef.current = setInterval(() => {
      setActiveStageIdx((prev) => (prev + 1) % ARCHITECTURE_LAYERS.length);
    }, 4200);

    return () => {
      if (cycleTimerRef.current) clearInterval(cycleTimerRef.current);
    };
  }, [isPlaying]);

  const activeLayer: ArchitectureLayer = ARCHITECTURE_LAYERS[activeStageIdx];

  return (
    <div className="space-y-8">
      {/* Pipeline Navigation & Stage Controller */}
      <div className="p-3.5 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-md flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center space-x-3 text-xs font-mono">
          <div className="flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-cyan-950/80 border border-cyan-800/50 text-cyan-300">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            <span className="font-semibold">7-STAGE OPERATIONAL PIPELINE</span>
          </div>
          <span className="text-slate-400 hidden sm:inline">
            Active: Stage {activeLayer.number} / 07
          </span>
        </div>

        {/* Step Buttons */}
        <div className="flex items-center space-x-1.5 overflow-x-auto max-w-full pb-1 md:pb-0">
          {ARCHITECTURE_LAYERS.map((layer, idx) => {
            const isActive = activeStageIdx === idx;
            return (
              <button
                key={layer.id}
                onClick={() => {
                  setActiveStageIdx(idx);
                  setIsPlaying(false);
                }}
                className={`px-2.5 py-1.5 rounded-xl text-xs font-mono transition-all flex items-center space-x-1 whitespace-nowrap ${
                  isActive
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50 shadow-md shadow-cyan-950/40 font-bold'
                    : 'bg-slate-950/60 text-slate-400 border border-slate-800 hover:text-slate-200 hover:border-slate-700'
                }`}
                title={layer.name}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-cyan-400' : 'bg-slate-600'}`} />
                <span>{layer.number}</span>
              </button>
            );
          })}
        </div>

        {/* Play / Pause Tour Button */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-mono text-slate-300 hover:text-white flex items-center space-x-1.5 transition-all"
          >
            {isPlaying ? (
              <>
                <Pause className="w-3 h-3 text-amber-400" />
                <span>Pause Tour</span>
              </>
            ) : (
              <>
                <Play className="w-3 h-3 text-emerald-400" />
                <span>Auto Tour</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* 7-Stage Interactive Cards Grid */}
      <div
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
        onMouseEnter={() => setIsPlaying(false)}
        onMouseLeave={() => setIsPlaying(true)}
      >
        {ARCHITECTURE_LAYERS.map((layer, index) => {
          const isActive = activeStageIdx === index;
          const IconComp = STAGE_ICONS[index] || Database;

          return (
            <div
              key={layer.id}
              onClick={() => {
                setActiveStageIdx(index);
                setIsPlaying(false);
              }}
              className={`p-5 rounded-2xl cursor-pointer transition-all duration-300 flex flex-col justify-between relative group ${
                isActive
                  ? 'bg-gradient-to-b from-cyan-950/30 to-slate-950/90 border border-cyan-500/70 shadow-xl shadow-cyan-950/30 -translate-y-1'
                  : 'bg-slate-900/60 border border-slate-800/80 hover:border-slate-700 hover:-translate-y-0.5'
              }`}
            >
              {/* Active top line highlight */}
              {isActive && (
                <div className="absolute top-0 left-6 right-6 h-[2px] bg-gradient-to-r from-cyan-400 to-blue-500 rounded-full shadow-[0_0_10px_rgba(56,189,248,0.7)]" />
              )}

              <div>
                {/* Header Badge */}
                <div className="flex items-center justify-between mb-3">
                  <div className={`w-9 h-9 rounded-xl border flex items-center justify-center transition-all ${
                    isActive
                      ? 'bg-cyan-950 border-cyan-700/60 text-cyan-300'
                      : 'bg-slate-950 border-slate-800 text-slate-400 group-hover:text-cyan-400'
                  }`}>
                    <IconComp className="w-4 h-4" />
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <span className="text-[10px] font-mono text-cyan-400 font-bold px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-900/50">
                      STAGE {layer.number}
                    </span>
                    <span className="text-[10px] font-mono text-slate-500">
                      0{index + 1}/07
                    </span>
                  </div>
                </div>

                {/* Micro-Visualization SVG for each Stage */}
                <div className="my-2.5 p-2 rounded-xl bg-slate-950/80 border border-slate-800/70 relative overflow-hidden h-16 flex items-center justify-center">
                  {index === 0 && (
                    // STAGE 01: Ingestion Data Packets Stream
                    <div className="w-full h-full relative flex items-center justify-center">
                      <svg className="w-full h-full" viewBox="0 0 140 50">
                        <line x1="10" y1="25" x2="130" y2="25" stroke="#0284c7" strokeWidth="1.5" strokeDasharray="4 3" className="animate-laser-flow" />
                        <rect x="25" y="15" width="20" height="20" rx="3" fill="#0c2d48" stroke="#38bdf8" strokeWidth="1" />
                        <text x="35" y="29" fill="#e0f2fe" fontSize="7" textAnchor="middle" fontFamily="monospace">GRIB2</text>
                        <rect x="85" y="15" width="20" height="20" rx="3" fill="#064e3b" stroke="#34d399" strokeWidth="1" />
                        <text x="95" y="29" fill="#ecfdf5" fontSize="7" textAnchor="middle" fontFamily="monospace">CF-1.8</text>
                      </svg>
                      <div className="absolute right-2 bottom-1 text-[8px] font-mono text-emerald-400 flex items-center space-x-1">
                        <CheckCircle2 className="w-2.5 h-2.5 text-emerald-400" />
                        <span>QC Clean</span>
                      </div>
                    </div>
                  )}

                  {index === 1 && (
                    // STAGE 02: 23-D Spatiotemporal Feature Tensor
                    <div className="w-full h-full relative flex items-center justify-center">
                      <svg className="w-full h-full" viewBox="0 0 140 50">
                        {/* 3D Wind Vector arrows */}
                        <line x1="20" y1="35" x2="45" y2="15" stroke="#38bdf8" strokeWidth="1.5" markerEnd="url(#arrow)" />
                        <line x1="50" y1="35" x2="75" y2="15" stroke="#818cf8" strokeWidth="1.5" />
                        <line x1="80" y1="35" x2="105" y2="15" stroke="#34d399" strokeWidth="1.5" />
                        <circle cx="120" cy="25" r="8" fill="#082f49" stroke="#38bdf8" strokeWidth="1" />
                        <text x="120" y="28" fill="#38bdf8" fontSize="6.5" textAnchor="middle" fontFamily="monospace">23D</text>
                      </svg>
                      <div className="absolute left-2 bottom-1 text-[8px] font-mono text-cyan-400">
                        CAPE • Shear • PWAT
                      </div>
                    </div>
                  )}

                  {index === 2 && (
                    // STAGE 03: 7-Class Softmax Probability Bars
                    <div className="w-full h-full relative flex items-center justify-around px-2">
                      <div className="flex items-end space-x-1.5 h-10 w-full justify-center">
                        <div className="w-2 bg-cyan-400 h-8 rounded-t animate-pulse" />
                        <div className="w-2 bg-blue-500 h-4 rounded-t" />
                        <div className="w-2 bg-purple-500 h-2 rounded-t" />
                        <div className="w-2 bg-slate-700 h-1 rounded-t" />
                        <div className="w-2 bg-slate-700 h-1.5 rounded-t" />
                        <div className="w-2 bg-slate-700 h-1 rounded-t" />
                        <div className="w-2 bg-slate-700 h-1 rounded-t" />
                      </div>
                      <div className="absolute right-2 top-1 text-[8px] font-mono text-cyan-300">
                        Σ p_i = 1.0
                      </div>
                    </div>
                  )}

                  {index === 3 && (
                    // STAGE 04: Soft Mixture-of-Experts Branching Lasers
                    <div className="w-full h-full relative flex items-center justify-center">
                      <svg className="w-full h-full" viewBox="0 0 140 50">
                        <circle cx="20" cy="25" r="8" fill="#0c1e38" stroke="#38bdf8" strokeWidth="1" />
                        <text x="20" y="28" fill="#7dd3fc" fontSize="6" textAnchor="middle" fontFamily="monospace">Gate</text>
                        <path d="M 28 25 Q 50 10, 75 10" stroke="#38bdf8" strokeWidth="1.5" strokeDasharray="3 2" className="animate-laser-flow" />
                        <path d="M 28 25 L 75 25" stroke="#34d399" strokeWidth="1.5" strokeDasharray="3 2" className="animate-laser-flow" />
                        <path d="M 28 25 Q 50 40, 75 40" stroke="#818cf8" strokeWidth="1.5" strokeDasharray="3 2" />
                        <circle cx="115" cy="25" r="8" fill="#064e3b" stroke="#34d399" strokeWidth="1" />
                        <text x="115" y="28" fill="#a7f3d0" fontSize="6" textAnchor="middle" fontFamily="monospace">Blend</text>
                      </svg>
                      <div className="absolute right-2 bottom-1 text-[8px] font-mono text-emerald-400">
                        Analytic Expectation
                      </div>
                    </div>
                  )}

                  {index === 4 && (
                    // STAGE 05: Extreme Rainfall Heavy Tail Exceedance
                    <div className="w-full h-full relative flex items-center justify-center">
                      <svg className="w-full h-full" viewBox="0 0 140 50">
                        <path d="M 15 40 Q 60 38, 90 10 T 130 40" fill="none" stroke="#f43f5e" strokeWidth="1.5" />
                        <line x1="80" y1="5" x2="80" y2="45" stroke="#facc15" strokeWidth="1" strokeDasharray="2 2" />
                      </svg>
                      <div className="absolute right-2 top-1 text-[8px] font-mono text-rose-300 bg-rose-950/80 px-1 rounded">
                        &gt;64.5 mm Tail
                      </div>
                    </div>
                  )}

                  {index === 5 && (
                    // STAGE 06: Spatial Product & 788 District Boundaries
                    <div className="w-full h-full relative flex items-center justify-center">
                      <svg className="w-full h-full" viewBox="0 0 140 50">
                        <polygon points="30,10 70,8 95,22 85,42 40,45 20,30" fill="#082f49" stroke="#38bdf8" strokeWidth="1" />
                        <circle cx="58" cy="25" r="2.5" fill="#38bdf8" className="animate-ping" />
                      </svg>
                      <div className="absolute right-2 bottom-1 text-[8px] font-mono text-cyan-300">
                        788 Districts
                      </div>
                    </div>
                  )}

                  {index === 6 && (
                    // STAGE 07: Verification Contingency Matrix
                    <div className="w-full h-full relative flex items-center justify-center">
                      <svg className="w-full h-full" viewBox="0 0 140 50">
                        <rect x="25" y="10" width="40" height="30" fill="#0f172a" stroke="#475569" strokeWidth="1" />
                        <line x1="45" y1="10" x2="45" y2="40" stroke="#475569" strokeWidth="1" />
                        <line x1="25" y1="25" x2="65" y2="25" stroke="#475569" strokeWidth="1" />
                        <text x="35" y="21" fill="#34d399" fontSize="6.5" textAnchor="middle" fontFamily="monospace">Hit</text>
                        <text x="55" y="21" fill="#f87171" fontSize="6.5" textAnchor="middle" fontFamily="monospace">FA</text>
                      </svg>
                      <div className="absolute right-2 bottom-1 text-[8px] font-mono text-emerald-400">
                        WMO Standard
                      </div>
                    </div>
                  )}
                </div>

                <h3 className="text-base font-bold text-white group-hover:text-cyan-300 transition-colors mb-1">
                  {layer.name}
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed line-clamp-2">
                  {layer.tagline}
                </p>
              </div>

              {/* Bottom QC Tag */}
              <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-cyan-400/90 truncate">
                <span className="truncate">{layer.metricsOrQC}</span>
                <ChevronRight className={`w-3.5 h-3.5 shrink-0 transition-transform ${isActive ? 'text-cyan-400 translate-x-1' : 'text-slate-600'}`} />
              </div>

              {/* Active Progress countdown bar */}
              {isActive && isPlaying && (
                <div className="absolute bottom-0 left-0 right-0 h-1 bg-slate-800 overflow-hidden rounded-b-2xl">
                  <div
                    className="h-full bg-cyan-400 animate-pulse"
                    style={{ width: '100%', animationDuration: '4.2s' }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Deep Dive Architecture Inspector Card for Active Stage */}
      <div className="p-7 rounded-3xl bg-gradient-to-r from-[#081224] via-[#09152C] to-[#081224] border border-cyan-900/50 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 left-0 bottom-0 w-1.5 bg-gradient-to-b from-cyan-400 to-blue-600" />

        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 pb-6 border-b border-slate-800/80">
          <div>
            <div className="flex items-center space-x-2 text-xs font-mono text-cyan-400 font-bold mb-1">
              <span>OPERATIONAL STAGE {activeLayer.number} DEEP DIVE</span>
              <span className="text-slate-600">•</span>
              <span className="text-slate-400 font-normal">Layer ID: {activeLayer.id}</span>
            </div>
            <h3 className="text-2xl font-bold text-white">{activeLayer.name}</h3>
            <p className="text-sm text-slate-300 mt-1">{activeLayer.tagline}</p>
          </div>

          <div className="flex items-center space-x-3">
            <div className="px-3.5 py-2 rounded-xl bg-slate-900/90 border border-slate-700/60 text-xs font-mono text-cyan-300 flex items-center space-x-2">
              <Clock className="w-3.5 h-3.5 text-cyan-400" />
              <span>{activeLayer.metricsOrQC}</span>
            </div>
          </div>
        </div>

        {/* Inputs, Outputs, Scientific Purpose, and Logic */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-6">
          <div className="space-y-4">
            <div className="p-4 rounded-2xl bg-slate-950/70 border border-slate-800/80">
              <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 mb-2.5">
                Ingested Inputs &amp; Preconditions
              </h4>
              <ul className="space-y-2">
                {activeLayer.inputs.map((inp, idx) => (
                  <li key={idx} className="flex items-start space-x-2 text-xs text-slate-300">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 mt-1.5 flex-shrink-0" />
                    <span>{inp}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="p-4 rounded-2xl bg-slate-950/70 border border-slate-800/80">
              <h4 className="text-xs font-mono uppercase tracking-wider text-emerald-400 mb-2.5">
                Emitted Verified Artifacts
              </h4>
              <ul className="space-y-2">
                {activeLayer.outputs.map((out, idx) => (
                  <li key={idx} className="flex items-start space-x-2 text-xs text-emerald-200">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
                    <span>{out}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="space-y-4">
            <div className="p-4 rounded-2xl bg-slate-950/70 border border-cyan-950/60">
              <h4 className="text-xs font-mono uppercase tracking-wider text-cyan-400 mb-2">
                Scientific Purpose
              </h4>
              <p className="text-xs text-slate-300 leading-relaxed">
                {activeLayer.scientificPurpose}
              </p>
            </div>

            <div className="p-4 rounded-2xl bg-slate-950/70 border border-cyan-950/60">
              <h4 className="text-xs font-mono uppercase tracking-wider text-cyan-400 mb-2">
                Governing Numerical Logic
              </h4>
              <p className="text-xs text-slate-300 leading-relaxed font-mono text-[11px]">
                {activeLayer.governingLogic}
              </p>
            </div>
          </div>
        </div>

        {/* Stepper navigation bar */}
        <div className="mt-6 pt-4 border-t border-slate-800 flex items-center justify-between">
          <span className="text-xs font-mono text-slate-500">
            Click any stage above or let auto-tour guide you through the operational cycle.
          </span>
          <button
            onClick={() => {
              setActiveStageIdx((prev) => (prev + 1) % ARCHITECTURE_LAYERS.length);
              setIsPlaying(false);
            }}
            className="px-4 py-2 rounded-xl bg-cyan-950/70 hover:bg-cyan-900 border border-cyan-700/50 text-cyan-300 text-xs font-mono flex items-center space-x-2 transition-all"
          >
            <span>Next Stage (0{(activeStageIdx + 1) % ARCHITECTURE_LAYERS.length + 1})</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
export default SolutionPipelineInteractive;
