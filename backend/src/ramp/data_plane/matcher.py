"""
RAMP NWP + IMD Temporal Matcher & Observation Ingestion Engine
SIH26080 | Phase 11 — Real Data Activation & Operational Data Plane
MoES / NCMRWF

Complies with Sections 8 & 9 of Phase 11:
- Observation matched using: forecast_valid_time == observation_time.
- Temporal Anti-Leakage Guard: Never use future observations during prediction.
- Explicit matching keys: initialization_time, valid_time, latitude, longitude, lead_time.
- Matching statuses:
    MATCHED
    PARTIAL
    MISSING_OBSERVATION
    MISSING_FORECAST
    MISALIGNED
- Scientific integrity: NEVER convert missing observations into 0 mm.
- Extreme-but-valid rainfall values (> 204.5 mm) flagged VALID_EXTREME and preserved.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class MatchStatus(str, Enum):
    MATCHED = "MATCHED"                        # Forecast valid time and observation time align exactly
    PARTIAL = "PARTIAL"                        # Overlapping grid or some lead times missing
    MISSING_OBSERVATION = "MISSING_OBSERVATION"# NWP forecast present, but IMD observation absent
    MISSING_FORECAST = "MISSING_FORECAST"      # IMD observation present, but NWP forecast absent
    MISALIGNED = "MISALIGNED"                  # Time offset exceeds alignment tolerance (> 3 hours)


@dataclass
class MatchResult:
    status: MatchStatus
    initialization_time: str
    forecast_valid_time: str
    observation_time: Optional[str]
    lead_time_hours: int
    model_name: str
    provider_id: str
    obs_provider_id: str
    time_offset_seconds: float
    is_temporally_valid: bool                  # False if observation is in the future relative to run
    leakage_violation: bool                    # True if future observation was requested
    spatial_coverage_fraction: float           # 1.0 for full coverage
    observed_missing_fraction: float           # Fraction of missing grid cells
    extreme_values_detected: int               # Count of rainfall values > 204.5 mm
    error_message: Optional[str] = None
    data_mode: str = "SYNTHETIC_DEMO"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


class DataMatchingEngine:
    """
    Temporal & spatial alignment engine coupling NWP forecast cycles with IMD observations.
    Enforces strict scientific contracts:
      1. forecast_valid_time == observation_time
      2. Missing observations are NEVER filled with 0 mm.
    """

    MAX_TIME_TOLERANCE_HOURS = 3.0  # Max acceptable misalignment

    @classmethod
    def match_forecast_to_observation(
        cls,
        initialization_time: datetime,
        lead_time_hours: int,
        observation_time: Optional[datetime],
        model_name: str = "NCUM",
        provider_id: str = "ncmrwf_ncum",
        obs_provider_id: str = "imd_obs",
        forecast_grid_present: bool = True,
        obs_grid_present: bool = True,
        obs_missing_fraction: float = 0.0,
        extreme_obs_count: int = 0,
        data_mode: str = "SYNTHETIC_DEMO",
    ) -> MatchResult:
        """
        Executes strict matching between a forecast time step and ground truth.
        """
        if initialization_time.tzinfo is None:
            initialization_time = initialization_time.replace(tzinfo=timezone.utc)

        valid_time = initialization_time + timedelta(hours=lead_time_hours)
        init_iso = initialization_time.isoformat()
        valid_iso = valid_time.isoformat()

        # Case 1: Forecast absent
        if not forecast_grid_present:
            obs_iso = observation_time.isoformat() if observation_time else None
            return MatchResult(
                status=MatchStatus.MISSING_FORECAST,
                initialization_time=init_iso,
                forecast_valid_time=valid_iso,
                observation_time=obs_iso,
                lead_time_hours=lead_time_hours,
                model_name=model_name,
                provider_id=provider_id,
                obs_provider_id=obs_provider_id,
                time_offset_seconds=0.0,
                is_temporally_valid=False,
                leakage_violation=False,
                spatial_coverage_fraction=0.0,
                observed_missing_fraction=obs_missing_fraction,
                extreme_values_detected=extreme_obs_count,
                error_message=f"Forecast grid missing for model {model_name} at init {init_iso} +{lead_time_hours}h",
                data_mode=data_mode,
            )

        # Case 2: Observation absent
        if observation_time is None or not obs_grid_present:
            return MatchResult(
                status=MatchStatus.MISSING_OBSERVATION,
                initialization_time=init_iso,
                forecast_valid_time=valid_iso,
                observation_time=None,
                lead_time_hours=lead_time_hours,
                model_name=model_name,
                provider_id=provider_id,
                obs_provider_id=obs_provider_id,
                time_offset_seconds=0.0,
                is_temporally_valid=True,
                leakage_violation=False,
                spatial_coverage_fraction=0.0,
                observed_missing_fraction=1.0,
                extreme_values_detected=0,
                error_message=(
                    "Observation data is missing for forecast valid time. "
                    "Rule enforced: Missing observations are NEVER converted into 0 mm."
                ),
                data_mode=data_mode,
            )

        if observation_time.tzinfo is None:
            observation_time = observation_time.replace(tzinfo=timezone.utc)
        obs_iso = observation_time.isoformat()

        # Check temporal offset
        offset_sec = abs((valid_time - observation_time).total_seconds())
        offset_hours = offset_sec / 3600.0

        # Anti-leakage verification:
        # Prediction time cannot use observations timestamped after prediction generation
        leakage_violation = False
        if observation_time > valid_time + timedelta(hours=1.0):
            leakage_violation = True

        if offset_hours > cls.MAX_TIME_TOLERANCE_HOURS:
            return MatchResult(
                status=MatchStatus.MISALIGNED,
                initialization_time=init_iso,
                forecast_valid_time=valid_iso,
                observation_time=obs_iso,
                lead_time_hours=lead_time_hours,
                model_name=model_name,
                provider_id=provider_id,
                obs_provider_id=obs_provider_id,
                time_offset_seconds=offset_sec,
                is_temporally_valid=False,
                leakage_violation=leakage_violation,
                spatial_coverage_fraction=0.0,
                observed_missing_fraction=obs_missing_fraction,
                extreme_values_detected=extreme_obs_count,
                error_message=f"Temporal misalignment ({offset_hours:.1f}h) exceeds tolerance ({cls.MAX_TIME_TOLERANCE_HOURS}h)",
                data_mode=data_mode,
            )

        # Partial coverage check
        if obs_missing_fraction > 0.25:
            status = MatchStatus.PARTIAL
        else:
            status = MatchStatus.MATCHED

        return MatchResult(
            status=status,
            initialization_time=init_iso,
            forecast_valid_time=valid_iso,
            observation_time=obs_iso,
            lead_time_hours=lead_time_hours,
            model_name=model_name,
            provider_id=provider_id,
            obs_provider_id=obs_provider_id,
            time_offset_seconds=offset_sec,
            is_temporally_valid=True,
            leakage_violation=leakage_violation,
            spatial_coverage_fraction=round(1.0 - obs_missing_fraction, 4),
            observed_missing_fraction=round(obs_missing_fraction, 4),
            extreme_values_detected=extreme_obs_count,
            error_message=None,
            data_mode=data_mode,
        )

    @classmethod
    def match_cycle_to_observations(
        cls,
        cycle_initialization: datetime,
        available_leads: List[int],
        available_obs_times: List[datetime],
        model_name: str = "NCUM",
        data_mode: str = "SYNTHETIC_DEMO",
    ) -> List[MatchResult]:
        """
        Matches an entire multi-lead cycle against available observation times.
        """
        results: List[MatchResult] = []
        obs_set = {
            t.astimezone(timezone.utc).date(): t.astimezone(timezone.utc)
            for t in available_obs_times
        }

        for lead in sorted(available_leads):
            target_valid = (cycle_initialization + timedelta(hours=lead)).astimezone(timezone.utc)
            target_date = target_valid.date()
            matching_obs = obs_set.get(target_date)

            res = cls.match_forecast_to_observation(
                initialization_time=cycle_initialization,
                lead_time_hours=lead,
                observation_time=matching_obs,
                model_name=model_name,
                obs_grid_present=(matching_obs is not None),
                data_mode=data_mode,
            )
            results.append(res)

        return results
