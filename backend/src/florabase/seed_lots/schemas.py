import unicodedata
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    WithJsonSchema,
    field_validator,
    model_validator,
)

from florabase.seed_lots.model import (
    PartialDatePrecision,
    SeedLotLifecycle,
    SeedLotSourceKind,
    SeedQuantityKind,
    SeedWeightUnit,
)


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


class PartialDate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    precision: PartialDatePrecision
    year: int = Field(ge=1, le=9999)
    month: int | None = Field(default=None, ge=1, le=12)
    day: int | None = Field(default=None, ge=1, le=31)

    @model_validator(mode="after")
    def validate_precision(self) -> Self:
        if self.precision == PartialDatePrecision.YEAR:
            if self.month is not None or self.day is not None:
                raise ValueError("Year precision must not include month or day")
        elif self.precision == PartialDatePrecision.MONTH:
            if self.month is None or self.day is not None:
                raise ValueError("Month precision requires month and must not include day")
        elif self.month is None or self.day is None:
            raise ValueError("Day precision requires month and day")
        if self.precision == PartialDatePrecision.DAY:
            assert self.month is not None
            assert self.day is not None
            date(self.year, self.month, self.day)
        return self


DecimalString = Annotated[
    Decimal,
    PlainSerializer(lambda value: str(value), return_type=str, when_used="json"),
    WithJsonSchema(
        {
            "type": "string",
            "pattern": r"^(0|[1-9][0-9]*)(\.[0-9]+)?$",
            "description": "An exact non-negative decimal serialized as a JSON string.",
        },
        mode="serialization",
    ),
]


class SeedQuantity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: SeedQuantityKind
    value: DecimalString
    unit: SeedWeightUnit | None = None
    is_approximate: bool

    @model_validator(mode="after")
    def validate_quantity(self) -> Self:
        if not self.value.is_finite() or self.value < 0:
            raise ValueError("Quantity must be a finite non-negative value")
        if self.kind == SeedQuantityKind.SEED_COUNT:
            if self.value != self.value.to_integral_value():
                raise ValueError("Seed count must be a whole number")
            if self.unit is not None:
                raise ValueError("Seed count must not include a unit")
        elif self.unit is None:
            raise ValueError("Weight requires a unit")
        if self.value == 0 and self.is_approximate:
            raise ValueError("Zero quantity must be exact")
        return self


class SeedLotWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    botanical_identity_id: UUID
    label: str | None = Field(default=None, max_length=255)
    source_kind: SeedLotSourceKind = SeedLotSourceKind.UNKNOWN
    source_detail: str | None = Field(default=None, max_length=255)
    supplier_id: UUID | None = None
    material_provenance_place_id: UUID | None = None
    acquisition_date: PartialDate | None = None
    harvest_date: PartialDate | None = None
    quantity: SeedQuantity | None = None
    expected_viability_until: PartialDate | None = None
    location_id: UUID | None = None
    lifecycle: SeedLotLifecycle = SeedLotLifecycle.ACTIVE
    notes: str | None = Field(default=None, max_length=20_000)

    @field_validator("label", "source_detail", mode="before")
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
    def validate_source_and_lifecycle(self) -> Self:
        if self.source_kind != SeedLotSourceKind.OTHER and self.source_detail is not None:
            raise ValueError("Source detail is only valid when source kind is other")
        if (
            self.quantity is not None
            and self.quantity.value == 0
            and self.lifecycle != SeedLotLifecycle.EXHAUSTED
        ):
            raise ValueError("Zero quantity is only valid for an exhausted SeedLot")
        return self


class SeedLotCreate(SeedLotWrite):
    pass


class SeedLotUpdate(SeedLotWrite):
    pass


class BotanicalIdentitySummary(BaseModel):
    id: UUID
    display_label: str


class SupplierSummary(BaseModel):
    id: UUID
    name: str


class GeographicPlaceSummary(BaseModel):
    id: UUID
    display_path: str


class LocationSummary(BaseModel):
    id: UUID
    display_path: str


class SeedLotResponse(BaseModel):
    id: UUID
    botanical_identity_id: UUID
    botanical_identity: BotanicalIdentitySummary
    label: str | None
    source_kind: SeedLotSourceKind
    source_detail: str | None
    supplier_id: UUID | None
    supplier: SupplierSummary | None
    material_provenance_place_id: UUID | None
    material_provenance: GeographicPlaceSummary | None
    acquisition_date: PartialDate | None
    harvest_date: PartialDate | None
    quantity: SeedQuantity | None
    expected_viability_until: PartialDate | None
    location_id: UUID | None
    location: LocationSummary | None
    lifecycle: SeedLotLifecycle
    notes: str | None
    created_at: datetime
    updated_at: datetime
