"""Add the reusable Supplier directory.

Revision ID: 20260830_0005
Revises: 20260829_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260830_0005"
down_revision: str | None = "20260829_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("website", sa.String(length=2048), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("char_length(name) BETWEEN 1 AND 255", name="ck_suppliers_name_length"),
        sa.CheckConstraint(
            "name = regexp_replace(btrim(name), '[[:space:]]+', ' ', 'g')",
            name="ck_suppliers_name_normalized",
        ),
        sa.CheckConstraint("name !~ '[[:cntrl:]]'", name="ck_suppliers_name_no_control"),
        sa.CheckConstraint(
            "kind IN ('seller', 'nursery', 'supermarket', 'person', 'exchange', 'other')",
            name="ck_suppliers_kind",
        ),
        sa.CheckConstraint(
            "website IS NULL OR (char_length(website) BETWEEN 1 AND 2048 AND website ~ '^https?://')",
            name="ck_suppliers_website",
        ),
        sa.CheckConstraint(
            "email IS NULL OR (char_length(email) BETWEEN 3 AND 320 AND email = btrim(email) "
            "AND email !~ '[[:space:][:cntrl:]]' AND email ~ '^[^@]+@[^@]+$')",
            name="ck_suppliers_email",
        ),
        sa.CheckConstraint(
            "phone IS NULL OR (char_length(phone) BETWEEN 1 AND 120 AND phone = "
            "regexp_replace(btrim(phone), '[[:space:]]+', ' ', 'g') AND phone !~ '[[:cntrl:]]')",
            name="ck_suppliers_phone",
        ),
        sa.CheckConstraint(
            "notes IS NULL OR (char_length(notes) BETWEEN 1 AND 20000 AND notes = btrim(notes) "
            "AND regexp_replace(notes, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
            name="ck_suppliers_notes",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_suppliers")),
    )


def downgrade() -> None:
    op.drop_table("suppliers")
