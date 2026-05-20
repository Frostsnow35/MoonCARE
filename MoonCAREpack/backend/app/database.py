import logging
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

logger = logging.getLogger(__name__)

_SQLITE_JOURNAL_MODES = {"DELETE", "TRUNCATE", "PERSIST", "MEMORY", "WAL", "OFF"}


def _is_sqlite_url(database_url: str) -> bool:
    """Return whether the configured SQLAlchemy URL points to SQLite."""
    return database_url.startswith("sqlite")


def _normalize_database_url(database_url: str) -> str:
    """Normalize platform-provided URLs to SQLAlchemy-compatible forms."""
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)
    return database_url


def _database_backend(database_url: str) -> str:
    """Return a compact database backend label for health and diagnostics."""
    if database_url.startswith("sqlite"):
        return "sqlite"
    if database_url.startswith("postgresql"):
        return "postgresql"
    return database_url.split(":", 1)[0] or "unknown"


def _sqlite_connect_args(database_url: str) -> dict:
    """Return SQLite-specific connection options for FastAPI threadpool use."""
    if not _is_sqlite_url(database_url):
        return {}
    return {
        "check_same_thread": False,
        "timeout": float(settings.SQLITE_BUSY_TIMEOUT_SECONDS),
    }


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    """Create the SQLite file parent directory before SQLAlchemy opens it."""
    if not _is_sqlite_url(database_url):
        return

    database_path = make_url(database_url).database
    if not database_path or database_path == ":memory:":
        return

    Path(database_path).parent.mkdir(parents=True, exist_ok=True)


_DEFAULT_DATABASE_URL = "sqlite:///./data/mooncare.db"
DATABASE_URL = _normalize_database_url(
    (settings.DATABASE_URL or _DEFAULT_DATABASE_URL).strip() or _DEFAULT_DATABASE_URL
)
_ensure_sqlite_parent_dir(DATABASE_URL)


engine = create_engine(
    DATABASE_URL,
    connect_args=_sqlite_connect_args(DATABASE_URL),
    pool_pre_ping=True,
)


if _is_sqlite_url(DATABASE_URL):
    @event.listens_for(engine, "connect")
    def _configure_sqlite_connection(dbapi_connection, _connection_record):
        """Apply pragmatic local-dev SQLite settings on every new connection."""
        journal_mode = settings.SQLITE_JOURNAL_MODE.upper().strip()
        if journal_mode not in _SQLITE_JOURNAL_MODES:
            logger.warning("Invalid SQLITE_JOURNAL_MODE=%s; using TRUNCATE", journal_mode)
            journal_mode = "TRUNCATE"

        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(f"PRAGMA journal_mode={journal_mode}")
            cursor.execute(f"PRAGMA busy_timeout={int(float(settings.SQLITE_BUSY_TIMEOUT_SECONDS) * 1000)}")
        finally:
            cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def check_database_health(target_engine: Engine = engine) -> dict:
    """Check whether the configured database is reachable."""
    backend = _database_backend(str(target_engine.url))
    try:
        with target_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"available": True, "backend": backend}
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        return {"available": False, "backend": backend, "error": str(exc)}


def get_db():
    """Dependency for database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
