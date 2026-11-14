import json
import logging
import os
import subprocess
import sys
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from queue import Queue
from threading import Event
from time import monotonic
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, Response
from fastapi.testclient import TestClient
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy import Connection, Engine, delete, select, text
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import JSONResponse

from florabase.auth import service
from florabase.auth.api import LoginRequest, LoginResponse, login, logout, recover_csrf
from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
    require_origin,
    require_owner,
)
from florabase.auth.model import AuthSession, LoginThrottle, User
from florabase.auth.security import dummy_password_hash, password_hasher, token_digest
from florabase.auth.service import (
    BootstrapError,
    InvalidCredentialsError,
    authenticate,
    bootstrap_owner,
    resolve_session,
    revoke_session,
    revoke_user_sessions,
)
from florabase.core.config import CookieMode, Environment, Settings
from florabase.saved_views.model import SavedView
from florabase.saved_views.state import SavedViewSurface

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
            result = login(
                LoginRequest(login_name=login_name, password=password),
                request(),
                Response(),
                database,
                settings(),
            )
            assert isinstance(result, JSONResponse)
            failures.append((result.status_code, json.loads(bytes(result.body))["detail"]))

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

        result = login(
            LoginRequest(login_name="owner", password=PASSWORD),
            request(),
            Response(),
            database,
            settings(),
        )
        assert isinstance(result, JSONResponse)
        assert result.status_code == 401
        assert json.loads(bytes(result.body))["detail"] == "Invalid login credentials"


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
        assert isinstance(body, LoginResponse)
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

        body = recover_csrf(request(), response, actor, settings(), database)
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
            recover_csrf(request(origin=origin), Response(), current_actor, settings(), MagicMock())
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
        body = logout(response, actor, database, settings(), authenticated.csrf_token)

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
        throttled = login(
            LoginRequest(login_name="owner", password=PASSWORD),
            request(),
            Response(),
            database,
            app_settings,
        )
        assert isinstance(throttled, JSONResponse)
        assert throttled.status_code == 429
        assert int(throttled.headers["Retry-After"]) in range(1, 6)

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


