# ARCHITECTURE — RAMP
## Regime-Aware Mixture-of-Experts Post-Processor
**SIH26080 | NCMRWF / Ministry of Earth Sciences**

---

## 1. High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA INGESTION LAYER                         │
│                                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌───────────┐  │
│  │ NCMRWF NCUM  │ │ NCMRWF NEPS  │ │  NOAA GFS/   │ │   IMD     │  │
│  │  Adapter     │ │  Adapter     │ │  GEFS Adapter│ │  Obs Adap.│  │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └─────┬─────┘  │
│         └────────────────┴────────────────┴───────────────┘         │
│                                    │                                 │
│                    ┌───────────────▼───────────────┐                │
│                    │  NWPForecastBundle (xarray DS) │                │
│                    └───────────────────────────────┘                │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                     DATA HARMONISATION                               │
│  Grid alignment · Time alignment · Unit normalisation · QC flags    │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                     FEATURE ENGINEERING                              │
│                                                                     │
│  Atmospheric: u/v wind shear, PWAT, CAPE, vorticity, OLR anomaly   │
│  Physics:     Monsoon Hadley index, LP system proximity             │
│               Orographic lift index, WD jet index                   │
│  Terrain:     DEM elevation, slope, aspect, coastal distance        │
│  Climatology: Daily climatological anomaly (rainfall, wind)         │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                     REGIME CLASSIFIER                                │
│                                                                     │
│  Model:   LightGBM / XGBoost ensemble                               │
│  Input:   Feature vector (see above)                                │
│  Output:  P(regime | features) — 7-dim probability vector           │
│           [Active, Break, Depression, Coastal,                      │
│            Orographic, WesternDisturbance, Transition]              │
│  Calibration: Isotonic regression per regime                        │
│  Constraint:  sum(P) == 1.0 (softmax normalised)                    │
└──────────┬──────────────────┬──────────────────────────────────────-┘
           │  regime_probs    │
┌──────────▼──────────────────▼────────────────────────────────────────┐
│                  RAMP MIXTURE-OF-EXPERTS ENGINE                      │
│                                                                      │
│  ┌───────────┐ ┌─────────┐ ┌───────────┐ ┌─────────┐ ┌───────────┐ │
│  │  Expert   │ │ Expert  │ │  Expert   │ │ Expert  │ │  Expert   │ │
│  │  Active   │ │  Break  │ │ Depressn  │ │ Coastal │ │ Orograph  │ │
│  └─────┬─────┘ └────┬────┘ └─────┬─────┘ └────┬────┘ └─────┬─────┘ │
│        │            │            │             │            │        │
│  ┌─────┴─────┐ ┌────┴────┐                                           │
│  │ Expert WD │ │ Expert  │     Soft Blending Gate                    │
│  │ (Western  │ │ Trans.  │                                           │
│  │ Disturb.) │ │ /Other  │     corrected(x) =                       │
│  └─────┬─────┘ └────┬────┘       Sum_r [ p_r * Expert_r(x_nwp) ]   │
│        └────────────┘                                                │
│                  │                                                   │
│          blended_correction                                          │
└──────────────────┬───────────────────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────────────────┐
│               EXTREME RAINFALL PROBABILITY ENGINE                    │
│                                                                      │
│  Threshold calibrators (logistic regression + isotonic):            │
│    P(R >= 64.5  mm/24h)  — Heavy                                    │
│    P(R >= 115.6 mm/24h)  — Very Heavy                               │
│    P(R >= 204.5 mm/24h)  — Extremely Heavy                          │
│                                                                      │
│  Input: blended_correction + regime_probs + NWP spread              │
└──────────────────┬───────────────────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────────────────┐
│                  SPATIAL POST-PROCESSING                             │
│                                                                      │
│  FSS-optimal neighbourhood smoothing                                │
│  Regridding (bilinear / conservative)                               │
│  Grid forecast product (NetCDF)                                     │
│  District aggregation (GeoPandas area-weighted mean)                │
└──────────────────┬───────────────────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────────────────┐
│                    VERIFICATION ENGINE                               │
│                                                                      │
│  Observation source: IMD Gridded Rainfall (0.25 deg)                │
│  Metrics: RMSE, CSI, POD, FAR, ETS, FSS                            │
│  Baselines: Raw NWP, Mean-Bias, Quantile Map, Global ML             │
│  Output: JSON verification report, HTML dashboard feed              │
└──────────────────┬───────────────────────────────────────────────────┘
                   │
     ┌─────────────┴──────────────┐
     │                            │
