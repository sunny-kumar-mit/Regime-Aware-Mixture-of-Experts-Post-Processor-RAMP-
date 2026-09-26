"""
RAMP Configuration Module
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
"""

from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env files."""

    model_config = SettingsConfigDict(
        env_file=(".env", "configs/dev.env", "config/dev.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application Metadata
    APP_NAME: str = "RAMP-MoES-NCMRWF"
    APP_DESCRIPTION: str = (
        "Regime-Aware Mixture-of-Experts Post-Processor for Monsoon Rainfall Forecasts"
    )
    APP_ENV: str = "development"
    VERSION: str = "0.1.0"
    ORGANIZATION: str = "Ministry of Earth Sciences (MoES)"
    DEPARTMENT: str = "National Centre for Medium Range Weather Forecasting (NCMRWF)"

    # Server Networking
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    API_PREFIX: str = "/api"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Security & CORS
    SECRET_KEY: str = "changeme-in-production-use-a-secure-random-secret-key-min-32-chars"
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
    )

    # Operational Mode
    RAMP_DATA_MODE: str = "SYNTHETIC_DEMO"

    # Storage & Model Paths
    RAMP_DATA_ROOT: str = "./data"
    RAMP_CONFIG_PATH: str = "./config/model_config.yaml"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, tuple)):
            return list(v)
        return ["*"]


settings = Settings()
