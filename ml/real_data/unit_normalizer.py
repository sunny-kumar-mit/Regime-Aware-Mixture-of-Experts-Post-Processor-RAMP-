"""
Unit Normalization & Auditing Engine for RAMP Real Data
SIH26080 | MoES / NCMRWF | Phase 19

Performs scientifically validated meteorological unit conversions
(Kelvin -> Celsius, Pa -> hPa, kg m^-2 s^-1 -> mm, etc.)
and appends immutable transformation records to:
data/manifests/transformation_manifest.json
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

TRANSFORMATION_MANIFEST_PATH = Path("data/manifests/transformation_manifest.json")


class UnitNormalizer:
    """
    Applies explicit, scientifically valid conversions to meteorological data.
    Records every conversion in data/manifests/transformation_manifest.json.
    """

    SUPPORTED_CONVERSIONS = {
        ("k", "degc"): ("x - 273.15", lambda x: x - 273.15, "Thermodynamic absolute temperature to Celsius"),
        ("kelvin", "degc"): ("x - 273.15", lambda x: x - 273.15, "Kelvin to Celsius"),
        ("pa", "hpa"): ("x / 100.0", lambda x: x / 100.0, "Pascals to hectopascals (millibars)"),
        ("pascal", "hpa"): ("x / 100.0", lambda x: x / 100.0, "Pascals to hectopascals"),
        ("m/s", "km/h"): ("x * 3.6", lambda x: x * 3.6, "Meters per second to kilometers per hour"),
        ("kg m-2 s-1", "mm"): ("x * 86400.0", lambda x: x * 86400.0, "Precipitation flux rate to 24h accumulation mm"),
        ("kg/m^2/s", "mm"): ("x * 86400.0", lambda x: x * 86400.0, "Precipitation rate to 24h accumulation mm"),
        ("fraction", "%"): ("x * 100.0", lambda x: x * 100.0, "Dimensionless fraction to percentage"),
    }

    def __init__(self, manifest_path: Path = TRANSFORMATION_MANIFEST_PATH):
        self.manifest_path = manifest_path
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)

    def convert_array(
        self,
        values: np.ndarray,
        source_unit: str,
        target_unit: str,
        feature_name: str = "unknown",
        file_id: str = "unknown",
    ) -> Tuple[np.ndarray, bool, Optional[str]]:
        """
        Converts a numpy array from source_unit to target_unit.
        Returns: (converted_array, success, error_message)
        """
        s_clean = source_unit.strip().lower()
        t_clean = target_unit.strip().lower()

        if s_clean == t_clean:
            return values, True, None

        key = (s_clean, t_clean)
        if key not in self.SUPPORTED_CONVERSIONS:
            return values, False, f"Unsupported unit conversion: '{source_unit}' -> '{target_unit}'"

        formula_str, func, reason = self.SUPPORTED_CONVERSIONS[key]
        converted = func(values)

        # Record in manifest
        self._record_transformation(
            feature_name=feature_name,
            file_id=file_id,
            source_unit=source_unit,
            target_unit=target_unit,
            formula=formula_str,
            reason=reason,
        )

        return converted, True, None

    def _record_transformation(
        self,
        feature_name: str,
        file_id: str,
        source_unit: str,
        target_unit: str,
        formula: str,
        reason: str,
    ) -> None:
        record = {
            "feature_name": feature_name,
            "file_id": file_id,
            "source_unit": source_unit,
            "target_unit": target_unit,
            "conversion": formula,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        records: List[Dict[str, Any]] = []
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    records = json.load(f)
            except Exception:
                records = []

        records.append(record)
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
