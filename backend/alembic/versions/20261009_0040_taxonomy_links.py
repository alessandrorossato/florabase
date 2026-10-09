"""Operator-confirmed WFO links; no canonical provider dataset.

Revision ID: 20261009_0040
Revises: 20261009_0039
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261009_0040"
down_revision: str | None = "20261009_0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wfo_links",
        sa.Column(
            "identity_id",
            sa.Uuid(),
            sa.ForeignKey("botanical_identities.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("version", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(14), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("external_id ~ '^wfo-[0-9]{10}$'", name="ck_wfo_link_external_id"),
        sa.CheckConstraint("jsonb_typeof(evidence) = 'object'", name="ck_wfo_link_evidence"),
    )


def downgrade() -> None:
    op.execute("LOCK TABLE wfo_links IN ACCESS EXCLUSIVE MODE")
    op.execute("""DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM wfo_links) THEN
        RAISE EXCEPTION 'Cannot downgrade with confirmed WFO links';
      END IF;
    END $$""")
    op.drop_table("wfo_links")
