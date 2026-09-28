import React, { useEffect, useState } from 'react';
import { Info, Building2, BookOpen, ExternalLink } from 'lucide-react';
import { fetchSystemInfo } from '../api/client';
import { SystemInfoResponse } from '../types/api';

export const AboutPage: React.FC = () => {
  const [info, setInfo] = useState<SystemInfoResponse | null>(null);

  useEffect(() => {
    fetchSystemInfo()
      .then(setInfo)
      .catch((e) => console.error('Failed to load system info:', e));
  }, []);

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-white flex items-center space-x-2">
          <Info className="w-5 h-5 text-monsoon-400" />
          <span>System Information & Institutional Background</span>
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Ministry of Earth Sciences (MoES) • National Centre for Medium Range Weather Forecasting (NCMRWF)
        </p>
      </div>

      {/* Institutional Metadata Card */}
      <div className="glass-panel rounded-2xl p-6 space-y-4">
        <div className="flex items-center space-x-3 pb-3 border-b border-slate-800">
          <Building2 className="w-6 h-6 text-monsoon-400" />
          <div>
            <h3 className="text-base font-bold text-white">SIH26080 Problem Statement Overview</h3>
            <p className="text-xs text-slate-400">Smart India Hackathon 2026 — Ministry of Earth Sciences</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="space-y-1">
            <span className="text-slate-500 uppercase tracking-wider font-semibold text-[10px]">Problem Statement</span>
            <div className="font-semibold text-slate-200">
              Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts (SIH26080)
            </div>
          </div>

          <div className="space-y-1">
            <span className="text-slate-500 uppercase tracking-wider font-semibold text-[10px]">Client Organization</span>
            <div className="font-semibold text-slate-200">
              {info?.organization || 'Ministry of Earth Sciences (MoES)'}
            </div>
            <div className="text-slate-400">{info?.department || 'National Centre for Medium Range Weather Forecasting (NCMRWF)'}</div>
          </div>

          <div className="space-y-1">
            <span className="text-slate-500 uppercase tracking-wider font-semibold text-[10px]">Software System</span>
            <div className="font-mono text-monsoon-400 font-semibold">{info?.app_name || 'RAMP-MoES-NCMRWF'} v{info?.version || '0.1.0'}</div>
            <div className="text-slate-400">{info?.description}</div>
          </div>

          <div className="space-y-1">
            <span className="text-slate-500 uppercase tracking-wider font-semibold text-[10px]">Operational Data Mode</span>
            <div className="font-mono text-amber-400 font-semibold">{info?.data_mode || 'SYNTHETIC_DEMO'}</div>
            <div className="text-slate-400">Governed under strict scientific verification protocols</div>
          </div>
        </div>
      </div>

      {/* Scientific Background */}
      <div className="glass-card rounded-xl p-6 space-y-3">
        <h4 className="text-sm font-semibold text-white flex items-center space-x-2">
          <BookOpen className="w-4 h-4 text-indigo-400" />
          <span>Scientific Motivation: Why Regime Awareness Matters</span>
        </h4>
        <div className="space-y-2 text-xs text-slate-300 leading-relaxed">
          <p>
            The Indian Summer Monsoon (June–September) delivers over 70% of India’s annual precipitation.
            Modern Numerical Weather Prediction (NWP) systems—such as NCMRWF's Unified Model (NCUM) and National Ensemble (NEPS)—provide
            crucial guidance but suffer from systematic, state-dependent biases.
          </p>
          <p>
            A static bias correction that subtracts 5 mm from a forecast grid cell during an <em>Active Monsoon</em> phase will severely
            degrade predictions during a dry <em>Break Monsoon</em> spell. Similarly, terrain-induced orographic precipitation requires
            drastically different non-linear adjustments than synoptic cyclonic depressions migrating across the Bay of Bengal.
          </p>
          <p>
            <strong>RAMP (Regime-Aware Mixture-of-Experts)</strong> solves this fundamental limitation by conditioning non-linear corrections
            on the prevailing meteorological regime, using soft probability vectors to continuously blend expert model adjustments.
          </p>
        </div>
      </div>

      {/* API References */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
        <div>
          <div className="font-semibold text-white">Live OpenAPI Interactive Documentation</div>
          <div className="text-slate-400">Explore auto-generated Swagger UI and backend contracts</div>
        </div>
        <a
          href={import.meta.env.VITE_API_BASE_URL ? `${import.meta.env.VITE_API_BASE_URL}/docs` : '/docs'}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-monsoon-600 hover:bg-monsoon-500 text-white font-medium transition-colors"
        >
          <span>Open Swagger Docs</span>
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      </div>
    </div>
  );
};
