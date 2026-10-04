"""
RAMP Provenance Registry & Cryptographic Audit Event Store
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Persists immutable forecast execution provenance records and append-only
cryptographic audit events with hash chaining in PostgreSQL.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select

try:
    from .connection import DatabaseManager
    from .models import AuditEventModel, ForecastProvenanceModel
    from .repository import BaseRepository
except (ImportError, ValueError):
    from ramp.storage.connection import DatabaseManager
    from ramp.storage.models import AuditEventModel, ForecastProvenanceModel
    from ramp.storage.repository import BaseRepository

logger = logging.getLogger(__name__)

GENESIS_HASH = "0" * 64


class ProvenanceStore(BaseRepository):
    """
    Manages immutable execution manifests and cryptographically chained audit events.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        super().__init__(db_manager)

    def record_provenance(
        self,
        forecast_run_id: str,
        input_file_ids: List[str],
        input_hashes: Dict[str, str],
        model_version: str = "v2.0.0",
        model_hash: Optional[str] = None,
        dataset_version: str = "v1.8",
        feature_contract: str = "ramp_features_v1.0.0",
        target_contract: str = "ramp_targets_v1.0.0",
        calibration_version: str = "v1.0",
        software_version: str = "2.0.0",
        git_commit: Optional[str] = None,
        data_mode: str = "REAL_OPERATIONAL",
        manifest: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        with self.db.session() as session:
            existing = session.execute(
                select(ForecastProvenanceModel).where(
                    ForecastProvenanceModel.forecast_run_id == forecast_run_id
                )
            ).scalar_one_or_none()

            if existing:
                return existing.to_dict()

            prov = ForecastProvenanceModel(
                forecast_run_id=forecast_run_id,
                input_file_ids=input_file_ids,
                input_hashes=input_hashes,
                model_version=model_version,
                model_hash=model_hash,
                dataset_version=dataset_version,
                feature_contract=feature_contract,
                target_contract=target_contract,
                calibration_version=calibration_version,
                software_version=software_version,
                git_commit=git_commit,
                data_mode=data_mode,
                manifest=manifest or {},
            )
            session.add(prov)
            session.flush()
            return prov.to_dict()

    def get_provenance(self, forecast_run_id: str) -> Optional[Dict[str, Any]]:
        with self.db.session() as session:
            rec = session.execute(
                select(ForecastProvenanceModel).where(
                    ForecastProvenanceModel.forecast_run_id == forecast_run_id
                )
            ).scalar_one_or_none()
            return rec.to_dict() if rec else None

    def record_audit_event(
        self,
        event_id: str,
        event_type: str,
        actor_role: str = "SYSTEM",
        actor_id: str = "RAMP_DAEMON",
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Appends an audit record to the cryptographic hash chain.
        Each record signs: previous_hash + event_id + event_type + timestamp + details.
        """
        now = datetime.now(timezone.utc)
        ts_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        details_clean = details or {}
        details_str = json.dumps(details_clean, sort_keys=True)

        with self.db.session() as session:
            # Fetch latest audit record for previous hash
            latest = session.execute(
                select(AuditEventModel).order_by(desc(AuditEventModel.id)).limit(1)
            ).scalar_one_or_none()

            prev_hash = latest.sha256_signature if latest else GENESIS_HASH

            # Compute SHA-256 signature
            sig_input = f"{prev_hash}|{event_id}|{event_type}|{ts_str}|{actor_role}|{actor_id}|{details_str}"
            sha256_sig = hashlib.sha256(sig_input.encode("utf-8")).hexdigest()

            event = AuditEventModel(
                event_id=event_id,
                event_type=event_type,
                timestamp_utc=now,
                actor_role=actor_role,
                actor_id=actor_id,
                details=details_clean,
                sha256_signature=sha256_sig,
                previous_hash=prev_hash,
            )
            session.add(event)
            session.flush()
            return event.to_dict()

    def get_audit_trail(
        self,
        limit: int = 50,
        event_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with self.db.session() as session:
            stmt = select(AuditEventModel).order_by(desc(AuditEventModel.timestamp_utc))
            if event_type:
                stmt = stmt.where(AuditEventModel.event_type == event_type)
            stmt = stmt.limit(limit)

            recs = session.execute(stmt).scalars().all()
            return [r.to_dict() for r in recs]

    def verify_audit_chain(self) -> Dict[str, Any]:
        """
        Verifies the cryptographic integrity of the entire audit chain.
        """
        with self.db.session() as session:
            records = session.execute(
                select(AuditEventModel).order_by(AuditEventModel.id.asc())
            ).scalars().all()

            if not records:
                return {"valid": True, "records_checked": 0, "status": "EMPTY"}

            prev_hash = GENESIS_HASH
            for rec in records:
                if rec.previous_hash != prev_hash:
                    return {
                        "valid": False,
                        "broken_at_id": rec.id,
                        "broken_event_id": rec.event_id,
                        "reason": f"Hash chain mismatch: expected {prev_hash}, found {rec.previous_hash}",
                    }
                ts_str = rec.timestamp_utc.strftime("%Y-%m-%dT%H:%M:%SZ") if hasattr(rec.timestamp_utc, "strftime") else str(rec.timestamp_utc)
                details_str = json.dumps(rec.details or {}, sort_keys=True)
                sig_input = f"{rec.previous_hash}|{rec.event_id}|{rec.event_type}|{ts_str}|{rec.actor_role}|{rec.actor_id}|{details_str}"
                expected_sig = hashlib.sha256(sig_input.encode("utf-8")).hexdigest()

                if rec.sha256_signature != expected_sig:
                    return {
                        "valid": False,
                        "broken_at_id": rec.id,
                        "broken_event_id": rec.event_id,
                        "reason": "Signature tampering detected",
                    }
                prev_hash = rec.sha256_signature

            return {
                "valid": True,
                "records_checked": len(records),
                "events_verified": len(records),
                "status": "VERIFIED",
            }
