"""Read-only production startup guard and explicit release schema maintenance."""

import argparse
import os
import sys

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError

from alembic import command
from florabase.db.session import get_readiness_engine

# Serialize schema maintenance commands from this image in the selected database.
SCHEMA_LOCK = 721669727
USER_OBJECTS = text("""
    SELECT EXISTS (
        SELECT FROM pg_namespace
        WHERE nspname NOT IN ('public', 'information_schema')
          AND nspname !~ '^pg_'
        UNION ALL
        SELECT FROM pg_depend
        WHERE refclassid = 'pg_namespace'::regclass
          AND refobjid = 'public'::regnamespace
    )
""")


class SchemaError(Exception):
    pass


def current_heads(connection: Connection) -> tuple[str, ...]:
    return MigrationContext.configure(connection).get_current_heads()


def image_schema(config: Config | None = None) -> tuple[Config, ScriptDirectory, str]:
    if config is None:
        config = Config("/app/alembic.ini")
        config.set_main_option("script_location", "/app/alembic")
    scripts = ScriptDirectory.from_config(config)
    heads = scripts.get_heads()
    if len(heads) != 1:
        raise SchemaError(f"expected a single Alembic head in the image, found {heads}")
    return config, scripts, heads[0]


def require_image_head(connection: Connection, head: str) -> None:
    current = current_heads(connection)
    if current != (head,):
        raise SchemaError(
            f"database revision {current or 'empty'} differs from image head {head}; "
            "use the documented initialization, upgrade or recovery procedure"
        )


def maintain(config: Config, scripts: ScriptDirectory, head: str, previous: str | None) -> None:
    with get_readiness_engine().begin() as connection:
        connection.execute(text("SET LOCAL statement_timeout = 0"))
        connection.execute(text("SET LOCAL lock_timeout = '10s'"))
        connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": SCHEMA_LOCK})
        current = current_heads(connection)
        if previous is None:
            if current or connection.scalar(USER_OBJECTS):
                raise SchemaError("initialization requires an empty, unversioned database")
        elif current != (previous,) or previous not in {
            revision.revision for revision in scripts.walk_revisions()
        }:
            raise SchemaError(
                f"upgrade requires the exact previous release head {previous!r} "
                f"in this image's migration history; found {current or 'empty'}"
            )
        config.attributes["connection"] = connection
        command.upgrade(config, head)
        if current_heads(connection) != (head,):
            raise SchemaError(f"migration did not reach image head {head}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("serve")
    actions.add_parser("init")
    upgrade = actions.add_parser("upgrade")
    upgrade.add_argument("previous_head")
    args = parser.parse_args()
    try:
        config, scripts, head = image_schema()
        if args.action == "serve":
            with get_readiness_engine().connect() as connection:
                require_image_head(connection, head)
        else:
            previous = args.previous_head if args.action == "upgrade" else None
            maintain(config, scripts, head, previous)
    except SchemaError as error:
        sys.stderr.write(f"schema-guard: {error}\n")
        return 1
    except Exception as error:
        # Settings and driver exceptions can include submitted credentials.
        sqlstate = getattr(error.orig, "sqlstate", None) if isinstance(error, DBAPIError) else None
        detail = f", SQLSTATE {sqlstate}" if sqlstate else ""
        sys.stderr.write(
            f"schema-guard: {args.action} failed ({type(error).__name__}{detail}); "
            "check database connectivity, configuration and migration prerequisites\n"
        )
        return 1
    if args.action == "serve":
        os.execvp(
            "uvicorn",
            [
                "uvicorn",
                "florabase.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
                "--no-server-header",
                "--no-proxy-headers",
            ],
        )
    sys.stdout.write(f"schema-guard: database at image head {head}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
