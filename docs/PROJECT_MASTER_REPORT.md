# RAMP Master Technical Report — Smart India Hackathon 2026

**Project Title:** RAMP — Regime-Aware Mixture-of-Experts Post-Processor  
**Problem Statement:** SIH26080 — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts  
**Ministry / Organization:** Ministry of Earth Sciences (MoES)  
**Department:** National Centre for Medium Range Weather Forecasting (NCMRWF)  
**Document Classification:** Master Technical Report (Phase 8 Milestone)  
**Current Milestone:** PHASE 8 COMPLETE (Real-Data Integration & Operational Verification Readiness)  

---

## 1. Problem Statement & Operational Context
Numerical Weather Prediction (NWP) models operated by NCMRWF (including the deterministic NCUM global model and NEPS ensemble system) provide the foundational dynamical forecasts for the Indian monsoon. However, raw NWP outputs exhibit pronounced, systematic rainfall biases:
1. **Orographic Over/Under-Prediction:** Coarse grid resolutions smooth steep topographical gradients along the Western Ghats and Himalayan foothills, failing to resolve localized convective ascent.
2. **Marine Boundary Layer Smoothing:** Global models struggle to capture coastal land-sea thermal breezes and convergence lines, smearing offshore convection onto land stations.
3. **Depression Track Errors:** Minor spatial displacements in synoptic low pressure and depression tracks produce severe spatial dipole errors (false deluge in one district, false drought in another).
4. **Extreme Precipitation Tail Suppression:** Convective parameterization schemes frequently underestimate rainfall accumulations exceeding IMD heavy ($\ge 64.5$ mm), very heavy ($\ge 115.6$ mm), and extremely heavy ($\ge 204.5$ mm) thresholds.

SIH26080 challenges us to build an operational AI post-processing system that conditions rainfall corrections on prevailing and forecast weather regimes, moving beyond traditional one-size-fits-all bias correction methods.

---

## 2. Scientific Motivation & Core Innovation
Conventional post-processing methods (such as simple mean bias correction, classical quantile mapping, or monolithic gradient boosting) apply global transformations across all weather states. This creates severe trade-offs: a correction that improves active monsoon forecasts degrades forecasts during break periods or depression events.

**RAMP's Core Innovation:**
Instead of a monolithic regressor or discrete hard classification, RAMP introduces a **Regime-Aware Mixture-of-Experts (MoE)** architecture:
1. **Soft Probability Gating:** The forecast atmospheric state is mapped into a continuous probability distribution across 7 canonical weather regimes:
   $$p = [p_{\text{active}}, p_{\text{break}}, p_{\text{depression}}, p_{\text{coastal}}, p_{\text{orographic}}, p_{\text{wd}}, p_{\text{transition}}]^T \in \mathbb{R}^7, \quad \sum_{k=1}^7 p_k = 1.0$$
2. **Regime-Conditioned Experts:** Dedicated post-processing experts are trained on specific meteorological subsets.
3. **Convex Mixture Prediction:** Final post-processed precipitation is the smooth, continuous convex combination of expert estimators:
   $$\hat{R}_{\text{RAMP}}(x) = \sum_{k=1}^7 p_k(x) \cdot \operatorname{Expert}_k(x)$$

---

## 3. High-Level System Architecture
```
                         NWP FORECASTS (NCUM, NEPS, GFS)
                                        │
                                        ▼
                      Phase 2: METEOROLOGICAL DATA LAYER
                   (Unit Conversion, 0.25° Regridding, QA)
                                        │
                                        ▼
                     Phase 3: DATASET & FEATURE ENGINEERING
                 (27 Predictor Features, 6 Targets, Purge Split)
                                        │
                                        ▼
                   Phase 4: WEATHER REGIME INTELLIGENCE ENGINE
                (Physics Indicators -> LightGBM -> Calibration)
                                        │
                 ┌──────────────────────┴──────────────────────┐
                 ▼                                             ▼
       Regime Probability Vector P(regime)            Transition & Uncertainty
                 │                                             │
                 ▼                                             ▼
     [Phase 5: Baseline Models]                     [Phase 6: RAMP MoE Post-Processor]*
     (Raw NWP, Mean Bias, QMap, ML)                 (Soft Convex Combination of Experts)*
                 │                                             │
                 └──────────────────────┬──────────────────────┘
                                        ▼
                   [Phase 7: Extreme Probabilistic Engine]*
                   (Calibrated P(Rain >= 64.5, 115.6, 204.5 mm))*
                                        │
                                        ▼
                   [Phase 8: Spatial & District Forecasts]*
                   (0.25° India Grids & District Alert Bulletins)*
                                        │
                                        ▼
                   [Phase 9: Scientific Verification & WMO]*
                   (RMSE, CSI, POD, FAR, ETS, FSS vs IMD Obs)*
                                        │
                                        ▼
                   [Phase 10: Explainability & Jury Demo]*
```
*\* Note: Phases marked with an asterisk are planned and intentionally scoped for subsequent development.*

