"""
RAMP FastAPI Main Application Entrypoint
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF
"""

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

# Also expose /health and /version at root for standard orchestrator probes
@app.get("/health", tags=["Probes"], include_in_schema=False)
async def root_health():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "data_mode": settings.RAMP_DATA_MODE,
    }


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
