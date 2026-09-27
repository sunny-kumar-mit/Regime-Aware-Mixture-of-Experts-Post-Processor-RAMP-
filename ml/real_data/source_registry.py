"""
RAMP Central Meteorological Source Registry
SIH26080 | MoES / NCMRWF | Phase 19 Upgrade

Defines authoritative source registry for NCMRWF (NCUM, NEPS) and IMD (0.25° Gridded, Merged GPM).
Provides official portal URLs, variable definitions, levels, access types, and health check metadata.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ml.real_data.models import AuthorityLevel, ProviderType, SourceType


class SourceVariableDefinition(BaseModel):
    name: str
    canonical_ramp_feature: Optional[str] = None
    level: str = "Surface"
    unit: str = ""
    is_derived: bool = False
    derivation_formula: Optional[str] = None
    description: str = ""


class MeteorologicalSource(BaseModel):
    source_id: str
    provider: ProviderType
    provider_name: str
    dataset_name: str
    source_type: SourceType
    authority: AuthorityLevel
    resolution: str
    coverage: str = "Indian Subcontinent (6.5°N - 38.5°N, 66.5°E - 100.5°E)"
    grid_dims: str = "129 x 137 at 0.25°"
    official_source_url: str
    dataset_page_url: str
    download_endpoint_template: Optional[str] = None
    access_type: str  # "PUBLIC", "AUTH_REQUIRED", "IMDLIB_ADAPTER", "HPC_MOUNT_ONLY"
    access_status: str  # "READY", "AUTH_REQUIRED", "CONNECTED", "UNAVAILABLE"
    data_type: str
    cycles: List[str] = Field(default_factory=list)
    leads_hours: List[int] = Field(default_factory=list)
    supported_formats: List[str] = Field(default_factory=list)
    available_levels: List[str] = Field(default_factory=list)
    variables: List[SourceVariableDefinition] = Field(default_factory=list)
    terms_notes: str = ""
    last_checked_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# Canonical Source Registry
# ---------------------------------------------------------------------------

CENTRAL_SOURCES: Dict[str, MeteorologicalSource] = {
    "NCMRWF_NCUM": MeteorologicalSource(
        source_id="NCMRWF_NCUM",
        provider=ProviderType.NCMRWF,
        provider_name="National Centre for Medium Range Weather Forecasting (NCMRWF)",
        dataset_name="NCUM Deterministic Global Forecast",
        source_type=SourceType.NCUM,
        authority=AuthorityLevel.AUTHORITATIVE_PRIMARY,
        resolution="~12 km (NCUM-G) / 0.12°",
        coverage="India & Surrounding Monsoonal Domain (6.5°N - 38.5°N, 66.5°E - 100.5°E)",
        grid_dims="Interpolated to canonical 129 x 137 at 0.25°",
        official_source_url="https://nwp.ncmrwf.gov.in/",
        dataset_page_url="https://nwp.ncmrwf.gov.in/ncum_products.php",
        download_endpoint_template="https://nwp.ncmrwf.gov.in/archive/ncum/{cycle}/{date}/ncum_{lead}.nc",
        access_type="AUTH_REQUIRED",
        access_status="AUTH_REQUIRED",
        data_type="Operational Numerical Weather Prediction (Deterministic)",
        cycles=["00Z", "12Z"],
        leads_hours=[6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72, 78, 84, 90, 96, 102, 108, 114, 120],
        supported_formats=["NetCDF4", "GRIB2", "CSV", "Parquet"],
        available_levels=["850 hPa", "Surface / Single-Level"],
        variables=[
            SourceVariableDefinition(
                name="u850",
                canonical_ramp_feature="u850",
                level="850 hPa",
                unit="m/s",
                description="Zonal wind component at 850 hPa",
            ),
            SourceVariableDefinition(
                name="v850",
                canonical_ramp_feature="v850",
                level="850 hPa",
                unit="m/s",
                description="Meridional wind component at 850 hPa",
            ),
            SourceVariableDefinition(
                name="t850",
                canonical_ramp_feature="t850",
                level="850 hPa",
                unit="K",
                description="Air temperature at 850 hPa (converted to °C)",
            ),
            SourceVariableDefinition(
                name="precip_nwp_raw",
                canonical_ramp_feature="precip_nwp_raw",
                level="Surface",
                unit="mm",
                description="Total model surface precipitation accumulation",
            ),
            SourceVariableDefinition(
                name="mslp",
                canonical_ramp_feature="mslp",
                level="Mean Sea Level",
                unit="hPa",
                description="Mean sea level atmospheric pressure",
            ),
            SourceVariableDefinition(
                name="cape",
                canonical_ramp_feature="cape",
                level="Single Layer",
                unit="J/kg",
                description="Convective Available Potential Energy",
            ),
            SourceVariableDefinition(
                name="q850",
                canonical_ramp_feature="humidity_proxy",
                level="850 hPa",
                unit="kg/kg",
                description="Specific humidity at 850 hPa",
            ),
            # Derived features noted for transparency
            SourceVariableDefinition(
                name="wind_speed_850",
                canonical_ramp_feature="wind_speed_850",
                level="850 hPa",
                unit="m/s",
                is_derived=True,
                derivation_formula="sqrt(u850² + v850²)",
                description="Derived wind speed at 850 hPa",
            ),
            SourceVariableDefinition(
                name="wind_dir_850",
                canonical_ramp_feature="wind_dir_850",
                level="850 hPa",
                unit="deg",
                is_derived=True,
                derivation_formula="atan2(v850, u850) * 180 / π",
                description="Derived meteorological wind direction",
            ),
            SourceVariableDefinition(
                name="zonal_shear",
                canonical_ramp_feature="zonal_shear",
                level="Synoptic",
                unit="m/s",
                is_derived=True,
                derivation_formula="u850 - u200",
                description="Monsoon tropospheric zonal wind shear",
            ),
        ],
        terms_notes="NCMRWF raw multi-level model fields require MoES/NCMRWF authorization or dedicated HPC network mount. Public web portal displays graphical forecast charts.",
    ),
    "NCMRWF_NEPS": MeteorologicalSource(
        source_id="NCMRWF_NEPS",
        provider=ProviderType.NCMRWF,
        provider_name="National Centre for Medium Range Weather Forecasting (NCMRWF)",
        dataset_name="NEPS Global Ensemble Prediction System",
        source_type=SourceType.NEPS,
        authority=AuthorityLevel.AUTHORITATIVE_PRIMARY,
        resolution="~12 km (control) / ~33 km (perturbed members)",
        coverage="India & Global Monsoon Domain",
        grid_dims="129 x 137 at 0.25°",
        official_source_url="https://nwp.ncmrwf.gov.in/",
        dataset_page_url="https://nwp.ncmrwf.gov.in/neps_products.php",
        download_endpoint_template="https://nwp.ncmrwf.gov.in/archive/neps/{cycle}/{date}/neps_{lead}.nc",
        access_type="AUTH_REQUIRED",
        access_status="AUTH_REQUIRED",
        data_type="Operational Numerical Weather Prediction (23-Member Ensemble)",
        cycles=["00Z", "12Z"],
        leads_hours=[6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72, 78, 84, 90, 96, 102, 108, 114, 120],
        supported_formats=["NetCDF4", "GRIB2", "Parquet"],
        available_levels=["Surface", "850 hPa"],
        variables=[
            SourceVariableDefinition(
                name="tp_members",
                canonical_ramp_feature="precip_nwp_raw",
                level="Surface",
                unit="mm",
                description="23 individual ensemble member rainfall fields (mem00..mem22)",
            ),
            SourceVariableDefinition(
                name="tp_ens_mean",
                canonical_ramp_feature="precip_nwp_raw",
                level="Surface",
                unit="mm",
                is_derived=True,
                derivation_formula="mean(mem00..mem22)",
                description="Ensemble mean surface precipitation",
            ),
            SourceVariableDefinition(
                name="tp_ens_spread",
                level="Surface",
                unit="mm",
                is_derived=True,
                derivation_formula="std(mem00..mem22)",
                description="Ensemble standard deviation / forecast spread",
            ),
        ],
        terms_notes="Control member plus 22 perturbed members (23 total). Institutional access required for raw GRIB2/NetCDF binary data stream.",
    ),
    "IMD_RAINFALL_025": MeteorologicalSource(
        source_id="IMD_RAINFALL_025",
        provider=ProviderType.IMD,
        provider_name="India Meteorological Department (IMD) / Climate Research & Services, Pune",
        dataset_name="Daily Gridded Rainfall (0.25° x 0.25°)",
        source_type=SourceType.IMD_OBSERVATION,
        authority=AuthorityLevel.AUTHORITATIVE_PRIMARY,
        resolution="0.25° x 0.25° (approx 25 km)",
        coverage="Indian Landmass and Coastal Boundaries (6.5°N - 38.5°N, 66.5°E - 100.5°E)",
        grid_dims="129 x 137 points",
        official_source_url="https://imdpune.gov.in/",
        dataset_page_url="https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html",
        download_endpoint_template="https://imdpune.gov.in/cmpg/Griddata/rainfall.php",
        access_type="IMDLIB_ADAPTER",
        access_status="READY",
        data_type="Observed Meteorological Ground Truth (Station-Interpolated Gridded Rainfall)",
        cycles=["Daily (08:30 IST / 03:00 UTC)"],
        leads_hours=[0],  # Ground truth observation
        supported_formats=["Binary (.grd)", "NetCDF4", "CSV"],
        available_levels=["Surface (Daily Accumulation)"],
        variables=[
            SourceVariableDefinition(
                name="rain",
                canonical_ramp_feature="ground_truth_rainfall",
                level="Surface",
                unit="mm/day",
                description="24-hour accumulated rainfall ending at 08:30 IST (03:00 UTC)",
            )
        ],
        terms_notes="Official IMD Pune gridded product based on ~3,000+ raingauge stations interpolated using Shepard's angular distance weighting method. Permanent GROUND_TRUTH_ONLY designation.",
    ),
    "IMD_MERGED_GAUGE_GPM": MeteorologicalSource(
        source_id="IMD_MERGED_GAUGE_GPM",
        provider=ProviderType.IMD,
        provider_name="India Meteorological Department (IMD)",
        dataset_name="Daily Rainfall Merged Gauge + Satellite (GPM IMERG)",
        source_type=SourceType.IMD_OBSERVATION,
        authority=AuthorityLevel.SECONDARY,
        resolution="0.25° x 0.25°",
        coverage="India and Surrounding Oceanic Basins",
        grid_dims="129 x 137 points",
        official_source_url="https://imdpune.gov.in/",
        dataset_page_url="https://www.imdpune.gov.in/cmpg/Realtimedata/gpm/rain.php",
        download_endpoint_template="https://www.imdpune.gov.in/cmpg/Realtimedata/gpm/rain.php",
        access_type="IMDLIB_ADAPTER",
        access_status="READY",
        data_type="Observed Meteorological Ground Truth (Merged Gauge + Satellite)",
        cycles=["Daily"],
        leads_hours=[0],
        supported_formats=["Binary (.grd)", "NetCDF4"],
        available_levels=["Surface"],
        variables=[
            SourceVariableDefinition(
                name="rain_gpm",
                canonical_ramp_feature="ground_truth_rainfall",
                level="Surface",
                unit="mm/day",
                description="Merged IMD gauge + GPM satellite daily rainfall",
            )
        ],
        terms_notes="Available for current/real-time monsoon monitoring via IMD Pune real-time portal. Permanent GROUND_TRUTH_ONLY designation.",
    ),
}


class CentralSourceRegistry:
    """
    Central access and lookup service for meteorological sources.
    """

    @classmethod
    def list_sources(cls) -> List[MeteorologicalSource]:
        return list(CENTRAL_SOURCES.values())

    @classmethod
    def get_source(cls, source_id: str) -> Optional[MeteorologicalSource]:
        return CENTRAL_SOURCES.get(source_id)

    @classmethod
    def get_sources_by_provider(cls, provider: ProviderType) -> List[MeteorologicalSource]:
        return [s for s in CENTRAL_SOURCES.values() if s.provider == provider]

    @classmethod
    def get_variables_for_source(cls, source_id: str) -> List[SourceVariableDefinition]:
        src = cls.get_source(source_id)
        return src.variables if src else []
