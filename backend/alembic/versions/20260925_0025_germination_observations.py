"""Add dated germination observations.

Revision ID: 20260925_0025
Revises: 20260913_0024
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260925_0025"
down_revision: str | None = "20260913_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "germination_observations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "sowing_id",
            sa.Uuid(),
            sa.ForeignKey("sowings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("observed_on", sa.Date(), nullable=False),
        sa.Column("newly_germinated_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("newly_germinated_count >= 0", name="ck_germination_observations_count"),
        sa.UniqueConstraint(
            "sowing_id", "observed_on", name="uq_germination_observations_sowing_date"
        ),
    )


def downgrade() -> None:
    op.drop_table("germination_observations")
