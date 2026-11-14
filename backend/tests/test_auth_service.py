from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid7

import pytest

from florabase.auth import service
from florabase.auth.model import AuthSession, LoginThrottle, User
from florabase.auth.security import token_digest
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
        scalar_result(one_or_none=state),
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
        scalar_result(one_or_none=state),
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


def presenting_session(owner: User, now: datetime) -> AuthSession:
    return AuthSession(
        id=uuid7(),
        user=owner,
        user_id=owner.id,
        csrf_digest=token_digest("csrf-token"),
        revoked_at=None,
        last_seen_at=now - timedelta(hours=1),
        idle_expires_at=now + timedelta(hours=1),
        absolute_expires_at=now + timedelta(days=1),
    )


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        ("invalid_new", service.InvalidNewPasswordError),
        ("disabled", InvalidCredentialsError),
        ("non_owner", InvalidCredentialsError),
        ("missing_user", InvalidCredentialsError),
        ("missing_session", InvalidCredentialsError),
        ("foreign_session", InvalidCredentialsError),
        ("revoked", InvalidCredentialsError),
        ("idle_expiry", InvalidCredentialsError),
        ("absolute_expiry", InvalidCredentialsError),
        ("stale_csrf", service.SessionCsrfError),
        ("unicode_csrf", service.SessionCsrfError),
        ("backoff", LoginThrottledError),
        ("wrong_current", service.InvalidCurrentPasswordError),
        ("reuse", service.PasswordUnchangedError),
        ("expires_during_hash", InvalidCredentialsError),
        ("success", None),
    ],
)
def test_change_password_decisions(condition: str, expected: type[Exception] | None) -> None:
    now = datetime.now(UTC)
    owner = user(now)
    presenting = presenting_session(owner, now)
    already_revoked = presenting_session(owner, now)
    already_revoked.revoked_at = now - timedelta(days=1)
    other = presenting_session(owner, now)
    database = MagicMock()
    hasher = MagicMock()
    hasher.verify.return_value = condition != "wrong_current"
    hasher.hash.return_value = "replacement-hash"
    bucket = throttle(now) if condition in {"backoff", "success"} else None
    if condition == "backoff":
        assert bucket is not None
        bucket.backoff_until = now + timedelta(seconds=5)
    owner.enabled = condition != "disabled"
    owner.owner = condition != "non_owner"
    if condition == "foreign_session":
        presenting.user_id = uuid7()
    if condition == "revoked":
        presenting.revoked_at = now
    if condition == "idle_expiry":
        presenting.idle_expires_at = now
    if condition == "absolute_expiry":
        presenting.absolute_expires_at = now
    database.scalars.side_effect = [
        scalar_result(one_or_none=bucket),
        scalar_result(one_or_none=None if condition == "missing_user" else owner),
        scalar_result(
            all=[
                *([] if condition == "missing_session" else [presenting]),
                already_revoked,
                other,
            ]
        ),
    ]
    current = "current synthetic password"
    new = current if condition == "reuse" else "new synthetic password"
    if condition == "invalid_new":
        new = "short"
    csrf = {"stale_csrf": "stale", "unicode_csrf": "é"}.get(condition, "csrf-token")
    clock = [now, presenting.idle_expires_at if condition == "expires_during_hash" else now]
    with (
        patch.object(service, "utc_now", side_effect=clock),
        patch.object(service, "password_hasher", return_value=hasher) as get_hasher,
    ):
        if expected is None:
            result = service.change_password(database, presenting, csrf, current, new, settings())
            assert result.user is owner
            assert result.session.user_id == owner.id
            assert result.session.token_digest == token_digest(result.session_token)
            assert result.session.csrf_digest == token_digest(result.csrf_token)
            assert owner.password_hash == "replacement-hash"
            assert owner.updated_at == owner.password_changed_at == now
            assert presenting.revoked_at == other.revoked_at == now
            database.delete.assert_called_once_with(bucket)
            database.add.assert_called_once_with(result.session)
        else:
            with pytest.raises(expected):
                service.change_password(database, presenting, csrf, current, new, settings())
            assert owner.password_hash == "encoded"
            assert other.revoked_at is None
            database.delete.assert_not_called()
            if condition == "wrong_current":
                saved_bucket = database.add.call_args.args[0]
                assert saved_bucket.login_name == f"pwchg:{owner.id}"
                assert saved_bucket.failed_attempts == 1
            else:
                database.add.assert_not_called()
            if condition not in {"wrong_current", "reuse", "expires_during_hash"}:
                get_hasher.assert_not_called()
            if condition in {"wrong_current", "reuse"}:
                hasher.hash.assert_not_called()
    assert already_revoked.revoked_at == now - timedelta(days=1)
    if condition == "invalid_new":
        database.execute.assert_not_called()
    else:
        assert database.expire.call_count == 2
        database.expire.assert_any_call(presenting)
        database.expire.assert_any_call(owner)


