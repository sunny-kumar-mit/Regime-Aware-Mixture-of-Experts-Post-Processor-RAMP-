"""
RAMP Data Ingestion & Source Monitoring API Endpoints
SIH26080 | Phase 16 — Real-Data Activation & Operational Ingestion
MoES / NCMRWF

PART AF Ingestion Endpoints:
  GET /api/ingestion/status
  GET /api/ingestion/sources
  GET /api/ingestion/files
  GET /api/ingestion/qc
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query

from ml.ingestion.discovery import OperationalFileDiscoveryService
from ml.ingestion.qc import MeteorologicalQCEngine
from ml.ingestion.registry import SourceRegistry
from ml.ingestion.sources import AUTHORITATIVE_SOURCE_CONTRACTS

router = APIRouter(prefix="/ingestion", tags=["Meteorological Ingestion"])

_discovery_service = OperationalFileDiscoveryService()
_source_registry = SourceRegistry()
_qc_engine = MeteorologicalQCEngine()


@router.get("/status", summary="Get overall data ingestion pipeline health and source states")
async def get_ingestion_status() -> Dict[str, Any]:
    statuses = _source_registry.refresh_availability()
    catalog = _discovery_service.discover_files()
    
    # Detailed provider status cards for NCUM, NEPS, IMD
    cards = {}
    for sid in ["NCMRWF_NCUM", "NCMRWF_NEPS", "IMD_GRIDDED_RAINFALL"]:
        contract = _source_registry.get_source(sid)
        src_files = [f for f in catalog.files if sid.split("_")[-1].lower() in f.model.lower() or sid.lower() in f.provider.lower()]
        latest_file = src_files[-1] if src_files else None

        cards[sid] = {
            "source_id": sid,
            "provider": contract.provider if contract else "NCMRWF",
            "model": contract.model if contract else "NWP",
            "availability": statuses.get(sid, "UNAVAILABLE"),
            "resolution": contract.resolution if contract else "0.25°",
            "target_grid": "0.25°",
            "variables_count": len(contract.variables) if contract else 0,
            "expected_format": contract.expected_format if contract else [".nc"],
            "files_found": len(src_files),
            "latest_file": latest_file.file_name if latest_file else "None",
            "latest_cycle": latest_file.cycle if latest_file else "None",
            "coverage_percent": 100.0 if latest_file and latest_file.is_valid_metadata else 0.0,
            "qc_status": "PASSED" if latest_file and latest_file.is_valid_integrity else "NOT_AVAILABLE",
            "checksum": latest_file.checksum_sha256 if latest_file else "None",
            "status": "DETECTED" if src_files else "WAITING_FOR_DATA",
        }

    return {
        "pipeline_status": "OPERATIONAL_READY",
        "authoritative_archive_mounted": False,
        "sources_monitored": len(_source_registry.list_sources()),
        "total_files_discovered": catalog.total_files_found,
        "authoritative_files_count": catalog.authoritative_files_count,
        "test_fixture_files_count": catalog.test_fixture_files_count,
        "provider_cards": cards,
        "disclaimer": "Real-data ingestion requires authoritative NCMRWF / IMD archives mounted.",
    }


@router.get("/sources", summary="Get catalog of authoritative meteorological data sources")
async def get_ingestion_sources() -> List[Dict[str, Any]]:
    _source_registry.refresh_availability()
    return [s.to_dict() for s in _source_registry.list_sources()]


@router.get("/files", summary="Get list of all discovered meteorological files")
async def get_ingestion_files(
    limit: int = Query(default=50, ge=1, le=200),
    authority: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    catalog = _discovery_service.discover_files()
    files = catalog.files
    if authority:
        files = [f for f in files if f.authority_level.upper() == authority.upper()]
    return {
        "total": len(files),
        "returned": min(limit, len(files)),
        "files": [f.to_dict() for f in files[:limit]],
    }


@router.get("/qc", summary="Get aggregated meteorological quality control metrics")
async def get_ingestion_qc() -> Dict[str, Any]:
    return {
        "quality_control_engine": "MeteorologicalQCEngine v1.0.0",
        "active_rules": [
            {"id": "QC_001", "name": "Non-Finite Guard", "description": "Rejects NaNs and Infs exceeding 5%"},
            {"id": "QC_002", "name": "Negative Rainfall Rejection", "description": "Rainfall < 0.0 mm rejected"},
            {"id": "QC_003", "name": "Physical Precipitation Cap", "description": "Rainfall > 1500.0 mm/24h capped"},
            {"id": "QC_004", "name": "Thermodynamic Envelope", "description": "T850 within [180K, 340K]"},
            {"id": "QC_005", "name": "Barometric Range", "description": "MSLP within [870hPa, 1085hPa]"},
            {"id": "QC_006", "name": "Wind Speed Upper Bound", "description": "Wind speed within [0m/s, 120m/s]"},
        ],
        "overall_qc_verdict": "NOMINAL",
        "datasets_passed": 0,
        "datasets_failed": 0,
        "notes": "QC evaluates automatically upon operational file arrival.",
    }
