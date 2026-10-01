"""Optional persistent snapshots of external references; never fetch during migration.

Revision ID: 20261001_0028
Revises: 20261001_0027
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261001_0028"
down_revision: str | None = "20261001_0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("media_assets", sa.Column("fetched_at", sa.DateTime(timezone=True)))
    op.add_column("media_assets", sa.Column("copy_cleanup_attachment_id", sa.Uuid()))
    op.create_foreign_key(
        "fk_media_copy_cleanup_attachment",
        "media_assets",
        "attachments",
        ["copy_cleanup_attachment_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_media_copy_cleanup_attachment", "media_assets", ["copy_cleanup_attachment_id"]
    )
    op.drop_constraint("ck_media_assets_source", "media_assets")
    op.create_check_constraint(
        "ck_media_assets_source",
        "media_assets",
        "(kind = 'local' AND attachment_id IS NOT NULL AND image_url IS NULL AND source_url IS "
        "NULL) OR (kind = 'external' AND image_url IS NOT NULL AND source_url IS NOT NULL AND "
        "attribution IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_media_assets_local_copy",
        "media_assets",
        "(kind = 'local' AND fetched_at IS NULL AND copy_cleanup_attachment_id IS NULL) OR "
        "(kind = 'external' AND ((attachment_id IS NULL AND fetched_at IS NULL) OR "
        "(attachment_id IS NOT NULL AND fetched_at IS NOT NULL)))",
    )
    op.create_check_constraint(
        "ck_media_assets_distinct_copy_cleanup",
        "media_assets",
        "copy_cleanup_attachment_id IS NULL OR copy_cleanup_attachment_id <> attachment_id",
    )


def downgrade() -> None:
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM media_assets WHERE kind = 'external' AND (attachment_id "
            "IS NOT NULL OR copy_cleanup_attachment_id IS NOT NULL))"
        )
    ):
        raise RuntimeError("Remove external local copies and complete cleanup before downgrading.")
    op.drop_constraint("ck_media_assets_local_copy", "media_assets")
    op.drop_constraint("ck_media_assets_distinct_copy_cleanup", "media_assets")
    op.drop_constraint("ck_media_assets_source", "media_assets")
    op.create_check_constraint(
        "ck_media_assets_source",
        "media_assets",
        "(kind = 'local' AND attachment_id IS NOT NULL AND image_url IS NULL AND source_url IS "
        "NULL) OR (kind = 'external' AND attachment_id IS NULL AND image_url IS NOT NULL AND "
        "source_url IS NOT NULL AND attribution IS NOT NULL)",
    )
    op.drop_constraint("uq_media_copy_cleanup_attachment", "media_assets")
    op.drop_constraint("fk_media_copy_cleanup_attachment", "media_assets")
    op.drop_column("media_assets", "copy_cleanup_attachment_id")
    op.drop_column("media_assets", "fetched_at")
