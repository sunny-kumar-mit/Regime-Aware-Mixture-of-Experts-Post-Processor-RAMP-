"""
RAMP Lead-Time Verification — Phase 10
SIH26080 | MoES / NCMRWF

Evaluates forecast performance across lead times Day 1 to Day 5 (24h–120h).
Shows degradation curves and sample counts for each horizon.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np

LEAD_TIMES = [24, 48, 72, 96, 120]
LEAD_TIME_NAMES = {24: "Day 1", 48: "Day 2", 72: "Day 3", 96: "Day 4", 120: "Day 5"}
MIN_LT_SAMPLES = 10


@dataclass
class LeadTimePoint:
    lead_time_hours: int
    lead_time_name: str
    n_samples: int
    availability_status: str
    rmse: Optional[float] = None
    mae: Optional[float] = None
    bias: Optional[float] = None
    csi: Optional[float] = None
    pod: Optional[float] = None
    far: Optional[float] = None
    brier: Optional[float] = None
    fss_25km: Optional[float] = None
    data_mode: str = "SYNTHETIC_DEMO"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lead_time_hours": self.lead_time_hours,
            "lead_time_name": self.lead_time_name,
            "n_samples": self.n_samples,
            "availability_status": self.availability_status,
            "rmse": self.rmse,
            "mae": self.mae,
            "bias": self.bias,
            "csi": self.csi,
            "pod": self.pod,
            "far": self.far,
            "brier": self.brier,
            "fss_25km": self.fss_25km,
            "data_mode": self.data_mode,
        }


class LeadTimeVerification:
    """
    Lead-time stratified verification across Day 1 to Day 5.
    Shows sample count for every curve point.
    Degradation expected with increasing lead time.
    """

    # Synthetic degradation profile (RMSE degradation factor per day)
    DEGRADATION_PROFILE = {
        "RAW_NWP":           [1.00, 1.15, 1.28, 1.42, 1.56],
        "MEAN_BIAS":         [0.90, 1.05, 1.18, 1.31, 1.45],
        "QUANTILE_MAPPING":  [0.82, 0.96, 1.08, 1.21, 1.35],
        "GLOBAL_ML":         [0.76, 0.90, 1.02, 1.15, 1.29],
        "RAMP_MOE":          [0.68, 0.81, 0.93, 1.06, 1.20],
        "RAMP_EXTREME":      [0.65, 0.78, 0.90, 1.03, 1.17],
    }

    BASE_RMSE = 13.85  # From Phase 6 benchmark

    def __init__(self, data_mode: str = "SYNTHETIC_DEMO", random_seed: int = 42):
        self.data_mode = data_mode
        self.random_seed = random_seed

    def compute_lead_time_curves(
        self,
        observations_by_lt: Optional[Dict[int, np.ndarray]] = None,
        predictions_by_lt: Optional[Dict[int, Dict[str, np.ndarray]]] = None,
    ) -> Dict[str, List[LeadTimePoint]]:
        """
        Compute lead-time curves for all 6 models.
        Returns dict keyed by model, with list of LeadTimePoint per lead time.
        """
        if observations_by_lt is None:
            return self._synthetic_curves()

        results = {}
        for model in self.DEGRADATION_PROFILE.keys():
            points = []
            for lt in LEAD_TIMES:
                yt = observations_by_lt.get(lt)
                yp_map = predictions_by_lt.get(lt, {})
                yp = yp_map.get(model)

                if yt is None or yp is None or len(yt) < MIN_LT_SAMPLES:
                    n = 0 if yt is None else len(yt)
                    points.append(LeadTimePoint(
                        lead_time_hours=lt,
                        lead_time_name=LEAD_TIME_NAMES[lt],
                        n_samples=n,
                        availability_status="NOT_AVAILABLE" if n == 0 else "SAMPLE_LIMITED",
                        data_mode=self.data_mode,
                    ))
                    continue

                r = yp - yt
                rmse = float(np.sqrt(np.mean(r ** 2)))
                mae = float(np.mean(np.abs(r)))
                bias = float(np.mean(r))

                obs_rain = yt >= 0.1
                fcst_rain = yp >= 0.1
                n_rain = int(np.sum(obs_rain))
                csi = pod = far = None
                if n_rain >= 3:
                    h = int(np.sum(obs_rain & fcst_rain))
                    ms = int(np.sum(obs_rain & ~fcst_rain))
                    fa = int(np.sum(~obs_rain & fcst_rain))
                    if h + ms + fa > 0:
                        csi = h / (h + ms + fa)
                    if h + ms > 0:
                        pod = h / (h + ms)
                    if h + fa > 0:
                        far = fa / (h + fa)

                points.append(LeadTimePoint(
                    lead_time_hours=lt,
                    lead_time_name=LEAD_TIME_NAMES[lt],
                    n_samples=len(yt),
                    availability_status="AVAILABLE",
                    rmse=round(rmse, 4),
                    mae=round(mae, 4),
                    bias=round(bias, 4),
                    csi=round(csi, 4) if csi is not None else None,
                    pod=round(pod, 4) if pod is not None else None,
                    far=round(far, 4) if far is not None else None,
                    data_mode=self.data_mode,
                ))
            results[model] = points
        return results

    def _synthetic_curves(self) -> Dict[str, List[LeadTimePoint]]:
        """Generate synthetic lead-time degradation curves for DEMO mode."""
        rng = np.random.RandomState(self.random_seed)
        sample_counts = [52, 48, 45, 40, 38]  # decreasing with lead time
        results = {}

        for model, degradation in self.DEGRADATION_PROFILE.items():
            points = []
            for i, lt in enumerate(LEAD_TIMES):
                n = sample_counts[i]
                rmse = round(self.BASE_RMSE * degradation[i] + rng.uniform(-0.3, 0.3), 4)
                mae = round(rmse * 0.60, 4)
                bias = round(rng.uniform(-0.5, 0.5), 4)

                # CSI degrades with lead time and improves with better models
                base_csi = 0.55 - i * 0.07
                model_bonus = {"RAW_NWP": 0.0, "MEAN_BIAS": 0.03, "QUANTILE_MAPPING": 0.05,
                               "GLOBAL_ML": 0.07, "RAMP_MOE": 0.10, "RAMP_EXTREME": 0.11}.get(model, 0.0)
                csi = round(max(0.05, base_csi + model_bonus + rng.uniform(-0.02, 0.02)), 4)
                pod = round(min(1.0, csi + 0.15 + rng.uniform(-0.02, 0.02)), 4)
                far = round(max(0.0, 0.35 - model_bonus * 2 + rng.uniform(-0.03, 0.03)), 4)

                points.append(LeadTimePoint(
                    lead_time_hours=lt,
                    lead_time_name=LEAD_TIME_NAMES[lt],
                    n_samples=n,
                    availability_status="AVAILABLE",
                    rmse=rmse,
                    mae=mae,
                    bias=bias,
                    csi=csi,
                    pod=pod,
                    far=far,
                    data_mode=self.data_mode,
                ))
            results[model] = points
        return results

    def flat_table(
        self,
        lead_time_results: Dict[str, List[LeadTimePoint]],
    ) -> List[Dict[str, Any]]:
        rows = []
        for model, points in lead_time_results.items():
            for p in points:
                row = p.to_dict()
                row["model"] = model
                rows.append(row)
        return rows
