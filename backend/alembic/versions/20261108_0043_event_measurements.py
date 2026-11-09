"""Add typed height measurement Events for individual Plants.

Revision ID: 20261108_0043
Revises: 20261013_0042
"""

import sqlalchemy as sa

from alembic import op

revision = "20261108_0043"
down_revision = "20261013_0042"
branch_labels = None
depends_on = None

_KINDS = (
    "'observation', 'movement', 'repotting', 'flowering', 'fruiting', 'pruning', 'treatment', "
    "'harvest', 'extraction', 'reintegration', 'transfer', 'death', 'loss', 'discarded', 'other'"
)
MEASUREMENT = (
    "((kind = 'measurement' AND plant_id IS NOT NULL AND occurred_on_precision IS NOT NULL "
    "AND measurement_quantity = 'height' AND measurement_unit IN ('mm', 'cm', 'm') "
    "AND measurement_value > 0 AND measurement_value * CASE measurement_unit "
    "WHEN 'mm' THEN 1 WHEN 'cm' THEN 10 ELSE 1000 END <= 200000 "
    "AND scale(measurement_value) <= 3 AND measurement_is_approximate IS NOT NULL) OR "
    "(kind <> 'measurement' AND measurement_quantity IS NULL AND measurement_value IS NULL "
    "AND measurement_unit IS NULL AND measurement_is_approximate IS NULL)) IS TRUE"
)


def upgrade() -> None:
    op.add_column("events", sa.Column("measurement_quantity", sa.String(16), nullable=True))
    op.add_column("events", sa.Column("measurement_value", sa.Numeric(), nullable=True))
    op.add_column("events", sa.Column("measurement_unit", sa.String(8), nullable=True))
    op.add_column("events", sa.Column("measurement_is_approximate", sa.Boolean(), nullable=True))
    op.drop_constraint("ck_events_kind", "events", type_="check")
    op.create_check_constraint("ck_events_kind", "events", f"kind IN ({_KINDS}, 'measurement')")
    op.create_check_constraint("ck_events_measurement", "events", MEASUREMENT)


def downgrade() -> None:
    op.execute("LOCK TABLE events IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM events WHERE kind = 'measurement')")
    ):
        raise RuntimeError("Measurement Events exist; delete them explicitly before downgrade.")
    op.drop_constraint("ck_events_measurement", "events", type_="check")
    op.drop_constraint("ck_events_kind", "events", type_="check")
    op.create_check_constraint("ck_events_kind", "events", f"kind IN ({_KINDS})")
    for column in ("is_approximate", "unit", "value", "quantity"):
        op.drop_column("events", f"measurement_{column}")
