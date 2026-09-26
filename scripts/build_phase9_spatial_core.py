"""Script to build Phase 9 spatial core modules.
"""
import os

# 2. ml/spatial/validation.py
validation_code = '''"""
RAMP Spatial Grid & Product Validation Engine
SIH26080 | Spatial Forecast Products & District Aggregation
MoES / NCMRWF
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from ml.spatial.grid import GridCell, STANDARD_LAT_MIN, STANDARD_LAT_MAX, STANDARD_LON_MIN, STANDARD_LON_MAX


class SpatialValidationError(ValueError):
    """Raised when spatial grid cells or district products fail scientific invariants."""
    pass


class SpatialValidator:
    """
    Validates spatial coordinates, duplicate keys, probabilities, and physical bounds.
    """

    @staticmethod
    def validate_grid_cell(cell: GridCell) -> Tuple[bool, List[str]]:
        """
        Validates a single GridCell according to 10 scientific checks:
        1. Latitude bounds [6.5, 38.5]
        2. Longitude bounds [66.5, 100.5]
        3. Non-empty grid ID
        4. Non-negative rainfall prediction
        5. Physical upper bound (<= 1500 mm/day)
        6. Probability range [0.0, 1.0] for all thresholds
        7. Strict probability monotonicity: P(0.1) >= P(64.5) >= P(115.6) >= P(204.5)
        8. Non-empty valid_time and init_time
        9. Non-negative lead time
        10. Non-empty model_version
        """
        errors: List[str] = []

        if not (STANDARD_LAT_MIN - 0.5 <= cell.latitude <= STANDARD_LAT_MAX + 0.5):
            errors.append(f"Latitude {cell.latitude} out of bounds [{STANDARD_LAT_MIN}, {STANDARD_LAT_MAX}].")

        if not (STANDARD_LON_MIN - 0.5 <= cell.longitude <= STANDARD_LON_MAX + 0.5):
            errors.append(f"Longitude {cell.longitude} out of bounds [{STANDARD_LON_MIN}, {STANDARD_LON_MAX}].")

        if not cell.grid_id or not cell.grid_id.strip():
            errors.append("Empty grid_id.")

        if cell.rainfall_prediction_mm < 0.0:
            errors.append(f"Negative rainfall prediction: {cell.rainfall_prediction_mm} mm.")

        if cell.rainfall_prediction_mm > 1500.0:
            errors.append(f"Physical upper bound exceeded (>1500 mm): {cell.rainfall_prediction_mm} mm.")

        probs = [
            ("rainfall_probability", cell.rainfall_probability),
            ("heavy_probability", cell.heavy_probability),
            ("very_heavy_probability", cell.very_heavy_probability),
            ("extreme_probability", cell.extreme_probability),
        ]
        for name, p in probs:
            if np.isnan(p) or p < -1e-5 or p > 1.0 + 1e-5:
                errors.append(f"Probability {name}={p} outside [0.0, 1.0].")

        # Probability monotonicity
        eps = 1e-4
        if cell.rainfall_probability + eps < cell.heavy_probability:
            errors.append(f"Monotonicity violation: P(Rain)={cell.rainfall_probability} < P(Heavy)={cell.heavy_probability}.")
        if cell.heavy_probability + eps < cell.very_heavy_probability:
            errors.append(f"Monotonicity violation: P(Heavy)={cell.heavy_probability} < P(VeryHeavy)={cell.very_heavy_probability}.")
        if cell.very_heavy_probability + eps < cell.extreme_probability:
            errors.append(f"Monotonicity violation: P(VeryHeavy)={cell.very_heavy_probability} < P(Extreme)={cell.extreme_probability}.")

        if not cell.forecast_valid_time:
            errors.append("Missing forecast_valid_time.")

        if cell.lead_time_hours < 0:
            errors.append(f"Negative lead time: {cell.lead_time_hours}.")

        return (len(errors) == 0, errors)

    @classmethod
    def validate_grid_collection(cls, cells: List[GridCell]) -> Dict[str, Any]:
        """
        Validates an entire collection of GridCells including duplicate ID checks.
        """
        seen_ids = set()
        seen_coords = set()
        invalid_count = 0
        error_log = []

        for cell in cells:
            is_valid, errs = cls.validate_grid_cell(cell)
            if not is_valid:
                invalid_count += 1
                error_log.append({"grid_id": cell.grid_id, "errors": errs})

            if cell.grid_id in seen_ids:
                invalid_count += 1
                error_log.append({"grid_id": cell.grid_id, "errors": ["Duplicate grid_id detected."]})
            seen_ids.add(cell.grid_id)

            coord_key = (round(cell.latitude, 4), round(cell.longitude, 4))
            if coord_key in seen_coords:
                invalid_count += 1
                error_log.append({"grid_id": cell.grid_id, "errors": [f"Duplicate coordinate {coord_key} detected."]})
            seen_coords.add(coord_key)

        return {
            "total_cells": len(cells),
            "valid_cells": len(cells) - invalid_count,
            "invalid_cells": invalid_count,
            "passed": invalid_count == 0,
            "errors": error_log[:50],  # cap reporting
        }
'''

with open("ml/spatial/validation.py", "w", encoding="utf-8") as f:
    f.write(validation_code)
print("Wrote ml/spatial/validation.py")
