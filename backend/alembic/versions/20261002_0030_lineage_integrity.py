"""Enforce acyclic concrete lineage and coherent new operation references.

Revision ID: 20261002_0030
Revises: 20261001_0029
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261002_0030"
down_revision: str | None = "20261001_0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RELATIONS = {
    "seed_lots": ("seed_lot", "producer_plant_id, producer_plant_group_id"),
    "sowings": ("sowing", "seed_lot_id"),
    "plants": ("plant", "originating_sowing_id, originating_plant_group_id"),
    "plant_groups": ("plant_group", "originating_sowing_id"),
}


def upgrade() -> None:
    # Freeze writes for the preflight and installation. Never repair or erase history.
    op.execute("LOCK TABLE seed_lots, sowings, plants, plant_groups IN SHARE ROW EXCLUSIVE MODE")
    op.execute("""
        CREATE FUNCTION florabase_lineage_has_cycle(subject_kind text, subject_id uuid)
        RETURNS boolean LANGUAGE sql VOLATILE AS $$
            WITH RECURSIVE walk(kind, id, path, is_cycle) AS (
                SELECT subject_kind, subject_id,
                       ARRAY[subject_kind || ':' || subject_id::text], false
                UNION ALL
                SELECT next.kind, next.id,
                       array_append(w.path, next.kind || ':' || next.id::text),
                       next.kind || ':' || next.id::text = ANY(w.path)
                FROM walk w
                CROSS JOIN LATERAL (
                    SELECT 'plant'::text kind, producer_plant_id id FROM seed_lots
                    WHERE w.kind = 'seed_lot' AND id = w.id AND producer_plant_id IS NOT NULL
                    UNION ALL
                    SELECT 'plant_group', producer_plant_group_id FROM seed_lots
                    WHERE w.kind = 'seed_lot' AND id = w.id AND producer_plant_group_id IS NOT NULL
                    UNION ALL
                    SELECT 'seed_lot', seed_lot_id FROM sowings
                    WHERE w.kind = 'sowing' AND id = w.id
                    UNION ALL
                    SELECT 'sowing', originating_sowing_id FROM plants
                    WHERE w.kind = 'plant' AND id = w.id AND originating_sowing_id IS NOT NULL
                    UNION ALL
                    SELECT 'plant_group', originating_plant_group_id FROM plants
                    WHERE w.kind = 'plant' AND id = w.id AND originating_plant_group_id IS NOT NULL
                    UNION ALL
                    SELECT 'sowing', originating_sowing_id FROM plant_groups
                    WHERE w.kind = 'plant_group' AND id = w.id AND originating_sowing_id IS NOT NULL
                ) next
                WHERE NOT w.is_cycle
            ) SELECT coalesce(bool_or(is_cycle), false) FROM walk
        $$
    """)
    for table, (kind, _) in RELATIONS.items():
        op.execute(f"""
            DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM {table}
                           WHERE florabase_lineage_has_cycle('{kind}', id)) THEN
                    RAISE EXCEPTION 'existing collection lineage contains a cycle';
                END IF;
            END $$
        """)
    op.execute("""
        CREATE FUNCTION florabase_lock_lineage_writes() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            -- A repeatable-read snapshot taken before waiting could miss the winning edge.
            -- Florabase uses READ COMMITTED; fail closed for stale-snapshot graph writers.
            IF current_setting('transaction_isolation') <> 'read committed' THEN
                RAISE EXCEPTION 'collection lineage writes require READ COMMITTED'
                    USING ERRCODE = '25001';
            END IF;
            -- Shared with lineage.service; held to transaction end, before statement row locks.
            PERFORM pg_advisory_xact_lock(1179406162, 1);
            RETURN NULL;
        END $$;
        CREATE FUNCTION florabase_check_lineage() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF florabase_lineage_has_cycle(TG_ARGV[0], NEW.id) THEN
                RAISE EXCEPTION 'collection lineage must be acyclic'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_collection_lineage_acyclic';
            END IF;
            RETURN NULL;
        END $$
    """)
    for table, (kind, columns) in RELATIONS.items():
        op.execute(f"""
            CREATE TRIGGER trg_{table}_lineage_lock BEFORE INSERT OR UPDATE OF {columns} ON {table}
            FOR EACH STATEMENT EXECUTE FUNCTION florabase_lock_lineage_writes();
            CREATE TRIGGER trg_{table}_lineage_check AFTER INSERT OR UPDATE OF {columns} ON {table}
            FOR EACH ROW EXECUTE FUNCTION florabase_check_lineage('{kind}')
        """)
    # Only new receipts must agree with current relationships. Later authorized corrections
    # intentionally leave original receipt facts stale; inverse services then block restoration.
    op.execute("""
        CREATE FUNCTION florabase_check_new_operation_relationships()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE coherent boolean;
        BEGIN
            CASE NEW.kind
            WHEN 'seed_lot_to_sowing' THEN
                SELECT seed_lot_id = NEW.seed_lot_id INTO coherent
                    FROM sowings WHERE id = NEW.sowing_id;
            WHEN 'sowing_to_plant' THEN
                SELECT originating_sowing_id = NEW.sowing_id INTO coherent
                    FROM plants WHERE id = NEW.plant_id;
            WHEN 'sowing_to_plant_group' THEN
                SELECT originating_sowing_id = NEW.sowing_id INTO coherent
                    FROM plant_groups WHERE id = NEW.plant_group_id;
            WHEN 'plant_group_extraction' THEN
                SELECT p.originating_plant_group_id = NEW.plant_group_id
                    AND e.kind = 'extraction' AND e.plant_group_id = NEW.plant_group_id
                    AND e.resulting_plant_id = NEW.plant_id INTO coherent
                    FROM plants p, events e WHERE p.id = NEW.plant_id AND e.id = NEW.event_id;
            WHEN 'plant_transfer' THEN
                SELECT kind = 'transfer' AND plant_id = NEW.plant_id INTO coherent
                    FROM events WHERE id = NEW.event_id;
            WHEN 'plant_group_transfer' THEN
                SELECT kind = 'transfer' AND plant_group_id = NEW.plant_group_id INTO coherent
                    FROM events WHERE id = NEW.event_id;
            ELSE coherent := false;
            END CASE;
            IF coherent IS DISTINCT FROM true THEN
                RAISE EXCEPTION 'operation receipt source/result/event mismatch'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_operation_receipts_relationships';
            END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER trg_operation_receipt_relationships BEFORE INSERT ON operation_receipts
        FOR EACH ROW EXECUTE FUNCTION florabase_check_new_operation_relationships()
    """)


def downgrade() -> None:
    # No stored facts change in either direction. Downgrade removes only these guards.
    op.execute("DROP TRIGGER trg_operation_receipt_relationships ON operation_receipts")
    op.execute("DROP FUNCTION florabase_check_new_operation_relationships()")
    for table in RELATIONS:
        op.execute(f"DROP TRIGGER trg_{table}_lineage_check ON {table}")
        op.execute(f"DROP TRIGGER trg_{table}_lineage_lock ON {table}")
    op.execute("DROP FUNCTION florabase_check_lineage()")
    op.execute("DROP FUNCTION florabase_lock_lineage_writes()")
    op.execute("DROP FUNCTION florabase_lineage_has_cycle(text, uuid)")
