# TODO — RAMP Implementation Checklist
## SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts

> **Instructions:** Work through phases sequentially. Do not begin a phase until the previous
> phase's tests pass. Each checkbox maps to a distinct implementable unit.
>
> Legend: [ ] = not started | [x] = done | [~] = in progress | [!] = blocked

---

## Phase 0 — Foundation & Documentation
*Status: ✅ COMPLETE — all items done*

- [x] Inspect repository (empty slate confirmed)
- [x] Create `DEVELOPMENT_PLAN.md`
- [x] Create `ARCHITECTURE.md`
- [x] Create `DATA_CONTRACTS.md`
- [x] Create `MODEL_CARD.md`
- [x] Create `TODO.md`
- [x] Create `README.md` (project overview, quickstart, architecture summary)
- [x] Create `.gitignore` (Python, Node, NetCDF, GRIB2, MLflow artifacts, env files)
- [x] Create monorepo folder skeleton (33 dirs + 16 `__init__.py` stubs)
- [x] Create `configs/model_config.yaml` (hyperparameter registry — all model components)
- [x] Create `configs/dev.env` template (no secrets, `RAMP_DATA_MODE=SYNTHETIC_DEMO`)

---

## Phase 1 — Backend Skeleton & Data Layer

### 1.1 Project Setup & Foundation
- [x] Create `backend/pyproject.toml` (uv/pip-compatible, all deps pinned)
- [x] Set up `src/ramp/` package structure
- [x] Create `backend/src/ramp/config.py` — Pydantic Settings with env vars & CORS
- [x] Create `backend/src/ramp/logger.py` — Structured JSON/text logging
- [x] Create `backend/src/ramp/main.py` — FastAPI app shell with CORS and timing middleware
- [x] Implement `GET /api/health` and `GET /api/system/info` typed endpoints
- [x] Setup Frontend (React 18, TypeScript 5, Vite, Tailwind, Responsive Shell, Routing)
- [x] Create 8 initial pages (`/dashboard`, `/data`, `/regime`, `/forecast`, `/extreme`, `/verification`, `/explainability`, `/about`)
- [x] Create `Dockerfile` (Backend & Frontend) and `docker-compose.yml`
- [x] Create `.env.example` and update `README.md` with complete local setup guide
- [x] Pass all backend unit/integration tests and frontend lint/type checks

### 1.2 Abstract Interfaces
- [ ] Create `ingestion/base.py` — `NWPAdapter` abstract base class
- [ ] Create `ingestion/base.py` — `BoundingBox`, `DataMode` types
- [ ] Create `ingestion/base.py` — `NWPForecastBundle` dataclass wrapping xarray Dataset
- [ ] Enforce `get_data_mode()` abstract method on all adapters

### 1.3 Data Adapters
- [ ] Create `ingestion/ncum_adapter.py` — NCMRWF NCUM NetCDF4 reader
  - [ ] Handle NCUM variable name mapping (non-standard names)
  - [ ] Unit conversion (if needed)
  - [ ] QC: check required variables present
- [ ] Create `ingestion/neps_adapter.py` — NCMRWF NEPS NetCDF4 reader
  - [ ] Handle ensemble dimension if present
- [ ] Create `ingestion/gfs_adapter.py` — NOAA GFS GRIB2 reader (cfgrib)
  - [ ] Handle GRIB2 shortName/typeOfLevel mapping
- [ ] Create `ingestion/gefs_adapter.py` — NOAA GEFS GRIB2 reader
  - [ ] Handle ensemble member dimension
- [ ] Create `ingestion/imd_obs_adapter.py` — IMD gridded rainfall NetCDF reader
  - [ ] Parse QC flags (0=good, 1=suspect, 2=missing)
  - [ ] Return `data_mode=REAL`

