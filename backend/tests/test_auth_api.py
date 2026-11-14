import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid7

import pytest
from fastapi import HTTPException, Response
from starlette.requests import Request
from starlette.responses import JSONResponse

from florabase.auth.api import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    change_owner_password,
    get_session,
    login,
    logout,
    recover_csrf,
)
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
    InvalidNewPasswordError,
    LoginThrottledError,
    NewSession,
    PasswordUnchangedError,
    SessionCsrfError,
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
    assert isinstance(body, LoginResponse)
    assert body.csrf_token == "csrf-token"
    assert "__Host-florabase-session=session-token" in response.headers["set-cookie"]
    assert "Secure" in response.headers["set-cookie"]
    assert response.headers["cache-control"] == "no-store"

    failures: tuple[tuple[Exception, int], ...] = (
        (InvalidCredentialsError(), 401),
        (LoginThrottledError(7), 429),
    )
    for failure, status_code in failures:
        with patch("florabase.auth.api.authenticate", side_effect=failure):
            failed = login(
                LoginRequest(login_name="owner", password="a valid password"),
                request(),
                Response(),
                database,
                app_settings,
            )
        assert isinstance(failed, JSONResponse)
        assert failed.status_code == status_code
    database.commit.assert_not_called()


def test_session_response_logout_and_owner_boundary() -> None:
    database = MagicMock()
    current_actor = actor()
    response = Response()
    session_body = get_session(response, current_actor, settings())
    assert session_body.login_name == "owner"
    assert session_body.canonical_origin == "https://florabase.example"
    assert response.headers["cache-control"] == "no-store"

    csrf_response = Response()
    previous_digest = current_actor.session.csrf_digest
    with patch("florabase.auth.api.lock_presenting_session", return_value=current_actor.session):
        csrf_body = recover_csrf(request(), csrf_response, current_actor, settings(), database)
    assert current_actor.session.csrf_digest == token_digest(csrf_body.csrf_token)
    assert current_actor.session.csrf_digest != previous_digest
    assert csrf_response.headers["cache-control"] == "no-store"

    logout_response = Response()
    with (
        patch("florabase.auth.api.lock_presenting_session", return_value=current_actor.session),
        patch("florabase.auth.api.revoke_session") as revoke,
    ):
        logout_body = logout(logout_response, current_actor, database, settings(), "csrf-token")
    assert logout_body.status == "ok"
    revoke.assert_called_once_with(database, current_actor.session)
    assert "Max-Age=0" in logout_response.headers["set-cookie"]

    with pytest.raises(HTTPException) as caught:
        require_owner(actor(owner=False))
    assert caught.value.status_code == 403


@pytest.mark.parametrize("outcome", [200, 403, 429])
@pytest.mark.parametrize("fail_commit", [False, True])
def test_mounted_password_responses_wait_for_commit(
    outcome: int, fail_commit: bool, caplog: pytest.LogCaptureFixture
) -> None:
    from florabase.auth.dependencies import require_csrf
    from florabase.auth.service import InvalidCurrentPasswordError
    from florabase.main import create_app

    database = MagicMock()
    events: list[str] = []
    database.commit.side_effect = (
        RuntimeError("private database URL and statement parameter")
        if fail_commit
        else lambda: events.append("commit")
    )
    database.rollback.side_effect = lambda: events.append("rollback")
    session_class = MagicMock()
    session_class.return_value.__enter__.return_value = database
    app = create_app()
    current_actor = actor()
    app.dependency_overrides[require_csrf] = lambda: current_actor
    user = User(id=current_actor.user_id)
    result = NewSession(user, current_actor.session, "private-session", "private-csrf")
    service_mock = MagicMock(return_value=result)
    if outcome == 403:
        service_mock.side_effect = InvalidCurrentPasswordError
    elif outcome == 429:
        service_mock.side_effect = LoginThrottledError(3)

    body = b'{"current_password":"synthetic-current","new_password":"synthetic-new"}'
    messages = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict[str, object]) -> None:
        if message["type"] == "http.response.start":
            events.append(f"response-{message['status']}")
        messages.append(message)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/password",
        "root_path": "",
        "scheme": "https",
        "query_string": b"",
        "headers": [(b"content-type", b"application/json"), (b"x-csrf-token", b"original")],
    }
    with (
        patch("florabase.db.session.Session", session_class),
        patch("florabase.db.session.get_engine", return_value=MagicMock()),
        patch("florabase.auth.api.change_password", service_mock),
    ):
        asyncio.run(app(scope, receive, send))  # type: ignore[arg-type]
    assert events == (
        ["rollback", "response-500"] if fail_commit else ["commit", f"response-{outcome}"]
    )
    transcript = repr(messages)
    assert "no-store" in transcript
    if fail_commit or outcome != 200:
        assert "set-cookie" not in transcript
        assert "private-csrf" not in transcript
    else:
        assert "private-session" in transcript
        assert "private-csrf" in transcript
    for secret in ("synthetic-current", "synthetic-new", "private database URL"):
        assert secret not in transcript + caplog.text


