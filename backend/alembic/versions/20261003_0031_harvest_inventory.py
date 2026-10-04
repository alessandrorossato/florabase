"""Optional managed Harvest material; no inventory backfill."""

import sqlalchemy as sa

from alembic import op

revision = "20261003_0031"
down_revision = "20261002_0030"
branch_labels = None
depends_on = None


def quantity_check(prefix: str) -> str:
    return f"""(({prefix}_kind IS NULL AND {prefix}_value IS NULL AND
    {prefix}_unit IS NULL AND {prefix}_is_approximate IS NULL) OR
    ({prefix}_value > 0 AND {prefix}_value < 'Infinity'::numeric AND
    {prefix}_is_approximate IS NOT NULL AND
    (({prefix}_kind = 'item_count' AND {prefix}_value = trunc({prefix}_value)
      AND {prefix}_unit IS NULL) OR
     ({prefix}_kind = 'weight' AND {prefix}_unit IN ('mg', 'g', 'kg'))))) IS TRUE"""


def state_check(state: str, quantity: str) -> str:
    return (
        f"{state} IN ('active', 'depleted') AND ({state} <> 'depleted' OR {quantity}_kind IS NULL)"
    )


def quantity_columns(prefix: str) -> list[sa.Column]:
    return [
        sa.Column(f"{prefix}_kind", sa.String(16)),
        sa.Column(f"{prefix}_value", sa.Numeric()),
        sa.Column(f"{prefix}_unit", sa.String(8)),
        sa.Column(f"{prefix}_is_approximate", sa.Boolean()),
    ]


def disposition_balance_check() -> str:
    return """((mode = 'use_all' AND
        ROW(quantity_kind, quantity_value, quantity_unit, quantity_is_approximate)
        IS NOT DISTINCT FROM
        ROW(before_quantity_kind, before_quantity_value, before_quantity_unit,
            before_quantity_is_approximate)) OR
    (mode = 'partial' AND (
        (before_quantity_kind IS NULL AND after_quantity_kind IS NULL) OR
        (before_quantity_is_approximate IS TRUE AND after_quantity_is_approximate IS TRUE
         AND before_quantity_kind = after_quantity_kind
         AND before_quantity_unit IS NOT DISTINCT FROM after_quantity_unit
         AND (quantity_kind IS NULL OR (quantity_kind = before_quantity_kind
             AND quantity_unit IS NOT DISTINCT FROM before_quantity_unit))) OR
        (before_quantity_is_approximate IS FALSE AND quantity_is_approximate IS FALSE
         AND after_quantity_is_approximate IS FALSE
         AND quantity_kind = before_quantity_kind AND after_quantity_kind = before_quantity_kind
         AND quantity_unit IS NOT DISTINCT FROM before_quantity_unit
         AND after_quantity_unit IS NOT DISTINCT FROM before_quantity_unit
         AND after_quantity_value = before_quantity_value - quantity_value)
    ))) IS TRUE"""


