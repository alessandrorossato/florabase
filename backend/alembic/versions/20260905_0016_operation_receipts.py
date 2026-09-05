"""Add immutable typed authoritative-operation receipts.

Revision ID: 20260905_0016
Revises: 20260904_0015
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260905_0016"
down_revision: str | None = "20260904_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


KINDS = (
    "kind IN ('seed_lot_to_sowing', 'sowing_to_plant', 'sowing_to_plant_group', "
    "'plant_group_extraction', 'plant_transfer', 'plant_group_transfer')"
)
TYPED_REFERENCES = (
    "((kind = 'seed_lot_to_sowing' AND seed_lot_id IS NOT NULL AND sowing_id IS NOT NULL "
    "AND plant_id IS NULL AND plant_group_id IS NULL AND event_id IS NULL "
    "AND adjustment_mode IS NOT NULL) OR "
    "(kind = 'sowing_to_plant' AND seed_lot_id IS NULL AND sowing_id IS NOT NULL "
    "AND plant_id IS NOT NULL AND plant_group_id IS NULL AND event_id IS NULL "
    "AND adjustment_mode IS NULL) OR "
    "(kind = 'sowing_to_plant_group' AND seed_lot_id IS NULL AND sowing_id IS NOT NULL "
    "AND plant_id IS NULL AND plant_group_id IS NOT NULL AND event_id IS NULL "
    "AND adjustment_mode IS NULL) OR "
    "(kind = 'plant_group_extraction' AND seed_lot_id IS NULL AND sowing_id IS NULL "
    "AND plant_id IS NOT NULL AND plant_group_id IS NOT NULL AND event_id IS NOT NULL "
    "AND adjustment_mode IS NULL) OR "
    "(kind = 'plant_transfer' AND seed_lot_id IS NULL AND sowing_id IS NULL "
    "AND plant_id IS NOT NULL AND plant_group_id IS NULL AND event_id IS NOT NULL "
    "AND adjustment_mode IS NULL) OR "
    "(kind = 'plant_group_transfer' AND seed_lot_id IS NULL AND sowing_id IS NULL "
    "AND plant_id IS NULL AND plant_group_id IS NOT NULL AND event_id IS NOT NULL "
    "AND adjustment_mode IS NULL)) IS TRUE"
)
BEFORE_QUANTITY = (
    "((before_quantity_kind IS NULL AND before_quantity_value IS NULL AND "
    "before_quantity_unit IS NULL AND before_quantity_is_approximate IS NULL) OR "
    "(before_quantity_kind = 'seed_count' AND before_quantity_value >= 0 AND "
    "before_quantity_value = trunc(before_quantity_value) AND before_quantity_unit IS NULL "
    "AND before_quantity_is_approximate IS NOT NULL) OR "
    "(before_quantity_kind = 'weight' AND before_quantity_value >= 0 AND "
    "before_quantity_unit IN ('g', 'mg') AND before_quantity_is_approximate IS NOT NULL) OR "
    "(before_quantity_kind = 'count' AND before_quantity_value >= 0 AND "
    "before_quantity_value = trunc(before_quantity_value) AND before_quantity_unit IS NULL "
    "AND before_quantity_is_approximate IS NOT NULL)) IS TRUE"
)
AFTER_QUANTITY = BEFORE_QUANTITY.replace("before_", "after_")
TYPED_STATE = (
    "((kind = 'seed_lot_to_sowing' AND before_lifecycle IN "
    "('active', 'exhausted', 'discarded', 'lost') AND after_lifecycle IN "
    "('active', 'exhausted', 'discarded', 'lost') AND "
    "(before_quantity_kind IS NULL OR before_quantity_kind IN ('seed_count', 'weight')) AND "
    "(after_quantity_kind IS NULL OR after_quantity_kind IN ('seed_count', 'weight'))) OR "
    "(kind IN ('sowing_to_plant', 'sowing_to_plant_group') AND before_lifecycle IN "
    "('active', 'completed', 'failed', 'abandoned') AND after_lifecycle IN "
    "('active', 'completed', 'failed', 'abandoned') AND "
    "before_quantity_kind IS NULL AND before_quantity_value IS NULL AND "
    "before_quantity_unit IS NULL AND before_quantity_is_approximate IS NULL AND "
    "after_quantity_kind IS NULL AND after_quantity_value IS NULL AND "
    "after_quantity_unit IS NULL AND after_quantity_is_approximate IS NULL) OR "
    "(kind = 'plant_group_extraction' AND before_lifecycle = 'active' AND "
    "after_lifecycle IN ('active', 'completed') AND "
    "(before_quantity_kind IS NULL OR before_quantity_kind = 'count') AND "
    "(after_quantity_kind IS NULL OR after_quantity_kind = 'count')) OR "
    "(kind = 'plant_transfer' AND before_lifecycle IN "
    "('active', 'dead', 'lost', 'discarded') AND "
    "after_lifecycle = 'transferred' AND before_quantity_kind IS NULL AND "
    "before_quantity_value IS NULL AND before_quantity_unit IS NULL AND "
    "before_quantity_is_approximate IS NULL AND after_quantity_kind IS NULL AND "
    "after_quantity_value IS NULL AND after_quantity_unit IS NULL AND "
    "after_quantity_is_approximate IS NULL) OR "
    "(kind = 'plant_group_transfer' AND before_lifecycle IN "
    "('active', 'completed', 'dead', 'lost', 'discarded') AND "
    "after_lifecycle = 'transferred' AND "
    "(before_quantity_kind IS NULL OR before_quantity_kind = 'count') AND "
    "(after_quantity_kind IS NULL OR after_quantity_kind = 'count'))) IS TRUE"
)


def upgrade() -> None:
    op.create_table(
        "operation_receipts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("seed_lot_id", sa.Uuid(), nullable=True),
        sa.Column("sowing_id", sa.Uuid(), nullable=True),
        sa.Column("plant_id", sa.Uuid(), nullable=True),
        sa.Column("plant_group_id", sa.Uuid(), nullable=True),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("adjustment_mode", sa.String(length=16), nullable=True),
        sa.Column("before_lifecycle", sa.String(length=16), nullable=False),
        sa.Column("after_lifecycle", sa.String(length=16), nullable=False),
        sa.Column("before_quantity_kind", sa.String(length=16), nullable=True),
        sa.Column("before_quantity_value", sa.Numeric(), nullable=True),
        sa.Column("before_quantity_unit", sa.String(length=8), nullable=True),
        sa.Column("before_quantity_is_approximate", sa.Boolean(), nullable=True),
        sa.Column("after_quantity_kind", sa.String(length=16), nullable=True),
        sa.Column("after_quantity_value", sa.Numeric(), nullable=True),
        sa.Column("after_quantity_unit", sa.String(length=8), nullable=True),
        sa.Column("after_quantity_is_approximate", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(KINDS, name="ck_operation_receipts_kind"),
        sa.CheckConstraint(
            "status IN ('applied', 'reversed')", name="ck_operation_receipts_status"
        ),
        sa.CheckConstraint(
            "adjustment_mode IS NULL OR adjustment_mode IN ('none', 'partial', 'use_all')",
            name="ck_operation_receipts_adjustment_mode",
        ),
        sa.CheckConstraint(TYPED_REFERENCES, name="ck_operation_receipts_typed_references"),
        sa.CheckConstraint(BEFORE_QUANTITY, name="ck_operation_receipts_before_quantity"),
        sa.CheckConstraint(AFTER_QUANTITY, name="ck_operation_receipts_after_quantity"),
        sa.CheckConstraint(TYPED_STATE, name="ck_operation_receipts_typed_state"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plant_group_id"], ["plant_groups.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["seed_lot_id"], ["seed_lots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sowing_id"], ["sowings.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_operation_receipts_event_id"),
    )
    for column in ("seed_lot_id", "sowing_id", "plant_id", "plant_group_id"):
        op.create_index(f"ix_operation_receipts_{column}", "operation_receipts", [column])
    op.execute(
        """
        CREATE FUNCTION operation_receipt_original_facts_immutable() RETURNS trigger AS $$
        BEGIN
            IF (to_jsonb(NEW) - 'status') IS DISTINCT FROM (to_jsonb(OLD) - 'status') THEN
                RAISE EXCEPTION 'operation receipt original facts are immutable';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_operation_receipt_original_facts_immutable
        BEFORE UPDATE ON operation_receipts
        FOR EACH ROW EXECUTE FUNCTION operation_receipt_original_facts_immutable()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_operation_receipt_original_facts_immutable ON operation_receipts")
    op.execute("DROP FUNCTION operation_receipt_original_facts_immutable()")
    op.drop_table("operation_receipts")
