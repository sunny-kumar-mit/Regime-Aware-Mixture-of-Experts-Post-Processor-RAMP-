# RAMP — Regime-Aware Mixture-of-Experts Post-Processor

> **SIH26080** | Smart India Hackathon 2026  
> **Organisation:** Ministry of Earth Sciences (MoES), Government of India  
> **Department:** National Centre for Medium Range Weather Forecasting (NCMRWF)  
> **Ground Truth Reference:** India Meteorological Department (IMD), Pune

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4-3178c6.svg)](https://www.typescriptlang.org/)
[![MinIO / S3](https://img.shields.io/badge/Storage-MinIO%20S3%20%2B%20Fallback-c72c48.svg)](https://min.io/)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ed.svg)](https://www.docker.com/)

---

## 1. Executive Summary & Problem Statement

Numerical Weather Prediction (NWP) models (such as the NCMRWF Unified Model **NCUM 12 km** and the National Ensemble Prediction System **NEPS 12 km**) exhibit systematic spatial displacement, orographic overestimation, and conditional intensity under-prediction during the Indian Summer Monsoon (JJAS). 

Traditional post-processing approaches—such as stationary quantile mapping or monolithic global linear regression—fail because bias structures vary dynamically with synoptic monsoon regimes.

**RAMP (Regime-Aware Mixture-of-Experts Post-Processor)** introduces a meteorologically conditioned post-processing architecture:
1. Dynamically classifies the prevailing synoptic state into **7 distinct weather regimes** using a 23-variable atmospheric feature vector.
2. Generates **soft probability vectors** $\mathbf{p} \in \Delta^6$ ($\sum p_i = 1.0$), ensuring smooth, physically continuous transitions without boundary artifacts.
3. Routes predictions through specialized **Mixture-of-Experts (MoE)** regressors weighted by regime probabilities.
4. Calibrates extreme rainfall probabilities against **IMD operational warning thresholds** (Heavy $\ge 64.5$ mm, Very Heavy $\ge 115.6$ mm, Extremely Heavy $\ge 204.5$ mm).
5. Provides enterprise operational governance with **14 cutover gates**, **single source of truth health telemetry**, and **Two-Stage Operator/Supervisor signoff**.

---

## 2. Scientific Architecture & Flow

```mermaid
graph TD
    subgraph Data Layer
        A1[NCMRWF NCUM / NEPS Streams\nGRIB2 / NetCDF4] --> B[Meteorological Data Vault\nMinIO S3 / Local Disk Fallback]
        A2[IMD Gridded Rainfall Truth\n0.25° Daily Binary .grd / NC4] --> B
    end

    subgraph Feature & Regime Pipeline
        B --> C[0.25° Grid Harmonisation\nDomain: 6.5°N–38.5°N, 66.5°E–100.5°E]
        C --> D[23 Atmospheric Feature Extractor\nLLJ u850, MTMI, Shear, CAPE, DEM, Divergence]
        D --> E[Weather Regime Classifier\n7-Class Soft Probabilities p ∈ Δ⁶]
    end

    subgraph Mixture of Experts & Calibration
        E --> F[Mixture-of-Experts Combiner\nR̂ = Σᵢ pᵢ · Expertᵢ(x)]
        F --> G[Extreme Rainfall Calibrator\nP(R ≥ 64.5 mm), P(R ≥ 115.6 mm), P(R ≥ 204.5 mm)]
    end

    subgraph Operational Control & UI
        G --> H[FastAPI Backend\n22 Modular Routers / Port 8000]
        H <--> I[React + Vite Frontend\nOperational Dashboards / Port 5173]
        H --> J[Operational State Engine\n14 Cutover Gates & 2-Stage Signoff]
    end
```

### The 7 Monsoon Weather Regimes
| Regime | Name | Meteorological Characteristics | Key Predictors |
| :---: | :--- | :--- | :--- |
| **R1** | **Active Monsoon** | Strong cross-equatorial flow, low-level jet over Arabian Sea, active trough | $u_{850} > 15\text{ m/s}$, negative OLR, high MTMI |
| **R2** | **Break Monsoon** | Trough shifts north to Himalayan foothills, suppressed central India rain | $u_{850} < 8\text{ m/s}$, high pressure anomaly, low PWV |
| **R3** | **Monsoon Low / Depression** | Synoptic vortex over Bay of Bengal moving WNW inland | Strong low-level vorticity, negative SLP anomaly, shear |
| **R4** | **Coastal Rainfall** | Strong offshore trough along Konkan/Goa, heavy maritime precipitation | High low-level humidity ($q_{925}$), coastal wind convergence |
| **R5** | **Orographic Rainfall** | Moisture barrier ascent over Western Ghats & Northeast hills | Topographic slope $\times$ perpendicular wind, high CAPE |
| **R6** | **Western Disturbance** | Mid-latitude upper-tropospheric trough interacting with monsoon flow | 200 hPa westerly jet anomaly, geopotential height dip |
| **R7** | **Transition / Other** | Onset/withdrawal periods, weak synoptic gradient, unstratified flow | Moderate shear, variable wind direction |

---

## 3. Repository Structure

```
SIH26080/
├── backend/                        # FastAPI Python backend
│   ├── src/ramp/
│   │   ├── api/                    # 22 Typed REST API Routers
│   │   │   ├── v1/
│   │   │   │   ├── forecast.py     # Operational forecast serving
│   │   │   │   ├── production.py   # Production telemetry & health probes
│   │   │   │   ├── acceptance.py   # Institutional scorecard & cutover state machine
│   │   │   │   ├── real_data.py    # Real Data Lab (discovery, download, conversion)
│   │   │   │   ├── operational.py  # Phase 8 operational verification
│   │   │   │   ├── regime.py       # Weather regimes & classifier outputs
│   │   │   │   ├── extreme.py      # IMD extreme warning calibrator
│   │   │   │   ├── models.py       # Model registry & frozen hashes
│   │   │   │   └── ...             # Data, spatial, scientific, operations routers
│   │   │   └── router.py           # Core system info & health router
│   │   ├── config.py               # Pydantic BaseSettings environment config
│   │   ├── logger.py               # Structured logging system
│   │   └── main.py                 # FastAPI application root & middleware
│   ├── tests/                      # Unit, integration & operational test suites
│   ├── pyproject.toml              # Dependencies & build configuration
│   └── Dockerfile                  # Production container definition
├── frontend/                       # Vite + React 18 + TypeScript frontend
│   ├── src/
│   │   ├── components/             # Reusable UI widgets & MapLibre layers
│   │   │   ├── layout/Shell.tsx    # Responsive navigation shell with live alerts
│   │   │   └── ...
│   │   ├── pages/                  # Operational dashboards & interfaces
│   │   │   ├── OperationalForecast.tsx # (/forecast) Interactive map & regime controls
│   │   │   ├── ProductionStatus.tsx    # (/production) Health probes & 14-gate cutover
│   │   │   ├── Acceptance.tsx          # (/acceptance) Institutional scorecard (Cats A-L)
│   │   │   ├── RealDataLab.tsx         # (/real-data) Ingestion, download & conversions
│   │   │   ├── RealDataCases.tsx       # (/forecast/cases) Extreme monsoon event cases
│   │   │   ├── WeatherRegimes.tsx      # (/regime) Soft classification & diagnostics
│   │   │   ├── ExtremeRainfall.tsx     # (/extreme) IMD warning thresholds
│   │   │   ├── ModelRegistry.tsx       # (/models) SHA-256 frozen weight hashes
│   │   │   ├── Explainability.tsx      # (/explainability) Feature attribution & XAI
│   │   │   ├── JuryDemo.tsx            # (/jury-demo) Guided evaluation showcase
│   │   │   └── ...
│   │   ├── api/                    # Type-safe client service modules
│   │   └── types/                  # TypeScript interface contracts
│   ├── package.json
│   └── vite.config.ts
├── ml/                             # Post-processing ML engine
│   ├── acceptance/                 # Verification criteria, cycles, mounts & engine
│   ├── data/                       # Discovery, manifest, quality control & providers
│   ├── extreme/                    # Extreme value calibration (GEV, Quantiles)
│   ├── operations/                 # OperationalStateService (Single Source of Truth)
│   ├── postprocessing/             # MoE combiner & expert models
│   ├── production/                 # Monitoring, SLA, emergency circuit breaker & audit
│   ├── real_data/                  # MinIO vault, adapters (NCUM, NEPS, IMD), converters
│   ├── regimes/                    # Regime definitions, feature engineering & classifier
│   └── training/                   # Model registry, pipelines & experiment tracker
├── config/                         # Configuration templates & YAML specs
├── data/                           # Data directory (raw, real vault, processed)
├── docker-compose.yml              # Multi-service stack (FastAPI, React, MinIO, Postgres)
├── run_guide.md                    # Comprehensive execution and troubleshooting guide
└── README.md                       # Main project overview (this file)
```

---

## 4. Frontend Application Dashboards

| Route | Dashboard Name | Operational Function |
| :--- | :--- | :--- |
| `/forecast` | **Operational Forecast** | Primary forecaster cockpit. Interactive MapLibre rainfall map, Day 1–5 lead-time slider, dynamic regime probability bars, and IMD warning badges. |
| `/production` | **Production Status** | Single source of truth for runtime reliability. 8 modular service health probes (DB, MinIO, MoE Weights, Inference, Streams), Service Detail Drawer, 14-Gate Cutover Engine, live telemetry, and audited Emergency Stop. |
| `/acceptance` | **Institutional Acceptance** | Institutional compliance matrix covering Categories A–L (24 verified checks), multi-cycle verification against IMD ground truth, 8-stage staging runner, and Two-Stage Operator/Supervisor cutover state machine. |
| `/real-data` | **Real Data Activation Lab** | Official NCMRWF/IMD source catalog, download manager, format converter (GRIB2/GRD to NetCDF4), SHA-256 checksum validator, and anti-leakage temporal pairing. |
| `/forecast/cases`| **Extreme Event Cases** | Deep dives into historical benchmark storms (e.g. Cyclone Biparjoy June 2023, North India Deluge July 2023) with raw vs RAMP corrected comparison. |
| `/regime` | **Weather Regimes** | Real-time 7-class soft probability vector display, regime centroids, transitions, and climatological diagnostics. |
| `/extreme` | **Extreme Rainfall** | Calibrated probability maps for IMD Yellow (64.5 mm), Orange (115.6 mm), and Red (204.5 mm) alert thresholds. |
| `/models` | **Model Registry** | Immutable model catalogue with SHA-256 weight hashes, hyperparameter cards, and training lineage. |
| `/explainability`| **Explainability & XAI** | Feature importance rankings, SHAP summary plots, and meteorological attribution of corrections. |
| `/jury-demo` | **Jury Evaluation** | Guided walk-through for institutional evaluation panels with step-by-step verification proofs. |

---

## 5. Quick Start Instructions

For in-depth operational setup and deployment details, see [run_guide.md](file:///d:/SIH26080/run_guide.md).

### Step 1: Environment Setup
Verify that `.env` exists in the repository root:
```ini
APP_NAME=RAMP-MoES-NCMRWF
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
RAMP_DATA_MODE=REAL_OPERATIONAL
STORAGE_MODE=MINIO
MINIO_ENDPOINT=http://localhost:9000
MINIO_BUCKET=ramp-meteorological-vault
RAMP_DATA_ROOT=D:/SIH26080/data
```

### Step 2: Start the Backend (FastAPI)
```powershell
cd d:\SIH26080
python -m uvicorn ramp.main:app --host 0.0.0.0 --port 8000 --reload
```
- **Live Health Endpoint**: `http://localhost:8000/api/health`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`

### Step 3: Start the Frontend (Vite + React)
```powershell
cd d:\SIH26080\frontend
npm install   # Required on initial clone
npm run dev
```
- **Web Application**: `http://localhost:5173`

### Step 4 (Optional): Start MinIO Object Storage
```bash
docker run -d --name ramp-minio \
  -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=admin" -e "MINIO_ROOT_PASSWORD=admin12345" \
  minio/minio server /data --console-address ":9001"
```
> **Fail-Safe Design**: If MinIO is not running, RAMP's pre-flight probe automatically switches to **`LOCAL_FALLBACK`** mode within 1.5 seconds, ensuring uninterrupted operation without crashes.

---

## 6. Operational Data Modes & Cutover Governance

RAMP enforces 3 mutually exclusive operational modes configured via `RAMP_DATA_MODE`:

1. **`SYNTHETIC_DEMO`**:
   - High-fidelity synthetic monsoon generation for UI demonstrations, fast local testing, and offline presentations without live internet dependencies.
2. **`REAL_DATA_EXPERIMENT`**:
   - Offline research mode. Uses genuine historical NCUM/NEPS NetCDF4 runs and IMD observations stored in the local vault to train, validate, and benchmark models with full provenance tracking.
3. **`REAL_OPERATIONAL`**:
   - Live stream integration mode. RAMP post-processes authoritative operational NWP feeds.
   - **Cutover Lock**: Production broadcast is `BLOCKED` until all **14 Cutover Gates** pass and the **Two-Stage Authorization** (Operator submission + Supervisor PIN signoff) is completed.

---

## 7. Institutional Acceptance & Cutover Gates

The **14 Operational Cutover Gates** evaluate readiness across 7 critical dimensions:

| Gate ID | Category | Requirement | Acceptance Criterion |
| :--- | :--- | :--- | :--- |
| `GATE-01` | Data | NCMRWF NCUM Stream Mount | Authoritative directory mounted & readable |
| `GATE-02` | Data | IMD Gridded Rainfall Mount | Verified 0.25° observation archive available |
| `GATE-03` | Integrity | Model Weights SHA-256 | Exact cryptographic match against frozen registry |
| `GATE-04` | Integrity | Feature Contract Verification | All 23 atmospheric predictors computed within physical bounds |
| `GATE-05` | Scientific | Multi-Scale FSS (Spatial Skill) | Fractions Skill Score $\ge 0.60$ for $\ge 35\text{ mm}$ at $25\text{ km}$ |
| `GATE-06` | Scientific | Extreme Value Calibration | Expected Calibration Error ($\text{ECE}$) $\le 0.10$ |
| `GATE-07` | Scientific | Bias Correction Integrity | RMSE improvement $> 15\%$ over raw NCUM baseline |
| `GATE-08` | Reliability | Ingestion Latency SLA | Complete pipeline execution $< 15\text{ min}$ for 5-day lead |
| `GATE-09` | Reliability | Database Connectivity | Sub-50ms ping, schema migrations fully applied |
| `GATE-10` | Reliability | Object Storage Vault | MinIO / Vault read, write, and delete health probe PASS |
| `GATE-11` | Security | Emergency Stop Circuit Breaker | Instant operator shutdown verified & audited |
| `GATE-12` | Security | Audit Trail Immutability | Append-only tamper-evident event logging active |
| `GATE-13` | Authorization | Stage 1: Operator Cutover Request | Lead Forecaster operational justification submitted |
| `GATE-14` | Authorization | Stage 2: Supervisor Authorization | MoES Shift Supervisor PIN authentication verified |

---

## 8. Verification & Automated Testing

```powershell
# Run the complete test suite
pytest tests/ -v

# Run acceptance engine verification tests
python -m pytest tests/test_acceptance_phase18.py -v

# Frontend lint & type check
cd frontend && npm run lint
```

---

## 9. Contacts & Institutional Credits

- **Project:** SIH26080 — Regime-Aware Mixture-of-Experts Post-Processor (RAMP)
- **Ministry:** Ministry of Earth Sciences (MoES), Government of India
- **Centre:** National Centre for Medium Range Weather Forecasting (NCMRWF), A-50, Sector 62, Noida, Uttar Pradesh 201309
- **Observational Partner:** India Meteorological Department (IMD), Climate Application and Research Center, Pune
