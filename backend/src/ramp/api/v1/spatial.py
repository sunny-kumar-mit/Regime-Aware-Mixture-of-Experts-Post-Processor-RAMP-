"""
Phase 9 Spatial Forecast Products & District Aggregation API Router
SIH26080 | /api/spatial/* endpoints
MoES / NCMRWF

15 Spatial Endpoints:
  1.  GET /api/spatial/status
  2.  GET /api/spatial/grid
  3.  GET /api/spatial/districts
  4.  GET /api/spatial/district/{district_id}
  5.  GET /api/spatial/states
  6.  GET /api/spatial/state/{state_id}
  7.  GET /api/spatial/summary
  8.  GET /api/spatial/probability
  9.  GET /api/spatial/hotspots
  10. GET /api/spatial/regimes
  11. GET /api/spatial/uncertainty
  12. GET /api/spatial/difference
  13. GET /api/spatial/fss
  14. GET /api/spatial/geojson
  15. GET /api/spatial/export
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from ramp.config import settings
from ml.spatial.grid import SpatialGridEngine, GridCell
from ml.spatial.boundaries import AdministrativeBoundaryProvider, DistrictBoundary
from ml.spatial.intersection import GridDistrictIntersectionEngine
from ml.spatial.aggregation import DistrictAggregationEngine
from ml.spatial.products import DistrictForecastProduct, StateForecastProduct, NationalForecastSummary
from ml.spatial.fss import FractionsSkillScoreService
from ml.spatial.export import GISExportService
from ml.spatial.registry import SpatialProductRegistry, SPATIAL_PRODUCT_VERSION

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/spatial", tags=["Spatial Forecast Products & District Aggregation"])

# Singletons
_boundary_provider = AdministrativeBoundaryProvider()
_grid_engine = SpatialGridEngine()
_agg_engine = DistrictAggregationEngine()
_export_service = GISExportService()
_registry = SpatialProductRegistry()

DATASET_PATH = "data/processed/training/ramp_dataset_v0.3.0/ramp_dataset.parquet"

# Cached state
_cached_df: Optional[pd.DataFrame] = None
_cached_district_products: Dict[int, List[DistrictForecastProduct]] = {}  # keyed by lead_hours
_cached_grid_cells: Dict[int, List[GridCell]] = {}


def _get_base_dataframe() -> pd.DataFrame:
    global _cached_df
    if _cached_df is None:
        if os.path.exists(DATASET_PATH):
            df = pd.read_parquet(DATASET_PATH)
            if "raw_nwp_rainfall" in df.columns and "nwp_rainfall_mm" not in df.columns:
                df["nwp_rainfall_mm"] = df["raw_nwp_rainfall"]
            if "ramp_pred" not in df.columns and "nwp_rainfall_mm" in df.columns:
                df["ramp_pred"] = np.maximum(0.0, df["nwp_rainfall_mm"] * 0.90 + 2.5)
            if "global_ml_pred" not in df.columns and "nwp_rainfall_mm" in df.columns:
                df["global_ml_pred"] = np.maximum(0.0, df["nwp_rainfall_mm"] * 0.95)
            _cached_df = df
        else:
            # Fallback realistic spatial slice
            lats = [21.0, 21.25, 21.5, 18.5, 19.0, 22.5, 23.0]
            lons = [78.0, 78.25, 78.5, 73.5, 74.0, 72.0, 72.5]
            records = []
            for lat, lon in zip(lats, lons):
                records.append({
                    "latitude": lat,
                    "longitude": lon,
                    "forecast_valid_time": "2026-07-15T00:00:00Z",
                    "forecast_initialization_time": "2026-07-14T00:00:00Z",
                    "lead_time_hours": 24,
                    "nwp_rainfall_mm": 24.5,
                    "ramp_pred": 32.1,
                    "global_ml_pred": 28.0,
                    "observed_rainfall_mm": 35.0,
                    "p_rain": 0.95,
                    "p_heavy": 0.35,
                    "p_very_heavy": 0.10,
                    "p_extreme": 0.02,
                    "top_regime": "ACTIVE_MONSOON",
                    "uncertainty": 0.15,
                })
            _cached_df = pd.DataFrame(records)
    return _cached_df


# ---------------------------------------------------------------------------
# Realistic synthetic district forecast generation for SYNTHETIC_DEMO mode
# ---------------------------------------------------------------------------

# Monsoon climatology by state (mean_rain_mm, spread_mm, dominant_regime)
_STATE_MONSOON_CLIMO = {
    "MH": (28.0, 18.0, "ACTIVE_MONSOON"),
    "KL": (52.0, 30.0, "ACTIVE_MONSOON"),
    "GJ": (20.0, 14.0, "LOW_DEPRESSION"),
    "KA": (32.0, 22.0, "ACTIVE_MONSOON"),
    "OD": (38.0, 24.0, "LOW_DEPRESSION"),
    "AS": (45.0, 28.0, "ACTIVE_MONSOON"),
    "HP": (22.0, 16.0, "WESTERN_DISTURBANCE"),
    "RJ": (10.0, 12.0, "BREAK_MONSOON"),
    "DL": (12.0, 10.0, "BREAK_MONSOON"),
    "TN": (18.0, 14.0, "POST_MONSOON"),
    "WB": (40.0, 26.0, "LOW_DEPRESSION"),
}

_REGIME_COLORS = {
    "ACTIVE_MONSOON": "#0ea5e9",
    "LOW_DEPRESSION": "#f97316",
    "BREAK_MONSOON": "#94a3b8",
    "WESTERN_DISTURBANCE": "#a855f7",
    "POST_MONSOON": "#22c55e",
}

_RISK_THRESHOLDS = [
    (204.5, "EXTREME_RAINFALL",   "Extremely heavy rainfall expected. Highest alert issued.", "#ef4444"),
    (115.6, "VERY_HIGH_RAINFALL", "Very heavy rainfall. Flood risk - evacuate low-lying areas.", "#f97316"),
    (64.5,  "HIGH_RAINFALL",      "Heavy rainfall. Risk of flash floods and waterlogging.", "#eab308"),
    (15.6,  "WATCH",              "Moderate rainfall watch. Minor disruption possible.", "#22c55e"),
    (0.1,   "NORMAL",             "Normal monsoon conditions.", "#009933"),
]


def _classify_risk(rainfall_mm: float):
    for threshold, category, description, color in _RISK_THRESHOLDS:
        if rainfall_mm >= threshold:
            return category, description, color
    return "NORMAL", "Normal monsoon conditions.", "#009933"


def _generate_synthetic_district_product(
    district,
    lead_hours: int,
    valid_time: str,
    init_time: str,
    rng: np.random.Generator,
) -> DistrictForecastProduct:
    """
    Generate a realistic synthetic forecast for a district lacking grid coverage.
    Uses state-level monsoon climatology with gamma-distributed rainfall amounts.
    """
    s_id = district.state_id
    mean_rain, spread, regime = _STATE_MONSOON_CLIMO.get(s_id, (18.0, 12.0, "ACTIVE_MONSOON"))

    # Lead-time decay
    lead_factor = max(0.5, 1.0 - 0.04 * (lead_hours - 24) / 24.0)
    mean_rain_adj = mean_rain * lead_factor
    spread_val = spread * lead_factor

    # Gamma-distributed rainfall
    shape_param = 1.5
    scale_param = max(0.1, mean_rain_adj / shape_param)
    rainfall_mm = round(max(0.0, float(rng.gamma(shape=shape_param, scale=scale_param))), 2)

    nwp_mm = round(max(0.0, rainfall_mm / 0.90 + float(rng.normal(0, 2.5))), 2)
    global_ml_mm = round(max(0.0, rainfall_mm * 0.95 + float(rng.normal(0, 1.5))), 2)

    min_mm = round(max(0.0, rainfall_mm - spread_val * 0.4), 2)
    max_mm = round(rainfall_mm + spread_val * 0.8, 2)
    median_mm = round(rainfall_mm * 0.95, 2)
    p90_mm = round(rainfall_mm + spread_val * 0.5, 2)
    p95_mm = round(rainfall_mm + spread_val * 0.7, 2)
    p99_mm = round(rainfall_mm + spread_val * 1.0, 2)

    p_rain = round(float(np.clip(0.4 + 0.6 * (rainfall_mm / max(0.1, mean_rain_adj + spread)), 0.0, 1.0)), 3)
    p_heavy = round(float(np.clip((rainfall_mm - 64.5) / max(0.1, spread), 0.0, 1.0)) if rainfall_mm > 20 else 0.0, 3)
    p_very_heavy = round(float(np.clip((rainfall_mm - 115.6) / max(0.1, spread), 0.0, 1.0)) if rainfall_mm > 50 else 0.0, 3)
    p_extreme = round(float(np.clip((rainfall_mm - 204.5) / max(0.1, spread), 0.0, 1.0)) if rainfall_mm > 100 else 0.0, 3)

    bounds = district.geometry.bounds
    cx = (bounds[0] + bounds[2]) / 2
    cy = (bounds[1] + bounds[3]) / 2
    hotspot_lon = round(cx + float(rng.uniform(-0.1, 0.1)), 4)
    hotspot_lat = round(cy + float(rng.uniform(-0.1, 0.1)), 4)
    hotspot_rainfall = round(max_mm * 1.1, 2)

    bbox_w = bounds[2] - bounds[0]
    bbox_h = bounds[3] - bounds[1]
    total_cells = max(1, int(bbox_w * 4) * max(1, int(bbox_h * 4)))
    valid_cells = max(1, int(total_cells * float(rng.uniform(0.7, 1.0))))
    coverage = round(valid_cells / total_cells, 3)

    primary_weight = float(rng.uniform(0.5, 0.85))
    other_regimes = [r for r in _REGIME_COLORS.keys() if r != regime]
    regime_dist: Dict[str, float] = {regime: round(primary_weight, 3)}
    remaining = 1.0 - primary_weight
    for i, r2 in enumerate(other_regimes[:2]):
        regime_dist[r2] = round(remaining * (0.7 if i == 0 else 0.3), 3)

    risk_cat, risk_desc, risk_color = _classify_risk(rainfall_mm)

    return DistrictForecastProduct(
        product_id=f"PROD_{district.district_id}_SYNTH_{lead_hours}H",
        district_id=district.district_id,
        district_name=district.district_name,
        state_id=district.state_id,
        state_name=district.state_name,
        forecast_valid_time=valid_time,
        initialization_time=init_time,
        lead_time_hours=lead_hours,
        aggregation_method="AREA_WEIGHTED",
        rainfall_mm=rainfall_mm,
        min_rainfall_mm=min_mm,
        max_rainfall_mm=max_mm,
        median_rainfall_mm=median_mm,
        p90_rainfall_mm=p90_mm,
        p95_rainfall_mm=p95_mm,
        p99_rainfall_mm=p99_mm,
        rain_probability=p_rain,
        heavy_probability=p_heavy,
        very_heavy_probability=p_very_heavy,
        extreme_probability=p_extreme,
        hotspot_latitude=hotspot_lat,
        hotspot_longitude=hotspot_lon,
        hotspot_rainfall_mm=hotspot_rainfall,
        valid_grid_cells=valid_cells,
        total_grid_cells=total_cells,
        coverage_fraction=coverage,
        regime_distribution=regime_dist,
        uncertainty={
            "uncertainty_available": True,
            "spread_mm": round(spread_val * 0.4, 2),
            "confidence_level": round(1.0 - (lead_hours / 240.0), 2),
            "method": "ENSEMBLE_SPREAD",
        },
        model_version="ramp_v1.0.0",
        dataset_version="ramp_v0.3.0",
        data_mode="SYNTHETIC_DEMO",
        boundary_version="v1.0.0",
        raw_nwp_rainfall_mm=nwp_mm,
        global_ml_rainfall_mm=global_ml_mm,
        difference_nwp_mm=round(rainfall_mm - nwp_mm, 2),
        difference_global_ml_mm=round(rainfall_mm - global_ml_mm, 2),
        risk_category=risk_cat,
        risk_description=risk_desc,
        color_hex=risk_color,
        hotspot_intensity=round(hotspot_rainfall / max(0.1, mean_rain_adj * 2), 2),
        max_heavy_probability=p_heavy,
        max_extreme_probability=p_extreme,
        high_risk_cells_count=int(valid_cells * p_heavy),
        area_km2=round(district.area_km2, 2),
        classification_rule="SYNTHETIC_CLIMATOLOGY_GAMMA",
    )


def _get_district_products(lead_hours: int = 24) -> List[DistrictForecastProduct]:
    global _cached_district_products, _cached_grid_cells
    if lead_hours not in _cached_district_products:
        df = _get_base_dataframe()
        if "lead_time_hours" in df.columns and lead_hours in df["lead_time_hours"].values:
            sub_df = df[df["lead_time_hours"] == lead_hours].copy()
        else:
            sub_df = df.copy()

        valid_time = f"2026-07-{14 + lead_hours // 24:02d}T00:00:00Z"
        init_time = "2026-07-14T00:00:00Z"

        cells = _grid_engine.build_grid_cells_from_dataframe(
            df=sub_df,
            valid_time=valid_time,
            init_time=init_time,
            lead_hours=lead_hours,
        )
        _cached_grid_cells[lead_hours] = cells

        districts = _boundary_provider.list_districts()
        intersections = GridDistrictIntersectionEngine.intersect_all_districts(districts, cells)

        products = []
        for d in districts:
            intersect_recs = intersections.get(d.district_id, [])
            if intersect_recs:
                prod = _agg_engine.aggregate_district(
                    district=d,
                    intersections=intersect_recs,
                    aggregation_method="AREA_WEIGHTED",
                )
                prod.data_mode = "SYNTHETIC_DEMO"
            else:
                seed_str = f"{d.district_id}_{lead_hours}"
                seed_int = int(hashlib.md5(seed_str.encode("utf-8")).hexdigest()[:8], 16)
                rng = np.random.default_rng(seed_int)
                prod = _generate_synthetic_district_product(d, lead_hours, valid_time, init_time, rng)
            products.append(prod)

        _cached_district_products[lead_hours] = products

    return _cached_district_products[lead_hours]

# ---------------------------------------------------------------------------
# API Responses
# ---------------------------------------------------------------------------

@router.get("")
@router.get("/")
def get_spatial_root(lead_hours: int = Query(24, ge=12, le=144)) -> Dict[str, Any]:
    """Root endpoint for /api/spatial and /api/forecast/spatial returning national summary."""
    return get_national_summary(lead_hours=lead_hours)


@router.get("/status")
def get_spatial_status() -> Dict[str, Any]:
    """Returns spatial engine operational readiness and dataset metadata."""
    meta = _boundary_provider.get_metadata()
    return {
        "status": "OPERATIONAL",
        "data_mode": "SYNTHETIC_DEMO",
        "banner": "SYNTHETIC DEMONSTRATION — REAL OPERATIONAL DATA NOT AVAILABLE",
        "product_version": SPATIAL_PRODUCT_VERSION,
        "model_version": "ramp_v1.0.0",
        "extreme_prob_version": "extreme_prob_v1.0.0",
        "regime_version": "regime_v1.0.0",
        "boundary_metadata": meta,
        "default_lead_time_hours": 24,
        "supported_lead_days": ["Day 1 (+24h)", "Day 2 (+48h)", "Day 3 (+72h)", "Day 4 (+96h)", "Day 5 (+120h)"],
        "default_aggregation_method": "AREA_WEIGHTED",
        "geographic_crs": _boundary_provider.geographic_crs,
        "projected_crs": _boundary_provider.projected_crs,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/grid")
def get_spatial_grid(
    lead_hours: int = Query(24, ge=12, le=144),
    limit: int = Query(100, ge=1, le=500),
) -> Dict[str, Any]:
    """Returns 0.25° grid cells with RAMP predictions and exceedance probabilities."""
    _get_district_products(lead_hours)
    cells = _cached_grid_cells.get(lead_hours, [])
    sample = [c.to_dict() for c in cells[:limit]]
    return {
        "data_mode": "SYNTHETIC_DEMO",
        "lead_time_hours": lead_hours,
        "forecast_valid_time": sample[0]["forecast_valid_time"] if sample else "",
        "total_cells": len(cells),
        "returned_cells": len(sample),
        "model_version": "ramp_v1.0.0",
        "cells": sample,
    }


@router.get("/districts")
def list_districts(
    lead_hours: int = Query(24, ge=12, le=144),
    risk_filter: Optional[str] = Query(None, description="Optional risk category filter"),
) -> Dict[str, Any]:
    """Lists district forecast products with area-weighted rainfall and hotspot diagnostics."""
    prods = _get_district_products(lead_hours)
    if risk_filter:
        filtered = [p for p in prods if p.risk_category.upper() == risk_filter.upper()]
    else:
        filtered = prods

    return {
        "data_mode": "SYNTHETIC_DEMO",
        "banner": "SYNTHETIC DEMONSTRATION — REAL OPERATIONAL DATA NOT AVAILABLE",
        "lead_time_hours": lead_hours,
        "total_districts": len(filtered),
        "aggregation_method": "AREA_WEIGHTED",
        "model_version": "ramp_v1.0.0",
        "boundary_version": _boundary_provider.dataset_version,
        "districts": [p.to_dict() for p in filtered],
    }


@router.get("/district/{district_id}")
@router.get("/districts/{district_id}")
def get_district_detail(
    district_id: str,
    lead_hours: int = Query(24, ge=12, le=144),
) -> Dict[str, Any]:
    """Returns granular forecast, hotspot, and uncertainty diagnostics for a single district."""
    prods = _get_district_products(lead_hours)
    did_clean = district_id.upper().replace("DIST_", "").replace("MAH_", "")
    target = next((
        p for p in prods 
        if p.district_id.upper() == district_id.upper()
        or p.district_name.upper() == district_id.upper()
        or p.district_id.upper() == did_clean
        or did_clean in p.district_id.upper()
        or p.district_id.upper() in did_clean
    ), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"District '{district_id}' not found.")

    boundary = _boundary_provider.get_district(target.district_id)
    return {
        "data_mode": "SYNTHETIC_DEMO",
        "product": target.to_dict(),
        "boundary_geometry": boundary.to_geojson_feature()["geometry"] if boundary else None,
        "provenance": {
            "model_version": target.model_version,
            "boundary_version": target.boundary_version,
            "aggregation_method": target.aggregation_method,
            "crs": _boundary_provider.projected_crs,
        },
    }


@router.get("/states")
def list_states(lead_hours: int = Query(24, ge=12, le=144)) -> Dict[str, Any]:
    """Returns state-level aggregations and risk summaries."""
    prods = _get_district_products(lead_hours)
    states_meta = _boundary_provider.list_states()

    state_products = []
    for s in states_meta:
        s_id = s["state_id"]
        d_prods = [p for p in prods if p.state_id == s_id]
        if not d_prods:
            continue

        weights = [max(1e-3, p.area_km2) for p in d_prods]
        total_w = sum(weights)
        area_weighted_rain = sum(w * p.rainfall_mm for w, p in zip(weights, d_prods)) / total_w
        max_d = max(d_prods, key=lambda x: x.rainfall_mm)

        high_risk = sum(1 for p in d_prods if p.risk_category == "HIGH_RAINFALL")
        vhigh_risk = sum(1 for p in d_prods if p.risk_category == "VERY_HIGH_RAINFALL")
        ext_risk = sum(1 for p in d_prods if p.risk_category == "EXTREME_RAINFALL")

        state_prod = StateForecastProduct(
            state_id=s_id,
            state_name=s["state_name"],
            forecast_valid_time=d_prods[0].forecast_valid_time,
            lead_time_hours=lead_hours,
            district_count=len(d_prods),
            total_area_km2=s["total_area_km2"],
            area_weighted_rainfall_mm=round(area_weighted_rain, 2),
            max_district_rainfall_mm=round(max_d.rainfall_mm, 2),
            max_rainfall_district=max_d.district_name,
            mean_rainfall_mm=round(float(np.mean([p.rainfall_mm for p in d_prods])), 2),
            high_risk_districts=high_risk,
            very_high_risk_districts=vhigh_risk,
            extreme_risk_districts=ext_risk,
            mean_heavy_probability=round(float(np.mean([p.heavy_probability for p in d_prods])), 4),
            mean_extreme_probability=round(float(np.mean([p.extreme_probability for p in d_prods])), 4),
            districts=[p.to_dict() for p in d_prods],
        )
        state_products.append(state_prod.to_dict())

    return {
        "data_mode": "SYNTHETIC_DEMO",
        "lead_time_hours": lead_hours,
        "total_states": len(state_products),
        "states": state_products,
    }


@router.get("/state/{state_id}")
def get_state_detail(
    state_id: str,
    lead_hours: int = Query(24, ge=12, le=144),
) -> Dict[str, Any]:
    """Returns single state summary with all contained districts."""
    states_res = list_states(lead_hours=lead_hours)
    target = next((s for s in states_res["states"] if s["state_id"].upper() == state_id.upper()), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"State '{state_id}' not found.")
    return target


@router.get("/summary")
def get_national_summary(lead_hours: int = Query(24, ge=12, le=144)) -> Dict[str, Any]:
    """National executive forecast bulletin across all monitored districts and states."""
    prods = _get_district_products(lead_hours)
    states_meta = _boundary_provider.list_states()

    covered = [p for p in prods if p.valid_grid_cells > 0]
    max_d = max(covered, key=lambda x: x.rainfall_mm) if covered else (prods[0] if prods else None)

    risk_counts: Dict[str, int] = {}
    for p in prods:
        risk_counts[p.risk_category] = risk_counts.get(p.risk_category, 0) + 1

    heavy_count = sum(1 for p in prods if p.heavy_probability >= 0.20)
    vheavy_count = sum(1 for p in prods if p.very_heavy_probability >= 0.10)
    ext_count = sum(1 for p in prods if p.extreme_probability >= 0.05)

    valid_cells_sum = sum(p.valid_grid_cells for p in prods)

    summary = NationalForecastSummary(
        forecast_valid_time=prods[0].forecast_valid_time if prods else "",
        lead_time_hours=lead_hours,
        data_mode="SYNTHETIC_DEMO",
        model_version="ramp_v1.0.0",
        boundary_version=_boundary_provider.dataset_version,
        total_districts_evaluated=len(prods),
        total_states_evaluated=len(states_meta),
        valid_grid_cells=valid_cells_sum,
        overall_coverage_pct=round(len(covered) / max(1, len(prods)) * 100.0, 1),
        districts_with_heavy_probability=heavy_count,
        districts_with_very_heavy_probability=vheavy_count,
        districts_with_extreme_probability=ext_count,
        max_predicted_district_rainfall_mm=max_d.rainfall_mm if max_d else 0.0,
        max_rainfall_district_name=max_d.district_name if max_d else "N/A",
        max_rainfall_state_name=max_d.state_name if max_d else "N/A",
        highest_risk_spatial_region=f"{max_d.district_name}, {max_d.state_name}" if max_d else "N/A",
        risk_category_counts=risk_counts,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    return summary.to_dict()


@router.get("/probability")
def get_spatial_probabilities(lead_hours: int = Query(24, ge=12, le=144)) -> Dict[str, Any]:
    """Returns spatial exceedance probabilities across IMD standard thresholds."""
    prods = _get_district_products(lead_hours)
    records = []
    for p in prods:
        records.append({
            "district_id": p.district_id,
            "district_name": p.district_name,
            "state_name": p.state_name,
            "rain_prob": p.rain_probability,
            "heavy_prob": p.heavy_probability,
            "very_heavy_prob": p.very_heavy_probability,
            "extreme_prob": p.extreme_probability,
            "max_heavy_prob": p.max_heavy_probability,
            "max_extreme_prob": p.max_extreme_probability,
        })
    return {
        "data_mode": "SYNTHETIC_DEMO",
        "lead_time_hours": lead_hours,
        "probabilities": records,
    }


@router.get("/hotspots")
def get_hotspots(lead_hours: int = Query(24, ge=12, le=144)) -> Dict[str, Any]:
    """Returns localized peak rainfall hotspots across districts."""
    prods = _get_district_products(lead_hours)
    hotspots = []
    for p in prods:
        if p.valid_grid_cells > 0 and p.hotspot_rainfall_mm > 0.0:
            hotspots.append({
                "district_id": p.district_id,
                "district_name": p.district_name,
                "state_name": p.state_name,
                "hotspot_latitude": p.hotspot_latitude,
                "hotspot_longitude": p.hotspot_longitude,
                "hotspot_rainfall_mm": p.hotspot_rainfall_mm,
                "district_mean_mm": p.rainfall_mm,
                "hotspot_intensity": p.hotspot_intensity,
                "max_heavy_prob": p.max_heavy_probability,
                "max_extreme_prob": p.max_extreme_probability,
                "risk_category": p.risk_category,
            })
    hotspots_sorted = sorted(hotspots, key=lambda x: x["hotspot_rainfall_mm"], reverse=True)
    return {
        "data_mode": "SYNTHETIC_DEMO",
        "lead_time_hours": lead_hours,
        "total_hotspots": len(hotspots_sorted),
        "hotspots": hotspots_sorted,
    }


@router.get("/regimes")
def get_regime_map(lead_hours: int = Query(24, ge=12, le=144)) -> Dict[str, Any]:
    """Exposes dominant weather regime and probability distribution by district."""
    prods = _get_district_products(lead_hours)
    records = []
    for p in prods:
        top_reg = max(p.regime_distribution.items(), key=lambda x: x[1])[0] if p.regime_distribution else "ACTIVE_MONSOON"
        records.append({
            "district_id": p.district_id,
            "district_name": p.district_name,
            "dominant_regime": top_reg,
            "regime_distribution": p.regime_distribution,
        })
    return {
        "data_mode": "SYNTHETIC_DEMO",
        "lead_time_hours": lead_hours,
        "regimes": records,
    }


@router.get("/uncertainty")
def get_uncertainty_map(lead_hours: int = Query(24, ge=12, le=144)) -> Dict[str, Any]:
    """Returns spatial spread, coverage penalty, and composite uncertainty by district."""
    prods = _get_district_products(lead_hours)
    records = []
    for p in prods:
        records.append({
            "district_id": p.district_id,
            "district_name": p.district_name,
            "state_name": p.state_name,
            "uncertainty": p.uncertainty,
        })
    return {
        "data_mode": "SYNTHETIC_DEMO",
        "lead_time_hours": lead_hours,
        "district_uncertainties": records,
    }


@router.get("/difference")
def get_difference_map(lead_hours: int = Query(24, ge=12, le=144)) -> Dict[str, Any]:
    """Calculates spatial difference maps: RAMP - Raw NWP and RAMP - Global ML."""
    prods = _get_district_products(lead_hours)
    records = []
    for p in prods:
        records.append({
            "district_id": p.district_id,
            "district_name": p.district_name,
            "state_name": p.state_name,
            "ramp_rainfall_mm": p.rainfall_mm,
            "raw_nwp_rainfall_mm": p.raw_nwp_rainfall_mm,
            "global_ml_rainfall_mm": p.global_ml_rainfall_mm,
            "difference_nwp_mm": p.difference_nwp_mm,
            "difference_global_ml_mm": p.difference_global_ml_mm,
            "correction_type": "POSITIVE_CORRECTION" if p.difference_nwp_mm > 0 else ("NEGATIVE_CORRECTION" if p.difference_nwp_mm < 0 else "ZERO_CORRECTION"),
        })
    return {
        "data_mode": "SYNTHETIC_DEMO",
        "lead_time_hours": lead_hours,
        "units": "mm",
        "differences": records,
    }


@router.get("/fss")
def get_fss_results() -> Dict[str, Any]:
    """Returns neighborhood Fractions Skill Score curves across scales and thresholds."""
    df = _get_base_dataframe()
    return FractionsSkillScoreService.evaluate_spatial_fss(df)


@router.get("/layers")
def list_spatial_layers() -> Dict[str, Any]:
    """Returns available forecast visualization layers and their operational availability."""
    return {
        "status": "SUCCESS",
        "layers": [
            {
                "id": "ramp_rainfall",
                "name": "RAMP MoE Calibrated Rainfall",
                "category": "Precipitation",
                "unit": "mm / day",
                "available": True,
                "description": "Regime-conditioned bias-corrected precipitation forecast from Mixture-of-Experts.",
            },
            {
                "id": "raw_nwp",
                "name": "Raw NCUM NWP Baseline",
                "category": "Precipitation",
                "unit": "mm / day",
                "available": True,
                "description": "Deterministic numerical weather prediction baseline from NCMRWF NCUM-G.",
            },
            {
                "id": "global_ml",
                "name": "Global ML Baseline",
                "category": "Precipitation",
                "unit": "mm / day",
                "available": True,
                "description": "Non-regime global machine learning baseline model.",
            },
            {
                "id": "diff_nwp",
                "name": "RAMP Correction (RAMP − NWP)",
                "category": "Diagnostics",
                "unit": "mm / day",
                "available": True,
                "description": "Spatial difference showing where RAMP increases (positive) or decreases (negative) rainfall.",
            },
            {
                "id": "prob_rain",
                "name": "Rainfall Exceedance P(≥0.1 mm)",
                "category": "Probabilistic",
                "unit": "Probability [0, 1]",
                "available": True,
                "description": "Calibrated probability of measurable precipitation.",
            },
            {
                "id": "prob_heavy",
                "name": "Heavy Rainfall P(≥64.5 mm)",
                "category": "Probabilistic",
                "unit": "Probability [0, 1]",
                "available": True,
                "description": "IMD Heavy rainfall threshold exceedance probability.",
            },
            {
                "id": "prob_very_heavy",
                "name": "Very Heavy Rainfall P(≥115.6 mm)",
                "category": "Probabilistic",
                "unit": "Probability [0, 1]",
                "available": True,
                "description": "IMD Very Heavy rainfall threshold exceedance probability.",
            },
            {
                "id": "prob_extreme",
                "name": "Extreme Rainfall P(≥204.5 mm)",
                "category": "Probabilistic",
                "unit": "Probability [0, 1]",
                "available": True,
                "description": "IMD Extremely Heavy rainfall threshold exceedance probability.",
            },
            {
                "id": "regime",
                "name": "Dominant Weather Regime",
                "category": "Diagnostics",
                "unit": "Regime Class",
                "available": True,
                "description": "Top classified Indian monsoon meteorological regime (e.g. Western Ghats, Monsoon Depression).",
            },
            {
                "id": "uncertainty",
                "name": "Forecast Uncertainty (Spread)",
                "category": "Diagnostics",
                "unit": "%",
                "available": True,
                "description": "Normalized ensemble spread across members quantifying forecast uncertainty.",
            },
            {
                "id": "obs",
                "name": "IMD 0.25° Gridded Observation",
                "category": "Verification",
                "unit": "mm / day",
                "available": False,
                "reason": "Authoritative IMD gridded observation file is not paired for this run.",
                "description": "Observed rainfall from India Meteorological Department ground truth.",
            },
            {
                "id": "error",
                "name": "Forecast Error (RAMP − Obs)",
                "category": "Verification",
                "unit": "mm / day",
                "available": False,
                "reason": "Requires paired ground truth observation.",
                "description": "True forecast residual error evaluated against genuine observations.",
            },
        ],
    }


@router.get("/verification")
def get_spatial_verification(lead_hours: int = Query(24, ge=12, le=144)) -> Dict[str, Any]:
    """Returns spatial verification metrics including FSS and baseline comparison."""
    return {
        "status": "VERIFICATION_PENDING",
        "data_mode": "SYNTHETIC_DEMO",
        "lead_time_hours": lead_hours,
        "fss_status": "FSS — VERIFICATION PENDING",
        "disclaimer": "REAL VERIFICATION NOT AVAILABLE: Authoritative IMD gridded observations are not mounted.",
        "scales_km": [5, 25, 50, 100, 200],
        "thresholds_mm": [0.1, 15.6, 64.5, 115.6, 204.5],
        "baseline_comparison": {
            "raw_nwp": {"mae": None, "rmse": None, "csi": None, "pod": None, "far": None, "ets": None},
            "baseline": {"mae": None, "rmse": None, "csi": None, "pod": None, "far": None, "ets": None},
            "ramp_moe": {"mae": None, "rmse": None, "csi": None, "pod": None, "far": None, "ets": None},
        },
        "reason": "Verification is conditionally calculated only when an authoritative IMD gridded observation file is paired.",
    }


@router.get("/geojson/{layer}")
@router.get("/geojson")
def get_spatial_geojson(
    layer: str = "districts",
    lead_hours: int = Query(24, ge=12, le=144),
) -> Dict[str, Any]:
    """Serves dynamic GeoJSON FeatureCollection layers for map rendering."""
    prods = _get_district_products(lead_hours)
    features = []

    if layer == "states":
        state_fc = _boundary_provider.to_geojson("states")
        states_summary = list_states(lead_hours=lead_hours)["states"]
        state_map = {s["state_id"]: s for s in states_summary}
        for feat in state_fc.get("features", []):
            s_id = feat["properties"].get("state_id")
            if s_id in state_map:
                feat["properties"].update(state_map[s_id])
            features.append(feat)

    elif layer == "india":
        india_fc = _boundary_provider.to_geojson("india")
        features = india_fc.get("features", [])

    elif layer in ("districts", "risk", "probability"):
        for p in prods:
            boundary = _boundary_provider.get_district(p.district_id)
            if not boundary:
                continue
            geom = boundary.to_geojson_feature()["geometry"]
            feat = {
                "type": "Feature",
                "properties": {
                    "district_id": p.district_id,
                    "district_name": p.district_name,
                    "state_id": p.state_id,
                    "state_name": p.state_name,
                    "rainfall_mm": p.rainfall_mm,
                    "raw_nwp_rainfall_mm": p.raw_nwp_rainfall_mm,
                    "difference_nwp_mm": p.difference_nwp_mm,
                    "min_rainfall_mm": p.min_rainfall_mm,
                    "max_rainfall_mm": p.max_rainfall_mm,
                    "rain_probability": p.rain_probability,
                    "heavy_probability": p.heavy_probability,
                    "very_heavy_probability": p.very_heavy_probability,
                    "extreme_probability": p.extreme_probability,
                    "risk_category": p.risk_category,
                    "color_hex": p.color_hex,
                    "hotspot_rainfall_mm": p.hotspot_rainfall_mm,
                    "hotspot_latitude": p.hotspot_latitude,
                    "hotspot_longitude": p.hotspot_longitude,
                    "coverage_fraction": p.coverage_fraction,
                    "lead_time_hours": p.lead_time_hours,
                    "forecast_valid_time": p.forecast_valid_time,
                },
                "geometry": geom,
            }
            features.append(feat)

    else:  # layer == "grid"
        cells = _cached_grid_cells.get(lead_hours, [])
        for c in cells[:350]:
            bounds = c.bounds
            feat = {
                "type": "Feature",
                "properties": {
                    "grid_id": c.grid_id,
                    "latitude": c.latitude,
                    "longitude": c.longitude,
                    "rainfall_mm": c.rainfall_prediction_mm,
                    "raw_nwp_mm": c.raw_nwp_rainfall_mm,
                    "correction_mm": round(c.rainfall_prediction_mm - c.raw_nwp_rainfall_mm, 2),
                    "heavy_probability": c.heavy_probability,
                    "extreme_probability": c.extreme_probability,
                    "regime": c.regime,
                    "uncertainty": c.uncertainty,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [bounds[0], bounds[1]],
                        [bounds[2], bounds[1]],
                        [bounds[2], bounds[3]],
                        [bounds[0], bounds[3]],
                        [bounds[0], bounds[1]],
                    ]],
                },
            }
            features.append(feat)

    return {
        "type": "FeatureCollection",
        "metadata": {
            "layer": layer,
            "data_mode": "SYNTHETIC_DEMO",
            "lead_time_hours": lead_hours,
            "feature_count": len(features),
            "crs": _boundary_provider.geographic_crs,
        },
        "features": features,
    }


@router.get("/export")
def get_spatial_exports(lead_hours: int = Query(24, ge=12, le=144)) -> Dict[str, Any]:
    """Generates and returns download artifacts in GeoJSON, CSV, and Parquet."""
    prods = _get_district_products(lead_hours)
    p_geo = _export_service.export_district_forecast_geojson(prods, _boundary_provider)
    p_csv = _export_service.export_district_csv(prods)
    p_par = _export_service.export_district_parquet(prods)

    return {
        "status": "SUCCESS",
        "data_mode": "SYNTHETIC_DEMO",
        "lead_time_hours": lead_hours,
        "files": {
            "geojson": p_geo,
            "csv": p_csv,
            "parquet": p_par,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_districts": len(prods),
    }
