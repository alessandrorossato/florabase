"""Owner-private named operator views; no result or application-state snapshots.

Revision ID: 20261006_0034
Revises: 20261005_0033
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261006_0034"
down_revision: str | None = "20261005_0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "saved_views",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "owner_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("surface", sa.String(32), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("state", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "char_length(name) BETWEEN 1 AND 120", name="ck_saved_views_name_length"
        ),
        sa.CheckConstraint(
            "name = btrim(name) AND name !~ '[[:cntrl:]]'", name="ck_saved_views_name"
        ),
        sa.CheckConstraint(
            "surface IN ('global_search', 'seed_lots', 'sowings', 'plants', 'harvests', "
            "'stored_material', 'events', 'media', 'botanical_identities', 'suppliers', "
            "'locations', 'geography', 'provenance_map')",
            name="ck_saved_views_surface",
        ),
        sa.CheckConstraint("state_version >= 1", name="ck_saved_views_version"),
        sa.CheckConstraint(
            "jsonb_typeof(state) = 'object' AND octet_length(state::text) <= 8192",
            name="ck_saved_views_state",
        ),
    )
    op.create_index(
        "uq_saved_views_owner_surface_name_ci",
        "saved_views",
        ["owner_id", "surface", sa.text("lower(name)")],
        unique=True,
    )


def downgrade() -> None:
    # Follow the repository's populated-history refusal before destructive DDL.
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM saved_views)")):
        raise RuntimeError("Saved Views exist; delete them explicitly before downgrade.")
    op.drop_table("saved_views")
