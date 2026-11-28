"""DATA-EXPORT-001 streaming and API behaviour without PostgreSQL (fake read-only session).

The PostgreSQL behaviour (snapshot, real tables, golden dataset) is covered by
tests/integration/test_data_export.py; these tests pin the archive layout and edge cases.
"""

import asyncio
import csv
import hashlib
import io
import json
import logging
import zipfile
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import Select, TextClause
from sqlalchemy.orm import Session

import florabase.main  # noqa: F401  (registers every model on Base.metadata)
from florabase.attachments.storage import AttachmentStorage, AttachmentStorageError
from florabase.core.config import Environment, Settings
from florabase.data_export import api as export_api
from florabase.data_export import service
from florabase.data_export.registry import TABLES
from florabase.data_export.service import (
    LINEAGE_COLUMNS,
    MANIFEST_NAME,
    README_NAME,
    ExportOptions,
    stream_export,
    summary,
)

FIXED = datetime(2026, 11, 28, 12, 0, tzinfo=UTC)
IDENTITY = UUID("01900000-0000-7000-8000-000000000001")
PLANT = UUID("01900000-0000-7000-8000-000000000002")
OWNER = UUID("01900000-0000-7000-8000-000000000003")
PHOTO = UUID("01900000-0000-7000-8000-000000000004")
GONE = UUID("01900000-0000-7000-8000-000000000005")
SOWING = UUID("01900000-0000-7000-8000-000000000006")
LOT = UUID("01900000-0000-7000-8000-000000000007")
PHOTO_BYTES = b"\x89PNG\r\n\x1a\nphoto"


def _data() -> dict[str, list[dict[str, Any]]]:
    created = datetime(2026, 1, 2, 3, 4, tzinfo=UTC)
    return {
        "users": [{"id": OWNER, "display_name": "Owner"}],
        "botanical_identities": [
            {
                "id": IDENTITY,
                "scientific_name": "Aloe vera",
                "cultivar_name": "Gold",
                "created_at": created,
            }
        ],
        "plants": [
            {
                "id": PLANT,
                "botanical_identity_id": IDENTITY,
                "label": "=cmd()",
                "lifecycle": "active",
                "collection_entry_date_precision": "month",
                "collection_entry_date_year": 2025,
                "collection_entry_date_month": 4,
                "collection_entry_date_day": None,
                "notes": "-2 leaves",
                "created_at": created,
            }
        ],
        "saved_views": [
            {"id": UUID(int=9), "owner_id": OWNER, "state": {"b": 1, "a": [2]}, "name": "Mine"}
        ],
        "attachments": [
            {
                "id": PHOTO,
                "storage_key": "keep",
                "byte_size": len(PHOTO_BYTES),
                "media_type": "image/png",
                "sha256": hashlib.sha256(PHOTO_BYTES).hexdigest(),
                "state": "active",
                "created_at": created,
            },
            {
                "id": GONE,
                "storage_key": "gone",
                "byte_size": 3,
                "media_type": "image/jpeg",
                "state": "active",
                "created_at": created,
            },
        ],
    }


class _Mappings:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def __iter__(self) -> Iterator[dict[str, Any]]:
        return iter(self.rows)

    def partitions(self) -> Iterator[list[dict[str, Any]]]:
        if self.rows:
            yield self.rows


class _Result:
    def __init__(self, names: list[str], rows: list[dict[str, Any]], scalar: object = None):
        self.names = names
        self.maps = [{name: row.get(name) for name in names} for row in rows]
        self.scalar = scalar

    def __iter__(self) -> Iterator[tuple[Any, ...]]:
        return iter(self.all())

    def all(self) -> list[tuple[Any, ...]]:
        return [tuple(row[name] for name in self.names) for row in self.maps]

    def mappings(self) -> _Mappings:
        return _Mappings(self.maps)

    def scalar_one(self) -> object:
        return self.scalar

    def scalar_one_or_none(self) -> object:
        return self.scalar

    def one(self) -> tuple[Any, ...]:
        return cast(tuple[Any, ...], self.scalar)


