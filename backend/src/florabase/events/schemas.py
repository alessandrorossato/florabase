import unicodedata
from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from florabase.events.model import EventKind
from florabase.plants.model import PlantGroupLifecycle, PlantLifecycle
from florabase.plants.schemas import LocationSummary
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


class EventWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: EventKind
    occurred_on: PartialDate | None = None
    notes: str | None = Field(default=None, max_length=20_000)
    destination_location_id: UUID | None = None

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value: object) -> object:
        if value is not None and not isinstance(value, str):
            return value
        return _notes(value)

    @model_validator(mode="after")
    def validate_destination(self) -> Self:
        if self.kind == EventKind.MOVEMENT and self.destination_location_id is None:
            raise ValueError("Movement requires a destination Location")
        if self.kind != EventKind.MOVEMENT and self.destination_location_id is not None:
            raise ValueError("Only movement may have a destination Location")
        return self


class EventCreate(EventWrite):
    pass


class EventUpdate(EventWrite):
    pass


class PlantEventTarget(BaseModel):
    type: Literal["plant"] = "plant"
    id: UUID
    label: str | None
    lifecycle: PlantLifecycle


class PlantGroupEventTarget(BaseModel):
    type: Literal["plant_group"] = "plant_group"
    id: UUID
    label: str | None
    lifecycle: PlantGroupLifecycle


EventTarget = Annotated[
    PlantEventTarget | PlantGroupEventTarget,
    Field(discriminator="type"),
]


class EventResponse(BaseModel):
    id: UUID
    target: EventTarget
    kind: EventKind
    occurred_on: PartialDate | None
    notes: str | None
    destination_location_id: UUID | None
    destination_location: LocationSummary | None
    created_at: datetime
    updated_at: datetime
