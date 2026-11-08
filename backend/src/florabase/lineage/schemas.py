from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from florabase.plants.model import DirectOriginKind, PlantGroupLifecycle, PlantLifecycle
from florabase.seed_lots.model import SeedLotLifecycle, SeedLotSourceKind
from florabase.seed_lots.schemas import PartialDate
from florabase.sowings.model import SowingLifecycle


class BotanicalIdentitySummary(BaseModel):
    id: UUID
    display_label: str


class SeedLotLineageNode(BaseModel):
    kind: Literal["seed_lot"] = "seed_lot"
    id: UUID
    label: str | None
    lifecycle: SeedLotLifecycle
    botanical_identity: BotanicalIdentitySummary


class SowingLineageNode(BaseModel):
    kind: Literal["sowing"] = "sowing"
    id: UUID
    label: str | None
    lifecycle: SowingLifecycle


class PlantLineageNode(BaseModel):
    kind: Literal["plant"] = "plant"
    id: UUID
    label: str | None
    lifecycle: PlantLifecycle
    botanical_identity: BotanicalIdentitySummary


class PlantGroupLineageNode(BaseModel):
    kind: Literal["plant_group"] = "plant_group"
    id: UUID
    label: str | None
    lifecycle: PlantGroupLifecycle
    botanical_identity: BotanicalIdentitySummary


LineageNode = Annotated[
    SeedLotLineageNode | SowingLineageNode | PlantLineageNode | PlantGroupLineageNode,
    Field(discriminator="kind"),
]


class LineageResponse(BaseModel):
    subject: LineageNode
    ancestors: list[LineageNode]


class HarvestConversionEvidence(BaseModel):
    """The explicit HARVEST-003 conversion that recorded a SeedLot's producer."""

    conversion_id: UUID
    status: Literal["applied", "reversed"]
    harvest_id: UUID
    harvest_label: str | None
    harvested_on: PartialDate | None


class AncestryNode(BaseModel):
    record: LineageNode
    # The record's own recorded origin kind; absent for Sowings and records with a recorded source.
    origin: SeedLotSourceKind | DirectOriginKind | None
    harvest_conversion: HarvestConversionEvidence | None
    descendant_count: int


class AncestryChildren(BaseModel):
    total: int
    offset: int
    limit: int
    items: list[AncestryNode]


class AncestryResponse(BaseModel):
    focus: AncestryNode
    # Nearest first, exactly as the recorded upstream walk.
    ancestors: list[AncestryNode]
    children: AncestryChildren
