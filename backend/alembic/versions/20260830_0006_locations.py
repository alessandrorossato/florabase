"""Add the hierarchical Location directory.

Revision ID: 20260830_0006
Revises: 20260830_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260830_0006"
down_revision: str | None = "20260830_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("char_length(name) BETWEEN 1 AND 255", name="ck_locations_name_length"),
        sa.CheckConstraint(
            "name = regexp_replace(btrim(name), '[[:space:]]+', ' ', 'g')",
            name="ck_locations_name_normalized",
        ),
        sa.CheckConstraint("name !~ '[[:cntrl:]]'", name="ck_locations_name_no_control"),
        sa.CheckConstraint(
            "parent_id IS NULL OR parent_id <> id", name="ck_locations_not_self_parent"
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["locations.id"],
            name=op.f("fk_locations_parent_id_locations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_locations")),
    )
    op.create_index(op.f("ix_locations_parent_id"), "locations", ["parent_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_locations_parent_id"), table_name="locations")
    op.drop_table("locations")
