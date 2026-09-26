"""
RAMP Scientific Report Generator — Phase 10
SIH26080 | MoES / NCMRWF

Generates verification, calibration, regime, lead-time, spatial, and
explainability reports in JSON and Markdown formats.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from ml.scientific.benchmarks import ModelBenchmarkComparison
from ml.scientific.case_study import CaseStudyReplayEngine
from ml.scientific.explainability import ExplainabilityEngine
from ml.scientific.expert_analysis import ExpertGatingAnalyzer
from ml.scientific.failure_analysis import FailureAnalysisEngine
from ml.scientific.registry import ScientificRegistry, SCIENTIFIC_VERSION, REPORT_DIR, EXPORT_DIR
from ml.scientific.spatial import SpatialVerificationEngine

import numpy as np


def _default_serializer(o: Any) -> Any:
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(f"Object of type {type(o)} is not JSON serializable")


class ScientificReportGenerator:
    """
    Generates comprehensive scientific reports for Phase 10.
    Outputs: JSON exports + Markdown summary report.
    """

    def __init__(self, data_mode: str = "SYNTHETIC_DEMO", random_seed: int = 42):
        self.data_mode = data_mode
        self.random_seed = random_seed
        self.registry = ScientificRegistry(data_mode=data_mode)
        self.benchmark = ModelBenchmarkComparison(data_mode=data_mode, random_seed=random_seed)
        self.case_engine = CaseStudyReplayEngine(data_mode=data_mode, random_seed=random_seed)
        self.explain_engine = ExplainabilityEngine(data_mode=data_mode, random_seed=random_seed)
        self.expert_analyzer = ExpertGatingAnalyzer(data_mode=data_mode, random_seed=random_seed)
        self.failure_engine = FailureAnalysisEngine(data_mode=data_mode, random_seed=random_seed)
        self.spatial_engine = SpatialVerificationEngine(data_mode=data_mode, random_seed=random_seed)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    def _write_json(self, name: str, data: Any) -> Path:
        path = REPORT_DIR / name
        path.write_text(
            json.dumps(data, indent=2, default=_default_serializer),
            encoding="utf-8"
        )
        return path

    def _write_export_json(self, name: str, data: Any) -> Path:
        path = EXPORT_DIR / name
        path.write_text(
            json.dumps(data, indent=2, default=_default_serializer),
            encoding="utf-8"
        )
        return path

    def _write_csv(self, name: str, rows: list) -> Optional[Path]:
        if not rows:
            return None
        path = EXPORT_DIR / name
        headers = list(rows[0].keys())
        lines = [",".join(str(h) for h in headers)]
        for row in rows:
            lines.append(",".join(str(row.get(h, "")) for h in headers))
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def generate_all(self) -> Dict[str, str]:
        """Generate all Phase 10 reports and exports. Returns dict of paths."""
        manifest = self.registry.create_run_manifest()
        generated = {}

        # 1. Full benchmark
        benchmark_data = self.benchmark.full_benchmark()
        generated["verification_report.json"] = str(self._write_json("verification_report.json", benchmark_data))

        # 2. Threshold
        threshold_rows = benchmark_data.get("threshold_metrics", [])
        generated["threshold_report.json"] = str(self._write_json("threshold_report.json", {"data": threshold_rows}))
        csv_path = self._write_csv("threshold_metrics.csv", threshold_rows)
        if csv_path:
            generated["threshold_metrics.csv"] = str(csv_path)

        # 3. Regime
        regime_rows = benchmark_data.get("regime_metrics", [])
        generated["regime_report.json"] = str(self._write_json("regime_report.json", {"data": regime_rows}))
        csv_path = self._write_csv("regime_metrics.csv", regime_rows)
        if csv_path:
            generated["regime_metrics.csv"] = str(csv_path)

        # 4. Lead-time
        lt_rows = benchmark_data.get("lead_time_curves", [])
        generated["lead_time_report.json"] = str(self._write_json("lead_time_report.json", {"data": lt_rows}))
        csv_path = self._write_csv("lead_time_metrics.csv", lt_rows)
        if csv_path:
            generated["lead_time_metrics.csv"] = str(csv_path)

        # 5. Calibration
        calib_data = benchmark_data.get("calibration_analysis", {})
        generated["calibration_report.json"] = str(self._write_json("calibration_report.json", calib_data))

        # 6. Bootstrap
        boot_rows = benchmark_data.get("bootstrap_comparisons", [])
        generated["bootstrap_report.json"] = str(self._write_json("bootstrap_report.json", {"data": boot_rows}))
        csv_path = self._write_csv("bootstrap_results.csv", boot_rows)
        if csv_path:
            generated["bootstrap_results.csv"] = str(csv_path)

        # 7. Failure analysis
        failure_summary = self.failure_engine._synthetic_failure_summary()
        failure_data = failure_summary.to_dict()
        failure_data["cases"] = [c.to_dict() for c in failure_summary.failure_cases]
        generated["failure_analysis.json"] = str(self._write_json("failure_analysis.json", failure_data))
        csv_path = self._write_csv("failure_cases.csv", [c.to_dict() for c in failure_summary.failure_cases])
        if csv_path:
            generated["failure_cases.csv"] = str(csv_path)

        # 8. Explainability
        explanation = self.explain_engine.explain_synthetic_sample()
        generated["explainability_report.json"] = str(
            self._write_json("explainability_report.json", explanation.to_dict())
        )

        # 9. Expert gating
        matrix = self.expert_analyzer._synthetic_regime_expert_matrix()
        generated["expert_analysis.json"] = str(
            self._write_json("expert_analysis.json", matrix.to_dict())
        )

        # 10. Case studies
        cases = self.case_engine.replay_all()
        case_data = {"cases": [c.to_dict() for c in cases]}
        generated["case_study_report.json"] = str(self._write_json("case_study_report.json", case_data))
        generated["case_studies.json"] = str(self._write_export_json("case_studies.json", case_data))

        # 11. Spatial
        district_records = self.spatial_engine._synthetic_district_records()
        spatial_summary = self.spatial_engine.get_spatial_summary(district_records)
        spatial_data = {
            "summary": spatial_summary,
            "districts": [d.to_dict() for d in district_records],
        }
        generated["spatial_verification.json"] = str(self._write_json("spatial_verification.json", spatial_data))

        # 12. Feature importance CSV
        from ml.scientific.feature_attribution import FeatureAttributionEngine
        attr_engine = FeatureAttributionEngine(data_mode=self.data_mode, random_seed=self.random_seed)
        attr = attr_engine.get_synthetic_attribution()
        fi_rows = [f.to_dict() for f in attr.feature_importances]
        csv_path = self._write_csv("feature_importance.csv", fi_rows)
        if csv_path:
            generated["feature_importance.csv"] = str(csv_path)

        # 13. Continuous verification CSV
        continuous = self.benchmark.verif_engine.compute_all_continuous_metrics()
        cont_rows = [v.to_dict() for v in continuous.values()]
        csv_path = self._write_csv("verification.csv", cont_rows)
        if csv_path:
            generated["verification.csv"] = str(csv_path)

        # 14. Provenance
        provenance = self.registry.get_standard_provenance()
        provenance["run_id"] = manifest.run_id
        generated["provenance.json"] = str(self._write_json("provenance.json", provenance))

        # 15. Markdown report
        md_path = self._write_markdown_report(manifest.run_id, benchmark_data, generated)
        generated["verification_report.md"] = str(md_path)

        return generated

    def _write_markdown_report(
        self,
        run_id: str,
        benchmark: Dict[str, Any],
        generated_files: Dict[str, str],
    ) -> Path:
        """Write Markdown summary of Phase 10 scientific verification."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        cont = benchmark.get("continuous_metrics", [])

        lines = [
            "# RAMP Phase 10 — Scientific Verification Report",
            "",
            f"**Run ID:** `{run_id}`",
            f"**Generated:** {ts}",
            f"**Data Mode:** `SYNTHETIC_DEMO`",
            f"**Scientific Version:** `{SCIENTIFIC_VERSION}`",
            "",
            "> **⚠️ REAL IMD/NCMRWF OBSERVATIONAL ARCHIVES ARE NOT CURRENTLY MOUNTED.**",
            "> All metrics are derived from synthetic test partitions and must be labeled",
            "> **SYNTHETIC DEMONSTRATION ONLY**. Real-world operational accuracy cannot be claimed.",
            "",
            "---",
            "",
            "## 1. Continuous Metrics Summary",
            "",
            "| Model | RMSE (mm) | MAE (mm) | Bias (mm) | Pearson r | Samples |",
            "|-------|-----------|----------|-----------|-----------|---------|",
        ]

        for row in cont:
            lines.append(
                f"| {row['model']} | {row.get('rmse', 'N/A')} | {row.get('mae', 'N/A')} | "
                f"{row.get('bias', 'N/A')} | {row.get('pearson_r', 'N/A')} | {row.get('n_samples', 0)} |"
            )

        lines += [
            "",
            "*Factual labels only: LOWER_RMSE, NOT_SIGNIFICANT, SAMPLE_LIMITED. No model is ranked 'best'.*",
            "",
            "---",
            "",
            "## 2. Regime-Stratified Verification",
            "",
            "| Regime | RMSE | MAE | Heavy CSI | Samples |",
            "|--------|------|-----|-----------|---------|",
        ]

        for row in benchmark.get("regime_metrics", []):
            lines.append(
                f"| {row['regime']} | {row.get('rmse', 'N/A')} | {row.get('mae', 'N/A')} | "
                f"{row.get('heavy_csi', 'N/A')} | {row.get('n_samples', 0)} |"
            )

        lines += [
            "",
            "---",
            "",
            "## 3. Data Mode & Real Data Policy",
            "",
            "| Field | Value |",
            "|-------|-------|",
            "| Data Mode | `SYNTHETIC_DEMO` |",
            "| Real Observations | NOT AVAILABLE |",
            "| SHAP Attribution | SHAP_NOT_AVAILABLE (graceful fallback to gain importance) |",
            "| FSS Observations | NOT_AVAILABLE (no real radar/gauge grids mounted) |",
            "| Operational Accuracy | Cannot be claimed |",
            "",
            "---",
            "",
            "## 4. Generated Artifacts",
            "",
        ]

        for fname in sorted(generated_files.keys()):
            lines.append(f"- `{fname}`")

        path = REPORT_DIR / "verification_report.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path
