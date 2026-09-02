"""Add concrete PlantGroup origin for extracted Plants.

Revision ID: 20260901_0013
Revises: 20260901_0012
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260901_0013"
down_revision: str | None = "20260901_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("plants", sa.Column("originating_plant_group_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_plants_originating_plant_group_id_plant_groups"),
        "plants",
        "plant_groups",
        ["originating_plant_group_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_plants_originating_plant_group_id"),
        "plants",
        ["originating_plant_group_id"],
        unique=False,
    )
    op.drop_constraint("ck_plants_origin", "plants", type_="check")
    op.create_check_constraint(
        "ck_plants_origin",
        "plants",
        "((originating_plant_group_id IS NOT NULL AND originating_sowing_id IS NULL "
        "AND direct_origin_kind IS NULL AND direct_origin_detail IS NULL "
        "AND supplier_id IS NULL AND material_provenance_place_id IS NULL) OR "
        "(originating_plant_group_id IS NULL AND ((originating_sowing_id IS NOT NULL "
        "AND direct_origin_kind IS NULL AND direct_origin_detail IS NULL AND supplier_id IS NULL "
        "AND material_provenance_place_id IS NULL) OR (originating_sowing_id IS NULL "
        "AND direct_origin_kind IN ('purchased', 'gift_exchange', 'collection_produced', "
        "'other', 'unknown'))))) IS TRUE",
    )


def downgrade() -> None:
    op.drop_constraint("ck_plants_origin", "plants", type_="check")
    op.execute(
        "UPDATE plants SET direct_origin_kind = 'unknown' "
        "WHERE originating_plant_group_id IS NOT NULL"
    )
    op.create_check_constraint(
        "ck_plants_origin",
        "plants",
        "((originating_sowing_id IS NOT NULL AND direct_origin_kind IS NULL "
        "AND direct_origin_detail IS NULL AND supplier_id IS NULL "
        "AND material_provenance_place_id IS NULL) OR "
        "(originating_sowing_id IS NULL AND direct_origin_kind IN "
        "('purchased', 'gift_exchange', 'collection_produced', 'other', 'unknown'))) IS TRUE",
    )
    op.drop_index(op.f("ix_plants_originating_plant_group_id"), table_name="plants")
    op.drop_constraint(
        op.f("fk_plants_originating_plant_group_id_plant_groups"),
        "plants",
        type_="foreignkey",
    )
    op.drop_column("plants", "originating_plant_group_id")
