"""Add recorded Plant reintegration into its original PlantGroup.

Revision ID: 20260905_0017
Revises: 20260905_0016
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260905_0017"
down_revision: str | None = "20260905_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


EVENT_KINDS = (
    "kind IN ('observation', 'movement', 'repotting', 'flowering', 'fruiting', "
    "'pruning', 'treatment', 'harvest', 'extraction', 'reintegration', 'transfer', "
    "'death', 'loss', 'discarded', 'other')"
)
OLD_EVENT_KINDS = EVENT_KINDS.replace("'reintegration', ", "")
OPERATION_RESULT = (
    "((kind IN ('extraction', 'reintegration') AND plant_group_id IS NOT NULL AND "
    "resulting_plant_id IS NOT NULL) OR "
    "(kind NOT IN ('extraction', 'reintegration') AND resulting_plant_id IS NULL)) IS TRUE"
)
OLD_EXTRACTION_RESULT = (
    "((kind = 'extraction' AND plant_group_id IS NOT NULL AND "
    "resulting_plant_id IS NOT NULL) OR "
    "(kind <> 'extraction' AND resulting_plant_id IS NULL)) IS TRUE"
)


def upgrade() -> None:
    op.drop_constraint("ck_plants_lifecycle", "plants", type_="check")
    op.create_check_constraint(
        "ck_plants_lifecycle",
        "plants",
        "lifecycle IN ('active', 'reintegrated', 'transferred', 'dead', 'lost', 'discarded')",
    )
    op.add_column("events", sa.Column("reversed_operation_receipt_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_events_reversed_operation_receipt_id",
        "events",
        "operation_receipts",
        ["reversed_operation_receipt_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_events_reversed_operation_receipt_id",
        "events",
        ["reversed_operation_receipt_id"],
    )
    op.drop_constraint("ck_events_kind", "events", type_="check")
    op.create_check_constraint("ck_events_kind", "events", EVENT_KINDS)
    op.drop_constraint("ck_events_extraction_result", "events", type_="check")
    op.create_check_constraint("ck_events_extraction_result", "events", OPERATION_RESULT)
    op.create_check_constraint(
        "ck_events_reintegration_receipt",
        "events",
        "((kind = 'reintegration' AND reversed_operation_receipt_id IS NOT NULL) OR "
        "(kind <> 'reintegration' AND reversed_operation_receipt_id IS NULL)) IS TRUE",
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM plants WHERE lifecycle = 'reintegrated')
               OR EXISTS (SELECT 1 FROM events WHERE kind = 'reintegration') THEN
                RAISE EXCEPTION 'cannot downgrade while Plant reintegration history exists';
            END IF;
        END
        $$
        """
    )
    op.drop_constraint("ck_events_reintegration_receipt", "events", type_="check")
    op.drop_constraint("ck_events_extraction_result", "events", type_="check")
    op.create_check_constraint("ck_events_extraction_result", "events", OLD_EXTRACTION_RESULT)
    op.drop_constraint("ck_events_kind", "events", type_="check")
    op.create_check_constraint("ck_events_kind", "events", OLD_EVENT_KINDS)
    op.drop_constraint("uq_events_reversed_operation_receipt_id", "events", type_="unique")
    op.drop_constraint("fk_events_reversed_operation_receipt_id", "events", type_="foreignkey")
    op.drop_column("events", "reversed_operation_receipt_id")
    op.drop_constraint("ck_plants_lifecycle", "plants", type_="check")
    op.create_check_constraint(
        "ck_plants_lifecycle",
        "plants",
        "lifecycle IN ('active', 'transferred', 'dead', 'lost', 'discarded')",
    )
