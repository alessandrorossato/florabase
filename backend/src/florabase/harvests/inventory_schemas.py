from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from florabase.harvests.model import MaterialKind
from florabase.harvests.schemas import HarvestQuantity, HarvestSource
from florabase.seed_lots.schemas import PartialDate, _notes

InventoryState = Literal["active", "depleted"]
DispositionKind = Literal["consumed", "processed", "discarded", "gifted", "used_for_propagation"]


class InventoryWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: InventoryState
    quantity: HarvestQuantity | None
    location_id: UUID | None = None

    @model_validator(mode="after")
    def coherent_state(self) -> Self:
        if self.state == "depleted" and self.quantity is not None:
            raise ValueError("Depleted inventory has no remaining quantity")
        return self


class DispositionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: DispositionKind
    mode: Literal["partial", "use_all"]
    occurred_on: PartialDate | None = None
    quantity: HarvestQuantity | None = None
    resulting_quantity: HarvestQuantity | None = None
    notes: str | None = Field(default=None, max_length=20000)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return _notes(value)

    @model_validator(mode="after")
    def explicit_all(self) -> Self:
        if self.mode == "use_all" and (
            self.quantity is not None or self.resulting_quantity is not None
        ):
            raise ValueError("Use all takes the current balance; omit usage and resulting quantity")
        return self


class InventorySnapshot(BaseModel):
    state: InventoryState
    quantity: HarvestQuantity | None


class DispositionResponse(BaseModel):
    id: UUID
    inventory_id: UUID
    kind: DispositionKind
    mode: Literal["partial", "use_all"]
    occurred_on: PartialDate | None
    quantity: HarvestQuantity | None
    before: InventorySnapshot
    after: InventorySnapshot
    notes: str | None
    created_at: datetime


class InventoryLocation(BaseModel):
    id: UUID
    display_path: str


class InventoryResponse(InventorySnapshot):
    id: UUID
    harvest_item_id: UUID
    harvest_id: UUID
    harvest_title: str
    source: HarvestSource
    material_kind: MaterialKind
    description: str | None
    location: InventoryLocation | None
    has_dispositions: bool
    created_at: datetime
    updated_at: datetime
