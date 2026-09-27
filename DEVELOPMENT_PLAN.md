# DEVELOPMENT PLAN — SIH26080
## Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts (RAMP)
**Organisation:** Ministry of Earth Sciences (MoES) / NCMRWF  
**Team Role:** Lead AI/Weather-Science Software Architect  
**Date:** 2026-09-25  
**Status:** Pre-implementation — Architecture & Planning Phase

---

## 1. Problem Summary

Rainfall forecast errors over India vary systematically with the prevailing **weather regime**
(active monsoon, break monsoon, monsoon low/depression, coastal, orographic, western disturbance).
A single global bias-correction cannot capture this regime-conditioned heterogeneity.

**RAMP** (Regime-Aware Mixture-of-Experts Post-Processor) addresses this by:
1. Identifying the *probability* of each weather regime from NWP fields.
2. Running a regime-specific **correction expert** for each regime.
3. Blending expert outputs using regime probabilities as soft weights.
4. Estimating calibrated probabilities of heavy / very heavy / extremely heavy rainfall.
5. Producing district-level forecast tables and grid maps.
6. Verifying skill against IMD gridded observations.

> **Scientific Constraint:** The system must **never** silently replace real data with synthetic data.
> All synthetic/demo modes must be explicitly labelled.

---

## 2. Existing Repository State

| Item | Status |
|------|--------|
| Repository at `d:\SIH26080` | **Empty — clean slate** |
| Existing models | None |
| Existing APIs | None |
| Existing frontend | None |
| Existing data pipelines | None |

No existing functionality to preserve. Full greenfield build.

---

## 3. Phased Delivery Plan

### Phase 0 — Foundation & Documentation ✅ *(this phase)*
- [x] Repository inspection
- [x] `DEVELOPMENT_PLAN.md`
- [x] `ARCHITECTURE.md`
- [x] `DATA_CONTRACTS.md`
- [x] `MODEL_CARD.md`
- [x] `TODO.md` (phase-divided checklist)
- [ ] Monorepo scaffold (folder skeleton, `.gitignore`, `README.md`)

### Phase 1 — Production Foundation ✅ COMPLETE
- FastAPI application shell with health, version, system endpoints
- React + TypeScript + Vite + Tailwind dashboard shell
- Docker & docker-compose configuration
- PostgreSQL & Redis configuration
- Unit & integration test scaffolding

### Phase 2 — Meteorological Data Layer ✅ COMPLETE
- Provider abstraction & registry (GFS, GEFS, NCMRWF, IMD 0.25°, Synthetic)
- NCMRWF adapter with honest UNAVAILABLE behavior (no fabrication)
- IMD 0.25° gridded observation adapter
- Spatial regridding to canonical 0.25° grid (bilinear/nearest)
- Unit normalisation & time harmonisation (valid_time invariant)
- QualityFlag engine (VALID_EXTREME preserved)
- 109/109 tests passed

### Phase 3 — Training Dataset Builder & Feature Engineering ✅ COMPLETE
- Spatio-temporal join engine on (latitude, longitude, forecast_valid_time)
- Feature engineering engine (wind speed/direction, cyclic doy/hour, 3x3 spatial, seasonal flags)
- Target construction pipeline (6 targets: continuous, occurrence, heavy, very heavy, extremely heavy, train climatology anomaly)
- Extreme rainfall preservation (>204.5mm up to 400+mm preserved without outlier clipping)
- Chronological data splitting with 24-hour purge embargo buffers
- LeakageGuard: 10-point audit failing loudly on violation
- Preprocessing pipeline (train-only fitting, serialized to manifest)
- Ensemble aggregator (preserves members, computes stats only when >1 member)
- Dataset versioning & artifacts (Parquet, Manifests, DATASET_CARD.md)
- 143/143 tests passed

### Phase 4 — Weather Regime Intelligence Engine ✅ COMPLETE
- Configurable regime definition registry (`config/regimes.yaml`)
- Physics-informed indicator engine (`RegimeIndicatorEngine`) for all 7 regimes
- Weak-label generation engine (`RegimeLabeler`) with `WEAK_RULE` provenance and quality tiers
- Authoritative label provider interface (`AuthoritativeRegimeLabelProvider`)
- Candidate classifiers: Rule Baseline, Random Forest, LightGBM with balanced class weights
- Zero-leakage enforcement via `LeakageGuard`
- One-vs-Rest Isotonic probability calibration fitted strictly on validation partition ($\sum p_i = 1.0$)
- UncertaintyEngine (Shannon entropy $H(p)$, normalized entropy, LOW/MEDIUM/HIGH levels)
- RegimeTransitionDetector (Total Variation Distance across sequential forecast horizons)
- Ensemble consensus evaluator aggregating member probabilities and inter-member spread
- 8 production REST API endpoints under `/api/regime/*`
- Upgraded `/regime` dashboard view with probability vectors, "Why this regime?" attribution, and grid preview
- 184/184 tests passed (41 Phase 4 tests)

