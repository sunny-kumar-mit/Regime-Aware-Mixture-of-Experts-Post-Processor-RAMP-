"""
RAMP Operational Data Plane — Data Sources & Provider Hierarchy
SIH26080 | Phase 11 — Real Data Activation & Operational Data Plane
MoES / NCMRWF

Enforces:
1. Strict provider hierarchy (PRIMARY -> SECONDARY -> DEMO).
2. Explicit DataMode tagging (REAL_OPERATIONAL, REAL_ARCHIVE, PUBLIC_PROXY, SYNTHETIC_DEMO, NOT_AVAILABLE).
3. Scientific integrity: Never substitute sources silently; never label PUBLIC_PROXY as NCMRWF.
4. Complete metadata and chain-of-custody provenance schema.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


# =============================================================================
# Operational Data Modes
# =============================================================================

class DataMode(str, Enum):
    """
    Operational data mode contract.
    Strictly prevents misattribution and synthetic data masquerading as real.
    """
    REAL_OPERATIONAL = "REAL_OPERATIONAL"  # Real NCMRWF/IMD operational stream
    REAL_ARCHIVE = "REAL_ARCHIVE"          # Historical real datasets (IMD gridded / NCMRWF reanalysis)
    PUBLIC_PROXY = "PUBLIC_PROXY"          # Real public NWP/obs (GFS/ERA5/GEFS) — NEVER label as NCMRWF
    SYNTHETIC_DEMO = "SYNTHETIC_DEMO"      # Artificial physics-informed demonstration data
    NOT_AVAILABLE = "NOT_AVAILABLE"        # No valid data source present

    # Backward compatibility alias
    REAL = "REAL_OPERATIONAL"


class ProviderTier(str, Enum):
    """Operational provider priority tier."""
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    DEMO = "DEMO"


class ProviderCategory(str, Enum):
    NWP_DETERMINISTIC = "NWP_DETERMINISTIC"
    NWP_ENSEMBLE = "NWP_ENSEMBLE"
    OBSERVATION_GRIDDED = "OBSERVATION_GRIDDED"
    DEMO_GENERATOR = "DEMO_GENERATOR"


# =============================================================================
# Provider Specification
# =============================================================================

@dataclass(frozen=True)
class ProviderSpec:
    provider_id: str
    name: str
    organization: str
    tier: ProviderTier
    category: ProviderCategory
    model_name: str
    native_resolution_deg: float
    canonical_resolution_deg: float = 0.25
    expected_dir: str = ""
    is_operational_primary: bool = False
    description: str = ""
    allowed_data_modes: List[DataMode] = field(default_factory=list)


# Authoritative Provider Registry and Hierarchy
SOURCE_PROVIDER_SPECS: Dict[str, ProviderSpec] = {
    # ── PRIMARY ─────────────────────────────────────────────────────────────
    "ncmrwf_ncum": ProviderSpec(
        provider_id="ncmrwf_ncum",
        name="NCMRWF NCUM Unified Model (Deterministic)",
        organization="NCMRWF / MoES",
        tier=ProviderTier.PRIMARY,
        category=ProviderCategory.NWP_DETERMINISTIC,
        model_name="NCUM",
        native_resolution_deg=0.12,  # ~12 km native resolution
        canonical_resolution_deg=0.25,
        expected_dir="data/raw/nwp/ncmrwf/ncum",
        is_operational_primary=True,
        description="NCMRWF operational deterministic numerical weather prediction model.",
        allowed_data_modes=[DataMode.REAL_OPERATIONAL, DataMode.REAL_ARCHIVE, DataMode.NOT_AVAILABLE],
    ),
    "ncmrwf_neps": ProviderSpec(
        provider_id="ncmrwf_neps",
        name="NCMRWF NEPS Ensemble Prediction System",
        organization="NCMRWF / MoES",
        tier=ProviderTier.PRIMARY,
        category=ProviderCategory.NWP_ENSEMBLE,
        model_name="NEPS",
        native_resolution_deg=0.12,  # ~12 km ensemble members
        canonical_resolution_deg=0.25,
        expected_dir="data/raw/nwp/ncmrwf/neps",
        is_operational_primary=True,
        description="NCMRWF operational 23-member ensemble prediction system.",
        allowed_data_modes=[DataMode.REAL_OPERATIONAL, DataMode.REAL_ARCHIVE, DataMode.NOT_AVAILABLE],
    ),
    "imd_obs": ProviderSpec(
        provider_id="imd_obs",
        name="IMD 0.25° Gridded Daily Rainfall Observations",
        organization="India Meteorological Department (IMD) / MoES",
        tier=ProviderTier.PRIMARY,
        category=ProviderCategory.OBSERVATION_GRIDDED,
        model_name="IMD_GRIDDED_OBS",
        native_resolution_deg=0.25,
        canonical_resolution_deg=0.25,
        expected_dir="data/raw/observations/imd",
        is_operational_primary=True,
        description="Official IMD daily gridded observed rainfall (ground truth).",
        allowed_data_modes=[DataMode.REAL_OPERATIONAL, DataMode.REAL_ARCHIVE, DataMode.NOT_AVAILABLE],
    ),

    # ── SECONDARY ───────────────────────────────────────────────────────────
    "gfs": ProviderSpec(
        provider_id="gfs",
        name="NCEP Global Forecast System (GFS)",
        organization="NOAA / NCEP",
        tier=ProviderTier.SECONDARY,
        category=ProviderCategory.NWP_DETERMINISTIC,
        model_name="GFS",
        native_resolution_deg=0.25,
        canonical_resolution_deg=0.25,
        expected_dir="data/raw/nwp/gfs",
        is_operational_primary=False,
        description="Public proxy/backup NWP deterministic forecast. NEVER label as NCMRWF.",
        allowed_data_modes=[DataMode.PUBLIC_PROXY, DataMode.NOT_AVAILABLE],
    ),
    "gefs": ProviderSpec(
        provider_id="gefs",
        name="NCEP Global Ensemble Forecast System (GEFS)",
        organization="NOAA / NCEP",
        tier=ProviderTier.SECONDARY,
        category=ProviderCategory.NWP_ENSEMBLE,
        model_name="GEFS",
        native_resolution_deg=0.50,
        canonical_resolution_deg=0.25,
        expected_dir="data/raw/nwp/gefs",
        is_operational_primary=False,
        description="Public proxy/backup NWP ensemble forecast. NEVER label as NCMRWF.",
        allowed_data_modes=[DataMode.PUBLIC_PROXY, DataMode.NOT_AVAILABLE],
    ),

    # ── DEMO ────────────────────────────────────────────────────────────────
    "synthetic_demo": ProviderSpec(
        provider_id="synthetic_demo",
        name="Synthetic Meteorological Demo Generator",
        organization="RAMP Core System",
        tier=ProviderTier.DEMO,
        category=ProviderCategory.DEMO_GENERATOR,
        model_name="SYNTHETIC_DEMO",
        native_resolution_deg=0.25,
        canonical_resolution_deg=0.25,
        expected_dir="data/processed",
        is_operational_primary=False,
        description="Synthetic demonstration generator for offline development and UI testing.",
        allowed_data_modes=[DataMode.SYNTHETIC_DEMO],
    ),
}


# =============================================================================
# Dataset Metadata Schema (Contract Required by Section 1)
# =============================================================================

@dataclass
class OperationalDatasetMetadata:
    """
    Standard dataset contract required for every ingested or discovered dataset.
    Never silently omit any field.
    """
    source_provider: str              # e.g. "NCMRWF", "IMD", "NOAA"
    source_model: str                 # e.g. "NCUM", "NEPS", "IMD_GRIDDED_OBS", "GFS"
    initialization_time: str          # ISO 8601 UTC
    forecast_valid_time: str          # ISO 8601 UTC (init + lead)
    cycle: str                        # e.g. "00 UTC", "06 UTC", "12 UTC", "18 UTC"
    lead_time_hours: int              # Lead time in hours (0 for observations)
    native_resolution: float          # e.g. 0.12 or 0.25
    target_resolution: float = 0.25   # RAMP canonical resolution
    variables: List[str] = field(default_factory=list)
    units: Dict[str, str] = field(default_factory=dict)
    data_mode: str = DataMode.NOT_AVAILABLE.value
    file_name: str = ""
    file_hash: str = ""               # SHA256 checksum
    ingestion_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z"
    )
    quality_status: str = "VALID"     # VALID, VALID_EXTREME, SUSPICIOUS, CORRUPTED, EMPTY
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# Provider Hierarchy Manager
# =============================================================================

class ProviderHierarchy:
    """
    Enforces the explicit provider priority rules:
      PRIMARY (NCUM, NEPS, IMD) > SECONDARY (GFS, GEFS) > DEMO (SYNTHETIC_DEMO).
    """

    @classmethod
    def get_provider(cls, provider_id: str) -> Optional[ProviderSpec]:
        return SOURCE_PROVIDER_SPECS.get(provider_id.lower())

    @classmethod
    def list_providers(cls) -> List[Dict[str, Any]]:
        results = []
        for p in SOURCE_PROVIDER_SPECS.values():
            results.append({
                "provider_id": p.provider_id,
                "name": p.name,
                "organization": p.organization,
                "tier": p.tier.value,
                "category": p.category.value,
                "model_name": p.model_name,
                "native_resolution_deg": p.native_resolution_deg,
                "canonical_resolution_deg": p.canonical_resolution_deg,
                "expected_dir": p.expected_dir,
                "is_operational_primary": p.is_operational_primary,
                "description": p.description,
            })
        return results

    @classmethod
    def validate_mode_for_provider(cls, provider_id: str, proposed_mode: DataMode) -> DataMode:
        """
        Guards against mislabeling:
        - Never label GFS/GEFS as NCMRWF or REAL_OPERATIONAL.
        - Never label synthetic demo as REAL_OPERATIONAL or REAL_ARCHIVE.
        """
        spec = cls.get_provider(provider_id)
        if not spec:
            return DataMode.NOT_AVAILABLE

        if proposed_mode not in spec.allowed_data_modes:
            if spec.tier == ProviderTier.SECONDARY and proposed_mode in (DataMode.REAL_OPERATIONAL, DataMode.REAL_ARCHIVE):
                # Enforce: secondary sources must be PUBLIC_PROXY, never operational MoES/NCMRWF
                return DataMode.PUBLIC_PROXY
            if spec.tier == ProviderTier.DEMO:
                return DataMode.SYNTHETIC_DEMO
            return DataMode.NOT_AVAILABLE

        return proposed_mode