@pytest.fixture
def auth_client(
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    from florabase.core.config import get_settings
    from florabase.main import create_app

    with database_engine.begin() as connection:
        connection.execute(delete(User))
        connection.execute(delete(LoginThrottle))
    monkeypatch.setattr("florabase.db.session.get_engine", lambda: database_engine)
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings(login_failure_threshold=3)
    try:
        with Session(database_engine) as database, database.begin():
            bootstrap_owner(database, "owner", PASSWORD)
        yield TestClient(app, base_url=ORIGIN)
    finally:
        with database_engine.begin() as connection:
            connection.execute(delete(User))
            connection.execute(delete(LoginThrottle))


AUTH = "/api/v1/auth/"
NEW_PASSWORD = "  a new botanical passphrase 🪴  "


def login_client(client: TestClient, password: str = PASSWORD) -> tuple[str, dict[str, str]]:
    response = client.post(
        AUTH + "login",
        headers={"Origin": ORIGIN},
        json={"login_name": "owner", "password": password},
    )
    assert response.status_code == 200
    token = response.cookies["__Host-florabase-session"]
    return token, {"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]}


def test_change_persists_failures_and_replaces_sessions_atomically(
    auth_client: TestClient,
    database_engine: Engine,
) -> None:
    payload = {"current_password": PASSWORD, "new_password": NEW_PASSWORD}
    assert auth_client.post(AUTH + "password", json=payload).status_code == 401
    other, _ = login_client(auth_client)
    presenting, headers = login_client(auth_client)
    with Session(database_engine) as db, db.begin():
        owner = db.scalars(select(User)).one()
        prior_hash, prior_time, user_id = owner.password_hash, owner.password_changed_at, owner.id
        old_session = db.scalars(
            select(AuthSession).where(AuthSession.token_digest == token_digest(presenting))
        ).one()
        old_session.last_seen_at -= timedelta(minutes=10)
        old_session.created_at = old_session.last_seen_at
        seen = old_session.last_seen_at
    private_key = f"pwchg:{user_id}"
    payload["current_password"] = "wrong synthetic password"
    for _ in range(3):
        rejected = auth_client.post(AUTH + "password", json=payload, headers=headers)
        assert rejected.status_code == 403
        assert rejected.json()["detail"]["code"] == "invalid_current_password"
        assert "set-cookie" not in rejected.headers
    backoff = auth_client.post(AUTH + "password", json=payload, headers=headers)
    assert backoff.status_code == 429
    assert int(backoff.headers["Retry-After"]) > 0
    with Session(database_engine) as db, db.begin():
        private = db.get(LoginThrottle, private_key)
        assert private is not None
        assert private.failed_attempts == 3
        saved_owner = db.get(User, user_id)
        assert saved_owner is not None
        assert saved_owner.password_hash == prior_hash
        assert saved_owner.password_changed_at == prior_time
        old_session = db.scalars(
            select(AuthSession).where(AuthSession.token_digest == token_digest(presenting))
        ).one()
        assert old_session.last_seen_at == seen
        assert old_session.revoked_at is None
        private.backoff_until = None
    # Public backoff and private backoff have independent state.
    for _ in range(3):
        assert (
            auth_client.post(
                AUTH + "login",
                headers={"Origin": ORIGIN},
                json={"login_name": "owner", "password": payload["current_password"]},
            ).status_code
            == 401
        )
    payload["current_password"] = PASSWORD
    for bad_headers in (
        {},
        {"Origin": ORIGIN, "X-CSRF-Token": "different-token"},
        headers | {"Origin": "https://wrong.example"},
        [
            (b"Origin", b"https://florabase\xe9.example"),
            (b"X-CSRF-Token", headers["X-CSRF-Token"].encode()),
        ],
        [("Origin", ORIGIN), ("Origin", ORIGIN), ("X-CSRF-Token", headers["X-CSRF-Token"])],
    ):
        assert (
            auth_client.post(AUTH + "password", json=payload, headers=bad_headers).status_code
            == 403
        )
    reused = auth_client.post(
        AUTH + "password", json=payload | {"new_password": PASSWORD}, headers=headers
    )
    assert reused.status_code == 422
    assert reused.json()["detail"]["code"] == "password_unchanged"
    changed = auth_client.post(AUTH + "password", json=payload, headers=headers)
    assert changed.status_code == 200
    assert changed.headers["cache-control"] == "no-store"
    assert all(
        value in changed.headers["set-cookie"]
        for value in ("Secure", "HttpOnly", "SameSite=strict")
    )
    fresh = changed.cookies["__Host-florabase-session"]
    csrf = changed.json()["csrf_token"]
    assert fresh not in (other, presenting)
    with Session(database_engine) as db, db.begin():
        saved_owner = db.get(User, user_id)
        assert saved_owner is not None
        assert saved_owner.password_hash != prior_hash
        assert saved_owner.updated_at == saved_owner.password_changed_at > prior_time
        assert db.get(LoginThrottle, private_key) is None
        public = db.get(LoginThrottle, "owner")
        assert public is not None
        assert public.failed_attempts == 3
        public.backoff_until = None
        rows = list(db.scalars(select(AuthSession)))
        assert sum(row.revoked_at is None for row in rows) == 1
        active = next(row for row in rows if row.revoked_at is None)
        assert active.token_digest == token_digest(fresh)
        assert active.csrf_digest == token_digest(csrf)
    stale = TestClient(auth_client.app, base_url=ORIGIN)
    for old_token in (other, presenting):
        assert (
            stale.get(
                AUTH + "session", headers={"Cookie": f"__Host-florabase-session={old_token}"}
            ).status_code
            == 401
        )
    assert auth_client.post(AUTH + "logout", headers=headers).status_code == 403
    assert (
        auth_client.post(AUTH + "logout", headers=headers | {"X-CSRF-Token": csrf}).status_code
        == 200
    )
    assert (
        auth_client.post(
            AUTH + "login",
            headers={"Origin": ORIGIN},
            json={"login_name": "owner", "password": PASSWORD},
        ).status_code
        == 401
    )
    with Session(database_engine) as db, db.begin():
        public = db.get(LoginThrottle, "owner")
        assert public is not None
        public.backoff_until = None
    login_client(auth_client, NEW_PASSWORD)


def test_login_cleanup_is_bounded_and_skips_locked_and_private_rows(
    auth_client: TestClient,
    database_engine: Engine,
) -> None:
    expired = datetime.now(UTC) - timedelta(days=1)
    with Session(database_engine) as db, db.begin():
        owner = db.scalars(select(User)).one()
        private_key = f"pwchg:{owner.id}"
        db.add_all(
            [
                LoginThrottle(
                    login_name=key, failed_attempts=1, expires_at=expired, updated_at=expired
                )
                for key in [*(f"guessed-{index:02}" for index in range(40)), private_key]
            ]
        )
    with Session(database_engine) as blocker, blocker.begin():
        blocker.scalars(
            select(LoginThrottle).where(LoginThrottle.login_name == "guessed-00").with_for_update()
        ).one()
        login_client(auth_client)
        with Session(database_engine) as db:
            keys = set(db.scalars(select(LoginThrottle.login_name)))
            assert len(keys) == 9
            assert {"guessed-00", private_key} <= keys


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        ("login", "change", "ok"),
        ("change", "login", "invalid"),
        ("login", "reset", "ok"),
        ("reset", "login", "invalid"),
        ("change", "change", "invalid"),
        ("reset", "reset", "ok"),
        ("change", "reset", "ok"),
        ("reset", "change", "invalid"),
        ("logout", "csrf", "invalid"),
        ("csrf", "logout", "csrf"),
        ("change", "csrf", "invalid"),
        ("csrf", "change", "csrf"),
        ("reset", "csrf", "invalid"),
        ("csrf", "reset", "ok"),
        ("logout", "change", "invalid"),
        ("change", "logout", "invalid"),
        ("csrf", "csrf", "ok"),
        ("csrf", "expiry", "invalid"),
        ("rehash", "reset", "ok"),
        ("reset", "rehash", "invalid"),
    ],
)
def test_credential_races_observe_committed_state_after_wait(
    auth_client: TestClient,
    database_engine: Engine,
    first: str,
    second: str,
    expected: str,
) -> None:
    presenting, headers = login_client(auth_client)
    csrf = headers["X-CSRF-Token"]
    with Session(database_engine) as seed, seed.begin():
        old_session = seed.scalars(
            select(AuthSession).where(AuthSession.token_digest == token_digest(presenting))
        ).one()
        old_session.last_seen_at -= timedelta(minutes=10)
        old_session.created_at = old_session.last_seen_at
        old_session_id = old_session.id
        original_digest = old_session.csrf_digest
        if "rehash" in (first, second):
            owner = seed.get(User, old_session.user_id)
            assert owner is not None
            owner.password_hash = PasswordHash((Argon2Hasher(memory_cost=19456),)).hash(PASSWORD)

    app_settings = settings()
    waiting: Queue[int] = Queue()
    start = Event()

    def mutate(db: Session, action: str, session: AuthSession | None, password: str) -> str:
        if action in ("login", "rehash"):
            authenticate(db, "owner", PASSWORD, app_settings)
        elif action == "reset":
            service.set_auth_timeouts(db)
            db.execute(text("SELECT pg_advisory_xact_lock(721669727)"))
            service.reset_owner_password(db, "owner", password)
        else:
            assert session is not None
            if action == "change":
                service.change_password(db, session, csrf, PASSWORD, password, app_settings)
            elif action == "logout":
                locked = service.lock_presenting_session(db, session, csrf)
                revoke_session(db, locked)
            else:
                locked = service.lock_presenting_session(db, session)
                service.rotate_csrf(locked, app_settings)
        db.flush()
        return "ok"

    def load_presenting(db: Session, action: str) -> AuthSession | None:
        return (
            resolve_session(db, presenting, app_settings)[1]
            if action in {"change", "logout", "csrf", "expiry"}
            else None
        )

    def contender() -> str:
        try:
            with Session(database_engine) as db, db.begin():
                pid = db.scalar(text("SELECT pg_backend_pid()"))
                assert isinstance(pid, int)
                session = load_presenting(db, second)
                with db.no_autoflush:
                    waiting.put(pid)
                assert start.wait(5)
                return mutate(db, second, session, "second credential value")
        except InvalidCredentialsError:
            return "invalid"
        except service.SessionCsrfError:
            return "csrf"

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(contender)
        contender_pid = waiting.get(timeout=5)
        try:
            with Session(database_engine) as db, db.begin():
                blocker_pid = db.scalar(text("SELECT pg_backend_pid()"))
                mutate(db, first, load_presenting(db, first), NEW_PASSWORD)
                if second == "expiry":
                    expiring = db.get(AuthSession, old_session_id)
                    assert expiring is not None
                    expiring.idle_expires_at = datetime.now(UTC) - timedelta(seconds=1)
                    db.flush()
                start.set()
                with database_engine.connect().execution_options(
                    isolation_level="AUTOCOMMIT"
                ) as observer:
                    deadline = monotonic() + 4
                    while monotonic() < deadline:
                        blockers = observer.scalar(
                            text("SELECT pg_blocking_pids(:pid)"), {"pid": contender_pid}
                        )
                        if blockers and blocker_pid in blockers:
                            break
                    else:
                        pytest.fail("Contender did not wait for the first transaction")
        finally:
            start.set()
        assert future.result(timeout=8) == expected

    with Session(database_engine) as db:
        owner = db.scalars(select(User)).one()
        sessions = list(db.scalars(select(AuthSession).order_by(AuthSession.id)))
        persisted_session = db.get(AuthSession, old_session_id)
        assert persisted_session is not None
        if first in {"logout", "change", "reset"} and second == "csrf":
            assert persisted_session.csrf_digest == original_digest
            assert persisted_session.revoked_at is not None
        if first in {"change", "reset", "rehash"} or second == "reset":
            assert owner.updated_at == owner.password_changed_at
        if second == "reset":
            assert all(session.revoked_at is not None for session in sessions)
            assert password_hasher().verify("second credential value", owner.password_hash)
        elif first == "reset":
            assert all(session.revoked_at is not None for session in sessions)
            assert password_hasher().verify(NEW_PASSWORD, owner.password_hash)
        elif first == "change" or (second == "change" and expected == "ok"):
            assert sum(session.revoked_at is None for session in sessions) == 1
            committed = NEW_PASSWORD if first == "change" else "second credential value"
            assert password_hasher().verify(committed, owner.password_hash)


