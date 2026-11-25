import logging
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from florabase import __version__
from florabase.auth.service import InvalidCredentialsError
from florabase.core.config import CookieMode, Environment, Settings, get_settings
from florabase.db.session import get_database_session
from florabase.main import create_app


def _production_settings() -> Settings:
    return Settings.model_validate(
        {
            "environment": Environment.PRODUCTION,
            "database_url": "postgresql+psycopg://test:test@db/test",
            "canonical_origin": "https://florabase.example",
            "cors_origins": [],
            "cookie_mode": CookieMode.SECURE,
        }
    )


def test_system_info_returns_compatibility_contract_without_secrets() -> None:
    app = create_app()
    with TestClient(app, base_url="https://florabase.example") as client:
        response = client.get("/api/v1/system/info")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    payload = response.json()
    assert payload == {
        "server_version": __version__,
        "api_version": 1,
        "min_client_version": "0.1.0-beta.8",
        "capabilities": ["device-auth"],
    }
    serialized = response.text.lower()
    for forbidden in ("postgresql", "database", "secret", "origin", "password"):
        assert forbidden not in serialized


@pytest.mark.parametrize("origin", ["https://localhost", "capacitor://localhost"])
def test_native_cors_works_in_production_without_credentials(origin: str) -> None:
    prod_settings = _production_settings()
    with patch("florabase.main.get_settings", return_value=prod_settings):
        app = create_app()
    app.dependency_overrides[get_settings] = lambda: prod_settings

    with TestClient(app, base_url="https://florabase.example") as client:
        preflight = client.options(
            "/api/v1/auth/device-sessions",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )
        assert preflight.status_code == 200
        assert preflight.headers["access-control-allow-origin"] == origin
        assert "access-control-allow-credentials" not in preflight.headers
        assert "POST" in preflight.headers["access-control-allow-methods"]
        assert "Authorization" in preflight.headers["access-control-allow-headers"]
        assert "Origin" in preflight.headers.get("vary", "")

        actual = client.get("/api/v1/system/info", headers={"Origin": origin})
        assert actual.status_code == 200
        assert actual.headers["access-control-allow-origin"] == origin
        assert "access-control-allow-credentials" not in actual.headers
        assert "Content-Disposition" in actual.headers["access-control-expose-headers"]
        assert "Retry-After" in actual.headers["access-control-expose-headers"]
        assert "Origin" in actual.headers.get("vary", "")


@pytest.mark.parametrize(
    "origin",
    [
        "https://evil.example",
        "http://localhost",
        "https://localhost:8443",
        "capacitor://evil.example",
    ],
)
def test_native_cors_rejects_non_allowlisted_origins_in_production(origin: str) -> None:
    prod_settings = _production_settings()
    with patch("florabase.main.get_settings", return_value=prod_settings):
        app = create_app()
    app.dependency_overrides[get_settings] = lambda: prod_settings

    with TestClient(app, base_url="https://florabase.example") as client:
        preflight = client.options(
            "/api/v1/auth/device-sessions",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )
        assert "access-control-allow-origin" not in preflight.headers

        actual = client.get("/api/v1/system/info", headers={"Origin": origin})
        assert actual.status_code == 200
        assert "access-control-allow-origin" not in actual.headers


def test_production_still_forbids_generic_cors_origins() -> None:
    with pytest.raises(
        ValidationError, match="Production authentication requires same-origin CORS configuration"
    ):
        Settings.model_validate(
            {
                "environment": Environment.PRODUCTION,
                "database_url": "postgresql+psycopg://test:test@db/test",
                "canonical_origin": "https://florabase.example",
                "cors_origins": ["https://other.example"],
                "cookie_mode": CookieMode.SECURE,
            }
        )


def test_device_session_settings_validation() -> None:
    with pytest.raises(ValidationError, match="device_session_absolute_seconds"):
        Settings.model_validate(
            {
                "environment": Environment.TEST,
                "database_url": "postgresql+psycopg://unused",
                "canonical_origin": "https://florabase.example",
                "cookie_mode": CookieMode.SECURE,
                "device_session_idle_seconds": 3600,
                "device_session_absolute_seconds": 3600,
            }
        )
    with pytest.raises(ValidationError):
        Settings.model_validate(
            {
                "environment": Environment.TEST,
                "database_url": "postgresql+psycopg://unused",
                "canonical_origin": "https://florabase.example",
                "cookie_mode": CookieMode.SECURE,
                "device_session_max_active": 0,
            }
        )


