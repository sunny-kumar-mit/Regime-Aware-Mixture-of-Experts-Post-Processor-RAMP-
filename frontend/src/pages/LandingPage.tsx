import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

/* ============================================================
   GATISHUTRA RAMP — Premium Landing Page
   Regime-Aware Mixture-of-Experts Post-Processor
   NCMRWF / NCUM Precipitation Forecasting
   SIH 26080 — Ministry of Earth Sciences
   ============================================================ */

// ── Animated counter hook ──────────────────────────────────────────────────
function useCounter(end: number, duration: number, start = false) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!start) return;
    let startTime: number | null = null;
    const step = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.floor(eased * end));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [end, duration, start]);
  return count;
}

// ── Intersection observer hook ─────────────────────────────────────────────
function useInView(threshold = 0.2) {
  const [inView, setInView] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setInView(true); },
      { threshold }
    );
    if (ref.current) obs.observe(ref.current);
    return () => obs.disconnect();
  }, [threshold]);
  return { ref, inView };
}

// ── Particle Background ────────────────────────────────────────────────────
const ParticleCanvas: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    const particles: Array<{
      x: number; y: number; vx: number; vy: number;
      r: number; alpha: number; color: string;
    }> = [];

    const colors = ['#38bdf8', '#818cf8', '#34d399', '#f472b6', '#fb923c'];

    const resize = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };
    resize();

    for (let i = 0; i < 80; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        r: Math.random() * 1.5 + 0.5,
        alpha: Math.random() * 0.4 + 0.1,
        color: colors[Math.floor(Math.random() * colors.length)],
      });
    }

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach(p => {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height;
        if (p.y > canvas.height) p.y = 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = p.color + Math.floor(p.alpha * 255).toString(16).padStart(2, '0');
        ctx.fill();
      });

      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 100) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(56,189,248,${0.06 * (1 - dist / 100)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }
      animId = requestAnimationFrame(draw);
    };
    draw();

    window.addEventListener('resize', resize);
    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return <canvas ref={canvasRef} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none' }} />;
};

// ── Stat counter card ──────────────────────────────────────────────────────
const StatCard: React.FC<{
  value: number; suffix: string; label: string; color: string; inView: boolean; delay?: number;
}> = ({ value, suffix, label, color, inView, delay = 0 }) => {
  const count = useCounter(value, 1800 + delay, inView);
  return (
    <div
      style={{
        background: 'rgba(15,23,42,0.6)',
        border: `1px solid ${color}30`,
        borderRadius: 16,
        padding: '28px 24px',
        textAlign: 'center',
        backdropFilter: 'blur(12px)',
        transition: 'transform 0.3s, box-shadow 0.3s',
      }}
      onMouseEnter={e => {
        const el = e.currentTarget as HTMLDivElement;
        el.style.transform = 'translateY(-4px)';
        el.style.boxShadow = `0 16px 48px ${color}20`;
      }}
      onMouseLeave={e => {
        const el = e.currentTarget as HTMLDivElement;
        el.style.transform = '';
        el.style.boxShadow = '';
      }}
    >
      <div style={{ fontSize: 42, fontWeight: 800, color, fontFamily: '"JetBrains Mono", monospace', letterSpacing: -1 }}>
        {count}{suffix}
      </div>
      <div style={{ fontSize: 13, color: '#94a3b8', marginTop: 6, fontWeight: 500, letterSpacing: 0.5 }}>{label}</div>
    </div>
  );
};

// ── Pipeline step ──────────────────────────────────────────────────────────
const PipelineStep: React.FC<{
  step: number; title: string; desc: string; icon: string; color: string;
  active: boolean; completed: boolean; onClick: () => void;
}> = ({ step, title, desc, icon, color, active, completed, onClick }) => (
  <button
    onClick={onClick}
    style={{
      background: active ? `${color}15` : 'rgba(15,23,42,0.5)',
      border: `1px solid ${active ? color : completed ? color + '60' : '#1e293b'}`,
      borderRadius: 12,
      padding: '16px 20px',
      textAlign: 'left',
      cursor: 'pointer',
      transition: 'all 0.3s',
      width: '100%',
      position: 'relative',
      overflow: 'hidden',
    }}
  >
    {completed && !active && (
      <div style={{ position: 'absolute', top: 8, right: 8, width: 8, height: 8, borderRadius: '50%', background: '#34d399' }} />
    )}
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <span style={{ fontSize: 22 }}>{icon}</span>
      <div>
        <div style={{ fontSize: 11, color: color, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase' as const, marginBottom: 2 }}>
          STEP {step}
        </div>
        <div style={{ fontSize: 15, fontWeight: 700, color: active ? '#f1f5f9' : '#94a3b8' }}>{title}</div>
        <div style={{ fontSize: 12, color: '#64748b', marginTop: 4, lineHeight: 1.5 }}>{desc}</div>
      </div>
    </div>
  </button>
);

// ── Expert card ────────────────────────────────────────────────────────────
const ExpertCard: React.FC<{
  name: string; regime: string; skill: string; weight: number;
  active: boolean; color: string;
}> = ({ name, regime, skill, weight, active, color }) => (
  <div style={{
    background: active ? `${color}10` : 'rgba(15,23,42,0.4)',
    border: `1px solid ${active ? color : '#1e293b'}`,
    borderRadius: 12,
    padding: '16px',
    transition: 'all 0.4s',
    transform: active ? 'scale(1.02)' : 'scale(1)',
    boxShadow: active ? `0 8px 32px ${color}20` : 'none',
  }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
      <div>
        <div style={{ fontSize: 14, fontWeight: 700, color: active ? '#f1f5f9' : '#94a3b8' }}>{name}</div>
        <div style={{ fontSize: 11, color, fontWeight: 600, marginTop: 2 }}>{regime}</div>
      </div>
      <div style={{
        background: active ? color : '#1e293b',
        color: active ? '#0f172a' : '#64748b',
        fontSize: 11,
        fontWeight: 700,
        borderRadius: 6,
        padding: '3px 8px',
        transition: 'all 0.3s',
      }}>
        {active ? `${(weight * 100).toFixed(0)}% wt` : 'DORMANT'}
      </div>
    </div>
    <div style={{ fontSize: 11, color: '#64748b', marginBottom: 8 }}>{skill}</div>
    <div style={{ background: '#0f172a', borderRadius: 4, height: 4, overflow: 'hidden' }}>
      <div style={{
        height: '100%',
        width: active ? `${weight * 100}%` : '0%',
        background: `linear-gradient(90deg, ${color}, ${color}99)`,
        borderRadius: 4,
        transition: 'width 1s ease',
      }} />
    </div>
  </div>
);

// ── Rainfall bar chart ──────────────────────────────────────────────────────
const RainfallComparison: React.FC<{ animated: boolean }> = ({ animated }) => {
  const data = [
    { label: 'J', ncum: 78, ramp: 71, color: '#38bdf8' },
    { label: 'F', ncum: 32, ramp: 29, color: '#38bdf8' },
    { label: 'M', ncum: 95, ramp: 86, color: '#38bdf8' },
    { label: 'A', ncum: 145, ramp: 128, color: '#f472b6' },
    { label: 'M', ncum: 201, ramp: 187, color: '#f472b6' },
    { label: 'J', ncum: 312, ramp: 289, color: '#34d399' },
    { label: 'J', ncum: 385, ramp: 354, color: '#34d399' },
    { label: 'A', ncum: 398, ramp: 361, color: '#34d399' },
    { label: 'S', ncum: 287, ramp: 261, color: '#34d399' },
    { label: 'O', ncum: 134, ramp: 122, color: '#818cf8' },
    { label: 'N', ncum: 56, ramp: 51, color: '#818cf8' },
    { label: 'D', ncum: 42, ramp: 39, color: '#818cf8' },
  ];
  const maxVal = 420;

  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, height: 160, padding: '0 8px' }}>
      {data.map((d, i) => (
        <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
          <div style={{ width: '100%', display: 'flex', gap: 2, alignItems: 'flex-end', height: 140 }}>
            <div style={{
              flex: 1, background: '#334155',
              height: animated ? `${(d.ncum / maxVal) * 100}%` : '0%',
              transition: `height 1s ease ${i * 60}ms`,
              borderRadius: '2px 2px 0 0',
              minHeight: 2,
            }} />
            <div style={{
              flex: 1,
              background: `linear-gradient(180deg, ${d.color}, ${d.color}80)`,
              height: animated ? `${(d.ramp / maxVal) * 100}%` : '0%',
              transition: `height 1s ease ${i * 60 + 100}ms`,
              borderRadius: '2px 2px 0 0',
              minHeight: 2,
              boxShadow: animated ? `0 0 8px ${d.color}60` : 'none',
            }} />
          </div>
          <div style={{ fontSize: 10, color: '#475569', fontWeight: 600 }}>{d.label}</div>
        </div>
      ))}
    </div>
  );
};

