"""DATA-EXPORT-001 against the golden dataset in disposable PostgreSQL."""

import asyncio
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
import zipfile
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from sqlalchemy import Engine, create_engine, func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from florabase.attachments.storage import AttachmentStorage
from florabase.auth.dependencies import require_authenticated_actor
from florabase.core.config import CookieMode, Environment, Settings, get_settings
from florabase.data_export import api as export_api
from florabase.data_export import service as export_service
from florabase.data_export.api import get_export_session
from florabase.data_export.registry import EXCLUDED, TABLES, classification_errors
from florabase.data_export.service import (
    LINEAGE_COLUMNS,
    MANIFEST_NAME,
    ExportOptions,
    stream_export,
    table_for,
)
from florabase.db.session import get_database_session
from florabase.main import app

sys.path.insert(0, "/review")
pytest.importorskip("golden_plan", reason="available in integration runner only")
pytestmark = pytest.mark.integration
SCRIPT = "/review/golden_dataset.py"
COPIES = Path("/tmp/florabase-golden")
COPY = "golden_data_export"
ORIGIN = "https://florabase.example"
FIXED = datetime(2026, 11, 28, 12, 0, tzinfo=UTC)


def _golden(*arguments: str) -> None:
    result = subprocess.run(
        [sys.executable, SCRIPT, *arguments, "--copy", COPY],
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    _golden("create-copy")
    try:
        _golden("generate")
        url = make_url(get_settings().database_url).set(database=COPY)
        golden = create_engine(url)
        try:
            yield golden
        finally:
            golden.dispose()
    finally:
        _golden("retire-copy")


def _snapshot(engine: Engine) -> Session:
    session = Session(engine)
    session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
    return session


def _export(engine: Engine, *, include_files: bool = False) -> bytes:
    storage = AttachmentStorage(COPIES / COPY) if include_files else None
    with _snapshot(engine) as session:
        return b"".join(
            stream_export(
                session,
                ExportOptions(include_files=include_files),
                storage=storage,
                now=lambda: FIXED,
            )
        )


def _rows(archive: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    content = archive.read(name).decode("utf-8")
    assert content.startswith("﻿"), name
    return list(csv.DictReader(io.StringIO(content.removeprefix("﻿"), newline="")))


def test_database_tables_are_all_classified(engine: Engine) -> None:
    assert classification_errors(set(inspect(engine).get_table_names()), database=True) == []


def test_golden_export_parses_counts_match_and_references_resolve(engine: Engine) -> None:
    archive = zipfile.ZipFile(io.BytesIO(_export(engine)))
    manifest = json.loads(archive.read(MANIFEST_NAME))
    assert manifest["format_version"] == 1
    assert manifest["include_files"] is False
    with Session(engine) as session:
        assert (
            manifest["alembic_revision"]
            == session.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        )
        counts = {
            entry.table: session.execute(
                select(func.count()).select_from(table_for(entry.table))
            ).scalar_one()
            for entry in TABLES
        }
    listed = {item["path"]: item for item in manifest["files"]}
    ids: dict[str, set[str]] = {}
    files: dict[str, list[dict[str, str]]] = {}
    for entry in TABLES:
        rows = _rows(archive, entry.file)
        files[entry.table] = rows
        assert listed[entry.file]["rows"] == len(rows)
        data = archive.read(entry.file)
        assert listed[entry.file]["sha256"] == hashlib.sha256(data).hexdigest()
        if entry.referenced_only:
            assert 0 < len(rows) <= counts[entry.table]
        else:
            assert len(rows) == counts[entry.table], entry.table
        if "id" in table_for(entry.table).c:
            ids[entry.table] = {row["id"] for row in rows}
    assert sum(counts.values()) > 100
    exported = {entry.table: entry for entry in TABLES}
    for entry in TABLES:
        for column in table_for(entry.table).columns:
            if column.name in entry.dropped:
                continue
            for key in column.foreign_keys:
                target = key.column.table.name
                if key.column.name != "id" or target not in exported:
                    continue
                for row in files[entry.table]:
                    if row[column.name]:
                        assert row[column.name] in ids[target], (entry.table, column.name)
    edges = _rows(archive, "lineage_edges.csv")
    assert edges
    assert list(edges[0]) == list(LINEAGE_COLUMNS)
    tables = {kind: f"{kind}s" for kind in ("seed_lot", "sowing", "plant", "vegetative_lot")}
    tables |= {"plant_group": "plant_groups", "propagation_attempt": "propagation_attempts"}
    for edge in edges:
        assert edge["parent_id"] in ids[tables[edge["parent_kind"]]]
        assert edge["child_id"] in ids[tables[edge["child_kind"]]]


def test_no_secret_or_excluded_data_appears(engine: Engine) -> None:
    data = _export(engine)
    archive = zipfile.ZipFile(io.BytesIO(data))
    names = set(archive.namelist())
    for table in EXCLUDED:
        assert f"{table}.csv" not in names
    content = b"".join(archive.read(name) for name in names)
    with Session(engine) as session:
        secrets = [
            *session.execute(text("SELECT password_hash FROM users")).scalars(),
            *session.execute(text("SELECT token_digest FROM auth_sessions")).scalars(),
            *session.execute(text("SELECT csrf_digest FROM auth_sessions")).scalars(),
            *session.execute(text("SELECT storage_key FROM attachments")).scalars(),
        ]
    assert secrets
    for secret in secrets:
        if secret:
            assert str(secret).encode() not in content


def test_two_exports_of_unchanged_data_are_identical_except_the_manifest_time(
    engine: Engine,
) -> None:
    first = zipfile.ZipFile(io.BytesIO(_export(engine)))
    storage = None
    with _snapshot(engine) as session:
        later = b"".join(
            stream_export(
                session,
                ExportOptions(include_files=False),
                storage=storage,
                now=lambda: datetime(2027, 1, 1, tzinfo=UTC),
            )
        )
    second = zipfile.ZipFile(io.BytesIO(later))
    assert first.namelist() == second.namelist()
    for name in first.namelist():
        if name != MANIFEST_NAME:
            assert first.read(name) == second.read(name), name
    left, right = (json.loads(item.read(MANIFEST_NAME)) for item in (first, second))
    assert left.pop("exported_at") != right.pop("exported_at")
    assert left == right
    assert _export(engine) == _export(engine)


def test_include_files_streams_photos_with_matching_hashes(engine: Engine) -> None:
    archive = zipfile.ZipFile(io.BytesIO(_export(engine, include_files=True)))
    manifest = json.loads(archive.read(MANIFEST_NAME))
    attachments = _rows(archive, "attachments.csv")
    assert attachments
    assert manifest["include_files"] is True
    assert manifest["attachment_files"] == {"included": len(attachments), "missing": 0}
    for row in attachments:
        assert row["file_path"].startswith(f"files/{row['id']}.")
        assert hashlib.sha256(archive.read(row["file_path"])).hexdigest() == row["sha256"]
        assert int(row["byte_size"]) == archive.getinfo(row["file_path"]).file_size


def test_formula_cells_are_neutralised(engine: Engine) -> None:
    with Session(engine) as session:
        session.execute(text("UPDATE plants SET notes = '=HYPERLINK(\"x\")'"))
        data = b"".join(
            stream_export(session, ExportOptions(include_files=False), now=lambda: FIXED)
        )
        session.rollback()
    rows = _rows(zipfile.ZipFile(io.BytesIO(data)), "plants.csv")
    assert rows
    assert all(row["notes"] == '\'=HYPERLINK("x")' for row in rows)


def _settings(*, demo: bool) -> Settings:
    return Settings.model_validate(
        {
            "environment": Environment.TEST,
            "database_url": "postgresql+psycopg://unused",
            "canonical_origin": ORIGIN,
            "cookie_mode": CookieMode.SECURE,
            "attachment_storage_root": str(COPIES / COPY),
            "demo_readonly": demo,
        }
    )


def _serve(engine: Engine, *, demo: bool) -> None:
    def session() -> Iterator[Session]:
        with Session(engine) as database:
            yield database
            database.rollback()

    def snapshot() -> Iterator[Session]:
        with _snapshot(engine) as database:
            yield database

    app.dependency_overrides[get_database_session] = session
    app.dependency_overrides[get_export_session] = snapshot
    app.dependency_overrides[get_settings] = lambda: _settings(demo=demo)


async def _get(path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
        return await client.get(path)


def test_endpoint_requires_authentication(engine: Engine) -> None:
    _serve(engine, demo=False)
    try:
        for path in ("/api/v1/exports/full.zip", "/api/v1/exports/full/summary"):
            assert asyncio.run(_get(path)).status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_demo_mode_exports_without_files(engine: Engine) -> None:
    _serve(engine, demo=True)
    try:
        response = asyncio.run(_get("/api/v1/exports/full.zip?include_files=true"))
        summary: Any = asyncio.run(_get("/api/v1/exports/full/summary")).json()
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["cache-control"] == "no-store"
    disposition = response.headers["content-disposition"]
    assert disposition.startswith('attachment; filename="florabase-export-')
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    assert not any(name.startswith("files/") for name in archive.namelist())
    assert json.loads(archive.read(MANIFEST_NAME))["include_files"] is False
    assert all(row["file_path"] == "" for row in _rows(archive, "attachments.csv"))
    assert summary["files_allowed"] is False
    assert summary["attachments"] > 0
    assert summary["attachment_bytes"] > 0


def test_export_session_is_one_read_only_repeatable_read_snapshot(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(export_api, "get_engine", lambda: engine)
    sessions = export_api.get_export_session()
    session = next(sessions)
    try:
        assert session.execute(text("SHOW transaction_isolation")).scalar_one() == (
            "repeatable read"
        )
        assert session.execute(text("SHOW transaction_read_only")).scalar_one() == "on"
    finally:
        sessions.close()


def test_authenticated_download_with_files_and_unavailable_storage(engine: Engine) -> None:
    _serve(engine, demo=False)
    app.dependency_overrides[require_authenticated_actor] = lambda: None
    try:
        response = asyncio.run(_get("/api/v1/exports/full.zip?include_files=true"))
        broken = _settings(demo=False).model_copy(
            update={"attachment_storage_root": Path("/nonexistent/florabase-attachments")}
        )
        app.dependency_overrides[get_settings] = lambda: broken
        unavailable = asyncio.run(_get("/api/v1/exports/full.zip?include_files=true"))
        without_files = asyncio.run(_get("/api/v1/exports/full.zip"))
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    assert json.loads(archive.read(MANIFEST_NAME))["include_files"] is True
    assert any(name.startswith("files/") for name in archive.namelist())
    assert unavailable.status_code == 503
    assert unavailable.json()["detail"]["message"] == "Attachment storage is unavailable"
    assert without_files.status_code == 200


class _VanishingStorage(AttachmentStorage):
    """The first photo disappears between the snapshot check and the copy."""

    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.vanished = False

    def active_path(self, storage_key: str, expected_size: int) -> Path:
        path = super().active_path(storage_key, expected_size)
        if not self.vanished:
            self.vanished = True
            return path.with_name(path.name + ".gone")
        return path


def test_a_photo_missing_during_the_export_is_counted_not_fatal(engine: Engine) -> None:
    storage = _VanishingStorage(COPIES / COPY)
    with _snapshot(engine) as session:
        data = b"".join(
            stream_export(
                session, ExportOptions(include_files=True), storage=storage, now=lambda: FIXED
            )
        )
    archive = zipfile.ZipFile(io.BytesIO(data))
    assert archive.testzip() is None
    attachments = _rows(archive, "attachments.csv")
    manifest = json.loads(archive.read(MANIFEST_NAME))
    assert manifest["attachment_files"] == {"included": len(attachments) - 1, "missing": 1}
    assert sum(1 for row in attachments if row["file_path"] == "") == 1


def test_a_failing_export_logs_where_without_content(
    engine: Engine, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def broken(_database: Session) -> None:
        raise RuntimeError("secret row content")

    monkeypatch.setattr(export_service, "_Labels", broken)
    with _snapshot(engine) as session, pytest.raises(RuntimeError):
        b"".join(stream_export(session, ExportOptions(include_files=False), now=lambda: FIXED))
    failures = [record for record in caplog.records if record.msg == "Full data export failed"]
    assert len(failures) == 1
    assert failures[0].__dict__["export_error"] == "RuntimeError"
    assert "secret" not in failures[0].getMessage()


def test_concurrent_full_exports_are_limited(engine: Engine) -> None:
    _serve(engine, demo=False)
    app.dependency_overrides[require_authenticated_actor] = lambda: None
    held = 0
    try:
        for _ in range(export_api.MAX_CONCURRENT_EXPORTS):
            assert export_api.EXPORT_SLOTS.acquire(blocking=False)
            held += 1
        busy = asyncio.run(_get("/api/v1/exports/full.zip"))
        while held:
            export_api.EXPORT_SLOTS.release()
            held -= 1
        first = asyncio.run(_get("/api/v1/exports/full.zip"))
        second = asyncio.run(_get("/api/v1/exports/full.zip"))
    finally:
        while held:
            export_api.EXPORT_SLOTS.release()
            held -= 1
        app.dependency_overrides.clear()
    assert busy.status_code == 429
    assert busy.json()["detail"]["code"] == "export_in_progress"
    assert busy.headers["retry-after"] == "30"
    # Finished downloads give their slot back.
    assert (first.status_code, second.status_code) == (200, 200)
    for _ in range(export_api.MAX_CONCURRENT_EXPORTS):
        assert export_api.EXPORT_SLOTS.acquire(blocking=False)
    for _ in range(export_api.MAX_CONCURRENT_EXPORTS):
        export_api.EXPORT_SLOTS.release()


def test_a_client_that_stops_reading_is_logged(
    engine: Engine, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("INFO")
    with _snapshot(engine) as session:
        chunks = stream_export(session, ExportOptions(include_files=False), now=lambda: FIXED)
        assert next(chunks)
        chunks.close()
    assert any(record.msg == "Full data export stopped by the client" for record in caplog.records)
