import React, { useState, useEffect, useRef } from 'react';
import { Gauge, AlertTriangle, Activity, CloudRain, MapPin, ChevronRight, Play, Pause, ArrowRight, Sparkles } from 'lucide-react';

interface StageData {
  id: number;
  stageNum: string;
  title: string;
  subtitle: string;
  bottomNote: string;
  themeColor: 'blue' | 'amber' | 'purple' | 'rose' | 'emerald';
  icon: React.ElementType;
  corePhysicalIssue: string;
  rampSolutionInsight: string;
  metricBadge: string;
}

const STAGES: StageData[] = [
  {
    id: 0,
    stageNum: 'STAGE 1',
    title: 'Raw NWP Grid',
    subtitle: 'Hydrostatic dynamical cores simulate large-scale pressure and moisture advection on ~18 km grid points.',
    bottomNote: 'Discrete spatial approximations',
    themeColor: 'blue',
    icon: Gauge,
    corePhysicalIssue: 'Hydrostatic dynamical cores solve Navier-Stokes approximations on coarse ~18 km mesh points. Sub-grid topographic valleys and localized micro-climates fall below the spatial resolution limit.',
    rampSolutionInsight: 'RAMP ingests raw 0.125°–0.25° grid arrays and fuses high-resolution regional topography, surface roughness, and coastline proximity grids to reconstruct fine-scale boundary variations.',
    metricBadge: 'Spatial Cell: ~18 km Mesh'
  },
  {
    id: 1,
    stageNum: 'STAGE 2',
    title: 'Grid-Scale Bias',
    subtitle: 'Sub-grid convective parameterizations systematically underpredict cloudburst peaks and overpredict widespread drizzle.',
    bottomNote: 'Non-linear error distribution',
    themeColor: 'amber',
    icon: AlertTriangle,
    corePhysicalIssue: 'Convective parameterizations smear convective updrafts over an entire grid cell, systematically damping peak cloudburst intensities while distributing unrealistically persistent light drizzle.',
    rampSolutionInsight: 'RAMP applies non-linear quantile mapping conditioned on atmospheric buoyancy (CAPE, CIN) and moisture flux, eliminating the artificial drizzle ceiling.',
    metricBadge: 'Error Bias: Non-Linear Skew'
  },
  {
    id: 2,
    stageNum: 'STAGE 3',
    title: 'Changing Regimes',
    subtitle: 'When the monsoon shifts from an active trough to a break state or a tropical depression, the entire bias signature flips.',
    bottomNote: 'Physical mechanisms change',
    themeColor: 'purple',
    icon: Activity,
    corePhysicalIssue: 'During an Active Monsoon, raw models underpredict orographic lifting. But in a Break Monsoon, the exact same equations produce widespread false-alarm drizzle over central India.',
    rampSolutionInsight: 'RAMP continuously computes a 7-class soft atmospheric regime probability vector. When synoptic conditions flip, gating shifts expert weighting smoothly without boundary artifacts.',
    metricBadge: 'Synoptic Shift: 7 Dynamic Regimes'
  },
  {
    id: 3,
    stageNum: 'STAGE 4',
    title: 'Extreme Events',
    subtitle: 'Conventional statistical methods smooth out rare heavy events (>64.5 mm), creating critical missed flood warnings.',
    bottomNote: 'Heavy tail probability loss',
    themeColor: 'rose',
    icon: CloudRain,
    corePhysicalIssue: 'Standard L2 loss and linear regression optimize for mean square error, pulling extreme high-impact rainfall peaks toward the climatological median and discarding heavy-tail distributions.',
    rampSolutionInsight: 'RAMP features specialized extreme-event experts trained with weighted tail loss, combined with calibrated probabilistic exceedance forecasts for 64.5 mm and 115.5 mm thresholds.',
    metricBadge: 'Tail Threshold: >64.5 mm Heavy Rain'
  },
  {
    id: 4,
    stageNum: 'STAGE 5',
    title: 'District Decisions',
    subtitle: 'Disaster managers operate on administrative districts, not floating-point grid coordinates with uncalibrated uncertainty.',
    bottomNote: 'Actionable spatial intelligence',
    themeColor: 'emerald',
    icon: MapPin,
    corePhysicalIssue: 'Municipal authorities and civil disaster teams cannot deploy flood rescue boats based on raw floating-point grid indices without knowing confidence bounds and administrative district boundaries.',
    rampSolutionInsight: 'RAMP aggregates calibrated probabilities onto 700+ administrative districts with color-coded IMD hazard levels (Green / Yellow / Orange / Red) and 90% credible intervals.',
    metricBadge: 'Actionable: IMD District Protocols'
  }
];