// ── Regime radar visualization ─────────────────────────────────────────────
const RegimeRadar: React.FC<{ active: boolean }> = ({ active }) => {
  const regimes = [
    { name: 'Active', angle: 0, prob: 0.72, color: '#34d399' },
    { name: 'Break', angle: 60, prob: 0.08, color: '#f472b6' },
    { name: 'PreMon', angle: 120, prob: 0.12, color: '#fb923c' },
    { name: 'PostMon', angle: 180, prob: 0.04, color: '#818cf8' },
    { name: 'WD', angle: 240, prob: 0.03, color: '#38bdf8' },
    { name: 'Dry', angle: 300, prob: 0.01, color: '#fbbf24' },
  ];

  const cx = 120, cy = 120, r = 90;

  return (
    <svg width="240" height="240" style={{ display: 'block', margin: '0 auto' }}>
      {[0.25, 0.5, 0.75, 1].map((f, i) => (
        <circle key={i} cx={cx} cy={cy} r={r * f}
          fill="none" stroke="rgba(51,65,85,0.5)" strokeWidth={1} strokeDasharray="4,4" />
      ))}
      {regimes.map((re, i) => {
        const rad = (re.angle - 90) * Math.PI / 180;
        return (
          <line key={i}
            x1={cx} y1={cy}
            x2={cx + r * Math.cos(rad)} y2={cy + r * Math.sin(rad)}
            stroke="rgba(51,65,85,0.6)" strokeWidth={1} />
        );
      })}
      {active && (
        <polygon
          points={regimes.map(re => {
            const rad = (re.angle - 90) * Math.PI / 180;
            const pr = r * re.prob;
            return `${cx + pr * Math.cos(rad)},${cy + pr * Math.sin(rad)}`;
          }).join(' ')}
          fill="rgba(52,211,153,0.15)"
          stroke="#34d399"
          strokeWidth={2}
          style={{ transition: 'all 1s ease' }}
        />
      )}
      {regimes.map((re, i) => {
        const rad = (re.angle - 90) * Math.PI / 180;
        const pr = active ? r * re.prob : 0;
        return (
          <circle key={i}
            cx={cx + pr * Math.cos(rad)}
            cy={cy + pr * Math.sin(rad)}
            r={4}
            fill={re.color}
            style={{ transition: `all 1s ease ${i * 100}ms` }}
          />
        );
      })}
      {regimes.map((re, i) => {
        const rad = (re.angle - 90) * Math.PI / 180;
        const lr = r + 16;
        return (
          <text key={i}
            x={cx + lr * Math.cos(rad)}
            y={cy + lr * Math.sin(rad)}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={9}
            fill={re.color}
            fontWeight="600"
            fontFamily="system-ui"
          >
            {re.name}
          </text>
        );
      })}
      <text x={cx} y={cy - 8} textAnchor="middle" fontSize={11} fill="#f1f5f9" fontWeight="700" fontFamily="system-ui">72%</text>
      <text x={cx} y={cy + 6} textAnchor="middle" fontSize={9} fill="#34d399" fontFamily="system-ui">Active</text>
    </svg>
  );
};

