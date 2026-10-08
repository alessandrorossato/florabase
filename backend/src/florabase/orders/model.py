from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid7

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from florabase.db.base import Base
from florabase.seed_lots.model import _partial_date_constraint, utc_now


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            str(_partial_date_constraint("ordered_on").sqltext), name="ck_orders_ordered_on"
        ),
        CheckConstraint(
            "order_reference IS NULL OR (char_length(order_reference) BETWEEN 1 AND 255 "
            "AND order_reference = btrim(order_reference) AND order_reference !~ '[[:cntrl:]]')",
            name="ck_orders_reference",
        ),
        CheckConstraint(
            "(total_price IS NULL AND currency IS NULL) OR "
            "(total_price IS NOT NULL AND total_price >= 0 AND total_price < 'Infinity'::numeric "
            "AND currency IS NOT NULL AND currency ~ '^[A-Z]{3}$')",
            name="ck_orders_price_currency",
        ),
        CheckConstraint(
            "notes IS NULL OR (char_length(notes) BETWEEN 1 AND 20000 AND notes = btrim(notes) "
            "AND regexp_replace(notes, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
            name="ck_orders_notes",
        ),
        Index("ix_orders_date", "ordered_on_year", "ordered_on_month", "ordered_on_day", "id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    supplier_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"), index=True
    )
    ordered_on_precision: Mapped[str | None] = mapped_column(String(8))
    ordered_on_year: Mapped[int | None] = mapped_column(SmallInteger())
    ordered_on_month: Mapped[int | None] = mapped_column(SmallInteger())
    ordered_on_day: Mapped[int | None] = mapped_column(SmallInteger())
    order_reference: Mapped[str | None] = mapped_column(String(255))
    total_price: Mapped[Decimal | None] = mapped_column(Numeric())
    currency: Mapped[str | None] = mapped_column(String(3))
    notes: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
