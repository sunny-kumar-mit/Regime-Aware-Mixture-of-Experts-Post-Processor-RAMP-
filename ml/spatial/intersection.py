"""
RAMP Grid -> District Spatial Intersection Engine
SIH26080 | Spatial Forecast Products & District Aggregation
MoES / NCMRWF
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from shapely.geometry import Polygon, MultiPolygon
from shapely.strtree import STRtree

from ml.spatial.grid import GridCell
from ml.spatial.boundaries import DistrictBoundary, compute_physical_area_km2


@dataclass
class IntersectionRecord:
    """
    Intersection relationship between a GridCell and a DistrictBoundary.
    """
    grid_id: str
    district_id: str
    state_id: str
    intersection_area_km2: float
    intersection_fraction: float  # Fraction of grid cell that lies inside district
    district_coverage_fraction: float  # Fraction of district area represented by this cell
    grid_cell: GridCell

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grid_id": self.grid_id,
            "district_id": self.district_id,
            "state_id": self.state_id,
            "intersection_area_km2": round(self.intersection_area_km2, 2),
            "intersection_fraction": round(self.intersection_fraction, 4),
            "district_coverage_fraction": round(self.district_coverage_fraction, 6),
            "rainfall_prediction_mm": self.grid_cell.rainfall_prediction_mm,
            "heavy_probability": self.grid_cell.heavy_probability,
            "very_heavy_probability": self.grid_cell.very_heavy_probability,
            "extreme_probability": self.grid_cell.extreme_probability,
        }


class GridDistrictIntersectionEngine:
    """
    Performs computational geometry intersection between canonical 0.25° grid cells
    and administrative district boundaries using Shapely spatial indexing.
    """

    @classmethod
    def intersect_district_with_cells(
        cls,
        district: DistrictBoundary,
        cells: List[GridCell],
    ) -> List[IntersectionRecord]:
        """
        Intersects a single DistrictBoundary with a collection of GridCells.
        """
        records: List[IntersectionRecord] = []
        dist_geom = district.geometry
        if dist_geom.is_empty:
            return records

        # Filter candidate cells using bounding box check first for efficiency
        min_lon, min_lat, max_lon, max_lat = dist_geom.bounds

        for cell in cells:
            c_bounds = cell.bounds
            # Quick bounding box overlap rejection
            if (
                c_bounds[2] < min_lon
                or c_bounds[0] > max_lon
                or c_bounds[3] < min_lat
                or c_bounds[1] > max_lat
            ):
                continue

            cell_poly = cell.polygon
            if not dist_geom.intersects(cell_poly):
                continue

            try:
                inter_geom = dist_geom.intersection(cell_poly)
                if inter_geom.is_empty or inter_geom.area <= 0.0:
                    continue

                inter_area_km2 = compute_physical_area_km2(inter_geom)
                cell_area_km2 = cell.cell_area_km2
                fraction = min(1.0, max(0.0, inter_area_km2 / max(1e-6, cell_area_km2)))
                dist_frac = inter_area_km2 / max(1e-6, district.area_km2)

                if inter_area_km2 > 0.01:  # reject negligible precision slivers
                    rec = IntersectionRecord(
                        grid_id=cell.grid_id,
                        district_id=district.district_id,
                        state_id=district.state_id,
                        intersection_area_km2=round(inter_area_km2, 2),
                        intersection_fraction=round(fraction, 4),
                        district_coverage_fraction=round(dist_frac, 6),
                        grid_cell=cell,
                    )
                    records.append(rec)
            except Exception:
                continue

        return records

    @classmethod
    def intersect_all_districts(
        cls,
        districts: List[DistrictBoundary],
        cells: List[GridCell],
    ) -> Dict[str, List[IntersectionRecord]]:
        """
        Intersects all districts with grid cells, returning a mapping of district_id -> records.
        """
        results: Dict[str, List[IntersectionRecord]] = {}
        for d in districts:
            recs = cls.intersect_district_with_cells(d, cells)
            results[d.district_id] = recs
        return results
