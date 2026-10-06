import React, { useState, useEffect, useRef } from 'react';
import { Sparkles, AlertTriangle, Zap, RefreshCw } from 'lucide-react';

interface RegimeScenario {
  id: string;
  name: string;
  icon: string;
  synopticState: string;
  dynamicCondition: string;
  dominantExpert: string;
  dominantWeight: number;
  secondaryExpert: string;
  secondaryWeight: number;
  tertiaryWeight: number;
  traditionalFailure: string;
  rampBenefit: string;
  accentColor: string;
}

const REGIME_SCENARIOS: RegimeScenario[] = [
  {
    id: 'cyclone',
    name: 'Monsoon Depression',
    icon: '🌀',
    synopticState: 'Low-Pressure Vortex over Bay of Bengal',
    dynamicCondition: '850 hPa Vorticity > 1.2×10⁻⁴ s⁻¹ | High PW > 62 mm',
    dominantExpert: 'Depression / Cyclonic Expert',
    dominantWeight: 78,
    secondaryExpert: 'Deep Convective Expert',
    secondaryWeight: 16,
    tertiaryWeight: 6,
    traditionalFailure: 'Blunts torrential eyewall & convective bands into moderate rain; critical underprediction of flood risk.',
    rampBenefit: 'Specialized heavy-tail loss preserves cloudburst peaks (>115 mm) without spatial boundary tears.',
    accentColor: '#38bdf8' // Cyan
  },
  {
    id: 'active_trough',
    name: 'Active Monsoon Trough',
    icon: '⚡',
    synopticState: 'Monsoon Trough South of Normal Position',
    dynamicCondition: 'Strong Low-Level Somali Jet (>32 kts) | Moist Advection',
    dominantExpert: 'Active Trough Expert',
    dominantWeight: 72,
    secondaryExpert: 'Orographic Ghats Expert',
    secondaryWeight: 21,
    tertiaryWeight: 7,
    traditionalFailure: 'Global linear model underestimates Western Ghats orographic uplifting by 35–45%.',
    rampBenefit: 'Smoothly blends orographic ascent and synoptic moisture convergence with high localized precision.',
    accentColor: '#818cf8' // Indigo/Violet
  },
  {
    id: 'break',
    name: 'Break Monsoon Spell',
    icon: '☀️',
    synopticState: 'Trough Shifted to Himalayan Foothills',
    dynamicCondition: 'Mid-Tropospheric Subsidence over Plains | Low CAPE',
    dominantExpert: 'Suppression / Dry Expert',
    dominantWeight: 84,
    secondaryExpert: 'Transition Expert',
    secondaryWeight: 11,
    tertiaryWeight: 5,
    traditionalFailure: 'Global model predicts spurious convective rain (drizzle) across dry central states; high false alarms.',
    rampBenefit: 'Suppression expert damps convective noise, driving false alarm ratio down by 34%.',
    accentColor: '#34d399' // Emerald
  }
];

