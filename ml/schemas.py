"""
RAMP Machine Learning Schemas
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Canonical Pydantic contracts for:
  - Target variables & target records
  - Feature specifications & feature registry
  - Dataset splitting specifications
  - Preprocessing manifests
  - Dataset versioning & manifests
  - Leakage audit reports
  - Dataset distribution statistics
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DataMode(str, Enum):
    """Operational integrity tag propagated through dataset generation."""
    SYNTHETIC_DEMO = "SYNTHETIC_DEMO"
    REAL = "REAL"


class SplitType(str, Enum):
    """Supported temporal data splitting strategies."""
    CHRONOLOGICAL = "chronological"
    YEAR_BASED = "year_based"
    ROLLING_ORIGIN = "rolling_origin"
    EVENT_AWARE = "event_aware"


class ImputationStrategy(str, Enum):
    """Conservative missing data handling strategies."""
    DROP = "DROP"
    MEDIAN_TRAIN = "MEDIAN_TRAIN"
    FORWARD_ONLY = "FORWARD_ONLY"
    MODEL_NATIVE = "MODEL_NATIVE"


class QualityPolicy(str, Enum):
    """Quality filtering policy for training dataset generation."""
    STRICT = "strict"          # Only VALID and VALID_EXTREME
    BALANCED = "balanced"      # VALID, VALID_EXTREME, review SUSPICIOUS; exclude INVALID, MISSING
    PERMISSIVE = "permissive"  # Include SUSPICIOUS, exclude only INVALID and MISSING target


# =============================================================================
# Feature Specification
# =============================================================================

class FeatureSpec(BaseModel):
    """Metadata specification for every registered feature."""
    name: str = Field(..., description="Canonical feature column name")
    description: str = Field(..., description="Physical or meteorological meaning")
    source: str = Field(..., description="Source variable or calculation inputs")
    unit: str = Field(..., description="Measurement unit (e.g. m/s, mm, hPa, K)")
    dtype: str = Field(..., description="Data type (float32, int32, etc.)")
    required: bool = Field(False, description="Whether dataset generation requires this feature")
    derivation: Optional[str] = Field(None, description="Mathematical or algorithmic formula")
    leakage_risk: str = Field("none", description="Audit classification: none, low, medium, high")
    available: bool = Field(True, description="Whether provider/source data currently exists")


# =============================================================================
# Target Record & Schema
# =============================================================================

class TargetRecord(BaseModel):
    """
    Observation target record corresponding to forecast_valid_time.
    
    CRITICAL SCIENTIFIC CONTRACT:
      Observation targets must align strictly with forecast_valid_time.
      Never match targets using forecast initialization time alone.
    """
    target_valid_time: datetime = Field(..., description="Observation valid time (UTC)")
    latitude: float = Field(..., description="Grid cell latitude")
    longitude: float = Field(..., description="Grid cell longitude")

    # Target 1: Continuous rainfall in mm / 24h
    observed_rainfall_mm: float = Field(..., description="Target 1: IMD observed rainfall (mm)")

    # Target 2: Binary rainfall occurrence (> threshold, default 0.1 mm)
    rainfall_occurrence: int = Field(..., description="Target 2: Binary occurrence flag (0 or 1)")

    # Target 3: Heavy rainfall (>= 64.5 mm / 24h)
    heavy_rainfall: int = Field(..., description="Target 3: Heavy rainfall event flag (>=64.5mm)")

    # Target 4: Very heavy rainfall (>= 115.6 mm / 24h)
    very_heavy_rainfall: int = Field(..., description="Target 4: Very heavy event flag (>=115.6mm)")

    # Target 5: Extremely heavy rainfall (>= 204.5 mm / 24h)
    extremely_heavy_rainfall: int = Field(..., description="Target 5: Extremely heavy flag (>=204.5mm)")

    # Climatology & Target 6: Rainfall anomaly
    climatology_rainfall_mm: Optional[float] = Field(None, description="Training-fitted climatology baseline (mm)")
    rainfall_anomaly: Optional[float] = Field(None, description="Target 6: Observed minus train-fitted climatology")

    # Target provenance & quality
    observation_quality_flag: str = Field(..., description="VALID, VALID_EXTREME, SUSPICIOUS, etc.")
    observation_source: str = Field(..., description="Observation source identifier (e.g. IMD_025)")

    # Regime labels reserved for Phase 4 (MUST BE NULL in Phase 3)
    regime_label: Optional[str] = Field(None, description="Phase 4 regime assignment (NULL in Phase 3)")
    regime_label_source: Optional[str] = Field(None, description="Phase 4 regime source (NULL in Phase 3)")
    regime_label_confidence: Optional[float] = Field(None, description="Phase 4 regime confidence (NULL in Phase 3)")


# =============================================================================
# Canonical Training Sample Schema
# =============================================================================

class TrainingSample(BaseModel):
    """
    Canonical record combining NWP predictor features and verified observation targets.
    """
    sample_id: str = Field(..., description="Unique sample hash identifier")

    # Forecast identifiers & alignment
    forecast_initialization_time: datetime = Field(..., description="Model initialization timestamp (UTC)")
    forecast_valid_time: datetime = Field(..., description="Forecast valid timestamp (UTC)")
    lead_time_hours: int = Field(..., description="Forecast horizon in whole hours")

    # Spatial coordinates
    latitude: float = Field(..., description="Grid latitude (degrees North)")
    longitude: float = Field(..., description="Grid longitude (degrees East)")

    # Provider metadata
    provider: str = Field(..., description="NWP Provider (e.g. GFS, GEFS, NCMRWF)")
    model: str = Field(..., description="Model identifier")
    ensemble_member: Optional[str] = Field(None, description="Ensemble member ID (e.g. 'c00', 'p01', or None)")

    # NWP Predictors
    raw_nwp_rainfall: float = Field(..., description="Raw NWP forecasted precipitation (mm)")
    u850: Optional[float] = Field(None, description="Zonal wind at 850 hPa (m/s)")
    v850: Optional[float] = Field(None, description="Meridional wind at 850 hPa (m/s)")
    mslp: Optional[float] = Field(None, description="Mean sea level pressure (Pa)")
    temperature: Optional[float] = Field(None, description="2m temperature (K)")
    relative_humidity: Optional[float] = Field(None, description="Relative humidity (%)")
    precipitable_water: Optional[float] = Field(None, description="Precipitable water (kg/m^2)")
    cape: Optional[float] = Field(None, description="Convective Available Potential Energy (J/kg)")
    geopotential_height: Optional[float] = Field(None, description="Geopotential height at 500 hPa (m)")

    # Derived meteorological features
    wind_speed_850: Optional[float] = Field(None, description="sqrt(u850^2 + v850^2) (m/s)")
    wind_direction_850: Optional[float] = Field(None, description="Meteorological wind direction (degrees)")

    # Geographical features
    elevation: Optional[float] = Field(None, description="Surface elevation from DEM (m) or None if unavailable")
    distance_to_coast: Optional[float] = Field(None, description="Distance to coastline (km) or None if unavailable")

    # Cyclic temporal features
    day_of_year_sin: float = Field(..., description="sin(2*pi*day_of_year/365.25)")
    day_of_year_cos: float = Field(..., description="cos(2*pi*day_of_year/365.25)")
    valid_hour_sin: float = Field(..., description="sin(2*pi*valid_hour/24.0)")
    valid_hour_cos: float = Field(..., description="cos(2*pi*valid_hour/24.0)")

    # Monsoon season indicators
    pre_monsoon: int = Field(0, description="1 if March-May, else 0")
    monsoon: int = Field(0, description="1 if June-September, else 0")
    post_monsoon: int = Field(0, description="1 if October-December, else 0")
    winter: int = Field(0, description="1 if January-February, else 0")

    # Observation Targets
    observed_rainfall_mm: float = Field(..., description="Observed rainfall (mm)")
    rainfall_occurrence: int = Field(..., description="Occurrence flag (0 or 1)")
    heavy_rainfall: int = Field(..., description=">=64.5 mm flag")
    very_heavy_rainfall: int = Field(..., description=">=115.6 mm flag")
    extremely_heavy_rainfall: int = Field(..., description=">=204.5 mm flag")
    rainfall_anomaly: Optional[float] = Field(None, description="Anomaly relative to train climatology")
    observation_quality_flag: str = Field(..., description="VALID, VALID_EXTREME, etc.")

    # Phase 4 Regime placeholders (must be NULL)
    regime_label: Optional[str] = Field(None, description="Reserved for Phase 4")
    regime_label_source: Optional[str] = Field(None, description="Reserved for Phase 4")
    regime_label_confidence: Optional[float] = Field(None, description="Reserved for Phase 4")


# =============================================================================
# Dataset Versioning & Manifests
# =============================================================================

class DatasetVersion(BaseModel):
    """Complete dataset version manifest tracking provenance and configuration."""
    dataset_id: str = Field(..., description="Identifier (e.g. ramp_dataset_v0.1.0)")
    version: str = Field(..., description="SemVer dataset version")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    data_mode: str = Field("SYNTHETIC_DEMO", description="REAL or SYNTHETIC_DEMO")
    source_datasets: List[str] = Field(default_factory=list, description="List of source datasets ingested")
    feature_schema_version: str = Field("1.0.0", description="Feature registry schema version")
    target_schema_version: str = Field("1.0.0", description="Target definition schema version")
    split_version: str = Field("1.0.0", description="Split configuration version")
    preprocessing_version: str = Field("1.0.0", description="Preprocessing pipeline version")
    row_count: int = Field(0, description="Total sample count across all splits")
    feature_count: int = Field(0, description="Total predictor features in X")
    target_count: int = Field(6, description="Total target definitions")
    time_range: Dict[str, str] = Field(default_factory=dict, description="start and end UTC timestamps")
    spatial_range: Dict[str, float] = Field(default_factory=dict, description="lat_min, lat_max, lon_min, lon_max")
    checksum: Optional[str] = Field(None, description="SHA256 checksum of generated dataset file")


class SplitManifest(BaseModel):
    """Manifest specifying sample counts and temporal boundaries per split."""
    split_type: str = Field(..., description="chronological, year_based, or event_aware")
    train_range: Dict[str, Optional[str]] = Field(default_factory=dict)
    val_range: Dict[str, Optional[str]] = Field(default_factory=dict)
    test_range: Dict[str, Optional[str]] = Field(default_factory=dict)
    train_rows: int = Field(0)
    val_rows: int = Field(0)
    test_rows: int = Field(0)
    purge_gap_hours: int = Field(24, description="Temporal embargo buffer between splits")


class PreprocessingManifest(BaseModel):
    """Serialized preprocessing parameters fitted strictly on training data."""
    fitted_on_split: str = Field("TRAIN", description="Must be TRAIN to guarantee zero leakage")
    imputation_strategy: str = Field(..., description="DROP, MEDIAN_TRAIN, etc.")
    fitted_statistics: Dict[str, Any] = Field(default_factory=dict, description="Medians/means from train")
    feature_transformations: Dict[str, str] = Field(default_factory=dict)
    training_period: Dict[str, str] = Field(default_factory=dict)
    created_at: str = Field(..., description="Timestamp of fitting")


class LeakageReport(BaseModel):
    """Audit report from LeakageGuard verification."""
    status: str = Field(..., description="PASS or FAIL")
    checks_run: int = Field(..., description="Total leakage invariants audited")
    passed_checks: List[str] = Field(default_factory=list)
    violations: List[str] = Field(default_factory=list)
    checked_at: str = Field(..., description="Timestamp of audit execution")


class SplitStatistics(BaseModel):
    """Statistical summary for a single dataset partition."""
    split_name: str = Field(..., description="TRAIN, VALIDATION, or TEST")
    row_count: int = Field(0)
    grid_cells: int = Field(0)
    time_coverage: Dict[str, str] = Field(default_factory=dict)
    rainfall_mean: float = Field(0.0)
    rainfall_median: float = Field(0.0)
    rainfall_p90: float = Field(0.0)
    rainfall_p95: float = Field(0.0)
    rainfall_p99: float = Field(0.0)
    rainfall_max: float = Field(0.0)
    event_counts: Dict[str, int] = Field(default_factory=dict)
    class_imbalance: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    feature_missingness: Dict[str, float] = Field(default_factory=dict)
