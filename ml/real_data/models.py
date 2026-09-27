"""
RAMP Real Data Lab Data Models & Schema Contracts
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF | Phase 19

Defines type-safe Enums, Records, Manifests, and Failure Taxonomies
governing genuine meteorological file ingestion, validation, mapping,
and experimental inference runs.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class ProviderType(str, enum.Enum):
    NCMRWF = "NCMRWF"
    IMD = "IMD"
    OTHER_AUTHORIZED_SOURCE = "OTHER_AUTHORIZED_SOURCE"


class SourceType(str, enum.Enum):
    NCUM = "NCUM"
    NEPS = "NEPS"
    IMD_OBSERVATION = "IMD_OBSERVATION"
    OTHER = "OTHER"


class AuthorityLevel(str, enum.Enum):
    AUTHORITATIVE_PRIMARY = "AUTHORITATIVE_PRIMARY"
    SECONDARY = "SECONDARY"
    TEST_FIXTURE = "TEST_FIXTURE"


class DataMode(str, enum.Enum):
    SYNTHETIC_DEMO = "SYNTHETIC_DEMO"
    REAL_DATA_EXPERIMENT = "REAL_DATA_EXPERIMENT"
    STAGING_REAL_DATA = "STAGING_REAL_DATA"
    REAL_OPERATIONAL_ACTIVE = "REAL_OPERATIONAL_ACTIVE"
    BLOCKED = "BLOCKED"


class ValidationStatus(str, enum.Enum):
    PENDING = "PENDING"
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    SAMPLE_LIMITED = "SAMPLE_LIMITED"
    REJECTED = "REJECTED"
    PROMOTED = "PROMOTED"


class FailureStage(str, enum.Enum):
    NONE = "NONE"
    IMPORT_FAILED = "IMPORT_FAILED"
    FORMAT_FAILED = "FORMAT_FAILED"
    METADATA_FAILED = "METADATA_FAILED"
    FEATURE_MAPPING_FAILED = "FEATURE_MAPPING_FAILED"
    MISSING_FEATURE = "MISSING_FEATURE"
    UNIT_FAILED = "UNIT_FAILED"
    GRID_FAILED = "GRID_FAILED"
    TIME_FAILED = "TIME_FAILED"
    QC_FAILED = "QC_FAILED"
    PAIRING_FAILED = "PAIRING_FAILED"
    MODEL_LOAD_FAILED = "MODEL_LOAD_FAILED"
    INFERENCE_FAILED = "INFERENCE_FAILED"
    OUTPUT_VALIDATION_FAILED = "OUTPUT_VALIDATION_FAILED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"


class FeatureMappingStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    MISSING = "MISSING"
    EXTRA = "EXTRA"
    MAPPED = "MAPPED"
    UNIT_CONVERSION_REQUIRED = "UNIT_CONVERSION_REQUIRED"
    SPATIAL_REGRID_REQUIRED = "SPATIAL_REGRID_REQUIRED"
    TEMPORAL_ALIGNMENT_REQUIRED = "TEMPORAL_ALIGNMENT_REQUIRED"
    UNSUPPORTED = "UNSUPPORTED"


class FeatureMappingItem(BaseModel):
    ramp_feature: str
    source_variable: Optional[str] = None
    unit: Optional[str] = None
    source_grid: Optional[str] = None
    status: FeatureMappingStatus
    notes: Optional[str] = None


class GridValidationRecord(BaseModel):
    is_valid: bool
    source_grid_dims: Tuple[int, int] = (0, 0)
    target_grid_dims: Tuple[int, int] = (129, 137)
    resolution_deg: float = 0.25
    lat_bounds: Tuple[float, float] = (6.0, 38.0)
    lon_bounds: Tuple[float, float] = (68.0, 97.0)
    regrid_required: bool = False
    regrid_method: Optional[str] = None
    regrid_library: Optional[str] = None
    regrid_config: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class TransformationRecord(BaseModel):
    source_unit: str
    target_unit: str
    conversion_formula: str
    reason: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ValidationErrorDetail(BaseModel):
    source: str  # NCUM, NEPS, IMD
    dataset: str  # NCUM_GLOBAL, IMD_RAINFALL_025, etc.
    rule: str  # GRID_COORDINATES, NON_NEGATIVE_RAINFALL, FEATURE_CONTRACT, TIME_CONSISTENCY, etc.
    severity: str = "ERROR"  # ERROR, WARNING, BLOCKING
    variable: Optional[str] = None
    message: str
    expected: str
    actual: str
    location: Optional[str] = None
    remediation: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ImportedFileRecord(BaseModel):
    import_id: str
    source_id: str
    filename: str
    filepath: str
    provider: ProviderType
    source_type: SourceType
    authority_level: AuthorityLevel
    format: str
    size_bytes: int
    sha256: str
    import_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data_mode: DataMode
    validation_status: ValidationStatus = ValidationStatus.PENDING
    validation_notes: List[str] = Field(default_factory=list)
    validation_error_detail: Optional[ValidationErrorDetail] = None
    failure_stage: FailureStage = FailureStage.NONE
    cycle: Optional[str] = None
    initialization_time: Optional[str] = None
    valid_time: Optional[str] = None
    lead_time_hours: Optional[int] = None
    variables: List[str] = Field(default_factory=list)
    dimensions: Dict[str, int] = Field(default_factory=dict)
    lat_range: Optional[Tuple[float, float]] = None
    lon_range: Optional[Tuple[float, float]] = None
    resolution: Optional[float] = None
    units_map: Dict[str, str] = Field(default_factory=dict)
    feature_mappings: List[FeatureMappingItem] = Field(default_factory=list)
    is_ground_truth_only: bool = False
    promoted_path: Optional[str] = None
    rejected_path: Optional[str] = None
    rejected_reason: Optional[str] = None


class ExperimentRunRecord(BaseModel):
    run_id: str
    source_id: str
    provider: str
    file_hash: str
    cycle: Optional[str] = None
    lead_hours: Optional[int] = None
    initialization_time: Optional[str] = None
    valid_time: Optional[str] = None
    features_count: int = 0
    missing_features: List[str] = Field(default_factory=list)
    model_version: str = "v2.0.0"
    status: str = "RUNNING"
    failure_stage: FailureStage = FailureStage.NONE
    failure_detail: Optional[str] = None
    runtime_ms: float = 0.0
    output_hash: Optional[str] = None
    verification_status: str = "NOT_AVAILABLE"
    data_mode: DataMode = DataMode.REAL_DATA_EXPERIMENT
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    manifest_path: Optional[str] = None
    report_path: Optional[str] = None


class ExperimentRunManifest(BaseModel):
    run_id: str
    source_id: str
    provider: str
    file_hash: str
    cycle: Optional[str] = None
    lead_hours: Optional[int] = None
    initialization_time: Optional[str] = None
    valid_time: Optional[str] = None
    variables: List[str] = Field(default_factory=list)
    feature_mapping: Dict[str, str] = Field(default_factory=dict)
    unit_mapping: Dict[str, str] = Field(default_factory=dict)
    grid_mapping: Dict[str, Any] = Field(default_factory=dict)
    observation_pair: Optional[Dict[str, Any]] = None
    model_version: str = "v2.0.0"
    feature_contract: str = "ramp_features_v1.0.0"
    target_contract: str = "ramp_targets_v1.0.0"
    output_hash: Optional[str] = None
    verification: Optional[Dict[str, Any]] = None
    runtime_ms: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
