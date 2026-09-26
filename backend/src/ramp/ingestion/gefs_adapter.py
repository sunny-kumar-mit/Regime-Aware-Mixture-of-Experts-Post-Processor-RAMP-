"""
RAMP GEFS Provider Adapter
SIH26080 | NOAA Global Ensemble Forecast System GRIB2 Adapter

Handles ensemble member dimension.
If files are not locally present: ProviderUnavailableError — never fabricates data.
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

logger = logging.getLogger("ramp.ingestion.gefs")

GEFS_VARIABLE_MAP: Dict[str, str] = {
    "tp": "precip_nwp_raw",
    "u": "u850",
    "v": "v850",
    "mslet": "mslp",
    "t": "t850",
    "pwat": "pw",
    "cape": "cape",
}

GEFS_SOURCE_UNITS: Dict[str, str] = {
    "tp": "kg/m²",
    "mslet": "Pa",
    "t": "K",
    "pwat": "kg/m²",
    "cape": "J/kg",
    "u": "m/s",
    "v": "m/s",
}

GEFS_N_MEMBERS = 31  # GEFS ensemble size


class GEFSProvider(WeatherForecastProvider):
    """
    NOAA GEFS 0.5° ensemble NWP provider.

    Expected filename pattern:
      gefs_YYYYMMDD_HHz_pXX_f{lead:03d}.grib2
      where XX is ensemble member number (00 = control, 01-30 = perturbed).
    """

    PROVIDER_ID = "gefs"

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self._data_dir = Path(data_dir) if data_dir else Path("data/raw/nwp/gefs")
        logger.info("GEFSProvider initialized: data_dir=%s", self._data_dir)

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.NWP

    def _is_available(self) -> bool:
        return self._data_dir.exists() and len(list(self._data_dir.glob("*.grib2"))) > 0

    def get_info(self) -> ProviderInfo:
        status = ProviderStatus.AVAILABLE if self._is_available() else ProviderStatus.NOT_CONFIGURED
        return ProviderInfo(
            provider_id=self.PROVIDER_ID,
            name="NOAA Global Ensemble Forecast System (GEFS)",
            provider_type=ProviderType.NWP,
            status=status,
            description=(
                f"NOAA GEFS {GEFS_N_MEMBERS}-member ensemble, 0.5° global grid, GRIB2 format."
            ),
            supported_formats=[FileFormat.GRIB2],
            available_variables=list(GEFS_VARIABLE_MAP.values()),
            spatial_resolution_deg=0.5,
            notes=f"Data directory: {self._data_dir}",
        )

    def get_available_times(self) -> List[datetime]:
        if not self._data_dir.exists():
            return []
        times = set()
        for f in sorted(self._data_dir.glob("gefs_????????_??z_p??_f???.grib2")):
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
        ensemble_member: Optional[int] = None,
    ) -> NWPForecastBundle:
        """
        Load a GEFS ensemble forecast from local GRIB2 file.
        If ensemble_member is None, loads control member (p00).
        """
        if not self._is_available():
            raise ProviderUnavailableError(
                self.PROVIDER_ID,
                f"No GEFS GRIB2 files found in {self._data_dir}."
            )

        member_str = f"p{(ensemble_member or 0):02d}"
        fname = (
            self._data_dir
            / f"gefs_{initialization_time.strftime('%Y%m%d')}_{initialization_time.strftime('%H')}z"
              f"_{member_str}_f{lead_time_hours:03d}.grib2"
        )

        if not fname.exists():
            raise ProviderUnavailableError(
                self.PROVIDER_ID,
                f"Expected GEFS file not found: {fname}"
            )

        time_spec = ForecastTimeSpec(
            initialization_time=initialization_time.astimezone(timezone.utc),
            lead_time_hours=lead_time_hours,
        )

        provenance = DataProvenance(
            source_provider="NOAA/NCEP",
            source_model="GEFS",
            original_filename=str(fname.name),
            source_url="https://nomads.ncep.noaa.gov",
            data_mode=DataMode.REAL,
        )

        xr_ds = self._load_grib2(fname)
        provenance.add_step(f"Loaded GRIB2: {fname.name}")

        var_descriptors: Dict[str, VariableDescriptor] = {}
        for grib_name, ramp_name in GEFS_VARIABLE_MAP.items():
            if variables and ramp_name not in variables:
                continue
            src_unit = GEFS_SOURCE_UNITS.get(grib_name, "unknown")
            from ramp.harmonisation.units import CANONICAL_TARGET_UNITS
            var_descriptors[ramp_name] = VariableDescriptor(
                name=ramp_name,
                source_name=grib_name,
                standard_units=CANONICAL_TARGET_UNITS.get(ramp_name, src_unit),
                source_units=src_unit,
                present=True,
            )

        return NWPForecastBundle(
            time_spec=time_spec,
            provider_id=self.PROVIDER_ID,
            model_name="GEFS",
            ensemble_member=ensemble_member,
            variables=var_descriptors,
            data_mode=DataMode.REAL,
            provenance=provenance,
            xr_dataset=xr_ds,
        )

    def _load_grib2(self, filepath: Path) -> Any:
        try:
            import xarray as xr
            ds = xr.open_dataset(str(filepath), engine="cfgrib",
                                 backend_kwargs={"indexpath": ""})
            return ds
        except Exception as exc:
            raise ProviderUnavailableError(
                self.PROVIDER_ID,
                f"GRIB2 load error for {filepath.name}: {exc}"
            )

    def validate_source(self) -> ValidationReport:
        report = ValidationReport(
            dataset_name="GEFS GRIB2 Local Files",
            provider_id=self.PROVIDER_ID,
            model_name="GEFS",
            data_mode=DataMode.REAL,
        )
        files = list(self._data_dir.glob("*.grib2")) if self._data_dir.exists() else []
        report.n_timesteps = len(files)
        if not files:
            report.add_error(f"No GEFS GRIB2 files in {self._data_dir}")
        else:
            report.notes = f"Found {len(files)} GRIB2 file(s) for GEFS."
        return report
