"""Hardened read-only access to SQLite reference indexes built by Florabase's own builders.

A reference index is a file an operator provisions, so its schema is untrusted input: a crafted
file can replace a table the application queries with a view or a virtual table (for example
FTS5) and drive SQLite extension code from an ordinary query. Every connection therefore
disables views, triggers, extension loading and untrusted schema functions, and requires the
file's complete schema to equal the exact layout the supported builder writes, before any
application statement runs. The schema check and the application queries share one read
transaction, so a cooperating writer cannot change the schema in between.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Final

logger = logging.getLogger(__name__)

# (type, name, tbl_name, sql) exactly as sqlite_schema records it; automatic PRIMARY KEY/UNIQUE
# indexes have no SQL text.
SchemaObject = tuple[str, str, str, str | None]
SchemaContract = frozenset[SchemaObject]

# Defensive mode, no views, no triggers, no extension loading and no schema-invoked functions.
_CONNECTION_HARDENING: Final = (
    (sqlite3.SQLITE_DBCONFIG_DEFENSIVE, True),
    (sqlite3.SQLITE_DBCONFIG_TRUSTED_SCHEMA, False),
    (sqlite3.SQLITE_DBCONFIG_ENABLE_VIEW, False),
    (sqlite3.SQLITE_DBCONFIG_ENABLE_TRIGGER, False),
    (sqlite3.SQLITE_DBCONFIG_ENABLE_LOAD_EXTENSION, False),
    (sqlite3.SQLITE_DBCONFIG_WRITABLE_SCHEMA, False),
)
_MAX_REPORTED_OBJECTS: Final = 10


class UnsupportedIndexError(ValueError):
    """The file is not an index in the layout the supported builder writes."""


def _describe(objects: set[SchemaObject]) -> str:
    # Names come from the untrusted file: quote and bound them for the operator log.
    shown = sorted(f"{kind} {name[:64]!r}" for kind, name, _table, _sql in objects)
    if len(shown) > _MAX_REPORTED_OBJECTS:
        shown = [*shown[:_MAX_REPORTED_OBJECTS], f"... {len(shown) - _MAX_REPORTED_OBJECTS} more"]
    return ", ".join(shown)


def open_reference_index(path: Path, contract: SchemaContract, label: str) -> sqlite3.Connection:
    """Open ``path`` read-only and return it only if its schema equals ``contract``.

    Raises ``UnsupportedIndexError`` (a ``ValueError``) for a schema that differs in any object,
    and ``sqlite3.Error`` for a file SQLite cannot read; the connection is closed in both cases.
    """
    connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        for option, enabled in _CONNECTION_HARDENING:
            connection.setconfig(option, enabled)
            if connection.getconfig(option) != enabled:
                raise UnsupportedIndexError("SQLite connection hardening is unavailable")
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA cell_size_check=ON")
        # Hold one read transaction (and its shared lock) from the schema check to close().
        connection.execute("BEGIN")
        found = {
            (str(kind), str(name), str(table), None if sql is None else str(sql))
            for kind, name, table, sql in connection.execute(
                "SELECT type, name, tbl_name, sql FROM sqlite_schema"
            )
        }
        if found != contract:
            logger.warning(
                "Refusing %s reference index %s: not the layout Florabase's builder writes "
                "(unexpected: %s; missing: %s)",
                label,
                path.name[:128],
                _describe(found - contract) or "none",
                _describe(set(contract) - found) or "none",
            )
            raise UnsupportedIndexError("Unsupported reference index schema")
        connection.row_factory = sqlite3.Row
        return connection
    except BaseException:
        connection.close()
        raise
