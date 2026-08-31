"""Persist the first Sowing and germination summary slice.

Revision ID: 20260831_0010
Revises: 20260830_0009
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260831_0010"
down_revision: str | None = "20260830_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _single_line_constraint(column: str, maximum: int) -> sa.CheckConstraint:
    return sa.CheckConstraint(
        f"{column} IS NULL OR (char_length({column}) BETWEEN 1 AND {maximum} "
        f"AND {column} = regexp_replace(btrim({column}), '[[:space:]]+', ' ', 'g') "
        f"AND {column} !~ '[[:cntrl:]]')",
        name=f"ck_sowings_{column}",
    )


def upgrade() -> None:
    op.create_table(
        "sowings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("seed_lot_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("sowing_date_precision", sa.String(length=8), nullable=True),
        sa.Column("sowing_date_year", sa.SmallInteger(), nullable=True),
        sa.Column("sowing_date_month", sa.SmallInteger(), nullable=True),
        sa.Column("sowing_date_day", sa.SmallInteger(), nullable=True),
        sa.Column("quantity_kind", sa.String(length=16), nullable=True),
        sa.Column("quantity_value", sa.Numeric(), nullable=True),
        sa.Column("quantity_unit", sa.String(length=8), nullable=True),
        sa.Column("quantity_is_approximate", sa.Boolean(), nullable=True),
        sa.Column("germinated_count", sa.Integer(), nullable=True),
        sa.Column("location_id", sa.Uuid(), nullable=True),
        sa.Column("substrate", sa.String(length=1000), nullable=True),
        sa.Column("method_container", sa.String(length=1000), nullable=True),
        sa.Column("pretreatment", sa.String(length=1000), nullable=True),
        sa.Column("temperature_min_c", sa.Numeric(), nullable=True),
        sa.Column("temperature_max_c", sa.Numeric(), nullable=True),
        sa.Column("environment", sa.String(length=1000), nullable=True),
        sa.Column("lifecycle", sa.String(length=16), server_default="active", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        _single_line_constraint("label", 255),
        sa.CheckConstraint(
            "(sowing_date_precision IS NULL AND sowing_date_year IS NULL "
            "AND sowing_date_month IS NULL AND sowing_date_day IS NULL) OR ("
            "sowing_date_year BETWEEN 1 AND 9999 AND ("
            "(sowing_date_precision = 'year' AND sowing_date_month IS NULL "
            "AND sowing_date_day IS NULL) OR "
            "(sowing_date_precision = 'month' AND sowing_date_month BETWEEN 1 AND 12 "
            "AND sowing_date_day IS NULL) OR "
            "(sowing_date_precision = 'day' AND sowing_date_month BETWEEN 1 AND 12 "
            "AND sowing_date_day BETWEEN 1 AND 31 AND make_date(sowing_date_year, "
            "sowing_date_month, sowing_date_day) IS NOT NULL))) IS TRUE",
            name="ck_sowings_sowing_date",
        ),
        sa.CheckConstraint(
            "((quantity_kind IS NULL AND quantity_value IS NULL AND quantity_unit IS NULL "
            "AND quantity_is_approximate IS NULL) OR "
            "(quantity_kind = 'seed_count' AND quantity_value > 0 "
            "AND quantity_value = trunc(quantity_value) AND quantity_unit IS NULL "
            "AND quantity_is_approximate IS NOT NULL) OR "
            "(quantity_kind = 'weight' AND quantity_value > 0 "
            "AND quantity_unit IN ('g', 'mg') AND quantity_is_approximate IS NOT NULL)) IS TRUE",
            name="ck_sowings_quantity",
        ),
        sa.CheckConstraint(
            "germinated_count IS NULL OR germinated_count >= 0",
            name="ck_sowings_germinated_count",
        ),
        sa.CheckConstraint(
            "NOT (quantity_kind = 'seed_count' AND quantity_is_approximate = false "
            "AND germinated_count IS NOT NULL) OR germinated_count <= quantity_value",
            name="ck_sowings_germinated_within_exact_count",
        ),
        _single_line_constraint("substrate", 1000),
        _single_line_constraint("method_container", 1000),
        _single_line_constraint("pretreatment", 1000),
        sa.CheckConstraint(
            "temperature_min_c IS NULL OR temperature_max_c IS NULL "
            "OR temperature_min_c <= temperature_max_c",
            name="ck_sowings_temperature_order",
        ),
        _single_line_constraint("environment", 1000),
        sa.CheckConstraint(
            "lifecycle IN ('active', 'completed', 'failed', 'abandoned')",
            name="ck_sowings_lifecycle",
        ),
        sa.CheckConstraint(
            "notes IS NULL OR (char_length(notes) BETWEEN 1 AND 20000 "
            "AND notes = btrim(notes) "
            "AND regexp_replace(notes, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
            name="ck_sowings_notes",
        ),
        sa.ForeignKeyConstraint(
            ["seed_lot_id"],
            ["seed_lots.id"],
            name=op.f("fk_sowings_seed_lot_id_seed_lots"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
            name=op.f("fk_sowings_location_id_locations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sowings")),
    )
    for column in ("seed_lot_id", "location_id", "lifecycle"):
        op.create_index(op.f(f"ix_sowings_{column}"), "sowings", [column], unique=False)


def downgrade() -> None:
    for column in ("lifecycle", "location_id", "seed_lot_id"):
        op.drop_index(op.f(f"ix_sowings_{column}"), table_name="sowings")
    op.drop_table("sowings")
