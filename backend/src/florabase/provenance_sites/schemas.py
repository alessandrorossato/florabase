import unicodedata
from datetime import datetime
from decimal import Decimal
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _single_line(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("Name must not be blank")
    if any(unicodedata.category(character) == "Cc" for character in normalized):
        raise ValueError("Name must not contain control characters")
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
        raise ValueError("Notes must not contain unsupported control characters")
    return normalized


class ProvenanceSiteWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(max_length=255)
    geographic_place_id: UUID | None = None
    latitude: Decimal | None = Field(default=None, ge=-90, le=90, max_digits=9, decimal_places=6)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180, max_digits=9, decimal_places=6)
    coordinate_accuracy_m: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=3
    )
    notes: str | None = Field(default=None, max_length=20_000)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        return _single_line(value) if isinstance(value, str) else value

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value: object) -> object:
        return _notes(value) if value is None or isinstance(value, str) else value

    @model_validator(mode="after")
    def coherent_coordinates(self) -> Self:
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be supplied together")
        if self.coordinate_accuracy_m is not None and self.latitude is None:
            raise ValueError("Coordinate accuracy requires latitude and longitude")
        return self


class ProvenanceSiteCreate(ProvenanceSiteWrite):
    pass


class ProvenanceSiteUpdate(ProvenanceSiteWrite):
    pass


class ProvenanceSiteUsage(BaseModel):
    seed_lots: int = 0
    plants: int = 0
    plant_groups: int = 0


class ProvenanceSiteResponse(ProvenanceSiteWrite):
    id: UUID
    geographic_place_path: str | None
    usage: ProvenanceSiteUsage
    created_at: datetime
    updated_at: datetime


class ProvenanceSiteSummary(BaseModel):
    id: UUID
    name: str
    geographic_place_path: str | None
    latitude: Decimal | None
    longitude: Decimal | None


class ProvenanceMapBotanicalIdentity(BaseModel):
    id: UUID
    display_label: str


class ProvenanceMapRecord(BaseModel):
    record_type: Literal["seed_lot", "plant", "plant_group"]
    id: UUID
    label: str | None
    botanical_identity: ProvenanceMapBotanicalIdentity
    lifecycle: str
    is_active: bool


class ProvenanceMapUsage(BaseModel):
    seed_lots: int
    plants: int
    plant_groups: int
    total: int


class ProvenanceMapSite(BaseModel):
    id: UUID
    name: str
    latitude: Decimal
    longitude: Decimal
    coordinate_accuracy_m: Decimal | None
    geographic_place_id: UUID | None
    geographic_place_path: str | None
    usage: ProvenanceMapUsage
    records: list[ProvenanceMapRecord]


class ProvenanceMapResponse(BaseModel):
    total_provenance_sites: int
    coordinate_less_sites: int
    sites: list[ProvenanceMapSite]
