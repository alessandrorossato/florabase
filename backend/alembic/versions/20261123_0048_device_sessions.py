"""Extend auth_sessions for opaque Bearer device sessions (MOBILE-002).

Revision ID: 20261123_0048
Revises: 20261110_0047
Create Date: 2026-11-23 12:15:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261123_0048"
down_revision: str | None = "20261110_0047"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_auth_sessions_csrf_digest", "auth_sessions", type_="check")
    op.alter_column(
        "auth_sessions",
        "csrf_digest",
        existing_type=sa.LargeBinary(length=32),
        nullable=True,
    )
    op.add_column(
        "auth_sessions",
        sa.Column("transport", sa.String(length=16), nullable=False, server_default="cookie"),
    )
    op.add_column(
        "auth_sessions",
        sa.Column("device_label", sa.String(length=120), nullable=True),
    )
    op.create_check_constraint(
        "ck_auth_sessions_transport",
        "auth_sessions",
        "transport IN ('cookie', 'bearer')",
    )
    op.create_check_constraint(
        "ck_auth_sessions_transport_fields",
        "auth_sessions",
        "(transport = 'cookie' AND csrf_digest IS NOT NULL "
        "AND octet_length(csrf_digest) = 32 AND device_label IS NULL) OR "
        "(transport = 'bearer' AND csrf_digest IS NULL "
        "AND device_label IS NOT NULL AND char_length(device_label) BETWEEN 1 AND 120)",
    )
    op.create_index(
        "ix_auth_sessions_user_transport",
        "auth_sessions",
        ["user_id", "transport", "revoked_at"],
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM auth_sessions WHERE transport = 'bearer'"))
    op.drop_index("ix_auth_sessions_user_transport", table_name="auth_sessions")
    op.drop_constraint("ck_auth_sessions_transport_fields", "auth_sessions", type_="check")
    op.drop_constraint("ck_auth_sessions_transport", "auth_sessions", type_="check")
    op.drop_column("auth_sessions", "device_label")
    op.drop_column("auth_sessions", "transport")
    op.alter_column(
        "auth_sessions",
        "csrf_digest",
        existing_type=sa.LargeBinary(length=32),
        nullable=False,
    )
    op.create_check_constraint(
        "ck_auth_sessions_csrf_digest",
        "auth_sessions",
        "octet_length(csrf_digest) = 32",
    )