┌────▼──────┐              ┌──────▼────────────────────────────────────┐
│ REST API  │              │           REACT DASHBOARD                 │
│ FastAPI   │              │                                           │
│ /v1/      │◄─────────────│  MapLibre: India rainfall map             │
│  forecast │              │  MapLibre: Regime probability overlay     │
│  regime   │              │  Recharts: Regime prob. radar chart       │
│  extreme  │              │  Recharts: Verification skill bar chart   │
│  verify   │              │  Recharts: Time series (NWP vs RAMP)     │
│  district │              │  Table: District forecast (sortable)      │
└───────────┘              │  Panel: Extreme rainfall probabilities    │
                           │  Panel: SHAP feature importance           │
                           │  Banner: DEMO/SYNTHETIC mode indicator    │
                           └───────────────────────────────────────────┘
```

---

## 2. Monorepo Structure

```
SIH26080/
├── ARCHITECTURE.md
├── DATA_CONTRACTS.md
├── DEVELOPMENT_PLAN.md
├── MODEL_CARD.md
├── TODO.md
├── README.md
├── .gitignore
├── docker-compose.yml
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── cd.yml
│
├── backend/                          # Python / FastAPI service
│   ├── pyproject.toml
│   ├── alembic/                      # DB migrations
│   ├── src/
│   │   └── ramp/
│   │       ├── __init__.py
│   │       ├── main.py               # FastAPI app entry point
│   │       ├── config.py             # Pydantic Settings
│   │       │
│   │       ├── ingestion/            # Phase 1 — Data Layer
│   │       │   ├── __init__.py
│   │       │   ├── base.py           # Abstract NWPAdapter interface
│   │       │   ├── ncum_adapter.py
│   │       │   ├── neps_adapter.py
│   │       │   ├── gfs_adapter.py
│   │       │   ├── gefs_adapter.py
│   │       │   ├── imd_obs_adapter.py
│   │       │   └── synthetic_generator.py  # DEMO mode — labelled
│   │       │
│   │       ├── harmonisation/        # Phase 1
│   │       │   ├── __init__.py
│   │       │   ├── grid_aligner.py
│   │       │   ├── time_aligner.py
│   │       │   ├── unit_converter.py
│   │       │   └── qc_flags.py
│   │       │
│   │       ├── features/             # Phase 2
│   │       │   ├── __init__.py
│   │       │   ├── atmospheric.py    # PWAT, CAPE, wind shear, vort.
│   │       │   ├── physics.py        # Hadley index, LP proximity
│   │       │   ├── terrain.py        # DEM, slope, coastal dist.
│   │       │   └── climatology.py    # Anomaly calculation
│   │       │
│   │       ├── regime/               # Phase 2
│   │       │   ├── __init__.py
│   │       │   ├── classifier.py     # LightGBM soft classifier
│   │       │   ├── calibrator.py     # Isotonic regression
│   │       │   ├── trainer.py        # MLflow training pipeline
│   │       │   └── schemas.py        # RegimeProbVector Pydantic model
│   │       │
│   │       ├── moe/                  # Phase 3 — Core RAMP engine
│   │       │   ├── __init__.py
│   │       │   ├── base_expert.py    # Abstract Expert interface
│   │       │   ├── experts/
│   │       │   │   ├── active.py
│   │       │   │   ├── break_.py
│   │       │   │   ├── depression.py
│   │       │   │   ├── coastal.py
│   │       │   │   ├── orographic.py
│   │       │   │   ├── western_disturbance.py
│   │       │   │   └── transition.py
│   │       │   ├── blender.py        # Soft mixture-of-experts gate
│   │       │   ├── baselines.py      # RawNWP, MeanBias, QuantileMap, GlobalML
│   │       │   └── trainer.py
│   │       │
│   │       ├── extreme/              # Phase 4
│   │       │   ├── __init__.py
│   │       │   ├── probability_engine.py
│   │       │   └── calibration.py
│   │       │
│   │       ├── spatial/              # Phase 5
│   │       │   ├── __init__.py
│   │       │   ├── smoothing.py      # FSS neighbourhood
│   │       │   ├── regridder.py      # Rasterio regridding
│   │       │   └── district.py       # GeoPandas aggregation
│   │       │
│   │       ├── verification/         # Phase 6
│   │       │   ├── __init__.py
│   │       │   ├── metrics.py        # RMSE, CSI, POD, FAR, ETS, FSS
│   │       │   ├── report.py         # HTML + JSON report generator
│   │       │   └── scheduler.py      # Daily verification job
│   │       │
│   │       ├── api/                  # Phase 7
│   │       │   ├── __init__.py
│   │       │   ├── deps.py           # Dependency injection
│   │       │   ├── auth.py
│   │       │   └── v1/
│   │       │       ├── __init__.py
│   │       │       ├── router.py
│   │       │       ├── forecast.py
│   │       │       ├── regime.py
│   │       │       ├── extreme.py
│   │       │       ├── verification.py
│   │       │       └── district.py
│   │       │
│   │       └── db/
│   │           ├── __init__.py
│   │           ├── models.py         # SQLAlchemy ORM
│   │           └── session.py
│   │
│   └── tests/
│       ├── unit/
│       └── integration/
│
├── frontend/                         # Phase 8 — React app
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── components/
│       │   ├── layout/
│       │   ├── map/
│       │   │   ├── RainfallMap.tsx
│       │   │   └── RegimeOverlay.tsx
│       │   ├── charts/
│       │   │   ├── RegimeProbChart.tsx
│       │   │   ├── SkillScoreChart.tsx
│       │   │   └── TimeSeriesChart.tsx
│       │   ├── tables/
│       │   │   └── DistrictTable.tsx
│       │   ├── panels/
│       │   │   ├── ExtremeRainfallPanel.tsx
│       │   │   └── ExplainabilityPanel.tsx
│       │   └── DemoModeBanner.tsx
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── Verification.tsx
│       │   └── About.tsx
│       ├── api/
│       │   └── rampClient.ts
│       ├── store/
│       │   └── rampStore.ts
│       └── types/
│           └── ramp.d.ts
│
├── ml/                               # Standalone training scripts
│   ├── train_regime_classifier.py
│   ├── train_ramp_experts.py
│   ├── train_extreme_engine.py
│   └── evaluate_baselines.py
│
├── data/
│   ├── raw/                          # Gitignored — NWP/obs files
│   ├── processed/                    # Gitignored — harmonised data
│   ├── shapefiles/                   # India district ADM2 shapefiles
│   └── dem/                          # SRTM30 DEM tiles
│
├── configs/
│   ├── dev.env
│   ├── prod.env
│   └── model_config.yaml             # Hyperparameter registry
│
├── mlflow/
│   └── mlartifacts/                  # Gitignored
│
└── infra/
    ├── docker/
    │   ├── backend.Dockerfile
    │   └── frontend.Dockerfile
    ├── nginx/
    │   └── nginx.conf
    └── monitoring/
        ├── prometheus.yml
        └── grafana/
