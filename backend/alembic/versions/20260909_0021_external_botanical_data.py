"""Add external botanical taxon links and provider cache.

Revision ID: 20260909_0021
Revises: 20260908_0020
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260909_0021"
down_revision: str | None = "20260908_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "external_taxon_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("botanical_identity_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("scientific_name", sa.String(length=500), nullable=False),
        sa.Column("canonical_name", sa.String(length=500), nullable=True),
        sa.Column("authorship", sa.String(length=255), nullable=True),
        sa.Column("rank", sa.String(length=64), nullable=True),
        sa.Column("taxonomic_status", sa.String(length=64), nullable=True),
        sa.Column("accepted_external_id", sa.String(length=255), nullable=True),
        sa.Column("accepted_name", sa.String(length=500), nullable=True),
        sa.Column("kingdom", sa.String(length=255), nullable=True),
        sa.Column("phylum", sa.String(length=255), nullable=True),
        sa.Column("class_name", sa.String(length=255), nullable=True),
        sa.Column("order_name", sa.String(length=255), nullable=True),
        sa.Column("family", sa.String(length=255), nullable=True),
        sa.Column("genus", sa.String(length=255), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_refreshed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_refresh_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("refresh_error", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "provider = lower(provider) AND char_length(provider) BETWEEN 1 AND 32",
            name="ck_external_taxon_links_provider",
        ),
        sa.CheckConstraint(
            "char_length(external_id) BETWEEN 1 AND 255", name="ck_external_taxon_links_external_id"
        ),
        sa.ForeignKeyConstraint(
            ["botanical_identity_id"],
            ["botanical_identities.id"],
            name="fk_external_taxon_links_identity",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_external_taxon_links")),
        sa.UniqueConstraint(
            "botanical_identity_id", "provider", name="uq_external_taxon_links_identity_provider"
        ),
    )
    op.create_index(
        "ix_external_taxon_links_identity", "external_taxon_links", ["botanical_identity_id"]
    )
    op.create_table(
        "external_provider_cache",
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("resource_key", sa.String(length=255), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint(
            "provider = lower(provider) AND char_length(provider) BETWEEN 1 AND 32",
            name="ck_external_provider_cache_provider",
        ),
        sa.CheckConstraint(
            "char_length(resource_key) BETWEEN 1 AND 255",
            name="ck_external_provider_cache_resource_key",
        ),
        sa.PrimaryKeyConstraint(
            "provider", "resource_key", name=op.f("pk_external_provider_cache")
        ),
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM external_taxon_links)
               OR EXISTS (SELECT 1 FROM external_provider_cache) THEN
                RAISE EXCEPTION
                    'cannot downgrade while external botanical link or cache data exists';
            END IF;
        END
        $$
        """
    )
    op.drop_table("external_provider_cache")
    op.drop_index("ix_external_taxon_links_identity", table_name="external_taxon_links")
    op.drop_table("external_taxon_links")
