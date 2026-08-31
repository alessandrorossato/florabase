import logging
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException, Response
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy import Connection, Engine, delete, select
from sqlalchemy.orm import Session
from starlette.requests import Request

from florabase.auth import service
from florabase.auth.api import LoginRequest, login, logout, recover_csrf
from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
    require_origin,
    require_owner,
)
from florabase.auth.model import AuthSession, LoginThrottle, User
from florabase.auth.security import dummy_password_hash, token_digest
from florabase.auth.service import (
    BootstrapError,
    InvalidCredentialsError,
    authenticate,
    bootstrap_owner,
    resolve_session,
    revoke_user_sessions,
)
from florabase.core.config import CookieMode, Environment, Settings

pytestmark = pytest.mark.integration

PASSWORD = "correct horse battery staple"
ORIGIN = "https://florabase.example"


def settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": Environment.TEST,
        "database_url": "postgresql+psycopg://unused",
        "canonical_origin": ORIGIN,
        "cookie_mode": CookieMode.SECURE,
    }
    values.update(overrides)
    return Settings.model_validate(values)


def request(
    *, method: str = "POST", origin: str | None = ORIGIN, cookie: str | None = None
) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if origin is not None:
        headers.append((b"origin", origin.encode("ascii")))
    if cookie is not None:
        headers.append((b"cookie", cookie.encode("ascii")))
    return Request(
        {"type": "http", "method": method, "path": "/api/v1/auth/login", "headers": headers}
    )


def database_session(connection: Connection) -> Session:
    return Session(bind=connection, join_transaction_mode="create_savepoint")


def owner_and_session(
    connection: Connection, app_settings: Settings | None = None
) -> tuple[Session, User, service.NewSession]:
    database = database_session(connection)
    owner = bootstrap_owner(database, "owner", PASSWORD, "Florabase Owner")
    database.flush()
    authenticated = authenticate(database, owner.login_name, PASSWORD, app_settings or settings())
    database.flush()
    return database, owner, authenticated


def test_first_owner_bootstrap_is_guarded_and_persists_only_argon2id(
    database_connection: Connection,
) -> None:
    with database_session(database_connection) as database:
        owner = bootstrap_owner(database, " OWNER ", PASSWORD, "Florabase Owner")
        database.flush()

        assert owner.login_name == "owner"
        assert owner.enabled is True
        assert owner.owner is True
        assert owner.password_hash.startswith("$argon2id$v=19$m=65536,t=3,p=1$")
        assert PASSWORD not in owner.password_hash
        with pytest.raises(BootstrapError, match="already exists"):
            bootstrap_owner(database, "other", PASSWORD)


def test_concurrent_bootstrap_creates_exactly_one_owner(database_engine: Engine) -> None:
    with database_engine.begin() as connection:
        connection.execute(delete(User))

    def attempt(login_name: str) -> str:
        try:
            with Session(database_engine) as database, database.begin():
                bootstrap_owner(database, login_name, PASSWORD)
        except BootstrapError:
            return "rejected"
        return "created"

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(attempt, ("owner-one", "owner-two")))
        with Session(database_engine) as database:
            count = len(database.scalars(select(User.id)).all())
        assert sorted(outcomes) == ["created", "rejected"]
        assert count == 1
    finally:
        with database_engine.begin() as connection:
            connection.execute(delete(User))


def test_bootstrap_cli_reads_password_from_stdin_and_refuses_second_owner(
    database_engine: Engine,
) -> None:
    with database_engine.begin() as connection:
        connection.execute(delete(User))
    command = [sys.executable, "-m", "florabase.auth.bootstrap", "cli-owner", "--password-stdin"]
    environment = {**os.environ, "PYTHONPATH": "/app/src"}

    try:
        first = subprocess.run(
            command,
            input=f"{PASSWORD}\n",
            capture_output=True,
            text=True,
            check=False,
            env=environment,
        )
        second = subprocess.run(
            command,
            input=f"{PASSWORD}\n",
            capture_output=True,
            text=True,
            check=False,
            env=environment,
        )
        with Session(database_engine) as database:
            owner = database.scalars(select(User)).one()

        assert first.returncode == 0
        assert first.stdout == "Owner created: cli-owner\n"
        assert second.returncode == 1
        assert "already exists" in second.stderr
        assert PASSWORD not in first.stdout + first.stderr + second.stdout + second.stderr
        assert owner.password_hash.startswith("$argon2id$")
        assert PASSWORD not in owner.password_hash
    finally:
        with database_engine.begin() as connection:
            connection.execute(delete(User))


