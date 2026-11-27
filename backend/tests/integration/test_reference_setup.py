"""PostgreSQL-backed integration tests for automatic reference index provisioning."""

from __future__ import annotations

import hashlib
import http.server
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from unittest.mock import patch
from uuid import uuid7

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection
from sqlalchemy.orm import Session
from test_reference_setup import (
    _build_valid_wcvp_v16,
    _build_valid_wfo,
    _make_synthetic_wcvp_zip,
    _make_synthetic_wfo_zip,
)

from florabase.auth.service import authenticate, bootstrap_owner
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.core.config import (
    CookieMode,
    Environment,
    ReferencesSetupMode,
    Settings,
    get_settings,
)
from florabase.db.session import get_database_session
from florabase.main import create_app
from florabase.native_range_enrichment import source as wcvp_source
from florabase.reference_setup.runner import ReferenceSetupCoordinator
from florabase.reference_setup.state import (
    managed_wcvp_v16_path,
    managed_wfo_path,
    reset_runtime_state,
)
from florabase.reference_setup.worker import ProvisionOutcome, provision_index
from florabase.taxonomy import snapshot as wfo_snapshot
from florabase.taxonomy import source as wfo_source

pytestmark = pytest.mark.integration

ORIGIN = "https://florabase.example"


def _make_settings(tmp_path: Path, **overrides: object) -> Settings:
    base = get_settings()
    media = tmp_path / "media"
    media.mkdir(parents=True, exist_ok=True)
    media.chmod(0o700)
    data: dict[str, object] = {
        "environment": Environment.TEST,
        "database_url": base.database_url,
        "canonical_origin": ORIGIN,
        "cookie_mode": CookieMode.SECURE,
        "attachment_storage_root": media,
        "references_state_dir": tmp_path / "state" / "reference",
        "references_setup": ReferencesSetupMode.OFF,
        "wfo_snapshot_path": None,
        "wcvp_v16_snapshot_path": None,
        "wcvp_snapshot_path": None,
    }
    data.update(overrides)
    return Settings.model_validate(data)


def _override_database(connection: Connection) -> Callable[[], Iterator[Session]]:
    def dependency() -> Iterator[Session]:
        with Session(bind=connection, join_transaction_mode="create_savepoint") as database:
            try:
                yield database
                database.commit()
            except Exception:
                database.rollback()
                raise

    return dependency


def _create_owner_cookie_and_identity(
    connection: Connection, tmp_path: Path
) -> tuple[dict[str, str], str]:
    password = "Test-Password-12345!"
    with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
        owner = bootstrap_owner(db, "owner", password)
        db.flush()
        issued = authenticate(db, owner.login_name, password, _make_settings(tmp_path))
        identity = BotanicalIdentity(scientific_name=f"Solanum refsetup {uuid7().hex}")
        db.add(identity)
        db.commit()
        identity_id = str(identity.id)
    return {"__Host-florabase-session": issued.session_token}, identity_id


def _start_fixture_server(
    routes: dict[str, tuple[int, list[tuple[str, str]], bytes]],
) -> tuple[http.server.ThreadingHTTPServer, list[str]]:
    hits: list[str] = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            hits.append(self.path)
            entry = routes.get(self.path)
            if entry is None:
                self.send_response(404)
                self.end_headers()
                return
            code, headers, body = entry
            self.send_response(code)
            for key, value in headers:
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: object) -> None:
            return

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, hits


