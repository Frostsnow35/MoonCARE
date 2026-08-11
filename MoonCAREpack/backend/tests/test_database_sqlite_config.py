import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


class DatabaseSqliteConfigTests(unittest.TestCase):
    def test_sqlite_connections_are_threadpool_safe(self):
        from app.database import _sqlite_connect_args

        args = _sqlite_connect_args("sqlite:///./healthai.db")

        self.assertFalse(args["check_same_thread"])
        self.assertGreaterEqual(args["timeout"], 1.0)

    def test_non_sqlite_connections_keep_default_args(self):
        from app.database import _sqlite_connect_args

        self.assertEqual(_sqlite_connect_args("postgresql://localhost/mooncare"), {})


if __name__ == "__main__":
    unittest.main()