---

## 4. Phase-by-Phase Progress Summary

### Phase 1 — Production Foundation [COMPLETE]
- FastAPI enterprise backend with typed Pydantic contracts and structured JSON logging.
- React 18 + TypeScript + Vite frontend with Tailwind CSS and glassmorphic meteorological dashboard.
- Docker and multi-service docker-compose setup (FastAPI, Redis, PostgreSQL).
- Testing: 4 unit tests passing.

### Phase 2 — Meteorological Data Layer [COMPLETE]
- Provider abstraction architecture (`BaseMeteorologicalProvider`).
- Adapters for GFS, GEFS, NCMRWF (NCUM/NEPS), IMD gridded observations, and synthetic generators.
- Bilinear spatial regridding to canonical India 0.25° grid ($129 \times 137 = 17,673$ grid points).
- Automated unit harmonization (kg m⁻² s⁻¹ $\to$ mm, Pa $\to$ hPa, Kelvin $\to$ Celsius, knots $\to$ m/s).
- Quality flag engine (`VALID`, `MISSING`, `INVALID`, `ESTIMATED`, `EXTREME`) and SHA-256 provenance auditing.
- Honest unavailable behavior: reports `UNAVAILABLE` when real archives are absent (never fabricates).
- Testing: 74 unit tests passing.

### Phase 3 — Training Dataset & Feature Engineering [COMPLETE]
- Feature store with 31 registered specifications (27 active tabular predictors).
- 6 canonical verification targets aligned with IMD standards (continuous, log-transformed, rain flag, heavy, very heavy, extremely heavy).
- Chronological train/validation/test splitting with a 48-hour purge buffer to eliminate autoregressive leakage.
- Strict `LeakageGuard` preventing future observation targets from entering predictor feature sets.
- Parquet dataset serialization (`ramp_dataset_v0.3.0`) with version metadata.
- Testing: 65 unit and integration tests passing.

### Phase 4 — Weather Regime Intelligence Engine [COMPLETE]
- Registered 7 canonical monsoon regimes in `config/regimes.yaml`.
- `RegimeIndicatorEngine` computing physics-informed composite scores with graceful degradation for missing DEM/coastal features.
- Weak-label generation engine (`RegimeLabeler`) with `WEAK_RULE` provenance and quality tiers.
- Authoritative label interface (`AuthoritativeRegimeLabelProvider`).
- Candidate classifiers: Rule Baseline, Random Forest, and LightGBM with balanced multiclass weights.
- Multi-class probability calibration (Isotonic Regression) fitted **strictly on validation data**; probabilities strictly sum to $1.0 \pm 10^{-5}$.
- Information-theoretic Shannon entropy ($H(p)$ bits) and uncertainty levels (`LOW`, `MEDIUM`, `HIGH`).
- Sequential regime transition detector ($TVD$) and trajectory state tracking.
- Ensemble consensus evaluator aggregating member probabilities and inter-member spread.
- 8 production REST endpoints under `/api/regime/*`.
- Upgraded frontend `/regime` dashboard with probability vectors, "Why this regime?" attribution, and spatial grid previews.
- Testing: 41 unit and integration tests passing.

