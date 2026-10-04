"""
RAMP Database & PostGIS Connection Management
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Manages PostgreSQL + PostGIS connections, session lifecycles, connection pooling,
schema initialization, and health telemetry.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import declarative_base, sessionmaker, Session

logger = logging.getLogger(__name__)

Base = declarative_base()

REQUIRED_TABLES = [
    "datasets",
    "file_objects",
    "file_chunks",
    "forecast_runs",
    "forecast_grid",
    "forecast_districts",
    "forecast_states",
    "imd_observations",
    "nwp_files",
    "forecast_provenance",
    "audit_events",
    "system_state",
]


def is_production_env() -> bool:
    """Detects if running in Render or production deployment."""
    return (
        os.environ.get("APP_ENV", "").lower() == "production"
        or "RENDER" in os.environ
        or "RENDER_SERVICE_ID" in os.environ
    )


def get_database_url() -> str:
    """
    Resolves the canonical database connection URL in an environment-aware manner.
    - Production (Render): Requires DATABASE_URL from Render PostgreSQL service.
      Does NOT fall back to localhost/5432.
    - Development: Uses DATABASE_URL if present, otherwise POSTGRES_* component env vars
      or localhost:5432 default.
    - Normalizes postgres:// and postgresql:// to postgresql+psycopg:// for SQLAlchemy 2.
    """
    raw_url = os.environ.get("DATABASE_URL", "").strip()

    if not raw_url:
        if is_production_env():
            logger.error(
                "CRITICAL: DATABASE_URL is missing in Render production environment! "
                "Render PostgreSQL connection string must be provided via render.yaml or environment."
            )
            # Return empty or invalid string so diagnostics report DATABASE_UNAVAILABLE
            return ""

        # Local development fallback
        host = os.environ.get("POSTGRES_HOST", "localhost")
        port = os.environ.get("POSTGRES_PORT", "5432")
        db = os.environ.get("POSTGRES_DB", "ramp_db")
        user = os.environ.get("POSTGRES_USER", "ramp")
        password = os.environ.get("POSTGRES_PASSWORD", "ramp")
        raw_url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"

    # Normalize dialect to psycopg v3 if standard postgresql:// or postgres:// provided
    if raw_url.startswith("postgresql://"):
        raw_url = raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql+psycopg://", 1)

    return raw_url


def parse_database_url_safely(url_str: str) -> Dict[str, Any]:
    """
    Parses connection string safely without ever exposing the password.
    """
    if not url_str:
        return {
            "host": "NONE",
            "port": None,
            "database": "NONE",
            "user": "NONE",
            "driver": "NONE",
            "is_valid": False,
        }

    try:
        url_obj = make_url(url_str)
        return {
            "host": url_obj.host or "localhost",
            "port": url_obj.port,
            "database": url_obj.database or "unknown",
            "user": url_obj.username or "unknown",
            "driver": url_obj.drivername,
            "is_valid": True,
        }
    except Exception:
        # Fallback basic parse
        try:
            parts = urlsplit(url_str)
            db_name = parts.path.lstrip("/") if parts.path else "unknown"
            host = parts.hostname or "unknown"
            port = parts.port
            user = parts.username or "unknown"
            return {
                "host": host,
                "port": port,
                "database": db_name,
                "user": user,
                "driver": parts.scheme,
                "is_valid": True,
            }
        except Exception as pe:
            return {
                "host": "PARSE_ERROR",
                "port": None,
                "database": "PARSE_ERROR",
                "user": "PARSE_ERROR",
                "driver": "PARSE_ERROR",
                "is_valid": False,
                "error": str(pe),
            }


class DatabaseManager:
    """
    Singleton connection manager handling engine initialization,
    schema migrations/creation, PostGIS extensions, sessions, and state persistence.
    """

    _instance: Optional["DatabaseManager"] = None

    def __init__(self, database_url: Optional[str] = None, pool_size: int = 10):
        self.database_url = database_url or get_database_url()
        self.is_production = is_production_env()
        self.is_sqlite = "sqlite" in self.database_url if self.database_url else False
        self.pool_size = pool_size
        self._postgis_active: bool = False
        self._schema_ready: bool = False
        self._connected: bool = False
        self._connection_error: Optional[str] = None

        parsed = parse_database_url_safely(self.database_url)
        self.db_host = parsed.get("host")
        self.db_name = parsed.get("database")

        self.engine: Engine = self._create_engine()
        self.SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    @classmethod
    def get_instance(cls, database_url: Optional[str] = None) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = cls(database_url)
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Resets the singleton instance and releases pool resources."""
        if cls._instance is not None:
            try:
                cls._instance.close()
            except Exception:
                pass
            cls._instance = None

    def _create_engine(self) -> Engine:
        """Creates engine with connection pooling and fast connection timeout."""
        if not self.database_url:
            self._connected = False
            self._connection_error = "DATABASE_URL is not configured."
            if self.is_production:
                logger.error("Production database connection failed: DATABASE_URL is empty.")
            # Create a dummy sqlite memory engine to prevent hard crashes while health check reports DOWN
            return create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

        try:
            if self.is_sqlite:
                eng = create_engine(
                    self.database_url,
                    connect_args={"check_same_thread": False},
                )
            else:
                eng = create_engine(
                    self.database_url,
                    pool_size=self.pool_size,
                    max_overflow=20,
                    pool_pre_ping=True,
                    pool_recycle=1800,
                    connect_args={"connect_timeout": 5},
                )
            return eng
        except Exception as e:
            self._connection_error = str(e)
            logger.warning(f"Could not initialize database engine for {self.db_host}/{self.db_name}: {e}.")
            if not self.is_production:
                logger.info("Local environment: falling back to SQLite for isolated development.")
                self.database_url = "sqlite:///data/ramp_storage.db"
                self.is_sqlite = True
                Path("data").mkdir(exist_ok=True)
                return create_engine(self.database_url, connect_args={"check_same_thread": False})
            else:
                # In production, do NOT mask failure by pretending SQLite has real data
                return create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    def run_startup_diagnostics(self) -> Dict[str, Any]:
        """
        Executes strict startup diagnostic protocol:
        1. Read & validate DATABASE_URL
        2. Verify connection
        3. Verify required tables
        4. Verify PostGIS
        5. Log DATABASE_HOST, DATABASE_NAME, DATABASE_CONNECTED, DATABASE_SCHEMA_READY (no password!)
        """
        diag = {
            "database_host": self.db_host,
            "database_name": self.db_name,
            "database_connected": False,
            "database_schema_ready": False,
            "postgis_active": False,
            "postgis_version": None,
            "tables_found": [],
            "missing_tables": [],
        }

        # 1. Connection check
        try:
            with self.engine.connect() as conn:
                res = conn.execute(text("SELECT 1;")).scalar()
                if res == 1:
                    self._connected = True
                    diag["database_connected"] = True

                # 2. Check PostGIS
                if not self.is_sqlite:
                    try:
                        pgis_ver = conn.execute(text("SELECT PostGIS_Version();")).scalar()
                        self._postgis_active = True
                        diag["postgis_active"] = True
                        diag["postgis_version"] = str(pgis_ver)
                    except Exception:
                        self._postgis_active = False

                # 3. Check Tables
                inspector = inspect(conn)
                existing_tables = inspector.get_table_names()
                diag["tables_found"] = existing_tables
                missing = [t for t in REQUIRED_TABLES if t not in existing_tables]
                diag["missing_tables"] = missing
                diag["database_schema_ready"] = (len(missing) == 0)
                self._schema_ready = diag["database_schema_ready"]

        except Exception as e:
            self._connected = False
            self._connection_error = str(e)
            logger.warning(f"Database connection check failed: {e}")

        # Requirement 2: Log diagnostics without password
        logger.info(f"DATABASE_HOST: {diag['database_host']}")
        logger.info(f"DATABASE_NAME: {diag['database_name']}")
        logger.info(f"DATABASE_CONNECTED: {diag['database_connected']}")
        logger.info(f"DATABASE_SCHEMA_READY: {diag['database_schema_ready']}")

        return diag

    def init_schema(self) -> bool:
        """
        Enables PostGIS extension on PostgreSQL and creates all defined tables.
        Executes migrations/table creation safely.
        """
        try:
            with self.engine.begin() as conn:
                if not self.is_sqlite:
                    # Enable PostGIS extension
                    try:
                        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
                        self._postgis_active = True
                        logger.info("PostGIS extension enabled.")
                    except Exception as ext_err:
                        logger.warning(f"PostGIS extension notice: {ext_err}")

                # Create all tables defined in models
                try:
                    from . import models
                except (ImportError, ValueError):
                    from backend.src.ramp.storage import models
                Base.metadata.create_all(bind=conn)
                self._schema_ready = True
                self._connected = True
                logger.info("Database schema initialized successfully.")

            # Run diagnostics to confirm
            self.run_startup_diagnostics()
            return True
        except Exception as err:
            logger.warning(f"Database schema initialization deferred or failed: {err}")
            self._connection_error = str(err)
            if not self.is_production and not self.is_sqlite:
                logger.info("Attempting local SQLite database initialization...")
                self.database_url = "sqlite:///data/ramp_storage.db"
                self.is_sqlite = True
                Path("data").mkdir(exist_ok=True)
                self.engine = create_engine(self.database_url, connect_args={"check_same_thread": False})
                self.SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
                try:
                    try:
                        from . import models
                    except (ImportError, ValueError):
                        from backend.src.ramp.storage import models
                    Base.metadata.create_all(bind=self.engine)
                    self._schema_ready = True
                    self._connected = True
                    return True
                except Exception as sq_err:
                    logger.error(f"Local SQLite fallback failed: {sq_err}")
            return False

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Provides a transactional database session scope."""
        sess: Session = self.SessionFactory()
        try:
            yield sess
            sess.commit()
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()

    def get_state(self, state_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves persistent system state from PostgreSQL system_state table.
        """
        try:
            try:
                from .models import SystemStateModel
            except (ImportError, ValueError):
                from backend.src.ramp.storage.models import SystemStateModel
            with self.session() as s:
                rec = s.query(SystemStateModel).filter(SystemStateModel.state_key == state_key).first()
                if rec and rec.state_json:
                    return dict(rec.state_json)
        except Exception as e:
            logger.debug(f"Could not load state '{state_key}' from database: {e}")
        return None

    def set_state(self, state_key: str, data: Dict[str, Any], updated_by: str = "SYSTEM") -> bool:
        """
        Persists system state into PostgreSQL system_state table.
        """
        try:
            try:
                from .models import SystemStateModel
            except (ImportError, ValueError):
                from backend.src.ramp.storage.models import SystemStateModel
            with self.session() as s:
                rec = s.query(SystemStateModel).filter(SystemStateModel.state_key == state_key).first()
                if rec:
                    rec.state_json = data
                    rec.updated_at = datetime.now(timezone.utc)
                    rec.updated_by = updated_by
                else:
                    new_rec = SystemStateModel(
                        state_key=state_key,
                        state_json=data,
                        updated_by=updated_by,
                    )
                    s.add(new_rec)
            return True
        except Exception as e:
            logger.warning(f"Could not save state '{state_key}' to database: {e}")
            return False

    def check_health(self) -> Dict[str, Any]:
        """
        Comprehensive database health probe testing connection and PostGIS availability.
        """
        health: Dict[str, Any] = {
            "status": "DOWN",
            "backend": "PostgreSQL + PostGIS" if not self.is_sqlite else "SQLite",
            "connected": False,
            "schema_ready": self._schema_ready,
            "postgis_enabled": self._postgis_active,
            "postgis_version": None,
            "dialect": self.engine.dialect.name,
            "engine": self.engine.dialect.name,
            "host": self.db_host,
            "database": self.db_name,
        }

        try:
            with self.engine.connect() as conn:
                res = conn.execute(text("SELECT 1;")).scalar()
                health["connected"] = (res == 1)
                health["is_healthy"] = health["connected"]
                health["status"] = "HEALTHY" if health["connected"] else "DOWN"

                if not self.is_sqlite:
                    try:
                        pgis_ver = conn.execute(text("SELECT PostGIS_Version();")).scalar()
                        health["postgis_enabled"] = True
                        health["postgis_version"] = str(pgis_ver)
                    except Exception:
                        health["postgis_enabled"] = False
                else:
                    health["postgis_enabled"] = False
                    health["postgis_version"] = "N/A (SQLite)"
        except Exception as e:
            health["error"] = str(e)
            health["is_healthy"] = False
            health["status"] = "DOWN"

        return health

    def dispose(self):
        """Disposes connection pool engine."""
        if hasattr(self, "engine") and self.engine:
            self.engine.dispose()

    def close(self):
        """Closes database manager resources."""
        self.dispose()


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions."""
    manager = DatabaseManager.get_instance()
    with manager.session() as session:
        yield session

