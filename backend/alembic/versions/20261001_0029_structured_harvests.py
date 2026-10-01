"""Structured Harvest aggregates; historical free-form Events are untouched.

Revision ID: 20261001_0029
Revises: 20261001_0028
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261001_0029"
down_revision: str | None = "20261001_0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(r"""CREATE TABLE harvests (
	id UUID NOT NULL,
	plant_id UUID,
	plant_group_id UUID,
	event_id UUID NOT NULL,
	label VARCHAR(255),
	occurred_on_precision VARCHAR(8),
	occurred_on_year SMALLINT,
	occurred_on_month SMALLINT,
	occurred_on_day SMALLINT,
	notes TEXT,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_harvests_source CHECK (num_nonnulls(plant_id, plant_group_id) = 1),
    CONSTRAINT ck_harvests_label CHECK (label IS NULL OR (char_length(label) BETWEEN 1 AND
    255 AND label = btrim(label) AND label !~ '[[:cntrl:]]')),
    CONSTRAINT ck_harvests_notes CHECK (notes IS NULL OR (char_length(notes) BETWEEN 1 AND
    20000 AND notes = btrim(notes) AND regexp_replace(notes, E'[\n\t]', '', 'g') !~
    '[[:cntrl:]]')),
    CONSTRAINT ck_harvests_occurred_on CHECK ((occurred_on_precision IS NULL AND
    occurred_on_year IS NULL AND occurred_on_month IS NULL AND occurred_on_day IS NULL) OR
    (occurred_on_year BETWEEN 1 AND 9999 AND ((occurred_on_precision = 'year' AND
    occurred_on_month IS NULL AND occurred_on_day IS NULL) OR (occurred_on_precision =
    'month' AND occurred_on_month BETWEEN 1 AND 12 AND occurred_on_day IS NULL) OR
    (occurred_on_precision = 'day' AND occurred_on_month BETWEEN 1 AND 12 AND
    occurred_on_day BETWEEN 1 AND 31 AND make_date(occurred_on_year, occurred_on_month,
    occurred_on_day) IS NOT NULL))) IS TRUE),
	FOREIGN KEY(plant_id) REFERENCES plants (id) ON DELETE RESTRICT,
	FOREIGN KEY(plant_group_id) REFERENCES plant_groups (id) ON DELETE RESTRICT,
	UNIQUE (event_id),
	FOREIGN KEY(event_id) REFERENCES events (id) ON DELETE RESTRICT
)""")
    op.execute(r"""CREATE TABLE harvest_items (
	id UUID NOT NULL,
	harvest_id UUID NOT NULL,
	display_order INTEGER NOT NULL,
	material_kind VARCHAR(16) NOT NULL,
	description TEXT,
	quantity_kind VARCHAR(16),
	quantity_value NUMERIC,
	quantity_unit VARCHAR(8),
	quantity_is_approximate BOOLEAN,
	PRIMARY KEY (id),
	CONSTRAINT uq_harvest_items_order UNIQUE (harvest_id, display_order),
	CONSTRAINT ck_harvest_items_order CHECK (display_order >= 0),
    CONSTRAINT ck_harvest_items_material CHECK (material_kind IN ('fruit', 'flower', 'leaf',
    'root', 'seed', 'stem_or_shoot', 'whole_plant', 'other')),
    CONSTRAINT ck_harvest_items_description CHECK (description IS NULL OR
    (char_length(description) BETWEEN 1 AND 2000 AND description = btrim(description) AND
    regexp_replace(description, E'[\n\t]', '', 'g') !~ '[[:cntrl:]]')),
    CONSTRAINT ck_harvest_items_quantity CHECK (((quantity_kind IS NULL AND quantity_value
    IS NULL AND quantity_unit IS NULL AND quantity_is_approximate IS NULL) OR
    (quantity_value > 0 AND quantity_value < 'Infinity'::numeric AND quantity_is_approximate
    IS NOT NULL AND ((quantity_kind = 'item_count' AND quantity_value =
    trunc(quantity_value) AND quantity_unit IS NULL) OR (quantity_kind = 'weight' AND
    quantity_unit IN ('mg', 'g', 'kg'))))) IS TRUE),
	FOREIGN KEY(harvest_id) REFERENCES harvests (id) ON DELETE CASCADE
)""")
    op.execute("CREATE INDEX ix_harvests_plant_id ON harvests (plant_id)")
    op.execute("CREATE INDEX ix_harvests_plant_group_id ON harvests (plant_group_id)")
    op.execute("CREATE INDEX ix_harvest_items_harvest_id ON harvest_items (harvest_id)")
    op.add_column("record_media_links", sa.Column("harvest_id", sa.Uuid()))
    op.create_foreign_key(
        "fk_record_media_links_harvest",
        "record_media_links",
        "harvests",
        ["harvest_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_record_media_links_harvest_id", "record_media_links", ["harvest_id"])
    for prefix, columns in (
        ("asset", ["media_asset_id", "harvest_id"]),
        ("id", ["id", "harvest_id"]),
    ):
        op.create_unique_constraint(
            f"uq_record_media_links_{prefix}_harvest_id", "record_media_links", columns
        )
    op.drop_constraint("ck_record_media_links_exactly_one_target", "record_media_links")
    op.create_check_constraint(
        "ck_record_media_links_exactly_one_target",
        "record_media_links",
        "num_nonnulls(seed_lot_id, sowing_id, plant_id, plant_group_id, event_id, harvest_id) = 1",
    )
    op.add_column("collection_primary_photos", sa.Column("harvest_id", sa.Uuid()))
    op.create_foreign_key(
        "fk_primary_harvest",
        "collection_primary_photos",
        "harvests",
        ["harvest_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_collection_primary_photos_harvest_id", "collection_primary_photos", ["harvest_id"]
    )
    for source in ("local_collection_photo_id", "external_image_reference_id"):
        op.create_foreign_key(
            f"fk_primary_{source}_harvest_id",
            "collection_primary_photos",
            "record_media_links",
            [source, "harvest_id"],
            ["id", "harvest_id"],
            ondelete="CASCADE",
        )
    op.drop_constraint(
        "ck_collection_primary_photos_exactly_one_target", "collection_primary_photos"
    )
    op.create_check_constraint(
        "ck_collection_primary_photos_exactly_one_target",
        "collection_primary_photos",
        "num_nonnulls(seed_lot_id, plant_id, plant_group_id, harvest_id) = 1",
    )
    op.execute("""
        CREATE FUNCTION check_harvest_aggregate(harvest_uuid uuid) RETURNS void
        LANGUAGE plpgsql AS $$
        DECLARE h harvests%ROWTYPE; e events%ROWTYPE;
        BEGIN
            SELECT * INTO h FROM harvests WHERE id = harvest_uuid FOR UPDATE;
            IF NOT FOUND THEN RETURN; END IF;
            IF NOT EXISTS (SELECT 1 FROM harvest_items WHERE harvest_id = h.id) THEN
                RAISE EXCEPTION 'Harvest requires at least one material line' USING ERRCODE =
                '23514';
            END IF;
            SELECT * INTO e FROM events WHERE id = h.event_id FOR UPDATE;
            IF NOT FOUND OR e.kind <> 'harvest'
                OR e.plant_id IS DISTINCT FROM h.plant_id
                OR e.plant_group_id IS DISTINCT FROM h.plant_group_id
                OR e.occurred_on_precision IS DISTINCT FROM h.occurred_on_precision
                OR e.occurred_on_year IS DISTINCT FROM h.occurred_on_year
                OR e.occurred_on_month IS DISTINCT FROM h.occurred_on_month
                OR e.occurred_on_day IS DISTINCT FROM h.occurred_on_day
                OR e.notes IS DISTINCT FROM h.notes THEN
                RAISE EXCEPTION 'Harvest and owned Event must remain coherent' USING ERRCODE =
                '23514';
            END IF;
        END $$
    """)
    op.execute("""
        CREATE FUNCTION enforce_harvest_aggregate() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE h_id uuid;
        BEGIN
            IF TG_TABLE_NAME = 'harvests' THEN
                IF TG_OP <> 'DELETE' THEN PERFORM check_harvest_aggregate(NEW.id); END IF;
                IF TG_OP <> 'INSERT' THEN PERFORM check_harvest_aggregate(OLD.id); END IF;
            ELSIF TG_TABLE_NAME = 'harvest_items' THEN
                IF TG_OP <> 'DELETE' THEN PERFORM check_harvest_aggregate(NEW.harvest_id); END IF;
                IF TG_OP <> 'INSERT' THEN PERFORM check_harvest_aggregate(OLD.harvest_id); END IF;
            ELSE
                FOR h_id IN SELECT id FROM harvests WHERE event_id = NEW.id LOOP
                    PERFORM check_harvest_aggregate(h_id);
                END LOOP;
            END IF;
            RETURN NULL;
        END $$
    """)
    for table in ("harvests", "harvest_items"):
        op.execute(
            f"CREATE CONSTRAINT TRIGGER {table}_aggregate_integrity "
            f"AFTER INSERT OR UPDATE OR DELETE ON {table} DEFERRABLE INITIALLY DEFERRED "
            "FOR EACH ROW EXECUTE FUNCTION enforce_harvest_aggregate()"
        )
    op.execute(
        "CREATE CONSTRAINT TRIGGER events_harvest_integrity AFTER UPDATE ON events "
        "DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION "
        "enforce_harvest_aggregate()"
    )
    # Serialize raw line mutations too, so concurrent last-line deletions cannot write-skew.
    op.execute("""
        CREATE FUNCTION lock_harvest_item_owner() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP <> 'INSERT' THEN PERFORM id FROM harvests WHERE id = OLD.harvest_id FOR
            UPDATE; END IF;
            IF TG_OP <> 'DELETE' THEN PERFORM id FROM harvests WHERE id = NEW.harvest_id FOR
            UPDATE; END IF;
            IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
            RETURN NEW;
        END $$
    """)
    op.execute(
        "CREATE TRIGGER harvest_items_owner_lock BEFORE INSERT OR UPDATE OR DELETE ON "
        "harvest_items FOR EACH ROW EXECUTE FUNCTION lock_harvest_item_owner()"
    )


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM harvests)")):
        raise RuntimeError(
            "Structured Harvest history exists; restore a coordinated pre-upgrade backup "
            "to downgrade without data loss."
        )
    op.execute("DROP TRIGGER events_harvest_integrity ON events")
    for table in ("harvests", "harvest_items"):
        op.execute(f"DROP TRIGGER {table}_aggregate_integrity ON {table}")
    op.execute("DROP TRIGGER harvest_items_owner_lock ON harvest_items")
    op.execute("DROP FUNCTION lock_harvest_item_owner()")
    op.execute("DROP FUNCTION enforce_harvest_aggregate()")
    op.execute("DROP FUNCTION check_harvest_aggregate(uuid)")
    for source in ("local_collection_photo_id", "external_image_reference_id"):
        op.drop_constraint(f"fk_primary_{source}_harvest_id", "collection_primary_photos")
    op.drop_constraint("uq_collection_primary_photos_harvest_id", "collection_primary_photos")
    op.drop_constraint("fk_primary_harvest", "collection_primary_photos")
    op.drop_constraint(
        "ck_collection_primary_photos_exactly_one_target", "collection_primary_photos"
    )
    op.drop_column("collection_primary_photos", "harvest_id")
    op.create_check_constraint(
        "ck_collection_primary_photos_exactly_one_target",
        "collection_primary_photos",
        "num_nonnulls(seed_lot_id, plant_id, plant_group_id) = 1",
    )
    op.drop_constraint("ck_record_media_links_exactly_one_target", "record_media_links")
    for prefix in ("asset", "id"):
        op.drop_constraint(f"uq_record_media_links_{prefix}_harvest_id", "record_media_links")
    op.drop_constraint("fk_record_media_links_harvest", "record_media_links")
    op.drop_index("ix_record_media_links_harvest_id", "record_media_links")
    op.drop_column("record_media_links", "harvest_id")
    op.create_check_constraint(
        "ck_record_media_links_exactly_one_target",
        "record_media_links",
        "num_nonnulls(seed_lot_id, sowing_id, plant_id, plant_group_id, event_id) = 1",
    )
    op.drop_table("harvest_items")
    op.drop_table("harvests")
