"""Retain the prior value of each corrected measurement Event.

Revision ID: 20261109_0044
Revises: 20261108_0043
"""

import sqlalchemy as sa

from alembic import op

revision = "20261109_0044"
down_revision = "20261108_0043"
branch_labels = None
depends_on = None

VALUE = (
    "(quantity = 'height' AND unit IN ('mm', 'cm', 'm') AND value > 0 "
    "AND value * CASE unit WHEN 'mm' THEN 1 WHEN 'cm' THEN 10 ELSE 1000 END <= 200000 "
    "AND scale(value) <= 3) IS TRUE"
)
DATE = (
    "(occurred_on_year BETWEEN 1 AND 9999 AND ("
    "(occurred_on_precision = 'year' AND occurred_on_month IS NULL AND occurred_on_day IS NULL) OR "
    "(occurred_on_precision = 'month' AND occurred_on_month BETWEEN 1 AND 12 "
    "AND occurred_on_day IS NULL) OR "
    "(occurred_on_precision = 'day' AND occurred_on_month BETWEEN 1 AND 12 "
    "AND occurred_on_day BETWEEN 1 AND 31 AND "
    "make_date(occurred_on_year, occurred_on_month, occurred_on_day) IS NOT NULL))) IS TRUE"
)


def upgrade() -> None:
    op.create_table(
        "event_measurement_corrections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Uuid(),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("quantity", sa.String(16), nullable=False),
        sa.Column("value", sa.Numeric(), nullable=False),
        sa.Column("unit", sa.String(8), nullable=False),
        sa.Column("is_approximate", sa.Boolean(), nullable=False),
        sa.Column("occurred_on_precision", sa.String(8), nullable=False),
        sa.Column("occurred_on_year", sa.SmallInteger(), nullable=False),
        sa.Column("occurred_on_month", sa.SmallInteger(), nullable=True),
        sa.Column("occurred_on_day", sa.SmallInteger(), nullable=True),
        sa.Column("replaced_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(VALUE, name="ck_event_measurement_corrections_value"),
        sa.CheckConstraint(DATE, name="ck_event_measurement_corrections_date"),
    )
    op.create_index(
        "ix_event_measurement_corrections_event",
        "event_measurement_corrections",
        ["event_id", "replaced_at"],
    )


def downgrade() -> None:
    op.execute("LOCK TABLE event_measurement_corrections IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM event_measurement_corrections)")):
        raise RuntimeError(
            "Measurement corrections exist; delete them explicitly before downgrade."
        )
    op.drop_table("event_measurement_corrections")
