# RAMP Master Technical Report — Smart India Hackathon 2026

**Project Title:** RAMP — Regime-Aware Mixture-of-Experts Post-Processor  
**Problem Statement:** SIH26080 — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts  
**Ministry / Organization:** Ministry of Earth Sciences (MoES)  
**Department:** National Centre for Medium Range Weather Forecasting (NCMRWF)  
**Current Milestone:** PHASE 19 COMPLETE (Real Data Activation Lab: Authoritative Data Acquisition, Format Ingestion, Canonical Feature Contract Mapping, Unit/Grid/Temporal Normalization, Isolated Real-Data Experiment Engine, First Real Inference Milestone, Lineage & Failure Diagnostics, and Real Data Lab Console)



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

# 5. Scientific Verification, Explainability & Jury Demo (Phase 10)
python -m ml.scientific verify
python -m ml.scientific report
python -m ml.scientific inspect

# 6. Operational Data Plane & Real Data Discovery (Phase 11)
python -c "from ramp.data_plane.discovery import DataDiscoveryService; print(DataDiscoveryService().get_availability_matrix())"

# 7. Compile and Build Frontend Production Bundle
cd frontend
npm run build

# 8. Launch Production API & Dashboard
# Terminal 1: Backend
uvicorn ramp.main:app --host 0.0.0.0 --port 8000 --reload
# Terminal 2: Frontend
npm run dev
```

---

## 11. Phase 10 — Scientific Verification, Explainability & Jury Demo
- **Verification Engine (`ml/scientific/`):** Full WMO standard verification across rain/no-rain (0.1 mm), heavy (64.5 mm), very heavy (115.6 mm), and extremely heavy (204.5 mm) thresholds.
- **Explainability (XAI):** Tree gain importances, feature group aggregation (NWP: 53.4%, Regime: 23.5%), gate entropy analysis, and Regime × Expert diagonal dominance matrix.
- **Jury Demo Interface:** 8-stage interactive pipeline tour, 5 synoptic case replays (Nagpur, Visakhapatnam, Kochi, Shimla, Jaipur), and 6-model benchmark comparison.
- **REST APIs:** 19 dedicated endpoints mounted under `/api/scientific/*`.

---

## 12. Phase 11 — Real Data Activation & Operational Data Plane
- **Source Priority Hierarchy:** Enforced PRIMARY (NCUM, NEPS, IMD Obs) > SECONDARY (GFS, GEFS) > DEMO (Synthetic Demo). Secondary proxies are never labeled as NCMRWF.
- **Operational Data Modes:** `REAL_OPERATIONAL`, `REAL_ARCHIVE`, `PUBLIC_PROXY`, `SYNTHETIC_DEMO`, `NOT_AVAILABLE`.
- **CF NetCDF/GRIB Ingestion Engine:** Automatic coordinate detection, latitude ordering normalization, longitude domain conversion, metadata-driven units, and SHA-256 checksum tracking.
- **Forecast Cycle Model & Arbitrary Lead Discovery:** Discovers 00, 06, 12, 18 UTC cycles without fabrication; derives arbitrary lead times dynamically from disk.
- **Native Resolution Preservation & Harmonisation:** NCMRWF ~0.12° (12km) native grid explicitly preserved and harmonised via mass-conserving interpolation to canonical 0.25° RAMP grid.
- **NWP + IMD Temporal Matcher:** Temporal alignment (`valid_time == obs_time`), anti-leakage guard, and strict prohibition of filling missing observations with 0 mm.
- **Live Status Header & UI:** 4 live badges (NCUM, NEPS, IMD, RAMP) and interactive Data Feeds operational desk with dynamic filters.
- **Handoff Contract:** ML models remain unfrozen/unaltered during Phase 11. Phase 12 will create the real paired training dataset.

---

## 13. Phase 12 — Real Paired Training Dataset & Operational UI Shell
- **Authoritative Real Dataset Pipeline (`ramp_dataset_real_v1.0.0`):** Created `ml/datasets/real/` pairing real NWP forecasts (NCUM, NEPS) with IMD 0.25° gridded observations using Phase 11 data plane.
- **Scientific Honesty Contract:** Truthfully reports `NOT_AVAILABLE` when real archives are unmounted in local raw storage, maintaining zero fabricated samples or statistics.
- **Strict Anti-Leakage Rule:** Forbidden observation variables blocked from predictor set X; target Y contains continuous rainfall + IMD threshold labels.
- **Chronological Split:** Sequential TRAIN (70%) / VAL (15%) / TEST (15%) partitions with zero temporal overlap.
- **Authoritative Manifests:** 10 metadata artifacts created in `ml/datasets/real/ramp_dataset_real_v1.0.0/`.
- **API Endpoints:** 8 dedicated endpoints under `/api/datasets/real/*`.
- **Redesigned Meteorological UI Shell (`Shell.tsx`):** Fixed 64px header with 3 primary zones (Brand | Center Context | Right System Status & Popover); organized sidebar into professional meteorological groups (Operations, RAMP AI, Verification, Data & System, Jury).
- **Test Suite Status:** 351 passed / 351 total tests across repository; production build verified.

---

## 14. Phase 13 — Production Model Retraining, Calibration & Model Registry
- **Automated ML Training Pipeline (`ml/training/`):** Full end-to-end retraining pipeline integrating dataset verification, feature contract enforcement, temporal split validation, baseline benchmarking, LightGBM models, soft MoE combination, extreme rainfall classifiers, and validation calibration.
- **Scientific Honesty Contract & Real Training Gate:** Since authoritative NCMRWF/IMD paired archives remain unmounted, real production retraining is explicitly **DEFERRED**. The pipeline was validated using deterministic synthetic fixtures, registering models strictly as `DEVELOPMENT` in `SYNTHETIC_DEMO` mode with zero fabricated scores.
- **Canonical Feature & Target Schemas:** Enforced `ramp_features_v1.0.0` (18 approved predictors, zero future-observation leakage) and `ramp_targets_v1.0.0` (continuous rainfall + 4 IMD thresholds).
- **Core Models Trained & Registered:**
  - `ramp_global_v2.0.0`: Global LightGBM precipitation regressor (non-negativity enforced).
  - `ramp_regime_v2.0.0`: 7-class synoptic weather regime classifier ($p_k(x) \in \mathbb{R}^7$).
  - `ramp_moe_v2.0.0`: Regime-Aware Mixture-of-Experts combining 7 specialized experts with soft gating.
  - `ramp_extreme_v2.0.0`: 4 binary classification heads for IMD thresholds ($\ge 0.1, 64.5, 115.6, 204.5$ mm) with monotonicity enforcement.
- **Validation-Fitted Calibration:** Isotonic regression and Platt scaling fitted exclusively on the validation partition (zero test contamination); reliability curve bin data and ECE/MCE calculated.
- **12 Mandatory Model Promotion Gates:** Automated gates (`DATASET_VALID`, `LEAKAGE_FREE`, `FEATURE_SCHEMA_VALID`, `TARGET_SCHEMA_VALID`, `TEMPORAL_SPLIT_VALID`, `TRAINING_COMPLETED`, `VALIDATION_COMPLETED`, `TEST_EVALUATION_COMPLETED`, `CALIBRATION_COMPLETED`, `MONOTONICITY_VALID`, `PROVENANCE_COMPLETE`, `CHECKSUM_VALID`). Synthetic models blocked from `PRODUCTION_READY`.
- **Production Model Registry (`ml/model_registry/`):** Immutable versioning with complete model artifacts, SHA-256 checksums, and comprehensive model cards (`MODEL_CARD.md`).
- **REST APIs & UI Integration:** 8 dedicated endpoints under `/api/models/*`, Model Registry page (`/models`), and Model Training orchestrator (`/training`).
- **Cumulative Testing:** 372 passed / 372 total tests; production frontend build verified.

---

## 15. Phase 14 — Operational Forecast Inference, Cycle Orchestration & NCMRWF-Style Forecast Products
- **16-Step Operational Inference Engine (`ml/inference/`):** Built complete production pipeline resolving forecast cycles, lead times, 11 input validation gates, 18-predictor feature contract (`ramp_features_v1.0.0`), model registry loading with SHA-256 checksum verification, RAMP MoE inference, calibrated extreme probabilities, monotonicity enforcement, spatial/district/state products, and immutable provenance logging.
- **Scientific Honesty Rule & Data Honesty Banner:** Accurately recognizes unmounted raw NCMRWF/IMD archives and operates strictly in `SYNTHETIC_DEMO` mode, permanently displaying the Rule 14-AB Data Honesty Banner across all views without fabricating operational data.
- **Dynamic Cycle & Lead Engine:** Discovers available cycles (`00 UTC`, `12 UTC`) and dynamic leads (+6h to +120h) from disk without fabricating unavailable timestamps or leads.
- **11 Automated Operational Gates:** Verifies upstream source, cycle, lead availability, variables, units, coordinates, feature schema, model presence, model checksum, calibration, and input QC before allowing forecast generation.
- **9 Canonical Meteorological Products:** Generates Rainfall Forecast, Correction Field, 4 Exceedance Probabilities (Rain $\ge 0.1$mm, Heavy $\ge 64.5$mm, Very Heavy $\ge 115.6$mm, Extreme $\ge 204.5$mm), Weather Regime Gating, Uncertainty Spread, and NWP Difference Field.
- **Spatial, District & State Synthesis:** Maps predictions to 0.25° grid, aggregates 21 representative districts across India with probability-first risk classification, generates 11 state syntheses, and national meteorological synopsis.
- **Deterministic Run IDs & Provenance:** Issues collision-free IDs (e.g. `RAMP_20260927_00UTC_T24`), creates `forecast_manifest.json` with input/model/output checksums, and records every run in `forecast_audit.jsonl`.
- **13 REST API Endpoints:** Mounted at `/api/forecast/*` with uniform response envelopes and multi-format exports (`json`, `csv`, `geojson`).
- **Operational Forecast Dashboard (`/forecast`):** Rebuilt primary operational workspace featuring interactive India Canvas map, Grid Point Inspector, horizontal timeline (+6h to +120h), representative district table with drill-down modal (NWP vs Global ML vs RAMP MoE without subjective winner labels), state syntheses, and operational status desk.
- **Test Suite & Verification:** 26/26 Phase 14 tests passed; 84/84 cumulative repository tests passed; browser subagent verified with 0 console errors.

---

## 16. Phase 15 — Operations Control Center
- **Automated Lifecycle Governance (`ml/operations/state.py`):** Implemented thread-safe 11-state operational automaton governing every forecast cycle from `INITIALIZING` to `CYCLE_COMPLETE` with full transition audit history.
- **Idempotent Background Scheduler (`ml/operations/scheduler.py`):** Background polling scheduler with SHA-256 job deduplication preventing double-execution of cycles.
- **8-Rule Real-Time Alert Engine (`ml/operations/alerts.py`):** Metric threshold evaluator covering failure rates, ECE drift, unauthorized activation, and data corruption.
- **Diagnostic Drift Monitor (`ml/operations/drift.py`):** Measures feature drift (KS-statistic), prediction drift, regime frequency drift, and ECE calibration drift across 4 IMD rainfall thresholds.
- **30-Point Production Readiness Engine (`ml/operations/production.py`):** Evaluates 6 categories and issues GO / CONDITIONAL_GO / NO_GO verdict with persistent scientific honesty disclaimer (`REAL_OPERATIONAL = BLOCKED` in synthetic demo mode).
- **15 Operational REST APIs & 5-Tab UI:** Mounted at `/api/operations/*` and rendered at `/operations`.
- **Testing:** 44/44 Phase 15 tests passed in 9.10 s.

---

## 17. Phase 16 — Real-Data Activation, Live Ingestion & Cutover
- **Authoritative Data Source Contracts (`ml/ingestion/sources.py`):** Established formal contracts for NCMRWF NCUM (deterministic 18 predictors), NCMRWF NEPS (23 ensemble members), and IMD Gridded Rainfall (0.25° ground truth).
- **Multi-Tier Meteorological Validation:** Built CF-1.8 NetCDF/GRIB metadata validation (`ml/ingestion/metadata.py`), SHA-256 integrity hashing (`ml/ingestion/integrity.py`), synoptic temporal validation (`ml/ingestion/temporal.py`), 17,673-cell spatial domain validation (`ml/ingestion/spatial.py`), strict unit normalization (`ml/ingestion/units.py`), and physical meteorological QC bounds (`ml/ingestion/qc.py`).
- **Zero-Future-Leakage Forecast/Obs Pairing (`ml/ingestion/pairing.py`):** Temporal and spatial matching with anti-leakage guarantee preventing observations from feeding inference features.
- **15-Gate Activation Engine & Two-Stage Human Approval (`ml/ingestion/activation.py`):** 5-stage lifecycle (`WAITING_DATA` -> `DISCOVERED` -> `VALIDATING` -> `DATA_ELIGIBLE` -> `OPERATIONAL_READY` -> `OPERATIONAL_ACTIVE`) with operator activation request and supervisor approval.
- **Safety Fallback Protection:** Real-mode transition protected; silent synthetic fallback impossible. Missing real files trips `REAL_DATA_LOST -> OPERATIONAL_DEGRADED -> FORECAST_GENERATION_BLOCKED` and fires CRITICAL alerts.
- **Scientific Honesty & Verification Baseline:** Authoritative data unmounted -> system strictly reports `WAITING_FOR_AUTHORITATIVE_DATA`, `REAL_OPERATIONAL = BLOCKED`, and `REAL_VERIFICATION = NOT_AVAILABLE`. All pipeline mechanics validated via explicitly labeled `TEST_FIXTURE` files.
- **14 REST API Endpoints & Operational UIs:** Dedicated consoles at `/activation`, `/data/ingestion`, `/forecast/verification`, and `/operations` Tab 6.
- **Performance & Testing:** 30/30 Phase 16 tests passed in 7.45 s; 157/157 full regression tests passed across Phases 11–16; measured total pipeline latency of 390.257 ms recorded in `real_data_performance.json`; 0 browser console errors.

---

## 18. Phase 17 — Production Deployment, Live Data Connectivity, Continuous Verification & Operational Reliability
- **Production Deployment Infrastructure (`deployment/`):** Multi-stage Docker containers with non-root security profiles (`Dockerfile`, `Dockerfile.frontend`, `docker-compose.prod.yml`), hardened Nginx reverse proxy with TLS 1.3, rate limiting, and security headers, systemd service units with auto-restart (`ramp-backend.service`, `ramp-worker.service`, `ramp-scheduler.service`), Prometheus metrics exporter with 24 operational alerts, and Grafana dashboard templates.
- **Production Configuration Engine (`ml/production/config.py`):** Environment-tier aware configuration schema (`AppEnvironment.PRODUCTION`) requiring cryptographically secure tokens, strict path existence, and explicit validation locks.
- **Live Provider Connectivity & SLA Deadlines (`ml/production/connectivity.py`):** Authoritative connectivity monitor for NCMRWF NCUM (03:30 / 15:30 UTC deadline), NEPS (04:15 / 16:15 UTC deadline), and IMD 0.25° Obs (08:30 UTC deadline). Circuit breakers trip on consecutive upstream timeouts; truthfully reports `WAITING_FOR_AUTHORITATIVE_DATA` when paths are unmounted.
- **Operational Cycle Automaton (`ml/production/cycle_engine.py`):** 7-stage state automaton governing operational forecast execution with per-cycle SHA-256 manifests, retry exponential backoff with jitter, and append-only audit trail.
- **Continuous Operational Verification (`ml/production/continuous_verification.py`):** Rolling 7-day, 30-day, and 90-day WMO verification engine calculating continuous (RMSE, MAE, Bias) and extreme categorical metrics (CSI, POD, FAR, ETS) against ground truth IMD observations with sample sufficiency guards (`MIN_SAMPLES = 10`).
- **14-Gate Production Cutover Engine (`ml/production/cutover.py`):** Automated cutover governance checking 14 prerequisite gates across Data, Security, Reliability, Verification, and Operations. Enforces two-stage dual-operator authorization (`OPERATOR_REQUEST` + `SUPERVISOR_APPROVAL`) with single-click emergency rollback.
- **Modular Health Probes (`ml/production/health_probes.py`):** 7 granular probes mounted at `/health/*` (Liveness, Readiness, Data Plane, Model Registry, Inference Engine, Operations Automaton, and Overall System Health).
- **Automated Backup & Disaster Recovery (`ml/production/backup.py`):** Incremental and full backup orchestration with SHA-256 validation, compression, retention policies, and dry-run restore tests.
- **Security Hardening (`ml/production/security.py`):** Role-Based Access Control (`VIEWER`, `OPERATOR`, `SUPERVISOR`, `ADMIN`), rate limiters, security audit logs, and audit trail hashing.
- **17 REST API Endpoints & 7 Health Probes:** Mounted at `/api/production/*` and `/health/*`.
- **Production Frontend Consoles:** `/production` (Production Cutover & System Status), `/operations/cycles` (Operational Cycles), `/operations/data-health` (Data Health & Connectivity), `/forecast/verification/history` (Verification History), and upgraded `/operations` Tab 6 (Live Operations).
- **Test Metrics & Browser Quality:** 35/35 Phase 17 unit and integration tests passed; 192/192 cumulative regression tests passed across Phases 11–17; 0 console errors across all 13 primary views.

---

## 19. Phase 18 — Real-Data Activation, Institutional Acceptance Testing, Multi-Cycle Scientific Verification & Operational Product Validation
- **Authoritative Data Source Discovery & Validation (`ml/acceptance/sources.py`, `validation.py`):** Implemented `AuthoritativeMountValidator`, `NCUMValidator` (18 predictors, bounds, no silent interpolation), `NEPSValidator` (23 members, spread, exceedance probabilities), `IMDValidator` (0.25° grid, `GROUND_TRUTH_ONLY`), and `RealDataIntegrityMatrix`. Discovers operational mount status without fabricating artificial files or scores (`NOT_AVAILABLE` / `WAITING_FOR_AUTHORITATIVE_DATA`).
- **Multi-Cycle Discovery & Anti-Leakage Pairing (`ml/acceptance/cycles.py`):** `MultiCycleDiscoveryEngine` audits synoptic cycles (00Z, 12Z) and continuous lead times (+6h to +120h), requiring $\ge 3$ cycles for cutover eligibility. Enforces zero-future-leakage observation pairing with cryptographic hash chaining.
- **Staging Environment Sandbox (`ml/acceptance/staging.py`):** Fully isolated staging engine executing complete 16-step operational inference on frozen models (`v2.0.0`) with `PUBLICATION = DISABLED`. Validates physical non-negativity, regime convexity, and probability monotonicity across all 5 IMD thresholds ($P(\ge 2.5) \ge P(\ge 15.6) \ge P(\ge 64.5) \ge P(\ge 115.6) \ge P(\ge 204.5)$).
- **Multi-Cycle Scientific Verification Suite (`ml/acceptance/verification.py`):** End-to-end WMO continuous (RMSE, MAE, Bias, $r$) and categorical (CSI, POD, FAR, ETS, Frequency Bias) verification engines, non-parametric 95% bootstrap confidence intervals (1,000 resamples), spatial error hotspot analysis, Fractions Skill Score (FSS) across 6 neighborhood radii (5–200 km), reliability diagrams with 10 bins, and Expected Calibration Error (ECE).
- **Objective 5-System Baseline Comparison:** Side-by-side comparison of Raw NCUM, Mean Bias Corrected, Quantile Mapping, Global ML, and RAMP MoE without subjective or promotional winner labels.
- **Operational Failure Taxonomy & Case Replay (`ml/acceptance/cases.py`):** Automated failure detection (`FALSE_EXTREME`, `MISSED_EXTREME`, `TIMING_OFFSET`, `SPATIAL_DISPLACEMENT`, `REGIME_MISCLASSIFICATION`) and synoptic case study replay service with honest `NO_REAL_CASE_STUDIES_AVAILABLE` fallback notice.
- **12-Category Institutional Acceptance Engine (`ml/acceptance/engine.py`):** Audits categories A through L and evaluates overall status (`CONDITIONAL_ACCEPTANCE_PENDING_DATA` while physical mounts are unmounted).
- **Two-Stage Human Cutover Safety:** Enforces Stage 1 Operator Activation Request followed by Stage 2 Supervisor Approval with cryptographic tokens; rejects synthetic promotion; single-click emergency rollback; append-only audit trail in `acceptance_audit.jsonl`.
- **15 Acceptance REST APIs:** Mounted at `/api/acceptance/*` covering status, sources, cycles, gates, staging inference, verification, baselines, spatial, FSS, calibration, cases, audit, and cutover.
- **Operational Frontend Consoles:** Acceptance Console (`/acceptance`) with 4 interactive tabs and Operational Case Replay (`/forecast/cases`), integrated into primary navigation.
- **Automated Testing & Browser Verification:** 35/35 Phase 18 unit and integration tests passed; 227/227 cumulative tests passed across Phases 11–18 with zero regressions; frontend compiled cleanly; browser verification verified 0 console errors across all tabs.

---

## 20. Phase 19 — Real Data Activation Lab: Authoritative Data Acquisition, Format Ingestion, Canonical Feature Contract Mapping, Unit/Grid/Temporal Normalization, Isolated Real-Data Experiment Engine, First Real Inference Milestone, Lineage & Failure Diagnostics, and Real Data Lab Console
- **Isolated Real-Data Workspace Architecture (`data/real/`):** Established directory structure (`incoming/`, `validated/`, `rejected/`, `observations/`, `forecasts/`, `manifests/`, `runs/`) ensuring raw source files are never overwritten and every file is registered with SHA-256 hash, provider, authority, format, and validation status.
- **Multi-Format Ingestion Adapters (`ml/real_data/adapters/`):** Implemented native readers for NetCDF4 (`xarray`, `netCDF4`), GRIB2 (`cfgrib`), CSV, and Parquet (`pyarrow`), preserving original meteorological payload bytes without synthetic conversion.
- **NCUM Real Data Adapter (`ml/real_data/adapters/ncum.py`):** Ingests deterministic NCUM files, checks synoptic cycles (00Z, 12Z) and forecast lead times (+6h to +120h), and maps variables to canonical names. Enforces strict predictor presence, raising `MISSING_REQUIRED_FEATURE` without artificial infilling or silent substitution.
- **NEPS Real Data Adapter (`ml/real_data/adapters/neps.py`):** Ingests ensemble forecasts, validates control member and 22 perturbed members (`mem00`..`mem22` / `ens00`..`ens22`), computes ensemble statistics, and reports `NEPS_FEATURES_INCOMPLETE` if members or fields are absent.
- **IMD Real Observation Adapter (`ml/real_data/adapters/imd.py`):** Reads genuine IMD 0.25° gridded daily rainfall data, validates the domain, enforces physical non-negativity ($R \ge 0$), and permanently tags all observations as `GROUND_TRUTH_ONLY` to prevent any data leakage into model features.
- **Public Product Ingestion Adapter (`ml/real_data/adapters/public_products.py`):** Ingests publicly accessible NCMRWF/IMD bulletins with strict separation (`PUBLIC_PRODUCT_ONLY -> RAMP_INFERENCE_NOT_POSSIBLE`) when raw 3D predictor fields are unavailable.
- **Feature Contract Mapping Engine (`ml/real_data/feature_mapper.py`):** Systematically validates incoming variables against `ramp_features_v1.0.0` (18 canonical predictors). Categorizes variables (`AVAILABLE`, `MISSING`, `EXTRA`, `MAPPED`, `UNIT_CONVERSION_REQUIRED`, `SPATIAL_REGRID_REQUIRED`, `TEMPORAL_ALIGNMENT_REQUIRED`, `UNSUPPORTED`) without silent mapping.
- **Physical Unit Normalization (`ml/real_data/unit_normalizer.py`):** Formally converts physical units (Kelvin $\to$ Celsius, Pa $\to$ hPa, kg m⁻² s⁻¹ $\to$ mm) and logs conversions to `data/manifests/transformation_manifest.json`.
- **Spatial Grid & Domain Validator (`ml/real_data/grid_validator.py`):** Verifies the 0.25° India grid ($129 \times 137$ points, $6.5^\circ$N–$38.5^\circ$N, $66.5^\circ$E–$100.5^\circ$E) and records explicit bilinear regridding parameters without nearest-neighbor smoothing.
- **Temporal Alignment & Anti-Leakage Pairing:** Validates `valid_time = initialization_time + lead_time` and pairs forecasts with observations using SHA-256 forecast and observation hashes at matching valid times with zero future leakage.
- **Real Data Experiment Engine (`ml/real_data/run_engine.py`):** Executes an 11-stage pipeline on strictly frozen models (`v2.0.0`), producing post-processed rainfall, correction fields, regime probabilities, extreme rainfall exceedance probabilities, district aggregations, and WMO verification metrics.
- **Dual Operating Mode Separation:** `REAL_DATA_EXPERIMENT` (Mode A) allows isolated experimentation on real files without triggering production cutover; `REAL_OPERATIONAL_ACTIVATION` (Mode B) strictly enforces all Phase 16–18 gates.
- **Granular 14-Stage Failure Diagnostics:** Pinpoints exact failure stages (from `IMPORT_FAILED` to `VERIFICATION_FAILED`) without generic error messages.
- **Data Lineage & Cryptographic Manifests:** Generates immutable `run_manifest.json` and human-readable experiment reports (`docs/real-data-runs/<run_id>.md`) for every run.
- **Remote Storage Connector Abstraction (`ml/real_data/remote_connector.py`):** Supports HTTPS, SFTP, and S3-compatible sources with environment variable credentials (`NCUM_DATA_ROOT`, `NEPS_DATA_ROOT`, `IMD_DATA_ROOT`).
- **14 REST API Endpoints:** Mounted under `/api/real-data/*` covering scan, import, sources, files, status, validate, reject, promote, runs, execute, mount-status, and diagnose.
- **Real Data Lab Console (`/real-data`):** Frontend console featuring 4 interactive tabs, Canvas-based India NWP vs RAMP comparison map, 7-step user workflow guide, and one-click real data diagnostic modal.
- **Automated Testing & Browser Verification:** 30/30 Phase 19 tests passed; 257/257 full cumulative regression tests passed across Phases 11–19 with zero regressions; frontend compiled cleanly; browser subagent verified all tabs with 0 console errors.

