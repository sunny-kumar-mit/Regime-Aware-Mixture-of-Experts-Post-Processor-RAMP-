"""
Phase 7 Extreme Rainfall Probability Engine
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Orchestrates:
  1. Feature construction from RAMP predictions + NWP context
  2. Four independent threshold classifiers (0.1, 64.5, 115.6, 204.5 mm)
  3. Monotonicity reconciliation via Pool Adjacent Violators
  4. Risk index and IMD warning computation
  5. Evaluation suite (Brier, PR-AUC, ROC-AUC, ECE, calibration bins)

FROZEN: ramp_v1.0.0 — RAMP outputs are inputs, not retrained.
DATA MODE: SYNTHETIC_DEMO — all outputs carry honesty flags.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from ml.extreme_probability.classifier import (
    ExtremeThresholdClassifier,
    EXTREME_FEATURE_COLUMNS,
    FORBIDDEN_IN_EXTREME_X,
)
from ml.extreme_probability.reconciler import MonotonicProbabilityReconciler, THRESHOLD_KEYS
from ml.extreme_probability.schemas import (
    ExtremeProbabilityRecord,
    ExtremeThreshold,
    ProbabilityThresholdResult,
    ExtremeModelMetadata,
    ExtremeEngineStatus,
    ExtremeEvaluationSuite,
    BrierSkillScore,
    CalibrationDiagnostic,
    PRCurveData,
    IMD_THRESHOLDS,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Risk classification
# ---------------------------------------------------------------------------

def _compute_composite_risk(probs: List[float]) -> Tuple[float, str, str]:
    """
    Compute composite risk index from [p_trace, p_heavy, p_very_heavy, p_extreme].

    Risk = weighted combination emphasizing higher thresholds.
    Returns (index ∈ [0,1], category, imd_warning).
    """
    weights = [0.10, 0.30, 0.35, 0.25]
    idx = sum(w * p for w, p in zip(weights, probs))
    idx = round(float(np.clip(idx, 0.0, 1.0)), 4)

    p_extreme = probs[3]
    p_very_heavy = probs[2]
    p_heavy = probs[1]

    if p_extreme >= 0.25:
        cat, warn = "EXTREME", "RED"
    elif p_very_heavy >= 0.30 or p_extreme >= 0.10:
        cat, warn = "SEVERE", "RED"
    elif p_heavy >= 0.35 or p_very_heavy >= 0.15:
        cat, warn = "HIGH", "ORANGE"
    elif p_heavy >= 0.15 or p_very_heavy >= 0.05:
        cat, warn = "MODERATE", "YELLOW"
    else:
        cat, warn = "LOW", "NONE"

    return idx, cat, warn


class ExtremeRainfallProbabilityEngine:
    """
    Regime-Aware Extreme Rainfall Probability Engine.

    Provides calibrated P(R > T | RAMP, regime, NWP) for 4 IMD thresholds.
    Monotonicity P(R>0.1) >= P(R>64.5) >= P(R>115.6) >= P(R>204.5) is
    enforced by the Pool Adjacent Violators reconciler after all classifiers.
    """

    THRESHOLDS = [0.1, 64.5, 115.6, 204.5]
    VERSION = "extreme_v1.0.0"

    def __init__(
        self,
        calibration_method: str = "sigmoid",
        data_mode: str = "SYNTHETIC_DEMO",
    ) -> None:
        self.calibration_method = calibration_method
        self.data_mode = data_mode
        self.reconciler = MonotonicProbabilityReconciler()

        self._classifiers: Dict[float, ExtremeThresholdClassifier] = {
            t: ExtremeThresholdClassifier(
                threshold_mm=t,
                calibration_method=calibration_method,
            )
            for t in self.THRESHOLDS
        }

        self._is_fitted = False
        self._trained_at: Optional[str] = None

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def fit(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
    ) -> "ExtremeRainfallProbabilityEngine":
        """
        Train all four threshold classifiers.

        Strictly:
          - train_df used for LightGBM model fitting
          - val_df used ONLY for calibration + metric evaluation
          - Neither may contain FORBIDDEN_IN_EXTREME_X at inference columns
            (observed_rainfall_mm IS required for target construction but must
             be stripped before predict_proba calls)

        Args:
            train_df: DataFrame with feature columns + observed_rainfall_mm (target construction)
            val_df:   DataFrame with feature columns + observed_rainfall_mm (calibration only)
        """
        logger.info("[PHASE7] Training ExtremeRainfallProbabilityEngine on %d train / %d val samples",
                    len(train_df), len(val_df))

        for threshold in self.THRESHOLDS:
            logger.info("[PHASE7] Fitting classifier for threshold=%.1f mm ...", threshold)
            clf = self._classifiers[threshold]
            clf.fit(train_df, val_df)
            logger.info(
                "[PHASE7] threshold=%.1f mm | n_events=%d | event_rate=%.4f | "
                "val_brier=%.4f | val_roc_auc=%.4f | val_pr_auc=%.4f | val_ece=%.4f",
                threshold,
                clf.train_n_events,
                clf.train_event_rate,
                clf.val_brier_score,
                clf.val_roc_auc,
                clf.val_pr_auc,
                clf.val_ece,
            )
            if clf.sample_size_warning:
                logger.warning(
                    "[PHASE7 WARNING] threshold=%.1f mm has fewer than %d events in training. "
                    "SYNTHETIC DEMONSTRATION ONLY.",
                    threshold, 50
                )

        self._is_fitted = True
        self._trained_at = datetime.utcnow().isoformat() + "Z"
        return self

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict_sample(
        self,
        row: Dict[str, Any],
    ) -> ExtremeProbabilityRecord:
        """
        Full Phase 7 inference pipeline on a single sample.

        Expected keys in `row`:
          - ramp_prediction (mm) — from frozen ramp_v1.0.0
          - raw_nwp_rainfall (mm)
          - top_regime (str)
          - regime_confidence (float)
          - NWP atmospheric features
          - temporal/seasonal/spatial features
          - regime gating probabilities (p_active_monsoon, etc.)

        FORBIDDEN in `row`: observed_rainfall_mm and any target columns.
        """
        if not self._is_fitted:
            return self._synthetic_demo_record(row)

        # Collect raw + calibrated probabilities
        raw_probs = []
        cal_probs = []

        for t in self.THRESHOLDS:
            clf = self._classifiers[t]
            raw_p, cal_p = clf.predict_proba_single(row)
            raw_probs.append(raw_p)
            cal_probs.append(cal_p)

        # Enforce monotonicity
        reconciled, violated, n_corr = self.reconciler.reconcile_vector(cal_probs)

        p_trace, p_heavy, p_vh, p_extreme = reconciled

        # Composite risk
        risk_idx, risk_cat, imd_warn = _compute_composite_risk(reconciled)

        # Build per-threshold detail
        threshold_results = []
        for i, t in enumerate(self.THRESHOLDS):
            clf = self._classifiers[t]
            thr_enum = ExtremeThreshold(str(t))
            threshold_results.append(ProbabilityThresholdResult(
                threshold_mm=t,
                threshold_label=thr_enum.label,
                imd_warning_color=thr_enum.imd_warning,
                raw_probability=round(raw_probs[i], 4),
                calibrated_probability=round(reconciled[i], 4),
                calibration_method=self.calibration_method,
                top_features=clf.get_feature_importance(top_n=5),
                train_event_rate=clf.train_event_rate,
                train_n_events=clf.train_n_events,
                train_n_total=clf.train_n_samples,
                sample_size_warning=clf.sample_size_warning,
            ))

        return ExtremeProbabilityRecord(
            sample_id=str(row.get("sample_id", "sample_000")),
            forecast_valid_time=str(row.get("forecast_valid_time", "2026-07-01T00:00:00Z")),
            latitude=float(row.get("latitude", 20.0)),
            longitude=float(row.get("longitude", 78.0)),
            lead_time_hours=int(row.get("lead_time_hours", 24)),
            ramp_prediction_mm=float(row.get("ramp_prediction", 0.0)),
            raw_nwp_prediction_mm=float(row.get("raw_nwp_rainfall", 0.0)),
            top_regime=str(row.get("top_regime", "UNKNOWN")),
            regime_confidence=float(row.get("regime_confidence", 0.0)),
            p_trace=round(p_trace, 4),
            p_heavy=round(p_heavy, 4),
            p_very_heavy=round(p_vh, 4),
            p_extreme=round(p_extreme, 4),
            threshold_results=threshold_results,
            monotonicity_satisfied=not violated,
            monotonicity_corrections_applied=n_corr,
            composite_risk_index=risk_idx,
            risk_category=risk_cat,
            imd_warning_recommendation=imd_warn,
            model_version=self.VERSION,
            data_mode=self.data_mode,
        )

    def predict_batch(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Batch probability prediction — returns df augmented with probability columns.
        Applies monotonicity reconciliation per row.
        """
        if not self._is_fitted:
            df = df.copy()
            for key, t in zip(THRESHOLD_KEYS, self.THRESHOLDS):
                df[key] = self._classifiers[t].train_event_rate
            return df

        raw_matrix = np.zeros((len(df), len(self.THRESHOLDS)))
        cal_matrix = np.zeros((len(df), len(self.THRESHOLDS)))

        for i, t in enumerate(self.THRESHOLDS):
            clf = self._classifiers[t]
            raw_col, cal_col = clf.predict_proba_batch(df)
            raw_matrix[:, i] = raw_col
            cal_matrix[:, i] = cal_col

        reconciled, total_corrections = self.reconciler.reconcile_batch(cal_matrix)

        out = df.copy()
        for i, key in enumerate(THRESHOLD_KEYS):
            out[key] = reconciled[:, i]

        out["monotonicity_corrections"] = total_corrections
        return out

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        test_df: pd.DataFrame,
    ) -> ExtremeEvaluationSuite:
        """
        Evaluate engine on a held-out test set.
        test_df must contain observed_rainfall_mm for target derivation.
        """
        if "observed_rainfall_mm" not in test_df.columns:
            raise ValueError("evaluate() requires observed_rainfall_mm in test_df")

        brier_scores = []
        calibration_diagnostics = []
        pr_curves = []
        roc_aucs = {}

        for t in self.THRESHOLDS:
            clf = self._classifiers[t]
            y = (test_df["observed_rainfall_mm"] > t).astype(int).values

            _, cal_probs = clf.predict_proba_batch(test_df)

            # Monotonicity not needed for per-threshold evaluation
            brier = float(np.mean((cal_probs - y) ** 2))
            brier_ref = float(np.mean((y.mean() - y) ** 2))
            bss = 1.0 - brier / max(brier_ref, 1e-10)

            brier_scores.append(BrierSkillScore(
                threshold_mm=t,
                brier_score=round(brier, 4),
                brier_reference=round(brier_ref, 4),
                brier_skill_score=round(bss, 4),
                interpretation="BSS>0 = better than climatology; BSS<0 = worse",
            ))

            # ECE and calibration bins
            ece = clf._compute_ece(y, cal_probs)
            bins = clf.get_calibration_bins(y, cal_probs)
            calibration_diagnostics.append(CalibrationDiagnostic(
                threshold_mm=t,
                bin_confidence=bins["confidence"],
                bin_accuracy=bins["accuracy"],
                bin_counts=bins["counts"],
                expected_calibration_error=ece,
            ))

            # PR curve
            pr_data = self._compute_pr_curve(y, cal_probs, t)
            pr_curves.append(pr_data)

            # ROC AUC
            roc_aucs[str(t)] = clf._safe_roc_auc(y, cal_probs)

        # Overall monotonicity violation rate on test set
        probs_batch = self.predict_batch(test_df)
        mono_cols = [probs_batch[k].values for k in THRESHOLD_KEYS]
        violations = 0
        n = len(test_df)
        for i in range(len(THRESHOLD_KEYS) - 1):
            violations += int(np.sum(mono_cols[i] < mono_cols[i + 1] - 1e-8))
        mono_violation_rate = round(violations / max(n, 1), 4)

        return ExtremeEvaluationSuite(
            data_mode=self.data_mode,
            n_test_samples=n,
            brier_scores=brier_scores,
            calibration_diagnostics=calibration_diagnostics,
            pr_curves=pr_curves,
            roc_auc_per_threshold={k: round(v, 4) for k, v in roc_aucs.items()},
            monotonicity_violation_rate=mono_violation_rate,
        )

    def _compute_pr_curve(
        self, y: np.ndarray, probs: np.ndarray, threshold_mm: float
    ) -> PRCurveData:
        try:
            from sklearn.metrics import precision_recall_curve, average_precision_score
            precision, recall, _ = precision_recall_curve(y, probs)
            ap = float(average_precision_score(y, probs)) if len(np.unique(y)) > 1 else float(y.mean())
            return PRCurveData(
                threshold_mm=threshold_mm,
                precision=[round(float(p), 4) for p in precision[:50]],
                recall=[round(float(r), 4) for r in recall[:50]],
                pr_auc=round(ap, 4),
                average_precision=round(ap, 4),
                baseline_precision=round(float(y.mean()), 4),
            )
        except Exception:
            return PRCurveData(
                threshold_mm=threshold_mm,
                baseline_precision=round(float(y.mean()), 4) if len(y) > 0 else 0.0,
            )

    # ------------------------------------------------------------------
    # Status & metadata
    # ------------------------------------------------------------------

    def get_status(self) -> ExtremeEngineStatus:
        warnings_list = []
        for t in self.THRESHOLDS:
            clf = self._classifiers[t]
            if clf.sample_size_warning:
                warnings_list.append(
                    f"Threshold {t}mm: only {clf.train_n_events} events in training set"
                )

        return ExtremeEngineStatus(
            engine_version=self.VERSION,
            ramp_source_version="ramp_v1.0.0",
            data_mode=self.data_mode,
            n_thresholds=len(self.THRESHOLDS),
            thresholds=self.THRESHOLDS,
            models_status={str(t): self._classifiers[t].is_fitted for t in self.THRESHOLDS},
            all_fitted=self._is_fitted,
            monotonicity_enforced=True,
            calibration_applied=True,
            last_trained_at=self._trained_at,
            operational=self._is_fitted,
            warnings=warnings_list,
        )

    def get_model_metadata(self) -> List[ExtremeModelMetadata]:
        meta = []
        for t in self.THRESHOLDS:
            clf = self._classifiers[t]
            thr_enum = ExtremeThreshold(str(t))
            meta.append(ExtremeModelMetadata(
                threshold_mm=t,
                threshold_label=thr_enum.label,
                model_type="LightGBM",
                version=self.VERSION,
                calibration_method=self.calibration_method,
                is_fitted=clf.is_fitted,
                train_n_samples=clf.train_n_samples,
                train_n_events=clf.train_n_events,
                train_event_rate=round(clf.train_event_rate, 6),
                val_brier_score=round(clf.val_brier_score, 4),
                val_roc_auc=round(clf.val_roc_auc, 4),
                val_pr_auc=round(clf.val_pr_auc, 4),
                val_ece=round(clf.val_ece, 4),
                sample_size_warning=clf.sample_size_warning,
                feature_count=len(clf._feature_names),
                feature_names=clf._feature_names,
            ))
        return meta

    # ------------------------------------------------------------------
    # Synthetic demo record (unfitted engine fallback)
    # ------------------------------------------------------------------

    def _synthetic_demo_record(self, row: Dict[str, Any]) -> ExtremeProbabilityRecord:
        """
        Returns a physics-aware synthetic probability vector when the engine
        has not been fitted (synthetic demonstration mode).

        Uses RAMP prediction magnitude and regime context for plausible
        but clearly flagged synthetic outputs.
        """
        ramp_pred = float(row.get("ramp_prediction", 0.0))
        raw_nwp = float(row.get("raw_nwp_rainfall", 0.0))
        top_regime = str(row.get("top_regime", "UNKNOWN"))
        reg_conf = float(row.get("regime_confidence", 0.5))

        # Physics-aware synthetic probability ladder
        # Based on NWP rainfall magnitude and regime
        regime_boost = {
            "ACTIVE_MONSOON": 1.4,
            "LOW_DEPRESSION": 1.6,
            "COASTAL": 1.5,
            "OROGRAPHIC": 1.3,
            "BREAK_MONSOON": 0.6,
            "WESTERN_DISTURBANCE": 0.9,
            "TRANSITION_OTHER": 1.0,
        }.get(top_regime.upper(), 1.0)

        base = np.clip(ramp_pred / 250.0, 0.0, 1.0) * regime_boost

        p_trace = round(np.clip(base * 3.0 + 0.05, 0.0, 1.0), 4)
        p_heavy = round(np.clip(base * 1.5, 0.0, 1.0), 4)
        p_vh = round(np.clip(base * 0.8, 0.0, 1.0), 4)
        p_ext = round(np.clip(base * 0.3, 0.0, 1.0), 4)

        # Reconcile for monotonicity
        vec, _, n_corr = self.reconciler.reconcile_vector([p_trace, p_heavy, p_vh, p_ext])
        p_trace, p_heavy, p_vh, p_ext = vec

        risk_idx, risk_cat, imd_warn = _compute_composite_risk([p_trace, p_heavy, p_vh, p_ext])

        threshold_results = []
        for t_enum, prob in zip(IMD_THRESHOLDS, [p_trace, p_heavy, p_vh, p_ext]):
            threshold_results.append(ProbabilityThresholdResult(
                threshold_mm=t_enum.float_value,
                threshold_label=t_enum.label,
                imd_warning_color=t_enum.imd_warning,
                raw_probability=prob,
                calibrated_probability=prob,
                calibration_method="none",
                top_features={},
                train_event_rate=0.0,
                train_n_events=0,
                train_n_total=0,
                sample_size_warning=True,
            ))

        return ExtremeProbabilityRecord(
            sample_id=str(row.get("sample_id", "sample_000")),
            forecast_valid_time=str(row.get("forecast_valid_time", "2026-07-01T00:00:00Z")),
            latitude=float(row.get("latitude", 20.0)),
            longitude=float(row.get("longitude", 78.0)),
            lead_time_hours=int(row.get("lead_time_hours", 24)),
            ramp_prediction_mm=float(ramp_pred),
            raw_nwp_prediction_mm=float(raw_nwp),
            top_regime=top_regime,
            regime_confidence=reg_conf,
            p_trace=p_trace,
            p_heavy=p_heavy,
            p_very_heavy=p_vh,
            p_extreme=p_ext,
            threshold_results=threshold_results,
            monotonicity_satisfied=True,
            monotonicity_corrections_applied=n_corr,
            composite_risk_index=risk_idx,
            risk_category=risk_cat,
            imd_warning_recommendation=imd_warn,
            model_version=self.VERSION,
            data_mode="SYNTHETIC_DEMO",
        )
