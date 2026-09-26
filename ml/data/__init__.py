"""
Phase 8 Meteorological Data Integration Layer
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF
"""

from ml.data.contract import CanonicalRecord, DataMode, DatasetContract, validate_canonical_dataframe
from ml.data.units import UnitNormalizer
from ml.data.quality import MeteorologicalQualityControl, QualityReportData, MissingDataPolicy
from ml.data.alignment import TemporalAlignmentEngine, SpatialAlignmentEngine
from ml.data.discovery import DataDiscoveryService, DiscoverySummary
from ml.data.manifest import DatasetManifest
from ml.data.readiness import RealDataReadinessChecker

__all__ = [
    "CanonicalRecord",
    "DataMode",
    "DatasetContract",
    "validate_canonical_dataframe",
    "UnitNormalizer",
    "MeteorologicalQualityControl",
    "QualityReportData",
    "MissingDataPolicy",
    "TemporalAlignmentEngine",
    "SpatialAlignmentEngine",
    "DataDiscoveryService",
    "DiscoverySummary",
    "DatasetManifest",
    "RealDataReadinessChecker",
]
