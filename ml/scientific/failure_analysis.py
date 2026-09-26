"""
RAMP Failure Analysis Engine — Phase 10
SIH26080 | MoES / NCMRWF

Identifies cases where RAMP underpredicts, overpredicts, misses heavy events,
or produces false alarms. Records full context for each failure case.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np


FAILURE_TYPES = [
    "UNDERPREDICTION",    # RAMP < observed by > threshold
    "OVERPREDICTION",     # RAMP > observed by > threshold
    "MISS_HEAVY",         # Observed >= 64.5 mm, RAMP < 64.5 mm
    "FALSE_ALARM_HEAVY",  # RAMP >= 64.5 mm, observed < 64.5 mm
    "POOR_CALIBRATION",   # Extreme prob mismatch
    "LARGE_DIVERGENCE",   # RAMP differs substantially from Raw NWP
]


@dataclass
class FailureCase:
    case_id: str
    failure_type: str
    timestamp: str
    latitude: float
    longitude: float
    district: str
    state: str
    lead_time_hours: int
    regime: str
    ramp_prediction_mm: float
    raw_nwp_mm: float
    global_ml_mm: float
    rain_probability: float
    heavy_probability: float
    very_heavy_probability: float
    extreme_probability: float
    observed_mm: Optional[float]
    error_mm: Optional[float]
    absolute_error_mm: Optional[float]
    threshold_category: str
    data_mode: str = "SYNTHETIC_DEMO"
    availability_status: str = "SYNTHETIC_DEMO"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "failure_type": self.failure_type,
            "timestamp": self.timestamp,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "district": self.district,
            "state": self.state,
            "lead_time_hours": self.lead_time_hours,
            "regime": self.regime,
            "ramp_prediction_mm": self.ramp_prediction_mm,
            "raw_nwp_mm": self.raw_nwp_mm,
            "global_ml_mm": self.global_ml_mm,
            "rain_probability": self.rain_probability,
            "heavy_probability": self.heavy_probability,
            "very_heavy_probability": self.very_heavy_probability,
            "extreme_probability": self.extreme_probability,
            "observed_mm": self.observed_mm,
            "error_mm": self.error_mm,
            "absolute_error_mm": self.absolute_error_mm,
            "threshold_category": self.threshold_category,
            "data_mode": self.data_mode,
            "availability_status": self.availability_status,
        }


@dataclass
class FailureSummary:
    total_cases_analyzed: int
    n_underprediction: int
    n_overprediction: int
    n_miss_heavy: int
    n_false_alarm_heavy: int
    n_large_divergence: int
    mean_absolute_error_failures: Optional[float]
    failure_cases: List[FailureCase] = field(default_factory=list)
    availability_status: str = "SYNTHETIC_DEMO"
    data_mode: str = "SYNTHETIC_DEMO"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_cases_analyzed": self.total_cases_analyzed,
            "n_underprediction": self.n_underprediction,
            "n_overprediction": self.n_overprediction,
            "n_miss_heavy": self.n_miss_heavy,
            "n_false_alarm_heavy": self.n_false_alarm_heavy,
            "n_large_divergence": self.n_large_divergence,
            "mean_absolute_error_failures": self.mean_absolute_error_failures,
            "n_failure_cases": len(self.failure_cases),
            "availability_status": self.availability_status,
            "data_mode": self.data_mode,
        }


class FailureAnalysisEngine:
    """
    Identifies and catalogs forecast failure cases.
    When real observations absent: produces synthetic labeled examples
    clearly identified as SYNTHETIC CASE STUDY.
    """

    UNDER_THRESHOLD = 10.0  # mm: threshold for underprediction flag
    DIVERGENCE_THRESHOLD = 15.0  # mm: threshold for large RAMP-NWP divergence

    SYNTHETIC_DISTRICTS = [
        ("MH-NAG", "Nagpur", "Maharashtra", 21.15, 79.08, "LOW_DEPRESSION"),
        ("KA-BAN", "Bangalore Rural", "Karnataka", 12.97, 77.59, "BREAK_MONSOON"),
        ("KL-KCH", "Kochi", "Kerala", 9.93, 76.26, "COASTAL"),
        ("TN-CHE", "Chennai", "Tamil Nadu", 13.08, 80.27, "COASTAL"),
        ("GJ-AHM", "Ahmedabad", "Gujarat", 23.02, 72.57, "BREAK_MONSOON"),
        ("OR-BHU", "Bhubaneswar", "Odisha", 20.29, 85.82, "ACTIVE_MONSOON"),
        ("WB-KOL", "Kolkata", "West Bengal", 22.56, 88.36, "LOW_DEPRESSION"),
        ("AS-GUW", "Guwahati", "Assam", 26.18, 91.73, "ACTIVE_MONSOON"),
        ("HP-SHM", "Shimla", "Himachal Pradesh", 31.10, 77.17, "WESTERN_DISTURBANCE"),
        ("RJ-JYP", "Jaipur", "Rajasthan", 26.91, 75.79, "TRANSITION_OTHER"),
    ]

    def __init__(self, data_mode: str = "SYNTHETIC_DEMO", random_seed: int = 42):
        self.data_mode = data_mode
        self.random_seed = random_seed

    def detect_failures(
        self,
        ramp_predictions: np.ndarray,
        raw_nwp: np.ndarray,
        observations: Optional[np.ndarray] = None,
        metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> FailureSummary:
        """
        Detect forecast failure cases.
        If observations absent: returns synthetic labeled cases.
        """
        if observations is None:
            return self._synthetic_failure_summary()

        n = len(ramp_predictions)
        cases = []
        n_under = n_over = n_miss = n_fa = n_div = 0

        for i in range(n):
            ramp = float(ramp_predictions[i])
            nwp = float(raw_nwp[i])
            obs = float(observations[i]) if observations is not None else None
            meta = metadata[i] if metadata else {}

            failures = []
            if obs is not None:
                err = ramp - obs
                if err < -self.UNDER_THRESHOLD:
                    failures.append("UNDERPREDICTION")
                    n_under += 1
                elif err > self.UNDER_THRESHOLD:
                    failures.append("OVERPREDICTION")
                    n_over += 1
                if obs >= 64.5 and ramp < 64.5:
                    failures.append("MISS_HEAVY")
                    n_miss += 1
                if ramp >= 64.5 and obs < 64.5:
                    failures.append("FALSE_ALARM_HEAVY")
                    n_fa += 1

            if abs(ramp - nwp) > self.DIVERGENCE_THRESHOLD:
                failures.append("LARGE_DIVERGENCE")
                n_div += 1

            if failures:
                obs_val = float(observations[i]) if observations is not None else None
                err = ramp - obs_val if obs_val is not None else None
                abs_err = abs(err) if err is not None else None
                cases.append(FailureCase(
                    case_id=f"FC_{i:05d}",
                    failure_type=failures[0],
                    timestamp=meta.get("timestamp", "UNKNOWN"),
                    latitude=meta.get("latitude", 0.0),
                    longitude=meta.get("longitude", 0.0),
                    district=meta.get("district", "UNKNOWN"),
                    state=meta.get("state", "UNKNOWN"),
                    lead_time_hours=meta.get("lead_time_hours", 24),
                    regime=meta.get("regime", "UNKNOWN"),
                    ramp_prediction_mm=round(ramp, 4),
                    raw_nwp_mm=round(nwp, 4),
                    global_ml_mm=meta.get("global_ml_mm", 0.0),
                    rain_probability=meta.get("rain_probability", 0.0),
                    heavy_probability=meta.get("heavy_probability", 0.0),
                    very_heavy_probability=meta.get("very_heavy_probability", 0.0),
                    extreme_probability=meta.get("extreme_probability", 0.0),
                    observed_mm=obs_val,
                    error_mm=round(err, 4) if err is not None else None,
                    absolute_error_mm=round(abs_err, 4) if abs_err is not None else None,
                    threshold_category=self._categorize(obs_val or ramp),
                    data_mode=self.data_mode,
                    availability_status="AVAILABLE",
                ))

        aes = [c.absolute_error_mm for c in cases if c.absolute_error_mm is not None]
        return FailureSummary(
            total_cases_analyzed=n,
            n_underprediction=n_under,
            n_overprediction=n_over,
            n_miss_heavy=n_miss,
            n_false_alarm_heavy=n_fa,
            n_large_divergence=n_div,
            mean_absolute_error_failures=round(float(np.mean(aes)), 4) if aes else None,
            failure_cases=cases,
            availability_status="AVAILABLE",
            data_mode=self.data_mode,
        )

    def _categorize(self, rainfall_mm: float) -> str:
        if rainfall_mm >= 204.5:
            return "EXTREMELY_HEAVY"
        elif rainfall_mm >= 115.6:
            return "VERY_HEAVY"
        elif rainfall_mm >= 64.5:
            return "HEAVY"
        elif rainfall_mm >= 0.1:
            return "RAIN"
        return "NO_RAIN"

    def _synthetic_failure_summary(self) -> FailureSummary:
        """
        Generate synthetic labeled failure cases for DEMO mode.
        All cases clearly identified as SYNTHETIC CASE STUDY.
        """
        rng = np.random.RandomState(self.random_seed)
        cases = []
        n = len(self.SYNTHETIC_DISTRICTS)

        for i, (did, dname, sname, lat, lon, regime) in enumerate(self.SYNTHETIC_DISTRICTS):
            nwp = float(abs(rng.exponential(12.0)))
            ramp = float(abs(nwp + rng.normal(-1.5, 4.0)))
            gml = float(abs(nwp + rng.normal(-0.5, 3.5)))

            # Assign synthetic failure types in rotation
            ftype = FAILURE_TYPES[i % len(FAILURE_TYPES)]

            cases.append(FailureCase(
                case_id=f"SYNTH_FC_{i:03d}",
                failure_type=ftype,
                timestamp="2024-07-15T06:00:00Z",
                latitude=lat,
                longitude=lon,
                district=dname,
                state=sname,
                lead_time_hours=int(rng.choice([24, 48, 72, 96, 120])),
                regime=regime,
                ramp_prediction_mm=round(ramp, 4),
                raw_nwp_mm=round(nwp, 4),
                global_ml_mm=round(gml, 4),
                rain_probability=round(float(rng.uniform(0.3, 0.9)), 4),
                heavy_probability=round(float(rng.uniform(0.05, 0.4)), 4),
                very_heavy_probability=round(float(rng.uniform(0.01, 0.15)), 4),
                extreme_probability=round(float(rng.uniform(0.0, 0.05)), 4),
                observed_mm=None,  # NOT_AVAILABLE in SYNTHETIC mode
                error_mm=None,
                absolute_error_mm=None,
                threshold_category=self._categorize(ramp),
                data_mode=self.data_mode,
                availability_status="SYNTHETIC_DEMO",
            ))

        return FailureSummary(
            total_cases_analyzed=n,
            n_underprediction=2,
            n_overprediction=2,
            n_miss_heavy=2,
            n_false_alarm_heavy=2,
            n_large_divergence=2,
            mean_absolute_error_failures=None,  # No real observations
            failure_cases=cases,
            availability_status="SYNTHETIC_DEMO",
            data_mode=self.data_mode,
        )
