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
    Integer,
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


class SowingLifecycle(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


def _single_line_constraint(column: str, maximum: int) -> CheckConstraint:
    return CheckConstraint(
        f"{column} IS NULL OR (char_length({column}) BETWEEN 1 AND {maximum} "
        f"AND {column} = regexp_replace(btrim({column}), '[[:space:]]+', ' ', 'g') "
        f"AND {column} !~ '[[:cntrl:]]')",
        name=f"ck_sowings_{column}",
    )


class Sowing(Base):
    __tablename__ = "sowings"
    __table_args__ = (
        _single_line_constraint("label", 255),
        CheckConstraint(
            "(sowing_date_precision IS NULL AND sowing_date_year IS NULL "
            "AND sowing_date_month IS NULL AND sowing_date_day IS NULL) OR ("
            "sowing_date_year BETWEEN 1 AND 9999 AND ("
            "(sowing_date_precision = 'year' AND sowing_date_month IS NULL "
            "AND sowing_date_day IS NULL) OR "
            "(sowing_date_precision = 'month' AND sowing_date_month BETWEEN 1 AND 12 "
            "AND sowing_date_day IS NULL) OR "
            "(sowing_date_precision = 'day' AND sowing_date_month BETWEEN 1 AND 12 "
            "AND sowing_date_day BETWEEN 1 AND 31 AND make_date(sowing_date_year, "
            "sowing_date_month, sowing_date_day) IS NOT NULL))) IS TRUE",
            name="ck_sowings_sowing_date",
        ),
        CheckConstraint(
            "((quantity_kind IS NULL AND quantity_value IS NULL AND quantity_unit IS NULL "
            "AND quantity_is_approximate IS NULL) OR "
            "(quantity_kind = 'seed_count' AND quantity_value > 0 "
            "AND quantity_value = trunc(quantity_value) AND quantity_unit IS NULL "
            "AND quantity_is_approximate IS NOT NULL) OR "
            "(quantity_kind = 'weight' AND quantity_value > 0 "
            "AND quantity_unit IN ('g', 'mg') AND quantity_is_approximate IS NOT NULL)) IS TRUE",
            name="ck_sowings_quantity",
        ),
        CheckConstraint(
            "germinated_count IS NULL OR germinated_count >= 0",
            name="ck_sowings_germinated_count",
        ),
        CheckConstraint(
            "NOT (quantity_kind = 'seed_count' AND quantity_is_approximate = false "
            "AND germinated_count IS NOT NULL) OR germinated_count <= quantity_value",
            name="ck_sowings_germinated_within_exact_count",
        ),
        _single_line_constraint("substrate", 1000),
        _single_line_constraint("method_container", 1000),
        _single_line_constraint("pretreatment", 1000),
        CheckConstraint(
            "temperature_min_c IS NULL OR temperature_max_c IS NULL "
            "OR temperature_min_c <= temperature_max_c",
            name="ck_sowings_temperature_order",
        ),
        _single_line_constraint("environment", 1000),
        CheckConstraint(
            "lifecycle IN ('active', 'completed', 'failed', 'abandoned')",
            name="ck_sowings_lifecycle",
        ),
        CheckConstraint(
            "notes IS NULL OR (char_length(notes) BETWEEN 1 AND 20000 "
            "AND notes = btrim(notes) "
            "AND regexp_replace(notes, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
            name="ck_sowings_notes",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    seed_lot_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("seed_lots.id", ondelete="RESTRICT"), index=True
    )
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sowing_date_precision: Mapped[str | None] = mapped_column(String(8), nullable=True)
    sowing_date_year: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    sowing_date_month: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    sowing_date_day: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    quantity_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
    quantity_value: Mapped[Decimal | None] = mapped_column(Numeric(), nullable=True)
    quantity_unit: Mapped[str | None] = mapped_column(String(8), nullable=True)
    quantity_is_approximate: Mapped[bool | None] = mapped_column(Boolean(), nullable=True)
    germinated_count: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    location_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("locations.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    substrate: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    method_container: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    pretreatment: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    temperature_min_c: Mapped[Decimal | None] = mapped_column(Numeric(), nullable=True)
    temperature_max_c: Mapped[Decimal | None] = mapped_column(Numeric(), nullable=True)
    environment: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    lifecycle: Mapped[str] = mapped_column(String(16), default=SowingLifecycle.ACTIVE.value)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


Index("ix_sowings_lifecycle", Sowing.lifecycle)
