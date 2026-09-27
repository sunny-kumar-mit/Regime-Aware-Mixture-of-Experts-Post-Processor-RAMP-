"""
RAMP Temporal Validation & Forecast Cycle Matching Engine
SIH26080 | Phase 16 — Real-Data Activation & Operational Ingestion
MoES / NCMRWF

PART F — Temporal Validation Requirements:
  - Strict forecast-cycle matching:
      valid_time = initialization_time + lead_time
  - Canonical operational cycles (00Z, 12Z).
  - Absolute prohibitions:
      - Do NOT infer missing times.
      - Do NOT fabricate missing cycles.
      - Do NOT silently shift timestamps.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Standard NCMRWF Synoptic Forecast Cycles
CANONICAL_SYNOPTIC_CYCLES = ["00Z", "12Z"]


@dataclass
class TemporalValidationResult:
    """Detailed diagnostic of temporal coordinate validity and cycle alignment."""
    is_valid: bool
    status: str              # VALID | MISMATCH | INVALID_TIMESTAMP | MISSING_TIME | NON_CANONICAL_CYCLE
    initialization_time: Optional[str]
    valid_time: Optional[str]
    expected_valid_time: Optional[str]
    lead_time_hours: Optional[int]
    cycle: Optional[str]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TemporalValidator:
    """
    Enforces strict temporal consistency across forecast cycles and lead times.
    """

    @classmethod
    def parse_iso_datetime(cls, dt_str: Union[str, datetime]) -> datetime:
        """Parses an ISO format or YYYY-MM-DD string into a timezone-aware UTC datetime."""
        if isinstance(dt_str, datetime):
            if dt_str.tzinfo is None:
                return dt_str.replace(tzinfo=timezone.utc)
            return dt_str.astimezone(timezone.utc)

        s = str(dt_str).strip().replace("Z", "+00:00")
        # Handle date-only strings like 2026-09-27
        if len(s) == 10 and s.count("-") == 2:
            s += "T00:00:00+00:00"
        return datetime.fromisoformat(s).astimezone(timezone.utc)

    def validate_forecast_times(
        self,
        initialization_time: Union[str, datetime],
        valid_time: Union[str, datetime],
        lead_time_hours: int,
    ) -> TemporalValidationResult:
        """
        Validates the strict relationship: valid_time == initialization_time + lead_time.
        """
        errors: List[str] = []
        warnings: List[str] = []

        try:
            init_dt = self.parse_iso_datetime(initialization_time)
        except Exception as e:
            return TemporalValidationResult(
                is_valid=False,
                status="INVALID_TIMESTAMP",
                initialization_time=str(initialization_time),
                valid_time=str(valid_time),
                expected_valid_time=None,
                lead_time_hours=lead_time_hours,
                cycle=None,
                errors=[f"Failed to parse initialization_time: {e}"],
            )

        try:
            valid_dt = self.parse_iso_datetime(valid_time)
        except Exception as e:
            return TemporalValidationResult(
                is_valid=False,
                status="INVALID_TIMESTAMP",
                initialization_time=init_dt.isoformat(),
                valid_time=str(valid_time),
                expected_valid_time=None,
                lead_time_hours=lead_time_hours,
                cycle=None,
                errors=[f"Failed to parse valid_time: {e}"],
            )

        # 1. Lead time sanity check
        if lead_time_hours < 0:
            errors.append(f"Negative lead time ({lead_time_hours} hours) is physically impossible.")

        # 2. Cycle extraction (00Z, 12Z)
        cycle_str = f"{init_dt.hour:02d}Z"
        if cycle_str not in CANONICAL_SYNOPTIC_CYCLES:
            warnings.append(
                f"Initialization hour {init_dt.hour:02d}Z is non-canonical. Standard cycles are: {CANONICAL_SYNOPTIC_CYCLES}"
            )

        # 3. Strict valid time equality: valid_time == initialization_time + lead_time
        expected_valid_dt = init_dt + timedelta(hours=lead_time_hours)
        time_diff_sec = abs((valid_dt - expected_valid_dt).total_seconds())

        if time_diff_sec > 60:  # Tolerance within 1 minute
            errors.append(
                f"Temporal mismatch: valid_time ({valid_dt.isoformat()}) != "
                f"initialization_time ({init_dt.isoformat()}) + lead_time ({lead_time_hours}h). "
                f"Expected valid_time: {expected_valid_dt.isoformat()}."
            )

        is_valid = len(errors) == 0
        status = "VALID" if is_valid else "MISMATCH"

        return TemporalValidationResult(
            is_valid=is_valid,
            status=status,
            initialization_time=init_dt.isoformat(),
            valid_time=valid_dt.isoformat(),
            expected_valid_time=expected_valid_dt.isoformat(),
            lead_time_hours=lead_time_hours,
            cycle=cycle_str,
            errors=errors,
            warnings=warnings,
        )

    def validate_observation_date(
        self,
        observation_date: Union[str, datetime],
        expected_valid_date: Union[str, datetime],
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates that daily observation date matches the forecast valid date exactly.
        """
        try:
            obs_dt = self.parse_iso_datetime(observation_date).date()
            fcst_dt = self.parse_iso_datetime(expected_valid_date).date()
        except Exception as e:
            return False, f"Date parsing error: {e}"

        if obs_dt != fcst_dt:
            return False, f"Observation date ({obs_dt}) does not match forecast valid date ({fcst_dt})."

        return True, None
