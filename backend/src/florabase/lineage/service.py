from dataclasses import dataclass
from typing import Literal, cast
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import BotanicalIdentityResponse
from florabase.cuttings.model import PropagationAttempt, VegetativeLot
from florabase.harvests.conversion_model import HarvestSeedLotConversion
from florabase.harvests.inventory_model import HarvestMaterialInventory as Inventory
from florabase.harvests.model import Harvest, HarvestItem
from florabase.lineage.schemas import (
    AncestryChildren,
    AncestryNode,
    AncestryResponse,
    BotanicalIdentitySummary,
    HarvestConversionEvidence,
    LineageNode,
    LineageResponse,
    PlantGroupLineageNode,
    PlantLineageNode,
    PropagationAttemptLineageNode,
    SeedLotLineageNode,
    SowingLineageNode,
    VegetativeLotLineageNode,
)
from florabase.plants.model import DirectOriginKind, Plant, PlantGroup
from florabase.seed_lots.model import SeedLot, SeedLotSourceKind
from florabase.seed_lots.schemas import PartialDate
from florabase.sowings.model import Sowing

LineageKind = Literal[
    "seed_lot", "sowing", "plant", "plant_group", "vegetative_lot", "propagation_attempt"
]
LineageKey = tuple[LineageKind, UUID]


@dataclass(frozen=True)
class LineageCycleError(Exception):
    code: str = "lineage_cycle"
    message: str = "The proposed source relationship would create a lineage cycle"


_WALK = text(
    """
    WITH RECURSIVE lineage_walk(kind, id, depth, path, is_cycle) AS (
        SELECT CAST(:kind AS text), CAST(:item_id AS uuid), 0,
               ARRAY[CAST(:kind AS text) || ':' || CAST(:item_id AS text)], false
        UNION ALL
        SELECT next.kind, next.id, walk.depth + 1,
               array_append(walk.path, next.kind || ':' || CAST(next.id AS text)),
               next.kind || ':' || CAST(next.id AS text) = ANY(walk.path)
        FROM lineage_walk AS walk
        CROSS JOIN LATERAL (
            SELECT 'plant'::text AS kind, lot.producer_plant_id AS id
            FROM seed_lots AS lot
            WHERE walk.kind = 'seed_lot' AND lot.id = walk.id
              AND lot.producer_plant_id IS NOT NULL
            UNION ALL
            SELECT 'plant_group'::text, lot.producer_plant_group_id
            FROM seed_lots AS lot
            WHERE walk.kind = 'seed_lot' AND lot.id = walk.id
              AND lot.producer_plant_group_id IS NOT NULL
            UNION ALL
            SELECT 'sowing'::text, plant.originating_sowing_id
            FROM plants AS plant
            WHERE walk.kind = 'plant' AND plant.id = walk.id
              AND plant.originating_sowing_id IS NOT NULL
            UNION ALL
            SELECT 'plant_group'::text, plant.originating_plant_group_id
            FROM plants AS plant
            WHERE walk.kind = 'plant' AND plant.id = walk.id
              AND plant.originating_plant_group_id IS NOT NULL
            UNION ALL
            SELECT 'sowing'::text, plant_group.originating_sowing_id
            FROM plant_groups AS plant_group
            WHERE walk.kind = 'plant_group' AND plant_group.id = walk.id
              AND plant_group.originating_sowing_id IS NOT NULL
            UNION ALL
            SELECT 'seed_lot'::text, sowing.seed_lot_id
            FROM sowings AS sowing
            WHERE walk.kind = 'sowing' AND sowing.id = walk.id
            UNION ALL
            SELECT 'plant'::text, lot.mother_plant_id FROM vegetative_lots AS lot
            WHERE walk.kind = 'vegetative_lot' AND lot.id = walk.id
              AND lot.mother_plant_id IS NOT NULL
            UNION ALL
            SELECT 'plant_group'::text, lot.mother_plant_group_id FROM vegetative_lots AS lot
            WHERE walk.kind = 'vegetative_lot' AND lot.id = walk.id
              AND lot.mother_plant_group_id IS NOT NULL
            UNION ALL
            SELECT 'vegetative_lot'::text, attempt.vegetative_lot_id
            FROM propagation_attempts AS attempt
            WHERE walk.kind = 'propagation_attempt' AND attempt.id = walk.id
            UNION ALL
            SELECT 'propagation_attempt'::text, plant.originating_propagation_attempt_id
            FROM plants AS plant
            WHERE walk.kind = 'plant' AND plant.id = walk.id
              AND plant.originating_propagation_attempt_id IS NOT NULL
            UNION ALL
            SELECT 'propagation_attempt'::text, plant_group.originating_propagation_attempt_id
            FROM plant_groups AS plant_group
            WHERE walk.kind = 'plant_group' AND plant_group.id = walk.id
              AND plant_group.originating_propagation_attempt_id IS NOT NULL
        ) AS next
        WHERE NOT walk.is_cycle
    )
    SELECT kind, id, depth, is_cycle
    FROM lineage_walk
    ORDER BY depth
    """
)


