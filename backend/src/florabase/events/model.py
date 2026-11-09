from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid7

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
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


class EventKind(StrEnum):
    OBSERVATION = "observation"
    MOVEMENT = "movement"
    REPOTTING = "repotting"
    FLOWERING = "flowering"
    FRUITING = "fruiting"
    PRUNING = "pruning"
    TREATMENT = "treatment"
    HARVEST = "harvest"
    EXTRACTION = "extraction"
    REINTEGRATION = "reintegration"
    TRANSFER = "transfer"
    DEATH = "death"
    LOSS = "loss"
    DISCARDED = "discarded"
    MEASUREMENT = "measurement"
    OTHER = "other"


class MeasurementQuantity(StrEnum):
    HEIGHT = "height"


class LengthUnit(StrEnum):
    MM = "mm"
    CM = "cm"
    M = "m"


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(plant_id, plant_group_id) = 1",
            name="ck_events_exactly_one_target",
        ),
        CheckConstraint(
            "kind IN ('observation', 'movement', 'repotting', 'flowering', 'fruiting', "
            "'pruning', 'treatment', 'harvest', 'extraction', 'reintegration', 'transfer', "
            "'death', 'loss', "
            "'discarded', 'other', 'measurement')",
            name="ck_events_kind",
        ),
        CheckConstraint(
            "(occurred_on_precision IS NULL AND occurred_on_year IS NULL "
            "AND occurred_on_month IS NULL AND occurred_on_day IS NULL) OR ("
            "occurred_on_year BETWEEN 1 AND 9999 AND ("
            "(occurred_on_precision = 'year' AND occurred_on_month IS NULL "
            "AND occurred_on_day IS NULL) OR "
            "(occurred_on_precision = 'month' AND occurred_on_month BETWEEN 1 AND 12 "
            "AND occurred_on_day IS NULL) OR "
            "(occurred_on_precision = 'day' AND occurred_on_month BETWEEN 1 AND 12 "
            "AND occurred_on_day BETWEEN 1 AND 31 AND "
            "make_date(occurred_on_year, occurred_on_month, occurred_on_day) IS NOT NULL))) "
            "IS TRUE",
            name="ck_events_occurred_on",
        ),
        CheckConstraint(
            "((kind = 'movement' AND destination_location_id IS NOT NULL) OR "
            "(kind <> 'movement' AND destination_location_id IS NULL)) IS TRUE",
            name="ck_events_movement_destination",
        ),
        CheckConstraint(
            "recipient IS NULL OR (kind = 'transfer' AND char_length(recipient) BETWEEN 1 AND 255 "
            "AND recipient = regexp_replace(btrim(recipient), '[[:space:]]+', ' ', 'g') "
            "AND recipient !~ '[[:cntrl:]]')",
            name="ck_events_transfer_recipient",
        ),
        CheckConstraint(
            "((kind IN ('extraction', 'reintegration') AND plant_group_id IS NOT NULL AND "
            "resulting_plant_id IS NOT NULL) OR "
            "(kind NOT IN ('extraction', 'reintegration') AND resulting_plant_id IS NULL)) IS TRUE",
            name="ck_events_extraction_result",
        ),
        CheckConstraint(
            "((kind = 'reintegration' AND reversed_operation_receipt_id IS NOT NULL) OR "
            "(kind <> 'reintegration' AND reversed_operation_receipt_id IS NULL)) IS TRUE",
            name="ck_events_reintegration_receipt",
        ),
        CheckConstraint(
            "((kind = 'measurement' AND plant_id IS NOT NULL AND occurred_on_precision IS NOT NULL "
            "AND measurement_quantity = 'height' AND measurement_unit IN ('mm', 'cm', 'm') "
            "AND measurement_value > 0 AND measurement_value * CASE measurement_unit "
            "WHEN 'mm' THEN 1 WHEN 'cm' THEN 10 ELSE 1000 END <= 200000 "
            "AND scale(measurement_value) <= 3 AND measurement_is_approximate IS NOT NULL) OR "
            "(kind <> 'measurement' AND measurement_quantity IS NULL AND measurement_value IS NULL "
            "AND measurement_unit IS NULL AND measurement_is_approximate IS NULL)) IS TRUE",
            name="ck_events_measurement",
        ),
        ForeignKeyConstraint(
            ["resulting_plant_id", "plant_group_id"],
            ["plants.id", "plants.originating_plant_group_id"],
            name="fk_events_resulting_plant_source_group",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "notes IS NULL OR (char_length(notes) BETWEEN 1 AND 20000 AND notes = btrim(notes) "
            "AND regexp_replace(notes, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
            name="ck_events_notes",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    plant_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("plants.id", ondelete="RESTRICT"), nullable=True
    )
    plant_group_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("plant_groups.id", ondelete="RESTRICT"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(16))
    occurred_on_precision: Mapped[str | None] = mapped_column(String(8), nullable=True)
    occurred_on_year: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    occurred_on_month: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    occurred_on_day: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    destination_location_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("locations.id", ondelete="RESTRICT"), nullable=True
    )
    recipient: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resulting_plant_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("plants.id", ondelete="RESTRICT"), nullable=True
    )
    reversed_operation_receipt_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("operation_receipts.id", ondelete="RESTRICT"),
        nullable=True,
        unique=True,
    )
    # Unscaled numeric keeps the recorded resolution: 12.50 stays 12.50.
    measurement_quantity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    measurement_value: Mapped[Decimal | None] = mapped_column(Numeric(), nullable=True)
    measurement_unit: Mapped[str | None] = mapped_column(String(8), nullable=True)
    measurement_is_approximate: Mapped[bool | None] = mapped_column(Boolean(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


Index(
    "ix_events_plant_timeline",
    Event.plant_id,
    Event.occurred_on_year,
    Event.occurred_on_month,
    Event.occurred_on_day,
    Event.created_at,
    Event.id,
)
Index(
    "ix_events_plant_group_timeline",
    Event.plant_group_id,
    Event.occurred_on_year,
    Event.occurred_on_month,
    Event.occurred_on_day,
    Event.created_at,
    Event.id,
)
Index("ix_events_destination_location_id", Event.destination_location_id)
Index("ix_events_resulting_plant_id", Event.resulting_plant_id)
