"""Add concrete collection producer lineage to SeedLots.

Revision ID: 20260901_0012
Revises: 20260831_0011
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260901_0012"
down_revision: str | None = "20260831_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("seed_lots", sa.Column("producer_plant_id", sa.Uuid(), nullable=True))
    op.add_column("seed_lots", sa.Column("producer_plant_group_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_seed_lots_producer_plant_id_plants"),
        "seed_lots",
        "plants",
        ["producer_plant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_seed_lots_producer_plant_group_id_plant_groups"),
        "seed_lots",
        "plant_groups",
        ["producer_plant_group_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_seed_lots_producer_exclusive",
        "seed_lots",
        "NOT (producer_plant_id IS NOT NULL AND producer_plant_group_id IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_seed_lots_producer_source_kind",
        "seed_lots",
        "source_kind = 'collection_produced' OR "
        "(producer_plant_id IS NULL AND producer_plant_group_id IS NULL)",
    )
    op.create_index(
        op.f("ix_seed_lots_producer_plant_id"), "seed_lots", ["producer_plant_id"], unique=False
    )
    op.create_index(
        op.f("ix_seed_lots_producer_plant_group_id"),
        "seed_lots",
        ["producer_plant_group_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_seed_lots_producer_plant_group_id"), table_name="seed_lots")
    op.drop_index(op.f("ix_seed_lots_producer_plant_id"), table_name="seed_lots")
    op.drop_constraint("ck_seed_lots_producer_source_kind", "seed_lots", type_="check")
    op.drop_constraint("ck_seed_lots_producer_exclusive", "seed_lots", type_="check")
    op.drop_constraint(
        op.f("fk_seed_lots_producer_plant_group_id_plant_groups"),
        "seed_lots",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_seed_lots_producer_plant_id_plants"), "seed_lots", type_="foreignkey"
    )
    op.drop_column("seed_lots", "producer_plant_group_id")
    op.drop_column("seed_lots", "producer_plant_id")