### 1.4 Synthetic Demo Generator (CRITICAL)
- [ ] Create `ingestion/synthetic_generator.py`
  - [ ] Generate physically-plausible precipitation field (Gamma distribution + spatial correlation)
  - [ ] Generate realistic u850, v850, u200, v200, MSLP, PWAT fields
  - [ ] Set `data_mode=SYNTHETIC_DEMO` on ALL outputs — no exceptions
  - [ ] Add prominent docstring warning against operational use
  - [ ] Unit test: assert `data_mode == SYNTHETIC_DEMO`

### 1.5 Data Harmonisation
- [ ] Create `harmonisation/grid_aligner.py`
  - [ ] Bilinear interpolation to target 0.25° grid using xarray interp
  - [ ] Conservative regridding option via Rasterio
- [ ] Create `harmonisation/time_aligner.py`
  - [ ] Align obs and forecast to same valid_time
- [ ] Create `harmonisation/unit_converter.py`
  - [ ] Precipitation: kg/m²/s → mm/24h
  - [ ] Temperature: K → K (no-op, keep K)
  - [ ] Pressure: Pa (keep Pa)
- [ ] Create `harmonisation/qc_flags.py`
  - [ ] Apply obs QC mask (exclude suspect/missing from verification)

### 1.6 Database
- [ ] Create `db/session.py` — SQLAlchemy async session factory
- [ ] Create `db/models.py` — ORM for all 5 tables (from ARCHITECTURE.md §4)
- [ ] Create `alembic/` setup for migrations
- [ ] Write initial migration: create all tables
- [ ] Test DB connection in `GET /v1/health`

### 1.7 MLflow Bootstrap
- [ ] Create `configs/dev.env` with `MLFLOW_TRACKING_URI=http://localhost:5000`
- [ ] Bootstrap MLflow experiment: "ramp-regime-classifier"
- [ ] Bootstrap MLflow experiment: "ramp-moe-experts"
- [ ] Bootstrap MLflow experiment: "ramp-extreme-engine"

### 1.8 Tests — Phase 1
- [ ] `tests/unit/test_ncum_adapter.py` — mock file, assert variables present
- [ ] `tests/unit/test_gfs_adapter.py` — mock GRIB2, assert mapping
- [ ] `tests/unit/test_synthetic_generator.py` — assert SYNTHETIC_DEMO flag
- [ ] `tests/unit/test_grid_aligner.py` — assert output grid matches 0.25°
- [ ] `tests/unit/test_unit_converter.py` — assert precipitation units
- [ ] `tests/integration/test_health.py` — HTTP 200 from health endpoint

---

## Phase 2 — Feature Engineering & Regime Classifier

### 2.1 Atmospheric Features
- [ ] Create `features/atmospheric.py`
  - [ ] `compute_wind_shear(u850, v850, u200, v200)` → magnitude in m/s
  - [ ] `compute_vorticity(u850, v850, lat, lon)` → relative vorticity at 850 hPa
  - [ ] `compute_olr_anomaly(olr, climatology)` → anomaly (W/m²)
  - [ ] Fallback: fill missing CAPE/OLR with 0.0 (documented, not silent)

### 2.2 Physics-Inspired Features
- [ ] Create `features/physics.py`
  - [ ] `compute_hadley_index(v850, lat)` → Monsoon Hadley circulation index
  - [ ] `compute_lp_proximity(mslp, lat, lon)` → Distance to nearest LP centre (km)
  - [ ] `compute_orographic_lift(u850, v850, dem_slope, dem_aspect)` → lift index
  - [ ] `compute_wd_jet_index(u200, lat)` → Western Disturbance jet index

### 2.3 Terrain Features
- [ ] Create `features/terrain.py`
  - [ ] `load_dem(dem_path)` → xarray DataArray at 0.25°
  - [ ] `compute_slope_aspect(dem)` → slope (degrees), aspect (degrees)
  - [ ] `compute_coastal_distance(lat, lon)` → km to nearest coastline

### 2.4 Climatology Features
- [ ] Create `features/climatology.py`
  - [ ] `load_climatology(variable, doy)` → daily climatological mean field
  - [ ] `compute_anomaly(field, climatology)` → anomaly field
  - [ ] Seasonal encoding: month_sin, month_cos, doy_sin, doy_cos

