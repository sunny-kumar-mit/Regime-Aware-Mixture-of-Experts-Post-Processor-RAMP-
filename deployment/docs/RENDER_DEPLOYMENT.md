# RAMP — Render Cloud Deployment Guide
**SIH26080 | Regime-Aware Mixture-of-Experts Post-Processor for Monsoon Rainfall Forecasts**  
**Ministry of Earth Sciences (MoES) / National Centre for Medium Range Weather Forecasting (NCMRWF)**

---

## 1. Architecture Overview

This deployment runs the **entire RAMP platform** as a **single Render Web Service** using the **repository root (`.`)** as the Docker build context.

```text
                           RENDER CLOUD
                                │
                                ▼
                     ┌───────────────────────┐
                     │   Render Web Service  │
                     │     Port: $PORT       │
                     │                       │
                     │     Nginx Reverse     │
                     │         Proxy         │
                     └──────────┬────────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
                ▼                               ▼
          React 18 SPA                    FastAPI Backend
       (Static HTML/JS/CSS)             (Uvicorn 127.0.0.1:8000)
        /                                /api/*
        /forecast                        /health/*
        /production                      /docs
        /acceptance                      /openapi.json
        /real-data                       /redoc
                │                               │
                └───────────────┬───────────────┘
                                │
                                ▼
                         ML Engine (ml/)
                 ├── Weather Regime Classifier
                 ├── Mixture-of-Experts Post-Processor
                 ├── Extreme Rainfall Calibrator (IMD)
                 └── Operational State & Cutover Service
```

### Key Architectural Characteristics
1. **Single Public URL**: All traffic (frontend pages, backend APIs, interactive Swagger docs, and health checks) is served on the exact same Render domain (e.g., `https://ramp-sih26080.onrender.com`).
2. **Zero CORS Pre-Flight Overhead**: In production, frontend fetch calls target same-origin relative endpoints (`/api/...`), completely eliminating CORS failure modes.
3. **Dynamic Port Binding**: Nginx dynamically binds to Render's allocated `$PORT` at runtime using `envsubst`, while Uvicorn runs securely on internal loopback (`127.0.0.1:8000`).
4. **Self-Contained Fallback**: If external MinIO or PostgreSQL instances are unconfigured, RAMP automatically activates its internal `LOCAL_FALLBACK` disk vault and SQLite3 metadata store in sub-second time.

---

## 2. Step-by-Step Render Deployment