def _walk(database: Session, subject: LineageKey) -> list[LineageKey]:
    rows = database.execute(_WALK, {"kind": subject[0], "item_id": subject[1]}).mappings()
    keys: list[LineageKey] = []
    for row in rows:
        if row["is_cycle"]:
            raise LineageCycleError(message="Persisted collection lineage contains a cycle")
        keys.append((cast(LineageKind, row["kind"]), cast(UUID, row["id"])))
    return keys


def lock_lineage_writes(database: Session) -> None:
    """Serialize changes to the collection lineage, before aggregate locks.

    The migration's statement triggers use the same transaction-scoped namespace.
    Readers and operations that cannot write origin columns do not take this lock.
    """
    database.execute(text("SELECT pg_advisory_xact_lock(1179406162, 1)"))


def validate_source_assignment(
    database: Session, subject: LineageKey, source: LineageKey | None
) -> None:
    if source is not None and subject in _walk(database, source):
        raise LineageCycleError()


def validate_producer_assignment(
    database: Session,
    seed_lot_id: UUID,
    producer_plant_id: UUID | None,
    producer_plant_group_id: UUID | None,
) -> None:
    producer: LineageKey | None = None
    if producer_plant_id is not None:
        producer = ("plant", producer_plant_id)
    elif producer_plant_group_id is not None:
        producer = ("plant_group", producer_plant_group_id)
    validate_source_assignment(database, ("seed_lot", seed_lot_id), producer)


def _direct_origin(value: str | None) -> DirectOriginKind | None:
    return None if value is None else DirectOriginKind(value)


def _identity_summary(identity: BotanicalIdentity) -> BotanicalIdentitySummary:
    response = BotanicalIdentityResponse.from_model(identity)
    return BotanicalIdentitySummary(id=response.id, display_label=response.display_label)


Origin = SeedLotSourceKind | DirectOriginKind | None


def _summaries(
    database: Session, keys: list[LineageKey]
) -> dict[LineageKey, tuple[LineageNode, Origin]]:
    """One batch per concrete type; each node with its own recorded origin kind."""
    grouped: dict[LineageKind, list[UUID]] = {
        "seed_lot": [],
        "sowing": [],
        "plant": [],
        "plant_group": [],
        "vegetative_lot": [],
        "propagation_attempt": [],
    }
    for kind, item_id in keys:
        grouped[kind].append(item_id)

    result: dict[LineageKey, tuple[LineageNode, Origin]] = {}
    if grouped["seed_lot"]:
        statement = (
            select(SeedLot, BotanicalIdentity)
            .join(BotanicalIdentity, BotanicalIdentity.id == SeedLot.botanical_identity_id)
            .where(SeedLot.id.in_(grouped["seed_lot"]))
        )
        for item, identity in database.execute(statement):
            result[("seed_lot", item.id)] = (
                SeedLotLineageNode(
                    id=item.id,
                    label=item.label,
                    lifecycle=item.lifecycle,
                    botanical_identity=_identity_summary(identity),
                ),
                SeedLotSourceKind(item.source_kind),
            )
    if grouped["sowing"]:
        for item in database.scalars(select(Sowing).where(Sowing.id.in_(grouped["sowing"]))):
            result[("sowing", item.id)] = (
                SowingLineageNode(id=item.id, label=item.label, lifecycle=item.lifecycle),
                None,
            )
    if grouped["plant"]:
        plant_statement = (
            select(Plant, BotanicalIdentity)
            .join(BotanicalIdentity, BotanicalIdentity.id == Plant.botanical_identity_id)
            .where(Plant.id.in_(grouped["plant"]))
        )
        for item, identity in database.execute(plant_statement):
            result[("plant", item.id)] = (
                PlantLineageNode(
                    id=item.id,
                    label=item.label,
                    lifecycle=item.lifecycle,
                    botanical_identity=_identity_summary(identity),
                ),
                _direct_origin(item.direct_origin_kind),
            )
    if grouped["plant_group"]:
        group_statement = (
            select(PlantGroup, BotanicalIdentity)
            .join(BotanicalIdentity, BotanicalIdentity.id == PlantGroup.botanical_identity_id)
            .where(PlantGroup.id.in_(grouped["plant_group"]))
        )
        for item, identity in database.execute(group_statement):
            result[("plant_group", item.id)] = (
                PlantGroupLineageNode(
                    id=item.id,
                    label=item.label,
                    lifecycle=item.lifecycle,
                    botanical_identity=_identity_summary(identity),
                ),
                _direct_origin(item.direct_origin_kind),
            )
    if grouped["vegetative_lot"]:
        lot_statement = (
            select(VegetativeLot, BotanicalIdentity)
            .join(BotanicalIdentity, BotanicalIdentity.id == VegetativeLot.botanical_identity_id)
            .where(VegetativeLot.id.in_(grouped["vegetative_lot"]))
        )
        for item, identity in database.execute(lot_statement):
            result[("vegetative_lot", item.id)] = (
                VegetativeLotLineageNode(
                    id=item.id,
                    label=item.label,
                    lifecycle=item.lifecycle,
                    botanical_identity=_identity_summary(identity),
                ),
                None,
            )
    if grouped["propagation_attempt"]:
        for item in database.scalars(
            select(PropagationAttempt).where(
                PropagationAttempt.id.in_(grouped["propagation_attempt"])
            )
        ):
            result[("propagation_attempt", item.id)] = (
                PropagationAttemptLineageNode(
                    id=item.id,
                    label=item.label,
                    lifecycle=item.lifecycle,
                ),
                None,
            )
    return result


