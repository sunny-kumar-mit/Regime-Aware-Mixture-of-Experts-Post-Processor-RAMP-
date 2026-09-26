"""
RAMP Scientific Registry — Phase 10 Provenance & Audit Management
SIH26080 | MoES / NCMRWF

Manages immutable scientific run manifests, caching, and reproducibility.
"""

from __future__ import annotations

import hashlib
import json
import sys
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SCIENTIFIC_VERSION = "scientific_v1.0.0"
AUDIT_DIR = Path("data/audit/scientific")
EXPORT_DIR = Path("data/scientific_exports")
REPORT_DIR = Path("data/scientific_reports")
RANDOM_SEED = 42
BOOTSTRAP_SAMPLES = 300


@dataclass
class ScientificRunManifest:
    """Immutable audit record for a scientific analysis run."""
    run_id: str
    scientific_version: str
    model_versions: Dict[str, str]
    dataset_version: str
    feature_schema_version: str
    spatial_product_version: str
    boundary_version: str
    data_mode: str
    random_seed: int
    bootstrap_samples: int
    python_version: str
    timestamp: str
    phase_versions: Dict[str, str] = field(default_factory=dict)
    metric_config: Dict[str, Any] = field(default_factory=dict)
    threshold_config: List[float] = field(default_factory=list)
    bootstrap_config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class ScientificRegistry:
    """
    Manages scientific run manifests and provenance for Phase 10.
    Every scientific analysis run is recorded immutably.
    """

    MODEL_VERSIONS = {
        "regime": "regime_lgbm_v0.1.0",
        "mean_bias": "mean_bias_v1.0.0",
        "quantile_mapping": "quantile_mapping_v1.0.0",
        "global_ml": "global_ml_v1.0.0",
        "ramp": "ramp_v1.0.0",
        "extreme_prob": "extreme_prob_v1.0.0",
    }

    PHASE_VERSIONS = {
        "phase_1": "production_foundation_v1.0.0",
        "phase_2": "meteorological_data_v1.0.0",
        "phase_3": "training_dataset_v1.0.0",
        "phase_4": "regime_engine_v1.0.0",
        "phase_5": "baseline_benchmarks_v1.0.0",
        "phase_6": "ramp_moe_v1.0.0",
        "phase_7": "extreme_prob_engine_v1.0.0",
        "phase_8": "operational_verification_v1.0.0",
        "phase_9": "spatial_products_v1.0.0",
        "phase_10": SCIENTIFIC_VERSION,
    }

    THRESHOLDS = [0.1, 64.5, 115.6, 204.5]

    METRIC_CONFIG = {
        "continuous": ["rmse", "mae", "bias", "pearson_r", "spearman_r", "normalized_rmse", "normalized_mae"],
        "threshold": ["pod", "far", "csi", "ets", "bias_score", "frequency_bias", "success_ratio", "threat_score"],
        "probability": ["brier", "bss", "reliability", "ece", "mce", "roc_auc", "pr_auc", "log_loss"],
    }

    BOOTSTRAP_CONFIG = {
        "n_samples": BOOTSTRAP_SAMPLES,
        "random_seed": RANDOM_SEED,
        "confidence_level": 0.95,
        "method": "paired_bootstrap",
    }

    def __init__(self, data_mode: str = "SYNTHETIC_DEMO"):
        self.data_mode = data_mode
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)

    def create_run_manifest(
        self,
        dataset_version: str = "ramp_dataset_v0.3.0",
        feature_schema_version: str = "feature_registry_v1.0.0",
        spatial_product_version: str = "spatial_product_v1.0.0",
        boundary_version: str = "boundaries_v1.0.0",
    ) -> ScientificRunManifest:
        run_id = f"sci_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        manifest = ScientificRunManifest(
            run_id=run_id,
            scientific_version=SCIENTIFIC_VERSION,
            model_versions=dict(self.MODEL_VERSIONS),
            dataset_version=dataset_version,
            feature_schema_version=feature_schema_version,
            spatial_product_version=spatial_product_version,
            boundary_version=boundary_version,
            data_mode=self.data_mode,
            random_seed=RANDOM_SEED,
            bootstrap_samples=BOOTSTRAP_SAMPLES,
            python_version=sys.version,
            timestamp=datetime.now(timezone.utc).isoformat(),
            phase_versions=dict(self.PHASE_VERSIONS),
            metric_config=dict(self.METRIC_CONFIG),
            threshold_config=list(self.THRESHOLDS),
            bootstrap_config=dict(self.BOOTSTRAP_CONFIG),
        )
        self._persist_manifest(manifest)
        return manifest

    def _persist_manifest(self, manifest: ScientificRunManifest) -> None:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        path = AUDIT_DIR / f"{manifest.run_id}.json"
        path.write_text(manifest.to_json(), encoding="utf-8")

    def compute_cache_key(self, **kwargs) -> str:
        """Compute deterministic SHA-256 cache key from run parameters."""
        canonical = json.dumps(kwargs, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

    def get_standard_provenance(self) -> Dict[str, Any]:
        """Returns the standard provenance envelope for API responses."""
        return {
            "scientific_version": SCIENTIFIC_VERSION,
            "model_versions": dict(self.MODEL_VERSIONS),
            "phase_versions": dict(self.PHASE_VERSIONS),
            "data_mode": self.data_mode,
            "random_seed": RANDOM_SEED,
            "bootstrap_samples": BOOTSTRAP_SAMPLES,
            "thresholds_mm": list(self.THRESHOLDS),
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        }