### Phase 5 — Baseline Post-Processing & Benchmarking [COMPLETE]
- Constructed 4 global baseline systems: Raw NWP, Mean Bias Correction (lead-time stratified), Empirical Quantile Mapping (dry-occurrence separation + linear tail extrapolation), and Global LightGBM ($\log(1+x)$ regression).
- Strict non-negativity constraint ($R \ge 0.0$ mm) and extreme event tail preservation ($>64.5, >115.6, >204.5$ mm).
- Standardized verification engine: RMSE, MAE, Mean Bias, Pearson $r$, POD, FAR, CSI, ETS, FBIAS.
- Spatial Fractions Skill Score (`FSSCalculator`) across 25km, 50km, 100km, 200km neighborhood scales.
- Paired bootstrap statistical significance engine (`BootstrapComparator`) with 95% empirical confidence intervals.
- Post-hoc regime-stratified diagnostics across all 7 Phase 4 regimes: demonstrated that Global ML degrades in active convective regimes (bias $-6.20$ mm), proving the empirical need for Phase 6 RAMP.
- `BaselineModelRegistry`, `BaselineInferenceService`, CLI tools, and 8 REST API endpoints under `/api/baselines/*`.
- Frontend `/baseline` benchmarking dashboard with live charts, threshold selectors, and persistent synthetic demo notices.
- Testing: 37 unit and integration tests passing (221 cumulative tests passing, 0 failures).

### Phase 6 — RAMP Mixture-of-Experts [COMPLETE]
- Implemented RAMP core formulation: $\text{RAMP}(x) = \sum_{k=0}^6 p_k(x) \cdot \text{Expert}_k(x)$ using Phase 4 calibrated continuous probabilities.
- Enforced strictly soft gating ($p_k \ge 0, \sum p_k = 1.0 \pm 10^{-4}$), mathematical convexity invariant ($\min E_k \le \text{RAMP} \le \max E_k$), and physical non-negativity ($\text{RAMP} \ge 0.0$ mm).
- Specialized 7 LightGBM regime regression experts with $\log(1+x)$ target scaling.
- Built training-time regime assignment using Phase 4 forecast-time predictor inference with zero target leakage.
- Implemented `MIN_EXPERT_SAMPLES = 5` and fallback hierarchy ($\text{Regime Expert} \to \text{Global ML} \to \text{Raw NWP}$).
- Evaluated against Phase 5 frozen baselines on TEST split ($N=63$): RAMP achieved **RMSE 13.85 mm** (vs Global ML 15.48 mm, Raw NWP 16.18 mm), **MAE 6.84 mm** (vs Global ML 7.90 mm), **Pearson r 0.6697** (vs 0.5995).
- Paired bootstrap test verified significant MAE improvement ($p < 0.05, 95\%\text{ CI: } [-2.01, -0.11]\text{ mm}$).
- Ablation study proved calibrated soft gating ($13.85$ mm) outperforms uniform gating ($16.58$ mm) and Global ML ($15.48$ mm).
- Persisted versioned model artifacts under `data/models/ramp/ramp_v1.0.0/`.
- Built 13 REST API endpoints under `/api/ramp/*` and full interactive 10-section dashboard at `/ramp`.
- Testing: 39 unit and integration tests passing (260 cumulative tests passing, 0 failures).

### Phase 7 — Extreme Rainfall Probability Engine [COMPLETE]
- **Objective:** Build a calibrated probability engine converting RAMP's continuous rainfall forecasts and regime probabilities into reliable exceedance probabilities for IMD thresholds: Rain ($\ge 0.1$ mm), Heavy ($\ge 64.5$ mm), Very Heavy ($\ge 115.6$ mm), and Extremely Heavy ($\ge 204.5$ mm).
- **Implementation:** Specialized LightGBM threshold probability heads with class imbalance weighting; dual-tier calibration via Platt scaling (logistic sigmoid) and Isotonic regression fitted strictly on validation data; post-calibration monotonic probability reconciliation ($P(	ext{Rain}) \ge P(	ext{Heavy}) \ge P(	ext{Very Heavy}) \ge P(	ext{Extremely Heavy})$).
- **Architecture:** Feedforward pipeline taking RAMP deterministic forecast + Phase 4 regime probabilities + 25 atmospheric features $	o$ threshold probability heads $	o$ calibration $	o$ monotonicity reconciliation $	o$ spatial probability maps.
- **Data:** Training and validation on `ramp_dataset.parquet` (synthetic demonstration partition; $N=63$ test instances).
- **Models:** `extreme_prob_v1.0.0` frozen model artifacts serialized with threshold classifiers, calibrators, and configuration.
- **APIs:** 14 REST endpoints under `/api/extreme/*` (probabilities, calibration curves, reliability diagrams, threshold evaluations, regime/lead-time/spatial breakdowns, alerts).
- **Frontend:** Interactive 10-section dashboard at `/extreme` with probability gauges, reliability diagrams, threshold risk matrices, and spatial heatmaps.
- **Tests:** 39 unit/integration tests passing (bringing cumulative backend suite to 260 tests, 0 failures).
- **Results:** Brier score: Rain 0.0821, Heavy 0.0465, Very Heavy 0.0152, Extremely Heavy 0.0051; ECE $< 0.05$ across all thresholds; 100% monotonicity enforcement.
- **Limitations:** Synthetic test set contains 0 heavy rainfall events ($>64.5$ mm), resulting in `SAMPLE-LIMITED` base rates (0.000) and uncomputable ROC-AUC/PR-AUC on unobserved positive classes until real observational archives are mounted.
- **Artifacts:** `data/models/extreme/extreme_prob_v1.0.0/`, `docs/reports/PHASE_7_PROJECT_REPORT.md`.
- **Next Dependency:** Provides calibrated exceedance probabilities to Phase 8 Operational Verification Engine.

