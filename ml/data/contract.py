"""
Phase 8 Data Contract & Canonical Schema
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Defines canonical rainfall and NWP data structures:
- Minimum required metadata
- Scientific variable naming conventions
- Target variable specifications
- Data modes (REAL vs SYNTHETIC_DEMO)
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
import pandas as pd
from pydantic import BaseModel, Field, field_validator


class DataMode(str, Enum):
    """Execution and data availability modes."""
    REAL = "REAL"
    SYNTHETIC_DEMO = "SYNTHETIC_DEMO"


# ---------------------------------------------------------------------------
# Canonical Variable Definitions
# ---------------------------------------------------------------------------

CANONICAL_COORD_COLUMNS = [
    "latitude",
    "longitude",
]

CANONICAL_TIME_COLUMNS = [
    "initialization_time",
    "forecast_valid_time",
    "lead_time_hours",
]

CANONICAL_TARGET_COLUMNS = [
    "observed_rainfall_mm",
]

CANONICAL_NWP_COLUMNS = [
    "nwp_rainfall_mm",
]

CANONICAL_ATMOSPHERIC_COLUMNS = [
    "mslp_pa",
    "u850_ms",
    "v850_ms",
    "cape_jkg",
    "rh700_pct",
    "tpw_kgm2",
    "temp2m_k",
    "gh500_m",
]

CANONICAL_OPTIONAL_COLUMNS = [
    "u200_ms",
    "v200_ms",
    "shear_850_200",
    "dewpoint2m_k",
    "station_id",
    "elevation_m",
    "distance_to_coast_km",
]


class CanonicalRecord(BaseModel):
    """
    Standardized canonical meteorological data record.
    Represents a single spatiotemporal forecast and matching observation.
    """
    dataset_id: str = Field(..., description="Unique dataset identifier")
    dataset_version: str = Field(..., description="Version of dataset (e.g. v1.0.0)")
    source: str = Field(..., description="Data source (e.g. NCMRWF_NCUM, IMD_GRIDDED, SYNTHETIC)")
    data_mode: DataMode = Field(..., description="REAL or SYNTHETIC_DEMO")

    # Temporal Coordinates
    initialization_time: datetime = Field(..., description="Forecast cycle initialization timestamp (UTC)")
    forecast_valid_time: datetime = Field(..., description="Forecast target valid timestamp (UTC)")
    lead_time_hours: int = Field(..., ge=0, le=240, description="Lead time in hours (e.g., 24, 48, 72)")

    # Spatial Coordinates
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees north")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees east")

    # Primary Rainfall Variables
    nwp_rainfall_mm: float = Field(..., ge=0.0, description="NWP raw accumulated rainfall forecast (mm)")
    observed_rainfall_mm: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Ground-truth observed rainfall (mm). None if observation unavailable for evaluation."
    )

    # Meteorological Predictors (Optional/Available)
    mslp_pa: Optional[float] = Field(default=None, description="Mean sea-level pressure in Pascals")
    u850_ms: Optional[float] = Field(default=None, description="850 hPa zonal wind component (m/s)")
    v850_ms: Optional[float] = Field(default=None, description="850 hPa meridional wind component (m/s)")
    cape_jkg: Optional[float] = Field(default=None, ge=0.0, description="Convective Available Potential Energy (J/kg)")
    rh700_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="700 hPa relative humidity (%)")
    tpw_kgm2: Optional[float] = Field(default=None, ge=0.0, description="Total precipitable water (kg/m^2 or mm)")
    temp2m_k: Optional[float] = Field(default=None, description="2m air temperature (Kelvin)")
    gh500_m: Optional[float] = Field(default=None, description="500 hPa geopotential height (geopotential meters)")

    # Optional metadata
    station_id: Optional[str] = Field(default=None, description="Optional station ID for point observations")
    elevation_m: Optional[float] = Field(default=None, description="Surface elevation in meters above sea level")

    @field_validator("nwp_rainfall_mm", "observed_rainfall_mm")
    @classmethod
    def validate_non_negative_rain(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0.0:
            raise ValueError(f"Rainfall cannot be negative: {v}")
        return v


class DatasetContract(BaseModel):
    """
    Contract describing a validated, standardized meteorological dataset.
    """
    dataset_id: str
    dataset_version: str
    source: str
    data_mode: DataMode
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    time_range: Dict[str, str] = Field(..., description="start_date and end_date in ISO 8601")
    spatial_extent: Dict[str, float] = Field(..., description="lat_min, lat_max, lon_min, lon_max")
    resolution: str = Field(..., description="Nominal spatial resolution (e.g. 0.25 deg)")
    lead_times: List[int] = Field(..., description="Available lead times in hours (e.g. [24, 48, 72, 96, 120])")
    feature_schema_version: str = Field(default="canonical_v1.0.0")
    target_schema_version: str = Field(default="imd_rainfall_v1.0.0")
    total_records: int = 0
    valid_records: int = 0
    quality_status: str = Field(default="PENDING", description="PASS, CONDITIONAL_PASS, FAIL")
    variables: List[str] = Field(default_factory=list)


def validate_canonical_dataframe(df: pd.DataFrame, require_target: bool = True) -> List[str]:
    """
    Validates that a DataFrame conforms to the canonical schema.
    Returns a list of validation error messages (empty if valid).
    """
    errors: List[str] = []

    # Mandatory coordinates
    for col in ["latitude", "longitude"]:
        if col not in df.columns:
            errors.append(f"Missing mandatory spatial coordinate '{col}'")

    # Mandatory time columns
    for col in ["initialization_time", "forecast_valid_time", "lead_time_hours"]:
        if col not in df.columns:
            errors.append(f"Missing mandatory temporal column '{col}'")

    # NWP precipitation
    if "nwp_rainfall_mm" not in df.columns:
        errors.append("Missing mandatory NWP rainfall column 'nwp_rainfall_mm'")

    # Observation target
    if require_target and "observed_rainfall_mm" not in df.columns:
        errors.append("Missing mandatory observation target column 'observed_rainfall_mm'")

    return errors
