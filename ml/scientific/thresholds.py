"""
RAMP Threshold Verification Engine — Phase 10
SIH26080 | MoES / NCMRWF

Computes threshold-based categorical skill metrics for precipitation events.
Thresholds: 0.1 mm, 64.5 mm, 115.6 mm, 204.5 mm (IMD classification)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

IMD_THRESHOLDS = [0.1, 64.5, 115.6, 204.5]
IMD_THRESHOLD_NAMES = {
    0.1: "Rain",
    64.5: "Heavy",
    115.6: "Very Heavy",
    204.5: "Extremely Heavy",
}
MIN_EVENTS = 5  # minimum events to report CSI


@dataclass
class ContingencyTable:
    """2x2 contingency table for threshold verification."""
    threshold_mm: float
    threshold_name: str
    hit: int = 0
    miss: int = 0
    false_alarm: int = 0
    correct_negative: int = 0

    @property
    def n(self) -> int:
        return self.hit + self.miss + self.false_alarm + self.correct_negative

    @property
    def pod(self) -> Optional[float]:
        denom = self.hit + self.miss
        return self.hit / denom if denom > 0 else None

    @property
    def far(self) -> Optional[float]:
        denom = self.hit + self.false_alarm
        return self.false_alarm / denom if denom > 0 else None

    @property
    def csi(self) -> Optional[float]:
        denom = self.hit + self.miss + self.false_alarm
        return self.hit / denom if denom > 0 else None

    @property
    def ets(self) -> Optional[float]:
        """Equitable Threat Score (Gilbert Skill Score)."""
        denom = self.hit + self.miss + self.false_alarm
        if denom == 0:
            return None
        hits_random = ((self.hit + self.miss) * (self.hit + self.false_alarm)) / self.n
        ets_denom = self.hit + self.miss + self.false_alarm - hits_random
        return (self.hit - hits_random) / ets_denom if ets_denom != 0 else None

    @property
    def bias_score(self) -> Optional[float]:
        denom = self.hit + self.miss
        return (self.hit + self.false_alarm) / denom if denom > 0 else None

    @property
    def success_ratio(self) -> Optional[float]:
        denom = self.hit + self.false_alarm
        return self.hit / denom if denom > 0 else None

    @property
    def threat_score(self) -> Optional[float]:
        return self.csi  # Synonym

    @property
    def frequency_bias(self) -> Optional[float]:
        return self.bias_score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "threshold_mm": self.threshold_mm,
            "threshold_name": self.threshold_name,
            "hit": self.hit,
            "miss": self.miss,
            "false_alarm": self.false_alarm,
            "correct_negative": self.correct_negative,
            "n_total": self.n,
            "pod": round(self.pod, 4) if self.pod is not None else None,
            "far": round(self.far, 4) if self.far is not None else None,
            "csi": round(self.csi, 4) if self.csi is not None else None,
            "ets": round(self.ets, 4) if self.ets is not None else None,
            "bias_score": round(self.bias_score, 4) if self.bias_score is not None else None,
            "success_ratio": round(self.success_ratio, 4) if self.success_ratio is not None else None,
            "threat_score": round(self.threat_score, 4) if self.threat_score is not None else None,
            "frequency_bias": round(self.frequency_bias, 4) if self.frequency_bias is not None else None,
        }


@dataclass
class ThresholdMetrics:
    model: str
    threshold_mm: float
    threshold_name: str
    n_samples: int
    n_events: int
    availability_status: str
    contingency: Optional[ContingencyTable] = None
    data_mode: str = "SYNTHETIC_DEMO"
    model_version: str = "N/A"

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "model": self.model,
            "threshold_mm": self.threshold_mm,
            "threshold_name": self.threshold_name,
            "n_samples": self.n_samples,
            "n_events": self.n_events,
            "availability_status": self.availability_status,
            "data_mode": self.data_mode,
            "model_version": self.model_version,
        }
        if self.contingency:
            d.update(self.contingency.to_dict())
        else:
            d.update({k: None for k in ["pod", "far", "csi", "ets", "bias_score",
                                         "success_ratio", "threat_score", "frequency_bias"]})
        return d


class ThresholdVerificationEngine:
    """
    Categorical skill score engine for precipitation threshold verification.
    Supports 4 IMD thresholds across 6 model systems.
    """

    def __init__(self, data_mode: str = "SYNTHETIC_DEMO", random_seed: int = 42):
        self.data_mode = data_mode
        self.random_seed = random_seed

    def _contingency(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        threshold: float,
        model: str,
        model_version: str = "N/A",
    ) -> ThresholdMetrics:
        """Build contingency table for a single threshold and model pair."""
        obs_event = y_true >= threshold
        fcst_event = y_pred >= threshold
        n_events = int(np.sum(obs_event))

        if n_events < MIN_EVENTS:
            status = "NO_EVENTS_IN_DOMAIN" if n_events == 0 else "SAMPLE_LIMITED"
            return ThresholdMetrics(
                model=model,
                threshold_mm=threshold,
                threshold_name=IMD_THRESHOLD_NAMES.get(threshold, f"{threshold}mm"),
                n_samples=len(y_true),
                n_events=n_events,
                availability_status=status,
                data_mode=self.data_mode,
                model_version=model_version,
            )

        ct = ContingencyTable(
            threshold_mm=threshold,
            threshold_name=IMD_THRESHOLD_NAMES.get(threshold, f"{threshold}mm"),
            hit=int(np.sum(obs_event & fcst_event)),
            miss=int(np.sum(obs_event & ~fcst_event)),
            false_alarm=int(np.sum(~obs_event & fcst_event)),
            correct_negative=int(np.sum(~obs_event & ~fcst_event)),
        )

        return ThresholdMetrics(
            model=model,
            threshold_mm=threshold,
            threshold_name=IMD_THRESHOLD_NAMES.get(threshold, f"{threshold}mm"),
            n_samples=len(y_true),
            n_events=n_events,
            availability_status="AVAILABLE",
            contingency=ct,
            data_mode=self.data_mode,
            model_version=model_version,
        )

    def _generate_synthetic_data(self, n: int = 200) -> Dict:
        rng = np.random.RandomState(self.random_seed)
        y_true = np.abs(rng.exponential(8.0, n))
        noise = lambda s: rng.normal(0, s, n)
        return {
            "y_true": y_true,
            "RAW_NWP": np.maximum(0, y_true + noise(6.5) + 2.1),
            "MEAN_BIAS": np.maximum(0, y_true + noise(5.8) + 0.4),
            "QUANTILE_MAPPING": np.maximum(0, y_true + noise(5.2) + 0.1),
            "GLOBAL_ML": np.maximum(0, y_true + noise(4.8) - 0.3),
            "RAMP_MOE": np.maximum(0, y_true + noise(4.2) - 0.1),
            "RAMP_EXTREME": np.maximum(0, y_true + noise(4.0) + 0.05),
        }

    def compute_all_thresholds(
        self,
        observations: Optional[np.ndarray] = None,
        predictions: Optional[Dict[str, np.ndarray]] = None,
    ) -> Dict[str, List[ThresholdMetrics]]:
        """
        Compute threshold metrics for all 6 models × 4 thresholds.
        Returns dict keyed by model name with list of ThresholdMetrics per threshold.
        """
        if observations is None or predictions is None:
            synth = self._generate_synthetic_data()
            observations = synth["y_true"]
            models = ["RAW_NWP", "MEAN_BIAS", "QUANTILE_MAPPING", "GLOBAL_ML", "RAMP_MOE", "RAMP_EXTREME"]
            predictions = {m: synth[m] for m in models}

        model_versions = {
            "RAW_NWP": "nwp_raw",
            "MEAN_BIAS": "mean_bias_v1.0.0",
            "QUANTILE_MAPPING": "quantile_mapping_v1.0.0",
            "GLOBAL_ML": "global_ml_v1.0.0",
            "RAMP_MOE": "ramp_v1.0.0",
            "RAMP_EXTREME": "extreme_prob_v1.0.0",
        }

        results = {}
        for model, y_pred in predictions.items():
            model_metrics = []
            for thr in IMD_THRESHOLDS:
                tm = self._contingency(
                    observations, y_pred, thr, model,
                    model_versions.get(model, "N/A")
                )
                model_metrics.append(tm)
            results[model] = model_metrics
        return results

    def flat_table(
        self,
        threshold_results: Dict[str, List[ThresholdMetrics]],
    ) -> List[Dict[str, Any]]:
        """Returns flat list of dicts for tabular export."""
        rows = []
        for model, metrics_list in threshold_results.items():
            for m in metrics_list:
                rows.append(m.to_dict())
        return rows
