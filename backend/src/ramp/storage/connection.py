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
from pathlib import Path
from typing import Any, Dict, Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

logger = logging.getLogger(__name__)

Base = declarative_base()


def get_database_url() -> str:
    """
    Resolves the canonical database connection URL.
    Priority:
    1. DATABASE_URL environment variable
    2. POSTGRES_* component environment variables
    3. Default to postgresql+psycopg://ramp:ramp@localhost:5432/ramp_db
    """
    raw_url = os.environ.get("DATABASE_URL", "").strip()
    if not raw_url:
        host = os.environ.get("POSTGRES_HOST", "localhost")
        port = os.environ.get("POSTGRES_PORT", "5432")
        db = os.environ.get("POSTGRES_DB", "ramp_db")
        user = os.environ.get("POSTGRES_USER", "ramp")
        password = os.environ.get("POSTGRES_PASSWORD", "ramp")
        raw_url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"

    # Normalize dialect to psycopg v3 if standard postgresql:// provided
    if raw_url.startswith("postgresql://"):
        raw_url = raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql+psycopg://", 1)

    return raw_url


class DatabaseManager:
    """
    Singleton connection manager handling engine initialization,
    schema migrations/creation, PostGIS extensions, and sessions.
    """

    _instance: Optional["DatabaseManager"] = None

    def __init__(self, database_url: Optional[str] = None, pool_size: int = 10):
        self.database_url = database_url or get_database_url()
        self.is_sqlite = "sqlite" in self.database_url
        self.pool_size = pool_size
        self.engine: Engine = self._create_engine()
        self.SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self._postgis_active: bool = False
        self._initialized: bool = False

    @classmethod
    def get_instance(cls, database_url: Optional[str] = None) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = cls(database_url)
        return cls._instance

    def _create_engine(self) -> Engine:
        """Creates engine with connection pooling and fast connection timeout."""
        try:
            if self.is_sqlite:
                return create_engine(
                    self.database_url,
                    connect_args={"check_same_thread": False},
                )
            else:
                return create_engine(
                    self.database_url,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True,
                    pool_recycle=1800,
                    connect_args={"connect_timeout": 3},
                )
        except Exception as e:
            logger.warning(f"Could not initialize database engine for {self.database_url}: {e}. Falling back to SQLite.")
            self.database_url = "sqlite:///data/ramp_storage.db"
            self.is_sqlite = True
            Path("data").mkdir(exist_ok=True)
            return create_engine(self.database_url, connect_args={"check_same_thread": False})

    def init_schema(self) -> bool:
        """
        Enables PostGIS extension on PostgreSQL and creates all defined tables.
        """
        if self._initialized:
            return True

        try:
            with self.engine.begin() as conn:
                if not self.is_sqlite:
                    # Enable PostGIS extension
                    try:
                        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
                        self._postgis_active = True
                        logger.info("PostGIS extension enabled.")
                    except Exception as ext_err:
                        logger.warning(f"Could not enable PostGIS extension (might already exist or lack superuser): {ext_err}")

                # Create all tables defined in models
                from backend.src.ramp.storage.models import Base as ModelsBase
                ModelsBase.metadata.create_all(bind=conn)
                logger.info("Database schema initialized successfully.")

            self._initialized = True
            return True
        except Exception as err:
            logger.warning(f"Database schema initialization deferred or failed: {err}")
            # Fall back to sqlite if postgres was unreachable
            if not self.is_sqlite:
                logger.info("Attempting local SQLite database initialization...")
                self.database_url = "sqlite:///data/ramp_storage.db"
                self.is_sqlite = True
                Path("data").mkdir(exist_ok=True)
                self.engine = create_engine(self.database_url, connect_args={"check_same_thread": False})
                self.SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
                try:
                    from backend.src.ramp.storage.models import Base as ModelsBase
                    ModelsBase.metadata.create_all(bind=self.engine)
                    self._initialized = True
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

    def check_health(self) -> Dict[str, Any]:
        """
        Comprehensive database health probe testing connection and PostGIS availability.
        """
        health: Dict[str, Any] = {
            "status": "DOWN",
            "backend": "PostgreSQL + PostGIS" if not self.is_sqlite else "SQLite Fallback",
            "connected": False,
            "postgis_enabled": False,
            "postgis_version": None,
            "dialect": self.engine.dialect.name,
            "database": self.database_url.split("@")[-1] if "@" in self.database_url else self.database_url,
        }

        try:
            with self.engine.connect() as conn:
                res = conn.execute(text("SELECT 1;")).scalar()
                health["connected"] = (res == 1)
                health["is_healthy"] = health["connected"]
                health["engine"] = self.engine.dialect.name
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
