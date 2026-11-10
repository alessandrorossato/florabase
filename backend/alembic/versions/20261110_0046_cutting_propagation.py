"""Add explicit vegetative material, rooting attempts, and observations.

Revision ID: 20261110_0046
Revises: 20261109_0045
"""

import sqlalchemy as sa

from alembic import op

revision = "20261110_0046"
down_revision = "20261109_0045"
branch_labels = None
depends_on = None

_NEW_TABLES = ("vegetative_lots", "propagation_attempts", "rooting_observations")
_SCOPES = ("supports_vegetative_lots", "supports_propagation_attempts")
_REFERENCES = (
    ("plants", "originating_propagation_attempt_id", "propagation_attempts"),
    ("plant_groups", "originating_propagation_attempt_id", "propagation_attempts"),
    ("operation_receipts", "vegetative_lot_id", "vegetative_lots"),
    ("operation_receipts", "source_vegetative_lot_id", "vegetative_lots"),
    ("operation_receipts", "propagation_attempt_id", "propagation_attempts"),
)
_CHECKS = {
    "locations": ("ck_locations_at_least_one_scope",),
    "plants": ("ck_plants_origin",),
    "plant_groups": ("ck_plant_groups_origin",),
    "operation_receipts": (
        "ck_operation_receipts_kind",
        "ck_operation_receipts_result_snapshot",
        "ck_operation_receipts_typed_state",
        "ck_operation_receipts_typed_references",
    ),
}
_PREVIOUS_TRIGGERS = {
    "plants": ("plant", "originating_sowing_id, originating_plant_group_id"),
    "plant_groups": ("plant_group", "originating_sowing_id"),
}
_CUTTING_TRIGGERS = {
    "plants": (
        "plant",
        "originating_sowing_id, originating_plant_group_id, originating_propagation_attempt_id",
    ),
    "plant_groups": ("plant_group", "originating_sowing_id, originating_propagation_attempt_id"),
    "vegetative_lots": ("vegetative_lot", "mother_plant_id, mother_plant_group_id"),
    "propagation_attempts": ("propagation_attempt", "vegetative_lot_id"),
}

_PREVIOUS_CHECKS = {
    "ck_locations_at_least_one_scope": (
        "supports_plants OR supports_sowings OR supports_seed_lots OR supports_harvest_inventory"
    ),
    "ck_plants_origin": (
        "((originating_plant_group_id IS NOT NULL AND originating_sowing_id IS NULL AND "
        "direct_origin_kind IS NULL AND direct_origin_detail IS NULL AND supplier_id IS NULL AND "
        "material_provenance_place_id IS NULL AND provenance_site_id IS NULL) OR "
        "(originating_plant_group_id IS NULL AND ((originating_sowing_id IS NOT NULL AND "
        "direct_origin_kind IS NULL AND direct_origin_detail IS NULL AND supplier_id IS NULL AND "
        "material_provenance_place_id IS NULL AND provenance_site_id IS NULL) OR "
        "(originating_sowing_id IS NULL AND direct_origin_kind IN ('purchased', 'gift_exchange', "
        "'collection_produced', 'other', 'unknown'))))) IS TRUE"
    ),
    "ck_plant_groups_origin": (
        "((originating_sowing_id IS NOT NULL AND direct_origin_kind IS NULL AND "
        "direct_origin_detail "
        "IS NULL AND supplier_id IS NULL AND material_provenance_place_id IS NULL AND "
        "provenance_site_id IS NULL) OR (originating_sowing_id IS NULL AND direct_origin_kind IN "
        "('purchased', 'gift_exchange', 'collection_produced', 'other', 'unknown'))) IS TRUE"
    ),
    "ck_operation_receipts_kind": (
        "kind IN ('seed_lot_to_sowing', 'sowing_to_plant', 'sowing_to_plant_group', "
        "'plant_group_extraction', 'plant_transfer', 'plant_group_transfer')"
    ),
    "ck_operation_receipts_result_snapshot": (
        "((result_snapshot_version IS NULL AND result_lifecycle IS NULL AND "
        "result_quantity_kind IS "
        "NULL AND result_quantity_value IS NULL AND result_quantity_unit IS NULL AND "
        "result_quantity_is_approximate IS NULL AND result_botanical_identity_id IS NULL AND "
        "result_location_id IS NULL AND result_date_precision IS NULL AND result_date_year IS NULL "
        "AND result_date_month IS NULL AND result_date_day IS NULL AND source_location_id IS"
        " NULL AND"
        " source_seed_lot_id IS NULL) OR (result_snapshot_version = 1 AND ((kind = "
        "'seed_lot_to_sowing' AND result_lifecycle IN ('active', 'completed', 'failed', "
        "'abandoned') "
        "AND result_botanical_identity_id IS NULL AND source_seed_lot_id IS NULL AND "
        "(result_quantity_kind IS NULL OR result_quantity_kind IN ('seed_count', 'weight')))"
        " OR (kind"
        " = 'sowing_to_plant' AND result_lifecycle IN ('active', 'transferred', 'dead', 'lost', "
        "'discarded') AND result_botanical_identity_id IS NOT NULL AND source_seed_lot_id IS"
        " NOT NULL"
        " AND result_quantity_kind IS NULL) OR (kind = 'sowing_to_plant_group' AND "
        "result_lifecycle "
        "IN ('active', 'transferred', 'completed', 'dead', 'lost', 'discarded') AND "
        "result_botanical_identity_id IS NOT NULL AND source_seed_lot_id IS NOT NULL AND "
        "(result_quantity_kind IS NULL OR result_quantity_kind = 'count'))))) IS TRUE"
    ),
    "ck_operation_receipts_typed_state": (
        "((kind = 'seed_lot_to_sowing' AND before_lifecycle IN ('active', 'exhausted', "
        "'discarded', "
        "'lost') AND after_lifecycle IN ('active', 'exhausted', 'discarded', 'lost') AND "
        "(before_quantity_kind IS NULL OR before_quantity_kind IN ('seed_count', 'weight')) AND "
        "(after_quantity_kind IS NULL OR after_quantity_kind IN ('seed_count', 'weight'))) "
        "OR (kind "
        "IN ('sowing_to_plant', 'sowing_to_plant_group') AND before_lifecycle IN ('active', "
        "'completed', 'failed', 'abandoned') AND after_lifecycle IN ('active', 'completed', "
        "'failed',"
        " 'abandoned') AND (before_quantity_kind IS NULL OR before_quantity_kind IN ('seed_count', "
        "'weight')) AND (after_quantity_kind IS NULL OR after_quantity_kind IN ('seed_count', "
        "'weight'))) OR (kind = 'plant_group_extraction' AND before_lifecycle = 'active' AND "
        "after_lifecycle IN ('active', 'completed') AND (before_quantity_kind IS NULL OR "
        "before_quantity_kind = 'count') AND (after_quantity_kind IS NULL OR after_quantity_kind = "
        "'count')) OR (kind = 'plant_transfer' AND before_lifecycle IN ('active', 'dead', 'lost', "
        "'discarded') AND after_lifecycle = 'transferred' AND before_quantity_kind IS NULL AND "
        "before_quantity_value IS NULL AND before_quantity_unit IS NULL AND "
        "before_quantity_is_approximate IS NULL AND after_quantity_kind IS NULL AND "
        "after_quantity_value IS NULL AND after_quantity_unit IS NULL AND "
        "after_quantity_is_approximate IS NULL) OR (kind = 'plant_group_transfer' AND "
        "before_lifecycle IN ('active', 'completed', 'dead', 'lost', 'discarded') AND "
        "after_lifecycle"
        " = 'transferred' AND (before_quantity_kind IS NULL OR before_quantity_kind = 'count') AND "
        "(after_quantity_kind IS NULL OR after_quantity_kind = 'count'))) IS TRUE"
    ),
    "ck_operation_receipts_typed_references": (
        "((kind = 'seed_lot_to_sowing' AND seed_lot_id IS NOT NULL AND sowing_id IS NOT NULL AND "
        "plant_id IS NULL AND plant_group_id IS NULL AND event_id IS NULL AND "
        "adjustment_mode IS NOT "
        "NULL) OR (kind = 'sowing_to_plant' AND seed_lot_id IS NULL AND sowing_id IS NOT NULL AND "
        "plant_id IS NOT NULL AND plant_group_id IS NULL AND event_id IS NULL AND "
        "adjustment_mode IS "
        "NULL) OR (kind = 'sowing_to_plant_group' AND seed_lot_id IS NULL AND sowing_id IS "
        "NOT NULL "
        "AND plant_id IS NULL AND plant_group_id IS NOT NULL AND event_id IS NULL AND "
        "adjustment_mode"
        " IS NULL) OR (kind = 'plant_group_extraction' AND seed_lot_id IS NULL AND sowing_id"
        " IS NULL "
        "AND plant_id IS NOT NULL AND plant_group_id IS NOT NULL AND event_id IS NOT NULL AND "
        "adjustment_mode IS NULL) OR (kind = 'plant_transfer' AND seed_lot_id IS NULL AND "
        "sowing_id "
        "IS NULL AND plant_id IS NOT NULL AND plant_group_id IS NULL AND event_id IS NOT NULL AND "
        "adjustment_mode IS NULL) OR (kind = 'plant_group_transfer' AND seed_lot_id IS NULL AND "
        "sowing_id IS NULL AND plant_id IS NULL AND plant_group_id IS NOT NULL AND event_id IS NOT "
        "NULL AND adjustment_mode IS NULL)) IS TRUE"
    ),
}

