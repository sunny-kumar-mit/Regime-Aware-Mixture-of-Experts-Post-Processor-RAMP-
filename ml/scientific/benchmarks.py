"""
RAMP Model Benchmark Comparison — Phase 10
SIH26080 | MoES / NCMRWF

Neutral comparison tables across 6 forecast systems.
Uses factual labels only: LOWER_RMSE, HIGHER_CSI, NOT_SIGNIFICANT, SAMPLE_LIMITED.
Never uses 'winner', 'best model', or subjective rankings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ml.scientific.verification import ScientificVerificationEngine, ContinuousMetrics
from ml.scientific.thresholds import ThresholdVerificationEngine, ThresholdMetrics
from ml.scientific.lead_time import LeadTimeVerification
from ml.scientific.regimes import RegimeStratifiedVerification
from ml.scientific.significance import BootstrapSignificanceEngine, BootstrapResult
from ml.scientific.calibration import CalibrationAnalyzer


class ModelBenchmarkComparison:
    """
    Consolidated benchmark comparison across all 6 RAMP systems.
    Produces neutral, factual comparison tables.
    """

    MODELS = ["RAW_NWP", "MEAN_BIAS", "QUANTILE_MAPPING", "GLOBAL_ML", "RAMP_MOE", "RAMP_EXTREME"]
    MODEL_VERSIONS = {
        "RAW_NWP": "nwp_raw",
        "MEAN_BIAS": "mean_bias_v1.0.0",
        "QUANTILE_MAPPING": "quantile_mapping_v1.0.0",
        "GLOBAL_ML": "global_ml_v1.0.0",
        "RAMP_MOE": "ramp_v1.0.0",
        "RAMP_EXTREME": "extreme_prob_v1.0.0",
    }

    def __init__(self, data_mode: str = "SYNTHETIC_DEMO", random_seed: int = 42):
        self.data_mode = data_mode
        self.random_seed = random_seed
        self.verif_engine = ScientificVerificationEngine(data_mode=data_mode, random_seed=random_seed)
        self.threshold_engine = ThresholdVerificationEngine(data_mode=data_mode, random_seed=random_seed)
        self.lt_engine = LeadTimeVerification(data_mode=data_mode, random_seed=random_seed)
        self.regime_engine = RegimeStratifiedVerification(data_mode=data_mode, random_seed=random_seed)
        self.bootstrap_engine = BootstrapSignificanceEngine(data_mode=data_mode, random_seed=random_seed)
        self.calib_engine = CalibrationAnalyzer(data_mode=data_mode, random_seed=random_seed)

    def full_benchmark(self) -> Dict[str, Any]:
        """Run complete benchmark across all metrics and verification types."""
        # Continuous metrics
        continuous = self.verif_engine.compute_all_continuous_metrics()
        comparison_table = self.verif_engine.compute_neutral_comparison_table(continuous)

        # Threshold metrics
        threshold_results = self.threshold_engine.compute_all_thresholds()
        threshold_table = self.threshold_engine.flat_table(threshold_results)

        # Lead-time curves
        lead_time_curves = self.lt_engine.compute_lead_time_curves()
        lead_time_table = self.lt_engine.flat_table(lead_time_curves)

        # Regime stratification
        regime_metrics = self.regime_engine.compute_synthetic_regime_metrics()
        regime_table = self.regime_engine.regime_comparison_table(regime_metrics)

        # Bootstrap significance (RAMP_MOE vs RAW_NWP)
        bootstrap_results = self.bootstrap_engine.run_pairwise_battery()

        # Calibration
        calibration = self.calib_engine.analyze_all_thresholds()
        calibration_table = {str(thr): m.to_dict() for thr, m in calibration.items()}

        return {
            "benchmark_version": "scientific_v1.0.0",
            "data_mode": self.data_mode,
            "models_evaluated": self.MODELS,
            "n_models": len(self.MODELS),
            "continuous_metrics": comparison_table,
            "threshold_metrics": threshold_table,
            "lead_time_curves": lead_time_table,
            "regime_metrics": regime_table,
            "bootstrap_comparisons": [r.to_dict() for r in bootstrap_results],
            "calibration_analysis": calibration_table,
            "scientific_note": (
                "REAL IMD/NCMRWF OBSERVATIONAL ARCHIVES ARE NOT CURRENTLY MOUNTED. "
                "All metrics derived from synthetic test partition, labeled SYNTHETIC_DEMO."
            ),
        }

    def summary_table(self) -> List[Dict[str, Any]]:
        """Quick summary table: model, rmse, mae, csi_rain."""
        continuous = self.verif_engine.compute_all_continuous_metrics()
        threshold_results = self.threshold_engine.compute_all_thresholds()

        rows = []
        for model in self.MODELS:
            cm = continuous.get(model)
            threshold_list = threshold_results.get(model, [])
            rain_t = next((t for t in threshold_list if t.threshold_mm == 0.1), None)

            rows.append({
                "model": model,
                "model_version": self.MODEL_VERSIONS.get(model, "N/A"),
                "n_samples": cm.n_samples if cm else 0,
                "rmse": cm.rmse if cm else None,
                "mae": cm.mae if cm else None,
                "bias": cm.bias if cm else None,
                "pearson_r": cm.pearson_r if cm else None,
                "csi_rain": rain_t.contingency.csi if (rain_t and rain_t.contingency) else None,
                "pod_rain": rain_t.contingency.pod if (rain_t and rain_t.contingency) else None,
                "far_rain": rain_t.contingency.far if (rain_t and rain_t.contingency) else None,
                "availability": cm.availability_status if cm else "NOT_AVAILABLE",
                "data_mode": self.data_mode,
            })
        return rows