### 2.5 Feature Pipeline
- [ ] Create `features/__init__.py` — `FeaturePipeline` class
  - [ ] Input: `NWPForecastBundle` → Output: feature matrix (n_grid × 23)
  - [ ] Handles missing fields with documented fallbacks
  - [ ] Outputs feature names list for SHAP explainability

### 2.6 Regime Classifier
- [ ] Create `regime/classifier.py`
  - [ ] `RegimeClassifier` abstract base class
  - [ ] `LightGBMRegimeClassifier` implementation
  - [ ] `predict_proba()` method — returns `RegimeProbVector`, never a hard label
  - [ ] Softmax normalisation: ensures probabilities sum to 1.0
  - [ ] Validate output with `RegimeProbVector` Pydantic model on every call
- [ ] Create `regime/calibrator.py`
  - [ ] Isotonic regression wrapper per regime
  - [ ] Brier score evaluation
- [ ] Create `regime/schemas.py`
  - [ ] `RegimeProbVector` Pydantic model (with sum-to-1 validator)
  - [ ] `WeatherRegime` Enum
- [ ] Create `regime/trainer.py`
  - [ ] MLflow-integrated training pipeline
  - [ ] Time-blocked cross-validation
  - [ ] Log: log-loss, calibration curves, Brier score per regime

### 2.7 Training Script
- [ ] Create `ml/train_regime_classifier.py`
  - [ ] CLI: `python train_regime_classifier.py --data-path <path> --mlflow-uri <uri>`
  - [ ] Saves model artifact to MLflow registry

### 2.8 Tests — Phase 2
- [ ] `tests/unit/test_atmospheric_features.py` — wind shear, vorticity
- [ ] `tests/unit/test_physics_features.py` — LP proximity, Hadley index
- [ ] `tests/unit/test_regime_classifier.py` — assert output is RegimeProbVector
- [ ] `tests/unit/test_regime_sum.py` — assert probs always sum to 1.0 (property test)
- [ ] `tests/unit/test_calibrator.py` — Brier score < 1.0

---

## Phase 3 — RAMP Mixture-of-Experts Engine

### 3.1 Base Expert
- [ ] Create `moe/base_expert.py`
  - [ ] `RainfallCorrectionExpert` abstract base class
  - [ ] Abstract `correct(nwp_rainfall, features)` → corrected rainfall (mm/24h)
  - [ ] `regime` attribute (WeatherRegime enum)
  - [ ] Non-negativity enforcement on output (rainfall >= 0)

### 3.2 Regime-Specific Experts
- [ ] Create `moe/experts/active.py` — ActiveMonsoonExpert
- [ ] Create `moe/experts/break_.py` — BreakMonsoonExpert
- [ ] Create `moe/experts/depression.py` — DepressionExpert
- [ ] Create `moe/experts/coastal.py` — CoastalExpert
- [ ] Create `moe/experts/orographic.py` — OrographicExpert
- [ ] Create `moe/experts/western_disturbance.py` — WesternDisturbanceExpert
- [ ] Create `moe/experts/transition.py` — TransitionExpert
- [ ] Each expert: LightGBM with 30-feature input (23 + 7 regime probs)
- [ ] Each expert: `correct()` returns non-negative corrected rainfall

### 3.3 RAMP Blender (Core Algorithm)
- [ ] Create `moe/blender.py`
  - [ ] `RAMPBlender.blend(regime_probs, expert_outputs)` → np.ndarray
  - [ ] Formula: `corrected = Σ p_r × Expert_r(NWP)` — vectorised einsum
  - [ ] Assertion: blended output >= 0 everywhere
  - [ ] Returns metadata: per-expert contributions (for explainability)

### 3.4 Baseline Models
- [ ] Create `moe/baselines.py`
  - [ ] `RawNWPBaseline` — identity transformation
  - [ ] `MeanBiasBaseline` — subtract long-term mean bias
  - [ ] `QuantileMapBaseline` — CDF-matching correction
  - [ ] `GlobalMLBaseline` — single LightGBM (regime-unaware)
  - [ ] All baselines: same interface as `RainfallCorrectionExpert`

