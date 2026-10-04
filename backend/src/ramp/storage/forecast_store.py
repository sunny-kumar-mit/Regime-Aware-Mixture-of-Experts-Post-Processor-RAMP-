"""
RAMP Forecast Persistence & PostGIS Spatial Products Store
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Handles persistent storage and spatial retrieval of:
  - forecast_runs (execution metadata and run envelope)
  - forecast_grid (canonical 0.25° grid with PostGIS Point geometries)
  - forecast_districts (area-weighted district summaries with polygon geometries)
  - forecast_states (state synoptic summaries)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, select, text
from geoalchemy2.functions import ST_AsGeoJSON

try:
    from .connection import DatabaseManager
    from .models import (
        ForecastDistrictModel,
        ForecastGridModel,
        ForecastRunModel,
        ForecastStateModel,
    )
    from .repository import BaseRepository
except (ImportError, ValueError):
    from ramp.storage.connection import DatabaseManager
    from ramp.storage.models import (
        ForecastDistrictModel,
        ForecastGridModel,
        ForecastRunModel,
        ForecastStateModel,
    )
    from ramp.storage.repository import BaseRepository

logger = logging.getLogger(__name__)


class ForecastStore(BaseRepository):
    """
    Manages operational forecast runs and PostGIS spatial products.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        super().__init__(db_manager)

    def persist_forecast_run(
        self,
        forecast_run_id: str,
        cycle: str,
        initialization_time: datetime,
        valid_time: datetime,
        lead_time_hours: int,
        grid_cells: List[Dict[str, Any]],
        districts: Optional[List[Dict[str, Any]]] = None,
        states: Optional[List[Dict[str, Any]]] = None,
        model_version: str = "v2.0.0",
        dataset_version: str = "v1.8",
        data_mode: str = "REAL_OPERATIONAL",
        status: str = "SUCCESS",
        runtime_ms: float = 0.0,
        provenance: Optional[Dict[str, Any]] = None,
        manifest: Optional[Dict[str, Any]] = None,
        sha256: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Persists a complete forecast execution: run record, PostGIS grid cells (batched),
        and district/state aggregations.
        """
        with self.db.session() as session:
            # 1. Clean existing run if re-running
            session.execute(delete(ForecastGridModel).where(ForecastGridModel.forecast_run_id == forecast_run_id))
            session.execute(delete(ForecastDistrictModel).where(ForecastDistrictModel.forecast_run_id == forecast_run_id))
            session.execute(delete(ForecastStateModel).where(ForecastStateModel.forecast_run_id == forecast_run_id))
            session.execute(delete(ForecastRunModel).where(ForecastRunModel.forecast_run_id == forecast_run_id))
            session.flush()

            # 2. Insert run record
            run_rec = ForecastRunModel(
                forecast_run_id=forecast_run_id,
                cycle=cycle,
                initialization_time=initialization_time,
                valid_time=valid_time,
                lead_time_hours=lead_time_hours,
                model_version=model_version,
                dataset_version=dataset_version,
                data_mode=data_mode,
                status=status,
                runtime_ms=runtime_ms,
                provenance=provenance or {},
                manifest=manifest or {},
                sha256=sha256,
            )
            session.add(run_rec)
            session.flush()

            # 3. Batch insert grid cells
            grid_models: List[ForecastGridModel] = []
            for c in grid_cells:
                lat = float(c.get("latitude", c.get("lat", 0.0)))
                lon = float(c.get("longitude", c.get("lon", 0.0)))

                pt_geom = None
                if not self.db.is_sqlite:
                    pt_geom = f"SRID=4326;POINT({lon} {lat})"

                grid_models.append(
                    ForecastGridModel(
                        forecast_run_id=forecast_run_id,
                        latitude=lat,
                        longitude=lon,
                        geometry=pt_geom,
                        ramp_precip_mm=float(c.get("ramp_precip_mm", c.get("ramp", 0.0))),
                        raw_nwp_mm=float(c.get("raw_nwp_mm", c.get("raw_ncum", 0.0))),
                        correction_mm=float(c.get("correction_mm", c.get("correction", 0.0))),
                        neps_mean_mm=float(c["neps_mean_mm"]) if c.get("neps_mean_mm") is not None else None,
                        neps_spread_mm=float(c["neps_spread_mm"]) if c.get("neps_spread_mm") is not None else None,
                        imd_observation_mm=float(c["imd_observation_mm"]) if c.get("imd_observation_mm") is not None else (float(c["imd_obs"]) if c.get("imd_obs") is not None else None),
                        error_mm=float(c["error_mm"]) if c.get("error_mm") is not None else (float(c["error"]) if c.get("error") is not None else None),
                        absolute_error_mm=float(c["absolute_error_mm"]) if c.get("absolute_error_mm") is not None else (float(c["abs_error"]) if c.get("abs_error") is not None else None),
                        risk_class=c.get("risk_class", "LIGHT"),
                        regime=c.get("regime", "active_monsoon"),
                        regime_probability=c.get("regime_probability", c.get("regime_probabilities", {})),
                        extreme_probability=c.get("extreme_probability", {
                            "p64": c.get("prob_extreme", 0.0),
                            "p115": c.get("prob_very_heavy", 0.0),
                        }),
                    )
                )

            inserted_cells = self.bulk_insert_batch(session, grid_models, batch_size=500)

            # 4. Insert district aggregations
            if districts:
                dist_models = [
                    ForecastDistrictModel(
                        district_id=d.get("district_id", d.get("name", "")),
                        district_name=d.get("district_name", d.get("name", "")),
                        state_name=d.get("state_name", d.get("state", "")),
                        forecast_run_id=forecast_run_id,
                        mean_rainfall=float(d.get("mean_rainfall", d.get("mean", 0.0))),
                        median_rainfall=float(d.get("median_rainfall", d.get("median", 0.0))),
                        maximum_rainfall=float(d.get("maximum_rainfall", d.get("max", 0.0))),
                        p90=float(d.get("p90", 0.0)),
                        p95=float(d.get("p95", 0.0)),
                        p99=float(d.get("p99", 0.0)),
                        risk_class=d.get("risk_class", "LIGHT"),
                        peak_lat=float(d["peak_lat"]) if d.get("peak_lat") is not None else None,
                        peak_lon=float(d["peak_lon"]) if d.get("peak_lon") is not None else None,
                        affected_area_km2=float(d.get("affected_area_km2", 0.0)),
                        metadata_json=d.get("metadata", {}),
                    )
                    for d in districts
                ]
                self.bulk_insert_batch(session, dist_models, batch_size=250)

            # 5. Insert state aggregations
            if states:
                state_models = [
                    ForecastStateModel(
                        state_id=s.get("state_id", s.get("name", "")),
                        state_name=s.get("state_name", s.get("name", "")),
                        forecast_run_id=forecast_run_id,
                        mean_rainfall=float(s.get("mean_rainfall", s.get("mean", 0.0))),
                        median_rainfall=float(s.get("median_rainfall", s.get("median", 0.0))),
                        maximum_rainfall=float(s.get("maximum_rainfall", s.get("max", 0.0))),
                        p90=float(s.get("p90", 0.0)),
                        p95=float(s.get("p95", 0.0)),
                        p99=float(s.get("p99", 0.0)),
                        risk_class=s.get("risk_class", "LIGHT"),
                        peak_lat=float(s["peak_lat"]) if s.get("peak_lat") is not None else None,
                        peak_lon=float(s["peak_lon"]) if s.get("peak_lon") is not None else None,
                        affected_area_km2=float(s.get("affected_area_km2", 0.0)),
                        metadata_json=s.get("metadata", {}),
                    )
                    for s in states
                ]
                self.bulk_insert_batch(session, state_models, batch_size=100)

        logger.info(
            f"Successfully persisted forecast run {forecast_run_id} to PostgreSQL: "
            f"{inserted_cells} cells, {len(districts or [])} districts, {len(states or [])} states."
        )

        return {
            "status": "SUCCESS",
            "forecast_run_id": forecast_run_id,
            "grid_cells_persisted": inserted_cells,
            "districts_persisted": len(districts or []),
            "states_persisted": len(states or []),
            "grid_count": inserted_cells,
            "district_count": len(districts or []),
            "state_count": len(states or []),
        }

    def get_forecast_run(self, forecast_run_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves metadata of a forecast run."""
        with self.db.session() as session:
            rec = session.execute(
                select(ForecastRunModel).where(ForecastRunModel.forecast_run_id == forecast_run_id)
            ).scalar_one_or_none()
            return rec.to_dict() if rec else None

    def get_grid_cells(self, forecast_run_id: str) -> List[Dict[str, Any]]:
        """Retrieves all grid cells for a forecast run."""
        with self.db.session() as session:
            cells = session.execute(
                select(ForecastGridModel).where(ForecastGridModel.forecast_run_id == forecast_run_id)
            ).scalars().all()
            return [c.to_dict() for c in cells]

    def get_districts(self, forecast_run_id: str) -> List[Dict[str, Any]]:
        """Retrieves area-weighted district aggregations."""
        with self.db.session() as session:
            dists = session.execute(
                select(ForecastDistrictModel).where(ForecastDistrictModel.forecast_run_id == forecast_run_id)
            ).scalars().all()
            return [d.to_dict() for d in dists]

    def get_states(self, forecast_run_id: str) -> List[Dict[str, Any]]:
        """Retrieves state aggregations."""
        with self.db.session() as session:
            sts = session.execute(
                select(ForecastStateModel).where(ForecastStateModel.forecast_run_id == forecast_run_id)
            ).scalars().all()
            return [s.to_dict() for s in sts]

    def generate_geojson(self, forecast_run_id: str) -> Dict[str, Any]:
        """
        Generates GeoJSON FeatureCollection using PostGIS ST_AsGeoJSON when available,
        or Python geometry serialization.
        """
        with self.db.session() as session:
            run_meta = self.get_forecast_run(forecast_run_id) or {}
            features = []

            if not self.db.is_sqlite:
                # Query with PostGIS ST_AsGeoJSON
                try:
                    stmt = select(
                        ForecastGridModel,
                        func.ST_AsGeoJSON(ForecastGridModel.geometry).label("geom_json"),
                    ).where(ForecastGridModel.forecast_run_id == forecast_run_id)
                    results = session.execute(stmt).all()

                    for row in results:
                        cell = row[0]
                        geom_str = row[1]
                        geom = json.loads(geom_str) if geom_str else {
                            "type": "Point",
                            "coordinates": [cell.longitude, cell.latitude],
                        }
                        features.append({
                            "type": "Feature",
                            "id": f"G_{cell.latitude}_{cell.longitude}",
                            "geometry": geom,
                            "properties": cell.to_dict(),
                        })
                except Exception as pg_err:
                    logger.warning(f"PostGIS ST_AsGeoJSON failed ({pg_err}), falling back to Python geometry.")
                    cells = self.get_grid_cells(forecast_run_id)
                    for c in cells:
                        features.append({
                            "type": "Feature",
                            "id": f"G_{c['latitude']}_{c['longitude']}",
                            "geometry": {"type": "Point", "coordinates": [c["longitude"], c["latitude"]]},
                            "properties": c,
                        })
            else:
                cells = self.get_grid_cells(forecast_run_id)
                for c in cells:
                    features.append({
                        "type": "Feature",
                        "id": f"G_{c['latitude']}_{c['longitude']}",
                        "geometry": {"type": "Point", "coordinates": [c["longitude"], c["latitude"]]},
                        "properties": c,
                    })

            return {
                "type": "FeatureCollection",
                "metadata": run_meta.get("provenance", {}),
                "features": features,
            }