def test_credential_preparser_and_validation_are_scoped() -> None:
    from fastapi.testclient import TestClient

    from florabase.auth.dependencies import require_csrf
    from florabase.db.session import get_database_session
    from florabase.main import create_app

    app = create_app()
    app.dependency_overrides[require_csrf] = lambda: actor()
    app.dependency_overrides[get_database_session] = lambda: MagicMock()
    client = TestClient(app, base_url="https://florabase.example")
    endpoint = "/api/v1/auth/password"
    headers = {"Content-Type": "application/json", "X-CSRF-Token": "test"}
    for suffix, content, overrides, status in (
        ("?secret=query-canary", b"{}", {}, 400),
        ("/", b"{}", {}, 404),
        ("", b"{}", {"Content-Type": "text/plain"}, 415),
        ("", b"{}", {"Content-Encoding": "gzip"}, 415),
        ("", b"[" * 32769, {}, 413),
        ("", "{}".encode("utf-16-le"), {}, 422),
        ("", b'"bad-utf8-\xff"', {}, 422),
        ("", b'{"bad-secret-key": "value-canary"}', {}, 422),
        ("", b'{"current_password":"\\ud800","new_password":"valid length"}', {}, 422),
        ("", b'{"current_password":"value-canary"', {}, 422),
    ):
        response = client.post(endpoint + suffix, content=content, headers=headers | overrides)
        assert response.status_code == status
        assert response.headers["cache-control"] == "no-store"
        assert "location" not in response.headers
        assert "canary" not in response.text
    streamed = client.post(endpoint, content=iter([b" " * 16384] * 3), headers=headers)
    assert streamed.status_code == 413
    assert client.post("/api/v1/health", content=b"{}").status_code == 405


def test_uvicorn_access_filter_omits_auth_query_before_formatting() -> None:
    from logging import LogRecord

    from florabase.core.logging import AuthAccessFilter

    for path in ("/api/v1/auth/password", "/api/v1/%61uth/password"):
        record = LogRecord(
            "uvicorn.access",
            20,
            "",
            0,
            '%s - "%s %s HTTP/%s" %d',
            ("127.0.0.1", "POST", path + "?query-canary", "1.1", 400),
            None,
        )
        assert AuthAccessFilter().filter(record)
        assert "query-canary" not in record.getMessage()
        assert path in record.getMessage()


@pytest.mark.parametrize(
    ("failure", "status", "detail"),
    [
        (InvalidCredentialsError, 401, "Authentication required"),
        (SessionCsrfError, 403, "Request forbidden"),
        (InvalidNewPasswordError, 422, "invalid_new_password"),
        (PasswordUnchangedError, 422, "password_unchanged"),
        (None, 403, "Request forbidden"),
    ],
)
def test_password_rejection_never_stages_replacement_cookie(
    failure: type[Exception] | None,
    status: int,
    detail: str,
) -> None:
    response = Response()
    with (
        patch("florabase.auth.api.change_password", side_effect=failure) as change,
        pytest.raises(HTTPException) as rejected,
    ):
        change_owner_password(
            ChangePasswordRequest(
                current_password="synthetic current", new_password="synthetic new"
            ),
            response,
            actor(owner=failure is not None),
            MagicMock(),
            settings(),
            "csrf-token",
        )
    assert rejected.value.status_code == status
    body = rejected.value.detail
    assert (body["code"] if isinstance(body, dict) else body) == detail
    assert "set-cookie" not in response.headers
    if failure is None:
        change.assert_not_called()


@pytest.mark.parametrize("operation", ["recovery", "logout", "logout_csrf"])
def test_session_mutations_reject_invalidated_lock_results(operation: str) -> None:
    response = Response()
    failure = SessionCsrfError if operation == "logout_csrf" else InvalidCredentialsError
    with patch("florabase.auth.api.lock_presenting_session", side_effect=failure):
        if operation == "recovery":
            with pytest.raises(HTTPException) as rejected:
                recover_csrf(request(), response, actor(), settings(), MagicMock())
        else:
            with pytest.raises(HTTPException) as rejected:
                logout(response, actor(), MagicMock(), settings(), "stale-token")
    assert rejected.value.status_code == (403 if operation == "logout_csrf" else 401)
    assert "set-cookie" not in response.headers


def test_malformed_login_validation_does_not_reflect_credentials() -> None:
    from fastapi.testclient import TestClient

    from florabase.main import create_app

    client = TestClient(create_app(), base_url="https://florabase.example")
    with patch("florabase.auth.api.authenticate") as authenticate:
        response = client.post(
            "/api/v1/auth/login",
            json={"login_name": "owner", "password": {"value": "synthetic-secret-canary"}},
        )
    assert response.status_code == 422
    assert response.json() == {"detail": "Check the login name and password."}
    assert response.headers["cache-control"] == "no-store"
    assert "synthetic-secret-canary" not in response.text
    authenticate.assert_not_called()
