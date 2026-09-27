"""
Grid Validation & Alignment Engine for RAMP Real Data
SIH26080 | MoES / NCMRWF | Phase 19

Validates coordinate arrays, spatial resolution, and domain bounds
against the canonical RAMP India 0.25° grid (129 lats x 137 lons).
Explicitly specifies regridding requirements without silent interpolation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from ml.real_data.models import GridValidationRecord

# Canonical India domain specifications
CANONICAL_LATS = 129
CANONICAL_LONS = 137
CANONICAL_RESOLUTION = 0.25
CANONICAL_LAT_MIN = 6.0
CANONICAL_LAT_MAX = 38.5
CANONICAL_LON_MIN = 66.5
CANONICAL_LON_MAX = 100.5


class GridValidator:
    """
    Validates spatial grids from NWP (NCUM/NEPS) and IMD observation files.
    Ensures resolution, ordering, and extent match or can be explicitly regridded.
    """

    def __init__(
        self,
        target_lats: int = CANONICAL_LATS,
        target_lons: int = CANONICAL_LONS,
        resolution: float = CANONICAL_RESOLUTION,
    ):
        self.target_lats = target_lats
        self.target_lons = target_lons
        self.resolution = resolution

    def validate_grid(
        self,
        lats: np.ndarray,
        lons: np.ndarray,
    ) -> GridValidationRecord:
        """
        Validates 1D or 2D latitude and longitude coordinate arrays.
        """
        if lats is None or lons is None or len(lats) == 0 or len(lons) == 0:
            return GridValidationRecord(
                is_valid=False,
                source_grid_dims=(0, 0),
                notes="Coordinate arrays are empty or None",
            )

        # Handle 1D vs 2D coordinate representations
        if lats.ndim == 2 and lons.ndim == 2:
            n_lat, n_lon = lats.shape
            lat_min, lat_max = float(np.nanmin(lats)), float(np.nanmax(lats))
            lon_min, lon_max = float(np.nanmin(lons)), float(np.nanmax(lons))
            lat_diffs = np.diff(lats[:, 0])
            lon_diffs = np.diff(lons[0, :])
        elif lats.ndim == 1 and lons.ndim == 1:
            n_lat = len(lats)
            n_lon = len(lons)
            lat_min, lat_max = float(np.nanmin(lats)), float(np.nanmax(lats))
            lon_min, lon_max = float(np.nanmin(lons)), float(np.nanmax(lons))
            lat_diffs = np.diff(lats)
            lon_diffs = np.diff(lons)
        else:
            return GridValidationRecord(
                is_valid=False,
                source_grid_dims=(len(lats), len(lons)),
                notes="Inconsistent coordinate array dimensions",
            )

        # Check spacing regularity
        lat_step = float(np.nanmean(np.abs(lat_diffs))) if len(lat_diffs) > 0 else 0.0
        lon_step = float(np.nanmean(np.abs(lon_diffs))) if len(lon_diffs) > 0 else 0.0

        # Exact match check
        exact_dim_match = (n_lat == self.target_lats and n_lon == self.target_lons)
        exact_res_match = (
            abs(lat_step - self.resolution) < 0.01 and abs(lon_step - self.resolution) < 0.01
        )
        domain_encloses_india = (
            lat_min <= 8.0 and lat_max >= 36.0 and lon_min <= 69.0 and lon_max >= 95.0
        )

        if not domain_encloses_india:
            return GridValidationRecord(
                is_valid=False,
                source_grid_dims=(n_lat, n_lon),
                resolution_deg=round(lat_step, 4),
                lat_bounds=(lat_min, lat_max),
                lon_bounds=(lon_min, lon_max),
                notes=f"Domain bounds ({lat_min:.1f}-{lat_max:.1f}N, {lon_min:.1f}-{lon_max:.1f}E) do not enclose India canonical extent",
            )

        if exact_dim_match and exact_res_match:
            return GridValidationRecord(
                is_valid=True,
                source_grid_dims=(n_lat, n_lon),
                target_grid_dims=(self.target_lats, self.target_lons),
                resolution_deg=round(lat_step, 4),
                lat_bounds=(lat_min, lat_max),
                lon_bounds=(lon_min, lon_max),
                regrid_required=False,
                notes="Exact match with canonical RAMP 0.25° India grid",
            )

        # Regridding is required
        return GridValidationRecord(
            is_valid=True,
            source_grid_dims=(n_lat, n_lon),
            target_grid_dims=(self.target_lats, self.target_lons),
            resolution_deg=round(lat_step, 4),
            lat_bounds=(lat_min, lat_max),
            lon_bounds=(lon_min, lon_max),
            regrid_required=True,
            regrid_method="bilinear",
            regrid_library="scipy.interpolate.RegularGridInterpolator",
            regrid_config={"bounds_error": False, "fill_value": np.nan},
            notes=f"Regridding required: ({n_lat}x{n_lon}, {lat_step:.3f}°) -> ({self.target_lats}x{self.target_lons}, {self.resolution}°)",
        )
