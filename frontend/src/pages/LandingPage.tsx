import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  CloudRain,
  AlertTriangle,
  ArrowRight,
  Zap,
  Radio,
  Sparkles,
  Menu,
  X,
  ChevronDown
} from 'lucide-react';
import { AtmosphericHeroCanvas } from './landing/AtmosphericHeroCanvas';
import { TypewriterHeroSubtitle } from './landing/TypewriterHeroHeadline';
import { ProblemStagesInteractive } from './landing/ProblemStagesInteractive';
import { CoreInsightMoEInteractive } from './landing/CoreInsightMoEInteractive';
import { SolutionPipelineInteractive } from './landing/SolutionPipelineInteractive';
import { WatchRampDecideInteractive } from './landing/WatchRampDecideInteractive';
import { TechnicalArchitectureInteractive } from './landing/TechnicalArchitectureInteractive';
import { OperationalWorkflowInteractive } from './landing/OperationalWorkflowInteractive';
import {
  VERIFIED_TECH_STACK,
  BENCHMARK_MODELS,
  FEASIBILITY_PILLARS,
  MATURITY_ROADMAP,
  IMPACT_VERTICALS
} from './landing/landingData';

export const LandingPage: React.FC = () => {
  // Navigation & Scroll State
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Tech Stack Category Filter
  const [selectedTechCategory, setSelectedTechCategory] = useState<string>('All');

  // Handle Scroll effect for global sticky header
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 40);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToSection = (id: string) => {
    setMobileMenuOpen(false);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const techCategories = ['All', 'Frontend', 'Visualization', 'Backend API', 'ML & Numerics', 'Meteorological Data', 'Storage & Infra'];
  const filteredTech = selectedTechCategory === 'All'
    ? VERIFIED_TECH_STACK
    : VERIFIED_TECH_STACK.filter((t) => t.category === selectedTechCategory);

  return (
    <div className="min-h-screen bg-[#070C18] text-slate-100 selection:bg-cyan-500 selection:text-black font-sans antialiased relative overflow-x-hidden">
      
      {/* =========================================================================
          01. GLOBAL STICKY HEADER (RELAXED, CLEAN & PREMIUM)
          ========================================================================= */}
      <header
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 h-20 flex items-center ${
          isScrolled
            ? 'bg-[#070C18]/80 backdrop-blur-md border-b border-cyan-900/30 shadow-lg shadow-black/40'
            : 'bg-transparent border-b border-transparent'
        }`}
      >
        <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-10 flex items-center justify-between">
          {/* Left: Brand & Subtitle (Spaced & Relaxed, No congested badge) */}
          <div className="flex items-center space-x-3.5">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 border border-cyan-400/40 flex-shrink-0">
              <CloudRain className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="text-xl font-bold tracking-tight text-white font-mono block leading-tight">
                GatiSutra RAMP
              </span>
              <p className="text-xs text-slate-400 font-medium tracking-wide hidden sm:block">
                Regime-Aware Weather Forecast Post-Processor
              </p>
            </div>
          </div>

          {/* Center: Curated Primary Navigation (Only the 5 essential sections) */}
          <nav className="hidden lg:flex items-center space-x-8 xl:space-x-10 text-sm font-medium text-slate-300">
            <button
              onClick={() => scrollToSection('problem')}
              className="hover:text-cyan-400 transition-colors py-1 focus:outline-none"
            >
              Problem
            </button>
            <button
              onClick={() => scrollToSection('solution')}
              className="hover:text-cyan-400 transition-colors py-1 focus:outline-none"
            >
              Solution
            </button>
            <button
              onClick={() => scrollToSection('architecture')}
              className="hover:text-cyan-400 transition-colors py-1 focus:outline-none"
            >
              Architecture
            </button>
            <button
              onClick={() => scrollToSection('evidence')}
              className="hover:text-cyan-400 transition-colors py-1 focus:outline-none"
            >
              Evidence
            </button>
            <button
              onClick={() => scrollToSection('impact')}
              className="hover:text-cyan-400 transition-colors py-1 focus:outline-none"
            >
              Impact
            </button>
          </nav>

          {/* Right: Jury Demo & Dashboard CTAs */}
          <div className="hidden sm:flex items-center space-x-3.5">
            <Link
              to="/jury-demo"
              className="text-xs font-semibold px-4 py-2.5 rounded-xl bg-slate-900/80 hover:bg-slate-800 text-slate-200 border border-slate-700/80 backdrop-blur-md transition-all flex items-center space-x-2"
            >
              <Radio className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
              <span>Jury Demo</span>
            </Link>
            <Link
              to="/forecast"
              className="text-xs font-bold px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 shadow-md shadow-cyan-500/25 transition-all flex items-center space-x-2 transform hover:-translate-y-0.5"
            >
              <span>Dashboard</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {/* Mobile Right: Dashboard Icon + Hamburger */}
          <div className="flex sm:hidden items-center space-x-2">
            <Link
              to="/forecast"
              className="text-xs font-bold px-3 py-1.5 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 flex items-center space-x-1"
            >
              <span>Dashboard</span>
              <ArrowRight className="w-3 h-3" />
            </Link>
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg bg-slate-800/90 text-slate-300 hover:text-white border border-slate-700"
              aria-label="Toggle Navigation Menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation Glass Drawer */}
        {mobileMenuOpen && (
          <div className="lg:hidden absolute top-20 left-0 right-0 bg-[#070C18]/95 backdrop-blur-2xl border-b border-cyan-900/30 px-6 py-6 space-y-4 shadow-2xl">
            <div className="flex flex-col space-y-3 text-sm font-medium">
              <button
                onClick={() => scrollToSection('problem')}
                className="text-left text-slate-300 hover:text-cyan-400 py-1.5"
              >
                Problem
              </button>
              <button
                onClick={() => scrollToSection('solution')}
                className="text-left text-slate-300 hover:text-cyan-400 py-1.5"
              >
                Solution
              </button>
              <button
                onClick={() => scrollToSection('architecture')}
                className="text-left text-slate-300 hover:text-cyan-400 py-1.5"
              >
                Architecture
              </button>
              <button
                onClick={() => scrollToSection('evidence')}
                className="text-left text-slate-300 hover:text-cyan-400 py-1.5"
              >
                Evidence
              </button>
              <button
                onClick={() => scrollToSection('impact')}
                className="text-left text-slate-300 hover:text-cyan-400 py-1.5"
              >
                Impact
              </button>
            </div>
            <div className="pt-4 border-t border-slate-800/80 flex flex-col gap-2">
              <Link
                to="/forecast"
                className="w-full text-center py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 font-bold text-sm shadow-md"
              >
                Open Operational Dashboard →
              </Link>
              <Link
                to="/jury-demo"
                className="w-full text-center py-2.5 rounded-xl bg-slate-900 text-slate-200 text-sm font-semibold border border-slate-700/80"
              >
                Launch Jury Demonstration
              </Link>
            </div>
          </div>
        )}
      </header>

      {/* =========================================================================
          02. HERO: CINEMATIC ATMOSPHERIC INTELLIGENCE
          ========================================================================= */}
      <section className="relative min-h-screen flex items-center justify-center pt-28 pb-16 overflow-hidden">
        {/* Layer 1: Three.js Atmospheric Forecast Field WebGL Canvas */}
        <AtmosphericHeroCanvas />

        {/* Layer 2: Atmospheric Vignettes & Dark Readability Gradients */}
        <div className="absolute inset-0 bg-gradient-to-b from-[#070C18]/40 via-[#070C18]/70 to-[#070C18] pointer-events-none z-10" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-transparent via-[#070C18]/50 to-[#070C18]/90 pointer-events-none z-10" />
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[800px] h-[450px] bg-cyan-600/10 rounded-full blur-[160px] pointer-events-none z-0" />

        {/* Layer 3: Foreground Content Hierarchy */}
        <div className="relative z-20 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          {/* Institutional Identification Badge */}
          <div className="inline-flex items-center space-x-2.5 px-4 py-1.5 rounded-full bg-slate-900/80 border border-cyan-800/50 backdrop-blur-md mb-6 shadow-inner">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            <span className="text-xs font-mono font-medium text-cyan-300 tracking-wide">
              Ministry of Earth Sciences • NCMRWF NCUM Post-Processing (0.17° Resolution)
            </span>
          </div>

          {/* Main Hero Headline (Loading Text Animation) */}
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight leading-[1.1] mb-6 select-none">
            <span className="block animate-text-loading">
              Forecast Rainfall.
            </span>
            <span className="block animate-gradient-loading">
              Understand the Atmosphere.
            </span>
            <span className="block animate-text-loading">
              Act Before the Extremes.
            </span>
          </h1>

          {/* Subtitle & Core Thesis (Yellow Color with Typewriting Effect) */}
          <div className="max-w-3xl mx-auto mb-4 min-h-[3.2rem] flex items-center justify-center">
            <p className="text-lg sm:text-xl leading-relaxed">
              <TypewriterHeroSubtitle
                text="Regime-Aware Mixture-of-Experts Post-Processor for next-generation tropical precipitation forecasting."
                className="text-yellow-400 text-yellow-glow font-medium"
                cursorClassName="bg-yellow-400 shadow-[0_0_10px_#facc15]"
              />
            </p>
          </div>

          <p className="text-sm sm:text-base text-slate-400 max-w-2xl mx-auto mb-8 font-light leading-relaxed">
            Raw numerical weather prediction delivers the raw physics grid. RAMP diagnoses the instantaneous atmospheric regime — and probabilistically routes the forecast to specialized correction experts.
          </p>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center justify-center gap-4 mb-12">
            <Link
              to="/forecast"
              className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-sm tracking-wide shadow-lg shadow-cyan-500/25 transition-all flex items-center space-x-2 transform hover:-translate-y-0.5"
            >
              <span>Open Live Dashboard</span>
              <ArrowRight className="w-4 h-4" />
            </Link>

            <Link
              to="/jury-demo"
              className="px-6 py-3.5 rounded-xl bg-slate-900/80 hover:bg-slate-800 text-slate-200 font-semibold text-sm border border-slate-700/80 backdrop-blur-md transition-all flex items-center space-x-2"
            >
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <span>Explore Jury Demo</span>
            </Link>

            <button
              onClick={() => scrollToSection('problem')}
              className="px-5 py-3.5 rounded-xl bg-transparent hover:bg-slate-800/40 text-slate-400 hover:text-slate-200 font-medium text-sm transition-all flex items-center space-x-1.5"
            >
              <span>See How It Works</span>
              <ChevronDown className="w-4 h-4 animate-bounce" />
            </button>
          </div>

          {/* Linear High-Level Transformation Pipeline */}
          <div className="max-w-4xl mx-auto p-4 rounded-2xl bg-slate-900/70 border border-slate-800/90 backdrop-blur-md shadow-2xl">
            <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-3 text-center flex items-center justify-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
              <span>Autonomous Atmospheric Post-Processing Pipeline</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-left">
              <div className="p-3 rounded-xl bg-[#091122]/90 border border-cyan-900/40 relative">
                <div className="text-[10px] font-mono text-cyan-400 font-bold">01 • INPUT</div>
                <div className="text-xs font-bold text-white mt-0.5">Raw NCUM NWP</div>
                <div className="text-[11px] text-slate-400 mt-1">GRIB2/NetCDF 0.17°</div>
              </div>
              <div className="p-3 rounded-xl bg-[#091122]/90 border border-cyan-900/40 relative">
                <div className="text-[10px] font-mono text-cyan-400 font-bold">02 • DIAGNOSIS</div>
                <div className="text-xs font-bold text-white mt-0.5">7-Regime Gating</div>
                <div className="text-[11px] text-slate-400 mt-1">Calibrated Probabilities</div>
              </div>
              <div className="p-3 rounded-xl bg-[#091122]/90 border border-cyan-900/40 relative">
                <div className="text-[10px] font-mono text-cyan-400 font-bold">03 • CORRECTION</div>
                <div className="text-xs font-bold text-white mt-0.5">Specialized MoE</div>
                <div className="text-[11px] text-slate-400 mt-1">Soft Blended Experts</div>
              </div>
              <div className="p-3 rounded-xl bg-[#091122]/90 border border-cyan-900/40 relative">
                <div className="text-[10px] font-mono text-cyan-400 font-bold">04 • PRODUCT</div>
                <div className="text-xs font-bold text-white mt-0.5">Calibrated Districts</div>
                <div className="text-[11px] text-slate-400 mt-1">788 District Envelopes</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          03. THE PROBLEM: FORECASTING RAINFALL IS NOT ONE PROBLEM
          ========================================================================= */}
      <section id="problem" className="py-24 relative border-t border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mb-16">
            <div className="inline-flex items-center space-x-2 text-xs font-mono uppercase tracking-widest text-cyan-400 mb-3">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
              <span>Atmospheric Challenge</span>
            </div>
            <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight leading-tight">
              Forecasting Rainfall Is Not One Problem.
            </h2>
            <p className="text-base sm:text-lg text-slate-400 mt-4 leading-relaxed">
              Numerical Weather Prediction models solve hydrostatic atmospheric physics on discrete grids. But rainfall over the Indian subcontinent is driven by radically disparate physical mechanisms that defy a single blanket correction.
            </p>
          </div>

          {/* Interactive Dynamic 5-Stage Scientific Story Pipeline */}
          <ProblemStagesInteractive />
        </div>
      </section>

      {/* =========================================================================
          04 & 05. THE CORE INSIGHT: ONE CORRECTION DOES NOT FIT EVERY ATMOSPHERE
          ========================================================================= */}
      <section className="py-24 relative bg-gradient-to-b from-[#070C18] via-[#091122] to-[#070C18] border-t border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-400">The Core Insight</span>
            <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mt-2">
              "One correction does not fit every atmosphere."
            </h2>
            <p className="text-slate-400 mt-4 text-base sm:text-lg">
              Applying a single global machine learning model or mean offset across all seasons fails because the atmosphere operates in distinct regimes.
            </p>
          </div>

          {/* Interactive Regime-Aware Mixture-of-Experts vs Traditional Comparison */}
          <CoreInsightMoEInteractive />
        </div>
      </section>

      {/* =========================================================================
          06. THE RAMP SOLUTION: MEET GATISUTRA RAMP (7-STAGE PIPELINE)
          ========================================================================= */}
      <section id="solution" className="py-24 relative border-t border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-400">The Solution</span>
            <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mt-2">
              Meet GatiSutra RAMP
            </h2>
            <p className="text-slate-400 mt-4 text-base sm:text-lg">
              Regime-Aware Mixture-of-Experts Post-Processor. An end-to-end meteorological AI pipeline designed for NCMRWF operational numerical weather forecasts.
            </p>
          </div>

          {/* Interactive Animated 7-Stage Pipeline Visual */}
          <SolutionPipelineInteractive />
        </div>
      </section>

      {/* =========================================================================
          07. THE "MAGIC MOMENT": WATCH RAMP DECIDE (INTERACTIVE SIMULATION)
          ========================================================================= */}
      <section id="decision" className="py-24 relative bg-gradient-to-b from-[#070C18] via-[#081326] to-[#070C18] border-t border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mb-12">
            <div className="inline-flex items-center space-x-2 text-xs font-mono uppercase tracking-widest text-cyan-400 mb-3">
              <Zap className="w-4 h-4 text-cyan-400" />
              <span>Interactive Decision Engine</span>
            </div>
            <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
              Watch RAMP Decide.
            </h2>
            <p className="text-base sm:text-lg text-slate-300 mt-4 leading-relaxed">
              Select an atmospheric weather regime below to see how RAMP dynamically updates its soft gating probability distribution, activates specialized correction experts, and quantifies extreme rainfall risk.
            </p>
          </div>

          {/* Interactive Animated Decision Engine Display */}
          <WatchRampDecideInteractive />
        </div>
      </section>

      {/* =========================================================================
          08. TECHNICAL ARCHITECTURE EXPLORER
          ========================================================================= */}
      <section id="architecture" className="py-24 relative border-t border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mb-14">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-400">Engineering Rigor</span>
            <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mt-2">
              Technical Architecture
            </h2>
            <p className="text-slate-400 mt-4 text-base sm:text-lg">
              Explore the inputs, outputs, mathematical logic, and scientific objectives of each component in the operational pipeline.
            </p>
          </div>

          {/* Interactive Animated Architecture Component */}
          <TechnicalArchitectureInteractive />
        </div>
      </section>

      {/* =========================================================================
          09. END-TO-END WORKFLOW (10-STEP OPERATIONAL TIMELINE)
          ========================================================================= */}
      <section id="workflow" className="py-24 relative bg-gradient-to-b from-[#070C18] via-[#091122] to-[#070C18] border-t border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mb-16">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-400">Execution Lifecycle</span>
            <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mt-2">
              End-to-End Operational Workflow
            </h2>
            <p className="text-slate-400 mt-4 text-base sm:text-lg">
              From raw GRIB2 forecast ingestion to district disaster advisories, each cycle executes autonomously in under 400 milliseconds.
            </p>
          </div>

          {/* Interactive Animated Operational Stepper */}
          <OperationalWorkflowInteractive />
        </div>
      </section>

      {/* =========================================================================
          10. REAL TECHNOLOGY STACK
          ========================================================================= */}
      <section id="technology" className="py-24 relative border-t border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mb-12">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-400">Audited Dependencies</span>
            <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mt-2">
              Technology Stack
            </h2>
            <p className="text-slate-400 mt-4 text-base sm:text-lg">
              Strictly verified technologies actively used across frontend, backend, numerical modeling, and production deployment.
            </p>
          </div>

          {/* Category Filter Pills */}
          <div className="flex flex-wrap gap-2 mb-8">
            {techCategories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedTechCategory(cat)}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-mono transition-all ${
                  selectedTechCategory === cat
                    ? 'bg-cyan-500 text-slate-950 font-bold shadow-md'
                    : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredTech.map((tech) => (
              <div
                key={tech.name}
                className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-cyan-800/60 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-900/50">
                      {tech.category}
                    </span>
                    <span className="text-[10px] font-mono text-slate-500">{tech.whereInRepo}</span>
                  </div>
                  <h3 className="text-base font-bold text-white mb-2">{tech.name}</h3>
                  <p className="text-xs text-slate-300 leading-relaxed mb-4">
                    <strong className="text-slate-200">Role:</strong> {tech.role}
                  </p>
                </div>
                <div className="pt-3 border-t border-slate-800 text-xs text-slate-400 leading-relaxed">
                  <strong className="text-cyan-400">Why:</strong> {tech.why}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* =========================================================================
          11. BENCHMARK & EVIDENCE: SCIENTIFIC INTEGRITY & VERIFICATION
          ========================================================================= */}
      <section id="evidence" className="py-24 relative bg-gradient-to-b from-[#070C18] via-[#091122] to-[#070C18] border-t border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mb-12">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-400">Scientific Integrity</span>
            <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mt-2">
              Evidence. Measurement. Verification.
            </h2>
            <p className="text-slate-400 mt-4 text-base sm:text-lg">
              Verification scores must be grounded in defensible data. Below is the objective benchmark comparison across baseline models on the controlled test partition.
            </p>
          </div>

          {/* Transparent Integrity Notice */}
          <div className="p-4 rounded-2xl bg-amber-950/40 border border-amber-800/50 mb-8 flex items-start space-x-3 text-amber-200 text-xs">
            <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="leading-relaxed">
              <strong className="font-bold uppercase tracking-wider text-amber-300">Synthetic Demonstration Mode Notice:</strong>
              <br />
              Metrics displayed below reflect test-fixture evaluation under strictly controlled demonstration data (<code className="text-amber-300">ramp_dataset_real_v1.0.0</code>).
              Because authoritative multi-year NCMRWF NCUM and IMD gridded observation archives are pending physical operational mounting, no fabricated real-world claims are made.
            </div>
          </div>

          {/* Benchmark Table */}
          <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-[#081224] shadow-2xl mb-8">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/80 text-slate-300 font-mono text-[11px]">
                  <th className="py-3.5 px-4">Model / Approach</th>
                  <th className="py-3.5 px-4">Description</th>
                  <th className="py-3.5 px-4 text-right">RMSE (mm) ↓</th>
                  <th className="py-3.5 px-4 text-right">CSI (&gt;64.5mm) ↑</th>
                  <th className="py-3.5 px-4 text-right">POD ↑</th>
                  <th className="py-3.5 px-4 text-right">FAR ↓</th>
                  <th className="py-3.5 px-4 text-right">Brier Score ↓</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {BENCHMARK_MODELS.map((model) => (
                  <tr
                    key={model.modelKey}
                    className={`hover:bg-slate-800/40 transition-colors ${
                      model.modelKey === 'ramp' ? 'bg-cyan-950/30 text-cyan-200 font-semibold' : 'text-slate-300'
                    }`}
                  >
                    <td className="py-3.5 px-4 font-bold text-white flex items-center space-x-2">
                      {model.modelKey === 'ramp' && <Sparkles className="w-3.5 h-3.5 text-cyan-400" />}
                      <span>{model.modelName}</span>
                    </td>
                    <td className="py-3.5 px-4 font-sans text-slate-400 text-[11px]">{model.description}</td>
                    <td className="py-3.5 px-4 text-right">{model.rmse.toFixed(2)}</td>
                    <td className="py-3.5 px-4 text-right text-emerald-400">{model.csiHeavy.toFixed(2)}</td>
                    <td className="py-3.5 px-4 text-right">{model.pod.toFixed(2)}</td>
                    <td className="py-3.5 px-4 text-right text-rose-400">{model.far.toFixed(2)}</td>
                    <td className="py-3.5 px-4 text-right">{model.brierScore.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Measured Timing Performance Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 text-center">
              <div className="text-[10px] font-mono text-slate-400 uppercase">QC Evaluation</div>
              <div className="text-xl font-bold text-white font-mono mt-1">0.78 ms</div>
              <div className="text-[10px] text-slate-500 mt-1">70,692 cells checked</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 text-center">
              <div className="text-[10px] font-mono text-slate-400 uppercase">Regime Posterior</div>
              <div className="text-xl font-bold text-white font-mono mt-1">0.53 ms</div>
              <div className="text-[10px] text-slate-500 mt-1">7 classes calibrated</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 text-center">
              <div className="text-[10px] font-mono text-slate-400 uppercase">MoE Inference</div>
              <div className="text-xl font-bold text-white font-mono mt-1">328.6 ms</div>
              <div className="text-[10px] text-slate-500 mt-1">482 operational grid points</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 text-center">
              <div className="text-[10px] font-mono text-cyan-400 uppercase font-bold">Total Latency</div>
              <div className="text-xl font-bold text-cyan-400 font-mono mt-1">390.2 ms</div>
              <div className="text-[10px] text-slate-500 mt-1">End-to-end execution</div>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          12. WHAT MAKES GATISUTRA RAMP DIFFERENT
          ========================================================================= */}
      <section className="py-24 relative border-t border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-400">Comparative Value</span>
            <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mt-2">
              "Not just better correction. Better context."
            </h2>
            <p className="text-slate-400 mt-4 text-base sm:text-lg">
              How RAMP fundamentally transforms numerical post-processing compared to traditional statistical methods.
            </p>
          </div>

          <div className="max-w-4xl mx-auto rounded-3xl border border-slate-800 bg-[#081224] overflow-hidden shadow-2xl">
            <div className="grid grid-cols-3 p-4 bg-slate-900 border-b border-slate-800 font-mono text-xs text-slate-400 uppercase">
              <div>Capability</div>
              <div>Traditional Methods</div>
              <div className="text-cyan-400 font-bold">GatiSutra RAMP</div>
            </div>
            <div className="divide-y divide-slate-800/60 text-xs">
              <div className="grid grid-cols-3 p-4 items-center">
                <span className="font-bold text-white">Atmospheric Awareness</span>
                <span className="text-slate-400">Blind to changing regimes</span>
                <span className="text-cyan-300 font-semibold">7 Canonical Weather Regimes</span>
              </div>
              <div className="grid grid-cols-3 p-4 items-center">
                <span className="font-bold text-white">Model Architecture</span>
                <span className="text-slate-400">Monolithic model or static offset</span>
                <span className="text-cyan-300 font-semibold">Mixture-of-Experts with Gating Network</span>
              </div>
              <div className="grid grid-cols-3 p-4 items-center">
                <span className="font-bold text-white">Boundary Transitions</span>
                <span className="text-slate-400">Discontinuous hard classifications</span>
                <span className="text-cyan-300 font-semibold">Continuous Analytical Soft Blending</span>
              </div>
              <div className="grid grid-cols-3 p-4 items-center">
                <span className="font-bold text-white">Extreme Tail Events</span>
                <span className="text-slate-400">Severe underprediction / smoothing</span>
                <span className="text-cyan-300 font-semibold">Calibrated Logistic Heads at 64.5/115.6/204.5 mm</span>
              </div>
              <div className="grid grid-cols-3 p-4 items-center">
                <span className="font-bold text-white">Spatial Decision Support</span>
                <span className="text-slate-400">Raw continuous grid floats</span>
                <span className="text-cyan-300 font-semibold">788 District Polygons with Max-Pooling</span>
              </div>
              <div className="grid grid-cols-3 p-4 items-center">
                <span className="font-bold text-white">Operational Observability</span>
                <span className="text-slate-400">Unmonitored offline scripts</span>
                <span className="text-cyan-300 font-semibold">PostgreSQL Telemetry, SHA-256 Model Cards & Drift</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          13. FEASIBILITY & OPERATIONAL READINESS
          ========================================================================= */}
      <section className="py-24 relative bg-gradient-to-b from-[#070C18] via-[#091122] to-[#070C18] border-t border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mb-14">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-400">Implementation Honesty</span>
            <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mt-2">
              Can This Actually Work?
            </h2>
            <p className="text-slate-400 mt-4 text-base sm:text-lg">
              Transparent readiness breakdown across scientific, technical, data, and operational dimensions.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {FEASIBILITY_PILLARS.map((pillar) => (
              <div
                key={pillar.pillar}
                className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-lg font-bold text-white">{pillar.pillar}</h3>
                    <span
                      className={`text-[10px] font-mono px-2.5 py-0.5 rounded-full font-bold uppercase ${
                        pillar.status === 'VERIFIED'
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                          : pillar.status === 'READY'
                          ? 'bg-cyan-950 text-cyan-400 border border-cyan-800'
                          : 'bg-amber-950 text-amber-400 border border-amber-800'
                      }`}
                    >
                      {pillar.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed mb-4">
                    <strong className="text-cyan-400">Current Capability:</strong> {pillar.currentCapability}
                  </p>
                  <p className="text-xs text-slate-400 leading-relaxed mb-4">
                    <strong className="text-slate-300">Operational Requirement:</strong> {pillar.requirement}
                  </p>
                </div>
                <div className="pt-3 border-t border-slate-800 text-xs text-amber-300/90 leading-relaxed font-mono">
                  Remaining Dependency: {pillar.remainingDependency}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* =========================================================================
          14. VIABILITY & MATURITY ROADMAP
          ========================================================================= */}
      <section className="py-24 relative border-t border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mb-14">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-400">Evolution Path</span>
            <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mt-2">
              Maturity & Deployment Roadmap
            </h2>
            <p className="text-slate-400 mt-4 text-base sm:text-lg">
              A 6-phase trajectory guiding RAMP from architectural prototype to national operational integration.
            </p>
          </div>

          <div className="space-y-4">
            {MATURITY_ROADMAP.map((phase) => (
              <div
                key={phase.phase}
                className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-cyan-800/60 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-mono font-bold text-cyan-400">{phase.phase}</span>
                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded-full uppercase ${
                        phase.currentStatus === 'COMPLETE'
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                          : phase.currentStatus === 'ACTIVE'
                          ? 'bg-cyan-950 text-cyan-400 border border-cyan-800 animate-pulse'
                          : 'bg-slate-800 text-slate-400 border border-slate-700'
                      }`}
                    >
                      {phase.currentStatus}
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-white">{phase.title}</h3>
                  <div className="flex flex-wrap gap-2 pt-1">
                    {phase.deliverables.map((del, idx) => (
                      <span key={idx} className="text-[11px] font-mono text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                        {del}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="md:text-right font-mono text-xs text-slate-400 md:max-w-xs">
                  <span className="text-cyan-400 font-bold block mb-0.5">Success Gate:</span>
                  <span>{phase.successCondition}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* =========================================================================
          15. REAL-WORLD SCENARIO: SYNOPTIC CASE STUDY
          ========================================================================= */}
      <section className="py-24 relative bg-gradient-to-b from-[#070C18] via-[#091122] to-[#070C18] border-t border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mb-12">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-400">Operational Walkthrough</span>
            <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mt-2">
              Scenario: Monsoon Low-Pressure Over Central India
            </h2>
            <p className="text-slate-400 mt-4 text-base sm:text-lg">
              Trace how RAMP intervenes during a critical synoptic storm system to avert a catastrophic forecast underprediction.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3">
              <span className="text-xs font-mono text-cyan-400 font-bold">01 • SYNOPTIC FORMATION</span>
              <h3 className="text-base font-bold text-white">Bay of Bengal Depression</h3>
              <p className="text-xs text-slate-300 leading-relaxed">
                A cyclonic vortex forms over the north Bay of Bengal and tracks west-northwest into Odisha and Chhattisgarh with central pressure dropping by 3 hPa.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3">
              <span className="text-xs font-mono text-amber-400 font-bold">02 • RAW NWP DISTORTION</span>
              <h3 className="text-base font-bold text-white">Displaced Rainfall Core</h3>
              <p className="text-xs text-slate-300 leading-relaxed">
                Raw NCUM predicts peak 24h rainfall of 42 mm displaced 70 km south of the vortex track, underestimating local convection due to parameterized grid limits.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-slate-900/80 border border-cyan-800/60 bg-gradient-to-b from-[#0B172E] to-slate-950 space-y-3">
              <span className="text-xs font-mono text-emerald-400 font-bold">03 • RAMP INTERVENTION</span>
              <h3 className="text-base font-bold text-white">Low-Pressure Expert Activation</h3>
              <p className="text-xs text-slate-200 leading-relaxed">
                Regime classifier flags Low/Depression (79%). Specialized expert boosts vortex core intensity to 118 mm/24h and issues an Orange Alert across 4 districts.
              </p>
            </div>
          </div>

          <div className="mt-6 text-center text-xs font-mono text-slate-500">
            Illustrative synoptic scenario demonstrating RAMP decision dynamics under monsoon disturbance events.
          </div>
        </div>
      </section>

      {/* =========================================================================
          16. IMPACT VERTICALS
          ========================================================================= */}
      <section id="impact" className="py-24 relative border-t border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mb-14">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-400">Societal Relevance</span>
            <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mt-2">
              Designed for High-Consequence Decisions
            </h2>
            <p className="text-slate-400 mt-4 text-base sm:text-lg">
              Precipitation forecasting directly impacts life-safety, food security, and urban infrastructure across India.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {IMPACT_VERTICALS.map((imp) => (
              <div
                key={imp.domain}
                className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 flex flex-col justify-between hover:border-cyan-800/60 transition-all"
              >
                <div>
                  <h3 className="text-lg font-bold text-white mb-2">{imp.domain}</h3>
                  <p className="text-xs font-semibold text-cyan-400 mb-3">{imp.focus}</p>
                  <p className="text-xs text-slate-300 leading-relaxed mb-4">
                    {imp.application}
                  </p>
                </div>
                <div className="pt-3 border-t border-slate-800 text-[11px] font-mono text-slate-400">
                  Target Metric: {imp.metricFocus}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* =========================================================================
          17. LIVE SYSTEM LAUNCHPAD & CTA
          ========================================================================= */}
      <section className="py-28 relative bg-gradient-to-b from-[#070C18] via-[#09152B] to-[#070C18] border-t border-slate-800/80 overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-cyan-500/10 rounded-full blur-[120px] pointer-events-none" />
        
        <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <span className="text-xs font-mono uppercase tracking-widest text-cyan-400">Operational Verification Desk</span>
          <h2 className="text-4xl sm:text-6xl font-extrabold text-white tracking-tight mt-3 mb-6">
            From Forecast Complexity to Actionable Intelligence.
          </h2>
          <p className="text-base sm:text-lg text-slate-300 max-w-2xl mx-auto mb-10 leading-relaxed">
            Experience the live operational modules, inspect real data lineage, or walk through the interactive jury demonstration.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4 mb-14">
            <Link
              to="/forecast"
              className="px-8 py-4 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-sm shadow-xl shadow-cyan-500/25 transition-all flex items-center space-x-2 transform hover:-translate-y-0.5"
            >
              <span>Open Live Forecast Desk</span>
              <ArrowRight className="w-4 h-4" />
            </Link>

            <Link
              to="/jury-demo"
              className="px-8 py-4 rounded-xl bg-slate-900/90 hover:bg-slate-800 text-slate-200 font-semibold text-sm border border-slate-700/80 backdrop-blur-md transition-all flex items-center space-x-2"
            >
              <Radio className="w-4 h-4 text-cyan-400 animate-pulse" />
              <span>Launch Jury Demonstration</span>
            </Link>
          </div>

          {/* Direct Module Links */}
          <div className="max-w-3xl mx-auto grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs font-mono">
            <Link to="/regime" className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800 text-slate-300 hover:text-cyan-400 hover:border-cyan-800/60 transition-all">
              Weather Regimes →
            </Link>
            <Link to="/spatial" className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800 text-slate-300 hover:text-cyan-400 hover:border-cyan-800/60 transition-all">
              Spatial Forecast →
            </Link>
            <Link to="/extreme" className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800 text-slate-300 hover:text-cyan-400 hover:border-cyan-800/60 transition-all">
              Extreme Rainfall →
            </Link>
            <Link to="/real-data" className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800 text-slate-300 hover:text-cyan-400 hover:border-cyan-800/60 transition-all">
              Real Data Lab →
            </Link>
            <Link to="/production" className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800 text-slate-300 hover:text-cyan-400 hover:border-cyan-800/60 transition-all col-span-2 sm:col-span-1">
              Production Status →
            </Link>
          </div>
        </div>
      </section>

      {/* =========================================================================
          18. FINAL SCIENTIFIC FOOTER
          ========================================================================= */}
      <footer className="border-t border-slate-800/80 bg-[#050912] py-12 text-slate-400 text-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6 pb-8 border-b border-slate-800/80">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white">
                <CloudRain className="w-4 h-4" />
              </div>
              <div>
                <div className="text-sm font-bold text-white font-mono">GatiSutra RAMP</div>
                <div className="text-[11px] text-slate-400">
                  Ministry of Earth Sciences (MoES) • NCMRWF
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-6 text-slate-400">
              <Link to="/forecast" className="hover:text-cyan-400 transition-colors">Operational Dashboard</Link>
              <Link to="/jury-demo" className="hover:text-cyan-400 transition-colors">Jury Demo</Link>
              <Link to="/regime" className="hover:text-cyan-400 transition-colors">Regimes</Link>
              <Link to="/spatial" className="hover:text-cyan-400 transition-colors">Spatial Desk</Link>
              <Link to="/about" className="hover:text-cyan-400 transition-colors">About System</Link>
            </div>

            <div>
              <button
                onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                className="text-xs font-mono text-cyan-400 hover:text-cyan-300 flex items-center space-x-1"
              >
                <span>Back to top</span>
                <span>↑</span>
              </button>
            </div>
          </div>

          <div className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-slate-500 text-[11px]">
            <div>
              Made by <span className="text-slate-300 font-semibold">Team GatiSutra</span>
            </div>
            <div>
              Regime-Aware Mixture-of-Experts Post-Processor (RAMP) • Operational Meteorological Intelligence
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