_CUTTING_CHECKS = {
    "ck_locations_at_least_one_scope": (
        "supports_plants OR supports_sowings OR supports_seed_lots OR "
        "supports_harvest_inventory OR "
        "supports_vegetative_lots OR supports_propagation_attempts"
    ),
    "ck_plants_origin": (
        "((num_nonnulls(originating_sowing_id, originating_propagation_attempt_id, "
        "originating_plant_group_id) = 1 AND direct_origin_kind IS NULL AND "
        "direct_origin_detail IS "
        "NULL AND supplier_id IS NULL AND material_provenance_place_id IS NULL AND "
        "provenance_site_id"
        " IS NULL) OR (num_nonnulls(originating_sowing_id, originating_propagation_attempt_id, "
        "originating_plant_group_id) = 0 AND direct_origin_kind IN ('purchased', 'gift_exchange', "
        "'collection_produced', 'other', 'unknown'))) IS TRUE"
    ),
    "ck_plant_groups_origin": (
        "((num_nonnulls(originating_sowing_id, originating_propagation_attempt_id) = 1 AND "
        "direct_origin_kind IS NULL AND direct_origin_detail IS NULL AND supplier_id IS NULL AND "
        "material_provenance_place_id IS NULL AND provenance_site_id IS NULL) OR "
        "(num_nonnulls(originating_sowing_id, originating_propagation_attempt_id) = 0 AND "
        "direct_origin_kind IN ('purchased', 'gift_exchange', 'collection_produced', 'other', "
        "'unknown'))) IS TRUE"
    ),
    "ck_operation_receipts_kind": (
        "kind IN ('seed_lot_to_sowing', 'sowing_to_plant', 'sowing_to_plant_group', "
        "'plant_group_extraction', 'plant_transfer', 'plant_group_transfer', "
        "'vegetative_lot_to_propagation_attempt', 'propagation_attempt_to_plant', "
        "'propagation_attempt_to_plant_group')"
    ),
    "ck_operation_receipts_result_snapshot": (
        "(CASE WHEN kind IN ('vegetative_lot_to_propagation_attempt', "
        "'propagation_attempt_to_plant',"
        " 'propagation_attempt_to_plant_group') THEN (result_snapshot_version = 1 AND "
        "result_botanical_identity_id IS NOT NULL AND ((kind = "
        "'vegetative_lot_to_propagation_attempt' AND result_lifecycle = 'active' AND "
        "(result_quantity_kind IS NULL OR result_quantity_kind = 'count')) OR (kind = "
        "'propagation_attempt_to_plant' AND result_lifecycle = 'active' AND "
        "result_quantity_kind IS "
        "NULL) OR (kind = 'propagation_attempt_to_plant_group' AND result_lifecycle = 'active' AND "
        "(result_quantity_kind IS NULL OR result_quantity_kind = 'count')))) ELSE "
        "((((result_snapshot_version IS NULL AND result_lifecycle IS NULL AND "
        "result_quantity_kind IS"
        " NULL AND result_quantity_value IS NULL AND result_quantity_unit IS NULL AND "
        "result_quantity_is_approximate IS NULL AND result_botanical_identity_id IS NULL AND "
        "result_location_id IS NULL AND result_date_precision IS NULL AND result_date_year IS NULL "
        "AND result_date_month IS NULL AND result_date_day IS NULL AND source_location_id IS"
        " NULL AND"
        " source_seed_lot_id IS NULL) OR (result_snapshot_version = 1 AND ((kind = "
        "'seed_lot_to_sowing' AND result_lifecycle IN ('active', 'completed', 'failed', "
        "'abandoned') "
        "AND result_botanical_identity_id IS NULL AND source_seed_lot_id IS NULL AND "
        "(result_quantity_kind IS NULL OR result_quantity_kind IN ('seed_count', 'weight')))"
        " OR (kind"
        " = 'sowing_to_plant' AND result_lifecycle IN ('active', 'transferred', 'dead', 'lost', "
        "'discarded') AND result_botanical_identity_id IS NOT NULL AND source_seed_lot_id IS"
        " NOT NULL"
        " AND result_quantity_kind IS NULL) OR (kind = 'sowing_to_plant_group' AND "
        "result_lifecycle "
        "IN ('active', 'transferred', 'completed', 'dead', 'lost', 'discarded') AND "
        "result_botanical_identity_id IS NOT NULL AND source_seed_lot_id IS NOT NULL AND "
        "(result_quantity_kind IS NULL OR result_quantity_kind = 'count'))))) IS TRUE) AND (true)) "
        "END) IS TRUE"
    ),
    "ck_operation_receipts_typed_state": (
        "(CASE WHEN kind IN ('vegetative_lot_to_propagation_attempt', "
        "'propagation_attempt_to_plant',"
        " 'propagation_attempt_to_plant_group') THEN (before_lifecycle = 'active' AND "
        "(before_quantity_kind IS NULL OR before_quantity_kind = 'count') AND "
        "(after_quantity_kind IS"
        " NULL OR after_quantity_kind = 'count') AND (CASE WHEN kind = "
        "'vegetative_lot_to_propagation_attempt' THEN after_lifecycle IN ('active', "
        "'exhausted') ELSE"
        " after_lifecycle IN ('active', 'completed', 'abandoned') END)) ELSE ((((kind = "
        "'seed_lot_to_sowing' AND before_lifecycle IN ('active', 'exhausted', 'discarded', 'lost') "
        "AND after_lifecycle IN ('active', 'exhausted', 'discarded', 'lost') AND "
        "(before_quantity_kind IS NULL OR before_quantity_kind IN ('seed_count', 'weight')) AND "
        "(after_quantity_kind IS NULL OR after_quantity_kind IN ('seed_count', 'weight'))) "
        "OR (kind "
        "IN ('sowing_to_plant', 'sowing_to_plant_group') AND before_lifecycle IN ('active', "
        "'completed', 'failed', 'abandoned') AND after_lifecycle IN ('active', 'completed', "
        "'failed',"
        " 'abandoned') AND (before_quantity_kind IS NULL OR before_quantity_kind IN ('seed_count', "
        "'weight')) AND (after_quantity_kind IS NULL OR after_quantity_kind IN ('seed_count', "
        "'weight'))) OR (kind = 'plant_group_extraction' AND before_lifecycle = 'active' AND "
        "after_lifecycle IN ('active', 'completed') AND (before_quantity_kind IS NULL OR "
        "before_quantity_kind = 'count') AND (after_quantity_kind IS NULL OR after_quantity_kind = "
        "'count')) OR (kind = 'plant_transfer' AND before_lifecycle IN ('active', 'dead', 'lost', "
        "'discarded') AND after_lifecycle = 'transferred' AND before_quantity_kind IS NULL AND "
        "before_quantity_value IS NULL AND before_quantity_unit IS NULL AND "
        "before_quantity_is_approximate IS NULL AND after_quantity_kind IS NULL AND "
        "after_quantity_value IS NULL AND after_quantity_unit IS NULL AND "
        "after_quantity_is_approximate IS NULL) OR (kind = 'plant_group_transfer' AND "
        "before_lifecycle IN ('active', 'completed', 'dead', 'lost', 'discarded') AND "
        "after_lifecycle"
        " = 'transferred' AND (before_quantity_kind IS NULL OR before_quantity_kind = 'count') AND "
        "(after_quantity_kind IS NULL OR after_quantity_kind = 'count'))) IS TRUE) AND "
        "(true)) END) "
        "IS TRUE"
    ),
    "ck_operation_receipts_typed_references": (
        "(CASE WHEN kind IN ('vegetative_lot_to_propagation_attempt', "
        "'propagation_attempt_to_plant',"
        " 'propagation_attempt_to_plant_group') THEN (seed_lot_id IS NULL AND sowing_id IS "
        "NULL AND "
        "source_seed_lot_id IS NULL AND event_id IS NULL AND propagation_attempt_id IS NOT "
        "NULL AND "
        "((kind = 'vegetative_lot_to_propagation_attempt' AND vegetative_lot_id IS NOT NULL AND "
        "source_vegetative_lot_id IS NULL AND plant_id IS NULL AND plant_group_id IS NULL AND "
        "adjustment_mode IS NOT NULL) OR (kind = 'propagation_attempt_to_plant' AND "
        "vegetative_lot_id"
        " IS NULL AND source_vegetative_lot_id IS NOT NULL AND plant_id IS NOT NULL AND "
        "plant_group_id IS NULL AND adjustment_mode IS NULL) OR (kind = "
        "'propagation_attempt_to_plant_group' AND vegetative_lot_id IS NULL AND "
        "source_vegetative_lot_id IS NOT NULL AND plant_group_id IS NOT NULL AND plant_id IS"
        " NULL AND"
        " adjustment_mode IS NULL))) ELSE ((((kind = 'seed_lot_to_sowing' AND seed_lot_id IS"
        " NOT NULL"
        " AND sowing_id IS NOT NULL AND plant_id IS NULL AND plant_group_id IS NULL AND "
        "event_id IS "
        "NULL AND adjustment_mode IS NOT NULL) OR (kind = 'sowing_to_plant' AND seed_lot_id "
        "IS NULL "
        "AND sowing_id IS NOT NULL AND plant_id IS NOT NULL AND plant_group_id IS NULL AND "
        "event_id "
        "IS NULL AND adjustment_mode IS NULL) OR (kind = 'sowing_to_plant_group' AND "
        "seed_lot_id IS "
        "NULL AND sowing_id IS NOT NULL AND plant_id IS NULL AND plant_group_id IS NOT NULL AND "
        "event_id IS NULL AND adjustment_mode IS NULL) OR (kind = 'plant_group_extraction' AND "
        "seed_lot_id IS NULL AND sowing_id IS NULL AND plant_id IS NOT NULL AND "
        "plant_group_id IS NOT"
        " NULL AND event_id IS NOT NULL AND adjustment_mode IS NULL) OR (kind = "
        "'plant_transfer' AND "
        "seed_lot_id IS NULL AND sowing_id IS NULL AND plant_id IS NOT NULL AND plant_group_id IS "
        "NULL AND event_id IS NOT NULL AND adjustment_mode IS NULL) OR (kind = "
        "'plant_group_transfer'"
        " AND seed_lot_id IS NULL AND sowing_id IS NULL AND plant_id IS NULL AND plant_group_id IS "
        "NOT NULL AND event_id IS NOT NULL AND adjustment_mode IS NULL)) IS TRUE) AND "
        "(num_nonnulls(vegetative_lot_id, propagation_attempt_id, source_vegetative_lot_id) = 0)) "
        "END) IS TRUE"
    ),
}

