"""
RAMP Operational Case Study Replay & Error / Failure Analysis
SIH26080 | Phase 18 — Real-Data Activation & Institutional Acceptance Testing
MoES / NCMRWF

PART V: Real-Data Failure Analysis (Underprediction, Overprediction, Miss, False Alarm, Correct Detection)
PART W: Operational Case Study Replay (/forecast/cases; Timeline T0 -> Lead -> Obs -> Verification)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ForecastErrorClassification:
    error_type: str  # UNDERPREDICTION | OVERPREDICTION | MISS | FALSE_ALARM | CORRECT_DETECTION
    lead_hours: int
    threshold_mm: float
    region: str
    regime: str
    cycle: str
    count: int
    mean_error_magnitude_mm: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OperationalCaseStudy:
    case_id: str
    cycle_id: str
    date_str: str
    lead_hours: int
    regime: str
    timeline: Dict[str, str]  # T0, T_lead, T_obs, T_verif
    ncmrwf_input_summary: Dict[str, Any]
    raw_ncum_summary: Dict[str, Any]
    neps_ensemble_summary: Dict[str, Any]
    ramp_output_summary: Dict[str, Any]
    extreme_probability_summary: Dict[str, Any]
    uncertainty_summary: Dict[str, Any]
    imd_observation_summary: Optional[Dict[str, Any]]
    error_field_summary: Optional[Dict[str, Any]]
    verification_metrics: Optional[Dict[str, Any]]
    provenance: Dict[str, Any]
    data_mode: str  # REAL_OPERATIONAL | TEST_FIXTURE

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FailureAnalysisEngine:
    """
    PART V: Classifies meteorological forecast errors across paired cycles.
    Strict rule: Create case studies ONLY from actual data.
    """

    @staticmethod
    def classify_errors(
        obs: np.ndarray,
        pred: np.ndarray,
        lead_hours: int = 24,
        threshold_mm: float = 64.5,
        region: str = "NATIONAL",
        regime: str = "active_monsoon",
        cycle: str = "00Z",
    ) -> List[ForecastErrorClassification]:
        if len(obs) == 0 or len(pred) == 0:
            return []

        diff = pred - obs
        obs_event = obs >= threshold_mm
        pred_event = pred >= threshold_mm

        hits = obs_event & pred_event
        fa = (~obs_event) & pred_event
        miss = obs_event & (~pred_event)
        cd = (~obs_event) & (~pred_event)

        under = (diff < -5.0) & obs_event
        over = (diff > 5.0)

        classes = [
            ForecastErrorClassification(
                error_type="CORRECT_DETECTION",
                lead_hours=lead_hours,
                threshold_mm=threshold_mm,
                region=region,
                regime=regime,
                cycle=cycle,
                count=int(np.sum(hits)),
                mean_error_magnitude_mm=float(np.mean(np.abs(diff[hits]))) if np.sum(hits) > 0 else 0.0,
            ),
            ForecastErrorClassification(
                error_type="MISS",
                lead_hours=lead_hours,
                threshold_mm=threshold_mm,
                region=region,
                regime=regime,
                cycle=cycle,
                count=int(np.sum(miss)),
                mean_error_magnitude_mm=float(np.mean(np.abs(diff[miss]))) if np.sum(miss) > 0 else 0.0,
            ),
            ForecastErrorClassification(
                error_type="FALSE_ALARM",
                lead_hours=lead_hours,
                threshold_mm=threshold_mm,
                region=region,
                regime=regime,
                cycle=cycle,
                count=int(np.sum(fa)),
                mean_error_magnitude_mm=float(np.mean(np.abs(diff[fa]))) if np.sum(fa) > 0 else 0.0,
            ),
            ForecastErrorClassification(
                error_type="UNDERPREDICTION",
                lead_hours=lead_hours,
                threshold_mm=threshold_mm,
                region=region,
                regime=regime,
                cycle=cycle,
                count=int(np.sum(under)),
                mean_error_magnitude_mm=float(np.mean(np.abs(diff[under]))) if np.sum(under) > 0 else 0.0,
            ),
            ForecastErrorClassification(
                error_type="OVERPREDICTION",
                lead_hours=lead_hours,
                threshold_mm=threshold_mm,
                region=region,
                regime=regime,
                cycle=cycle,
                count=int(np.sum(over)),
                mean_error_magnitude_mm=float(np.mean(np.abs(diff[over]))) if np.sum(over) > 0 else 0.0,
            ),
        ]
        return classes


class OperationalCaseReplayService:
    """
    PART W: Manages historical case study replays.
    If no verified real cycles exist: returns NO_REAL_CASE_STUDIES_AVAILABLE.
    """

    def __init__(self, cases_dir: Optional[Path | str] = None):
        self.cases_dir = Path(cases_dir or "data/processed/case_studies")
        self._cases: List[OperationalCaseStudy] = []

    def list_cases(self) -> Dict[str, Any]:
        """Returns catalog of verified real case studies, or honest empty report."""
        if not self._cases:
            return {
                "status": "NO_REAL_CASE_STUDIES_AVAILABLE",
                "cases_count": 0,
                "cases": [],
                "disclaimer": "NO_REAL_CASE_STUDIES_AVAILABLE: Real operational archives unmounted. No real forecast cases have been verified.",
            }

        return {
            "status": "AVAILABLE",
            "cases_count": len(self._cases),
            "cases": [c.to_dict() for c in self._cases],
            "disclaimer": "Verified operational meteorological case studies available for interactive replay.",
        }

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        for c in self._cases:
            if c.case_id == case_id:
                return c.to_dict()
        return None

    def register_case(self, case: OperationalCaseStudy):
        self._cases.append(case)
