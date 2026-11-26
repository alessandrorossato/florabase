from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid7

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from starlette.requests import Request

from florabase.auth.demo_readonly import (
    DEMO_READONLY_CODE,
    DEMO_READONLY_MESSAGE,
    resolve_demo_actor,
)
from florabase.auth.dependencies import require_authenticated_actor, require_csrf
from florabase.auth.model import User
from florabase.core.config import CookieMode, Environment, Settings, get_settings
from florabase.db import release_schema
from florabase.db.session import get_database_session
from florabase.main import create_app


def _demo_settings(*, demo_readonly: bool = True, workers: int = 1) -> Settings:
    return Settings.model_validate(
        {
            "environment": Environment.PRODUCTION,
            "database_url": "postgresql+psycopg://test:test@db/test",
            "canonical_origin": "https://demo.florabase.eu",
            "cors_origins": [],
            "cookie_mode": CookieMode.SECURE,
            "demo_readonly": demo_readonly,
            "workers": workers,
        }
    )


def _owner_user() -> User:
    return User(
        id=uuid7(),
        login_name="demo",
        display_name="Florabase Demo",
        password_hash="encoded",
        enabled=True,
        owner=True,
    )


def test_demo_settings_defaults_and_worker_bounds() -> None:
    standard = _demo_settings(demo_readonly=False)
    assert standard.demo_readonly is False
    assert standard.workers == 1

    scaled = _demo_settings(demo_readonly=True, workers=4)
    assert scaled.demo_readonly is True
    assert scaled.workers == 4

    for invalid_workers in (0, 9):
        with pytest.raises(ValidationError):
            _demo_settings(workers=invalid_workers)


def test_uvicorn_workers_from_environment_and_serve_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert release_schema.uvicorn_workers_from_environment({}) == 1
    assert release_schema.uvicorn_workers_from_environment({"FLORABASE_WORKERS": "  "}) == 1
    assert release_schema.uvicorn_workers_from_environment({"FLORABASE_WORKERS": "4"}) == 4

    for bad in ("0", "9", "-2", "abc"):
        with pytest.raises(release_schema.SchemaError, match="FLORABASE_WORKERS"):
            release_schema.uvicorn_workers_from_environment({"FLORABASE_WORKERS": bad})

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
    monkeypatch.setattr("sys.argv", ["release_schema", "serve"])

    assert release_schema.main() == 0
    program, arguments = exec_server.call_args.args
    assert program == "uvicorn"
    assert "--workers" in arguments
    assert arguments[arguments.index("--workers") + 1] == "3"


def test_demo_readonly_system_info_and_session_auto_resolution() -> None:
    settings = _demo_settings(demo_readonly=True)
    owner = _owner_user()
    database = MagicMock()
    database.scalars.return_value.one_or_none.return_value = owner

    with patch("florabase.main.get_settings", return_value=settings):
        app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_database_session] = lambda: database

    with TestClient(app, base_url="https://demo.florabase.eu") as client:
        info = client.get("/api/v1/system/info")
        assert info.status_code == 200
        assert info.json()["capabilities"] == ["device-auth", "demo-readonly"]

        session = client.get("/api/v1/auth/session")
        assert session.status_code == 200
        assert session.headers["cache-control"] == "no-store"
        assert session.json() == {
            "user_id": str(owner.id),
            "login_name": "demo",
            "display_name": "Florabase Demo",
            "owner": True,
            "canonical_origin": "https://demo.florabase.eu",
            "demo_readonly": True,
        }

        preflight = client.options("/api/v1/system/info")
        assert preflight.status_code != 403

    database.add.assert_not_called()
    database.commit.assert_not_called()


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
def test_demo_readonly_middleware_rejects_all_mutations(method: str, path: str) -> None:
    settings = _demo_settings(demo_readonly=True)
    with patch("florabase.main.get_settings", return_value=settings):
        app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app, base_url="https://demo.florabase.eu") as client:
        response = client.request(method, path)

    assert response.status_code == 403
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "detail": {
            "code": DEMO_READONLY_CODE,
            "message": DEMO_READONLY_MESSAGE,
        }
    }


def test_demo_readonly_dependency_defense_in_depth() -> None:
    settings = _demo_settings(demo_readonly=True)
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
    standard = _demo_settings(demo_readonly=False)
    with pytest.raises(HTTPException) as std_exc:
        require_authenticated_actor(get_request, database, standard)
    assert std_exc.value.status_code == 401
    assert isinstance(SimpleNamespace(actor=actor).actor.user_id, type(owner.id))
