import unicodedata
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from florabase.collection_photos.schemas import PrimaryPhotoResponse
from florabase.events.model import EventKind, LengthUnit, MeasurementQuantity
from florabase.plants.model import PlantGroupLifecycle, PlantLifecycle
from florabase.plants.schemas import (
    BotanicalIdentitySummary,
    LocationSummary,
    PlantGroupResponse,
    PlantResponse,
)
from florabase.seed_lots.schemas import DecimalString, PartialDate


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


_MILLIMETRES = {LengthUnit.MM: Decimal(1), LengthUnit.CM: Decimal(10), LengthUnit.M: Decimal(1000)}
_MAX_HEIGHT_MM = Decimal(200_000)  # Tallest recorded trees are ~116 m; larger values are typos.


class Measurement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: MeasurementQuantity
    value: DecimalString
    unit: LengthUnit
    is_approximate: bool = False

    @model_validator(mode="after")
    def validate_value(self) -> Self:
        if not self.value.is_finite() or self.value <= 0:
            raise ValueError("Measurement value must be a positive number")
        # Plain notation keeps the recorded resolution and matches what PostgreSQL returns.
        self.value = Decimal(format(self.value, "f"))
        exponent = self.value.as_tuple().exponent
        if isinstance(exponent, int) and exponent < -3:
            raise ValueError("Measurement value must have at most 3 decimal places")
        if self.value * _MILLIMETRES[self.unit] > _MAX_HEIGHT_MM:
            raise ValueError("Height must not exceed 200 m")
        return self


class EventWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: EventKind
    occurred_on: PartialDate | None = None
    notes: str | None = Field(default=None, max_length=20_000)
    destination_location_id: UUID | None = None
    recipient: str | None = Field(default=None, max_length=255)
    resulting_plant_id: UUID | None = None
    measurement: Measurement | None = None

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
        if self.kind == EventKind.MEASUREMENT:
            if self.measurement is None:
                raise ValueError("Measurement requires a quantity, value and unit")
            if self.occurred_on is None:
                raise ValueError("Measurement requires an occurrence date")
        elif self.measurement is not None:
            raise ValueError("Only measurement may have a measured value")
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
    primary_photo: PrimaryPhotoResponse | None = None


class PlantGroupEventTarget(BaseModel):
    type: Literal["plant_group"] = "plant_group"
    id: UUID
    label: str | None
    lifecycle: PlantGroupLifecycle
    botanical_identity: BotanicalIdentitySummary
    primary_photo: PrimaryPhotoResponse | None = None


EventTarget = Annotated[
    PlantEventTarget | PlantGroupEventTarget,
    Field(discriminator="type"),
]


class ResultingPlantSummary(BaseModel):
    id: UUID
    label: str | None
    botanical_identity: BotanicalIdentitySummary


class MeasurementCorrectionResponse(BaseModel):
    """The measurement as recorded before a correction replaced it at `replaced_at`."""

    measurement: Measurement
    occurred_on: PartialDate
    replaced_at: datetime


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
    measurement: Measurement | None = None
    measurement_corrections: list[MeasurementCorrectionResponse] = []
    harvest_id: UUID | None = None
    harvest_title: str | None = None
    harvest_primary_photo: PrimaryPhotoResponse | None = None
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
