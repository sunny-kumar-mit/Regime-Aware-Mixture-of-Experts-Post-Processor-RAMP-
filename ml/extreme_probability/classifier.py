"""
Phase 7 Extreme Rainfall Probability — Per-Threshold Classifier
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Each threshold gets its own LightGBM binary classifier + calibration layer.
Calibration is STRICTLY fitted on VALIDATION data only.
"""

from __future__ import annotations

import logging
import warnings
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Feature Set for Extreme Classifiers (Phase 7 allowed predictors)
# ---------------------------------------------------------------------------

EXTREME_FEATURE_COLUMNS: List[str] = [
    # RAMP deterministic output (frozen, not a target leak)
    "ramp_prediction",
    "raw_nwp_rainfall",
    "global_ml_prediction",
    # NWP atmospheric predictors
    "u850",
    "v850",
    "mslp",
    "temperature",
    "relative_humidity",
    "precipitable_water",
    "cape",
    "geopotential_height",
    "wind_speed_850",
    "wind_direction_850",
    # Temporal
    "lead_time_hours",
    "day_of_year_sin",
    "day_of_year_cos",
    "valid_hour_sin",
    "valid_hour_cos",
    # Season
    "pre_monsoon",
    "monsoon",
    "post_monsoon",
    "winter",
    # Regime gating probabilities (allowed — produced by Phase 4, not from targets)
    "p_active_monsoon",
    "p_break_monsoon",
    "p_low_depression",
    "p_coastal",
    "p_orographic",
    "p_western_disturbance",
    "p_transition_other",
    "active_score",
    "break_score",
    "low_depression_score",
    "coastal_score",
    "orographic_score",
    "western_disturbance_score",
    "transition_score",
    "regime_confidence",
    "entropy",
    # Geography
    "latitude",
    "longitude",
    "elevation",
    "distance_to_coast",
]

# Columns that must NEVER appear in features — strict leakage guard
FORBIDDEN_IN_EXTREME_X: set = {
    "observed_rainfall_mm",
    "rainfall_occurrence",
    "heavy_rainfall",
    "very_heavy_rainfall",
    "extremely_heavy_rainfall",
    "rainfall_anomaly",
    "observation_quality_flag",
    "target_valid_time",
    "forecast_error",
    "forecast_error_mm",
    "rainfall_error",
}

# Minimum event count below which we flag sample_size_warning
MIN_EVENTS_WARNING = 50


