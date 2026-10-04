"""
RAMP Meteorological File Store
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

High-level meteorological file storage managing:
  - Raw binary files via PostgresStorageProvider
  - NWP file registry in `nwp_files`
  - IMD observation point records in `imd_observations`
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Union

from sqlalchemy import select
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

try:
    from .connection import DatabaseManager
    from .models import IMDObservationModel, NWPFileModel
    from .postgres_storage import PostgresStorageProvider
except (ImportError, ValueError):
    from ramp.storage.connection import DatabaseManager
    from ramp.storage.models import IMDObservationModel, NWPFileModel
    from ramp.storage.postgres_storage import PostgresStorageProvider

logger = logging.getLogger(__name__)


class MeteorologicalFileStore:
    """
    Manages raw meteorological file storage in PostgreSQL + PostGIS.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager.get_instance()
        self.storage = PostgresStorageProvider(self.db)

    def store_nwp_file(
        self,
        provider: str,
        model: str,
        cycle: str,
        initialization_time: datetime,
        valid_time: datetime,
        lead_time_hours: int,
        filename: str,
        data: Union[bytes, BinaryIO],
        dataset_id: Optional[str] = None,
        native_resolution: str = "0.12°",
        variables: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Stores an NWP file (NCUM/NEPS) into PostgreSQL chunked storage and registers its metadata.
        """
        file_id = f"nwp_{provider.lower()}_{model.lower()}_{cycle}_{lead_time_hours}h_{Path(filename).stem}"
        upload_meta = self.storage.upload(
            file_id=file_id,
            filename=filename,
            data=data,
            dataset_id=dataset_id,
            source_provider=provider,
            mime_type="application/x-netcdf" if filename.endswith((".nc", ".nc4")) else "application/octet-stream",
            metadata=metadata or {},
        )

        with self.db.session() as session:
            # Register in nwp_files
            nwp_record = NWPFileModel(
                dataset_id=dataset_id,
                provider=provider,
                model=model,
                cycle=cycle,
                initialization_time=initialization_time,
                valid_time=valid_time,
                lead_time_hours=lead_time_hours,
                filename=filename,
                file_object_id=file_id,
                sha256=upload_meta["sha256"],
                native_resolution=native_resolution,
                variables=variables or [],
                metadata_json=metadata or {},
                quality_status="VALIDATED",
            )
            session.add(nwp_record)

        return {**upload_meta, "nwp_file_id": file_id}

    def store_imd_observation(
        self,
        observation_date: datetime,
        latitude: float,
        longitude: float,
        rainfall_mm: float,
        dataset_id: Optional[str] = None,
        source_file_id: Optional[str] = None,
        quality_flag: str = "VALID",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Stores an IMD gridded observation cell with PostGIS Point geometry.
        """
        pt_geom = None
        if not self.db.is_sqlite:
            pt_geom = f"SRID=4326;POINT({longitude} {latitude})"

        with self.db.session() as session:
            obs = IMDObservationModel(
                dataset_id=dataset_id,
                observation_time=observation_date,
                latitude=latitude,
                longitude=longitude,
                geometry=pt_geom,
                rainfall_mm=rainfall_mm,
                quality_flag=quality_flag,
                source_file_id=source_file_id,
                metadata_json=metadata or {},
            )
            session.add(obs)
            session.flush()
            return obs.to_dict()

    def register_nwp_file(
        self,
        nwp_id: str,
        dataset_id: Optional[str],
        provider: str,
        model: str,
        cycle: str,
        initialization_time: datetime,
        valid_time: datetime,
        lead_time_hours: int,
        filename: str,
        file_object_id: str,
        sha256: str,
        native_resolution: str = "0.12°",
        variables: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        quality_status: str = "VALIDATED",
    ) -> Dict[str, Any]:
        """Registers metadata for an NWP file object."""
        with self.db.session() as session:
            nwp_record = NWPFileModel(
                dataset_id=dataset_id,
                provider=provider,
                model=model,
                cycle=cycle,
                initialization_time=initialization_time,
                valid_time=valid_time,
                lead_time_hours=lead_time_hours,
                filename=filename,
                file_object_id=file_object_id,
                sha256=sha256,
                native_resolution=native_resolution,
                variables=variables or [],
                metadata_json=metadata or {},
                quality_status=quality_status,
            )
            session.add(nwp_record)
            session.flush()
            return nwp_record.to_dict()

    def bulk_insert_observations(
        self,
        dataset_id: str,
        observation_time: datetime,
        observations: List[Dict[str, Any]],
        source_file_id: Optional[str] = None,
    ) -> int:
        """Bulk inserts IMD gridded observation points with PostGIS geometries."""
        records = []
        for o in observations:
            lat = o["latitude"]
            lon = o["longitude"]
            pt_geom = None if self.db.is_sqlite else f"SRID=4326;POINT({lon} {lat})"
            records.append(
                IMDObservationModel(
                    dataset_id=dataset_id,
                    observation_time=observation_time,
                    latitude=lat,
                    longitude=lon,
                    geometry=pt_geom,
                    rainfall_mm=o.get("rainfall_mm", 0.0),
                    quality_flag=o.get("quality_flag", "VALID"),
                    source_file_id=source_file_id,
                    metadata_json=o.get("metadata", {}),
                )
            )
        with self.db.session() as session:
            session.add_all(records)
        return len(records)

    def get_observations_in_bbox(
        self,
        min_lat: float,
        max_lat: float,
        min_lon: float,
        max_lon: float,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves observations within bounding box and time window."""
        with self.db.session() as session:
            stmt = select(IMDObservationModel).where(
                IMDObservationModel.latitude >= min_lat,
                IMDObservationModel.latitude <= max_lat,
                IMDObservationModel.longitude >= min_lon,
                IMDObservationModel.longitude <= max_lon,
            )
            if start_time:
                stmt = stmt.where(IMDObservationModel.observation_time >= start_time)
            if end_time:
                stmt = stmt.where(IMDObservationModel.observation_time <= end_time)
            obs = session.execute(stmt).scalars().all()
            return [o.to_dict() for o in obs]

    def get_raw_file(self, file_id: str) -> bytes:
        """Retrieves raw meteorological file content."""
        return self.storage.download(file_id)

    def stream_raw_file(self, file_id: str):
        """Streams raw meteorological file content."""
        return self.storage.stream(file_id)
