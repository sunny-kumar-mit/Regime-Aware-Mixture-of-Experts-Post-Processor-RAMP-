"""
RAMP Storage Base Repository & Transaction Operations
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Encapsulates database transaction management, bulk batching, and error rollback.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Generator, Iterable, List, Optional, Type, TypeVar
from sqlalchemy.orm import Session
from sqlalchemy import select, delete, func

from backend.src.ramp.storage.connection import DatabaseManager

logger = logging.getLogger(__name__)
T = TypeVar("T")


class BaseRepository:
    """
    Base repository providing transaction boundaries, batch chunking, and session utilities.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager.get_instance()

    def get_session(self) -> Session:
        return self.db.SessionFactory()

    @staticmethod
    def chunked_iterable(iterable: Iterable[T], size: int) -> Generator[List[T], None, None]:
        """Splits an iterable into fixed-size chunks for bulk database operations."""
        chunk = []
        for item in iterable:
            chunk.append(item)
            if len(chunk) == size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk

    def bulk_insert_batch(self, session: Session, items: List[Any], batch_size: int = 500) -> int:
        """Performs optimized bulk inserts in configurable batch sizes."""
        if not items:
            return 0
        total = 0
        for batch in self.chunked_iterable(items, batch_size):
            session.bulk_save_objects(batch)
            session.flush()
            total += len(batch)
        return total
