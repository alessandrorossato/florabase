"""Persist the first SeedLot inventory slice.

Revision ID: 20260830_0008
Revises: 20260830_0007
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260830_0008"
down_revision: str | None = "20260830_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _partial_date_constraint(prefix: str) -> sa.CheckConstraint:
    precision = f"{prefix}_precision"
    year = f"{prefix}_year"
    month = f"{prefix}_month"
    day = f"{prefix}_day"
    return sa.CheckConstraint(
        f"({precision} IS NULL AND {year} IS NULL AND {month} IS NULL AND {day} IS NULL) OR ("
        f"{year} BETWEEN 1 AND 9999 AND ("
        f"({precision} = 'year' AND {month} IS NULL AND {day} IS NULL) OR "
        f"({precision} = 'month' AND {month} BETWEEN 1 AND 12 AND {day} IS NULL) OR "
        f"({precision} = 'day' AND {month} BETWEEN 1 AND 12 AND {day} BETWEEN 1 AND 31 "
        f"AND make_date({year}, {month}, {day}) IS NOT NULL))) IS TRUE",
        name=f"ck_seed_lots_{prefix}",
    )


def upgrade() -> None:
    op.create_table(
        "seed_lots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("botanical_identity_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("source_kind", sa.String(length=32), server_default="unknown", nullable=False),
        sa.Column("source_detail", sa.String(length=255), nullable=True),
        sa.Column("supplier_id", sa.Uuid(), nullable=True),
        sa.Column("material_provenance_place_id", sa.Uuid(), nullable=True),
        sa.Column("acquisition_date_precision", sa.String(length=8), nullable=True),
        sa.Column("acquisition_date_year", sa.SmallInteger(), nullable=True),
        sa.Column("acquisition_date_month", sa.SmallInteger(), nullable=True),
        sa.Column("acquisition_date_day", sa.SmallInteger(), nullable=True),
        sa.Column("harvest_date_precision", sa.String(length=8), nullable=True),
        sa.Column("harvest_date_year", sa.SmallInteger(), nullable=True),
        sa.Column("harvest_date_month", sa.SmallInteger(), nullable=True),
        sa.Column("harvest_date_day", sa.SmallInteger(), nullable=True),
        sa.Column("quantity_kind", sa.String(length=16), nullable=True),
        sa.Column("quantity_value", sa.Numeric(), nullable=True),
        sa.Column("quantity_unit", sa.String(length=8), nullable=True),
        sa.Column("quantity_is_approximate", sa.Boolean(), nullable=True),
        sa.Column("expected_viability_until_precision", sa.String(length=8), nullable=True),
        sa.Column("expected_viability_until_year", sa.SmallInteger(), nullable=True),
        sa.Column("expected_viability_until_month", sa.SmallInteger(), nullable=True),
        sa.Column("expected_viability_until_day", sa.SmallInteger(), nullable=True),
        sa.Column("location_id", sa.Uuid(), nullable=True),
        sa.Column("lifecycle", sa.String(length=16), server_default="active", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "label IS NULL OR (char_length(label) BETWEEN 1 AND 255 AND label = "
            "regexp_replace(btrim(label), '[[:space:]]+', ' ', 'g') "
            "AND label !~ '[[:cntrl:]]')",
            name="ck_seed_lots_label",
        ),
        sa.CheckConstraint(
            "source_kind IN ('purchased', 'purchased_fruit', 'self_collected', "
            "'collection_produced', 'gift_exchange', 'other', 'unknown')",
            name="ck_seed_lots_source_kind",
        ),
        sa.CheckConstraint(
            "(source_kind = 'other' AND (source_detail IS NULL OR "
            "(char_length(source_detail) BETWEEN 1 AND 255 AND source_detail = "
            "regexp_replace(btrim(source_detail), '[[:space:]]+', ' ', 'g') "
            "AND source_detail !~ '[[:cntrl:]]'))) OR "
            "(source_kind <> 'other' AND source_detail IS NULL)",
            name="ck_seed_lots_source_detail",
        ),
        _partial_date_constraint("acquisition_date"),
        _partial_date_constraint("harvest_date"),
        _partial_date_constraint("expected_viability_until"),
        sa.CheckConstraint(
            "((quantity_kind IS NULL AND quantity_value IS NULL AND quantity_unit IS NULL "
            "AND quantity_is_approximate IS NULL) OR "
            "(quantity_kind = 'seed_count' AND quantity_value > 0 "
            "AND quantity_value = trunc(quantity_value) AND quantity_unit IS NULL "
            "AND quantity_is_approximate IS NOT NULL) OR "
            "(quantity_kind = 'weight' AND quantity_value > 0 "
            "AND quantity_unit IN ('g', 'mg') AND quantity_is_approximate IS NOT NULL)) IS TRUE",
            name="ck_seed_lots_quantity",
        ),
        sa.CheckConstraint(
            "lifecycle IN ('active', 'exhausted', 'discarded', 'lost')",
            name="ck_seed_lots_lifecycle",
        ),
        sa.CheckConstraint(
            "notes IS NULL OR (char_length(notes) BETWEEN 1 AND 20000 AND notes = btrim(notes) "
            "AND regexp_replace(notes, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
            name="ck_seed_lots_notes",
        ),
        sa.ForeignKeyConstraint(
            ["botanical_identity_id"],
            ["botanical_identities.id"],
            name=op.f("fk_seed_lots_botanical_identity_id_botanical_identities"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name=op.f("fk_seed_lots_supplier_id_suppliers"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["material_provenance_place_id"],
            ["geographic_places.id"],
            name=op.f("fk_seed_lots_material_provenance_place_id_geographic_places"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
            name=op.f("fk_seed_lots_location_id_locations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_seed_lots")),
    )
    for column in (
        "botanical_identity_id",
        "supplier_id",
        "material_provenance_place_id",
        "location_id",
        "lifecycle",
    ):
        op.create_index(op.f(f"ix_seed_lots_{column}"), "seed_lots", [column], unique=False)


def downgrade() -> None:
    for column in (
        "lifecycle",
        "location_id",
        "material_provenance_place_id",
        "supplier_id",
        "botanical_identity_id",
    ):
        op.drop_index(op.f(f"ix_seed_lots_{column}"), table_name="seed_lots")
    op.drop_table("seed_lots")
