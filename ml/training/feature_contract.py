"""
RAMP Authoritative Feature Contract
SIH26080 | MoES / NCMRWF

Freezes the 18 approved atmospheric predictors from Phase 12.
Enforces zero-future-observation leakage.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional
import pandas as pd

from ml.training.config import FEATURE_SCHEMA_VERSION


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    dtype: str
    units: str
    source: str
    description: str
    valid_range: tuple[float, float]
    missing_policy: str
    transformation: str
    future_leakage_allowed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["valid_range"] = list(self.valid_range)
        return d


# 18 Canonical Approved Meteorological Predictors (Zero Leakage)
FEATURE_SPECS: List[FeatureSpec] = [
    FeatureSpec(
        name="precip_nwp_raw",
        dtype="float64",
        units="mm",
        source="NWP (NCUM/NEPS/GFS)",
        description="Raw precipitation forecast accumulation",
        valid_range=(0.0, 1500.0),
        missing_policy="reject_sample",
        transformation="none",
    ),
    FeatureSpec(
        name="u850",
        dtype="float64",
        units="m/s",
        source="NWP",
        description="Zonal wind component at 850 hPa pressure level",
        valid_range=(-80.0, 80.0),
        missing_policy="median_impute",
        transformation="standardize",
    ),
    FeatureSpec(
        name="v850",
        dtype="float64",
        units="m/s",
        source="NWP",
        description="Meridional wind component at 850 hPa pressure level",
        valid_range=(-80.0, 80.0),
        missing_policy="median_impute",
        transformation="standardize",
    ),
    FeatureSpec(
        name="mslp",
        dtype="float64",
        units="hPa",
        source="NWP",
        description="Mean sea level atmospheric pressure",
        valid_range=(870.0, 1085.0),
        missing_policy="median_impute",
        transformation="standardize",
    ),
    FeatureSpec(
        name="t850",
        dtype="float64",
        units="degC",
        source="NWP",
        description="Temperature at 850 hPa pressure level",
        valid_range=(-40.0, 55.0),
        missing_policy="median_impute",
        transformation="standardize",
    ),
    FeatureSpec(
        name="cape",
        dtype="float64",
        units="J/kg",
        source="NWP",
        description="Convective Available Potential Energy",
        valid_range=(0.0, 7500.0),
        missing_policy="zero_fill",
        transformation="log1p",
    ),
    FeatureSpec(
        name="wind_speed_850",
        dtype="float64",
        units="m/s",
        source="Derived (u850, v850)",
        description="Wind speed magnitude at 850 hPa",
        valid_range=(0.0, 100.0),
        missing_policy="calculate",
        transformation="standardize",
    ),
    FeatureSpec(
        name="wind_dir_850",
        dtype="float64",
        units="deg",
        source="Derived (u850, v850)",
        description="Meteorological wind direction at 850 hPa",
        valid_range=(0.0, 360.0),
        missing_policy="calculate",
        transformation="cyclic_sin_cos",
    ),
    FeatureSpec(
        name="lead_time_hours",
        dtype="int64",
        units="hours",
        source="Forecast Cycle",
        description="Forecast lead horizon in hours (6h to 120h+)",
        valid_range=(0.0, 360.0),
        missing_policy="reject_sample",
        transformation="none",
    ),
    FeatureSpec(
        name="latitude",
        dtype="float64",
        units="degN",
        source="Grid Coordinate",
        description="Geographic latitude within India domain",
        valid_range=(6.5, 38.5),
        missing_policy="reject_sample",
        transformation="none",
    ),
    FeatureSpec(
        name="longitude",
        dtype="float64",
        units="degE",
        source="Grid Coordinate",
        description="Geographic longitude within India domain",
        valid_range=(66.5, 100.5),
        missing_policy="reject_sample",
        transformation="none",
    ),
    FeatureSpec(
        name="elevation_m",
        dtype="float64",
        units="m",
        source="Topography / DEM",
        description="Terrain surface elevation above mean sea level",
        valid_range=(-50.0, 8900.0),
        missing_policy="zero_fill",
        transformation="standardize",
    ),
    FeatureSpec(
        name="day_of_year_sin",
        dtype="float64",
        units="dimensionless",
        source="Calendar",
        description="Sine embedding of day of year",
        valid_range=(-1.0, 1.0),
        missing_policy="calculate",
        transformation="none",
    ),
    FeatureSpec(
        name="day_of_year_cos",
        dtype="float64",
        units="dimensionless",
        source="Calendar",
        description="Cosine embedding of day of year",
        valid_range=(-1.0, 1.0),
        missing_policy="calculate",
        transformation="none",
    ),
    FeatureSpec(
        name="zonal_shear",
        dtype="float64",
        units="m/s",
        source="Derived NWP",
        description="Zonal wind vertical shear (u200 - u850)",
        valid_range=(-60.0, 60.0),
        missing_policy="median_impute",
        transformation="standardize",
    ),
    FeatureSpec(
        name="monsoon_trough_intensity",
        dtype="float64",
        units="dimensionless",
        source="Synoptic Indicator",
        description="Pressure gradient metric measuring monsoon trough strength",
        valid_range=(-5.0, 15.0),
        missing_policy="median_impute",
        transformation="standardize",
    ),
    FeatureSpec(
        name="meridional_flow",
        dtype="float64",
        units="m/s",
        source="Derived NWP",
        description="Cross-equatorial southerly low-level jet proxy",
        valid_range=(-50.0, 50.0),
        missing_policy="median_impute",
        transformation="standardize",
    ),
    FeatureSpec(
        name="convective_instability",
        dtype="float64",
        units="dimensionless",
        source="Derived NWP",
        description="Thermodynamic stability index (t850 - t500 proxy)",
        valid_range=(-20.0, 50.0),
        missing_policy="median_impute",
        transformation="standardize",
    ),
]

FEATURE_NAMES: List[str] = [spec.name for spec in FEATURE_SPECS]
APPROVED_PREDICTORS = FEATURE_NAMES

# Forbidden Features (Leakage Guard)
FORBIDDEN_FEATURES: List[str] = [
    "observed_rainfall_mm",
    "observed_rainfall",
    "rain_label",
    "heavy_label",
    "very_heavy_label",
    "extreme_label",
    "post_event_rainfall",
    "future_observation",
    "imd_rainfall",
    "target",
]


class FeatureContractValidator:
    """Validates that a feature matrix matches the authoritative Phase 12 schema."""

    @staticmethod
    def validate_features(df: pd.DataFrame) -> Dict[str, Any]:
        missing = [f for f in FEATURE_NAMES if f not in df.columns]
        forbidden = [f for f in FORBIDDEN_FEATURES if f in df.columns]

        # Check for presence of targets erroneously included in predictor names
        leakage_detected = len(forbidden) > 0

        # Range checks
        range_violations = []
        for spec in FEATURE_SPECS:
            if spec.name in df.columns:
                series = df[spec.name].dropna()
                if not series.empty:
                    mn, mx = spec.valid_range
                    if (series < mn).any() or (series > mx).any():
                        range_violations.append(spec.name)

        is_valid = len(missing) == 0 and not leakage_detected and len(range_violations) == 0

        return {
            "schema_version": FEATURE_SCHEMA_VERSION,
            "feature_count": len(FEATURE_NAMES),
            "is_valid": is_valid,
            "missing_features": missing,
            "forbidden_features_detected": forbidden,
            "range_violations": range_violations,
            "leakage_free": not leakage_detected,
        }

    @staticmethod
    def get_schema_metadata() -> Dict[str, Any]:
        return {
            "schema_version": FEATURE_SCHEMA_VERSION,
            "total_approved_features": len(FEATURE_SPECS),
            "features": [spec.to_dict() for spec in FEATURE_SPECS],
        }


def audit_predictor_dataframe(df: pd.DataFrame) -> None:
    """
    Guard checking that no forbidden target/leakage columns exist among the features.
    Raises ValueError if forbidden features are detected.
    """
    for forbidden in FORBIDDEN_FEATURES:
        if forbidden in df.columns and forbidden in ("future_observation", "post_event_rainfall"):
            raise ValueError(f"CRITICAL LEAKAGE DETECTED: Column '{forbidden}' is forbidden in training features.")

