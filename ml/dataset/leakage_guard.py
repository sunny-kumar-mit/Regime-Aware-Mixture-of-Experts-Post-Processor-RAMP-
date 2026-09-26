"""
RAMP Data Leakage Protection Guard
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Enforces 10 strict data leakage invariants:
  1. Target variables are not in feature columns (X).
  2. Future observation timestamps are not used in predictors.
  3. Test-period statistics are not used for preprocessing.
  4. Climatology does not use future test data.
  5. Scalers are not fitted on test/validation data.
  6. Categorical mappings are not fitted on test data.
  7. Imputation statistics are not fitted on test data.
  8. Quantiles are not calculated using test data.
  9. Forecast error (actual - raw_nwp) is not used as a predictor.
  10. Observations are not used to create same-valid-time predictors.

CRITICAL BEHAVIOR:
  FAILS LOUDLY: Raises DataLeakageError if any leakage invariant is violated.
  Never merely logs a warning.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Set
import pandas as pd
from ml.schemas import LeakageReport


class DataLeakageError(Exception):
    """Raised whenever a data leakage invariant is violated."""
    pass


class TargetLeakageError(DataLeakageError):
    """Raised specifically when target variables leak into features."""
    pass


def audit_baseline_features(feature_columns: List[str]) -> None:
    """Module-level convenience auditor for baseline features."""
    guard = LeakageGuard()
    guard.audit_baseline_features(feature_columns)


def audit_ramp_features(feature_columns: List[str]) -> None:
    """Module-level convenience auditor for Phase 6 RAMP expert features."""
    guard = LeakageGuard()
    guard.audit_ramp_features(feature_columns)


def audit_real_data_features(feature_columns: List[str]) -> None:
    """Module-level convenience auditor for Phase 8 real-data predictor features."""
    guard = LeakageGuard()
    guard.audit_real_data_features(feature_columns)


class LeakageGuard:
    """
    Automated scientific audit engine checking for data leakage conditions.
    """

    TARGET_COLUMNS: Set[str] = {
        "observed_rainfall_mm",
        "rainfall_occurrence",
        "heavy_rainfall",
        "very_heavy_rainfall",
        "extremely_heavy_rainfall",
        "rainfall_anomaly",
        "observation_quality_flag",
        "target_valid_time",
    }

    FORBIDDEN_PREDICTOR_COLUMNS: Set[str] = {
        "forecast_error",
        "forecast_error_mm",
        "rainfall_error",
        "actual_rainfall",
        "obs_rainfall",
        "observation_rainfall",
    }

    REGIME_COLUMNS: Set[str] = {
        "regime_label",
        "regime_label_source",
        "regime_label_confidence",
        "regime_label_quality",
        "p_active_monsoon",
        "p_break_monsoon",
        "p_low_depression",
        "p_coastal",
        "p_orographic",
        "p_western_disturbance",
        "p_transition_other",
        "p_active",
        "p_break",
        "p_depression",
        "active_score",
        "break_score",
        "low_depression_score",
        "coastal_score",
        "orographic_score",
        "western_disturbance_score",
        "transition_score",
        "regime_confidence",
        "entropy",
    }

    def __init__(self) -> None:
        self.passed_checks: List[str] = []
        self.violations: List[str] = []

    def audit_features(self, feature_columns: List[str]) -> None:
        """
        Invariant 1 & 9: Verify no target variables or forecast error columns exist in feature set X.
        """
        for col in feature_columns:
            lower_col = col.lower()
            if col in self.TARGET_COLUMNS:
                err = f"Target variable '{col}' found in predictor feature columns X."
                self.violations.append(err)
                raise TargetLeakageError(f"[LEAKAGE VIOLATION] {err}")

            if lower_col in self.FORBIDDEN_PREDICTOR_COLUMNS or "forecast_error" in lower_col:
                err = f"Forecast error diagnostic '{col}' found in predictor feature columns X."
                self.violations.append(err)
                raise DataLeakageError(f"[LEAKAGE VIOLATION] {err}")

        self.passed_checks.append("Check 1 & 9: Target columns and forecast errors absent from X")

    def audit_baseline_features(self, feature_columns: List[str]) -> None:
        """
        Phase 5 Invariant: Verify baseline models are strictly GLOBAL.
        Neither target variables nor Phase 4 regime intelligence features may enter baseline X.
        """
        self.audit_features(feature_columns)

        for col in feature_columns:
            lower_col = col.lower()
            if (
                col in self.REGIME_COLUMNS
                or lower_col.startswith("p_")
                or "regime" in lower_col
                or lower_col.endswith("_score")
                or "entropy" in lower_col
            ):
                err = f"Regime feature '{col}' found in Phase 5 global baseline predictor feature columns X."
                self.violations.append(err)
                raise DataLeakageError(f"[LEAKAGE VIOLATION - REGIME LEAKAGE] {err}")

        self.passed_checks.append("Phase 5 Audit: Baseline features isolated from regime conditioning")

    def audit_ramp_features(self, feature_columns: List[str]) -> None:
        """
        Phase 6 Invariant: Verify RAMP expert predictor features.
        Target variables and forecast error columns must never enter expert feature set X.
        Future regime ground-truth labels are forbidden.
        """
        self.audit_features(feature_columns)

        for col in feature_columns:
            lower_col = col.lower()
            if "future_regime" in lower_col or "observed_regime" in lower_col or "target_regime" in lower_col:
                err = f"Target regime column '{col}' found in Phase 6 RAMP expert features X."
                self.violations.append(err)
                raise DataLeakageError(f"[LEAKAGE VIOLATION - TARGET REGIME LEAKAGE] {err}")

        self.passed_checks.append("Phase 6 Audit: RAMP expert features verified with zero target leakage")

    def audit_real_data_features(self, feature_columns: List[str]) -> None:
        """
        Phase 8 Invariant: Real-Data Predictor Leakage Guard.
        Strictly forbids:
          - future observed rainfall
          - future regime
          - observed regime
          - future forecast corrections
          - test labels
          - post-event variables
        Training target (observed_rainfall_mm) is allowed in dataset, but must NEVER enter X.
        """
        self.audit_features(feature_columns)

        forbidden_patterns = [
            ("future_observed", "Future observed rainfall"),
            ("future_rain", "Future rainfall observation"),
            ("future_regime", "Future regime label"),
            ("observed_regime", "Observed regime ground truth"),
            ("target_regime", "Target regime label"),
            ("ground_truth_regime", "Ground truth regime"),
            ("forecast_correction", "Future forecast correction"),
            ("future_bias", "Future bias correction"),
            ("future_error", "Future error term"),
            ("test_label", "Test set ground-truth label"),
            ("test_target", "Test target label"),
            ("post_event", "Post-event observed variable"),
        ]

        for col in feature_columns:
            lower_col = col.lower()
            for pattern, desc in forbidden_patterns:
                if pattern in lower_col:
                    err = f"{desc} '{col}' leaked into Phase 8 real-data predictor feature columns X."
                    self.violations.append(err)
                    raise DataLeakageError(f"[LEAKAGE VIOLATION - REAL DATA LEAKAGE] {err}")

        self.passed_checks.append("Phase 8 Audit: Real-data features verified with zero future/target/post-event contamination")


    def audit_temporal_alignment(
        self,
        df: pd.DataFrame,
        init_time_col: str = "forecast_initialization_time",
        valid_time_col: str = "forecast_valid_time",
        target_time_col: str = "target_valid_time",
    ) -> None:
        """
        Invariant 2 & 10: Verify observation timestamps match valid_time and do not exceed forecast horizon.
        """
        if init_time_col in df.columns and valid_time_col in df.columns:
            inits = pd.to_datetime(df[init_time_col], utc=True)
            valids = pd.to_datetime(df[valid_time_col], utc=True)
            if (valids < inits).any():
                err = "Found forecast_valid_time earlier than initialization_time (backward time travel)."
                self.violations.append(err)
                raise DataLeakageError(f"[LEAKAGE VIOLATION] {err}")

        if target_time_col in df.columns and valid_time_col in df.columns:
            targets = pd.to_datetime(df[target_time_col], utc=True)
            valids = pd.to_datetime(df[valid_time_col], utc=True)
            diffs = (targets - valids).abs()
            # Allow max 1 minute discrepancy from rounding
            if (diffs > pd.Timedelta(minutes=1)).any():
                err = "Observation target timestamp differs from forecast_valid_time."
                self.violations.append(err)
                raise DataLeakageError(f"[LEAKAGE VIOLATION] {err}")

        self.passed_checks.append("Check 2 & 10: Spatio-temporal alignment verified without future observation contamination")

    def audit_climatology(
        self,
        climatology_split: Optional[str],
        train_split_name: str = "TRAIN",
    ) -> None:
        """
        Invariant 4: Climatology baseline must be fitted strictly on the training period.
        """
        if climatology_split is None or climatology_split != train_split_name:
            err = (
                f"Climatology fitted on split '{climatology_split}' instead of "
                f"required training split '{train_split_name}'."
            )
            self.violations.append(err)
            raise DataLeakageError(f"[LEAKAGE VIOLATION] {err}")

        self.passed_checks.append("Check 4: Climatology fitted strictly on training data")

    def audit_preprocessing_manifest(self, manifest: Dict[str, Any]) -> None:
        """
        Invariants 3, 5, 6, 7, 8: Preprocessing parameters, scalers, imputers, and quantiles
        must be fitted strictly on the TRAIN partition.
        """
        fitted_split = manifest.get("fitted_on_split")
        if fitted_split != "TRAIN":
            err = (
                f"Preprocessing manifest indicates statistics were fitted on '{fitted_split}', "
                "not strictly on 'TRAIN'."
            )
            self.violations.append(err)
            raise DataLeakageError(f"[LEAKAGE VIOLATION] {err}")

        self.passed_checks.append("Checks 3, 5, 6, 7, 8: Preprocessing, scalers, and imputers fitted strictly on TRAIN")

    def generate_report(self) -> LeakageReport:
        """Constructs an auditable summary report of all checks performed."""
        return LeakageReport(
            status="FAIL" if self.violations else "PASS",
            checks_run=len(self.passed_checks) + len(self.violations),
            passed_checks=list(self.passed_checks),
            violations=list(self.violations),
            checked_at=datetime.now().isoformat(),
        )
