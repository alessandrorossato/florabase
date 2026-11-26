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
import time
from collections import Counter
from pathlib import Path
from typing import Final, Literal

import httpx

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
DEFAULT_DOWNLOAD_MAX_SECONDS: Final[float] = 1800.0
ALLOWED_ARCHIVE_CONTENT_TYPES: Final[frozenset[str]] = frozenset(
    {"application/zip", "application/octet-stream"}
)


class UnsupportedIndexError(ValueError):
    """The file is not an index in the layout the supported builder writes."""


class ReferenceDownloadError(ValueError):
    """A pinned reference archive download failed validation or timed out."""

    category: Literal["network", "size"] = "network"


class ReferenceDownloadSizeError(ReferenceDownloadError):
    """Archive exceeded or did not match the expected byte bound."""

    category: Literal["network", "size"] = "size"


class ReferenceDownloadTimeoutError(ReferenceDownloadError):
    """Archive download exceeded the configured wall-clock cap."""

    category: Literal["network", "size"] = "network"


class ReferenceDownloadContentTypeError(ReferenceDownloadError):
    """Archive response carried an unexpected Content-Type."""

    category: Literal["network", "size"] = "network"


def _validate_archive_content_type(
    headers: httpx.Headers,
    allowed: frozenset[str],
    label: str,
) -> None:
    # Zenodo emits duplicate `content-type: application/octet-stream` headers on GET.
    raw_values = headers.get_list("content-type")
    media_types = [
        part.split(";", 1)[0].strip().lower()
        for value in raw_values
        for part in value.split(",")
        if part.strip()
    ]
    if not media_types or any(media not in allowed for media in media_types):
        raise ReferenceDownloadContentTypeError(f"Unexpected {label} archive content type")


def _validate_content_length(
    headers: httpx.Headers,
    *,
    max_bytes: int,
    exact_bytes: int | None,
    label: str,
) -> None:
    raw_lengths = headers.get_list("content-length")
    if not raw_lengths:
        return
    if len(raw_lengths) != 1:
        raise ReferenceDownloadSizeError(f"Ambiguous {label} archive Content-Length header")
    raw = raw_lengths[0].strip()
    if not raw.isdigit():
        raise ReferenceDownloadSizeError(f"Invalid {label} archive Content-Length header")
    declared = int(raw)
    if declared > max_bytes or (exact_bytes is not None and declared != exact_bytes):
        raise ReferenceDownloadSizeError(f"{label} download exceeds size bound")


def download_archive(
    url: str,
    destination: Path,
    *,
    max_bytes: int,
    exact_bytes: int | None = None,
    max_seconds: float = DEFAULT_DOWNLOAD_MAX_SECONDS,
    connect_timeout: float = 10.0,
    read_timeout: float = 60.0,
    accept: str = "*/*",
    allowed_content_types: frozenset[str] = ALLOWED_ARCHIVE_CONTENT_TYPES,
    label: str = "Reference",
) -> int:
    """Stream a pinned official archive to ``destination`` with strict HTTP, size & time bounds."""
    if max_seconds <= 0:
        raise ValueError("max_seconds must be positive")
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    size = 0
    started = time.monotonic()
    with (
        httpx.Client(
            timeout=httpx.Timeout(read_timeout, connect=connect_timeout),
            follow_redirects=False,
        ) as client,
        client.stream("GET", url, headers={"Accept": accept}) as response,
    ):
        response.raise_for_status()
        _validate_archive_content_type(response.headers, allowed_content_types, label)
        _validate_content_length(
            response.headers,
            max_bytes=max_bytes,
            exact_bytes=exact_bytes,
            label=label,
        )
        with destination.open("wb") as output:
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > max_bytes:
                    raise ReferenceDownloadSizeError(f"{label} download exceeds size bound")
                if time.monotonic() - started > max_seconds:
                    raise ReferenceDownloadTimeoutError(f"{label} download timed out")
                output.write(chunk)
    if exact_bytes is not None and size != exact_bytes:
        raise ReferenceDownloadSizeError(f"Unexpected {label} archive size")
    return size


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
        # No other database can be attached to a reference connection.
        connection.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA cell_size_check=ON")
        # Hold one read transaction (and its shared lock) from the schema check to close().
        connection.execute("BEGIN")
        rows = [
            (str(kind), str(name), str(table), None if sql is None else str(sql))
            for kind, name, table, sql in connection.execute(
                "SELECT type, name, tbl_name, sql FROM sqlite_schema"
            )
        ]
        found = set(rows)
        # Duplicate rows (for example a second automatic index) must not collapse into the set,
        # so the row count must match too. Both checks are linear in the schema size.
        if len(rows) != len(contract) or found != contract:
            duplicated = {row for row, count in Counter(rows).items() if count > 1}
            logger.warning(
                "Refusing %s reference index %s: not the layout Florabase's builder writes "
                "(unexpected: %s; missing: %s; duplicated: %s)",
                label,
                path.name[:128],
                _describe(found - contract) or "none",
                _describe(set(contract) - found) or "none",
                _describe(duplicated) or "none",
            )
            raise UnsupportedIndexError("Unsupported reference index schema")
        connection.row_factory = sqlite3.Row
        return connection
    except BaseException:
        connection.close()
        raise
