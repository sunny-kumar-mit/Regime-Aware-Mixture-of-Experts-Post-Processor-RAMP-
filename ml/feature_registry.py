"""
RAMP Centralized Feature Registry
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Central repository of all canonical meteorological, geographical, temporal,
and ensemble features. Ensures full auditability, provenance tracking,
and strict prevention of target leakage.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional
from ml.schemas import FeatureSpec


# =============================================================================
# Canonical Feature Definitions
# =============================================================================

CANONICAL_FEATURES: Dict[str, FeatureSpec] = {
    # -------------------------------------------------------------------------
    # Core NWP Raw Predictors
    # -------------------------------------------------------------------------
    "raw_nwp_rainfall": FeatureSpec(
        name="raw_nwp_rainfall",
        description="Raw NWP forecasted precipitation accumulation",
        source="nwp.tp",
        unit="mm",
        dtype="float32",
        required=True,
        derivation="Accumulated surface precipitation over forecast window",
        leakage_risk="none",
        available=True,
    ),
    "lead_time_hours": FeatureSpec(
        name="lead_time_hours",
        description="Forecast horizon from model initialization",
        source="forecast_spec.lead_time_hours",
        unit="hours",
        dtype="int32",
        required=True,
        derivation="forecast_valid_time - initialization_time",
        leakage_risk="none",
        available=True,
    ),
    "u850": FeatureSpec(
        name="u850",
        description="Zonal wind velocity at 850 hPa isobaric level (positive eastward)",
        source="nwp.u850",
        unit="m/s",
        dtype="float32",
        required=False,
        derivation="Direct NWP isobaric wind component",
        leakage_risk="none",
        available=True,
    ),
    "v850": FeatureSpec(
        name="v850",
        description="Meridional wind velocity at 850 hPa isobaric level (positive northward)",
        source="nwp.v850",
        unit="m/s",
        dtype="float32",
        required=False,
        derivation="Direct NWP isobaric wind component",
        leakage_risk="none",
        available=True,
    ),
    "mslp": FeatureSpec(
        name="mslp",
        description="Mean sea level atmospheric pressure",
        source="nwp.mslp",
        unit="Pa",
        dtype="float32",
        required=False,
        derivation="Reduced surface pressure to sea level",
        leakage_risk="none",
        available=True,
    ),
    "temperature": FeatureSpec(
        name="temperature",
        description="2-meter air temperature",
        source="nwp.t2m",
        unit="K",
        dtype="float32",
        required=False,
        derivation="Near-surface air temperature",
        leakage_risk="none",
        available=True,
    ),
    "relative_humidity": FeatureSpec(
        name="relative_humidity",
        description="2-meter or 850 hPa relative humidity",
        source="nwp.rh",
        unit="%",
        dtype="float32",
        required=False,
        derivation="Vapour pressure relative to saturation vapour pressure",
        leakage_risk="none",
        available=True,
    ),
    "precipitable_water": FeatureSpec(
        name="precipitable_water",
        description="Total column integrated water vapour",
        source="nwp.tcwv",
        unit="kg/m^2",
        dtype="float32",
        required=False,
        derivation="Vertical integral of specific humidity",
        leakage_risk="none",
        available=True,
    ),
    "cape": FeatureSpec(
        name="cape",
        description="Convective Available Potential Energy",
        source="nwp.cape",
        unit="J/kg",
        dtype="float32",
        required=False,
        derivation="Vertical integral of parcel buoyant energy",
        leakage_risk="none",
        available=True,
    ),
    "geopotential_height": FeatureSpec(
        name="geopotential_height",
        description="Geopotential height at 500 hPa isobaric surface",
        source="nwp.gh500",
        unit="m",
        dtype="float32",
        required=False,
        derivation="Geopotential divided by standard gravity g0 (9.80665 m/s^2)",
        leakage_risk="none",
        available=True,
    ),

    # -------------------------------------------------------------------------
    # Physically Meaningful Derived Meteorological Features
    # -------------------------------------------------------------------------
    "wind_speed_850": FeatureSpec(
        name="wind_speed_850",
        description="Horizontal wind speed magnitude at 850 hPa",
        source="u850, v850",
        unit="m/s",
        dtype="float32",
        required=False,
        derivation="sqrt(u850^2 + v850^2)",
        leakage_risk="none",
        available=True,
    ),
    "wind_direction_850": FeatureSpec(
        name="wind_direction_850",
        description="Meteorological wind direction at 850 hPa (degrees clockwise from North, indicating direction from which wind blows)",
        source="u850, v850",
        unit="degrees",
        dtype="float32",
        required=False,
        derivation="(270.0 - atan2(v850, u850) * 180.0 / pi) % 360.0",
        leakage_risk="none",
        available=True,
    ),

    # -------------------------------------------------------------------------
    # Spatial Neighborhood Predictor Features (Derived from NWP only)
    # -------------------------------------------------------------------------
    "rainfall_mean_3x3": FeatureSpec(
        name="rainfall_mean_3x3",
        description="3x3 grid neighborhood mean of NWP raw rainfall forecast",
        source="raw_nwp_rainfall",
        unit="mm",
        dtype="float32",
        required=False,
        derivation="Spatial 3x3 uniform convolution on NWP rainfall grid at valid time",
        leakage_risk="none",
        available=True,
    ),
    "rainfall_max_3x3": FeatureSpec(
        name="rainfall_max_3x3",
        description="3x3 grid neighborhood maximum of NWP raw rainfall forecast",
        source="raw_nwp_rainfall",
        unit="mm",
        dtype="float32",
        required=False,
        derivation="Spatial 3x3 max pooling on NWP rainfall grid at valid time",
        leakage_risk="none",
        available=True,
    ),
    "rainfall_std_3x3": FeatureSpec(
        name="rainfall_std_3x3",
        description="3x3 grid neighborhood standard deviation of NWP raw rainfall",
        source="raw_nwp_rainfall",
        unit="mm",
        dtype="float32",
        required=False,
        derivation="Spatial 3x3 local standard deviation on NWP rainfall grid",
        leakage_risk="none",
        available=True,
    ),

    # -------------------------------------------------------------------------
    # Geographical Features
    # -------------------------------------------------------------------------
    "latitude": FeatureSpec(
        name="latitude",
        description="Grid point latitude coordinate (India domain 6.5°N - 38.5°N)",
        source="grid.lat",
        unit="degrees_north",
        dtype="float32",
        required=True,
        derivation="Canonical grid coordinate",
        leakage_risk="none",
        available=True,
    ),
    "longitude": FeatureSpec(
        name="longitude",
        description="Grid point longitude coordinate (India domain 66.5°E - 100.5°E)",
        source="grid.lon",
        unit="degrees_east",
        dtype="float32",
        required=True,
        derivation="Canonical grid coordinate",
        leakage_risk="none",
        available=True,
    ),
    "elevation": FeatureSpec(
        name="elevation",
        description="Terrain surface elevation above mean sea level from DEM",
        source="dem.elevation",
        unit="m",
        dtype="float32",
        required=False,
        derivation="Bilinear interpolation from Digital Elevation Model (SRTM/CartoDEM)",
        leakage_risk="none",
        available=False,  # Honest: DEM dataset not yet ingested
    ),
    "distance_to_coast": FeatureSpec(
        name="distance_to_coast",
        description="Shortest geodesic distance to Indian coastline",
        source="gis.coastline",
        unit="km",
        dtype="float32",
        required=False,
        derivation="Minimum Haversine distance to digitized coastline geometry",
        leakage_risk="none",
        available=False,  # Honest: Coastline GIS layer not yet loaded
    ),

    # -------------------------------------------------------------------------
    # Temporal & Cyclic Features
    # -------------------------------------------------------------------------
    "day_of_year_sin": FeatureSpec(
        name="day_of_year_sin",
        description="Sine component of annual seasonal cycle",
        source="forecast_valid_time.timetuple().tm_yday",
        unit="dimensionless",
        dtype="float32",
        required=True,
        derivation="sin(2 * pi * day_of_year / 365.25)",
        leakage_risk="none",
        available=True,
    ),
    "day_of_year_cos": FeatureSpec(
        name="day_of_year_cos",
        description="Cosine component of annual seasonal cycle",
        source="forecast_valid_time.timetuple().tm_yday",
        unit="dimensionless",
        dtype="float32",
        required=True,
        derivation="cos(2 * pi * day_of_year / 365.25)",
        leakage_risk="none",
        available=True,
    ),
    "valid_hour_sin": FeatureSpec(
        name="valid_hour_sin",
        description="Sine component of diurnal diurnal cycle",
        source="forecast_valid_time.hour",
        unit="dimensionless",
        dtype="float32",
        required=True,
        derivation="sin(2 * pi * valid_hour / 24.0)",
        leakage_risk="none",
        available=True,
    ),
    "valid_hour_cos": FeatureSpec(
        name="valid_hour_cos",
        description="Cosine component of diurnal diurnal cycle",
        source="forecast_valid_time.hour",
        unit="dimensionless",
        dtype="float32",
        required=True,
        derivation="cos(2 * pi * valid_hour / 24.0)",
        leakage_risk="none",
        available=True,
    ),

    # -------------------------------------------------------------------------
    # Monsoon Seasonality Indicators
    # -------------------------------------------------------------------------
    "pre_monsoon": FeatureSpec(
        name="pre_monsoon",
        description="IMD Pre-monsoon season indicator (March to May)",
        source="forecast_valid_time.month in [3, 4, 5]",
        unit="binary",
        dtype="int32",
        required=True,
        derivation="1 if month in [3, 4, 5] else 0",
        leakage_risk="none",
        available=True,
    ),
    "monsoon": FeatureSpec(
        name="monsoon",
        description="IMD Southwest Monsoon season indicator (June to September)",
        source="forecast_valid_time.month in [6, 7, 8, 9]",
        unit="binary",
        dtype="int32",
        required=True,
        derivation="1 if month in [6, 7, 8, 9] else 0",
        leakage_risk="none",
        available=True,
    ),
    "post_monsoon": FeatureSpec(
        name="post_monsoon",
        description="IMD Post-monsoon season indicator (October to December)",
        source="forecast_valid_time.month in [10, 11, 12]",
        unit="binary",
        dtype="int32",
        required=True,
        derivation="1 if month in [10, 11, 12] else 0",
        leakage_risk="none",
        available=True,
    ),
    "winter": FeatureSpec(
        name="winter",
        description="IMD Winter season indicator (January to February)",
        source="forecast_valid_time.month in [1, 2]",
        unit="binary",
        dtype="int32",
        required=True,
        derivation="1 if month in [1, 2] else 0",
        leakage_risk="none",
        available=True,
    ),

    # -------------------------------------------------------------------------
    # Ensemble Derived Features (Computed only when multiple members exist)
    # -------------------------------------------------------------------------
    "ensemble_mean_rainfall": FeatureSpec(
        name="ensemble_mean_rainfall",
        description="Ensemble mean precipitation forecast across all available members",
        source="gefs.tp across members",
        unit="mm",
        dtype="float32",
        required=False,
        derivation="mean(member_rainfall)",
        leakage_risk="none",
        available=True,
    ),
    "ensemble_std_rainfall": FeatureSpec(
        name="ensemble_std_rainfall",
        description="Ensemble spread (standard deviation) across forecast members",
        source="gefs.tp across members",
        unit="mm",
        dtype="float32",
        required=False,
        derivation="std(member_rainfall)",
        leakage_risk="none",
        available=True,
    ),
    "ensemble_min_rainfall": FeatureSpec(
        name="ensemble_min_rainfall",
        description="Ensemble minimum precipitation forecast across members",
        source="gefs.tp across members",
        unit="mm",
        dtype="float32",
        required=False,
        derivation="min(member_rainfall)",
        leakage_risk="none",
        available=True,
    ),
    "ensemble_max_rainfall": FeatureSpec(
        name="ensemble_max_rainfall",
        description="Ensemble maximum precipitation forecast across members",
        source="gefs.tp across members",
        unit="mm",
        dtype="float32",
        required=False,
        derivation="max(member_rainfall)",
        leakage_risk="none",
        available=True,
    ),
}


class FeatureAvailabilityRegistry:
    """Manages availability, queries, and JSON export of features."""

    def __init__(self, features: Optional[Dict[str, FeatureSpec]] = None):
        self._features: Dict[str, FeatureSpec] = dict(features or CANONICAL_FEATURES)

    def get(self, name: str) -> Optional[FeatureSpec]:
        return self._features.get(name)

    def list_features(self, available_only: bool = False) -> List[FeatureSpec]:
        if available_only:
            return [f for f in self._features.values() if f.available]
        return list(self._features.values())

    def set_availability(self, name: str, available: bool) -> None:
        if name in self._features:
            spec = self._features[name]
            self._features[name] = spec.model_copy(update={"available": available})

    def export_json(self, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = {name: spec.model_dump() for name, spec in self._features.items()}
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return output_path

    @classmethod
    def load_json(cls, input_path: Path) -> "FeatureAvailabilityRegistry":
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        features = {name: FeatureSpec(**spec_data) for name, spec_data in data.items()}
        return cls(features)


# Global default instance
feature_registry = FeatureAvailabilityRegistry()