def test_locked_user_allows_foreign_key_insert(
    auth_client: TestClient,
    database_engine: Engine,
) -> None:
    with Session(database_engine) as lock_owner, lock_owner.begin():
        owner = service._locked_user(lock_owner, login="owner")
        assert owner is not None
        with Session(database_engine) as inserter, inserter.begin():
            inserter.execute(text("SET LOCAL lock_timeout = '500ms'"))
            inserter.add(
                SavedView(
                    owner_id=owner.id,
                    name="Credential lock compatibility",
                    surface=SavedViewSurface.GLOBAL_SEARCH.value,
                    state_version=1,
                    state={},
                )
            )
            inserter.flush()


def test_offline_reset_command_revokes_and_clears_both_buckets(
    auth_client: TestClient,
    database_engine: Engine,
) -> None:
    login_client(auth_client)
    login_client(auth_client)
    now = datetime.now(UTC)
    with Session(database_engine) as db, db.begin():
        owner = db.scalars(select(User)).one()
        owner_id = owner.id
        db.add_all(
            [
                LoginThrottle(
                    login_name=key,
                    failed_attempts=5,
                    backoff_until=now + timedelta(minutes=10),
                    updated_at=now,
                    expires_at=now + timedelta(days=1),
                )
                for key in ("owner", f"pwchg:{owner_id}")
            ]
        )
    command = [
        sys.executable,
        "-m",
        "florabase.auth.reset_password",
        "OWNER",
        "--password-json-stdin",
    ]
    for login_name, status in (("missing", 1), ("OWNER", 0)):
        result = subprocess.run(
            [*command[:3], login_name, command[-1]],
            input=json.dumps(NEW_PASSWORD),
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
            env={**os.environ, "PYTHONPATH": "/app/src"},
        )
        assert result.returncode == status, result.stderr
        assert NEW_PASSWORD not in result.stdout + result.stderr
    with Session(database_engine) as db:
        saved = db.get(User, owner_id)
        assert saved is not None
        assert saved.updated_at == saved.password_changed_at
        assert list(db.scalars(select(LoginThrottle))) == []
        assert all(session.revoked_at is not None for session in db.scalars(select(AuthSession)))
    assert auth_client.get(AUTH + "session").status_code == 401
    login_client(auth_client, NEW_PASSWORD)


