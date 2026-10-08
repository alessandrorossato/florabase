from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from florabase.seed_lots.schemas import PartialDate


class HistoryCategory(StrEnum):
    EVENT = "event"
    PROPAGATION = "propagation"
    GERMINATION = "germination"
    HARVEST = "harvest"
    MATERIAL = "material"


class HistorySubjectKind(StrEnum):
    PLANT = "plant"
    PLANT_GROUP = "plant_group"
    SOWING = "sowing"
    HARVEST = "harvest"
    HARVEST_INVENTORY = "harvest_inventory"
    SEED_LOT = "seed_lot"


class HistoryReference(BaseModel):
    kind: HistorySubjectKind | Literal["location"]
    id: UUID
    label: str
    harvest_id: UUID | None = None


class HistoryEntry(BaseModel):
    key: str
    category: HistoryCategory
    source_kind: Literal[
        "event", "operation_receipt", "germination", "harvest", "disposition", "conversion"
    ]
    source_id: UUID
    subtype: str
    occurred_on: PartialDate | None
    occurred_at: datetime | None
    recorded_at: datetime
    date_basis: Literal["occurred", "recorded"]
    title: str
    context: str
    primary: HistoryReference
    related: list[HistoryReference] = Field(max_length=2)
    status: Literal["applied", "reversed"] | None


class HistoryResponse(BaseModel):
    items: list[HistoryEntry]
    total: int
    offset: int
    limit: int
