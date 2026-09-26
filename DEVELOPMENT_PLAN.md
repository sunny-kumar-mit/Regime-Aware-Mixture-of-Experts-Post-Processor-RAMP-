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

### Phase 10 — Scientific Verification & Explainability (NEXT)
- Comprehensive WMO verification metrics across regimes, lead-times, and spatial zones
- SHAP feature attributions and regime expert sensitivity
- Synoptic case replays (active monsoon low, Western Disturbance, coastal cyclonic burst)
- Jury demonstration mode with side-by-side post-processing comparisons
- Final SIH Master Project Package and documentation hardening

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
