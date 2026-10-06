import React, { useState, useEffect, useRef } from 'react';
import {
  Zap,
  Play,
  Pause,
  Info,
  ShieldAlert,
  TrendingUp,
  Activity,
  Wind
} from 'lucide-react';
import { CANONICAL_REGIMES, WeatherRegime } from './landingData';

export const WatchRampDecideInteractive: React.FC = () => {
  const [selectedRegimeIdx, setSelectedRegimeIdx] = useState<number>(0);
  const [isTourPlaying, setIsTourPlaying] = useState<boolean>(true);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Auto-tour through the 7 regimes
  useEffect(() => {
    if (!isTourPlaying) return;

    timerRef.current = setInterval(() => {
      setSelectedRegimeIdx((prev) => (prev + 1) % CANONICAL_REGIMES.length);
    }, 5000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isTourPlaying]);

  const selectedRegime: WeatherRegime = CANONICAL_REGIMES[selectedRegimeIdx];

  // Visual icons and badges for the 7 regimes
  const regimeBadges: Record<string, { icon: string; tagColor: string }> = {
    ACTIVE_MONSOON: { icon: '🌊', tagColor: 'text-cyan-400 bg-cyan-950 border-cyan-800' },
    BREAK_MONSOON: { icon: '☀️', tagColor: 'text-amber-400 bg-amber-950 border-amber-800' },
    LOW_DEPRESSION: { icon: '🌀', tagColor: 'text-rose-400 bg-rose-950 border-rose-800' },
    COASTAL: { icon: '🏖️', tagColor: 'text-teal-400 bg-teal-950 border-teal-800' },
    OROGRAPHIC: { icon: '⛰️', tagColor: 'text-emerald-400 bg-emerald-950 border-emerald-800' },
    WESTERN_DISTURBANCE: { icon: '❄️', tagColor: 'text-indigo-400 bg-indigo-950 border-indigo-800' },
    TRANSITION_OTHER: { icon: '🔄', tagColor: 'text-purple-400 bg-purple-950 border-purple-800' }
  };

  const badgeMeta = regimeBadges[selectedRegime.code] || { icon: '⚡', tagColor: 'text-cyan-400 bg-cyan-950 border-cyan-800' };

  return (
    <div className="space-y-8">
      {/* Regime Selector Pills & Auto Tour Button */}
      <div className="flex flex-col lg:flex-row items-center justify-between gap-4 p-4 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-md">
        <div className="flex items-center space-x-2 text-xs font-mono text-slate-300">
          <Zap className="w-4 h-4 text-cyan-400" />
          <span className="font-semibold text-white">SELECT REGIME TO WITNESS GATING:</span>
        </div>

        {/* 7 Canonical Regime Pills */}
        <div className="flex items-center space-x-2 overflow-x-auto max-w-full pb-1 lg:pb-0">
          {CANONICAL_REGIMES.map((regime, idx) => {
            const isSelected = selectedRegimeIdx === idx;
            const meta = regimeBadges[regime.code];
            return (
              <button
                key={regime.id}
                onClick={() => {
                  setSelectedRegimeIdx(idx);
                  setIsTourPlaying(false);
                }}
                className={`px-3 py-1.5 rounded-xl text-xs font-mono transition-all flex items-center space-x-2 whitespace-nowrap border ${
                  isSelected
                    ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 font-bold border-cyan-300 shadow-md shadow-cyan-500/20'
                    : 'bg-slate-950/70 text-slate-300 border-slate-800 hover:border-slate-700 hover:text-white'
                }`}
              >
                <span>{meta?.icon || '⚡'}</span>
                <span>{regime.name}</span>
                {isSelected && <span className="w-1.5 h-1.5 rounded-full bg-slate-950 animate-ping" />}
              </button>
            );
          })}
        </div>

        {/* Tour Control */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setIsTourPlaying(!isTourPlaying)}
            className="px-3 py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 border border-slate-700 text-xs font-mono text-slate-300 hover:text-white flex items-center space-x-1.5 transition-all"
          >
            {isTourPlaying ? (
              <>
                <Pause className="w-3 h-3 text-amber-400" />
                <span>Pause</span>
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

      {/* Main Interactive Simulation Display */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        {/* Left: Atmospheric State Diagnostics & Synoptic Graphic */}
        <div className="lg:col-span-5 p-7 rounded-3xl bg-[#091222] border border-cyan-900/50 shadow-2xl flex flex-col justify-between space-y-6 relative overflow-hidden">
          {/* Subtle Ambient Background glow */}
          <div className="absolute top-0 right-0 w-48 h-48 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-cyan-400 font-bold flex items-center space-x-2">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                <span>ACTIVE REGIME ID: 0{selectedRegime.id}</span>
              </span>
              <span className={`px-2.5 py-0.5 rounded text-[10px] font-mono border ${badgeMeta.tagColor}`}>
                {selectedRegime.code}
              </span>
            </div>

            <div>
              <div className="flex items-center space-x-2">
                <span className="text-2xl">{badgeMeta.icon}</span>
                <h3 className="text-2xl font-bold text-white">{selectedRegime.name}</h3>
              </div>
              <p className="text-sm text-slate-300 mt-2 leading-relaxed">
                {selectedRegime.shortDesc}
              </p>
            </div>

            {/* DYNAMIC SYNOPTIC CANVAS / ANIMATED ATMOSPHERE SCHEMATIC */}
            <div className="p-3 rounded-2xl bg-slate-950/90 border border-slate-800/80 relative overflow-hidden h-28 flex items-center justify-center">
              {selectedRegime.code === 'ACTIVE_MONSOON' && (
                <div className="w-full h-full relative flex items-center justify-center">
                  <svg className="w-full h-full" viewBox="0 0 200 70">
                    {/* Strong Somali Jet Westerly Streamlines */}
                    <path d="M 10 20 Q 80 15, 180 30" stroke="#38bdf8" strokeWidth="2" strokeDasharray="6 3" className="animate-laser-flow" />
                    <path d="M 10 40 Q 80 35, 180 50" stroke="#38bdf8" strokeWidth="2.5" strokeDasharray="6 3" className="animate-laser-flow-fast" />
                    <text x="30" y="14" fill="#38bdf8" fontSize="8" fontFamily="monospace">Somali Jet &gt;30 kts</text>
                  </svg>
                  <div className="absolute right-3 bottom-2 text-[9px] font-mono text-cyan-300 bg-cyan-950/80 px-1.5 py-0.5 rounded border border-cyan-800/50">
                    High PWAT &gt;55mm
                  </div>
                </div>
              )}

              {selectedRegime.code === 'BREAK_MONSOON' && (
                <div className="w-full h-full relative flex items-center justify-center">
                  <svg className="w-full h-full" viewBox="0 0 200 70">
                    {/* Ridge Subsidence Rings */}
                    <ellipse cx="100" cy="35" rx="60" ry="20" fill="none" stroke="#fbbf24" strokeWidth="1.5" strokeDasharray="4 3" />
                    <ellipse cx="100" cy="35" rx="30" ry="10" fill="none" stroke="#f59e0b" strokeWidth="1" />
                    <text x="100" y="38" fill="#fde68a" fontSize="8" textAnchor="middle" fontFamily="monospace">Ridge Subsidence</text>
                  </svg>
                  <div className="absolute right-3 bottom-2 text-[9px] font-mono text-amber-300 bg-amber-950/80 px-1.5 py-0.5 rounded border border-amber-800/50">
                    False Alarms -34%
                  </div>
                </div>
              )}

              {selectedRegime.code === 'LOW_DEPRESSION' && (
                <div className="w-full h-full relative flex items-center justify-center">
                  <svg className="w-full h-full" viewBox="0 0 200 70">
                    {/* Rotating Cyclonic Vortex Spiral */}
                    <circle cx="100" cy="35" r="24" fill="none" stroke="#f43f5e" strokeWidth="1.5" strokeDasharray="4 2" className="animate-spin" />
                    <circle cx="100" cy="35" r="12" fill="none" stroke="#fb7185" strokeWidth="2" strokeDasharray="4 2" className="animate-spin" />
                    <circle cx="100" cy="35" r="3" fill="#f43f5e" />
                    <text x="100" y="38" fill="#ffffff" fontSize="7" textAnchor="middle" fontFamily="monospace">Low (L)</text>
                  </svg>
                  <div className="absolute right-3 bottom-2 text-[9px] font-mono text-rose-300 bg-rose-950/80 px-1.5 py-0.5 rounded border border-rose-800/50">
                    ΔP ≥ -4 hPa Vortex
                  </div>
                </div>
              )}

              {selectedRegime.code === 'OROGRAPHIC' && (
                <div className="w-full h-full relative flex items-center justify-center">
                  <svg className="w-full h-full" viewBox="0 0 200 70">
                    {/* Western Ghats Terrain Barrier */}
                    <polygon points="70,60 110,15 150,60" fill="#064e3b" stroke="#10b981" strokeWidth="1.5" />
                    <path d="M 20 50 Q 70 45, 100 20" stroke="#34d399" strokeWidth="2" strokeDasharray="4 2" className="animate-laser-flow" />
                    <text x="110" y="10" fill="#a7f3d0" fontSize="8" textAnchor="middle" fontFamily="monospace">Ghats Barrier</text>
                  </svg>
                  <div className="absolute right-3 bottom-2 text-[9px] font-mono text-emerald-300 bg-emerald-950/80 px-1.5 py-0.5 rounded border border-emerald-800/50">
                    Mechanical Lift +41%
                  </div>
                </div>
              )}

              {['COASTAL', 'WESTERN_DISTURBANCE', 'TRANSITION_OTHER'].includes(selectedRegime.code) && (
                <div className="w-full h-full relative flex items-center justify-center">
                  <svg className="w-full h-full" viewBox="0 0 200 70">
                    <line x1="20" y1="35" x2="180" y2="35" stroke="#818cf8" strokeWidth="1.5" strokeDasharray="4 3" className="animate-laser-flow" />
                    <circle cx="100" cy="35" r="16" fill="#1e1b4b" stroke="#a5b4fc" strokeWidth="1" />
                    <text x="100" y="38" fill="#e0e7ff" fontSize="7.5" textAnchor="middle" fontFamily="monospace">Synoptic Convergence</text>
                  </svg>
                  <div className="absolute right-3 bottom-2 text-[9px] font-mono text-indigo-300 bg-indigo-950/80 px-1.5 py-0.5 rounded border border-indigo-800/50">
                    Local Circulation
                  </div>
                </div>
              )}
            </div>

            {/* Synoptic Diagnostics Info Box */}
            <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-2.5">
              <div className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center space-x-1.5">
                <Activity className="w-3.5 h-3.5 text-cyan-400" />
                <span>Synoptic Diagnostics</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                <strong className="text-cyan-400">Features:</strong> {selectedRegime.synopticFeatures}
              </p>
              <p className="text-xs text-slate-300 leading-relaxed">
                <strong className="text-cyan-400">Dynamics:</strong> {selectedRegime.primaryDynamics}
              </p>
            </div>

            {/* Forecast Delta & Tail Risk Metrics */}
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3.5 rounded-2xl bg-slate-900/80 border border-slate-800">
                <div className="text-[10px] font-mono text-slate-400 flex items-center space-x-1">
                  <TrendingUp className="w-3 h-3 text-emerald-400" />
                  <span>FORECAST DELTA</span>
                </div>
                <div className="text-xs font-bold text-emerald-400 mt-1 leading-snug">
                  {selectedRegime.correctedRainDelta}
                </div>
              </div>

              <div className="p-3.5 rounded-2xl bg-slate-900/80 border border-slate-800">
                <div className="text-[10px] font-mono text-slate-400 flex items-center space-x-1">
                  <ShieldAlert className="w-3 h-3 text-cyan-400" />
                  <span>P(EXTREME &gt; 64.5mm)</span>
                </div>
                <div className="text-xs font-bold text-cyan-400 mt-1">
                  {(selectedRegime.extremeProbability * 100).toFixed(0)}% Risk Envelope
                </div>
              </div>
            </div>
          </div>

          <div className="text-[11px] font-mono text-slate-500 flex items-center space-x-1.5 pt-2 border-t border-slate-800/60">
            <Info className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            <span>Illustrative routing simulation grounded in RAMP model architecture.</span>
          </div>
        </div>

        {/* Right: Soft Gating Distribution & Mixture-of-Experts Allocation */}
        <div className="lg:col-span-7 p-7 rounded-3xl bg-[#091222] border border-cyan-900/50 shadow-2xl flex flex-col justify-between space-y-6">
          <div className="space-y-6">
            {/* Soft Gating Distribution Bar */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-mono uppercase tracking-wider text-slate-300 font-bold flex items-center space-x-2">
                  <Wind className="w-4 h-4 text-cyan-400" />
                  <span>Soft Gating Distribution: P(Regime)</span>
                </h4>
                <span className="text-xs font-mono text-cyan-400 font-bold bg-cyan-950/80 px-2.5 py-0.5 rounded border border-cyan-800">
                  Dominant: {(selectedRegime.sampleProb * 100).toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-slate-950 h-3.5 rounded-full overflow-hidden border border-slate-800 p-0.5">
                <div
                  className="h-full bg-gradient-to-r from-cyan-500 via-blue-500 to-emerald-400 rounded-full transition-all duration-700 shadow-sm"
                  style={{ width: `${selectedRegime.sampleProb * 100}%` }}
                />
              </div>
              <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 mt-1.5">
                <span>Normalized Softmax Posterior</span>
                <span>Shannon Entropy H(p) = 0.42 bits</span>
              </div>
            </div>

            {/* Mixture-of-Experts Weight Allocation Bars with Animated Routing */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold">
                  Mixture-of-Experts Weight Allocation: Σ w_i = 1.0
                </div>
                <span className="text-[10px] font-mono text-emerald-400 flex items-center space-x-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                  <span>Dynamic Expert Routing</span>
                </span>
              </div>

              <div className="space-y-3.5">
                {Object.entries(selectedRegime.simulatedWeights).map(([expertName, weight], idx) => {
                  const isTopExpert = idx === 0;
                  return (
                    <div key={expertName} className="space-y-1.5">
                      <div className="flex items-center justify-between text-xs">
                        <span className={`font-medium ${isTopExpert ? 'text-white font-bold' : 'text-slate-300'}`}>
                          {expertName}
                        </span>
                        <div className="flex items-center space-x-2">
                          {isTopExpert && (
                            <span className="text-[9px] font-mono text-emerald-300 bg-emerald-950/80 px-1.5 rounded border border-emerald-800/60">
                              DOMINANT
                            </span>
                          )}
                          <span className={`font-mono font-bold ${isTopExpert ? 'text-cyan-300 text-sm' : 'text-cyan-400'}`}>
                            {(weight * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                      <div className="w-full bg-slate-950 h-3 rounded-full overflow-hidden border border-slate-800">
                        <div
                          className={`h-full rounded-full transition-all duration-700 ${
                            isTopExpert
                              ? 'bg-gradient-to-r from-cyan-400 to-emerald-400 shadow-[0_0_8px_rgba(56,189,248,0.5)]'
                              : 'bg-gradient-to-r from-blue-600 to-cyan-600'
                          }`}
                          style={{ width: `${weight * 100}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Mathematical Guarantee Box */}
          <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 text-xs font-mono text-slate-300">
            <div className="text-cyan-400 font-bold mb-1 flex items-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
              <span>ANALYTICAL BLENDING GUARANTEE:</span>
            </div>
            <p className="text-slate-400 leading-relaxed">
              Corrected_Rainfall = Σ [ p(regime_i) × Expert_i(NWP_Features) ]
              <br />
              <span className="text-slate-500">
                Zero discrete switching. Continuous spatial gradients preserved across all 788 districts.
              </span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
export default WatchRampDecideInteractive;