```

---

## 3. Component Interfaces

### 3.1 NWP Data Adapter Interface

```python
class NWPAdapter(ABC):
    """Provider-independent interface for NWP forecast ingestion."""

    @abstractmethod
    def load_forecast(
        self,
        init_time: datetime,
        lead_hours: list[int],
        variables: list[str],
        bbox: BoundingBox,
    ) -> xr.Dataset:
        """
        Returns an xarray Dataset with dimensions (time, lat, lon).
        All variables in SI units. CRS: WGS84 EPSG:4326.
        """

    @abstractmethod
    def get_data_mode(self) -> DataMode:
        """Returns DataMode.REAL or DataMode.SYNTHETIC_DEMO."""
```

### 3.2 Regime Classifier Interface

```python
class RegimeClassifier(ABC):
    """Always outputs a probability vector, never a hard label."""

    @abstractmethod
    def predict_proba(self, features: np.ndarray) -> RegimeProbVector:
        """
        Returns RegimeProbVector where all 7 probabilities sum to 1.0.
        Shape: (n_gridpoints, 7) or (7,) for single point.
        """
```

### 3.3 Expert Interface

```python
class RainfallCorrectionExpert(ABC):
    """One expert per weather regime."""

    regime: WeatherRegime

    @abstractmethod
    def correct(self, nwp_rainfall: np.ndarray, features: np.ndarray) -> np.ndarray:
        """Returns bias-corrected rainfall in mm/24h."""
