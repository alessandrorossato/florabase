"""Split owned photos into reusable assets and exact record links.

Revision ID: 20261001_0027
Revises: 20260925_0026

Original binaries and Attachment identifiers/keys never move. Downgrade is
intentionally guarded: populated media cannot be represented losslessly by the
old single-owner model. Restore the paired backup to reverse a populated upgrade.
"""

from collections.abc import Sequence
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import sqlalchemy as sa

from alembic import op

revision: str = "20261001_0027"
down_revision: str | None = "20260925_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
TARGETS = ("seed_lot", "sowing", "plant", "plant_group", "event")
TABLES = ("seed_lots", "sowings", "plants", "plant_groups", "events")


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column(
            "attachment_id",
            sa.Uuid(),
            sa.ForeignKey("attachments.id", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.Column("title", sa.Text()),
        sa.Column("image_url", sa.String(2048)),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("attribution", sa.Text()),
        sa.Column("licence_label", sa.Text()),
        sa.Column("licence_url", sa.String(2048)),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('local', 'external')", name="ck_media_assets_kind"),
        sa.CheckConstraint("state IN ('active', 'pending_delete')", name="ck_media_assets_state"),
        sa.CheckConstraint(
            "(kind = 'local' AND attachment_id IS NOT NULL AND image_url IS NULL AND "
            "source_url IS NULL) OR (kind = 'external' AND attachment_id IS NULL AND "
            "image_url IS NOT NULL AND source_url IS NOT NULL AND attribution IS NOT NULL)",
            name="ck_media_assets_source",
        ),
        sa.CheckConstraint("width IS NULL OR width > 0", name="ck_media_assets_width"),
        sa.CheckConstraint("height IS NULL OR height > 0", name="ck_media_assets_height"),
        *[
            sa.CheckConstraint(
                f"{c} IS NULL OR (char_length({c}) BETWEEN 1 AND 2000 AND {c} = btrim({c}) "
                f"AND regexp_replace({c}, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
                name=f"ck_media_assets_{c}",
            )
            for c in ("title", "attribution", "licence_label")
        ],
        *[
            sa.CheckConstraint(
                f"{c} IS NULL OR (char_length({c}) BETWEEN 1 AND 2048 AND {c} ~ '^https://[^[:space:]]+$')",
                name=f"ck_media_assets_{c}",
            )
            for c in ("image_url", "source_url", "licence_url")
        ],
        sa.UniqueConstraint("id", "kind", name="uq_media_assets_id_kind"),
    )
    op.create_index("ix_media_assets_created_at_id", "media_assets", ["created_at", "id"])
    op.create_table(
        "record_media_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("media_asset_id", sa.Uuid(), nullable=False),
        sa.Column("source_kind", sa.String(16), nullable=False),
        *[
            sa.Column(f"{target}_id", sa.Uuid(), sa.ForeignKey(f"{table}.id", ondelete="RESTRICT"))
            for target, table in zip(TARGETS, TABLES, strict=True)
        ],
        sa.Column("caption", sa.Text()),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "num_nonnulls(seed_lot_id, sowing_id, plant_id, plant_group_id, event_id) = 1",
            name="ck_record_media_links_exactly_one_target",
        ),
        sa.CheckConstraint(
            "source_kind IN ('local', 'external')", name="ck_record_media_links_kind"
        ),
        sa.CheckConstraint("display_order >= 0", name="ck_record_media_links_order"),
        sa.CheckConstraint(
            "caption IS NULL OR (char_length(caption) BETWEEN 1 AND 2000 AND caption = "
            "btrim(caption) AND regexp_replace(caption, E'[\\n\\t]', '', 'g') !~ "
            "'[[:cntrl:]]')",
            name="ck_record_media_links_caption",
        ),
        sa.ForeignKeyConstraint(
            ["media_asset_id", "source_kind"],
            ["media_assets.id", "media_assets.kind"],
            ondelete="RESTRICT",
            name="fk_record_media_links_asset_kind",
        ),
        *[
            sa.UniqueConstraint(
                "media_asset_id", f"{target}_id", name=f"uq_record_media_links_asset_{target}_id"
            )
            for target in TARGETS
        ],
        *[
            sa.UniqueConstraint("id", f"{target}_id", name=f"uq_record_media_links_id_{target}_id")
            for target in TARGETS
        ],
    )
    for column in ("media_asset_id", *(f"{target}_id" for target in TARGETS)):
        op.create_index(f"ix_record_media_links_{column}", "record_media_links", [column])
    # One asset for EVERY existing local binary, including genuinely standalone uploads.
    op.execute("""
        INSERT INTO media_assets (id, kind, attachment_id, state, attribution,
        created_at, updated_at)
        SELECT a.id, 'local', a.id, a.state, p.attribution, a.created_at,
               coalesce(p.updated_at, c.updated_at, a.created_at)
        FROM attachments a
        LEFT JOIN local_collection_photos p ON p.attachment_id = a.id
        LEFT JOIN botanical_identity_cover_images c ON c.attachment_id = a.id;
        INSERT INTO media_assets (id, kind, state, image_url, source_url, attribution,
        created_at, updated_at)
        SELECT id, 'external', 'active', image_url, source_url, attribution, created_at,
        updated_at FROM external_image_references;
        INSERT INTO media_assets (id, kind, state, image_url, source_url, attribution,
        licence_label, licence_url, created_at, updated_at)
        SELECT id, 'external', 'active', image_url, source_url, attribution,
        licence_label, licence_url, created_at, updated_at
        FROM botanical_identity_cover_images WHERE source_mode = 'external';
        INSERT INTO record_media_links (id, media_asset_id, source_kind, seed_lot_id,
        sowing_id, plant_id, plant_group_id, event_id, caption, display_order,
        created_at, updated_at)
        SELECT id, asset_id, kind, seed_lot_id, sowing_id, plant_id, plant_group_id,
        event_id, caption,
               row_number() OVER (PARTITION BY seed_lot_id, sowing_id, plant_id,
               plant_group_id, event_id ORDER BY created_at, id) - 1,
               created_at, updated_at
        FROM (
            SELECT id, attachment_id AS asset_id, 'local' AS kind, seed_lot_id,
            sowing_id, plant_id, plant_group_id, event_id, caption, created_at,
            updated_at FROM local_collection_photos
            UNION ALL
            SELECT id, id, 'external', seed_lot_id, sowing_id, plant_id,
            plant_group_id, event_id, caption, created_at, updated_at FROM
            external_image_references
        ) photos;
    """)
    # Convert the cover in place after moving all source metadata to its asset.
    op.add_column("botanical_identity_cover_images", sa.Column("media_asset_id", sa.Uuid()))
    op.execute(
        "UPDATE botanical_identity_cover_images SET media_asset_id = CASE WHEN source_mode "
        "= 'local' THEN attachment_id ELSE id END"
    )
    op.alter_column("botanical_identity_cover_images", "media_asset_id", nullable=False)
    op.execute(
        "DROP TRIGGER trg_botanical_identity_cover_images_attachment_image_owner ON "
        "botanical_identity_cover_images"
    )
    op.execute(
        "DROP TRIGGER trg_local_collection_photos_attachment_image_owner ON local_collection_photos"
    )
    op.execute("DROP FUNCTION florabase_enforce_attachment_image_owner()")
    for c in (
        "source_fields",
        "attribution",
        "licence_label",
        "image_url",
        "source_url",
        "licence_url",
    ):
        op.drop_constraint(
            f"ck_botanical_identity_cover_images_{c}",
            "botanical_identity_cover_images",
            type_="check",
        )
    for c in (
        "attachment_id",
        "image_url",
        "source_url",
        "attribution",
        "licence_label",
        "licence_url",
    ):
        op.drop_column("botanical_identity_cover_images", c)
    op.create_foreign_key(
        "fk_identity_cover_asset_kind",
        "botanical_identity_cover_images",
        "media_assets",
        ["media_asset_id", "source_mode"],
        ["id", "kind"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_botanical_identity_cover_images_media_asset_id",
        "botanical_identity_cover_images",
        ["media_asset_id"],
    )
    for source in ("local_collection_photo_id", "external_image_reference_id"):
        for foreign_key in sa.inspect(op.get_bind()).get_foreign_keys("collection_primary_photos"):
            if foreign_key["constrained_columns"] == [source]:
                op.drop_constraint(
                    foreign_key["name"], "collection_primary_photos", type_="foreignkey"
                )
        op.create_foreign_key(
            f"fk_primary_{source}_link",
            "collection_primary_photos",
            "record_media_links",
            [source],
            ["id"],
            ondelete="CASCADE",
        )
        for target in ("seed_lot_id", "plant_id", "plant_group_id"):
            op.create_foreign_key(
                f"fk_primary_{source}_{target}",
                "collection_primary_photos",
                "record_media_links",
                [source, target],
                ["id", target],
                ondelete="CASCADE",
            )
    op.drop_table("local_collection_photos")
    op.drop_table("external_image_references")
    # Direct SQL cannot reference pending content. The asset lock serializes new
    # references with guarded deletion, including the separate cover relationship.
    op.execute("""
        CREATE FUNCTION florabase_require_active_media() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE asset_state text; file_state text;
        BEGIN
            SELECT m.state, a.state INTO asset_state, file_state
            FROM media_assets m LEFT JOIN attachments a ON a.id = m.attachment_id
            WHERE m.id = NEW.media_asset_id FOR UPDATE OF m;
            IF asset_state IS NULL OR asset_state <> 'active' OR (file_state IS NOT
            NULL AND file_state <> 'active') THEN
                RAISE EXCEPTION 'media asset is unavailable or pending deletion'
                USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END; $$;
        CREATE TRIGGER trg_record_media_active BEFORE INSERT OR UPDATE OF media_asset_id
        ON record_media_links FOR EACH ROW EXECUTE FUNCTION
        florabase_require_active_media();
        CREATE TRIGGER trg_cover_media_active BEFORE INSERT OR UPDATE OF media_asset_id
        ON botanical_identity_cover_images FOR EACH ROW EXECUTE FUNCTION
        florabase_require_active_media();
        CREATE FUNCTION florabase_media_link_identity() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF (NEW.media_asset_id, NEW.source_kind, NEW.seed_lot_id, NEW.sowing_id,
                NEW.plant_id, NEW.plant_group_id, NEW.event_id)
                IS DISTINCT FROM
               (OLD.media_asset_id, OLD.source_kind, OLD.seed_lot_id, OLD.sowing_id,
                OLD.plant_id, OLD.plant_group_id, OLD.event_id) THEN
                RAISE EXCEPTION 'media link identity is immutable; unlink and create a new link'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END; $$;
        CREATE TRIGGER trg_media_link_identity BEFORE UPDATE ON record_media_links
            FOR EACH ROW EXECUTE FUNCTION florabase_media_link_identity();
        CREATE FUNCTION florabase_media_delete_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.state = 'pending_delete' AND OLD.state <> 'pending_delete' AND
                (EXISTS (SELECT 1 FROM record_media_links WHERE media_asset_id = OLD.id) OR
                 EXISTS (SELECT 1 FROM botanical_identity_cover_images
                         WHERE media_asset_id = OLD.id)) THEN
                RAISE EXCEPTION 'media asset still has active references' USING ERRCODE = '23503';
            END IF;
            RETURN NEW;
        END; $$;
        CREATE TRIGGER trg_media_delete_guard BEFORE UPDATE OF state ON media_assets
            FOR EACH ROW EXECUTE FUNCTION florabase_media_delete_guard();
        CREATE FUNCTION florabase_primary_link_kind() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE expected text; actual text;
        BEGIN
            expected := CASE WHEN NEW.local_collection_photo_id IS NOT NULL THEN
            'local' ELSE 'external' END;
            SELECT source_kind INTO actual FROM record_media_links WHERE id =
            coalesce(NEW.local_collection_photo_id,
            NEW.external_image_reference_id);
            IF actual IS DISTINCT FROM expected THEN
                RAISE EXCEPTION 'primary source kind does not match linked
                media' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END; $$;
        CREATE TRIGGER trg_primary_link_kind BEFORE INSERT OR UPDATE ON
        collection_primary_photos FOR EACH ROW EXECUTE FUNCTION
        florabase_primary_link_kind();
    """)


def _restore_schema(filename: str) -> None:
    spec = spec_from_file_location("previous_attachment_schema", Path(__file__).with_name(filename))
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    module.upgrade()


def downgrade() -> None:
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM media_assets) OR EXISTS (SELECT 1 FROM record_media_links)
           OR EXISTS (SELECT 1 FROM botanical_identity_cover_images) THEN
            RAISE EXCEPTION 'cannot downgrade while shared media metadata exists;
            restore the paired pre-upgrade backup';
        END IF;
    END $$;""")
    op.drop_table("collection_primary_photos")
    op.drop_table("botanical_identity_cover_images")
    op.drop_table("record_media_links")
    op.execute("DROP FUNCTION florabase_require_active_media()")
    op.execute("DROP FUNCTION florabase_primary_link_kind()")
    op.drop_table("media_assets")
    op.execute("DROP FUNCTION IF EXISTS florabase_media_link_identity()")
    op.execute("DROP FUNCTION IF EXISTS florabase_media_delete_guard()")
    _restore_schema("20260913_0024_collection_photos.py")
    _restore_schema("20260925_0026_collection_primary_photos.py")
