import unicodedata
from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from florabase.events.model import EventKind
from florabase.plants.model import PlantGroupLifecycle, PlantLifecycle
from florabase.plants.schemas import (
    BotanicalIdentitySummary,
    LocationSummary,
    PlantGroupResponse,
    PlantResponse,
)
from florabase.seed_lots.schemas import PartialDate


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


def _single_line(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    if not normalized:
        return None
    if any(unicodedata.category(character) == "Cc" for character in normalized):
        raise ValueError("Value must not contain control characters")
    return normalized


class EventWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: EventKind
    occurred_on: PartialDate | None = None
    notes: str | None = Field(default=None, max_length=20_000)
    destination_location_id: UUID | None = None
    recipient: str | None = Field(default=None, max_length=255)
    resulting_plant_id: UUID | None = None

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value: object) -> object:
        if value is not None and not isinstance(value, str):
            return value
        return _notes(value)

    @field_validator("recipient", mode="before")
    @classmethod
    def normalize_recipient(cls, value: object) -> object:
        if value is not None and not isinstance(value, str):
            return value
        return _single_line(value)

    @model_validator(mode="after")
    def validate_destination(self) -> Self:
        if self.kind == EventKind.MOVEMENT and self.destination_location_id is None:
            raise ValueError("Movement requires a destination Location")
        if self.kind != EventKind.MOVEMENT and self.destination_location_id is not None:
            raise ValueError("Only movement may have a destination Location")
        if self.kind != EventKind.TRANSFER and self.recipient is not None:
            raise ValueError("Only transfer may have a recipient")
        operation_kinds = {EventKind.EXTRACTION, EventKind.REINTEGRATION}
        if self.kind in operation_kinds and self.resulting_plant_id is None:
            raise ValueError("Extraction and reintegration require a resulting Plant")
        if self.kind not in operation_kinds and self.resulting_plant_id is not None:
            raise ValueError("Only extraction or reintegration may have a resulting Plant")
        return self


class EventCreate(EventWrite):
    pass


class EventUpdate(EventWrite):
    pass


class TransferCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    occurred_on: PartialDate | None = None
    recipient: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=20_000)

    @field_validator("recipient", mode="before")
    @classmethod
    def normalize_recipient(cls, value: object) -> object:
        if value is not None and not isinstance(value, str):
            return value
        return _single_line(value)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value: object) -> object:
        if value is not None and not isinstance(value, str):
            return value
        return _notes(value)


class PlantEventTarget(BaseModel):
    type: Literal["plant"] = "plant"
    id: UUID
    label: str | None
    lifecycle: PlantLifecycle
    botanical_identity: BotanicalIdentitySummary


class PlantGroupEventTarget(BaseModel):
    type: Literal["plant_group"] = "plant_group"
    id: UUID
    label: str | None
    lifecycle: PlantGroupLifecycle
    botanical_identity: BotanicalIdentitySummary


EventTarget = Annotated[
    PlantEventTarget | PlantGroupEventTarget,
    Field(discriminator="type"),
]


class ResultingPlantSummary(BaseModel):
    id: UUID
    label: str | None
    botanical_identity: BotanicalIdentitySummary


class EventResponse(BaseModel):
    id: UUID
    target: EventTarget
    kind: EventKind
    occurred_on: PartialDate | None
    notes: str | None
    destination_location_id: UUID | None
    destination_location: LocationSummary | None
    recipient: str | None
    resulting_plant_id: UUID | None
    resulting_plant: ResultingPlantSummary | None
    operation_kind: str | None = None
    operation_status: str | None = None
    created_at: datetime
    updated_at: datetime


class PlantExtractionResponse(BaseModel):
    plant: PlantResponse
    plant_group: PlantGroupResponse
    event: EventResponse


class PlantReintegrationResponse(BaseModel):
    plant: PlantResponse
    plant_group: PlantGroupResponse
    event: EventResponse
    operation_status: Literal["reversed"] = "reversed"


class PlantTransferResponse(BaseModel):
    plant: PlantResponse
    event: EventResponse


class PlantGroupTransferResponse(BaseModel):
    plant_group: PlantGroupResponse
    event: EventResponse
