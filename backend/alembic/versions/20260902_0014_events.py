"""Add Plant and PlantGroup event journal.

Revision ID: 20260902_0014
Revises: 20260901_0013
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260902_0014"
down_revision: str | None = "20260901_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plant_id", sa.Uuid(), nullable=True),
        sa.Column("plant_group_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("occurred_on_precision", sa.String(length=8), nullable=True),
        sa.Column("occurred_on_year", sa.SmallInteger(), nullable=True),
        sa.Column("occurred_on_month", sa.SmallInteger(), nullable=True),
        sa.Column("occurred_on_day", sa.SmallInteger(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("destination_location_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "num_nonnulls(plant_id, plant_group_id) = 1",
            name="ck_events_exactly_one_target",
        ),
        sa.CheckConstraint(
            "kind IN ('observation', 'movement', 'repotting', 'flowering', 'fruiting', "
            "'pruning', 'treatment', 'harvest', 'death', 'loss', 'discarded', 'other')",
            name="ck_events_kind",
        ),
        sa.CheckConstraint(
            "(occurred_on_precision IS NULL AND occurred_on_year IS NULL "
            "AND occurred_on_month IS NULL AND occurred_on_day IS NULL) OR ("
            "occurred_on_year BETWEEN 1 AND 9999 AND ("
            "(occurred_on_precision = 'year' AND occurred_on_month IS NULL "
            "AND occurred_on_day IS NULL) OR "
            "(occurred_on_precision = 'month' AND occurred_on_month BETWEEN 1 AND 12 "
            "AND occurred_on_day IS NULL) OR "
            "(occurred_on_precision = 'day' AND occurred_on_month BETWEEN 1 AND 12 "
            "AND occurred_on_day BETWEEN 1 AND 31 AND "
            "make_date(occurred_on_year, occurred_on_month, occurred_on_day) IS NOT NULL))) "
            "IS TRUE",
            name="ck_events_occurred_on",
        ),
        sa.CheckConstraint(
            "((kind = 'movement' AND destination_location_id IS NOT NULL) OR "
            "(kind <> 'movement' AND destination_location_id IS NULL)) IS TRUE",
            name="ck_events_movement_destination",
        ),
        sa.CheckConstraint(
            "notes IS NULL OR (char_length(notes) BETWEEN 1 AND 20000 AND notes = btrim(notes) "
            "AND regexp_replace(notes, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
            name="ck_events_notes",
        ),
        sa.ForeignKeyConstraint(
            ["plant_id"], ["plants.id"], name=op.f("fk_events_plant_id_plants"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["plant_group_id"],
            ["plant_groups.id"],
            name=op.f("fk_events_plant_group_id_plant_groups"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["destination_location_id"],
            ["locations.id"],
            name=op.f("fk_events_destination_location_id_locations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_events")),
    )
    op.create_index(
        "ix_events_plant_timeline",
        "events",
        [
            "plant_id",
            "occurred_on_year",
            "occurred_on_month",
            "occurred_on_day",
            "created_at",
            "id",
        ],
    )
    op.create_index(
        "ix_events_plant_group_timeline",
        "events",
        [
            "plant_group_id",
            "occurred_on_year",
            "occurred_on_month",
            "occurred_on_day",
            "created_at",
            "id",
        ],
    )
    op.create_index(
        op.f("ix_events_destination_location_id"),
        "events",
        ["destination_location_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_events_destination_location_id"), table_name="events")
    op.drop_index("ix_events_plant_group_timeline", table_name="events")
    op.drop_index("ix_events_plant_timeline", table_name="events")
    op.drop_table("events")
