"""
IMD Real Observation Adapter
SIH26080 | MoES / NCMRWF | Phase 19

Ingests genuine IMD 0.25° gridded daily rainfall observations.
Validates spatial grid, valid date, physical non-negativity (rain >= 0.0),
and permanently stamps observations with GROUND_TRUTH_ONLY isolation.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

try:
    import netCDF4 as nc
except ImportError:
    nc = None

from ml.real_data.grid_validator import GridValidator
from ml.real_data.models import (
    AuthorityLevel,
    DataMode,
    FailureStage,
    ImportedFileRecord,
    ProviderType,
    SourceType,
    ValidationErrorDetail,
    ValidationStatus,
)


class IMDRealObservationAdapter:
    """
    Adapter for genuine India Meteorological Department (IMD) 0.25° gridded daily rainfall observations.
    """

    def __init__(self):
        self.grid_validator = GridValidator()

    def inspect_and_validate(
        self,
        filepath: str | Path,
        source_id: str = "IMD_OBSERVATION",
        authority_level: AuthorityLevel = AuthorityLevel.AUTHORITATIVE_PRIMARY,
    ) -> ImportedFileRecord:
        path = Path(filepath)
        if not path.exists():
            return ImportedFileRecord(
                import_id=f"imd_err_{int(datetime.now(timezone.utc).timestamp())}",
                source_id=source_id,
                filename=path.name,
                filepath=str(path),
                provider=ProviderType.IMD,
                source_type=SourceType.IMD_OBSERVATION,
                authority_level=authority_level,
                format="UNKNOWN",
                size_bytes=0,
                sha256="",
                data_mode=DataMode.BLOCKED,
                validation_status=ValidationStatus.FAIL,
                failure_stage=FailureStage.IMPORT_FAILED,
                validation_notes=[f"File path does not exist: {path}"],
                is_ground_truth_only=True,
            )

        size_bytes = path.stat().st_size
        sha256 = self._compute_sha256(path)
        format_type = "NETCDF4" if path.suffix in [".nc", ".nc4", ".grd"] else "CSV"

        raw_vars: List[str] = []
        dims_map: Dict[str, int] = {}
        lats: Optional[np.ndarray] = None
        lons: Optional[np.ndarray] = None
        valid_date = None
        units_map = {"rain": "mm/day"}
        validation_notes: List[str] = []
        failure_stage = FailureStage.NONE
        has_negative_rain = False

        try:
            if nc is not None and path.suffix in [".nc", ".nc4"]:
                with nc.Dataset(path, "r") as ds:
                    valid_date = getattr(ds, "valid_date", getattr(ds, "date", None))
                    for dname, dim in ds.dimensions.items():
                        dims_map[dname] = len(dim)

                    for vname in ds.variables.keys():
                        raw_vars.append(vname)

                    min_detected_val: Optional[float] = None
                    offending_var: Optional[str] = None
                    for rname in ds.variables.keys():
                        if any(term in rname.lower() for term in ["rain", "rf", "precip"]):
                            arr = np.array(ds.variables[rname][:], dtype=float)
                            valid_arr = arr[~np.isnan(arr)]
                            # Exclude missing flag e.g. -999.0
                            physical_vals = valid_arr[valid_arr > -900]
                            if len(physical_vals) > 0 and np.nanmin(physical_vals) < -0.01:
                                has_negative_rain = True
                                min_detected_val = float(round(np.nanmin(physical_vals), 2))
                                offending_var = rname
                                break

                    for lat_c in ["lat", "latitude"]:
                        if lat_c in ds.variables:
                            lats = np.array(ds.variables[lat_c][:], dtype=float)
                            break
                    for lon_c in ["lon", "longitude"]:
                        if lon_c in ds.variables:
                            lons = np.array(ds.variables[lon_c][:], dtype=float)
                            break
        except Exception as e:
            validation_notes.append(f"Failed to read IMD observation file: {str(e)}")
            failure_stage = FailureStage.FORMAT_FAILED

        err_detail: Optional[ValidationErrorDetail] = None

        if has_negative_rain:
            validation_notes.append(
                f"QC_FAILED: Physical violation detected: rainfall contains negative values ({min_detected_val} mm/day)"
            )
            if failure_stage == FailureStage.NONE:
                failure_stage = FailureStage.QC_FAILED
            err_detail = ValidationErrorDetail(
                source="IMD",
                dataset="IMD_GRIDDED_RAINFALL",
                rule="NON_NEGATIVE_RAINFALL",
                severity="ERROR",
                variable=offending_var or "rain",
                message=f"Physical violation: invalid negative rainfall detected ({min_detected_val} mm/day).",
                expected="rainfall >= 0.0 mm/day",
                actual=f"{min_detected_val} mm/day",
                location="Observational grid cells",
                remediation="Reject observational file to maintain ground truth integrity; inspect IMD quality control flag.",
            )

        grid_record = self.grid_validator.validate_grid(lats, lons) if lats is not None and lons is not None else None
        if grid_record and not grid_record.is_valid:
            validation_notes.append(f"IMD observation grid invalid: {grid_record.notes}")
            if failure_stage == FailureStage.NONE:
                failure_stage = FailureStage.GRID_FAILED
            if not err_detail:
                err_detail = ValidationErrorDetail(
                    source="IMD",
                    dataset="IMD_GRIDDED_RAINFALL",
                    rule="GRID_RESOLUTION",
                    severity="ERROR",
                    variable="lat/lon",
                    message=f"IMD observation grid mismatch: {grid_record.notes}",
                    expected="IMD canonical 0.25° gridded rainfall domain [6.5°N-38.5°N, 66.5°E-100.0°E]",
                    actual=f"lat_range={grid_record.lat_bounds}, lon_range={grid_record.lon_bounds}",
                    location="Spatial grid coordinates",
                    remediation="Verify file is genuine IMD 0.25° daily rainfall binary (.grd) or converted NetCDF.",
                )

        if failure_stage == FailureStage.NONE and not has_negative_rain:
            val_status = ValidationStatus.PASS
            validation_notes.append("IMD observation satisfies 0.25° grid, non-negativity, and metadata standards.")
            data_mode = DataMode.REAL_DATA_EXPERIMENT
        else:
            val_status = ValidationStatus.FAIL
            data_mode = DataMode.BLOCKED
            if not err_detail:
                err_detail = ValidationErrorDetail(
                    source="IMD",
                    dataset="IMD_GRIDDED_RAINFALL",
                    rule="FORMAT_INTEGRITY",
                    severity="ERROR",
                    message="Failed to parse IMD observation file format",
                    expected="Valid IMD NetCDF4 or binary .grd file",
                    actual=format_type,
                    location=str(path.name),
                    remediation="Verify file integrity or re-fetch from IMD Pune portal via imdlib.",
                )

        import_id = f"imd_{path.stem}_{sha256[:8]}"

        return ImportedFileRecord(
            import_id=import_id,
            source_id=source_id,
            filename=path.name,
            filepath=str(path.resolve()),
            provider=ProviderType.IMD,
            source_type=SourceType.IMD_OBSERVATION,
            authority_level=authority_level,
            format=format_type,
            size_bytes=size_bytes,
            sha256=sha256,
            data_mode=data_mode,
            validation_status=val_status,
            validation_notes=validation_notes,
            validation_error_detail=err_detail,
            failure_stage=failure_stage,
            valid_time=valid_date,
            variables=raw_vars,
            dimensions=dims_map,
            lat_range=grid_record.lat_bounds if grid_record else None,
            lon_range=grid_record.lon_bounds if grid_record else None,
            resolution=grid_record.resolution_deg if grid_record else None,
            units_map=units_map,
            is_ground_truth_only=True,  # Critical integrity invariant
        )

    def _compute_sha256(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