def test_device_sessions_endpoint_enforces_strict_json_and_never_logs_bearer(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app()
    app.dependency_overrides[get_database_session] = lambda: MagicMock()
    canary = "secret-bearer-canary-9f8e7d6c5b4a"

    with (
        caplog.at_level(logging.DEBUG),
        TestClient(app, base_url="https://florabase.example") as client,
    ):
        for content_type, body in (
            ("application/x-www-form-urlencoded", b"login_name=owner&password=x&device_label=p"),
            ("text/plain", b'{"login_name":"owner","password":"x","device_label":"p"}'),
            ("multipart/form-data; boundary=abc", b"--abc--\r\n"),
        ):
            response = client.post(
                "/api/v1/auth/device-sessions",
                content=body,
                headers={"Content-Type": content_type, "Origin": "https://localhost"},
            )
            assert response.status_code == 415
            assert response.headers["cache-control"] == "no-store"

        query_resp = client.post(
            "/api/v1/auth/device-sessions?token=leak",
            content=b"{}",
            headers={"Content-Type": "application/json"},
        )
        assert query_resp.status_code == 400

        oversized = client.post(
            "/api/v1/auth/device-sessions",
            content=b"[" * 32769,
            headers={"Content-Type": "application/json"},
        )
        assert oversized.status_code == 413

        with patch(
            "florabase.auth.dependencies.resolve_session",
            side_effect=InvalidCredentialsError,
        ):
            unauth = client.get(
                "/api/v1/auth/session",
                headers={"Authorization": f"Bearer {canary}", "Origin": "https://localhost"},
            )
        assert unauth.status_code == 401
        assert unauth.headers["www-authenticate"] == "Bearer"
        assert canary not in unauth.text

    for record in caplog.records:
        assert canary not in record.getMessage()


def test_device_session_service_and_dependency_unit_paths() -> None:
    from datetime import UTC, datetime, timedelta
    from uuid import uuid7

    from fastapi import HTTPException, Response
    from starlette.requests import Request

    from florabase.auth.api import (
        DeviceSessionCreateRequest,
        create_device_session,
        list_device_sessions,
        revoke_all_owner_device_sessions,
        revoke_current_device_session,
        revoke_device_session,
    )
    from florabase.auth.dependencies import (
        AuthenticatedActor,
        require_authenticated_actor,
        require_bearer_actor,
        require_cookie_actor,
        require_cookie_csrf,
        require_csrf,
    )
    from florabase.auth.model import AuthSession, User
    from florabase.auth.service import (
        InvalidDeviceLabelError,
        LoginThrottledError,
        NewDeviceSession,
        SessionCsrfError,
        authenticate_device,
        list_active_device_sessions,
        normalize_device_label,
        revoke_all_device_sessions,
        revoke_device_session_by_id,
        rotate_csrf,
        verify_csrf,
    )

    assert normalize_device_label("  Pixel 9  ") == "Pixel 9"
    for bad in ("", "   ", "a" * 121, "bad\x00label"):
        with pytest.raises(InvalidDeviceLabelError):
            normalize_device_label(bad)

    now = datetime.now(UTC)
    app_settings = Settings.model_validate(
        {
            "environment": Environment.TEST,
            "database_url": "postgresql+psycopg://unused",
            "canonical_origin": "https://florabase.example",
            "cookie_mode": CookieMode.SECURE,
            "device_session_max_active": 2,
        }
    )
    owner = User(
        id=uuid7(),
        login_name="owner",
        display_name="Owner",
        password_hash="encoded",
        enabled=True,
        owner=True,
    )
    bearer_session = AuthSession(
        id=uuid7(),
        user_id=owner.id,
        transport="bearer",
        device_label="Pixel 9",
        token_digest=b"b" * 32,
        csrf_digest=None,
        created_at=now,
        last_seen_at=now,
        idle_expires_at=now + timedelta(days=30),
        absolute_expires_at=now + timedelta(days=180),
        user=owner,
    )
    assert verify_csrf(bearer_session, "anything") is False
    with pytest.raises(SessionCsrfError):
        rotate_csrf(bearer_session, app_settings)

    # Service list/revoke helpers
    db = MagicMock()
    db.scalars.return_value.all.return_value = [bearer_session]
    assert list_active_device_sessions(db, owner.id) == [bearer_session]

    db.scalars.return_value.one_or_none.return_value = bearer_session
    assert revoke_device_session_by_id(db, owner.id, bearer_session.id) is True
    assert bearer_session.revoked_at is not None

    db.scalars.return_value.one_or_none.return_value = None
    assert revoke_device_session_by_id(db, owner.id, uuid7()) is False

    bearer_session.revoked_at = None
    db.scalars.return_value.all.return_value = [bearer_session]
    assert revoke_all_device_sessions(db, owner.id) == 1
    assert bearer_session.revoked_at is not None

    # authenticate_device success + eviction + invalid credentials
    bearer_session.revoked_at = None
    older_session = AuthSession(
        id=uuid7(),
        user_id=owner.id,
        transport="bearer",
        device_label="Older",
        token_digest=b"c" * 32,
        csrf_digest=None,
        created_at=now - timedelta(days=2),
        last_seen_at=now - timedelta(days=2),
        idle_expires_at=now + timedelta(days=28),
        absolute_expires_at=now + timedelta(days=178),
        user=owner,
    )
    db_auth = MagicMock()
    db_auth.scalars.return_value.one_or_none.return_value = owner
    db_auth.scalars.return_value.all.return_value = [older_session, bearer_session]
    with patch(
        "florabase.auth.service._verify_login_credentials",
        return_value=(owner, "owner", now),
    ):
        issued = authenticate_device(db_auth, "owner", "pw", "New Phone", app_settings)
    assert issued.session.transport == "bearer"
    assert issued.session.device_label == "New Phone"
    assert older_session.revoked_at == now

    # Deterministic lock-order check on _issue_device_session:
    # 1. users row FOR NO KEY UPDATE via _locked_user
    # 2. auth_sessions rows ORDER BY AuthSession.id FOR UPDATE
    from sqlalchemy import Select
    from sqlalchemy.dialects import postgresql

    from florabase.auth.service import _issue_device_session

    executed_sql: list[str] = []

    def capture_scalars(stmt: Select[tuple[object]]) -> MagicMock:
        compiled = str(
            stmt.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": False},
            )
        )
        executed_sql.append(compiled)
        result = MagicMock()
        if "FROM users" in compiled:
            result.one_or_none.return_value = owner
        else:
            result.all.return_value = []
        return result

    db_lock_order = MagicMock()
    db_lock_order.scalars.side_effect = capture_scalars
    _issue_device_session(db_lock_order, owner, "Lock Order Phone", app_settings, now)
    assert len(executed_sql) == 2
    assert "FROM users" in executed_sql[0]
    assert "FOR NO KEY UPDATE OF users" in executed_sql[0]
    assert "FROM auth_sessions" in executed_sql[1]
    assert "ORDER BY auth_sessions.id" in executed_sql[1]
    assert "FOR UPDATE OF auth_sessions" in executed_sql[1]

    # Disabled/missing user on _locked_user raises InvalidCredentialsError
    db_missing_user = MagicMock()
    db_missing_user.scalars.return_value.one_or_none.return_value = None
    with pytest.raises(InvalidCredentialsError):
        _issue_device_session(db_missing_user, owner, "Disabled Phone", app_settings, now)

    # Dependency transport isolation
    bearer_actor = AuthenticatedActor(
        owner.id, "owner", "Owner", True, bearer_session, transport="bearer"
    )
    cookie_actor = AuthenticatedActor(
        owner.id, "owner", "Owner", True, bearer_session, transport="cookie"
    )
    assert require_bearer_actor(bearer_actor) is bearer_actor
    assert require_cookie_actor(cookie_actor) is cookie_actor
    with pytest.raises(HTTPException) as exc_cookie:
        require_cookie_actor(bearer_actor)
    assert exc_cookie.value.status_code == 403
    with pytest.raises(HTTPException) as exc_bearer:
        require_bearer_actor(cookie_actor)
    assert exc_bearer.value.status_code == 403
    req_bearer = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/locations",
            "headers": [(b"authorization", b"Bearer valid-token")],
        }
    )
    assert require_csrf(req_bearer, bearer_actor, app_settings, None) is bearer_actor
    with pytest.raises(HTTPException) as exc_cookie_csrf:
        require_cookie_csrf(bearer_actor)
    assert exc_cookie_csrf.value.status_code == 403

    with patch(
        "florabase.auth.dependencies.resolve_session",
        return_value=(owner, bearer_session),
    ):
        resolved_actor = require_authenticated_actor(req_bearer, db, app_settings)
    assert resolved_actor.transport == "bearer"

    req_ambiguous = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/auth/session",
            "headers": [
                (b"authorization", b"Bearer tok"),
                (b"cookie", b"__Host-florabase-session=tok"),
            ],
        }
    )
    with pytest.raises(HTTPException) as exc_ambig:
        require_authenticated_actor(req_ambiguous, db, app_settings)
    assert exc_ambig.value.status_code == 401

    req_bad_scheme = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/auth/session",
            "headers": [(b"authorization", b"Basic abc")],
        }
    )
    with pytest.raises(HTTPException) as exc_scheme:
        require_authenticated_actor(req_bad_scheme, db, app_settings)
    assert exc_scheme.value.status_code == 401

    # API handler unit paths
    req_plain = Request({"type": "http", "method": "POST", "path": "/", "headers": []})
    req_with_cookie = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": [(b"cookie", b"__Host-florabase-session=abc")],
        }
    )
    payload = DeviceSessionCreateRequest(login_name="owner", password="pw", device_label="Pixel 9")
    cookie_reject = create_device_session(payload, req_with_cookie, Response(), db, app_settings)
    assert getattr(cookie_reject, "status_code", None) == 401

    with patch(
        "florabase.auth.api.authenticate_device",
        return_value=NewDeviceSession(owner, bearer_session, "tok-value"),
    ):
        created_resp = create_device_session(payload, req_plain, Response(), db, app_settings)
    assert getattr(created_resp, "token", None) == "tok-value"

    for err, expected_status in (
        (InvalidDeviceLabelError(), 422),
        (LoginThrottledError(5), 429),
        (InvalidCredentialsError(), 401),
    ):
        with patch("florabase.auth.api.authenticate_device", side_effect=err):
            err_resp = create_device_session(payload, req_plain, Response(), db, app_settings)
        assert getattr(err_resp, "status_code", None) == expected_status

    with patch("florabase.auth.api.list_active_device_sessions", return_value=[bearer_session]):
        listed = list_device_sessions(Response(), bearer_actor, db)
    assert len(listed.items) == 1
    assert listed.items[0].current is True

    with patch("florabase.auth.api.revoke_device_session_by_id", return_value=True):
        assert revoke_current_device_session(bearer_actor, db).status_code == 204
    with (
        patch("florabase.auth.api.revoke_device_session_by_id", return_value=False),
        pytest.raises(HTTPException) as exc_401,
    ):
        revoke_current_device_session(bearer_actor, db)
    assert exc_401.value.status_code == 401
    with patch("florabase.auth.api.revoke_device_session_by_id", return_value=True):
        assert revoke_device_session(bearer_session.id, bearer_actor, db).status_code == 204
    with (
        patch("florabase.auth.api.revoke_device_session_by_id", return_value=False),
        pytest.raises(HTTPException) as exc_404,
    ):
        revoke_device_session(uuid7(), bearer_actor, db)
    assert exc_404.value.status_code == 404
    with patch("florabase.auth.api.revoke_all_device_sessions", return_value=2):
        assert revoke_all_owner_device_sessions(Response(), bearer_actor, db).revoked_count == 2

    # Non-owner authenticated actors can also list, revoke current, revoke one, and revoke all
    member_id = uuid7()
    member_session = AuthSession(
        id=uuid7(),
        user_id=member_id,
        transport="bearer",
        device_label="Member Phone",
        token_digest=b"m" * 32,
        csrf_digest=None,
        created_at=now,
        last_seen_at=now,
        idle_expires_at=now + timedelta(days=30),
        absolute_expires_at=now + timedelta(days=180),
    )
    member_actor = AuthenticatedActor(
        member_id, "member", "Member", False, member_session, transport="bearer"
    )
    with patch("florabase.auth.api.list_active_device_sessions", return_value=[member_session]):
        member_listed = list_device_sessions(Response(), member_actor, db)
    assert len(member_listed.items) == 1
    assert member_listed.items[0].id == member_session.id
    with patch("florabase.auth.api.revoke_device_session_by_id", return_value=True):
        assert revoke_current_device_session(member_actor, db).status_code == 204
        assert revoke_device_session(member_session.id, member_actor, db).status_code == 204
    with patch("florabase.auth.api.revoke_all_device_sessions", return_value=1):
        assert revoke_all_owner_device_sessions(Response(), member_actor, db).revoked_count == 1