@pytest.mark.parametrize("condition", ["active", "missing", "disabled", "revoked"])
def test_lock_presenting_session_rechecks_database_results(condition: str) -> None:
    now = datetime.now(UTC)
    owner = user(now)
    initial = presenting_session(owner, now)
    refreshed = presenting_session(owner, now)
    refreshed.id = initial.id
    owner.enabled = condition != "disabled"
    if condition == "revoked":
        refreshed.revoked_at = now
    database = MagicMock()
    database.scalars.side_effect = [
        scalar_result(one_or_none=None if condition == "missing" else refreshed),
        scalar_result(one_or_none=owner),
    ]
    with patch.object(service, "utc_now", return_value=now):
        if condition == "active":
            locked = service.lock_presenting_session(database, initial, "csrf-token")
            assert locked is refreshed
            token = service.rotate_csrf(locked, settings())
            assert locked.csrf_digest == token_digest(token)
            assert locked.last_seen_at == now
        else:
            with pytest.raises(InvalidCredentialsError):
                service.lock_presenting_session(database, initial)
    assert database.expire.call_count == 2


@pytest.mark.parametrize(
    "condition",
    [
        "no_users",
        "multiple_users",
        "other_login",
        "disabled",
        "changed_login",
        "missing_locked_user",
        "non_owner",
        "success",
        "no_throttles",
    ],
)
def test_offline_reset_requires_matching_enabled_single_owner(condition: str) -> None:
    now = datetime.now(UTC)
    owner = user(now)
    session = presenting_session(owner, now)
    database = MagicMock()
    candidate = MagicMock(id=owner.id, login_name="owner")
    if condition == "other_login":
        candidate.login_name = "other"
    candidates = {"no_users": [], "multiple_users": [candidate, candidate]}
    database.execute.return_value.all.return_value = candidates.get(condition, [candidate])
    owner.enabled = condition != "disabled"
    owner.owner = condition != "non_owner"
    if condition == "changed_login":
        owner.login_name = "other"
    public = throttle(now)
    private = throttle(now)
    private.login_name = f"pwchg:{owner.id}"
    database.scalars.side_effect = [
        scalar_result(one_or_none=None if condition == "no_throttles" else public),
        scalar_result(one_or_none=None if condition == "no_throttles" else private),
        scalar_result(one_or_none=None if condition == "missing_locked_user" else owner),
        scalar_result(all=[session]),
    ]
    hasher = MagicMock()
    hasher.hash.return_value = "reset-hash"
    password = "synthetic reset password"
    with (
        patch.object(service, "utc_now", return_value=now),
        patch.object(service, "password_hasher", return_value=hasher),
    ):
        if condition in {"success", "no_throttles"}:
            service.reset_owner_password(database, "owner", password)
            hasher.hash.assert_called_once_with(password)
            hasher.verify.assert_not_called()
            assert owner.password_hash == "reset-hash"
            assert owner.updated_at == owner.password_changed_at == now
            assert session.revoked_at == now
            if condition == "success":
                assert [entry.args[0] for entry in database.delete.call_args_list] == [
                    public,
                    private,
                ]
            else:
                database.delete.assert_not_called()
        else:
            with pytest.raises(service.PasswordResetRefusedError):
                service.reset_owner_password(database, "owner", password)
            hasher.hash.assert_not_called()
            assert owner.password_hash == "encoded"
            assert session.revoked_at is None
            database.delete.assert_not_called()
    database.add.assert_not_called()


def test_expired_throttle_discards_previous_backoff_and_counter() -> None:
    now = datetime.now(UTC)
    bucket = throttle(now)
    bucket.expires_at = now
    bucket.backoff_until = now + timedelta(minutes=10)
    bucket.failed_attempts = 20
    service._check_throttle(bucket, now)
    service._record_failure(bucket, now, settings())
    assert bucket.failed_attempts == 1
    assert bucket.backoff_until is None
    assert bucket.expires_at > now


def test_login_with_current_hash_issues_session_without_rehashing() -> None:
    now = datetime.now(UTC)
    owner = user(now - timedelta(days=1))
    previous_change = owner.password_changed_at
    database = MagicMock()
    database.scalars.side_effect = [
        scalar_result(one_or_none=None),
        scalar_result(one_or_none=owner),
    ]
    hasher = MagicMock()
    hasher.verify_and_update.return_value = (True, None)
    with (
        patch.object(service, "utc_now", return_value=now),
        patch.object(service, "password_hasher", return_value=hasher),
    ):
        result = authenticate(database, "owner", "synthetic password", settings())
    assert owner.password_hash == "encoded"
    assert owner.password_changed_at == previous_change
    assert result.session.created_at == now
    assert result.session.user_id == owner.id
    database.delete.assert_not_called()
    database.add.assert_called_once_with(result.session)


def test_login_with_malformed_name_verifies_dummy_hash_and_records_failure() -> None:
    now = datetime.now(UTC)
    database = MagicMock()
    database.scalars.return_value.one_or_none.return_value = None
    hasher = MagicMock()
    hasher.verify_and_update.return_value = (False, None)
    with (
        patch.object(service, "utc_now", return_value=now),
        patch.object(service, "password_hasher", return_value=hasher),
        patch.object(service, "dummy_password_hash", return_value="dummy"),
        pytest.raises(InvalidCredentialsError),
    ):
        authenticate(database, "invalid name!", "synthetic password", settings())
    hasher.verify_and_update.assert_called_once_with("synthetic password", "dummy")
    bucket = database.add.call_args.args[0]
    assert bucket.login_name == "invalid-login-name"
    assert bucket.failed_attempts == 1
