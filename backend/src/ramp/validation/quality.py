"""
RAMP Data Quality Engine
SIH26080 | Validation, Quality Flags, Outlier Classification

SCIENTIFIC RULES:
  1. Extreme rainfall is NOT automatically removed.
     300 mm/24h may be valid in the Indian monsoon context.
     VALID_EXTREME flag marks these — they are kept.
  2. Negative rainfall IS invalid — flagged as INVALID.
  3. Missing values (NaN) are flagged as MISSING, not INVALID.
  4. SUSPICIOUS covers plausible-but-unexpected values.
  5. No silent data deletion — every flag is traceable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from ramp.ingestion.base import (
    DataMode,
    QualityFlag,
    ValidationReport,
)

logger = logging.getLogger("ramp.validation.quality")


# =============================================================================
# Physical bounds per variable (scientifically motivated)
# These define INVALID ranges and VALID_EXTREME thresholds.
# =============================================================================

@dataclass
class VariableBounds:
    variable: str
    hard_min: Optional[float] = None      # Below this → INVALID
    hard_max: Optional[float] = None      # Above this → INVALID
    extreme_min: Optional[float] = None   # Below this → VALID_EXTREME (but keep)
    extreme_max: Optional[float] = None   # Above this → VALID_EXTREME (but keep)
    suspicious_min: Optional[float] = None
    suspicious_max: Optional[float] = None


VARIABLE_BOUNDS: Dict[str, VariableBounds] = {
    # Rainfall (mm/24h)
    "rainfall_mm": VariableBounds(
        variable="rainfall_mm",
        hard_min=0.0,          # Negative rainfall is physically impossible
        hard_max=None,         # No upper hard limit — 300+ mm possible in monsoon
        extreme_max=300.0,     # >300 mm/24h flagged VALID_EXTREME (keep, note)
        suspicious_min=-0.001, # Float precision artefact
        suspicious_max=2000.0, # Truly exceptional if > 2000 mm
    ),
    "precip_nwp_raw": VariableBounds(
        variable="precip_nwp_raw",
        hard_min=-0.1,         # Small negative NWP artefact threshold
        hard_max=None,
        extreme_max=300.0,
    ),
    "observed_rainfall_mm": VariableBounds(
        variable="observed_rainfall_mm",
        hard_min=0.0,
        hard_max=None,
        extreme_max=300.0,
        suspicious_max=2000.0,
    ),
    # Temperature (°C)
    "t850": VariableBounds(
        variable="t850",
        hard_min=-80.0,
        hard_max=60.0,
        extreme_min=-40.0,
        extreme_max=50.0,
    ),
    "t500": VariableBounds(
        variable="t500",
        hard_min=-80.0,
        hard_max=40.0,
    ),
    # Wind (m/s)
    "u850": VariableBounds(variable="u850", hard_min=-100.0, hard_max=100.0),
    "v850": VariableBounds(variable="v850", hard_min=-100.0, hard_max=100.0),
    "u200": VariableBounds(variable="u200", hard_min=-150.0, hard_max=150.0),
    "v200": VariableBounds(variable="v200", hard_min=-150.0, hard_max=150.0),
    # Pressure (hPa)
    "mslp": VariableBounds(variable="mslp", hard_min=850.0, hard_max=1100.0),
    # Humidity
    "q850": VariableBounds(variable="q850", hard_min=0.0, hard_max=30.0),
    "q700": VariableBounds(variable="q700", hard_min=0.0, hard_max=30.0),
    # CAPE (J/kg)
    "cape": VariableBounds(variable="cape", hard_min=0.0, hard_max=15000.0),
    "cin": VariableBounds(variable="cin", hard_min=-5000.0, hard_max=0.0),
}


# =============================================================================
# Core Validation Functions
# =============================================================================

def flag_array(
    data: np.ndarray,
    bounds: Optional[VariableBounds] = None,
) -> np.ndarray:
    """
    Flag every element of a data array with a QualityFlag.

    Args:
        data:   Input array (may contain NaN).
        bounds: Optional VariableBounds for physical range checks.

    Returns:
        Array of QualityFlag strings, same shape as data.
    """
    flags = np.full(data.shape, QualityFlag.VALID.value, dtype=object)

    # MISSING — NaN or inf
    nan_mask = np.isnan(data)
    inf_mask = np.isinf(data)
    flags[nan_mask] = QualityFlag.MISSING.value
    flags[inf_mask] = QualityFlag.INVALID.value

    if bounds is None:
        return flags

    valid_mask = ~nan_mask & ~inf_mask

    # INVALID — physically impossible
    if bounds.hard_min is not None:
        too_low = valid_mask & (data < bounds.hard_min)
        flags[too_low] = QualityFlag.INVALID.value

    if bounds.hard_max is not None:
        too_high = valid_mask & (data > bounds.hard_max)
        flags[too_high] = QualityFlag.INVALID.value

    # Re-evaluate valid mask after hard bounds
    current_valid = valid_mask & (flags == QualityFlag.VALID.value)

    # SUSPICIOUS — outside expected but not physically impossible
    if bounds.suspicious_min is not None:
        suspicious = current_valid & (data < bounds.suspicious_min)
        flags[suspicious] = QualityFlag.SUSPICIOUS.value

    if bounds.suspicious_max is not None:
        suspicious = current_valid & (data > bounds.suspicious_max)
        flags[suspicious] = QualityFlag.SUSPICIOUS.value

    # VALID_EXTREME — kept but highlighted (e.g. extreme monsoon rainfall)
    # Note: Does not override INVALID or SUSPICIOUS
    current_valid2 = valid_mask & (flags == QualityFlag.VALID.value)

    if bounds.extreme_min is not None:
        extreme = current_valid2 & (data < bounds.extreme_min)
        flags[extreme] = QualityFlag.VALID_EXTREME.value

    if bounds.extreme_max is not None:
        extreme = current_valid2 & (data > bounds.extreme_max)
        flags[extreme] = QualityFlag.VALID_EXTREME.value

    return flags


def compute_flag_counts(flags: np.ndarray) -> Dict[str, int]:
    """Count occurrences of each QualityFlag in a flag array."""
    unique, counts = np.unique(flags, return_counts=True)
    return dict(zip(unique.tolist(), counts.tolist()))


def validate_array(
    data: np.ndarray,
    variable_name: str,
    report: ValidationReport,
) -> np.ndarray:
    """
    Validate a 2-D or N-D data array for a named variable.
    Updates report in-place. Returns flag array.

    Critical: VALID_EXTREME values are NOT removed. They are flagged and counted.
    """
    bounds = VARIABLE_BOUNDS.get(variable_name)
    flags = flag_array(data, bounds)
    counts = compute_flag_counts(flags)
    total = data.size

    n_missing = counts.get(QualityFlag.MISSING.value, 0)
    n_invalid = counts.get(QualityFlag.INVALID.value, 0)
    n_suspicious = counts.get(QualityFlag.SUSPICIOUS.value, 0)
    n_extreme = counts.get(QualityFlag.VALID_EXTREME.value, 0)

    report.missing_fraction = (report.missing_fraction * total + n_missing) / total
    report.invalid_count += n_invalid
    report.suspicious_count += n_suspicious
    report.extreme_value_count += n_extreme

    if n_invalid > 0:
        report.add_warning(
            f"Variable '{variable_name}' has {n_invalid} physically invalid values "
            f"({100*n_invalid/total:.2f}%). These are flagged INVALID, not removed."
        )

    if n_extreme > 0:
        arr_valid = data[flags == QualityFlag.VALID_EXTREME.value]
        report.add_warning(
            f"Variable '{variable_name}' has {n_extreme} VALID_EXTREME values "
            f"(max={np.nanmax(arr_valid):.2f}). Kept — extreme rainfall is scientifically important."
        )

    logger.debug(
        "%s flags: VALID=%d, MISSING=%d, INVALID=%d, SUSPICIOUS=%d, EXTREME=%d",
        variable_name,
        counts.get(QualityFlag.VALID.value, 0),
        n_missing, n_invalid, n_suspicious, n_extreme,
    )
    return flags


def validate_coordinate_range(
    values: np.ndarray,
    name: str,
    expected_min: float,
    expected_max: float,
    report: ValidationReport,
) -> bool:
    """Validate that coordinate values fall within expected range."""
    actual_min = float(np.nanmin(values))
    actual_max = float(np.nanmax(values))
    ok = True

    if actual_min < expected_min - 0.01:
        report.add_error(
            f"{name} minimum {actual_min:.4f} is below expected {expected_min}"
        )
        ok = False
    if actual_max > expected_max + 0.01:
        report.add_error(
            f"{name} maximum {actual_max:.4f} exceeds expected {expected_max}"
        )
        ok = False
    return ok


def validate_grid_spacing(
    coords: np.ndarray,
    expected_spacing: float,
    tolerance: float = 0.01,
    name: str = "coordinate",
    report: Optional[ValidationReport] = None,
) -> bool:
    """Check that coordinate spacing is approximately uniform."""
    if len(coords) < 2:
        return True
    diffs = np.diff(np.sort(coords))
    max_dev = float(np.max(np.abs(diffs - expected_spacing)))
    ok = max_dev <= tolerance
    if not ok and report is not None:
        report.add_warning(
            f"{name} spacing deviates from expected {expected_spacing}° "
            f"by up to {max_dev:.4f}°."
        )
    return ok


def compute_summary_statistics(
    data: np.ndarray,
    variable_name: str = "",
) -> Dict[str, float]:
    """Compute descriptive statistics — for rainfall includes percentile tail."""
    flat = data[~np.isnan(data)].ravel()
    if len(flat) == 0:
        return {"count": 0, "note": "all_missing"}

    stats: Dict[str, float] = {
        "count": len(flat),
        "min": float(np.min(flat)),
        "max": float(np.max(flat)),
        "mean": float(np.mean(flat)),
        "median": float(np.median(flat)),
        "std": float(np.std(flat)),
    }

    # For rainfall — compute percentile tail (scientifically important)
    if "rainfall" in variable_name or "precip" in variable_name:
        for pct in [50, 90, 95, 99]:
            stats[f"p{pct}"] = float(np.percentile(flat, pct))

    return stats
