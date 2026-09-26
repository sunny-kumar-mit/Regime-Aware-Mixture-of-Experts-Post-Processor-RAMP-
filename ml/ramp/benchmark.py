"""
RAMP Benchmark Engine & Ablation Suite
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Executes comprehensive benchmarking of RAMP against Phase 5 baselines:
  RAW NWP vs MEAN BIAS vs QUANTILE MAPPING vs GLOBAL ML vs RAMP
"""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from ml.baselines.benchmark import BaselineBenchmarkEngine
from ml.baselines.diagnostics.lead_time_stratification import LeadTimeStratifiedEvaluator
from ml.baselines.diagnostics.regime_stratification import RegimeStratifiedEvaluator
from ml.baselines.diagnostics.spatial_evaluation import SpatialEvaluator
from ml.baselines.model_registry import BaselineModelRegistry
from ml.baselines.verification.bootstrap import BootstrapComparator
from ml.baselines.verification.fss import FSSCalculator
from ml.baselines.verification.metrics import (
    calculate_all_threshold_metrics,
    calculate_categorical_metrics_for_threshold,
    calculate_continuous_metrics,
)
from ml.ramp.gating import RegimeGatingEngine
from ml.ramp.inference import RAMPInferenceService
from ml.ramp.model import RAMPModel
from ml.ramp.model_registry import RAMPModelRegistry
from ml.regimes.definitions import REGIME_ORDER
from ml.regimes.inference import RegimeInferenceService
from ml.regimes.model_registry import RegimeModelRegistry


