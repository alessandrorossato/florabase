import unicodedata
from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from florabase.plants.model import DirectOriginKind, PlantGroupLifecycle, PlantLifecycle
from florabase.seed_lots.model import PartialDatePrecision
from florabase.seed_lots.schemas import PartialDate
from florabase.sowings.model import SowingLifecycle


def _contains_control(value: str, *, allow_newlines: bool = False) -> bool:
    allowed = {"\n", "\t"} if allow_newlines else set()
    return any(
        unicodedata.category(character) == "Cc" and character not in allowed for character in value
    )


def _single_line(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    if not normalized:
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


class CollectionRecordWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    botanical_identity_id: UUID
    originating_sowing_id: UUID | None = None
    direct_origin_kind: DirectOriginKind | None = None
    direct_origin_detail: str | None = Field(default=None, max_length=255)
    supplier_id: UUID | None = None
    material_provenance_place_id: UUID | None = None
    label: str | None = Field(default=None, max_length=255)
    collection_entry_date: PartialDate | None = None
    location_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=20_000)

    @field_validator("label", "direct_origin_detail", mode="before")
    @classmethod
    def normalize_single_line(cls, value: object) -> object:
        if value is not None and not isinstance(value, str):
            return value
        return _single_line(value)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value: object) -> object:
        if value is not None and not isinstance(value, str):
            return value
        return _notes(value)

    @model_validator(mode="after")
    def validate_origin(self) -> Self:
        if self.originating_sowing_id is not None:
            if any(
                value is not None
                for value in (
                    self.direct_origin_kind,
                    self.direct_origin_detail,
                    self.supplier_id,
                    self.material_provenance_place_id,
                )
            ):
                raise ValueError("Sowing origin and direct-origin data are mutually exclusive")
        else:
            if self.direct_origin_kind is None:
                self.direct_origin_kind = DirectOriginKind.UNKNOWN
            if (
                self.direct_origin_kind != DirectOriginKind.OTHER
                and self.direct_origin_detail is not None
            ):
                raise ValueError("Direct-origin detail is only valid when origin kind is other")
        return self


class PlantWrite(CollectionRecordWrite):
    lifecycle: PlantLifecycle = PlantLifecycle.ACTIVE


class PlantCreate(PlantWrite):
    pass


class PlantUpdate(PlantWrite):
    pass


class PlantGroupQuantity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: int = Field(ge=0)
    is_approximate: bool

    @model_validator(mode="after")
    def reject_approximate_zero(self) -> Self:
        if self.value == 0 and self.is_approximate:
            raise ValueError("Zero quantity must be exact")
        return self


class PlantGroupWrite(CollectionRecordWrite):
    quantity: PlantGroupQuantity | None = None
    lifecycle: PlantGroupLifecycle = PlantGroupLifecycle.ACTIVE

    @model_validator(mode="after")
    def validate_quantity_lifecycle(self) -> Self:
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


class PlantGroupCreate(PlantGroupWrite):
    pass


class PlantGroupUpdate(PlantGroupWrite):
    pass


class BotanicalIdentitySummary(BaseModel):
    id: UUID
    display_label: str


class OriginatingSowingSummary(BaseModel):
    id: UUID
    label: str | None
    lifecycle: SowingLifecycle
    seed_lot_id: UUID
    botanical_identity_id: UUID
    botanical_identity_display_label: str


class SupplierSummary(BaseModel):
    id: UUID
    name: str


class GeographicPlaceSummary(BaseModel):
    id: UUID
    display_path: str


class LocationSummary(BaseModel):
    id: UUID
    display_path: str


class CollectionRecordResponse(BaseModel):
    id: UUID
    botanical_identity_id: UUID
    botanical_identity: BotanicalIdentitySummary
    originating_sowing_id: UUID | None
    originating_sowing: OriginatingSowingSummary | None
    direct_origin_kind: DirectOriginKind | None
    direct_origin_detail: str | None
    supplier_id: UUID | None
    supplier: SupplierSummary | None
    material_provenance_place_id: UUID | None
    material_provenance: GeographicPlaceSummary | None
    label: str | None
    collection_entry_date: PartialDate | None
    location_id: UUID | None
    location: LocationSummary | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class PlantResponse(CollectionRecordResponse):
    lifecycle: PlantLifecycle


class PlantGroupResponse(CollectionRecordResponse):
    quantity: PlantGroupQuantity | None
    lifecycle: PlantGroupLifecycle


assert {item.value for item in PartialDatePrecision} == {"year", "month", "day"}