_PREVIOUS_EDGES = """
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
"""
_CUTTING_EDGES = """
                    UNION ALL
                    SELECT 'plant', mother_plant_id FROM vegetative_lots
                    WHERE w.kind = 'vegetative_lot' AND id = w.id AND mother_plant_id IS NOT NULL
                    UNION ALL
                    SELECT 'plant_group', mother_plant_group_id FROM vegetative_lots
                    WHERE w.kind = 'vegetative_lot' AND id = w.id
                      AND mother_plant_group_id IS NOT NULL
                    UNION ALL
                    SELECT 'vegetative_lot', vegetative_lot_id FROM propagation_attempts
                    WHERE w.kind = 'propagation_attempt' AND id = w.id
                    UNION ALL
                    SELECT 'propagation_attempt', originating_propagation_attempt_id FROM plants
                    WHERE w.kind = 'plant' AND id = w.id
                      AND originating_propagation_attempt_id IS NOT NULL
                    UNION ALL
                    SELECT 'propagation_attempt', originating_propagation_attempt_id
                    FROM plant_groups
                    WHERE w.kind = 'plant_group' AND id = w.id
                      AND originating_propagation_attempt_id IS NOT NULL
"""
_CUTTING_RECEIPT_CASES = """
            WHEN 'vegetative_lot_to_propagation_attempt' THEN
                SELECT vegetative_lot_id = NEW.vegetative_lot_id INTO coherent
                    FROM propagation_attempts WHERE id = NEW.propagation_attempt_id;
            WHEN 'propagation_attempt_to_plant' THEN
                SELECT p.originating_propagation_attempt_id = NEW.propagation_attempt_id
                    AND a.vegetative_lot_id = NEW.source_vegetative_lot_id INTO coherent
                    FROM plants p, propagation_attempts a
                    WHERE p.id = NEW.plant_id AND a.id = NEW.propagation_attempt_id;
            WHEN 'propagation_attempt_to_plant_group' THEN
                SELECT p.originating_propagation_attempt_id = NEW.propagation_attempt_id
                    AND a.vegetative_lot_id = NEW.source_vegetative_lot_id INTO coherent
                    FROM plant_groups p, propagation_attempts a
                    WHERE p.id = NEW.plant_group_id AND a.id = NEW.propagation_attempt_id;
"""


