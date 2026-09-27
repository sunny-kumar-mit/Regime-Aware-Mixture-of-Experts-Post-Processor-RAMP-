"""
RAMP Recursive File Discovery & Cataloging Service
SIH26080 | Phase 16 — Real-Data Activation & Operational Ingestion
MoES / NCMRWF

PART C — File Discovery Requirements:
  - Recursive scanning for NetCDF (.nc, .nc4), GRIB (.grib, .grib2, .grb), CSV, Parquet.
  - Identification of:
      provider, model, cycle, initialization_time, valid_time,
      lead_time, variable, resolution, file_path, file_size, checksum.
  - Header inspection (never filenames alone).
  - Explicit labeling of TEST_FIXTURE vs AUTHORITATIVE_PRIMARY.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ml.ingestion.integrity import FileIntegrityEngine
from ml.ingestion.metadata import MetadataValidator
from ml.ingestion.sources import (
    AuthorityLevel,
    DatasetType,
    SourceContract,
    get_authoritative_contract,
    list_authoritative_contracts,
)

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredOperationalFile:
    """Detailed record of an inspected operational meteorological file."""
    file_path: str
    file_name: str
    file_size_bytes: int
    checksum_sha256: str
    format: str              # NetCDF | GRIB | Parquet | CSV | UNKNOWN
    provider: str            # NCMRWF | IMD | NCEP_NOAA | SYNTHETIC | TEST_FIXTURE
    model: str               # NCUM | NEPS | IMD_GRIDDED | GFS
    authority_level: str     # AUTHORITATIVE_PRIMARY | SECONDARY_PROXY | TEST_FIXTURE
    cycle: Optional[str]
    initialization_time: Optional[str]
    valid_time: Optional[str]
    lead_time_hours: Optional[int]
    variables: List[str]
    resolution: Optional[str]
    is_valid_integrity: bool
    is_valid_metadata: bool
    status: str              # DISCOVERED | VALIDATED | REJECTED | TEST_FIXTURE

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DiscoveryCatalog:
    """Catalog of operational files discovered across registered sources."""
    catalog_id: str
    scanned_at: str
    search_roots: List[str]
    total_files_found: int
    authoritative_files_count: int
    test_fixture_files_count: int
    secondary_files_count: int
    files: List[DiscoveredOperationalFile] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["files"] = [f.to_dict() if hasattr(f, "to_dict") else f for f in self.files]
        return d


class OperationalFileDiscoveryService:
    """
    Scans filesystem roots, inspects headers and checksums, and catalogs operational files.
    """

    SUPPORTED_EXTENSIONS = {
        ".nc": "NetCDF",
        ".nc4": "NetCDF",
        ".netcdf": "NetCDF",
        ".grib": "GRIB",
        ".grib2": "GRIB",
        ".grb": "GRIB",
        ".grb2": "GRIB",
        ".parquet": "Parquet",
        ".pq": "Parquet",
        ".csv": "CSV",
    }

    def __init__(self):
        self.integrity_engine = FileIntegrityEngine()
        self.metadata_validator = MetadataValidator()

    def discover_files(
        self,
        search_paths: Optional[List[Path | str]] = None,
        source_id: Optional[str] = None,
    ) -> DiscoveryCatalog:
        """
        Recursively scans provided paths or standard source paths.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        cid = f"CAT_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        if search_paths is None:
            if source_id:
                contract = get_authoritative_contract(source_id)
                search_paths = [contract.root_path] if contract else ["data/raw"]
            else:
                search_paths = [c.root_path for c in list_authoritative_contracts()] + ["data/raw"]

        discovered_list: List[DiscoveredOperationalFile] = []
        authoritative_count = 0
        fixture_count = 0
        secondary_count = 0

        for root in search_paths:
            root_path = Path(root)
            if not root_path.exists():
                continue

            for file_path in root_path.rglob("*"):
                if not file_path.is_file():
                    continue

                ext = file_path.suffix.lower()
                if ext not in self.SUPPORTED_EXTENSIONS:
                    continue

                # Classify authority level based on path and file name
                is_fixture = (
                    "fixture" in str(file_path).lower()
                    or "synthetic" in str(file_path).lower()
                    or "test" in str(file_path).lower()
                )
                if is_fixture:
                    authority = AuthorityLevel.TEST_FIXTURE.value
                    fixture_count += 1
                elif "ncmrwf" in str(file_path).lower() or "imd" in str(file_path).lower():
                    authority = AuthorityLevel.AUTHORITATIVE_PRIMARY.value
                    authoritative_count += 1
                else:
                    authority = AuthorityLevel.SECONDARY_PROXY.value
                    secondary_count += 1

                # 1. Integrity check
                integ_rec = self.integrity_engine.validate_file(file_path)

                # 2. Metadata inspection
                meta_res = self.metadata_validator.extract_and_validate_file(file_path)

                # Infer provider and model
                provider = meta_res.provider or ("NCMRWF" if "ncum" in file_path.name.lower() or "neps" in file_path.name.lower() else "IMD")
                if is_fixture:
                    provider = f"TEST_FIXTURE_{provider}"

                model = meta_res.model or (
                    "NCUM" if "ncum" in file_path.name.lower()
                    else ("NEPS" if "neps" in file_path.name.lower() else "IMD_GRIDDED")
                )

                temp = meta_res.temporal_summary
                cycle = temp.get("cycle")
                init_t = temp.get("initialization_time")
                valid_t = temp.get("valid_time")
                lead_t = temp.get("lead_time_hours")

                status = "TEST_FIXTURE" if is_fixture else ("VALIDATED" if meta_res.is_valid and integ_rec.is_valid else "REJECTED")

                discovered_file = DiscoveredOperationalFile(
                    file_path=str(file_path),
                    file_name=file_path.name,
                    file_size_bytes=integ_rec.file_size_bytes,
                    checksum_sha256=integ_rec.checksum_sha256,
                    format=self.SUPPORTED_EXTENSIONS.get(ext, "UNKNOWN"),
                    provider=provider,
                    model=model,
                    authority_level=authority,
                    cycle=cycle,
                    initialization_time=init_t,
                    valid_time=valid_t,
                    lead_time_hours=lead_t,
                    variables=meta_res.variables_present,
                    resolution=meta_res.spatial_summary.get("target_resolution", "0.25deg"),
                    is_valid_integrity=integ_rec.is_valid,
                    is_valid_metadata=meta_res.is_valid,
                    status=status,
                )
                discovered_list.append(discovered_file)

        return DiscoveryCatalog(
            catalog_id=cid,
            scanned_at=now_iso,
            search_roots=[str(p) for p in search_paths],
            total_files_found=len(discovered_list),
            authoritative_files_count=authoritative_count,
            test_fixture_files_count=fixture_count,
            secondary_files_count=secondary_count,
            files=discovered_list,
        )
