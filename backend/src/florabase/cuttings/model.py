from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
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

MaterialType = Literal["stem_cutting", "leaf_cutting", "root_cutting"]
SourceKind = Literal[
    "collection_produced", "purchased", "gift_exchange", "self_collected", "other", "unknown"
]
LotLifecycle = Literal["active", "exhausted", "discarded", "lost", "reversed"]
AttemptLifecycle = Literal["active", "completed", "failed", "abandoned", "reversed"]
RootingStage = Literal["callus", "root_initials", "rooted", "loss", "inspection"]


def utc_now() -> datetime:
    return datetime.now(UTC)


def _date(prefix: str) -> str:
    precision, year, month, day = (
        f"{prefix}_{part}" for part in ("precision", "year", "month", "day")
    )
    return (
        f"(num_nonnulls({precision}, {year}, {month}, {day}) = 0 OR "
        f"({year} BETWEEN 1 AND 9999 AND ("
        f"({precision} = 'year' AND {month} IS NULL AND {day} IS NULL) OR "
        f"({precision} = 'month' AND {month} BETWEEN 1 AND 12 AND {day} IS NULL) OR "
        f"({precision} = 'day' AND {month} BETWEEN 1 AND 12 AND {day} BETWEEN 1 AND 31 "
        f"AND make_date({year}, {month}, {day}) IS NOT NULL)))) IS TRUE"
    )


def _quantity(prefix: str, *, lot_remainder: bool = False) -> str:
    value, approximate = f"{prefix}_value", f"{prefix}_is_approximate"
    zero = (
        f" OR ({value} = 0 AND NOT {approximate} AND lifecycle = 'exhausted')"
        if lot_remainder
        else ""
    )
    return (
        f"(({value} IS NULL AND {approximate} IS NULL) OR "
        f"({value} IS NOT NULL AND {approximate} IS NOT NULL AND ({value} > 0{zero})))"
    )


def _line(column: str, maximum: int) -> str:
    return (
        f"{column} IS NULL OR (char_length({column}) BETWEEN 1 AND {maximum} "
        f"AND {column} = regexp_replace(btrim({column}), '[[:space:]]+', ' ', 'g') "
        f"AND {column} !~ '[[:cntrl:]]')"
    )


_NOTES = (
    "notes IS NULL OR (char_length(notes) BETWEEN 1 AND 20000 AND notes = btrim(notes) "
    "AND regexp_replace(notes, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')"
)


class CuttingRecord:
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    notes: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class VegetativeLot(CuttingRecord, Base):
    __tablename__ = "vegetative_lots"
    __table_args__ = (
        CheckConstraint(_line("label", 255), name="ck_vegetative_lots_label"),
        CheckConstraint(_line("source_detail", 255), name="ck_vegetative_lots_source_detail_text"),
        CheckConstraint(
            "material_type IN ('stem_cutting', 'leaf_cutting', 'root_cutting')",
            name="ck_vegetative_lots_material_type",
        ),
        CheckConstraint(
            "source_kind IN ('collection_produced', 'purchased', 'gift_exchange', "
            "'self_collected', 'other', 'unknown')",
            name="ck_vegetative_lots_source_kind",
        ),
        CheckConstraint(
            "source_detail IS NULL OR source_kind = 'other'",
            name="ck_vegetative_lots_source_detail",
        ),
        CheckConstraint(
            "CASE WHEN source_kind = 'collection_produced' THEN "
            "num_nonnulls(mother_plant_id, mother_plant_group_id) <= 1 AND "
            "num_nonnulls(supplier_id, order_id, material_provenance_place_id, "
            "provenance_site_id) = 0 "
            "ELSE num_nonnulls(mother_plant_id, mother_plant_group_id) = 0 END",
            name="ck_vegetative_lots_source_references",
        ),
        CheckConstraint(
            "order_id IS NULL OR source_kind = 'purchased'", name="ck_vegetative_lots_order_source"
        ),
        CheckConstraint(_date("taken_on"), name="ck_vegetative_lots_taken_on"),
        CheckConstraint(_quantity("initial_quantity"), name="ck_vegetative_lots_initial_quantity"),
        CheckConstraint(
            _quantity("quantity", lot_remainder=True), name="ck_vegetative_lots_quantity"
        ),
        CheckConstraint(
            "lifecycle IN ('active', 'exhausted', 'discarded', 'lost', 'reversed')",
            name="ck_vegetative_lots_lifecycle",
        ),
        CheckConstraint(_NOTES, name="ck_vegetative_lots_notes"),
    )

    label: Mapped[str | None] = mapped_column(String(255))
    material_type: Mapped[MaterialType] = mapped_column(String(32))
    source_kind: Mapped[SourceKind] = mapped_column(String(32))
    source_detail: Mapped[str | None] = mapped_column(String(255))
    lifecycle: Mapped[LotLifecycle] = mapped_column(String(32), default="active", index=True)
    botanical_identity_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("botanical_identities.id", ondelete="RESTRICT"), index=True
    )
    mother_plant_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("plants.id", ondelete="RESTRICT"), index=True
    )
    mother_plant_group_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("plant_groups.id", ondelete="RESTRICT"), index=True
    )
    supplier_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("suppliers.id", ondelete="RESTRICT"), index=True
    )
    order_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("orders.id", ondelete="RESTRICT"), index=True
    )
    material_provenance_place_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("geographic_places.id", ondelete="RESTRICT"), index=True
    )
    provenance_site_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("provenance_sites.id", ondelete="RESTRICT"), index=True
    )
    location_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("locations.id", ondelete="RESTRICT"), index=True
    )
    taken_on_precision: Mapped[str | None] = mapped_column(String(8))
    taken_on_year: Mapped[int | None] = mapped_column(SmallInteger())
    taken_on_month: Mapped[int | None] = mapped_column(SmallInteger())
    taken_on_day: Mapped[int | None] = mapped_column(SmallInteger())
    initial_quantity_value: Mapped[int | None] = mapped_column(Integer())
    initial_quantity_is_approximate: Mapped[bool | None] = mapped_column(Boolean())
    quantity_value: Mapped[int | None] = mapped_column(Integer())
    quantity_is_approximate: Mapped[bool | None] = mapped_column(Boolean())