class ExtremeThresholdClassifier:
    """
    Binary LightGBM classifier for a single IMD exceedance threshold.

    P(R > threshold | RAMP_prediction, regime_context, NWP_features)

    Calibration via Platt (sigmoid) scaling fitted on VALIDATION data only.
    """

    # LightGBM hyperparameters tuned for rare-event classification
    _LGBM_PARAMS: Dict[str, Any] = {
        "objective": "binary",
        "metric": ["binary_logloss", "auc"],
        "n_estimators": 400,
        "learning_rate": 0.05,
        "num_leaves": 31,
        "max_depth": 6,
        "min_child_samples": 10,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 0.1,
        "class_weight": "balanced",   # critical for rare extreme events
        "verbose": -1,
        "random_state": 42,
    }

    def __init__(
        self,
        threshold_mm: float,
        calibration_method: str = "sigmoid",
        n_bootstrap: int = 50,
    ) -> None:
        self.threshold_mm = threshold_mm
        self.calibration_method = calibration_method
        self.n_bootstrap = n_bootstrap
        self.is_fitted = False

        self._model: Any = None
        self._calibrator: Any = None
        self._feature_names: List[str] = []

        # Training statistics
        self.train_n_samples: int = 0
        self.train_n_events: int = 0
        self.train_event_rate: float = 0.0
        self.sample_size_warning: bool = False

        # Validation metrics
        self.val_brier_score: float = 0.0
        self.val_roc_auc: float = 0.0
        self.val_pr_auc: float = 0.0
        self.val_ece: float = 0.0

    # ------------------------------------------------------------------
    # Feature preparation
    # ------------------------------------------------------------------

    def _prepare_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """
        Select available EXTREME_FEATURE_COLUMNS from df.
        Enforces leakage guard — raises if any forbidden column is present.
        """
        cols_present = [c for c in df.columns if c in FORBIDDEN_IN_EXTREME_X]
        if cols_present:
            raise ValueError(
                f"[LEAKAGE VIOLATION] Forbidden columns detected in extreme classifier input: {cols_present}"
            )

        available = [c for c in EXTREME_FEATURE_COLUMNS if c in df.columns]
        X = df[available].copy()

        # Fill NaN with median (computed from calling code on train split only)
        for col in X.columns:
            if X[col].isna().any():
                X[col] = X[col].fillna(X[col].median())

        return X, available

    def _get_target(self, df: pd.DataFrame) -> np.ndarray:
        """
        Derive binary target from observed_rainfall_mm for training phase only.
        Uses threshold_mm comparison on the raw observation column.
        """
        if "observed_rainfall_mm" not in df.columns:
            raise ValueError("observed_rainfall_mm required for classifier training")
        return (df["observed_rainfall_mm"] > self.threshold_mm).astype(int).values

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def fit(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
    ) -> "ExtremeThresholdClassifier":
        """
        Train the threshold classifier.

        IMPORTANT:
          - train_df must contain both features and observed_rainfall_mm
          - val_df is used ONLY for calibration fitting and metric evaluation
          - Test data must NEVER be passed here
        """
        try:
            import lightgbm as lgb
            from sklearn.calibration import CalibratedClassifierCV
            from sklearn.linear_model import LogisticRegression
        except ImportError as e:
            raise ImportError(f"Phase 7 requires lightgbm and scikit-learn: {e}")

        # ── 1. Prepare training features ────────────────────────────────
        X_train, feat_names = self._prepare_features(train_df)
        y_train = self._get_target(train_df)

        self.train_n_samples = len(y_train)
        self.train_n_events = int(y_train.sum())
        self.train_event_rate = float(y_train.mean()) if len(y_train) > 0 else 0.0
        self.sample_size_warning = self.train_n_events < MIN_EVENTS_WARNING
        self._feature_names = feat_names

        if self.sample_size_warning:
            logger.warning(
                f"[PHASE7 SAMPLE WARNING] Threshold {self.threshold_mm}mm: "
                f"only {self.train_n_events} positive events in training set "
                f"(< {MIN_EVENTS_WARNING}). Probability estimates will be unreliable."
            )

        if self.train_n_events == 0:
            logger.warning(
                f"[PHASE7] No positive events for threshold {self.threshold_mm}mm. "
                "Classifier will output near-zero probabilities."
            )

        # ── 2. Fit LightGBM classifier ──────────────────────────────────
        params = dict(self._LGBM_PARAMS)

        # Adjust class weight for very rare events
        if self.train_n_events > 0 and self.train_event_rate < 0.02:
            neg_to_pos = (self.train_n_samples - self.train_n_events) / max(self.train_n_events, 1)
            params["scale_pos_weight"] = neg_to_pos
            params.pop("class_weight", None)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._model = lgb.LGBMClassifier(**params)
            self._model.fit(
                X_train,
                y_train,
                eval_set=[(self._prepare_features(val_df)[0], self._get_target(val_df))]
                if len(val_df) > 0 else None,
                callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(-1)]
                if len(val_df) > 0 else None,
            )

        # ── 3. Calibrate on VALIDATION data ────────────────────────────
        if len(val_df) > 0 and self.train_n_events > 0:
            X_val, _ = self._prepare_features(val_df)
            y_val = self._get_target(val_df)

            val_raw_probs = self._model.predict_proba(X_val)[:, 1]
            self._calibrator = self._fit_calibrator(val_raw_probs, y_val)

            # ── 4. Compute validation metrics ───────────────────────────
            val_cal_probs = self._apply_calibrator(val_raw_probs)
            self.val_brier_score = float(np.mean((val_cal_probs - y_val) ** 2))
            self.val_roc_auc = self._safe_roc_auc(y_val, val_cal_probs)
            self.val_pr_auc = self._safe_pr_auc(y_val, val_cal_probs)
            self.val_ece = self._compute_ece(y_val, val_cal_probs)
        else:
            self._calibrator = None

        self.is_fitted = True
        return self

    def _fit_calibrator(self, raw_probs: np.ndarray, y: np.ndarray) -> Any:
        """Fit Platt (sigmoid) or isotonic regression calibrator on validation data."""
        from sklearn.isotonic import IsotonicRegression
        from sklearn.linear_model import LogisticRegression

        if self.calibration_method == "sigmoid":
            # Platt scaling: logistic regression on raw model output logits
            lr = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000)
            lr.fit(raw_probs.reshape(-1, 1), y)
            return lr
        elif self.calibration_method == "isotonic":
            iso = IsotonicRegression(out_of_bounds="clip")
            iso.fit(raw_probs, y)
            return iso
        return None

    def _apply_calibrator(self, raw_probs: np.ndarray) -> np.ndarray:
        """Apply fitted calibrator to raw model probabilities."""
        if self._calibrator is None:
            return raw_probs

        if self.calibration_method == "sigmoid":
            return self._calibrator.predict_proba(raw_probs.reshape(-1, 1))[:, 1]
        elif self.calibration_method == "isotonic":
            return np.clip(self._calibrator.predict(raw_probs), 0.0, 1.0)
        return raw_probs

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict_proba_single(self, row: Dict[str, Any]) -> Tuple[float, float]:
        """
        Returns (raw_probability, calibrated_probability) for a single sample.
        The input dict must NOT contain any forbidden target columns.
        """
        if not self.is_fitted or self._model is None:
            return 0.0, self.train_event_rate

        df = pd.DataFrame([row])
        X, _ = self._prepare_features(df)

        # Align to training feature order
        missing = [c for c in self._feature_names if c not in X.columns]
        for c in missing:
            X[c] = 0.0
        X = X[self._feature_names]

        raw = float(self._model.predict_proba(X)[0, 1])
        calibrated = float(self._apply_calibrator(np.array([raw]))[0])
        return raw, np.clip(calibrated, 0.0, 1.0)

    def predict_proba_batch(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Returns (raw_probs, calibrated_probs) arrays of shape (n,).
        """
        if not self.is_fitted or self._model is None:
            n = len(df)
            base = self.train_event_rate
            return np.full(n, base), np.full(n, base)

        X, _ = self._prepare_features(df)
        missing = [c for c in self._feature_names if c not in X.columns]
        for c in missing:
            X[c] = 0.0
        X = X[self._feature_names]

        raw = self._model.predict_proba(X)[:, 1]
        cal = self._apply_calibrator(raw)
        return raw, np.clip(cal, 0.0, 1.0)

    def get_feature_importance(self, top_n: int = 10) -> Dict[str, float]:
        """Returns top-N feature importances (normalized gain)."""
        if not self.is_fitted or self._model is None:
            return {}
        importances = self._model.feature_importances_
        total = importances.sum()
        if total == 0:
            return {}
        normed = importances / total
        pairs = sorted(
            zip(self._feature_names, normed.tolist()),
            key=lambda x: x[1],
            reverse=True,
        )
        return {k: round(float(v), 4) for k, v in pairs[:top_n]}

    # ------------------------------------------------------------------
    # Metrics helpers
    # ------------------------------------------------------------------

    def _safe_roc_auc(self, y: np.ndarray, probs: np.ndarray) -> float:
        try:
            from sklearn.metrics import roc_auc_score
            if len(np.unique(y)) < 2:
                return 0.5
            return float(roc_auc_score(y, probs))
        except Exception:
            return 0.5

    def _safe_pr_auc(self, y: np.ndarray, probs: np.ndarray) -> float:
        try:
            from sklearn.metrics import average_precision_score
            if len(np.unique(y)) < 2:
                return float(y.mean())
            return float(average_precision_score(y, probs))
        except Exception:
            return float(y.mean())

    def _compute_ece(self, y: np.ndarray, probs: np.ndarray, n_bins: int = 10) -> float:
        """Expected Calibration Error (ECE) — weighted absolute bias across probability bins."""
        n = len(y)
        if n == 0:
            return 0.0
        ece = 0.0
        bins = np.linspace(0.0, 1.0, n_bins + 1)
        for lo, hi in zip(bins[:-1], bins[1:]):
            mask = (probs >= lo) & (probs < hi)
            if mask.sum() == 0:
                continue
            acc = float(y[mask].mean())
            conf = float(probs[mask].mean())
            ece += (mask.sum() / n) * abs(acc - conf)
        return round(ece, 4)

    def get_calibration_bins(self, y: np.ndarray, probs: np.ndarray, n_bins: int = 10) -> Dict[str, List]:
        """Reliability diagram data for API/frontend."""
        bins = np.linspace(0.0, 1.0, n_bins + 1)
        bin_conf, bin_acc, bin_counts = [], [], []
        for lo, hi in zip(bins[:-1], bins[1:]):
            mask = (probs >= lo) & (probs < hi)
            if mask.sum() == 0:
                continue
            bin_conf.append(round(float(probs[mask].mean()), 4))
            bin_acc.append(round(float(y[mask].mean()), 4))
            bin_counts.append(int(mask.sum()))
        return {"confidence": bin_conf, "accuracy": bin_acc, "counts": bin_counts}
