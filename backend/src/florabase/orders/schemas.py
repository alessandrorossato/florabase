import re
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

from florabase.seed_lots.schemas import (
    PartialDate,
    SupplierSummary,
    _contains_control,
    _notes,
)
from florabase.suppliers.schemas import SupplierSeedLotLink

Money = Annotated[
    Decimal,
    PlainSerializer(lambda value: format(value, "f"), return_type=str, when_used="json"),
    WithJsonSchema(
        {
            "type": "string",
            "pattern": r"^[0-9]{1,24}(\.[0-9]{1,24})?$",
            "description": "Exact transaction total supplied and returned as decimal text.",
        }
    ),
]


class OrderWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplier_id: UUID | None = None
    ordered_on: PartialDate | None = None
    order_reference: str | None = Field(default=None, max_length=255)
    total_price: Money | None = None
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    notes: str | None = Field(default=None, max_length=20_000)

    @field_validator("order_reference", mode="before")
    @classmethod
    def reference(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        value = value.strip()
        if _contains_control(value):
            raise ValueError("Order reference must not contain control characters")
        return value or None

    @field_validator("notes", mode="before")
    @classmethod
    def notes_text(cls, value: object) -> object:
        return _notes(value) if isinstance(value, str) else value

    @field_validator("total_price", mode="before")
    @classmethod
    def exact_price(cls, value: object) -> object:
        # Browser/API money crosses the boundary as text, never a binary float.
        if value is None or isinstance(value, Decimal):
            return value
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,24}(\.[0-9]{1,24})?", value):
            raise ValueError(
                "Total price must be an exact non-negative decimal string "
                "(up to 24 digits per part)"
            )
        return value

    @model_validator(mode="after")
    def price_currency(self) -> Self:
        if (self.total_price is None) != (self.currency is None):
            raise ValueError("Total price and currency must be supplied or cleared together")
        if self.total_price is not None and (
            not self.total_price.is_finite() or self.total_price < 0
        ):
            raise ValueError("Total price must be finite and non-negative")
        return self


class OrderCreate(OrderWrite):
    pass


class OrderUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplier_id: UUID | None = None
    ordered_on: PartialDate | None = None
    order_reference: str | None = None
    total_price: Money | None = None
    currency: str | None = None
    notes: str | None = None

    # Complete merged state is validated against OrderWrite by the service.
    @field_validator("total_price", mode="before")
    @classmethod
    def exact_price(cls, value: object) -> object:
        return OrderWrite.exact_price(value)


class OrderResponse(OrderWrite):
    id: UUID
    supplier: SupplierSummary | None
    seed_lot_count: int
    created_at: datetime
    updated_at: datetime


class OrderPage(BaseModel):
    items: list[OrderResponse]
    total: int
    offset: int
    limit: int


class OrderDetailResponse(OrderResponse):
    seed_lots: list[SupplierSeedLotLink]
    seed_lots_total: int
    seed_lots_offset: int
    seed_lots_limit: int
