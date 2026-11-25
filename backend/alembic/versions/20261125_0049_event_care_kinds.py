"""Add watering and feeding Event kinds and nullable Event batch_id.

Revision ID: 20261125_0049
Revises: 20261123_0048
"""

import sqlalchemy as sa

from alembic import op

revision = "20261125_0049"
down_revision = "20261123_0048"
branch_labels = None
depends_on = None

_OLD_KINDS = (
    "'observation', 'movement', 'repotting', 'flowering', 'fruiting', 'pruning', 'treatment', "
    "'harvest', 'extraction', 'reintegration', 'transfer', 'death', 'loss', 'discarded', "
    "'other', 'measurement'"
)
_NEW_KINDS = f"{_OLD_KINDS}, 'watering', 'feeding'"


def upgrade() -> None:
    op.execute("LOCK TABLE events IN ACCESS EXCLUSIVE MODE")
    op.drop_constraint("ck_events_kind", "events", type_="check")
    op.create_check_constraint("ck_events_kind", "events", f"kind IN ({_NEW_KINDS})")
    op.add_column("events", sa.Column("batch_id", sa.Uuid(), nullable=True))
    op.create_index(
        "ix_events_batch_id",
        "events",
        ["batch_id"],
        postgresql_where=sa.text("batch_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.execute("LOCK TABLE events IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM events WHERE kind IN ('watering', 'feeding'))")
    ):
        raise RuntimeError(
            "Watering or feeding Events exist; delete them explicitly before downgrade."
        )
    op.drop_index("ix_events_batch_id", table_name="events")
    op.drop_column("events", "batch_id")
    op.drop_constraint("ck_events_kind", "events", type_="check")
    op.create_check_constraint("ck_events_kind", "events", f"kind IN ({_OLD_KINDS})")