### Phase 8 — Real-Data Integration & Operational Verification Readiness [COMPLETE]
- **Objective:** Construct the real-data integration layer and operational verification framework ready to consume real IMD/NCMRWF archives without breaking frozen models or fabricating data.
- **Implementation:**
  - `RealDataProvider` orchestrating NetCDF, GRIB/GRIB2, Parquet, and CSV adapters with safe fallback to `SyntheticDataProvider`.
  - Canonical `DatasetContract` schema (`observed_rainfall_mm`, `nwp_rainfall_mm`, spatiotemporal keys, metadata).
  - 13-point `MeteorologicalQualityControl` distinguishing unphysical corruptions (`PHYSICAL_INVALID`) from severe convective events (`EXTREME_BUT_VALID` $\ge 204.5$ mm). Missing target observations mapped to evaluation unavailable (never 0.0 mm).
  - `UnitNormalizer` with documented conversions (m $	o$ mm, kg/m² $	o$ mm, rate $	o$ accumulation, Pa, K) and audit trails.
  - `TemporalAlignmentEngine` supporting Day 1 through Day 5 lead-time valid-time synchronization; `SpatialAlignmentEngine` supporting bilinear/nearest-neighbor 0.25° grid alignment over India.
  - Extended `LeakageGuard` for real-data feature auditing (forbidding future observations, future/observed regimes, post-event variables).
  - `PipelineReplayer` orchestrating full 8-stage operational replay in 1.233s.
  - `OperationalModelRegistry` tracking Phase 4, Phase 5, Phase 6 (`ramp_v1.0.0`), and Phase 7 (`extreme_prob_v1.0.0`) with immutable freeze locks.
  - `OperationalReadinessEvaluator` defining 6 engineering readiness tiers (Levels 0–5). Current state: **Level 0 (Synthetic Demonstration)**.
  - `OperationalVerificationEngine` evaluating all 6 systems (Raw NWP, Mean Bias, Quantile Mapping, Global ML, RAMP MoE, RAMP + Extreme Prob) across continuous metrics (RMSE, MAE, Bias, Pearson $r$), threshold contingency (POD, FAR, CSI, ETS, FBIAS), probability metrics (Brier, BSS, ECE, MCE, PR-AUC), paired bootstrap (300 resamples), 7-regime stratification, Day 1–5 lead-time breakdown, and spatial grid.
  - `AuditTrailManager` persisting run manifests to `data/audit/runs/`.
- **Architecture:** Ingestion $	o$ Validation $	o$ Standardization $	o$ QC $	o$ Temporal Alignment $	o$ Spatial Regridding $	o$ Feature Contract $	o$ Phase 4 $	o$ Phase 5 $	o$ Phase 6 $	o$ Phase 7 $	o$ Operational Verification.
- **Data:** `SYNTHETIC_DEMO` mode active (`REAL_DATA_AVAILABLE = NO`). Explicitly reports required formats and variables when queried via CLI or API.
- **Models:** Frozen locks maintained for `ramp_v1.0.0` and `extreme_prob_v1.0.0`. New real-data models will use `_real` suffixes.
- **APIs:** 14 REST endpoints under `/api/operational/*` (status, data, data-quality, dataset, coverage, verification, threshold, regime, lead-time, spatial, calibration, leakage, models, readiness).
- **Frontend:** Comprehensive 15-section dashboard at `/operational` with prominent `SYNTHETIC DEMONSTRATION` banner, readiness ladder, 6-system benchmark matrix, bootstrap charts, and data quality inspection.
- **Tests:** 26 new unit tests in `backend/tests/unit/operational/test_phase8_suite.py`; **286 total backend tests passing, 0 failures**.
- **Results:** Operational readiness Level 0 confirmed; 8-stage pipeline replay verified; 6-system benchmark ladder and bootstrap evaluated; zero data leakage detected.
- **Limitations:** Real IMD/NCMRWF operational data archives are not yet mounted locally; extreme rainfall event metrics remain sample-limited on synthetic test partition.
- **Artifacts:** `data/manifests/dataset_manifest.json`, `data/models/operational_model_registry.json`, `data/audit/runs/`, `data_quality_report.json`, `DATA_QUALITY_REPORT.md`, `docs/reports/PHASE_8_PROJECT_REPORT.md`.
- **Next Dependency:** System is fully verified and ready for Phase 9.

