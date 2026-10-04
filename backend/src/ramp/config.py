"""
RAMP Configuration Module
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
"""

from pathlib import Path
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_project_root() -> Path:
    """Walk up from this file to find the project root (contains 'backend/' and 'data/' dirs)."""
    current = Path(__file__).resolve().parent
    for _ in range(8):
        if (current / "backend").is_dir() and (current / "data").is_dir():
            return current
        current = current.parent
    # Fallback: two levels up from backend/src/ramp/config.py
    return Path(__file__).resolve().parents[3]


_PROJECT_ROOT = _find_project_root()
_ENV_FILE = str(_PROJECT_ROOT / ".env")
_DEV_ENV1 = str(_PROJECT_ROOT / "configs" / "dev.env")
_DEV_ENV2 = str(_PROJECT_ROOT / "config" / "dev.env")


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env files."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,  # absolute path — always correct regardless of CWD
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
        default=[
            "https://gatisura-ramp.onrender.com",
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
        ]
    )

    # Operational Mode
    RAMP_DATA_MODE: str = "SYNTHETIC_DEMO"

    # Storage & Model Paths
    RAMP_DATA_ROOT: str = "./data"
    RAMP_CONFIG_PATH: str = "./config/model_config.yaml"

    # Database & PostGIS Persistent Storage
    DATABASE_URL: str = ""
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "ramp_db"
    POSTGRES_USER: str = "ramp"
    POSTGRES_PASSWORD: str = "ramp"
    STORAGE_MODE: str = "POSTGRESQL"

    def get_database_url(self) -> str:
        """Returns the configured PostgreSQL connection string."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        defaults = [
            "https://gatisura-ramp.onrender.com",
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
        ]
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            parsed = [i.strip() for i in v.split(",") if i.strip()]
            for d in defaults:
                if d not in parsed:
                    parsed.append(d)
            return parsed
        elif isinstance(v, (list, tuple)):
            res = list(v)
            for d in defaults:
                if d not in res:
                    res.append(d)
            return res
        return defaults


settings = Settings()