```

### 3.4 RAMP Blender

```python
class RAMPBlender:
    """
    Soft Mixture-of-Experts gate.
    corrected(x) = sum_r [ p_r(x) * Expert_r(x) ]
    """
    def blend(
        self,
        regime_probs: RegimeProbVector,   # shape (n_grid, 7)
        expert_outputs: ExpertOutputs,    # shape (7, n_grid)
    ) -> np.ndarray:                      # shape (n_grid,)
        return (regime_probs * expert_outputs.T).sum(axis=1)
```

---

## 4. Database Schema (PostgreSQL)

```sql
-- NWP Forecast Run metadata
CREATE TABLE forecast_run (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider        VARCHAR(32) NOT NULL,       -- ncum | neps | gfs | gefs
    init_time       TIMESTAMPTZ NOT NULL,
    lead_hours      INTEGER[] NOT NULL,
    bbox            GEOMETRY(Polygon, 4326),
    data_mode       VARCHAR(16) NOT NULL,       -- REAL | SYNTHETIC_DEMO
    ingested_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(provider, init_time)
);

-- Grid-level RAMP output
CREATE TABLE ramp_grid_forecast (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID REFERENCES forecast_run(id),
    valid_time      TIMESTAMPTZ NOT NULL,
    lat             FLOAT NOT NULL,
    lon             FLOAT NOT NULL,
    nwp_rain_mm     FLOAT,
    ramp_rain_mm    FLOAT,
    p_heavy         FLOAT,        -- P(R >= 64.5)
    p_very_heavy    FLOAT,        -- P(R >= 115.6)
    p_extreme       FLOAT,        -- P(R >= 204.5)
    UNIQUE(run_id, valid_time, lat, lon)
);

-- Regime probabilities per grid point
CREATE TABLE regime_probabilities (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id                  UUID REFERENCES forecast_run(id),
    valid_time              TIMESTAMPTZ NOT NULL,
    lat                     FLOAT NOT NULL,
    lon                     FLOAT NOT NULL,
    p_active                FLOAT NOT NULL CHECK(p_active BETWEEN 0 AND 1),
    p_break                 FLOAT NOT NULL CHECK(p_break BETWEEN 0 AND 1),
    p_depression            FLOAT NOT NULL CHECK(p_depression BETWEEN 0 AND 1),
    p_coastal               FLOAT NOT NULL CHECK(p_coastal BETWEEN 0 AND 1),
    p_orographic            FLOAT NOT NULL CHECK(p_orographic BETWEEN 0 AND 1),
    p_western_disturbance   FLOAT NOT NULL CHECK(p_western_disturbance BETWEEN 0 AND 1),
    p_transition            FLOAT NOT NULL CHECK(p_transition BETWEEN 0 AND 1),
    -- Constraint: probabilities sum to 1.0 (within float tolerance)
    UNIQUE(run_id, valid_time, lat, lon)
);

-- District-level aggregated forecast
CREATE TABLE district_forecast (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID REFERENCES forecast_run(id),
    valid_time      TIMESTAMPTZ NOT NULL,
    state_name      VARCHAR(64) NOT NULL,
    district_name   VARCHAR(64) NOT NULL,
    district_code   VARCHAR(16),
    nwp_rain_mm     FLOAT,
    ramp_rain_mm    FLOAT,
    p_heavy         FLOAT,
    p_very_heavy    FLOAT,
    p_extreme       FLOAT,
    dominant_regime VARCHAR(32),
    UNIQUE(run_id, valid_time, district_code)
);

-- Verification results
CREATE TABLE verification_result (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID REFERENCES forecast_run(id),
    valid_time      TIMESTAMPTZ NOT NULL,
    model_name      VARCHAR(32) NOT NULL,     -- raw_nwp | mean_bias | qmap | global_ml | ramp
    threshold_mm    FLOAT,                    -- NULL for continuous metrics
    rmse            FLOAT,
    csi             FLOAT,
    pod             FLOAT,
    far             FLOAT,
    ets             FLOAT,
    fss             FLOAT,
    fss_scale_km    FLOAT,
    computed_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(run_id, valid_time, model_name, threshold_mm)
);

