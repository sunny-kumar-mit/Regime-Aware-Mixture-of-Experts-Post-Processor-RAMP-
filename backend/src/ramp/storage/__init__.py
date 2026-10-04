"""
RAMP Storage Module (PostgreSQL + PostGIS Persistent Storage Layer)
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Replaces MinIO with PostgreSQL + PostGIS as the single persistent storage backend.
"""

from backend.src.ramp.storage.connection import (
    Base,
    DatabaseManager,
    get_database_url,
    get_db_session,
)
from backend.src.ramp.storage.models import (
    AuditEventModel,
    DatasetModel,
    FileChunkModel,
    FileObjectModel,
    ForecastDistrictModel,
    ForecastGridModel,
    ForecastProvenanceModel,
    ForecastRunModel,
    ForecastStateModel,
    IMDObservationModel,
    NWPFileModel,
)
from backend.src.ramp.storage.postgres_storage import PostgresStorageProvider
from backend.src.ramp.storage.repository import BaseRepository
from backend.src.ramp.storage.file_store import MeteorologicalFileStore
from backend.src.ramp.storage.forecast_store import ForecastStore
from backend.src.ramp.storage.dataset_store import DatasetStore
from backend.src.ramp.storage.provenance_store import ProvenanceStore

__all__ = [
    "Base",
    "DatabaseManager",
    "get_database_url",
    "get_db_session",
    "DatasetModel",
    "FileObjectModel",
    "FileChunkModel",
    "ForecastRunModel",
    "ForecastGridModel",
    "ForecastDistrictModel",
    "ForecastStateModel",
    "IMDObservationModel",
    "NWPFileModel",
    "ForecastProvenanceModel",
    "AuditEventModel",
    "PostgresStorageProvider",
    "BaseRepository",
    "MeteorologicalFileStore",
    "ForecastStore",
    "DatasetStore",
    "ProvenanceStore",
]
