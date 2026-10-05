# GatiSutra RAMP — Landing Page Redesign & Engineering Implementation Plan
**Document Version:** 2.0.0  
**Target:** Deployed Production Landing Page (`/`) at `https://gatisura-ramp.onrender.com/`  
**Identity:** GatiSutra RAMP (Regime-Aware Mixture-of-Experts Post-Processor)  
**Institutions:** Ministry of Earth Sciences (MoES) • National Centre for Medium Range Weather Forecasting (NCMRWF)  
**Authoring Body:** Team GatiSutra  

---

## 1. Current Landing-Page Audit
The previous landing page attempt (introduced in commit `4046067`) fell short of the high bar demanded for a national-level scientific platform and jury presentation:
- **Card-Heavy Clutter:** Displayed isolated boxes and static tiles rather than a unified cinematic atmospheric story.
- **Unverified & Fabricated Metrics:** Displayed ungrounded numbers (e.g., "31% bias reduction", "89% classification accuracy", "22% CSI improvement", "4x faster", "45% overforecast correction", "1.4B people", "28 states", "4500+ districts") without rigorous dataset provenance, contrary to the repository's strict Scientific Integrity Statement.
- **Regime Count Inaccuracy:** Displayed "6 Atmospheric Regimes" instead of the authoritative **7 canonical monsoon regimes** defined in `REGIME_MODEL_CARD.md` and `MODEL_CARD.md`.
- **Unsubstantiated Marketing Claims:** Used marketing hyperbole such as "for the first time in India" and generic SaaS copy.
- **Unwanted Attribution & Labels:** Displayed "Built by Sunny Kumar", "MIT Manipal", and repeated "SIH26080" identifiers across headers, badges, and footers.
- **Disconnected Operational Context:** Failed to seamlessly bridge the narrative to the live operational modules (`/forecast`, `/jury-demo`, `/regime`, `/real-data`, `/spatial`, `/extreme`, `/production`).

---

## 2. Current Routing Audit
Inspection of `frontend/src/App.tsx` and operational pages demonstrates the following active routes that **must be strictly preserved**:

| Route Path | Page Component | Shell Wrapped? | Purpose |
| :--- | :--- | :--- | :--- |
| `/` | `LandingPage` *(NEW)* | **Standalone (No Shell)** | Full-viewport cinematic scientific narrative |
| `/forecast` | `OperationalForecastPage` | Yes | Operational forecast desk & interactive maps |
| `/forecast/cases` | `RealDataCasesPage` | Yes | Real-data case studies |
| `/forecast/verification` | `ForecastVerificationPage` | Yes | Model verification & contingency scores |
| `/forecast/verification/history` | `VerificationHistoryPage`| Yes | Verification historical logs |
| `/jury-demo`, `/jury/phase18` | `JuryDemoPage` | Yes | Dedicated jury walkthrough demo |
| `/real-data` | `RealDataLabPage` | Yes | Real-data inspection & lineage |
| `/regime` | `WeatherRegimesPage` | Yes | 7-regime classifier analytics |
| `/baseline` | `BaselineBenchmarkingPage` | Yes | Raw NWP, Mean Bias, QMap, Global ML, RAMP benchmarks |
| `/extreme` | `ExtremeRainfallPage` | Yes | IMD threshold extreme precipitation probability heads |
| `/spatial` | `SpatialForecastPage` | Yes | District and sub-grid spatial post-processing |
| `/data`, `/data/ingestion` | `DataFeedsPage`, `DataIngestionPage` | Yes | Raw NCUM/NEPS/IMD ingestion pipelines |
| `/operations`, `/operations/cycles` | `OperationsPage`, `OperationalCyclesPage` | Yes | Production cycle orchestration & telemetry |
| `/production`, `/acceptance` | `ProductionStatusPage`, `AcceptancePage` | Yes | Production readiness & Phase acceptance gates |

**Routing Rule:** The root route `/` will render the new `LandingPage` as an unencumbered, standalone single-page experience. All operational navigation elements ("Dashboard →", "Jury Demo", "Explore Modules") link directly to their corresponding operational routes.

---

