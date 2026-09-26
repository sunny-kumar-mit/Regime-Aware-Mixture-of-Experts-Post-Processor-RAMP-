"""
RAMP Data API Router
SIH26080 | /api/data/* endpoints

Provides:
  GET  /api/data/providers          - List all registered providers with status
  GET  /api/data/providers/{id}     - Single provider details
  GET  /api/data/datasets           - All datasets from the manifest
  GET  /api/data/datasets/{id}      - Single dataset entry
  GET  /api/data/status             - Full system data readiness status
  POST /api/data/validate/{id}      - Run provider validation
  GET  /api/data/schema/{variable}  - Canonical variable schema
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ramp.ingestion.registry import get_registry
from ramp.validation.manifest import DatasetEntry, load_manifest

router = APIRouter(prefix="/data", tags=["Data Layer"])


# ============================================================
# Pydantic response schemas
# ============================================================

class ProviderStatusResponse(BaseModel):
    provider_id: str
    name: str
    provider_type: str
    status: str
    description: str = ""
    available_variables: List[str] = []
    spatial_resolution_deg: Optional[float] = None
    notes: Optional[str] = None


class ProvidersListResponse(BaseModel):
    total: int
    providers: List[ProviderStatusResponse]


class DatasetResponse(BaseModel):
    id: str
    name: str
    provider: str
    provider_type: str
    variables: List[str]
    time_range_start: Optional[str] = None
    time_range_end: Optional[str] = None
    spatial_domain: str = "India"
    resolution_deg: Optional[float] = None
    file_format: str
    status: str
    data_mode: str
    notes: str = ""
    last_validated: Optional[str] = None


class DatasetsListResponse(BaseModel):
    total: int
    datasets: List[DatasetResponse]


class ValidationResultResponse(BaseModel):
    dataset_name: str
    provider_id: str
    generated_at: str
    passed: bool
    errors: List[str]
    warnings: List[str]
    n_timesteps: int
    missing_fraction: float
    invalid_count: int
    extreme_value_count: int
    notes: str
    data_mode: str


class DataStatusResponse(BaseModel):
    timestamp: str
    data_mode: str
    providers_available: int
    providers_not_configured: int
    providers_unavailable: int
    ready_for_ml: bool
    readiness_message: str
    providers: List[ProviderStatusResponse]


class VariableSchemaResponse(BaseModel):
    variable: str
    standard_units: str
    description: str
    physical_min: Optional[float]
    physical_max: Optional[float]
    extreme_threshold: Optional[float]


# ============================================================
# Endpoint implementations
# ============================================================

@router.get("/providers", response_model=ProvidersListResponse)
async def list_providers() -> ProvidersListResponse:
    """List all registered data providers with current availability status."""
    registry = get_registry()
    infos = registry.list_all_providers()
    providers = [
        ProviderStatusResponse(
            provider_id=p.provider_id,
            name=p.name,
            provider_type=p.provider_type.value,
            status=p.status.value,
            description=p.description,
            available_variables=p.available_variables,
            spatial_resolution_deg=p.spatial_resolution_deg,
            notes=p.notes,
        )
        for p in infos
    ]
    return ProvidersListResponse(total=len(providers), providers=providers)


@router.get("/providers/{provider_id}", response_model=ProviderStatusResponse)
async def get_provider(provider_id: str) -> ProviderStatusResponse:
    """Get details for a specific data provider."""
    registry = get_registry()
    provider = registry.get_nwp(provider_id) or registry.get_obs(provider_id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_id}' not found in registry.",
        )
    info = provider.get_info()
    return ProviderStatusResponse(
        provider_id=info.provider_id,
        name=info.name,
        provider_type=info.provider_type.value,
        status=info.status.value,
        description=info.description,
        available_variables=info.available_variables,
        spatial_resolution_deg=info.spatial_resolution_deg,
        notes=info.notes,
    )


@router.get("/datasets", response_model=DatasetsListResponse)
async def list_datasets() -> DatasetsListResponse:
    """List all datasets from the data manifest."""
    manifest = load_manifest()
    datasets = [
        DatasetResponse(
            id=ds.id,
            name=ds.name,
            provider=ds.provider,
            provider_type=ds.provider_type,
            variables=ds.variables,
            time_range_start=ds.time_range_start,
            time_range_end=ds.time_range_end,
            spatial_domain=ds.spatial_domain,
            resolution_deg=ds.resolution_deg,
            file_format=ds.file_format,
            status=ds.status,
            data_mode=ds.data_mode,
            notes=ds.notes,
            last_validated=ds.last_validated,
        )
        for ds in manifest.datasets
    ]
    return DatasetsListResponse(total=len(datasets), datasets=datasets)


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(dataset_id: str) -> DatasetResponse:
    """Get details for a specific dataset."""
    manifest = load_manifest()
    ds = manifest.get_dataset(dataset_id)
    if ds is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found in manifest.",
        )
    return DatasetResponse(
        id=ds.id,
        name=ds.name,
        provider=ds.provider,
        provider_type=ds.provider_type,
        variables=ds.variables,
        time_range_start=ds.time_range_start,
        time_range_end=ds.time_range_end,
        spatial_domain=ds.spatial_domain,
        resolution_deg=ds.resolution_deg,
        file_format=ds.file_format,
        status=ds.status,
        data_mode=ds.data_mode,
        notes=ds.notes,
        last_validated=ds.last_validated,
    )


@router.get("/status", response_model=DataStatusResponse)
async def get_data_status() -> DataStatusResponse:
    """Return overall data readiness for the RAMP pipeline."""
    from ramp.config import settings

    registry = get_registry()
    infos = registry.list_all_providers()

    available = sum(1 for p in infos if p.status.value == "AVAILABLE")
    not_configured = sum(1 for p in infos if p.status.value in ("NOT_CONFIGURED", "CONFIGURED"))
    unavailable = sum(1 for p in infos if p.status.value == "UNAVAILABLE")

    # Ready for ML = at least 1 NWP + 1 obs provider available
    nwp_available = any(
        p.status.value == "AVAILABLE" and p.provider_type.value == "nwp"
        for p in infos
    )
    obs_available = any(
        p.status.value == "AVAILABLE" and p.provider_type.value == "observation"
        for p in infos
    )
    ready = nwp_available and obs_available

    if ready:
        msg = "Data layer ready: NWP and observation providers available."
    elif not nwp_available and not obs_available:
        msg = (
            "Data layer NOT ready: No NWP or observation providers configured. "
            "Add data files to data/raw/ directories."
        )
    elif not nwp_available:
        msg = "Data layer NOT ready: No NWP provider available."
    else:
        msg = "Data layer NOT ready: No observation provider available."

    providers = [
        ProviderStatusResponse(
            provider_id=p.provider_id,
            name=p.name,
            provider_type=p.provider_type.value,
            status=p.status.value,
            description=p.description,
            available_variables=p.available_variables,
            spatial_resolution_deg=p.spatial_resolution_deg,
            notes=p.notes,
        )
        for p in infos
    ]

    return DataStatusResponse(
        timestamp=datetime.now(timezone.utc).isoformat(),
        data_mode=settings.RAMP_DATA_MODE,
        providers_available=available,
        providers_not_configured=not_configured,
        providers_unavailable=unavailable,
        ready_for_ml=ready,
        readiness_message=msg,
        providers=providers,
    )


@router.post("/validate/{provider_id}", response_model=ValidationResultResponse)
async def validate_provider(provider_id: str) -> ValidationResultResponse:
    """Run source validation for a specific provider."""
    registry = get_registry()
    provider = registry.get_nwp(provider_id) or registry.get_obs(provider_id)

    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_id}' not found.",
        )

    report = provider.validate_source()

    return ValidationResultResponse(
        dataset_name=report.dataset_name,
        provider_id=report.provider_id,
        generated_at=report.generated_at.isoformat(),
        passed=report.passed,
        errors=report.errors,
        warnings=report.warnings,
        n_timesteps=report.n_timesteps,
        missing_fraction=report.missing_fraction,
        invalid_count=report.invalid_count,
        extreme_value_count=report.extreme_value_count,
        notes=report.notes,
        data_mode=report.data_mode.value,
    )


# Variable schemas for /api/data/schema/{variable}
_VARIABLE_SCHEMAS: Dict[str, VariableSchemaResponse] = {
    "precip_nwp_raw": VariableSchemaResponse(
        variable="precip_nwp_raw",
        standard_units="mm",
        description="Raw NWP total precipitation (not bias-corrected)",
        physical_min=0.0,
        physical_max=None,
        extreme_threshold=300.0,
    ),
    "observed_rainfall_mm": VariableSchemaResponse(
        variable="observed_rainfall_mm",
        standard_units="mm",
        description="IMD gridded observed daily rainfall (ground truth)",
        physical_min=0.0,
        physical_max=None,
        extreme_threshold=300.0,
    ),
    "u850": VariableSchemaResponse(
        variable="u850",
        standard_units="m/s",
        description="Zonal wind at 850 hPa",
        physical_min=-100.0,
        physical_max=100.0,
        extreme_threshold=None,
    ),
    "v850": VariableSchemaResponse(
        variable="v850",
        standard_units="m/s",
        description="Meridional wind at 850 hPa",
        physical_min=-100.0,
        physical_max=100.0,
        extreme_threshold=None,
    ),
    "u200": VariableSchemaResponse(
        variable="u200",
        standard_units="m/s",
        description="Zonal wind at 200 hPa (upper level)",
        physical_min=-150.0,
        physical_max=150.0,
        extreme_threshold=None,
    ),
    "mslp": VariableSchemaResponse(
        variable="mslp",
        standard_units="hPa",
        description="Mean sea level pressure",
        physical_min=850.0,
        physical_max=1100.0,
        extreme_threshold=None,
    ),
    "t850": VariableSchemaResponse(
        variable="t850",
        standard_units="degC",
        description="Air temperature at 850 hPa",
        physical_min=-80.0,
        physical_max=60.0,
        extreme_threshold=None,
    ),
    "cape": VariableSchemaResponse(
        variable="cape",
        standard_units="J/kg",
        description="Convective Available Potential Energy",
        physical_min=0.0,
        physical_max=15000.0,
        extreme_threshold=None,
    ),
    "pw": VariableSchemaResponse(
        variable="pw",
        standard_units="kg/m²",
        description="Column precipitable water",
        physical_min=0.0,
        physical_max=100.0,
        extreme_threshold=None,
    ),
}


@router.get("/schema/{variable}", response_model=VariableSchemaResponse)
async def get_variable_schema(variable: str) -> VariableSchemaResponse:
    """Return canonical schema and physical bounds for a RAMP variable."""
    schema = _VARIABLE_SCHEMAS.get(variable)
    if schema is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Schema for variable '{variable}' not found. "
                f"Known variables: {list(_VARIABLE_SCHEMAS.keys())}"
            ),
        )
    return schema