### Phase 5 — Baseline Post-Processing & Benchmarking ✅ COMPLETE
- Raw NWP reference baseline (identity mapping, physical non-negativity $R \ge 0$)
- Classical Mean Bias Correction (train-only fitting, lead-time stratified, fallback)
- Empirical Quantile Mapping (0.1mm precipitation-aware dry occurrence, linear tail extrapolation)
- Global ML Post-Processor (LightGBM regressor with $\log(1+x)$ target transform, 25 atmospheric features)
- Continuous verification (RMSE, MAE, Mean Bias, Pearson $r$)
- Categorical contingency metrics (POD, FAR, CSI, ETS, FBIAS) at 0.1, 64.5, 115.6, 204.5 mm
- Neighborhood spatial verification (FSS across 25km, 50km, 100km, 200km)
- Paired bootstrap statistical significance engine (95% empirical confidence intervals vs RAW NWP)
- Post-hoc regime-stratified diagnostics across all 7 Phase 4 regimes: proven conditional degradation of Global ML during active monsoon
- Model registry (`BaselineModelRegistry`), inference service (`BaselineInferenceService`), 8 REST endpoints
- Frontend `/baseline` benchmarking dashboard with live charts, threshold toggles, and persistent synthetic demo banner
- 221/221 tests passed (37 Phase 5 tests)

### Phase 6 — RAMP Mixture-of-Experts Engine ✅ COMPLETE
- Core architectural implementation: $\text{RAMP}(x) = \sum_{k=0}^6 p_k(x) \cdot \text{Expert}_k(x)$
- Strictly soft gating ($p_k \ge 0, \sum p_k = 1.0 \pm 10^{-4}$), mathematical convexity invariant ($\min E_k \le \text{RAMP} \le \max E_k$), physical non-negativity ($\text{RAMP} \ge 0.0$ mm)
- 7 specialized regime regression experts with $\log(1+x)$ target scaling
- Leakage-free train-time regime assignment using Phase 4 forecast-time predictor inference
- Minimum sample threshold (`MIN_EXPERT_SAMPLES = 5`) and fallback hierarchy ($\text{Regime Expert} \to \text{Global ML} \to \text{Raw NWP}$)
- Benchmark verification against frozen Phase 5 ladder on TEST split ($N=63$): RAMP achieved RMSE 13.85 mm, MAE 6.84 mm, Pearson r 0.6697
- Statistically significant MAE improvement verified via paired bootstrap ($p < 0.05, 95\%\text{ CI: } [-2.01, -0.11]\text{ mm}$)
- Controlled ablation study (Global ML only vs Hard argmax vs Soft RAMP vs Uniform gating)
- Model registry (`RAMPModelRegistry`), inference service (`RAMPInferenceService`), deterministic CLI
- 13 REST API endpoints under `/api/ramp/*` and full interactive 10-section dashboard at `/ramp`
- 260/260 tests passed (39 Phase 6 tests)

### Phase 7 — Extreme Rainfall Probability Engine ✅ COMPLETE
- Multi-threshold classification heads for Rain ($\ge 0.1$ mm), Heavy ($\ge 64.5$ mm), Very Heavy ($\ge 115.6$ mm), and Extremely Heavy ($\ge 204.5$ mm)
- Platt scaling (logistic sigmoid) and Isotonic regression calibration fitted strictly on validation data
- Strict monotonic probability reconciliation ($P(\text{Rain}) \ge P(\text{Heavy}) \ge P(\text{Very Heavy}) \ge P(\text{Extremely Heavy})$)
- Comprehensive probability metrics (Brier, Brier Skill Score, ECE, MCE, Log Loss, ROC-AUC, PR-AUC)
- Lead-time, regime-conditioned, and spatial probability outputs
- Frozen model `extreme_prob_v1.0.0` serialized under `data/models/extreme/`
- 14 REST API endpoints under `/api/extreme/*`
- Interactive 10-section dashboard at `/extreme`
- 260/260 tests passed (39 Phase 7 tests)
- Report: `docs/reports/PHASE_7_PROJECT_REPORT.md`