-- Spatial indices
CREATE INDEX ON ramp_grid_forecast USING GIST(ST_MakePoint(lon, lat));
CREATE INDEX ON regime_probabilities USING GIST(ST_MakePoint(lon, lat));
CREATE INDEX ON ramp_grid_forecast(run_id, valid_time);
```

---

## 5. API Endpoints Summary

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/health` | Health check |
| POST | `/v1/forecast/ingest` | Ingest NWP forecast run |
| GET | `/v1/forecast/{run_id}` | Get forecast metadata |
| GET | `/v1/regime/{run_id}` | Get regime probabilities grid |
| GET | `/v1/ramp/{run_id}` | Get RAMP corrected forecast grid |
| GET | `/v1/extreme/{run_id}` | Get extreme rainfall probabilities |
| GET | `/v1/district/{run_id}` | Get district-level forecasts |
| GET | `/v1/verification/{run_id}` | Get verification scores |
| GET | `/v1/verification/summary` | Cross-run skill summary |
| POST | `/v1/observations/ingest` | Ingest IMD observations |

---

## 6. Weather Regime Definitions

| ID | Regime | Key Indicators |
|----|--------|----------------|
| 0 | Active Monsoon | Strong cross-equatorial flow, widespread rainfall, negative OLR anomaly |
| 1 | Break Monsoon | Dry mainland, rainfall confined to Himalayan foothills & coasts, positive OLR |
| 2 | Monsoon Low/Depression | Closed circulation < 1000 hPa, LP system over Bay of Bengal/land |
| 3 | Coastal Rainfall | Onshore wind, high humidity, coastal convergence |
| 4 | Orographic Rainfall | Windward-slope moisture uplift, terrain index > threshold |
| 5 | Western Disturbance | Upper-level westerly trough, active in pre/post-monsoon |
| 6 | Transition/Other | None of the above; mixed conditions |

---

## 7. Data Flow — Single Forecast Cycle

```
T=0h: NWP init time
  │
  ├─► Ingestion adapter reads NetCDF/GRIB2
  ├─► Harmonisation: align to 0.25° grid, convert units
  ├─► Feature engineering: compute 30+ features
  ├─► Regime classifier: output p_regime[7] per grid point
  ├─► Each of 7 experts: apply correction to NWP rainfall
  ├─► Blender: weighted sum → RAMP corrected rainfall
  ├─► Extreme engine: compute P(heavy/very heavy/extreme)
  ├─► Spatial: FSS smoothing, district aggregation
  ├─► Store all outputs to PostgreSQL
  └─► Verification (when obs available, T+24h)
```

---

## 8. Demo/Synthetic Mode

When real NWP data is unavailable:

1. `SyntheticDataGenerator` creates physically-plausible fields.
2. **Every** API response includes `"data_mode": "SYNTHETIC_DEMO"`.
3. Dashboard shows a persistent orange banner: **"⚠ DEMO MODE — Synthetic data only"**.
4. Verification scores are computed on synthetic obs vs synthetic forecasts — explicitly labelled.
5. This mode is activated via environment variable `RAMP_DATA_MODE=SYNTHETIC_DEMO`.

---

## 9. Phase 3 — Training Dataset Builder & Feature Engineering

Implemented in Phase 3:
- **Feature Engineering Engine (`ml.dataset.features.FeatureEngineer`):**
  - Atmospheric derivations: `wind_speed_850` ($\sqrt{u^2 + v^2}$), `wind_direction_850` (meteorological $0^\circ$–$360^\circ$ convention).
  - Cyclic periodic encodings: `day_of_year_sin/cos`, `valid_hour_sin/cos`.
  - Regional monsoon indicators: `pre_monsoon`, `monsoon`, `post_monsoon`, `winter`.
  - Predictor spatial neighborhood stats: $3 \times 3$ mean, max, std on NWP rainfall.
- **Canonical Target Builder (`ml.dataset.targets.TargetBuilder`):**
  - Continuous rainfall (`observed_rainfall_mm`).
  - Binary event threshold ($\ge 0.1$ mm/24h).
  - IMD heavy rainfall alert categories ($\ge 64.5$ mm, $\ge 115.6$ mm, $\ge 204.5$ mm).
  - Zero-leakage anomaly relative to train-fitted daily climatology.
- **Leakage Protection Guard (`ml.dataset.leakage_guard.LeakageGuard`):**
  - Enforces 10 scientific invariants; fails loudly (`DataLeakageError`) upon violation.
- **Chronological Data Splitter (`ml.dataset.split.ChronologicalSplitter`):**
  - Strict time-ordered splits with 24-hour purge embargo buffers.
- **Dataset Versioning & Manifests (`ml.dataset.versioning.DatasetVersionManager`):**
  - Exports Parquet, JSON manifests, and `DATASET_CARD.md`.
