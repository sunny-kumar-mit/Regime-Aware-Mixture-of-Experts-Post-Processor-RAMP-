"""
RAMP GFS Provider Adapter
SIH26080 | NOAA Global Forecast System GRIB2 Adapter

Reads GFS 0.25° GRIB2 files using cfgrib/xarray.
If files are not present locally, returns ProviderUnavailableError — never fabricates data.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ramp.ingestion.base import (
    BoundingBox,
    DataMode,
    DataProvenance,
    FileFormat,
    ForecastTimeSpec,
    INDIA_DOMAIN,
    NWPForecastBundle,
    ProviderInfo,
    ProviderStatus,
    ProviderType,
    ProviderUnavailableError,
    ValidationReport,
    VariableDescriptor,
    WeatherForecastProvider,
)
from ramp.harmonisation.units import convert_units

logger = logging.getLogger("ramp.ingestion.gfs")


# GFS variable name mapping: GFS GRIB2 shortName → RAMP canonical
GFS_VARIABLE_MAP: Dict[str, str] = {
    "tp": "precip_nwp_raw",      # Total precipitation
    "acpcp": "precip_conv_nwp",  # Convective precipitation
    "u": "u850",                 # Zonal wind (level-dependent)
    "v": "v850",                 # Meridional wind
    "mslet": "mslp",             # MSLP
    "t": "t850",                 # Temperature
    "q": "q850",                 # Specific humidity
    "pwat": "pw",                # Precipitable water
    "cape": "cape",
    "cin": "cin",
    "gh": "z500",                # Geopotential height
}

# GFS GRIB2 source units (read from metadata — listed here for reference)
GFS_SOURCE_UNITS: Dict[str, str] = {
    "tp": "kg/m²",     # Accumulated precipitation
    "acpcp": "kg/m²",
    "mslet": "Pa",
    "t": "K",
    "q": "kg/kg",
    "pwat": "kg/m²",
    "cape": "J/kg",
    "cin": "J/kg",
    "gh": "m",
    "u": "m/s",
    "v": "m/s",
}


class GFSProvider(WeatherForecastProvider):
    """
    NOAA GFS GRIB2 data provider.

    Configuration:
        data_dir: Path to directory containing GFS GRIB2 files.
                  Expected filename pattern: gfs_YYYYMMDD_HHz_f{lead:03d}.grib2
    """

    PROVIDER_ID = "gfs"

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self._data_dir = Path(data_dir) if data_dir else Path("data/raw/nwp/gfs")
        self._data_mode = DataMode.REAL
        logger.info("GFSProvider initialized: data_dir=%s", self._data_dir)

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.NWP

    def _is_available(self) -> bool:
        """Check if GFS data directory exists and contains any GRIB2 files."""
        return self._data_dir.exists() and len(list(self._data_dir.glob("*.grib2"))) > 0

    def get_info(self) -> ProviderInfo:
        status = ProviderStatus.AVAILABLE if self._is_available() else ProviderStatus.NOT_CONFIGURED
        return ProviderInfo(
            provider_id=self.PROVIDER_ID,
            name="NOAA Global Forecast System (GFS)",
            provider_type=ProviderType.NWP,
            status=status,
            description=(
                "NOAA GFS deterministic NWP, 0.25° global grid, GRIB2 format. "
                "Available via NOMADS: https://nomads.ncep.noaa.gov"
            ),
            supported_formats=[FileFormat.GRIB2],
            available_variables=list(GFS_VARIABLE_MAP.values()),
            spatial_resolution_deg=0.25,
            notes=f"Data directory: {self._data_dir}",
        )

    def get_available_times(self) -> List[datetime]:
        """Scan local GRIB2 files and extract initialization times."""
        if not self._data_dir.exists():
            return []
        times = set()
        for f in sorted(self._data_dir.glob("gfs_????????_??z_f???.grib2")):
            try:
                parts = f.stem.split("_")
                date_str = parts[1]
                hour_str = parts[2].replace("z", "")
                dt = datetime(
                    int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]),
                    int(hour_str), tzinfo=timezone.utc
                )
                times.add(dt)
            except (ValueError, IndexError):
                logger.warning("Could not parse datetime from GFS filename: %s", f.name)
        return sorted(times)

    def get_forecast(
        self,
        initialization_time: datetime,
        lead_time_hours: int,
        variables: Optional[List[str]] = None,
        domain: BoundingBox = INDIA_DOMAIN,
    ) -> NWPForecastBundle:
        """
        Load a GFS forecast from local GRIB2 file.

        Raises ProviderUnavailableError if file is not found — NEVER fabricates data.
        """
        if not self._is_available():
            raise ProviderUnavailableError(
                self.PROVIDER_ID,
                f"No GFS GRIB2 files found in {self._data_dir}. "
                "Download GFS data from NOMADS and place in the configured directory."
            )

        # Construct expected filename
        ts = initialization_time.strftime("%Y%m%d_%Hz").replace("Z", "z").replace(
            "UTC", "z"
        )
        expected_hour = initialization_time.strftime("%H")
        fname = (
            self._data_dir
            / f"gfs_{initialization_time.strftime('%Y%m%d')}_{expected_hour}z"
              f"_f{lead_time_hours:03d}.grib2"
        )

        if not fname.exists():
            raise ProviderUnavailableError(
                self.PROVIDER_ID,
                f"Expected GFS file not found: {fname}"
            )

        time_spec = ForecastTimeSpec(
            initialization_time=initialization_time.astimezone(timezone.utc),
            lead_time_hours=lead_time_hours,
        )

        provenance = DataProvenance(
            source_provider="NOAA/NCEP",
            source_model="GFS",
            original_filename=str(fname.name),
            source_url="https://nomads.ncep.noaa.gov",
            data_mode=DataMode.REAL,
        )

        # Attempt to load with cfgrib
        xr_ds = self._load_grib2(fname, domain)
        provenance.add_step(f"Loaded GRIB2: {fname.name}")

        var_descriptors = self._build_var_descriptors(variables)

        bundle = NWPForecastBundle(
            time_spec=time_spec,
            provider_id=self.PROVIDER_ID,
            model_name="GFS",
            ensemble_member=None,
            variables=var_descriptors,
            data_mode=DataMode.REAL,
            provenance=provenance,
            xr_dataset=xr_ds,
        )
        logger.info(
            "GFS forecast loaded: init=%s lead=%dh valid=%s",
            initialization_time.isoformat(),
            lead_time_hours,
            bundle.forecast_valid_time.isoformat(),
        )
        return bundle

    def _load_grib2(self, filepath: Path, domain: BoundingBox) -> Any:
        """Load GRIB2 file using cfgrib. Returns xarray.Dataset or None."""
        try:
            import cfgrib
            import xarray as xr
            ds = xr.open_dataset(
                str(filepath),
                engine="cfgrib",
                backend_kwargs={"indexpath": ""},
            )
            logger.debug("Opened GRIB2: %s, variables: %s", filepath.name, list(ds.data_vars))
            return ds
        except Exception as exc:
            logger.error("Failed to open GRIB2 %s: %s", filepath, exc)
            raise ProviderUnavailableError(
                self.PROVIDER_ID,
                f"GRIB2 load error for {filepath.name}: {exc}"
            )

    def _build_var_descriptors(
        self, requested_vars: Optional[List[str]]
    ) -> Dict[str, VariableDescriptor]:
        descriptors: Dict[str, VariableDescriptor] = {}
        for grib_name, ramp_name in GFS_VARIABLE_MAP.items():
            if requested_vars and ramp_name not in requested_vars:
                continue
            src_unit = GFS_SOURCE_UNITS.get(grib_name, "unknown")
            from ramp.harmonisation.units import CANONICAL_TARGET_UNITS
            std_unit = CANONICAL_TARGET_UNITS.get(ramp_name, src_unit)
            descriptors[ramp_name] = VariableDescriptor(
                name=ramp_name,
                source_name=grib_name,
                standard_units=std_unit,
                source_units=src_unit,
                present=True,
            )
        return descriptors

    def validate_source(self) -> ValidationReport:
        """Check GFS data directory and report status."""
        report = ValidationReport(
            dataset_name="GFS GRIB2 Local Files",
            provider_id=self.PROVIDER_ID,
            model_name="GFS",
            data_mode=DataMode.REAL,
        )
        if not self._data_dir.exists():
            report.add_error(
                f"GFS data directory does not exist: {self._data_dir}"
            )
            return report

        files = list(self._data_dir.glob("*.grib2"))
        report.n_timesteps = len(files)
        if len(files) == 0:
            report.add_error(
                f"No GRIB2 files found in {self._data_dir}"
            )
        else:
            report.notes = f"Found {len(files)} GRIB2 file(s)."
            report.variables = list(GFS_VARIABLE_MAP.values())

        return report
