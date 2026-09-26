"""
RAMP Unit Normalization Layer
SIH26080 | Meteorological Unit Conversion

Rules:
  - Never blindly convert without reading source metadata.
  - Source units and normalized units are always recorded in DataProvenance.
  - Raises UnitConversionError if conversion path is unknown.
  - Extreme values must NOT be clipped during conversion.

Canonical normalized units:
  rainfall     → mm              (mm per accumulation period)
  pressure     → hPa             (MSLP, etc.)
  temperature  → °C              (degrees Celsius)
  wind speed   → m/s
  humidity     → g/kg or %       (specific: g/kg; relative: %)
  geopotential → m² s⁻²         (raw), or m (geopotential height via /g)
  CAPE         → J/kg
  precip water → kg/m²           (precipitable water column)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np

from ramp.ingestion.base import UnitConversionError

logger = logging.getLogger("ramp.harmonisation.units")

# Gravitational acceleration for geopotential conversion
G_STD = 9.80665  # m/s²


# =============================================================================
# Conversion Registry
# Format: ("source_unit_canonical", "target_unit") -> conversion_function(array)
# =============================================================================

def _noop(x: Any) -> Any:
    return x


def _kelvin_to_celsius(x: Any) -> Any:
    return np.asarray(x, dtype=float) - 273.15


def _celsius_to_celsius(x: Any) -> Any:
    return np.asarray(x, dtype=float)


def _pa_to_hpa(x: Any) -> Any:
    return np.asarray(x, dtype=float) / 100.0


def _hpa_to_hpa(x: Any) -> Any:
    return np.asarray(x, dtype=float)


def _knots_to_ms(x: Any) -> Any:
    return np.asarray(x, dtype=float) * 0.514444


def _ms_to_ms(x: Any) -> Any:
    return np.asarray(x, dtype=float)


def _kgm2_to_mm(x: Any) -> Any:
    """kg/m² ≡ mm for liquid water (density = 1000 kg/m³, thickness = kg/m² / 1000 kg/m³ * 1000 mm/m)."""
    return np.asarray(x, dtype=float)  # numerically equal


def _mm_to_mm(x: Any) -> Any:
    return np.asarray(x, dtype=float)


def _m_to_mm(x: Any) -> Any:
    return np.asarray(x, dtype=float) * 1000.0


def _gph_to_m(x: Any) -> Any:
    """Geopotential (m²/s²) → geopotential height (m)."""
    return np.asarray(x, dtype=float) / G_STD


def _m2s2_to_m2s2(x: Any) -> Any:
    return np.asarray(x, dtype=float)


# Canonical aliases — map various string representations to a canonical token
_UNIT_ALIASES: Dict[str, str] = {
    # Temperature
    "k": "K",
    "kelvin": "K",
    "°c": "degC",
    "°C": "degC",
    "degc": "degC",
    "celsius": "degC",
    "c": "degC",
    # Pressure
    "pa": "Pa",
    "pascal": "Pa",
    "hpa": "hPa",
    "mb": "hPa",
    "millibar": "hPa",
    "mbar": "hPa",
    # Wind
    "m s-1": "m/s",
    "m/s": "m/s",
    "ms-1": "m/s",
    "meter/second": "m/s",
    "knots": "knots",
    "kt": "knots",
    "kts": "knots",
    # Rainfall / moisture
    "mm": "mm",
    "millimeter": "mm",
    "millimetre": "mm",
    "kg m-2": "kg/m²",
    "kg/m2": "kg/m²",
    "kg/m²": "kg/m²",
    "kgm-2": "kg/m²",
    "m": "m_water",   # metres of water — used in ERA5 for precip
    # CAPE
    "j/kg": "J/kg",
    "j kg-1": "J/kg",
    # Geopotential
    "m2 s-2": "m²/s²",
    "m2/s2": "m²/s²",
    "m²/s²": "m²/s²",
}


def _canonical(unit: str) -> str:
    """Normalize a unit string to a canonical token."""
    return _UNIT_ALIASES.get(unit.strip(), unit.strip())


# Conversion table: (canonical_source, canonical_target) → function
_CONVERSIONS: Dict[Tuple[str, str], Any] = {
    # Temperature
    ("K", "degC"): _kelvin_to_celsius,
    ("degC", "degC"): _celsius_to_celsius,
    # Pressure
    ("Pa", "hPa"): _pa_to_hpa,
    ("hPa", "hPa"): _hpa_to_hpa,
    # Wind
    ("m/s", "m/s"): _ms_to_ms,
    ("knots", "m/s"): _knots_to_ms,
    # Rainfall / water
    ("mm", "mm"): _mm_to_mm,
    ("kg/m²", "mm"): _kgm2_to_mm,
    ("m_water", "mm"): _m_to_mm,
    # CAPE / CIN
    ("J/kg", "J/kg"): _noop,
    # Geopotential
    ("m²/s²", "m²/s²"): _m2s2_to_m2s2,
    ("m²/s²", "m"): _gph_to_m,       # Convert to geopotential height
}


# Variable-to-target-unit mapping for RAMP canonical space
CANONICAL_TARGET_UNITS: Dict[str, str] = {
    "rainfall_mm": "mm",
    "precip_nwp_raw": "mm",
    "precip_conv_nwp": "mm",
    "precip_strat_nwp": "mm",
    "u850": "m/s",
    "v850": "m/s",
    "u200": "m/s",
    "v200": "m/s",
    "w850": "m/s",
    "t850": "degC",
    "t500": "degC",
    "q850": "g/kg",
    "q700": "g/kg",
    "pw": "kg/m²",    # Precipitable water stays as kg/m² (≡ mm numerically)
    "cape": "J/kg",
    "cin": "J/kg",
    "mslp": "hPa",
    "z500": "m",       # Geopotential height
    "observed_rainfall_mm": "mm",
}


def convert_units(
    data: Any,
    source_unit: str,
    variable_name: str,
    target_unit: Optional[str] = None,
) -> Tuple[Any, str, str]:
    """
    Convert meteorological data from source_unit to the RAMP canonical unit.

    Args:
        data:          array-like values (numpy or xarray DataArray)
        source_unit:   unit string as read from source file metadata
        variable_name: RAMP canonical variable name (used to look up target)
        target_unit:   explicit override target unit (optional)

    Returns:
        Tuple of (converted_data, source_unit_canonical, target_unit_used)

    Raises:
        UnitConversionError if no conversion path is known.
    """
    src_canonical = _canonical(source_unit)

    if target_unit is None:
        target_unit = CANONICAL_TARGET_UNITS.get(variable_name, src_canonical)

    tgt_canonical = _canonical(target_unit)

    key = (src_canonical, tgt_canonical)
    fn = _CONVERSIONS.get(key)

    if fn is None:
        # Try identity conversion for matching canonicals
        if src_canonical == tgt_canonical:
            logger.debug(
                "No explicit conversion for (%s→%s), treating as identity.",
                src_canonical, tgt_canonical
            )
            return data, src_canonical, tgt_canonical

        raise UnitConversionError(
            f"Unknown unit conversion for variable '{variable_name}': "
            f"'{source_unit}' ({src_canonical}) → '{target_unit}' ({tgt_canonical}). "
            "Add an explicit conversion function to ramp.harmonisation.units."
        )

    logger.debug(
        "Converting %s: %s → %s", variable_name, src_canonical, tgt_canonical
    )
    converted = fn(data)
    return converted, src_canonical, tgt_canonical


def get_target_unit(variable_name: str) -> Optional[str]:
    """Return the canonical target unit for a RAMP variable name."""
    return CANONICAL_TARGET_UNITS.get(variable_name)
