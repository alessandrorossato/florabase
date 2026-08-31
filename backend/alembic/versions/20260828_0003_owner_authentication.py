"""Create local owner authentication persistence.

Revision ID: 20260828_0003
Revises: 20260828_0002
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260828_0003"
down_revision: str | None = "20260828_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("login_name", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("owner", sa.Boolean(), nullable=False),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("owner", name="ck_users_initial_owner_only"),
        sa.CheckConstraint(
            "login_name ~ '^[a-z0-9][a-z0-9._-]{2,63}$'",
            name="ck_users_login_name_normalized",
        ),
        sa.CheckConstraint(
            "display_name IS NULL OR char_length(display_name) BETWEEN 1 AND 120",
            name="ck_users_display_name_length",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("login_name", name=op.f("uq_users_login_name")),
    )
    op.create_table(
        "login_throttles",
        sa.Column("login_name", sa.String(length=64), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), nullable=False),
        sa.Column("backoff_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("failed_attempts >= 0", name="ck_login_throttles_failed_attempts"),
        sa.PrimaryKeyConstraint("login_name", name=op.f("pk_login_throttles")),
    )
    op.create_index(
        "ix_login_throttles_expires_at", "login_throttles", ["expires_at"], unique=False
    )
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_digest", sa.LargeBinary(length=32), nullable=False),
        sa.Column("csrf_digest", sa.LargeBinary(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idle_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("absolute_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("octet_length(csrf_digest) = 32", name="ck_auth_sessions_csrf_digest"),
        sa.CheckConstraint(
            "idle_expires_at <= absolute_expires_at", name="ck_auth_sessions_idle_limit"
        ),
        sa.CheckConstraint("last_seen_at >= created_at", name="ck_auth_sessions_seen_after_create"),
        sa.CheckConstraint("octet_length(token_digest) = 32", name="ck_auth_sessions_token_digest"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_auth_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_sessions")),
        sa.UniqueConstraint("token_digest", name=op.f("uq_auth_sessions_token_digest")),
    )
    op.create_index(
        "ix_auth_sessions_expiry",
        "auth_sessions",
        ["absolute_expires_at", "idle_expires_at"],
        unique=False,
    )
    op.create_index("ix_auth_sessions_revoked_at", "auth_sessions", ["revoked_at"], unique=False)
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_revoked_at", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_expiry", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index("ix_login_throttles_expires_at", table_name="login_throttles")
    op.drop_table("login_throttles")
    op.drop_table("users")
