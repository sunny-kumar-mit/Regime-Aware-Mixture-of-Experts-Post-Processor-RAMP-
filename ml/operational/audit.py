"""
Phase 8 Audit Trail & Reproducibility Engine
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Generates immutable verification run manifests:
  - run_id
  - dataset_id & dataset_version
  - git commit hash
  - model versions
  - feature schema
  - runtime environment (Python, OS, packages)
  - configuration
  - data quality & leakage audit status
  - summary metrics
"""

from __future__ import annotations

import json
import logging
import platform
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

AUDIT_DIR = Path("data/audit/runs")


@dataclass
class RunManifest:
    run_id: str
    dataset_id: str
    dataset_version: str
    data_mode: str
    timestamp: str
    git_commit: str
    python_version: str
    platform_info: str
    dependency_versions: Dict[str, str]
    model_versions: Dict[str, str]
    feature_schema_version: str
    target_schema_version: str
    data_quality_status: str
    leakage_guard_status: str
    configuration: Dict[str, Any]
    summary_metrics: Dict[str, Any]
    notes: Optional[str] = None


class AuditTrailManager:
    """Manages creation and retrieval of verification run manifests."""

    def __init__(self, audit_dir: Path | str = AUDIT_DIR) -> None:
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_git_commit(cls) -> str:
        try:
            res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            return res.stdout.strip()
        except Exception:
            return "git_commit_unavailable"

    @classmethod
    def get_dependencies(cls) -> Dict[str, str]:
        packages = ["numpy", "pandas", "scipy", "sklearn", "lightgbm", "fastapi", "pydantic", "xarray"]
        versions = {}
        for p in packages:
            try:
                mod = __import__(p)
                versions[p] = getattr(mod, "__version__", "unknown")
            except Exception:
                versions[p] = "not_installed"
        return versions

    def create_run_manifest(
        self,
        dataset_id: str,
        dataset_version: str,
        data_mode: str,
        model_versions: Dict[str, str],
        data_quality_status: str,
        leakage_guard_status: str,
        summary_metrics: Dict[str, Any],
        configuration: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None,
    ) -> RunManifest:
        run_id = f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        manifest = RunManifest(
            run_id=run_id,
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            data_mode=data_mode,
            timestamp=datetime.utcnow().isoformat() + "Z",
            git_commit=self.get_git_commit(),
            python_version=sys.version.split()[0],
            platform_info=f"{platform.system()} {platform.release()} ({platform.machine()})",
            dependency_versions=self.get_dependencies(),
            model_versions=model_versions,
            feature_schema_version="canonical_v1.0.0",
            target_schema_version="imd_rainfall_v1.0.0",
            data_quality_status=data_quality_status,
            leakage_guard_status=leakage_guard_status,
            configuration=configuration or {},
            summary_metrics=summary_metrics,
            notes=notes,
        )

        out_path = self.audit_dir / f"{run_id}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(asdict(manifest), f, indent=2)
        logger.info(f"Created run manifest {run_id} at {out_path}")
        return manifest

    def list_runs(self) -> List[Dict[str, Any]]:
        runs = []
        for p in sorted(self.audit_dir.glob("run_*.json"), reverse=True):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    runs.append(json.load(f))
            except Exception as e:
                logger.warning(f"Error loading {p}: {e}")
        return runs
