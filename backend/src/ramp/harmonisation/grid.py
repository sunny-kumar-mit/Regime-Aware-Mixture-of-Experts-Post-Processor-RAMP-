"""
RAMP Grid Harmonization Module
SIH26080 | Spatial Regridding, Coordinate Normalization, Clipping

Scientific Choices:
  - Bilinear interpolation is used for continuous atmospheric fields
    (temperature, wind, humidity, pressure, geopotential).
  - For precipitation/rainfall, nearest-neighbour is used by default
    with a documented note. Conservative regridding would be preferable
    for area-integrated quantities but requires more complex setup.
  - All decisions are logged and traced in provenance.

RAMP Target Grid:
  lat: 6.5°N to 38.5°N  (129 points at 0.25°)
  lon: 66.5°E to 100.5°E (137 points at 0.25°)
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Tuple

import numpy as np

from ramp.ingestion.base import BoundingBox, GridSpec, INDIA_DOMAIN, RAMP_TARGET_GRID

logger = logging.getLogger("ramp.harmonisation.grid")

try:
    import xarray as xr
    HAS_XARRAY = True
except ImportError:
    HAS_XARRAY = False

try:
    from scipy.interpolate import RegularGridInterpolator
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


# =============================================================================
# Coordinate Normalization
# =============================================================================

def normalize_longitudes(lons: Any, to_range: Tuple[float, float] = (-180.0, 180.0)) -> Any:
    """
    Normalize longitudes to a specified range.

    Args:
        lons:     Longitude array (degrees).
        to_range: Target range, either (-180, 180) or (0, 360).

    Returns:
        Normalized longitude array.
    """
    lons = np.asarray(lons, dtype=float)
    lo, hi = to_range
    span = hi - lo
    return lo + np.mod(lons - lo, span)


def normalize_longitudes_to_0_360(lons: Any) -> Any:
    return normalize_longitudes(lons, to_range=(0.0, 360.0))


def normalize_longitudes_to_m180_180(lons: Any) -> Any:
    return normalize_longitudes(lons, to_range=(-180.0, 180.0))


def ensure_ascending_latitudes(
    lats: Any, data: Optional[Any] = None
) -> Tuple[Any, Optional[Any]]:
    """
    Ensure latitudes are in ascending order. Flip data along lat axis if needed.

    Args:
        lats: 1-D latitude array.
        data: Optional array with lat as first axis.

    Returns:
        (sorted_lats, optionally_flipped_data)
    """
    lats = np.asarray(lats, dtype=float)
    if lats[0] > lats[-1]:
        logger.debug("Flipping descending latitude array to ascending order.")
        lats = lats[::-1]
        if data is not None:
            data = data[..., ::-1, :]  # flip lat axis (second-to-last assumed)
    return lats, data


def clip_to_domain(
    lats: Any,
    lons: Any,
    data: Optional[Any] = None,
    domain: BoundingBox = INDIA_DOMAIN,
) -> Tuple[Any, Any, Optional[Any]]:
    """
    Spatially clip lat/lon arrays (and associated data) to a bounding box.

    Args:
        lats:   1-D latitude array (ascending).
        lons:   1-D longitude array (ascending).
        data:   Array with shape (..., n_lat, n_lon).
        domain: Target bounding box.

    Returns:
        (clipped_lats, clipped_lons, clipped_data)
    """
    lats = np.asarray(lats, dtype=float)
    lons = np.asarray(lons, dtype=float)

    lat_mask = (lats >= domain.lat_min) & (lats <= domain.lat_max)
    lon_mask = (lons >= domain.lon_min) & (lons <= domain.lon_max)

    clipped_lats = lats[lat_mask]
    clipped_lons = lons[lon_mask]

    clipped_data = None
    if data is not None:
        data_arr = np.asarray(data)
        # Assume data shape is (..., n_lat, n_lon)
        clipped_data = data_arr[..., lat_mask, :][..., lon_mask]

    logger.debug(
        "Clipped to domain %s: lat %d→%d pts, lon %d→%d pts",
        domain, len(lats), len(clipped_lats), len(lons), len(clipped_lons)
    )
    return clipped_lats, clipped_lons, clipped_data


# =============================================================================
# Target Grid Generation
# =============================================================================

def make_target_lats(grid: GridSpec = RAMP_TARGET_GRID) -> np.ndarray:
    return np.arange(grid.lat_min, grid.lat_max + grid.resolution_deg / 2, grid.resolution_deg)


def make_target_lons(grid: GridSpec = RAMP_TARGET_GRID) -> np.ndarray:
    return np.arange(grid.lon_min, grid.lon_max + grid.resolution_deg / 2, grid.resolution_deg)


# =============================================================================
# Regridding
# =============================================================================

RegridMethod = str  # "bilinear" | "nearest"


def regrid_field(
    src_lats: Any,
    src_lons: Any,
    src_data: Any,
    target_lats: Optional[Any] = None,
    target_lons: Optional[Any] = None,
    method: RegridMethod = "bilinear",
    is_precipitation: bool = False,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Regrid a 2-D field from source grid to RAMP target grid.

    Choices:
      - Bilinear for continuous atmospheric fields (temperature, wind, etc.).
      - Nearest for precipitation (bilinear can create sub-zero artefacts).
        NOTE: Conservative regridding is more accurate for precipitation but
        requires additional tooling (e.g. xesmf). Nearest is a reasonable
        fallback here and is the documented choice.

    Args:
        src_lats:        1-D source latitudes (ascending).
        src_lons:        1-D source longitudes (ascending).
        src_data:        2-D array shape (n_lat, n_lon).
        target_lats:     Target latitudes (default: RAMP 0.25°).
        target_lons:     Target longitudes (default: RAMP 0.25°).
        method:          "bilinear" or "nearest".
        is_precipitation: If True, forces nearest-neighbour to prevent
                          negative value artefacts.

    Returns:
        (target_lats, target_lons, regridded_data)
    """
    if not HAS_SCIPY:
        raise ImportError(
            "scipy is required for regridding. Install via: pip install scipy"
        )

    src_lats = np.asarray(src_lats, dtype=float)
    src_lons = np.asarray(src_lons, dtype=float)
    src_data = np.asarray(src_data, dtype=float)

    if target_lats is None:
        target_lats = make_target_lats()
    if target_lons is None:
        target_lons = make_target_lons()

    target_lats = np.asarray(target_lats, dtype=float)
    target_lons = np.asarray(target_lons, dtype=float)

    # Precipitation: use nearest-neighbour (avoids negative value artefacts)
    effective_method = "nearest" if is_precipitation else method

    if effective_method == "nearest":
        regridded = _regrid_nearest(src_lats, src_lons, src_data, target_lats, target_lons)
    elif effective_method == "bilinear":
        regridded = _regrid_bilinear(src_lats, src_lons, src_data, target_lats, target_lons)
    else:
        raise ValueError(f"Unknown regrid method: {method!r}. Use 'bilinear' or 'nearest'.")

    logger.debug(
        "Regridded (%s): %dx%d → %dx%d (method=%s, precip=%s)",
        "precip" if is_precipitation else "field",
        len(src_lats), len(src_lons),
        len(target_lats), len(target_lons),
        effective_method, is_precipitation,
    )

    return target_lats, target_lons, regridded


