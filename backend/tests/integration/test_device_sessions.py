from collections.abc import Iterator
from datetime import timedelta
from typing import Any
from uuid import uuid7

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import Engine, delete, inspect, select, text
from sqlalchemy.orm import Session

from alembic import command
from florabase.auth.model import AuthSession, LoginThrottle, User
from florabase.auth.security import token_digest
from florabase.auth.service import bootstrap_owner
from florabase.core.config import CookieMode, Environment, Settings, get_settings
from florabase.main import create_app

pytestmark = pytest.mark.integration

PASSWORD = "correct horse battery staple"
NEW_PASSWORD = "a second botanical passphrase"
WEB_ORIGIN = "https://florabase.example"
NATIVE_ORIGIN = "https://localhost"


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": Environment.TEST,
        "database_url": "postgresql+psycopg://unused",
        "canonical_origin": WEB_ORIGIN,
        "cookie_mode": CookieMode.SECURE,
    }
    values.update(overrides)
    return Settings.model_validate(values)


@pytest.fixture
def device_auth_client(
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    with database_engine.begin() as connection:
        connection.execute(delete(User))
        connection.execute(delete(LoginThrottle))
    monkeypatch.setattr("florabase.db.session.get_engine", lambda: database_engine)
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: _settings(
        login_failure_threshold=3,
        device_session_max_active=5,
    )
    try:
        with Session(database_engine) as database, database.begin():
            bootstrap_owner(database, "owner", PASSWORD, "Florabase Owner")
        yield TestClient(app, base_url=WEB_ORIGIN)
    finally:
        with database_engine.begin() as connection:
            connection.execute(delete(User))
            connection.execute(delete(LoginThrottle))


def _create_device(
    client: TestClient,
    label: str = "Pixel 9",
    password: str = PASSWORD,
    origin: str = NATIVE_ORIGIN,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/auth/device-sessions",
        headers={"Origin": origin, "Content-Type": "application/json"},
        json={"login_name": "owner", "password": password, "device_label": label},
    )
    assert response.status_code == 201, response.text
    assert response.headers["cache-control"] == "no-store"
    assert "set-cookie" not in response.headers
    payload: dict[str, Any] = response.json()
    return payload


def _login_browser(client: TestClient, password: str = PASSWORD) -> tuple[str, dict[str, str]]:
    response = client.post(
        "/api/v1/auth/login",
        headers={"Origin": WEB_ORIGIN},
        json={"login_name": "owner", "password": password},
    )
    assert response.status_code == 200, response.text
    cookie_token = response.cookies["__Host-florabase-session"]
    return cookie_token, {"Origin": WEB_ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]}


