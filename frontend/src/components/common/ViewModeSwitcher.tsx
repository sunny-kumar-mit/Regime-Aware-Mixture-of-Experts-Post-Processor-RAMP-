import React, { useState, useEffect } from 'react';
import { Monitor, Smartphone, X } from 'lucide-react';
import { useViewMode } from '../../hooks/useViewMode';

export const ViewModeSwitcher: React.FC = () => {
  const { mode, isMobileDevice, toggleMode } = useViewMode();
  const [collapsed, setCollapsed] = useState(false);

  // Auto-collapse to a compact floating badge after 6 seconds
  useEffect(() => {
    const timer = setTimeout(() => {
      setCollapsed(true);
    }, 6000);
    return () => clearTimeout(timer);
  }, []);

  // Show only on mobile devices or narrow viewports (< 1024px)
  if (!isMobileDevice) {
    return null;
  }

  const isDesktop = mode === 'desktop';

  return (
    <aside
      aria-label="Viewport display mode switcher"
      className="fixed bottom-4 right-4 z-[9990] select-none flex items-center print:hidden"
    >
      {collapsed ? (
        <button
          onClick={() => {
            setCollapsed(false);
          }}
          className={`group flex items-center justify-center p-2.5 rounded-full shadow-2xl backdrop-blur-xl border transition-all duration-300 transform hover:scale-105 active:scale-95 ${
            isDesktop
              ? 'bg-slate-900/90 border-cyan-500/50 text-cyan-400 shadow-cyan-950/40 hover:bg-slate-800'
              : 'bg-slate-900/90 border-amber-500/50 text-amber-400 shadow-amber-950/40 hover:bg-slate-800'
          }`}
          title={isDesktop ? 'Desktop View (Auto Active) — Tap to expand' : 'Mobile View Active — Tap to expand'}
          aria-label="Expand View Mode Controls"
        >
          {isDesktop ? (
            <div className="relative">
              <Monitor className="w-4 h-4 text-cyan-300" />
              <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            </div>
          ) : (
            <div className="relative">
              <Smartphone className="w-4 h-4 text-amber-300" />
              <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-amber-400" />
            </div>
          )}
        </button>
      ) : (
        <div className="flex items-center space-x-1.5 p-1 rounded-full bg-slate-900/95 backdrop-blur-xl border border-slate-700/80 shadow-2xl shadow-black/80 animate-in fade-in slide-in-from-bottom-2 duration-200">
          {/* Main Mode Toggle Button */}
          <button
            onClick={toggleMode}
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-mono font-semibold transition-all duration-200 ${
              isDesktop
                ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-500/40 hover:bg-cyan-900/60 shadow-sm'
                : 'bg-amber-950/80 text-amber-300 border border-amber-500/40 hover:bg-amber-900/60 shadow-sm'
            }`}
            title="Toggle between Desktop Preview and Mobile Responsive layout"
          >
            {isDesktop ? (
              <>
                <Monitor className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                <span className="tracking-tight whitespace-nowrap">Desktop View (Auto)</span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              </>
            ) : (
              <>
                <Smartphone className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                <span className="tracking-tight whitespace-nowrap">Mobile View</span>
              </>
            )}
          </button>

          {/* Minimize Button */}
          <button
            onClick={() => setCollapsed(true)}
            aria-label="Collapse view controls"
            className="p-1 rounded-full text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
            title="Minimize"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </aside>
  );
};
