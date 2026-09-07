from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from florabase.reversals.model import OperationKind, OperationReceipt


class LifecycleRecord(Protocol):
    id: UUID
    lifecycle: str


class QuantityRecord(LifecycleRecord, Protocol):
    quantity_value: int | None
    quantity_is_approximate: bool | None


class SeedQuantityRecord(LifecycleRecord, Protocol):
    quantity_kind: str | None
    quantity_value: Decimal | None
    quantity_unit: str | None
    quantity_is_approximate: bool | None


@dataclass(frozen=True)
class QuantitySnapshot:
    kind: str | None
    value: Decimal | None
    unit: str | None
    is_approximate: bool | None

    def columns(self, prefix: str) -> dict[str, object]:
        return {
            f"{prefix}_quantity_kind": self.kind,
            f"{prefix}_quantity_value": self.value,
            f"{prefix}_quantity_unit": self.unit,
            f"{prefix}_quantity_is_approximate": self.is_approximate,
        }


def seed_quantity(record: SeedQuantityRecord) -> QuantitySnapshot:
    return QuantitySnapshot(
        kind=record.quantity_kind,
        value=record.quantity_value,
        unit=record.quantity_unit,
        is_approximate=record.quantity_is_approximate,
    )


def group_quantity(record: QuantityRecord) -> QuantitySnapshot:
    value = record.quantity_value
    return QuantitySnapshot(
        kind="count" if value is not None else None,
        value=Decimal(value) if value is not None else None,
        unit=None,
        is_approximate=record.quantity_is_approximate,
    )


def add_receipt(
    database: Session,
    *,
    kind: OperationKind,
    before_lifecycle: str,
    after_lifecycle: str,
    before_quantity: QuantitySnapshot | None = None,
    after_quantity: QuantitySnapshot | None = None,
    seed_lot_id: UUID | None = None,
    sowing_id: UUID | None = None,
    plant_id: UUID | None = None,
    plant_group_id: UUID | None = None,
    event_id: UUID | None = None,
    adjustment_mode: str | None = None,
    propagation_snapshot: dict[str, object] | None = None,
) -> OperationReceipt:
    receipt = OperationReceipt(
        **(propagation_snapshot or {}),
        kind=kind.value,
        seed_lot_id=seed_lot_id,
        sowing_id=sowing_id,
        plant_id=plant_id,
        plant_group_id=plant_group_id,
        event_id=event_id,
        adjustment_mode=adjustment_mode,
        before_lifecycle=before_lifecycle,
        after_lifecycle=after_lifecycle,
        **(before_quantity or QuantitySnapshot(None, None, None, None)).columns("before"),
        **(after_quantity or QuantitySnapshot(None, None, None, None)).columns("after"),
    )
    database.add(receipt)
    database.flush()
    return receipt
