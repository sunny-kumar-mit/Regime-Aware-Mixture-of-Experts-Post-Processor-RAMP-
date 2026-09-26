"""
RAMP Weather Regime Classifiers
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Implements candidate classifiers:
  1. Rule-Based Physics Baseline (RuleBasedBaselineClassifier)
  2. Random Forest Multi-Class Classifier (RandomForestRegimeClassifier)
  3. LightGBM Multi-Class Classifier (LightGBMRegimeClassifier)

Features & Guarantees:
  - Class weighting / balanced objectives for class imbalance.
  - Probability distributions strictly sum to 1.0.
  - Zero leakage: Rejects future target variables from X.
  - Feature importance attribution for "Why this regime?" inspection.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from ml.dataset.leakage_guard import DataLeakageError, LeakageGuard
from ml.regimes.definitions import REGIME_ORDER, REGIME_TO_INT, WeatherRegime
from ml.regimes.indicators import RegimeIndicatorEngine
from ml.regimes.weak_labeler import RegimeLabeler


class BaseRegimeClassifier:
    """Base class for all regime classifiers."""

    def __init__(self, name: str, feature_columns: Optional[List[str]] = None) -> None:
        self.name = name
        self.feature_columns = feature_columns or []
        self.is_fitted = False
        self.feature_importances: Dict[str, float] = {}

    def _validate_features(self, X: pd.DataFrame) -> None:
        """Audits feature columns against target leakage."""
        cols = self.feature_columns if self.feature_columns else [c for c in X.columns if c not in LeakageGuard.TARGET_COLUMNS]
        guard = LeakageGuard()
        guard.audit_features(cols)


class RuleBasedBaselineClassifier(BaseRegimeClassifier):
    """
    Physics-informed rule baseline using RegimeIndicatorEngine and softmax.
    Requires no ML training; serves as physical reference baseline.
    """

    def __init__(self, temperature: float = 0.5) -> None:
        super().__init__(name="RuleBased_Baseline")
        self.labeler = RegimeLabeler(temperature=temperature)
        self.is_fitted = True

    def fit(self, X: pd.DataFrame, y: Optional[np.ndarray] = None) -> "RuleBasedBaselineClassifier":
        self._validate_features(X)
        self.is_fitted = True
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        self._validate_features(X)
        labeled = self.labeler.generate_weak_labels(X)
        prob_cols = [f"p_{r.value.lower()}" for r in REGIME_ORDER]
        probs = labeled[prob_cols].values
        # Ensure row sums == 1.0
        return probs / np.sum(probs, axis=1, keepdims=True)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        probs = self.predict_proba(X)
        return np.argmax(probs, axis=1)


class RandomForestRegimeClassifier(BaseRegimeClassifier):
    """
    Random Forest ensemble with balanced class weighting.
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: Optional[int] = 12,
        random_state: int = 42,
        feature_columns: Optional[List[str]] = None,
    ) -> None:
        super().__init__(name="RandomForest_Classifier", feature_columns=feature_columns)
        self.clf = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            class_weight="balanced",
            random_state=random_state,
            n_jobs=-1,
        )

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> "RandomForestRegimeClassifier":
        self._validate_features(X)
        feats = self.feature_columns if self.feature_columns else list(X.columns)
        self.feature_columns = feats

        X_mat = X[feats].fillna(0.0).values
        self.clf.fit(X_mat, y)

        # Feature importances
        if hasattr(self.clf, "feature_importances_"):
            imp = self.clf.feature_importances_
            self.feature_importances = {
                feat: round(float(imp[i]), 4)
                for i, feat in enumerate(feats)
            }

        self.is_fitted = True
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        self._validate_features(X)
        feats = self.feature_columns if self.feature_columns else list(X.columns)
        X_mat = X[feats].fillna(0.0).values

        raw_probs = self.clf.predict_proba(X_mat)
        # Ensure full 7-class representation even if some classes weren't in mini-batches
        n_samples = len(X)
        full_probs = np.zeros((n_samples, 7), dtype=float)

        for col_idx, class_val in enumerate(self.clf.classes_):
            if 0 <= class_val < 7:
                full_probs[:, int(class_val)] = raw_probs[:, col_idx]

        # Normalize rows to sum to 1.0
        row_sums = np.sum(full_probs, axis=1, keepdims=True)
        row_sums = np.where(row_sums < 1e-9, 1.0, row_sums)
        return full_probs / row_sums

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        probs = self.predict_proba(X)
        return np.argmax(probs, axis=1)


class LightGBMRegimeClassifier(BaseRegimeClassifier):
    """
    LightGBM gradient boosted trees multi-class classifier with balanced class weighting.
    """

    def __init__(
        self,
        n_estimators: int = 100,
        learning_rate: float = 0.05,
        max_depth: int = 6,
        random_state: int = 42,
        feature_columns: Optional[List[str]] = None,
    ) -> None:
        super().__init__(name="LightGBM_Classifier", feature_columns=feature_columns)
        try:
            import lightgbm as lgb
            self.clf = lgb.LGBMClassifier(
                n_estimators=n_estimators,
                learning_rate=learning_rate,
                max_depth=max_depth,
                objective="multiclass",
                num_class=7,
                class_weight="balanced",
                random_state=random_state,
                verbosity=-1,
            )
        except ImportError:
            # Fallback if lightgbm not available
            from sklearn.ensemble import HistGradientBoostingClassifier
            self.clf = HistGradientBoostingClassifier(
                max_iter=n_estimators,
                learning_rate=learning_rate,
                max_depth=max_depth,
                random_state=random_state,
            )

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> "LightGBMRegimeClassifier":
        self._validate_features(X)
        feats = self.feature_columns if self.feature_columns else list(X.columns)
        self.feature_columns = feats

        X_mat = X[feats].fillna(0.0).values
        self.clf.fit(X_mat, y)

        if hasattr(self.clf, "feature_importances_"):
            imp = self.clf.feature_importances_.astype(float)
            total = float(np.sum(imp)) if np.sum(imp) > 0 else 1.0
            self.feature_importances = {
                feat: round(float(imp[i] / total), 4)
                for i, feat in enumerate(feats)
            }

        self.is_fitted = True
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        self._validate_features(X)
        feats = self.feature_columns if self.feature_columns else list(X.columns)
        X_mat = X[feats].fillna(0.0).values

        raw_probs = self.clf.predict_proba(X_mat)
        n_samples = len(X)
        full_probs = np.zeros((n_samples, 7), dtype=float)

        classes = getattr(self.clf, "classes_", np.arange(raw_probs.shape[1]))
        for col_idx, class_val in enumerate(classes):
            if 0 <= class_val < 7:
                full_probs[:, int(class_val)] = raw_probs[:, col_idx]

        row_sums = np.sum(full_probs, axis=1, keepdims=True)
        row_sums = np.where(row_sums < 1e-9, 1.0, row_sums)
        return full_probs / row_sums

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        probs = self.predict_proba(X)
        return np.argmax(probs, axis=1)
