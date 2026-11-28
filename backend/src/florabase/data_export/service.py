"""Stream the full collection export: one ZIP of CSV files, a manifest and a README.

The ZIP is written into an unseekable sink and handed out chunk by chunk, so memory stays bounded by
one row batch and libraries of any size work (zip64 entries). Every entry carries a fixed
timestamp and rows have a deterministic order, so two exports of unchanged data differ only in
``manifest.json``.
"""

import csv
import hashlib
import io
import json
import logging
import time
import zipfile
from collections.abc import Callable, Generator, Iterator, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Column, Select, Table, func, select, text, union
from sqlalchemy.orm import Session

from florabase import __version__
from florabase.attachments.model import Attachment, AttachmentState
from florabase.attachments.storage import AttachmentStorage, AttachmentStorageError
from florabase.data_export.registry import (
    LABEL_TABLES,
    LINEAGE_EDGES_FILE,
    TABLES,
    ExportTable,
)
from florabase.db.base import Base
from florabase.import_export.service import date_cell, safe_cell
from florabase.lineage.service import _CHILD_EDGES

logger = logging.getLogger(__name__)

FORMAT = "florabase-data-export"
FORMAT_VERSION = 1
ROW_BATCH = 500
FILE_CHUNK = 1024 * 1024
# Fixed entry timestamp (the earliest ZIP date), so entry headers never depend on the clock.
ENTRY_TIME = (1980, 1, 1, 0, 0, 0)
FILE_EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
README_NAME = "README.txt"
MANIFEST_NAME = "manifest.json"
FILES_DIR = "files"

README = """Florabase full data export
==========================

This ZIP holds every collection record of this Florabase installation as CSV files, one file
per table, readable in a spreadsheet (UTF-8) and by scripts.

What is included
- Collection records and their history: botanical identities and names, seed lots, sowings,
  germination, plants, plant groups, events (with measurement corrections), vegetative lots,
  propagation attempts and rooting, harvests and dispositions, locations, suppliers, orders,
  provenance sites, the geographic places the collection uses, schedule, saved views, media
  metadata and record photo links, and non-secret installation settings.
- lineage_edges.csv: every recorded source relationship (parent -> child).
- External catalogue links (WFO, WCVP, GBIF): provider ids only, no licensed provider data.
- files/: the photo files, only when "Include photos and files" was chosen.
  attachments.csv maps each attachment id to its file_path.

What is not included
- User accounts, passwords, sessions, login security state, undo receipts and provider caches.

Format
- Ids are UUIDs; a column ending in _id points to the id column of another file in this export.
  Columns ending in _label repeat a readable name next to it.
- Dates are ISO 8601. A partial date has a <name> column (YYYY, YYYY-MM or YYYY-MM-DD) and a
  <name>_precision column. Timestamps are UTC. Booleans are true/false.
- A text cell starting with = + - or @ is prefixed with ' so spreadsheets do not run it.
- manifest.json lists every file with its row count and SHA-256.

This export is NOT a backup and cannot be imported back. To protect or move an installation use
the backup and restore procedure: docs/operate/backup-restore.md in the Florabase documentation.
"""


@dataclass
class ExportOptions:
    include_files: bool


@dataclass
class _FileRecord:
    path: str
    rows: int | None
    bytes: int = 0
    digest: Any = field(default_factory=hashlib.sha256)

    def manifest(self) -> dict[str, object]:
        result: dict[str, object] = {
            "path": self.path,
            "bytes": self.bytes,
            "sha256": self.digest.hexdigest(),
        }
        if self.rows is not None:
            result["rows"] = self.rows
        return result


class _Sink(io.RawIOBase):
    """Unseekable write target; the generator drains what ZipFile wrote so far."""

    def __init__(self) -> None:
        self._chunks: list[bytes] = []

    def writable(self) -> bool:
        return True

    def write(self, data: Any) -> int:
        chunk = bytes(data)
        self._chunks.append(chunk)
        return len(chunk)

    def drain(self) -> bytes:
        data = b"".join(self._chunks)
        self._chunks.clear()
        return data


