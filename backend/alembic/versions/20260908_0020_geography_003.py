"""Add finer custom geography and precise ProvenanceSites.

Revision ID: 20260908_0020
Revises: 20260907_0019
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260908_0020"
down_revision: str | None = "20260907_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _origin_constraint(table: str) -> str:
    common = (
        "((originating_sowing_id IS NOT NULL AND direct_origin_kind IS NULL "
        "AND direct_origin_detail IS NULL AND supplier_id IS NULL "
        "AND material_provenance_place_id IS NULL AND provenance_site_id IS NULL) OR "
        "(originating_sowing_id IS NULL AND direct_origin_kind IN "
        "('purchased', 'gift_exchange', 'collection_produced', 'other', 'unknown')))"
    )
    if table == "plant_groups":
        return f"{common} IS TRUE"
    return (
        "((originating_plant_group_id IS NOT NULL AND originating_sowing_id IS NULL "
        "AND direct_origin_kind IS NULL AND direct_origin_detail IS NULL "
        "AND supplier_id IS NULL AND material_provenance_place_id IS NULL "
        "AND provenance_site_id IS NULL) OR "
        f"(originating_plant_group_id IS NULL AND {common})) IS TRUE"
    )


def _old_origin_constraint(table: str) -> str:
    common = (
        "((originating_sowing_id IS NOT NULL AND direct_origin_kind IS NULL "
        "AND direct_origin_detail IS NULL AND supplier_id IS NULL "
        "AND material_provenance_place_id IS NULL) OR "
        "(originating_sowing_id IS NULL AND direct_origin_kind IN "
        "('purchased', 'gift_exchange', 'collection_produced', 'other', 'unknown')))"
    )
    if table == "plant_groups":
        return f"{common} IS TRUE"
    return (
        "((originating_plant_group_id IS NOT NULL AND originating_sowing_id IS NULL "
        "AND direct_origin_kind IS NULL AND direct_origin_detail IS NULL "
        "AND supplier_id IS NULL AND material_provenance_place_id IS NULL) OR "
        f"(originating_plant_group_id IS NULL AND {common})) IS TRUE"
    )


def upgrade() -> None:
    op.add_column("geographic_places", sa.Column("place_type", sa.String(length=32), nullable=True))
    op.execute(
        "UPDATE geographic_places SET place_type = 'other_named_area' WHERE place_kind = 'custom'"
    )
    op.create_check_constraint(
        "ck_geographic_places_type",
        "geographic_places",
        "(place_kind = 'canonical' AND place_type IS NULL) OR "
        "(place_kind = 'custom' AND place_type IN "
        "('city_town', 'locality', 'other_named_area'))",
    )
    op.create_table(
        "provenance_sites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("geographic_place_id", sa.Uuid(), nullable=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("coordinate_accuracy_m", sa.Numeric(12, 3), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "char_length(name) BETWEEN 1 AND 255 AND "
            "name = regexp_replace(btrim(name), '[[:space:]]+', ' ', 'g') AND "
            "name !~ '[[:cntrl:]]'",
            name="ck_provenance_sites_name",
        ),
        sa.CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL) OR "
            "(latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180) IS TRUE",
            name="ck_provenance_sites_coordinates",
        ),
        sa.CheckConstraint(
            "coordinate_accuracy_m IS NULL OR "
            "(latitude IS NOT NULL AND longitude IS NOT NULL AND coordinate_accuracy_m >= 0)",
            name="ck_provenance_sites_accuracy",
        ),
        sa.CheckConstraint(
            "notes IS NULL OR (char_length(notes) BETWEEN 1 AND 20000 AND notes = btrim(notes) "
            "AND regexp_replace(notes, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
            name="ck_provenance_sites_notes",
        ),
        sa.ForeignKeyConstraint(
            ["geographic_place_id"],
            ["geographic_places.id"],
            name=op.f("fk_provenance_sites_geographic_place_id_geographic_places"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_provenance_sites")),
    )
    op.create_index(
        op.f("ix_provenance_sites_geographic_place_id"),
        "provenance_sites",
        ["geographic_place_id"],
    )
    for table in ("seed_lots", "plants", "plant_groups"):
        op.add_column(table, sa.Column("provenance_site_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            op.f(f"fk_{table}_provenance_site_id_provenance_sites"),
            table,
            "provenance_sites",
            ["provenance_site_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_index(op.f(f"ix_{table}_provenance_site_id"), table, ["provenance_site_id"])
    for table in ("plants", "plant_groups"):
        op.drop_constraint(f"ck_{table}_origin", table, type_="check")
        op.create_check_constraint(f"ck_{table}_origin", table, _origin_constraint(table))


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM provenance_sites)
               OR EXISTS (SELECT 1 FROM seed_lots WHERE provenance_site_id IS NOT NULL)
               OR EXISTS (SELECT 1 FROM plants WHERE provenance_site_id IS NOT NULL)
               OR EXISTS (SELECT 1 FROM plant_groups WHERE provenance_site_id IS NOT NULL) THEN
                RAISE EXCEPTION 'cannot downgrade while ProvenanceSite data or references exist';
            END IF;
        END
        $$
        """
    )
    for table in ("plants", "plant_groups"):
        op.drop_constraint(f"ck_{table}_origin", table, type_="check")
        op.create_check_constraint(
            f"ck_{table}_origin",
            table,
            _old_origin_constraint(table),
        )
    for table in ("plant_groups", "plants", "seed_lots"):
        op.drop_index(op.f(f"ix_{table}_provenance_site_id"), table_name=table)
        op.drop_constraint(
            op.f(f"fk_{table}_provenance_site_id_provenance_sites"), table, type_="foreignkey"
        )
        op.drop_column(table, "provenance_site_id")
    op.drop_index(op.f("ix_provenance_sites_geographic_place_id"), table_name="provenance_sites")
    op.drop_table("provenance_sites")
    op.drop_constraint("ck_geographic_places_type", "geographic_places", type_="check")
    op.drop_column("geographic_places", "place_type")
