"""
RAMP Bootstrap Statistical Significance Engine — Phase 10
SIH26080 | MoES / NCMRWF

Paired bootstrap resampling for statistical comparison of forecasting systems.
Default: 300 samples, seed=42, 95% confidence intervals.

IMPORTANT: Never claim statistical significance without supporting evidence.
Uses LOWER_RMSE, NOT_SIGNIFICANT, SAMPLE_LIMITED labels.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

BOOTSTRAP_SAMPLES = 300
RANDOM_SEED = 42
CONFIDENCE_LEVEL = 0.95


@dataclass
class BootstrapResult:
    model_a: str
    model_b: str
    metric: str
    n_samples: int
    model_a_value: float
    model_b_value: float
    difference: float  # model_a - model_b
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    p_value_approx: Optional[float] = None
    conclusion: str = "NOT_SIGNIFICANT"  # NOT_SIGNIFICANT, LOWER_RMSE, HIGHER_CSI, SAMPLE_LIMITED, NOT_AVAILABLE
    n_bootstrap: int = BOOTSTRAP_SAMPLES
    confidence_level: float = CONFIDENCE_LEVEL
    effect_size: Optional[float] = None
    data_mode: str = "SYNTHETIC_DEMO"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_a": self.model_a,
            "model_b": self.model_b,
            "metric": self.metric,
            "n_samples": self.n_samples,
            "model_a_value": self.model_a_value,
            "model_b_value": self.model_b_value,
            "difference": self.difference,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "p_value_approx": self.p_value_approx,
            "conclusion": self.conclusion,
            "n_bootstrap": self.n_bootstrap,
            "confidence_level": self.confidence_level,
            "effect_size": self.effect_size,
            "data_mode": self.data_mode,
        }


class BootstrapSignificanceEngine:
    """
    Paired bootstrap resampling for model comparison.
    Reports factual metric labels — no subjective claims.
    Follows Phase 6 convention: 300 bootstrap samples, seed=42.
    """

    def __init__(
        self,
        n_bootstrap: int = BOOTSTRAP_SAMPLES,
        random_seed: int = RANDOM_SEED,
        confidence_level: float = CONFIDENCE_LEVEL,
        data_mode: str = "SYNTHETIC_DEMO",
    ):
        self.n_bootstrap = n_bootstrap
        self.random_seed = random_seed
        self.confidence_level = confidence_level
        self.data_mode = data_mode
        self.rng = np.random.RandomState(random_seed)

    def _paired_bootstrap_rmse(
        self,
        y_true: np.ndarray,
        y_a: np.ndarray,
        y_b: np.ndarray,
    ) -> Tuple[float, float, float, float, float]:
        """
        Paired bootstrap resampling for RMSE comparison.
        Returns (rmse_a, rmse_b, ci_lower, ci_upper, p_value_approx)
        """
        n = len(y_true)
        rmse_a = float(np.sqrt(np.mean((y_a - y_true) ** 2)))
        rmse_b = float(np.sqrt(np.mean((y_b - y_true) ** 2)))
        obs_diff = rmse_a - rmse_b

        boot_diffs = np.zeros(self.n_bootstrap)
        for i in range(self.n_bootstrap):
            idx = self.rng.randint(0, n, n)
            bt = y_true[idx]
            ba = y_a[idx]
            bb = y_b[idx]
            rmse_ba = float(np.sqrt(np.mean((ba - bt) ** 2)))
            rmse_bb = float(np.sqrt(np.mean((bb - bt) ** 2)))
            boot_diffs[i] = rmse_ba - rmse_bb

        alpha = 1.0 - self.confidence_level
        ci_lower = float(np.percentile(boot_diffs, alpha / 2 * 100))
        ci_upper = float(np.percentile(boot_diffs, (1 - alpha / 2) * 100))

        # Approximate p-value: fraction of bootstrap diffs that disagree with sign of obs_diff
        p_value = float(np.mean(boot_diffs >= 0)) if obs_diff < 0 else float(np.mean(boot_diffs <= 0))
        p_value = min(p_value * 2, 1.0)  # two-tailed

        return rmse_a, rmse_b, ci_lower, ci_upper, p_value

    def compare_rmse(
        self,
        y_true: np.ndarray,
        y_a: np.ndarray,
        y_b: np.ndarray,
        model_a: str,
        model_b: str,
    ) -> BootstrapResult:
        """Statistically compare RMSE of two models via paired bootstrap."""
        n = len(y_true)
        if n < 20:
            return BootstrapResult(
                model_a=model_a, model_b=model_b, metric="rmse",
                n_samples=n,
                model_a_value=float("nan"),
                model_b_value=float("nan"),
                difference=float("nan"),
                conclusion="SAMPLE_LIMITED",
                data_mode=self.data_mode,
            )

        rmse_a, rmse_b, ci_lower, ci_upper, p_val = self._paired_bootstrap_rmse(
            y_true, y_a, y_b
        )
        diff = rmse_a - rmse_b

        # Factual conclusion — no subjective ranking
        sig = ci_lower > 0 or ci_upper < 0  # CI does not cross 0
        if not sig:
            conclusion = "NOT_SIGNIFICANT"
        elif diff < 0:
            conclusion = "LOWER_RMSE"  # model_a has lower RMSE
        else:
            conclusion = "HIGHER_RMSE"  # model_a has higher RMSE

        effect_size = abs(diff) / max(rmse_a, rmse_b, 1e-6)

        return BootstrapResult(
            model_a=model_a, model_b=model_b, metric="rmse",
            n_samples=n,
            model_a_value=round(rmse_a, 4),
            model_b_value=round(rmse_b, 4),
            difference=round(diff, 4),
            ci_lower=round(ci_lower, 4),
            ci_upper=round(ci_upper, 4),
            p_value_approx=round(p_val, 4),
            conclusion=conclusion,
            n_bootstrap=self.n_bootstrap,
            confidence_level=self.confidence_level,
            effect_size=round(effect_size, 4),
            data_mode=self.data_mode,
        )

    def compare_mae(
        self,
        y_true: np.ndarray,
        y_a: np.ndarray,
        y_b: np.ndarray,
        model_a: str,
        model_b: str,
    ) -> BootstrapResult:
        """Compare MAE of two models via paired bootstrap."""
        n = len(y_true)
        if n < 20:
            return BootstrapResult(
                model_a=model_a, model_b=model_b, metric="mae",
                n_samples=n, model_a_value=float("nan"), model_b_value=float("nan"),
                difference=float("nan"), conclusion="SAMPLE_LIMITED", data_mode=self.data_mode,
            )

        mae_a = float(np.mean(np.abs(y_a - y_true)))
        mae_b = float(np.mean(np.abs(y_b - y_true)))
        diff = mae_a - mae_b

        boot_diffs = np.zeros(self.n_bootstrap)
        for i in range(self.n_bootstrap):
            idx = self.rng.randint(0, n, n)
            bt = y_true[idx]
            boot_diffs[i] = np.mean(np.abs(y_a[idx] - bt)) - np.mean(np.abs(y_b[idx] - bt))

        alpha = 1.0 - self.confidence_level
        ci_lower = float(np.percentile(boot_diffs, alpha / 2 * 100))
        ci_upper = float(np.percentile(boot_diffs, (1 - alpha / 2) * 100))
        p_val = min(2.0 * (float(np.mean(boot_diffs >= 0)) if diff < 0 else float(np.mean(boot_diffs <= 0))), 1.0)

        sig = ci_lower > 0 or ci_upper < 0
        conclusion = "NOT_SIGNIFICANT" if not sig else ("LOWER_MAE" if diff < 0 else "HIGHER_MAE")

        return BootstrapResult(
            model_a=model_a, model_b=model_b, metric="mae",
            n_samples=n,
            model_a_value=round(mae_a, 4),
            model_b_value=round(mae_b, 4),
            difference=round(diff, 4),
            ci_lower=round(ci_lower, 4),
            ci_upper=round(ci_upper, 4),
            p_value_approx=round(p_val, 4),
            conclusion=conclusion,
            n_bootstrap=self.n_bootstrap,
            confidence_level=self.confidence_level,
            data_mode=self.data_mode,
        )

    def run_pairwise_battery(
        self,
        y_true: Optional[np.ndarray] = None,
        predictions: Optional[Dict[str, np.ndarray]] = None,
        reference_model: str = "RAW_NWP",
        comparison_models: Optional[List[str]] = None,
    ) -> List[BootstrapResult]:
        """
        Run paired bootstrap comparisons: all models vs reference model (RAW_NWP).
        Default uses synthetic test partition data.
        """
        if y_true is None or predictions is None:
            rng = np.random.RandomState(self.random_seed)
            n = 200
            y_true = np.abs(rng.exponential(8.0, n))
            predictions = {
                "RAW_NWP": np.maximum(0, y_true + rng.normal(2.1, 6.5, n)),
                "MEAN_BIAS": np.maximum(0, y_true + rng.normal(0.4, 5.8, n)),
                "QUANTILE_MAPPING": np.maximum(0, y_true + rng.normal(0.1, 5.2, n)),
                "GLOBAL_ML": np.maximum(0, y_true + rng.normal(-0.3, 4.8, n)),
                "RAMP_MOE": np.maximum(0, y_true + rng.normal(-0.1, 4.2, n)),
                "RAMP_EXTREME": np.maximum(0, y_true + rng.normal(0.05, 4.0, n)),
            }

        if comparison_models is None:
            comparison_models = [m for m in predictions.keys() if m != reference_model]

        y_ref = predictions.get(reference_model)
        if y_ref is None:
            return []

        results = []
        for model in comparison_models:
            y_m = predictions.get(model)
            if y_m is None:
                continue
            # Compare model vs reference (RAW_NWP) for RMSE and MAE
            results.append(self.compare_rmse(y_true, y_m, y_ref, model, reference_model))
            results.append(self.compare_mae(y_true, y_m, y_ref, model, reference_model))

        return results
