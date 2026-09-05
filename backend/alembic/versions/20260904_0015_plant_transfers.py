"""Add transferred lifecycle and coordinated transfer/extraction Events.

Revision ID: 20260904_0015
Revises: 20260902_0014
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260904_0015"
down_revision: str | None = "20260902_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PLANT_LIFECYCLES = "lifecycle IN ('active', 'transferred', 'dead', 'lost', 'discarded')"
GROUP_LIFECYCLES = (
    "lifecycle IN ('active', 'transferred', 'completed', 'dead', 'lost', 'discarded')"
)
GROUP_QUANTITY = (
    "((quantity_value IS NULL AND quantity_is_approximate IS NULL) OR "
    "(quantity_value > 0 AND quantity_is_approximate IS NOT NULL) OR "
    "(quantity_value = 0 AND quantity_is_approximate = false "
    "AND lifecycle IN ('completed', 'dead', 'discarded'))) IS TRUE"
)
EVENT_KINDS = (
    "kind IN ('observation', 'movement', 'repotting', 'flowering', 'fruiting', "
    "'pruning', 'treatment', 'harvest', 'extraction', 'transfer', 'death', 'loss', "
    "'discarded', 'other')"
)


def upgrade() -> None:
    op.drop_constraint("ck_plants_lifecycle", "plants", type_="check")
    op.create_check_constraint("ck_plants_lifecycle", "plants", PLANT_LIFECYCLES)
    op.drop_constraint("ck_plant_groups_quantity", "plant_groups", type_="check")
    op.drop_constraint("ck_plant_groups_lifecycle", "plant_groups", type_="check")
    op.create_check_constraint("ck_plant_groups_lifecycle", "plant_groups", GROUP_LIFECYCLES)
    op.create_check_constraint("ck_plant_groups_quantity", "plant_groups", GROUP_QUANTITY)

    op.add_column("events", sa.Column("recipient", sa.String(length=255), nullable=True))
    op.add_column("events", sa.Column("resulting_plant_id", sa.Uuid(), nullable=True))
    op.create_unique_constraint(
        "uq_plants_id_originating_plant_group_id",
        "plants",
        ["id", "originating_plant_group_id"],
    )
    op.create_foreign_key(
        op.f("fk_events_resulting_plant_id_plants"),
        "events",
        "plants",
        ["resulting_plant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_events_resulting_plant_source_group",
        "events",
        "plants",
        ["resulting_plant_id", "plant_group_id"],
        ["id", "originating_plant_group_id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_events_resulting_plant_id"), "events", ["resulting_plant_id"], unique=False
    )
    op.drop_constraint("ck_events_kind", "events", type_="check")
    op.create_check_constraint("ck_events_kind", "events", EVENT_KINDS)
    op.create_check_constraint(
        "ck_events_transfer_recipient",
        "events",
        "recipient IS NULL OR (kind = 'transfer' AND char_length(recipient) BETWEEN 1 AND 255 "
        "AND recipient = regexp_replace(btrim(recipient), '[[:space:]]+', ' ', 'g') "
        "AND recipient !~ '[[:cntrl:]]')",
    )
    op.create_check_constraint(
        "ck_events_extraction_result",
        "events",
        "((kind = 'extraction' AND plant_group_id IS NOT NULL AND "
        "resulting_plant_id IS NOT NULL) OR "
        "(kind <> 'extraction' AND resulting_plant_id IS NULL)) IS TRUE",
    )


def downgrade() -> None:
    op.execute("UPDATE events SET kind = 'other', recipient = NULL WHERE kind = 'transfer'")
    op.execute(
        "UPDATE events SET kind = 'other', resulting_plant_id = NULL WHERE kind = 'extraction'"
    )
    op.drop_constraint("ck_events_extraction_result", "events", type_="check")
    op.drop_constraint("ck_events_transfer_recipient", "events", type_="check")
    op.drop_constraint("ck_events_kind", "events", type_="check")
    op.create_check_constraint(
        "ck_events_kind",
        "events",
        "kind IN ('observation', 'movement', 'repotting', 'flowering', 'fruiting', "
        "'pruning', 'treatment', 'harvest', 'death', 'loss', 'discarded', 'other')",
    )
    op.drop_index(op.f("ix_events_resulting_plant_id"), table_name="events")
    op.drop_constraint("fk_events_resulting_plant_source_group", "events", type_="foreignkey")
    op.drop_constraint(op.f("fk_events_resulting_plant_id_plants"), "events", type_="foreignkey")
    op.drop_column("events", "resulting_plant_id")
    op.drop_column("events", "recipient")
    op.drop_constraint("uq_plants_id_originating_plant_group_id", "plants", type_="unique")

    op.execute("UPDATE plants SET lifecycle = 'active' WHERE lifecycle = 'transferred'")
    op.execute("UPDATE plant_groups SET lifecycle = 'active' WHERE lifecycle = 'transferred'")
    op.drop_constraint("ck_plant_groups_quantity", "plant_groups", type_="check")
    op.drop_constraint("ck_plant_groups_lifecycle", "plant_groups", type_="check")
    op.create_check_constraint(
        "ck_plant_groups_lifecycle",
        "plant_groups",
        "lifecycle IN ('active', 'completed', 'dead', 'lost', 'discarded')",
    )
    op.create_check_constraint("ck_plant_groups_quantity", "plant_groups", GROUP_QUANTITY)
    op.drop_constraint("ck_plants_lifecycle", "plants", type_="check")
    op.create_check_constraint(
        "ck_plants_lifecycle",
        "plants",
        "lifecycle IN ('active', 'dead', 'lost', 'discarded')",
    )
