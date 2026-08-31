import unicodedata
from datetime import datetime
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

from florabase.seed_lots.model import SeedLotLifecycle, SeedQuantityKind, SeedWeightUnit
from florabase.seed_lots.schemas import DecimalString, PartialDate
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


class SowingQuantity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: SeedQuantityKind
    value: DecimalString
    unit: SeedWeightUnit | None = None
    is_approximate: bool

    @model_validator(mode="after")
    def validate_quantity(self) -> Self:
        if not self.value.is_finite() or self.value <= 0:
            raise ValueError("Quantity sown must be a finite positive value")
        if self.kind == SeedQuantityKind.SEED_COUNT:
            if self.value != self.value.to_integral_value():
                raise ValueError("Seed count must be a whole number")
            if self.unit is not None:
                raise ValueError("Seed count must not include a unit")
        elif self.unit is None:
            raise ValueError("Weight requires a unit")
        return self


SignedDecimalString = Annotated[
    Decimal,
    PlainSerializer(lambda value: str(value), return_type=str, when_used="json"),
    WithJsonSchema(
        {
            "type": "string",
            "pattern": r"^-?(0|[1-9][0-9]*)(\.[0-9]+)?$",
            "description": "An exact decimal serialized as a JSON string.",
        },
        mode="serialization",
    ),
]


class SowingWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed_lot_id: UUID
    label: str | None = Field(default=None, max_length=255)
    sowing_date: PartialDate | None = None
    quantity: SowingQuantity | None = None
    germinated_count: int | None = Field(default=None, ge=0)
    location_id: UUID | None = None
    substrate: str | None = Field(default=None, max_length=1000)
    method_container: str | None = Field(default=None, max_length=1000)
    pretreatment: str | None = Field(default=None, max_length=1000)
    temperature_min_c: SignedDecimalString | None = None
    temperature_max_c: SignedDecimalString | None = None
    environment: str | None = Field(default=None, max_length=1000)
    lifecycle: SowingLifecycle = SowingLifecycle.ACTIVE
    notes: str | None = Field(default=None, max_length=20_000)

    @field_validator(
        "label", "substrate", "method_container", "pretreatment", "environment", mode="before"
    )
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

    @field_validator("temperature_min_c", "temperature_max_c")
    @classmethod
    def finite_temperature(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not value.is_finite():
            raise ValueError("Temperature must be finite")
        return value

    @model_validator(mode="after")
    def validate_final_state(self) -> Self:
        if (
            self.temperature_min_c is not None
            and self.temperature_max_c is not None
            and self.temperature_min_c > self.temperature_max_c
        ):
            raise ValueError("Minimum temperature must not exceed maximum temperature")
        if (
            self.germinated_count is not None
            and self.quantity is not None
            and self.quantity.kind == SeedQuantityKind.SEED_COUNT
            and not self.quantity.is_approximate
            and Decimal(self.germinated_count) > self.quantity.value
        ):
            raise ValueError("Germinated count must not exceed an exact seed count")
        return self


class SowingCreate(SowingWrite):
    pass


class SowingUpdate(SowingWrite):
    pass


class SowingSeedLotSummary(BaseModel):
    id: UUID
    label: str | None
    lifecycle: SeedLotLifecycle
    botanical_identity_id: UUID
    botanical_identity_display_label: str


class SowingLocationSummary(BaseModel):
    id: UUID
    display_path: str


class SowingResponse(BaseModel):
    id: UUID
    seed_lot_id: UUID
    seed_lot: SowingSeedLotSummary
    label: str | None
    sowing_date: PartialDate | None
    quantity: SowingQuantity | None
    germinated_count: int | None
    location_id: UUID | None
    location: SowingLocationSummary | None
    substrate: str | None
    method_container: str | None
    pretreatment: str | None
    temperature_min_c: SignedDecimalString | None
    temperature_max_c: SignedDecimalString | None
    environment: str | None
    lifecycle: SowingLifecycle
    notes: str | None
    created_at: datetime
    updated_at: datetime
