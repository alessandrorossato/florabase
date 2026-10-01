from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from florabase.collection_photos.schemas import PrimaryPhotoResponse
from florabase.harvests.model import MaterialKind
from florabase.plants.schemas import BotanicalIdentitySummary
from florabase.seed_lots.schemas import DecimalString, PartialDate, _notes, _single_line


class HarvestQuantity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["item_count", "weight"]
    value: DecimalString
    unit: Literal["mg", "g", "kg"] | None = None
    is_approximate: bool

    @model_validator(mode="after")
    def validate_quantity(self) -> Self:
        if not self.value.is_finite() or self.value <= 0:
            raise ValueError(
                "Harvest quantity must be finite and positive; use unknown when not recorded"
            )
        if self.kind == "item_count":
            if self.value != self.value.to_integral_value() or self.unit is not None:
                raise ValueError("Item count must be a whole number without a weight unit")
        elif self.unit is None:
            raise ValueError("Weight requires a unit")
        return self


class HarvestItemWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID | None = None
    material_kind: MaterialKind
    description: str | None = Field(default=None, max_length=2000)
    quantity: HarvestQuantity | None = None

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        return _notes(value)


class HarvestWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plant_id: UUID | None = None
    plant_group_id: UUID | None = None
    label: str | None = Field(default=None, max_length=255)
    occurred_on: PartialDate | None = None
    notes: str | None = Field(default=None, max_length=20000)
    items: list[HarvestItemWrite] = Field(min_length=1, max_length=100)

    @field_validator("label")
    @classmethod
    def normalize_label(cls, value: str | None) -> str | None:
        return _single_line(value)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return _notes(value)

    @model_validator(mode="after")
    def validate_source(self) -> Self:
        if (self.plant_id is None) == (self.plant_group_id is None):
            raise ValueError("Choose exactly one source Plant or PlantGroup")
        ids = [item.id for item in self.items if item.id is not None]
        if len(ids) != len(set(ids)):
            raise ValueError("Material line IDs must be unique")
        return self


class HarvestItemResponse(BaseModel):
    id: UUID
    display_order: int
    material_kind: MaterialKind
    description: str | None
    quantity: HarvestQuantity | None


class HarvestSource(BaseModel):
    type: Literal["plant", "plant_group"]
    id: UUID
    label: str | None
    display_name: str
    lifecycle: str
    botanical_identity: BotanicalIdentitySummary
    primary_photo: PrimaryPhotoResponse | None = None


class HarvestResponse(BaseModel):
    id: UUID
    plant_id: UUID | None
    plant_group_id: UUID | None
    label: str | None
    display_title: str
    source: HarvestSource
    occurred_on: PartialDate | None
    notes: str | None
    items: list[HarvestItemResponse]
    event_id: UUID
    primary_photo: PrimaryPhotoResponse | None = None
    created_at: datetime
    updated_at: datetime
