import unicodedata
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from florabase.plants.model import PlantGroupLifecycle, PlantLifecycle
from florabase.plants.schemas import (
    PlantGroupQuantity,
    PlantGroupResponse,
    PlantResponse,
)
from florabase.seed_lots.schemas import PartialDate, SeedLotResponse, SeedQuantity
from florabase.sowings.model import SowingLifecycle
from florabase.sowings.schemas import SowingDetails, SowingResponse


class NoSourceAdjustment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["none"] = "none"


class PartialSourceAdjustment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["partial"]
    resulting_quantity: SeedQuantity | None = None


class UseAllSourceAdjustment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["use_all"]


SourceAdjustment = Annotated[
    NoSourceAdjustment | PartialSourceAdjustment | UseAllSourceAdjustment,
    Field(discriminator="mode"),
]


class SeedLotSowingTransitionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sowing: SowingDetails
    source_adjustment: SourceAdjustment

    @model_validator(mode="after")
    def reject_reversed_result(self) -> Self:
        if self.sowing.lifecycle == SowingLifecycle.REVERSED:
            raise ValueError("Reversed is assigned only by propagation reversal")
        return self


class SeedLotSowingTransitionResponse(BaseModel):
    sowing: SowingResponse
    seed_lot: SeedLotResponse


def _single_line(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    if not normalized:
        return None
    if any(unicodedata.category(character) == "Cc" for character in normalized):
        raise ValueError("Value must not contain control characters")
    return normalized


def _notes(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return None
    if any(
        unicodedata.category(character) == "Cc" and character not in {"\n", "\t"}
        for character in normalized
    ):
        raise ValueError("Value must not contain unsupported control characters")
    return normalized


class DescendantFromSowingDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")

    botanical_identity_id: UUID
    label: str | None = Field(default=None, max_length=255)
    collection_entry_date: PartialDate | None = None
    location_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=20_000)

    @field_validator("label", mode="before")
    @classmethod
    def normalize_label(cls, value: object) -> object:
        return _single_line(value) if value is None or isinstance(value, str) else value

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value: object) -> object:
        return _notes(value) if value is None or isinstance(value, str) else value


class PlantFromSowingCreate(DescendantFromSowingDetails):
    lifecycle: PlantLifecycle = PlantLifecycle.ACTIVE

    @model_validator(mode="after")
    def reject_historical_operation_lifecycle(self) -> Self:
        if self.lifecycle in {PlantLifecycle.REVERSED, PlantLifecycle.REINTEGRATED}:
            raise ValueError("Historical operation lifecycles cannot be assigned at creation")
        return self


class PlantGroupFromSowingCreate(DescendantFromSowingDetails):
    quantity: PlantGroupQuantity | None = None
    lifecycle: PlantGroupLifecycle = PlantGroupLifecycle.ACTIVE

    @model_validator(mode="after")
    def validate_quantity_lifecycle(self) -> Self:
        if self.lifecycle == PlantGroupLifecycle.REVERSED:
            raise ValueError("Reversed is assigned only by propagation reversal")
        if (
            self.quantity is not None
            and self.quantity.value == 0
            and self.lifecycle
            not in {
                PlantGroupLifecycle.COMPLETED,
                PlantGroupLifecycle.DEAD,
                PlantGroupLifecycle.DISCARDED,
            }
        ):
            raise ValueError("Exact zero is only valid for a completed, dead, or discarded group")
        return self


class SowingPlantTransitionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plant: PlantFromSowingCreate
    resulting_sowing_lifecycle: SowingLifecycle

    @model_validator(mode="after")
    def reject_reversed_source(self) -> Self:
        if self.resulting_sowing_lifecycle == SowingLifecycle.REVERSED:
            raise ValueError("Reversed is assigned only by propagation reversal")
        return self


class SowingPlantGroupTransitionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plant_group: PlantGroupFromSowingCreate
    resulting_sowing_lifecycle: SowingLifecycle

    @model_validator(mode="after")
    def reject_reversed_source(self) -> Self:
        if self.resulting_sowing_lifecycle == SowingLifecycle.REVERSED:
            raise ValueError("Reversed is assigned only by propagation reversal")
        return self


class SowingPlantTransitionResponse(BaseModel):
    plant: PlantResponse
    sowing: SowingResponse


class SowingPlantGroupTransitionResponse(BaseModel):
    plant_group: PlantGroupResponse
    sowing: SowingResponse


class PropagationPlantSummary(BaseModel):
    id: UUID
    botanical_identity_id: UUID
    label: str | None
    lifecycle: PlantLifecycle


class PropagationPlantGroupSummary(BaseModel):
    id: UUID
    botanical_identity_id: UUID
    label: str | None
    lifecycle: PlantGroupLifecycle
    quantity: PlantGroupQuantity | None


class SowingPropagationSummary(BaseModel):
    sowing_id: UUID
    lifecycle: SowingLifecycle
    germinated_count: int | None
    plants: list[PropagationPlantSummary]
    plant_groups: list[PropagationPlantGroupSummary]
    exact_descendant_count: int
    approximate_plant_group_count: int
    unknown_plant_group_count: int
