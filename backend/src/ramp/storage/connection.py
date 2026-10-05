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
import time
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
    "operations_state",
    "operation_events",
    "operational_cycles",
    "cycle_events",
    "scheduler_state",
    "forecast_jobs",
    "alert_rules",
    "alert_events",
    "drift_measurements",
    "readiness_runs",
    "data_source_health",
]


def is_production_env() -> bool:
    """Detects if running in Render or production deployment."""
    app_env = (os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "").lower()
    return (
        app_env == "production"
        or "RENDER" in os.environ
        or "RENDER_SERVICE_ID" in os.environ
    )


def normalize_database_url(raw_url: str) -> str:
    """
    Normalizes a PostgreSQL URL for Render and psycopg 3:
    1. Strips whitespace and surrounding quotes
    2. Maps postgres:// and postgresql:// to postgresql+psycopg://
    3. Auto-fills port 5432 if missing on Render internal or external hosts
    4. For external Render hosts (*.render.com), ensures sslmode=require is configured
    """
    if not raw_url:
        return ""

    url = raw_url.strip().strip("'\"")
    if not url:
        return ""

    # Normalize dialect to postgresql+psycopg://
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)

    try:
        url_obj = make_url(url)
        host = url_obj.host or ""

        # Auto-fill port 5432 if omitted for Render hosts
        if not url_obj.port and ("dpg-" in host or "render.com" in host or "postgres" in host):
            url_obj = url_obj.set(port=5432)

        # For external Render databases (*.render.com), SSL is mandatory
        if "render.com" in host:
            query = dict(url_obj.query)
            if "sslmode" not in query:
                query["sslmode"] = "require"
                url_obj = url_obj.set(query=query)

        return url_obj.render_as_string(hide_password=False)
    except Exception:
        return url


