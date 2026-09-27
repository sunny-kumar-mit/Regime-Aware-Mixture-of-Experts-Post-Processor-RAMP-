"""
RAMP Meteorological Metadata Extraction & Validation Engine
SIH26080 | Phase 16 — Real-Data Activation & Operational Ingestion
MoES / NCMRWF

PART E — Metadata Validation Requirements:
  - Validate:
      provider, model, variable, units, latitude, longitude,
      calendar, time coordinate, forecast reference time, valid time, resolution.
  - Detect:
      missing metadata, duplicate timestamps, invalid coordinates,
      invalid time ranges, unsupported units.
  - Return explicit validation errors.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ml.ingestion.spatial import SpatialValidator
from ml.ingestion.temporal import TemporalValidator
from ml.ingestion.units import UnitNormalizer

logger = logging.getLogger(__name__)


@dataclass
class MetadataValidationResult:
    """Detailed validation diagnostic for file/dataset metadata."""
    is_valid: bool
    status: str              # VALID | INVALID_METADATA | MISSING_COORDINATES | UNSUPPORTED_UNITS | OUT_OF_BOUNDS
    provider: Optional[str]
    model: Optional[str]
    variables_present: List[str]
    variables_missing: List[str]
    units_validated: Dict[str, str]
    spatial_summary: Dict[str, Any]
    temporal_summary: Dict[str, Any]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MetadataValidator:
    """
    Validates NetCDF / GRIB / CSV metadata attributes against operational contracts.
    """

    def __init__(self):
        self.spatial_validator = SpatialValidator()
        self.temporal_validator = TemporalValidator()

    def validate_metadata_dict(
        self,
        metadata: Dict[str, Any],
        required_variables: Optional[List[str]] = None,
        allow_regridding: bool = False,
    ) -> MetadataValidationResult:
        """
        Validates an extracted metadata dictionary.
        """
        errors: List[str] = []
        warnings: List[str] = []

        provider = metadata.get("provider") or metadata.get("institution") or metadata.get("source")
        model = metadata.get("model") or metadata.get("title")

        # 1. Variable presence validation
        vars_present = metadata.get("variables", [])
        if isinstance(vars_present, dict):
            vars_present = list(vars_present.keys())
        vars_present = list(vars_present)

        vars_missing: List[str] = []
        if required_variables:
            for req in required_variables:
                if req not in vars_present:
                    vars_missing.append(req)

            if vars_missing:
                errors.append(f"Required variables missing from metadata: {vars_missing}")

        # 2. Units validation
        units_dict = metadata.get("units", {})
        validated_units: Dict[str, str] = {}
        for var, u in units_dict.items():
            valid_u, canon_or_err = UnitNormalizer.validate_variable_unit(var, str(u))
            if valid_u:
                validated_units[var] = canon_or_err or str(u)
            else:
                errors.append(f"Unit error for '{var}': {canon_or_err}")

        # 3. Spatial coordinate validation
        lats = metadata.get("latitude")
        if lats is None:
            lats = metadata.get("lat")
        if lats is None:
            lats = metadata.get("lats")

        lons = metadata.get("longitude")
        if lons is None:
            lons = metadata.get("lon")
        if lons is None:
            lons = metadata.get("lons")

        spatial_summary: Dict[str, Any] = {}
        if lats is not None and lons is not None:
            spatial_res = self.spatial_validator.validate_grid(
                lats, lons, allow_regridding=allow_regridding
            )
            spatial_summary = spatial_res.to_dict()
            if not spatial_res.is_valid:
                errors.extend(spatial_res.errors)
            warnings.extend(spatial_res.warnings)
        else:
            errors.append("Spatial coordinates (latitude, longitude) missing from metadata.")

        # 4. Temporal coordinate validation
        init_time = (
            metadata.get("initialization_time")
            or metadata.get("forecast_reference_time")
            or metadata.get("init_time")
        )
        valid_time = metadata.get("valid_time") or metadata.get("time")
        lead_time = metadata.get("lead_time_hours") or metadata.get("lead_time")

        temporal_summary: Dict[str, Any] = {}
        if init_time and valid_time and lead_time is not None:
            try:
                temp_res = self.temporal_validator.validate_forecast_times(
                    init_time, valid_time, int(lead_time)
                )
                temporal_summary = temp_res.to_dict()
                if not temp_res.is_valid:
                    errors.extend(temp_res.errors)
                warnings.extend(temp_res.warnings)
            except Exception as e:
                errors.append(f"Temporal validation failed: {e}")
        elif metadata.get("observation_date"):
            # For observational data
            temporal_summary = {"observation_date": str(metadata.get("observation_date"))}
        else:
            warnings.append("Temporal coordinates incomplete (missing init_time, valid_time, or lead_time).")

        is_valid = len(errors) == 0
        status = "VALID" if is_valid else "INVALID_METADATA"

        return MetadataValidationResult(
            is_valid=is_valid,
            status=status,
            provider=provider,
            model=model,
            variables_present=vars_present,
            variables_missing=vars_missing,
            units_validated=validated_units,
            spatial_summary=spatial_summary,
            temporal_summary=temporal_summary,
            errors=errors,
            warnings=warnings,
        )

    def extract_and_validate_file(
        self,
        filepath: Path | str,
        required_variables: Optional[List[str]] = None,
        allow_regridding: bool = False,
    ) -> MetadataValidationResult:
        """
        Extracts CF metadata directly from NetCDF or GRIB file and validates it.
        """
        p = Path(filepath)
        if not p.exists():
            return MetadataValidationResult(
                is_valid=False,
                status="FILE_NOT_FOUND",
                provider=None,
                model=None,
                variables_present=[],
                variables_missing=required_variables or [],
                units_validated={},
                spatial_summary={},
                temporal_summary={},
                errors=[f"File not found: {p}"],
            )

        metadata: Dict[str, Any] = {
            "file_name": p.name,
            "file_size": p.stat().st_size,
        }

        # Attempt NetCDF extraction using netCDF4 or xarray
        ext = p.suffix.lower()
        if ext in {".nc", ".nc4", ".netcdf"}:
            try:
                import netCDF4 as nc
                with nc.Dataset(p, "r") as ds:
                    metadata["provider"] = getattr(ds, "institution", getattr(ds, "source", None))
                    metadata["model"] = getattr(ds, "title", getattr(ds, "model", None))
                    metadata["variables"] = list(ds.variables.keys())

                    units_dict = {}
                    for vname, vobj in ds.variables.items():
                        if hasattr(vobj, "units"):
                            units_dict[vname] = vobj.units
                    metadata["units"] = units_dict

                    if "lat" in ds.variables:
                        metadata["latitude"] = ds.variables["lat"][:]
                    elif "latitude" in ds.variables:
                        metadata["latitude"] = ds.variables["latitude"][:]

                    if "lon" in ds.variables:
                        metadata["longitude"] = ds.variables["lon"][:]
                    elif "longitude" in ds.variables:
                        metadata["longitude"] = ds.variables["longitude"][:]

                    for attr in ["initialization_time", "forecast_reference_time", "valid_time", "lead_time_hours"]:
                        if hasattr(ds, attr):
                            metadata[attr] = getattr(ds, attr)
            except Exception as e:
                logger.warning(f"netCDF4 extraction error on {p.name}: {e}")
                # Try fallback JSON companion if exists (common in test fixtures)
                companion = p.with_suffix(".json")
                if companion.exists():
                    try:
                        with open(companion, "r", encoding="utf-8") as f:
                            metadata.update(json.load(f))
                    except Exception:
                        pass

        elif ext in {".csv", ".parquet"}:
            try:
                import pandas as pd
                df = pd.read_parquet(p) if ext == ".parquet" else pd.read_csv(p, nrows=100)
                metadata["variables"] = list(df.columns)
                if "latitude" in df.columns and "longitude" in df.columns:
                    metadata["latitude"] = df["latitude"].unique()
                    metadata["longitude"] = df["longitude"].unique()
            except Exception as e:
                logger.warning(f"Tabular extraction error on {p.name}: {e}")

        return self.validate_metadata_dict(
            metadata,
            required_variables=required_variables,
            allow_regridding=allow_regridding,
        )
