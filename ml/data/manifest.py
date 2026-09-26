"""
Phase 8 Dataset Manifest Management
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Manages versioned dataset manifests located in data/manifests/dataset_manifest.json.
Provides provenance, variable tracking, spatial/temporal extents, and quality sign-off.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_MANIFEST_PATH = Path("data/manifests/dataset_manifest.json")


@dataclass
class DatasetManifest:
    dataset_id: str
    dataset_version: str
    mode: str  # REAL or SYNTHETIC_DEMO
    source: str
    variables: List[str]
    start_date: str
    end_date: str
    spatial_extent: Dict[str, float]
    resolution: str
    lead_times: List[int]
    quality_status: str  # PASS, CONDITIONAL_PASS, FAIL, PENDING
    total_records: int = 0
    valid_records: int = 0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatasetManifest":
        return cls(**data)

    def save(self, filepath: Path | str = DEFAULT_MANIFEST_PATH) -> None:
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Dataset manifest saved to {p}")

    @classmethod
    def load(cls, filepath: Path | str = DEFAULT_MANIFEST_PATH) -> Optional["DatasetManifest"]:
        p = Path(filepath)
        if not p.exists():
            return None
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def create_default_synthetic_manifest(cls) -> "DatasetManifest":
        """Default manifest for current SYNTHETIC_DEMO mode."""
        return cls(
            dataset_id="ramp_synthetic_monsoon_demo_v1",
            dataset_version="v1.0.0",
            mode="SYNTHETIC_DEMO",
            source="SyntheticMonsoonGenerator_NCMRWF_IMD_Parametric",
            variables=[
                "nwp_rainfall_mm",
                "observed_rainfall_mm",
                "mslp_pa",
                "u850_ms",
                "v850_ms",
                "cape_jkg",
                "rh700_pct",
                "tpw_kgm2",
                "temp2m_k",
                "gh500_m",
                "latitude",
                "longitude",
                "lead_time_hours",
            ],
            start_date="2023-06-01T00:00:00Z",
            end_date="2023-09-30T00:00:00Z",
            spatial_extent={
                "lat_min": 8.0,
                "lat_max": 35.0,
                "lon_min": 68.0,
                "lon_max": 97.0,
            },
            resolution="0.25 deg (~28 km)",
            lead_times=[24, 48, 72, 96, 120],
            quality_status="PASS",
            total_records=1000,
            valid_records=1000,
            notes="Active synthetic demonstration archive for Phase 1-8 development and UI verification.",
        )