def test_auto_provisioning_end_to_end_with_local_fixture_server(
    database_connection: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reset_runtime_state()
    wfo_zip, wfo_members = _make_synthetic_wfo_zip()
    wfo_checksum = hashlib.sha256(wfo_zip).hexdigest()
    wcvp_zip, wcvp_sizes = _make_synthetic_wcvp_zip()
    wcvp_checksum = hashlib.sha256(wcvp_zip).hexdigest()

    server, hits = _start_fixture_server(
        {
            "/wfo.zip": (
                200,
                [
                    ("Content-Type", "application/octet-stream"),
                    ("Content-Type", "application/octet-stream"),
                ],
                wfo_zip,
            ),
            "/wcvp.zip": (
                200,
                [("Content-Type", "application/zip")],
                wcvp_zip,
            ),
        }
    )
    port = server.server_address[1]
    wfo_url = f"http://127.0.0.1:{port}/wfo.zip"
    wcvp_url = f"http://127.0.0.1:{port}/wcvp.zip"

    monkeypatch.setattr(wfo_snapshot, "ARCHIVE_URL", wfo_url)
    monkeypatch.setattr(wfo_source, "ARCHIVE_URL", wfo_url)
    monkeypatch.setattr(wfo_snapshot, "ARCHIVE_BYTES", len(wfo_zip))
    monkeypatch.setattr(wfo_snapshot, "CHECKSUM", wfo_checksum)
    monkeypatch.setattr(wfo_snapshot, "MEMBERS", wfo_members)
    monkeypatch.setattr(wfo_source, "CHECKSUM", wfo_checksum)

    test_release = wcvp_source.Release(
        "16",
        wcvp_url,
        wcvp_checksum,
        wcvp_source.RELEASES["16"].citation,
        wcvp_sizes,
    )
    monkeypatch.setattr(
        wcvp_source,
        "RELEASES",
        {"15": wcvp_source.RELEASES["15"], "16": test_release},
    )

    # Run the real provision_index pipeline (real local HTTP + builders + seals + atomic publish)
    # inside the coordinator's async runner so test-only monkeypatched pins apply cleanly.
    async def in_process_worker(key: str, state_dir: Path, max_seconds: float) -> ProvisionOutcome:
        return provision_index(
            key,  # type: ignore[arg-type]
            state_dir,
            max_seconds=max_seconds,
            required_bytes=1024,
        )

    cookies, identity_id = _create_owner_cookie_and_identity(database_connection, tmp_path)
    settings = _make_settings(tmp_path, references_setup=ReferencesSetupMode.AUTO)

    def make_coordinator(cfg: Settings) -> ReferenceSetupCoordinator:
        return ReferenceSetupCoordinator(cfg, worker_runner=in_process_worker)

    try:
        with (
            patch("florabase.main.get_settings", return_value=settings),
            patch("florabase.main.ReferenceSetupCoordinator", side_effect=make_coordinator),
        ):
            app = create_app()
            app.dependency_overrides[get_settings] = lambda: settings
            app.dependency_overrides[get_database_session] = _override_database(database_connection)
            with TestClient(app, base_url=ORIGIN, cookies=cookies) as client:
                # App is immediately healthy while/after provisioning runs.
                assert client.get("/api/v1/health").status_code == 200

                deadline = time.monotonic() + 10.0
                refs = client.get("/api/v1/system/references").json()
                while (
                    refs["wfo"]["state"] != "ready" or refs["wcvp_v16"]["state"] != "ready"
                ) and time.monotonic() < deadline:
                    time.sleep(0.05)
                    refs = client.get("/api/v1/system/references").json()

                assert refs == {
                    "mode": "auto",
                    "wfo": {"state": "ready", "status": "ready", "reason": None, "available": True},
                    "wcvp_v16": {
                        "state": "ready",
                        "status": "ready",
                        "reason": None,
                        "available": True,
                    },
                }
                assert hits == ["/wfo.zip", "/wcvp.zip"]

                # Real WFO and WCVP v16 lookups now work without restart.
                wfo_resp = client.get(
                    "/api/v1/explore/taxonomy/candidates", params={"q": "Solanum"}
                )
                assert wfo_resp.status_code == 200
                assert wfo_resp.json()[0]["taxon"]["scientific_name"] == "Solanum lycopersicum"

                wcvp_src = client.get(
                    f"/api/v1/botanical-identities/{identity_id}/native-range-enrichment/source"
                )
                assert wcvp_src.status_code == 200
                assert wcvp_src.json()["available"] is True

                wcvp_taxa = client.get(
                    f"/api/v1/botanical-identities/{identity_id}/native-range-enrichment/taxa",
                    params={"q": "Solanum"},
                )
                assert wcvp_taxa.status_code == 200
                assert wcvp_taxa.json()[0]["name"] == "Solanum lycopersicum"
    finally:
        server.shutdown()
        server.server_close()
        reset_runtime_state()


def test_off_mode_never_touches_network_and_reuses_sealed_managed_indexes(
    database_connection: Connection, tmp_path: Path
) -> None:
    reset_runtime_state()
    server, hits = _start_fixture_server({})
    cookies, identity_id = _create_owner_cookie_and_identity(database_connection, tmp_path)
    settings = _make_settings(tmp_path, references_setup=ReferencesSetupMode.OFF)

    try:
        with patch("florabase.main.get_settings", return_value=settings):
            app = create_app()
            app.dependency_overrides[get_settings] = lambda: settings
            app.dependency_overrides[get_database_session] = _override_database(database_connection)
            with TestClient(app, base_url=ORIGIN, cookies=cookies) as client:
                assert client.get("/api/v1/health").status_code == 200
                refs = client.get("/api/v1/system/references").json()
                assert refs["mode"] == "off"
                assert refs["wfo"]["status"] == "off"
                assert refs["wcvp_v16"]["status"] == "off"
                assert hits == []

        # Pre-populate valid sealed managed indexes while staying in off mode.
        _build_valid_wfo(managed_wfo_path(settings.references_state_dir))
        _build_valid_wcvp_v16(managed_wcvp_v16_path(settings.references_state_dir), with_seal=True)
        with patch("florabase.main.get_settings", return_value=settings):
            app = create_app()
            app.dependency_overrides[get_settings] = lambda: settings
            app.dependency_overrides[get_database_session] = _override_database(database_connection)
            with TestClient(app, base_url=ORIGIN, cookies=cookies) as client:
                refs = client.get("/api/v1/system/references").json()
                assert refs["wfo"]["status"] == "ready (setup off)"
                assert refs["wcvp_v16"]["status"] == "ready (setup off)"
                assert (
                    client.get(
                        "/api/v1/explore/taxonomy/candidates", params={"q": "Solanum"}
                    ).status_code
                    == 200
                )
                assert (
                    client.get(
                        f"/api/v1/botanical-identities/{identity_id}/native-range-enrichment/source"
                    ).json()["available"]
                    is True
                )
                assert hits == []
    finally:
        server.shutdown()
        server.server_close()
        reset_runtime_state()


def test_offline_failure_reports_failed_keeps_app_healthy_and_manual_ro_never_written(
    database_connection: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reset_runtime_state()
    server, _hits = _start_fixture_server({})
    port = server.server_address[1]
    bad_url = f"http://127.0.0.1:{port}/missing.zip"

    monkeypatch.setattr(wfo_snapshot, "ARCHIVE_URL", bad_url)
    monkeypatch.setattr(wfo_source, "ARCHIVE_URL", bad_url)
    test_release = wcvp_source.Release(
        "16",
        bad_url,
        wcvp_source.RELEASES["16"].checksum,
        wcvp_source.RELEASES["16"].citation,
        wcvp_source.RELEASES["16"].member_sizes,
    )
    monkeypatch.setattr(
        wcvp_source,
        "RELEASES",
        {"15": wcvp_source.RELEASES["15"], "16": test_release},
    )

    async def in_process_worker(key: str, state_dir: Path, max_seconds: float) -> ProvisionOutcome:
        return provision_index(
            key,  # type: ignore[arg-type]
            state_dir,
            max_seconds=max_seconds,
            required_bytes=1024,
        )

    # Set up a read-only manual WFO mount alongside an auto-managed WCVP v16 that will fail offline.
    ro_dir = tmp_path / "manual-ro"
    ro_wfo = ro_dir / "wfo-2026-06.sqlite"
    _build_valid_wfo(ro_wfo)
    ro_dir.chmod(0o555)

    cookies, _identity_id = _create_owner_cookie_and_identity(database_connection, tmp_path)
    settings = _make_settings(
        tmp_path,
        references_setup=ReferencesSetupMode.AUTO,
        wfo_snapshot_path=ro_wfo,
    )

    def make_coordinator(cfg: Settings) -> ReferenceSetupCoordinator:
        return ReferenceSetupCoordinator(
            cfg, retry_interval_seconds=3600.0, worker_runner=in_process_worker
        )

    try:
        with (
            patch("florabase.main.get_settings", return_value=settings),
            patch("florabase.main.ReferenceSetupCoordinator", side_effect=make_coordinator),
        ):
            app = create_app()
            app.dependency_overrides[get_settings] = lambda: settings
            app.dependency_overrides[get_database_session] = _override_database(database_connection)
            with TestClient(app, base_url=ORIGIN, cookies=cookies) as client:
                assert client.get("/api/v1/health").status_code == 200
                deadline = time.monotonic() + 10.0
                refs = client.get("/api/v1/system/references").json()
                while refs["wcvp_v16"]["state"] != "failed" and time.monotonic() < deadline:
                    time.sleep(0.05)
                    refs = client.get("/api/v1/system/references").json()

                assert refs["wfo"] == {
                    "state": "manual",
                    "status": "manual",
                    "reason": None,
                    "available": True,
                }
                assert refs["wcvp_v16"] == {
                    "state": "failed",
                    "status": "failed: network",
                    "reason": "network",
                    "available": False,
                }
                assert not managed_wcvp_v16_path(settings.references_state_dir).exists()
                assert client.get("/api/v1/health").status_code == 200
    finally:
        ro_dir.chmod(0o755)
        server.shutdown()
        server.server_close()
        reset_runtime_state()