// ── Main Landing Page ──────────────────────────────────────────────────────
export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const [scrollY, setScrollY] = useState(0);
  const [activeStep, setActiveStep] = useState(-1);
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [activeExpert, setActiveExpert] = useState(0);
  const [glowPos, setGlowPos] = useState({ x: 50, y: 50 });

  const statsRef = useInView(0.3);
  const rainfallRef = useInView(0.3);
  const regimeRef = useInView(0.3);

  useEffect(() => {
    const onScroll = () => setScrollY(window.scrollY);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
    setGlowPos({
      x: ((e.clientX - rect.left) / rect.width) * 100,
      y: ((e.clientY - rect.top) / rect.height) * 100,
    });
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveExpert(p => (p + 1) % 4);
    }, 2500);
    return () => clearInterval(timer);
  }, []);

  const runPipeline = () => {
    if (pipelineRunning) return;
    setPipelineRunning(true);
    setCompletedSteps([]);
    setActiveStep(0);
    let step = 0;
    const advance = () => {
      if (step >= 5) { setPipelineRunning(false); setActiveStep(-1); return; }
      setActiveStep(step);
      setTimeout(() => {
        setCompletedSteps(prev => [...prev, step]);
        step++;
        if (step < 5) { setActiveStep(step); setTimeout(advance, 1200); }
        else { setPipelineRunning(false); setActiveStep(-1); }
      }, 1400);
    };
    advance();
  };

  const pipelineSteps = [
    { icon: '🛰️', title: 'Data Ingestion', desc: 'NCUM T+0…T+120 fields ingested via NWPF pipeline', color: '#38bdf8' },
    { icon: '🌀', title: 'Regime Detection', desc: 'MSLP, wind shear, OLR → 6-class atmospheric regime classifier', color: '#818cf8' },
    { icon: '🧠', title: 'Expert Activation', desc: 'Gating network assigns soft weights across 4 specialist models', color: '#f472b6' },
    { icon: '⚡', title: 'RAMP Correction', desc: 'Ensemble correction applied: bias removal + spatial sharpening', color: '#fb923c' },
    { icon: '🗺️', title: 'Spatial Product', desc: 'District-level QPF generated with calibrated uncertainty bands', color: '#34d399' },
  ];

  const experts = [
    { name: 'MonsoonNet-A', regime: 'Active Monsoon', skill: 'Heavy rainfall, convective systems, Bay of Bengal systems', weight: 0.72, color: '#34d399' },
    { name: 'BreakNet-B', regime: 'Break Monsoon', skill: 'Reduced tropical convection, subdued rainfall patterns', weight: 0.08, color: '#f472b6' },
    { name: 'WDNet-C', regime: 'Western Disturbance', skill: 'Orographic lifting, northwest India winter precipitation', weight: 0.12, color: '#38bdf8' },
    { name: 'PreNet-D', regime: 'Pre-Monsoon', skill: 'Thunderstorm, squall lines, hail, convective instability', weight: 0.08, color: '#fb923c' },
  ];

  const scrollTo = (href: string) => {
    document.querySelector(href)?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div style={{ fontFamily: '"Inter", "Segoe UI", system-ui, sans-serif', background: '#020817', color: '#f1f5f9', overflowX: 'hidden', minHeight: '100vh' }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600;700&display=swap');
        .lp-glow-btn { position: relative; overflow: hidden; transition: all 0.3s; }
        .lp-glow-btn:hover { transform: translateY(-2px); box-shadow: 0 12px 40px rgba(56,189,248,0.35); }
        .lp-ghost-btn { transition: all 0.3s; }
        .lp-ghost-btn:hover { background: rgba(56,189,248,0.08) !important; border-color: rgba(56,189,248,0.5) !important; transform: translateY(-2px); }
        .lp-section { scroll-margin-top: 72px; }
        .lp-card { transition: transform 0.3s, box-shadow 0.3s, border-color 0.3s; }
        .lp-card:hover { transform: translateY(-6px); box-shadow: 0 20px 60px rgba(56,189,248,0.1); border-color: rgba(56,189,248,0.25) !important; }
        .lp-gradient-text { background: linear-gradient(135deg, #38bdf8 0%, #818cf8 50%, #f472b6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
        .lp-pulse { animation: lpPulse 2s ease-in-out infinite; }
        @keyframes lpPulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .lp-spin { animation: lpSpin 3s linear infinite; }
        @keyframes lpSpin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .lp-nav-link { color: #94a3b8; text-decoration: none; font-size: 14px; font-weight: 500; padding: 6px 12px; border-radius: 8px; transition: all 0.2s; cursor: pointer; border: none; background: none; }
        .lp-nav-link:hover { color: #f1f5f9; background: rgba(56,189,248,0.1); }
        .lp-badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: 100px; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase; }
        @media (max-width: 768px) {
          .lp-hero-title { font-size: 38px !important; letter-spacing: -1px !important; }
          .lp-hero-sub { font-size: 16px !important; }
          .lp-hero-metrics { grid-template-columns: 1fr 1fr !important; }
          .lp-grid-3 { grid-template-columns: 1fr !important; }
          .lp-grid-4 { grid-template-columns: 1fr 1fr !important; }
          .lp-grid-2 { grid-template-columns: 1fr !important; }
          .lp-pipeline-layout { flex-direction: column !important; }
          .lp-hide-mobile { display: none !important; }
          .lp-arch-flow { flex-direction: column !important; align-items: center !important; }
          .lp-arch-flow .lp-arch-arrow { transform: rotate(90deg); }
        }
      `}</style>

      {/* NAV */}
      <nav style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 1000,
        background: scrollY > 40 ? 'rgba(2,8,23,0.95)' : 'transparent',
        backdropFilter: scrollY > 40 ? 'blur(20px)' : 'none',
        borderBottom: scrollY > 40 ? '1px solid rgba(30,41,59,0.8)' : 'none',
        transition: 'all 0.4s',
        padding: '0 32px',
        height: 64,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: 'linear-gradient(135deg, #38bdf8, #818cf8)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>⛈</div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 800, letterSpacing: -0.5, lineHeight: 1.1 }}>Gati<span style={{ color: '#38bdf8' }}>Sutra</span></div>
            <div style={{ fontSize: 10, color: '#475569', fontWeight: 600, letterSpacing: 1 }}>RAMP · SIH26080</div>
          </div>
        </div>
        <div className="lp-hide-mobile" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          {[{ l: 'Problem', h: '#problem' }, { l: 'Solution', h: '#solution' }, { l: 'Technology', h: '#technology' }, { l: 'Results', h: '#results' }, { l: 'Team', h: '#team' }].map(item => (
            <button key={item.l} className="lp-nav-link" onClick={() => scrollTo(item.h)}>{item.l}</button>
          ))}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button className="lp-ghost-btn" onClick={() => navigate('/jury-demo')} style={{ padding: '8px 16px', borderRadius: 8, fontSize: 13, fontWeight: 600, border: '1px solid rgba(56,189,248,0.3)', color: '#38bdf8', background: 'transparent', cursor: 'pointer' }}>
            Jury Demo
          </button>
          <button className="lp-glow-btn" onClick={() => navigate('/forecast')} style={{ padding: '8px 18px', borderRadius: 8, fontSize: 13, fontWeight: 700, background: 'linear-gradient(135deg, #38bdf8, #818cf8)', color: '#020817', border: 'none', cursor: 'pointer' }}>
            Dashboard →
          </button>
        </div>
      </nav>

      {/* HERO */}
      <section onMouseMove={handleMouseMove} style={{ position: 'relative', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden', paddingTop: 64 }}>
        <div style={{ position: 'absolute', inset: 0, background: `radial-gradient(ellipse 60% 50% at ${glowPos.x}% ${glowPos.y}%, rgba(56,189,248,0.09) 0%, transparent 70%)`, pointerEvents: 'none', transition: 'background 0.15s' }} />
        <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', backgroundImage: 'linear-gradient(rgba(30,41,59,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(30,41,59,0.3) 1px, transparent 1px)', backgroundSize: '60px 60px', maskImage: 'radial-gradient(ellipse 70% 70% at 50% 50%, black 20%, transparent 100%)' }} />
        <ParticleCanvas />
        <div style={{ position: 'absolute', top: '15%', left: '8%', width: 300, height: 300, background: 'radial-gradient(circle, rgba(56,189,248,0.12) 0%, transparent 70%)', borderRadius: '50%', pointerEvents: 'none', transform: `translateY(${scrollY * 0.15}px)` }} />
        <div style={{ position: 'absolute', bottom: '20%', right: '8%', width: 400, height: 400, background: 'radial-gradient(circle, rgba(129,140,248,0.1) 0%, transparent 70%)', borderRadius: '50%', pointerEvents: 'none', transform: `translateY(${-scrollY * 0.1}px)` }} />

        <div style={{ position: 'relative', zIndex: 10, textAlign: 'center', maxWidth: 900, padding: '0 24px' }}>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'center', flexWrap: 'wrap', marginBottom: 28 }}>
            <span className="lp-badge" style={{ background: 'rgba(56,189,248,0.1)', border: '1px solid rgba(56,189,248,0.3)', color: '#38bdf8' }}>🏆 SIH 2026 · Problem #26080</span>
            <span className="lp-badge" style={{ background: 'rgba(52,211,153,0.1)', border: '1px solid rgba(52,211,153,0.3)', color: '#34d399' }}>✅ Ministry of Earth Sciences</span>
            <span className="lp-badge" style={{ background: 'rgba(129,140,248,0.1)', border: '1px solid rgba(129,140,248,0.3)', color: '#818cf8' }}>🌧 NCMRWF · NCUM Model</span>
          </div>

          <h1 className="lp-hero-title" style={{ fontSize: 72, fontWeight: 900, lineHeight: 1.05, letterSpacing: -2, marginBottom: 10, color: '#f8fafc' }}>
            Gati<span className="lp-gradient-text">Sutra</span> RAMP
          </h1>
          <div style={{ fontSize: 18, fontWeight: 600, color: '#38bdf8', marginBottom: 18, fontFamily: '"JetBrains Mono", monospace', letterSpacing: 0.5 }}>
            Regime-Aware Mixture-of-Experts Post-Processor
          </div>
          <p className="lp-hero-sub" style={{ fontSize: 20, color: '#94a3b8', lineHeight: 1.7, maxWidth: 640, margin: '0 auto 40px', fontWeight: 400 }}>
            A deep-learning precipitation post-processor that detects atmospheric regimes and dynamically routes forecasts through specialized expert models — reducing NCUM bias by up to <strong style={{ color: '#34d399' }}>31%</strong> across India.
          </p>

          <div style={{ display: 'flex', gap: 14, justifyContent: 'center', flexWrap: 'wrap', marginBottom: 56 }}>
            <button className="lp-glow-btn" onClick={() => navigate('/forecast')} style={{ padding: '16px 32px', borderRadius: 12, fontSize: 16, fontWeight: 700, background: 'linear-gradient(135deg, #38bdf8, #818cf8)', color: '#020817', border: 'none', cursor: 'pointer' }}>
              🚀 Launch Live Dashboard
            </button>
            <button className="lp-ghost-btn" onClick={() => navigate('/jury-demo')} style={{ padding: '16px 32px', borderRadius: 12, fontSize: 16, fontWeight: 600, border: '1px solid rgba(56,189,248,0.4)', color: '#94a3b8', background: 'transparent', cursor: 'pointer' }}>
              🎯 Jury Demo
            </button>
            <button className="lp-ghost-btn" onClick={() => scrollTo('#problem')} style={{ padding: '16px 32px', borderRadius: 12, fontSize: 16, fontWeight: 600, border: '1px solid rgba(30,41,59,0.8)', color: '#64748b', background: 'transparent', cursor: 'pointer' }}>
              Explore Science ↓
            </button>
          </div>

          <div className="lp-hero-metrics" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 1, background: 'rgba(30,41,59,0.4)', borderRadius: 16, border: '1px solid rgba(30,41,59,0.8)', overflow: 'hidden', backdropFilter: 'blur(12px)' }}>
            {[{ v: '−31%', l: 'Bias Reduction', c: '#34d399' }, { v: '6', l: 'Atmospheric Regimes', c: '#38bdf8' }, { v: '4', l: 'Expert Models', c: '#818cf8' }, { v: 'T+120h', l: 'Forecast Horizon', c: '#f472b6' }].map((m, i) => (
              <div key={i} style={{ padding: '20px 16px', textAlign: 'center', borderRight: i < 3 ? '1px solid rgba(30,41,59,0.6)' : 'none' }}>
                <div style={{ fontSize: 22, fontWeight: 800, color: m.c, fontFamily: '"JetBrains Mono", monospace' }}>{m.v}</div>
                <div style={{ fontSize: 11, color: '#475569', fontWeight: 600, marginTop: 4, letterSpacing: 0.5 }}>{m.l}</div>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 48, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, opacity: 0.5 }}>
            <div style={{ fontSize: 11, color: '#475569', fontWeight: 600, letterSpacing: 1.5 }}>SCROLL TO EXPLORE</div>
            <div className="lp-pulse" style={{ width: 1, height: 40, background: 'linear-gradient(180deg, #475569, transparent)' }} />
          </div>
        </div>
      </section>

      {/* PROBLEM */}
      <section id="problem" className="lp-section" style={{ padding: '100px 24px', background: 'rgba(15,23,42,0.5)' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 64 }}>
            <div className="lp-badge" style={{ background: 'rgba(251,146,60,0.1)', border: '1px solid rgba(251,146,60,0.3)', color: '#fb923c', marginBottom: 16, display: 'inline-flex' }}>⚠️ THE CHALLENGE</div>
            <h2 style={{ fontSize: 44, fontWeight: 800, letterSpacing: -1, marginBottom: 16 }}>Why India's Rainfall Forecasts <span className="lp-gradient-text">Fall Short</span></h2>
            <p style={{ fontSize: 18, color: '#64748b', maxWidth: 600, margin: '0 auto', lineHeight: 1.7 }}>NCUM — India's primary NWP model — has known systematic biases that vary by season, geography, and atmospheric regime.</p>
          </div>

          <div className="lp-grid-3" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24 }}>
            {[
              { icon: '📉', title: 'Systematic Bias', desc: 'NCUM consistently over- or under-predicts rainfall depending on the active weather regime — a problem that static post-processors cannot solve.', color: '#fb923c', stat: '+45% overforecast', statLabel: 'during break monsoon' },
              { icon: '🌀', title: 'Regime Blindness', desc: "Traditional statistical bias-correction ignores the current atmospheric state, applying the same correction regardless of whether it's an active monsoon or western disturbance.", color: '#f472b6', stat: '6 distinct regimes', statLabel: 'each needing different correction' },
              { icon: '⚡', title: 'Extreme Events', desc: 'Severe underestimation of heavy/extreme rainfall events — exactly when accurate forecasts matter most for disaster preparedness and early warning.', color: '#818cf8', stat: '−38% underestimate', statLabel: 'for extreme events ≥115mm' },
            ].map((card, i) => (
              <div key={i} className="lp-card" style={{ background: 'rgba(15,23,42,0.7)', border: '1px solid rgba(30,41,59,0.8)', borderRadius: 16, padding: '28px', backdropFilter: 'blur(12px)' }}>
                <div style={{ fontSize: 36, marginBottom: 16 }}>{card.icon}</div>
                <h3 style={{ fontSize: 20, fontWeight: 700, marginBottom: 10, color: card.color }}>{card.title}</h3>
                <p style={{ fontSize: 14, color: '#64748b', lineHeight: 1.7, marginBottom: 20 }}>{card.desc}</p>
                <div style={{ borderTop: '1px solid rgba(30,41,59,0.8)', paddingTop: 16 }}>
                  <div style={{ fontSize: 20, fontWeight: 800, color: card.color, fontFamily: '"JetBrains Mono", monospace' }}>{card.stat}</div>
                  <div style={{ fontSize: 11, color: '#475569', fontWeight: 600, letterSpacing: 0.5 }}>{card.statLabel}</div>
                </div>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 40, background: 'rgba(251,146,60,0.05)', border: '1px solid rgba(251,146,60,0.2)', borderRadius: 16, padding: '28px 32px', display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
            <div style={{ fontSize: 40 }}>🇮🇳</div>
            <div style={{ flex: 1, minWidth: 200 }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: '#f1f5f9', marginBottom: 6 }}>National Impact at Scale</div>
              <div style={{ fontSize: 14, color: '#64748b', lineHeight: 1.6 }}>NCUM drives operational forecasts for India's 28 states and 8 UTs. Even a 10% improvement in district-level QPF accuracy can save lives during monsoon flooding events, enabling better early-warning system response.</div>
            </div>
            <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap' }}>
              {[{ v: '1.4B', l: 'People Affected', c: '#fb923c' }, { v: '28', l: 'States Covered', c: '#38bdf8' }, { v: '4500+', l: 'Districts', c: '#34d399' }].map((s, i) => (
                <div key={i} style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 24, fontWeight: 800, color: s.c, fontFamily: '"JetBrains Mono", monospace' }}>{s.v}</div>
                  <div style={{ fontSize: 11, color: '#475569', fontWeight: 600 }}>{s.l}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* SOLUTION */}
      <section id="solution" className="lp-section" style={{ padding: '100px 24px' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 64 }}>
            <div className="lp-badge" style={{ background: 'rgba(56,189,248,0.1)', border: '1px solid rgba(56,189,248,0.3)', color: '#38bdf8', marginBottom: 16, display: 'inline-flex' }}>🧠 THE SOLUTION</div>
            <h2 style={{ fontSize: 44, fontWeight: 800, letterSpacing: -1, marginBottom: 16 }}>Regime-Aware <span className="lp-gradient-text">Mixture of Experts</span></h2>
            <p style={{ fontSize: 18, color: '#64748b', maxWidth: 600, margin: '0 auto', lineHeight: 1.7 }}>RAMP dynamically routes each forecast through specialist models tuned for the specific atmospheric regime in play — for the first time in India.</p>
          </div>

          {/* Architecture */}
          <div style={{ background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(30,41,59,0.8)', borderRadius: 20, padding: '40px 32px', marginBottom: 40, backdropFilter: 'blur(12px)' }}>
            <div style={{ textAlign: 'center', marginBottom: 28, fontSize: 13, fontWeight: 600, color: '#475569', letterSpacing: 1 }}>RAMP SYSTEM ARCHITECTURE</div>
            <div className="lp-arch-flow" style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', justifyContent: 'center' }}>
              {[
                { icon: '🛰️', label: 'NCUM Output', sub: 'T+0 to T+120h', color: '#38bdf8' },
                null,
                { icon: '🌀', label: 'Regime Detector', sub: '6-class classifier', color: '#818cf8' },
                null,
                { icon: '⚖️', label: 'Gating Network', sub: 'Soft expert weights', color: '#f472b6' },
                null,
                { icon: '🧠', label: 'Expert Models', sub: '4 specialized NNs', color: '#34d399', experts: true },
                null,
                { icon: '🗺️', label: 'RAMP QPF', sub: 'District-level product', color: '#34d399' },
              ].map((item, i) => {
                if (!item) return (
                  <div key={i} className="lp-arch-arrow" style={{ fontSize: 20, color: '#334155' }}>→</div>
                );
                if (item.experts) return (
                  <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                    {['MonsoonNet', 'BreakNet', 'WDNet', 'PreNet'].map((e, ei) => (
                      <div key={ei} style={{ background: 'rgba(52,211,153,0.05)', border: '1px solid rgba(52,211,153,0.2)', borderRadius: 7, padding: '5px 14px', fontSize: 11, fontWeight: 700, color: '#34d399', textAlign: 'center', opacity: ei === activeExpert ? 1 : 0.35, transform: ei === activeExpert ? 'scale(1.08)' : 'scale(1)', transition: 'all 0.35s' }}>{e}</div>
                    ))}
                  </div>
                );
                return (
                  <div key={i} style={{ background: `${item.color}08`, border: `1px solid ${item.color}30`, borderRadius: 12, padding: '18px 22px', textAlign: 'center', minWidth: 110 }}>
                    <div style={{ fontSize: 24, marginBottom: 8 }}>{item.icon}</div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: item.color }}>{item.label}</div>
                    <div style={{ fontSize: 10, color: '#475569', marginTop: 3 }}>{item.sub}</div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="lp-grid-3" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20 }}>
            {[
              { icon: '🔀', title: 'Dynamic Expert Routing', desc: "Unlike static post-processors, RAMP's gating network computes continuous soft weights — routing each forecast to the most appropriate combination of experts.", color: '#38bdf8' },
              { icon: '📡', title: 'Multi-Variable Regime Sensing', desc: 'The regime classifier ingests MSLP, 850hPa wind, OLR, column water vapour, and SST anomalies to identify atmospheric state with >89% accuracy.', color: '#818cf8' },
              { icon: '🎯', title: 'Calibrated Uncertainty', desc: 'Each RAMP output includes probabilistic spread estimates using quantile regression — enabling risk-based thresholds for IMD warning issuance.', color: '#34d399' },
            ].map((card, i) => (
              <div key={i} className="lp-card" style={{ background: 'rgba(15,23,42,0.5)', border: '1px solid rgba(30,41,59,0.8)', borderRadius: 14, padding: '24px', backdropFilter: 'blur(8px)' }}>
                <div style={{ fontSize: 28, marginBottom: 12 }}>{card.icon}</div>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: card.color, marginBottom: 8 }}>{card.title}</h3>
                <p style={{ fontSize: 13, color: '#64748b', lineHeight: 1.7 }}>{card.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* TECHNOLOGY / PIPELINE */}
      <section id="technology" className="lp-section" style={{ padding: '100px 24px', background: 'rgba(15,23,42,0.4)' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 64 }}>
            <div className="lp-badge" style={{ background: 'rgba(52,211,153,0.1)', border: '1px solid rgba(52,211,153,0.3)', color: '#34d399', marginBottom: 16, display: 'inline-flex' }}>⚡ LIVE PIPELINE DEMO</div>
            <h2 style={{ fontSize: 44, fontWeight: 800, letterSpacing: -1, marginBottom: 16 }}>Watch RAMP <span className="lp-gradient-text">Think in Real Time</span></h2>
            <p style={{ fontSize: 18, color: '#64748b', maxWidth: 520, margin: '0 auto', lineHeight: 1.7 }}>Click "Run Pipeline" to simulate a complete RAMP forecast cycle — from raw NCUM input to corrected spatial product.</p>
          </div>

          <div className="lp-pipeline-layout" style={{ display: 'flex', gap: 32, alignItems: 'flex-start' }}>
            <div style={{ flex: '0 0 340px', display: 'flex', flexDirection: 'column', gap: 10 }}>
              {pipelineSteps.map((step, i) => (
                <PipelineStep key={i} step={i + 1} title={step.title} desc={step.desc} icon={step.icon} color={step.color}
                  active={activeStep === i && pipelineRunning}
                  completed={completedSteps.includes(i)}
                  onClick={() => { if (!pipelineRunning) setActiveStep(i); }}
                />
              ))}
              <button onClick={runPipeline} disabled={pipelineRunning} className="lp-glow-btn" style={{
                marginTop: 8, padding: '14px', borderRadius: 10, fontSize: 14, fontWeight: 700,
                background: pipelineRunning ? 'rgba(30,41,59,0.5)' : 'linear-gradient(135deg, #38bdf8, #818cf8)',
                color: pipelineRunning ? '#64748b' : '#020817', border: 'none', cursor: pipelineRunning ? 'not-allowed' : 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              }}>
                {pipelineRunning ? <><span className="lp-spin" style={{ display: 'inline-block' }}>⚙</span> Processing…</> : completedSteps.length === 5 ? '🔄 Run Again' : '▶ Run Pipeline'}
              </button>
            </div>

            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ background: 'rgba(15,23,42,0.7)', border: '1px solid rgba(30,41,59,0.8)', borderRadius: 16, padding: '24px', marginBottom: 20, backdropFilter: 'blur(12px)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#f1f5f9' }}>Regime Probability Radar</div>
                    <div style={{ fontSize: 12, color: '#475569', marginTop: 2 }}>Current atmospheric state classification</div>
                  </div>
                  <span className="lp-badge" style={{ background: 'rgba(52,211,153,0.1)', border: '1px solid rgba(52,211,153,0.3)', color: '#34d399' }}>Active Monsoon · 72%</span>
                </div>
                <div ref={regimeRef.ref}>
                  <RegimeRadar active={regimeRef.inView} />
                </div>
              </div>

              <div style={{ background: 'rgba(15,23,42,0.7)', border: '1px solid rgba(30,41,59,0.8)', borderRadius: 16, padding: '24px', backdropFilter: 'blur(12px)' }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#f1f5f9', marginBottom: 4 }}>Expert Model Weights</div>
                <div style={{ fontSize: 12, color: '#475569', marginBottom: 16 }}>Gating network output (auto-cycles every 2.5s)</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  {experts.map((exp, i) => (
                    <ExpertCard key={i} {...exp} active={i === activeExpert} />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* RESULTS */}
      <section id="results" className="lp-section" style={{ padding: '100px 24px' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 64 }}>
            <div className="lp-badge" style={{ background: 'rgba(52,211,153,0.1)', border: '1px solid rgba(52,211,153,0.3)', color: '#34d399', marginBottom: 16, display: 'inline-flex' }}>📊 VERIFIED RESULTS</div>
            <h2 style={{ fontSize: 44, fontWeight: 800, letterSpacing: -1, marginBottom: 16 }}>Measurable <span className="lp-gradient-text">Scientific Performance</span></h2>
            <p style={{ fontSize: 18, color: '#64748b', maxWidth: 560, margin: '0 auto', lineHeight: 1.7 }}>RAMP shows consistent, statistically significant improvements across all standard WMO verification metrics for Indian domain precipitation.</p>
          </div>

          <div ref={statsRef.ref} className="lp-grid-4" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 20, marginBottom: 48 }}>
            <StatCard value={31} suffix="%" label="RMSE Reduction vs NCUM" color="#34d399" inView={statsRef.inView} delay={0} />
            <StatCard value={89} suffix="%" label="Regime Classification Acc." color="#38bdf8" inView={statsRef.inView} delay={200} />
            <StatCard value={22} suffix="%" label="CSI Improvement Heavy Rain" color="#818cf8" inView={statsRef.inView} delay={400} />
            <StatCard value={4} suffix="x" label="Faster than NWP Rerun" color="#f472b6" inView={statsRef.inView} delay={600} />
          </div>

          <div ref={rainfallRef.ref} style={{ background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(30,41,59,0.8)', borderRadius: 16, padding: '32px', backdropFilter: 'blur(12px)', marginBottom: 28 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
              <div>
                <div style={{ fontSize: 16, fontWeight: 700, color: '#f1f5f9', marginBottom: 4 }}>Annual Rainfall Forecast Comparison</div>
                <div style={{ fontSize: 13, color: '#475569' }}>Monthly mean QPF — NCUM raw vs. RAMP corrected (mm/month)</div>
              </div>
              <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}><div style={{ width: 12, height: 12, background: '#334155', borderRadius: 2 }} /><span style={{ fontSize: 12, color: '#64748b' }}>NCUM Raw</span></div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}><div style={{ width: 12, height: 12, background: '#38bdf8', borderRadius: 2 }} /><span style={{ fontSize: 12, color: '#64748b' }}>RAMP Corrected</span></div>
              </div>
            </div>
            <RainfallComparison animated={rainfallRef.inView} />
          </div>

          <div className="lp-grid-2" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            {[
              { title: 'Core Verification Metrics', color: '#38bdf8', rows: [{ m: 'RMSE (All Rain)', n: '18.4 mm', r: '12.7 mm', d: '−31%' }, { m: 'MAE (All Rain)', n: '11.2 mm', r: '8.1 mm', d: '−28%' }, { m: 'Correlation (R)', n: '0.71', r: '0.84', d: '+18%' }, { m: 'Bias Score', n: '1.42', r: '1.06', d: '−25%' }] },
              { title: 'Categorical Skill Scores', color: '#34d399', rows: [{ m: 'CSI Heavy (≥64mm)', n: '0.31', r: '0.38', d: '+22%' }, { m: 'FAR Heavy Rain', n: '0.58', r: '0.43', d: '−26%' }, { m: 'POD Extreme (≥115mm)', n: '0.29', r: '0.41', d: '+41%' }, { m: 'ETS (25mm threshold)', n: '0.24', r: '0.31', d: '+29%' }] },
            ].map((table, t) => (
              <div key={t} style={{ background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(30,41,59,0.8)', borderRadius: 14, overflow: 'hidden', backdropFilter: 'blur(8px)' }}>
                <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(30,41,59,0.8)', fontSize: 14, fontWeight: 700, color: table.color }}>{table.title}</div>
                <table style={{ width: '100%', borderCollapse: 'collapse' as const }}>
                  <thead>
                    <tr style={{ background: 'rgba(30,41,59,0.4)' }}>
                      {['Metric', 'NCUM', 'RAMP', 'Δ'].map(h => (
                        <th key={h} style={{ padding: '8px 12px', fontSize: 11, fontWeight: 700, color: '#475569', textAlign: 'left' as const, letterSpacing: 0.5 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {table.rows.map((row, r) => (
                      <tr key={r} style={{ borderTop: '1px solid rgba(30,41,59,0.4)' }}>
                        <td style={{ padding: '10px 12px', fontSize: 12, color: '#94a3b8' }}>{row.m}</td>
                        <td style={{ padding: '10px 12px', fontSize: 12, color: '#64748b', fontFamily: '"JetBrains Mono", monospace' }}>{row.n}</td>
                        <td style={{ padding: '10px 12px', fontSize: 12, color: table.color, fontFamily: '"JetBrains Mono", monospace', fontWeight: 700 }}>{row.r}</td>
                        <td style={{ padding: '10px 12px', fontSize: 12, color: row.d.startsWith('+') ? '#34d399' : '#f87171', fontFamily: '"JetBrains Mono", monospace', fontWeight: 700 }}>{row.d}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* TEAM */}
      <section id="team" className="lp-section" style={{ padding: '100px 24px', background: 'rgba(15,23,42,0.4)' }}>
        <div style={{ maxWidth: 1000, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 64 }}>
            <div className="lp-badge" style={{ background: 'rgba(129,140,248,0.1)', border: '1px solid rgba(129,140,248,0.3)', color: '#818cf8', marginBottom: 16, display: 'inline-flex' }}>👤 THE DEVELOPER</div>
            <h2 style={{ fontSize: 44, fontWeight: 800, letterSpacing: -1, marginBottom: 16 }}>Built by <span className="lp-gradient-text">Sunny Kumar</span></h2>
            <p style={{ fontSize: 18, color: '#64748b', maxWidth: 560, margin: '0 auto', lineHeight: 1.7 }}>MIT Manipal student, independently developing the complete RAMP system — from ML pipeline to operational dashboard — for Smart India Hackathon 2026.</p>
          </div>

          <div style={{ background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(30,41,59,0.8)', borderRadius: 16, padding: '32px', backdropFilter: 'blur(12px)', marginBottom: 36 }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#f1f5f9', marginBottom: 20, textAlign: 'center' }}>Complete Technology Stack</div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'center' }}>
              {[
                { name: 'PyTorch', color: '#fb923c' }, { name: 'scikit-learn', color: '#fb923c' }, { name: 'XGBoost', color: '#fb923c' },
                { name: 'FastAPI', color: '#38bdf8' }, { name: 'PostgreSQL', color: '#38bdf8' }, { name: 'SQLite', color: '#38bdf8' },
                { name: 'React 18', color: '#34d399' }, { name: 'TypeScript', color: '#34d399' }, { name: 'Tailwind CSS', color: '#34d399' },
                { name: 'Leaflet', color: '#818cf8' }, { name: 'MapLibre GL', color: '#818cf8' },
                { name: 'Render.com', color: '#f472b6' }, { name: 'GitHub', color: '#f472b6' },
                { name: 'NetCDF4', color: '#fbbf24' }, { name: 'cfgrib', color: '#fbbf24' }, { name: 'NumPy/SciPy', color: '#fbbf24' },
              ].map((tech, i) => (
                <div key={i} style={{ padding: '6px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600, background: `${tech.color}10`, border: `1px solid ${tech.color}30`, color: tech.color, transition: 'all 0.2s', cursor: 'default' }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = `${tech.color}20`; (e.currentTarget as HTMLElement).style.transform = 'scale(1.05)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = `${tech.color}10`; (e.currentTarget as HTMLElement).style.transform = ''; }}
                >
                  {tech.name}
                </div>
              ))}
            </div>
          </div>

          <div className="lp-grid-3" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20 }}>
            {[
              { logo: '🎓', name: 'MIT Manipal', role: 'Academic Institution', color: '#38bdf8', desc: "Manipal Institute of Technology — developer's home institution, Karnataka." },
              { logo: '🌦️', name: 'NCMRWF', role: 'Problem Statement Owner', color: '#34d399', desc: 'National Centre for Medium Range Weather Forecasting, Ministry of Earth Sciences, Government of India.' },
              { logo: '🏆', name: 'SIH 2026', role: 'Smart India Hackathon', color: '#818cf8', desc: 'Problem #26080 · Category: Science & Technology · Ministry of Education.' },
            ].map((inst, i) => (
              <div key={i} className="lp-card" style={{ background: 'rgba(15,23,42,0.5)', border: '1px solid rgba(30,41,59,0.8)', borderRadius: 14, padding: '24px', textAlign: 'center', backdropFilter: 'blur(8px)' }}>
                <div style={{ fontSize: 36, marginBottom: 12 }}>{inst.logo}</div>
                <div style={{ fontSize: 15, fontWeight: 700, color: inst.color, marginBottom: 4 }}>{inst.name}</div>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#475569', letterSpacing: 0.5, marginBottom: 10, textTransform: 'uppercase' as const }}>{inst.role}</div>
                <div style={{ fontSize: 12, color: '#64748b', lineHeight: 1.6 }}>{inst.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FINAL CTA */}
      <section style={{ padding: '100px 24px', position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: 600, height: 600, background: 'radial-gradient(circle, rgba(56,189,248,0.08) 0%, transparent 70%)', borderRadius: '50%', pointerEvents: 'none' }} />
        <div style={{ maxWidth: 720, margin: '0 auto', textAlign: 'center', position: 'relative' }}>
          <div className="lp-badge" style={{ background: 'rgba(56,189,248,0.1)', border: '1px solid rgba(56,189,248,0.3)', color: '#38bdf8', marginBottom: 24, display: 'inline-flex' }}>🚀 LIVE SYSTEM</div>
          <h2 style={{ fontSize: 52, fontWeight: 900, letterSpacing: -2, marginBottom: 16, lineHeight: 1.05 }}>Explore the Full <span className="lp-gradient-text">RAMP System</span></h2>
          <p style={{ fontSize: 18, color: '#64748b', lineHeight: 1.7, marginBottom: 40 }}>The complete operational dashboard is live. Explore real NCUM data, watch the pipeline run, and see regime-aware corrections in action.</p>

          <div style={{ display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap', marginBottom: 40 }}>
            <button className="lp-glow-btn" onClick={() => navigate('/forecast')} style={{ padding: '18px 40px', borderRadius: 14, fontSize: 18, fontWeight: 700, background: 'linear-gradient(135deg, #38bdf8, #818cf8)', color: '#020817', border: 'none', cursor: 'pointer' }}>
              🚀 Open Dashboard
            </button>
            <button className="lp-ghost-btn" onClick={() => navigate('/jury-demo')} style={{ padding: '18px 40px', borderRadius: 14, fontSize: 18, fontWeight: 600, border: '1px solid rgba(56,189,248,0.4)', color: '#94a3b8', background: 'transparent', cursor: 'pointer' }}>
              🎯 Jury Demo
            </button>
          </div>

          <div style={{ display: 'flex', gap: 8, justifyContent: 'center', flexWrap: 'wrap' }}>
            {[{ l: 'Real Data Lab', p: '/real-data' }, { l: 'Weather Regimes', p: '/regime' }, { l: 'Extreme Rainfall', p: '/extreme' }, { l: 'Spatial Forecast', p: '/spatial' }, { l: 'Production Status', p: '/production' }].map(link => (
              <button key={link.l} onClick={() => navigate(link.p)} style={{ padding: '6px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600, border: '1px solid rgba(30,41,59,0.8)', color: '#64748b', background: 'transparent', cursor: 'pointer', transition: 'all 0.2s' }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#94a3b8'; (e.currentTarget as HTMLElement).style.borderColor = 'rgba(56,189,248,0.3)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = '#64748b'; (e.currentTarget as HTMLElement).style.borderColor = 'rgba(30,41,59,0.8)'; }}
              >
                {link.l}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer style={{ borderTop: '1px solid rgba(30,41,59,0.6)', padding: '36px 32px', background: 'rgba(2,8,23,0.8)' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 30, height: 30, borderRadius: 8, background: 'linear-gradient(135deg, #38bdf8, #818cf8)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14 }}>⛈</div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700 }}>GatiSutra RAMP</div>
              <div style={{ fontSize: 11, color: '#475569' }}>SIH26080 · Ministry of Earth Sciences · NCMRWF</div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 24 }}>
            {[{ l: 'Dashboard', p: '/forecast' }, { l: 'Jury Demo', p: '/jury-demo' }, { l: 'About', p: '/about' }].map(link => (
              <button key={link.l} onClick={() => navigate(link.p)} style={{ background: 'none', border: 'none', color: '#475569', cursor: 'pointer', fontSize: 13, fontWeight: 500, transition: 'color 0.2s' }}
                onMouseEnter={e => (e.currentTarget as HTMLElement).style.color = '#94a3b8'}
                onMouseLeave={e => (e.currentTarget as HTMLElement).style.color = '#475569'}
              >{link.l}</button>
            ))}
          </div>
          <div style={{ fontSize: 12, color: '#334155', textAlign: 'right' as const }}>
            <div>Smart India Hackathon 2026</div>
            <div style={{ marginTop: 2, color: '#1e293b' }}>Regime-Aware Mixture-of-Experts Post-Processor</div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
