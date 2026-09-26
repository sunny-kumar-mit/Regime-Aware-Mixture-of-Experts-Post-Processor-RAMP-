"""
RAMP Canonical Spatial Grid Engine
SIH26080 | Spatial Forecast Products & District Aggregation
MoES / NCMRWF

Consumes the Phase 8 canonical 0.25° × 0.25° India domain grid:
  Latitude:  6.5°N - 38.5°N (129 points)
  Longitude: 66.5°E - 100.5°E (137 points)
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from shapely.geometry import Polygon, box

STANDARD_LAT_MIN = 6.5
STANDARD_LAT_MAX = 38.5
STANDARD_LON_MIN = 66.5
STANDARD_LON_MAX = 100.5
STANDARD_RES_DEG = 0.25


@dataclass
class GridCell:
    """
    Validated single grid-cell forecast product representation.
    """
    grid_id: str
    latitude: float
    longitude: float
    forecast_valid_time: str
    initialization_time: str
    lead_time_hours: int
    rainfall_prediction_mm: float
    rainfall_probability: float
    heavy_probability: float
    very_heavy_probability: float
    extreme_probability: float
    regime: str
    regime_probabilities: Dict[str, float] = field(default_factory=dict)
    uncertainty: float = 0.0
    data_mode: str = "SYNTHETIC_DEMO"
    model_version: str = "ramp_v1.0.0"
    raw_nwp_rainfall_mm: float = 0.0
    global_ml_rainfall_mm: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """Returns (min_lon, min_lat, max_lon, max_lat) for 0.25° cell."""
        half_res = STANDARD_RES_DEG / 2.0
        return (
            round(self.longitude - half_res, 4),
            round(self.latitude - half_res, 4),
            round(self.longitude + half_res, 4),
            round(self.latitude + half_res, 4),
        )

    @property
    def polygon(self) -> Polygon:
        """Returns Shapely Polygon representing the grid cell bounding box."""
        min_lon, min_lat, max_lon, max_lat = self.bounds
        return box(min_lon, min_lat, max_lon, max_lat)

    @property
    def cell_area_km2(self) -> float:
        """
        Calculates exact physical spherical area of this 0.25° x 0.25° cell in km².
        R_earth = 6371.0 km
        """
        r = 6371.0
        half_res = np.radians(STANDARD_RES_DEG / 2.0)
        phi = np.radians(self.latitude)
        d_lambda = np.radians(STANDARD_RES_DEG)
        phi_south = phi - half_res
        phi_north = phi + half_res
        area = (r ** 2) * d_lambda * (np.sin(phi_north) - np.sin(phi_south))
        return float(np.abs(area))


class SpatialGridEngine:
    """
    Manages grid indexing, cell generation, and spatiotemporal coordinate alignment.
    """

    def __init__(
        self,
        lat_min: float = STANDARD_LAT_MIN,
        lat_max: float = STANDARD_LAT_MAX,
        lon_min: float = STANDARD_LON_MIN,
        lon_max: float = STANDARD_LON_MAX,
        res_deg: float = STANDARD_RES_DEG,
    ) -> None:
        self.lat_min = lat_min
        self.lat_max = lat_max
        self.lon_min = lon_min
        self.lon_max = lon_max
        self.res_deg = res_deg

        self.latitudes = np.round(
            np.arange(lat_min, lat_max + res_deg / 2.0, res_deg), 4
        )
        self.longitudes = np.round(
            np.arange(lon_min, lon_max + res_deg / 2.0, res_deg), 4
        )

    @staticmethod
    def generate_grid_id(lat: float, lon: float) -> str:
        """Generates standard unique canonical grid ID: e.g. 'GRID_21.000N_078.250E'."""
        ns = "N" if lat >= 0 else "S"
        ew = "E" if lon >= 0 else "W"
        return f"GRID_{abs(lat):06.3f}{ns}_{abs(lon):07.3f}{ew}"

    def build_grid_cells_from_dataframe(
        self,
        df: pd.DataFrame,
        valid_time: str,
        init_time: str,
        lead_hours: int = 24,
        data_mode: str = "SYNTHETIC_DEMO",
        model_version: str = "ramp_v1.0.0",
    ) -> List[GridCell]:
        """
        Converts prediction DataFrame into validated GridCell instances.
        """
        cells: List[GridCell] = []
        for _, row in df.iterrows():
            lat = float(row["latitude"])
            lon = float(row["longitude"])
            grid_id = str(row.get("grid_id", self.generate_grid_id(lat, lon)))

            # Deterministic and probabilistic outputs
            ramp_pred = float(row.get("ramp_pred", row.get("rainfall_prediction_mm", 0.0)))
            raw_nwp = float(row.get("nwp_rainfall_mm", row.get("raw_nwp_rainfall", 0.0)))
            global_ml = float(row.get("global_ml_pred", ramp_pred * 0.95))

            p_rain = float(row.get("p_rain", 1.0 if ramp_pred >= 0.1 else 0.15))
            p_heavy = float(row.get("p_heavy", min(p_rain, 0.85 if ramp_pred >= 64.5 else (0.25 if ramp_pred >= 35.0 else 0.05))))
            p_very_heavy = float(row.get("p_very_heavy", min(p_heavy, 0.70 if ramp_pred >= 115.6 else 0.02)))
            p_extreme = float(row.get("p_extreme", min(p_very_heavy, 0.50 if ramp_pred >= 204.5 else 0.005)))

            regime = str(row.get("top_regime", row.get("regime", "ACTIVE_MONSOON")))
            regime_probs = row.get("regime_probabilities", {regime: 0.85, "TRANSITION_OTHER": 0.15})
            uncertainty = float(row.get("uncertainty", 0.12))

            row_valid_time = str(row.get("forecast_valid_time", valid_time))
            row_init_time = str(row.get("forecast_initialization_time", init_time))
            row_lead = int(row.get("lead_time_hours", lead_hours))

            cell = GridCell(
                grid_id=grid_id,
                latitude=round(lat, 4),
                longitude=round(lon, 4),
                forecast_valid_time=row_valid_time,
                initialization_time=row_init_time,
                lead_time_hours=row_lead,
                rainfall_prediction_mm=max(0.0, round(ramp_pred, 2)),
                rainfall_probability=round(np.clip(p_rain, 0.0, 1.0), 4),
                heavy_probability=round(np.clip(p_heavy, 0.0, 1.0), 4),
                very_heavy_probability=round(np.clip(p_very_heavy, 0.0, 1.0), 4),
                extreme_probability=round(np.clip(p_extreme, 0.0, 1.0), 4),
                regime=regime,
                regime_probabilities=regime_probs if isinstance(regime_probs, dict) else {},
                uncertainty=round(uncertainty, 4),
                data_mode=data_mode,
                model_version=model_version,
                raw_nwp_rainfall_mm=max(0.0, round(raw_nwp, 2)),
                global_ml_rainfall_mm=max(0.0, round(global_ml, 2)),
            )
            cells.append(cell)
        return cells
