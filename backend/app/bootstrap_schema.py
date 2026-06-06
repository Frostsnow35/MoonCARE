from __future__ import annotations

import argparse
import sys

from app.database import engine
from app.services.schema_bootstrap_service import (
    bootstrap_database_schema,
    build_schema_bootstrap_plan,
)


def main() -> int:
    """Inspect and optionally bootstrap the current database schema."""

    parser = argparse.ArgumentParser(description="Inspect or bootstrap MoonCARE database schema.")
    parser.add_argument("--print-action", action="store_true", help="Print only the chosen bootstrap action.")
    parser.add_argument(
        "--apply-if-needed",
        action="store_true",
        help="Create missing tables when the database should be bootstrapped or adopted.",
    )
    args = parser.parse_args()

    plan = build_schema_bootstrap_plan(engine)

    if args.print_action:
        print(plan.action)
        return 0

    if args.apply_if_needed:
        if plan.action in {"bootstrap_fresh", "adopt_existing"}:
            bootstrap_database_schema(engine)
        print(plan.action)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
