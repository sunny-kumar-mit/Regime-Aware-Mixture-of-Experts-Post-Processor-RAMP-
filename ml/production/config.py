"""
RAMP Production Environment Configuration & Safety Validator
SIH26080 | Phase 17 — Production Deployment & Operational Reliability
MoES / NCMRWF
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AppEnvironment(str, Enum):
    DEVELOPMENT = "DEVELOPMENT"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"


class OperationalDataMode(str, Enum):
    SYNTHETIC_DEMO = "SYNTHETIC_DEMO"
    STAGING_REAL_DATA = "STAGING_REAL_DATA"
    REAL_OPERATIONAL = "REAL_OPERATIONAL"
    NOT_AVAILABLE = "NOT_AVAILABLE"


@dataclass
class ProductionConfig:
    """Production deployment configuration container."""
    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    data_mode: OperationalDataMode = OperationalDataMode.SYNTHETIC_DEMO
    ncmrwf_data_root: str = "data/ncmrwf"
    imd_data_root: str = "data/imd"
    model_registry_root: str = "ml/model_registry"
    forecast_output_root: str = "data/processed/forecasts"
    audit_root: str = "data/audit"
    log_root: str = "data/logs"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    secret_key: str = "ramp-operational-secret-key-change-in-production-min32"
    require_authoritative_mount: bool = False
    enable_staging_mode: bool = False
    max_request_body_bytes: int = 50 * 1024 * 1024  # 50 MB
    request_timeout_seconds: int = 60

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["app_env"] = self.app_env.value
        d["data_mode"] = self.data_mode.value
        # Redact secret key
        d["secret_key"] = "[REDACTED]"
        return d


class ConfigurationValidationError(Exception):
    """Raised when production configuration fails strict safety verification."""
    pass


class ProductionConfigValidator:
    """
    Validates environment configurations against institutional MoES/NCMRWF rules.
    Guarantees that production systems never boot with unsafe fallbacks or invalid paths.
    """

    @classmethod
    def validate_config(cls, config: ProductionConfig) -> List[str]:
        """
        Validates configuration and returns list of errors.
        Raises ConfigurationValidationError if in PRODUCTION and errors exist.
        """
        errors: List[str] = []

        # 1. Port safety
        if not (1024 <= config.app_port <= 65535):
            errors.append(f"Invalid app_port {config.app_port}: must be between 1024 and 65535.")

        # 2. Secret key length in PRODUCTION
        if config.app_env == AppEnvironment.PRODUCTION:
            if len(config.secret_key) < 32 or "change-in-production" in config.secret_key:
                errors.append("PRODUCTION secret_key must be at least 32 characters and cannot use default template.")

        # 3. Model registry presence
        model_path = Path(config.model_registry_root)
        if not model_path.exists():
            errors.append(f"Model registry root does not exist: {model_path}")

        # 4. In PRODUCTION: Must not silently default to SYNTHETIC_DEMO unless explicitly configured
        if config.app_env == AppEnvironment.PRODUCTION:
            if config.data_mode == OperationalDataMode.SYNTHETIC_DEMO and not os.environ.get("RAMP_ALLOW_DEMO_IN_PROD"):
                errors.append(
                    "PRODUCTION environment cannot run in SYNTHETIC_DEMO without explicit RAMP_ALLOW_DEMO_IN_PROD=1."
                )

        # 5. Authoritative data mounts check
        if config.require_authoritative_mount or config.data_mode == OperationalDataMode.REAL_OPERATIONAL:
            ncmrwf_path = Path(config.ncmrwf_data_root)
            imd_path = Path(config.imd_data_root)
            if not ncmrwf_path.exists() or not any(ncmrwf_path.iterdir() if ncmrwf_path.exists() else []):
                errors.append(
                    f"Authoritative NCMRWF data root '{config.ncmrwf_data_root}' is missing or empty. "
                    "Cannot enable REAL_OPERATIONAL."
                )
            if not imd_path.exists() or not any(imd_path.iterdir() if imd_path.exists() else []):
                errors.append(
                    f"Authoritative IMD data root '{config.imd_data_root}' is missing or empty. "
                    "Cannot enable REAL_OPERATIONAL."
                )

        # 6. Audit & Log roots exist or can be created
        for p_name, p_val in [("audit_root", config.audit_root), ("log_root", config.log_root), ("forecast_output_root", config.forecast_output_root)]:
            p = Path(p_val)
            try:
                p.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot initialize or write to {p_name} '{p_val}': {e}")

        if config.app_env == AppEnvironment.PRODUCTION and errors:
            raise ConfigurationValidationError(
                f"Production configuration validation failed with {len(errors)} error(s):\n" + "\n".join(f"- {e}" for e in errors)
            )

        return errors


def get_production_config() -> ProductionConfig:
    """Loads configuration from environment variables with safe defaults."""
    env_str = os.environ.get("APP_ENV", "DEVELOPMENT").upper()
    try:
        app_env = AppEnvironment(env_str)
    except ValueError:
        app_env = AppEnvironment.DEVELOPMENT

    mode_str = os.environ.get("RAMP_DATA_MODE", "SYNTHETIC_DEMO").upper()
    try:
        data_mode = OperationalDataMode(mode_str)
    except ValueError:
        data_mode = OperationalDataMode.SYNTHETIC_DEMO

    # Port
    try:
        port = int(os.environ.get("APP_PORT", "8000"))
    except ValueError:
        port = 8000

    cfg = ProductionConfig(
        app_env=app_env,
        data_mode=data_mode,
        ncmrwf_data_root=os.environ.get("NCMRWF_DATA_ROOT", "data/ncmrwf"),
        imd_data_root=os.environ.get("IMD_DATA_ROOT", "data/imd"),
        model_registry_root=os.environ.get("MODEL_REGISTRY_ROOT", "ml/model_registry"),
        forecast_output_root=os.environ.get("FORECAST_OUTPUT_ROOT", "data/processed/forecasts"),
        audit_root=os.environ.get("AUDIT_ROOT", "data/audit"),
        log_root=os.environ.get("LOG_ROOT", "data/logs"),
        app_host=os.environ.get("APP_HOST", "0.0.0.0"),
        app_port=port,
        secret_key=os.environ.get("SECRET_KEY", "ramp-operational-secret-key-change-in-production-min32"),
        require_authoritative_mount=os.environ.get("REQUIRE_AUTHORITATIVE_MOUNT", "0") in ("1", "true", "TRUE"),
        enable_staging_mode=os.environ.get("ENABLE_STAGING_MODE", "0") in ("1", "true", "TRUE"),
    )

    return cfg