def _lineage_guards(*, cutting: bool) -> None:
    edges = _PREVIOUS_EDGES + (_CUTTING_EDGES if cutting else "")
    op.execute(f"""
        CREATE OR REPLACE FUNCTION florabase_lineage_has_cycle(subject_kind text, subject_id uuid)
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
{edges}
                ) next
                WHERE NOT w.is_cycle
            ) SELECT coalesce(bool_or(is_cycle), false) FROM walk
        $$
    """)
    for table in _PREVIOUS_TRIGGERS if cutting else _CUTTING_TRIGGERS:
        op.execute(f"DROP TRIGGER trg_{table}_lineage_check ON {table}")
        op.execute(f"DROP TRIGGER trg_{table}_lineage_lock ON {table}")
    for table, (kind, columns) in (_CUTTING_TRIGGERS if cutting else _PREVIOUS_TRIGGERS).items():
        op.execute(f"""
            CREATE TRIGGER trg_{table}_lineage_lock BEFORE INSERT OR UPDATE OF {columns} ON {table}
            FOR EACH STATEMENT EXECUTE FUNCTION florabase_lock_lineage_writes();
            CREATE TRIGGER trg_{table}_lineage_check AFTER INSERT OR UPDATE OF {columns} ON {table}
            FOR EACH ROW EXECUTE FUNCTION florabase_check_lineage('{kind}')
        """)
    receipt_cases = _CUTTING_RECEIPT_CASES if cutting else ""
    op.execute(f"""
        CREATE OR REPLACE FUNCTION florabase_check_new_operation_relationships()
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
{receipt_cases}            ELSE coherent := false;
            END CASE;
            IF coherent IS DISTINCT FROM true THEN
                RAISE EXCEPTION 'operation receipt source/result/event mismatch'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_operation_receipts_relationships';
            END IF;
            RETURN NEW;
        END $$
    """)


