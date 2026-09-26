"""
RAMP IMD Observation Provider
SIH26080 | India Meteorological Department Gridded Rainfall

Reads IMD 0.25° gridded daily rainfall NetCDF files.
Metadata (units, calendar, fill value) is always read FROM the file, not hardcoded.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from ramp.ingestion.base import (
    BoundingBox,
    DataMode,
    DataProvenance,
    FileFormat,
    INDIA_DOMAIN,
    ObservationBundle,
    ObservationProvider,
    ProviderInfo,
    ProviderStatus,
    ProviderType,
    ProviderUnavailableError,
    ValidationReport,
)
from ramp.harmonisation.units import convert_units
from ramp.validation.quality import validate_array

logger = logging.getLogger("ramp.ingestion.imd")


class IMDObservationProvider(ObservationProvider):
    """
    IMD 0.25° Gridded Daily Rainfall observation provider.

    Data source: IMD official gridded rainfall dataset (NetCDF format).
    Temporal resolution: Daily (08:30 IST to 08:30 IST, i.e. 03:00 UTC to 03:00 UTC).

    Expected filename pattern:
        imd_rainfall_YYYY.nc  (annual files)
        or imd_rainfall_YYYYMMDD.nc  (daily files)

    Variable names, units, calendar, and fill values are read from file metadata.
    Nothing is hardcoded that can be read from the file.
    """

    PROVIDER_ID = "imd"
    EXPECTED_VARIABLE_CANDIDATES = ["rf", "rain", "RAIN", "precipitation", "tp"]
    EXPECTED_LAT_DIMS = ["lat", "latitude", "LAT"]
    EXPECTED_LON_DIMS = ["lon", "longitude", "LON"]
    EXPECTED_TIME_DIMS = ["time", "TIME", "date"]

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self._data_dir = (
            Path(data_dir) if data_dir else Path("data/raw/observations/imd")
        )
        self._cache: Dict[str, Any] = {}
        logger.info("IMDObservationProvider initialized: data_dir=%s", self._data_dir)

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def _nc_files(self) -> List[Path]:
        if not self._data_dir.exists():
            return []
        return sorted(
            list(self._data_dir.glob("*.nc"))
            + list(self._data_dir.glob("*.nc4"))
        )

    def _is_available(self) -> bool:
        return len(self._nc_files()) > 0

    def get_info(self) -> ProviderInfo:
        status = ProviderStatus.AVAILABLE if self._is_available() else ProviderStatus.NOT_CONFIGURED
        files = self._nc_files()
        return ProviderInfo(
            provider_id=self.PROVIDER_ID,
            name="IMD 0.25° Gridded Daily Rainfall",
            provider_type=ProviderType.OBSERVATION,
            status=status,
            description=(
                "Official IMD gridded daily rainfall at 0.25° resolution over India. "
                "Available from IMD Pune."
            ),
            supported_formats=[FileFormat.NETCDF],
            available_variables=["observed_rainfall_mm"],
            spatial_resolution_deg=0.25,
            notes=(
                f"Data directory: {self._data_dir}. "
                f"Found {len(files)} NetCDF file(s)."
            ),
        )

    def get_available_times(self) -> List[datetime]:
        """
        Return list of observation datetimes by scanning NetCDF time dimensions.
        Only loads time coordinates (lazy), not full data arrays.
        """
        times: List[datetime] = []
        for nc_path in self._nc_files():
            try:
                times.extend(self._extract_times_from_file(nc_path))
            except Exception as exc:
                logger.warning("Could not extract times from %s: %s", nc_path.name, exc)
        return sorted(set(times))

    def _extract_times_from_file(self, nc_path: Path) -> List[datetime]:
        import xarray as xr
        ds = xr.open_dataset(str(nc_path), chunks={})
        time_dim = self._find_dim(ds, self.EXPECTED_TIME_DIMS)
        if time_dim is None:
            return []
        time_vals = ds[time_dim].values
        result = []
        for t in time_vals:
            try:
                # Convert numpy datetime64 or cftime to Python datetime
                if hasattr(t, "astype"):
                    # numpy datetime64
                    ts = (
                        t.astype("datetime64[s]").astype(int)
                    )
                    dt = datetime.utcfromtimestamp(ts).replace(tzinfo=timezone.utc)
                elif hasattr(t, "year"):
                    # cftime
                    dt = datetime(t.year, t.month, t.day, t.hour, t.minute,
                                  tzinfo=timezone.utc)
                else:
                    continue
                result.append(dt)
            except Exception:
                continue
        return result

    def _find_dim(self, ds: Any, candidates: List[str]) -> Optional[str]:
        for c in candidates:
            if c in ds.dims or c in ds.coords:
                return c
        return None

    def _find_var(self, ds: Any, candidates: List[str]) -> Optional[str]:
        for c in candidates:
            if c in ds.data_vars:
                return c
        return None

    def get_observations(
        self,
        observation_time: datetime,
        domain: BoundingBox = INDIA_DOMAIN,
    ) -> ObservationBundle:
        """
        Retrieve IMD gridded rainfall for a specific observation time (UTC).

        IMPORTANT: The caller must ensure that observation_time == forecast_valid_time.
        Mismatching init_time with obs_time is a data leakage bug.

        Raises:
            ProviderUnavailableError: If no data is available.
        """
        if not self._is_available():
            raise ProviderUnavailableError(
                self.PROVIDER_ID,
                f"No IMD NetCDF files in {self._data_dir}. "
                "Place IMD gridded rainfall files there."
            )

        obs_utc = observation_time.astimezone(timezone.utc)

        # Find the file containing this observation time
        for nc_path in self._nc_files():
            try:
                bundle = self._load_obs_from_file(nc_path, obs_utc, domain)
                if bundle is not None:
                    return bundle
            except Exception as exc:
                logger.debug("File %s did not contain %s: %s",
                             nc_path.name, obs_utc.date(), exc)

        raise ProviderUnavailableError(
            self.PROVIDER_ID,
            f"IMD observation for {obs_utc.date()} not found in {self._data_dir}."
        )

    def _load_obs_from_file(
        self,
        nc_path: Path,
        obs_time: datetime,
        domain: BoundingBox,
    ) -> Optional[ObservationBundle]:
        import xarray as xr

        ds = xr.open_dataset(str(nc_path), chunks={})

        time_dim = self._find_dim(ds, self.EXPECTED_TIME_DIMS)
        lat_dim = self._find_dim(ds, self.EXPECTED_LAT_DIMS)
        lon_dim = self._find_dim(ds, self.EXPECTED_LON_DIMS)
        rain_var = self._find_var(ds, self.EXPECTED_VARIABLE_CANDIDATES)

        if any(d is None for d in [time_dim, lat_dim, lon_dim, rain_var]):
            logger.warning(
                "File %s: could not identify required dimensions. "
                "time=%s lat=%s lon=%s rain=%s",
                nc_path.name, time_dim, lat_dim, lon_dim, rain_var
            )
            return None

        # Read source unit FROM metadata (never hardcode)
        da_rain = ds[rain_var]
        source_unit = da_rain.attrs.get(
            "units", da_rain.attrs.get("unit", "mm")
        )

        # Select time slice
        try:
            da_day = da_rain.sel({time_dim: obs_time.date().isoformat()}, method="nearest")
        except Exception:
            return None  # Time not in this file

        # Clip to domain
        da_day = da_day.sel({
            lat_dim: slice(domain.lat_min, domain.lat_max),
            lon_dim: slice(domain.lon_min, domain.lon_max),
        })

        raw_vals = da_day.values.squeeze()

        # Normalize units
        converted, src_u, tgt_u = convert_units(
            raw_vals, source_unit, variable_name="observed_rainfall_mm"
        )

        # Quality flag the data
        from ramp.ingestion.base import ValidationReport
        qc_report = ValidationReport(
            dataset_name="IMD Rainfall QC",
            provider_id=self.PROVIDER_ID,
            data_mode=DataMode.REAL,
        )
        flags = validate_array(np.asarray(converted, dtype=float), "observed_rainfall_mm", qc_report)
        missing_frac = float(np.sum(np.isnan(converted)) / converted.size)

        provenance = DataProvenance(
            source_provider="IMD",
            source_model="IMD_Gridded",
            original_filename=nc_path.name,
            original_units={"observed_rainfall_mm": src_u},
            normalized_units={"observed_rainfall_mm": tgt_u},
            data_mode=DataMode.REAL,
        )
        provenance.add_step(f"Loaded from {nc_path.name}")
        provenance.add_step(f"Unit conversion: {src_u} → {tgt_u}")
        provenance.add_step("Quality flagging applied (extreme values preserved)")

        logger.info(
            "IMD observation loaded: %s, missing=%.2f%%, extreme=%d",
            obs_time.date(), 100 * missing_frac, qc_report.extreme_value_count
        )

        return ObservationBundle(
            observation_time=obs_time,
            provider_id=self.PROVIDER_ID,
            source="IMD_Gridded_0.25deg",
            observed_rainfall_mm=converted,
            quality_flags=flags,
            missing_fraction=missing_frac,
            data_mode=DataMode.REAL,
            provenance=provenance,
        )

    def validate_source(self) -> ValidationReport:
        report = ValidationReport(
            dataset_name="IMD 0.25° Gridded Rainfall",
            provider_id=self.PROVIDER_ID,
            model_name="IMD_Gridded",
            data_mode=DataMode.REAL,
        )
        files = self._nc_files()
        report.n_timesteps = len(files)
        report.variables = ["observed_rainfall_mm"]
        report.units = {"observed_rainfall_mm": "mm"}
        report.grid_resolution_deg = 0.25

        if not files:
            report.add_error(
                f"No IMD NetCDF files found in {self._data_dir}."
            )
        else:
            report.notes = f"Found {len(files)} IMD NetCDF file(s)."

        return report