def lineage(database: Session, subject: LineageKey) -> LineageResponse:
    keys = _walk(database, subject)
    summaries = _summaries(database, keys)
    if any(key not in summaries for key in keys):
        raise RuntimeError("Persisted lineage references a missing concrete record")
    return LineageResponse(
        subject=summaries[keys[0]][0], ancestors=[summaries[key][0] for key in keys[1:]]
    )


# The six explicit downstream edges: each child's own concrete source column.
_CHILD_EDGES = """
    SELECT 'sowing'::text AS kind, id, 'seed_lot'::text AS parent_kind, seed_lot_id AS parent_id
    FROM sowings
    UNION ALL
    SELECT 'plant', id, 'sowing', originating_sowing_id FROM plants
    WHERE originating_sowing_id IS NOT NULL
    UNION ALL
    SELECT 'plant_group', id, 'sowing', originating_sowing_id FROM plant_groups
    WHERE originating_sowing_id IS NOT NULL
    UNION ALL
    SELECT 'plant', id, 'plant_group', originating_plant_group_id FROM plants
    WHERE originating_plant_group_id IS NOT NULL
    UNION ALL
    SELECT 'seed_lot', id, 'plant', producer_plant_id FROM seed_lots
    WHERE producer_plant_id IS NOT NULL
    UNION ALL
    SELECT 'seed_lot', id, 'plant_group', producer_plant_group_id FROM seed_lots
    WHERE producer_plant_group_id IS NOT NULL
"""

_CHILDREN = text(
    f"""
    SELECT edge.kind, edge.id, count(*) OVER () AS total
    FROM ({_CHILD_EDGES}) AS edge
    WHERE edge.parent_kind = :kind AND edge.parent_id = CAST(:item_id AS uuid)
    ORDER BY array_position(
        ARRAY['sowing', 'plant_group', 'plant', 'seed_lot'], edge.kind
    ), edge.id
    OFFSET :offset LIMIT :limit
    """
)

# Per-kind ID arrays keep each branch an indexable equality on its own source column.
_PARENT_COUNTS = text(
    """
    SELECT 'seed_lot' AS kind, seed_lot_id AS id, count(*) AS total FROM sowings
    WHERE seed_lot_id = ANY(CAST(:seed_lot AS uuid[])) GROUP BY seed_lot_id
    UNION ALL
    SELECT 'sowing', originating_sowing_id, count(*) FROM plants
    WHERE originating_sowing_id = ANY(CAST(:sowing AS uuid[])) GROUP BY originating_sowing_id
    UNION ALL
    SELECT 'sowing', originating_sowing_id, count(*) FROM plant_groups
    WHERE originating_sowing_id = ANY(CAST(:sowing AS uuid[])) GROUP BY originating_sowing_id
    UNION ALL
    SELECT 'plant_group', originating_plant_group_id, count(*) FROM plants
    WHERE originating_plant_group_id = ANY(CAST(:plant_group AS uuid[]))
    GROUP BY originating_plant_group_id
    UNION ALL
    SELECT 'plant_group', producer_plant_group_id, count(*) FROM seed_lots
    WHERE producer_plant_group_id = ANY(CAST(:plant_group AS uuid[]))
    GROUP BY producer_plant_group_id
    UNION ALL
    SELECT 'plant', producer_plant_id, count(*) FROM seed_lots
    WHERE producer_plant_id = ANY(CAST(:plant AS uuid[])) GROUP BY producer_plant_id
    """
)

