"""Execute and verify the canonical cycle on the disposable PostgreSQL database only."""

from __future__ import annotations

import json
import sys

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from alembic import command
from florabase.core.config import get_settings
from florabase.db.testing import require_disposable_test_database


def main(base: str) -> None:
    settings = get_settings()
    require_disposable_test_database(settings)
    engine = create_engine(settings.database_url)
    if engine.dialect.name != "postgresql":
        raise ValueError("migration cycle requires disposable PostgreSQL")
    config = Config("alembic.ini")
    head = ScriptDirectory.from_config(config).get_current_head()
    if head is None:
        raise ValueError("migration cycle requires one code head")
    verified = []
    try:
        for operation, target, expected in (
            (command.upgrade, base, base),
            (command.upgrade, "head", head),
            (command.downgrade, base, base),
            (command.upgrade, "head", head),
        ):
            operation(config, target)
            with engine.connect() as connection:
                actual = MigrationContext.configure(connection).get_current_heads()
            if actual != (expected,):
                raise ValueError(f"migration state differs: expected {expected}, found {actual}")
            verified.append(expected)
    finally:
        engine.dispose()
    sys.stdout.write("MIGRATION_SCHEMA_VERIFIED " + json.dumps(verified) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main(sys.argv[1])
