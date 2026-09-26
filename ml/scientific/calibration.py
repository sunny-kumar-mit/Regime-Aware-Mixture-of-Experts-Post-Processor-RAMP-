"""
RAMP Probability Calibration Analyzer — Phase 10
SIH26080 | MoES / NCMRWF

Reliability diagrams and calibration metrics for Phase 7 extreme probability outputs.
Thresholds: 0.1 mm, 64.5 mm, 115.6 mm, 204.5 mm
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np

IMD_THRESHOLDS = [0.1, 64.5, 115.6, 204.5]
N_BINS = 10
MIN_BIN_SAMPLES = 5


@dataclass
class BrierMetrics:
    threshold_mm: float
    n_samples: int
    n_events: int
    brier: Optional[float] = None
    bss: Optional[float] = None
    ece: Optional[float] = None
    mce: Optional[float] = None
    log_loss: Optional[float] = None
    reliability_bins: List[Dict[str, Any]] = field(default_factory=list)
    availability_status: str = "NOT_AVAILABLE"
    data_mode: str = "SYNTHETIC_DEMO"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "threshold_mm": self.threshold_mm,
            "n_samples": self.n_samples,
            "n_events": self.n_events,
            "brier": self.brier,
            "bss": self.bss,
            "ece": self.ece,
            "mce": self.mce,
            "log_loss": self.log_loss,
            "reliability_bins": self.reliability_bins,
            "availability_status": self.availability_status,
            "data_mode": self.data_mode,
        }


class CalibrationAnalyzer:
    """
    Reliability diagram and calibration metric engine.
    Evaluates Phase 7 calibrated exceedance probabilities.
    Returns NOT_AVAILABLE if extreme events absent in synthetic domain.
    """

    def __init__(self, data_mode: str = "SYNTHETIC_DEMO", random_seed: int = 42):
        self.data_mode = data_mode
        self.random_seed = random_seed

    def _brier(self, y_true: np.ndarray, y_prob: np.ndarray) -> float:
        return float(np.mean((y_prob - y_true) ** 2))

    def _brier_skill_score(
        self, brier: float, y_true: np.ndarray
    ) -> Optional[float]:
        base_rate = np.mean(y_true)
        brier_ref = base_rate * (1 - base_rate)
        if brier_ref < 1e-9:
            return None
        return float(1.0 - brier / brier_ref)

    def _ece(self, y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = N_BINS) -> float:
        """Expected Calibration Error."""
        bin_edges = np.linspace(0, 1, n_bins + 1)
        ece_total = 0.0
        n = len(y_true)
        for i in range(n_bins):
            mask = (y_prob >= bin_edges[i]) & (y_prob < bin_edges[i + 1])
            if not np.any(mask):
                continue
            mean_prob = float(np.mean(y_prob[mask]))
            obs_freq = float(np.mean(y_true[mask]))
            ece_total += (np.sum(mask) / n) * abs(mean_prob - obs_freq)
        return round(ece_total, 6)

    def _mce(self, y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = N_BINS) -> float:
        """Maximum Calibration Error."""
        bin_edges = np.linspace(0, 1, n_bins + 1)
        errors = []
        for i in range(n_bins):
            mask = (y_prob >= bin_edges[i]) & (y_prob < bin_edges[i + 1])
            if np.sum(mask) < MIN_BIN_SAMPLES:
                continue
            errors.append(abs(float(np.mean(y_prob[mask])) - float(np.mean(y_true[mask]))))
        return round(max(errors), 6) if errors else 0.0

    def _log_loss(self, y_true: np.ndarray, y_prob: np.ndarray) -> float:
        eps = 1e-7
        p = np.clip(y_prob, eps, 1 - eps)
        return float(-np.mean(y_true * np.log(p) + (1 - y_true) * np.log(1 - p)))

    def _reliability_bins(
        self, y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = N_BINS
    ) -> List[Dict[str, Any]]:
        """Build reliability diagram bin data."""
        bin_edges = np.linspace(0, 1, n_bins + 1)
        bins = []
        for i in range(n_bins):
            mask = (y_prob >= bin_edges[i]) & (y_prob < bin_edges[i + 1])
            count = int(np.sum(mask))
            bins.append({
                "bin_lower": round(float(bin_edges[i]), 3),
                "bin_upper": round(float(bin_edges[i + 1]), 3),
                "bin_center": round(float((bin_edges[i] + bin_edges[i + 1]) / 2), 3),
                "mean_predicted_prob": round(float(np.mean(y_prob[mask])), 4) if count > 0 else None,
                "observed_frequency": round(float(np.mean(y_true[mask])), 4) if count >= MIN_BIN_SAMPLES else None,
                "count": count,
                "sufficient_samples": count >= MIN_BIN_SAMPLES,
            })
        return bins

    def analyze(
        self,
        y_true: np.ndarray,
        y_prob: np.ndarray,
        threshold_mm: float,
    ) -> BrierMetrics:
        """Compute calibration metrics for a single threshold."""
        n = len(y_true)
        n_events = int(np.sum(y_true >= 0.5))  # y_true should be binary 0/1 at threshold

        if n < 10:
            return BrierMetrics(
                threshold_mm=threshold_mm, n_samples=n, n_events=n_events,
                availability_status="NOT_AVAILABLE", data_mode=self.data_mode
            )
        if n_events < 5:
            return BrierMetrics(
                threshold_mm=threshold_mm, n_samples=n, n_events=n_events,
                availability_status="NO_EVENTS_IN_DOMAIN", data_mode=self.data_mode
            )

        brier = self._brier(y_true, y_prob)
        bss = self._brier_skill_score(brier, y_true)
        ece = self._ece(y_true, y_prob)
        mce = self._mce(y_true, y_prob)
        log_loss = self._log_loss(y_true, y_prob)
        rel_bins = self._reliability_bins(y_true, y_prob)

        return BrierMetrics(
            threshold_mm=threshold_mm,
            n_samples=n,
            n_events=n_events,
            brier=round(brier, 6),
            bss=round(bss, 4) if bss is not None else None,
            ece=round(ece, 6),
            mce=round(mce, 6),
            log_loss=round(log_loss, 6),
            reliability_bins=rel_bins,
            availability_status="AVAILABLE",
            data_mode=self.data_mode,
        )

    def analyze_all_thresholds(
        self,
        y_true_rainfall: Optional[np.ndarray] = None,
        prob_predictions: Optional[Dict[str, np.ndarray]] = None,
    ) -> Dict[float, BrierMetrics]:
        """
        Analyze calibration for all 4 IMD thresholds.
        In SYNTHETIC_DEMO mode, most extreme events are absent in the synthetic domain.
        Returns SAMPLE_LIMITED or NO_EVENTS_IN_DOMAIN as appropriate.
        """
        rng = np.random.RandomState(self.random_seed)

        if y_true_rainfall is None:
            n = 200
            y_true_rainfall = np.abs(rng.exponential(8.0, n))

        results = {}
        for thr in IMD_THRESHOLDS:
            obs_binary = (y_true_rainfall >= thr).astype(float)
            n_events = int(np.sum(obs_binary))

            if n_events < 5:
                results[thr] = BrierMetrics(
                    threshold_mm=thr, n_samples=len(y_true_rainfall), n_events=n_events,
                    availability_status="NO_EVENTS_IN_DOMAIN" if n_events == 0 else "SAMPLE_LIMITED",
                    data_mode=self.data_mode
                )
                continue

            # Synthetic calibrated probability based on exceedance
            base_rate = float(np.mean(obs_binary))
            y_prob = np.clip(
                obs_binary * 0.65 + (1 - obs_binary) * 0.08 + rng.normal(0, 0.06, len(y_true_rainfall)),
                0.0, 1.0
            )
            results[thr] = self.analyze(obs_binary, y_prob, thr)

        return results