def test_change_commit_failure_rolls_back_all_persisted_state(
    auth_client: TestClient, database_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, headers = login_client(auth_client)

    class FailedCommitSession(Session):
        def commit(self) -> None:
            raise RuntimeError("synthetic commit diagnostic")

    monkeypatch.setattr("florabase.db.session.Session", FailedCommitSession)
    response = auth_client.post(
        AUTH + "password",
        headers=headers,
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 500
    assert "set-cookie" not in response.headers
    assert "synthetic commit diagnostic" not in response.text
    with Session(database_engine) as db:
        owner = db.scalars(select(User)).one()
        assert password_hasher().verify(PASSWORD, owner.password_hash)
        assert db.scalars(select(AuthSession)).one().revoked_at is None
        assert list(db.scalars(select(LoginThrottle))) == []


def test_reset_refuses_revision_and_lock_contention(
    auth_client: TestClient, database_engine: Engine
) -> None:
    login_client(auth_client)

    def reset() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "florabase.auth.reset_password",
                "owner",
                "--password-json-stdin",
            ],
            input=json.dumps(NEW_PASSWORD),
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )

    with database_engine.begin() as connection:
        head = connection.scalar(text("SELECT version_num FROM alembic_version"))
        connection.execute(text("UPDATE alembic_version SET version_num = 'wrong_test_revision'"))
    try:
        result = reset()
        assert result.returncode == 1
        assert "installed database revision" in result.stderr
        assert "wrong_test_revision" not in result.stderr
    finally:
        with database_engine.begin() as connection:
            connection.execute(
                text("UPDATE alembic_version SET version_num = :head"), {"head": head}
            )
    with database_engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(721669727)"))
        result = reset()
        assert result.returncode == 1
        assert "Check database health" in result.stderr
    assert auth_client.get(AUTH + "session").status_code == 200
    with Session(database_engine) as db:
        owner = db.scalars(select(User)).one()
        assert password_hasher().verify(PASSWORD, owner.password_hash)