### Phase 8 — Real-Data Integration & Operational Verification Readiness ✅ COMPLETE
- Multi-provider architecture (`RealDataProvider`, `SyntheticDataProvider`, NetCDF, GRIB, Parquet, CSV)
- Canonical `DatasetContract` schema (`observed_rainfall_mm`, `nwp_rainfall_mm`, spatiotemporal coordinates)
- 13-point `MeteorologicalQualityControl` distinguishing unphysical corruptions (`PHYSICAL_INVALID`) from severe convective events (`EXTREME_BUT_VALID` $\ge 204.5$ mm)
- Missing target observations mapped to evaluation unavailable (never 0.0 mm)
- Explicit `UnitNormalizer` with documented conversions and audit logs
- `TemporalAlignmentEngine` supporting Day 1 through Day 5 lead-time synchronization
- `SpatialAlignmentEngine` supporting 0.25° grid snap over India
- Extended `LeakageGuard` for real-data feature auditing (forbidding future observations, future/observed regimes, post-event variables)
- `PipelineReplayer` orchestrating full 8-stage operational replay
- `OperationalModelRegistry` maintaining freeze locks on `ramp_v1.0.0` and `extreme_prob_v1.0.0`
- `OperationalReadinessEvaluator` defining 6 engineering readiness tiers (Levels 0–5; currently Level 0: Synthetic Demo)
- `OperationalVerificationEngine` evaluating 6 systems (Raw NWP, Mean Bias, Quantile Mapping, Global ML, RAMP MoE, RAMP + Extreme Prob)
- Continuous metrics, threshold contingency (POD, FAR, CSI, ETS, FBIAS), probability metrics (Brier, BSS, ECE, MCE, PR-AUC), paired bootstrap (300 resamples), 7-regime stratification, Day 1–5 lead-time breakdown, spatial grid
- 14 REST API endpoints under `/api/operational/*`
- 15-section interactive dashboard at `/operational` with dynamic data status banner
- 286/286 tests passed (26 Phase 8 tests, 0 failures)
- Report: `docs/reports/PHASE_8_PROJECT_REPORT.md`

### Phase 9 — Spatial Forecast Products & District Aggregation ✅ COMPLETE
- Canonical 0.25° India grid model ($6.5^\circ\text{N}-38.5^\circ\text{N}$, $66.5^\circ\text{E}-100.5^\circ\text{E}$) with spherical metric cell area calculation
- 10-point `SpatialValidator` enforcing bounded domain, spatiotemporal uniqueness on `(grid_id, valid_time, lead_time)`, and strict probability monotonicity ($P(R \ge 0.1) \ge P(R \ge 64.5) \ge P(R \ge 115.6) \ge P(R \ge 204.5)$)
- `AdministrativeBoundaryProvider` normalizing boundary polygons into geographic EPSG:4326 for display and analytical Albers Equal Area Conic (EPSG:7755 parameters) for exact physical area calculation in $\text{km}^2$
- `GridDistrictIntersectionEngine` computing Shapely geometry intersections, overlap fractions, and district coverage percentages
- `DistrictAggregationEngine` executing area-weighted aggregation ($R_d = \sum w_i R_i / \sum w_i$), distribution quantiles (Min, Median, Mean, Max, P90, P95, P99), exceedance risk fractions, and localized convective hotspot identification
- Configurable rule-based `DistrictRiskClassifier` defining 5 engineering risk tiers (`NORMAL`, `WATCH`, `HIGH_RAINFALL`, `VERY_HIGH_RAINFALL`, `EXTREME_RAINFALL`) with transparent rule strings and probability criteria
- `SpatialUncertaintyEngine` combining spatial variance, grid coverage penalty, and regime classification entropy
- Multi-scale neighborhood `FractionsSkillScoreService` evaluating 5km, 25km, 50km, 100km, and 200km neighborhood windows against thresholds 0.1, 64.5, 115.6, and 204.5 mm (returning `NOT_AVAILABLE` when observations are absent without fabrication)
- Open GIS data exporter generating GeoJSON, CSV, and Parquet products with complete provenance metadata in `data/spatial_exports/`
- `SpatialProductRegistry` managing cache invalidation keys and immutable run manifests in `data/audit/spatial/`
- 15 REST API endpoints under `backend/src/ramp/api/v1/spatial.py` (`/api/spatial/*`)
- Interactive 18-section dashboard at `/spatial` with interactive SVG map, layer selectors (RAMP, NWP, Global ML, Difference, Probabilities, Regimes, Uncertainty, Coverage), district drawer, FSS inspection, and GIS downloads
- 314/314 tests passed (28 Phase 9 tests, 0 failures)
- Frontend production build passing (`tsc && vite build`, 0 errors)
- Report: `docs/reports/PHASE_9_PROJECT_REPORT.md`

