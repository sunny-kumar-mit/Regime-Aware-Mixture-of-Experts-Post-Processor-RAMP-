import React, { useState, useEffect } from 'react';
import { Clock, Play, Pause, ArrowRight, FileCode, CheckCircle2 } from 'lucide-react';
import { WORKFLOW_STEPS, WorkflowStep } from './landingData';

export const OperationalWorkflowInteractive: React.FC = () => {
  const [activeStepIdx, setActiveStepIdx] = useState<number>(0);
  const [isAutoPlaying, setIsAutoPlaying] = useState<boolean>(true);

  useEffect(() => {
    if (!isAutoPlaying) return;

    const timer = setInterval(() => {
      setActiveStepIdx((prev) => (prev + 1) % WORKFLOW_STEPS.length);
    }, 3800);

    return () => clearInterval(timer);
  }, [isAutoPlaying]);

  const activeStep: WorkflowStep = WORKFLOW_STEPS[activeStepIdx];

  return (
    <div className="space-y-8">
      {/* Timeline Controls & Cycle Clock Header */}
      <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-md flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center space-x-3 text-xs font-mono">
          <div className="flex items-center space-x-2 px-3 py-1 rounded-lg bg-cyan-950/80 border border-cyan-800/60 text-cyan-300">
            <Clock className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
            <span className="font-semibold">CYCLE LATENCY: &lt; 380 ms END-TO-END</span>
          </div>
          <span className="text-slate-400 hidden sm:inline">
            Active Phase: Step {activeStep.step} of 10 ({activeStep.title})
          </span>
        </div>

        {/* Step Scrubber Pills */}
        <div className="flex items-center space-x-1.5 overflow-x-auto max-w-full pb-1 md:pb-0">
          {WORKFLOW_STEPS.map((step, idx) => {
            const isActive = activeStepIdx === idx;
            return (
              <button
                key={step.step}
                onClick={() => {
                  setActiveStepIdx(idx);
                  setIsAutoPlaying(false);
                }}
                className={`px-2 py-1 rounded-lg text-xs font-mono transition-all border ${
                  isActive
                    ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400 font-bold shadow-md shadow-cyan-950'
                    : 'bg-slate-950/60 text-slate-500 border-slate-800 hover:text-slate-300'
                }`}
                title={step.title}
              >
                {step.step}
              </button>
            );
          })}
        </div>

        {/* Pause / Resume Button */}
        <div>
          <button
            onClick={() => setIsAutoPlaying(!isAutoPlaying)}
            className="px-3 py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 border border-slate-700 text-xs font-mono text-slate-300 hover:text-white flex items-center space-x-1.5 transition-all"
          >
            {isAutoPlaying ? (
              <>
                <Pause className="w-3 h-3 text-amber-400" />
                <span>Pause</span>
              </>
            ) : (
              <>
                <Play className="w-3 h-3 text-emerald-400" />
                <span>Auto Play</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* 10-Step Interactive Cards Grid */}
      <div
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4"
        onMouseEnter={() => setIsAutoPlaying(false)}
        onMouseLeave={() => setIsAutoPlaying(true)}
      >
        {WORKFLOW_STEPS.map((step, idx) => {
          const isActive = activeStepIdx === idx;
          return (
            <div
              key={step.step}
              onClick={() => {
                setActiveStepIdx(idx);
                setIsAutoPlaying(false);
              }}
              className={`p-5 rounded-2xl cursor-pointer transition-all duration-300 flex flex-col justify-between relative group ${
                isActive
                  ? 'bg-gradient-to-b from-cyan-950/30 to-slate-950/90 border border-cyan-500/70 shadow-xl shadow-cyan-950/40 -translate-y-1'
                  : 'bg-slate-900/70 border border-slate-800/80 hover:border-slate-700 hover:-translate-y-0.5'
              }`}
            >
              {/* Active top line */}
              {isActive && (
                <div className="absolute top-0 left-4 right-4 h-[2px] bg-cyan-400 rounded-full shadow-[0_0_8px_#38bdf8]" />
              )}

              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded border ${
                    isActive
                      ? 'bg-cyan-950 text-cyan-300 border-cyan-800'
                      : 'bg-slate-950 text-slate-400 border-slate-800'
                  }`}>
                    STEP {step.step}
                  </span>
                  <span className={`w-2 h-2 rounded-full ${isActive ? 'bg-cyan-400 animate-ping' : 'bg-slate-700'}`} />
                </div>

                <h3 className={`text-sm font-bold mb-2 transition-colors ${isActive ? 'text-cyan-300' : 'text-white group-hover:text-cyan-400'}`}>
                  {step.title}
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed line-clamp-3">
                  {step.subtext}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center space-x-1.5 text-[10px] font-mono text-cyan-400/80 truncate">
                <FileCode className="w-3 h-3 text-cyan-500 shrink-0" />
                <span className="truncate">{step.technicalArtifact}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Active Phase Deep Dive Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-slate-950 via-[#081224] to-slate-950 border border-cyan-900/40 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-1 max-w-2xl">
          <div className="flex items-center space-x-2 text-xs font-mono text-cyan-400 font-bold">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>ACTIVE PHASE {activeStep.step}: {activeStep.title}</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            {activeStep.subtext}
          </p>
          <div className="text-[11px] font-mono text-slate-400 pt-1">
            Production code artifact: <span className="text-cyan-300 font-bold">{activeStep.technicalArtifact}</span>
          </div>
        </div>

        <button
          onClick={() => {
            setActiveStepIdx((prev) => (prev + 1) % WORKFLOW_STEPS.length);
            setIsAutoPlaying(false);
          }}
          className="px-4 py-2 rounded-xl bg-cyan-950/70 hover:bg-cyan-900 border border-cyan-700/50 text-cyan-300 text-xs font-mono flex items-center space-x-2 transition-all shrink-0"
        >
          <span>Next Phase</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
export default OperationalWorkflowInteractive;
