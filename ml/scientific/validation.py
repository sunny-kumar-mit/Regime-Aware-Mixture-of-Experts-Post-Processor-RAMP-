"""
RAMP Scientific Validation Engine
SIH26080 | Phase 10 | MoES / NCMRWF

Validates scientific data contracts, frozen model compatibility,
and ensures no leakage into explainability pipelines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

# Frozen model versions that MUST NOT be modified
FROZEN_MODEL_REGISTRY = {
    "regime": "regime_lgbm_v0.1.0",
    "mean_bias": "mean_bias_v1.0.0",
    "quantile_mapping": "quantile_mapping_v1.0.0",
    "global_ml": "global_ml_v1.0.0",
    "ramp": "ramp_v1.0.0",
    "extreme_prob": "extreme_prob_v1.0.0",
}

# Features that constitute leakage (must never enter explainability)
LEAKAGE_FEATURES = {
    "observed_rainfall_mm",
    "observed_rainfall",
    "target_rainfall",
    "target",
    "y_true",
    "future_regime",
    "future_observed_regime",
    "post_event_measurement",
    "future_bias_correction",
    "test_label",
    "future_observed_rainfall",
    "analysis_rainfall",
}

DATA_MODES = {"SYNTHETIC_DEMO", "REAL_OPERATIONAL", "HYBRID"}

SCIENTIFIC_CONTRACTS = {
    "PHASE_4": {"regime_probabilities", "dominant_regime", "entropy"},
    "PHASE_5": {"baseline_rmse", "baseline_mae", "baseline_csi"},
    "PHASE_6": {"ramp_prediction", "gate_weights", "expert_predictions"},
    "PHASE_7": {"rain_probability", "heavy_probability", "very_heavy_probability", "extreme_probability"},
    "PHASE_8": {"operational_rmse", "operational_mae", "data_mode"},
    "PHASE_9": {"rainfall_mm", "district_id", "coverage_fraction", "hotspot_rainfall_mm"},
}


@dataclass
class ValidationResult:
    passed: bool
    checks_run: int
    failed_checks: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def all_passed(self) -> bool:
        return self.passed and len(self.failed_checks) == 0


class ScientificValidator:
    """
    Scientific data contract validator for Phase 10.
    Ensures compatibility with Phases 4–9 and prevents frozen model tampering.
    """

    def validate_data_mode(self, data_mode: str) -> Tuple[bool, str]:
        if data_mode not in DATA_MODES:
            return False, f"Invalid data_mode '{data_mode}'. Must be one of {DATA_MODES}"
        return True, "ok"

    def validate_frozen_models(self, provided_versions: Dict[str, str]) -> Tuple[bool, List[str]]:
        """Validate that frozen model versions have not been tampered with."""
        errors = []
        for model_key, expected_version in FROZEN_MODEL_REGISTRY.items():
            if model_key in provided_versions:
                actual = provided_versions[model_key]
                if actual != expected_version:
                    errors.append(
                        f"FROZEN MODEL VIOLATION: '{model_key}' expected "
                        f"'{expected_version}', got '{actual}'"
                    )
        return len(errors) == 0, errors

    def check_leakage(self, feature_names: List[str]) -> Tuple[bool, List[str]]:
        """
        Checks for data leakage variables in feature set.
        If leakage is detected, STOP explanation generation.
        Returns (is_clean, leaking_features).
        """
        leaking = [f for f in feature_names if f.lower() in LEAKAGE_FEATURES]
        return len(leaking) == 0, leaking

    def validate_probability_bounds(self, probs: np.ndarray) -> Tuple[bool, str]:
        """Validate all probabilities are in [0, 1]."""
        if np.any(probs < 0.0) or np.any(probs > 1.0):
            bad = np.sum((probs < 0.0) | (probs > 1.0))
            return False, f"{bad} probability values outside [0,1]"
        return True, "ok"

    def validate_probability_monotonicity(
        self,
        p_rain: float,
        p_heavy: float,
        p_very_heavy: float,
        p_extreme: float,
        tol: float = 1e-4,
    ) -> Tuple[bool, str]:
        """
        Enforce: P(Rain) >= P(Heavy) >= P(VeryHeavy) >= P(Extreme)
        """
        violations = []
        if p_rain < p_heavy - tol:
            violations.append(f"P(Rain)={p_rain:.4f} < P(Heavy)={p_heavy:.4f}")
        if p_heavy < p_very_heavy - tol:
            violations.append(f"P(Heavy)={p_heavy:.4f} < P(VeryHeavy)={p_very_heavy:.4f}")
        if p_very_heavy < p_extreme - tol:
            violations.append(f"P(VeryHeavy)={p_very_heavy:.4f} < P(Extreme)={p_extreme:.4f}")
        return len(violations) == 0, "; ".join(violations) if violations else "ok"

    def validate_sample_size(self, n: int, min_n: int = 10) -> Tuple[str, str]:
        """
        Returns availability status based on sample count.
        'AVAILABLE', 'SAMPLE_LIMITED', or 'NOT_AVAILABLE'
        """
        if n >= min_n:
            return "AVAILABLE", f"n={n} >= min_n={min_n}"
        elif n > 0:
            return "SAMPLE_LIMITED", f"n={n} < min_n={min_n}"
        else:
            return "NOT_AVAILABLE", "n=0: no samples available"

    def validate_phase_compatibility(
        self, phase: str, provided_keys: set
    ) -> Tuple[bool, List[str]]:
        """Validates that required phase contract keys are available."""
        required = SCIENTIFIC_CONTRACTS.get(phase, set())
        missing = required - provided_keys
        if missing:
            return False, [f"Missing phase {phase} contract key: '{k}'" for k in missing]
        return True, []

    def full_scientific_validation(
        self,
        data_mode: str,
        feature_names: List[str],
        model_versions: Dict[str, str],
        n_samples: int,
        phase_data: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """Run full scientific validation battery."""
        checks = 0
        failed = []
        warnings = []

        # Check 1: Data mode
        checks += 1
        ok, msg = self.validate_data_mode(data_mode)
        if not ok:
            failed.append(msg)

        # Check 2: Leakage
        checks += 1
        clean, leaking = self.check_leakage(feature_names)
        if not clean:
            failed.append(f"LEAKAGE_DETECTED: {leaking}")

        # Check 3: Frozen models
        checks += 1
        ok, errs = self.validate_frozen_models(model_versions)
        if not ok:
            failed.extend(errs)

        # Check 4: Sample size warning
        checks += 1
        status, msg = self.validate_sample_size(n_samples)
        if status != "AVAILABLE":
            warnings.append(f"Sample availability: {status} — {msg}")

        # Check 5: Phase compatibility
        if phase_data:
            for phase_key, data_keys in phase_data.items():
                checks += 1
                ok, errs = self.validate_phase_compatibility(phase_key, set(data_keys))
                if not ok:
                    warnings.extend(errs)  # warnings, not hard failures, for missing phase data

        return ValidationResult(
            passed=len(failed) == 0,
            checks_run=checks,
            failed_checks=failed,
            warnings=warnings,
            metadata={
                "data_mode": data_mode,
                "n_samples": n_samples,
                "n_features": len(feature_names),
                "leakage_clean": clean,
            },
        )
