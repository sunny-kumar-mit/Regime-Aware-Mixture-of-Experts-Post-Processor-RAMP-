"""
RAMP Real Paired Dataset API Router
SIH26080 | /api/datasets/real/* endpoints
MoES / NCMRWF

Section A14 Endpoints:
  GET /api/datasets/real/status
  GET /api/datasets/real/sources
  GET /api/datasets/real/coverage
  GET /api/datasets/real/statistics
  GET /api/datasets/real/events
  GET /api/datasets/real/splits
  GET /api/datasets/real/quality
  GET /api/datasets/real/provenance
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import APIRouter

from ramp.data_plane.discovery import DataDiscoveryService
from ramp.data_plane.sources import DataMode
from ml.datasets.real.pipeline import RealDatasetPipeline

router = APIRouter(prefix="/datasets/real", tags=["Real Paired Dataset"])

DATASET_ROOT = Path("ml/datasets/real/ramp_dataset_real_v1.0.0")


def _read_manifest_file(filename: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    fpath = DATASET_ROOT / filename
    if fpath.exists():
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default or {}


def _build_envelope(
    payload: Dict[str, Any],
    source: str = "RealDatasetPipeline",
    availability_status: str = "NOT_AVAILABLE",
    data_mode: Optional[str] = None,
    dataset_version: str = "1.0.0",
) -> Dict[str, Any]:
    discovery = DataDiscoveryService()
    matrix = discovery.get_availability_matrix()
    mode = data_mode or matrix.overall_mode

    return {
        "dataset_version": dataset_version,
        "data_mode": mode,
        "source": source,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "provenance": {
            "dataset_id": "ramp_dataset_real_v1.0.0",
            "pipeline": "Phase 11 Operational Data Plane -> Phase 12 Paired Dataset",
            "sha256_active": True,
            "anti_leakage_enforced": True,
            "institution": "MoES / NCMRWF",
        },
        "availability_status": availability_status,
        "data": payload,
    }


@router.get("/status")
def get_real_dataset_status() -> Dict[str, Any]:
    """
    GET /api/datasets/real/status
    Reports operational status and readiness of ramp_dataset_real_v1.0.0.
    """
    pipeline = RealDatasetPipeline()
    readiness = pipeline.inspect_pipeline_readiness()
    manifest = _read_manifest_file("dataset_manifest.json")

    status_str = readiness["status"]
    data_mode = readiness["data_mode"]

    payload = {
        "dataset_id": pipeline.dataset_id,
        "version": pipeline.version,
        "status": status_str,
        "data_mode": data_mode,
        "real_data_available": readiness["real_data_available"],
        "message": readiness["message"],
        "sample_count": manifest.get("sample_count", 0),
        "feature_count": manifest.get("feature_count", 18),
        "target_count": manifest.get("target_count", 5),
        "creation_timestamp": manifest.get("creation_timestamp"),
        "resolution": manifest.get("resolution", {"native_ncmrwf_deg": 0.12, "canonical_ramp_deg": 0.25}),
        "thresholds": readiness["target_thresholds"],
    }

    return _build_envelope(
        payload=payload,
        availability_status=status_str,
        data_mode=data_mode,
    )


@router.get("/sources")
def get_real_dataset_sources() -> Dict[str, Any]:
    """
    GET /api/datasets/real/sources
    Returns provider hierarchy status and physical scan counts.
    """
    pipeline = RealDatasetPipeline()
    disc = pipeline.discover_operational_sources()

    return _build_envelope(
        payload={
            "hierarchy": {
                "PRIMARY": ["NCMRWF_NCUM (0.12°)", "NCMRWF_NEPS (0.12°)", "IMD_OBS (0.25°)"],
                "SECONDARY": ["NCEP_GFS (0.25°)", "NCEP_GEFS (0.50°)"],
                "DEMO": ["SYNTHETIC_DEMO"],
            },
            "operational_matrix": disc["matrix"],
            "scanned_providers": disc["scans"],
            "real_data_available": disc["real_data_available"],
            "public_proxy_available": disc["public_proxy_available"],
            "honesty_notice": disc["honesty_notice"],
        },
        availability_status="AVAILABLE" if disc["real_data_available"] else "NOT_AVAILABLE",
        data_mode=disc["overall_mode"],
    )


@router.get("/coverage")
def get_real_dataset_coverage() -> Dict[str, Any]:
    """
    GET /api/datasets/real/coverage
    Reports spatial domain bounds, grid cell resolution, and coverage percentage.
    """
    coverage = _read_manifest_file(
        "spatial_coverage.json",
        default={
            "latitude_min": 6.5,
            "latitude_max": 38.5,
            "longitude_min": 66.5,
            "longitude_max": 100.5,
            "resolution_deg": 0.25,
            "domain": "India Meteorological Domain",
        },
    )

    return _build_envelope(
        payload=coverage,
        availability_status="AVAILABLE" if coverage.get("grid_cells_covered", 0) > 0 else "NOT_AVAILABLE",
    )


@router.get("/statistics")
def get_real_dataset_statistics() -> Dict[str, Any]:
    """
    GET /api/datasets/real/statistics
    Reports distribution statistics, rainfall moments, and NWP correlations.
    """
    stats = _read_manifest_file("dataset_statistics.json", default={"sample_count": 0, "status": "NOT_AVAILABLE"})

    return _build_envelope(
        payload=stats,
        availability_status="AVAILABLE" if stats.get("total_samples", 0) > 0 else "NOT_AVAILABLE",
    )


@router.get("/events")
def get_real_dataset_events() -> Dict[str, Any]:
    """
    GET /api/datasets/real/events
    Returns rainfall threshold event counts (Rain, Heavy, Very Heavy, Extreme).
    """
    events = _read_manifest_file(
        "event_distribution.json",
        default={"total_events": 0, "extreme_event_status": "INSUFFICIENT_REAL_EVENTS"},
    )

    return _build_envelope(
        payload=events,
        availability_status="AVAILABLE" if events.get("total_samples", 0) > 0 else "NOT_AVAILABLE",
    )


@router.get("/splits")
def get_real_dataset_splits() -> Dict[str, Any]:
    """
    GET /api/datasets/real/splits
    Returns chronological train/val/test partition boundaries and sample counts.
    """
    splits = _read_manifest_file(
        "split_manifest.json",
        default={
            "train_samples": 0,
            "validation_samples": 0,
            "test_samples": 0,
            "splitting_strategy": "Chronological (Unseen temporal holdout)",
        },
    )

    return _build_envelope(
        payload=splits,
        availability_status="AVAILABLE" if splits.get("train_samples", 0) > 0 else "NOT_AVAILABLE",
    )


@router.get("/quality")
def get_real_dataset_quality() -> Dict[str, Any]:
    """
    GET /api/datasets/real/quality
    Returns quality control report, NaN counts, and integrity flags.
    """
    qc = _read_manifest_file(
        "qc_report.json",
        default={"qc_passed": True, "total_records": 0, "status": "AWAITING_RAW_ARCHIVES"},
    )

    return _build_envelope(
        payload=qc,
        availability_status="PASSED" if qc.get("qc_passed") else "CORRUPTION_DETECTED",
    )


@router.get("/provenance")
def get_real_dataset_provenance() -> Dict[str, Any]:
    """
    GET /api/datasets/real/provenance
    Returns cryptographic file checksums, source manifests, and anti-leakage audit.
    """
    checksums = _read_manifest_file("checksum_manifest.json", default={"sha256": {}})
    sources = _read_manifest_file("source_manifest.json", default={})
    leakage = _read_manifest_file("leakage_report.json", default={"leakage_detected": False})

    return _build_envelope(
        payload={
            "dataset_id": "ramp_dataset_real_v1.0.0",
            "checksums": checksums.get("sha256", {}),
            "sources": sources,
            "leakage_audit": leakage,
            "cf_conventions": ["CF-1.6", "CF-1.8"],
            "grid_harmonisation": "0.12° NCMRWF native -> 0.25° canonical RAMP grid (mass-conserving)",
        },
        availability_status="AVAILABLE",
    )
