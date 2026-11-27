from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid7

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import inspect as sa_inspect
from starlette.requests import Request

from florabase.auth.demo_readonly import (
    DEMO_EXTERNAL_LOOKUP_DISABLED_CODE,
    DEMO_MARKER_FILENAME,
    DEMO_MARKER_TOKEN,
    DEMO_READONLY_CODE,
    DEMO_READONLY_MESSAGE,
    DEMO_STARTUP_WARNING,
    DEMO_VISITOR_DISPLAY_NAME,
    EPHEMERAL_DEMO_SESSION_ID,
    DemoMarkerError,
    demo_thumbnail_headers,
    resolve_demo_actor,
    verify_demo_marker,
)
from florabase.auth.dependencies import require_authenticated_actor, require_csrf
from florabase.auth.model import User
from florabase.core.config import CookieMode, Environment, Settings, get_settings
from florabase.db import release_schema
from florabase.db.session import get_database_session
from florabase.external_botany.api import get_provider
from florabase.external_botany.model import ExternalProviderCache, ExternalTaxonLink
from florabase.main import create_app


def _write_demo_marker(root: Path, content: str = DEMO_MARKER_TOKEN) -> Path:
    marker = root / DEMO_MARKER_FILENAME
    marker.write_text(f"{content}\n", encoding="ascii")
    return marker


def _demo_settings(tmp_path: Path, *, demo_readonly: bool = True) -> Settings:
    return Settings.model_validate(
        {
            "environment": Environment.PRODUCTION,
            "database_url": "postgresql+psycopg://test:test@db/test",
            "canonical_origin": "https://demo.example.org",
            "cors_origins": [],
            "cookie_mode": CookieMode.SECURE,
            "attachment_storage_root": str(tmp_path),
            "references_setup": "off",
            "demo_readonly": demo_readonly,
        }
    )


def _owner_user() -> User:
    return User(
        id=uuid7(),
        login_name="golden-owner",
        display_name="Golden Owner",
        password_hash="encoded",
        enabled=True,
        owner=True,
    )


def test_demo_settings_default_off_and_marker_guard(tmp_path: Path) -> None:
    standard = _demo_settings(tmp_path, demo_readonly=False)
    assert standard.demo_readonly is False
    assert not hasattr(standard, "workers")

    # Missing marker refused.
    with pytest.raises(DemoMarkerError, match="missing demo marker"):
        verify_demo_marker(tmp_path)

    # Wrong token refused.
    _write_demo_marker(tmp_path, "wrong-token")
    with pytest.raises(DemoMarkerError, match="invalid demo marker"):
        verify_demo_marker(tmp_path)

    # Symlink marker refused.
    target = tmp_path / "real-marker"
    target.write_text(f"{DEMO_MARKER_TOKEN}\n", encoding="ascii")
    (tmp_path / DEMO_MARKER_FILENAME).unlink()
    (tmp_path / DEMO_MARKER_FILENAME).symlink_to(target)
    with pytest.raises(DemoMarkerError, match="missing demo marker"):
        verify_demo_marker(tmp_path)

    # Valid regular marker file accepted.
    (tmp_path / DEMO_MARKER_FILENAME).unlink()
    marker = _write_demo_marker(tmp_path)
    assert verify_demo_marker(tmp_path) == marker


def test_demo_lifespan_refuses_without_marker_and_warns_when_accepted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    settings = _demo_settings(tmp_path, demo_readonly=True)
    with patch("florabase.main.get_settings", return_value=settings):
        app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings

    with (
        pytest.raises(DemoMarkerError, match="missing demo marker"),
        TestClient(app, base_url="https://demo.example.org"),
    ):
        pass

    _write_demo_marker(tmp_path)
    with TestClient(app, base_url="https://demo.example.org") as client:
        assert client.get("/api/v1/system/info").status_code == 200
    captured = capsys.readouterr()
    assert DEMO_STARTUP_WARNING in (captured.err + captured.out)


