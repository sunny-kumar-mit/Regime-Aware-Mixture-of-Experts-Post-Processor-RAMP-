"""
RAMP Core API Router
SIH26080 | Production-Grade Endpoints
"""

from datetime import datetime, timezone
from fastapi import APIRouter
from ramp.config import settings
from ramp.api.schemas import (
    DataMode,
    HealthResponse,
    RegimeType,
    SystemInfoResponse,
    BaselineModel,
)

api_router = APIRouter()


@api_router.get("/health", response_model=HealthResponse, tags=["System"])
async def get_health() -> HealthResponse:
    """Return health status, current data mode, version and environment."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        version=settings.VERSION,
        environment=settings.APP_ENV,
        data_mode=DataMode(settings.RAMP_DATA_MODE),
    )


@api_router.get("/version", tags=["System"])
async def get_version() -> dict:
    """Return application version and build metadata."""
    return {
        "version": settings.VERSION,
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }


@api_router.get("/system/info", response_model=SystemInfoResponse, tags=["System"])
async def get_system_info() -> SystemInfoResponse:
    """Return complete system metadata, active regimes, IMD thresholds, and supported baselines."""
    return SystemInfoResponse(
        app_name=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.VERSION,
        environment=settings.APP_ENV,
        organization=settings.ORGANIZATION,
        department=settings.DEPARTMENT,
        data_mode=DataMode(settings.RAMP_DATA_MODE),
        active_regimes=list(RegimeType),
        imd_thresholds_mm_per_24h={
            "heavy": 64.5,
            "very_heavy": 115.6,
            "extremely_heavy": 204.5,
        },
        supported_baselines=list(BaselineModel),
        pipeline_stages=[
            "nwp_ingestion",
            "harmonisation",
            "feature_engineering",
            "regime_classification",
            "moe_post_processing",
            "extreme_calibration",
            "spatial_aggregation",
            "verification",
        ],
    )