class RAMPBenchmarkEngine:
    """
    Standardized benchmark engine evaluating RAMP and ablations against Phase 5 baselines.
    """

    def __init__(
        self,
        dataset_dir: Optional[Path | str] = None,
        models_dir: Optional[Path | str] = None,
        baselines_dir: Optional[Path | str] = None,
        regimes_dir: Optional[Path | str] = None,
        data_mode: str = "SYNTHETIC_DEMO",
    ) -> None:
        self.dataset_dir = Path(dataset_dir) if dataset_dir else Path("./data/processed/training/ramp_dataset_v0.3.0")
        self.models_dir = Path(models_dir) if models_dir else Path("./data/models/ramp")
        self.baselines_dir = Path(baselines_dir) if baselines_dir else Path("./data/models/baselines")
        self.regimes_dir = Path(regimes_dir) if regimes_dir else Path("./data/models/regime")
        self.data_mode = data_mode

    def run_benchmark(self, model_id: str = "ramp_v1.0.0") -> Dict[str, Any]:
        """
        Runs full test-set evaluation across all 5 systems and generates all benchmark artifacts.
        """
        test_path = self.dataset_dir / "test.parquet"
        if not test_path.exists():
            raise FileNotFoundError(f"Test dataset not found at {test_path}")

        df_test = pd.read_parquet(test_path)
        y_obs = df_test["observed_rainfall_mm"].values
        n_test = len(df_test)

        # 1. Load Phase 4 & Phase 5 & Phase 6 models
        ramp_reg = RAMPModelRegistry(models_dir=self.models_dir)
        ramp_model, ramp_meta = ramp_reg.load_model(model_id, baselines_dir=self.baselines_dir)

        base_reg = BaselineModelRegistry(models_dir=self.baselines_dir)
        raw_nwp_m, _ = base_reg.load_model("raw_nwp_v1")
        mean_bias_m, _ = base_reg.load_model("mean_bias_v1")
        qmap_m, _ = base_reg.load_model("quantile_mapping_v1")
        global_ml_m, _ = base_reg.load_model("global_lgbm_v1")

        reg_reg = RegimeModelRegistry(models_dir=self.regimes_dir)
        reg_models = reg_reg.list_models()
        clf, cal, _ = reg_reg.load_model(reg_models[0].model_id)
        regime_service = RegimeInferenceService(classifier=clf, calibrator=cal)

        # 2. Compute predictions for all 5 systems on TEST
        eval_df = df_test.copy()
        eval_df["raw_nwp"] = raw_nwp_m.predict(df_test)
        eval_df["mean_bias"] = mean_bias_m.predict(df_test)
        eval_df["quantile_mapping"] = qmap_m.predict(df_test)
        eval_df["global_ml"] = global_ml_m.predict(df_test)

        # Compute gating probabilities for RAMP
        gate_matrix = np.zeros((n_test, len(REGIME_ORDER)), dtype=float)
        gating_records: List[Dict[str, Any]] = []

        for i in range(n_test):
            row_dict = df_test.iloc[i].to_dict()
            res = regime_service.predict_sample(row_dict)
            gw = RegimeGatingEngine.create_gate_weights(res["probabilities"])
            gate_matrix[i, :] = gw.as_array()

            gating_records.append({
                "sample_id": str(row_dict.get("sample_id", f"sample_{i}")),
                "top_regime": res["top_regime"],
                "top_probability": res["confidence"],
                "entropy": res["entropy"],
                "uncertainty": res["uncertainty_level"],
                "gate_weights": gw.as_dict(),
            })

        # Standard RAMP (Soft Gating)
        ramp_batch = ramp_model.predict_batch(df_test, gate_matrix, mode="soft_gating")
        eval_df["ramp"] = ramp_batch["ramp_prediction"].values

        # Ablations
        hard_batch = ramp_model.predict_batch(df_test, gate_matrix, mode="hard_argmax")
        uniform_batch = ramp_model.predict_batch(df_test, gate_matrix, mode="uniform_gating")

        eval_df["ramp_hard_gating"] = hard_batch["ramp_prediction"].values
        eval_df["ramp_uniform_gating"] = uniform_batch["ramp_prediction"].values

        # Assign inferred regime for diagnostic breakdown
        eval_df["regime_label"] = [rec["top_regime"] for rec in gating_records]

        # 3. Master Systems Evaluation
        systems = ["raw_nwp", "mean_bias", "quantile_mapping", "global_ml", "ramp"]
        overall_metrics: Dict[str, Any] = {}
        threshold_metrics: Dict[str, Any] = {}

        for sys_name in systems:
            preds = eval_df[sys_name].values
            overall_metrics[sys_name] = calculate_continuous_metrics(preds, y_obs)
            threshold_metrics[sys_name] = calculate_all_threshold_metrics(preds, y_obs)

        # 4. Master Benchmark Table
        benchmark_matrix: List[Dict[str, Any]] = []
        for sys_name in systems:
            cont = overall_metrics[sys_name]
            thresh = threshold_metrics[sys_name]
            benchmark_matrix.append({
                "model": sys_name,
                "rmse": cont["rmse"],
                "mae": cont["mae"],
                "mean_bias": cont["mean_bias"],
                "pearson_r": cont["pearson_r"],
                "rain_occurrence_csi": thresh["rain_occurrence"]["csi"],
                "heavy_rain_csi_64_5": thresh["heavy_rainfall"]["csi"],
                "heavy_rain_pod_64_5": thresh["heavy_rainfall"]["pod"],
                "heavy_rain_far_64_5": thresh["heavy_rainfall"]["far"],
                "heavy_rain_ets_64_5": thresh["heavy_rainfall"]["ets"],
                "very_heavy_csi_115_6": thresh["very_heavy_rainfall"]["csi"],
                "extremely_heavy_csi_204_5": thresh["extremely_heavy_rainfall"]["csi"],
            })

        # 5. Lead-Time Stratification
        lead_time_res = LeadTimeStratifiedEvaluator.evaluate(
            eval_df,
            model_names=systems,
            lead_time_col="lead_time_hours",
            obs_col="observed_rainfall_mm",
        )

        # 6. Regime-Stratified Diagnostics
        regime_evaluator = RegimeStratifiedEvaluator()
        regime_res = regime_evaluator.evaluate(
            eval_df,
            model_names=["raw_nwp", "global_ml", "ramp"],
            regime_col="regime_label",
            obs_col="observed_rainfall_mm",
        )

        # 7. Spatial Evaluation
        spatial_res = SpatialEvaluator.evaluate_grid_points(
            eval_df,
            model_names=["raw_nwp", "global_ml", "ramp"],
            lat_col="latitude",
            lon_col="longitude",
            obs_col="observed_rainfall_mm",
        )

        # 8. Paired Bootstrap Statistical Significance (RAMP vs Raw NWP, RAMP vs Global ML)
        comparator = BootstrapComparator(n_bootstraps=300, random_seed=42)
        bootstrap_comp = {
            "ramp_vs_raw_nwp": comparator.compare_continuous(
                eval_df["ramp"].values, eval_df["raw_nwp"].values, y_obs
            ),
            "ramp_vs_global_ml": comparator.compare_continuous(
                eval_df["ramp"].values, eval_df["global_ml"].values, y_obs
            ),
        }

        # 9. Ablation Study Comparison
        ablation_systems = {
            "A_global_ml_only": eval_df["global_ml"].values,
            "B_hard_regime_argmax": eval_df["ramp_hard_gating"].values,
            "C_soft_ramp_gating": eval_df["ramp"].values,
            "E_uniform_gating": eval_df["ramp_uniform_gating"].values,
        }
        ablation_table: List[Dict[str, Any]] = []
        for ab_name, ab_preds in ablation_systems.items():
            c_metrics = calculate_continuous_metrics(ab_preds, y_obs)
            t_metrics = calculate_all_threshold_metrics(ab_preds, y_obs)
            ablation_table.append({
                "ablation_tier": ab_name,
                "rmse": c_metrics["rmse"],
                "mae": c_metrics["mae"],
                "mean_bias": c_metrics["mean_bias"],
                "heavy_rain_csi_64_5": t_metrics["heavy_rainfall"]["csi"],
                "heavy_rain_pod_64_5": t_metrics["heavy_rainfall"]["pod"],
                "heavy_rain_ets_64_5": t_metrics["heavy_rainfall"]["ets"],
            })

        # Save all artifacts to data/models/ramp/{model_id}/
        target_dir = self.models_dir / model_id
        target_dir.mkdir(parents=True, exist_ok=True)

        benchmark_data = {
            "evaluation_timestamp": datetime.now().isoformat(),
            "data_mode": self.data_mode,
            "performance_notice": (
                "SYNTHETIC DEMONSTRATION ONLY — Real training data is not available. "
                "These benchmarks establish relative algorithm ladders under synthetic demonstration conditions."
            ),
            "dataset_version": "v0.3.0",
            "model_version": model_id,
            "test_sample_count": n_test,
            "benchmark_matrix": benchmark_matrix,
            "overall_metrics": overall_metrics,
            "threshold_metrics": threshold_metrics,
            "lead_time_metrics": lead_time_res["lead_time_diagnostics"],
            "regime_metrics": regime_res["regime_diagnostics"],
            "spatial_metrics": spatial_res,
            "bootstrap_significance": bootstrap_comp,
            "ablation_comparison": ablation_table,
        }

        # Write JSON files
        with open(target_dir / "ramp_benchmark.json", "w", encoding="utf-8") as f:
            json.dump(benchmark_data, f, indent=2)

        with open(target_dir / "ramp_metrics.json", "w", encoding="utf-8") as f:
            json.dump(overall_metrics, f, indent=2)

        with open(target_dir / "ramp_threshold_metrics.json", "w", encoding="utf-8") as f:
            json.dump(threshold_metrics, f, indent=2)

        with open(target_dir / "ramp_lead_time_metrics.json", "w", encoding="utf-8") as f:
            json.dump(lead_time_res["lead_time_diagnostics"], f, indent=2)

        with open(target_dir / "ramp_regime_metrics.json", "w", encoding="utf-8") as f:
            json.dump(regime_res["regime_diagnostics"], f, indent=2)

        with open(target_dir / "ramp_spatial_metrics.json", "w", encoding="utf-8") as f:
            json.dump(spatial_res, f, indent=2)

        with open(target_dir / "ramp_bootstrap.json", "w", encoding="utf-8") as f:
            json.dump(bootstrap_comp, f, indent=2)

        with open(target_dir / "ramp_ablation.json", "w", encoding="utf-8") as f:
            json.dump(ablation_table, f, indent=2)

        with open(target_dir / "gating_diagnostics.json", "w", encoding="utf-8") as f:
            json.dump({
                "sample_count": n_test,
                "high_uncertainty_samples": sum(1 for g in gating_records if g["uncertainty"] == "HIGH"),
                "mean_entropy": round(float(np.mean([g["entropy"] for g in gating_records])), 4),
                "samples": gating_records[:20],
            }, f, indent=2)

        # Generate RAMP_MODEL_CARD.md
        self._write_model_card(target_dir, benchmark_data)

        return benchmark_data

    def _write_model_card(self, target_dir: Path, data: Dict[str, Any]) -> None:
        """Generates RAMP_MODEL_CARD.md."""
        card_content = f"""# RAMP Model Card: Regime-Aware Mixture-of-Experts Post-Processor

**Model ID:** `ramp_v1.0.0`  
**Dataset Version:** `v0.3.0`  
**Data Mode:** `SYNTHETIC_DEMO`  
**Evaluation Notice:** `SYNTHETIC DEMONSTRATION ONLY — Real training data is not available.`  

---

## 1. Model Overview
RAMP (Regime-Aware Mixture-of-Experts Post-Processor) dynamically routes weather forecast corrections through 7 regime-specialized regression experts weighted by continuous, calibrated regime probabilities:
$$\\text{{RAMP}}(x) = \\sum_{{k=0}}^6 p_k(x) \\cdot \\text{{Expert}}_k(x)$$

## 2. Benchmark Summary (TEST Partition, N=63)
- **RAW NWP RMSE:** {data['overall_metrics']['raw_nwp']['rmse']:.2f} mm
- **Global ML RMSE:** {data['overall_metrics']['global_ml']['rmse']:.2f} mm
- **RAMP (MoE) RMSE:** {data['overall_metrics']['ramp']['rmse']:.2f} mm
- **Heavy Rain CSI (>64.5mm):** RAW={data['threshold_metrics']['raw_nwp']['heavy_rainfall']['csi']}, Global ML={data['threshold_metrics']['global_ml']['heavy_rainfall']['csi']}, RAMP={data['threshold_metrics']['ramp']['heavy_rainfall']['csi']}

## 3. Scientific Invariants
1. $p_k \\ge 0, \\sum p_k = 1.0$ (calibrated soft gating).
2. Physical non-negativity: $R \\ge 0.0$ mm.
3. Mathematical convexity: $\\min_k E_k \\le \\text{{RAMP}} \\le \\max_k E_k$.
4. Zero target leakage: future rainfall never enters feature set X or regime assignment.
"""
        with open(target_dir / "RAMP_MODEL_CARD.md", "w", encoding="utf-8") as f:
            f.write(card_content)
        with open(self.models_dir / "RAMP_MODEL_CARD.md", "w", encoding="utf-8") as f:
            f.write(card_content)
