"""Supplier is an explicit shared-media target; no inferred links or asset changes.

Revision ID: 20261005_0033
Revises: 20261004_0032
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261005_0033"
down_revision: str | None = "20261004_0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LINK_TARGETS = "seed_lot_id, sowing_id, plant_id, plant_group_id, event_id, harvest_id"
PRIMARY_TARGETS = "seed_lot_id, plant_id, plant_group_id, harvest_id"


def _identity_guard(*, supplier: bool) -> None:
    # Replace only the identity guard; active-media/deletion/source-kind guards stay intact.
    columns = (
        "media_asset_id, source_kind, seed_lot_id, sowing_id, plant_id, plant_group_id, event_id"
    )
    if supplier:
        columns += ", harvest_id, supplier_id"
    new = ", ".join(f"NEW.{column}" for column in columns.split(", "))
    old = ", ".join(f"OLD.{column}" for column in columns.split(", "))
    op.execute(f"""
        CREATE OR REPLACE FUNCTION florabase_media_link_identity() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF ({new}) IS DISTINCT FROM ({old}) THEN
                RAISE EXCEPTION 'media link identity is immutable; unlink and create a new link'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END; $$;
    """)


def upgrade() -> None:
    for table, targets in (
        ("record_media_links", LINK_TARGETS),
        ("collection_primary_photos", PRIMARY_TARGETS),
    ):
        op.add_column(table, sa.Column("supplier_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            f"fk_{table}_supplier",
            table,
            "suppliers",
            ["supplier_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.drop_constraint(f"ck_{table}_exactly_one_target", table)
        op.create_check_constraint(
            f"ck_{table}_exactly_one_target",
            table,
            f"num_nonnulls({targets}, supplier_id) = 1",
        )
    op.create_index("ix_record_media_links_supplier_id", "record_media_links", ["supplier_id"])
    for prefix, columns in (
        ("asset", ["media_asset_id", "supplier_id"]),
        ("id", ["id", "supplier_id"]),
    ):
        op.create_unique_constraint(
            f"uq_record_media_links_{prefix}_supplier_id", "record_media_links", columns
        )
    op.create_unique_constraint(
        "uq_collection_primary_photos_supplier_id", "collection_primary_photos", ["supplier_id"]
    )
    for source in ("local_collection_photo_id", "external_image_reference_id"):
        op.create_foreign_key(
            f"fk_primary_{source}_supplier_id",
            "collection_primary_photos",
            "record_media_links",
            [source, "supplier_id"],
            ["id", "supplier_id"],
            ondelete="CASCADE",
        )
    _identity_guard(supplier=True)


def downgrade() -> None:
    # Refuse before any DDL, including malformed primary-only state from privileged SQL.
    if op.get_bind().scalar(
        sa.text("""
        SELECT EXISTS (SELECT 1 FROM record_media_links WHERE supplier_id IS NOT NULL)
            OR EXISTS (SELECT 1 FROM collection_primary_photos WHERE supplier_id IS NOT NULL)
    """)
    ):
        raise RuntimeError(
            "Supplier media history exists; unlink Supplier media explicitly before downgrade."
        )
    _identity_guard(supplier=False)
    for source in ("local_collection_photo_id", "external_image_reference_id"):
        op.drop_constraint(f"fk_primary_{source}_supplier_id", "collection_primary_photos")
    op.drop_constraint("uq_collection_primary_photos_supplier_id", "collection_primary_photos")
    for prefix in ("asset", "id"):
        op.drop_constraint(f"uq_record_media_links_{prefix}_supplier_id", "record_media_links")
    op.drop_index("ix_record_media_links_supplier_id", "record_media_links")
    for table, targets in (
        ("collection_primary_photos", PRIMARY_TARGETS),
        ("record_media_links", LINK_TARGETS),
    ):
        op.drop_constraint(f"ck_{table}_exactly_one_target", table)
        op.drop_constraint(f"fk_{table}_supplier", table)
        op.drop_column(table, "supplier_id")
        op.create_check_constraint(
            f"ck_{table}_exactly_one_target", table, f"num_nonnulls({targets}) = 1"
        )
