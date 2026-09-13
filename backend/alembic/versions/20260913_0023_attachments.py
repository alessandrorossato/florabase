"""Add guarded local attachment metadata.

Revision ID: 20260913_0023
Revises: 20260909_0022
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260913_0023"
down_revision: str | None = "20260909_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("media_type", sa.String(length=32), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "storage_key ~ '^objects/[0-9a-f]{2}/[0-9a-f]{32}$'",
            name="ck_attachments_storage_key",
        ),
        sa.CheckConstraint(
            "char_length(original_filename) BETWEEN 1 AND 255 "
            "AND original_filename = btrim(original_filename) "
            "AND original_filename !~ '[[:cntrl:]/\\\\]'",
            name="ck_attachments_original_filename",
        ),
        sa.CheckConstraint(
            "media_type IN ('image/jpeg', 'image/png', 'image/webp')",
            name="ck_attachments_media_type",
        ),
        sa.CheckConstraint(
            "byte_size BETWEEN 1 AND 26214400",
            name="ck_attachments_byte_size",
        ),
        sa.CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="ck_attachments_sha256"),
        sa.CheckConstraint(
            "state IN ('active', 'pending_delete')",
            name="ck_attachments_state",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attachments")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_attachments_storage_key")),
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM attachments) THEN
                RAISE EXCEPTION 'cannot downgrade while attachment metadata exists';
            END IF;
        END
        $$
        """
    )
    op.drop_table("attachments")