## 3. Current Frontend Architecture
- **Framework & Language:** React 18.3.1 with TypeScript 5.4.5, compiled via Vite 5.2.11.
- **Styling:** Tailwind CSS 3.4.3 with custom color tokens, dark glassmorphism, and responsive utilities.
- **Icons:** `lucide-react` (0.378.0).
- **Geospatial & Visualization:** Leaflet 1.9.4, React-Leaflet 4.2.1, MapLibre GL 6.11.2, and newly integrated `three` (Three.js WebGL atmospheric visualization).
- **Build Pipeline:** `tsc && vite build` emitting zero warnings or type errors.

---

## 4. Existing Components That Can Be Reused
- Existing color palette and theme tokens (`bg-[#0B1120]`, `bg-[#0F172A]`, cyan-to-blue accents, emerald validated tags, amber/rose extreme badges).
- Geospatial coordinates and India boundary GeoJSON references from `frontend/src/` data utilities.
- Backend API contract types (`OperationalCycleResponse`, `RegimeProbabilities`, `VerificationReport`).
- Sound, lightweight SVG icons and UI primitives from `lucide-react`.

---

## 5. Components That Should Be Replaced
- **Old `LandingPage.tsx`:** Completely purged via git rollback. Rebuilt from scratch with clean modular components or cohesive high-performance sub-sections.
- **Hardcoded Fake Metric Cards:** Replaced with authenticated test-fixture metrics and clear `SYNTHETIC_DEMO` / `DEVELOPMENT` provenance labels.
- **Generic Hero Banner:** Replaced with interactive Three.js atmospheric canvas depicting India's latitude-longitude grid, streamlines, pressure contours, and precipitation particles.

---

## 6. Existing Backend & API Dependencies
- **FastAPI / Uvicorn Server:** Running on port 8000 (deployed on Render).
- **Endpoints for Live Telemetry:**
  - `GET /api/v1/forecast/latest` & `/api/v1/cycles/latest`
  - `GET /api/v1/regimes/latest` & `/api/v1/regimes/probabilities`
  - `GET /api/v1/verification/latest` & `/api/v1/health`
  - `GET /api/v1/system/status`
- **Graceful Fallback Guarantee:** The landing page is engineered with self-contained, scientifically vetted fallback data structures (`landingData.ts`). If the backend is cold-starting or temporarily unreachable, the page renders seamlessly with zero layout shifts or console errors.

---

## 7. Existing Benchmark & Data Sources (Authoritative Audit)
A thorough scan of repository files (`MODEL_CARD.md`, `REGIME_MODEL_CARD.md`, `PHASE_13_PROJECT_REPORT.md`, `real_data_performance.json`, `reports/verification/`) reveals:
1. **Operating Posture:** `SYNTHETIC_DEMO` / `DEVELOPMENT`. Real NCMRWF NCUM 0.17° and IMD 0.25° gridded observation archives are pending physical operational mounting.
2. **Authoritative Timing Benchmark (Fixture Mode):**
   - Total Pipeline Latency: ~390 ms
   - Source Discovery: 5.4 ms
   - Metadata Parsing: 52.4 ms
   - Meteorological QC: 0.8 ms (70,692 cells checked)
   - Forecast Execution: 328.6 ms (482 grid points inferred)
   - Verification Calculation: 2.5 ms
3. **Regime Classifier Synthetic Test Metrics (Held-out chronological partition):**
   - Test Accuracy: 0.9206 (Synthetic Demo)
   - Macro F1: 0.5922 | Calibrated Brier Score: 0.1568
   - 7 Canonical Regimes: Active Monsoon, Break Monsoon, Monsoon Low/Depression, Coastal Rainfall, Orographic Rainfall, Western Disturbance, Transition/Other.
4. **Baseline Comparison Models:**
   - `raw_nwp`: Raw NCUM precipitation forecast (uncalibrated)
   - `mean_bias`: Additive climatological offset
   - `qmap`: Quantile Mapping via historical CDF
   - `global_ml`: Single global LightGBM model (regime-unaware)
   - `ramp`: Regime-Aware Mixture-of-Experts (probabilistically gated)
5. **Categorical & Spatial Metrics:**
   - Continuous: RMSE, MAE, Bias
   - Contingency (Heavy Rainfall > 64.5 mm): CSI, POD, FAR, ETS
   - Spatial: Fractions Skill Score (FSS) at neighborhood scales