### Phase 10 — Scientific Verification, Explainability & Jury Demo ✅ COMPLETE
- Comprehensive WMO verification metrics across regimes, lead-times, and spatial zones
- 300-sample bootstrap confidence intervals and Brier reliability calibration curves
- SHAP feature attributions and regime expert gating sensitivity matrix
- 5 synoptic case replays (Nagpur, Visakhapatnam, Kochi, Shimla, Jaipur)
- Jury demonstration mode with 8-stage pipeline tour and side-by-side post-processing comparisons
- 19 REST API endpoints under `/api/scientific/*`
- Interactive dashboards at `/verification`, `/explainability`, and `/jury-demo`
- Report: `docs/reports/PHASE_10_PROJECT_REPORT.md`

### Phase 11 — Real Data Activation & Operational Data Plane ✅ COMPLETE
- Provider hierarchy: PRIMARY (NCUM, NEPS, IMD Obs) > SECONDARY (GFS, GEFS) > DEMO (Synthetic Demo)
- Strict operational data modes: `REAL_OPERATIONAL`, `REAL_ARCHIVE`, `PUBLIC_PROXY`, `SYNTHETIC_DEMO`, `NOT_AVAILABLE`
- `CFMetadataInspector`: NetCDF & GRIB inspection, coordinate normalization, metadata-driven units, SHA-256 tracking
- `CycleManager`: 00, 06, 12, 18 UTC forecast cycle discovery without fabrication
- `LeadTimeNormalizer`: Arbitrary lead discovery from actual files (6h to 120h+)
- `NCMRWFGridHarmoniser`: Native NCMRWF grid (0.12°) mass-conserving harmonisation to canonical 0.25° RAMP grid
- `DataMatchingEngine`: NWP + IMD temporal matcher (`valid_time == obs_time`), anti-leakage guard, missing value zero-fill prohibition
- Live Header Status: 4 real-time indicators (NCUM, NEPS, IMD, RAMP) and interactive Data Feeds desk
- 9 REST API endpoints under `/api/data/*`
- 328/328 tests passed (13 Phase 11 tests, 0 failures)
- Report: `docs/reports/PHASE_11_PROJECT_REPORT.md`

### Phase 12 — Real Paired Training Dataset & Operational UI Shell ✅ COMPLETE
- Constructed real NWP + IMD paired dataset pipeline (`ramp_dataset_real_v1.0.0`) in `ml/datasets/real/`
- Strict Scientific Honesty Contract: Truthfully reports `NOT_AVAILABLE` when real archives are unmounted; 0 fake records created
- Zero-leakage feature policy: 18 predictors in X; targets strictly in Y
- Sequential chronological train/validation/test partitioning
- Exported 10 authoritative metadata artifacts and manifests
- Mounted 8 dedicated REST API endpoints under `/api/datasets/real/*`
- Redesigned 3-zone meteorological operations header with compact DATA status popover and categorized sidebar
- 351/351 tests passed (23 Phase 12 tests, 0 failures)
- Report: `docs/reports/PHASE_12_PROJECT_REPORT.md`

### Phase 13 — Production Model Retraining, Calibration & Model Registry ✅ COMPLETE
- Automated end-to-end ML training pipeline in `ml/training/`
- Real training eligibility gate: honestly reported `REAL_DATA: DEFERRED` while raw archives are unmounted
- Validated pipeline using deterministic synthetic fixtures with lifecycle strictly set to `DEVELOPMENT`
- Trained & registered 4 immutable models in `ml/model_registry/` (`ramp_global_v2.0.0`, `ramp_regime_v2.0.0`, `ramp_moe_v2.0.0`, `ramp_extreme_v2.0.0`)
- Enforced 12 mandatory promotion gates and multi-threshold probability monotonicity
- Validation-fitted calibration via Isotonic Regression & Platt Scaling
- Mounted 8 REST APIs under `/api/models/*`
- Built Model Registry (`/models`) and Model Training (`/training`) UI dashboards
- 372/372 tests passed (21 Phase 13 tests, zero regressions)
- Report: `docs/reports/PHASE_13_PROJECT_REPORT.md`

