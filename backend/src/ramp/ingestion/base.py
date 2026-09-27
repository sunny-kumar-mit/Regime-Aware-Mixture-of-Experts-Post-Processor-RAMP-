"""
RAMP Ingestion Base — Abstract Provider Interfaces
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts

Scientific Rules Enforced Here:
  R1. forecast_valid_time = initialization_time + lead_time_hours.
      Observation matching MUST use forecast_valid_time, never initialization_time.
  R2. Missing optional variables must be explicitly represented (never silently absent).
  R3. SYNTHETIC_DEMO data must never be labelled as real observations.
  R4. An unavailable provider must return ProviderUnavailable, never fabricated data.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


# =============================================================================
# Enumerations
# =============================================================================

class DataMode(str, Enum):
    """Operational integrity tag propagated through the full pipeline."""
    REAL_OPERATIONAL = "REAL_OPERATIONAL"
    REAL_ARCHIVE = "REAL_ARCHIVE"
    PUBLIC_PROXY = "PUBLIC_PROXY"
    SYNTHETIC_DEMO = "SYNTHETIC_DEMO"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    REAL = "REAL"


class ProviderStatus(str, Enum):
    """Indicates availability and configuration state of a data provider."""
    AVAILABLE = "AVAILABLE"
    CONFIGURED = "CONFIGURED"        # Config present but data not yet downloaded/verified
    NOT_CONFIGURED = "NOT_CONFIGURED"
    UNAVAILABLE = "UNAVAILABLE"      # Expected source not reachable / data files absent
    PROCESSING = "PROCESSING"
    INVALID = "INVALID"              # Source found but fails validation


class ProviderType(str, Enum):
    NWP = "nwp"
    OBSERVATION = "observation"
    AUXILIARY = "auxiliary"


class QualityFlag(str, Enum):
    """Per-value quality flags — distinct categories, not just bad/good."""
    VALID = "VALID"
    VALID_EXTREME = "VALID_EXTREME"   # Physically possible but very large — keep, do not delete
    SUSPICIOUS = "SUSPICIOUS"         # Outside expected range but not definitively wrong
    MISSING = "MISSING"              # NaN / fill value
    INVALID = "INVALID"              # Physically impossible (negative rainfall, etc.)


class FileFormat(str, Enum):
    NETCDF = "netcdf"
    GRIB2 = "grib2"
    CSV = "csv"
    ZARR = "zarr"
    UNKNOWN = "unknown"


# =============================================================================
# Domain Types
# =============================================================================

@dataclass(frozen=True)
class BoundingBox:
    """Geographic bounding box."""
    lat_min: float  # degrees north
    lat_max: float
    lon_min: float  # degrees east
    lon_max: float

    def __post_init__(self) -> None:
        if self.lat_min >= self.lat_max:
            raise ValueError(f"lat_min ({self.lat_min}) must be < lat_max ({self.lat_max})")
        if self.lon_min >= self.lon_max:
            raise ValueError(f"lon_min ({self.lon_min}) must be < lon_max ({self.lon_max})")


# Standard India domain used across RAMP
INDIA_DOMAIN = BoundingBox(lat_min=6.5, lat_max=38.5, lon_min=66.5, lon_max=100.5)


@dataclass
class ForecastTimeSpec:
    """
    Full temporal specification of a single NWP forecast.

    CRITICAL SCIENTIFIC CONTRACT:
      forecast_valid_time = initialization_time + timedelta(hours=lead_time_hours)

    Observation matching MUST use forecast_valid_time.
    Do NOT match observations by initialization_time.
    """
    initialization_time: datetime   # When the model run began (UTC)
    lead_time_hours: int            # Forecast horizon in whole hours

    def __post_init__(self) -> None:
        if self.initialization_time.tzinfo is None:
            raise ValueError("initialization_time must be timezone-aware (UTC)")
        if self.lead_time_hours < 0:
            raise ValueError("lead_time_hours must be non-negative")

    @property
    def forecast_valid_time(self) -> datetime:
        """The time to which this forecast corresponds. Match observations on THIS."""
        return self.initialization_time + timedelta(hours=self.lead_time_hours)


@dataclass
class GridSpec:
    """Target or source grid specification."""
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    resolution_deg: float

    @property
    def n_lats(self) -> int:
        return round((self.lat_max - self.lat_min) / self.resolution_deg) + 1

    @property
    def n_lons(self) -> int:
        return round((self.lon_max - self.lon_min) / self.resolution_deg) + 1


# RAMP canonical output grid: India 0.25°
RAMP_TARGET_GRID = GridSpec(
    lat_min=6.5, lat_max=38.5, lon_min=66.5, lon_max=100.5, resolution_deg=0.25
)


@dataclass
class VariableDescriptor:
    """
    Descriptor for a single meteorological variable in a provider dataset.

    Missing optional variables must be represented explicitly via present=False.
    """
    name: str                        # RAMP canonical name (e.g. 'u850')
    source_name: str                 # Provider-specific variable name
    standard_units: str              # Unit after normalization
    source_units: Optional[str] = None  # As read from source metadata (None = not yet determined)
    level: Optional[str] = None      # e.g. '850hPa', 'surface'
    present: bool = True             # False when variable is structurally absent in this provider


@dataclass
class DataProvenance:
    """Full chain-of-custody record for a processed dataset."""
    source_provider: str
    source_model: str
    original_filename: Optional[str] = None
    download_time: Optional[datetime] = None
    processing_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_url: Optional[str] = None
    dataset_version: Optional[str] = None
    checksum_sha256: Optional[str] = None
    original_units: Dict[str, str] = field(default_factory=dict)
    normalized_units: Dict[str, str] = field(default_factory=dict)
    spatial_domain: Optional[str] = None
    temporal_domain: Optional[str] = None
    processing_steps: List[str] = field(default_factory=list)
    data_mode: DataMode = DataMode.REAL

    def add_step(self, description: str) -> None:
        self.processing_steps.append(
            f"[{datetime.now(timezone.utc).isoformat()}] {description}"
        )

    @staticmethod
    def compute_checksum(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()


@dataclass
class ProviderInfo:
    """Registry entry and status for a data provider."""
    provider_id: str
    name: str
    provider_type: ProviderType
    status: ProviderStatus
    description: str = ""
    supported_formats: List[FileFormat] = field(default_factory=list)
    available_variables: List[str] = field(default_factory=list)
    time_coverage_start: Optional[str] = None
    time_coverage_end: Optional[str] = None
    spatial_resolution_deg: Optional[float] = None
    last_validated: Optional[datetime] = None
    notes: Optional[str] = None


# =============================================================================
# Abstract Provider Interfaces
# =============================================================================

class WeatherForecastProvider(ABC):
    """
    Abstract base for all NWP forecast data providers.

    Implementors: GFSProvider, GEFSProvider, NCMRWFProvider.

    Rules:
      - get_forecast() returns data tagged with DataMode.
      - If data is unavailable, raise ProviderUnavailableError (never fabricate).
      - forecast_valid_time property must always be computed as init + lead.
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        ...

    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        return ProviderType.NWP

    @abstractmethod
    def get_info(self) -> ProviderInfo:
        """Return full provider status and metadata."""
        ...

    @abstractmethod
    def get_available_times(self) -> List[datetime]:
        """List initialization times for which forecast data is locally available."""
        ...

    @abstractmethod
    def get_forecast(
        self,
        initialization_time: datetime,
        lead_time_hours: int,
        variables: Optional[List[str]] = None,
        domain: BoundingBox = INDIA_DOMAIN,
    ) -> "NWPForecastBundle":
        """
        Retrieve a single forecast time step.

        Returns NWPForecastBundle tagged with appropriate DataMode.
        Raises ProviderUnavailableError if data is not present.
        """
        ...

    @abstractmethod
    def validate_source(self) -> "ValidationReport":
        """Run source health checks and return a validation report."""
        ...

    def get_metadata(self) -> Dict[str, Any]:
        return self.get_info().__dict__


