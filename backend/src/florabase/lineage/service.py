from dataclasses import dataclass
from typing import Literal, cast
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import BotanicalIdentityResponse
from florabase.lineage.schemas import (
    BotanicalIdentitySummary,
    LineageNode,
    LineageResponse,
    PlantGroupLineageNode,
    PlantLineageNode,
    SeedLotLineageNode,
    SowingLineageNode,
)
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing

LineageKind = Literal["seed_lot", "sowing", "plant", "plant_group"]
LineageKey = tuple[LineageKind, UUID]


@dataclass(frozen=True)
class LineageCycleError(Exception):
    code: str = "lineage_cycle"
    message: str = "The proposed producer would create a lineage cycle"


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
    if producer is not None and ("seed_lot", seed_lot_id) in _walk(database, producer):
        raise LineageCycleError()


def _identity_summary(identity: BotanicalIdentity) -> BotanicalIdentitySummary:
    response = BotanicalIdentityResponse.from_model(identity)
    return BotanicalIdentitySummary(id=response.id, display_label=response.display_label)


def _summaries(database: Session, keys: list[LineageKey]) -> dict[LineageKey, LineageNode]:
    grouped: dict[LineageKind, list[UUID]] = {
        "seed_lot": [],
        "sowing": [],
        "plant": [],
        "plant_group": [],
    }
    for kind, item_id in keys:
        grouped[kind].append(item_id)

    result: dict[LineageKey, LineageNode] = {}
    if grouped["seed_lot"]:
        statement = (
            select(SeedLot, BotanicalIdentity)
            .join(BotanicalIdentity, BotanicalIdentity.id == SeedLot.botanical_identity_id)
            .where(SeedLot.id.in_(grouped["seed_lot"]))
        )
        for item, identity in database.execute(statement):
            result[("seed_lot", item.id)] = SeedLotLineageNode(
                id=item.id,
                label=item.label,
                lifecycle=item.lifecycle,
                botanical_identity=_identity_summary(identity),
            )
    if grouped["sowing"]:
        for item in database.scalars(select(Sowing).where(Sowing.id.in_(grouped["sowing"]))):
            result[("sowing", item.id)] = SowingLineageNode(
                id=item.id, label=item.label, lifecycle=item.lifecycle
            )
    if grouped["plant"]:
        plant_statement = (
            select(Plant, BotanicalIdentity)
            .join(BotanicalIdentity, BotanicalIdentity.id == Plant.botanical_identity_id)
            .where(Plant.id.in_(grouped["plant"]))
        )
        for item, identity in database.execute(plant_statement):
            result[("plant", item.id)] = PlantLineageNode(
                id=item.id,
                label=item.label,
                lifecycle=item.lifecycle,
                botanical_identity=_identity_summary(identity),
            )
    if grouped["plant_group"]:
        group_statement = (
            select(PlantGroup, BotanicalIdentity)
            .join(BotanicalIdentity, BotanicalIdentity.id == PlantGroup.botanical_identity_id)
            .where(PlantGroup.id.in_(grouped["plant_group"]))
        )
        for item, identity in database.execute(group_statement):
            result[("plant_group", item.id)] = PlantGroupLineageNode(
                id=item.id,
                label=item.label,
                lifecycle=item.lifecycle,
                botanical_identity=_identity_summary(identity),
            )
    return result


def lineage(database: Session, subject: LineageKey) -> LineageResponse:
    keys = _walk(database, subject)
    summaries = _summaries(database, keys)
    if any(key not in summaries for key in keys):
        raise RuntimeError("Persisted lineage references a missing concrete record")
    return LineageResponse(
        subject=summaries[keys[0]], ancestors=[summaries[key] for key in keys[1:]]
    )