def _regrid_bilinear(
    src_lats: np.ndarray,
    src_lons: np.ndarray,
    src_data: np.ndarray,
    target_lats: np.ndarray,
    target_lons: np.ndarray,
) -> np.ndarray:
    """Bilinear interpolation using scipy.RegularGridInterpolator."""
    interp = RegularGridInterpolator(
        (src_lats, src_lons),
        src_data,
        method="linear",
        bounds_error=False,
        fill_value=np.nan,
    )
    tgt_lon_grid, tgt_lat_grid = np.meshgrid(target_lons, target_lats)
    pts = np.column_stack([tgt_lat_grid.ravel(), tgt_lon_grid.ravel()])
    regridded = interp(pts).reshape(len(target_lats), len(target_lons))
    return regridded


def _regrid_nearest(
    src_lats: np.ndarray,
    src_lons: np.ndarray,
    src_data: np.ndarray,
    target_lats: np.ndarray,
    target_lons: np.ndarray,
) -> np.ndarray:
    """Nearest-neighbour regridding."""
    interp = RegularGridInterpolator(
        (src_lats, src_lons),
        src_data,
        method="nearest",
        bounds_error=False,
        fill_value=np.nan,
    )
    tgt_lon_grid, tgt_lat_grid = np.meshgrid(target_lons, target_lats)
    pts = np.column_stack([tgt_lat_grid.ravel(), tgt_lon_grid.ravel()])
    regridded = interp(pts).reshape(len(target_lats), len(target_lons))
    return regridded


