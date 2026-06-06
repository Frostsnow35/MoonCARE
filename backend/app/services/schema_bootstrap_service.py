from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from app.database import Base


logger = logging.getLogger(__name__)

SchemaBootstrapAction = Literal[
    "bootstrap_fresh",
    "migrate",
    "adopt_existing",
    "manual_intervention",
]


@dataclass(frozen=True)
class SchemaBootstrapPlan:
    """Describe how deployment should prepare the database schema."""

    action: SchemaBootstrapAction
    existing_tables: set[str]


def load_model_metadata() -> None:
    """Import all SQLAlchemy models so Base.metadata is complete."""

    from app.models.assessment import AssessmentObservation, AssessmentSession  # noqa: F401
    from app.models.auth import EmailVerificationCode  # noqa: F401
    from app.models.biometric import BiometricData  # noqa: F401
    from app.models.chat_memory import ChatMemory  # noqa: F401
    from app.models.conversation import Conversation  # noqa: F401
    from app.models.menstrual import MenstrualRecord  # noqa: F401
    from app.models.mood import MoodDiary  # noqa: F401
    from app.models.music import Music, MusicFeedback  # noqa: F401
    from app.models.user import User  # noqa: F401


def _table_columns(engine: Engine, table_name: str) -> set[str]:
    """Return the current column names for a database table."""

    inspector = inspect(engine)
    return {column["name"] for column in inspector.get_columns(table_name)}


def _metadata_columns(table_name: str) -> set[str]:
    """Return the column names defined by the current SQLAlchemy metadata."""

    return {column.name for column in Base.metadata.tables[table_name].columns}


def _is_schema_compatible_with_metadata(engine: Engine, existing_tables: set[str]) -> bool:
    """Return whether existing managed tables already satisfy current metadata columns."""

    managed_tables = existing_tables & set(Base.metadata.tables.keys())
    for table_name in managed_tables:
        if not _metadata_columns(table_name).issubset(_table_columns(engine, table_name)):
            logger.warning("Table %s is missing metadata columns; manual intervention required.", table_name)
            return False
    return True


def build_schema_bootstrap_plan(engine: Engine) -> SchemaBootstrapPlan:
    """Choose the safest schema-preparation strategy for the current database."""

    load_model_metadata()
    existing_tables = set(inspect(engine).get_table_names())

    if "alembic_version" in existing_tables:
        return SchemaBootstrapPlan(action="migrate", existing_tables=existing_tables)

    managed_tables = existing_tables & set(Base.metadata.tables.keys())
    if not managed_tables:
        return SchemaBootstrapPlan(action="bootstrap_fresh", existing_tables=existing_tables)

    if _is_schema_compatible_with_metadata(engine, existing_tables):
        return SchemaBootstrapPlan(action="adopt_existing", existing_tables=existing_tables)

    return SchemaBootstrapPlan(action="manual_intervention", existing_tables=existing_tables)


def bootstrap_database_schema(engine: Engine) -> None:
    """Create all missing tables for the latest metadata shape."""

    load_model_metadata()
    Base.metadata.create_all(bind=engine)


def should_runtime_create_tables(database_url: str) -> bool:
    """Keep runtime create_all limited to local SQLite development."""

    return database_url.startswith("sqlite")
