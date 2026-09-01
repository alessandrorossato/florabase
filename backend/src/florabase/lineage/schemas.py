from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from florabase.plants.model import PlantGroupLifecycle, PlantLifecycle
from florabase.seed_lots.model import SeedLotLifecycle
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
