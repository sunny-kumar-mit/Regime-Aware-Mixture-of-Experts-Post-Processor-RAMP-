"""
RAMP NCMRWF Provider Adapter
SIH26080 | NCMRWF NCUM/NEPS NetCDF Adapter

CRITICAL NOTICE:
  NCMRWF NCUM and NEPS data require institutional access.
  Data is NOT available in this development environment.

  This adapter:
    1. Implements the full WeatherForecastProvider interface.
    2. Returns ProviderUnavailableError when data is not present.
    3. Documents exactly what file format and variable names are expected.
    4. NEVER fabricates synthetic data and claims it is NCMRWF output.

  When real NCMRWF data files are supplied, configure:
    NCUM_DATA_PATH=/path/to/ncum/files
  and this adapter will load them.
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

logger = logging.getLogger("ramp.ingestion.ncmrwf")


# NCUM NetCDF variable names (as documented in NCMRWF technical notes)
# These may vary between NCUM versions — read from file metadata when possible.
NCUM_VARIABLE_MAP: Dict[str, str] = {
    "total_precipitation": "precip_nwp_raw",
    "convective_precipitation": "precip_conv_nwp",
    "large_scale_precipitation": "precip_strat_nwp",
    "eastward_wind_850hPa": "u850",
    "northward_wind_850hPa": "v850",
    "eastward_wind_200hPa": "u200",
    "northward_wind_200hPa": "v200",
    "air_pressure_at_sea_level": "mslp",
    "air_temperature_850hPa": "t850",
    "air_temperature_500hPa": "t500",
    "specific_humidity_850hPa": "q850",
    "specific_humidity_700hPa": "q700",
    "precipitable_water": "pw",
    "cape": "cape",
    "relative_vorticity_850hPa": "vort850",
}

NCUM_SOURCE_UNITS: Dict[str, str] = {
    "total_precipitation": "kg/m²",
    "convective_precipitation": "kg/m²",
    "large_scale_precipitation": "kg/m²",
    "eastward_wind_850hPa": "m/s",
    "northward_wind_850hPa": "m/s",
    "eastward_wind_200hPa": "m/s",
    "northward_wind_200hPa": "m/s",
    "air_pressure_at_sea_level": "Pa",
    "air_temperature_850hPa": "K",
    "air_temperature_500hPa": "K",
    "specific_humidity_850hPa": "kg/kg",
    "specific_humidity_700hPa": "kg/kg",
    "precipitable_water": "kg/m²",
    "cape": "J/kg",
    "relative_vorticity_850hPa": "s-1",
}


class NCMRWFProvider(WeatherForecastProvider):
    """
    NCMRWF NCUM/NEPS NetCDF data provider (institutional access required).

    Configuration:
        data_dir:     Path to NCUM/NEPS NetCDF files.
        model_name:   "NCUM" (deterministic) or "NEPS" (ensemble).
        is_ensemble:  True for NEPS ensemble files.

    Expected filename pattern:
        NCUM: ncum_YYYYMMDD_HHz_f{lead:03d}.nc
        NEPS: neps_YYYYMMDD_HHz_m{member:03d}_f{lead:03d}.nc

    IMPORTANT:
        If data files are absent, this provider returns ProviderUnavailableError.
        It will NEVER substitute synthetic data for NCMRWF output.
    """

    def __init__(
        self,
        data_dir: Optional[str] = None,
        model_name: str = "NCUM",
        is_ensemble: bool = False,
    ) -> None:
        self._model = model_name.upper()
        self._is_ensemble = is_ensemble
        default_dir = f"data/raw/nwp/ncmrwf/{self._model.lower()}"
        self._data_dir = Path(data_dir) if data_dir else Path(default_dir)
        logger.info(
            "NCMRWFProvider initialized: model=%s data_dir=%s",
            self._model, self._data_dir
        )

    @property
    def provider_id(self) -> str:
        return f"ncmrwf_{self._model.lower()}"

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.NWP

    def _is_available(self) -> bool:
        """True only if data directory exists AND contains NetCDF files."""
        if not self._data_dir.exists():
            return False
        nc_files = list(self._data_dir.glob("*.nc")) + list(self._data_dir.glob("*.nc4"))
        return len(nc_files) > 0

    def get_info(self) -> ProviderInfo:
        if self._is_available():
            status = ProviderStatus.AVAILABLE
        elif self._data_dir.exists():
            status = ProviderStatus.CONFIGURED  # Dir exists but no data yet
        else:
            status = ProviderStatus.UNAVAILABLE

        return ProviderInfo(
            provider_id=self.provider_id,
            name=f"NCMRWF {self._model} {'Ensemble' if self._is_ensemble else 'Deterministic'}",
            provider_type=ProviderType.NWP,
            status=status,
            description=(
                f"NCMRWF {self._model} requires institutional data access from NCMRWF Noida. "
                "Data is available only to authorized users. "
                "This adapter will NOT fabricate data if files are absent."
            ),
            supported_formats=[FileFormat.NETCDF],
            available_variables=list(NCUM_VARIABLE_MAP.values()),
            spatial_resolution_deg=0.12,
            notes=(
                f"Expected data dir: {self._data_dir}. "
                f"Status: {'DATA PRESENT' if self._is_available() else 'NO DATA — institutional access required'}."
            ),
        )

    def get_available_times(self) -> List[datetime]:
        if not self._is_available():
            return []

        times = set()
        prefix = self._model.lower()
        for f in sorted(self._data_dir.glob(f"{prefix}_????????_??z_f???.nc")):
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
                pass
        return sorted(times)

    def get_forecast(
        self,
        initialization_time: datetime,
        lead_time_hours: int,
        variables: Optional[List[str]] = None,
        domain: BoundingBox = INDIA_DOMAIN,
    ) -> NWPForecastBundle:
        """
        Attempt to load NCMRWF data from local NetCDF files.

        Raises:
            ProviderUnavailableError: If files are not present.
                                     NEVER substitutes synthetic data.
        """
        if not self._is_available():
            raise ProviderUnavailableError(
                self.provider_id,
                f"NCMRWF {self._model} data not found in {self._data_dir}. "
                "Institutional data access from NCMRWF Noida is required. "
                "This system will NOT generate fabricated {self._model} data as a substitute."
            )

        prefix = self._model.lower()
        fname = (
            self._data_dir
            / f"{prefix}_{initialization_time.strftime('%Y%m%d')}_"
              f"{initialization_time.strftime('%H')}z_f{lead_time_hours:03d}.nc"
        )

        if not fname.exists():
            raise ProviderUnavailableError(
                self.provider_id,
                f"Expected {self._model} file not found: {fname}"
            )

        time_spec = ForecastTimeSpec(
            initialization_time=initialization_time.astimezone(timezone.utc),
            lead_time_hours=lead_time_hours,
        )

        provenance = DataProvenance(
            source_provider="NCMRWF",
            source_model=self._model,
            original_filename=str(fname.name),
            data_mode=DataMode.REAL,
        )
        provenance.add_step(f"Loaded NetCDF: {fname.name}")

        xr_ds = self._load_netcdf(fname)

        var_descriptors: Dict[str, VariableDescriptor] = {}
        for ncum_name, ramp_name in NCUM_VARIABLE_MAP.items():
            if variables and ramp_name not in variables:
                continue
            src_unit = NCUM_SOURCE_UNITS.get(ncum_name, "unknown")
            from ramp.harmonisation.units import CANONICAL_TARGET_UNITS
            var_descriptors[ramp_name] = VariableDescriptor(
                name=ramp_name,
                source_name=ncum_name,
                standard_units=CANONICAL_TARGET_UNITS.get(ramp_name, src_unit),
                source_units=src_unit,
                present=True,
            )

        return NWPForecastBundle(
            time_spec=time_spec,
            provider_id=self.provider_id,
            model_name=self._model,
            ensemble_member=None,
            variables=var_descriptors,
            data_mode=DataMode.REAL,
            provenance=provenance,
            xr_dataset=xr_ds,
        )

    def _load_netcdf(self, filepath: Path) -> Any:
        try:
            import xarray as xr
            ds = xr.open_dataset(str(filepath), chunks={})  # Lazy loading
            return ds
        except Exception as exc:
            raise ProviderUnavailableError(
                self.provider_id,
                f"NetCDF load error for {filepath.name}: {exc}"
            )

    def validate_source(self) -> ValidationReport:
        report = ValidationReport(
            dataset_name=f"NCMRWF {self._model} Local Files",
            provider_id=self.provider_id,
            model_name=self._model,
            data_mode=DataMode.REAL,
        )
        if not self._data_dir.exists():
            report.add_error(
                f"NCMRWF {self._model} data directory not found: {self._data_dir}. "
                "This is expected — institutional data access is required."
            )
        elif not self._is_available():
            report.add_error(
                f"NCMRWF {self._model} directory exists but contains no NetCDF files."
            )
        else:
            files = list(self._data_dir.glob("*.nc")) + list(self._data_dir.glob("*.nc4"))
            report.n_timesteps = len(files)
            report.notes = f"Found {len(files)} NetCDF files."
        return report
