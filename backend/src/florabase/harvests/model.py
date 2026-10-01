"""A historical collection occurrence; never harvested-material inventory."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid7

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from florabase.db.base import Base
from florabase.events.model import utc_now


class MaterialKind(StrEnum):
    FRUIT = "fruit"
    FLOWER = "flower"
    LEAF = "leaf"
    ROOT = "root"
    SEED = "seed"
    STEM_OR_SHOOT = "stem_or_shoot"
    WHOLE_PLANT = "whole_plant"
    OTHER = "other"


class Harvest(Base):
    __tablename__ = "harvests"
    __table_args__ = (
        CheckConstraint("num_nonnulls(plant_id, plant_group_id) = 1", name="ck_harvests_source"),
        CheckConstraint(
            "label IS NULL OR (char_length(label) BETWEEN 1 AND 255 AND label = btrim(label) "
            "AND label !~ '[[:cntrl:]]')",
            name="ck_harvests_label",
        ),
        CheckConstraint(
            "notes IS NULL OR (char_length(notes) BETWEEN 1 AND 20000 AND notes = btrim(notes) "
            "AND regexp_replace(notes, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
            name="ck_harvests_notes",
        ),
        CheckConstraint(
            "(occurred_on_precision IS NULL AND occurred_on_year IS NULL "
            "AND occurred_on_month IS NULL AND occurred_on_day IS NULL) OR ("
            "occurred_on_year BETWEEN 1 AND 9999 AND ("
            "(occurred_on_precision = 'year' AND occurred_on_month IS NULL AND "
            "occurred_on_day IS NULL) OR  "
            "(occurred_on_precision = 'month' AND occurred_on_month BETWEEN 1 AND 12 AND "
            "occurred_on_day IS NULL) OR  "
            "(occurred_on_precision = 'day' AND occurred_on_month BETWEEN 1 AND 12 AND "
            "occurred_on_day BETWEEN 1 AND 31  "
            "AND make_date(occurred_on_year, occurred_on_month, occurred_on_day) IS NOT "
            "NULL))) IS TRUE",
            name="ck_harvests_occurred_on",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    plant_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("plants.id", ondelete="RESTRICT"), index=True
    )
    plant_group_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("plant_groups.id", ondelete="RESTRICT"), index=True
    )
    event_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("events.id", ondelete="RESTRICT"), unique=True
    )
    label: Mapped[str | None] = mapped_column(String(255))
    occurred_on_precision: Mapped[str | None] = mapped_column(String(8))
    occurred_on_year: Mapped[int | None] = mapped_column(SmallInteger())
    occurred_on_month: Mapped[int | None] = mapped_column(SmallInteger())
    occurred_on_day: Mapped[int | None] = mapped_column(SmallInteger())
    notes: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class HarvestItem(Base):
    __tablename__ = "harvest_items"
    __table_args__ = (
        UniqueConstraint("harvest_id", "display_order", name="uq_harvest_items_order"),
        CheckConstraint("display_order >= 0", name="ck_harvest_items_order"),
        CheckConstraint(
            "material_kind IN ('fruit', 'flower', 'leaf', 'root', 'seed', "
            "'stem_or_shoot', 'whole_plant', 'other')",
            name="ck_harvest_items_material",
        ),
        CheckConstraint(
            "description IS NULL OR (char_length(description) BETWEEN 1 AND 2000 AND "
            "description = btrim(description)  "
            "AND regexp_replace(description, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
            name="ck_harvest_items_description",
        ),
        CheckConstraint(
            "((quantity_kind IS NULL AND quantity_value IS NULL AND quantity_unit IS "
            "NULL AND quantity_is_approximate IS NULL) OR  "
            "(quantity_value > 0 AND quantity_value < 'Infinity'::numeric AND "
            "quantity_is_approximate IS NOT NULL AND ("
            "(quantity_kind = 'item_count' AND quantity_value = trunc(quantity_value) "
            "AND quantity_unit IS NULL) OR  "
            "(quantity_kind = 'weight' AND quantity_unit IN ('mg', 'g', 'kg'))))) IS TRUE",
            name="ck_harvest_items_quantity",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    harvest_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("harvests.id", ondelete="CASCADE"), index=True
    )
    display_order: Mapped[int] = mapped_column(Integer())
    material_kind: Mapped[str] = mapped_column(String(16))
    description: Mapped[str | None] = mapped_column(Text())
    quantity_kind: Mapped[str | None] = mapped_column(String(16))
    quantity_value: Mapped[Decimal | None] = mapped_column(Numeric())
    quantity_unit: Mapped[str | None] = mapped_column(String(8))
    quantity_is_approximate: Mapped[bool | None] = mapped_column(Boolean())
