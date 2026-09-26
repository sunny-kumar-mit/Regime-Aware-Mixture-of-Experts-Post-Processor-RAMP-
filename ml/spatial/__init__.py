"""
RAMP Spatial Forecast Products & District Aggregation Package
SIH26080 | MoES / NCMRWF
"""

from ml.spatial.grid import GridCell, SpatialGridEngine
from ml.spatial.boundaries import DistrictBoundary, AdministrativeBoundaryProvider
from ml.spatial.intersection import IntersectionRecord, GridDistrictIntersectionEngine
from ml.spatial.uncertainty import SpatialUncertaintyEngine
from ml.spatial.risk import DistrictRiskClassifier
from ml.spatial.aggregation import DistrictAggregationEngine
from ml.spatial.products import DistrictForecastProduct, StateForecastProduct, NationalForecastSummary
from ml.spatial.fss import FractionsSkillScoreService
from ml.spatial.export import GISExportService
from ml.spatial.registry import SpatialProductRegistry, SPATIAL_PRODUCT_VERSION
from ml.spatial.validation import SpatialValidator, SpatialValidationError

__all__ = [
    "GridCell",
    "SpatialGridEngine",
    "DistrictBoundary",
    "AdministrativeBoundaryProvider",
    "IntersectionRecord",
    "GridDistrictIntersectionEngine",
    "SpatialUncertaintyEngine",
    "DistrictRiskClassifier",
    "DistrictAggregationEngine",
    "DistrictForecastProduct",
    "StateForecastProduct",
    "NationalForecastSummary",
    "FractionsSkillScoreService",
    "GISExportService",
    "SpatialProductRegistry",
    "SPATIAL_PRODUCT_VERSION",
    "SpatialValidator",
    "SpatialValidationError",
]
