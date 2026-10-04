"""
RAMP Dataset Catalog Store
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Manages dataset metadata in the `datasets` table.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import delete, select, update

try:
    from .connection import DatabaseManager
    from .models import DatasetModel
    from .repository import BaseRepository
except (ImportError, ValueError):
    from ramp.storage.connection import DatabaseManager
    from ramp.storage.models import DatasetModel
    from ramp.storage.repository import BaseRepository

logger = logging.getLogger(__name__)


class DatasetStore(BaseRepository):
    """
    CRUD repository for dataset definitions.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        super().__init__(db_manager)

    def create_dataset(
        self,
        dataset_id: str,
        dataset_type: str,
        source_provider: str,
        source_model: Optional[str] = None,
        data_mode: str = "REAL_OPERATIONAL",
        version: str = "v1.0",
        description: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        native_resolution: str = "0.12°",
        target_resolution: str = "0.25°",
        file_count: int = 0,
        total_size_bytes: int = 0,
        quality_status: str = "VALIDATED",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        with self.db.session() as session:
            existing = session.execute(
                select(DatasetModel).where(DatasetModel.dataset_id == dataset_id)
            ).scalar_one_or_none()

            if existing:
                existing.dataset_type = dataset_type
                existing.source_provider = source_provider
                existing.source_model = source_model
                existing.data_mode = data_mode
                existing.version = version
                existing.description = description
                existing.start_time = start_time
                existing.end_time = end_time
                existing.native_resolution = native_resolution
                existing.target_resolution = target_resolution
                existing.file_count = file_count
                existing.total_size_bytes = total_size_bytes
                existing.quality_status = quality_status
                existing.metadata_json = metadata or {}
                session.flush()
                return existing.to_dict()

            rec = DatasetModel(
                dataset_id=dataset_id,
                dataset_type=dataset_type,
                source_provider=source_provider,
                source_model=source_model,
                data_mode=data_mode,
                version=version,
                description=description,
                start_time=start_time,
                end_time=end_time,
                native_resolution=native_resolution,
                target_resolution=target_resolution,
                file_count=file_count,
                total_size_bytes=total_size_bytes,
                quality_status=quality_status,
                metadata_json=metadata or {},
            )
            session.add(rec)
            session.flush()
            return rec.to_dict()

    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        with self.db.session() as session:
            rec = session.execute(
                select(DatasetModel).where(DatasetModel.dataset_id == dataset_id)
            ).scalar_one_or_none()
            return rec.to_dict() if rec else None

    def list_datasets(
        self,
        dataset_type: Optional[str] = None,
        source_provider: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with self.db.session() as session:
            stmt = select(DatasetModel)
            if dataset_type:
                stmt = stmt.where(DatasetModel.dataset_type == dataset_type)
            if source_provider:
                stmt = stmt.where(DatasetModel.source_provider == source_provider)
            recs = session.execute(stmt).scalars().all()
            return [r.to_dict() for r in recs]

    def update_quality_status(self, dataset_id: str, quality_status: str) -> bool:
        with self.db.session() as session:
            rec = session.execute(
                select(DatasetModel).where(DatasetModel.dataset_id == dataset_id)
            ).scalar_one_or_none()
            if not rec:
                return False
            rec.quality_status = quality_status
            return True

    def delete_dataset(self, dataset_id: str) -> bool:
        with self.db.session() as session:
            rec = session.execute(
                select(DatasetModel).where(DatasetModel.dataset_id == dataset_id)
            ).scalar_one_or_none()
            if not rec:
                return False
            session.delete(rec)
            return True