### Phase 14 — Operational Forecast Inference, Cycle Orchestration & NCMRWF-Style Forecast Products ✅ COMPLETE
- Complete 16-step operational forecast inference engine in `ml/inference/`
- Dynamic forecast cycle (00Z, 12Z) and dynamic lead time (+6h to +120h) resolution without data fabrication
- Enforced 11 automated operational validation gates before inference
- Enforced `ramp_features_v1.0.0` (18 canonical predictors) and `ramp_targets_v1.0.0` contracts
- RAMP Mixture-of-Experts inference with non-negativity and convex expert spread uncertainty
- Calibrated extreme rainfall exceedance probabilities with strict monotonicity verification
- Spatial grid mapping (0.25°), 21 representative district forecasts, and 11 state syntheses
- Standardized 9 operational forecast products with embedded immutable metadata blocks
- Forecast Run IDs (`RAMP_YYYYMMDD_CYCLE_T*`), `forecast_manifest.json`, and audit logging
- 13 dedicated REST API endpoints under `/api/forecast/*` with multi-format export (`json`, `csv`, `geojson`)
- Primary Operational Workspace (`/forecast`) with interactive Canvas map, timeline, and drill-down modal
- Rule 14-AB Data Honesty Banner permanently displayed in `SYNTHETIC_DEMO` mode
- 84/84 cumulative repository tests passed (26 Phase 14 tests, zero regressions)
- Report: `docs/reports/PHASE_14_PROJECT_REPORT.md`

### Phase 15 — Operations Control Center ✅ COMPLETE
- Thread-safe 11-state operational automaton governing forecast cycle lifecycle (`ml/operations/state.py`)
- Background idempotent scheduler with SHA-256 job deduplication preventing double-runs (`ml/operations/scheduler.py`)
- 8-rule real-time metric alert monitor with full alert lifecycle (`ml/operations/alerts.py`)
- Diagnostic drift monitor for KS-statistic feature drift, prediction drift, and ECE calibration drift (`ml/operations/drift.py`)
- 30-point production readiness engine with GO / CONDITIONAL_GO / NO_GO launch verdicts (`ml/operations/production.py`)
- 15 operational REST APIs mounted under `/api/operations/*`
- 5-tab Operations Control Center UI at `/operations`
- 44/44 Phase 15 tests passed; report: `docs/reports/PHASE_15_PROJECT_REPORT.md`

### Phase 16 — Real-Data Activation, Live Ingestion, End-to-End Operational Validation & Production Cutover ✅ COMPLETE
- Production-grade source adapters for NCMRWF NCUM, NCMRWF NEPS, and IMD 0.25° Gridded Rainfall (`ml/ingestion/adapters.py`)
- Recursive file discovery service with header inspection and authority level tagging (`ml/ingestion/discovery.py`)
- Zero-byte guard and SHA-256 manifest integrity engine (`ml/ingestion/integrity.py`)
- CF-1.8 NetCDF and GRIB metadata validation engine (`ml/ingestion/metadata.py`)
- Synoptic temporal cycle alignment (00Z, 12Z) and dynamic lead time verification (`ml/ingestion/temporal.py`)
- Canonical Indian Subcontinent spatial domain (17,673 cells) and 700+ district coverage validation (`ml/ingestion/spatial.py`)
- Strict rainfall unit normalization to mm with fatal error on unverified units (`ml/ingestion/units.py`)
- Meteorological physical QC bounds engine with NaN/Inf guards (`ml/ingestion/qc.py`)
- Zero-future-leakage forecast/observation pairing engine and `pairing_manifest.json` (`ml/ingestion/pairing.py`)
- 15-gate real-data activation engine with 5-stage lifecycle and two-stage operator authorization (`ml/ingestion/activation.py`)
- Tamper-evident activation audit trail in `data/audit/activation_audit.jsonl`
- Scientific honesty safeguard: Authoritative data unmounted -> system strictly reports `WAITING_FOR_AUTHORITATIVE_DATA`, `REAL_OPERATIONAL = BLOCKED`, and `REAL_VERIFICATION = NOT_AVAILABLE`
- Continuous and probabilistic verification engine (Brier Score, BSS, ECE) with sample sufficiency guard (`ml/ingestion/verification.py`)
- 14 REST API endpoints under `/api/activation/*`, `/api/ingestion/*`, `/api/verification/*`
- Dedicated operational web consoles at `/activation`, `/data/ingestion`, `/forecast/verification`, and `/operations` Tab 6
- 30/30 Phase 16 tests passing (7.45 s); 157/157 full regression tests passing across Phases 11–16 (18.09 s)
- Measured pipeline performance saved in `real_data_performance.json` (390.257 ms total latency)
- 0 browser console errors across all pages
- Report: `docs/reports/PHASE_16_PROJECT_REPORT.md`

