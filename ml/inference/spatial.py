"""
Spatial, District, State & National Forecast Product Engine
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Parts J, K, L, M, N, O:
Maps grid-cell predictions to:
- Canonical India 0.25° Spatial Grid
- District Aggregations & Probability-First Risk Classification
- State-Level Syntheses
- National Operational Synopsis
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from ml.inference.config import GRID_LAT_MAX, GRID_LAT_MIN, GRID_LON_MAX, GRID_LON_MIN, GRID_RES_DEG
from ml.spatial.boundaries import BoundaryProvider, DistrictBoundary
from ml.spatial.grid import GridCell
from ml.spatial.risk import DEFAULT_RISK_RULES

logger = logging.getLogger(__name__)


class SpatialForecastEngine:
    """
    Constructs high-resolution spatial, district, and state products from point inferences.
    """

    def __init__(self, boundary_provider: Optional[BoundaryProvider] = None):
        self.boundaries = boundary_provider or BoundaryProvider()

    def generate_grid_cells(
        self,
        grid_points: List[Dict[str, float]],
        continuous_preds: Dict[str, np.ndarray],
        prob_preds: Dict[str, np.ndarray],
        initialization_time: str,
        forecast_valid_time: str,
        lead_time_hours: int,
        data_mode: str = "SYNTHETIC_DEMO",
        model_version: str = "ramp_moe_v2.0.0",
    ) -> List[GridCell]:
        """
        Converts array predictions into a collection of validated GridCell domain objects.
        """
        cells = []
        n = len(grid_points)

        for i in range(n):
            lat = grid_points[i]["latitude"]
            lon = grid_points[i]["longitude"]
            grid_id = f"G_{lat:.2f}_{lon:.2f}"

            reg_probs = {}
            if "regime_probabilities" in continuous_preds and len(continuous_preds["regime_probabilities"]) > i:
                raw_rp = continuous_preds["regime_probabilities"][i]
                from ml.regimes.definitions import REGIME_ORDER
                reg_probs = {r.value: float(raw_rp[idx]) for idx, r in enumerate(REGIME_ORDER)}

            cell = GridCell(
                grid_id=grid_id,
                latitude=round(lat, 2),
                longitude=round(lon, 2),
                forecast_valid_time=forecast_valid_time,
                initialization_time=initialization_time,
                lead_time_hours=lead_time_hours,
                rainfall_prediction_mm=float(continuous_preds["ramp_moe"][i]),
                raw_nwp_rainfall_mm=float(continuous_preds["raw_nwp"][i]),
                global_ml_rainfall_mm=float(continuous_preds["global_ml"][i]),
                rainfall_probability=float(prob_preds["prob_rain"][i]),
                heavy_probability=float(prob_preds["prob_heavy"][i]),
                very_heavy_probability=float(prob_preds["prob_very_heavy"][i]),
                extreme_probability=float(prob_preds["prob_extreme"][i]),
                regime=str(continuous_preds["dominant_regime"][i]),
                regime_probabilities=reg_probs,
                uncertainty=float(continuous_preds["uncertainty"][i]),
                data_mode=data_mode,
                model_version=model_version,
            )
            cells.append(cell)

        return cells

    def aggregate_districts(
        self,
        cells: List[GridCell],
    ) -> List[Dict[str, Any]]:
        """
        Aggregates grid cells into representative district forecast products.
        Assigns probability-first risk classification (Part M).
        """
        districts = self.boundaries.list_districts()
        district_products = []

        for dist in districts:
            min_lon, min_lat, max_lon, max_lat = dist.bbox

            # Spatial filtering of cells inside district bounding box
            matching_cells = [
                c for c in cells
                if min_lat <= c.latitude <= max_lat and min_lon <= c.longitude <= max_lon
            ]

            if not matching_cells:
                # If district bbox has no grid cell (edge case), use nearest cell
                nearest = min(cells, key=lambda c: (c.latitude - (min_lat + max_lat)/2)**2 + (c.longitude - (min_lon + max_lon)/2)**2)
                matching_cells = [nearest]

            ramp_rain = float(np.mean([c.rainfall_prediction_mm for c in matching_cells]))
            raw_nwp = float(np.mean([c.raw_nwp_rainfall_mm for c in matching_cells]))
            global_ml = float(np.mean([c.global_ml_rainfall_mm for c in matching_cells]))
            correction = ramp_rain - raw_nwp
            pct_corr = round((correction / max(0.1, raw_nwp)) * 100.0, 1)

            p_rain = float(np.mean([c.rainfall_probability for c in matching_cells]))
            p_heavy = float(np.mean([c.heavy_probability for c in matching_cells]))
            p_very_heavy = float(np.mean([c.very_heavy_probability for c in matching_cells]))
            p_extreme = float(np.mean([c.extreme_probability for c in matching_cells]))
            uncertainty = float(np.mean([c.uncertainty for c in matching_cells]))

            # Dominant regime across district cells
            regimes = [c.regime for c in matching_cells]
            dominant_regime = max(set(regimes), key=regimes.count)

            # Determine risk category using canonical rules
            risk_category = "NORMAL"
            for rule in DEFAULT_RISK_RULES:
                if (
                    ramp_rain >= rule.min_rainfall_mm
                    or p_heavy >= rule.min_heavy_prob
                    or p_very_heavy >= rule.min_very_heavy_prob
                    or p_extreme >= rule.min_extreme_prob
                ):
                    risk_category = rule.category
                    break

            district_products.append({
                "district_id": dist.district_id,
                "district_name": dist.district_name,
                "state_id": dist.state_id,
                "state_name": dist.state_name,
                "lead_time_hours": matching_cells[0].lead_time_hours,
                "forecast_valid_time": matching_cells[0].forecast_valid_time,
                "rainfall": {
                    "ramp_mm": round(ramp_rain, 2),
                    "raw_nwp_mm": round(raw_nwp, 2),
                    "global_ml_mm": round(global_ml, 2),
                    "correction_mm": round(correction, 2),
                    "percentage_correction": pct_corr,
                },
                "probabilities": {
                    "rain": round(p_rain, 4),
                    "heavy": round(p_heavy, 4),
                    "very_heavy": round(p_very_heavy, 4),
                    "extreme": round(p_extreme, 4),
                },
                "regime": {
                    "dominant_regime": dominant_regime,
                    "confidence": round(float(np.mean([c.regime_probabilities.get(dominant_regime, 0.5) for c in matching_cells])), 4),
                },
                "uncertainty_mm": round(uncertainty, 2),
                "risk_category": risk_category,
                "sample_grid_cells_count": len(matching_cells),
                "data_mode": matching_cells[0].data_mode,
            })

        return sorted(district_products, key=lambda x: x["rainfall"]["ramp_mm"], reverse=True)

    def aggregate_states(
        self,
        district_products: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Synthesizes district forecasts into State Operational Summaries (Part N).
        """
        state_map: Dict[str, List[Dict[str, Any]]] = {}
        for d in district_products:
            s_name = d["state_name"]
            if s_name not in state_map:
                state_map[s_name] = []
            state_map[s_name].append(d)

        state_summaries = []
        for s_name, d_list in state_map.items():
            rains = [d["rainfall"]["ramp_mm"] for d in d_list]
            p_extremes = [d["probabilities"]["extreme"] for d in d_list]
            regimes = [d["regime"]["dominant_regime"] for d in d_list]
            dom_reg = max(set(regimes), key=regimes.count)

            high_risk_count = sum(1 for d in d_list if d["risk_category"] in ("HIGH_RAINFALL", "VERY_HIGH_RAINFALL", "EXTREME_RAINFALL"))

            state_summaries.append({
                "state_name": s_name,
                "state_id": d_list[0]["state_id"],
                "district_count": len(d_list),
                "lead_time_hours": d_list[0]["lead_time_hours"],
                "forecast_valid_time": d_list[0]["forecast_valid_time"],
                "mean_rainfall_mm": round(float(np.mean(rains)), 2),
                "max_rainfall_mm": round(float(np.max(rains)), 2),
                "p95_rainfall_mm": round(float(np.percentile(rains, 95)), 2),
                "max_extreme_probability": round(float(np.max(p_extremes)), 4),
                "dominant_regime": dom_reg,
                "high_risk_district_count": high_risk_count,
                "data_mode": d_list[0]["data_mode"],
            })

        return sorted(state_summaries, key=lambda x: x["max_rainfall_mm"], reverse=True)

    def generate_national_summary(
        self,
        cells: List[GridCell],
        district_products: List[Dict[str, Any]],
        state_summaries: List[Dict[str, Any]],
        cycle_info: Any,
        lead_time_hours: int,
    ) -> Dict[str, Any]:
        """
        Generates National Meteorological Synopsis (Part O).
        """
        rains = [c.rainfall_prediction_mm for c in cells]
        raw_rains = [c.raw_nwp_rainfall_mm for c in cells]
        p_extremes = [c.extreme_probability for c in cells]
        regimes = [c.regime for c in cells]

        affected_cells = sum(1 for r in rains if r >= 2.5)
        affected_districts = sum(1 for d in district_products if d["rainfall"]["ramp_mm"] >= 2.5)
        affected_states = sum(1 for s in state_summaries if s["max_rainfall_mm"] >= 2.5)

        return {
            "forecast_cycle": getattr(cycle_info, "cycle_utc", "00 UTC"),
            "initialization_time": getattr(cycle_info, "initialization_time", "2026-09-27T00:00:00Z"),
            "lead_time_hours": lead_time_hours,
            "forecast_valid_time": cells[0].forecast_valid_time if cells else "N/A",
            "data_source": getattr(cycle_info, "model", "NCUM_SYNTHETIC_DEMO"),
            "model_version": cells[0].model_version if cells else "ramp_moe_v2.0.0",
            "data_mode": cells[0].data_mode if cells else "SYNTHETIC_DEMO",
            "national_metrics": {
                "mean_ramp_rainfall_mm": round(float(np.mean(rains)), 2),
                "max_ramp_rainfall_mm": round(float(np.max(rains)), 2),
                "mean_raw_nwp_mm": round(float(np.mean(raw_rains)), 2),
                "max_raw_nwp_mm": round(float(np.max(raw_rains)), 2),
                "max_extreme_probability": round(float(np.max(p_extremes)), 4),
                "affected_grid_cells_count": affected_cells,
                "affected_districts_count": affected_districts,
                "affected_states_count": affected_states,
                "dominant_regime": max(set(regimes), key=regimes.count),
            },
        }
