import sys
import unittest
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


class SchemaBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    def test_fresh_database_without_alembic_version_bootstraps_latest_schema(self):
        from app.services.schema_bootstrap_service import build_schema_bootstrap_plan

        plan = build_schema_bootstrap_plan(self.engine)

        self.assertEqual(plan.action, "bootstrap_fresh")
        self.assertEqual(plan.existing_tables, set())

    def test_database_with_alembic_version_prefers_alembic_migrations(self):
        from app.services.schema_bootstrap_service import build_schema_bootstrap_plan

        with self.engine.begin() as connection:
            connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))

        plan = build_schema_bootstrap_plan(self.engine)

        self.assertEqual(plan.action, "migrate")
        self.assertIn("alembic_version", plan.existing_tables)

    def test_metadata_compatible_database_without_alembic_version_can_be_adopted(self):
        from app.database import Base
        from app.services.schema_bootstrap_service import build_schema_bootstrap_plan, load_model_metadata

        load_model_metadata()
        Base.metadata.create_all(bind=self.engine)

        plan = build_schema_bootstrap_plan(self.engine)

        self.assertEqual(plan.action, "adopt_existing")
        self.assertIn("users", plan.existing_tables)

    def test_partial_legacy_database_without_alembic_version_requires_manual_intervention(self):
        from app.services.schema_bootstrap_service import build_schema_bootstrap_plan

        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE users (
                        id INTEGER PRIMARY KEY,
                        email VARCHAR(255) NOT NULL,
                        hashed_password VARCHAR(255) NOT NULL
                    )
                    """
                )
            )

        plan = build_schema_bootstrap_plan(self.engine)

        self.assertEqual(plan.action, "manual_intervention")
        self.assertIn("users", plan.existing_tables)

    def test_bootstrap_database_schema_creates_latest_tables(self):
        from app.services.schema_bootstrap_service import bootstrap_database_schema

        bootstrap_database_schema(self.engine)

        table_names = set(inspect(self.engine).get_table_names())
        self.assertIn("users", table_names)
        self.assertIn("email_verification_codes", table_names)


if __name__ == "__main__":
    unittest.main()