def upgrade() -> None:
    op.add_column(
        "locations",
        sa.Column(
            "supports_harvest_inventory", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.drop_constraint("ck_locations_at_least_one_scope", "locations")
    op.create_check_constraint(
        "ck_locations_at_least_one_scope",
        "locations",
        "supports_plants OR supports_sowings OR supports_seed_lots OR supports_harvest_inventory",
    )
    op.create_unique_constraint(
        "uq_harvest_items_inventory_context", "harvest_items", ["id", "harvest_id", "material_kind"]
    )
    op.create_table(
        "harvest_material_inventory",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "harvest_item_id",
            sa.Uuid(),
            sa.ForeignKey("harvest_items.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("location_id", sa.Uuid(), sa.ForeignKey("locations.id", ondelete="RESTRICT")),
        sa.Column("harvest_id", sa.Uuid(), nullable=False),
        sa.Column("material_kind", sa.String(16), nullable=False),
        sa.ForeignKeyConstraint(
            ["harvest_item_id", "harvest_id", "material_kind"],
            ["harvest_items.id", "harvest_items.harvest_id", "harvest_items.material_kind"],
            name="fk_harvest_inventory_material_context",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        sa.Column("state", sa.String(8), nullable=False),
        *quantity_columns("quantity"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(quantity_check("quantity"), name="ck_harvest_inventory_quantity"),
        sa.CheckConstraint(state_check("state", "quantity"), name="ck_harvest_inventory_state"),
    )
    op.create_index(
        "ix_harvest_material_inventory_location_id", "harvest_material_inventory", ["location_id"]
    )
    op.create_table(
        "harvest_material_dispositions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "inventory_id",
            sa.Uuid(),
            sa.ForeignKey("harvest_material_inventory.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("mode", sa.String(8), nullable=False),
        sa.Column("occurred_on_precision", sa.String(8)),
        sa.Column("occurred_on_year", sa.SmallInteger()),
        sa.Column("occurred_on_month", sa.SmallInteger()),
        sa.Column("occurred_on_day", sa.SmallInteger()),
        *quantity_columns("quantity"),
        sa.CheckConstraint(disposition_balance_check(), name="ck_harvest_disposition_balance"),
        sa.Column("before_state", sa.String(8), nullable=False),
        *quantity_columns("before_quantity"),
        sa.Column("after_state", sa.String(8), nullable=False),
        *quantity_columns("after_quantity"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "kind IN ('consumed', 'processed', 'discarded', 'gifted', 'used_for_propagation')",
            name="ck_harvest_disposition_kind",
        ),
        sa.CheckConstraint(
            (
                "mode IN ('partial', 'use_all') AND before_state = 'active' AND "
                "((mode = 'partial' AND after_state = 'active') OR (mode = "
                "'use_all' AND after_state = 'depleted'))"
            ),
            name="ck_harvest_disposition_transition",
        ),
        *(
            sa.CheckConstraint(quantity_check(p), name=f"ck_harvest_disposition_{p}")
            for p in ("quantity", "before_quantity", "after_quantity")
        ),
        sa.CheckConstraint(
            state_check("before_state", "before_quantity"),
            name="ck_harvest_disposition_before_state",
        ),
        sa.CheckConstraint(
            state_check("after_state", "after_quantity"), name="ck_harvest_disposition_after_state"
        ),
        sa.CheckConstraint(
            (
                "((occurred_on_precision IS NULL AND occurred_on_year IS NULL AND "
                "occurred_on_month IS NULL AND occurred_on_day IS NULL) OR\n"
                "        (occurred_on_year BETWEEN 1 AND 9999 AND "
                "((occurred_on_precision = 'year' AND occurred_on_month IS NULL "
                "AND occurred_on_day IS NULL) OR\n"
                "        (occurred_on_precision = 'month' AND occurred_on_month "
                "BETWEEN 1 AND 12 AND occurred_on_day IS NULL) OR\n"
                "        (occurred_on_precision = 'day' AND occurred_on_month "
                "BETWEEN 1 AND 12 AND occurred_on_day BETWEEN 1 AND 31 AND "
                "make_date(occurred_on_year, occurred_on_month, occurred_on_day) "
                "IS NOT NULL)))) IS TRUE"
            ),
            name="ck_harvest_disposition_date",
        ),
        sa.CheckConstraint(
            (
                "notes IS NULL OR (char_length(notes) BETWEEN 1 AND 20000 AND "
                "notes = btrim(notes) AND regexp_replace(notes, E'[\\n\\t]', '', "
                "'g') !~ '[[:cntrl:]]')"
            ),
            name="ck_harvest_disposition_notes",
        ),
    )
    op.create_index(
        "ix_harvest_material_dispositions_inventory_id",
        "harvest_material_dispositions",
        ["inventory_id"],
    )
    op.execute(
        "\n"
        "    CREATE FUNCTION protect_tracked_harvest_item() RETURNS "
        "trigger LANGUAGE plpgsql AS $$\n"
        "    BEGIN\n"
        "        IF (NEW.material_kind IS DISTINCT FROM OLD.material_kind "
        "OR NEW.harvest_id IS DISTINCT FROM OLD.harvest_id)\n"
        "           AND EXISTS (SELECT 1 FROM harvest_material_inventory "
        "WHERE harvest_item_id = OLD.id) THEN\n"
        "            RAISE EXCEPTION 'Tracked Harvest material "
        "identity/kind is retained' USING ERRCODE = '23514';\n"
        "        END IF;\n"
        "        RETURN NEW;\n"
        "    END $$;\n"
        "    CREATE TRIGGER tracked_harvest_item_guard BEFORE UPDATE ON "
        "harvest_items\n"
        "        FOR EACH ROW EXECUTE FUNCTION "
        "protect_tracked_harvest_item();\n"
        "    CREATE FUNCTION protect_harvest_inventory_source() RETURNS "
        "trigger LANGUAGE plpgsql AS $$\n"
        "    BEGIN\n"
        "        IF ROW(NEW.harvest_item_id, NEW.harvest_id, NEW.material_kind) "
        "IS DISTINCT FROM ROW(OLD.harvest_item_id, OLD.harvest_id, OLD.material_kind) THEN\n"
        "            RAISE EXCEPTION 'Harvest inventory source is "
        "immutable' USING ERRCODE = '23514';\n"
        "        END IF;\n"
        "        RETURN NEW;\n"
        "    END $$;\n"
        "    CREATE TRIGGER harvest_inventory_source_guard BEFORE UPDATE "
        "ON harvest_material_inventory\n"
        "        FOR EACH ROW EXECUTE FUNCTION "
        "protect_harvest_inventory_source();\n"
        "    CREATE FUNCTION protect_harvest_disposition() RETURNS trigger"
        " LANGUAGE plpgsql AS $$\n"
        "    BEGIN\n"
        "        RAISE EXCEPTION 'Harvest disposition facts are immutable'"
        " USING ERRCODE = '23514';\n"
        "    END $$;\n"
        "    CREATE TRIGGER harvest_disposition_guard BEFORE UPDATE ON "
        "harvest_material_dispositions\n"
        "        FOR EACH ROW EXECUTE FUNCTION "
        "protect_harvest_disposition();\n"
        "    "
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "LOCK TABLE harvest_material_inventory, "
            "harvest_material_dispositions, locations IN ACCESS EXCLUSIVE MODE"
        )
    )
    if connection.scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM harvest_material_inventory) OR "
            "EXISTS (SELECT 1 FROM harvest_material_dispositions)"
        )
    ):
        raise RuntimeError("Managed Harvest material/history cannot be discarded by downgrade")
    if connection.scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM locations WHERE NOT (supports_plants"
            " OR supports_sowings OR supports_seed_lots))"
        )
    ):
        raise RuntimeError("Harvest-only Location scope cannot be discarded by downgrade")
    op.execute(
        "DROP TRIGGER tracked_harvest_item_guard ON harvest_items; DROP "
        "FUNCTION protect_tracked_harvest_item(); DROP FUNCTION "
        "protect_harvest_inventory_source() CASCADE; DROP FUNCTION "
        "protect_harvest_disposition() CASCADE;"
    )
    op.drop_table("harvest_material_dispositions")
    op.drop_table("harvest_material_inventory")
    op.drop_constraint("uq_harvest_items_inventory_context", "harvest_items", type_="unique")
    op.drop_constraint("ck_locations_at_least_one_scope", "locations")
    op.create_check_constraint(
        "ck_locations_at_least_one_scope",
        "locations",
        "supports_plants OR supports_sowings OR supports_seed_lots",
    )
    op.drop_column("locations", "supports_harvest_inventory")