def _replace_checks(expressions: dict[str, str]) -> None:
    for table, names in _CHECKS.items():
        for name in names:
            op.drop_constraint(name, table, type_="check")
            op.create_check_constraint(name, table, expressions[name])


_MEDIA_TARGETS = (
    (
        "record_media_links",
        "seed_lot_id, sowing_id, plant_id, plant_group_id, event_id, harvest_id, supplier_id",
    ),
    ("collection_primary_photos", "seed_lot_id, plant_id, plant_group_id, harvest_id, supplier_id"),
)
_CUTTING_TARGETS = (
    ("vegetative_lot_id", "vegetative_lots"),
    ("propagation_attempt_id", "propagation_attempts"),
)
_PHOTO_SOURCES = ("local_collection_photo_id", "external_image_reference_id")
_SCHEDULE_TARGETS = (
    "botanical_identity_id, seed_lot_id, sowing_id, plant_id, plant_group_id, location_id"
)
_SCHEDULE_KINDS = (
    "'repot', 'water', 'fertilize', 'move', 'check_germination', 'inspect', 'harvest', 'follow_up'"
)


def _replace_target_checks(*, cutting: bool) -> None:
    suffix = ", vegetative_lot_id, propagation_attempt_id" if cutting else ""
    for table, previous in _MEDIA_TARGETS:
        name = f"ck_{table}_exactly_one_target"
        op.drop_constraint(name, table, type_="check")
        op.create_check_constraint(name, table, f"num_nonnulls({previous}{suffix}) = 1")
    op.drop_constraint("ck_schedule_target", "scheduled_activities", type_="check")
    op.create_check_constraint(
        "ck_schedule_target",
        "scheduled_activities",
        f"num_nonnulls({_SCHEDULE_TARGETS}{suffix}) <= 1",
    )
    kinds = _SCHEDULE_KINDS + (", 'check_rooting'" if cutting else "")
    op.drop_constraint("ck_schedule_kind", "scheduled_activities", type_="check")
    op.create_check_constraint(
        "ck_schedule_kind", "scheduled_activities", f"activity_kind IN ({kinds})"
    )

    columns = f"media_asset_id, source_kind, {_MEDIA_TARGETS[0][1]}{suffix}".split(", ")
    new = ", ".join(f"NEW.{column}" for column in columns)
    old = ", ".join(f"OLD.{column}" for column in columns)
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


def _add_targets() -> None:
    for column, target in _CUTTING_TARGETS:
        for table in ("scheduled_activities", "record_media_links", "collection_primary_photos"):
            op.add_column(table, sa.Column(column, sa.Uuid(), nullable=True))
            op.create_foreign_key(
                f"fk_{table}_{column}",
                table,
                target,
                [column],
                ["id"],
                ondelete="RESTRICT",
            )
            if table != "collection_primary_photos":
                op.create_index(f"ix_{table}_{column}", table, [column])
        op.create_unique_constraint(
            f"uq_record_media_links_asset_{column}",
            "record_media_links",
            ["media_asset_id", column],
        )
        op.create_unique_constraint(
            f"uq_record_media_links_id_{column}", "record_media_links", ["id", column]
        )
        op.create_unique_constraint(
            f"uq_collection_primary_photos_{column}", "collection_primary_photos", [column]
        )
        for source in _PHOTO_SOURCES:
            op.create_foreign_key(
                f"fk_primary_{source}_{column}",
                "collection_primary_photos",
                "record_media_links",
                [source, column],
                ["id", column],
                ondelete="CASCADE",
            )
    _replace_target_checks(cutting=True)


def _drop_targets() -> None:
    _replace_target_checks(cutting=False)
    for column, _ in _CUTTING_TARGETS:
        for source in _PHOTO_SOURCES:
            op.drop_constraint(
                f"fk_primary_{source}_{column}", "collection_primary_photos", type_="foreignkey"
            )
        for table in ("collection_primary_photos", "record_media_links", "scheduled_activities"):
            op.drop_column(table, column)


_SOURCE_COLUMNS = (
    ("source_botanical_identity_id", sa.Uuid()),
    ("source_date_precision", sa.String(8)),
    ("source_date_year", sa.SmallInteger()),
    ("source_date_month", sa.SmallInteger()),
    ("source_date_day", sa.SmallInteger()),
)
_SOURCE_CHECK = "ck_operation_receipts_cutting_source"


def _add_receipt_source_snapshot() -> None:
    for column, data_type in _SOURCE_COLUMNS:
        op.add_column("operation_receipts", sa.Column(column, data_type, nullable=True))
    op.create_check_constraint(
        _SOURCE_CHECK,
        "operation_receipts",
        "(CASE WHEN kind IN ('vegetative_lot_to_propagation_attempt', "
        "'propagation_attempt_to_plant', 'propagation_attempt_to_plant_group') "
        "THEN source_botanical_identity_id IS NOT NULL ELSE "
        "num_nonnulls(source_botanical_identity_id, source_date_precision, source_date_year, "
        "source_date_month, source_date_day) = 0 END) IS TRUE",
    )


_PREVIOUS_SAVED_VIEW_SURFACES = (
    "'global_search', 'seed_lots', 'sowings', 'plants', 'harvests', 'stored_material', 'events', "
    "'history', 'media', 'botanical_identities', 'suppliers', 'orders', 'locations', 'geography', "
    "'provenance_map', 'species_distribution', 'native_ranges'"
)


def _saved_view_surface(*, cutting: bool) -> None:
    surfaces = _PREVIOUS_SAVED_VIEW_SURFACES + (", 'cuttings'" if cutting else "")
    op.drop_constraint("ck_saved_views_surface", "saved_views", type_="check")
    op.create_check_constraint("ck_saved_views_surface", "saved_views", f"surface IN ({surfaces})")