def test_login_uses_generic_failures_dummy_verification_and_redacts_secrets(
    database_connection: Connection,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with database_session(database_connection) as database:
        bootstrap_owner(database, "owner", PASSWORD)
        database.flush()
        calls = 0
        real_dummy = dummy_password_hash

        def observed_dummy() -> str:
            nonlocal calls
            calls += 1
            return real_dummy()

        monkeypatch.setattr(service, "dummy_password_hash", observed_dummy)
        caplog.set_level(logging.INFO)
        failures: list[tuple[int, str]] = []
        for login_name, password in (("owner", "wrong password value"), ("unknown", PASSWORD)):
            with pytest.raises(HTTPException) as caught:
                login(
                    LoginRequest(login_name=login_name, password=password),
                    request(),
                    Response(),
                    database,
                    settings(),
                )
            failures.append((caught.value.status_code, str(caught.value.detail)))

        log_text = caplog.text
        assert failures == [(401, "Invalid login credentials")] * 2
        assert calls == 1
        assert PASSWORD not in log_text
        assert "wrong password value" not in log_text
        assert "unknown" not in log_text


def test_disabled_owner_cannot_log_in(database_connection: Connection) -> None:
    with database_session(database_connection) as database:
        owner = bootstrap_owner(database, "owner", PASSWORD)
        owner.enabled = False
        database.flush()

        with pytest.raises(HTTPException) as caught:
            login(
                LoginRequest(login_name="owner", password=PASSWORD),
                request(),
                Response(),
                database,
                settings(),
            )
        assert caught.value.status_code == 401
        assert caught.value.detail == "Invalid login credentials"


def test_successful_login_creates_digest_only_session_and_secure_cookie(
    database_connection: Connection,
) -> None:
    with database_session(database_connection) as database:
        bootstrap_owner(database, "owner", PASSWORD)
        database.flush()
        response = Response()
        body = login(
            LoginRequest(login_name="owner", password=PASSWORD),
            request(),
            response,
            database,
            settings(),
        )
        persisted = database.scalars(select(AuthSession)).one()
        set_cookie = response.headers["set-cookie"]
        raw_session = set_cookie.split("=", 1)[1].split(";", 1)[0]

        assert persisted.token_digest == token_digest(raw_session)
        assert persisted.csrf_digest == token_digest(body.csrf_token)
        assert body.csrf_token.encode() not in persisted.csrf_digest
        assert PASSWORD.encode() not in persisted.token_digest
        assert set_cookie.startswith("__Host-florabase-session=")
        assert "Secure" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "SameSite=strict" in set_cookie
        assert "Path=/" in set_cookie
        assert "Domain=" not in set_cookie
        assert response.headers["cache-control"] == "no-store"


def test_login_origin_policy_and_development_cookie_are_explicit(
    database_connection: Connection,
) -> None:
    with database_session(database_connection) as database:
        bootstrap_owner(database, "owner", PASSWORD)
        database.flush()
        for invalid_origin in (None, "https://evil.example"):
            with pytest.raises(HTTPException) as caught:
                login(
                    LoginRequest(login_name="owner", password=PASSWORD),
                    request(origin=invalid_origin),
                    Response(),
                    database,
                    settings(),
                )
            assert caught.value.status_code == 403

        development = settings(
            environment=Environment.DEVELOPMENT,
            canonical_origin="http://localhost:5173",
            cookie_mode=CookieMode.LOOPBACK_DEVELOPMENT,
        )
        response = Response()
        login(
            LoginRequest(login_name="owner", password=PASSWORD),
            request(origin="http://localhost:5173"),
            response,
            database,
            development,
        )
        assert response.headers["set-cookie"].startswith("florabase-session-dev=")
        assert "Secure" not in response.headers["set-cookie"]


def test_successful_login_upgrades_weaker_hash_and_revokes_existing_sessions(
    database_connection: Connection,
) -> None:
    weak_hasher = PasswordHash((Argon2Hasher(memory_cost=19_456, time_cost=2, parallelism=1),))
    with database_session(database_connection) as database:
        owner = bootstrap_owner(database, "owner", PASSWORD)
        owner.password_hash = weak_hasher.hash(PASSWORD)
        database.flush()
        first = authenticate(database, "owner", PASSWORD, settings())
        database.flush()
        owner.password_hash = weak_hasher.hash(PASSWORD)
        second = authenticate(database, "owner", PASSWORD, settings())
        database.flush()

        assert owner.password_hash.startswith("$argon2id$v=19$m=65536,t=3,p=1$")
        assert first.session.revoked_at is not None
        assert second.session.revoked_at is None


def test_session_validation_expiry_disablement_touch_and_revocation(
    database_connection: Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    app_settings = settings(session_touch_interval_seconds=300)
    base = datetime(2026, 8, 28, 10, tzinfo=UTC)
    monkeypatch.setattr(service, "utc_now", lambda: base)
    with database_session(database_connection) as database:
        owner = bootstrap_owner(database, "owner", PASSWORD)
        authenticated = authenticate(database, "owner", PASSWORD, app_settings)
        database.flush()

        assert (
            resolve_session(database, authenticated.session_token, app_settings)[0].id == owner.id
        )
        with pytest.raises(InvalidCredentialsError):
            resolve_session(database, "not-a-session", app_settings)

        monkeypatch.setattr(service, "utc_now", lambda: base + timedelta(seconds=299))
        resolve_session(database, authenticated.session_token, app_settings)
        assert authenticated.session.last_seen_at == base
        monkeypatch.setattr(service, "utc_now", lambda: base + timedelta(seconds=301))
        resolve_session(database, authenticated.session_token, app_settings)
        assert authenticated.session.last_seen_at == base + timedelta(seconds=301)

        authenticated.session.revoked_at = base + timedelta(seconds=302)
        with pytest.raises(InvalidCredentialsError):
            resolve_session(database, authenticated.session_token, app_settings)
        authenticated.session.revoked_at = None
        authenticated.session.idle_expires_at = base
        with pytest.raises(InvalidCredentialsError):
            resolve_session(database, authenticated.session_token, app_settings)
        authenticated.session.idle_expires_at = base + timedelta(seconds=300)
        authenticated.session.absolute_expires_at = base + timedelta(seconds=300)
        with pytest.raises(InvalidCredentialsError):
            resolve_session(database, authenticated.session_token, app_settings)
        authenticated.session.idle_expires_at = base + timedelta(days=2)
        authenticated.session.absolute_expires_at = base + timedelta(days=30)
        owner.enabled = False
        with pytest.raises(InvalidCredentialsError):
            resolve_session(database, authenticated.session_token, app_settings)


def test_authentication_dependency_returns_generic_401_for_missing_and_invalid_cookie(
    database_connection: Connection,
) -> None:
    with database_session(database_connection) as database:
        for incoming_request in (
            request(method="GET"),
            request(method="GET", cookie="__Host-florabase-session=invalid-token"),
        ):
            with pytest.raises(HTTPException) as caught:
                require_authenticated_actor(incoming_request, database, settings())
            assert caught.value.status_code == 401
            assert caught.value.detail == "Authentication required"


def test_csrf_is_session_bound_and_origin_bound(database_connection: Connection) -> None:
    with database_session(database_connection) as database:
        owner = bootstrap_owner(database, "owner", PASSWORD)
        first = authenticate(database, "owner", PASSWORD, settings())
        second = authenticate(database, "owner", PASSWORD, settings())
        actor = AuthenticatedActor(
            owner.id, owner.login_name, owner.display_name, True, first.session
        )

        assert require_csrf(request(), actor, settings(), first.csrf_token) is actor
        for csrf_token in (None, "wrong-csrf-token", second.csrf_token):
            with pytest.raises(HTTPException) as caught:
                require_csrf(request(), actor, settings(), csrf_token)
            assert caught.value.status_code == 403
        with pytest.raises(HTTPException) as caught:
            require_csrf(
                request(origin="https://evil.example"), actor, settings(), first.csrf_token
            )
        assert caught.value.status_code == 403

        require_origin(request(method="GET"), settings())
        assert first.session.revoked_at is None


def test_csrf_recovery_rotates_only_csrf_and_redacts_raw_tokens(
    database_connection: Connection, caplog: pytest.LogCaptureFixture
) -> None:
    database, owner, authenticated = owner_and_session(database_connection)
    with database:
        actor = AuthenticatedActor(
            owner.id, owner.login_name, owner.display_name, True, authenticated.session
        )
        session_id = authenticated.session.id
        session_digest = authenticated.session.token_digest
        previous_csrf = authenticated.csrf_token
        caplog.set_level(logging.INFO)
        response = Response()

        body = recover_csrf(request(), response, actor, settings())
        database.flush()
        persisted = database.get(AuthSession, session_id)

        assert persisted is not None
        assert persisted.id == session_id
        assert persisted.token_digest == session_digest
        assert persisted.csrf_digest == token_digest(body.csrf_token)
        assert body.csrf_token != previous_csrf
        assert require_csrf(request(), actor, settings(), body.csrf_token) is actor
        with pytest.raises(HTTPException) as caught:
            require_csrf(request(), actor, settings(), previous_csrf)
        assert caught.value.status_code == 403
        assert response.headers["cache-control"] == "no-store"
        assert body.csrf_token not in caplog.text
        assert authenticated.session_token not in caplog.text


def test_csrf_recovery_requires_exact_origin() -> None:
    current_actor = AuthenticatedActor(
        user_id=User().id,
        login_name="owner",
        display_name=None,
        owner=True,
        session=AuthSession(csrf_digest=b"x" * 32),
    )
    for origin in (None, "https://evil.example"):
        with pytest.raises(HTTPException) as caught:
            recover_csrf(request(origin=origin), Response(), current_actor, settings())
        assert caught.value.status_code == 403


def test_owner_authorization_boundary_returns_403() -> None:
    actor = AuthenticatedActor(
        user_id=User().id,
        login_name="member",
        display_name=None,
        owner=False,
        session=AuthSession(),
    )

    with pytest.raises(HTTPException) as caught:
        require_owner(actor)
    assert caught.value.status_code == 403
    assert caught.value.detail == "Request forbidden"


def test_logout_revokes_server_state_and_expires_cookie(database_connection: Connection) -> None:
    database, owner, authenticated = owner_and_session(database_connection)
    with database:
        actor = AuthenticatedActor(
            owner.id, owner.login_name, owner.display_name, True, authenticated.session
        )
        response = Response()
        body = logout(response, actor, database, settings())

        assert body.status == "ok"
        assert authenticated.session.revoked_at is not None
        assert response.headers["set-cookie"].startswith("__Host-florabase-session=")
        assert "Max-Age=0" in response.headers["set-cookie"]
        with pytest.raises(InvalidCredentialsError):
            resolve_session(database, authenticated.session_token, settings())


def test_user_wide_revocation_primitive_is_explicit(database_connection: Connection) -> None:
    database, owner, first = owner_and_session(database_connection)
    with database:
        second = authenticate(database, "owner", PASSWORD, settings())
        database.flush()
        assert revoke_user_sessions(database, owner.id) == 2
        assert first.session.revoked_at is not None
        assert second.session.revoked_at is not None


def test_throttling_backoff_retry_after_success_reset_and_expired_reuse(
    database_connection: Connection,
) -> None:
    app_settings = settings(login_failure_threshold=3, login_backoff_base_seconds=5)
    with database_session(database_connection) as database:
        bootstrap_owner(database, "owner", PASSWORD)
        database.flush()
        for _ in range(3):
            with pytest.raises(InvalidCredentialsError):
                authenticate(database, "owner", "wrong password", app_settings)
        with pytest.raises(HTTPException) as throttled:
            login(
                LoginRequest(login_name="owner", password=PASSWORD),
                request(),
                Response(),
                database,
                app_settings,
            )
        assert throttled.value.status_code == 429
        assert throttled.value.headers is not None
        assert int(throttled.value.headers["Retry-After"]) in range(1, 6)

        throttle = database.get(LoginThrottle, "owner")
        assert throttle is not None
        throttle.backoff_until = None
        authenticate(database, "owner", PASSWORD, app_settings)
        database.flush()
        assert database.get(LoginThrottle, "owner") is None

        with pytest.raises(InvalidCredentialsError):
            authenticate(database, "unknown", "wrong password", app_settings)
        unknown = database.get(LoginThrottle, "unknown")
        assert unknown is not None
        unknown.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        with pytest.raises(InvalidCredentialsError):
            authenticate(database, "unknown", "wrong password", app_settings)
        reused = database.get(LoginThrottle, "unknown")
        assert reused is not None
        assert reused.failed_attempts == 1


def test_concurrent_failures_cannot_bypass_threshold(database_engine: Engine) -> None:
    app_settings = settings(login_failure_threshold=3)
    with database_engine.begin() as connection:
        connection.execute(delete(LoginThrottle))

    def fail_once(_: int) -> None:
        with Session(database_engine) as database:
            try:
                authenticate(database, "concurrent-unknown", "wrong password", app_settings)
            except InvalidCredentialsError:
                database.commit()

    try:
        with ThreadPoolExecutor(max_workers=3) as executor:
            list(executor.map(fail_once, range(3)))
        with Session(database_engine) as database:
            throttle = database.get(LoginThrottle, "concurrent-unknown")
            assert throttle is not None
            assert throttle.failed_attempts == 3
            assert throttle.backoff_until is not None
    finally:
        with database_engine.begin() as connection:
            connection.execute(delete(LoginThrottle))
