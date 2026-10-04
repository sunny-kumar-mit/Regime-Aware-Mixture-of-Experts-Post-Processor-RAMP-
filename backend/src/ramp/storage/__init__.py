"""
RAMP Storage Module (PostgreSQL + PostGIS Persistent Storage Layer)
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Replaces MinIO with PostgreSQL + PostGIS as the single persistent storage backend.
"""

from .connection import (
    Base,
    DatabaseManager,
    get_database_url,
    get_db_session,
)
from .models import (
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
from .postgres_storage import PostgresStorageProvider
from .repository import BaseRepository
from .file_store import MeteorologicalFileStore
from .forecast_store import ForecastStore
from .dataset_store import DatasetStore
from .provenance_store import ProvenanceStore

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
