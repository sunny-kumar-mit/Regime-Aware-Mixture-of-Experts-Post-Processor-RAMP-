"""
RAMP Real-Data Operational Activation API Endpoints
SIH26080 | Phase 16 — Real-Data Activation & Operational Ingestion
MoES / NCMRWF

PART AF & PART P Endpoints:
  GET  /api/activation/status
  GET  /api/activation/sources
  GET  /api/activation/cycles
  GET  /api/activation/validation
  GET  /api/activation/qc
  GET  /api/activation/pairing
  GET  /api/activation/audit
  POST /api/activation/request
  POST /api/activation/approve
  POST /api/activation/reject
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from ml.ingestion.activation import RealDataActivationEngine
from ml.ingestion.discovery import OperationalFileDiscoveryService
from ml.ingestion.pairing import ForecastObservationPairingEngine
from ml.ingestion.qc import MeteorologicalQCEngine
from ml.ingestion.registry import SourceRegistry
from ramp.logger import logger

router = APIRouter(prefix="/activation", tags=["Real Data Activation"])

_activation_engine = RealDataActivationEngine()
_discovery_service = OperationalFileDiscoveryService()
_source_registry = SourceRegistry()
_pairing_engine = ForecastObservationPairingEngine()


class ActivationRequestPayload(BaseModel):
    operator_id: str = Field(..., description="Unique operator identifier")
    source_id: str = Field(default="NCMRWF_NCUM", description="Authoritative data source ID")
    cycle: str = Field(default="00Z", description="Forecast cycle (00Z or 12Z)")
    reason: str = Field(default="Operational synoptic cycle run", description="Justification")


class ActivationApprovalPayload(BaseModel):
    operator_id: str = Field(..., description="Authorizing operator identifier")
    signature: str = Field(..., description="Cryptographic or verified signature token")
    activation_id: Optional[str] = Field(default=None, description="Target activation ID")


class ActivationRejectionPayload(BaseModel):
    operator_id: str = Field(..., description="Rejecting operator identifier")
    reason: str = Field(..., description="Detailed rejection reason")
    activation_id: Optional[str] = Field(default=None, description="Target activation ID")


@router.get("/status", summary="Get 15-gate operational activation status")
async def get_activation_status(
    cycle: str = Query(default="00Z", description="Forecast cycle"),
    source_id: str = Query(default="NCMRWF_NCUM", description="Source ID"),
) -> Dict[str, Any]:
    catalog = _discovery_service.discover_files()
    report = _activation_engine.get_status(catalog.files, source_id=source_id, cycle=cycle)
    return report.to_dict()


@router.get("/sources", summary="Get registered data sources and dynamic statuses")
async def get_activation_sources() -> List[Dict[str, Any]]:
    _source_registry.refresh_availability()
    sources = _source_registry.list_sources()
    return [s.to_dict() for s in sources]


@router.get("/cycles", summary="Get active and discovered forecast cycles")
async def get_activation_cycles() -> Dict[str, Any]:
    catalog = _discovery_service.discover_files()
    discovered_cycles = list({f.cycle for f in catalog.files if f.cycle})
    return {
        "canonical_cycles": ["00Z", "12Z"],
        "active_cycle": "00Z",
        "discovered_cycles": discovered_cycles,
        "total_files": len(catalog.files),
    }


@router.get("/validation", summary="Get detailed 15-gate validation results")
async def get_activation_validation(
    cycle: str = Query(default="00Z"),
    source_id: str = Query(default="NCMRWF_NCUM"),
) -> Dict[str, Any]:
    catalog = _discovery_service.discover_files()
    gates = _activation_engine.evaluate_gates(catalog.files, source_id=source_id, cycle=cycle)
    passed = sum(1 for g in gates if g.is_passed)
    return {
        "cycle": cycle,
        "source_id": source_id,
        "total_gates": len(gates),
        "passed": passed,
        "failed": len(gates) - passed,
        "all_passed": passed == len(gates),
        "gates": [g.to_dict() for g in gates],
    }


@router.get("/qc", summary="Get meteorological quality control status")
async def get_activation_qc() -> Dict[str, Any]:
    return {
        "qc_status": "MONITORING_ACTIVE",
        "checks_enforced": [
            "nan_and_inf_detection",
            "negative_rainfall_rejection",
            "physical_limits_24h_rainfall_0_to_1500mm",
            "t850_180_to_340K",
            "mslp_870_to_1085hPa",
            "wind_speed_0_to_120mps",
            "cape_0_to_8000Jkg",
            "duplicate_coordinate_rejection",
        ],
        "authoritative_stream_qc": "BLOCKED_NO_DATA",
        "disclaimer": "Real meteorological QC executes upon authoritative file discovery.",
    }


@router.get("/pairing", summary="Get forecast/observation pairing manifests")
async def get_activation_pairing() -> Dict[str, Any]:
    return {
        "pairing_status": "WAITING_FOR_PAIRED_ARCHIVES",
        "anti_leakage_guard": "ACTIVE",
        "verified_pairs_count": 0,
        "manifests": [],
        "disclaimer": "Forecast/observation pairing requires authoritative IMD 0.25° ground truth.",
    }


@router.get("/audit", summary="Get immutable operational activation audit trail")
async def get_activation_audit() -> List[Dict[str, Any]]:
    return _activation_engine.get_audit_trail()


@router.post("/request", summary="Submit an operational activation request (Operator only)")
async def request_activation(payload: ActivationRequestPayload) -> Dict[str, Any]:
    catalog = _discovery_service.discover_files()
    success, msg = _activation_engine.request_activation(
        operator_id=payload.operator_id,
        source_id=payload.source_id,
        cycle=payload.cycle,
        reason=payload.reason,
        discovered_files=catalog.files,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail={"error": "ACTIVATION_REQUEST_BLOCKED", "message": msg},
        )
    return {"status": "REQUESTED", "message": msg}


@router.post("/approve", summary="Authorize operational activation (Operator approval gate)")
async def approve_activation(payload: ActivationApprovalPayload) -> Dict[str, Any]:
    success, msg = _activation_engine.approve_activation(
        operator_id=payload.operator_id,
        signature=payload.signature,
        activation_id=payload.activation_id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "ACTIVATION_APPROVAL_FAILED", "message": msg},
        )
    return {"status": "APPROVED", "message": msg, "data_mode": "REAL_OPERATIONAL"}


@router.post("/reject", summary="Reject an operational activation request")
async def reject_activation(payload: ActivationRejectionPayload) -> Dict[str, Any]:
    success, msg = _activation_engine.reject_activation(
        operator_id=payload.operator_id,
        reason=payload.reason,
        activation_id=payload.activation_id,
    )
    return {"status": "REJECTED", "message": msg}
