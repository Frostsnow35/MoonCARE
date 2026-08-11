import logging
import os

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

logger = logging.getLogger(__name__)

_SQLITE_JOURNAL_MODES = {"DELETE", "TRUNCATE", "PERSIST", "MEMORY", "WAL", "OFF"}


def _normalize_database_url(url: str) -> str:
    """确保数据库 URL 符合 SQLAlchemy 格式。
    - 将 postgres:// 替换为 postgresql://（Railway 常用）
    """
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def _is_sqlite_url(database_url: str) -> bool:
    """Return whether the configured SQLAlchemy URL points to SQLite."""
    return database_url.startswith("sqlite")


def _sqlite_connect_args(database_url: str) -> dict:
    """Return SQLite-specific connection options for FastAPI threadpool use."""
    if not _is_sqlite_url(database_url):
        return {}
    return {
        "check_same_thread": False,
        "timeout": float(settings.SQLITE_BUSY_TIMEOUT_SECONDS),
    }


# 规范化 URL
DATABASE_URL = _normalize_database_url(settings.DATABASE_URL)

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


def get_db():
    """Dependency for database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()