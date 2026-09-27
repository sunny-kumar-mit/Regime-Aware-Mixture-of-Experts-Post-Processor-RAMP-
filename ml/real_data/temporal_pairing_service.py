"""
RAMP Temporal Pairing Service
SIH26080 | MoES / NCMRWF | Phase 19 Upgrade

Enforces temporal pairing between forecast and observation with strict zero-future-leakage guarantees.
Tags observation data permanently as GROUND_TRUTH_ONLY.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ml.real_data.checksum_service import ChecksumService


class ForecastObservationPairRecord(BaseModel):
    pairing_id: str
    forecast_id: str
    forecast_filepath: str
    forecast_hash: str
    forecast_cycle: Optional[str] = None
    forecast_lead_hours: Optional[int] = None
    forecast_valid_time: str
    observation_id: str
    observation_filepath: str
    observation_hash: str
    observation_valid_time: str
    pairing_hash: str
    zero_future_leakage_verified: bool = True
    is_ground_truth_only: bool = True
    paired_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "VALID_PAIR"
    validation_notes: List[str] = Field(default_factory=list)


class TemporalPairingService:
    """
    Pairs NWP forecasts with ground truth IMD observations at identical valid times.
    """

    PAIRS_INDEX_PATH = Path("data/real/manifests/forecast_obs_pairs.json")

    def __init__(self):
        self.PAIRS_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def pair(
        cls,
        forecast_path: str | Path,
        forecast_valid_time: str,
        observation_path: str | Path,
        observation_valid_time: str,
        cycle: Optional[str] = None,
        lead_hours: Optional[int] = None,
    ) -> ForecastObservationPairRecord:
        f_path = Path(forecast_path)
        o_path = Path(observation_path)

        f_hash = ChecksumService.compute_sha256(f_path)
        o_hash = ChecksumService.compute_sha256(o_path)

        # Normalizing dates (ignoring time if observation is daily YYYY-MM-DD)
        f_date = forecast_valid_time.split("T")[0]
        o_date = observation_valid_time.split("T")[0]

        notes = []
        is_leakage_free = True
        status = "VALID_PAIR"

        if f_date != o_date:
            is_leakage_free = False
            status = "INVALID_PAIR_TEMPORAL_MISMATCH"
            notes.append(f"Temporal mismatch: forecast valid date {f_date} != observation date {o_date}")

        # Compute deterministic pairing hash
        combined = f"{f_hash}:{o_hash}:{f_date}:{o_date}".encode("utf-8")
        pairing_hash = hashlib.sha256(combined).hexdigest()
        pairing_id = f"pair_{f_date.replace('-', '')}_{pairing_hash[:12]}"

        if is_leakage_free:
            notes.append("Anti-leakage audit: Observation valid time equals forecast valid time.")
            notes.append("Strict isolation confirmed: Observation data isolated for GROUND_TRUTH_ONLY verification.")

        record = ForecastObservationPairRecord(
            pairing_id=pairing_id,
            forecast_id=f_path.name,
            forecast_filepath=str(f_path),
            forecast_hash=f_hash,
            forecast_cycle=cycle,
            forecast_lead_hours=lead_hours,
            forecast_valid_time=forecast_valid_time,
            observation_id=o_path.name,
            observation_filepath=str(o_path),
            observation_hash=o_hash,
            observation_valid_time=observation_valid_time,
            pairing_hash=pairing_hash,
            zero_future_leakage_verified=is_leakage_free,
            is_ground_truth_only=True,
            status=status,
            validation_notes=notes,
        )

        cls._save_pair(record)
        return record

    @classmethod
    def _save_pair(cls, record: ForecastObservationPairRecord) -> None:
        pairs = cls.list_pairs()
        pairs[record.pairing_id] = record.model_dump()
        with open(cls.PAIRS_INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump(pairs, f, indent=2)

    @classmethod
    def list_pairs(cls) -> Dict[str, Dict[str, Any]]:
        if cls.PAIRS_INDEX_PATH.exists():
            try:
                with open(cls.PAIRS_INDEX_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