export const ProblemStagesInteractive: React.FC = () => {
  const [activeStage, setActiveStage] = useState<number>(0);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Auto-cycle through the 5 stages every 4.5 seconds
  useEffect(() => {
    if (isPaused) return;

    timerRef.current = setInterval(() => {
      setActiveStage((prev) => (prev + 1) % STAGES.length);
    }, 4500);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPaused]);

  const activeData = STAGES[activeStage];

  return (
    <div className="space-y-8">
      {/* Interactive Pipeline Progress Track */}
      <div className="relative p-3 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center space-x-3 text-xs font-mono">
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-cyan-950/80 border border-cyan-800/50 text-cyan-300">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
            <span>ATMOSPHERIC PIPELINE FLOW</span>
          </div>
          <span className="text-slate-400 hidden md:inline">
            Stage {activeStage + 1} of 5
          </span>
        </div>

        {/* 5 Step Indicator Buttons */}
        <div className="flex items-center space-x-1.5 sm:space-x-2">
          {STAGES.map((s, idx) => {
            const isActive = activeStage === idx;
            return (
              <button
                key={s.id}
                onClick={() => {
                  setActiveStage(idx);
                  setIsPaused(true);
                }}
                className={`group relative px-3 py-1.5 rounded-xl text-xs font-mono transition-all flex items-center space-x-1.5 ${
                  isActive
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50 shadow-lg shadow-cyan-950/50'
                    : 'bg-slate-950/60 text-slate-400 border border-slate-800 hover:border-slate-700 hover:text-slate-200'
                }`}
                title={`Jump to ${s.title}`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-cyan-400' : 'bg-slate-600'}`} />
                <span>0{idx + 1}</span>
                <span className="hidden xl:inline text-[11px] opacity-75">{s.title.split(' ')[0]}</span>
              </button>
            );
          })}
        </div>

        {/* Auto-play / Pause control */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setIsPaused(!isPaused)}
            className="px-2.5 py-1 rounded-lg bg-slate-800/70 hover:bg-slate-700/70 border border-slate-700/60 text-slate-300 hover:text-white text-xs font-mono flex items-center space-x-1.5 transition-all"
          >
            {isPaused ? (
              <>
                <Play className="w-3 h-3 text-emerald-400" />
                <span>Resume</span>
              </>
            ) : (
              <>
                <Pause className="w-3 h-3 text-amber-400" />
                <span>Pause</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* 5-Stage Story Cards Grid */}
      <div
        className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4"
        onMouseEnter={() => setIsPaused(true)}
        onMouseLeave={() => setIsPaused(false)}
      >
        {STAGES.map((stage, idx) => {
          const isActive = activeStage === idx;
          const IconComponent = stage.icon;

          // Border, glow and theme tokens
          const themeStyles = {
            blue: {
              activeBorder: 'border-cyan-500/70 shadow-lg shadow-cyan-950/40 bg-gradient-to-b from-cyan-950/30 to-slate-950/90',
              iconBg: 'bg-blue-950/80 border-blue-800/40 text-blue-400',
              badgeText: 'text-cyan-400',
              accentLine: 'bg-cyan-400'
            },
            amber: {
              activeBorder: 'border-amber-500/70 shadow-lg shadow-amber-950/40 bg-gradient-to-b from-amber-950/30 to-slate-950/90',
              iconBg: 'bg-amber-950/80 border-amber-800/40 text-amber-400',
              badgeText: 'text-amber-400',
              accentLine: 'bg-amber-400'
            },
            purple: {
              activeBorder: 'border-purple-500/70 shadow-lg shadow-purple-950/40 bg-gradient-to-b from-purple-950/30 to-slate-950/90',
              iconBg: 'bg-purple-950/80 border-purple-800/40 text-purple-400',
              badgeText: 'text-purple-400',
              accentLine: 'bg-purple-400'
            },
            rose: {
              activeBorder: 'border-rose-500/70 shadow-lg shadow-rose-950/40 bg-gradient-to-b from-rose-950/30 to-slate-950/90',
              iconBg: 'bg-rose-950/80 border-rose-800/40 text-rose-400',
              badgeText: 'text-rose-400',
              accentLine: 'bg-rose-400'
            },
            emerald: {
              activeBorder: 'border-emerald-500/70 shadow-lg shadow-emerald-950/40 bg-gradient-to-b from-emerald-950/30 to-slate-950/90',
              iconBg: 'bg-emerald-950/80 border-emerald-800/40 text-emerald-400',
              badgeText: 'text-emerald-400',
              accentLine: 'bg-emerald-400'
            }
          }[stage.themeColor];

          return (
            <div
              key={stage.id}
              onClick={() => {
                setActiveStage(idx);
                setIsPaused(true);
              }}
              className={`p-5 rounded-2xl cursor-pointer transition-all duration-300 flex flex-col justify-between relative group ${
                isActive
                  ? `${themeStyles.activeBorder} -translate-y-1.5`
                  : 'bg-gradient-to-b from-slate-900/80 to-slate-950/90 border border-slate-800/80 hover:border-slate-700/80 hover:-translate-y-0.5'
              }`}
            >
              {/* Active Top Glow Line */}
              {isActive && (
                <div className={`absolute top-0 left-6 right-6 h-[2px] ${themeStyles.accentLine} rounded-full shadow-[0_0_12px_rgba(56,189,248,0.8)]`} />
              )}

              <div>
                {/* Header Icon & Stage Number */}
                <div className="flex items-center justify-between mb-3">
                  <div className={`w-10 h-10 rounded-xl border flex items-center justify-center transition-transform group-hover:scale-105 ${themeStyles.iconBg}`}>
                    <IconComponent className="w-5 h-5" />
                  </div>
                  <span className={`text-[11px] font-mono font-bold tracking-wider ${themeStyles.badgeText}`}>
                    {stage.stageNum}
                  </span>
                </div>

                {/* Animated Micro-Visualization per stage */}
                <div className="my-3 p-2.5 rounded-xl bg-slate-950/80 border border-slate-800/70 relative overflow-hidden h-20 flex items-center justify-center">
                  {idx === 0 && (
                    // STAGE 1 MICRO-VISUAL: 18km Numerical Grid with Sweeping Scanline
                    <div className="w-full h-full relative flex items-center justify-center">
                      <svg className="w-full h-full opacity-60" viewBox="0 0 140 60">
                        {/* 18km Grid Lines */}
                        <line x1="10" y1="15" x2="130" y2="15" stroke="#38bdf8" strokeWidth="0.75" strokeDasharray="3 2" />
                        <line x1="10" y1="30" x2="130" y2="30" stroke="#38bdf8" strokeWidth="0.75" strokeDasharray="3 2" />
                        <line x1="10" y1="45" x2="130" y2="45" stroke="#38bdf8" strokeWidth="0.75" strokeDasharray="3 2" />
                        <line x1="30" y1="5" x2="30" y2="55" stroke="#38bdf8" strokeWidth="0.75" strokeDasharray="3 2" />
                        <line x1="70" y1="5" x2="70" y2="55" stroke="#38bdf8" strokeWidth="0.75" strokeDasharray="3 2" />
                        <line x1="110" y1="5" x2="110" y2="55" stroke="#38bdf8" strokeWidth="0.75" strokeDasharray="3 2" />
                        
                        {/* Grid Nodes */}
                        <circle cx="30" cy="15" r="2.5" fill="#38bdf8" />
                        <circle cx="70" cy="30" r="3" fill="#38bdf8" className={isActive ? 'animate-ping' : ''} />
                        <circle cx="110" cy="45" r="2.5" fill="#38bdf8" />
                      </svg>
                      {/* Scanning vertical laser */}
                      <div className="absolute top-0 bottom-0 w-[2px] bg-cyan-400 shadow-[0_0_8px_#38bdf8] animate-radar-sweep pointer-events-none" />
                      <div className="absolute bottom-1 right-2 text-[9px] font-mono text-cyan-400/90 bg-cyan-950/70 px-1 rounded">
                        Δx ~18km
                      </div>
                    </div>
                  )}

                  {idx === 1 && (
                    // STAGE 2 MICRO-VISUAL: Dual Curve (True vs Parameterized Drizzle Bias)
                    <div className="w-full h-full relative flex items-center justify-center">
                      <svg className="w-full h-full" viewBox="0 0 140 60">
                        {/* True sharp peak (dashed white) */}
                        <path
                          d="M 10 50 Q 50 48, 65 10 Q 75 48, 130 50"
                          fill="none"
                          stroke="#ffffff"
                          strokeWidth="1.5"
                          strokeDasharray="3 2"
                          opacity="0.8"
                        />
                        {/* NWP Damped Underprediction Curve (Amber) */}
                        <path
                          d="M 10 45 Q 50 42, 65 32 Q 75 42, 130 45"
                          fill="none"
                          stroke="#fbbf24"
                          strokeWidth="2"
                        />
                        {/* Bias Gap Fill */}
                        <path
                          d="M 65 10 L 65 32"
                          stroke="#f87171"
                          strokeWidth="1.5"
                          strokeDasharray="2 2"
                        />
                      </svg>
                      <div className="absolute top-1 left-2 text-[9px] font-mono text-amber-400 bg-amber-950/80 px-1 rounded">
                        -67% Peak Deficit
                      </div>
                      <div className="absolute bottom-1 right-2 text-[9px] font-mono text-amber-300/80">
                        Fake Drizzle Tail
                      </div>
                    </div>
                  )}

                  {idx === 2 && (
                    // STAGE 3 MICRO-VISUAL: Regime Shift Wave Oscillations (Active vs Break)
                    <div className="w-full h-full relative flex items-center justify-center overflow-hidden">
                      <svg className="w-full h-full" viewBox="0 0 140 60">
                        {/* Active Monsoon High Amplitude Wave */}
                        <path
                          d="M 5 30 Q 35 5, 70 30 T 135 30"
                          fill="none"
                          stroke="#c084fc"
                          strokeWidth="1.5"
                          className="animate-laser-flow"
                        />
                        {/* Inverted Break Monsoon Line */}
                        <line x1="10" y1="42" x2="130" y2="42" stroke="#a855f7" strokeWidth="1" strokeDasharray="4 3" opacity="0.6" />
                      </svg>
                      {/* Shifting Dynamic Regime Indicator */}
                      <div className="absolute top-1 right-2 text-[9px] font-mono text-purple-300 bg-purple-950/80 px-1.5 py-0.5 rounded border border-purple-800/40">
                        Active ⇄ Break
                      </div>
                      <div className="absolute bottom-1 left-2 text-[9px] font-mono text-purple-400">
                        Trough Oscillation
                      </div>
                    </div>
                  )}

                  {idx === 3 && (
                    // STAGE 4 MICRO-VISUAL: Cloudburst Storm with Extreme Threshold Line (>64.5 mm)
                    <div className="w-full h-full relative flex items-center justify-center overflow-hidden">
                      {/* Falling Rain Streaks */}
                      <div className="absolute inset-0 flex justify-around pointer-events-none opacity-70">
                        <div className="w-[1px] h-4 bg-rose-400 animate-rain-streak" style={{ animationDelay: '0s' }} />
                        <div className="w-[1.5px] h-5 bg-rose-300 animate-rain-streak" style={{ animationDelay: '0.3s' }} />
                        <div className="w-[1px] h-3 bg-rose-400 animate-rain-streak" style={{ animationDelay: '0.6s' }} />
                        <div className="w-[1.5px] h-6 bg-rose-200 animate-rain-streak" style={{ animationDelay: '0.9s' }} />
                        <div className="w-[1px] h-4 bg-rose-400 animate-rain-streak" style={{ animationDelay: '0.4s' }} />
                      </div>
                      {/* Threshold alert line */}
                      <div className="absolute inset-x-2 top-6 h-[1.5px] bg-rose-500 shadow-[0_0_8px_#f43f5e] flex items-center justify-between">
                        <span className="text-[8px] font-mono text-rose-200 bg-rose-950 px-1 rounded -translate-y-3">
                          &gt;64.5 mm Flood Tail
                        </span>
                        <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
                      </div>
                      <div className="absolute bottom-1 right-2 text-[9px] font-mono text-rose-400">
                        L2 Loss Truncates
                      </div>
                    </div>
                  )}

                  {idx === 4 && (
                    // STAGE 5 MICRO-VISUAL: Administrative District Polygon with Calibrated Radar Beacon
                    <div className="w-full h-full relative flex items-center justify-center">
                      <svg className="w-full h-full" viewBox="0 0 140 60">
                        {/* District Polygon Outline */}
                        <polygon
                          points="25,12 85,8 120,24 110,50 50,54 20,38"
                          fill="#064e3b"
                          fillOpacity="0.4"
                          stroke="#10b981"
                          strokeWidth="1.5"
                        />
                        {/* District HQ Center Point */}
                        <circle cx="68" cy="30" r="3" fill="#34d399" />
                        <circle cx="68" cy="30" r="9" fill="none" stroke="#34d399" strokeWidth="1" strokeDasharray="2 2" className="animate-spin" />
                      </svg>
                      <div className="absolute top-1 right-2 text-[9px] font-mono text-emerald-300 bg-emerald-950/80 px-1 rounded border border-emerald-800/40">
                        Taluk / District
                      </div>
                      <div className="absolute bottom-1 left-2 text-[9px] font-mono text-emerald-400">
                        90% Credible Range
                      </div>
                    </div>
                  )}
                </div>

                <h3 className="text-base font-bold text-white mb-1.5">{stage.title}</h3>
                <p className="text-xs text-slate-400 leading-relaxed line-clamp-3">
                  {stage.subtitle}
                </p>
              </div>

              {/* Card Footer */}
              <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-400">
                <span className="truncate">{stage.bottomNote}</span>
                <ChevronRight className={`w-3.5 h-3.5 transition-transform ${isActive ? 'text-cyan-400 translate-x-1' : 'text-slate-600'}`} />
              </div>

              {/* Progress Bar for Active Card */}
              {isActive && !isPaused && (
                <div className="absolute bottom-0 left-0 right-0 h-1 bg-slate-800 overflow-hidden rounded-b-2xl">
                  <div
                    className="h-full bg-cyan-400 animate-pulse"
                    style={{
                      width: '100%',
                      animationDuration: '4.5s'
                    }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Deep Scientific Insight Banner for Active Selected Stage */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-950 to-slate-900 border border-slate-800 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 left-0 bottom-0 w-1 bg-gradient-to-b from-cyan-400 to-blue-600" />
        
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="space-y-2 max-w-3xl">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider">
                {activeData.stageNum} SCIENTIFIC AUDIT:
              </span>
              <span className="text-sm font-bold text-white">
                {activeData.title}
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                {activeData.metricBadge}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs pt-1">
              <div className="p-3 rounded-xl bg-slate-950/70 border border-rose-950/40 text-slate-300">
                <div className="text-rose-400 font-semibold mb-1 flex items-center space-x-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>The Raw Physical Challenge</span>
                </div>
                <p className="text-slate-400 leading-relaxed text-[11px]">
                  {activeData.corePhysicalIssue}
                </p>
              </div>

              <div className="p-3 rounded-xl bg-slate-950/70 border border-cyan-950/40 text-slate-300">
                <div className="text-cyan-400 font-semibold mb-1 flex items-center space-x-1.5">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>How GatiSutra RAMP Solves It</span>
                </div>
                <p className="text-slate-300 leading-relaxed text-[11px]">
                  {activeData.rampSolutionInsight}
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-3 w-full lg:w-auto justify-end">
            <button
              onClick={() => {
                setActiveStage((prev) => (prev + 1) % STAGES.length);
                setIsPaused(true);
              }}
              className="px-4 py-2 rounded-xl bg-cyan-950/70 hover:bg-cyan-900/80 border border-cyan-700/50 text-cyan-300 text-xs font-mono font-semibold flex items-center space-x-2 transition-all"
            >
              <span>Next Stage</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
export default ProblemStagesInteractive;
