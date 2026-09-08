import re
import unicodedata
from datetime import datetime
from typing import TYPE_CHECKING, Literal, Self
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from florabase.plants.model import PlantGroupLifecycle, PlantLifecycle
from florabase.seed_lots.model import SeedLotLifecycle
from florabase.seed_lots.schemas import PartialDate
from florabase.suppliers.model import SupplierKind

if TYPE_CHECKING:
    from florabase.suppliers.model import Supplier


def _contains_control(value: str, *, allow_newlines: bool = False) -> bool:
    allowed = {"\n", "\t"} if allow_newlines else set()
    return any(
        unicodedata.category(character) == "Cc" and character not in allowed for character in value
    )


def _single_line(value: str | None, *, required: bool = False) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    if not normalized:
        if required:
            raise ValueError("Value must not be blank")
        return None
    if _contains_control(normalized):
        raise ValueError("Value must not contain control characters")
    return normalized


def _notes(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return None
    if _contains_control(normalized, allow_newlines=True):
        raise ValueError("Value must not contain unsupported control characters")
    return normalized


class SupplierWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(max_length=255)
    kind: SupplierKind
    website: str | None = Field(default=None, max_length=2048)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=20_000)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        return _single_line(value, required=True) if isinstance(value, str) else value

    @field_validator("website", mode="before")
    @classmethod
    def normalize_website(cls, value: object) -> object:
        if value is not None and not isinstance(value, str):
            return value
        normalized = _single_line(value)
        if normalized is None:
            return None
        parsed = urlsplit(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Website must be an HTTP or HTTPS URL")
        return normalized

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if value is not None and not isinstance(value, str):
            return value
        normalized = _single_line(value)
        if normalized is None:
            return None
        if not re.fullmatch(r"[^@\s]+@[^@\s]+", normalized):
            raise ValueError("Email must be a reasonable email address")
        return normalized

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, value: object) -> object:
        if value is not None and not isinstance(value, str):
            return value
        return _single_line(value)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value: object) -> object:
        if value is not None and not isinstance(value, str):
            return value
        return _notes(value)


class SupplierCreate(SupplierWrite):
    pass


class SupplierUpdate(SupplierWrite):
    pass


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    kind: SupplierKind
    website: str | None
    email: str | None
    phone: str | None
    notes: str | None
    retired_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, supplier: Supplier) -> Self:
        return cls.model_validate(supplier)


class SupplierUsageCounts(BaseModel):
    seed_lots_active: int
    seed_lots_total: int
    plants_active: int
    plants_total: int
    plant_groups_active: int
    plant_groups_total: int
    direct_records_active: int
    direct_records_total: int


class SupplierListResponse(SupplierResponse):
    usage_counts: SupplierUsageCounts


class SupplierBotanicalIdentitySummary(BaseModel):
    id: UUID
    display_label: str


class SupplierSeedLotLink(BaseModel):
    id: UUID
    label: str | None
    botanical_identity: SupplierBotanicalIdentitySummary
    lifecycle: SeedLotLifecycle
    acquisition_date: PartialDate | None


class SupplierPlantLink(BaseModel):
    id: UUID
    label: str | None
    botanical_identity: SupplierBotanicalIdentitySummary
    lifecycle: PlantLifecycle
    collection_entry_date: PartialDate | None


class SupplierPlantGroupLink(BaseModel):
    id: UUID
    label: str | None
    botanical_identity: SupplierBotanicalIdentitySummary
    lifecycle: PlantGroupLifecycle
    collection_entry_date: PartialDate | None


class SupplierRecentAcquisition(BaseModel):
    record_type: Literal["seed_lot", "plant", "plant_group"]
    id: UUID
    label: str | None
    botanical_identity: SupplierBotanicalIdentitySummary
    lifecycle: SeedLotLifecycle | PlantLifecycle | PlantGroupLifecycle
    acquired_on: PartialDate


class SupplierDetailResponse(SupplierResponse):
    usage_counts: SupplierUsageCounts
    seed_lots: list[SupplierSeedLotLink]
    plants: list[SupplierPlantLink]
    plant_groups: list[SupplierPlantGroupLink]
    recent_acquisitions: list[SupplierRecentAcquisition]
