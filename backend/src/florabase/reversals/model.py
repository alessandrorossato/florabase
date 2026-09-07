from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid7

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from florabase.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class OperationKind(StrEnum):
    SEED_LOT_TO_SOWING = "seed_lot_to_sowing"
    SOWING_TO_PLANT = "sowing_to_plant"
    SOWING_TO_PLANT_GROUP = "sowing_to_plant_group"
    PLANT_GROUP_EXTRACTION = "plant_group_extraction"
    PLANT_TRANSFER = "plant_transfer"
    PLANT_GROUP_TRANSFER = "plant_group_transfer"


class OperationStatus(StrEnum):
    APPLIED = "applied"
    REVERSED = "reversed"


class OperationReceipt(Base):
    __tablename__ = "operation_receipts"
    __table_args__ = (
        CheckConstraint(
            "((result_date_precision IS NULL AND result_date_year IS NULL AND res"
            "ult_date_month IS NU"
            "LL AND result_date_day IS NULL) OR (result_date_year BETWEEN 1 AND 9"
            "999 AND ((result_dat"
            "e_precision = 'year' AND result_date_month IS NULL AND result_date_d"
            "ay IS NULL) OR (resu"
            "lt_date_precision = 'month' AND result_date_month BETWEEN 1 AND 12 A"
            "ND result_date_day I"
            "S NULL) OR (result_date_precision = 'day' AND result_date_month BETW"
            "EEN 1 AND 12 AND res"
            "ult_date_day BETWEEN 1 AND 31 AND make_date(result_date_year, result"
            "_date_month, result_"
            "date_day) IS NOT NULL)))) IS TRUE",
            name="ck_operation_receipts_result_date",
        ),
        CheckConstraint(
            "((result_quantity_kind IS NULL AND result_quantity_value IS NULL AND"
            " result_quantity_uni"
            "t IS NULL AND result_quantity_is_approximate IS NULL) OR (result_qua"
            "ntity_kind IN ('seed"
            "_count', 'count') AND result_quantity_value >= 0 AND result_quantity"
            "_value = trunc(resul"
            "t_quantity_value) AND result_quantity_unit IS NULL AND result_quanti"
            "ty_is_approximate IS"
            " NOT NULL) OR (result_quantity_kind = 'weight' AND result_quantity_v"
            "alue > 0 AND result_"
            "quantity_unit IN ('g', 'mg') AND result_quantity_is_approximate IS N"
            "OT NULL)) IS TRUE",
            name="ck_operation_receipts_result_quantity",
        ),
        CheckConstraint(
            "((result_snapshot_version IS NULL AND result_lifecycle IS NULL AND r"
            "esult_quantity_kind "
            "IS NULL AND result_quantity_value IS NULL AND result_quantity_unit I"
            "S NULL AND result_qu"
            "antity_is_approximate IS NULL AND result_botanical_identity_id IS NU"
            "LL AND result_locati"
            "on_id IS NULL AND result_date_precision IS NULL AND result_date_year"
            " IS NULL AND result_"
            "date_month IS NULL AND result_date_day IS NULL AND source_location_i"
            "d IS NULL AND source"
            "_seed_lot_id IS NULL) OR (result_snapshot_version = 1 AND ((kind = '"
            "seed_lot_to_sowing' "
            "AND result_lifecycle IN ('active', 'completed', 'failed', 'abandoned"
            "') AND result_botani"
            "cal_identity_id IS NULL AND source_seed_lot_id IS NULL AND (result_q"
            "uantity_kind IS NULL"
            " OR result_quantity_kind IN ('seed_count', 'weight'))) OR (kind = 's"
            "owing_to_plant' AND "
            "result_lifecycle IN ('active', 'transferred', 'dead', 'lost', 'disca"
            "rded') AND result_bo"
            "tanical_identity_id IS NOT NULL AND source_seed_lot_id IS NOT NULL A"
            "ND result_quantity_k"
            "ind IS NULL) OR (kind = 'sowing_to_plant_group' AND result_lifecycle"
            " IN ('active', 'tran"
            "sferred', 'completed', 'dead', 'lost', 'discarded') AND result_botan"
            "ical_identity_id IS "
            "NOT NULL AND source_seed_lot_id IS NOT NULL AND (result_quantity_kin"
            "d IS NULL OR result_"
            "quantity_kind = 'count'))))) IS TRUE",
            name="ck_operation_receipts_result_snapshot",
        ),
        CheckConstraint(
            "kind IN ('seed_lot_to_sowing', 'sowing_to_plant', 'sowing_to_plant_group', "
            "'plant_group_extraction', 'plant_transfer', 'plant_group_transfer')",
            name="ck_operation_receipts_kind",
        ),
        CheckConstraint(
            "status IN ('applied', 'reversed')",
            name="ck_operation_receipts_status",
        ),
        CheckConstraint(
            "adjustment_mode IS NULL OR adjustment_mode IN ('none', 'partial', 'use_all')",
            name="ck_operation_receipts_adjustment_mode",
        ),
        CheckConstraint(
            "((kind = 'seed_lot_to_sowing' AND seed_lot_id IS NOT NULL AND "
            "sowing_id IS NOT NULL AND plant_id IS NULL AND plant_group_id IS NULL AND "
            "event_id IS NULL AND adjustment_mode IS NOT NULL) OR "
            "(kind = 'sowing_to_plant' AND seed_lot_id IS NULL AND sowing_id IS NOT NULL "
            "AND plant_id IS NOT NULL AND plant_group_id IS NULL AND event_id IS NULL "
            "AND adjustment_mode IS NULL) OR "
            "(kind = 'sowing_to_plant_group' AND seed_lot_id IS NULL AND sowing_id IS NOT NULL "
            "AND plant_id IS NULL AND plant_group_id IS NOT NULL AND event_id IS NULL "
            "AND adjustment_mode IS NULL) OR "
            "(kind = 'plant_group_extraction' AND seed_lot_id IS NULL AND sowing_id IS NULL "
            "AND plant_id IS NOT NULL AND plant_group_id IS NOT NULL AND event_id IS NOT NULL "
            "AND adjustment_mode IS NULL) OR "
            "(kind = 'plant_transfer' AND seed_lot_id IS NULL AND sowing_id IS NULL "
            "AND plant_id IS NOT NULL AND plant_group_id IS NULL AND event_id IS NOT NULL "
            "AND adjustment_mode IS NULL) OR "
            "(kind = 'plant_group_transfer' AND seed_lot_id IS NULL AND sowing_id IS NULL "
            "AND plant_id IS NULL AND plant_group_id IS NOT NULL AND event_id IS NOT NULL "
            "AND adjustment_mode IS NULL)) IS TRUE",
            name="ck_operation_receipts_typed_references",
        ),
        CheckConstraint(
            "((before_quantity_kind IS NULL AND before_quantity_value IS NULL AND "
            "before_quantity_unit IS NULL AND before_quantity_is_approximate IS NULL) OR "
            "(before_quantity_kind = 'seed_count' AND before_quantity_value >= 0 AND "
            "before_quantity_value = trunc(before_quantity_value) AND "
            "before_quantity_unit IS NULL AND before_quantity_is_approximate IS NOT NULL) OR "
            "(before_quantity_kind = 'weight' AND before_quantity_value >= 0 AND "
            "before_quantity_unit IN ('g', 'mg') AND "
            "before_quantity_is_approximate IS NOT NULL) OR "
            "(before_quantity_kind = 'count' AND before_quantity_value >= 0 AND "
            "before_quantity_value = trunc(before_quantity_value) AND "
            "before_quantity_unit IS NULL AND before_quantity_is_approximate IS NOT NULL)) "
            "IS TRUE",
            name="ck_operation_receipts_before_quantity",
        ),
        CheckConstraint(
            "((after_quantity_kind IS NULL AND after_quantity_value IS NULL AND "
            "after_quantity_unit IS NULL AND after_quantity_is_approximate IS NULL) OR "
            "(after_quantity_kind = 'seed_count' AND after_quantity_value >= 0 AND "
            "after_quantity_value = trunc(after_quantity_value) AND after_quantity_unit IS NULL "
            "AND after_quantity_is_approximate IS NOT NULL) OR "
            "(after_quantity_kind = 'weight' AND after_quantity_value >= 0 AND "
            "after_quantity_unit IN ('g', 'mg') AND after_quantity_is_approximate IS NOT NULL) OR "
            "(after_quantity_kind = 'count' AND after_quantity_value >= 0 AND "
            "after_quantity_value = trunc(after_quantity_value) AND after_quantity_unit IS NULL "
            "AND after_quantity_is_approximate IS NOT NULL)) IS TRUE",
            name="ck_operation_receipts_after_quantity",
        ),
        CheckConstraint(
            "((kind = 'seed_lot_to_sowing' AND before_lifecycle IN "
            "('active', 'exhausted', 'discarded', 'lost') AND after_lifecycle IN "
            "('active', 'exhausted', 'discarded', 'lost') AND "
            "(before_quantity_kind IS NULL OR before_quantity_kind IN ('seed_count', 'weight')) "
            "AND (after_quantity_kind IS NULL OR "
            "after_quantity_kind IN ('seed_count', 'weight'))) OR "
            "(kind IN ('sowing_to_plant', 'sowing_to_plant_group') AND before_lifecycle IN "
            "('active', 'completed', 'failed', 'abandoned') AND after_lifecycle IN "
            "('active', 'completed', 'failed', 'abandoned') AND "
            "(before_quantity_kind IS NULL OR before_quantity_kind IN ('seed_coun"
            "t', 'weight')) AND "
            "(after_quantity_kind IS NULL OR after_quantity_kind IN ('seed_count', 'weight'))) OR "
            "(kind = 'plant_group_extraction' AND before_lifecycle = 'active' AND "
            "after_lifecycle IN ('active', 'completed') AND "
            "(before_quantity_kind IS NULL OR before_quantity_kind = 'count') AND "
            "(after_quantity_kind IS NULL OR after_quantity_kind = 'count')) OR "
            "(kind = 'plant_transfer' AND before_lifecycle IN "
            "('active', 'dead', 'lost', 'discarded') AND "
            "after_lifecycle = 'transferred' AND before_quantity_kind IS NULL AND "
            "before_quantity_value IS NULL AND before_quantity_unit IS NULL AND "
            "before_quantity_is_approximate IS NULL AND after_quantity_kind IS NULL AND "
            "after_quantity_value IS NULL AND after_quantity_unit IS NULL AND "
            "after_quantity_is_approximate IS NULL) OR "
            "(kind = 'plant_group_transfer' AND before_lifecycle IN "
            "('active', 'completed', 'dead', 'lost', 'discarded') AND "
            "after_lifecycle = 'transferred' AND "
            "(before_quantity_kind IS NULL OR before_quantity_kind = 'count') AND "
            "(after_quantity_kind IS NULL OR after_quantity_kind = 'count'))) IS TRUE",
            name="ck_operation_receipts_typed_state",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    kind: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default=OperationStatus.APPLIED.value)
    seed_lot_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("seed_lots.id", ondelete="RESTRICT"), nullable=True
    )
    sowing_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("sowings.id", ondelete="RESTRICT"), nullable=True
    )
    plant_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("plants.id", ondelete="RESTRICT"), nullable=True
    )
    plant_group_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("plant_groups.id", ondelete="RESTRICT"), nullable=True
    )
    event_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("events.id", ondelete="RESTRICT"), nullable=True, unique=True
    )
    adjustment_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    before_lifecycle: Mapped[str] = mapped_column(String(16))
    after_lifecycle: Mapped[str] = mapped_column(String(16))
    before_quantity_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
    before_quantity_value: Mapped[Decimal | None] = mapped_column(Numeric(), nullable=True)
    before_quantity_unit: Mapped[str | None] = mapped_column(String(8), nullable=True)
    before_quantity_is_approximate: Mapped[bool | None] = mapped_column(Boolean(), nullable=True)
    after_quantity_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
    after_quantity_value: Mapped[Decimal | None] = mapped_column(Numeric(), nullable=True)
    after_quantity_unit: Mapped[str | None] = mapped_column(String(8), nullable=True)
    after_quantity_is_approximate: Mapped[bool | None] = mapped_column(Boolean(), nullable=True)
    # Version 1 exists only for newly captured propagation results; NULL means legacy.
    result_snapshot_version: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    result_lifecycle: Mapped[str | None] = mapped_column(String(16), nullable=True)
    result_quantity_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
    result_quantity_value: Mapped[Decimal | None] = mapped_column(Numeric(), nullable=True)
    result_quantity_unit: Mapped[str | None] = mapped_column(String(8), nullable=True)
    result_quantity_is_approximate: Mapped[bool | None] = mapped_column(Boolean(), nullable=True)
    result_botanical_identity_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    result_location_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    result_date_precision: Mapped[str | None] = mapped_column(String(8), nullable=True)
    result_date_year: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    result_date_month: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    result_date_day: Mapped[int | None] = mapped_column(SmallInteger(), nullable=True)
    source_location_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    source_seed_lot_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
