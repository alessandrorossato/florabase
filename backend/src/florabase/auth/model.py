from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from florabase.botanical_identities.model import utc_now
from florabase.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "login_name ~ '^[a-z0-9][a-z0-9._-]{2,63}$'",
            name="ck_users_login_name_normalized",
        ),
        CheckConstraint(
            "display_name IS NULL OR char_length(display_name) BETWEEN 1 AND 120",
            name="ck_users_display_name_length",
        ),
        CheckConstraint("owner", name="ck_users_initial_owner_only"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    login_name: Mapped[str] = mapped_column(String(64), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    password_hash: Mapped[str] = mapped_column(Text())
    enabled: Mapped[bool] = mapped_column(Boolean(), default=True)
    owner: Mapped[bool] = mapped_column(Boolean(), default=True)
    password_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    sessions: Mapped[list[AuthSession]] = relationship(back_populates="user")


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        CheckConstraint("octet_length(token_digest) = 32", name="ck_auth_sessions_token_digest"),
        CheckConstraint("octet_length(csrf_digest) = 32", name="ck_auth_sessions_csrf_digest"),
        CheckConstraint("last_seen_at >= created_at", name="ck_auth_sessions_seen_after_create"),
        CheckConstraint(
            "idle_expires_at <= absolute_expires_at", name="ck_auth_sessions_idle_limit"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_digest: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True)
    csrf_digest: Mapped[bytes] = mapped_column(LargeBinary(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    idle_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user: Mapped[User] = relationship(back_populates="sessions")


Index("ix_auth_sessions_user_id", AuthSession.user_id)
Index("ix_auth_sessions_expiry", AuthSession.absolute_expires_at, AuthSession.idle_expires_at)
Index("ix_auth_sessions_revoked_at", AuthSession.revoked_at)


class LoginThrottle(Base):
    __tablename__ = "login_throttles"
    __table_args__ = (
        CheckConstraint("failed_attempts >= 0", name="ck_login_throttles_failed_attempts"),
    )

    login_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    failed_attempts: Mapped[int] = mapped_column(Integer(), default=0)
    backoff_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


Index("ix_login_throttles_expires_at", LoginThrottle.expires_at)