### 3.5 RAMP Expert Training
- [ ] Create `moe/trainer.py`
  - [ ] Stratified training: for each regime, filter training data by dominant regime
  - [ ] MLflow logging per expert: RMSE, training samples, hyperparams
  - [ ] Save each expert as separate MLflow model artifact
- [ ] Create `ml/train_ramp_experts.py` — CLI training script
- [ ] Create `ml/evaluate_baselines.py` — CLI evaluation script

### 3.6 Tests — Phase 3
- [ ] `tests/unit/test_blender.py` — weights sum correct, output non-negative
- [ ] `tests/unit/test_experts.py` — each expert returns non-negative array
- [ ] `tests/unit/test_baselines.py` — RawNWP is identity transformation
- [ ] `tests/integration/test_ramp_pipeline.py` — end-to-end synthetic run

---

## Phase 4 — Extreme Rainfall Probability Engine

### 4.1 Probability Estimators
- [ ] Create `extreme/probability_engine.py`
  - [ ] `ExtremeRainfallEngine` class
  - [ ] 3 logistic regression models (one per threshold)
  - [ ] Inputs: blended rainfall + regime probs + NWP spread (if available)
  - [ ] Output: `p_heavy`, `p_very_heavy`, `p_extreme` each in [0, 1]
- [ ] Create `extreme/calibration.py`
  - [ ] Isotonic regression calibration per threshold
  - [ ] `ReliabilityDiagram` generator

### 4.2 Training Script
- [ ] Create `ml/train_extreme_engine.py`
  - [ ] CLI: train all 3 threshold models
  - [ ] MLflow logging: Brier score, BSS, reliability diagram artifact
  - [ ] Validate: calibration curves not degenerate

### 4.3 Tests — Phase 4
- [ ] `tests/unit/test_extreme_engine.py` — all outputs in [0, 1]
- [ ] `tests/unit/test_extreme_thresholds.py` — P(extreme) <= P(very heavy) <= P(heavy)
- [ ] `tests/unit/test_reliability.py` — reliability diagram generates without error

---

## Phase 5 — Spatial Post-Processing & District Aggregation

### 5.1 Neighbourhood Smoothing
- [ ] Create `spatial/smoothing.py`
  - [ ] FSS-optimal neighbourhood smoother
  - [ ] Configurable radius (km)
  - [ ] Apply only to probability fields, not point rainfall

### 5.2 Regridding
- [ ] Create `spatial/regridder.py`
  - [ ] Bilinear regridder (xarray interp)
  - [ ] Conservative regridder (Rasterio)
  - [ ] Configurable target grid

### 5.3 District Aggregation
- [ ] Create `spatial/district.py`
  - [ ] Load India ADM2 shapefiles (GeoPandas)
  - [ ] Area-weighted mean rainfall per district (rasterstats or manual)
  - [ ] Propagate `data_mode` to district output
  - [ ] Identify dominant regime per district (argmax of area-weighted regime probs)
  - [ ] Output: `DistrictForecast` list

### 5.4 Data
- [ ] Download/include India ADM2 shapefiles in `data/shapefiles/`
- [ ] Download/include SRTM30 DEM for India in `data/dem/`

### 5.5 Tests — Phase 5
- [ ] `tests/unit/test_smoothing.py` — output same shape as input
- [ ] `tests/unit/test_district.py` — 766 districts covered, no NaN districts
- [ ] `tests/unit/test_regridder.py` — output matches target grid spec

---

## Phase 6 — Verification Engine

### 6.1 Core Metrics
- [ ] Create `verification/metrics.py`
  - [ ] `compute_rmse(fcst, obs, mask=None)` — gridded and district
  - [ ] `compute_csi(fcst, obs, threshold)` — requires binarisation
  - [ ] `compute_pod(fcst, obs, threshold)`
  - [ ] `compute_far(fcst, obs, threshold)`
  - [ ] `compute_ets(fcst, obs, threshold)` — equitable threat score
  - [ ] `compute_fss(fcst, obs, threshold, scale_km)` — fractions skill score
  - [ ] All functions: validate obs is real (data_mode=REAL) before scoring
  - [ ] All functions: raise `ValueError` if obs has SYNTHETIC_DEMO flag

