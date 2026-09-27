"""
RAMP Authoritative Data Mount Validation & Provenance Tracking
SIH26080 | Phase 18 — Real-Data Activation & Institutional Acceptance Testing
MoES / NCMRWF

PART A: Authoritative Data Mount Validation
PART B: Authoritative Source Provenance
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MountClassification(str, Enum):
    UNMOUNTED = "UNMOUNTED"
    EMPTY = "EMPTY"
    CONNECTED = "CONNECTED"
    PARTIAL = "PARTIAL"
    INVALID = "INVALID"
    AVAILABLE = "AVAILABLE"


class AuthorityLevel(str, Enum):
    AUTHORITATIVE_PRIMARY = "AUTHORITATIVE_PRIMARY"
    SECONDARY_PROXY = "SECONDARY_PROXY"
    TEST_FIXTURE = "TEST_FIXTURE"


# Alias for backward compatibility
MountStatus = MountClassification


@dataclass
class SourceProvenanceRecord:
    provider: str
    source_id: str
    authority_level: str  # AUTHORITATIVE_PRIMARY | SECONDARY_PROXY | TEST_FIXTURE
    source_identifier: str
    filename: str
    size_bytes: int
    modified_time: str
    format: str
    sha256: str
    metadata_status: str  # VALID | INVALID | PENDING
    qc_status: str        # PASS | FAIL | NOT_EVALUATED
    discovery_timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SourceMountAudit:
    source_id: str
    provider: str
    model: str
    expected_paths: List[str]
    actual_path: Optional[str]
    exists: bool
    is_mounted: bool
    is_readable: bool
    file_count: int
    latest_file: Optional[str]
    latest_file_size_bytes: Optional[int]
    latest_file_format: Optional[str]
    latest_file_checksum: Optional[str]
    metadata_status: str
    qc_status: str
    classification: str  # UNMOUNTED | EMPTY | CONNECTED | PARTIAL | INVALID | AVAILABLE
    can_activate_real: bool
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


EXPECTED_SOURCE_TARGETS = [
    {
        "source_id": "NCMRWF_NCUM",
        "provider": "NCMRWF",
        "model": "NCUM",
        "expected_paths": ["/data/ncmrwf/ncum", "data/raw/nwp/ncmrwf/ncum", "data/ncmrwf/ncum"],
        "formats": [".nc", ".nc4", ".grib2", ".grb2"],
    },
    {
        "source_id": "NCMRWF_NEPS",
        "provider": "NCMRWF",
        "model": "NEPS",
        "expected_paths": ["/data/ncmrwf/neps", "data/raw/nwp/ncmrwf/neps", "data/ncmrwf/neps"],
        "formats": [".nc", ".nc4", ".grib2", ".grb2"],
    },
    {
        "source_id": "IMD_GRIDDED_RAINFALL",
        "provider": "IMD",
        "model": "IMD_025_GRID",
        "expected_paths": ["/data/imd/observed", "data/raw/observations/imd", "data/imd/observed"],
        "formats": [".nc", ".nc4", ".grd", ".csv", ".parquet"],
    },
]


class AuthoritativeMountValidator:
    """
    Validates physical data mounts for NCMRWF NCUM, NCMRWF NEPS, and IMD 0.25° Gridded Rainfall.
    Classifies each into: UNMOUNTED, EMPTY, CONNECTED, PARTIAL, INVALID, AVAILABLE.
    Enforces strict scientific rule: Only AUTHORITATIVE_PRIMARY can participate in REAL_OPERATIONAL.
    """

    def __init__(self, custom_mounts: Optional[Dict[str, str]] = None):
        self.custom_mounts = custom_mounts or {}

    @staticmethod
    def compute_sha256(filepath: Path | str, chunk_size: int = 65536) -> str:
        sha = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(chunk_size):
                sha.update(chunk)
        return sha.hexdigest()

    def inspect_source(self, target_cfg: Dict[str, Any]) -> Tuple[SourceMountAudit, List[SourceProvenanceRecord]]:
        source_id = target_cfg["source_id"]
        provider = target_cfg["provider"]
        model = target_cfg["model"]
        expected_paths = list(target_cfg["expected_paths"])
        if source_id in self.custom_mounts:
            expected_paths.insert(0, self.custom_mounts[source_id])

        chosen_path: Optional[Path] = None
        for p_str in expected_paths:
            p = Path(p_str)
            if p.exists():
                chosen_path = p
                break

        now_iso = datetime.now(timezone.utc).isoformat()
        records: List[SourceProvenanceRecord] = []

        if chosen_path is None or not chosen_path.exists():
            return (
                SourceMountAudit(
                    source_id=source_id,
                    provider=provider,
                    model=model,
                    expected_paths=expected_paths,
                    actual_path=None,
                    exists=False,
                    is_mounted=False,
                    is_readable=False,
                    file_count=0,
                    latest_file=None,
                    latest_file_size_bytes=None,
                    latest_file_format=None,
                    latest_file_checksum=None,
                    metadata_status="UNMOUNTED",
                    qc_status="NOT_EVALUATED",
                    classification=MountClassification.UNMOUNTED.value,
                    can_activate_real=False,
                    notes=f"Source directory unmounted. Checked paths: {', '.join(expected_paths)}",
                ),
                records,
            )

        # Check permissions & readability
        is_readable = os.access(chosen_path, os.R_OK)
        if not is_readable:
            return (
                SourceMountAudit(
                    source_id=source_id,
                    provider=provider,
                    model=model,
                    expected_paths=expected_paths,
                    actual_path=str(chosen_path),
                    exists=True,
                    is_mounted=True,
                    is_readable=False,
                    file_count=0,
                    latest_file=None,
                    latest_file_size_bytes=None,
                    latest_file_format=None,
                    latest_file_checksum=None,
                    metadata_status="PERMISSION_DENIED",
                    qc_status="NOT_EVALUATED",
                    classification=MountClassification.INVALID.value,
                    can_activate_real=False,
                    notes=f"Directory {chosen_path} exists but is not readable (Permission Denied).",
                ),
                records,
            )

        # Discover files
        valid_extensions = tuple(target_cfg.get("formats", [".nc", ".grib2"]))
        files: List[Path] = [
            f for f in chosen_path.rglob("*")
            if f.is_file() and f.suffix.lower() in valid_extensions
        ]

        if not files:
            return (
                SourceMountAudit(
                    source_id=source_id,
                    provider=provider,
                    model=model,
                    expected_paths=expected_paths,
                    actual_path=str(chosen_path),
                    exists=True,
                    is_mounted=True,
                    is_readable=True,
                    file_count=0,
                    latest_file=None,
                    latest_file_size_bytes=0,
                    latest_file_format=None,
                    latest_file_checksum=None,
                    metadata_status="EMPTY",
                    qc_status="NOT_EVALUATED",
                    classification=MountClassification.EMPTY.value,
                    can_activate_real=False,
                    notes=f"Directory {chosen_path} is mounted and readable but contains 0 matching operational files.",
                ),
                records,
            )

        # Sort files by modified time
        files.sort(key=lambda f: f.stat().st_mtime)
        latest = files[-1]
        stat = latest.stat()
        mtime_iso = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        size_bytes = stat.st_size

        # Check for zero-byte corruptions
        if size_bytes == 0:
            classification = MountClassification.INVALID.value
            checksum = ""
            meta_status = "CORRUPT_ZERO_BYTE"
            qc_status = "FAIL"
            notes = f"Latest file {latest.name} is zero bytes (corrupt)."
            can_activate = False
        else:
            try:
                checksum = self.compute_sha256(latest)
            except Exception as e:
                checksum = ""
                classification = MountClassification.INVALID.value
                meta_status = "CHECKSUM_ERROR"
                qc_status = "FAIL"
                notes = f"Failed to compute checksum for {latest.name}: {e}"
                can_activate = False
            else:
                # Determine authority level: Check if test fixture
                is_fixture = "fixture" in str(chosen_path).lower() or "fixture" in latest.name.lower() or "synthetic" in latest.name.lower()
                authority = AuthorityLevel.TEST_FIXTURE.value if is_fixture else AuthorityLevel.AUTHORITATIVE_PRIMARY.value
                
                # Check file count for completeness (e.g. NEPS expects 23 members per cycle)
                if model == "NEPS" and len(files) < 23 and not is_fixture:
                    classification = MountClassification.PARTIAL.value
                    notes = f"Found {len(files)} files; ensemble incomplete (< 23 members)."
                    can_activate = False
                elif is_fixture:
                    classification = MountClassification.CONNECTED.value
                    notes = f"Test fixture detected ({len(files)} files). Not authoritative."
                    can_activate = False
                else:
                    classification = MountClassification.AVAILABLE.value
                    notes = f"Authoritative source verified with {len(files)} operational files."
                    can_activate = True

                meta_status = "VALID"
                qc_status = "PASS"

        # Record provenance for each file
        for f in files:
            f_stat = f.stat()
            f_is_fixture = "fixture" in str(f).lower() or "fixture" in f.name.lower() or "synthetic" in f.name.lower()
            f_auth = AuthorityLevel.TEST_FIXTURE.value if f_is_fixture else AuthorityLevel.AUTHORITATIVE_PRIMARY.value
            f_chk = self.compute_sha256(f) if f_stat.st_size > 0 else "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            records.append(
                SourceProvenanceRecord(
                    provider=provider,
                    source_id=source_id,
                    authority_level=f_auth,
                    source_identifier=str(f),
                    filename=f.name,
                    size_bytes=f_stat.st_size,
                    modified_time=datetime.fromtimestamp(f_stat.st_mtime, tz=timezone.utc).isoformat(),
                    format=f.suffix.lower().lstrip("."),
                    sha256=f_chk,
                    metadata_status="VALID" if f_stat.st_size > 0 else "INVALID",
                    qc_status="PASS" if f_stat.st_size > 0 else "FAIL",
                    discovery_timestamp=now_iso,
                )
            )

        audit = SourceMountAudit(
            source_id=source_id,
            provider=provider,
            model=model,
            expected_paths=expected_paths,
            actual_path=str(chosen_path),
            exists=True,
            is_mounted=True,
            is_readable=True,
            file_count=len(files),
            latest_file=latest.name,
            latest_file_size_bytes=size_bytes,
            latest_file_format=latest.suffix.lower().lstrip("."),
            latest_file_checksum=checksum,
            metadata_status=meta_status,
            qc_status=qc_status,
            classification=classification,
            can_activate_real=can_activate,
            notes=notes,
        )
        return audit, records

    def audit_all_sources(self) -> Dict[str, Any]:
        """Audits all expected authoritative sources."""
        now_iso = datetime.now(timezone.utc).isoformat()
        audits: List[SourceMountAudit] = []
        all_records: List[SourceProvenanceRecord] = []

        for target in EXPECTED_SOURCE_TARGETS:
            audit, recs = self.inspect_source(target)
            audits.append(audit)
            all_records.extend(recs)

        # System-level authoritative data readiness
        all_available = all(a.classification == MountClassification.AVAILABLE.value and a.can_activate_real for a in audits)
        any_mounted = any(a.exists and a.file_count > 0 for a in audits)

        if all_available:
            overall_status = "AUTHORITATIVE_DATA_AVAILABLE"
            real_blocked = False
            disclaimer = "All authoritative NCMRWF & IMD data mounts verified and available for staging."
        elif any_mounted:
            overall_status = "AUTHORITATIVE_DATA_PARTIAL"
            real_blocked = True
            disclaimer = "Authoritative data partially mounted or incomplete; REAL_OPERATIONAL remains BLOCKED."
        else:
            overall_status = "WAITING_FOR_AUTHORITATIVE_DATA"
            real_blocked = True
            disclaimer = "AUTHORITATIVE NCMRWF/IMD DATA UNMOUNTED. REAL_OPERATIONAL remains BLOCKED. REAL_VERIFICATION = NOT_AVAILABLE."

        return {
            "timestamp": now_iso,
            "overall_status": overall_status,
            "real_operational_blocked": real_blocked,
            "authoritative_primary_sources_count": len(audits),
            "sources": [a.to_dict() for a in audits],
            "provenance_records_count": len(all_records),
            "provenance_records": [r.to_dict() for r in all_records],
            "disclaimer": disclaimer,
        }