class ObservationProvider(ABC):
    """
    Abstract base for observational data providers.

    Implementors: IMDObservationProvider.

    Critical Rule:
      Observations are indexed by observation_time.
      Never use these for training unless valid_time == observation_time.
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        ...

    @abstractmethod
    def get_info(self) -> ProviderInfo:
        ...

    @abstractmethod
    def get_available_times(self) -> List[datetime]:
        """List observation times available locally."""
        ...

    @abstractmethod
    def get_observations(
        self,
        observation_time: datetime,
        domain: BoundingBox = INDIA_DOMAIN,
    ) -> "ObservationBundle":
        """
        Retrieve observed gridded rainfall for a specific valid time.

        Args:
            observation_time: The VALID time (forecast_valid_time must equal this).
        """
        ...

    @abstractmethod
    def validate_source(self) -> "ValidationReport":
        ...


class AuxiliaryDataProvider(ABC):
    """Abstract base for static/auxiliary data (DEM, land-sea mask, shapefiles)."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        ...

    @abstractmethod
    def get_info(self) -> ProviderInfo:
        ...

    @abstractmethod
    def get_data(self, variable: str, domain: BoundingBox = INDIA_DOMAIN) -> Any:
        ...


# =============================================================================
# Data Bundle Types
# =============================================================================