### 6.2 Verification Pipeline
- [ ] Create `verification/report.py`
  - [ ] `VerificationReporter` — runs all metrics, all thresholds, all models
  - [ ] Generates `VerificationReport` Pydantic object
  - [ ] Serialises to JSON
  - [ ] Generates HTML summary report
  - [ ] Attaches `data_mode` to every report

### 6.3 Scheduler
- [ ] Create `verification/scheduler.py`
  - [ ] Background task: run verification 24h after each forecast init_time
  - [ ] Celery task or APScheduler

### 6.4 Tests — Phase 6
- [ ] `tests/unit/test_metrics.py` — known-answer tests for RMSE, CSI, POD, FAR, ETS, FSS
  - [ ] Perfect forecast: CSI=1, POD=1, FAR=0, ETS=1, FSS=1, RMSE=0
  - [ ] Climatology forecast: ETS~=0
- [ ] `tests/unit/test_verification_synthetic_guard.py` — assert ValueError on SYNTHETIC_DEMO obs
- [ ] `tests/integration/test_verification_pipeline.py` — end-to-end with synthetic data (labelled)

---

## Phase 7 — REST API (FastAPI)

### 7.1 API Structure
- [ ] Create `api/v1/router.py` — aggregate all sub-routers
- [ ] Create `api/deps.py` — DB session, MLflow client injection
- [ ] Create `api/auth.py` — API key middleware

### 7.2 Endpoints
- [ ] `GET /v1/health` — health check (DB ping, mode)
- [ ] `POST /v1/forecast/ingest` — accept NWP run, trigger RAMP pipeline
- [ ] `GET /v1/forecast/{run_id}` — metadata + data_mode
- [ ] `GET /v1/regime/{run_id}?valid_time=&lat=&lon=` — regime probs at point or grid
- [ ] `GET /v1/ramp/{run_id}?valid_time=` — corrected forecast grid (GeoJSON or NetCDF)
- [ ] `GET /v1/extreme/{run_id}?valid_time=` — extreme probability grid
- [ ] `GET /v1/district/{run_id}?valid_time=&state=` — district forecasts
- [ ] `GET /v1/verification/{run_id}` — verification report
- [ ] `GET /v1/verification/summary?n_runs=` — skill summary table
- [ ] `POST /v1/observations/ingest` — ingest IMD obs for verification

### 7.3 API Behaviour
- [ ] Every response: includes `data_mode` field
- [ ] `data_mode=SYNTHETIC_DEMO`: flag prominently in response header too (`X-Data-Mode`)
- [ ] Pagination for large grid responses
- [ ] GeoJSON output for map consumption
- [ ] NetCDF download endpoint for bulk data

### 7.4 Tests — Phase 7
- [ ] `tests/integration/test_api_health.py`
- [ ] `tests/integration/test_api_ingest.py` — POST with synthetic data
- [ ] `tests/integration/test_api_regime.py` — verify prob vector in response
- [ ] `tests/integration/test_api_ramp.py` — verify corrected > 0, data_mode present
- [ ] `tests/integration/test_api_verification.py` — verify report structure

---

## Phase 8 — React Dashboard

### 8.1 Setup
- [ ] Scaffold Vite + React + TypeScript app in `frontend/`
- [ ] Install: Tailwind CSS, MapLibre GL JS, Recharts, React Router, Zustand
- [ ] Create `frontend/src/types/ramp.d.ts` — TypeScript types from DATA_CONTRACTS.md
- [ ] Create `frontend/src/api/rampClient.ts` — typed API client
- [ ] Create `frontend/src/store/rampStore.ts` — Zustand global state

### 8.2 Layout & Common
- [ ] `components/layout/Sidebar.tsx` — navigation
- [ ] `components/layout/TopBar.tsx` — init time selector, data mode badge
- [ ] `components/DemoModeBanner.tsx` — orange persistent banner when SYNTHETIC_DEMO