### Phase 9 — Spatial Forecast Products & District Aggregation [COMPLETE]
- **Objective:** Transform grid-level RAMP post-processed forecasts into area-weighted administrative district and state spatial products, preserve localized convective hotspots, compute multi-scale neighborhood Fractions Skill Scores (FSS), generate GIS exports (GeoJSON/CSV/Parquet), expose 15 spatial REST APIs, and provide an interactive frontend spatial dashboard without fabricating real data.
- **Implementation:**
  - `ml/spatial/grid.py`: Canonical 0.25° grid model covering $6.5^\circ\text{N} - 38.5^\circ\text{N}$, $66.5^\circ\text{E} - 100.5^\circ\text{E}$ with spherical metric cell area calculation.
  - `ml/spatial/validation.py`: 10-point `SpatialValidator` enforcing bounded domain, spatiotemporal uniqueness on `(grid_id, valid_time, lead_time)`, strict probability monotonicity ($P(R \ge 0.1) \ge P(R \ge 64.5) \ge P(R \ge 115.6) \ge P(R \ge 204.5)$), and freezing checks.
  - `ml/spatial/boundaries.py`: `AdministrativeBoundaryProvider` normalizing boundary polygons into geographic EPSG:4326 for display and analytical Albers Equal Area Conic (EPSG:7755 parameters) for exact physical area calculation in $\text{km}^2$.
  - `ml/spatial/intersection.py`: `GridDistrictIntersectionEngine` computing polygon intersections, overlap fractions, and district coverage percentages via Shapely.
  - `ml/spatial/aggregation.py`: `DistrictAggregationEngine` executing area-weighted aggregation ($R_d = \sum w_i R_i / \sum w_i$), distribution quantiles (Min, Median, Mean, Max, P90, P95, P99), exceedance risk fractions, and localized convective hotspot identification.
  - `ml/spatial/risk.py`: Configurable rule-based `DistrictRiskClassifier` defining 5 engineering risk tiers (`NORMAL`, `WATCH`, `HIGH_RAINFALL`, `VERY_HIGH_RAINFALL`, `EXTREME_RAINFALL`) with transparent rule strings and probability criteria.
  - `ml/spatial/uncertainty.py`: `SpatialUncertaintyEngine` combining spatial variance, grid coverage penalty, and regime classification entropy.
  - `ml/spatial/products.py`: Strongly-typed dataclasses for district, state, and national spatial forecast products.
  - `ml/spatial/fss.py`: Multi-scale neighborhood `FractionsSkillScoreService` evaluating 5km, 25km, 50km, 100km, and 200km neighborhood windows against thresholds 0.1, 64.5, 115.6, and 204.5 mm. Returns `NOT_AVAILABLE` when observations are absent without fabrication.
  - `ml/spatial/export.py`: Open GIS data exporter generating GeoJSON, CSV, and Parquet products with complete provenance metadata in `data/spatial_exports/`.
  - `ml/spatial/registry.py`: `SpatialProductRegistry` managing cache invalidation keys and immutable run manifests in `data/audit/spatial/`.