def upgrade() -> None:
    op.execute(
        "LOCK TABLE seed_lots, sowings, plants, plant_groups, locations, operation_receipts "
        " , scheduled_activities, record_media_links, collection_primary_photos "
        "IN SHARE ROW EXCLUSIVE MODE"
    )
    op.create_table(
        "vegetative_lots",
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("material_type", sa.String(length=32), nullable=False),
        sa.Column("source_kind", sa.String(length=32), nullable=False),
        sa.Column("source_detail", sa.String(length=255), nullable=True),
        sa.Column("lifecycle", sa.String(length=32), nullable=False),
        sa.Column("botanical_identity_id", sa.Uuid(), nullable=False),
        sa.Column("mother_plant_id", sa.Uuid(), nullable=True),
        sa.Column("mother_plant_group_id", sa.Uuid(), nullable=True),
        sa.Column("supplier_id", sa.Uuid(), nullable=True),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("material_provenance_place_id", sa.Uuid(), nullable=True),
        sa.Column("provenance_site_id", sa.Uuid(), nullable=True),
        sa.Column("location_id", sa.Uuid(), nullable=True),
        sa.Column("taken_on_precision", sa.String(length=8), nullable=True),
        sa.Column("taken_on_year", sa.SmallInteger(), nullable=True),
        sa.Column("taken_on_month", sa.SmallInteger(), nullable=True),
        sa.Column("taken_on_day", sa.SmallInteger(), nullable=True),
        sa.Column("initial_quantity_value", sa.Integer(), nullable=True),
        sa.Column("initial_quantity_is_approximate", sa.Boolean(), nullable=True),
        sa.Column("quantity_value", sa.Integer(), nullable=True),
        sa.Column("quantity_is_approximate", sa.Boolean(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "((quantity_value IS NULL AND quantity_is_approximate IS NULL) OR "
            "(quantity_value IS NOT NULL AND quantity_is_approximate IS NOT NULL AND "
            "(quantity_value > 0 OR (quantity_value = 0 AND NOT quantity_is_approximate AND "
            "lifecycle = 'exhausted'))))",
            name="ck_vegetative_lots_quantity",
        ),
        sa.CheckConstraint(
            "(num_nonnulls(taken_on_precision, taken_on_year, taken_on_month, taken_on_day) "
            "= 0 OR (taken_on_year BETWEEN 1 AND 9999 AND ((taken_on_precision = 'year' AND "
            "taken_on_month IS NULL AND taken_on_day IS NULL) OR (taken_on_precision = "
            "'month' AND taken_on_month BETWEEN 1 AND 12 AND taken_on_day IS NULL) OR "
            "(taken_on_precision = 'day' AND taken_on_month BETWEEN 1 AND 12 AND "
            "taken_on_day BETWEEN 1 AND 31 AND make_date(taken_on_year, taken_on_month, "
            "taken_on_day) IS NOT NULL)))) IS TRUE",
            name="ck_vegetative_lots_taken_on",
        ),
        sa.CheckConstraint(
            "CASE WHEN source_kind = 'collection_produced' THEN "
            "num_nonnulls(mother_plant_id, mother_plant_group_id) <= 1 AND "
            "num_nonnulls(supplier_id, order_id, material_provenance_place_id, "
            "provenance_site_id) = 0 ELSE num_nonnulls(mother_plant_id, "
            "mother_plant_group_id) = 0 END",
            name="ck_vegetative_lots_source_references",
        ),
        sa.CheckConstraint(
            "label IS NULL OR (char_length(label) BETWEEN 1 AND 255 AND label = "
            "regexp_replace(btrim(label), '[[:space:]]+', ' ', 'g') AND label !~ "
            "'[[:cntrl:]]')",
            name="ck_vegetative_lots_label",
        ),
        sa.CheckConstraint(
            "lifecycle IN ('active', 'exhausted', 'discarded', 'lost', 'reversed')",
            name="ck_vegetative_lots_lifecycle",
        ),
        sa.CheckConstraint(
            "material_type IN ('stem_cutting', 'leaf_cutting', 'root_cutting')",
            name="ck_vegetative_lots_material_type",
        ),
        sa.CheckConstraint(
            "notes IS NULL OR (char_length(notes) BETWEEN 1 AND 20000 AND notes = "
            "btrim(notes) AND regexp_replace(notes, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
            name="ck_vegetative_lots_notes",
        ),
        sa.CheckConstraint(
            "order_id IS NULL OR source_kind = 'purchased'", name="ck_vegetative_lots_order_source"
        ),
        sa.CheckConstraint(
            "source_detail IS NULL OR (char_length(source_detail) BETWEEN 1 AND 255 AND "
            "source_detail = regexp_replace(btrim(source_detail), '[[:space:]]+', ' ', 'g') "
            "AND source_detail !~ '[[:cntrl:]]')",
            name="ck_vegetative_lots_source_detail_text",
        ),
        sa.CheckConstraint(
            "source_detail IS NULL OR source_kind = 'other'",
            name="ck_vegetative_lots_source_detail",
        ),
        sa.CheckConstraint(
            "source_kind IN ('collection_produced', 'purchased', 'gift_exchange', "
            "'self_collected', 'other', 'unknown')",
            name="ck_vegetative_lots_source_kind",
        ),
        sa.CheckConstraint(
            "((initial_quantity_value IS NULL AND initial_quantity_is_approximate IS NULL) "
            "OR (initial_quantity_value IS NOT NULL AND initial_quantity_is_approximate IS "
            "NOT NULL AND (initial_quantity_value > 0)))",
            name="ck_vegetative_lots_initial_quantity",
        ),
        sa.ForeignKeyConstraint(
            ["botanical_identity_id"], ["botanical_identities.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["material_provenance_place_id"], ["geographic_places.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["mother_plant_group_id"], ["plant_groups.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["mother_plant_id"], ["plants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["provenance_site_id"], ["provenance_sites.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_vegetative_lots_botanical_identity_id"),
        "vegetative_lots",
        ["botanical_identity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vegetative_lots_lifecycle"), "vegetative_lots", ["lifecycle"], unique=False
    )
    op.create_index(
        op.f("ix_vegetative_lots_location_id"), "vegetative_lots", ["location_id"], unique=False
    )
    op.create_index(
        op.f("ix_vegetative_lots_material_provenance_place_id"),
        "vegetative_lots",
        ["material_provenance_place_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vegetative_lots_mother_plant_group_id"),
        "vegetative_lots",
        ["mother_plant_group_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vegetative_lots_mother_plant_id"),
        "vegetative_lots",
        ["mother_plant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vegetative_lots_order_id"), "vegetative_lots", ["order_id"], unique=False
    )
    op.create_index(
        op.f("ix_vegetative_lots_provenance_site_id"),
        "vegetative_lots",
        ["provenance_site_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vegetative_lots_supplier_id"), "vegetative_lots", ["supplier_id"], unique=False
    )
    op.create_table(
        "propagation_attempts",
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("attempt_kind", sa.String(length=32), nullable=False),
        sa.Column("lifecycle", sa.String(length=32), nullable=False),
        sa.Column("rooted_count", sa.Integer(), nullable=True),
        sa.Column("hormone_treatment", sa.String(length=500), nullable=True),
        sa.Column("substrate", sa.String(length=500), nullable=True),
        sa.Column("container", sa.String(length=500), nullable=True),
        sa.Column("environment", sa.String(length=500), nullable=True),
        sa.Column("temperature_min_c", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("temperature_max_c", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("vegetative_lot_id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=True),
        sa.Column("started_on_precision", sa.String(length=8), nullable=True),
        sa.Column("started_on_year", sa.SmallInteger(), nullable=True),
        sa.Column("started_on_month", sa.SmallInteger(), nullable=True),
        sa.Column("started_on_day", sa.SmallInteger(), nullable=True),
        sa.Column("ended_on_precision", sa.String(length=8), nullable=True),
        sa.Column("ended_on_year", sa.SmallInteger(), nullable=True),
        sa.Column("ended_on_month", sa.SmallInteger(), nullable=True),
        sa.Column("ended_on_day", sa.SmallInteger(), nullable=True),
        sa.Column("quantity_value", sa.Integer(), nullable=True),
        sa.Column("quantity_is_approximate", sa.Boolean(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(num_nonnulls(ended_on_precision, ended_on_year, ended_on_month, ended_on_day) "
            "= 0 OR (ended_on_year BETWEEN 1 AND 9999 AND ((ended_on_precision = 'year' AND "
            "ended_on_month IS NULL AND ended_on_day IS NULL) OR (ended_on_precision = "
            "'month' AND ended_on_month BETWEEN 1 AND 12 AND ended_on_day IS NULL) OR "
            "(ended_on_precision = 'day' AND ended_on_month BETWEEN 1 AND 12 AND "
            "ended_on_day BETWEEN 1 AND 31 AND make_date(ended_on_year, ended_on_month, "
            "ended_on_day) IS NOT NULL)))) IS TRUE",
            name="ck_propagation_attempts_ended_on",
        ),
        sa.CheckConstraint(
            "(num_nonnulls(started_on_precision, started_on_year, started_on_month, "
            "started_on_day) = 0 OR (started_on_year BETWEEN 1 AND 9999 AND "
            "((started_on_precision = 'year' AND started_on_month IS NULL AND started_on_day"
            " IS NULL) OR (started_on_precision = 'month' AND started_on_month BETWEEN 1 AND"
            " 12 AND started_on_day IS NULL) OR (started_on_precision = 'day' AND "
            "started_on_month BETWEEN 1 AND 12 AND started_on_day BETWEEN 1 AND 31 AND "
            "make_date(started_on_year, started_on_month, started_on_day) IS NOT NULL)))) IS"
            " TRUE",
            name="ck_propagation_attempts_started_on",
        ),
        sa.CheckConstraint("attempt_kind = 'cutting'", name="ck_propagation_attempts_kind"),
        sa.CheckConstraint(
            "container IS NULL OR (char_length(container) BETWEEN 1 AND 500 AND container = "
            "regexp_replace(btrim(container), '[[:space:]]+', ' ', 'g') AND container !~ "
            "'[[:cntrl:]]')",
            name="ck_propagation_attempts_container",
        ),
        sa.CheckConstraint(
            "environment IS NULL OR (char_length(environment) BETWEEN 1 AND 500 AND "
            "environment = regexp_replace(btrim(environment), '[[:space:]]+', ' ', 'g') AND "
            "environment !~ '[[:cntrl:]]')",
            name="ck_propagation_attempts_environment",
        ),
        sa.CheckConstraint(
            "hormone_treatment IS NULL OR (char_length(hormone_treatment) BETWEEN 1 AND 500 "
            "AND hormone_treatment = regexp_replace(btrim(hormone_treatment), "
            "'[[:space:]]+', ' ', 'g') AND hormone_treatment !~ '[[:cntrl:]]')",
            name="ck_propagation_attempts_hormone_treatment",
        ),
        sa.CheckConstraint(
            "label IS NULL OR (char_length(label) BETWEEN 1 AND 255 AND label = "
            "regexp_replace(btrim(label), '[[:space:]]+', ' ', 'g') AND label !~ "
            "'[[:cntrl:]]')",
            name="ck_propagation_attempts_label",
        ),
        sa.CheckConstraint(
            "lifecycle <> 'failed' OR rooted_count IS NULL OR rooted_count = 0",
            name="ck_propagation_attempts_failed_count",
        ),
        sa.CheckConstraint(
            "lifecycle IN ('active', 'completed', 'failed', 'abandoned', 'reversed')",
            name="ck_propagation_attempts_lifecycle",
        ),
        sa.CheckConstraint(
            "notes IS NULL OR (char_length(notes) BETWEEN 1 AND 20000 AND notes = "
            "btrim(notes) AND regexp_replace(notes, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
            name="ck_propagation_attempts_notes",
        ),
        sa.CheckConstraint(
            "substrate IS NULL OR (char_length(substrate) BETWEEN 1 AND 500 AND substrate = "
            "regexp_replace(btrim(substrate), '[[:space:]]+', ' ', 'g') AND substrate !~ "
            "'[[:cntrl:]]')",
            name="ck_propagation_attempts_substrate",
        ),
        sa.CheckConstraint(
            "((quantity_value IS NULL AND quantity_is_approximate IS NULL) OR "
            "(quantity_value IS NOT NULL AND quantity_is_approximate IS NOT NULL AND "
            "(quantity_value > 0)))",
            name="ck_propagation_attempts_quantity",
        ),
        sa.CheckConstraint(
            "ROW(ended_on_year, coalesce(ended_on_month, 12), coalesce(ended_on_day, 31)) >="
            " ROW(started_on_year, coalesce(started_on_month, 1), coalesce(started_on_day, "
            "1))",
            name="ck_propagation_attempts_date_order",
        ),
        sa.CheckConstraint(
            "rooted_count >= 0 AND (quantity_is_approximate IS DISTINCT FROM false OR "
            "rooted_count <= quantity_value)",
            name="ck_propagation_attempts_rooted_count",
        ),
        sa.CheckConstraint(
            "temperature_max_c BETWEEN -50 AND 70", name="ck_propagation_attempts_temperature_max"
        ),
        sa.CheckConstraint(
            "temperature_min_c <= temperature_max_c",
            name="ck_propagation_attempts_temperature_order",
        ),
        sa.CheckConstraint(
            "temperature_min_c BETWEEN -50 AND 70", name="ck_propagation_attempts_temperature_min"
        ),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["vegetative_lot_id"], ["vegetative_lots.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_propagation_attempts_lifecycle"),
        "propagation_attempts",
        ["lifecycle"],
        unique=False,
    )
    op.create_index(
        op.f("ix_propagation_attempts_location_id"),
        "propagation_attempts",
        ["location_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_propagation_attempts_vegetative_lot_id"),
        "propagation_attempts",
        ["vegetative_lot_id"],
        unique=False,
    )
    op.create_table(
        "rooting_observations",
        sa.Column("propagation_attempt_id", sa.Uuid(), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("rooted_count", sa.Integer(), nullable=True),
        sa.Column("observed_on_precision", sa.String(length=8), nullable=True),
        sa.Column("observed_on_year", sa.SmallInteger(), nullable=True),
        sa.Column("observed_on_month", sa.SmallInteger(), nullable=True),
        sa.Column("observed_on_day", sa.SmallInteger(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(num_nonnulls(observed_on_precision, observed_on_year, observed_on_month, "
            "observed_on_day) = 0 OR (observed_on_year BETWEEN 1 AND 9999 AND "
            "((observed_on_precision = 'year' AND observed_on_month IS NULL AND "
            "observed_on_day IS NULL) OR (observed_on_precision = 'month' AND "
            "observed_on_month BETWEEN 1 AND 12 AND observed_on_day IS NULL) OR "
            "(observed_on_precision = 'day' AND observed_on_month BETWEEN 1 AND 12 AND "
            "observed_on_day BETWEEN 1 AND 31 AND make_date(observed_on_year, "
            "observed_on_month, observed_on_day) IS NOT NULL)))) IS TRUE",
            name="ck_rooting_observations_observed_on",
        ),
        sa.CheckConstraint(
            "notes IS NULL OR (char_length(notes) BETWEEN 1 AND 20000 AND notes = "
            "btrim(notes) AND regexp_replace(notes, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
            name="ck_rooting_observations_notes",
        ),
        sa.CheckConstraint(
            "stage IN ('callus', 'root_initials', 'rooted', 'loss', 'inspection')",
            name="ck_rooting_observations_stage",
        ),
        sa.CheckConstraint("rooted_count >= 0", name="ck_rooting_observations_rooted_count"),
        sa.ForeignKeyConstraint(
            ["propagation_attempt_id"], ["propagation_attempts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_rooting_observations_timeline",
        "rooting_observations",
        [
            "propagation_attempt_id",
            "observed_on_year",
            "observed_on_month",
            "observed_on_day",
            "id",
        ],
        unique=False,
    )
    for name in _SCOPES:
        op.add_column(
            "locations", sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.false())
        )
    for table, column, target in _REFERENCES:
        op.add_column(table, sa.Column(column, sa.Uuid(), nullable=True))
        op.create_foreign_key(
            f"fk_{table}_{column}", table, target, [column], ["id"], ondelete="RESTRICT"
        )
        op.create_index(f"ix_{table}_{column}", table, [column])
    op.alter_column("operation_receipts", "kind", existing_type=sa.String(32), type_=sa.String(40))
    _replace_checks(_CUTTING_CHECKS)
    _lineage_guards(cutting=True)
    _add_targets()
    _add_receipt_source_snapshot()
    _saved_view_surface(cutting=True)


def downgrade() -> None:
    op.execute(
        "LOCK TABLE seed_lots, sowings, plants, plant_groups, locations, operation_receipts, "
        "vegetative_lots, propagation_attempts, rooting_observations, scheduled_activities, "
        "record_media_links, collection_primary_photos, saved_views IN ACCESS EXCLUSIVE MODE"
    )
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM vegetative_lots)
                OR EXISTS (SELECT 1 FROM propagation_attempts)
                OR EXISTS (SELECT 1 FROM rooting_observations)
                OR EXISTS (SELECT 1 FROM scheduled_activities WHERE activity_kind = 'check_rooting')
                OR EXISTS (SELECT 1 FROM saved_views WHERE surface = 'cuttings')
                OR EXISTS (SELECT 1 FROM locations WHERE
                    supports_vegetative_lots OR supports_propagation_attempts) THEN
                RAISE EXCEPTION
                    'Cannot downgrade CUTTING-001 while cutting records or scope flags exist';
            END IF;
        END $$
    """)
    op.drop_constraint(_SOURCE_CHECK, "operation_receipts", type_="check")
    for column, _ in _SOURCE_COLUMNS:
        op.drop_column("operation_receipts", column)
    _saved_view_surface(cutting=False)
    _drop_targets()
    _lineage_guards(cutting=False)
    _replace_checks(_PREVIOUS_CHECKS)
    op.alter_column("operation_receipts", "kind", existing_type=sa.String(40), type_=sa.String(32))
    for table, column, _ in reversed(_REFERENCES):
        op.drop_index(f"ix_{table}_{column}", table_name=table)
        op.drop_constraint(f"fk_{table}_{column}", table, type_="foreignkey")
        op.drop_column(table, column)
    for name in _SCOPES:
        op.drop_column("locations", name)
    for table in reversed(_NEW_TABLES):
        op.drop_table(table)
