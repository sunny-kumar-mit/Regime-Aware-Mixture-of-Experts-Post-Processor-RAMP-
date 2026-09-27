"""
RAMP Provenance & Auditing Service
SIH26080 | MoES / NCMRWF | Phase 19 Upgrade

Captures and serves end-to-end cryptographic and metadata lineage records for real data experiments.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProvenanceRecord(BaseModel):
    experiment_id: str
    provider: str
    dataset: str
    official_source_url: str
    source_page_url: str
    download_timestamp: str
    original_filename: str
    original_sha256: str
    converted_filename: Optional[str] = None
    converted_sha256: Optional[str] = None
    conversion_method: Optional[str] = None
    validation_status: str
    validation_version: str = "v1.0.0"
    feature_contract_version: str = "ramp_features_v1.0.0"
    target_contract_version: str = "ramp_targets_v1.0.0"
    model_version: str = "v2.0.0"
    forecast_cycle: Optional[str] = None
    forecast_lead_hours: Optional[int] = None
    forecast_valid_time: Optional[str] = None
    observation_date: Optional[str] = None
    observation_sha256: Optional[str] = None
    pairing_hash: Optional[str] = None
    user_configuration: Dict[str, Any] = Field(default_factory=dict)
    output_hash: Optional[str] = None
    output_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProvenanceService:
    """
    Manages generation, storage, and retrieval of auditable provenance chains.
    """

    PROVENANCE_DIR = Path("data/real/provenance")

    def __init__(self):
        self.PROVENANCE_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def record_provenance(cls, record: ProvenanceRecord) -> None:
        cls.PROVENANCE_DIR.mkdir(parents=True, exist_ok=True)
        path = cls.PROVENANCE_DIR / f"{record.experiment_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record.model_dump(), f, indent=2)

    @classmethod
    def get_provenance(cls, experiment_id: str) -> Optional[Dict[str, Any]]:
        cls.PROVENANCE_DIR.mkdir(parents=True, exist_ok=True)
        path = cls.PROVENANCE_DIR / f"{experiment_id}.json"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    @classmethod
    def list_all_provenance(cls) -> List[Dict[str, Any]]:
        cls.PROVENANCE_DIR.mkdir(parents=True, exist_ok=True)
        items = []
        for p in cls.PROVENANCE_DIR.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    items.append(json.load(f))
            except Exception:
                pass
        return sorted(items, key=lambda x: x.get("output_timestamp", ""), reverse=True)