- **APIs:** 15 REST endpoints under `backend/src/ramp/api/v1/spatial.py` (`/api/spatial/*`).
- **Frontend:** Interactive 18-section dashboard at `/spatial` with interactive SVG map, layer selectors (RAMP, NWP, Global ML, Difference, Probabilities, Regimes, Uncertainty, Coverage), district drawer, FSS inspection, and GIS downloads.
- **Tests:** 28 unit tests in `backend/tests/unit/spatial/test_phase9_suite.py`; **314 total backend tests passing, 0 failures**.
- **Results:** 21 districts across 11 states aggregated with full area-weighting; Nagpur extreme hotspot (206.52 mm, 17.04x peak) preserved; FSS evaluated at 5 spatial scales; GIS exports verified.
- **Limitations:** Data mode remains `SYNTHETIC_DEMO`. Administrative boundary set is a canonical demonstration catalog. Real operational IMD district warnings and real FSS scores are not claimed or fabricated.
- **Artifacts:** `docs/reports/PHASE_9_PROJECT_REPORT.md`, `data/spatial_exports/`, `data/audit/spatial/`.
- **Next Dependency:** System is fully verified and ready for Phase 10 (Scientific Verification & Explainability).

---

## 5. Current System Limitations & Real Data Status
1. **Real Training Data Availability:** Authoritative historical archives from IMD and NCMRWF have not yet been mounted in local storage. All current pipelines, classifiers, and diagnostic metrics operate under **`SYNTHETIC_DEMO`** mode.
2. **No Performance Fabrication:** System metrics (e.g. Accuracy = 94.2%, Macro F1 = 0.918, Bulk RMSE = 13.85 mm) are derived strictly from synthetic test partitions and are explicitly labeled **`SYNTHETIC DEMONSTRATION ONLY`**. They must not be cited as real atmospheric accuracy.
3. **High-Resolution Topography:** Fine-scale digital elevation model (DEM) rasters are currently approximated via spatial corridors pending GeoTIFF raster integration.

---

## 6. Future Phases & Roadmap

| Phase | Milestone | Scope | Target Deliverables |
|---|---|---|---|
| **Phase 5** | Baseline Post-Processing | Benchmark models | **COMPLETE:** Raw NWP, Mean Bias, Quantile Mapping, Global ML |
| **Phase 6** | RAMP Mixture-of-Experts | Core post-processor | **COMPLETE:** 7 specialized regime experts + soft gating formula |
| **Phase 7** | Extreme Probabilistic Engine | Heavy precipitation risks | **COMPLETE:** Calibrated exceedance probabilities (64.5, 115.6, 204.5 mm) |
| **Phase 8** | Real-Data Integration & Operational Verification | Verification readiness | **COMPLETE:** Multi-provider data layer, 13-point QC, alignment, 6-system benchmark, /operational dashboard |
| **Phase 9** | Spatial & District Forecasts | User products | **COMPLETE:** Spatial grid, district area-weighting, hotspots, FSS, GIS exports, 15 APIs, /spatial dashboard |
| **Phase 10** | Scientific Verification & Explainability | Meteorological metrics & jury demo | *NEXT:* Comprehensive WMO metrics, SHAP attributions, synoptic case replays |

---

## 7. Master Reproduction Commands
```bash
# 1. Activate Environment & Run Full Test Suite (314 Tests, 0 Failures)
python -m pytest backend/tests/ -v

# 2. Phase 9 Spatial Products & District Aggregation
python -m ml.spatial inspect
python -m ml.spatial validate
python -m ml.spatial aggregate
python -m ml.spatial benchmark
python -m ml.spatial fss
python -m ml.spatial export
python -m ml.spatial report
python -m ml.spatial pipeline

# 2. Phase 7 Extreme Probability Engine
python -m ml.extreme train
python -m ml.extreme verify
python -m ml.extreme calibrate

# 3. Phase 8 Operational Readiness & Verification Engine
python -m ml.data readiness
python -m ml.pipeline replay
python -m ml.operational readiness
python -m ml.operational benchmark
python -m ml.operational verify
python -m ml.operational report

# 2. Re-train Weather Regime Classifier & Calibrate
python -m ml.regimes.train

# 3. Train & Evaluate Baseline Models (Phase 5 Frozen Ladder)
python -m ml.baselines train
python -m ml.baselines benchmark

# 4. Train, Verify & Benchmark RAMP Mixture-of-Experts (Phase 6)
python -m ml.ramp train
python -m ml.ramp verify
python -m ml.ramp benchmark
python -m ml.ramp ablation
python -m ml.ramp inspect

# 5. Compile and Build Frontend Production Bundle
cd frontend
npm run build

# 6. Launch Production API & Dashboard
# Terminal 1: Backend
uvicorn ramp.main:app --host 0.0.0.0 --port 8000
# Terminal 2: Frontend
npm run dev
```
