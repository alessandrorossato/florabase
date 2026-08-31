"""Allow exact zero quantity for exhausted SeedLots.

Revision ID: 20260830_0009
Revises: 20260830_0008
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260830_0009"
down_revision: str | None = "20260830_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_seed_lots_quantity", "seed_lots", type_="check")
    op.create_check_constraint(
        "ck_seed_lots_quantity",
        "seed_lots",
        "((quantity_kind IS NULL AND quantity_value IS NULL AND quantity_unit IS NULL "
        "AND quantity_is_approximate IS NULL) OR "
        "(quantity_kind = 'seed_count' AND quantity_value = trunc(quantity_value) "
        "AND quantity_unit IS NULL AND quantity_is_approximate IS NOT NULL AND "
        "(quantity_value > 0 OR (quantity_value = 0 AND lifecycle = 'exhausted' "
        "AND quantity_is_approximate = false))) OR "
        "(quantity_kind = 'weight' AND quantity_unit IN ('g', 'mg') "
        "AND quantity_is_approximate IS NOT NULL AND "
        "(quantity_value > 0 OR (quantity_value = 0 AND lifecycle = 'exhausted' "
        "AND quantity_is_approximate = false)))) IS TRUE",
    )


def downgrade() -> None:
    op.drop_constraint("ck_seed_lots_quantity", "seed_lots", type_="check")
    op.create_check_constraint(
        "ck_seed_lots_quantity",
        "seed_lots",
        "((quantity_kind IS NULL AND quantity_value IS NULL AND quantity_unit IS NULL "
        "AND quantity_is_approximate IS NULL) OR "
        "(quantity_kind = 'seed_count' AND quantity_value > 0 "
        "AND quantity_value = trunc(quantity_value) AND quantity_unit IS NULL "
        "AND quantity_is_approximate IS NOT NULL) OR "
        "(quantity_kind = 'weight' AND quantity_value > 0 "
        "AND quantity_unit IN ('g', 'mg') AND quantity_is_approximate IS NOT NULL)) IS TRUE",
    )
