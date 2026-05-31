from __future__ import annotations

import argparse
import sys

from app.db import engine
from app.migration_bootstrap import run_lightweight_migrations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the deprecated legacy lightweight migration path against the configured database."
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required. Acknowledge that this deprecated path is only for emergency legacy recovery.",
    )
    args = parser.parse_args()

    if not args.confirm:
        print(
            "Refusing to run legacy lightweight migrations without --confirm. "
            "Prefer Alembic-managed modes and only use this for emergency legacy recovery.",
            file=sys.stderr,
        )
        return 2

    run_lightweight_migrations(engine=engine)
    print("Legacy lightweight migration path completed.", file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
