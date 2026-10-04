"""Optional current stored material and retained, typed disposition facts."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid7

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    SmallInteger,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from florabase.db.base import Base
from florabase.events.model import utc_now


def quantity_check(prefix: str) -> str:
    return f"""(({prefix}_kind IS NULL AND {prefix}_value IS NULL AND
    {prefix}_unit IS NULL AND {prefix}_is_approximate IS NULL) OR
    ({prefix}_value > 0 AND {prefix}_value < 'Infinity'::numeric AND
    {prefix}_is_approximate IS NOT NULL AND
    (({prefix}_kind = 'item_count' AND {prefix}_value = trunc({prefix}_value)
      AND {prefix}_unit IS NULL) OR
     ({prefix}_kind = 'weight' AND {prefix}_unit IN ('mg', 'g', 'kg'))))) IS TRUE"""


def state_check(state: str, quantity: str) -> str:
    return (
        f"{state} IN ('active', 'depleted') AND ({state} <> 'depleted' OR {quantity}_kind IS NULL)"
    )


def disposition_balance_check() -> str:
    return """((mode = 'use_all' AND
        ROW(quantity_kind, quantity_value, quantity_unit, quantity_is_approximate)
        IS NOT DISTINCT FROM
        ROW(before_quantity_kind, before_quantity_value, before_quantity_unit,
            before_quantity_is_approximate)) OR
    (mode = 'partial' AND (
        (before_quantity_kind IS NULL AND after_quantity_kind IS NULL) OR
        (before_quantity_is_approximate IS TRUE AND after_quantity_is_approximate IS TRUE
         AND before_quantity_kind = after_quantity_kind
         AND before_quantity_unit IS NOT DISTINCT FROM after_quantity_unit
         AND (quantity_kind IS NULL OR (quantity_kind = before_quantity_kind
             AND quantity_unit IS NOT DISTINCT FROM before_quantity_unit))) OR
        (before_quantity_is_approximate IS FALSE AND quantity_is_approximate IS FALSE
         AND after_quantity_is_approximate IS FALSE
         AND quantity_kind = before_quantity_kind AND after_quantity_kind = before_quantity_kind
         AND quantity_unit IS NOT DISTINCT FROM before_quantity_unit
         AND after_quantity_unit IS NOT DISTINCT FROM before_quantity_unit
         AND after_quantity_value = before_quantity_value - quantity_value)
    ))) IS TRUE"""


class HarvestMaterialInventory(Base):
    __tablename__ = "harvest_material_inventory"
    __table_args__ = (
        ForeignKeyConstraint(
            ["harvest_item_id", "harvest_id", "material_kind"],
            ["harvest_items.id", "harvest_items.harvest_id", "harvest_items.material_kind"],
            name="fk_harvest_inventory_material_context",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        CheckConstraint(quantity_check("quantity"), name="ck_harvest_inventory_quantity"),
        CheckConstraint(state_check("state", "quantity"), name="ck_harvest_inventory_state"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    harvest_item_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("harvest_items.id", ondelete="RESTRICT"), unique=True
    )
    harvest_id: Mapped[UUID] = mapped_column(Uuid())
    material_kind: Mapped[str] = mapped_column(String(16))
    location_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("locations.id", ondelete="RESTRICT"), index=True
    )
    state: Mapped[str] = mapped_column(String(8))
    quantity_kind: Mapped[str | None] = mapped_column(String(16))
    quantity_value: Mapped[Decimal | None] = mapped_column(Numeric())
    quantity_unit: Mapped[str | None] = mapped_column(String(8))
    quantity_is_approximate: Mapped[bool | None] = mapped_column(Boolean())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class HarvestMaterialDisposition(Base):
    __tablename__ = "harvest_material_dispositions"
    __table_args__ = (
        CheckConstraint(disposition_balance_check(), name="ck_harvest_disposition_balance"),
        CheckConstraint(
            "kind IN ('consumed', 'processed', 'discarded', 'gifted', 'used_for_propagation')",
            name="ck_harvest_disposition_kind",
        ),
        CheckConstraint(
            (
                "mode IN ('partial', 'use_all') AND before_state = 'active' AND "
                "((mode = 'partial' AND after_state = 'active') OR (mode = "
                "'use_all' AND after_state = 'depleted'))"
            ),
            name="ck_harvest_disposition_transition",
        ),
        *(
            CheckConstraint(quantity_check(p), name=f"ck_harvest_disposition_{p}")
            for p in ("quantity", "before_quantity", "after_quantity")
        ),
        CheckConstraint(
            state_check("before_state", "before_quantity"),
            name="ck_harvest_disposition_before_state",
        ),
        CheckConstraint(
            state_check("after_state", "after_quantity"), name="ck_harvest_disposition_after_state"
        ),
        CheckConstraint(
            (
                "((occurred_on_precision IS NULL AND occurred_on_year IS NULL AND "
                "occurred_on_month IS NULL AND occurred_on_day IS NULL) OR\n"
                "        (occurred_on_year BETWEEN 1 AND 9999 AND "
                "((occurred_on_precision = 'year' AND occurred_on_month IS NULL "
                "AND occurred_on_day IS NULL) OR\n"
                "        (occurred_on_precision = 'month' AND occurred_on_month "
                "BETWEEN 1 AND 12 AND occurred_on_day IS NULL) OR\n"
                "        (occurred_on_precision = 'day' AND occurred_on_month "
                "BETWEEN 1 AND 12 AND occurred_on_day BETWEEN 1 AND 31 AND "
                "make_date(occurred_on_year, occurred_on_month, occurred_on_day) "
                "IS NOT NULL)))) IS TRUE"
            ),
            name="ck_harvest_disposition_date",
        ),
        CheckConstraint(
            (
                "notes IS NULL OR (char_length(notes) BETWEEN 1 AND 20000 AND "
                "notes = btrim(notes) AND regexp_replace(notes, E'[\\n\\t]', '', "
                "'g') !~ '[[:cntrl:]]')"
            ),
            name="ck_harvest_disposition_notes",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    inventory_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("harvest_material_inventory.id", ondelete="RESTRICT"), index=True
    )
    kind: Mapped[str] = mapped_column(String(24))
    mode: Mapped[str] = mapped_column(String(8))
    occurred_on_precision: Mapped[str | None] = mapped_column(String(8))
    occurred_on_year: Mapped[int | None] = mapped_column(SmallInteger())
    occurred_on_month: Mapped[int | None] = mapped_column(SmallInteger())
    occurred_on_day: Mapped[int | None] = mapped_column(SmallInteger())
    quantity_kind: Mapped[str | None] = mapped_column(String(16))
    quantity_value: Mapped[Decimal | None] = mapped_column(Numeric())
    quantity_unit: Mapped[str | None] = mapped_column(String(8))
    quantity_is_approximate: Mapped[bool | None] = mapped_column(Boolean())
    before_state: Mapped[str] = mapped_column(String(8))
    before_quantity_kind: Mapped[str | None] = mapped_column(String(16))
    before_quantity_value: Mapped[Decimal | None] = mapped_column(Numeric())
    before_quantity_unit: Mapped[str | None] = mapped_column(String(8))
    before_quantity_is_approximate: Mapped[bool | None] = mapped_column(Boolean())
    after_state: Mapped[str] = mapped_column(String(8))
    after_quantity_kind: Mapped[str | None] = mapped_column(String(16))
    after_quantity_value: Mapped[Decimal | None] = mapped_column(Numeric())
    after_quantity_unit: Mapped[str | None] = mapped_column(String(8))
    after_quantity_is_approximate: Mapped[bool | None] = mapped_column(Boolean())
    notes: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