class _FakeSession:
    """Answers the export's statements from in-memory rows keyed by table name."""

    def __init__(self, data: dict[str, list[dict[str, Any]]]) -> None:
        self.data = data

    def execute(self, statement: Any) -> _Result:
        if isinstance(statement, TextClause):
            if "alembic_version" in statement.text:
                return _Result([], [], scalar="20261125_0050")
            edge = {
                "parent_kind": "sowing",
                "parent_id": SOWING,
                "child_kind": "plant",
                "child_id": PLANT,
            }
            return _Result(list(LINEAGE_COLUMNS), [edge])
        assert isinstance(statement, Select)
        table = statement.get_final_froms()[0]
        rows = self.data.get(getattr(table, "name", ""), [])
        names = [column.name for column in statement.selected_columns]
        if names and names[0].startswith("count"):
            sizes = sum(row.get("byte_size", 0) for row in rows)
            return _Result([], [], scalar=(len(rows), sizes) if len(names) == 2 else len(rows))
        return _Result(names, rows)


class _Storage:
    def __init__(self, root: Path) -> None:
        self.root = root

    def active_path(self, storage_key: str, expected_size: int) -> Path:
        if storage_key == "gone":
            raise AttachmentStorageError("attachment_content_missing", "missing")
        return self.root / storage_key


def _export(*, include_files: bool, root: Path | None = None) -> zipfile.ZipFile:
    session = cast(Session, _FakeSession(_data()))
    storage = cast(AttachmentStorage, _Storage(root)) if root else None
    data = b"".join(
        stream_export(
            session, ExportOptions(include_files=include_files), storage=storage, now=lambda: FIXED
        )
    )
    archive = zipfile.ZipFile(io.BytesIO(data))
    assert archive.testzip() is None
    return archive


def _rows(archive: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    content = archive.read(name).decode("utf-8")
    assert content.startswith("﻿")
    return list(csv.DictReader(io.StringIO(content.removeprefix("﻿"), newline="")))


def test_archive_layout_manifest_and_values(tmp_path: Path) -> None:
    (tmp_path / "keep").write_bytes(PHOTO_BYTES)
    archive = _export(include_files=True, root=tmp_path)
    names = archive.namelist()
    assert names[0] == README_NAME
    assert names[-1] == MANIFEST_NAME
    assert f"files/{PHOTO}.png" in names
    for entry in TABLES:
        assert entry.file in names
    manifest = json.loads(archive.read(MANIFEST_NAME))
    assert manifest["exported_at"] == "2026-11-28T12:00:00Z"
    assert manifest["alembic_revision"] == "20261125_0050"
    assert manifest["include_files"] is True
    assert manifest["attachment_files"] == {"included": 1, "missing": 1}
    listed = {item["path"]: item for item in manifest["files"]}
    assert "rows" not in listed[README_NAME]
    assert listed["plants.csv"]["rows"] == 1
    assert listed["plants.csv"]["sha256"] == hashlib.sha256(archive.read("plants.csv")).hexdigest()
    assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist())

    plant = _rows(archive, "plants.csv")[0]
    assert plant["botanical_identity_label"] == "Aloe vera 'Gold'"
    assert plant["label"] == "'=cmd()"
    assert plant["notes"] == "'-2 leaves"
    assert plant["collection_entry_date"] == "2025-04"
    assert plant["collection_entry_date_precision"] == "month"
    assert plant["created_at"] == "2026-01-02T03:04:00+00:00"
    assert plant["supplier_id"] == plant["supplier_label"] == ""
    view = _rows(archive, "saved_views.csv")[0]
    assert view["owner_display_name"] == "Owner"
    assert view["state"] == '{"a":[2],"b":1}'
    photos = {row["id"]: row["file_path"] for row in _rows(archive, "attachments.csv")}
    assert photos == {str(PHOTO): f"files/{PHOTO}.png", str(GONE): ""}
    assert archive.read(f"files/{PHOTO}.png") == PHOTO_BYTES
    edges = _rows(archive, "lineage_edges.csv")
    assert edges == [
        {
            "parent_kind": "sowing",
            "parent_id": str(SOWING),
            "child_kind": "plant",
            "child_id": str(PLANT),
        }
    ]
    assert b"storage_key" not in archive.read("attachments.csv")
    assert b"keep" not in archive.read("attachments.csv")