### Phase 17 — Production Deployment, Live Data Connectivity, Continuous Verification & Operational Reliability ✅ COMPLETE
- Full production deployment infrastructure: Docker containers (`Dockerfile`, `Dockerfile.frontend`, `docker-compose.prod.yml`), Nginx reverse proxy with TLS/SSL configs and security headers, Systemd service units (`ramp-backend.service`, `ramp-worker.service`, `ramp-scheduler.service`), Prometheus metrics exporter & alerting rules, and Grafana dashboards (`deployment/`)
- Production Configuration Engine (`ml/production/config.py`) with strict validation across `DEVELOPMENT`, `STAGING`, and `PRODUCTION` tiers, preventing unvalidated deployments
- Live Data Provider Connectivity & SLA Deadlines Engine (`ml/production/connectivity.py`) monitoring NCMRWF NCUM, NEPS, and IMD 0.25° arrival deadlines (00Z/12Z cutoffs) with jitter, retry backoff, and circuit breaker patterns
- Robust Operational Cycle Automaton (`ml/production/cycle_engine.py`) managing synoptic cycle lifecycle (`DISCOVERY` -> `VALIDATION` -> `FEATURE_PREP` -> `INFERENCE` -> `SPATIAL_GEN` -> `VERIFICATION` -> `ARCHIVAL`) with strict idempotency and SHA-256 deduplication
- Zero-Downtime Hot-Reload & Safe Model Promotion Engine (`ml/production/model_lifecycle.py`) verifying frozen model invariants (`ramp_global_v2.0.0`, `ramp_regime_v2.0.0`, `ramp_moe_v2.0.0`, `ramp_extreme_v2.0.0`)
- Continuous Operational Verification Pipeline (`ml/production/continuous_verification.py`) computing rolling WMO metrics (RMSE, MAE, Bias, CSI, POD, FAR, ETS, Brier Score, ECE) when verified observations arrive
- Comprehensive 14-Gate Operational Cutover Engine (`ml/production/cutover.py`) enforcing automated gates across Data, Security, Reliability, Verification, and Operations, with operator cutover request, supervisor dual-authorization, and instant rollback capability
- Modular Health Check Probes (`ml/production/health_probes.py`) exposing `/health/live`, `/health/ready`, `/health/data`, `/health/models`, `/health/inference`, `/health/operations`, and `/health/overall`
- Disaster Recovery & Automated Backup Engine (`ml/production/backup.py`) with SHA-256 integrity manifests, automated rotation, and point-in-time restore
- Security & Compliance Hardening (`ml/production/security.py`) enforcing zero plain-text secrets, rate limiting, and RBAC
- 17 production REST API endpoints under `/api/production/*` and 7 modular health probes
- Frontend UIs: `/operations/cycles` (Operational Cycles), `/operations/data-health` (Data Health & Connectivity), `/forecast/verification/history` (Verification History), `/production` (Production Cutover & Health Status), upgraded `/operations` Live Operations tab rendering all 12 operational sections
- 35/35 Phase 17 tests passing; 192/192 full regression tests passing across Phases 11–17; 0 browser console errors across all 13 pages
- Complete Phase 17 report: `docs/reports/PHASE_17_PROJECT_REPORT.md`