class PropagationAttempt(CuttingRecord, Base):
    __tablename__ = "propagation_attempts"
    __table_args__ = (
        CheckConstraint(_line("label", 255), name="ck_propagation_attempts_label"),
        *(
            CheckConstraint(_line(column, 500), name=f"ck_propagation_attempts_{column}")
            for column in ("hormone_treatment", "substrate", "container", "environment")
        ),
        CheckConstraint("attempt_kind = 'cutting'", name="ck_propagation_attempts_kind"),
        CheckConstraint(
            "lifecycle IN ('active', 'completed', 'failed', 'abandoned', 'reversed')",
            name="ck_propagation_attempts_lifecycle",
        ),
        CheckConstraint(_date("started_on"), name="ck_propagation_attempts_started_on"),
        CheckConstraint(_date("ended_on"), name="ck_propagation_attempts_ended_on"),
        CheckConstraint(
            "ROW(ended_on_year, coalesce(ended_on_month, 12), coalesce(ended_on_day, 31)) "
            ">= ROW(started_on_year, coalesce(started_on_month, 1), coalesce(started_on_day, 1))",
            name="ck_propagation_attempts_date_order",
        ),
        CheckConstraint(_quantity("quantity"), name="ck_propagation_attempts_quantity"),
        CheckConstraint(
            "rooted_count >= 0 AND (quantity_is_approximate IS DISTINCT FROM false "
            "OR rooted_count <= quantity_value)",
            name="ck_propagation_attempts_rooted_count",
        ),
        CheckConstraint(
            "lifecycle <> 'failed' OR rooted_count IS NULL OR rooted_count = 0",
            name="ck_propagation_attempts_failed_count",
        ),
        CheckConstraint(
            "temperature_min_c BETWEEN -50 AND 70", name="ck_propagation_attempts_temperature_min"
        ),
        CheckConstraint(
            "temperature_max_c BETWEEN -50 AND 70", name="ck_propagation_attempts_temperature_max"
        ),
        CheckConstraint(
            "temperature_min_c <= temperature_max_c",
            name="ck_propagation_attempts_temperature_order",
        ),
        CheckConstraint(_NOTES, name="ck_propagation_attempts_notes"),
    )

    label: Mapped[str | None] = mapped_column(String(255))
    attempt_kind: Mapped[str] = mapped_column(String(32), default="cutting")
    lifecycle: Mapped[AttemptLifecycle] = mapped_column(String(32), default="active", index=True)
    rooted_count: Mapped[int | None] = mapped_column(Integer())
    hormone_treatment: Mapped[str | None] = mapped_column(String(500))
    substrate: Mapped[str | None] = mapped_column(String(500))
    container: Mapped[str | None] = mapped_column(String(500))
    environment: Mapped[str | None] = mapped_column(String(500))
    temperature_min_c: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    temperature_max_c: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    vegetative_lot_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("vegetative_lots.id", ondelete="RESTRICT"), index=True
    )
    location_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("locations.id", ondelete="RESTRICT"), index=True
    )
    started_on_precision: Mapped[str | None] = mapped_column(String(8))
    started_on_year: Mapped[int | None] = mapped_column(SmallInteger())
    started_on_month: Mapped[int | None] = mapped_column(SmallInteger())
    started_on_day: Mapped[int | None] = mapped_column(SmallInteger())
    ended_on_precision: Mapped[str | None] = mapped_column(String(8))
    ended_on_year: Mapped[int | None] = mapped_column(SmallInteger())
    ended_on_month: Mapped[int | None] = mapped_column(SmallInteger())
    ended_on_day: Mapped[int | None] = mapped_column(SmallInteger())
    quantity_value: Mapped[int | None] = mapped_column(Integer())
    quantity_is_approximate: Mapped[bool | None] = mapped_column(Boolean())


class RootingObservation(CuttingRecord, Base):
    __tablename__ = "rooting_observations"
    __table_args__ = (
        CheckConstraint(_date("observed_on"), name="ck_rooting_observations_observed_on"),
        CheckConstraint(
            "stage IN ('callus', 'root_initials', 'rooted', 'loss', 'inspection')",
            name="ck_rooting_observations_stage",
        ),
        CheckConstraint("rooted_count >= 0", name="ck_rooting_observations_rooted_count"),
        CheckConstraint(_NOTES, name="ck_rooting_observations_notes"),
        Index(
            "ix_rooting_observations_timeline",
            "propagation_attempt_id",
            "observed_on_year",
            "observed_on_month",
            "observed_on_day",
            "id",
        ),
    )

    propagation_attempt_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("propagation_attempts.id", ondelete="CASCADE")
    )
    stage: Mapped[RootingStage] = mapped_column(String(32))
    rooted_count: Mapped[int | None] = mapped_column(Integer())
    observed_on_precision: Mapped[str | None] = mapped_column(String(8))
    observed_on_year: Mapped[int | None] = mapped_column(SmallInteger())
    observed_on_month: Mapped[int | None] = mapped_column(SmallInteger())
    observed_on_day: Mapped[int | None] = mapped_column(SmallInteger())