def test_device_session_lifecycle_and_bearer_mutations_with_native_origin(
    device_auth_client: TestClient,
    database_engine: Engine,
) -> None:
    created = _create_device(device_auth_client, label="  Pixel 9 Pro  ")
    raw_token = created["token"]
    session_id = created["session_id"]
    assert created["device_label"] == "Pixel 9 Pro"
    assert len(raw_token) >= 32

    with Session(database_engine) as database:
        row = database.scalars(
            select(AuthSession).where(AuthSession.token_digest == token_digest(raw_token))
        ).one()
        assert str(row.id) == session_id
        assert row.transport == "bearer"
        assert row.device_label == "Pixel 9 Pro"
        assert row.csrf_digest is None
        assert row.revoked_at is None
        assert (row.idle_expires_at - row.created_at) == timedelta(days=30)
        assert (row.absolute_expires_at - row.created_at) == timedelta(days=180)
        # Ensure plaintext token is never stored in auth_sessions.
        raw_hits = database.execute(
            text("SELECT count(*) FROM auth_sessions WHERE device_label LIKE :pat"),
            {"pat": f"%{raw_token}%"},
        ).scalar_one()
        assert raw_hits == 0

    bearer_headers = {
        "Authorization": f"Bearer {raw_token}",
        "Origin": NATIVE_ORIGIN,
    }

    # Session probe works with CORS headers and no credentials flag.
    session_resp = device_auth_client.get("/api/v1/auth/session", headers=bearer_headers)
    assert session_resp.status_code == 200
    assert session_resp.json()["login_name"] == "owner"
    assert session_resp.headers["access-control-allow-origin"] == NATIVE_ORIGIN
    assert "access-control-allow-credentials" not in session_resp.headers

    # Bearer POST / PUT / PATCH / DELETE carrying Origin: https://localhost without CSRF succeed.
    created_loc = device_auth_client.post(
        "/api/v1/locations",
        headers=bearer_headers,
        json={"name": "Mobile Bench"},
    )
    assert created_loc.status_code == 201, created_loc.text
    assert created_loc.headers["access-control-allow-origin"] == NATIVE_ORIGIN
    loc_id = created_loc.json()["id"]

    updated_loc = device_auth_client.put(
        f"/api/v1/locations/{loc_id}",
        headers=bearer_headers,
        json={"name": "Mobile Bench Updated"},
    )
    assert updated_loc.status_code == 200, updated_loc.text
    assert updated_loc.json()["name"] == "Mobile Bench Updated"

    created_view = device_auth_client.post(
        "/api/v1/saved-views",
        headers=bearer_headers,
        json={
            "name": "Mobile View",
            "surface": "plants",
            "state_version": 1,
            "state": {"q": "Acer"},
        },
    )
    assert created_view.status_code == 201, created_view.text
    view_id = created_view.json()["id"]

    patched_view = device_auth_client.patch(
        f"/api/v1/saved-views/{view_id}",
        headers=bearer_headers,
        json={"name": "Mobile View Renamed"},
    )
    assert patched_view.status_code == 200, patched_view.text
    assert patched_view.json()["name"] == "Mobile View Renamed"
    assert patched_view.headers["access-control-allow-origin"] == NATIVE_ORIGIN

    deleted_view = device_auth_client.delete(
        f"/api/v1/saved-views/{view_id}",
        headers=bearer_headers,
    )
    assert deleted_view.status_code == 204, deleted_view.text

    deleted_loc = device_auth_client.delete(
        f"/api/v1/locations/{loc_id}",
        headers=bearer_headers,
    )
    assert deleted_loc.status_code == 204, deleted_loc.text

    # Sign out current device session.
    sign_out = device_auth_client.delete(
        "/api/v1/auth/device-sessions/current",
        headers=bearer_headers,
    )
    assert sign_out.status_code == 204

    # Subsequent calls fail with 401 + WWW-Authenticate: Bearer.
    after = device_auth_client.get("/api/v1/auth/session", headers=bearer_headers)
    assert after.status_code == 401
    assert after.headers["www-authenticate"] == "Bearer"