---

## 8. Git Rollback Strategy
- **Step 1:** Inspected commit history; identified single landing commit `4046067`.
- **Step 2:** Created immutable backup safety tag `backup/phase23-landing-page` and branch `safety/phase23-landing-page-backup`.
- **Step 3:** Executed clean `git revert 4046067 --no-edit`, leaving commit `af77d24`.
- **Step 4:** Verified clean build (`npm run build`) in 14.33s.
- **Step 5:** Rebuild landing page from clean baseline, commit with descriptive message, and push to `origin/main`.

---

## 9. New Information Architecture (The Continuous Storytelling Flow)
The landing page flows through 16 cinematic narrative chapters:
1. **01 — Global Header:** Transparent-to-glass sticky navigation, project identity, live links.
2. **02 — Cinematic Hero:** Three.js atmospheric canvas, India outline, particle stream, core thesis.
3. **03 — Scenographic Problem:** Why rainfall forecasting is not one problem (orographic, coastal, convection, extremes).
4. **04 — Why Raw NWP Is Not Enough:** The physics of grid-scale bias, systematic shifts, and uncaptured micro-regimes.
5. **05 — Core Insight ("One correction does not fit every atmosphere"):** Global ML vs. Regime-Aware routing.
6. **06 — Meet GatiSutra RAMP:** The 7-stage post-processing pipeline from ingest to spatial delivery.
7. **07 — Interactive Magic Moment ("Watch RAMP Decide"):** Live interactive simulation allowing users to select an atmospheric regime and witness soft gating, expert weights, and corrected output in real time.
8. **08 — Technical Architecture:** Interactive deep-dive into layers (Ingestion → QC → Feature Engine → Classifier → MoE Gating → Extreme Heads → Spatial → Verification).
9. **09 — End-to-End Workflow:** 10-step animated operational pipeline.
10. **10 — Real Technology Stack:** Strictly verified technologies with "What, Why, Where" rationale.
11. **11 — Evidence, Measurement & Verification:** Scientific verification framework, baseline comparison, transparent synthetic demo labeling.
12. **12 — What Makes RAMP Different:** Comparative matrix highlighting context-aware intelligence.
13. **13 — Feasibility & Operational Viability:** Transparent 4-pillar readiness breakdown and 6-phase maturity roadmap.
14. **14 — Real-World Scenario:** Walkthrough of a Low-Pressure System moving across Central India.
15. **15 — Operational Observability & Trust:** Lifecycle telemetry, cycle tracking, drift monitoring, data health.
16. **16 — Live System CTA & Footer:** Seamless launchpad to live operational dashboard, jury demo, and institutional footer ("Made by Team GatiSutra").

---

## 10. Animation Architecture
- **CSS Hardware-Accelerated Keyframes:** Particle flows, glowing node pulses, atmospheric wave propagation, radar sweeps.
- **Scroll-Triggered Reveals:** IntersectionObserver triggers staggered opacity, translation, and scale transitions.
- **Interactive State Transitions:** Smooth tab transitions in the "Watch RAMP Decide" simulation and Architecture explorer.
- **Hover Micro-Interactions:** Magnetic borders, gradient shifts, tooltips.

---

## 11. Three.js / WebGL Architecture
- **Scene Scope:** Dedicated `<canvas>` managed via React `useRef` and `useEffect`.
- **Atmospheric Visual Elements:**
  - Mathematical India coastline silhouette with glowing coordinate nodes.
  - Latitude/Longitude spherical grid lines with atmospheric curved mesh.
  - 1,200 particle velocity field simulating monsoon southwesterly winds and cyclonic vorticity.
  - Dynamic precipitation particles falling with responsive velocity.
  - Pulsing forecast grid points reflecting operational forecast nodes.
- **Resource Management & Performance:**
  - `requestAnimationFrame` loop paused when canvas scrolls out of viewport via `IntersectionObserver`.
  - Geometries, materials, and textures explicitly disposed on component unmount (`dispose()`).
  - Capped pixel ratio (`Math.min(window.devicePixelRatio, 2)`) to prevent GPU overhead on Retina/4K displays.
  - Particle count dynamically halved on mobile devices (`window.innerWidth < 768`).

