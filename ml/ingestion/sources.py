"""
RAMP Authoritative Data Source Contract & Provider Specifications
SIH26080 | Phase 16 — Real-Data Activation & Operational Ingestion
MoES / NCMRWF

Defines explicit authoritative providers:
  - NCMRWF_NCUM: Deterministic Numerical Weather Prediction (~12 km / 0.25° canonical)
  - NCMRWF_NEPS: Ensemble Prediction System (23 members, ~12 km / 0.25° canonical)
  - IMD_GRIDDED_RAINFALL: IMD Daily Gridded Rainfall Observation (0.25° canonical)

Scientific Integrity Rules:
  1. Authoritative status cannot be spoofed or inherited by secondary providers.
  2. Availability is dynamically determined by filesystem and integrity audits.
  3. No secondary provider (GFS, GEFS, ERA5) may ever be relabeled as NCMRWF or IMD.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class AuthorityLevel(str, Enum):
    """Authority tier of meteorological data sources."""
    AUTHORITATIVE_PRIMARY = "AUTHORITATIVE_PRIMARY"  # NCMRWF/IMD authoritative operational archives
    SECONDARY_PROXY = "SECONDARY_PROXY"              # GFS/ERA5 (development proxy only; NEVER NCMRWF)
    TEST_FIXTURE = "TEST_FIXTURE"                    # Synthetic pipeline verification fixtures only


class SourceStatus(str, Enum):
    """Dynamic operational status of data sources."""
    UNAVAILABLE = "UNAVAILABLE"                      # Data directory empty or not mounted
    DETECTED = "DETECTED"                            # Files discovered on filesystem
    VALIDATING = "VALIDATING"                        # Integrity, metadata, and QC checks underway
    VALIDATED = "VALIDATED"                          # All pre-ingestion checks passed
    ACTIVE = "ACTIVE"                                # Authorized and in active ingestion
    BLOCKED = "BLOCKED"                              # Failed integrity/metadata/QC or security check
    DEGRADED = "DEGRADED"                            # Partial coverage or intermittent missing files


class DatasetType(str, Enum):
    """Category of meteorological data product."""
    NWP_DETERMINISTIC = "NWP_DETERMINISTIC"
    NWP_ENSEMBLE = "NWP_ENSEMBLE"
    OBSERVATION_GRIDDED = "OBSERVATION_GRIDDED"
    TEST_FIXTURE = "TEST_FIXTURE"


# Canonical 18 predictors required by ramp_features_v1.0.0
CANONICAL_18_PREDICTORS: List[str] = [
    "precip_nwp_raw",
    "u850",
    "v850",
    "mslp",
    "t850",
    "cape",
    "wind_speed_850",
    "wind_dir_850",
    "lead_time_hours",
    "latitude",
    "longitude",
    "elevation_m",
    "day_of_year_sin",
    "day_of_year_cos",
    "zonal_shear",
    "monsoon_trough_intensity",
    "meridional_flow",
    "humidity_proxy",
]


@dataclass
class SourceContract:
    """
    Authoritative source contract declaring all metadata, resolution,
    and schema requirements for an operational meteorological source.
    """
    source_id: str
    provider: str
    model: str
    dataset_type: DatasetType
    resolution: str
    variables: List[str]
    units: Dict[str, str]
    expected_format: List[str]
    root_path: str
    authority_level: AuthorityLevel
    enabled: bool = True
    status: SourceStatus = SourceStatus.UNAVAILABLE
    description: str = ""
    target_grid_deg: float = 0.25
    allow_regridding: bool = False
    regridding_method: Optional[str] = None
    extra_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["dataset_type"] = self.dataset_type.value
        d["authority_level"] = self.authority_level.value
        d["status"] = self.status.value
        return d


# Authoritative Primary Providers for SIH26080
AUTHORITATIVE_SOURCE_CONTRACTS: Dict[str, SourceContract] = {
    "NCMRWF_NCUM": SourceContract(
        source_id="NCMRWF_NCUM",
        provider="NCMRWF",
        model="NCUM",
        dataset_type=DatasetType.NWP_DETERMINISTIC,
        resolution="0.12deg",
        variables=CANONICAL_18_PREDICTORS,
        units={
            "precip_nwp_raw": "mm",
            "u850": "m/s",
            "v850": "m/s",
            "mslp": "hPa",
            "t850": "K",
            "cape": "J/kg",
            "wind_speed_850": "m/s",
            "wind_dir_850": "deg",
            "lead_time_hours": "hours",
            "latitude": "deg_N",
            "longitude": "deg_E",
            "elevation_m": "m",
            "day_of_year_sin": "dimensionless",
            "day_of_year_cos": "dimensionless",
            "zonal_shear": "m/s",
            "monsoon_trough_intensity": "hPa",
            "meridional_flow": "m/s",
            "humidity_proxy": "dimensionless",
        },
        expected_format=[".nc", ".nc4", ".grib2", ".grb2"],
        root_path="data/raw/nwp/ncmrwf/ncum",
        authority_level=AuthorityLevel.AUTHORITATIVE_PRIMARY,
        enabled=True,
        status=SourceStatus.UNAVAILABLE,
        description="NCMRWF Unified Model operational deterministic NWP forecast (~12 km native resolution).",
        target_grid_deg=0.25,
        allow_regridding=True,
        regridding_method="bilinear",
    ),
    "NCMRWF_NEPS": SourceContract(
        source_id="NCMRWF_NEPS",
        provider="NCMRWF",
        model="NEPS",
        dataset_type=DatasetType.NWP_ENSEMBLE,
        resolution="0.12deg",
        variables=["precip_nwp_ensemble_member", "lead_time_hours", "latitude", "longitude"],
        units={
            "precip_nwp_ensemble_member": "mm",
            "lead_time_hours": "hours",
            "latitude": "deg_N",
            "longitude": "deg_E",
        },
        expected_format=[".nc", ".nc4", ".grib2", ".grb2"],
        root_path="data/raw/nwp/ncmrwf/neps",
        authority_level=AuthorityLevel.AUTHORITATIVE_PRIMARY,
        enabled=True,
        status=SourceStatus.UNAVAILABLE,
        description="NCMRWF Ensemble Prediction System 23-member NWP forecast ensemble.",
        target_grid_deg=0.25,
        allow_regridding=True,
        regridding_method="bilinear",
    ),
    "IMD_GRIDDED_RAINFALL": SourceContract(
        source_id="IMD_GRIDDED_RAINFALL",
        provider="IMD",
        model="IMD_GRIDDED",
        dataset_type=DatasetType.OBSERVATION_GRIDDED,
        resolution="0.25deg",
        variables=["observed_rainfall_mm", "latitude", "longitude", "valid_date"],
        units={
            "observed_rainfall_mm": "mm",
            "latitude": "deg_N",
            "longitude": "deg_E",
            "valid_date": "YYYY-MM-DD",
        },
        expected_format=[".nc", ".nc4", ".grd", ".csv", ".parquet"],
        root_path="data/raw/observations/imd",
        authority_level=AuthorityLevel.AUTHORITATIVE_PRIMARY,
        enabled=True,
        status=SourceStatus.UNAVAILABLE,
        description="Official IMD 0.25° gridded daily rainfall ground truth observation.",
        target_grid_deg=0.25,
        allow_regridding=False,
    ),
}

# Secondary Proxy Providers (Development & Synthetic fallback only; NEVER authoritative)
SECONDARY_SOURCE_CONTRACTS: Dict[str, SourceContract] = {
    "GFS_DETERMINISTIC": SourceContract(
        source_id="GFS_DETERMINISTIC",
        provider="NCEP_NOAA",
        model="GFS",
        dataset_type=DatasetType.NWP_DETERMINISTIC,
        resolution="0.25deg",
        variables=CANONICAL_18_PREDICTORS,
        units={"precip_nwp_raw": "mm"},
        expected_format=[".nc", ".grib2"],
        root_path="data/raw/nwp/gfs",
        authority_level=AuthorityLevel.SECONDARY_PROXY,
        enabled=False,
        status=SourceStatus.UNAVAILABLE,
        description="Public proxy GFS NWP. NEVER classify or label as NCMRWF.",
    ),
}


def get_authoritative_contract(source_id: str) -> Optional[SourceContract]:
    """Retrieve authoritative contract by source_id."""
    return AUTHORITATIVE_SOURCE_CONTRACTS.get(source_id)


def list_authoritative_contracts() -> List[SourceContract]:
    """List all registered primary authoritative contracts."""
    return list(AUTHORITATIVE_SOURCE_CONTRACTS.values())