@dataclass(frozen=True)
class _Column:
    header: str
    read: Callable[[Mapping[Any, Any]], str]


def table_for(name: str) -> Table:
    return Base.metadata.tables[name]


def _partial_date_prefixes(table: Table) -> set[str]:
    names = set(table.columns.keys())
    return {
        name.removesuffix("_precision")
        for name in names
        if name.endswith("_precision")
        and {f"{name.removesuffix('_precision')}_{part}" for part in ("year", "month", "day")}
        <= names
    }


def _label_target(column: Column[Any]) -> str | None:
    for key in column.foreign_keys:
        target = key.column.table.name
        if key.column.name == "id" and (target in LABEL_TABLES or target == "users"):
            return target
    return None


def format_value(value: object) -> str:
    """One database value as CSV text; only free text gets formula-injection protection."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat() if value.tzinfo else value.isoformat()
    if isinstance(value, (date, UUID, Decimal, int, float)):
        return str(value)
    if isinstance(value, (dict, list)):
        return safe_cell(
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
            text_field=True,
        )
    return safe_cell(value, text_field=True)


class _Labels:
    """Readable names for the label tables, loaded once from the export snapshot."""

    def __init__(self, database: Session) -> None:
        self.values: dict[str, dict[UUID, str]] = {}
        for name in LABEL_TABLES:
            table = table_for(name)
            if name == "botanical_identities":
                rows = database.execute(
                    select(table.c.id, table.c.scientific_name, table.c.cultivar_name)
                )
                self.values[name] = {
                    row[0]: row[1] + (f" '{row[2]}'" if row[2] else "") for row in rows
                }
                continue
            column = table.c.name if "name" in table.c else table.c.label
            self.values[name] = {
                row[0]: row[1] or "" for row in database.execute(select(table.c.id, column))
            }
        users = table_for("users")
        self.values["users"] = {
            row[0]: row[1] or ""
            for row in database.execute(select(users.c.id, users.c.display_name))
        }

    def get(self, target: str, value: object) -> str:
        if value is None:
            return ""
        return safe_cell(self.values[target].get(cast(UUID, value), ""), text_field=True)


def export_columns(entry: ExportTable, labels: _Labels | None = None) -> list[_Column]:
    """The CSV columns of one exported table in declared order (labels may be None for headers)."""
    table = table_for(entry.table)
    prefixes = _partial_date_prefixes(table)
    skipped = {f"{prefix}_{part}" for prefix in prefixes for part in ("year", "month", "day")}
    columns: list[_Column] = []
    for column in table.columns:
        name = column.name
        target = _label_target(column)
        if name in skipped:
            continue
        if name in entry.dropped:
            if target == "users":
                header = name.removesuffix("_id").removesuffix("_user") + "_display_name"
                columns.append(_Column(header, _label_reader(labels, target, name)))
            continue
        if name.endswith("_precision") and name.removesuffix("_precision") in prefixes:
            prefix = name.removesuffix("_precision")
            columns.append(_Column(prefix, _date_reader(prefix)))
            columns.append(_Column(name, _value_reader(name)))
            continue
        columns.append(_Column(name, _value_reader(name)))
        if target is not None and target != "users":
            header = name.removesuffix("_id") + "_label"
            columns.append(_Column(header, _label_reader(labels, target, name)))
    return columns


def _value_reader(name: str) -> Callable[[Mapping[Any, Any]], str]:
    return lambda row: format_value(row[name])


class _Attributes:
    """Attribute access over a row mapping, the shape ``date_cell`` reads."""

    def __init__(self, row: Mapping[Any, Any]) -> None:
        self._row = row

    def __getattr__(self, item: str) -> object:
        return self._row[item]


def _date_reader(prefix: str) -> Callable[[Mapping[Any, Any]], str]:
    return lambda row: date_cell(_Attributes(row), prefix)


def _label_reader(
    labels: _Labels | None, target: str, name: str
) -> Callable[[Mapping[Any, Any]], str]:
    def read(row: Mapping[Any, Any]) -> str:
        assert labels is not None
        return labels.get(target, row[name])

    return read


def _ordered(entry: ExportTable) -> Select[Any]:
    table = table_for(entry.table)
    keys = list(table.primary_key.columns)
    if "created_at" in table.c:
        keys = [table.c.created_at, *keys]
    statement = select(table)
    if entry.referenced_only:
        statement = statement.where(table.c.id.in_(_referenced_places()))
    return statement.order_by(*keys)


def _referenced_places() -> Select[Any]:
    """Geographic places any exported row points at, plus all their ancestors."""
    places = table_for("geographic_places")
    sources = []
    for entry in TABLES:
        table = table_for(entry.table)
        for column in table.columns:
            if column.name in entry.dropped or table is places:
                continue
            if any(key.column is places.c.id for key in column.foreign_keys):
                sources.append(select(column.label("id")).where(column.is_not(None)))
    direct = union(*sources).cte("direct_places")
    ancestry = (
        select(places.c.id, places.c.parent_id)
        .where(places.c.id.in_(select(direct.c.id)))
        .cte("place_ancestry", recursive=True)
    )
    ancestry = ancestry.union(
        select(places.c.id, places.c.parent_id).join(ancestry, places.c.id == ancestry.c.parent_id)
    )
    return select(ancestry.c.id)


_LINEAGE = text(
    f"""
    SELECT edge.parent_kind, edge.parent_id, edge.kind AS child_kind, edge.id AS child_id
    FROM ({_CHILD_EDGES}) AS edge
    ORDER BY edge.parent_kind, edge.parent_id, edge.kind, edge.id
    """
)
LINEAGE_COLUMNS = ("parent_kind", "parent_id", "child_kind", "child_id")


def alembic_revision(database: Session) -> str | None:
    return database.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()


@dataclass(frozen=True)
class ExportSummary:
    records: int
    attachments: int
    attachment_bytes: int


def summary(database: Session) -> ExportSummary:
    records = 0
    for entry in TABLES:
        if entry.referenced_only:
            continue
        records += database.execute(
            select(func.count()).select_from(table_for(entry.table))
        ).scalar_one()
    count, size = database.execute(
        select(func.count(), func.coalesce(func.sum(Attachment.byte_size), 0)).where(
            Attachment.state == AttachmentState.ACTIVE
        )
    ).one()
    return ExportSummary(records=records, attachments=count, attachment_bytes=int(size))


def _entry(name: str, *, compress: bool = True) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=ENTRY_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    info.external_attr = 0o644 << 16
    return info


def _csv_line(values: list[str]) -> bytes:
    buffer = io.StringIO(newline="")
    csv.writer(buffer, lineterminator="\r\n").writerow(values)
    return buffer.getvalue().encode("utf-8")


def stream_export(
    database: Session,
    options: ExportOptions,
    *,
    storage: AttachmentStorage | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> Generator[bytes]:
    """Yield the export ZIP; ``database`` should be one read-only consistent snapshot."""
    stage = ["start"]
    try:
        yield from _stream(database, options, storage=storage, now=now, stage=stage)
    except GeneratorExit:
        logger.info("Full data export stopped by the client", extra={"export_stage": stage[0]})
        raise
    except Exception as error:
        # The 200 response has started, so the client sees a truncated ZIP; log only where and
        # which error type, never record content.
        logger.error(
            "Full data export failed",
            extra={"export_stage": stage[0], "export_error": type(error).__name__},
        )
        raise


def _stream(
    database: Session,
    options: ExportOptions,
    *,
    storage: AttachmentStorage | None = None,
    now: Callable[[], datetime],
    stage: list[str],
) -> Iterator[bytes]:
    started = time.monotonic()
    exported_at = now()
    sink = _Sink()
    records: list[_FileRecord] = []
    archive = zipfile.ZipFile(sink, "w")

    def write(record: _FileRecord, handle: Any, data: bytes) -> None:
        record.bytes += len(data)
        record.digest.update(data)
        handle.write(data)

    readme = _FileRecord(README_NAME, rows=None)
    with archive.open(_entry(README_NAME), "w", force_zip64=True) as handle:
        write(readme, handle, README.encode("utf-8"))
    records.append(readme)
    yield sink.drain()

    included_files: dict[UUID, str] = {}
    missing = 0
    if options.include_files and storage is not None:
        stage[0] = FILES_DIR
        attachments = database.execute(
            select(
                Attachment.id, Attachment.storage_key, Attachment.byte_size, Attachment.media_type
            )
            .where(Attachment.state == AttachmentState.ACTIVE)
            .order_by(Attachment.created_at, Attachment.id)
        ).all()
        for attachment_id, storage_key, byte_size, media_type in attachments:
            try:
                path = storage.active_path(storage_key, byte_size)
            except AttachmentStorageError:
                missing += 1
                continue
            try:
                # Opened before the entry starts: a file deleted or unreadable since the snapshot
                # is counted as missing instead of truncating the ZIP after the 200 response.
                source = path.open("rb")
            except OSError:
                missing += 1
                continue
            name = f"{FILES_DIR}/{attachment_id}{FILE_EXTENSIONS.get(media_type, '')}"
            with (
                source,
                archive.open(_entry(name, compress=False), "w", force_zip64=True) as handle,
            ):
                while chunk := source.read(FILE_CHUNK):
                    handle.write(chunk)
                    yield sink.drain()
            included_files[attachment_id] = name
            yield sink.drain()

    labels = _Labels(database)
    for entry in TABLES:
        stage[0] = entry.table
        record = _FileRecord(entry.file, rows=0)
        columns = export_columns(entry, labels)
        headers = [column.header for column in columns]
        if entry.table == "attachments":
            headers.append("file_path")
        with archive.open(_entry(entry.file), "w", force_zip64=True) as handle:
            write(record, handle, "﻿".encode() + _csv_line(headers))
            result = database.execute(_ordered(entry).execution_options(yield_per=ROW_BATCH))
            for partition in result.mappings().partitions():
                lines = []
                for row in partition:
                    values = [column.read(row) for column in columns]
                    if entry.table == "attachments":
                        values.append(included_files.get(row["id"], ""))
                    lines.append(_csv_line(values))
                record.rows = (record.rows or 0) + len(partition)
                write(record, handle, b"".join(lines))
                yield sink.drain()
        records.append(record)
        yield sink.drain()

    stage[0] = LINEAGE_EDGES_FILE
    lineage = _FileRecord(LINEAGE_EDGES_FILE, rows=0)
    with archive.open(_entry(LINEAGE_EDGES_FILE), "w", force_zip64=True) as handle:
        write(lineage, handle, "﻿".encode() + _csv_line(list(LINEAGE_COLUMNS)))
        for row in database.execute(_LINEAGE).mappings():
            write(lineage, handle, _csv_line([format_value(row[name]) for name in LINEAGE_COLUMNS]))
            lineage.rows = (lineage.rows or 0) + 1
    records.append(lineage)
    yield sink.drain()

    stage[0] = MANIFEST_NAME
    manifest = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "florabase_version": __version__,
        "alembic_revision": alembic_revision(database),
        "exported_at": exported_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "include_files": options.include_files,
        "attachment_files": {"included": len(included_files), "missing": missing},
        "files": [record.manifest() for record in records],
    }
    with archive.open(_entry(MANIFEST_NAME), "w", force_zip64=True) as handle:
        handle.write(json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8") + b"\n")
    archive.close()
    yield sink.drain()
    logger.info(
        "Full data export finished",
        extra={
            "export_rows": sum(record.rows or 0 for record in records),
            "export_files": len(included_files),
            "export_missing_files": missing,
            "export_seconds": round(time.monotonic() - started, 2),
        },
    )


__all__ = [
    "LINEAGE_COLUMNS",
    "ExportOptions",
    "ExportSummary",
    "export_columns",
    "format_value",
    "stream_export",
    "summary",
]
