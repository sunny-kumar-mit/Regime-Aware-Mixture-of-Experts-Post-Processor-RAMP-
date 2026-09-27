"""
RAMP Operational Data Ingestion & Real-Data Activation Package
SIH26080 | Phase 16 — Real-Data Activation & Operational Ingestion
MoES / NCMRWF
"""

from ml.ingestion.activation import (
    ActivationAuditRecord,
    ActivationStage,
    ActivationStatusReport,
    GateCheckResult,
    RealDataActivationEngine,
)
from ml.ingestion.adapters import (
    AdapterIngestionResult,
    IMDObservationAdapter,
    NCUMAdapter,
    NEPSAdapter,
)
from ml.ingestion.discovery import (
    DiscoveredOperationalFile,
    DiscoveryCatalog,
    OperationalFileDiscoveryService,
)
from ml.ingestion.integrity import (
    FileIntegrityEngine,
    FileIntegrityRecord,
    IntegrityManifest,
)
from ml.ingestion.metadata import (
    MetadataValidationResult,
    MetadataValidator,
)
from ml.ingestion.pairing import (
    ForecastObservationPairingEngine,
    PairingManifest,
)
from ml.ingestion.qc import (
    DatasetQCReport,
    MeteorologicalQCEngine,
    VariableQCResult,
)
from ml.ingestion.registry import SourceRegistry
from ml.ingestion.sources import (
    AUTHORITATIVE_SOURCE_CONTRACTS,
    AuthorityLevel,
    CANONICAL_18_PREDICTORS,
    DatasetType,
    SourceContract,
    SourceStatus,
    get_authoritative_contract,
    list_authoritative_contracts,
)
from ml.ingestion.spatial import (
    RAMP_DOMAIN,
    SpatialValidationResult,
    SpatialValidator,
)
from ml.ingestion.temporal import (
    TemporalValidationResult,
    TemporalValidator,
)
from ml.ingestion.units import (
    UnitNormalizer,
    UnitValidationError,
)
from ml.ingestion.verification import (
    ModelVerificationMetrics,
    RealOperationalVerificationReport,
    RealVerificationEngine,
)

__all__ = [
    "AuthorityLevel",
    "SourceStatus",
    "DatasetType",
    "SourceContract",
    "CANONICAL_18_PREDICTORS",
    "AUTHORITATIVE_SOURCE_CONTRACTS",
    "get_authoritative_contract",
    "list_authoritative_contracts",
    "FileIntegrityEngine",
    "FileIntegrityRecord",
    "IntegrityManifest",
    "MetadataValidator",
    "MetadataValidationResult",
    "SpatialValidator",
    "SpatialValidationResult",
    "RAMP_DOMAIN",
    "TemporalValidator",
    "TemporalValidationResult",
    "UnitNormalizer",
    "UnitValidationError",
    "MeteorologicalQCEngine",
    "VariableQCResult",
    "DatasetQCReport",
    "OperationalFileDiscoveryService",
    "DiscoveredOperationalFile",
    "DiscoveryCatalog",
    "ForecastObservationPairingEngine",
    "PairingManifest",
    "NCUMAdapter",
    "NEPSAdapter",
    "IMDObservationAdapter",
    "AdapterIngestionResult",
    "SourceRegistry",
    "RealDataActivationEngine",
    "ActivationStage",
    "ActivationStatusReport",
    "GateCheckResult",
    "ActivationAuditRecord",
    "RealVerificationEngine",
    "RealOperationalVerificationReport",
    "ModelVerificationMetrics",
]