### 8.3 Maps
- [ ] `components/map/RainfallMap.tsx`
  - [ ] MapLibre India base map
  - [ ] Raw NWP vs RAMP side-by-side toggle
  - [ ] Rainfall choropleth (colour scale: white → light blue → dark blue → red)
  - [ ] District boundary overlay
  - [ ] Click district → show district detail panel
- [ ] `components/map/RegimeOverlay.tsx`
  - [ ] Regime probability overlay (dominant regime colour)
  - [ ] Toggle per-regime probability layer

### 8.4 Charts
- [ ] `components/charts/RegimeProbChart.tsx`
  - [ ] Recharts RadarChart or BarChart of 7 regime probabilities
  - [ ] Shows selected grid point's probabilities
- [ ] `components/charts/SkillScoreChart.tsx`
  - [ ] Grouped bar chart: RMSE/CSI/POD/FAR/ETS/FSS per model
  - [ ] 5 model groups (raw, mean-bias, qmap, global-ml, ramp)
- [ ] `components/charts/TimeSeriesChart.tsx`
  - [ ] Line chart: NWP vs RAMP vs Obs (when available) over time

### 8.5 Panels & Tables
- [ ] `components/panels/ExtremeRainfallPanel.tsx`
  - [ ] Traffic-light indicator: Heavy / Very Heavy / Extremely Heavy probabilities
  - [ ] Per-district probability bars
- [ ] `components/panels/ExplainabilityPanel.tsx`
  - [ ] SHAP bar chart (top 10 features contributing to RAMP correction)
  - [ ] Expert contribution pie chart (regime blend weights)
- [ ] `components/tables/DistrictTable.tsx`
  - [ ] Sortable, filterable district forecast table
  - [ ] Columns: State, District, NWP (mm), RAMP (mm), Heavy%, VHeavy%, Extreme%, Regime

### 8.6 Pages
- [ ] `pages/Dashboard.tsx` — main page: map + regime chart + extreme panel
- [ ] `pages/Verification.tsx` — skill score charts + tabular comparison
- [ ] `pages/About.tsx` — RAMP description, data mode explanation, SIH26080 reference

### 8.7 Tests — Phase 8
- [ ] Vitest component tests for DemoModeBanner — renders when SYNTHETIC_DEMO
- [ ] Vitest component tests for DistrictTable — sorts correctly
- [ ] Playwright E2E: dashboard loads, map renders, regime chart shows

---

## Phase 9 — Integration, Hardening & Deployment

### 9.1 Docker
- [ ] Create `infra/docker/backend.Dockerfile`
- [ ] Create `infra/docker/frontend.Dockerfile`
- [ ] Create `docker-compose.yml`
  - [ ] Services: `api`, `db` (PostgreSQL + PostGIS), `redis`, `celery`, `frontend`, `mlflow`
  - [ ] Health checks on all services
  - [ ] Volume mounts for `data/`, `mlflow/`

### 9.2 CI/CD
- [ ] Create `.github/workflows/ci.yml`
  - [ ] Backend: `pytest` + `ruff` + `mypy`
  - [ ] Frontend: `vitest` + `tsc --noEmit`
  - [ ] Fail on any test failure or type error
- [ ] Create `.github/workflows/cd.yml`
  - [ ] Build Docker images on tag push

### 9.3 Monitoring
- [ ] Create `infra/monitoring/prometheus.yml` — scrape FastAPI metrics
- [ ] Create Grafana dashboard JSON — latency, throughput, data_mode counts

### 9.4 Final Checks
- [ ] End-to-end synthetic demo run: ingest → regime → RAMP → extreme → district → verify
- [ ] Confirm demo mode banner appears throughout
- [ ] Confirm no verification scores reported without real observations
- [ ] Load test: 100 concurrent API requests
- [ ] Security: environment variable audit, no secrets in git
- [ ] Final `README.md` with quickstart, architecture summary, demo instructions
