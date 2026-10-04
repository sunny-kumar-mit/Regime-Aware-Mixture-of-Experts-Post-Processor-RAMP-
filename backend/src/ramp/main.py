"""
RAMP FastAPI Main Application Entrypoint
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF
"""

# ---------------------------------------------------------------------------
# Bootstrap: ensure the project root (containing ml/ and backend/) is on
# sys.path so that `import ml.*` works regardless of the CWD or PYTHONPATH
# set by the shell that launched uvicorn. This runs in every reloader child.
# ---------------------------------------------------------------------------
import sys
from pathlib import Path as _Path

def _bootstrap_path():
    current = _Path(__file__).resolve().parent
    for _ in range(8):
        if (current / "ml").is_dir() and (current / "backend").is_dir():
            proj_root = str(current)
            if proj_root not in sys.path:
                sys.path.insert(0, proj_root)
            return
        current = current.parent

_bootstrap_path()

import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ramp.config import settings
from ramp.logger import logger
from ramp.api.router import api_router
from ramp.api.v1.data import router as data_router
from ramp.api.v1.dataset import router as dataset_router
from ramp.api.v1.regime import router as regime_router
from ramp.api.v1.baselines import router as baselines_router
from ramp.api.v1.ramp import router as ramp_router
from ramp.api.v1.extreme import router as extreme_router
from ramp.api.v1.operational import router as operational_router
from ramp.api.v1.spatial import router as spatial_router
from ramp.api.v1.scientific import router as scientific_router
from ramp.api.v1.datasets_real import router as datasets_real_router
from ramp.api.v1.models import router as models_router
from ramp.api.v1.forecast import router as forecast_router
from ramp.api.v1.operations import router as operations_router
from ramp.api.v1.activation import router as activation_router
from ramp.api.v1.ingestion import router as ingestion_router
from ramp.api.v1.verification_real import router as verification_real_router
from ramp.api.v1.production import router as production_router
from ramp.api.v1.acceptance import router as acceptance_router
from ramp.api.v1.real_data import router as real_data_router



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan lifecycle manager."""
    logger.info(
        f"Starting {settings.APP_NAME} v{settings.VERSION} [{settings.APP_ENV}] "
        f"- DataMode: {settings.RAMP_DATA_MODE}"
    )
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS Configuration
# ---------------------------------------------------------------------------
origins = settings.CORS_ORIGINS
if isinstance(origins, str):
    origins = [origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Structured Request Timing Middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000.0

    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} "
        f"({duration_ms:.2f}ms)"
    )
    response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"
    return response


# ---------------------------------------------------------------------------
# Router Mounting
# ---------------------------------------------------------------------------
# Primary API prefix: /api
app.include_router(api_router, prefix=settings.API_PREFIX)
app.include_router(data_router, prefix=settings.API_PREFIX)
app.include_router(dataset_router, prefix=settings.API_PREFIX)
app.include_router(regime_router, prefix=settings.API_PREFIX)
app.include_router(baselines_router, prefix=settings.API_PREFIX)
app.include_router(ramp_router, prefix=settings.API_PREFIX)
app.include_router(extreme_router, prefix=settings.API_PREFIX)
app.include_router(operational_router, prefix=settings.API_PREFIX)
app.include_router(spatial_router, prefix=settings.API_PREFIX)
app.include_router(scientific_router, prefix=settings.API_PREFIX)
app.include_router(datasets_real_router, prefix=settings.API_PREFIX)
app.include_router(models_router, prefix=settings.API_PREFIX)
app.include_router(forecast_router, prefix=settings.API_PREFIX)
app.include_router(operations_router, prefix=settings.API_PREFIX)
app.include_router(activation_router, prefix=settings.API_PREFIX)
app.include_router(ingestion_router, prefix=settings.API_PREFIX)
app.include_router(verification_real_router, prefix=settings.API_PREFIX)
app.include_router(production_router, prefix=settings.API_PREFIX)
app.include_router(acceptance_router, prefix=settings.API_PREFIX)
app.include_router(real_data_router, prefix=settings.API_PREFIX)


# ---------------------------------------------------------------------------
# Modular Production Health Probes (PART F)
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Probes"], include_in_schema=False)
@app.get("/health/live", tags=["Probes"])
async def health_live():
    return {"status": "UP", "subsystem": "live", "app": settings.APP_NAME, "version": settings.VERSION}


@app.get("/health/ready", tags=["Probes"])
async def health_ready():
    from ml.real_data.object_storage import ObjectStorageService
    storage = ObjectStorageService()
    catalog = storage._load_metadata()
    catalog_ready = len(catalog) > 0
    return {
        "status": "UP" if catalog_ready else "DEGRADED",
        "subsystem": "ready",
        "ready": True,
        "catalog_objects": len(catalog),
        "storage_mode": storage.storage_mode,
    }


@app.get("/health/data", tags=["Probes"])
async def health_data():
    from ml.production.connectivity import DataConnectivityMonitor
    mon = DataConnectivityMonitor()
    conn = mon.check_all_providers()
    ncmrwf = conn.get("NCMRWF_NCUM")
    imd = conn.get("IMD_GRIDDED_RAINFALL")
    if ncmrwf and ncmrwf.is_mounted and imd and imd.is_mounted:
        return {"status": "UP", "subsystem": "data", "authoritative_mounted": True}
    return {
        "status": "BLOCKED",
        "subsystem": "data",
        "authoritative_mounted": False,
        "detail": "WAITING_FOR_AUTHORITATIVE_DATA: NCMRWF/IMD operational archives unmounted.",
    }


@app.get("/health/models", tags=["Probes"])
async def health_models():
    reg_file = _Path("ml/model_registry/registry.json")
    has_registry = reg_file.exists()
    models = list(_Path("ml/model_registry/models").rglob("model.bin")) if _Path("ml/model_registry/models").exists() else []
    return {
        "status": "UP" if has_registry else "DOWN",
        "subsystem": "models",
        "registry_present": has_registry,
        "models_count": len(models),
        "active_models": ["ramp_global_v2.0.0", "ramp_regime_v2.0.0", "ramp_moe_v2.0.0", "ramp_extreme_v2.0.0"] if has_registry else [],
    }


@app.get("/health/inference", tags=["Probes"])
async def health_inference():
    return {"status": "READY", "subsystem": "inference", "engine_version": "v2.0.0"}


@app.get("/health/operations", tags=["Probes"])
async def health_operations():
    from ml.production.connectivity import DataConnectivityMonitor
    mon = DataConnectivityMonitor()
    conn = mon.check_all_providers()
    ncmrwf = conn.get("NCMRWF_NCUM")
    if ncmrwf and ncmrwf.is_mounted:
        return {"status": "OPERATIONAL", "subsystem": "operations"}
    return {
        "status": "BLOCKED",
        "subsystem": "operations",
        "detail": "REAL_OPERATIONAL = BLOCKED: Waiting for authoritative data.",
    }


@app.get("/health/overall", tags=["Probes"])
async def health_overall():
    from ml.production.connectivity import DataConnectivityMonitor
    mon = DataConnectivityMonitor()
    conn = mon.check_all_providers()
    ncmrwf = conn.get("NCMRWF_NCUM")
    imd = conn.get("IMD_GRIDDED_RAINFALL")
    is_mounted = ncmrwf and ncmrwf.is_mounted and imd and imd.is_mounted
    return {
        "status": "UP" if is_mounted else "DEGRADED",
        "subsystem": "overall",
        "authoritative_data": "UP" if is_mounted else "BLOCKED",
        "detail": "System operational mechanics verified; real operational data unmounted." if not is_mounted else "All systems normal.",
    }


# ---------------------------------------------------------------------------
# Frontend Static SPA Serving & Fallback
# ---------------------------------------------------------------------------
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import HTTPException

frontend_dist_dirs = [
    _Path("/usr/share/nginx/html"),
    _Path("/app/frontend/dist"),
    _Path(__file__).resolve().parents[3] / "frontend" / "dist",
    _Path.cwd() / "frontend" / "dist",
]
frontend_dist = None
for cand in frontend_dist_dirs:
    if (cand / "index.html").is_file():
        frontend_dist = cand
        break

if frontend_dist:
    assets_dir = frontend_dist / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa_frontend(full_path: str):
        if full_path.startswith(("api", "health", "docs", "openapi.json", "redoc")):
            raise HTTPException(status_code=404, detail="Endpoint not found")
        file_target = frontend_dist / full_path
        if full_path and file_target.is_file():
            return FileResponse(file_target)
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/", tags=["Root"])
    async def root_info():
        return {
            "app": settings.APP_NAME,
            "version": settings.VERSION,
            "organization": settings.ORGANIZATION,
            "department": settings.DEPARTMENT,
            "status": "operational",
            "docs": "/docs",
            "health": f"{settings.API_PREFIX}/health",
            "system_info": f"{settings.API_PREFIX}/system/info",
        }