# =============================================================================
# xarray-based harmonization (preferred for full datasets)
# =============================================================================

def harmonize_xr_dataset(
    ds: Any,
    lat_dim: str = "latitude",
    lon_dim: str = "longitude",
    domain: BoundingBox = INDIA_DOMAIN,
    target_grid: GridSpec = RAMP_TARGET_GRID,
    precip_vars: Optional[list] = None,
) -> Any:
    """
    Harmonize an xarray.Dataset to RAMP canonical spatial domain and grid.

    Steps:
      1. Normalize longitude range to [0, 360].
      2. Ensure ascending latitude order.
      3. Clip to India domain.
      4. Regrid to target 0.25° grid.

    Args:
        ds:          Input xarray.Dataset.
        lat_dim:     Name of latitude dimension in ds.
        lon_dim:     Name of longitude dimension in ds.
        domain:      Target bounding box (default: India domain).
        target_grid: Target grid specification.
        precip_vars: List of precipitation variable names (use nearest regrid).

    Returns:
        Harmonized xarray.Dataset on RAMP canonical grid.
    """
    if not HAS_XARRAY:
        raise ImportError("xarray is required. Install via: pip install xarray")

    precip_vars = precip_vars or []

    # Step 1: Normalize longitude [0, 360]
    lons = ds[lon_dim].values
    if np.any(lons < 0):
        lons_360 = normalize_longitudes_to_0_360(lons)
        ds = ds.assign_coords({lon_dim: lons_360}).sortby(lon_dim)
        logger.debug("Normalized longitudes to [0, 360].")

    # Step 2: Ensure ascending latitude
    lats = ds[lat_dim].values
    if len(lats) > 1 and lats[0] > lats[-1]:
        ds = ds.isel({lat_dim: slice(None, None, -1)})
        logger.debug("Flipped latitudes to ascending order.")

    # Step 3: Clip to domain
    # Normalize domain lons to match [0, 360] space
    lon_min_360 = normalize_longitudes_to_0_360(np.array([domain.lon_min]))[0]
    lon_max_360 = normalize_longitudes_to_0_360(np.array([domain.lon_max]))[0]
    ds = ds.sel({
        lat_dim: slice(domain.lat_min, domain.lat_max),
        lon_dim: slice(lon_min_360, lon_max_360),
    })
    logger.debug("Clipped to India domain.")

    # Step 4: Regrid to target grid using interp (xarray native bilinear for non-precip)
    target_lats = make_target_lats(target_grid)
    target_lons = make_target_lons(target_grid)
    # Convert target lons to same [0,360] space
    target_lons_360 = normalize_longitudes_to_0_360(target_lons)

    # Interpolate — for precip vars use nearest, others use linear
    result_vars = {}
    for var in ds.data_vars:
        da = ds[var]
        method = "nearest" if var in precip_vars else "linear"
        try:
            regridded = da.interp(
                {lat_dim: target_lats, lon_dim: target_lons_360},
                method=method,
            )
            result_vars[var] = regridded
        except Exception as exc:
            logger.warning("Could not regrid variable %r: %s", var, exc)

    if result_vars:
        ds_out = xr.Dataset(result_vars)
    else:
        ds_out = ds

    logger.info(
        "Harmonized dataset: %d vars, lat %d pts, lon %d pts",
        len(ds_out.data_vars), len(target_lats), len(target_lons),
    )
    return ds_out
