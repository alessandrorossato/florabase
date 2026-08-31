"""Persist the first Plant and PlantGroup backend slice.

Revision ID: 20260831_0011
Revises: 20260831_0010
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260831_0011"
down_revision: str | None = "20260831_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _common_constraints(table: str, lifecycles: str) -> tuple[sa.CheckConstraint, ...]:
    return (
        sa.CheckConstraint(
            "label IS NULL OR (char_length(label) BETWEEN 1 AND 255 "
            "AND label = regexp_replace(btrim(label), '[[:space:]]+', ' ', 'g') "
            "AND label !~ '[[:cntrl:]]')",
            name=f"ck_{table}_label",
        ),
        sa.CheckConstraint(
            "((originating_sowing_id IS NOT NULL AND direct_origin_kind IS NULL "
            "AND direct_origin_detail IS NULL AND supplier_id IS NULL "
            "AND material_provenance_place_id IS NULL) OR "
            "(originating_sowing_id IS NULL AND direct_origin_kind IN "
            "('purchased', 'gift_exchange', 'collection_produced', 'other', 'unknown'))) IS TRUE",
            name=f"ck_{table}_origin",
        ),
        sa.CheckConstraint(
            "(direct_origin_kind = 'other' AND (direct_origin_detail IS NULL OR "
            "(char_length(direct_origin_detail) BETWEEN 1 AND 255 "
            "AND direct_origin_detail = regexp_replace(btrim(direct_origin_detail), "
            "'[[:space:]]+', ' ', 'g') AND direct_origin_detail !~ '[[:cntrl:]'))) "
            "OR (direct_origin_kind IS DISTINCT FROM 'other' AND direct_origin_detail IS NULL)",
            name=f"ck_{table}_direct_origin_detail",
        ),
        sa.CheckConstraint(
            "(collection_entry_date_precision IS NULL AND collection_entry_date_year IS NULL "
            "AND collection_entry_date_month IS NULL AND collection_entry_date_day IS NULL) OR ("
            "collection_entry_date_year BETWEEN 1 AND 9999 AND ("
            "(collection_entry_date_precision = 'year' "
            "AND collection_entry_date_month IS NULL AND collection_entry_date_day IS NULL) OR "
            "(collection_entry_date_precision = 'month' "
            "AND collection_entry_date_month BETWEEN 1 AND 12 "
            "AND collection_entry_date_day IS NULL) OR "
            "(collection_entry_date_precision = 'day' "
            "AND collection_entry_date_month BETWEEN 1 AND 12 "
            "AND collection_entry_date_day BETWEEN 1 AND 31 "
            "AND make_date(collection_entry_date_year, collection_entry_date_month, "
            "collection_entry_date_day) IS NOT NULL))) IS TRUE",
            name=f"ck_{table}_collection_entry_date",
        ),
        sa.CheckConstraint(f"lifecycle IN ({lifecycles})", name=f"ck_{table}_lifecycle"),
        sa.CheckConstraint(
            "notes IS NULL OR (char_length(notes) BETWEEN 1 AND 20000 "
            "AND notes = btrim(notes) "
            "AND regexp_replace(notes, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
            name=f"ck_{table}_notes",
        ),
    )


def _columns(*, group: bool) -> list[sa.Column[object]]:
    columns: list[sa.Column[object]] = [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("botanical_identity_id", sa.Uuid(), nullable=False),
        sa.Column("originating_sowing_id", sa.Uuid(), nullable=True),
        sa.Column("direct_origin_kind", sa.String(length=32), nullable=True),
        sa.Column("direct_origin_detail", sa.String(length=255), nullable=True),
        sa.Column("supplier_id", sa.Uuid(), nullable=True),
        sa.Column("material_provenance_place_id", sa.Uuid(), nullable=True),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("collection_entry_date_precision", sa.String(length=8), nullable=True),
        sa.Column("collection_entry_date_year", sa.SmallInteger(), nullable=True),
        sa.Column("collection_entry_date_month", sa.SmallInteger(), nullable=True),
        sa.Column("collection_entry_date_day", sa.SmallInteger(), nullable=True),
    ]
    if group:
        columns.extend(
            [
                sa.Column("quantity_value", sa.Integer(), nullable=True),
                sa.Column("quantity_is_approximate", sa.Boolean(), nullable=True),
            ]
        )
    columns.extend(
        [
            sa.Column("location_id", sa.Uuid(), nullable=True),
            sa.Column("lifecycle", sa.String(length=16), server_default="active", nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        ]
    )
    return columns


def _foreign_keys(table: str) -> tuple[sa.ForeignKeyConstraint, ...]:
    return tuple(
        sa.ForeignKeyConstraint(
            [column],
            [f"{target}.id"],
            name=op.f(f"fk_{table}_{column}_{target}"),
            ondelete="RESTRICT",
        )
        for column, target in (
            ("botanical_identity_id", "botanical_identities"),
            ("originating_sowing_id", "sowings"),
            ("supplier_id", "suppliers"),
            ("material_provenance_place_id", "geographic_places"),
            ("location_id", "locations"),
        )
    )


def upgrade() -> None:
    op.create_table(
        "plants",
        *_columns(group=False),
        *_common_constraints("plants", "'active', 'dead', 'lost', 'discarded'"),
        *_foreign_keys("plants"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plants")),
    )
    op.create_table(
        "plant_groups",
        *_columns(group=True),
        *_common_constraints("plant_groups", "'active', 'completed', 'dead', 'lost', 'discarded'"),
        sa.CheckConstraint(
            "((quantity_value IS NULL AND quantity_is_approximate IS NULL) OR "
            "(quantity_value > 0 AND quantity_is_approximate IS NOT NULL) OR "
            "(quantity_value = 0 AND quantity_is_approximate = false "
            "AND lifecycle IN ('completed', 'dead', 'discarded'))) IS TRUE",
            name="ck_plant_groups_quantity",
        ),
        *_foreign_keys("plant_groups"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plant_groups")),
    )
    for table in ("plants", "plant_groups"):
        for column in (
            "botanical_identity_id",
            "originating_sowing_id",
            "supplier_id",
            "material_provenance_place_id",
            "location_id",
            "lifecycle",
        ):
            op.create_index(op.f(f"ix_{table}_{column}"), table, [column], unique=False)


def downgrade() -> None:
    for table in ("plant_groups", "plants"):
        for column in (
            "lifecycle",
            "location_id",
            "material_provenance_place_id",
            "supplier_id",
            "originating_sowing_id",
            "botanical_identity_id",
        ):
            op.drop_index(op.f(f"ix_{table}_{column}"), table_name=table)
        op.drop_table(table)
