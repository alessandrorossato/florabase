"""Transient purchase-context review; no reconciliation records are persisted."""

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, model_validator

from florabase.orders.schemas import OrderResponse
from florabase.seed_lots.model import SeedLotSourceKind
from florabase.seed_lots.schemas import PartialDate, SeedLotCreate, SeedLotResponse, SupplierSummary


class AcquisitionContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_kind: SeedLotSourceKind = SeedLotSourceKind.UNKNOWN
    supplier_id: UUID | None = None
    acquisition_date: PartialDate | None = None
    order_id: UUID | None = None


class PurchasePreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seed_lot_id: UUID | None = None
    context: AcquisitionContext | None = None
    expected_seed_lot_updated_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def draft_version(self) -> Self:
        if self.seed_lot_id and self.context and not self.expected_seed_lot_updated_at:
            raise ValueError("An existing SeedLot draft requires its expected updated_at")
        return self


class PurchaseApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seed_lot_id: UUID | None = None
    context: AcquisitionContext
    expected_seed_lot_updated_at: AwareDatetime | None = None
    expected_order_updated_at: AwareDatetime
    use_order_supplier: bool = False
    use_order_date: bool = False

    @model_validator(mode="after")
    def lot_version(self) -> Self:
        if bool(self.seed_lot_id) != bool(self.expected_seed_lot_updated_at):
            raise ValueError("An existing SeedLot requires its expected updated_at")
        return self


class PurchasePreview(BaseModel):
    order: OrderResponse
    seed_lot_id: UUID | None
    seed_lot_updated_at: datetime | None
    current: AcquisitionContext
    stored: AcquisitionContext | None = None
    stored_supplier: SupplierSummary | None = None
    current_supplier: SupplierSummary | None
    proposed_source: SeedLotSourceKind
    supplier_action: Literal["keep", "fill", "replace"]
    date_action: Literal["keep", "copy", "replace"]
    can_apply: bool
    conflict: str | None


class PurchaseResolution(BaseModel):
    order: OrderResponse
    context: AcquisitionContext
    confirmation: PurchaseApplyRequest
    seed_lot: SeedLotResponse | None


class PurchaseSeedLotCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seed_lot: SeedLotCreate
    confirmation: PurchaseApplyRequest


class PurchaseSeedChoice(BaseModel):
    id: UUID
    label: str
    source_kind: SeedLotSourceKind
    supplier: SupplierSummary | None
    order_id: UUID | None


class PurchaseSeedPage(BaseModel):
    items: list[PurchaseSeedChoice]
    total: int
    offset: int
    limit: int
