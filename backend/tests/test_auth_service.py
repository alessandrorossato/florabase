from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid7

import pytest

from florabase.auth import service
from florabase.auth.model import AuthSession, LoginThrottle, User
from florabase.auth.service import (
    BootstrapError,
    InvalidCredentialsError,
    LoginThrottledError,
    authenticate,
    bootstrap_owner,
    resolve_session,
    revoke_session,
    revoke_user_sessions,
    verify_csrf,
)
from florabase.core.config import CookieMode, Environment, Settings


def settings() -> Settings:
    return Settings.model_validate(
        {
            "environment": Environment.TEST,
            "database_url": "postgresql+psycopg://unused",
            "canonical_origin": "https://florabase.example",
            "cookie_mode": CookieMode.SECURE,
            "login_failure_threshold": 3,
        }
    )


def user(now: datetime) -> User:
    return User(
        id=uuid7(),
        login_name="owner",
        display_name="Owner",
        password_hash="encoded",
        enabled=True,
        owner=True,
        password_changed_at=now,
        created_at=now,
        updated_at=now,
    )


def throttle(now: datetime) -> LoginThrottle:
    return LoginThrottle(
        login_name="owner",
        failed_attempts=0,
        expires_at=now + timedelta(days=1),
        updated_at=now,
    )


def scalar_result(**methods: object) -> MagicMock:
    result = MagicMock()
    for name, value in methods.items():
        getattr(result, name).return_value = value
    return result


def test_bootstrap_owner_policy_and_guard() -> None:
    database = MagicMock()
    database.scalar.return_value = None
    hasher = MagicMock()
    hasher.hash.return_value = "$argon2id$encoded"

    with patch("florabase.auth.service.password_hasher", return_value=hasher):
        owner = bootstrap_owner(database, " OWNER ", "correct horse battery staple", " Owner ")
    assert owner.login_name == "owner"
    assert owner.display_name == "Owner"
    database.add.assert_called_once_with(owner)
    database.flush.assert_called_once()

    database.scalar.return_value = uuid7()
    with pytest.raises(BootstrapError, match="already exists"):
        bootstrap_owner(database, "owner", "correct horse battery staple")
    with pytest.raises(ValueError, match="Display name"):
        bootstrap_owner(database, "owner", "correct horse battery staple", " ")


def test_throttle_policy_backoff_and_expiry() -> None:
    now = datetime.now(UTC)
    app_settings = settings()
    state = throttle(now)
    service._check_throttle(state, now)
    for _ in range(3):
        service._record_failure(state, now, app_settings)
    assert state.failed_attempts == 3
    assert state.backoff_until == now + timedelta(seconds=5)
    with pytest.raises(LoginThrottledError) as caught:
        service._check_throttle(state, now)
    assert caught.value.retry_after == 5


def test_authenticate_unknown_failure_and_success_paths() -> None:
    now = datetime.now(UTC)
    app_settings = settings()
    database = MagicMock()
    state = throttle(now)
    hasher = MagicMock()
    hasher.verify_and_update.return_value = (False, None)
    database.scalars.side_effect = [
        scalar_result(one=state),
        scalar_result(one_or_none=None),
    ]

    with (
        patch("florabase.auth.service.utc_now", return_value=now),
        patch("florabase.auth.service.password_hasher", return_value=hasher),
        patch("florabase.auth.service.dummy_password_hash", return_value="dummy"),
        pytest.raises(InvalidCredentialsError),
    ):
        authenticate(database, "unknown", "wrong", app_settings)
    assert state.failed_attempts == 1

    database.reset_mock()
    owner = user(now)
    state = throttle(now)
    hasher.verify_and_update.return_value = (True, "upgraded")
    database.scalars.side_effect = [
        scalar_result(one=state),
        scalar_result(one_or_none=owner),
        scalar_result(all=[]),
    ]
    with (
        patch("florabase.auth.service.utc_now", return_value=now),
        patch("florabase.auth.service.password_hasher", return_value=hasher),
    ):
        result = authenticate(database, "owner", "correct", app_settings)
    assert owner.password_hash == "upgraded"
    assert result.user is owner
    assert len(result.session.token_digest) == 32
    assert len(result.session.csrf_digest) == 32
    database.delete.assert_called_once_with(state)
    database.add.assert_called_once_with(result.session)


def test_resolve_session_expiry_touch_and_revocation_primitives() -> None:
    now = datetime.now(UTC)
    app_settings = settings()
    owner = user(now)
    auth_session = AuthSession(
        id=uuid7(),
        user_id=owner.id,
        token_digest=b"a" * 32,
        csrf_digest=b"b" * 32,
        created_at=now - timedelta(hours=1),
        last_seen_at=now - timedelta(minutes=6),
        idle_expires_at=now + timedelta(hours=1),
        absolute_expires_at=now + timedelta(days=1),
        user=owner,
    )
    database = MagicMock()
    database.scalars.return_value.one_or_none.return_value = auth_session

    with patch("florabase.auth.service.utc_now", return_value=now):
        resolved_user, resolved_session = resolve_session(database, "raw-token", app_settings)
    assert resolved_user is owner
    assert resolved_session.last_seen_at == now

    mutations: tuple[Callable[[], None], ...] = (
        lambda: setattr(auth_session, "revoked_at", now),
        lambda: setattr(auth_session, "idle_expires_at", now),
        lambda: setattr(auth_session, "absolute_expires_at", now),
        lambda: setattr(owner, "enabled", False),
    )
    for mutate in mutations:
        auth_session.revoked_at = None
        auth_session.idle_expires_at = now + timedelta(hours=1)
        auth_session.absolute_expires_at = now + timedelta(days=1)
        owner.enabled = True
        mutate()
        with (
            patch("florabase.auth.service.utc_now", return_value=now),
            pytest.raises(InvalidCredentialsError),
        ):
            resolve_session(database, "raw-token", app_settings)

    database.scalars.return_value.one_or_none.return_value = None
    with pytest.raises(InvalidCredentialsError):
        resolve_session(database, "raw-token", app_settings)

    assert verify_csrf(auth_session, "not-the-token") is False
    revoke_session(database, auth_session, now)
    assert auth_session.revoked_at == now
    database.scalars.return_value.all.return_value = [auth_session]
    auth_session.revoked_at = None
    assert revoke_user_sessions(database, owner.id, now) == 1
    assert auth_session.revoked_at == now