---

## 12. Responsive Strategy
- **Desktop (≥ 1280px):** Full-bleed cinematic layouts, dual-column interactive simulators, horizontal workflow steps.
- **Laptop / Tablet (768px – 1024px):** Proportional grid scaling, touch-friendly interactive targets, collapsible diagrams.
- **Mobile (320px – 640px):** Single-column stacked narrative, vertical workflow timeline, lightweight Three.js particle density, touch-swipeable regime selectors, zero horizontal overflow.

---

## 13. Accessibility & Reduced-Motion Strategy
- **`prefers-reduced-motion` Media Query:** If enabled:
  - Three.js animation speed drops to zero (static scientific visualization).
  - Continuous CSS keyframe loops (radar sweep, pulsing rings) are subdued or paused.
  - Scroll reveals appear immediately with instant opacity.
- **Keyboard Navigation & ARIA:** All interactive regime buttons, architecture tabs, and drawer controls have appropriate ARIA attributes, semantic roles, and visible focus rings.
- **Contrast Ratios:** Text colors adhere strictly to WCAG AA/AAA standards against dark backgrounds (`#F8FAFC`, `#94A3B8`, `#38BDF8`).

---

## 14. Performance Strategy
- **Zero Heavy External CDN Bloat:** Three.js bundled locally via Vite tree-shaking.
- **Code Splitting & Lazy Rendering:** Interactive canvas deferred until initial DOM render.
- **Lightweight DOM Footprint:** Clean SVG vectors for flowcharts and architecture nodes instead of monolithic image assets.

---

## 15. Scientific-Integrity Strategy
- **Zero Fabricated Accreditations:** No unverified metrics.
- **Explicit Provenance Labels:** Every benchmark table or performance chart clearly specifies:
  - Dataset: Synthetic Demonstration Fixture (`ramp_dataset_real_v1.0.0` architecture smoke tests)
  - Baseline: Raw NCUM NWP
  - Note: "Authoritative operational verification pending physical mounting of NCMRWF/IMD observation archives."
- **Strict Terminology:** Authoritative meteorological terms (NCUM, NEPS, IMD, Isotonic Calibration, Mixture-of-Experts, Fractions Skill Score, CSI, Brier Score).

---

## 16. Implementation Phases
- **Phase A:** Create centralized data config `frontend/src/pages/landing/landingData.ts`.
- **Phase B:** Create Three.js Atmospheric Background component `AtmosphericHeroCanvas.tsx`.
- **Phase C:** Build the comprehensive `LandingPage.tsx` adhering to all 16 story chapters.
- **Phase D:** Wire route `/` in `frontend/src/App.tsx` (standalone outside `Shell`).
- **Phase E:** Run test build (`npm run build`), verify zero lint/type errors, test all navigation links.
- **Phase F:** Git commit, push to remote, and verify deployment readiness.

---

## 17. Testing Checklist
- [ ] Clean build: `npm run build` exits 0 with no TypeScript errors.
- [ ] Route `/` loads standalone without navbar duplication or Shell chrome.
- [ ] Route `/forecast` opens operational dashboard without disruption.
- [ ] Route `/jury-demo` opens Jury Demo page without disruption.
- [ ] Three.js canvas initializes cleanly, responds to mouse movement, and cleans up on unmount.
- [ ] "Watch RAMP Decide" simulation updates probabilities, expert bars, and forecast corrections dynamically.
- [ ] Architecture interactive tabs display accurate inputs, outputs, and scientific purpose.
- [ ] Mobile responsive layout tested at 375px, 768px, and 1280px without horizontal scroll.
- [ ] No mention of "SIH26080" anywhere in landing page DOM.
- [ ] Attribution reads "Made by Team GatiSutra".
- [ ] No unsubstantiated claims ("for the first time in India" or fabricated percentages).

---

## 18. Deployment Checklist
- [ ] Git commit matches conventional commit format (`feat: rebuild GatiSutra RAMP landing page...`).
- [ ] Push to `origin/main` triggers automatic deployment pipeline on Render.
- [ ] Verify production HTTPS response at `https://gatisura-ramp.onrender.com/`.