def test_uvicorn_workers_and_demo_marker_in_release_schema_serve(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert release_schema.uvicorn_workers_from_environment({}) == 1
    assert release_schema.uvicorn_workers_from_environment({"FLORABASE_WORKERS": "  "}) == 1
    assert release_schema.uvicorn_workers_from_environment({"FLORABASE_WORKERS": "4"}) == 4

    for bad in ("0", "9", "-2", "abc"):
        with pytest.raises(release_schema.SchemaError, match="FLORABASE_WORKERS"):
            release_schema.uvicorn_workers_from_environment({"FLORABASE_WORKERS": bad})

    assert release_schema.demo_readonly_from_environment({}) is False
    assert (
        release_schema.demo_readonly_from_environment({"FLORABASE_DEMO_READONLY": "false"}) is False
    )
    assert (
        release_schema.demo_readonly_from_environment({"FLORABASE_DEMO_READONLY": "true"}) is True
    )
    with pytest.raises(release_schema.SchemaError, match="FLORABASE_DEMO_READONLY"):
        release_schema.demo_readonly_from_environment({"FLORABASE_DEMO_READONLY": "maybe"})

    scripts = MagicMock()
    scripts.get_heads.return_value = ["head_rev"]
    engine = MagicMock()
    connection = MagicMock()
    engine.connect.return_value.__enter__.return_value = connection
    context = MagicMock()
    context.get_current_heads.return_value = ("head_rev",)
    exec_server = MagicMock()

    monkeypatch.setattr(
        "florabase.db.release_schema.ScriptDirectory.from_config", lambda _: scripts
    )
    monkeypatch.setattr(release_schema, "get_readiness_engine", lambda: engine)
    monkeypatch.setattr("florabase.db.release_schema.MigrationContext.configure", lambda _: context)
    monkeypatch.setattr("florabase.db.release_schema.os.execvp", exec_server)
    monkeypatch.setenv("FLORABASE_WORKERS", "3")
    monkeypatch.setenv("FLORABASE_DEMO_READONLY", "true")
    monkeypatch.setenv("FLORABASE_ATTACHMENT_STORAGE_ROOT", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["release_schema", "serve"])

    # Without demo marker, serve refuses before execvp.
    assert release_schema.main() == 1
    assert "missing demo marker" in capsys.readouterr().err
    exec_server.assert_not_called()

    # With demo marker, serve logs loud warning and launches with --workers 3.
    _write_demo_marker(tmp_path)
    assert release_schema.main() == 0
    assert DEMO_STARTUP_WARNING in capsys.readouterr().err
    program, arguments = exec_server.call_args.args
    assert program == "uvicorn"
    assert "--workers" in arguments
    assert arguments[arguments.index("--workers") + 1] == "3"


def test_demo_readonly_neutral_session_empty_devices_and_thumbnail_headers(tmp_path: Path) -> None:
    _write_demo_marker(tmp_path)
    settings = _demo_settings(tmp_path, demo_readonly=True)
    owner = _owner_user()
    database = MagicMock()
    database.scalars.return_value.one_or_none.return_value = owner

    with patch("florabase.main.get_settings", return_value=settings):
        app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_database_session] = lambda: database

    with TestClient(app, base_url="https://demo.example.org") as client:
        info = client.get("/api/v1/system/info")
        assert info.status_code == 200
        assert info.json()["capabilities"] == ["device-auth", "demo-readonly"]

        session = client.get("/api/v1/auth/session")
        assert session.status_code == 200
        assert session.headers["cache-control"] == "no-store"
        assert session.json() == {
            "user_id": str(EPHEMERAL_DEMO_SESSION_ID),
            "login_name": "",
            "display_name": DEMO_VISITOR_DISPLAY_NAME,
            "owner": False,
            "canonical_origin": "https://demo.example.org",
            "demo_readonly": True,
        }
        assert "golden-owner" not in session.text

        devices = client.get("/api/v1/auth/device-sessions")
        assert devices.status_code == 200
        assert devices.headers["cache-control"] == "no-store"
        assert devices.json() == {"items": []}

        preflight = client.options("/api/v1/system/info")
        assert preflight.status_code != 403

    database.add.assert_not_called()
    database.commit.assert_not_called()

    demo_headers = demo_thumbnail_headers('"etag-1"', demo_readonly=True)
    assert demo_headers["Cache-Control"] == "public, max-age=86400"
    assert "Vary" not in demo_headers

    private_headers = demo_thumbnail_headers('"etag-1"', demo_readonly=False)
    assert private_headers["Cache-Control"] == "private, max-age=86400, must-revalidate"
    assert private_headers["Vary"] == "Cookie"


