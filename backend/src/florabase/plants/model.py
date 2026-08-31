from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid7

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from florabase.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class DirectOriginKind(StrEnum):
    PURCHASED = "purchased"
    GIFT_EXCHANGE = "gift_exchange"
    COLLECTION_PRODUCED = "collection_produced"
    OTHER = "other"
    UNKNOWN = "unknown"


class PlantLifecycle(StrEnum):
    ACTIVE = "active"
    DEAD = "dead"
    LOST = "lost"
    DISCARDED = "discarded"


class PlantGroupLifecycle(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    DEAD = "dead"
    LOST = "lost"
    DISCARDED = "discarded"


def _common_constraints(table: str, lifecycles: str) -> tuple[CheckConstraint, ...]:
    return (
        CheckConstraint(
            "label IS NULL OR (char_length(label) BETWEEN 1 AND 255 "
            "AND label = regexp_replace(btrim(label), '[[:space:]]+', ' ', 'g') "
            "AND label !~ '[[:cntrl:]]')",
            name=f"ck_{table}_label",
        ),
        CheckConstraint(
            "((originating_sowing_id IS NOT NULL AND direct_origin_kind IS NULL "
            "AND direct_origin_detail IS NULL AND supplier_id IS NULL "
            "AND material_provenance_place_id IS NULL) OR "
            "(originating_sowing_id IS NULL AND direct_origin_kind IN "
            "('purchased', 'gift_exchange', 'collection_produced', 'other', 'unknown'))) IS TRUE",
            name=f"ck_{table}_origin",
        ),
        CheckConstraint(
            "(direct_origin_kind = 'other' AND (direct_origin_detail IS NULL OR "
            "(char_length(direct_origin_detail) BETWEEN 1 AND 255 "
            "AND direct_origin_detail = regexp_replace(btrim(direct_origin_detail), "
            "'[[:space:]]+', ' ', 'g') AND direct_origin_detail !~ '[[:cntrl:]'))) "
            "OR (direct_origin_kind IS DISTINCT FROM 'other' AND direct_origin_detail IS NULL)",
            name=f"ck_{table}_direct_origin_detail",
        ),
        CheckConstraint(
            "(collection_entry_date_precision IS NULL AND collection_entry_date_year IS NULL "
            "AND collection_entry_date_month IS NULL AND collection_entry_date_day IS NULL) OR ("
            "collection_entry_date_year BETWEEN 1 AND 9999 AND ("
            "(collection_entry_date_precision = 'year' "
            "AND collection_entry_date_month IS NULL AND collection_entry_date_day IS NULL) OR "
            "(collection_entry_date_precision = 'month' "
            "AND collection_entry_date_month BETWEEN 1 AND 12 "
            "AND collection_entry_date_day IS NULL) OR "
            "(collection_entry_date_precision = 'day' "
            "AND collection_entry_date_month BETWEEN 1 AND 12 "
            "AND collection_entry_date_day BETWEEN 1 AND 31 "
            "AND make_date(collection_entry_date_year, collection_entry_date_month, "
            "collection_entry_date_day) IS NOT NULL))) IS TRUE",
            name=f"ck_{table}_collection_entry_date",
        ),
        CheckConstraint(f"lifecycle IN ({lifecycles})", name=f"ck_{table}_lifecycle"),
        CheckConstraint(
            "notes IS NULL OR (char_length(notes) BETWEEN 1 AND 20000 "
            "AND notes = btrim(notes) "
            "AND regexp_replace(notes, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
            name=f"ck_{table}_notes",
        ),
    )


class Plant(Base):
    __tablename__ = "plants"
    __table_args__ = _common_constraints("plants", "'active', 'dead', 'lost', 'discarded'")

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    botanical_identity_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("botanical_identities.id", ondelete="RESTRICT"), index=True
    )
    originating_sowing_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("sowings.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    direct_origin_kind: Mapped[str | None] = mapped_column(
        String(32), nullable=True, default=DirectOriginKind.UNKNOWN.value
    )
    direct_origin_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supplier_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    material_provenance_place_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("geographic_places.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    collection_entry_date_precision: Mapped[str | None] = mapped_column(String(8), nullable=True)
    collection_entry_date_year: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    collection_entry_date_month: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    collection_entry_date_day: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    location_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("locations.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    lifecycle: Mapped[str] = mapped_column(String(16), default=PlantLifecycle.ACTIVE.value)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class PlantGroup(Base):
    __tablename__ = "plant_groups"
    __table_args__ = (
        *_common_constraints("plant_groups", "'active', 'completed', 'dead', 'lost', 'discarded'"),
        CheckConstraint(
            "((quantity_value IS NULL AND quantity_is_approximate IS NULL) OR "
            "(quantity_value > 0 AND quantity_is_approximate IS NOT NULL) OR "
            "(quantity_value = 0 AND quantity_is_approximate = false "
            "AND lifecycle IN ('completed', 'dead', 'discarded'))) IS TRUE",
            name="ck_plant_groups_quantity",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    botanical_identity_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("botanical_identities.id", ondelete="RESTRICT"), index=True
    )
    originating_sowing_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("sowings.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    direct_origin_kind: Mapped[str | None] = mapped_column(
        String(32), nullable=True, default=DirectOriginKind.UNKNOWN.value
    )
    direct_origin_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supplier_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    material_provenance_place_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("geographic_places.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    collection_entry_date_precision: Mapped[str | None] = mapped_column(String(8), nullable=True)
    collection_entry_date_year: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    collection_entry_date_month: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    collection_entry_date_day: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    quantity_value: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    quantity_is_approximate: Mapped[bool | None] = mapped_column(Boolean(), nullable=True)
    location_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("locations.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    lifecycle: Mapped[str] = mapped_column(String(16), default=PlantGroupLifecycle.ACTIVE.value)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


Index("ix_plants_lifecycle", Plant.lifecycle)
Index("ix_plant_groups_lifecycle", PlantGroup.lifecycle)
