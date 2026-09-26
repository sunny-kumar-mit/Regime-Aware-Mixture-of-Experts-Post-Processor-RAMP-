"""
RAMP Data Manifest Manager
SIH26080 | Dataset Registry and Provenance Index

Rules:
  - "available" status only if the actual data file/feed exists and was validated.
  - "configured" if configuration is present but data has not been verified yet.
  - Do NOT claim "available" for NCMRWF data if real files are not present.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from ramp.ingestion.base import DataMode, ProviderStatus, ProviderType

logger = logging.getLogger("ramp.validation.manifest")

MANIFEST_PATH = Path("data/metadata/datasets/data_manifest.json")


@dataclass
class DatasetEntry:
    """Single dataset record in the manifest."""
    id: str
    name: str
    provider: str
    provider_type: str           # "nwp" | "observation" | "auxiliary"
    variables: List[str]
    time_range_start: Optional[str] = None
    time_range_end: Optional[str] = None
    spatial_domain: str = "India"
    resolution_deg: Optional[float] = None
    file_format: str = "netcdf"
    status: str = ProviderStatus.NOT_CONFIGURED.value
    data_mode: str = DataMode.REAL.value
    checksum_sha256: Optional[str] = None
    source_url: Optional[str] = None
    notes: str = ""
    last_validated: Optional[str] = None
    n_files: int = 0
    size_bytes: int = 0


@dataclass
class DataManifest:
    """Top-level manifest holding all known datasets."""
    version: str = "1.0"
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    description: str = (
        "RAMP (SIH26080) Data Manifest — registry of all known meteorological datasets"
    )
    datasets: List[DatasetEntry] = field(default_factory=list)

    def get_dataset(self, dataset_id: str) -> Optional[DatasetEntry]:
        for ds in self.datasets:
            if ds.id == dataset_id:
                return ds
        return None

    def upsert_dataset(self, entry: DatasetEntry) -> None:
        for i, ds in enumerate(self.datasets):
            if ds.id == entry.id:
                self.datasets[i] = entry
                return
        self.datasets.append(entry)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "description": self.description,
            "datasets": [asdict(ds) for ds in self.datasets],
        }


def load_manifest(path: Path = MANIFEST_PATH) -> DataManifest:
    """Load manifest from disk, returning an empty manifest if file doesn't exist."""
    if not path.exists():
        logger.debug("No manifest found at %s — creating empty manifest.", path)
        return _build_default_manifest()
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        manifest = DataManifest(
            version=raw.get("version", "1.0"),
            generated_at=raw.get("generated_at", ""),
            description=raw.get("description", ""),
            datasets=[DatasetEntry(**ds) for ds in raw.get("datasets", [])],
        )
        logger.info("Loaded manifest with %d datasets from %s", len(manifest.datasets), path)
        return manifest
    except Exception as exc:
        logger.error("Failed to load manifest: %s — returning default.", exc)
        return _build_default_manifest()


def save_manifest(manifest: DataManifest, path: Path = MANIFEST_PATH) -> None:
    """Save manifest to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest.generated_at = datetime.now(timezone.utc).isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)
    logger.info("Saved manifest with %d datasets to %s", len(manifest.datasets), path)


def _build_default_manifest() -> DataManifest:
    """Build the initial manifest with all known providers as NOT_CONFIGURED."""
    manifest = DataManifest()
    manifest.datasets = [
        DatasetEntry(
            id="imd_rainfall_025",
            name="IMD 0.25° Gridded Daily Rainfall",
            provider="IMD",
            provider_type=ProviderType.OBSERVATION.value,
            variables=["observed_rainfall_mm"],
            resolution_deg=0.25,
            file_format="netcdf",
            status=ProviderStatus.NOT_CONFIGURED.value,
            notes=(
                "IMD gridded rainfall dataset at 0.25° resolution. "
                "Place NetCDF files in data/raw/observations/imd/ and run validate."
            ),
        ),
        DatasetEntry(
            id="gfs_025",
            name="NOAA GFS 0.25° Forecast",
            provider="GFS",
            provider_type=ProviderType.NWP.value,
            variables=["precip_nwp_raw", "u850", "v850", "u200", "v200", "mslp",
                       "t850", "t500", "q850", "q700", "pw", "cape"],
            resolution_deg=0.25,
            file_format="grib2",
            status=ProviderStatus.NOT_CONFIGURED.value,
            source_url="https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl",
            notes=(
                "GFS 0.25° GRIB2 files. Place in data/raw/nwp/gfs/ or configure source URL."
            ),
        ),
        DatasetEntry(
            id="gefs_05",
            name="NOAA GEFS 0.5° Ensemble Forecast",
            provider="GEFS",
            provider_type=ProviderType.NWP.value,
            variables=["precip_nwp_raw", "u850", "v850", "u200", "mslp", "t850"],
            resolution_deg=0.5,
            file_format="grib2",
            status=ProviderStatus.NOT_CONFIGURED.value,
            source_url="https://nomads.ncep.noaa.gov/cgi-bin/filter_gefs_atm.pl",
            notes="GEFS 31-member ensemble GRIB2 files. Place in data/raw/nwp/gefs/.",
        ),
        DatasetEntry(
            id="ncmrwf_ncum",
            name="NCMRWF NCUM Deterministic Forecast",
            provider="NCMRWF",
            provider_type=ProviderType.NWP.value,
            variables=["precip_nwp_raw", "u850", "v850", "u200", "v200", "mslp",
                       "t850", "t500", "q850", "q700", "pw", "cape", "vort850"],
            resolution_deg=0.12,
            file_format="netcdf",
            status=ProviderStatus.UNAVAILABLE.value,
            notes=(
                "NCMRWF NCUM NetCDF files require institutional access. "
                "Data is NOT available in this environment. "
                "Place NCUM NetCDF files in data/raw/nwp/ncmrwf/ when available. "
                "This adapter will NOT fabricate data as a substitute."
            ),
        ),
        DatasetEntry(
            id="ncmrwf_neps",
            name="NCMRWF NEPS Ensemble Forecast",
            provider="NCMRWF",
            provider_type=ProviderType.NWP.value,
            variables=["precip_nwp_raw", "u850", "v850", "u200", "v200", "mslp", "t850"],
            resolution_deg=0.12,
            file_format="netcdf",
            status=ProviderStatus.UNAVAILABLE.value,
            notes=(
                "NCMRWF NEPS ensemble requires institutional data access. "
                "NOT available in this environment. WILL NOT be fabricated."
            ),
        ),
    ]
    return manifest
