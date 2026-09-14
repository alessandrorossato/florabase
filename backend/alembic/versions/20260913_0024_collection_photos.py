"""Relate collection photos and external image references.

Revision ID: 20260913_0024
Revises: 20260913_0023
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260913_0024"
down_revision: str | None = "20260913_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TARGETS = (
    ("seed_lot_id", "seed_lots"),
    ("sowing_id", "sowings"),
    ("plant_id", "plants"),
    ("plant_group_id", "plant_groups"),
    ("event_id", "events"),
)


def _target_columns() -> list[sa.Column[object]]:
    return [sa.Column(name, sa.Uuid(), nullable=True) for name, _ in TARGETS]


def _target_constraints(table: str) -> list[sa.Constraint]:
    constraints: list[sa.Constraint] = [
        sa.CheckConstraint(
            "num_nonnulls(seed_lot_id, sowing_id, plant_id, plant_group_id, event_id) = 1",
            name=f"ck_{table}_exactly_one_target",
        )
    ]
    constraints.extend(
        sa.ForeignKeyConstraint(
            [column],
            [f"{target}.id"],
            name=op.f(f"fk_{table}_{column}_{target}"),
            ondelete="RESTRICT",
        )
        for column, target in TARGETS
    )
    return constraints


def _optional_text(table: str, column: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(
        f"{column} IS NULL OR (char_length({column}) BETWEEN 1 AND 2000 "
        f"AND {column} = btrim({column}) "
        f"AND regexp_replace({column}, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
        name=f"ck_{table}_{column}",
    )


def upgrade() -> None:
    local = "local_collection_photos"
    op.create_table(
        local,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("attachment_id", sa.Uuid(), nullable=False),
        *_target_columns(),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("attribution", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        *_target_constraints(local),
        _optional_text(local, "caption"),
        _optional_text(local, "attribution"),
        sa.ForeignKeyConstraint(
            ["attachment_id"],
            ["attachments.id"],
            name=op.f("fk_local_collection_photos_attachment_id_attachments"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_local_collection_photos")),
        sa.UniqueConstraint("attachment_id", name=op.f("uq_local_collection_photos_attachment_id")),
    )
    external = "external_image_references"
    op.create_table(
        external,
        sa.Column("id", sa.Uuid(), nullable=False),
        *_target_columns(),
        sa.Column("image_url", sa.String(length=2048), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("attribution", sa.Text(), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        *_target_constraints(external),
        _optional_text(external, "caption"),
        sa.CheckConstraint(
            "char_length(attribution) BETWEEN 1 AND 2000 AND attribution = btrim(attribution) "
            "AND regexp_replace(attribution, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]'",
            name="ck_external_image_references_attribution",
        ),
        sa.CheckConstraint(
            "char_length(image_url) BETWEEN 1 AND 2048 AND image_url ~ '^https://[^[:space:]]+$'",
            name="ck_external_image_references_image_url",
        ),
        sa.CheckConstraint(
            "char_length(source_url) BETWEEN 1 AND 2048 AND source_url ~ '^https://[^[:space:]]+$'",
            name="ck_external_image_references_source_url",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_external_image_references")),
    )
    for table in (local, external):
        for column, _ in TARGETS:
            op.create_index(op.f(f"ix_{table}_{column}"), table, [column], unique=False)
    op.create_index(
        op.f("ix_local_collection_photos_attachment_id"),
        local,
        ["attachment_id"],
        unique=False,
    )
    cover = "botanical_identity_cover_images"
    op.create_table(
        cover,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("botanical_identity_id", sa.Uuid(), nullable=False),
        sa.Column("source_mode", sa.String(length=16), nullable=False),
        sa.Column("attachment_id", sa.Uuid(), nullable=True),
        sa.Column("image_url", sa.String(length=2048), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("attribution", sa.Text(), nullable=True),
        sa.Column("licence_label", sa.Text(), nullable=True),
        sa.Column("licence_url", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source_mode IN ('local', 'external')",
            name="ck_botanical_identity_cover_images_source_mode",
        ),
        sa.CheckConstraint(
            "(source_mode = 'local' AND attachment_id IS NOT NULL "
            "AND image_url IS NULL AND source_url IS NULL AND attribution IS NULL "
            "AND licence_label IS NULL AND licence_url IS NULL) OR "
            "(source_mode = 'external' AND attachment_id IS NULL "
            "AND image_url IS NOT NULL AND source_url IS NOT NULL "
            "AND attribution IS NOT NULL)",
            name="ck_botanical_identity_cover_images_source_fields",
        ),
        sa.CheckConstraint(
            "attribution IS NULL OR (char_length(attribution) BETWEEN 1 AND 2000 "
            "AND attribution = btrim(attribution) "
            "AND regexp_replace(attribution, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
            name="ck_botanical_identity_cover_images_attribution",
        ),
        _optional_text(cover, "licence_label"),
        sa.CheckConstraint(
            "image_url IS NULL OR (char_length(image_url) BETWEEN 1 AND 2048 "
            "AND image_url ~ '^https://[^[:space:]]+$')",
            name="ck_botanical_identity_cover_images_image_url",
        ),
        sa.CheckConstraint(
            "source_url IS NULL OR (char_length(source_url) BETWEEN 1 AND 2048 "
            "AND source_url ~ '^https://[^[:space:]]+$')",
            name="ck_botanical_identity_cover_images_source_url",
        ),
        sa.CheckConstraint(
            "licence_url IS NULL OR (char_length(licence_url) BETWEEN 1 AND 2048 "
            "AND licence_url ~ '^https://[^[:space:]]+$')",
            name="ck_botanical_identity_cover_images_licence_url",
        ),
        sa.ForeignKeyConstraint(
            ["botanical_identity_id"],
            ["botanical_identities.id"],
            name=op.f(
                "fk_botanical_identity_cover_images_botanical_identity_id_botanical_identities"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["attachment_id"],
            ["attachments.id"],
            name=op.f("fk_botanical_identity_cover_images_attachment_id_attachments"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_botanical_identity_cover_images")),
        sa.UniqueConstraint(
            "botanical_identity_id",
            name=op.f("uq_botanical_identity_cover_images_botanical_identity_id"),
        ),
        sa.UniqueConstraint(
            "attachment_id", name=op.f("uq_botanical_identity_cover_images_attachment_id")
        ),
    )
    op.create_index(
        op.f("ix_botanical_identity_cover_images_botanical_identity_id"),
        cover,
        ["botanical_identity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_botanical_identity_cover_images_attachment_id"),
        cover,
        ["attachment_id"],
        unique=False,
    )
    op.execute(
        """
        CREATE FUNCTION florabase_enforce_attachment_image_owner()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.attachment_id IS NULL THEN
                RETURN NEW;
            END IF;

            -- Serialise cross-table ownership checks for this Attachment. Individual
            -- unique constraints cannot prevent a direct write from owning the same
            -- Attachment through both image concepts.
            PERFORM pg_advisory_xact_lock(hashtextextended(NEW.attachment_id::text, 0));

            IF TG_TABLE_NAME = 'local_collection_photos' AND EXISTS (
                SELECT 1
                FROM botanical_identity_cover_images
                WHERE attachment_id = NEW.attachment_id
            ) THEN
                RAISE EXCEPTION 'attachment image ownership is already a botanical identity cover'
                    USING ERRCODE = '23505';
            ELSIF TG_TABLE_NAME = 'botanical_identity_cover_images' AND EXISTS (
                SELECT 1
                FROM local_collection_photos
                WHERE attachment_id = NEW.attachment_id
            ) THEN
                RAISE EXCEPTION 'attachment image ownership is already a collection photo'
                    USING ERRCODE = '23505';
            END IF;

            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_local_collection_photos_attachment_image_owner
        BEFORE INSERT OR UPDATE OF attachment_id ON local_collection_photos
        FOR EACH ROW EXECUTE FUNCTION florabase_enforce_attachment_image_owner();
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_botanical_identity_cover_images_attachment_image_owner
        BEFORE INSERT OR UPDATE OF attachment_id ON botanical_identity_cover_images
        FOR EACH ROW EXECUTE FUNCTION florabase_enforce_attachment_image_owner();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM local_collection_photos)
               OR EXISTS (SELECT 1 FROM external_image_references)
               OR EXISTS (SELECT 1 FROM botanical_identity_cover_images) THEN
                RAISE EXCEPTION 'cannot downgrade while photo or identity cover metadata exists';
            END IF;
        END
        $$
        """
    )
    op.drop_table("botanical_identity_cover_images")
    op.drop_table("external_image_references")
    op.drop_table("local_collection_photos")
    op.execute("DROP FUNCTION florabase_enforce_attachment_image_owner()")
