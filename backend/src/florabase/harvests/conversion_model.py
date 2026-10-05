"""Explicit seed conversion facts; source snapshots live in its immutable disposition."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid7

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from florabase.db.base import Base
from florabase.events.model import utc_now


class HarvestSeedLotConversion(Base):
    __tablename__ = "harvest_seed_lot_conversions"
    __table_args__ = (
        CheckConstraint(
            (
                "status IN ('applied', 'reversed') AND ((status = 'applied' AND reversed_at "
                "IS NULL) OR (status = 'reversed' AND reversed_at IS NOT NULL AND reversed_at"
                " >= created_at))"
            ),
            name="ck_harvest_conversion_status",
        ),
        CheckConstraint("source_correction_version >= 0", name="ck_harvest_conversion_version"),
        CheckConstraint(
            (
                "((quantity_kind IS NULL AND quantity_value IS NULL AND quantity_unit IS NULL"
                " AND quantity_is_approximate IS NULL) OR (quantity_value > 0 AND "
                "quantity_value < 'Infinity'::numeric AND quantity_is_approximate IS NOT NULL"
                " AND ((quantity_kind = 'seed_count' AND quantity_value = "
                "trunc(quantity_value) AND quantity_unit IS NULL) OR (quantity_kind = "
                "'weight' AND quantity_unit IN ('mg', 'g'))))) IS TRUE"
            ),
            name="ck_harvest_conversion_quantity",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    inventory_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("harvest_material_inventory.id", ondelete="RESTRICT"), index=True
    )
    disposition_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("harvest_material_dispositions.id", ondelete="RESTRICT"), unique=True
    )
    seed_lot_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("seed_lots.id", ondelete="RESTRICT"), unique=True
    )
    status: Mapped[str] = mapped_column(String(8), default="applied")
    source_correction_version: Mapped[int] = mapped_column(Integer())
    quantity_kind: Mapped[str | None] = mapped_column(String(16))
    quantity_value: Mapped[Decimal | None] = mapped_column(Numeric())
    quantity_unit: Mapped[str | None] = mapped_column(String(8))
    quantity_is_approximate: Mapped[bool | None] = mapped_column(Boolean())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