### Phase 18 — Real-Data Activation, Institutional Acceptance Testing, Multi-Cycle Scientific Verification & Operational Product Validation ✅ COMPLETE
- Authoritative data source discovery and validation (`ml/acceptance/sources.py`, `validation.py`) with honest `WAITING_FOR_AUTHORITATIVE_DATA` / `NOT_AVAILABLE` status reporting
- Rigorous file validation: NCUM (18 predictors, physical bounds, anti-interpolation), NEPS (23 members, spread, exceedance probabilities), IMD (0.25° grid, `GROUND_TRUTH_ONLY`)
- Multi-cycle discovery and pairing with anti-leakage guarantee (`ml/acceptance/cycles.py`), requiring $\ge 3$ cycles for cutover eligibility
- Real data integrity matrix evaluating SHA-256 hashes, temporal continuity, domain bounds, and physical consistency
- Staged batch inference engine (`ml/acceptance/staging.py`) operating on frozen models (`v2.0.0`) with `PUBLICATION = DISABLED` and probability monotonicity enforcement
- Comprehensive scientific verification suite (`ml/acceptance/verification.py`) computing WMO continuous (RMSE, MAE, Bias, $r$) and categorical (CSI, POD, FAR, ETS) metrics, 95% bootstrap confidence intervals ($B=1000$), spatial error analysis, Fractions Skill Score (5–200 km), and reliability diagrams
- Objective 5-system baseline comparison (Raw NCUM, Bias-Corrected, Quantile Mapping, Global ML, RAMP MoE) presented neutrally without subjective promotional labels
- Operational failure taxonomy (`ml/acceptance/cases.py`) detecting false extremes, misses, timing offsets, spatial displacements, and regime misclassifications
- Operational case replay service (`/forecast/cases`) with honest notice awaiting authoritative archive mounts
- 12-category institutional acceptance engine (`ml/acceptance/engine.py`) and two-stage human cutover governance (Operator Request + Supervisor Approval) with instant rollback
- 15 REST API endpoints mounted under `/api/acceptance/*`
- Frontend dashboards: Acceptance Console (`/acceptance`) with 4 interactive tabs and Operational Case Replay (`/forecast/cases`)
- 35/35 Phase 18 tests passing; 227/227 cumulative regression tests passing across Phases 11–18; 0 browser console errors
- Comprehensive documentation: `docs/reports/PHASE_18_PROJECT_REPORT.md`

### Phase 19 — Real Data Activation Lab: Authoritative Data Acquisition, Import, Mapping, Real Inference & First Real Forecast Experiment ✅ COMPLETE
- Isolated Real Data Workspace (`/data/real/`) with subdirectories for `incoming/`, `validated/`, `rejected/`, `observations/`, `forecasts/`, `manifests/`, `runs/`, and markdown run reports (`docs/real-data-runs/`)
- Multi-format ingestion adapters (`ml/real_data/adapters/`): NetCDF4, GRIB2, CSV, and Parquet readers preserving original byte payloads without lossy format conversions
- NCUM Real Data Adapter (`ml/real_data/adapters/ncum.py`) verifying synoptic cycles, leads (+6h to +120h), vertical levels (850 hPa), and mapping source variables to canonical RAMP names; raises `MISSING_REQUIRED_FEATURE` without artificial infilling
- NEPS Ensemble Adapter (`ml/real_data/adapters/neps.py`) supporting control and perturbed members (`mem00`..`mem22` / `ens00`..`ens22`), computing ensemble statistics and flagging `NEPS_FEATURES_INCOMPLETE` if members/fields are missing
- IMD Real Observation Adapter (`ml/real_data/adapters/imd.py`) reading 0.25° gridded daily rainfall, enforcing physical non-negativity ($R \ge 0$), and permanently tagging data `GROUND_TRUTH_ONLY` to prevent leakage into model features
- Public Product Ingestion Adapter (`ml/real_data/adapters/public_products.py`) parsing public NCMRWF/IMD bulletins with strict separation (`PUBLIC_PRODUCT_ONLY -> RAMP_INFERENCE_NOT_POSSIBLE`) when raw 3D predictors are absent
- Feature Contract Mapper (`ml/real_data/feature_mapper.py`) explicitly evaluating source variables against `ramp_features_v1.0.0` (18 canonical predictors) and emitting structured mapping manifests without silent substitution
- Explicit Unit Normalization (`ml/real_data/unit_normalizer.py`) converting physical units (Kelvin $\to$ Celsius, Pa $\to$ hPa, kg m⁻² s⁻¹ $\to$ mm) and appending audit entries to `data/manifests/transformation_manifest.json`
- Spatial Grid & Domain Validator (`ml/real_data/grid_validator.py`) verifying the 0.25° India domain ($129 \times 137$ cells) and recording explicit bilinear regridding parameters without nearest-neighbor smoothing
- Anti-Leakage Observation Pairing (`ml/real_data/run_engine.py`) using cryptographic SHA-256 forecast and observation hashes to pair forecasts with observations at valid time without temporal leakage
- Real Data Experiment Engine (`ml/real_data/run_engine.py`) orchestrating an 11-stage pipeline on strictly frozen models (`v2.0.0`), producing post-processed rainfall, correction fields, regime probabilities, extreme rainfall exceedance probabilities, district aggregations, and WMO verification metrics
- Dual Operating Mode Separation: `REAL_DATA_EXPERIMENT` (Mode A) allows isolated experimentation on real files without triggering production cutover; `REAL_OPERATIONAL_ACTIVATION` (Mode B) strictly enforces all Phase 16–18 gates
- Comprehensive Lineage & Manifest Generation: Cryptographic `run_manifest.json` and human-readable experiment reports (`docs/real-data-runs/<run_id>.md`) generated for every run
- Granular 14-Stage Failure Diagnostics (`ml/real_data/models.py`) identifying exact failure stages (from `IMPORT_FAILED` to `VERIFICATION_FAILED`) without generic error messages
- Remote Storage Connector Abstraction (`ml/real_data/remote_connector.py`) supporting HTTPS, SFTP, and S3-compatible sources with environment variable credentials (`NCUM_DATA_ROOT`, `NEPS_DATA_ROOT`, `IMD_DATA_ROOT`)
- 14 REST API Endpoints mounted under `/api/real-data/*` covering scan, import, sources, files, status, validate, reject, promote, runs, execute, mount-status, and diagnose
- Interactive Frontend Console: Real Data Lab (`/real-data`) with 4 interactive tabs, interactive Canvas-based India NWP vs RAMP comparison map, 7-step user workflow guide, and one-click real data diagnostic modal
- 30/30 Phase 19 tests passing; 257/257 full cumulative regression tests passing across Phases 11–19 with zero regressions; 0 browser console errors
- Comprehensive documentation: `docs/reports/PHASE_19_PROJECT_REPORT.md`