@dataclass
class NWPForecastBundle:
    """
    Canonical internal representation of a single NWP forecast time step.

    The xr_dataset attribute (when populated) is a lazy xarray.Dataset.
    Variables not present in this provider are marked via variables dict with present=False.
    """
    time_spec: ForecastTimeSpec
    provider_id: str
    model_name: str
    ensemble_member: Optional[int]          # None for deterministic; int for ensemble
    variables: Dict[str, VariableDescriptor]
    data_mode: DataMode
    provenance: DataProvenance
    xr_dataset: Optional[Any] = None        # xarray.Dataset (lazy-loaded)
    grid_spec: Optional[GridSpec] = None

    @property
    def initialization_time(self) -> datetime:
        return self.time_spec.initialization_time

    @property
    def forecast_valid_time(self) -> datetime:
        """Always use this for observation matching."""
        return self.time_spec.forecast_valid_time

    @property
    def lead_time_hours(self) -> int:
        return self.time_spec.lead_time_hours


@dataclass
class ObservationBundle:
    """Canonical internal representation of gridded observations."""
    observation_time: datetime
    provider_id: str
    source: str
    observed_rainfall_mm: Optional[Any]     # numpy array or xarray DataArray
    quality_flags: Optional[Any] = None     # Same shape as observed_rainfall_mm
    missing_fraction: float = 0.0
    data_mode: DataMode = DataMode.REAL
    provenance: Optional[DataProvenance] = None
    xr_dataset: Optional[Any] = None
    grid_spec: Optional[GridSpec] = None


# =============================================================================
# Exceptions
# =============================================================================

class ProviderUnavailableError(Exception):
    """Raised when a provider cannot supply data (files absent, API unreachable, etc.)."""
    def __init__(self, provider_id: str, reason: str) -> None:
        self.provider_id = provider_id
        self.reason = reason
        super().__init__(
            f"Provider '{provider_id}' is unavailable: {reason}. "
            "Do NOT fabricate data as a substitute."
        )


class DataValidationError(Exception):
    """Raised on unrecoverable data validation failure."""


class UnitConversionError(Exception):
    """Raised when a unit conversion cannot be determined safely."""


class TimeAlignmentError(Exception):
    """Raised when forecast valid time and observation time cannot be aligned."""


# =============================================================================
# Validation Report (shared schema)
# =============================================================================

@dataclass
class ValidationReport:
    """
    Structured validation output.
    Every ingestion call must produce one of these — no silent failures.
    """
    dataset_name: str
    provider_id: str
    model_name: str = ""
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Coverage
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    n_timesteps: int = 0

    # Spatial
    grid_resolution_deg: Optional[float] = None
    n_lat: int = 0
    n_lon: int = 0
    n_grid_points: int = 0

    # Variables
    variables: List[str] = field(default_factory=list)
    units: Dict[str, str] = field(default_factory=dict)

    # Quality
    missing_fraction: float = 0.0
    invalid_count: int = 0
    duplicate_timestamp_count: int = 0
    extreme_value_count: int = 0     # Count of VALID_EXTREME flagged values
    suspicious_count: int = 0

    # Status
    passed: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    notes: str = ""
    data_mode: DataMode = DataMode.REAL

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.passed = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset": self.dataset_name,
            "provider": self.provider_id,
            "model": self.model_name,
            "generated_at": self.generated_at.isoformat(),
            "time_start": self.time_start,
            "time_end": self.time_end,
            "n_timesteps": self.n_timesteps,
            "grid_resolution_deg": self.grid_resolution_deg,
            "n_lat": self.n_lat,
            "n_lon": self.n_lon,
            "n_grid_points": self.n_grid_points,
            "variables": self.variables,
            "units": self.units,
            "missing_fraction": round(self.missing_fraction, 6),
            "invalid_count": self.invalid_count,
            "duplicate_timestamp_count": self.duplicate_timestamp_count,
            "extreme_value_count": self.extreme_value_count,
            "suspicious_count": self.suspicious_count,
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "notes": self.notes,
            "data_mode": self.data_mode.value,
        }
