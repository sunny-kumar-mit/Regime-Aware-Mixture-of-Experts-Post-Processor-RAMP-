"""
RAMP Operational Forecast Inference REST API
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Part V: Operational forecast endpoints delivering uniform envelopes:
  - GET  /api/forecast/status
  - GET  /api/forecast/cycles
  - GET  /api/forecast/cycles/{cycle_id}
  - GET  /api/forecast/run/{forecast_run_id}
  - GET  /api/forecast/grid
  - GET  /api/forecast/districts
  - GET  /api/forecast/states
  - GET  /api/forecast/probability
  - GET  /api/forecast/regimes
  - GET  /api/forecast/metadata
  - POST /api/forecast/infer
  - GET  /api/forecast/export/{forecast_run_id}
  - GET  /api/forecast/provenance/{forecast_run_id}
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from ml.inference.config import (
    FEATURE_SCHEMA_VERSION,
    FORECAST_STORAGE_PATH,
    INFERENCE_ENGINE_VERSION,
    PRODUCT_CATEGORIES,
    TARGET_SCHEMA_VERSION,
    THRESHOLDS,
)
from ml.inference.input_resolver import ForecastCycleResolver
from ml.inference.model_resolver import ModelResolver
from ml.inference.pipeline import OperationalInferencePipeline
from ml.inference.products import ForecastProductManager
from ramp.data_plane.discovery import DataDiscoveryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/forecast", tags=["Operational Forecast Inference & Products"])

_cycle_resolver = ForecastCycleResolver()
_model_resolver = ModelResolver()
_pipeline = OperationalInferencePipeline(
    model_resolver=_model_resolver,
    cycle_resolver=_cycle_resolver,
)
_product_manager = ForecastProductManager()
_discovery = DataDiscoveryService()

# In-memory execution cache for snappy operational navigation
_run_cache: Dict[str, Dict[str, Any]] = {}


def _get_or_run_forecast(cycle_id: str, lead_hours: int) -> Dict[str, Any]:
    cache_key = f"{cycle_id}_T{lead_hours}"
    if cache_key in _run_cache:
        return _run_cache[cache_key]

    try:
        res = _pipeline.run_forecast(
            cycle_id=cycle_id,
            lead_time_hours=lead_hours,
            user_action="API_REQUEST",
        )
    except Exception as e:
        logger.warning(f"Inference execution for cycle '{cycle_id}' encountered: {e}. Resolving demo fallback.")
        cycles = _cycle_resolver.list_available_cycles()
        fallback_id = cycles[0].cycle_id if cycles else "DEMO_20260927_00Z"
        if fallback_id != cycle_id:
            try:
                res = _pipeline.run_forecast(
                    cycle_id=fallback_id,
                    lead_time_hours=lead_hours,
                    user_action="API_REQUEST",
                )
            except Exception as e2:
                logger.error(f"Fallback forecast run failed: {e2}")
                return {
                    "status": "NOT_AVAILABLE",
                    "forecast_run_id": f"BLOCKED_{cycle_id}",
                    "forecast_valid_time": "N/A",
                    "lead_time_hours": lead_hours,
                    "grid_cells": [],
                    "districts": [],
                    "states": [],
                    "data_mode": "REAL_OPERATIONAL_BLOCKED",
                    "provenance": {"reason": str(e), "subsystem": "operational_inference"},
                }
        else:
            return {
                "status": "NOT_AVAILABLE",
                "forecast_run_id": f"BLOCKED_{cycle_id}",
                "forecast_valid_time": "N/A",
                "lead_time_hours": lead_hours,
                "grid_cells": [],
                "districts": [],
                "states": [],
                "data_mode": "REAL_OPERATIONAL_BLOCKED",
                "provenance": {"reason": str(e), "subsystem": "operational_inference"},
            }

    if res.get("status") == "SUCCESS":
        _run_cache[cache_key] = res
        if "forecast_run_id" in res:
            _run_cache[res["forecast_run_id"]] = res
    return res


def _format_envelope(
    data: Any,
    cycle_id: Optional[str] = None,
    data_mode: str = "SYNTHETIC_DEMO",
    source: str = "NCUM_SYNTHETIC_DEMO",
    provenance: Optional[Dict[str, Any]] = None,
    status_str: str = "SUCCESS",
    availability_status: str = "DEMO_AVAILABLE",
) -> Dict[str, Any]:
    return {
        "status": status_str,
        "data": data,
        "data_mode": data_mode,
        "source": source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance or {},
        "availability_status": availability_status,
    }


class ForecastInferenceRequest(BaseModel):
    cycle_id: str = Field(..., description="Cycle identifier e.g. DEMO_20260927_00Z")
    lead_time_hours: int = Field(24, description="Forecast lead time in hours")
    enforce_monotonicity: bool = Field(True, description="Enforce P(extreme) <= ... <= P(rain)")


# ---------------------------------------------------------------------------
# 1. Operational Forecast Desk Status (Part AE)
# ---------------------------------------------------------------------------
@app_get_status := router.get("/status")
def get_forecast_status():
    mat = _discovery.get_availability_matrix()
    cycles = _cycle_resolver.list_available_cycles()
    latest_cycle = cycles[0] if cycles else None

    # Check model registry
    try:
        active = _model_resolver.resolve_active_models()
        model_status = "READY" if len(active) >= 4 else "DEGRADED"
    except Exception:
        model_status = "BLOCKED"

    return _format_envelope(
        data={
            "ncmrwf_ncum": "AVAILABLE" if mat.ncmrwf_ncum else "NOT_AVAILABLE",
            "ncmrwf_neps": "AVAILABLE" if mat.ncmrwf_neps else "NOT_AVAILABLE",
            "imd_obs": "AVAILABLE" if mat.imd_obs else "NOT_AVAILABLE",
            "ramp_model": model_status,
            "inference_engine": "READY",
            "overall_data_mode": mat.overall_mode,
            "real_operational_data_available": mat.real_data_available,
            "honesty_notice": mat.honesty_notice,
            "forecast_cycles_count": len(cycles),
            "latest_cycle": latest_cycle.to_dict() if latest_cycle else None,
            "available_leads": latest_cycle.available_leads if latest_cycle else [],
            "supported_thresholds": THRESHOLDS,
        },
        data_mode=mat.overall_mode,
        source="SYSTEM_DIAGNOSTIC",
        availability_status="READY" if mat.real_data_available else "DEMO_AVAILABLE",
    )


# ---------------------------------------------------------------------------
# 2. Cycles & Cycle Details (Parts C & D)
# ---------------------------------------------------------------------------
@router.get("/cycles")
def get_cycles():
    cycles = _cycle_resolver.list_available_cycles()
    mode = cycles[0].data_mode if cycles else "SYNTHETIC_DEMO"
    return _format_envelope(
        data=[c.to_dict() for c in cycles],
        data_mode=mode,
        source="CYCLE_DISCOVERY",
    )


@router.get("/cycles/{cycle_id}")
def get_cycle_detail(cycle_id: str):
    c = _cycle_resolver.get_cycle(cycle_id)
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cycle '{cycle_id}' not found.",
        )
    return _format_envelope(
        data=c.to_dict(),
        data_mode=c.data_mode,
        source=c.model,
    )


# ---------------------------------------------------------------------------
# 3. Forecast Inference Endpoint (Part A)
# ---------------------------------------------------------------------------
@router.post("/infer")
def run_forecast_inference(req: ForecastInferenceRequest):
    res = _get_or_run_forecast(req.cycle_id, req.lead_time_hours)
    if res.get("status") != "SUCCESS":
        return _format_envelope(
            data=res,
            status_str="FORECAST_GENERATION_BLOCKED",
            availability_status="BLOCKED",
        )

    return _format_envelope(
        data=res,
        data_mode=res.get("data_mode", "SYNTHETIC_DEMO"),
        source=res.get("cycle", {}).get("model", "NCUM"),
        provenance=res.get("provenance", {}),
    )


# ---------------------------------------------------------------------------
# 4. Run Lookup (Part R)
# ---------------------------------------------------------------------------
@router.get("/run/{forecast_run_id}")
def get_forecast_run(forecast_run_id: str):
    if forecast_run_id in _run_cache:
        res = _run_cache[forecast_run_id]
        return _format_envelope(
            data=res,
            data_mode=res.get("data_mode", "SYNTHETIC_DEMO"),
            source=res.get("cycle", {}).get("model", "NCUM"),
            provenance=res.get("provenance", {}),
        )

    # Search on disk
    matches = list(FORECAST_STORAGE_PATH.glob(f"**/{forecast_run_id}_summary.json"))
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast run '{forecast_run_id}' not found in storage.",
        )

    with open(matches[0], "r", encoding="utf-8") as f:
        run_data = json.load(f)

    return _format_envelope(
        data=run_data,
        data_mode=run_data.get("metadata", {}).get("data_mode", "SYNTHETIC_DEMO"),
        provenance=run_data.get("metadata", {}),
    )


# ---------------------------------------------------------------------------
# 5. Spatial Forecast Grid (Parts J, K, L)
# ---------------------------------------------------------------------------
@router.get("/grid")
def get_forecast_grid(
    cycle_id: Optional[str] = Query(None, description="Cycle ID"),
    lead: int = Query(24, description="Lead time in hours"),
):
    if not cycle_id:
        cycles = _cycle_resolver.list_available_cycles()
        cycle_id = cycles[0].cycle_id if cycles else "DEMO_20260927_00Z"

    res = _get_or_run_forecast(cycle_id, lead)
    if res.get("status") != "SUCCESS":
        raise HTTPException(status_code=400, detail=res)

    return _format_envelope(
        data={
            "forecast_run_id": res["forecast_run_id"],
            "forecast_valid_time": res["forecast_valid_time"],
            "lead_time_hours": res["lead_time_hours"],
            "grid_cells": res["grid_cells"],
        },
        data_mode=res["data_mode"],
        source=res.get("cycle", {}).get("model", "NCUM"),
        provenance=res.get("provenance", {}),
    )


# ---------------------------------------------------------------------------
# 6. District Forecasts (Part M)
# ---------------------------------------------------------------------------
@router.get("/districts")
def get_district_forecasts(
    cycle_id: Optional[str] = Query(None, description="Cycle ID"),
    lead: int = Query(24, description="Lead time in hours"),
):
    if not cycle_id:
        cycles = _cycle_resolver.list_available_cycles()
        cycle_id = cycles[0].cycle_id if cycles else "DEMO_20260927_00Z"

    res = _get_or_run_forecast(cycle_id, lead)
    if res.get("status") != "SUCCESS":
        raise HTTPException(status_code=400, detail=res)

    return _format_envelope(
        data={
            "forecast_run_id": res["forecast_run_id"],
            "forecast_valid_time": res["forecast_valid_time"],
            "lead_time_hours": res["lead_time_hours"],
            "districts": res["districts"],
        },
        data_mode=res["data_mode"],
        source=res.get("cycle", {}).get("model", "NCUM"),
        provenance=res.get("provenance", {}),
    )


# ---------------------------------------------------------------------------
# 7. State Forecasts (Part N)
# ---------------------------------------------------------------------------
@router.get("/states")
def get_state_forecasts(
    cycle_id: Optional[str] = Query(None, description="Cycle ID"),
    lead: int = Query(24, description="Lead time in hours"),
):
    if not cycle_id:
        cycles = _cycle_resolver.list_available_cycles()
        cycle_id = cycles[0].cycle_id if cycles else "DEMO_20260927_00Z"

    res = _get_or_run_forecast(cycle_id, lead)
    if res.get("status") != "SUCCESS":
        raise HTTPException(status_code=400, detail=res)

    return _format_envelope(
        data={
            "forecast_run_id": res["forecast_run_id"],
            "forecast_valid_time": res["forecast_valid_time"],
            "lead_time_hours": res["lead_time_hours"],
            "states": res["states"],
        },
        data_mode=res["data_mode"],
        source=res.get("cycle", {}).get("model", "NCUM"),
        provenance=res.get("provenance", {}),
    )


# ---------------------------------------------------------------------------
# 8. Probability Products (Part H)
# ---------------------------------------------------------------------------
@router.get("/probability")
def get_probability_forecasts(
    cycle_id: Optional[str] = Query(None, description="Cycle ID"),
    lead: int = Query(24, description="Lead time in hours"),
):
    if not cycle_id:
        cycles = _cycle_resolver.list_available_cycles()
        cycle_id = cycles[0].cycle_id if cycles else "DEMO_20260927_00Z"

    res = _get_or_run_forecast(cycle_id, lead)
    if res.get("status") != "SUCCESS":
        raise HTTPException(status_code=400, detail=res)

    probs = [
        {
            "lat": c["latitude"],
            "lon": c["longitude"],
            "prob_rain": c["rainfall_probability"],
            "prob_heavy": c["heavy_probability"],
            "prob_very_heavy": c["very_heavy_probability"],
            "prob_extreme": c["extreme_probability"],
        }
        for c in res["grid_cells"]
    ]

    return _format_envelope(
        data={
            "forecast_run_id": res["forecast_run_id"],
            "lead_time_hours": res["lead_time_hours"],
            "probabilities": probs,
            "monotonicity_report": res["monotonicity_report"],
            "thresholds": THRESHOLDS,
        },
        data_mode=res["data_mode"],
        source=res.get("cycle", {}).get("model", "NCUM"),
        provenance=res.get("provenance", {}),
    )


# ---------------------------------------------------------------------------
# 9. Regime Products (Part G)
# ---------------------------------------------------------------------------
@router.get("/regimes")
def get_regime_forecasts(
    cycle_id: Optional[str] = Query(None, description="Cycle ID"),
    lead: int = Query(24, description="Lead time in hours"),
):
    if not cycle_id:
        cycles = _cycle_resolver.list_available_cycles()
        cycle_id = cycles[0].cycle_id if cycles else "DEMO_20260927_00Z"

    res = _get_or_run_forecast(cycle_id, lead)
    if res.get("status") != "SUCCESS":
        raise HTTPException(status_code=400, detail=res)

    regimes = [
        {
            "lat": c["latitude"],
            "lon": c["longitude"],
            "regime": c["regime"],
            "probabilities": c.get("regime_probabilities", {}),
        }
        for c in res["grid_cells"]
    ]

    return _format_envelope(
        data={
            "forecast_run_id": res["forecast_run_id"],
            "lead_time_hours": res["lead_time_hours"],
            "regimes": regimes,
        },
        data_mode=res["data_mode"],
        source=res.get("cycle", {}).get("model", "NCUM"),
        provenance=res.get("provenance", {}),
    )


# ---------------------------------------------------------------------------
# 10. Forecast Metadata (Part Q)
# ---------------------------------------------------------------------------
@router.get("/metadata")
def get_forecast_metadata():
    return _format_envelope(
        data={
            "inference_engine_version": INFERENCE_ENGINE_VERSION,
            "feature_schema": FEATURE_SCHEMA_VERSION,
            "target_schema": TARGET_SCHEMA_VERSION,
            "product_categories": PRODUCT_CATEGORIES,
            "thresholds": THRESHOLDS,
            "canonical_resolution": "0.25° x 0.25°",
        },
        data_mode="CANONICAL_SPEC",
        source="RAMP_INFERENCE_ENGINE",
    )


# ---------------------------------------------------------------------------
# 11. Multi-Format Product Export (Part U)
# ---------------------------------------------------------------------------
@router.get("/export/{forecast_run_id}")
def export_forecast_product(
    forecast_run_id: str,
    format: str = Query("json", pattern="^(json|csv|geojson)$"),
):

    # Retrieve from cache or recompute
    run_data = _run_cache.get(forecast_run_id)
    if not run_data:
        # Find matching cycle and lead
        parts = forecast_run_id.split("_")
        lead = 24
        if len(parts) >= 4 and parts[3].startswith("T"):
            try:
                lead = int(parts[3].replace("T", ""))
            except Exception:
                pass

        cycles = _cycle_resolver.list_available_cycles()
        cycle_id = cycles[0].cycle_id if cycles else "DEMO_20260927_00Z"
        if len(parts) >= 3:
            for c in cycles:
                if c.cycle_utc.replace(" ", "").upper() in parts[2].upper() or parts[2].upper().startswith(c.cycle_utc.split()[0]):
                    cycle_id = c.cycle_id
                    break

        run_data = _get_or_run_forecast(cycle_id, lead)

    if not run_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{forecast_run_id}' not found.",
        )


    if format == "json":
        return Response(
            content=json.dumps(run_data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={forecast_run_id}.json"},
        )
    elif format == "csv":
        csv_str = _product_manager.export_to_csv({
            "metadata": run_data.get("provenance", {}),
            "data": {"values": run_data.get("grid_cells", [])},
        })
        return Response(
            content=csv_str,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={forecast_run_id}.csv"},
        )

    elif format == "geojson":
        # Form GeoJSON via PostGIS ForecastStore if persisted in database
        try:
            try:
                from ramp.storage.forecast_store import ForecastStore
            except ImportError:
                from backend.src.ramp.storage.forecast_store import ForecastStore
            f_store = ForecastStore()
            if f_store.get_forecast_run(forecast_run_id):
                geojson_doc = f_store.generate_geojson(forecast_run_id)
                return Response(
                    content=json.dumps(geojson_doc, indent=2),
                    media_type="application/geo+json",
                    headers={"Content-Disposition": f"attachment; filename={forecast_run_id}.geojson"},
                )
        except Exception as e:
            logger.debug(f"Direct PostGIS GeoJSON export fallback: {e}")

        # Form GeoJSON from run cells
        geojson_doc = {
            "type": "FeatureCollection",
            "metadata": run_data.get("provenance", {}),
            "features": [
                {
                    "type": "Feature",
                    "id": c.get("grid_id", f"G_{c['latitude']}_{c['longitude']}"),
                    "geometry": {
                        "type": "Point",
                        "coordinates": [c["longitude"], c["latitude"]],
                    },
                    "properties": c,
                }
                for c in run_data.get("grid_cells", [])
            ],
        }
        return Response(
            content=json.dumps(geojson_doc, indent=2),
            media_type="application/geo+json",
            headers={"Content-Disposition": f"attachment; filename={forecast_run_id}.geojson"},
        )


# ---------------------------------------------------------------------------
# 12. Run Provenance Manifest (Part S)
# ---------------------------------------------------------------------------
@router.get("/provenance/{forecast_run_id}")
def get_forecast_provenance(forecast_run_id: str):
    matches = list(FORECAST_STORAGE_PATH.glob(f"**/{forecast_run_id}_summary.json"))
    manifest = None
    if matches:
        manifest_p = matches[0].parent / "metadata" / "forecast_manifest.json"
        if manifest_p.exists():
            with open(manifest_p, "r", encoding="utf-8") as f:
                manifest = json.load(f)

    if not manifest and forecast_run_id in _run_cache:
        manifest = _run_cache[forecast_run_id].get("provenance")

    if not manifest:
        try:
            try:
                from ramp.storage.provenance_store import ProvenanceStore
            except ImportError:
                from backend.src.ramp.storage.provenance_store import ProvenanceStore
            p_store = ProvenanceStore()
            prov_rec = p_store.get_provenance(forecast_run_id)
            if prov_rec and prov_rec.get("manifest"):
                manifest = prov_rec["manifest"]
        except Exception as e:
            logger.debug(f"DB provenance lookup error: {e}")

    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provenance manifest for run '{forecast_run_id}' not found.",
        )

    return _format_envelope(
        data=manifest,
        data_mode=manifest.get("data_mode", "SYNTHETIC_DEMO"),
        source="PROVENANCE_REGISTRY",
        provenance=manifest,
    )