_COUNT_CHILDREN = text(
    f"""
    SELECT count(*) FROM ({_CHILD_EDGES}) AS edge
    WHERE edge.parent_kind = :kind AND edge.parent_id = CAST(:item_id AS uuid)
    """
)

_CONVERSIONS = (
    select(HarvestSeedLotConversion, Harvest)
    .join(Inventory, Inventory.id == HarvestSeedLotConversion.inventory_id)
    .join(HarvestItem, HarvestItem.id == Inventory.harvest_item_id)
    .join(Harvest, Harvest.id == HarvestItem.harvest_id)
)

MAX_CHILDREN_PAGE = 100


def _nodes(database: Session, keys: list[LineageKey]) -> dict[LineageKey, AncestryNode]:
    """Bounded batches: records, one grouped descendant count and one conversion lookup."""
    summaries = _summaries(database, keys)
    if any(key not in summaries for key in keys):
        raise RuntimeError("Persisted lineage references a missing concrete record")
    counts: dict[LineageKey, int] = {}
    if keys:
        ids: dict[str, list[UUID]] = {"seed_lot": [], "sowing": [], "plant": [], "plant_group": []}
        for kind, item_id in keys:
            ids[kind].append(item_id)
        for row in database.execute(_PARENT_COUNTS, ids).mappings():
            key = (cast(LineageKind, row["kind"]), cast(UUID, row["id"]))
            counts[key] = counts.get(key, 0) + int(row["total"])
    lot_ids = [item_id for kind, item_id in keys if kind == "seed_lot"]
    evidence: dict[UUID, HarvestConversionEvidence] = {}
    if lot_ids:
        statement = _CONVERSIONS.where(HarvestSeedLotConversion.seed_lot_id.in_(lot_ids))
        for conversion, harvest in database.execute(statement):
            evidence[conversion.seed_lot_id] = HarvestConversionEvidence(
                conversion_id=conversion.id,
                status=cast(Literal["applied", "reversed"], conversion.status),
                harvest_id=harvest.id,
                harvest_label=harvest.label,
                harvested_on=None
                if harvest.occurred_on_precision is None
                else PartialDate(
                    precision=harvest.occurred_on_precision,
                    year=harvest.occurred_on_year,
                    month=harvest.occurred_on_month,
                    day=harvest.occurred_on_day,
                ),
            )
    return {
        key: AncestryNode(
            record=summaries[key][0],
            origin=summaries[key][1],
            harvest_conversion=evidence.get(key[1]) if key[0] == "seed_lot" else None,
            descendant_count=counts.get(key, 0),
        )
        for key in keys
    }


def exists(database: Session, subject: LineageKey) -> bool:
    model = {"seed_lot": SeedLot, "sowing": Sowing, "plant": Plant, "plant_group": PlantGroup}
    return database.get(model[subject[0]], subject[1]) is not None


def children(
    database: Session, parent: LineageKey, *, offset: int = 0, limit: int = 25
) -> AncestryChildren:
    limit = min(limit, MAX_CHILDREN_PAGE)
    rows = list(
        database.execute(
            _CHILDREN,
            {"kind": parent[0], "item_id": parent[1], "offset": offset, "limit": limit},
        ).mappings()
    )
    keys = [(cast(LineageKind, row["kind"]), cast(UUID, row["id"])) for row in rows]
    if rows:
        total = int(rows[0]["total"])
    else:
        # An offset past the end returns no rows; the total still comes from the edges.
        total = int(
            database.execute(
                _COUNT_CHILDREN, {"kind": parent[0], "item_id": parent[1]}
            ).scalar_one()
        )
    nodes = _nodes(database, keys)
    return AncestryChildren(
        total=total, offset=offset, limit=limit, items=[nodes[key] for key in keys]
    )


def ancestry(database: Session, subject: LineageKey, *, limit: int = 25) -> AncestryResponse:
    """Recorded upstream chain (nearest first) and the first page of immediate descendants."""
    keys = _walk(database, subject)
    nodes = _nodes(database, keys)
    return AncestryResponse(
        focus=nodes[keys[0]],
        ancestors=[nodes[key] for key in keys[1:]],
        children=children(database, subject, limit=limit),
    )
