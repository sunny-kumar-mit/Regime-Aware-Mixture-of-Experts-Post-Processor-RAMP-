"""
Phase 8 Explicit Unit Normalization
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Implements mathematically rigorous, documented unit conversions for meteorological datasets.
Rules:
- Do NOT blindly convert values.
- Every conversion is logged with scientific justification.
- Rate-to-accumulation conversions REQUIRE an explicit, verified time interval.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class UnitConversionLogEntry:
    variable: str
    source_unit: str
    target_unit: str
    conversion_factor: float
    records_converted: int
    rationale: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class UnitConversionError(ValueError):
    """Raised when an unverified or scientifically ambiguous unit conversion is requested."""
    pass


class UnitNormalizer:
    """
    Standardizes units across diverse NWP centers (ECMWF, NCMRWF, IMD, NCEP)
    into canonical SI / meteorological units.
    """

    def __init__(self) -> None:
        self.conversion_history: List[UnitConversionLogEntry] = []

    def log_conversion(
        self,
        variable: str,
        source_unit: str,
        target_unit: str,
        conversion_factor: float,
        records_converted: int,
        rationale: str,
    ) -> None:
        entry = UnitConversionLogEntry(
            variable=variable,
            source_unit=source_unit,
            target_unit=target_unit,
            conversion_factor=conversion_factor,
            records_converted=records_converted,
            rationale=rationale,
        )
        self.conversion_history.append(entry)
        logger.info(
            f"[UNIT CONVERSION] {variable}: {source_unit} -> {target_unit} "
            f"(factor={conversion_factor}) for {records_converted} records. Rationale: {rationale}"
        )

    def normalize_precipitation_to_mm(
        self,
        values: np.ndarray | pd.Series,
        source_unit: str,
        interval_seconds: Optional[float] = None,
        variable_name: str = "precipitation",
    ) -> np.ndarray:
        """
        Converts precipitation to accumulated millimeters (mm).

        Supported source units:
        - 'mm', 'millimeter', 'millimeters', 'kg m-2', 'kg/m^2', 'kg m**-2':
          $1 kg/m^2 = 1 mm$ of liquid water assuming standard water density $\\rho_w = 1000 kg/m^3$.
        - 'm', 'meter', 'meters':
          Multiplied by 1000.0.
        - 'kg m-2 s-1', 'kg/m^2/s', 'mm/s':
          Requires interval_seconds. $accumulation = rate \\times interval\\_seconds$.
        - 'm/s', 'm s-1':
          Requires interval_seconds. $accumulation = rate \\times interval\\_seconds \\times 1000.0$.
        """
        arr = np.asarray(values, dtype=float).copy()
        clean_unit = source_unit.strip().lower()

        if clean_unit in ["mm", "millimeter", "millimeters"]:
            # Identity
            return arr

        elif clean_unit in ["kg m-2", "kg/m^2", "kg m**-2", "kg/m2"]:
            # Documented physical identity: 1 kg water / 1 m^2 area = 0.001 m depth = 1 mm depth
            self.log_conversion(
                variable=variable_name,
                source_unit=source_unit,
                target_unit="mm",
                conversion_factor=1.0,
                records_converted=int(len(arr)),
                rationale="Equivalent for liquid water: 1 kg/m^2 corresponds to 1.0 mm accumulation at standard density (1000 kg/m^3).",
            )
            return arr

        elif clean_unit in ["m", "meter", "meters"]:
            converted = arr * 1000.0
            self.log_conversion(
                variable=variable_name,
                source_unit=source_unit,
                target_unit="mm",
                conversion_factor=1000.0,
                records_converted=int(len(arr)),
                rationale="Meters to millimeters scale factor (1 m = 1000 mm). Typical for ECMWF/NCUM total precipitation.",
            )
            return converted

        elif clean_unit in ["kg m-2 s-1", "kg/m^2/s", "mm/s", "mm s-1"]:
            if interval_seconds is None or interval_seconds <= 0:
                raise UnitConversionError(
                    f"Cannot convert precipitation rate '{source_unit}' to accumulation without a positive interval_seconds."
                )
            converted = arr * interval_seconds
            self.log_conversion(
                variable=variable_name,
                source_unit=source_unit,
                target_unit="mm",
                conversion_factor=interval_seconds,
                records_converted=int(len(arr)),
                rationale=f"Precipitation flux integrated over verified accumulation duration of {interval_seconds} seconds ({interval_seconds/3600:.1f} hours).",
            )
            return converted

        elif clean_unit in ["m/s", "m s-1"]:
            if interval_seconds is None or interval_seconds <= 0:
                raise UnitConversionError(
                    f"Cannot convert precipitation rate '{source_unit}' to accumulation without a positive interval_seconds."
                )
            converted = arr * interval_seconds * 1000.0
            self.log_conversion(
                variable=variable_name,
                source_unit=source_unit,
                target_unit="mm",
                conversion_factor=interval_seconds * 1000.0,
                records_converted=int(len(arr)),
                rationale=f"Precipitation velocity in m/s integrated over {interval_seconds} seconds and scaled by 1000 mm/m.",
            )
            return converted

        else:
            raise UnitConversionError(f"Unsupported precipitation source unit: '{source_unit}'. Explicit mapping required.")

    def normalize_pressure_to_pa(
        self,
        values: np.ndarray | pd.Series,
        source_unit: str,
        variable_name: str = "mslp",
    ) -> np.ndarray:
        """Standardizes atmospheric pressure to Pascals (Pa)."""
        arr = np.asarray(values, dtype=float).copy()
        clean_unit = source_unit.strip().lower()

        if clean_unit in ["pa", "pascal", "pascals"]:
            return arr
        elif clean_unit in ["hpa", "hectopascal", "mbar", "millibar"]:
            converted = arr * 100.0
            self.log_conversion(
                variable=variable_name,
                source_unit=source_unit,
                target_unit="Pa",
                conversion_factor=100.0,
                records_converted=int(len(arr)),
                rationale="1 hPa / mbar = 100 Pa.",
            )
            return converted
        else:
            raise UnitConversionError(f"Unsupported pressure unit '{source_unit}'. Expected Pa or hPa/mbar.")

    def normalize_temperature_to_kelvin(
        self,
        values: np.ndarray | pd.Series,
        source_unit: str,
        variable_name: str = "temp",
    ) -> np.ndarray:
        """Standardizes temperature to Kelvin (K)."""
        arr = np.asarray(values, dtype=float).copy()
        clean_unit = source_unit.strip().lower()

        if clean_unit in ["k", "kelvin"]:
            return arr
        elif clean_unit in ["c", "celsius", "degc", "deg c"]:
            converted = arr + 273.15
            self.log_conversion(
                variable=variable_name,
                source_unit=source_unit,
                target_unit="K",
                conversion_factor=1.0,
                records_converted=int(len(arr)),
                rationale="Celsius to Kelvin offset (+273.15 K).",
            )
            return converted
        else:
            raise UnitConversionError(f"Unsupported temperature unit '{source_unit}'. Expected K or Celsius.")

    def get_audit_summary(self) -> List[Dict[str, Any]]:
        """Returns the complete audit log of all conversions executed."""
        return [
            {
                "variable": e.variable,
                "source_unit": e.source_unit,
                "target_unit": e.target_unit,
                "conversion_factor": e.conversion_factor,
                "records_converted": e.records_converted,
                "rationale": e.rationale,
                "timestamp": e.timestamp,
            }
            for e in self.conversion_history
        ]
