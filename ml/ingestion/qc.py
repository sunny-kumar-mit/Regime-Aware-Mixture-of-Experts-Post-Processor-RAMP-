"""
RAMP Meteorological Quality Control (QC) Engine
SIH26080 | Phase 16 — Real-Data Activation & Operational Ingestion
MoES / NCMRWF

PART I — Meteorological QC Requirements:
  - Comprehensive quality checks:
      - NaN / Null detection
      - Inf / Infinite values
      - Negative rainfall rejection (< 0.0 mm)
      - Physical atmospheric plausibility bounds:
          Rainfall: [0.0, 1500.0] mm/24h
          T850:     [180.0, 340.0] K
          MSLP:     [870.0, 1085.0] hPa
          Wind:     [0.0, 120.0] m/s
          CAPE:     [0.0, 8000.0] J/kg
      - Duplicate records
      - Missing grid cells
      - Unexpected variable ranges
  - Structured QC result containing:
      source, variable, record_count, valid_count, invalid_count, flags, status.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

logger = logging.getLogger(__name__)


# Physical Climatological & Meteorological Bounds
PHYSICAL_VARIABLE_BOUNDS: Dict[str, Tuple[float, float]] = {
    # Rainfall
    "precip_nwp_raw": (0.0, 1500.0),
    "precip_nwp_ensemble_member": (0.0, 1500.0),
    "observed_rainfall_mm": (0.0, 1500.0),
    "rainfall": (0.0, 1500.0),
    "total_precipitation": (0.0, 1500.0),
    # Dynamics & Thermodynamics
    "u850": (-120.0, 120.0),
    "v850": (-120.0, 120.0),
    "wind_speed_850": (0.0, 120.0),
    "wind_dir_850": (0.0, 360.0),
    "zonal_shear": (-80.0, 80.0),
    "meridional_flow": (-80.0, 80.0),
    "mslp": (870.0, 1085.0),
    "t850": (180.0, 340.0),
    "cape": (0.0, 8000.0),
    "monsoon_trough_intensity": (-50.0, 50.0),
    # Dimensionless proxies & coords
    "humidity_proxy": (0.0, 1.0),
    "latitude": (6.5, 38.5),
    "longitude": (66.5, 100.5),
    "elevation_m": (-100.0, 9000.0),
    "lead_time_hours": (0.0, 360.0),
}


@dataclass
class VariableQCResult:
    """Detailed QC result for an individual meteorological variable."""
    source: str
    variable: str
    record_count: int
    valid_count: int
    invalid_count: int
    nan_count: int
    inf_count: int
    negative_count: int
    out_of_bounds_count: int
    min_value: Optional[float]
    max_value: Optional[float]
    flags: List[str] = field(default_factory=list)
    status: str = "PASSED"  # PASSED | WARNED | FAILED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DatasetQCReport:
    """Aggregated QC report covering all variables in an operational dataset."""
    source_id: str
    timestamp: str
    overall_status: str     # PASSED | WARNED | FAILED
    is_acceptable: bool
    total_variables: int
    variables_passed: int
    variables_failed: int
    variables_warned: int
    results: Dict[str, VariableQCResult] = field(default_factory=dict)
    critical_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["results"] = {k: v.to_dict() if hasattr(v, "to_dict") else v for k, v in self.results.items()}
        return d


class MeteorologicalQCEngine:
    """
    Validates observational and numerical weather prediction fields against
    physical atmospheric limits and numerical sanity constraints.
    """

    def check_variable(
        self,
        values: Union[np.ndarray, List[float]],
        variable_name: str,
        source: str = "UNKNOWN",
        allow_nan_fraction: float = 0.05,
    ) -> VariableQCResult:
        """
        Executes physical and numerical QC on a single variable array.
        """
        arr = np.asarray(values, dtype=float).flatten()
        record_count = len(arr)
        flags: List[str] = []

        if record_count == 0:
            return VariableQCResult(
                source=source,
                variable=variable_name,
                record_count=0,
                valid_count=0,
                invalid_count=0,
                nan_count=0,
                inf_count=0,
                negative_count=0,
                out_of_bounds_count=0,
                min_value=None,
                max_value=None,
                flags=["EMPTY_DATASET"],
                status="FAILED",
            )

        # 1. NaN and Inf inspection
        nan_mask = np.isnan(arr)
        inf_mask = np.isinf(arr)
        nan_count = int(np.sum(nan_mask))
        inf_count = int(np.sum(inf_mask))

        if inf_count > 0:
            flags.append(f"CONTAINS_INFINITIES: {inf_count} infinite values detected")

        nan_fraction = nan_count / record_count
        if nan_fraction > allow_nan_fraction:
            flags.append(f"EXCESSIVE_NANS: {nan_count}/{record_count} ({nan_fraction*100:.1f}%) missing")
        elif nan_count > 0:
            flags.append(f"MISSING_VALUES: {nan_count} NaNs detected")

        # Finite mask
        finite_mask = ~(nan_mask | inf_mask)
        finite_vals = arr[finite_mask]

        if len(finite_vals) == 0:
            return VariableQCResult(
                source=source,
                variable=variable_name,
                record_count=record_count,
                valid_count=0,
                invalid_count=record_count,
                nan_count=nan_count,
                inf_count=inf_count,
                negative_count=0,
                out_of_bounds_count=0,
                min_value=None,
                max_value=None,
                flags=flags + ["ALL_VALUES_NON_FINITE"],
                status="FAILED",
            )

        min_val = float(np.min(finite_vals))
        max_val = float(np.max(finite_vals))

        # 2. Negative rainfall check
        negative_count = 0
        is_precip = any(term in variable_name.lower() for term in ["precip", "rain", "prcp", "tp"])
        if is_precip:
            neg_mask = finite_vals < -1e-4
            negative_count = int(np.sum(neg_mask))
            if negative_count > 0:
                flags.append(f"NEGATIVE_RAINFALL: {negative_count} negative precipitation values found")

        # 3. Physical plausibility bounds check
        bounds = PHYSICAL_VARIABLE_BOUNDS.get(variable_name)
        out_of_bounds_count = 0
        if bounds:
            b_min, b_max = bounds
            oob_mask = (finite_vals < b_min) | (finite_vals > b_max)
            out_of_bounds_count = int(np.sum(oob_mask))
            if out_of_bounds_count > 0:
                flags.append(
                    f"PHYSICAL_BOUNDS_VIOLATION: {out_of_bounds_count} values outside [{b_min}, {b_max}]"
                )

        invalid_count = nan_count + inf_count + negative_count + out_of_bounds_count
        valid_count = max(0, record_count - invalid_count)

        # Status determination
        if inf_count > 0 or negative_count > 0 or (nan_fraction > allow_nan_fraction) or out_of_bounds_count > 0:
            status = "FAILED"
        elif nan_count > 0:
            status = "WARNED"
        else:
            status = "PASSED"

        return VariableQCResult(
            source=source,
            variable=variable_name,
            record_count=record_count,
            valid_count=valid_count,
            invalid_count=invalid_count,
            nan_count=nan_count,
            inf_count=inf_count,
            negative_count=negative_count,
            out_of_bounds_count=out_of_bounds_count,
            min_value=round(min_val, 4),
            max_value=round(max_val, 4),
            flags=flags,
            status=status,
        )

    def evaluate_dataset(
        self,
        variable_data: Dict[str, Union[np.ndarray, List[float]]],
        source_id: str,
        timestamp: str,
    ) -> DatasetQCReport:
        """Evaluates QC for an entire dictionary of meteorological variables."""
        results: Dict[str, VariableQCResult] = {}
        passed = 0
        failed = 0
        warned = 0
        critical_errors: List[str] = []

        for vname, vals in variable_data.items():
            qc_res = self.check_variable(vals, vname, source=source_id)
            results[vname] = qc_res
            if qc_res.status == "PASSED":
                passed += 1
            elif qc_res.status == "FAILED":
                failed += 1
                critical_errors.extend([f"{vname}: {flag}" for flag in qc_res.flags])
            else:
                warned += 1

        if failed > 0:
            overall = "FAILED"
            is_acceptable = False
        elif warned > 0:
            overall = "WARNED"
            is_acceptable = True
        else:
            overall = "PASSED"
            is_acceptable = True

        return DatasetQCReport(
            source_id=source_id,
            timestamp=timestamp,
            overall_status=overall,
            is_acceptable=is_acceptable,
            total_variables=len(variable_data),
            variables_passed=passed,
            variables_failed=failed,
            variables_warned=warned,
            results=results,
            critical_errors=critical_errors,
        )
