# RAMP — Regime-Aware Mixture-of-Experts Post-Processor

> **SIH26080** | Smart India Hackathon 2026  
> **Organisation:** Ministry of Earth Sciences (MoES)  
> **Department:** National Centre for Medium Range Weather Forecasting (NCMRWF)

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4-3178c6.svg)](https://www.typescriptlang.org/)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ed.svg)](https://www.docker.com/)

---

## 1. Overview & Objective

RAMP is an AI/ML **post-processing pipeline** specifically engineered to correct and calibrate Numerical Weather Prediction (NWP) rainfall forecasts across the Indian subcontinent.

Instead of applying a monolithic global correction or stationary quantile mapping, RAMP conditions non-linear bias adjustments on **7 meteorologically distinct monsoon weather regimes**:
1. **Active Monsoon**
2. **Break Monsoon**
3. **Monsoon Low / Depression**
4. **Coastal Rainfall**
5. **Orographic Rainfall**
6. **Western Disturbance**
7. **Transition / Other**

### Core Pipeline Flow

```
NWP Forecast (NCUM / NEPS / GFS)
    │
    ▼
┌──────────────────────────────────────────┐
│  0.25° Grid Harmonisation (India Domain) │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│  23 Atmospheric Feature Extractor        │
│  (LLJ u850, MTMI, Shear, CAPE, DEM)      │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│  Weather Regime Classifier (LightGBM)    │
│  7-Class Soft Probabilities p ∈ Δ⁶       │
└──────────────────┬───────────────────────┘
                   │  p = [p₁ … p₇],  Σpᵢ = 1.0
                   ▼
┌──────────────────────────────────────────┐
│  Mixture-of-Experts (MoE) Post-Processor │
│  R̂ = Σᵢ pᵢ · Expertᵢ(x)                  │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│  Extreme Rainfall Calibrator (Isotonic)  │
│  P(R ≥ 64.5 mm), P(R ≥ 115.6), P(R ≥ 204.5)│
└──────────────────┬───────────────────────┘
                   │
                   ▼
  District / Subdivision Post-Processed Forecasts
  + Verification vs IMD Gridded Observations
```

---

## 2. Repository Structure

```
SIH26080/
├── backend/               # FastAPI backend & ML post-processing service
│   ├── src/ramp/
│   │   ├── api/           # Typed endpoints & Pydantic contracts
│   │   ├── config.py      # BaseSettings configuration
│   │   ├── logger.py      # Structured JSON/text logging
│   │   ├── main.py        # FastAPI entrypoint, CORS, lifespan
│   │   ├── ingestion/     # Adapters for NCUM, NEPS, GFS, IMD
│   │   ├── harmonisation/ # 0.25° bilinear regridding
│   │   ├── features/      # 23-variable atmospheric feature engine
│   │   ├── regime/        # 7-class soft probability classifier
│   │   ├── moe/           # Mixture-of-Experts combiner & experts
│   │   ├── extreme/       # Isotonic extreme rainfall calibrator
│   │   ├── spatial/       # District aggregation & smoothing
│   │   └── verification/  # RMSE, CSI, POD, FAR, ETS, FSS scorers
│   ├── tests/             # Backend test suite (unit + integration)
│   ├── pyproject.toml     # Python dependencies & metadata
│   └── Dockerfile         # Production backend container definition
├── frontend/              # React 18 + Vite + TypeScript + Tailwind
│   ├── src/
│   │   ├── components/    # Responsive shell, layout & UI elements
│   │   ├── pages/         # 8 Operational pages
│   │   │   ├── Dashboard.tsx        # (/dashboard) Pipeline overview
│   │   │   ├── DataFeeds.tsx        # (/data) Feeds & 23-feature catalog
│   │   │   ├── WeatherRegimes.tsx   # (/regime) 7 Regimes & soft math
│   │   │   ├── ForecastCorrection.tsx # (/forecast) Grid staging
│   │   │   ├── ExtremeRainfall.tsx  # (/extreme) IMD Warning calibration
│   │   │   ├── Verification.tsx     # (/verification) Scores & metrics
│   │   │   ├── Explainability.tsx   # (/explainability) XAI & SHAP
│   │   │   └── About.tsx            # (/about) MoES/NCMRWF specs
│   │   ├── api/           # Type-safe API client
│   │   └── types/         # Typed frontend contracts
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile         # Multi-stage Nginx production container
├── config/                # Central hyperparameter & environment templates
│   ├── model_config.yaml  # Model registry & parameters
│   └── dev.env            # Development env template
├── scripts/               # Automation scripts (run_dev, run_tests, lint)
│   ├── run_dev.ps1 / .sh
│   └── run_tests.ps1 / .sh
├── tests/                 # Root integration tests
├── docs/                  # Architectural references & data contracts
├── data/                  # Input NWP and observation stores (raw/processed)
├── ml/                    # Offline training workflows
├── docker-compose.yml     # Multi-container orchestration (backend, frontend, postgres, redis)
└── .env.example           # Environment template
```

---

## 3. Local Setup Instructions

### Prerequisites
- **Python**: `≥ 3.11`
- **Node.js**: `≥ 20` and `npm ≥ 10`
- **Docker & Docker Compose** (Optional, for containerized run)

### Method A: Local Native Development

#### Step 1: Environment Setup
```bash
cp .env.example .env
```

#### Step 2: Backend Setup
```bash
cd backend
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

pip install -e ".[dev]"
```

Run the backend server:
```bash
uvicorn ramp.main:app --reload --host 0.0.0.0 --port 8000
```
- API Base: `http://localhost:8000`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`
- Health Endpoint: `http://localhost:8000/api/health`
- System Info: `http://localhost:8000/api/system/info`

#### Step 3: Frontend Setup
In a new terminal:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

### Method B: Docker Compose (Full Stack)

To run the complete production-grade stack (FastAPI Backend + React Frontend + PostgreSQL + Redis):

```bash
docker-compose up --build
```
- Frontend Dashboard: `http://localhost:3000` (or `http://localhost:5173`)
- Backend API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`

---

## 4. Automated Testing & Verification

Run tests and type checks across backend and frontend:

### Windows PowerShell:
```powershell
.\scripts\run_tests.ps1
```

### Linux / macOS:
```bash
chmod +x ./scripts/run_tests.sh
./scripts/run_tests.sh
```

### Manual Commands:
```bash
# Backend unit & integration tests
python -m pytest backend/tests tests/

# Frontend TypeScript type check
cd frontend && npm run lint
```

---

## 5. Scientific Integrity & Data Mode Policy

- **Soft Probabilities Guarantee**: The regime classifier outputs a 7-dimensional soft probability vector ($p_i \in [0, 1], \sum p_i = 1.0$), ensuring smooth and continuous expert mixture weighting without discrete switching discontinuities.
- **No Fabricated Data Policy**: Phase 1 establishes the production architecture, typed contracts, schemas, and UI shell. In accordance with SIH26080 guidelines, no synthetic ML scores or fake model accuracies are fabricated.
- **DataMode Propagation**: Any data tagged `SYNTHETIC_DEMO` is strictly indicated across all API responses and the frontend UI banner to ensure complete operational transparency.
