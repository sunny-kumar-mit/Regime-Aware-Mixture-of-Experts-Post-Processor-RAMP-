"""
RAMP PostgreSQL & PostGIS Database Models
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Declares relational & spatial entities for:
  - datasets
  - file_objects & file_chunks (chunked raw file storage)
  - forecast_runs
  - forecast_grid (PostGIS Point geometry)
  - forecast_districts & forecast_states (PostGIS Spatial aggregations)
  - imd_observations (PostGIS ground truth observation storage)
  - nwp_files
  - forecast_provenance
  - audit_events (cryptographic hash chain)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator
from geoalchemy2 import Geometry

from backend.src.ramp.storage.connection import Base


class SafeGeometry(TypeDecorator):
    """
    Native PostGIS Geometry on PostgreSQL with automatic spatial indexing;
    graceful String/WKT storage fallback on SQLite for isolated testing.
    """
    impl = String
    cache_ok = True

    def __init__(self, geometry_type: str = "GEOMETRY", srid: int = 4326, **kwargs):
        super().__init__()
        self.geometry_type = geometry_type
        self.srid = srid
        self.postgis_geom = Geometry(geometry_type=geometry_type, srid=srid, **kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(self.postgis_geom)
        return dialect.type_descriptor(String())


# =============================================================================
# 1. Dataset Table
# =============================================================================
class DatasetModel(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(String(128), unique=True, index=True, nullable=False)
    dataset_type = Column(String(64), nullable=False)  # NWP_DETERMINISTIC | NWP_ENSEMBLE | OBSERVATION
    source_provider = Column(String(64), nullable=False)  # NCMRWF | IMD | ECMWF
    source_model = Column(String(64), nullable=True)  # NCUM | NEPS | IMD_025_GRID
    data_mode = Column(String(32), default="REAL_OPERATIONAL")  # REAL_OPERATIONAL | SYNTHETIC_DEMO
    version = Column(String(32), default="v1.0")
    description = Column(Text, nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    native_resolution = Column(String(32), default="0.12°")
    target_resolution = Column(String(32), default="0.25°")
    file_count = Column(Integer, default=0)
    total_size_bytes = Column(BigInteger, default=0)
    quality_status = Column(String(32), default="VALIDATED")  # VALIDATED | REJECTED | PENDING
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    metadata_json = Column("metadata", JSON, default=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "dataset_id": self.dataset_id,
            "dataset_type": self.dataset_type,
            "source_provider": self.source_provider,
            "source_model": self.source_model,
            "data_mode": self.data_mode,
            "version": self.version,
            "description": self.description,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "native_resolution": self.native_resolution,
            "target_resolution": self.target_resolution,
            "file_count": self.file_count,
            "total_size_bytes": self.total_size_bytes,
            "quality_status": self.quality_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata_json or {},
        }


# =============================================================================
# 2. File Objects & Chunks (Large File Storage)
# =============================================================================
class FileObjectModel(Base):
    __tablename__ = "file_objects"

    id = Column(String(128), primary_key=True)
    filename = Column(String(255), nullable=False)
    mime_type = Column(String(64), default="application/octet-stream")
    size_bytes = Column(BigInteger, nullable=False)
    sha256 = Column(String(64), index=True, nullable=False)
    dataset_id = Column(String(128), nullable=True)
    source_provider = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    metadata_json = Column("metadata", JSON, default=dict)

    chunks = relationship(
        "FileChunkModel",
        cascade="all, delete-orphan",
        back_populates="file_object",
        order_by="FileChunkModel.chunk_index",
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "filename": self.filename,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "dataset_id": self.dataset_id,
            "source_provider": self.source_provider,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata_json or {},
        }


class FileChunkModel(Base):
    __tablename__ = "file_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String(128), ForeignKey("file_objects.id", ondelete="CASCADE"), index=True, nullable=False)
    chunk_index = Column(Integer, index=True, nullable=False)
    chunk_size = Column(Integer, nullable=False)
    data = Column(LargeBinary, nullable=False)

    file_object = relationship("FileObjectModel", back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("file_id", "chunk_index", name="uq_file_chunk_index"),
        Index("ix_file_chunk_lookup", "file_id", "chunk_index"),
    )


# =============================================================================
# 3. Forecast Runs
# =============================================================================
class ForecastRunModel(Base):
    __tablename__ = "forecast_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    forecast_run_id = Column(String(128), unique=True, index=True, nullable=False)
    cycle = Column(String(32), nullable=False)
    initialization_time = Column(DateTime(timezone=True), index=True, nullable=False)
    valid_time = Column(DateTime(timezone=True), index=True, nullable=False)
    lead_time_hours = Column(Integer, index=True, nullable=False)
    model_version = Column(String(32), default="v2.0.0")
    dataset_version = Column(String(32), default="v1.8")
    data_mode = Column(String(32), default="REAL_OPERATIONAL")
    status = Column(String(32), index=True, default="SUCCESS")
    runtime_ms = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    provenance = Column(JSON, default=dict)
    manifest = Column(JSON, default=dict)
    sha256 = Column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_forecast_run_cycle_lead", "cycle", "lead_time_hours"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "forecast_run_id": self.forecast_run_id,
            "cycle": self.cycle,
            "initialization_time": self.initialization_time.isoformat() if self.initialization_time else None,
            "valid_time": self.valid_time.isoformat() if self.valid_time else None,
            "lead_time_hours": self.lead_time_hours,
            "model_version": self.model_version,
            "dataset_version": self.dataset_version,
            "data_mode": self.data_mode,
            "status": self.status,
            "runtime_ms": self.runtime_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "provenance": self.provenance or {},
            "manifest": self.manifest or {},
            "sha256": self.sha256,
        }


# =============================================================================
# 4. Forecast Grid (PostGIS Point Geometry)
# =============================================================================
class ForecastGridModel(Base):
    __tablename__ = "forecast_grid"

    id = Column(Integer, primary_key=True, autoincrement=True)
    forecast_run_id = Column(String(128), index=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    geometry = Column(SafeGeometry("POINT", srid=4326), nullable=True)
    ramp_precip_mm = Column(Float, default=0.0)
    raw_nwp_mm = Column(Float, default=0.0)
    correction_mm = Column(Float, default=0.0)
    neps_mean_mm = Column(Float, nullable=True)
    neps_spread_mm = Column(Float, nullable=True)
    imd_observation_mm = Column(Float, nullable=True)
    error_mm = Column(Float, nullable=True)
    absolute_error_mm = Column(Float, nullable=True)
    risk_class = Column(String(32), default="LIGHT")
    regime = Column(String(64), default="active_monsoon")
    regime_probability = Column(JSON, default=dict)
    extreme_probability = Column(JSON, default=dict)

    __table_args__ = (
        Index("ix_grid_run_lat_lon", "forecast_run_id", "latitude", "longitude"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "forecast_run_id": self.forecast_run_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "ramp_precip_mm": self.ramp_precip_mm,
            "raw_nwp_mm": self.raw_nwp_mm,
            "correction_mm": self.correction_mm,
            "neps_mean_mm": self.neps_mean_mm,
            "neps_spread_mm": self.neps_spread_mm,
            "imd_observation_mm": self.imd_observation_mm,
            "error_mm": self.error_mm,
            "absolute_error_mm": self.absolute_error_mm,
            "risk_class": self.risk_class,
            "regime": self.regime,
            "regime_probability": self.regime_probability or {},
            "extreme_probability": self.extreme_probability or {},
        }


# =============================================================================
# 5. Spatial Products: Districts & States (PostGIS Geometry)
# =============================================================================
class ForecastDistrictModel(Base):
    __tablename__ = "forecast_districts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    district_id = Column(String(64), index=True, nullable=False)
    district_name = Column(String(128), nullable=False)
    state_name = Column(String(128), nullable=False)
    geometry = Column(SafeGeometry("GEOMETRY", srid=4326), nullable=True)
    forecast_run_id = Column(String(128), index=True, nullable=False)
    mean_rainfall = Column(Float, default=0.0)
    median_rainfall = Column(Float, default=0.0)
    maximum_rainfall = Column(Float, default=0.0)
    p90 = Column(Float, default=0.0)
    p95 = Column(Float, default=0.0)
    p99 = Column(Float, default=0.0)
    risk_class = Column(String(32), default="LIGHT")
    peak_lat = Column(Float, nullable=True)
    peak_lon = Column(Float, nullable=True)
    affected_area_km2 = Column(Float, default=0.0)
    metadata_json = Column("metadata", JSON, default=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "district_id": self.district_id,
            "district_name": self.district_name,
            "state_name": self.state_name,
            "forecast_run_id": self.forecast_run_id,
            "mean_rainfall": self.mean_rainfall,
            "median_rainfall": self.median_rainfall,
            "maximum_rainfall": self.maximum_rainfall,
            "p90": self.p90,
            "p95": self.p95,
            "p99": self.p99,
            "risk_class": self.risk_class,
            "peak_lat": self.peak_lat,
            "peak_lon": self.peak_lon,
            "affected_area_km2": self.affected_area_km2,
            "metadata": self.metadata_json or {},
        }


class ForecastStateModel(Base):
    __tablename__ = "forecast_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    state_id = Column(String(64), index=True, nullable=False)
    state_name = Column(String(128), nullable=False)
    geometry = Column(SafeGeometry("GEOMETRY", srid=4326), nullable=True)
    forecast_run_id = Column(String(128), index=True, nullable=False)
    mean_rainfall = Column(Float, default=0.0)
    median_rainfall = Column(Float, default=0.0)
    maximum_rainfall = Column(Float, default=0.0)
    p90 = Column(Float, default=0.0)
    p95 = Column(Float, default=0.0)
    p99 = Column(Float, default=0.0)
    risk_class = Column(String(32), default="LIGHT")
    peak_lat = Column(Float, nullable=True)
    peak_lon = Column(Float, nullable=True)
    affected_area_km2 = Column(Float, default=0.0)
    metadata_json = Column("metadata", JSON, default=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "state_id": self.state_id,
            "state_name": self.state_name,
            "forecast_run_id": self.forecast_run_id,
            "mean_rainfall": self.mean_rainfall,
            "median_rainfall": self.median_rainfall,
            "maximum_rainfall": self.maximum_rainfall,
            "p90": self.p90,
            "p95": self.p95,
            "p99": self.p99,
            "risk_class": self.risk_class,
            "peak_lat": self.peak_lat,
            "peak_lon": self.peak_lon,
            "affected_area_km2": self.affected_area_km2,
            "metadata": self.metadata_json or {},
        }


# =============================================================================
# 6. Observations (IMD 0.25° Gridded Ground Truth)
# =============================================================================
class IMDObservationModel(Base):
    __tablename__ = "imd_observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(String(128), index=True, nullable=True)
    observation_time = Column(DateTime(timezone=True), index=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    geometry = Column(SafeGeometry("POINT", srid=4326), nullable=True)
    rainfall_mm = Column(Float, nullable=False)
    quality_flag = Column(String(32), default="VALID")
    source_file_id = Column(String(128), nullable=True)
    metadata_json = Column("metadata", JSON, default=dict)

    __table_args__ = (
        Index("ix_imd_obs_time_lat_lon", "observation_time", "latitude", "longitude"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "dataset_id": self.dataset_id,
            "observation_time": self.observation_time.isoformat() if self.observation_time else None,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "rainfall_mm": self.rainfall_mm,
            "quality_flag": self.quality_flag,
            "source_file_id": self.source_file_id,
            "metadata": self.metadata_json or {},
        }


# =============================================================================
# 7. NWP Inputs Catalog
# =============================================================================
class NWPFileModel(Base):
    __tablename__ = "nwp_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(String(128), index=True, nullable=True)
    provider = Column(String(64), nullable=False)  # NCMRWF | IMD | ECMWF
    model = Column(String(64), nullable=False)  # NCUM | NEPS | GFS
    cycle = Column(String(32), nullable=False)  # 00Z | 12Z
    initialization_time = Column(DateTime(timezone=True), nullable=False)
    valid_time = Column(DateTime(timezone=True), nullable=False)
    lead_time_hours = Column(Integer, nullable=False)
    filename = Column(String(255), nullable=False)
    file_object_id = Column(String(128), index=True, nullable=False)
    sha256 = Column(String(64), nullable=False)
    native_resolution = Column(String(32), nullable=True)
    variables = Column(JSON, default=list)
    metadata_json = Column("metadata", JSON, default=dict)
    quality_status = Column(String(32), default="VALIDATED")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "dataset_id": self.dataset_id,
            "provider": self.provider,
            "model": self.model,
            "cycle": self.cycle,
            "initialization_time": self.initialization_time.isoformat() if self.initialization_time else None,
            "valid_time": self.valid_time.isoformat() if self.valid_time else None,
            "lead_time_hours": self.lead_time_hours,
            "filename": self.filename,
            "file_object_id": self.file_object_id,
            "sha256": self.sha256,
            "native_resolution": self.native_resolution,
            "variables": self.variables or [],
            "metadata": self.metadata_json or {},
            "quality_status": self.quality_status,
        }


# =============================================================================
# 8. Forecast Provenance (Immutable Execution Manifests)
# =============================================================================
class ForecastProvenanceModel(Base):
    __tablename__ = "forecast_provenance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    forecast_run_id = Column(String(128), unique=True, index=True, nullable=False)
    input_file_ids = Column(JSON, default=list)
    input_hashes = Column(JSON, default=dict)
    model_version = Column(String(32), default="v2.0.0")
    model_hash = Column(String(64), nullable=True)
    dataset_version = Column(String(32), default="v1.8")
    feature_contract = Column(String(64), default="ramp_features_v1.0.0")
    target_contract = Column(String(64), default="ramp_targets_v1.0.0")
    calibration_version = Column(String(32), default="v1.0")
    software_version = Column(String(32), default="2.0.0")
    git_commit = Column(String(64), nullable=True)
    data_mode = Column(String(32), default="REAL_OPERATIONAL")
    generated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    manifest = Column(JSON, default=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "forecast_run_id": self.forecast_run_id,
            "input_file_ids": self.input_file_ids or [],
            "input_hashes": self.input_hashes or {},
            "model_version": self.model_version,
            "model_hash": self.model_hash,
            "dataset_version": self.dataset_version,
            "feature_contract": self.feature_contract,
            "target_contract": self.target_contract,
            "calibration_version": self.calibration_version,
            "software_version": self.software_version,
            "git_commit": self.git_commit,
            "data_mode": self.data_mode,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "manifest": self.manifest or {},
        }


# =============================================================================
# 9. Audit Events (Append-Only Cryptographic Chain)
# =============================================================================
class AuditEventModel(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(128), unique=True, index=True, nullable=False)
    event_type = Column(String(64), index=True, nullable=False)
    timestamp_utc = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    actor_role = Column(String(32), default="SYSTEM")
    actor_id = Column(String(128), default="RAMP_DAEMON")
    details = Column(JSON, default=dict)
    sha256_signature = Column(String(64), nullable=False)
    previous_hash = Column(String(64), nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp_utc": self.timestamp_utc.isoformat() if self.timestamp_utc else None,
            "actor_role": self.actor_role,
            "actor_id": self.actor_id,
            "details": self.details or {},
            "sha256_signature": self.sha256_signature,
            "previous_hash": self.previous_hash,
        }
