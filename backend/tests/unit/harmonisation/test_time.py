"""
Tests for RAMP Time Harmonization Module
SIH26080 | Critical: Valid-time vs Init-time alignment safeguards
"""

from datetime import datetime, timedelta, timezone

import pytest

from ramp.harmonisation.time import (
    align_forecast_to_observation,
    check_time_monotonicity,
    count_duplicate_times,
    generate_lead_times,
    make_time_spec,
    normalize_datetime_to_utc,
)
from ramp.ingestion.base import ForecastTimeSpec, TimeAlignmentError


class TestForecastTimeSpec:
    """Tests for the ForecastTimeSpec scientific contract."""

    def test_valid_time_is_init_plus_lead(self):
        """CRITICAL: forecast_valid_time MUST equal initialization_time + lead_time_hours."""
        init = datetime(2025, 7, 15, 0, 0, tzinfo=timezone.utc)
        lead = 72  # 3 days
        spec = ForecastTimeSpec(initialization_time=init, lead_time_hours=lead)
        expected_valid = datetime(2025, 7, 18, 0, 0, tzinfo=timezone.utc)
        assert spec.forecast_valid_time == expected_valid, (
            "forecast_valid_time must equal init + lead. "
            "This is the core scientific invariant of the system."
        )

    def test_valid_time_not_equal_to_init_time(self):
        """CRITICAL: valid_time must differ from init_time when lead > 0."""
        init = datetime(2025, 7, 15, 0, 0, tzinfo=timezone.utc)
        spec = ForecastTimeSpec(initialization_time=init, lead_time_hours=24)
        assert spec.forecast_valid_time != spec.initialization_time, (
            "forecast_valid_time must not equal initialization_time when lead > 0."
        )

    def test_lead_zero_valid_time_equals_init(self):
        """Lead=0 means analysis, so valid_time == init_time."""
        init = datetime(2025, 7, 15, 0, 0, tzinfo=timezone.utc)
        spec = ForecastTimeSpec(initialization_time=init, lead_time_hours=0)
        assert spec.forecast_valid_time == init

    def test_rejects_timezone_naive_init_time(self):
        """init_time must be UTC-aware. Naive datetimes are rejected."""
        naive = datetime(2025, 7, 15, 0, 0)  # no tzinfo
        with pytest.raises(ValueError):
            ForecastTimeSpec(initialization_time=naive, lead_time_hours=24)

    def test_rejects_negative_lead_time(self):
        """Negative lead time is physically nonsensical."""
        init = datetime(2025, 7, 15, 0, 0, tzinfo=timezone.utc)
        with pytest.raises(ValueError):
            ForecastTimeSpec(initialization_time=init, lead_time_hours=-6)


class TestMakeTimeSpec:
    def test_basic_creation(self):
        init = datetime(2025, 7, 15, 0, tzinfo=timezone.utc)
        spec = make_time_spec(init, 48)
        assert spec.lead_time_hours == 48
        assert spec.initialization_time == init

    def test_raises_on_naive_init(self):
        naive = datetime(2025, 7, 15, 0, 0)
        with pytest.raises(TimeAlignmentError):
            make_time_spec(naive, 24)

    def test_raises_on_negative_lead(self):
        init = datetime(2025, 7, 15, 0, tzinfo=timezone.utc)
        with pytest.raises(TimeAlignmentError):
            make_time_spec(init, -1)


class TestAlignForecastToObservation:
    """
    Tests for the critical alignment function.
    The key invariant: alignment must use forecast_valid_time, NOT initialization_time.
    """

    def _make_spec(self, init_date: str, lead_hours: int) -> ForecastTimeSpec:
        y, m, d = int(init_date[:4]), int(init_date[4:6]), int(init_date[6:8])
        init = datetime(y, m, d, 0, tzinfo=timezone.utc)
        return ForecastTimeSpec(initialization_time=init, lead_time_hours=lead_hours)

    def test_aligns_to_valid_time_not_init_time(self):
        """
        CRITICAL BUG-REGRESSION TEST.
        init=July 15, lead=72h → valid_time=July 18
        obs available at July 18 → must match July 18 (valid_time)
        obs available at July 15 → must NOT be preferred over July 18.
        """
        spec = self._make_spec("20250715", 72)
        assert spec.forecast_valid_time.day == 18, "Test setup: valid_time must be July 18"

        obs_times = [
            datetime(2025, 7, 15, 0, tzinfo=timezone.utc),  # init_time — WRONG match
            datetime(2025, 7, 18, 0, tzinfo=timezone.utc),  # valid_time — CORRECT match
            datetime(2025, 7, 19, 0, tzinfo=timezone.utc),
        ]

        matched = align_forecast_to_observation(spec, obs_times, tolerance_hours=12.0)
        assert matched is not None
        assert matched == datetime(2025, 7, 18, 0, tzinfo=timezone.utc), (
            "ALIGNMENT BUG: Must match forecast_valid_time (July 18), "
            "not initialization_time (July 15)."
        )

    def test_returns_none_when_no_obs_within_tolerance(self):
        spec = self._make_spec("20250715", 24)
        obs_times = [
            datetime(2025, 7, 20, 0, tzinfo=timezone.utc),  # 4 days away
        ]
        matched = align_forecast_to_observation(spec, obs_times, tolerance_hours=12.0)
        assert matched is None

    def test_returns_none_for_empty_obs_list(self):
        spec = self._make_spec("20250715", 24)
        matched = align_forecast_to_observation(spec, [], tolerance_hours=12.0)
        assert matched is None

    def test_tolerates_small_hour_offset(self):
        """Obs 2 hours after valid_time should match with 3h tolerance."""
        spec = self._make_spec("20250715", 24)
        valid = spec.forecast_valid_time
        obs_times = [valid + timedelta(hours=2)]
        matched = align_forecast_to_observation(spec, obs_times, tolerance_hours=3.0)
        assert matched == obs_times[0]

    def test_rejects_timezone_naive_obs_time(self):
        spec = self._make_spec("20250715", 24)
        naive_obs = [datetime(2025, 7, 16, 0)]
        with pytest.raises(TimeAlignmentError):
            align_forecast_to_observation(spec, naive_obs)


class TestTimeMonotonicity:
    def test_monotonic_ascending(self):
        times = [datetime(2025, 7, i, 0, tzinfo=timezone.utc) for i in range(1, 6)]
        ok, errors = check_time_monotonicity(times)
        assert ok
        assert not errors

    def test_non_monotonic_detected(self):
        times = [
            datetime(2025, 7, 1, 0, tzinfo=timezone.utc),
            datetime(2025, 7, 3, 0, tzinfo=timezone.utc),
            datetime(2025, 7, 2, 0, tzinfo=timezone.utc),  # out of order
        ]
        ok, errors = check_time_monotonicity(times)
        assert not ok
        assert len(errors) == 1

    def test_duplicate_detected(self):
        times = [
            datetime(2025, 7, 1, 0, tzinfo=timezone.utc),
            datetime(2025, 7, 1, 0, tzinfo=timezone.utc),  # duplicate
        ]
        n = count_duplicate_times(times)
        assert n == 1


class TestGenerateLeadTimes:
    def test_daily_leads(self):
        leads = generate_lead_times(24, 120, step_hours=24)
        assert leads == [24, 48, 72, 96, 120]

    def test_single_lead(self):
        leads = generate_lead_times(24, 24, step_hours=24)
        assert leads == [24]
