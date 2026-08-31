from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid7

import pytest
from fastapi import HTTPException, Response
from starlette.requests import Request

from florabase.auth.api import LoginRequest, get_session, login, logout, recover_csrf
from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
    require_origin,
    require_owner,
    session_cookie_name,
)
from florabase.auth.model import AuthSession, User
from florabase.auth.security import token_digest
from florabase.auth.service import (
    InvalidCredentialsError,
    LoginThrottledError,
    NewSession,
)
from florabase.core.config import CookieMode, Environment, Settings


def settings(cookie_mode: CookieMode = CookieMode.SECURE) -> Settings:
    origin = (
        "http://localhost:5173"
        if cookie_mode is CookieMode.LOOPBACK_DEVELOPMENT
        else "https://florabase.example"
    )
    environment = (
        Environment.DEVELOPMENT
        if cookie_mode is CookieMode.LOOPBACK_DEVELOPMENT
        else Environment.TEST
    )
    return Settings.model_validate(
        {
            "environment": environment,
            "database_url": "postgresql+psycopg://unused",
            "canonical_origin": origin,
            "cookie_mode": cookie_mode,
        }
    )


def request(origin: str | None = "https://florabase.example", cookie: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if origin is not None:
        headers.append((b"origin", origin.encode("ascii")))
    if cookie is not None:
        headers.append((b"cookie", cookie.encode("ascii")))
    return Request({"type": "http", "method": "POST", "path": "/", "headers": headers})


def actor(owner: bool = True) -> AuthenticatedActor:
    now = datetime.now(UTC)
    auth_session = AuthSession(
        id=uuid7(),
        user_id=uuid7(),
        token_digest=b"a" * 32,
        csrf_digest=token_digest("csrf-token"),
        created_at=now,
        last_seen_at=now,
        idle_expires_at=now + timedelta(days=1),
        absolute_expires_at=now + timedelta(days=30),
    )
    return AuthenticatedActor(uuid7(), "owner", "Owner", owner, auth_session)


def test_cookie_name_and_origin_policy() -> None:
    assert session_cookie_name(settings()) == "__Host-florabase-session"
    assert session_cookie_name(settings(CookieMode.LOOPBACK_DEVELOPMENT)) == "florabase-session-dev"
    require_origin(request(), settings())
    for invalid_origin in (None, "https://evil.example"):
        with pytest.raises(HTTPException, match="403"):
            require_origin(request(invalid_origin), settings())


def test_authentication_and_csrf_dependencies_have_generic_failures() -> None:
    database = MagicMock()
    app_settings = settings()
    current_actor = actor()
    user = User(
        id=current_actor.user_id,
        login_name=current_actor.login_name,
        display_name=current_actor.display_name,
        password_hash="encoded",
        enabled=True,
        owner=True,
    )

    with patch(
        "florabase.auth.dependencies.resolve_session",
        return_value=(user, current_actor.session),
    ):
        authenticated = require_authenticated_actor(
            request(cookie="__Host-florabase-session=raw-token"), database, app_settings
        )
    assert authenticated.user_id == user.id

    for incoming in (request(), request(cookie="__Host-florabase-session=bad")):
        with (
            patch(
                "florabase.auth.dependencies.resolve_session",
                side_effect=InvalidCredentialsError,
            ),
            pytest.raises(HTTPException) as caught,
        ):
            require_authenticated_actor(incoming, database, app_settings)
        assert caught.value.status_code == 401
        assert caught.value.detail == "Authentication required"

    assert require_csrf(request(), current_actor, app_settings, "csrf-token") is current_actor
    for token in (None, "wrong"):
        with pytest.raises(HTTPException) as caught:
            require_csrf(request(), current_actor, app_settings, token)
        assert caught.value.status_code == 403


def test_login_response_cookie_and_failure_mapping() -> None:
    database = MagicMock()
    app_settings = settings()
    current_actor = actor()
    user = User(
        id=current_actor.user_id,
        login_name="owner",
        display_name="Owner",
        password_hash="encoded",
        enabled=True,
        owner=True,
    )
    authenticated = NewSession(user, current_actor.session, "session-token", "csrf-token")
    response = Response()

    with patch("florabase.auth.api.authenticate", return_value=authenticated):
        body = login(
            LoginRequest(login_name="owner", password="a valid password"),
            request(),
            response,
            database,
            app_settings,
        )
    assert body.csrf_token == "csrf-token"
    assert "__Host-florabase-session=session-token" in response.headers["set-cookie"]
    assert "Secure" in response.headers["set-cookie"]
    assert response.headers["cache-control"] == "no-store"

    failures: tuple[tuple[Exception, int], ...] = (
        (InvalidCredentialsError(), 401),
        (LoginThrottledError(7), 429),
    )
    for failure, status_code in failures:
        with (
            patch("florabase.auth.api.authenticate", side_effect=failure),
            pytest.raises(HTTPException) as caught,
        ):
            login(
                LoginRequest(login_name="owner", password="a valid password"),
                request(),
                Response(),
                database,
                app_settings,
            )
        assert caught.value.status_code == status_code
    assert database.commit.call_count == 2


def test_session_response_logout_and_owner_boundary() -> None:
    database = MagicMock()
    current_actor = actor()
    response = Response()
    session_body = get_session(response, current_actor)
    assert session_body.login_name == "owner"
    assert response.headers["cache-control"] == "no-store"

    csrf_response = Response()
    previous_digest = current_actor.session.csrf_digest
    csrf_body = recover_csrf(request(), csrf_response, current_actor, settings())
    assert current_actor.session.csrf_digest == token_digest(csrf_body.csrf_token)
    assert current_actor.session.csrf_digest != previous_digest
    assert csrf_response.headers["cache-control"] == "no-store"

    logout_response = Response()
    with patch("florabase.auth.api.revoke_session") as revoke:
        logout_body = logout(logout_response, current_actor, database, settings())
    assert logout_body.status == "ok"
    revoke.assert_called_once_with(database, current_actor.session)
    assert "Max-Age=0" in logout_response.headers["set-cookie"]

    with pytest.raises(HTTPException) as caught:
        require_owner(actor(owner=False))
    assert caught.value.status_code == 403