def test_device_session_transport_isolation_and_ambiguity_rejection(
    device_auth_client: TestClient,
) -> None:
    created = _create_device(device_auth_client, label="Field Tablet")
    bearer_token = created["token"]
    cookie_token, csrf_headers = _login_browser(device_auth_client)

    # Cookie + Bearer sent simultaneously is always rejected.
    ambiguous = device_auth_client.get(
        "/api/v1/auth/session",
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    assert ambiguous.status_code == 401
    assert ambiguous.headers["www-authenticate"] == "Bearer"

    # Creating a device session while carrying a session cookie is rejected.
    cookie_device_post = device_auth_client.post(
        "/api/v1/auth/device-sessions",
        headers={"Origin": NATIVE_ORIGIN},
        json={"login_name": "owner", "password": PASSWORD, "device_label": "Blocked"},
    )
    assert cookie_device_post.status_code == 401
    assert cookie_device_post.headers["www-authenticate"] == "Bearer"

    # Cookie calling Bearer-only /device-sessions/current is rejected (403).
    cookie_current = device_auth_client.delete(
        "/api/v1/auth/device-sessions/current",
        headers=csrf_headers,
    )
    assert cookie_current.status_code == 403

    # Clear cookies on client before testing Bearer-only calls.
    device_auth_client.cookies.clear()

    # Replaying a cookie token as Bearer fails with 401 + WWW-Authenticate.
    replayed_cookie = device_auth_client.get(
        "/api/v1/auth/session",
        headers={"Authorization": f"Bearer {cookie_token}"},
    )
    assert replayed_cookie.status_code == 401
    assert replayed_cookie.headers["www-authenticate"] == "Bearer"

    # Invalid / malformed Authorization headers return 401 + WWW-Authenticate: Bearer.
    for bad_auth in ("Bearer not-a-real-token", "Basic dXNlcjpwYXNz", "Bearer "):
        bad_resp = device_auth_client.get(
            "/api/v1/auth/session",
            headers={"Authorization": bad_auth},
        )
        assert bad_resp.status_code == 401
        assert bad_resp.headers["www-authenticate"] == "Bearer"

    # Bearer calling cookie-only endpoints (/password, /csrf, /logout) is rejected with 403.
    bearer_headers = {"Authorization": f"Bearer {bearer_token}", "Origin": NATIVE_ORIGIN}
    assert (
        device_auth_client.post(
            "/api/v1/auth/password",
            headers=bearer_headers,
            json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        ).status_code
        == 403
    )
    assert device_auth_client.post("/api/v1/auth/csrf", headers=bearer_headers).status_code == 403
    assert device_auth_client.post("/api/v1/auth/logout", headers=bearer_headers).status_code == 403

    # Stuffing a Bearer token into the session cookie fails with 401.
    stuffed = device_auth_client.get(
        "/api/v1/auth/session",
        cookies={"__Host-florabase-session": bearer_token},
    )
    assert stuffed.status_code == 401


def test_device_session_idle_and_absolute_expiry(
    device_auth_client: TestClient,
    database_engine: Engine,
) -> None:
    idle_device = _create_device(device_auth_client, label="Idle Phone")
    abs_device = _create_device(device_auth_client, label="Old Phone")

    with Session(database_engine) as database, database.begin():
        idle_row = database.scalars(
            select(AuthSession).where(
                AuthSession.token_digest == token_digest(idle_device["token"])
            )
        ).one()
        idle_row.idle_expires_at = idle_row.created_at - timedelta(seconds=1)
        idle_row.created_at = idle_row.idle_expires_at - timedelta(days=30)
        idle_row.last_seen_at = idle_row.created_at

        abs_row = database.scalars(
            select(AuthSession).where(AuthSession.token_digest == token_digest(abs_device["token"]))
        ).one()
        abs_row.absolute_expires_at = abs_row.created_at - timedelta(seconds=1)
        abs_row.idle_expires_at = abs_row.absolute_expires_at
        abs_row.created_at = abs_row.absolute_expires_at - timedelta(days=180)
        abs_row.last_seen_at = abs_row.created_at

    for tok in (idle_device["token"], abs_device["token"]):
        resp = device_auth_client.get(
            "/api/v1/auth/session",
            headers={"Authorization": f"Bearer {tok}"},
        )
        assert resp.status_code == 401
        assert resp.headers["www-authenticate"] == "Bearer"


def test_device_session_listing_revocation_and_password_change(
    device_auth_client: TestClient,
    database_engine: Engine,
) -> None:
    d1 = _create_device(device_auth_client, label="Phone A")
    d2 = _create_device(device_auth_client, label="Phone B")

    # Listing via Bearer marks only the presenting device as current.
    bearer_list = device_auth_client.get(
        "/api/v1/auth/device-sessions",
        headers={"Authorization": f"Bearer {d1['token']}"},
    )
    assert bearer_list.status_code == 200
    items = bearer_list.json()["items"]
    assert len(items) == 2
    by_id = {item["id"]: item for item in items}
    assert by_id[d1["session_id"]]["current"] is True
    assert by_id[d2["session_id"]]["current"] is False

    # Browser cookie session lists devices (current is False for all), revokes one,
    # cannot delete a cookie session via device-sessions endpoint, and can revoke all.
    cookie_token, csrf_headers = _login_browser(device_auth_client)
    with Session(database_engine) as database:
        cookie_row = database.scalars(
            select(AuthSession).where(AuthSession.token_digest == token_digest(cookie_token))
        ).one()
        cookie_session_id = str(cookie_row.id)

    browser_list = device_auth_client.get("/api/v1/auth/device-sessions")
    assert browser_list.status_code == 200
    assert all(item["current"] is False for item in browser_list.json()["items"])

    # Attempting to delete a cookie session or unknown ID returns 404.
    assert (
        device_auth_client.delete(
            f"/api/v1/auth/device-sessions/{cookie_session_id}",
            headers=csrf_headers,
        ).status_code
        == 404
    )
    assert (
        device_auth_client.delete(
            f"/api/v1/auth/device-sessions/{uuid7()}",
            headers=csrf_headers,
        ).status_code
        == 404
    )
    # Browser cookie session is still alive.
    assert device_auth_client.get("/api/v1/auth/session").status_code == 200

    # Revoke Phone A from browser.
    revoke_one = device_auth_client.delete(
        f"/api/v1/auth/device-sessions/{d1['session_id']}",
        headers=csrf_headers,
    )
    assert revoke_one.status_code == 204

    # Revoke all remaining devices from browser.
    revoke_all = device_auth_client.delete("/api/v1/auth/device-sessions", headers=csrf_headers)
    assert revoke_all.status_code == 200
    assert revoke_all.json() == {"revoked_count": 1}

    # Browser session still alive after revoking all device sessions.
    assert device_auth_client.get("/api/v1/auth/session").status_code == 200

    # Verify both devices are revoked (with clean cookie jar).
    saved_cookies = dict(device_auth_client.cookies)
    device_auth_client.cookies.clear()
    for tok in (d1["token"], d2["token"]):
        resp = device_auth_client.get(
            "/api/v1/auth/session",
            headers={"Authorization": f"Bearer {tok}"},
        )
        assert resp.status_code == 401
        assert resp.headers["www-authenticate"] == "Bearer"

    # Issue a fresh device, then change password from browser -> device session must be revoked!
    d3 = _create_device(device_auth_client, label="Phone C")
    device_auth_client.cookies.update(saved_cookies)
    pw_resp = device_auth_client.post(
        "/api/v1/auth/password",
        headers=csrf_headers,
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert pw_resp.status_code == 200, pw_resp.text

    device_auth_client.cookies.clear()
    after_pw = device_auth_client.get(
        "/api/v1/auth/session",
        headers={"Authorization": f"Bearer {d3['token']}"},
    )
    assert after_pw.status_code == 401
    assert after_pw.headers["www-authenticate"] == "Bearer"


def test_device_session_max_active_cap_evicts_oldest_seen(
    device_auth_client: TestClient,
    database_engine: Engine,
) -> None:
    # Fixture configures device_session_max_active=5.
    devices = [_create_device(device_auth_client, label=f"Device {idx}") for idx in range(5)]

    # Make Device 1 the oldest-seen by moving its last_seen_at earlier than Device 0.
    with Session(database_engine) as database, database.begin():
        for idx, dev in enumerate(devices):
            row = database.scalars(
                select(AuthSession).where(AuthSession.token_digest == token_digest(dev["token"]))
            ).one()
            offset_minutes = 60 if idx == 1 else (10 - idx)
            row.created_at = row.created_at - timedelta(minutes=offset_minutes)
            row.last_seen_at = row.created_at

    # Creating a 6th device must evict Device 1 (oldest-seen) and keep the other 5 active.
    sixth = _create_device(device_auth_client, label="Device 5")

    evicted = device_auth_client.get(
        "/api/v1/auth/session",
        headers={"Authorization": f"Bearer {devices[1]['token']}"},
    )
    assert evicted.status_code == 401
    assert evicted.headers["www-authenticate"] == "Bearer"

    for dev in (devices[0], devices[2], devices[3], devices[4], sixth):
        ok = device_auth_client.get(
            "/api/v1/auth/session",
            headers={"Authorization": f"Bearer {dev['token']}"},
        )
        assert ok.status_code == 200


def test_device_session_shares_login_throttle_and_validates_label(
    device_auth_client: TestClient,
) -> None:
    for bad_label in ("", "   ", "a" * 121):
        invalid = device_auth_client.post(
            "/api/v1/auth/device-sessions",
            headers={"Origin": NATIVE_ORIGIN},
            json={"login_name": "owner", "password": PASSWORD, "device_label": bad_label},
        )
        assert invalid.status_code == 422

    # 3 failed attempts on /device-sessions trigger backoff shared with /login.
    for _ in range(3):
        resp = device_auth_client.post(
            "/api/v1/auth/device-sessions",
            headers={"Origin": NATIVE_ORIGIN},
            json={"login_name": "owner", "password": "wrong-password-123", "device_label": "Phone"},
        )
        assert resp.status_code == 401

    throttled_device = device_auth_client.post(
        "/api/v1/auth/device-sessions",
        headers={"Origin": NATIVE_ORIGIN},
        json={"login_name": "owner", "password": PASSWORD, "device_label": "Phone"},
    )
    assert throttled_device.status_code == 429
    assert int(throttled_device.headers["Retry-After"]) > 0

    throttled_browser = device_auth_client.post(
        "/api/v1/auth/login",
        headers={"Origin": WEB_ORIGIN},
        json={"login_name": "owner", "password": PASSWORD},
    )
    assert throttled_browser.status_code == 429


def test_non_owner_device_session_endpoints_and_cross_user_404(
    device_auth_client: TestClient,
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from starlette.requests import Request

    from florabase.auth.dependencies import (
        AuthenticatedActor,
        require_authenticated_actor,
        session_cookie_name,
    )
    from florabase.auth.security import password_hasher
    from florabase.auth.service import (
        InvalidCredentialsError,
        _issue_device_session,
        _issue_session,
        resolve_session,
        utc_now,
    )

    owner_device = _create_device(device_auth_client, label="Owner Phone")
    owner_session_id = owner_device["session_id"]
    _, owner_csrf_headers = _login_browser(device_auth_client)

    settings = _settings(device_session_max_active=5)
    now = utc_now()
    with Session(database_engine) as database, database.begin():
        member = User(
            login_name="member",
            display_name="Member User",
            password_hash=password_hasher().hash(PASSWORD),
            enabled=True,
            owner=True,  # users table currently has ck_users_initial_owner_only (owner = TRUE)
        )
        database.add(member)
        database.flush()
        member_id = member.id
        member_cookie = _issue_session(database, member, settings, now)
        m1 = _issue_device_session(database, member, "Member Phone 1", settings, now)
        m2 = _issue_device_session(database, member, "Member Phone 2", settings, now)
        m1_id, m1_token = str(m1.session.id), m1.token
        m2_id, m2_token = str(m2.session.id), m2.token
        member_cookie_token = member_cookie.session_token
        member_csrf_token = member_cookie.csrf_token

    # Override require_authenticated_actor on the app so that "member" resolves with owner=False,
    # proving the 4 device-session endpoints work for a non-owner actor (owner=False) over HTTP
    # while cross-user access between "owner" and "member" returns 404.
    original_require = require_authenticated_actor

    def resolve_with_non_owner_member(
        request: Request,
        database: Session,
        app_settings: Settings,
    ) -> AuthenticatedActor:
        actor = original_require(request, database, app_settings)
        if actor.user_id == member_id:
            return AuthenticatedActor(
                user_id=actor.user_id,
                login_name=actor.login_name,
                display_name=actor.display_name,
                owner=False,
                session=actor.session,
                transport=actor.transport,
            )
        return actor

    # Confirm the wrapper returns owner=False for member via FastAPI's dependency override:
    from typing import Annotated, cast

    from fastapi import Depends, FastAPI

    from florabase.db.session import get_database_session

    def override_actor(
        request: Request,
        database: Annotated[Session, Depends(get_database_session, scope="function")],
        app_settings: Annotated[Settings, Depends(get_settings)],
    ) -> AuthenticatedActor:
        return resolve_with_non_owner_member(request, database, app_settings)

    app = cast(FastAPI, device_auth_client.app)
    app.dependency_overrides[require_authenticated_actor] = override_actor
    try:
        # Owner cannot revoke member's device session (returns 404, not 403/204).
        cross_from_owner = device_auth_client.delete(
            f"/api/v1/auth/device-sessions/{m1_id}",
            headers=owner_csrf_headers,
        )
        assert cross_from_owner.status_code == 404

        # Switch client to member's browser cookie session (where actor.owner is False).
        device_auth_client.cookies.clear()
        device_auth_client.cookies.set(session_cookie_name(settings), member_cookie_token)
        member_csrf_headers = {"Origin": WEB_ORIGIN, "X-CSRF-Token": member_csrf_token}

        session_probe = device_auth_client.get("/api/v1/auth/session")
        assert session_probe.status_code == 200
        assert session_probe.json()["owner"] is False

        # Member lists only their own device sessions (m1, m2), never owner's device session.
        member_list = device_auth_client.get("/api/v1/auth/device-sessions")
        assert member_list.status_code == 200
        member_ids = {item["id"] for item in member_list.json()["items"]}
        assert member_ids == {m1_id, m2_id}
        assert owner_session_id not in member_ids

        # Member attempting to revoke owner's device session gets 404 (and owner's stays active).
        cross_from_member = device_auth_client.delete(
            f"/api/v1/auth/device-sessions/{owner_session_id}",
            headers=member_csrf_headers,
        )
        assert cross_from_member.status_code == 404

        # Member revokes one of their own devices (m1) via cookie + CSRF.
        revoke_m1 = device_auth_client.delete(
            f"/api/v1/auth/device-sessions/{m1_id}",
            headers=member_csrf_headers,
        )
        assert revoke_m1.status_code == 204

        # Clear cookies to test member Bearer calls.
        device_auth_client.cookies.clear()

        # Revoked m1 token is now rejected with 401.
        with pytest.raises(InvalidCredentialsError), Session(database_engine) as database:
            resolve_session(database, m1_token, settings, expected_transport="bearer")
        assert (
            device_auth_client.get(
                "/api/v1/auth/session",
                headers={"Authorization": f"Bearer {m1_token}"},
            ).status_code
            == 401
        )

        # Active m2 Bearer token lists member's remaining device with current=True.
        m2_headers = {"Authorization": f"Bearer {m2_token}", "Origin": NATIVE_ORIGIN}
        m2_list = device_auth_client.get("/api/v1/auth/device-sessions", headers=m2_headers)
        assert m2_list.status_code == 200
        assert [item["id"] for item in m2_list.json()["items"]] == [m2_id]
        assert m2_list.json()["items"][0]["current"] is True

        # Member revokes current device session (m2) via DELETE /device-sessions/current.
        revoke_current = device_auth_client.delete(
            "/api/v1/auth/device-sessions/current",
            headers=m2_headers,
        )
        assert revoke_current.status_code == 204
        assert device_auth_client.get("/api/v1/auth/session", headers=m2_headers).status_code == 401

        # Issue two more devices for member (m3, m4) and test member revoke-all.
        with Session(database_engine) as database, database.begin():
            member_row = database.scalars(select(User).where(User.login_name == "member")).one()
            m3 = _issue_device_session(database, member_row, "Member Phone 3", settings, utc_now())
            m4 = _issue_device_session(database, member_row, "Member Phone 4", settings, utc_now())
            m3_token, m4_token = m3.token, m4.token

        revoke_all = device_auth_client.delete(
            "/api/v1/auth/device-sessions",
            headers={"Authorization": f"Bearer {m3_token}", "Origin": NATIVE_ORIGIN},
        )
        assert revoke_all.status_code == 200
        assert revoke_all.json() == {"revoked_count": 2}

        for tok in (m3_token, m4_token):
            assert (
                device_auth_client.get(
                    "/api/v1/auth/session",
                    headers={"Authorization": f"Bearer {tok}"},
                ).status_code
                == 401
            )

        # Owner's device session is completely untouched and still active.
        owner_ok = device_auth_client.get(
            "/api/v1/auth/session",
            headers={"Authorization": f"Bearer {owner_device['token']}"},
        )
        assert owner_ok.status_code == 200
        assert owner_ok.json()["login_name"] == "owner"
    finally:
        app.dependency_overrides.pop(require_authenticated_actor, None)
        del monkeypatch


def test_concurrent_device_session_issuance_serializes_on_user_lock_and_enforces_cap(
    database_engine: Engine,
) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from florabase.auth.service import _issue_device_session, utc_now

    with database_engine.begin() as connection:
        connection.execute(delete(User))
        connection.execute(delete(LoginThrottle))

    settings = _settings(device_session_max_active=3)
    try:
        with Session(database_engine) as database, database.begin():
            owner = bootstrap_owner(database, "owner", PASSWORD, "Florabase Owner")
            owner_id = owner.id
            base_now = utc_now()
            for idx in range(3):
                _issue_device_session(
                    database,
                    owner,
                    f"Initial {idx}",
                    settings,
                    base_now + timedelta(seconds=idx),
                )

        barrier = Barrier(2)

        def issue_concurrent(idx: int) -> str:
            with Session(database_engine) as session, session.begin():
                user = session.get(User, owner_id)
                assert user is not None
                barrier.wait(timeout=10)
                issued = _issue_device_session(
                    session,
                    user,
                    f"Concurrent {idx}",
                    settings,
                    utc_now() + timedelta(minutes=1, seconds=idx),
                )
                return issued.token

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(issue_concurrent, 1), pool.submit(issue_concurrent, 2)]
            tokens = [future.result(timeout=15) for future in futures]
        assert len(tokens) == 2

        with Session(database_engine) as database:
            active_rows = list(
                database.scalars(
                    select(AuthSession).where(
                        AuthSession.user_id == owner_id,
                        AuthSession.transport == "bearer",
                        AuthSession.revoked_at.is_(None),
                    )
                ).all()
            )
            assert len(active_rows) == 3
            active_labels = {row.device_label for row in active_rows}
            assert "Concurrent 1" in active_labels
            assert "Concurrent 2" in active_labels
    finally:
        with database_engine.begin() as connection:
            connection.execute(delete(User))
            connection.execute(delete(LoginThrottle))


def test_device_sessions_migration_upgrade_downgrade_roundtrip(
    database_engine: Engine,
) -> None:
    config = Config("alembic.ini")
    with database_engine.begin() as conn:
        conn.execute(delete(User))
        conn.execute(delete(LoginThrottle))

    command.downgrade(config, "20261110_0047")
    try:
        with database_engine.connect() as conn:
            cols = {col["name"] for col in inspect(conn).get_columns("auth_sessions")}
            assert "transport" not in cols
            assert "device_label" not in cols

        command.upgrade(config, "head")

        def belongs_to_auth_sessions(
            obj: Any, name: str | None, type_: str, reflected: bool, compare_to: Any
        ) -> bool:
            if type_ == "table":
                return name == "auth_sessions"
            return getattr(getattr(obj, "table", None), "name", None) == "auth_sessions"

        with database_engine.connect() as conn:
            context = MigrationContext.configure(
                conn, opts={"include_object": belongs_to_auth_sessions}
            )
            assert compare_metadata(context, AuthSession.metadata) == []
            checks = {item["name"] for item in inspect(conn).get_check_constraints("auth_sessions")}
            assert "ck_auth_sessions_transport" in checks
            assert "ck_auth_sessions_transport_fields" in checks
            indexes = {item["name"] for item in inspect(conn).get_indexes("auth_sessions")}
            assert "ix_auth_sessions_user_transport" in indexes

        # Insert both cookie and bearer rows, then downgrade: bearer is removed, cookie stays.
        with Session(database_engine) as database, database.begin():
            bootstrap_owner(database, "owner", PASSWORD)
            database.flush()
            from florabase.auth.service import authenticate, authenticate_device

            authenticate(database, "owner", PASSWORD, _settings())
            authenticate_device(database, "owner", PASSWORD, "Test Device", _settings())

        command.downgrade(config, "20261110_0047")
        with database_engine.connect() as conn:
            remaining = conn.execute(text("SELECT count(*) FROM auth_sessions")).scalar_one()
            assert remaining == 1
            cols = {col["name"] for col in inspect(conn).get_columns("auth_sessions")}
            assert "transport" not in cols
            assert "device_label" not in cols

        command.upgrade(config, "head")
        with database_engine.connect() as conn:
            row = conn.execute(text("SELECT transport, device_label FROM auth_sessions")).one()
            assert row == ("cookie", None)
    finally:
        command.upgrade(config, "head")
        with database_engine.begin() as conn:
            conn.execute(delete(User))
            conn.execute(delete(LoginThrottle))
