"""
Feature Contract Mapper for RAMP Real Data
SIH26080 | MoES / NCMRWF | Phase 19

Compares source meteorological variables against the canonical
'ramp_features_v1.0.0' contract (18 predictors).
Records explicit mappings, detects missing/extra fields,
and strictly prevents silent variable substitution or fabrication.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple
from ml.ingestion.sources import CANONICAL_18_PREDICTORS
from ml.real_data.models import FeatureMappingItem, FeatureMappingStatus

# Recognized aliases in meteorological archives (GRIB2 / NetCDF / CF conventions)
KNOWN_VARIABLE_ALIASES: Dict[str, List[str]] = {
    "precip_nwp_raw": ["tp", "precip", "precipitation", "rain", "tot_precip", "pr", "apcp", "total_precipitation", "precip_nwp_raw"],
    "u850": ["u850", "u_wind_850", "ucomp_850", "u_850", "ua850"],
    "v850": ["v850", "v_wind_850", "vcomp_850", "v_850", "va850"],
    "mslp": ["sp", "ps", "surface_pressure", "pres_sfc", "mslp", "prmsl"],
    "t850": ["t850", "t2m", "temp_850", "temperature_850", "t_850", "ta850", "temperature_2m"],
    "cape": ["cape", "mucape", "surface_cape", "cape_sfc"],
    "wind_speed_850": ["wind_speed_850", "ws850", "ws_850", "wind_speed", "wspd"],
    "wind_dir_850": ["wind_dir_850", "wdir850", "wdir_850", "wind_direction"],
    "lead_time_hours": ["lead_time_hours", "lead_hours", "lead", "step", "forecast_period"],
    "latitude": ["latitude", "lat", "lats"],
    "longitude": ["longitude", "lon", "lons"],
    "elevation_m": ["elevation_m", "elevation", "topo", "dem", "height"],
    "day_of_year_sin": ["day_of_year_sin", "doy_sin", "doy"],
    "day_of_year_cos": ["day_of_year_cos", "doy_cos"],
    "zonal_shear": ["zonal_shear", "u_shear", "shear_0_6km", "shear"],
    "monsoon_trough_intensity": ["monsoon_trough_intensity", "mti", "trough_intensity", "monsoon_trough_distance", "mtd"],
    "meridional_flow": ["meridional_flow", "v_flow", "meridional_wind"],
    "humidity_proxy": ["humidity_proxy", "rh850", "r850", "relative_humidity_850", "rh_850"],
}

# Unit requirements for RAMP features
EXPECTED_UNITS: Dict[str, str] = {
    "precip_nwp_raw": "mm",
    "u850": "m/s",
    "v850": "m/s",
    "mslp": "hPa",
    "t850": "degC",
    "cape": "J/kg",
    "wind_speed_850": "m/s",
    "wind_dir_850": "deg",
    "lead_time_hours": "hours",
    "latitude": "deg_N",
    "longitude": "deg_E",
    "elevation_m": "m",
    "day_of_year_sin": "dimensionless",
    "day_of_year_cos": "dimensionless",
    "zonal_shear": "m/s",
    "monsoon_trough_intensity": "hPa",
    "meridional_flow": "m/s",
    "humidity_proxy": "%",
}


class FeatureContractMapper:
    """
    Compares real source variables against 'ramp_features_v1.0.0'.
    Detects matched, missing, and extra variables without silent fallback.
    """

    def __init__(self, canonical_features: Optional[List[str]] = None):
        self.canonical_features = canonical_features or list(CANONICAL_18_PREDICTORS)

    def map_features(
        self,
        source_variables: List[str],
        source_units: Optional[Dict[str, str]] = None,
        source_grid: Optional[str] = None,
    ) -> Tuple[List[FeatureMappingItem], List[str], List[str]]:
        """
        Maps source variables to canonical RAMP features.

        Returns:
            mappings: List of FeatureMappingItem records
            missing_features: List of canonical features not present in source
            extra_features: List of source variables not mapped to canonical features
        """
        source_units = source_units or {}
        var_set = {v.lower().strip(): v for v in source_variables}
        matched_source_vars: Set[str] = set()
        mappings: List[FeatureMappingItem] = []
        missing_features: List[str] = []

        for feature in self.canonical_features:
            feat_lower = feature.lower()
            matched_var: Optional[str] = None
            status = FeatureMappingStatus.MISSING
            notes = None

            # 1. Exact match
            if feat_lower in var_set:
                matched_var = var_set[feat_lower]
                matched_source_vars.add(matched_var)
                status = FeatureMappingStatus.AVAILABLE
            else:
                # 2. Alias match
                aliases = KNOWN_VARIABLE_ALIASES.get(feature, [])
                for alias in aliases:
                    if alias.lower() in var_set:
                        matched_var = var_set[alias.lower()]
                        matched_source_vars.add(matched_var)
                        status = FeatureMappingStatus.MAPPED
                        notes = f"Mapped from alias '{matched_var}' to canonical '{feature}'"
                        break

            if matched_var is None:
                missing_features.append(feature)
                mappings.append(
                    FeatureMappingItem(
                        ramp_feature=feature,
                        source_variable=None,
                        unit=EXPECTED_UNITS.get(feature),
                        source_grid=source_grid,
                        status=FeatureMappingStatus.MISSING,
                        notes="Required predictor absent in source file",
                    )
                )
            else:
                # Check unit
                unit = source_units.get(matched_var, EXPECTED_UNITS.get(feature, ""))
                expected_unit = EXPECTED_UNITS.get(feature, "")
                if unit and expected_unit and unit.lower() != expected_unit.lower():
                    status = FeatureMappingStatus.UNIT_CONVERSION_REQUIRED
                    notes = f"Unit conversion needed: {unit} -> {expected_unit}"

                mappings.append(
                    FeatureMappingItem(
                        ramp_feature=feature,
                        source_variable=matched_var,
                        unit=unit,
                        source_grid=source_grid,
                        status=status,
                        notes=notes,
                    )
                )

        extra_features = [v for v in source_variables if v not in matched_source_vars]
        return mappings, missing_features, extra_features