### Phase 20 — Physical Mount Integration, Authoritative Multi-Year Live Verification & Continuous Operational Routine (FUTURE / HANDOFF)
- Mount physical NCMRWF and IMD high-throughput storage volumes (`/data/ncmrwf/ncum`, `/data/ncmrwf/neps`, `/data/imd/observed`)
- Consume verified Phase 19 deliverables: real multi-cycle archive, first real inference results, real verification history, calibrated real forecasts, district-level real products, regime-specific real performance, real operational cycle history, data lineage, and acceptance evidence
- Transition live connectivity status from `UNMOUNTED` to `CONNECTED`
- Authorize live production cutover via dual-operator key workflow (`OPERATOR_REQUEST` + `SUPERVISOR_APPROVAL`)
- Run continuous automated daily operational synoptic cycles (00Z, 12Z) and continuous multi-year verification against incoming real IMD observations



---

## 4. Team Roles (Recommended)

| Role | Responsibility |
|------|----------------|
| ML Lead | Regime classifier, MoE engine, calibration |
| Data Engineer | Ingestion adapters, harmonisation, PostgreSQL |
| Backend Lead | FastAPI, Celery, Redis, MLflow |
| Frontend Lead | React dashboard, MapLibre, Recharts |
| DevOps | Docker, CI/CD, monitoring |
| Domain Expert | Feature validation, verification metrics, IMD thresholds |

---

## 5. Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Regime output type | **Soft probabilities** (never hard class) | Captures mixed-regime days; enables smooth blending |
| Expert blending | Linear mixture-of-experts | Interpretable, scientifically sound, differentiable |
| ML framework | LightGBM primary, PyTorch upgrade path | Fast iteration; neural upgrade without rewrite |
| Data format | NetCDF4 / GRIB2 -> xarray | Community standard for NWP data |
| DB | PostgreSQL + PostGIS | Spatial queries, time-series, robust |
| Frontend map | MapLibre GL JS | Open-source, fast vector tiles |
| Experiment tracking | MLflow | Self-hosted, model registry, no vendor lock-in |
| Demo mode | Explicit synthetic flag in all API responses | Scientific integrity requirement |

---

## 6. Scientific Integrity Rules

1. **Never** fabricate model accuracy or verification scores.
2. **Never** silently replace NWP data or observations with random data.
3. All synthetic data must carry `"data_mode": "SYNTHETIC_DEMO"` in API responses and UI banners.
4. All verification must be computed against actual observations, not model output.
5. Regime probabilities must sum to 1.0 at every grid point and time step.

---

## 7. Milestones

| Milestone | Target | Deliverable |
|-----------|--------|-------------|
| M0 | Day 1 | Architecture docs, folder scaffold |
| M1 | Day 3 | Backend skeleton, data adapters, DB schema |
| M2 | Day 6 | Feature engineering, regime classifier |
| M3 | Day 9 | RAMP MoE engine, baselines |
| M4 | Day 11 | Extreme rainfall engine |
| M5 | Day 13 | Spatial processing, district aggregation |
| M6 | Day 15 | Verification engine |
| M7 | Day 18 | Full REST API |
| M8 | Day 22 | React dashboard |
| M9 | Day 25 | Integration, Docker, CI/CD |
| M10 | Day 28 | Final demo, documentation |