### Method A: Blueprint Deployment (Recommended)
1. Push this repository to GitHub.
2. Log in to [Render Dashboard](https://dashboard.render.com/).
3. Click **New +** and select **Blueprint**.
4. Connect your GitHub repository.
5. Render will automatically detect `render.yaml` at the root and pre-configure the Web Service, Dockerfile, health check path, and environment variables.
6. Click **Apply**.

---

### Method B: Manual Web Service Setup
If creating the Web Service manually:

1. In Render Dashboard, click **New +** ➔ **Web Service**.
2. Connect your GitHub repository: `sunny-kumar-mit/Regime-Aware-Mixture-of-Experts-Post-Processor-RAMP-`.
3. Configure the service settings:
   - **Name**: `ramp-sih26080` (or your preferred name)
   - **Region**: Choose the closest region (e.g., Singapore, Frankfurt, Oregon)
   - **Branch**: `main`
   - **Root Directory**: `.` *(Leave blank or enter `.` — DO NOT set `backend` or `frontend`)*
   - **Runtime**: `Docker`
   - **Dockerfile Path**: `./Dockerfile`
   - **Docker Context**: `.`
   - **Instance Type**: `Starter` (0.5 CPU, 512 MB RAM) or `Standard` (1 CPU, 2 GB RAM recommended for heavy xarray operations)
4. Under **Advanced** ➔ **Health Check Path**:
   - Set to: `/health/live`
5. Configure Environment Variables (see Section 3 below).
6. Click **Create Web Service**.

---

## 3. Environment Variables Reference

| Variable | Recommended Render Value | Type | Description |
| :--- | :--- | :---: | :--- |
| `APP_ENV` | `production` | **Required** | Sets application environment mode |
| `DEBUG` | `false` | **Required** | Disables debug tracebacks in API responses |
| `LOG_LEVEL` | `INFO` | **Required** | Production logging verbosity |
| `RAMP_DATA_MODE` | `SYNTHETIC_DEMO` | **Required** | Safe, self-contained monsoon generation for cloud demo |
| `STORAGE_MODE` | `LOCAL_FALLBACK` | **Required** | Uses container filesystem vault (no external MinIO needed) |
| `RAMP_DATA_ROOT` | `/app/data` | **Required** | Container directory for local vaults and cache |
| `RAMP_CONFIG_PATH` | `/app/config/model_config.yaml` | **Required** | Model registry configuration path |
| `SECRET_KEY` | *(Render auto-generated 32+ char)* | **Secret** | Cryptographic session & token signing key |
| `CORS_ORIGINS` | `*` (or your Render URL) | **Public** | Permitted CORS origins |
| `VITE_API_BASE_URL` | *(Leave empty)* | **Public** | Empty string routes fetch calls to same-origin relative `/api` |

---

## 4. Verification & Testing After Deployment

Once the Render build completes and status changes to **Live**:

### 1. Test System Health Probes
```bash
# Basic Liveness Probe (Used by Render Healthcheck)
curl -f https://YOUR-SERVICE.onrender.com/health/live

# Application Readiness Probe
curl -f https://YOUR-SERVICE.onrender.com/health/ready

# Typed System Info
curl -f https://YOUR-SERVICE.onrender.com/api/system/info
```

### 2. Verify Interactive Documentation
Open in your browser:
- Swagger UI: `https://YOUR-SERVICE.onrender.com/docs`
- ReDoc: `https://YOUR-SERVICE.onrender.com/redoc`

### 3. Verify Operational Frontend Dashboards
Navigate directly to each SPA route and test refreshing the browser (ensuring Nginx `try_files` avoids 404s):
- **Forecast Cockpit**: `https://YOUR-SERVICE.onrender.com/forecast`
- **Production Status**: `https://YOUR-SERVICE.onrender.com/production`
- **Acceptance Scorecard**: `https://YOUR-SERVICE.onrender.com/acceptance`
- **Real Data Lab**: `https://YOUR-SERVICE.onrender.com/real-data`
- **Jury Demonstration**: `https://YOUR-SERVICE.onrender.com/jury-demo`
- **Weather Regimes**: `https://YOUR-SERVICE.onrender.com/regime`

---

## 5. Deployment Characteristics & Limitations

To ensure absolute transparency and compliance with institutional standards:

### 1. Ephemeral Filesystem
- Render Web Services use an **ephemeral disk**. Any files written to `/app/data/cache/` or `/app/data/real/vault/objects/` during a session are reset on container redeploy or restart.
- For demonstration, RAMP's internal mock catalog and model fixtures persist automatically within the built image.
- For long-term persistent storage in production, configure external **MinIO/AWS S3** (`MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`) and **PostgreSQL** (`DATABASE_URL`).

### 2. Authoritative NCMRWF & IMD Real Operational Data
- The cloud deployment operates by default in **`SYNTHETIC_DEMO`** mode.
- In accordance with MoES data governance, high-resolution operational NCUM/NEPS binaries and raw IMD daily `.grd` archives require authenticated institutional network mounts (`/ncmrwf/archive` and `/imd/daily`).
- The Production Status and Acceptance Scorecard dashboards **factually report** that authoritative operational archives are unmounted when in cloud demo mode, adhering to our strict zero-fabrication scientific integrity policy.

### 3. Memory & Startup Times
- Scientific Python packages (`xarray`, `scikit-learn`, `lightgbm`, `scipy`) require ~200–350 MB RAM at idle and ~500 MB under multi-grid inference.
- On Render's Free tier, services spin down after 15 minutes of inactivity. Cold starts can take 30–50 seconds as Python imports the ML stack. Upgrading to a Starter or Standard instance provides instant responsiveness without cold starts.
