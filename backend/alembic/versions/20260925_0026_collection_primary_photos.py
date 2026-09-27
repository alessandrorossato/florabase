"""Add explicit primary collection-photo designations.

Revision ID: 20260925_0026
Revises: 20260925_0025
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260925_0026"
down_revision: str | None = "20260925_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    table = "collection_primary_photos"
    op.create_table(
        table,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("seed_lot_id", sa.Uuid(), sa.ForeignKey("seed_lots.id", ondelete="RESTRICT")),
        sa.Column("plant_id", sa.Uuid(), sa.ForeignKey("plants.id", ondelete="RESTRICT")),
        sa.Column(
            "plant_group_id", sa.Uuid(), sa.ForeignKey("plant_groups.id", ondelete="RESTRICT")
        ),
        sa.Column(
            "local_collection_photo_id",
            sa.Uuid(),
            sa.ForeignKey("local_collection_photos.id", ondelete="CASCADE"),
        ),
        sa.Column(
            "external_image_reference_id",
            sa.Uuid(),
            sa.ForeignKey("external_image_references.id", ondelete="CASCADE"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "num_nonnulls(seed_lot_id, plant_id, plant_group_id) = 1",
            name="ck_collection_primary_photos_exactly_one_target",
        ),
        sa.CheckConstraint(
            "num_nonnulls(local_collection_photo_id, external_image_reference_id) = 1",
            name="ck_collection_primary_photos_exactly_one_source",
        ),
        sa.UniqueConstraint("seed_lot_id", name="uq_collection_primary_photos_seed_lot_id"),
        sa.UniqueConstraint("plant_id", name="uq_collection_primary_photos_plant_id"),
        sa.UniqueConstraint("plant_group_id", name="uq_collection_primary_photos_plant_group_id"),
        sa.UniqueConstraint(
            "local_collection_photo_id", name="uq_collection_primary_photos_local_id"
        ),
        sa.UniqueConstraint(
            "external_image_reference_id", name="uq_collection_primary_photos_external_id"
        ),
    )


def downgrade() -> None:
    op.drop_table("collection_primary_photos")
