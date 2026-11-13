import logging
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, or_, select, text
from sqlalchemy.orm import Session

from florabase.auth.model import AuthSession, LoginThrottle, User
from florabase.auth.security import (
    dummy_password_hash,
    new_token,
    normalize_login_name,
    password_hasher,
    token_digest,
    validate_password,
)
from florabase.core.config import Settings

logger = logging.getLogger(__name__)

BOOTSTRAP_LOCK = 677019539523289027
LOGIN_THROTTLE_NAMESPACE = 1179406670
PASSWORD_CHANGE_THROTTLE_NAMESPACE = 1179406671
PASSWORD_CHANGE_KEY_PREFIX = "pwchg:"


class InvalidCredentialsError(Exception):
    pass


class LoginThrottledError(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after


class BootstrapError(Exception):
    pass


class PasswordResetRefusedError(Exception):
    pass


class PasswordUnchangedError(Exception):
    pass


class InvalidCurrentPasswordError(Exception):
    pass


class InvalidNewPasswordError(Exception):
    pass


class SessionCsrfError(Exception):
    pass


@dataclass(frozen=True)
class NewSession:
    user: User
    session: AuthSession
    session_token: str = field(repr=False)
    csrf_token: str = field(repr=False)


def utc_now() -> datetime:
    return datetime.now(UTC)


def bootstrap_owner(
    database: Session, login_name: str, password: str, display_name: str | None = None
) -> User:
    normalized = normalize_login_name(login_name)
    validated_password = validate_password(password)
    normalized_display = display_name.strip() if display_name is not None else None
    if normalized_display == "" or (
        normalized_display is not None and len(normalized_display) > 120
    ):
        raise ValueError("Display name must be between 1 and 120 characters")

    lock_bootstrap(database)
    if database.scalar(select(User.id).limit(1)) is not None:
        raise BootstrapError("An owner account already exists")
    now = utc_now()
    owner = User(
        login_name=normalized,
        display_name=normalized_display,
        password_hash=password_hasher().hash(validated_password),
        enabled=True,
        owner=True,
        password_changed_at=now,
        created_at=now,
        updated_at=now,
    )
    database.add(owner)
    database.flush()
    logger.info("owner_bootstrap_succeeded user_id=%s", owner.id)
    return owner


def lock_bootstrap(database: Session) -> None:
    database.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": BOOTSTRAP_LOCK})


def set_auth_timeouts(database: Session) -> None:
    database.execute(text("SET LOCAL lock_timeout = '5s'"))
    database.execute(text("SET LOCAL statement_timeout = '15s'"))


def _lock_throttle_key(database: Session, namespace: int, key: str) -> None:
    database.execute(
        text("SELECT pg_advisory_xact_lock(:namespace, hashtext(:key))"),
        {"namespace": namespace, "key": key},
    )


def _locked_throttle(database: Session, key: str) -> LoginThrottle | None:
    return database.scalars(
        select(LoginThrottle)
        .where(LoginThrottle.login_name == key)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one_or_none()


def _prune_login_throttles(database: Session, key: str, now: datetime) -> None:
    expired = (
        select(LoginThrottle.login_name)
        .where(
            LoginThrottle.expires_at <= now,
            LoginThrottle.login_name != key,
            ~LoginThrottle.login_name.startswith(PASSWORD_CHANGE_KEY_PREFIX),
        )
        .order_by(LoginThrottle.expires_at, LoginThrottle.login_name)
        .limit(32)
        .with_for_update(skip_locked=True)
        .cte("expired_login_throttles")
    )
    database.execute(
        delete(LoginThrottle)
        .where(LoginThrottle.login_name.in_(select(expired.c.login_name)))
        .execution_options(synchronize_session=False)
    )


def _check_throttle(throttle: LoginThrottle | None, now: datetime) -> None:
    if (
        throttle is not None
        and throttle.expires_at > now
        and throttle.backoff_until is not None
        and throttle.backoff_until > now
    ):
        retry_after = max(1, int((throttle.backoff_until - now).total_seconds() + 0.999))
        raise LoginThrottledError(retry_after)


def _record_failure(throttle: LoginThrottle, now: datetime, settings: Settings) -> None:
    if throttle.expires_at <= now:
        throttle.failed_attempts = 0
        throttle.backoff_until = None
    throttle.failed_attempts = min(throttle.failed_attempts + 1, 2_147_483_647)
    if throttle.failed_attempts >= settings.login_failure_threshold:
        exponent = min(throttle.failed_attempts - settings.login_failure_threshold, 12)
        seconds = min(
            settings.login_backoff_base_seconds * (2**exponent), settings.login_backoff_max_seconds
        )
        throttle.backoff_until = now + timedelta(seconds=seconds)
    throttle.updated_at = now
    throttle.expires_at = now + timedelta(seconds=settings.login_throttle_retention_seconds)


def _record_bucket_failure(
    database: Session, key: str, throttle: LoginThrottle | None, now: datetime, settings: Settings
) -> None:
    if throttle is None:
        throttle = LoginThrottle(login_name=key, failed_attempts=0, expires_at=now, updated_at=now)
        database.add(throttle)
    _record_failure(throttle, now, settings)


def _locked_user(database: Session, *, user_id: UUID | None = None, login: str = "") -> User | None:
    condition = User.id == user_id if user_id is not None else User.login_name == login
    return database.scalars(
        select(User)
        .where(condition)
        .with_for_update(key_share=True, of=User)
        .execution_options(populate_existing=True)
    ).one_or_none()


def _replace_password(user: User, encoded: str, now: datetime) -> None:
    user.password_hash = encoded
    user.password_changed_at = now
    user.updated_at = now


def _issue_session(database: Session, user: User, settings: Settings, now: datetime) -> NewSession:
    raw_session = new_token()
    raw_csrf = new_token()
    absolute_expiry = now + timedelta(seconds=settings.session_absolute_seconds)
    session = AuthSession(
        user_id=user.id,
        token_digest=token_digest(raw_session),
        csrf_digest=token_digest(raw_csrf),
        created_at=now,
        last_seen_at=now,
        idle_expires_at=now + timedelta(seconds=settings.session_idle_seconds),
        absolute_expires_at=absolute_expiry,
    )
    database.add(session)
    database.flush()
    return NewSession(user=user, session=session, session_token=raw_session, csrf_token=raw_csrf)


def authenticate(
    database: Session, login_name: str, password: str, settings: Settings
) -> NewSession:
    try:
        normalized = normalize_login_name(login_name)
    except ValueError:
        normalized = "invalid-login-name"
    set_auth_timeouts(database)
    _lock_throttle_key(database, LOGIN_THROTTLE_NAMESPACE, normalized)
    throttle = _locked_throttle(database, normalized)
    _check_throttle(throttle, utc_now())
    user = _locked_user(database, login=normalized)
    encoded = user.password_hash if user is not None else dummy_password_hash()
    valid, replacement = password_hasher().verify_and_update(password, encoded)
    if user is None or not valid or not user.enabled or not user.owner:
        now = utc_now()
        _record_bucket_failure(database, normalized, throttle, now, settings)
        database.flush()
        _prune_login_throttles(database, normalized, now)
        raise InvalidCredentialsError

    if replacement is not None:
        sessions = _locked_user_sessions(database, user.id)
        now = utc_now()
        _replace_password(user, replacement, now)
        _revoke_sessions(sessions, now)
    else:
        now = utc_now()
    if throttle is not None:
        database.delete(throttle)
    result = _issue_session(database, user, settings, now)
    _prune_login_throttles(database, normalized, now)
    return result


def _active_session(session: AuthSession, now: datetime) -> bool:
    return (
        session.revoked_at is None
        and session.idle_expires_at > now
        and session.absolute_expires_at > now
    )


def _touch_session(session: AuthSession, settings: Settings, now: datetime) -> None:
    if session.last_seen_at <= now - timedelta(seconds=settings.session_touch_interval_seconds):
        session.last_seen_at = now
        session.idle_expires_at = min(
            now + timedelta(seconds=settings.session_idle_seconds), session.absolute_expires_at
        )


def _expire_presenting_session(database: Session, session: AuthSession) -> tuple[UUID, UUID]:
    session_id, user_id, user = session.id, session.user_id, session.user
    database.expire(session)
    database.expire(user)
    return session_id, user_id


def _recheck_session(
    user: User | None, session: AuthSession | None, now: datetime, csrf: str | None = None
) -> tuple[User, AuthSession]:
    if (
        user is None
        or not user.enabled
        or not user.owner
        or session is None
        or session.user_id != user.id
        or not _active_session(session, now)
    ):
        raise InvalidCredentialsError
    if csrf is not None and (not csrf.isascii() or not verify_csrf(session, csrf)):
        raise SessionCsrfError
    return user, session


def lock_presenting_session(
    database: Session, presenting: AuthSession, csrf: str | None = None
) -> AuthSession:
    with database.no_autoflush:
        session_id, user_id = _expire_presenting_session(database, presenting)
        set_auth_timeouts(database)
        session = database.scalars(
            select(AuthSession)
            .where(AuthSession.id == session_id, AuthSession.user_id == user_id)
            .with_for_update(of=AuthSession)
            .execution_options(populate_existing=True)
        ).one_or_none()
        user = database.scalars(
            select(User).where(User.id == user_id).execution_options(populate_existing=True)
        ).one_or_none()
        return _recheck_session(user, session, utc_now(), csrf)[1]


def change_password(
    database: Session,
    presenting: AuthSession,
    csrf: str,
    current: str,
    new: str,
    settings: Settings,
) -> NewSession:
    try:
        validate_password(new)
    except ValueError as error:
        raise InvalidNewPasswordError from error

    with database.no_autoflush:
        session_id, user_id = _expire_presenting_session(database, presenting)
        set_auth_timeouts(database)
        key = f"{PASSWORD_CHANGE_KEY_PREFIX}{user_id}"
        _lock_throttle_key(database, PASSWORD_CHANGE_THROTTLE_NAMESPACE, key)
        throttle = _locked_throttle(database, key)
        locked_user = _locked_user(database, user_id=user_id)
        sessions = _locked_user_sessions(database, user_id, session_id)
        session = next((row for row in sessions if row.id == session_id), None)
        now = utc_now()
        user, session = _recheck_session(locked_user, session, now, csrf)
        _check_throttle(throttle, now)

    hasher = password_hasher()
    if not hasher.verify(current, user.password_hash):
        now = utc_now()
        _recheck_session(user, session, now, csrf)
        _record_bucket_failure(database, key, throttle, now, settings)
        raise InvalidCurrentPasswordError
    if secrets.compare_digest(current.encode("utf-8"), new.encode("utf-8")):
        _recheck_session(user, session, utc_now(), csrf)
        raise PasswordUnchangedError

    encoded = hasher.hash(new)
    now = utc_now()
    _recheck_session(user, session, now, csrf)
    _replace_password(user, encoded, now)
    _revoke_sessions(sessions, now)
    if throttle is not None:
        database.delete(throttle)
    return _issue_session(database, user, settings, now)


def reset_owner_password(database: Session, login: str, password: str) -> None:
    lock_bootstrap(database)
    candidates = database.execute(select(User.id, User.login_name).limit(2)).all()
    if len(candidates) != 1 or candidates[0].login_name != login:
        raise PasswordResetRefusedError
    user_id = candidates[0].id
    key = f"{PASSWORD_CHANGE_KEY_PREFIX}{user_id}"
    _lock_throttle_key(database, LOGIN_THROTTLE_NAMESPACE, login)
    _lock_throttle_key(database, PASSWORD_CHANGE_THROTTLE_NAMESPACE, key)
    login_throttle = _locked_throttle(database, login)
    change_throttle = _locked_throttle(database, key)
    user = _locked_user(database, user_id=user_id)
    if user is None or user.login_name != login or not user.owner or not user.enabled:
        raise PasswordResetRefusedError
    sessions = _locked_user_sessions(database, user.id)
    encoded = password_hasher().hash(validate_password(password))
    now = utc_now()
    _replace_password(user, encoded, now)
    _revoke_sessions(sessions, now)
    for throttle in (login_throttle, change_throttle):
        if throttle is not None:
            database.delete(throttle)


def resolve_session(
    database: Session, raw_token: str, settings: Settings
) -> tuple[User, AuthSession]:
    now = utc_now()
    auth_session = database.scalars(
        select(AuthSession).where(AuthSession.token_digest == token_digest(raw_token))
    ).one_or_none()
    if (
        auth_session is None
        or not _active_session(auth_session, now)
        or not auth_session.user.enabled
    ):
        raise InvalidCredentialsError
    _touch_session(auth_session, settings, now)
    return auth_session.user, auth_session


def verify_csrf(auth_session: AuthSession, raw_csrf: str) -> bool:
    return secrets.compare_digest(auth_session.csrf_digest, token_digest(raw_csrf))


def rotate_csrf(auth_session: AuthSession, settings: Settings | None = None) -> str:
    if settings is not None:
        _touch_session(auth_session, settings, utc_now())
    raw_csrf = new_token()
    auth_session.csrf_digest = token_digest(raw_csrf)
    return raw_csrf


def revoke_session(
    database: Session, auth_session: AuthSession, now: datetime | None = None
) -> None:
    auth_session.revoked_at = now or utc_now()


def _locked_user_sessions(
    database: Session, user_id: UUID, presenting_id: UUID | None = None
) -> list[AuthSession]:
    active = AuthSession.revoked_at.is_(None)
    condition = active if presenting_id is None else or_(active, AuthSession.id == presenting_id)
    return list(
        database.scalars(
            select(AuthSession)
            .where(AuthSession.user_id == user_id, condition)
            .order_by(AuthSession.id)
            .with_for_update(of=AuthSession)
            .execution_options(populate_existing=True)
        ).all()
    )


def _revoke_sessions(sessions: list[AuthSession], now: datetime) -> None:
    for session in sessions:
        if session.revoked_at is None:
            session.revoked_at = now


def revoke_user_sessions(database: Session, user_id: UUID, now: datetime | None = None) -> int:
    sessions = _locked_user_sessions(database, user_id)
    _revoke_sessions(sessions, now or utc_now())
    return len(sessions)
