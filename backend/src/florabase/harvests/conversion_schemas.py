from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from florabase.harvests.inventory_schemas import InventorySnapshot
from florabase.harvests.schemas import HarvestQuantity
from florabase.seed_lots.schemas import PartialDate, SeedQuantity, _notes, _single_line


class ConversionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["partial", "use_all"]
    botanical_identity_id: UUID | None = None
    label: str | None = Field(default=None, max_length=255)
    quantity: SeedQuantity | None = None
    resulting_quantity: HarvestQuantity | None = None
    location_id: UUID | None = None
    expected_viability_until: PartialDate | None = None
    notes: str | None = Field(default=None, max_length=20000)

    @field_validator("label")
    @classmethod
    def label_text(cls, value: str | None) -> str | None:
        return _single_line(value)

    @field_validator("notes")
    @classmethod
    def notes_text(cls, value: str | None) -> str | None:
        return _notes(value)

    @model_validator(mode="after")
    def positive_transfer(self) -> ConversionCreate:
        if self.quantity and self.quantity.value <= 0:
            raise ValueError("Transferred seed quantity must be positive")
        return self


class ConversionResponse(BaseModel):
    id: UUID
    inventory_id: UUID
    harvest_id: UUID
    harvest_item_id: UUID
    disposition_id: UUID
    seed_lot_id: UUID
    seed_lot_label: str | None
    status: Literal["applied", "reversed"]
    quantity: SeedQuantity | None
    before: InventorySnapshot
    after: InventorySnapshot
    created_at: datetime
    reversed_at: datetime | None


class ConversionEligibility(BaseModel):
    status: Literal["safe", "blocked"]
    reasons: list[str]
