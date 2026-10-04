"""
RAMP Data Retention Policy Engine
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Enforces configurable retention windows for raw meteorological files, forecast products,
and observations while preserving immutable cryptographic provenance and audit events.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy import delete, select

from backend.src.ramp.storage.connection import DatabaseManager
from backend.src.ramp.storage.models import (
    FileChunkModel,
    FileObjectModel,
    ForecastDistrictModel,
    ForecastGridModel,
    ForecastRunModel,
    ForecastStateModel,
    IMDObservationModel,
)

logger = logging.getLogger(__name__)


class RetentionPolicyManager:
    """
    Manages data lifecycle and cleanup policies.
    Guarantees:
      - Audit logs and provenance records are NEVER purged automatically.
      - Raw files and forecast runs adhere to configurable retention windows.
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        raw_data_retention_days: Optional[int] = None,
        forecast_retention_days: Optional[int] = None,
        observation_retention_days: Optional[int] = None,
    ):
        self.db = db_manager or DatabaseManager.get_instance()
        # Retention windows in days (0 means indefinitely retained)
        self.raw_data_retention_days = (
            raw_data_retention_days
            if raw_data_retention_days is not None
            else int(os.environ.get("RAW_DATA_RETENTION_DAYS", "90"))
        )
        self.forecast_retention_days = (
            forecast_retention_days
            if forecast_retention_days is not None
            else int(os.environ.get("FORECAST_RETENTION_DAYS", "30"))
        )
        self.observation_retention_days = (
            observation_retention_days
            if observation_retention_days is not None
            else int(os.environ.get("OBSERVATION_RETENTION_DAYS", "365"))
        )

    def get_retention_config(self) -> Dict[str, Any]:
        return {
            "raw_data_retention_days": self.raw_data_retention_days,
            "forecast_retention_days": self.forecast_retention_days,
            "observation_retention_days": self.observation_retention_days,
            "provenance_retention": "PERMANENT_IMMUTABLE",
            "audit_retention": "PERMANENT_IMMUTABLE",
        }

    def apply_retention_policy(self) -> Dict[str, Any]:
        """
        Executes retention pruning on aged records according to configured policies.
        """
        now = datetime.now(timezone.utc)
        purged_stats = {
            "timestamp": now.isoformat(),
            "purged_files": 0,
            "purged_forecast_runs": 0,
            "purged_observations": 0,
            "pruned_file_objects": 0,
            "pruned_forecast_runs": 0,
            "pruned_observations": 0,
            "audit_events_preserved": True,
            "provenance_records_preserved": True,
        }

        with self.db.session() as session:
            # 1. Prune aged forecast runs and cascading grids
            if self.forecast_retention_days > 0:
                cutoff = now - timedelta(days=self.forecast_retention_days)
                aged_runs = session.execute(
                    select(ForecastRunModel.forecast_run_id).where(ForecastRunModel.created_at < cutoff)
                ).scalars().all()

                for run_id in aged_runs:
                    session.execute(delete(ForecastGridModel).where(ForecastGridModel.forecast_run_id == run_id))
                    session.execute(delete(ForecastDistrictModel).where(ForecastDistrictModel.forecast_run_id == run_id))
                    session.execute(delete(ForecastStateModel).where(ForecastStateModel.forecast_run_id == run_id))
                    session.execute(delete(ForecastRunModel).where(ForecastRunModel.forecast_run_id == run_id))
                    purged_stats["purged_forecast_runs"] += 1
                    purged_stats["pruned_forecast_runs"] += 1

            # 2. Prune aged raw files (cascades to chunks)
            if self.raw_data_retention_days > 0:
                cutoff = now - timedelta(days=self.raw_data_retention_days)
                aged_files = session.execute(
                    select(FileObjectModel).where(FileObjectModel.created_at < cutoff)
                ).scalars().all()

                for f in aged_files:
                    session.delete(f)
                    purged_stats["purged_files"] += 1
                    purged_stats["pruned_file_objects"] += 1

            # 3. Prune aged observations
            if self.observation_retention_days > 0:
                cutoff = now - timedelta(days=self.observation_retention_days)
                res = session.execute(
                    delete(IMDObservationModel).where(IMDObservationModel.observation_time < cutoff)
                )
                cnt = res.rowcount if hasattr(res, "rowcount") else 0
                purged_stats["purged_observations"] = cnt
                purged_stats["pruned_observations"] = cnt

        logger.info(f"Retention policy applied: {purged_stats}")
        return purged_stats

    def prune_expired_records(self) -> Dict[str, Any]:
        """Alias for apply_retention_policy."""
        return self.apply_retention_policy()
