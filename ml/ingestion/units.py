"""
RAMP Centralized Unit Normalization & Validation Layer
SIH26080 | Phase 16 — Real-Data Activation & Operational Ingestion
MoES / NCMRWF

PART H — Unit Normalization Requirements:
  - Rainfall converted to canonical RAMP unit: mm (or mm/day).
  - Meteorological variables retain documented canonical units.
  - Never silently convert an unknown unit.
  - Unknown unit triggers explicit UNIT_VALIDATION_FAILED error.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

logger = logging.getLogger(__name__)


class UnitValidationError(ValueError):
    """Raised when an unknown or unconvertible unit is encountered."""
    pass


# Canonical Unit Definitions for RAMP
CANONICAL_VARIABLE_UNITS: Dict[str, str] = {
    # Rainfall
    "precip_nwp_raw": "mm",
    "precip_nwp_ensemble_member": "mm",
    "observed_rainfall_mm": "mm",
    "rainfall": "mm",
    "total_precipitation": "mm",
    # Wind & Dynamics
    "u850": "m/s",
    "v850": "m/s",
    "wind_speed_850": "m/s",
    "wind_dir_850": "deg",
    "zonal_shear": "m/s",
    "meridional_flow": "m/s",
    # Thermodynamics
    "mslp": "hPa",
    "t850": "K",
    "cape": "J/kg",
    "monsoon_trough_intensity": "hPa",
    # Spatial & Temporal
    "lead_time_hours": "hours",
    "latitude": "deg_N",
    "longitude": "deg_E",
    "elevation_m": "m",
    "day_of_year_sin": "dimensionless",
    "day_of_year_cos": "dimensionless",
    "humidity_proxy": "dimensionless",
}


# Supported rainfall unit conversion factors to canonical 'mm'
RAINFALL_CONVERSION_FACTORS: Dict[str, float] = {
    "mm": 1.0,
    "mm/day": 1.0,
    "mm/24h": 1.0,
    "mm 24h-1": 1.0,
    "millimeter": 1.0,
    "millimeters": 1.0,
    "m": 1000.0,
    "meter": 1000.0,
    "meters": 1000.0,
    "m/day": 1000.0,
    "kg m-2": 1.0,       # 1 kg/m^2 of liquid water == 1 mm
    "kg/m^2": 1.0,
    "kg m^-2": 1.0,
    "kg m-2 s-1": 86400.0,  # kg/(m^2*s) flux rate over 24h (86,400 s)
    "kg/(m^2*s)": 86400.0,
    "kg m^-2 s^-1": 86400.0,
}

# Pressure conversion factors to 'hPa'
PRESSURE_CONVERSION_FACTORS: Dict[str, float] = {
    "hpa": 1.0,
    "mb": 1.0,
    "mbar": 1.0,
    "hectopascal": 1.0,
    "pa": 0.01,
    "pascal": 0.01,
}

# Wind conversion factors to 'm/s'
WIND_CONVERSION_FACTORS: Dict[str, float] = {
    "m/s": 1.0,
    "m s-1": 1.0,
    "m s^-1": 1.0,
    "mps": 1.0,
    "kt": 0.514444,
    "knot": 0.514444,
    "knots": 0.514444,
    "km/h": 0.277778,
}


class UnitNormalizer:
    """
    Centralized meteorological unit validator and normalization engine.
    Guarantees no unknown unit is silently converted.
    """

    @classmethod
    def normalize_rainfall(
        cls,
        values: Union[np.ndarray, List[float], float],
        source_unit: str,
    ) -> np.ndarray:
        """
        Converts input rainfall array to canonical 'mm'.
        Raises UnitValidationError if source_unit is unrecognized.
        """
        clean_unit = source_unit.strip().lower()
        if clean_unit not in RAINFALL_CONVERSION_FACTORS:
            raise UnitValidationError(
                f"UNIT_VALIDATION_FAILED: Unsupported rainfall unit '{source_unit}'. "
                f"Supported units are: {list(RAINFALL_CONVERSION_FACTORS.keys())}"
            )

        factor = RAINFALL_CONVERSION_FACTORS[clean_unit]
        arr = np.asarray(values, dtype=float)
        return arr * factor

    @classmethod
    def normalize_pressure(
        cls,
        values: Union[np.ndarray, List[float], float],
        source_unit: str,
    ) -> np.ndarray:
        """
        Converts atmospheric pressure to canonical 'hPa'.
        Raises UnitValidationError if source_unit is unrecognized.
        """
        clean_unit = source_unit.strip().lower()
        if clean_unit not in PRESSURE_CONVERSION_FACTORS:
            raise UnitValidationError(
                f"UNIT_VALIDATION_FAILED: Unsupported pressure unit '{source_unit}'. "
                f"Supported units are: {list(PRESSURE_CONVERSION_FACTORS.keys())}"
            )
        factor = PRESSURE_CONVERSION_FACTORS[clean_unit]
        arr = np.asarray(values, dtype=float)
        return arr * factor

    @classmethod
    def normalize_temperature_kelvin(
        cls,
        values: Union[np.ndarray, List[float], float],
        source_unit: str,
    ) -> np.ndarray:
        """
        Converts temperature to canonical 'K'.
        Raises UnitValidationError if source_unit is unrecognized.
        """
        clean_unit = source_unit.strip().lower()
        arr = np.asarray(values, dtype=float)
        if clean_unit in {"k", "kelvin", "degk"}:
            return arr
        elif clean_unit in {"c", "degc", "celsius", "degree_celsius"}:
            return arr + 273.15
        else:
            raise UnitValidationError(
                f"UNIT_VALIDATION_FAILED: Unsupported temperature unit '{source_unit}'."
            )

    @classmethod
    def normalize_wind_speed(
        cls,
        values: Union[np.ndarray, List[float], float],
        source_unit: str,
    ) -> np.ndarray:
        """
        Converts wind speed to canonical 'm/s'.
        Raises UnitValidationError if source_unit is unrecognized.
        """
        clean_unit = source_unit.strip().lower()
        if clean_unit not in WIND_CONVERSION_FACTORS:
            raise UnitValidationError(
                f"UNIT_VALIDATION_FAILED: Unsupported wind unit '{source_unit}'."
            )
        factor = WIND_CONVERSION_FACTORS[clean_unit]
        arr = np.asarray(values, dtype=float)
        return arr * factor

    @classmethod
    def validate_variable_unit(cls, variable_name: str, source_unit: str) -> Tuple[bool, Optional[str]]:
        """
        Validates whether a source unit is legally convertible to the canonical unit.
        Returns: (is_valid, canonical_unit_or_error)
        """
        v_lower = variable_name.lower()
        u_lower = source_unit.strip().lower()

        if any(term in v_lower for term in ["precip", "rain", "prcp", "tp"]):
            if u_lower in RAINFALL_CONVERSION_FACTORS:
                return True, "mm"
            return False, f"UNIT_VALIDATION_FAILED: Unknown rainfall unit '{source_unit}'"

        if "mslp" in v_lower or "pressure" in v_lower:
            if u_lower in PRESSURE_CONVERSION_FACTORS:
                return True, "hPa"
            return False, f"UNIT_VALIDATION_FAILED: Unknown pressure unit '{source_unit}'"

        if "wind" in v_lower or v_lower.startswith("u") or v_lower.startswith("v"):
            if u_lower in WIND_CONVERSION_FACTORS:
                return True, "m/s"
            return False, f"UNIT_VALIDATION_FAILED: Unknown wind unit '{source_unit}'"

        if "t850" in v_lower or "temp" in v_lower:
            if u_lower in {"k", "kelvin", "degk", "c", "degc", "degree_celsius"}:
                return True, "K"
            return False, f"UNIT_VALIDATION_FAILED: Unknown temperature unit '{source_unit}'"

        # Check canonical table fallback
        canonical = CANONICAL_VARIABLE_UNITS.get(variable_name)
        if canonical:
            if u_lower == canonical.lower() or u_lower in {"dimensionless", "1", "", "deg", "hours", "m"}:
                return True, canonical
            return False, f"UNIT_VALIDATION_FAILED: Unit '{source_unit}' does not match canonical '{canonical}'"

        return False, f"UNIT_VALIDATION_FAILED: Variable '{variable_name}' not recognized in canonical unit registry"
