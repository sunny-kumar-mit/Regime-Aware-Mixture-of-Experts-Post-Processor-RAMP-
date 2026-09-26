"""
RAMP Typed API Contracts and Schemas
SIH26080 | Pydantic Models for All Pipeline Boundaries
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class DataMode(str, Enum):
    """Operational data mode tag adhering to scientific integrity rules."""
    SYNTHETIC_DEMO = "SYNTHETIC_DEMO"
    REAL = "REAL"


class RegimeType(str, Enum):
    """7 Weather Regimes specified for Indian Monsoon Post-Processing."""
    ACTIVE_MONSOON = "ACTIVE_MONSOON"
    BREAK_MONSOON = "BREAK_MONSOON"
    MONSOON_LOW_DEPRESSION = "MONSOON_LOW_DEPRESSION"
    COASTAL_RAINFALL = "COASTAL_RAINFALL"
    OROGRAPHIC_RAINFALL = "OROGRAPHIC_RAINFALL"
    WESTERN_DISTURBANCE = "WESTERN_DISTURBANCE"
    TRANSITION_OTHER = "TRANSITION_OTHER"


class BaselineModel(str, Enum):
    """Supported models for comparative benchmark evaluation."""
    RAW_NWP = "raw_nwp"
    MEAN_BIAS = "mean_bias"
    QMAP = "qmap"
    GLOBAL_ML = "global_ml"
    RAMP = "ramp"


# =============================================================================
# Core System Contracts
# =============================================================================

class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str = Field(default="healthy", description="Service health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Deployment environment")
    data_mode: DataMode = Field(..., description="Current data pipeline integrity mode")


class SystemInfoResponse(BaseModel):
    """Detailed system metadata and configuration contract."""
    app_name: str
    description: str
    version: str
    environment: str
    organization: str
    department: str
    data_mode: DataMode
    active_regimes: List[RegimeType]
    imd_thresholds_mm_per_24h: Dict[str, float]
    supported_baselines: List[BaselineModel]
    pipeline_stages: List[str]


# =============================================================================
# Pipeline Contracts (Future Phases Type Definitions)
# =============================================================================

class RegimeProbabilityResponse(BaseModel):
    """Soft probability distribution over all 7 regimes (must sum to 1.0)."""
    forecast_id: str
    probabilities: Dict[RegimeType, float]
    dominant_regime: RegimeType
    entropy: float
    data_mode: DataMode
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExtremeProbabilityResponse(BaseModel):
    """Exceedance probability for IMD extreme rainfall thresholds."""
    forecast_id: str
    prob_heavy_gte_64_5mm: float
    prob_very_heavy_gte_115_6mm: float
    prob_extremely_heavy_gte_204_5mm: float
    data_mode: DataMode


class VerificationScoreResponse(BaseModel):
    """Statistical verification scores computed against IMD observations."""
    model_name: BaselineModel
    date_range_start: str
    date_range_end: str
    rmse: float
    csi_heavy: float
    pod_heavy: float
    far_heavy: float
    ets_heavy: float
    fss_50km: float
    data_mode: DataMode