def test_a_photo_that_cannot_be_opened_is_counted_missing(tmp_path: Path) -> None:
    # "keep" is not written, so opening it fails after the storage check.
    archive = _export(include_files=True, root=tmp_path)
    manifest = json.loads(archive.read(MANIFEST_NAME))
    assert manifest["attachment_files"] == {"included": 0, "missing": 2}
    assert not any(name.startswith("files/") for name in archive.namelist())


def test_without_files_and_byte_identical_repeat() -> None:
    first = _export(include_files=False)
    assert not any(name.startswith("files/") for name in first.namelist())
    assert json.loads(first.read(MANIFEST_NAME))["include_files"] is False
    second = _export(include_files=False)
    for name in first.namelist():
        assert first.read(name) == second.read(name)


def test_failure_and_client_abort_are_logged_without_content(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    session = cast(Session, _FakeSession(_data()))
    chunks = stream_export(session, ExportOptions(include_files=False), now=lambda: FIXED)
    assert next(chunks)
    chunks.close()
    assert any(r.msg == "Full data export stopped by the client" for r in caplog.records)

    def broken(_database: Session) -> None:
        raise RuntimeError("secret row content")

    monkeypatch.setattr(service, "_Labels", broken)
    with pytest.raises(RuntimeError):
        b"".join(stream_export(session, ExportOptions(include_files=False), now=lambda: FIXED))
    failure = next(r for r in caplog.records if r.msg == "Full data export failed")
    assert failure.__dict__["export_error"] == "RuntimeError"
    assert "secret" not in failure.getMessage()


def test_summary_counts_records_and_photo_bytes() -> None:
    result = summary(cast(Session, _FakeSession(_data())))
    assert result.attachments == 2
    assert result.attachment_bytes == len(PHOTO_BYTES) + 3
    # botanical identities, plants, saved views and attachments (users are not exported).
    assert result.records == 5


def _settings(**values: object) -> Settings:
    return Settings.model_validate(
        {"environment": Environment.TEST, "database_url": "postgresql+psycopg://unused", **values}
    )


def test_export_slots_refuse_when_busy_and_release() -> None:
    slots = [export_api.reserve_export_slot() for _ in range(export_api.MAX_CONCURRENT_EXPORTS)]
    for slot in slots:
        next(slot)
    with pytest.raises(HTTPException) as refused:
        next(export_api.reserve_export_slot())
    assert refused.value.status_code == 429
    assert cast(dict[str, str], refused.value.detail)["code"] == "export_in_progress"
    for slot in slots:
        slot.close()
    again = export_api.reserve_export_slot()
    next(again)
    again.close()


def test_unavailable_storage_is_a_503(tmp_path: Path) -> None:
    with pytest.raises(HTTPException) as unavailable:
        export_api.get_export_storage(_settings(attachment_storage_root=tmp_path / "absent"))
    assert unavailable.value.status_code == 503


def test_export_session_opens_a_read_only_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    statements: list[str] = []
    finished: list[str] = []

    class _Session:
        def __init__(self, _engine: object) -> None:
            pass

        def __enter__(self) -> _Session:
            return self

        def __exit__(self, *_: object) -> None:
            finished.append("closed")

        def execute(self, statement: TextClause) -> None:
            statements.append(statement.text)

        def rollback(self) -> None:
            finished.append("rollback")

    monkeypatch.setattr(export_api, "Session", _Session)
    monkeypatch.setattr(export_api, "get_engine", lambda: object())
    sessions = export_api.get_export_session()
    next(sessions)
    sessions.close()
    assert statements == ["SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"]
    assert finished == ["rollback", "closed"]


def test_endpoints_force_files_off_in_demo_mode() -> None:
    session = cast(Session, _FakeSession(_data()))
    demo = _settings(demo_readonly=True)
    result = export_api.read_full_export_summary(None, session, demo)  # type: ignore[arg-type]
    assert result.files_allowed is False
    response = export_api.export_full_data(None, None, session, demo, include_files=True)  # type: ignore[arg-type]
    assert response.media_type == "application/zip"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-disposition"].startswith(
        'attachment; filename="florabase-export-'
    )

    async def body() -> bytes:
        return b"".join([chunk async for chunk in response.body_iterator])  # type: ignore[misc]

    archive = zipfile.ZipFile(io.BytesIO(asyncio.run(body())))
    assert json.loads(archive.read(MANIFEST_NAME))["include_files"] is False
