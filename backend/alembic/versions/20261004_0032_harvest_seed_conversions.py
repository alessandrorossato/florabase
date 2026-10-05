"""Explicit seed conversions and guarded reversal; no inferred historical conversions."""

import sqlalchemy as sa

from alembic import op

revision = "20261004_0032"
down_revision = "20261003_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "harvest_material_inventory",
        sa.Column("correction_version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.drop_constraint("ck_seed_lots_lifecycle", "seed_lots")
    op.create_check_constraint(
        "ck_seed_lots_lifecycle",
        "seed_lots",
        "lifecycle IN ('active', 'exhausted', 'discarded', 'lost', 'reversed')",
    )
    op.create_table(
        "harvest_seed_lot_conversions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "inventory_id",
            sa.Uuid(),
            sa.ForeignKey("harvest_material_inventory.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "disposition_id",
            sa.Uuid(),
            sa.ForeignKey("harvest_material_dispositions.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "seed_lot_id",
            sa.Uuid(),
            sa.ForeignKey("seed_lots.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("source_correction_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(8), nullable=False),
        sa.Column("quantity_kind", sa.String(16)),
        sa.Column("quantity_value", sa.Numeric()),
        sa.Column("quantity_unit", sa.String(8)),
        sa.Column("quantity_is_approximate", sa.Boolean()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reversed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            (
                "status IN ('applied', 'reversed') AND ((status = 'applied' AND reversed_at "
                "IS NULL) OR (status = 'reversed' AND reversed_at IS NOT NULL AND reversed_at"
                " >= created_at))"
            ),
            name="ck_harvest_conversion_status",
        ),
        sa.CheckConstraint("source_correction_version >= 0", name="ck_harvest_conversion_version"),
        sa.CheckConstraint(
            (
                "((quantity_kind IS NULL AND quantity_value IS NULL AND quantity_unit IS NULL"
                " AND quantity_is_approximate IS NULL) OR (quantity_value > 0 AND "
                "quantity_value < 'Infinity'::numeric AND quantity_is_approximate IS NOT NULL"
                " AND ((quantity_kind = 'seed_count' AND quantity_value = "
                "trunc(quantity_value) AND quantity_unit IS NULL) OR (quantity_kind = "
                "'weight' AND quantity_unit IN ('mg', 'g'))))) IS TRUE"
            ),
            name="ck_harvest_conversion_quantity",
        ),
    )
    op.create_index(
        "ix_harvest_seed_lot_conversions_inventory_id",
        "harvest_seed_lot_conversions",
        ["inventory_id"],
    )
    op.execute("""
    CREATE FUNCTION protect_seed_conversion_facts() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF ROW(NEW.id, NEW.inventory_id, NEW.disposition_id, NEW.seed_lot_id,
               NEW.source_correction_version, NEW.quantity_kind, NEW.quantity_value,
               NEW.quantity_unit, NEW.quantity_is_approximate, NEW.created_at)
           IS DISTINCT FROM
           ROW(OLD.id, OLD.inventory_id, OLD.disposition_id, OLD.seed_lot_id,
               OLD.source_correction_version, OLD.quantity_kind, OLD.quantity_value,
               OLD.quantity_unit, OLD.quantity_is_approximate, OLD.created_at)
           OR (OLD.status = 'reversed' AND ROW(NEW.status, NEW.reversed_at)
               IS DISTINCT FROM ROW(OLD.status, OLD.reversed_at))
           OR (OLD.status = 'applied' AND NEW.status = 'applied'
               AND NEW.reversed_at IS DISTINCT FROM OLD.reversed_at)
        THEN
            RAISE EXCEPTION 'Seed conversion facts are immutable' USING ERRCODE='23514';
        END IF;
        RETURN NEW;
    END $$;
    CREATE TRIGGER seed_conversion_facts BEFORE UPDATE ON harvest_seed_lot_conversions
        FOR EACH ROW EXECUTE FUNCTION protect_seed_conversion_facts();

    CREATE FUNCTION protect_conversion_origin() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF TG_TABLE_NAME = 'seed_lots' THEN
            IF ROW(NEW.source_kind, NEW.producer_plant_id, NEW.producer_plant_group_id)
               IS DISTINCT FROM
               ROW(OLD.source_kind, OLD.producer_plant_id, OLD.producer_plant_group_id)
               AND EXISTS(
                   SELECT 1 FROM harvest_seed_lot_conversions WHERE seed_lot_id=OLD.id
               )
            THEN
                RAISE EXCEPTION 'Harvest Seed lot origin is retained' USING ERRCODE='23514';
            END IF;
            IF OLD.lifecycle='reversed' AND NEW.lifecycle<>'reversed' THEN
                RAISE EXCEPTION 'Reversed Seed lot cannot reactivate' USING ERRCODE='23514';
            END IF;
        ELSE
            IF ROW(NEW.plant_id, NEW.plant_group_id)
               IS DISTINCT FROM ROW(OLD.plant_id, OLD.plant_group_id)
               AND EXISTS(
                   SELECT 1 FROM harvest_seed_lot_conversions c
                   JOIN harvest_material_inventory i ON i.id=c.inventory_id
                   WHERE i.harvest_id=OLD.id
               )
            THEN
                RAISE EXCEPTION 'Converted Harvest source is retained' USING ERRCODE='23514';
            END IF;
        END IF;
        RETURN NEW;
    END $$;
    CREATE TRIGGER seed_conversion_origin BEFORE UPDATE ON seed_lots
        FOR EACH ROW EXECUTE FUNCTION protect_conversion_origin();
    CREATE TRIGGER harvest_conversion_origin BEFORE UPDATE ON harvests
        FOR EACH ROW EXECUTE FUNCTION protect_conversion_origin();

    CREATE FUNCTION check_seed_conversion() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE
        c harvest_seed_lot_conversions;
        i harvest_material_inventory;
        d harvest_material_dispositions;
        s seed_lots;
        h harvests;
    BEGIN
        IF TG_TABLE_NAME='seed_lots' THEN
            SELECT * INTO c FROM harvest_seed_lot_conversions WHERE seed_lot_id=NEW.id;
            SELECT * INTO s FROM seed_lots WHERE id=NEW.id;
            IF c.id IS NULL THEN
                IF s.lifecycle='reversed' THEN
                    RAISE EXCEPTION 'Reversed Seed lot needs conversion evidence'
                        USING ERRCODE='23514';
                END IF;
                RETURN NULL;
            END IF;
        ELSE
            SELECT * INTO c FROM harvest_seed_lot_conversions WHERE id=NEW.id;
            SELECT * INTO s FROM seed_lots WHERE id=c.seed_lot_id;
        END IF;
        SELECT * INTO i FROM harvest_material_inventory WHERE id=c.inventory_id;
        SELECT * INTO d FROM harvest_material_dispositions WHERE id=c.disposition_id;
        SELECT * INTO h FROM harvests WHERE id=i.harvest_id;
        IF i.material_kind<>'seed' OR d.inventory_id<>i.id OR d.kind<>'used_for_propagation'
           OR s.source_kind<>'collection_produced'
           OR ROW(s.producer_plant_id,s.producer_plant_group_id)
              IS DISTINCT FROM ROW(h.plant_id,h.plant_group_id)
           OR ((c.status='reversed') <> (s.lifecycle='reversed'))
        THEN
            RAISE EXCEPTION 'Incoherent seed conversion history' USING ERRCODE='23514';
        END IF;
        RETURN NULL;
    END $$;
    CREATE CONSTRAINT TRIGGER seed_conversion_coherent
        AFTER INSERT OR UPDATE ON harvest_seed_lot_conversions
        DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_seed_conversion();
    CREATE CONSTRAINT TRIGGER seed_lot_conversion_coherent AFTER INSERT OR UPDATE ON seed_lots
        DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_seed_conversion();

    CREATE FUNCTION protect_reversed_seed_source() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF (TG_OP='INSERT' OR NEW.seed_lot_id IS DISTINCT FROM OLD.seed_lot_id)
           AND EXISTS(
               SELECT 1 FROM seed_lots WHERE id=NEW.seed_lot_id AND lifecycle='reversed'
           )
        THEN
            RAISE EXCEPTION 'Reversed Seed lot cannot create new Sowings' USING ERRCODE='23514';
        END IF;
        RETURN NEW;
    END $$;
    CREATE TRIGGER reversed_seed_source BEFORE INSERT OR UPDATE OF seed_lot_id ON sowings
        FOR EACH ROW EXECUTE FUNCTION protect_reversed_seed_source();
    """)


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("LOCK TABLE harvest_seed_lot_conversions, seed_lots IN ACCESS EXCLUSIVE MODE")
    )
    if connection.scalar(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM harvest_seed_lot_conversions) OR EXISTS(SELECT 1"
            " FROM seed_lots WHERE lifecycle='reversed')"
        )
    ):
        raise RuntimeError("HARVEST-003 conversion history cannot be discarded")
    op.execute("""
    DROP TRIGGER reversed_seed_source ON sowings;
    DROP FUNCTION protect_reversed_seed_source();
    DROP TRIGGER seed_lot_conversion_coherent ON seed_lots;
    DROP TRIGGER seed_conversion_coherent ON harvest_seed_lot_conversions;
    DROP FUNCTION check_seed_conversion();
    DROP TRIGGER harvest_conversion_origin ON harvests;
    DROP TRIGGER seed_conversion_origin ON seed_lots;
    DROP FUNCTION protect_conversion_origin();
    DROP TRIGGER seed_conversion_facts ON harvest_seed_lot_conversions;
    DROP FUNCTION protect_seed_conversion_facts();
    """)
    op.drop_table("harvest_seed_lot_conversions")
    op.drop_column("harvest_material_inventory", "correction_version")
    op.drop_constraint("ck_seed_lots_lifecycle", "seed_lots")
    op.create_check_constraint(
        "ck_seed_lots_lifecycle",
        "seed_lots",
        "lifecycle IN ('active', 'exhausted', 'discarded', 'lost')",
    )
