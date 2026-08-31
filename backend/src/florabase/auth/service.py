import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert
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


class InvalidCredentialsError(Exception):
    pass


class LoginThrottledError(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after


class BootstrapError(Exception):
    pass


@dataclass(frozen=True)
class NewSession:
    user: User
    session: AuthSession
    session_token: str
    csrf_token: str


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

    database.execute(text("SELECT pg_advisory_xact_lock(677019539523289027)"))
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


def _locked_throttle(
    database: Session, login_name: str, now: datetime, settings: Settings
) -> LoginThrottle:
    database.execute(delete(LoginThrottle).where(LoginThrottle.expires_at <= now))
    database.execute(
        insert(LoginThrottle)
        .values(
            login_name=login_name,
            failed_attempts=0,
            expires_at=now + timedelta(seconds=settings.login_throttle_retention_seconds),
            updated_at=now,
        )
        .on_conflict_do_nothing(index_elements=[LoginThrottle.login_name])
    )
    return database.scalars(
        select(LoginThrottle)
        .where(LoginThrottle.login_name == login_name)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()


def _check_throttle(throttle: LoginThrottle, now: datetime) -> None:
    if throttle.backoff_until is not None and throttle.backoff_until > now:
        retry_after = max(1, int((throttle.backoff_until - now).total_seconds() + 0.999))
        raise LoginThrottledError(retry_after)


def _record_failure(throttle: LoginThrottle, now: datetime, settings: Settings) -> None:
    throttle.failed_attempts += 1
    if throttle.failed_attempts >= settings.login_failure_threshold:
        exponent = throttle.failed_attempts - settings.login_failure_threshold
        seconds = min(
            settings.login_backoff_base_seconds * (2**exponent), settings.login_backoff_max_seconds
        )
        throttle.backoff_until = now + timedelta(seconds=seconds)
    throttle.updated_at = now
    throttle.expires_at = now + timedelta(seconds=settings.login_throttle_retention_seconds)


def authenticate(
    database: Session, login_name: str, password: str, settings: Settings
) -> NewSession:
    try:
        normalized = normalize_login_name(login_name)
    except ValueError:
        normalized = "invalid-login-name"
    now = utc_now()
    throttle = _locked_throttle(database, normalized, now, settings)
    _check_throttle(throttle, now)
    user = database.scalars(select(User).where(User.login_name == normalized)).one_or_none()
    encoded = user.password_hash if user is not None else dummy_password_hash()
    valid, replacement = password_hasher().verify_and_update(password, encoded)
    if user is None or not valid or not user.enabled or not user.owner:
        _record_failure(throttle, now, settings)
        logger.warning("login_failed")
        raise InvalidCredentialsError

    if replacement is not None:
        user.password_hash = replacement
        user.password_changed_at = now
        revoke_user_sessions(database, user.id, now)
    database.delete(throttle)
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
    logger.info("login_succeeded user_id=%s session_id=%s", user.id, session.id)
    return NewSession(user=user, session=session, session_token=raw_session, csrf_token=raw_csrf)


def resolve_session(
    database: Session, raw_token: str, settings: Settings
) -> tuple[User, AuthSession]:
    now = utc_now()
    auth_session = database.scalars(
        select(AuthSession).where(AuthSession.token_digest == token_digest(raw_token))
    ).one_or_none()
    if (
        auth_session is None
        or auth_session.revoked_at is not None
        or auth_session.idle_expires_at <= now
        or auth_session.absolute_expires_at <= now
        or not auth_session.user.enabled
    ):
        raise InvalidCredentialsError
    touch_before = now - timedelta(seconds=settings.session_touch_interval_seconds)
    if auth_session.last_seen_at <= touch_before:
        auth_session.last_seen_at = now
        auth_session.idle_expires_at = min(
            now + timedelta(seconds=settings.session_idle_seconds),
            auth_session.absolute_expires_at,
        )
    return auth_session.user, auth_session


def verify_csrf(auth_session: AuthSession, raw_csrf: str) -> bool:
    return secrets.compare_digest(auth_session.csrf_digest, token_digest(raw_csrf))


def rotate_csrf(auth_session: AuthSession) -> str:
    raw_csrf = new_token()
    auth_session.csrf_digest = token_digest(raw_csrf)
    return raw_csrf


def revoke_session(
    database: Session, auth_session: AuthSession, now: datetime | None = None
) -> None:
    auth_session.revoked_at = now or utc_now()
    logger.info("session_revoked user_id=%s session_id=%s", auth_session.user_id, auth_session.id)


def revoke_user_sessions(database: Session, user_id: UUID, now: datetime | None = None) -> int:
    active_sessions = database.scalars(
        select(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .with_for_update()
    ).all()
    revoked_at = now or utc_now()
    for auth_session in active_sessions:
        auth_session.revoked_at = revoked_at
    return len(active_sessions)
