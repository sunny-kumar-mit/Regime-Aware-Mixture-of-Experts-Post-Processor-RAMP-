"""
RAMP Base Baseline Model Architecture
SIH26080 | Baseline Rainfall Post-Processing & Benchmarking
MoES / NCMRWF
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from ml.dataset.leakage_guard import LeakageGuard


class BaseBaselineModel(ABC):
    """
    Abstract base class for all global baseline rainfall post-processing models.
    Enforces physical non-negativity and Phase 5 baseline leakage isolation.
    """

    def __init__(self, name: str, version: str = "v1.0.0") -> None:
        self.name = name
        self.version = version
        self.is_fitted: bool = False
        self.fitted_split: Optional[str] = None
        self.metadata: Dict[str, Any] = {}

    def _validate_features(self, X: pd.DataFrame, feature_columns: Optional[List[str]] = None) -> None:
        """
        Ensures predictor columns contain neither ground-truth targets nor Phase 4 regime features.
        """
        guard = LeakageGuard()
        cols = feature_columns if feature_columns else list(X.columns)
        guard.audit_baseline_features(cols)

    @abstractmethod
    def fit(
        self,
        X: pd.DataFrame,
        y: np.ndarray | pd.Series,
        split_label: str = "TRAIN",
    ) -> "BaseBaselineModel":
        """Fits model strictly on training data."""
        pass

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generates continuous rainfall predictions in mm."""
        pass

    @staticmethod
    def enforce_physical_constraints(predictions: np.ndarray | List[float]) -> np.ndarray:
        """
        Enforces physical non-negativity: R_pred >= 0.0 mm.
        Does NOT clip extreme rainfall tails (e.g. preserves 204.5+ mm).
        """
        arr = np.asarray(predictions, dtype=np.float32)
        return np.maximum(0.0, arr)