export const CoreInsightMoEInteractive: React.FC = () => {
  const [selectedScenarioIdx, setSelectedScenarioIdx] = useState<number>(0);
  const [isAutoCycling, setIsAutoCycling] = useState<boolean>(true);
  const cycleTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!isAutoCycling) return;

    cycleTimerRef.current = setInterval(() => {
      setSelectedScenarioIdx((prev) => (prev + 1) % REGIME_SCENARIOS.length);
    }, 4500);

    return () => {
      if (cycleTimerRef.current) clearInterval(cycleTimerRef.current);
    };
  }, [isAutoCycling]);

  const activeScenario = REGIME_SCENARIOS[selectedScenarioIdx];

  return (
    <div className="space-y-8">
      {/* Interactive Regime Condition Simulator Switcher */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-md">
        <div className="flex items-center space-x-2 text-xs font-mono text-slate-300">
          <Zap className="w-4 h-4 text-cyan-400" />
          <span className="font-semibold text-white">LIVE SYNOPTIC REGIME SIMULATOR:</span>
          <span className="text-slate-400 hidden lg:inline">Test how both systems react to changing atmospheric physics</span>
        </div>

        {/* Regime Tabs */}
        <div className="flex items-center space-x-2 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
          {REGIME_SCENARIOS.map((scenario, idx) => {
            const isSelected = selectedScenarioIdx === idx;
            return (
              <button
                key={scenario.id}
                onClick={() => {
                  setSelectedScenarioIdx(idx);
                  setIsAutoCycling(false);
                }}
                className={`px-3 py-1.5 rounded-xl text-xs font-mono transition-all flex items-center space-x-2 whitespace-nowrap ${
                  isSelected
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50 shadow-md shadow-cyan-950/40'
                    : 'bg-slate-950/60 text-slate-400 border border-slate-800/80 hover:text-slate-200 hover:border-slate-700'
                }`}
              >
                <span>{scenario.icon}</span>
                <span className="font-medium">{scenario.name}</span>
                {isSelected && <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />}
              </button>
            );
          })}

          <button
            onClick={() => setIsAutoCycling(!isAutoCycling)}
            title={isAutoCycling ? 'Pause automatic cycle' : 'Resume automatic cycle'}
            className="p-1.5 rounded-xl bg-slate-800 text-slate-400 hover:text-white text-xs border border-slate-700"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isAutoCycling ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Side-by-side Architectural Comparison Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-stretch">
        {/* =========================================================
            TRADITIONAL POST-PROCESSING (THE RIGID FAILURE)
            ========================================================= */}
        <div className="p-8 rounded-3xl bg-slate-950/90 border border-slate-800/90 flex flex-col justify-between shadow-2xl relative overflow-hidden group">
          {/* Subtle red hazard ambient glow */}
          <div className="absolute top-0 right-0 w-48 h-48 bg-rose-500/5 rounded-full blur-3xl pointer-events-none" />

          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-rose-950/80 border border-rose-800/50 text-rose-300 text-xs font-mono">
                <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
                <span>Traditional Post-Processing</span>
              </div>
              <span className="text-[10px] font-mono text-rose-400/80 uppercase tracking-widest bg-rose-950/40 px-2 py-0.5 rounded">
                Stationary Model
              </span>
            </div>

            <h3 className="text-xl font-bold text-white mb-2">Static / Global Correction</h3>
            <p className="text-sm text-slate-400 leading-relaxed mb-6">
              Trained across all historical weather days simultaneously without conditioning on synoptic physics. It learns the "average" error, which degrades both extreme cloudbursts and dry spells.
            </p>

            {/* ANIMATED DIAGRAM: Monolithic Bottleneck Failure */}
            <div className="my-5 p-4 rounded-2xl bg-[#090d16] border border-rose-950/60 relative overflow-hidden">
              <div className="text-[11px] font-mono text-slate-400 mb-2 flex items-center justify-between">
                <span>MONOLITHIC PIPELINE BEHAVIOR:</span>
                <span className="text-rose-400 text-[10px] animate-pulse">● Collision & Signal Smear</span>
              </div>

              {/* Animated SVG Pipeline Diagram */}
              <div className="w-full h-28 relative flex items-center justify-center">
                <svg className="w-full h-full" viewBox="0 0 320 90">
                  {/* Multi-regime inputs entering from left */}
                  <path d="M 10 20 L 90 45" stroke="#38bdf8" strokeWidth="1.5" strokeDasharray="3 3" className="animate-laser-flow" />
                  <path d="M 10 45 L 90 45" stroke="#818cf8" strokeWidth="1.5" strokeDasharray="3 3" className="animate-laser-flow" />
                  <path d="M 10 70 L 90 45" stroke="#34d399" strokeWidth="1.5" strokeDasharray="3 3" className="animate-laser-flow" />

                  {/* Input labels */}
                  <text x="15" y="16" fill="#7dd3fc" fontSize="8" fontFamily="monospace">Cyclone</text>
                  <text x="15" y="42" fill="#a5b4fc" fontSize="8" fontFamily="monospace">Trough</text>
                  <text x="15" y="68" fill="#6ee7b7" fontSize="8" fontFamily="monospace">Break</text>

                  {/* Monolithic Bottleneck Box */}
                  <rect
                    x="95"
                    y="20"
                    width="110"
                    height="50"
                    rx="8"
                    fill="#180b12"
                    stroke="#e11d48"
                    strokeWidth="1.5"
                    className="animate-glitch-flicker"
                  />
                  <text x="150" y="40" fill="#f43f5e" fontSize="9" fontWeight="bold" textAnchor="middle" fontFamily="monospace">
                    Single Global Model
                  </text>
                  <text x="150" y="55" fill="#fda4af" fontSize="7.5" textAnchor="middle" fontFamily="monospace">
                    (Stationary Bias Offset)
                  </text>

                  {/* Single Blunted Output Line */}
                  <path d="M 205 45 L 290 45" stroke="#94a3b8" strokeWidth="2" strokeDasharray="4 2" />
                  
                  {/* Flattened blunted wave */}
                  <path d="M 250 45 Q 265 38, 280 45" stroke="#f87171" strokeWidth="2" fill="none" />
                  <text x="255" y="32" fill="#f87171" fontSize="7.5" fontFamily="monospace">Averaged</text>
                </svg>

                {/* Glitch friction spark */}
                <div className="absolute left-[34%] top-[30%] w-3 h-3 rounded-full bg-rose-500/30 animate-ping pointer-events-none" />
              </div>

              {/* Live Traditional Failure Impact for Current Scenario */}
              <div className="mt-2 p-3 rounded-xl bg-rose-950/40 border border-rose-900/50 text-[11px] text-rose-200 leading-relaxed font-sans">
                <span className="font-bold text-rose-300 font-mono block mb-1">
                  ⚠ FAILURE IN {activeScenario.name.toUpperCase()}:
                </span>
                {activeScenario.traditionalFailure}
              </div>
            </div>

            {/* Pipeline Flow Steps */}
            <div className="space-y-2 font-mono text-xs">
              <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between text-slate-300">
                <span className="text-slate-400">NWP Forecast</span>
                <span className="text-slate-600">→</span>
                <span className="text-rose-400 font-bold">Single Global Model</span>
                <span className="text-slate-600">→</span>
                <span className="text-slate-400">Averaged Output</span>
              </div>
            </div>
          </div>

          <div className="mt-8 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500 font-mono">
            <span>Hard model boundaries</span>
            <span className="text-rose-400/80">Zero regime awareness</span>
          </div>
        </div>

        {/* =========================================================
            GATISUTRA RAMP ARCHITECTURE (THE REGIME-AWARE MIXTURE-OF-EXPERTS)
            ========================================================= */}
        <div className="p-8 rounded-3xl bg-gradient-to-b from-[#0B1528] via-[#091222] to-[#070D1A] border border-cyan-500/40 flex flex-col justify-between shadow-2xl relative overflow-hidden group">
          {/* Luminous cyan & emerald ambient aura */}
          <div className="absolute top-0 right-0 w-72 h-72 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 left-0 w-48 h-48 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-500/60 text-cyan-300 text-xs font-mono shadow-sm shadow-cyan-950">
                <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                <span>GatiSutra RAMP Architecture</span>
              </div>
              <span className="text-[10px] font-mono text-cyan-300 uppercase tracking-widest bg-cyan-950/60 px-2.5 py-0.5 rounded border border-cyan-800/50">
                Dynamic Soft Gating
              </span>
            </div>

            <h3 className="text-xl font-bold text-white mb-2">Regime-Aware Mixture-of-Experts</h3>
            <p className="text-sm text-slate-300 leading-relaxed mb-6">
              Diagnoses the atmospheric state via 23 dynamic variables, produces a soft 7-class probability distribution, and blends specialized correction experts analytically without spatial edge discontinuities.
            </p>

            {/* ANIMATED DIAGRAM: Dynamic Neural Routing Flow */}
            <div className="my-5 p-4 rounded-2xl bg-[#040914] border border-cyan-900/60 relative overflow-hidden">
              <div className="text-[11px] font-mono text-cyan-300 mb-2 flex items-center justify-between">
                <span>DYNAMIC ROUTING GATING (ACTIVE):</span>
                <span className="text-emerald-400 text-[10px] flex items-center space-x-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                  <span>Soft Blending Active</span>
                </span>
              </div>

              {/* Animated SVG MoE Neural Architecture */}
              <div className="w-full h-32 relative flex items-center justify-center">
                <svg className="w-full h-full" viewBox="0 0 340 100">
                  {/* Left: 23 Dynamic Features Input Stream */}
                  <rect x="5" y="25" width="55" height="50" rx="6" fill="#0c1e38" stroke="#38bdf8" strokeWidth="1" />
                  <text x="32" y="44" fill="#38bdf8" fontSize="8" fontWeight="bold" textAnchor="middle" fontFamily="monospace">23 NWP</text>
                  <text x="32" y="56" fill="#7dd3fc" fontSize="7" textAnchor="middle" fontFamily="monospace">Features</text>

                  {/* Laser stream from features to Gating Network */}
                  <path d="M 60 50 L 95 50" stroke="#38bdf8" strokeWidth="2" strokeDasharray="4 2" className="animate-laser-flow" />

                  {/* Center Gating Node (Softmax Router) */}
                  <circle cx="115" cy="50" r="20" fill="#082f49" stroke="#06b6d4" strokeWidth="1.5" />
                  <text x="115" y="48" fill="#e0f2fe" fontSize="7.5" fontWeight="bold" textAnchor="middle" fontFamily="monospace">7-Regime</text>
                  <text x="115" y="58" fill="#38bdf8" fontSize="6.5" textAnchor="middle" fontFamily="monospace">Gating</text>

                  {/* Top Branch: Dominant Expert Path (Energetic Cyan Laser) */}
                  <path d="M 135 45 Q 165 20, 195 20" stroke={activeScenario.accentColor} strokeWidth="2.5" strokeDasharray="6 3" className="animate-laser-flow-fast" />
                  <rect x="195" y="10" width="75" height="20" rx="4" fill="#082f49" stroke={activeScenario.accentColor} strokeWidth="1.5" />
                  <text x="232" y="23" fill="#ffffff" fontSize="7" fontWeight="bold" textAnchor="middle" fontFamily="monospace">
                    {activeScenario.dominantWeight}% {activeScenario.dominantExpert.split(' ')[0]}
                  </text>

                  {/* Middle Branch: Secondary Expert */}
                  <path d="M 135 50 L 195 50" stroke="#0284c7" strokeWidth="1.5" strokeDasharray="4 3" className="animate-laser-flow" />
                  <rect x="195" y="40" width="75" height="20" rx="4" fill="#0c1e38" stroke="#0284c7" strokeWidth="1" />
                  <text x="232" y="53" fill="#93c5fd" fontSize="7" textAnchor="middle" fontFamily="monospace">
                    {activeScenario.secondaryWeight}% {activeScenario.secondaryExpert.split(' ')[0]}
                  </text>

                  {/* Bottom Branch: Transition / Suppression */}
                  <path d="M 135 55 Q 165 80, 195 80" stroke="#334155" strokeWidth="1" strokeDasharray="3 3" />
                  <rect x="195" y="70" width="75" height="20" rx="4" fill="#0b1322" stroke="#334155" strokeWidth="1" />
                  <text x="232" y="83" fill="#64748b" fontSize="6.5" textAnchor="middle" fontFamily="monospace">
                    {activeScenario.tertiaryWeight}% Other Experts
                  </text>

                  {/* Convergence into Soft Blending Node */}
                  <path d="M 270 20 Q 285 35, 295 50" stroke="#10b981" strokeWidth="2" strokeDasharray="4 2" className="animate-laser-flow" />
                  <path d="M 270 50 L 295 50" stroke="#10b981" strokeWidth="1.5" strokeDasharray="4 2" className="animate-laser-flow" />
                  <path d="M 270 80 Q 285 65, 295 50" stroke="#10b981" strokeWidth="1" strokeDasharray="4 2" />

                  {/* Calibrated Output Node */}
                  <circle cx="315" cy="50" r="14" fill="#064e3b" stroke="#34d399" strokeWidth="1.5" />
                  <text x="315" y="49" fill="#a7f3d0" fontSize="7" fontWeight="bold" textAnchor="middle" fontFamily="monospace">Ŷ</text>
                  <text x="315" y="58" fill="#ecfdf5" fontSize="5.5" textAnchor="middle" fontFamily="monospace">Smooth</text>
                </svg>

                {/* Pulsing energy glow on dominant expert */}
                <div className="absolute right-[24%] top-[12%] w-2 h-2 rounded-full bg-cyan-400 animate-ping pointer-events-none" />
              </div>

              {/* Dynamic Live RAMP Context Benefit for Current Scenario */}
              <div className="mt-2 p-3 rounded-xl bg-cyan-950/60 border border-cyan-800/50 text-[11px] text-cyan-200 leading-relaxed font-sans">
                <span className="font-bold text-emerald-400 font-mono block mb-1">
                  ✔ GATISUTRA RAMP REGIME INTELLIGENCE ({activeScenario.name}):
                </span>
                {activeScenario.rampBenefit}
              </div>
            </div>

            {/* Pipeline Step Blocks */}
            <div className="space-y-2.5 font-mono text-xs">
              <div className="p-3 rounded-xl bg-[#061020] border border-cyan-900/40 flex items-center justify-between text-cyan-200">
                <span>NWP Ingest</span>
                <span className="text-cyan-500">→</span>
                <span className="text-cyan-400 font-bold">23 Dynamic Features</span>
                <span className="text-cyan-500">→</span>
                <span className="text-cyan-300">7-Regime Gating</span>
              </div>
              <div className="p-3 rounded-xl bg-[#061020] border border-cyan-900/40 flex items-center justify-between text-emerald-200">
                <span>Specialized Experts</span>
                <span className="text-emerald-500">→</span>
                <span className="text-emerald-400 font-bold">Soft Blending</span>
                <span className="text-emerald-500">→</span>
                <span>Calibrated Extremes</span>
              </div>
            </div>
          </div>

          <div className="mt-8 pt-4 border-t border-cyan-900/60 flex items-center justify-between text-xs text-cyan-400 font-mono">
            <span className="flex items-center space-x-1">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
              <span>Probabilistically smooth</span>
            </span>
            <span className="flex items-center space-x-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span>Extreme-event calibrated</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
export default CoreInsightMoEInteractive;