def get_database_url() -> str:
    """
    Resolves the canonical database connection URL in an environment-aware manner.
    - Production (Render): Requires DATABASE_URL from Render PostgreSQL service.
      Does NOT fall back to localhost/5432 or SQLite.
    - Development: Uses DATABASE_URL if present, otherwise POSTGRES_* component env vars
      or localhost:5432 default.
    - Normalizes postgres://, postgresql://, postgresql+asyncpg://, postgresql+psycopg2://
      to postgresql+psycopg:// for SQLAlchemy 2 with psycopg v3.
    """
    raw_url = os.environ.get("DATABASE_URL", "").strip()

    if not raw_url:
        if is_production_env():
            logger.error(
                "CRITICAL: DATABASE_URL is missing in Render production environment! "
                "Render PostgreSQL connection string must be provided via render.yaml or environment."
            )
            # Return empty string so diagnostics report DATABASE_UNAVAILABLE and fail fast
            return ""

        # Local development fallback
        host = os.environ.get("POSTGRES_HOST", "localhost")
        port = os.environ.get("POSTGRES_PORT", "5432")
        db = os.environ.get("POSTGRES_DB", "ramp_db")
        user = os.environ.get("POSTGRES_USER", "ramp")
        password = os.environ.get("POSTGRES_PASSWORD", "ramp")
        raw_url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"

    return normalize_database_url(raw_url)


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

    @staticmethod
    def _configure_sqlite_engine(eng: Engine):
        """Enables WAL mode and 30s busy timeout for concurrent SQLite transactions."""
        from sqlalchemy import event
        @event.listens_for(eng, "connect")
        def _set_sqlite_pragma(dbapi_conn, conn_record):
            try:
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL;")
                cursor.execute("PRAGMA busy_timeout=30000;")
                cursor.close()
            except Exception:
                pass

    def _create_engine(self) -> Engine:
        """Creates engine with connection pooling and fast connection timeout."""
        if not self.database_url:
            self._connected = False
            self._schema_ready = False
            self._connection_error = "DATABASE_URL is not configured."
            self.is_sqlite = True
            if self.is_production:
                logger.error(
                    "FATAL CONFIGURATION: DATABASE_URL is missing in Render production environment! "
                    "Render PostgreSQL connection string must be provided via render.yaml or environment."
                )
            # Create a dummy sqlite memory engine to prevent hard crashes while health check reports DOWN
            return create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

        try:
            if self.is_sqlite:
                eng = create_engine(
                    self.database_url,
                    connect_args={"check_same_thread": False, "timeout": 30},
                )
            else:
                connect_args = {"connect_timeout": 2}
                eng = create_engine(
                    self.database_url,
                    pool_size=self.pool_size,
                    max_overflow=20,
                    pool_pre_ping=True,
                    pool_recycle=1800,
                    connect_args=connect_args,
                )
            self.is_sqlite = (eng.dialect.name == "sqlite")
            if self.is_sqlite:
                self._configure_sqlite_engine(eng)
            return eng
        except Exception as e:
            self._connection_error = str(e)
            logger.warning(f"Could not initialize database engine for {self.db_host}/{self.db_name}: {e}.")
            if not self.is_production:
                logger.info("Local environment: falling back to SQLite for isolated development.")
                self.database_url = "sqlite:///data/ramp_storage.db"
                self.is_sqlite = True
                Path("data").mkdir(exist_ok=True)
                eng = create_engine(self.database_url, connect_args={"check_same_thread": False, "timeout": 30})
                self._configure_sqlite_engine(eng)
                return eng
            else:
                # In production, do NOT mask failure by pretending SQLite has real data
                self.is_sqlite = True
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
        now = time.time()
        if hasattr(self, "_last_diag") and self._last_diag:
            if (now - getattr(self, "_last_diag_time", 0)) < 3.0:
                return dict(self._last_diag)

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

        if not self.database_url:
            self._connected = False
            self._schema_ready = False
            logger.error("DATABASE_CONNECTED: False (DATABASE_URL is missing)")
            logger.error("DATABASE_SCHEMA_READY: False")
            self._last_diag = dict(diag)
            self._last_diag_time = now
            return diag

        # If a connection error occurred very recently, avoid compounding timeouts
        if not self._connected and (now - getattr(self, "_last_error_time", 0)) < 5.0:
            self._last_diag = dict(diag)
            self._last_diag_time = now
            return diag

        # 1. Connection check
        try:
            with self.engine.connect() as conn:
                res = conn.execute(text("SELECT 1;")).scalar()
                if res == 1:
                    self._connected = True
                    diag["database_connected"] = True

                # 2. Check PostGIS ONLY if PostgreSQL
                if self.engine.dialect.name == "postgresql":
                    try:
                        pgis_ver = conn.execute(text("SELECT PostGIS_Version();")).scalar()
                        self._postgis_active = True
                        diag["postgis_active"] = True
                        diag["postgis_version"] = str(pgis_ver)
                    except Exception as pe:
                        self._postgis_active = False
                        diag["postgis_active"] = False
                        diag["postgis_error"] = str(pe)
                else:
                    self._postgis_active = False
                    diag["postgis_active"] = False
                    diag["postgis_version"] = f"N/A ({self.engine.dialect.name})"

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
            self._last_error_time = time.time()
            logger.warning(f"Database connection check failed: {e}")
            if not self.is_production and not self.is_sqlite:
                try:
                    self.database_url = "sqlite:///data/ramp_storage.db"
                    self.is_sqlite = True
                    Path("data").mkdir(exist_ok=True)
                    self.engine = create_engine(self.database_url, connect_args={"check_same_thread": False})
                    self.SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
                    from ramp.storage.models import Base
                    Base.metadata.create_all(bind=self.engine)
                    self._ensure_sqlite_columns()
                    self._schema_ready = True
                    self._connected = True
                    diag["database_connected"] = True
                    diag["database_schema_ready"] = True
                    diag["postgis_active"] = False
                    diag["postgis_version"] = "N/A (sqlite)"
                except Exception:
                    pass

        # Requirement 2: Log diagnostics without password
        logger.info(f"DATABASE_HOST: {diag['database_host']}")
        logger.info(f"DATABASE_NAME: {diag['database_name']}")
        logger.info(f"DATABASE_CONNECTED: {diag['database_connected']}")
        logger.info(f"DATABASE_SCHEMA_READY: {diag['database_schema_ready']}")

        self._last_diag = dict(diag)
        self._last_diag_time = time.time()
        return diag

    def init_schema(self) -> bool:
        """
        Enables PostGIS extension on PostgreSQL and creates all defined tables.
        Executes migrations/table creation safely.
        """
        if self._schema_ready:
            return True

        if not self.database_url:
            self._connected = False
            self._schema_ready = False
            self._connection_error = "DATABASE_URL is not configured."
            logger.error("Cannot initialize schema: DATABASE_URL is missing.")
            return False

        now = time.time()
        if not self._connected and (now - getattr(self, "_last_error_time", 0)) < 5.0:
            return False

        max_attempts = 3 if self.is_production else 1
        for attempt in range(1, max_attempts + 1):
            try:
                with self.engine.begin() as conn:
                    is_pg = (self.engine.dialect.name == "postgresql")
                    if is_pg:
                        # 1. Verify PostgreSQL
                        try:
                            pg_ver = conn.execute(text("SELECT version();")).scalar()
                            logger.info(f"Connected to PostgreSQL: {pg_ver}")
                        except Exception as ve:
                            logger.warning(f"Could not read PostgreSQL version: {ve}")

                        # 2. Enable PostGIS extension ONLY if PostgreSQL
                        try:
                            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
                            self._postgis_active = True
                            logger.info("PostGIS extension enabled.")
                        except Exception as ext_err:
                            self._postgis_active = False
                            logger.warning(f"PostGIS extension notice: {ext_err}")
                    else:
                        self._postgis_active = False
                        if self.is_production:
                            logger.error(
                                f"Production requires PostgreSQL + PostGIS, but connected engine dialect is {self.engine.dialect.name}."
                            )
                            return False

                    # 3. Create all tables defined in models
                    try:
                        from . import models
                    except (ImportError, ValueError):
                        from ramp.storage import models
                    Base.metadata.create_all(bind=conn)
                    self._schema_ready = True
                    self._connected = True
                    logger.info("Database schema initialized successfully.")

                # Run diagnostics to confirm
                self.run_startup_diagnostics()
                return True
            except Exception as err:
                self._connected = False
                self._schema_ready = False
                self._connection_error = str(err)
                self._last_error_time = time.time()
                logger.warning(f"Database schema initialization attempt {attempt}/{max_attempts} failed: {err}")
                if not self.is_production and "sqlite" not in self.database_url:
                    logger.info("Local environment: PostgreSQL unreachable, falling back to local SQLite engine.")
                    self.database_url = "sqlite:///data/ramp_storage.db"
                    self.is_sqlite = True
                    Path("data").mkdir(exist_ok=True)
                    self.engine = create_engine(self.database_url, connect_args={"check_same_thread": False})
                    self.SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
                    try:
                        from ramp.storage.models import Base
                        Base.metadata.create_all(bind=self.engine)
                        self._ensure_sqlite_columns()
                        self._schema_ready = True
                        self._connected = True
                        logger.info("SQLite schema initialized successfully for local development.")
                        return True
                    except Exception as sqle:
                        logger.warning(f"SQLite initialization notice: {sqle}")
                if attempt < max_attempts:
                    time.sleep(2.0)
        return False

    def _ensure_sqlite_columns(self) -> None:
        """Inspects and adds any missing columns to existing SQLite tables for local dev."""
        if not self.is_sqlite:
            return
        try:
            from ramp.storage.models import Base
            with self.engine.begin() as conn:
                for table_name, table in Base.metadata.tables.items():
                    try:
                        res = conn.execute(text(f"PRAGMA table_info('{table_name}')")).fetchall()
                        existing_cols = {row[1] for row in res}
                        for col in table.columns:
                            if col.name not in existing_cols:
                                col_type = col.type.compile(self.engine.dialect)
                                conn.execute(text(f"ALTER TABLE '{table_name}' ADD COLUMN {col.name} {col_type}"))
                                logger.info(f"SQLite migration: added column {table_name}.{col.name}")
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"SQLite column migration notice: {e}")

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
                from ramp.storage.models import SystemStateModel
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
                from ramp.storage.models import SystemStateModel
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
        Caches recent results for 3 seconds to protect from connection timeout cascades.
        """
        now = time.time()
        if hasattr(self, "_last_health_check") and self._last_health_check:
            if (now - getattr(self, "_last_health_time", 0)) < 3.0:
                return dict(self._last_health_check)

        if not self.database_url:
            return {
                "status": "DOWN",
                "backend": "PostgreSQL + PostGIS",
                "connected": False,
                "is_healthy": False,
                "schema_ready": False,
                "postgis_enabled": False,
                "postgis_version": None,
                "dialect": "none",
                "engine": "none",
                "host": self.db_host or "NONE",
                "database": self.db_name or "NONE",
                "error": "DATABASE_URL is not configured.",
            }

        health: Dict[str, Any] = {
            "status": "DOWN",
            "backend": "PostgreSQL + PostGIS" if self.engine.dialect.name == "postgresql" else self.engine.dialect.name,
            "connected": False,
            "schema_ready": self._schema_ready,
            "postgis_enabled": self._postgis_active,
            "postgis_version": None,
            "dialect": self.engine.dialect.name,
            "engine": self.engine.dialect.name,
            "host": self.db_host,
            "database": self.db_name,
        }

        # If a connection error occurred very recently, return DOWN without waiting for TCP timeout
        if not self._connected and (now - getattr(self, "_last_error_time", 0)) < 10.0:
            health["error"] = getattr(self, "_connection_error", "Database connection offline")
            self._last_health_check = dict(health)
            self._last_health_time = now
            return health

        try:
            with self.engine.connect() as conn:
                res = conn.execute(text("SELECT 1;")).scalar()
                health["connected"] = (res == 1)
                health["is_healthy"] = health["connected"]
                health["status"] = "HEALTHY" if health["connected"] else "DOWN"

                if self.engine.dialect.name == "postgresql":
                    try:
                        pgis_ver = conn.execute(text("SELECT PostGIS_Version();")).scalar()
                        health["postgis_enabled"] = True
                        health["postgis_version"] = str(pgis_ver)
                    except Exception:
                        health["postgis_enabled"] = False
                else:
                    health["postgis_enabled"] = False
                    health["postgis_version"] = f"N/A ({self.engine.dialect.name})"
        except Exception as e:
            health["error"] = str(e)
            health["is_healthy"] = False
            health["status"] = "DOWN"
            self._connected = False
            self._last_error_time = time.time()
            self._connection_error = str(e)

            if not self.is_production and not self.is_sqlite:
                logger.info("Local environment: PostgreSQL unreachable, automatically switching to local SQLite engine.")
                try:
                    self.database_url = "sqlite:///data/ramp_storage.db"
                    self.is_sqlite = True
                    Path("data").mkdir(exist_ok=True)
                    self.engine = create_engine(self.database_url, connect_args={"check_same_thread": False, "timeout": 30})
                    self._configure_sqlite_engine(self.engine)
                    self.SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
                    from ramp.storage.models import Base
                    Base.metadata.create_all(bind=self.engine)
                    self._ensure_sqlite_columns()
                    self._schema_ready = True
                    self._connected = True
                    health["connected"] = True
                    health["is_healthy"] = True
                    health["schema_ready"] = True
                    health["status"] = "HEALTHY"
                    health["backend"] = "sqlite"
                    health["dialect"] = "sqlite"
                    health["engine"] = "sqlite"
                    health["error"] = None
                    health["postgis_enabled"] = False
                    health["postgis_version"] = "N/A (sqlite)"
                    self._last_health_check = dict(health)
                    self._last_health_time = time.time()
                    return health
                except Exception as sqle:
                    logger.debug(f"SQLite fallback initialization notice: {sqle}")

        self._last_health_check = dict(health)
        self._last_health_time = time.time()
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

