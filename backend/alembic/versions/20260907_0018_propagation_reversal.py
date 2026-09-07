"""Capture typed propagation result snapshots and retain reversed results.

Revision ID: 20260907_0018
Revises: 20260905_0017
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260907_0018"
down_revision: str | None = "20260905_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RESULT_SNAPSHOT = (
    "((result_snapshot_version IS NULL AND result_lifecycle IS NULL AND r"
    "esult_quantity_kind "
    "IS NULL AND result_quantity_value IS NULL AND result_quantity_unit I"
    "S NULL AND result_qu"
    "antity_is_approximate IS NULL AND result_botanical_identity_id IS NU"
    "LL AND result_locati"
    "on_id IS NULL AND result_date_precision IS NULL AND result_date_year"
    " IS NULL AND result_"
    "date_month IS NULL AND result_date_day IS NULL AND source_location_i"
    "d IS NULL AND source"
    "_seed_lot_id IS NULL) OR (result_snapshot_version = 1 AND ((kind = '"
    "seed_lot_to_sowing' "
    "AND result_lifecycle IN ('active', 'completed', 'failed', 'abandoned"
    "') AND result_botani"
    "cal_identity_id IS NULL AND source_seed_lot_id IS NULL AND (result_q"
    "uantity_kind IS NULL"
    " OR result_quantity_kind IN ('seed_count', 'weight'))) OR (kind = 's"
    "owing_to_plant' AND "
    "result_lifecycle IN ('active', 'transferred', 'dead', 'lost', 'disca"
    "rded') AND result_bo"
    "tanical_identity_id IS NOT NULL AND source_seed_lot_id IS NOT NULL A"
    "ND result_quantity_k"
    "ind IS NULL) OR (kind = 'sowing_to_plant_group' AND result_lifecycle"
    " IN ('active', 'tran"
    "sferred', 'completed', 'dead', 'lost', 'discarded') AND result_botan"
    "ical_identity_id IS "
    "NOT NULL AND source_seed_lot_id IS NOT NULL AND (result_quantity_kin"
    "d IS NULL OR result_"
    "quantity_kind = 'count'))))) IS TRUE"
)
RESULT_QUANTITY = (
    "((result_quantity_kind IS NULL AND result_quantity_value IS NULL AND"
    " result_quantity_uni"
    "t IS NULL AND result_quantity_is_approximate IS NULL) OR (result_qua"
    "ntity_kind IN ('seed"
    "_count', 'count') AND result_quantity_value >= 0 AND result_quantity"
    "_value = trunc(resul"
    "t_quantity_value) AND result_quantity_unit IS NULL AND result_quanti"
    "ty_is_approximate IS"
    " NOT NULL) OR (result_quantity_kind = 'weight' AND result_quantity_v"
    "alue > 0 AND result_"
    "quantity_unit IN ('g', 'mg') AND result_quantity_is_approximate IS NOT NULL)) IS TRUE"
)
RESULT_DATE = (
    "((result_date_precision IS NULL AND result_date_year IS NULL AND res"
    "ult_date_month IS NU"
    "LL AND result_date_day IS NULL) OR (result_date_year BETWEEN 1 AND 9"
    "999 AND ((result_dat"
    "e_precision = 'year' AND result_date_month IS NULL AND result_date_d"
    "ay IS NULL) OR (resu"
    "lt_date_precision = 'month' AND result_date_month BETWEEN 1 AND 12 A"
    "ND result_date_day I"
    "S NULL) OR (result_date_precision = 'day' AND result_date_month BETW"
    "EEN 1 AND 12 AND res"
    "ult_date_day BETWEEN 1 AND 31 AND make_date(result_date_year, result"
    "_date_month, result_"
    "date_day) IS NOT NULL)))) IS TRUE"
)
TYPED_STATE = (
    "((kind = 'seed_lot_to_sowing' AND before_lifecycle IN ('active', 'ex"
    "hausted', 'discarded"
    "', 'lost') AND after_lifecycle IN ('active', 'exhausted', 'discarded"
    "', 'lost') AND (befo"
    "re_quantity_kind IS NULL OR before_quantity_kind IN ('seed_count', '"
    "weight')) AND (after"
    "_quantity_kind IS NULL OR after_quantity_kind IN ('seed_count', 'wei"
    "ght'))) OR (kind IN "
    "('sowing_to_plant', 'sowing_to_plant_group') AND before_lifecycle IN"
    " ('active', 'complet"
    "ed', 'failed', 'abandoned') AND after_lifecycle IN ('active', 'compl"
    "eted', 'failed', 'ab"
    "andoned') AND (before_quantity_kind IS NULL OR before_quantity_kind "
    "IN ('seed_count', 'w"
    "eight')) AND (after_quantity_kind IS NULL OR after_quantity_kind IN "
    "('seed_count', 'weig"
    "ht'))) OR (kind = 'plant_group_extraction' AND before_lifecycle = 'a"
    "ctive' AND after_lif"
    "ecycle IN ('active', 'completed') AND (before_quantity_kind IS NULL "
    "OR before_quantity_k"
    "ind = 'count') AND (after_quantity_kind IS NULL OR after_quantity_ki"
    "nd = 'count')) OR (k"
    "ind = 'plant_transfer' AND before_lifecycle IN ('active', 'dead', 'l"
    "ost', 'discarded') A"
    "ND after_lifecycle = 'transferred' AND before_quantity_kind IS NULL "
    "AND before_quantity_"
    "value IS NULL AND before_quantity_unit IS NULL AND before_quantity_i"
    "s_approximate IS NUL"
    "L AND after_quantity_kind IS NULL AND after_quantity_value IS NULL A"
    "ND after_quantity_un"
    "it IS NULL AND after_quantity_is_approximate IS NULL) OR (kind = 'pl"
    "ant_group_transfer' "
    "AND before_lifecycle IN ('active', 'completed', 'dead', 'lost', 'dis"
    "carded') AND after_l"
    "ifecycle = 'transferred' AND (before_quantity_kind IS NULL OR before"
    "_quantity_kind = 'co"
    "unt') AND (after_quantity_kind IS NULL OR after_quantity_kind = 'count'))) IS TRUE"
)
OLD_TYPED_STATE = (
    "((kind = 'seed_lot_to_sowing' AND before_lifecycle IN ('active', 'ex"
    "hausted', 'discarded"
    "', 'lost') AND after_lifecycle IN ('active', 'exhausted', 'discarded"
    "', 'lost') AND (befo"
    "re_quantity_kind IS NULL OR before_quantity_kind IN ('seed_count', '"
    "weight')) AND (after"
    "_quantity_kind IS NULL OR after_quantity_kind IN ('seed_count', 'wei"
    "ght'))) OR (kind IN "
    "('sowing_to_plant', 'sowing_to_plant_group') AND before_lifecycle IN"
    " ('active', 'complet"
    "ed', 'failed', 'abandoned') AND after_lifecycle IN ('active', 'compl"
    "eted', 'failed', 'ab"
    "andoned') AND before_quantity_kind IS NULL AND before_quantity_value"
    " IS NULL AND before_"
    "quantity_unit IS NULL AND before_quantity_is_approximate IS NULL AND"
    " after_quantity_kind"
    " IS NULL AND after_quantity_value IS NULL AND after_quantity_unit IS"
    " NULL AND after_quan"
    "tity_is_approximate IS NULL) OR (kind = 'plant_group_extraction' AND"
    " before_lifecycle = "
    "'active' AND after_lifecycle IN ('active', 'completed') AND (before_"
    "quantity_kind IS NUL"
    "L OR before_quantity_kind = 'count') AND (after_quantity_kind IS NUL"
    "L OR after_quantity_"
    "kind = 'count')) OR (kind = 'plant_transfer' AND before_lifecycle IN"
    " ('active', 'dead', "
    "'lost', 'discarded') AND after_lifecycle = 'transferred' AND before_"
    "quantity_kind IS NUL"
    "L AND before_quantity_value IS NULL AND before_quantity_unit IS NULL"
    " AND before_quantity"
    "_is_approximate IS NULL AND after_quantity_kind IS NULL AND after_qu"
    "antity_value IS NULL"
    " AND after_quantity_unit IS NULL AND after_quantity_is_approximate I"
    "S NULL) OR (kind = '"
    "plant_group_transfer' AND before_lifecycle IN ('active', 'completed'"
    ", 'dead', 'lost', 'd"
    "iscarded') AND after_lifecycle = 'transferred' AND (before_quantity_"
    "kind IS NULL OR befo"
    "re_quantity_kind = 'count') AND (after_quantity_kind IS NULL OR afte"
    "r_quantity_kind = 'c"
    "ount'))) IS TRUE"
)
LIFECYCLES = {
    "plants": "'active', 'reintegrated', 'transferred', 'dead', 'lost', 'discarded'",
    "plant_groups": "'active', 'transferred', 'completed', 'dead', 'lost', 'discarded'",
    "sowings": "'active', 'completed', 'failed', 'abandoned'",
}
GROUP_QUANTITY = (
    "((quantity_value IS NULL AND quantity_is_approximate IS NULL) OR (qu"
    "antity_value > 0 AND"
    " quantity_is_approximate IS NOT NULL) OR (quantity_value = 0 AND qua"
    "ntity_is_approximate"
    " = false AND lifecycle IN ('completed', 'dead', 'discarded', 'reversed'))) IS TRUE"
)


def upgrade() -> None:
    op.add_column(
        "operation_receipts", sa.Column("result_snapshot_version", sa.SmallInteger(), nullable=True)
    )
    op.add_column("operation_receipts", sa.Column("result_lifecycle", sa.String(16), nullable=True))
    op.add_column(
        "operation_receipts", sa.Column("result_quantity_kind", sa.String(16), nullable=True)
    )
    op.add_column(
        "operation_receipts", sa.Column("result_quantity_value", sa.Numeric(), nullable=True)
    )
    op.add_column(
        "operation_receipts", sa.Column("result_quantity_unit", sa.String(8), nullable=True)
    )
    op.add_column(
        "operation_receipts",
        sa.Column("result_quantity_is_approximate", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "operation_receipts", sa.Column("result_botanical_identity_id", sa.Uuid(), nullable=True)
    )
    op.add_column("operation_receipts", sa.Column("result_location_id", sa.Uuid(), nullable=True))
    op.add_column(
        "operation_receipts", sa.Column("result_date_precision", sa.String(8), nullable=True)
    )
    op.add_column(
        "operation_receipts", sa.Column("result_date_year", sa.SmallInteger(), nullable=True)
    )
    op.add_column(
        "operation_receipts", sa.Column("result_date_month", sa.SmallInteger(), nullable=True)
    )
    op.add_column(
        "operation_receipts", sa.Column("result_date_day", sa.SmallInteger(), nullable=True)
    )
    op.add_column("operation_receipts", sa.Column("source_location_id", sa.Uuid(), nullable=True))
    op.add_column("operation_receipts", sa.Column("source_seed_lot_id", sa.Uuid(), nullable=True))
    # No backfill: current aggregates cannot prove historical result state.
    op.drop_constraint("ck_operation_receipts_typed_state", "operation_receipts", type_="check")
    op.create_check_constraint(
        "ck_operation_receipts_typed_state", "operation_receipts", TYPED_STATE
    )
    for name, expression in (
        ("result_snapshot", RESULT_SNAPSHOT),
        ("result_quantity", RESULT_QUANTITY),
        ("result_date", RESULT_DATE),
    ):
        op.create_check_constraint(
            f"ck_operation_receipts_{name}", "operation_receipts", expression
        )
    for table, values in LIFECYCLES.items():
        op.drop_constraint(f"ck_{table}_lifecycle", table, type_="check")
        op.create_check_constraint(
            f"ck_{table}_lifecycle", table, f"lifecycle IN ({values}, 'reversed')"
        )
    op.drop_constraint("ck_plant_groups_quantity", "plant_groups", type_="check")
    op.create_check_constraint("ck_plant_groups_quantity", "plant_groups", GROUP_QUANTITY)


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM sowings WHERE lifecycle = 'reversed')
               OR EXISTS (SELECT 1 FROM plants WHERE lifecycle = 'reversed')
               OR EXISTS (SELECT 1 FROM plant_groups WHERE lifecycle = 'reversed')
               OR EXISTS (SELECT 1 FROM operation_receipts
                          WHERE result_snapshot_version IS NOT NULL)
            THEN RAISE EXCEPTION 'cannot downgrade while propagation history exists';
            END IF;
        END $$
    """)
    op.drop_constraint("ck_plant_groups_quantity", "plant_groups", type_="check")
    op.create_check_constraint(
        "ck_plant_groups_quantity", "plant_groups", GROUP_QUANTITY.replace(", 'reversed'", "")
    )
    for table, values in LIFECYCLES.items():
        op.drop_constraint(f"ck_{table}_lifecycle", table, type_="check")
        op.create_check_constraint(f"ck_{table}_lifecycle", table, f"lifecycle IN ({values})")
    for name in ("result_snapshot", "result_quantity", "result_date", "typed_state"):
        op.drop_constraint(f"ck_operation_receipts_{name}", "operation_receipts", type_="check")
    op.create_check_constraint(
        "ck_operation_receipts_typed_state", "operation_receipts", OLD_TYPED_STATE
    )
    op.drop_column("operation_receipts", "result_snapshot_version")
    op.drop_column("operation_receipts", "result_lifecycle")
    op.drop_column("operation_receipts", "result_quantity_kind")
    op.drop_column("operation_receipts", "result_quantity_value")
    op.drop_column("operation_receipts", "result_quantity_unit")
    op.drop_column("operation_receipts", "result_quantity_is_approximate")
    op.drop_column("operation_receipts", "result_botanical_identity_id")
    op.drop_column("operation_receipts", "result_location_id")
    op.drop_column("operation_receipts", "result_date_precision")
    op.drop_column("operation_receipts", "result_date_year")
    op.drop_column("operation_receipts", "result_date_month")
    op.drop_column("operation_receipts", "result_date_day")
    op.drop_column("operation_receipts", "source_location_id")
    op.drop_column("operation_receipts", "source_seed_lot_id")
