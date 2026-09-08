from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid7

from sqlalchemy import (
    Boolean,
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


def utc_now() -> datetime:
    return datetime.now(UTC)


class SeedLotSourceKind(StrEnum):
    PURCHASED = "purchased"
    PURCHASED_FRUIT = "purchased_fruit"
    SELF_COLLECTED = "self_collected"
    COLLECTION_PRODUCED = "collection_produced"
    GIFT_EXCHANGE = "gift_exchange"
    OTHER = "other"
    UNKNOWN = "unknown"


class PartialDatePrecision(StrEnum):
    YEAR = "year"
    MONTH = "month"
    DAY = "day"


class SeedQuantityKind(StrEnum):
    SEED_COUNT = "seed_count"
    WEIGHT = "weight"


class SeedWeightUnit(StrEnum):
    GRAM = "g"
    MILLIGRAM = "mg"


class SeedLotLifecycle(StrEnum):
    ACTIVE = "active"
    EXHAUSTED = "exhausted"
    DISCARDED = "discarded"
    LOST = "lost"


def _partial_date_constraint(prefix: str) -> CheckConstraint:
    precision = f"{prefix}_precision"
    year = f"{prefix}_year"
    month = f"{prefix}_month"
    day = f"{prefix}_day"
    return CheckConstraint(
        f"({precision} IS NULL AND {year} IS NULL AND {month} IS NULL AND {day} IS NULL) OR ("
        f"{year} BETWEEN 1 AND 9999 AND ("
        f"({precision} = 'year' AND {month} IS NULL AND {day} IS NULL) OR "
        f"({precision} = 'month' AND {month} BETWEEN 1 AND 12 AND {day} IS NULL) OR "
        f"({precision} = 'day' AND {month} BETWEEN 1 AND 12 AND {day} BETWEEN 1 AND 31 "
        f"AND make_date({year}, {month}, {day}) IS NOT NULL))) IS TRUE",
        name=f"ck_seed_lots_{prefix}",
    )


class SeedLot(Base):
    __tablename__ = "seed_lots"
    __table_args__ = (
        CheckConstraint(
            "label IS NULL OR (char_length(label) BETWEEN 1 AND 255 "
            "AND label = regexp_replace(btrim(label), '[[:space:]]+', ' ', 'g') "
            "AND label !~ '[[:cntrl:]]')",
            name="ck_seed_lots_label",
        ),
        CheckConstraint(
            "source_kind IN ('purchased', 'purchased_fruit', 'self_collected', "
            "'collection_produced', 'gift_exchange', 'other', 'unknown')",
            name="ck_seed_lots_source_kind",
        ),
        CheckConstraint(
            "(source_kind = 'other' AND (source_detail IS NULL OR "
            "(char_length(source_detail) BETWEEN 1 AND 255 "
            "AND source_detail = regexp_replace(btrim(source_detail), '[[:space:]]+', ' ', 'g') "
            "AND source_detail !~ '[[:cntrl:]]'))) OR "
            "(source_kind <> 'other' AND source_detail IS NULL)",
            name="ck_seed_lots_source_detail",
        ),
        CheckConstraint(
            "NOT (producer_plant_id IS NOT NULL AND producer_plant_group_id IS NOT NULL)",
            name="ck_seed_lots_producer_exclusive",
        ),
        CheckConstraint(
            "source_kind = 'collection_produced' OR "
            "(producer_plant_id IS NULL AND producer_plant_group_id IS NULL)",
            name="ck_seed_lots_producer_source_kind",
        ),
        _partial_date_constraint("acquisition_date"),
        _partial_date_constraint("harvest_date"),
        _partial_date_constraint("expected_viability_until"),
        CheckConstraint(
            "((quantity_kind IS NULL AND quantity_value IS NULL AND quantity_unit IS NULL "
            "AND quantity_is_approximate IS NULL) OR "
            "(quantity_kind = 'seed_count' AND quantity_value = trunc(quantity_value) "
            "AND quantity_unit IS NULL AND quantity_is_approximate IS NOT NULL AND "
            "(quantity_value > 0 OR (quantity_value = 0 AND lifecycle = 'exhausted' "
            "AND quantity_is_approximate = false))) OR "
            "(quantity_kind = 'weight' AND quantity_unit IN ('g', 'mg') "
            "AND quantity_is_approximate IS NOT NULL AND "
            "(quantity_value > 0 OR (quantity_value = 0 AND lifecycle = 'exhausted' "
            "AND quantity_is_approximate = false)))) IS TRUE",
            name="ck_seed_lots_quantity",
        ),
        CheckConstraint(
            "lifecycle IN ('active', 'exhausted', 'discarded', 'lost')",
            name="ck_seed_lots_lifecycle",
        ),
        CheckConstraint(
            "notes IS NULL OR (char_length(notes) BETWEEN 1 AND 20000 "
            "AND notes = btrim(notes) "
            "AND regexp_replace(notes, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
            name="ck_seed_lots_notes",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    botanical_identity_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("botanical_identities.id", ondelete="RESTRICT"), index=True
    )
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_kind: Mapped[str] = mapped_column(String(32), default=SeedLotSourceKind.UNKNOWN.value)
    source_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    producer_plant_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("plants.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    producer_plant_group_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("plant_groups.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    supplier_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    material_provenance_place_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("geographic_places.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    provenance_site_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("provenance_sites.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    acquisition_date_precision: Mapped[str | None] = mapped_column(String(8), nullable=True)
    acquisition_date_year: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    acquisition_date_month: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    acquisition_date_day: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    harvest_date_precision: Mapped[str | None] = mapped_column(String(8), nullable=True)
    harvest_date_year: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    harvest_date_month: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    harvest_date_day: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    quantity_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
    quantity_value: Mapped[Decimal | None] = mapped_column(Numeric(), nullable=True)
    quantity_unit: Mapped[str | None] = mapped_column(String(8), nullable=True)
    quantity_is_approximate: Mapped[bool | None] = mapped_column(Boolean(), nullable=True)
    expected_viability_until_precision: Mapped[str | None] = mapped_column(String(8), nullable=True)
    expected_viability_until_year: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    expected_viability_until_month: Mapped[int | None] = mapped_column(
        SmallInteger(), nullable=True
    )
    expected_viability_until_day: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    location_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("locations.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    lifecycle: Mapped[str] = mapped_column(String(16), default=SeedLotLifecycle.ACTIVE.value)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


Index("ix_seed_lots_lifecycle", SeedLot.lifecycle)