def test_demo_readonly_external_botany_gets_are_cache_only_and_never_call_provider(
    tmp_path: Path,
) -> None:
    _write_demo_marker(tmp_path)
    settings = _demo_settings(tmp_path, demo_readonly=True)
    owner = _owner_user()
    identity_id = uuid7()
    link = ExternalTaxonLink(
        id=uuid7(),
        botanical_identity_id=identity_id,
        provider="gbif",
        external_id="2777724",
        scientific_name="Aloe dichotoma",
        canonical_name="Aloe dichotoma",
        rank="SPECIES",
        taxonomic_status="ACCEPTED",
    )
    database = MagicMock()
    database.scalars.return_value.one_or_none.return_value = owner
    database.get.return_value = None

    provider = MagicMock()
    provider.provider_id = "gbif"
    provider.search_payload = AsyncMock()
    provider.occurrence_summary = AsyncMock()
    provider.occurrence_tile = AsyncMock()

    with patch("florabase.main.get_settings", return_value=settings):
        app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_database_session] = lambda: database
    app.dependency_overrides[get_provider] = lambda: provider

    with (
        patch("florabase.external_botany.api.get_botanical_identity", return_value=object()),
        patch("florabase.external_botany.api.get_link", return_value=link),
        TestClient(app, base_url="https://demo.example.org") as client,
    ):
        # 1. External search cache miss -> 403, no provider call, no DB write.
        search_miss = client.get(
            f"/api/v1/botanical-identities/{identity_id}/external-taxa/search?query=Aloe"
        )
        assert search_miss.status_code == 403
        assert search_miss.json()["detail"]["code"] == DEMO_EXTERNAL_LOOKUP_DISABLED_CODE
        provider.search_payload.assert_not_awaited()
        database.execute.assert_not_called()

        # 2. External search cache hit -> 200 from cache, no provider call.
        cached = ExternalProviderCache(
            provider="gbif",
            resource_key="match-v2-colxr:cached",
            fetched_at=datetime.now(UTC),
            payload={"results": []},
        )
        database.get.return_value = cached
        provider.normalize_search.return_value = []
        search_hit = client.get(
            f"/api/v1/botanical-identities/{identity_id}/external-taxa/search?query=Aloe"
        )
        assert search_hit.status_code == 200
        assert search_hit.json()["from_cache"] is True
        provider.search_payload.assert_not_awaited()

        # 3. Occurrence summary cache miss -> 403, no provider call.
        database.get.return_value = None
        summary_miss = client.get(
            f"/api/v1/botanical-identities/{identity_id}/occurrence-map/summary"
        )
        assert summary_miss.status_code == 403
        assert summary_miss.json()["detail"]["code"] == DEMO_EXTERNAL_LOOKUP_DISABLED_CODE
        provider.occurrence_summary.assert_not_awaited()

        # 4. Occurrence tile without generation -> 404 local_only, no provider call or disk write.
        tile_no_gen = client.get(
            f"/api/v1/botanical-identities/{identity_id}/occurrence-map/tiles/2/1/1.png"
        )
        assert tile_no_gen.status_code == 404
        assert tile_no_gen.json()["detail"]["code"] == "occurrence_tile_not_cached"
        provider.occurrence_tile.assert_not_awaited()
        assert sorted(path for path in tmp_path.rglob("*") if path.is_file()) == [
            tmp_path / DEMO_MARKER_FILENAME
        ]


def test_demo_readonly_returns_503_when_no_owner_exists() -> None:
    database = MagicMock()
    database.scalars.return_value.one_or_none.return_value = None
    with pytest.raises(HTTPException) as exc:
        resolve_demo_actor(database)
    assert exc.value.status_code == 503


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/v1/auth/login"),
        ("POST", "/api/v1/auth/password"),
        ("POST", "/api/v1/auth/csrf"),
        ("POST", "/api/v1/auth/logout"),
        ("POST", "/api/v1/auth/device-sessions"),
        ("POST", "/api/v1/plants"),
        ("PUT", "/api/v1/botanical-identities/00000000-0000-0000-0000-000000000001"),
        ("PATCH", "/api/v1/media/00000000-0000-0000-0000-000000000001"),
        ("DELETE", "/api/v1/locations/00000000-0000-0000-0000-000000000001"),
    ],
)
def test_demo_readonly_middleware_rejects_all_mutations(
    tmp_path: Path, method: str, path: str
) -> None:
    _write_demo_marker(tmp_path)
    settings = _demo_settings(tmp_path, demo_readonly=True)
    with patch("florabase.main.get_settings", return_value=settings):
        app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app, base_url="https://demo.example.org") as client:
        response = client.request(method, path)

    assert response.status_code == 403
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "detail": {
            "code": DEMO_READONLY_CODE,
            "message": DEMO_READONLY_MESSAGE,
        }
    }


def test_demo_readonly_dependency_defense_in_depth_and_transient_session(tmp_path: Path) -> None:
    settings = _demo_settings(tmp_path, demo_readonly=True)
    owner = _owner_user()
    database = MagicMock()
    database.scalars.return_value.one_or_none.return_value = owner

    post_request = Request(
        {"type": "http", "method": "POST", "path": "/api/v1/plants", "headers": []}
    )
    with pytest.raises(HTTPException) as auth_exc:
        require_authenticated_actor(post_request, database, settings)
    assert auth_exc.value.status_code == 403
    auth_detail: object = auth_exc.value.detail
    assert auth_detail == {
        "code": DEMO_READONLY_CODE,
        "message": DEMO_READONLY_MESSAGE,
    }

    actor = resolve_demo_actor(database)
    assert sa_inspect(actor.session).transient is True

    get_request = Request(
        {"type": "http", "method": "GET", "path": "/api/v1/plants", "headers": []}
    )
    with pytest.raises(HTTPException) as csrf_exc:
        require_csrf(get_request, actor, settings, "fake-csrf")
    assert csrf_exc.value.status_code == 403
    csrf_detail: object = csrf_exc.value.detail
    assert csrf_detail == {
        "code": DEMO_READONLY_CODE,
        "message": DEMO_READONLY_MESSAGE,
    }

    # Verify default production mode stays untouched (401 without cookie).
    standard = _demo_settings(tmp_path, demo_readonly=False)
    with pytest.raises(HTTPException) as std_exc:
        require_authenticated_actor(get_request, database, standard)
    assert std_exc.value.status_code == 401
