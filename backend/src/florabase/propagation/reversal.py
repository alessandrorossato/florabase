"""Purpose-specific, downstream-first propagation compensation; never inverse arithmetic."""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from florabase.collection_photos.model import RecordMediaLink
from florabase.cuttings.model import PropagationAttempt, RootingObservation, VegetativeLot
from florabase.events.model import Event
from florabase.lineage.service import lock_lineage_writes
from florabase.plants.model import Plant, PlantGroup
from florabase.propagation.reversal_schemas import (
    PropagationReversalEligibility,
    ReversalReason,
    ReversalReasonCode,
)
from florabase.propagation.service import PropagationConflictError, PropagationNotFoundError
from florabase.propagation.snapshots import (
    attempt_snapshot,
    cutting_source_snapshot,
    result_snapshot,
)
from florabase.reversals.model import OperationKind, OperationReceipt
from florabase.reversals.service import group_quantity, seed_quantity
from florabase.schedule.model import ScheduledActivity
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing

ResultType = Literal["sowing", "plant", "plant_group", "propagation_attempt"]
RESULTS: dict[
    ResultType,
    tuple[type[Sowing] | type[Plant] | type[PlantGroup] | type[PropagationAttempt], OperationKind],
] = {
    "sowing": (Sowing, OperationKind.SEED_LOT_TO_SOWING),
    "plant": (Plant, OperationKind.SOWING_TO_PLANT),
    "plant_group": (PlantGroup, OperationKind.SOWING_TO_PLANT_GROUP),
}
CUTTING_RESULTS: dict[
    ResultType,
    tuple[type[Sowing] | type[Plant] | type[PlantGroup] | type[PropagationAttempt], OperationKind],
] = {
    "propagation_attempt": (
        PropagationAttempt,
        OperationKind.VEGETATIVE_LOT_TO_PROPAGATION_ATTEMPT,
    ),
    "plant": (Plant, OperationKind.PROPAGATION_ATTEMPT_TO_PLANT),
    "plant_group": (PlantGroup, OperationKind.PROPAGATION_ATTEMPT_TO_PLANT_GROUP),
}
RETAINABLE = {"observation", "flowering", "fruiting", "measurement"}


@dataclass(frozen=True)
class Evaluation:
    eligibility: PropagationReversalEligibility
    receipt: OperationReceipt | None
    source: SeedLot | Sowing | VegetativeLot | PropagationAttempt | None
    result: Sowing | Plant | PlantGroup | PropagationAttempt


def evaluate(
    database: Session,
    result_type: ResultType,
    result_id: UUID,
    *,
    lock: bool = False,
    cutting: bool = False,
) -> Evaluation:
    model, kind = (CUTTING_RESULTS if cutting else RESULTS)[result_type]
    if lock and cutting:
        lock_lineage_writes(database)
    statement = select(OperationReceipt).where(
        OperationReceipt.kind == kind.value,
        getattr(OperationReceipt, f"{result_type}_id") == result_id,
    )
    if lock:
        statement = statement.with_for_update()
    receipts = list(database.scalars(statement.execution_options(populate_existing=True)))
    receipt = receipts[0] if len(receipts) == 1 else None
    # Global order agrees with forward propagation and extraction: receipt -> SeedLot ->
    # Sowing -> PlantGroup -> Plant. No dependent receipt is locked while holding aggregates.
    source_type: Literal["seed_lot", "sowing", "vegetative_lot", "propagation_attempt"]
    source_model: type[SeedLot] | type[Sowing] | type[VegetativeLot] | type[PropagationAttempt]
    if result_type == "propagation_attempt":
        source_type, source_model = "vegetative_lot", VegetativeLot
    elif cutting:
        source_type, source_model = "propagation_attempt", PropagationAttempt
    elif result_type == "sowing":
        source_type, source_model = "seed_lot", SeedLot
    else:
        source_type, source_model = "sowing", Sowing
    source_id = getattr(receipt, f"{source_type}_id") if receipt is not None else None
    source_statement = select(source_model).where(source_model.id == source_id)
    result_statement = select(model).where(model.id == result_id)
    if lock:
        source_statement = source_statement.with_for_update()
        result_statement = result_statement.with_for_update()
    source = (
        database.scalar(source_statement.execution_options(populate_existing=True))
        if receipt
        else None
    )
    result = database.scalar(result_statement.execution_options(populate_existing=True))
    if result is None:
        raise PropagationNotFoundError(f"{result_type}_not_found", "Propagation result not found")
    assert isinstance(result, (Sowing, Plant, PlantGroup, PropagationAttempt))
    assert source is None or isinstance(
        source, (SeedLot, Sowing, VegetativeLot, PropagationAttempt)
    )
    lot = (
        source
        if isinstance(source, VegetativeLot)
        else database.get(VegetativeLot, source.vegetative_lot_id)
        if isinstance(source, PropagationAttempt)
        else None
    )
    reasons: list[ReversalReason] = []
    observations: list[UUID] = []

    def block(
        code: ReversalReasonCode,
        message: str,
        entity_type: ResultType | Literal["seed_lot", "vegetative_lot"] | None = None,
        entity_id: UUID | None = None,
    ) -> None:
        reasons.append(
            ReversalReason(code=code, message=message, entity_type=entity_type, entity_id=entity_id)
        )

    if receipt is None:
        block(
            "propagation_receipt_not_found",
            "No unique supported propagation receipt exists for this record.",
        )
    elif source is None:
        block("receipt_relationship_mismatch", "The recorded source no longer exists.")
    else:
        if receipt.status != "applied":
            block(
                "receipt_already_reversed", "This propagation operation has already been reversed."
            )
        if receipt.result_snapshot_version != 1:
            block(
                "legacy_receipt_missing_result_snapshot",
                "This operation predates complete automatic-reversal metadata.",
            )
        else:
            parent_id = (
                result.seed_lot_id
                if isinstance(result, Sowing)
                else result.vegetative_lot_id
                if isinstance(result, PropagationAttempt)
                else result.originating_propagation_attempt_id
                if cutting
                else result.originating_sowing_id
            )
            if parent_id != source.id or (
                isinstance(result, Plant) and result.originating_plant_group_id is not None
            ):
                block(
                    "receipt_relationship_mismatch",
                    "The result no longer has its recorded source relationship.",
                )
            if isinstance(result, PropagationAttempt):
                assert lot is not None
                expected = attempt_snapshot(result, lot)
            else:
                expected = result_snapshot(result)
            if result.lifecycle != receipt.result_lifecycle:
                block("result_lifecycle_changed", "The result lifecycle changed after creation.")
            if any(
                getattr(receipt, field) != value
                for field, value in expected.items()
                if field != "result_lifecycle"
            ):
                block(
                    "result_structural_state_changed",
                    "Result quantity, identity, location, or date changed after creation.",
                )
            if result.lifecycle in {
                "reversed",
                "reintegrated",
                "transferred",
                "dead",
                "lost",
                "discarded",
                "failed",
                "abandoned",
            }:
                block(
                    "result_terminal_lifecycle",
                    "This historical or terminal result cannot be reversed automatically.",
                )
            if source.lifecycle != receipt.after_lifecycle:
                block(
                    "source_lifecycle_changed",
                    "The source lifecycle no longer matches the recorded expected state.",
                )
            quantity = (
                group_quantity(source)
                if isinstance(source, (VegetativeLot, PropagationAttempt))
                else seed_quantity(source)
            )
            if any(
                getattr(receipt, field) != value
                for field, value in quantity.columns("after").items()
            ):
                block(
                    "source_quantity_changed",
                    "Source quantity changed later; restoring the old snapshot would overwrite it.",
                )
            if (
                source.location_id != receipt.source_location_id
                or (isinstance(source, Sowing) and source.seed_lot_id != receipt.source_seed_lot_id)
                or (
                    isinstance(source, PropagationAttempt)
                    and source.vegetative_lot_id != receipt.source_vegetative_lot_id
                )
                or (
                    isinstance(source, (VegetativeLot, PropagationAttempt))
                    and lot is not None
                    and any(
                        getattr(receipt, field) != value
                        for field, value in cutting_source_snapshot(source, lot).items()
                    )
                )
            ):
                block(
                    "source_structural_state_changed",
                    "The source location or SeedLot relationship changed after this operation.",
                )

        # Later operations sharing the mutable source must be compensated first even if
        # their expected state happens to equal ours (e.g. two active -> active transitions).
        source_column = getattr(OperationReceipt, f"{source_type}_id")
        source_kinds = {
            "seed_lot": [OperationKind.SEED_LOT_TO_SOWING],
            "sowing": [OperationKind.SOWING_TO_PLANT, OperationKind.SOWING_TO_PLANT_GROUP],
            "vegetative_lot": [OperationKind.VEGETATIVE_LOT_TO_PROPAGATION_ATTEMPT],
            "propagation_attempt": [
                OperationKind.PROPAGATION_ATTEMPT_TO_PLANT,
                OperationKind.PROPAGATION_ATTEMPT_TO_PLANT_GROUP,
            ],
        }[source_type]
        later = list(
            database.scalars(
                select(OperationReceipt).where(
                    source_column == source.id,
                    OperationReceipt.kind.in_(source_kinds),
                    OperationReceipt.id > receipt.id,
                    OperationReceipt.status == "applied",
                )
            )
        )
        for item in later:
            child_type: ResultType = (
                "plant"
                if item.plant_id
                else "plant_group"
                if item.plant_group_id
                else "propagation_attempt"
                if item.propagation_attempt_id
                else "sowing"
            )
            child_id = (
                item.plant_id
                or item.plant_group_id
                or item.sowing_id
                or item.propagation_attempt_id
            )
            block(
                "later_source_operation",
                "Undo the later operation on this source first.",
                child_type,
                child_id,
            )

        active = list(
            database.scalars(
                select(OperationReceipt).where(
                    getattr(OperationReceipt, f"{result_type}_id") == result_id,
                    OperationReceipt.id != receipt.id,
                    OperationReceipt.status == "applied",
                )
            )
        )
        for item in active:
            code: ReversalReasonCode = (
                "transfer_exists" if "transfer" in item.kind else "active_downstream_operation"
            )
            child_type = (
                "plant" if item.plant_id else "plant_group" if item.plant_group_id else "sowing"
            )
            block(
                code,
                "Undo the dependent operation first; reversal never cascades.",
                child_type,
                item.plant_id or item.plant_group_id or item.sowing_id,
            )

        if cutting:
            for model_with_target, code, message in (
                (
                    RecordMediaLink,
                    "linked_media_exists",
                    "Remove linked media before reversing this operation.",
                ),
                (ScheduledActivity, "scheduled_work_exists", "Scheduled work retains this record."),
            ):
                if database.scalar(
                    select(
                        select(model_with_target.id)
                        .where(getattr(model_with_target, f"{result_type}_id") == result.id)
                        .exists()
                    )
                ):
                    block(code, message)
        if isinstance(result, PropagationAttempt):
            for child_model in (Plant, PlantGroup):
                if database.scalar(
                    select(
                        select(child_model.id)
                        .where(
                            child_model.originating_propagation_attempt_id == result.id,
                            child_model.lifecycle != "reversed",
                        )
                        .exists()
                    )
                ):
                    block("downstream_lineage", "Reverse dependent establishments first.")
            observations.extend(
                database.scalars(
                    select(RootingObservation.id).where(
                        RootingObservation.propagation_attempt_id == result.id
                    )
                )
            )
        elif isinstance(result, Sowing):
            children: list[Plant | PlantGroup] = list(
                database.scalars(select(Plant).where(Plant.originating_sowing_id == result.id))
            )
            children.extend(
                database.scalars(
                    select(PlantGroup).where(PlantGroup.originating_sowing_id == result.id)
                )
            )
            for child in children:
                child_type = "plant" if isinstance(child, Plant) else "plant_group"
                historical = database.scalar(
                    select(OperationReceipt.id).where(
                        OperationReceipt.sowing_id == result.id,
                        getattr(OperationReceipt, f"{child_type}_id") == child.id,
                        OperationReceipt.kind == RESULTS[child_type][1].value,
                        OperationReceipt.status == "reversed",
                    )
                )
                if child.lifecycle != "reversed" or historical is None:
                    block(
                        "downstream_lineage",
                        "A descendant still depends on this Sowing. Undo its creation first.",
                        child_type,
                        child.id,
                    )
        else:
            producer_column = (
                SeedLot.producer_plant_id
                if isinstance(result, Plant)
                else SeedLot.producer_plant_group_id
            )
            for lot_id in database.scalars(select(SeedLot.id).where(producer_column == result.id)):
                block(
                    "produced_seed_lot_exists",
                    "This result produced a SeedLot and must remain a valid producer.",
                    "seed_lot",
                    lot_id,
                )
            mother_column = (
                VegetativeLot.mother_plant_id
                if isinstance(result, Plant)
                else VegetativeLot.mother_plant_group_id
            )
            for lot_id in database.scalars(
                select(VegetativeLot.id).where(mother_column == result.id)
            ):
                block(
                    "produced_vegetative_lot_exists",
                    "This result is the mother of a retained vegetative lot.",
                    "vegetative_lot",
                    lot_id,
                )
            if isinstance(result, PlantGroup):
                for child in database.scalars(
                    select(Plant).where(Plant.originating_plant_group_id == result.id)
                ):
                    historical = database.scalar(
                        select(OperationReceipt.id).where(
                            OperationReceipt.kind == "plant_group_extraction",
                            OperationReceipt.plant_id == child.id,
                            OperationReceipt.plant_group_id == result.id,
                            OperationReceipt.status == "reversed",
                        )
                    )
                    if child.lifecycle != "reintegrated" or historical is None:
                        block(
                            "later_extraction_exists",
                            "Reintegrate the extracted Plant first.",
                            "plant",
                            child.id,
                        )
            event_column = Event.plant_id if isinstance(result, Plant) else Event.plant_group_id
            for event in database.scalars(select(Event).where(event_column == result.id)):
                historical_operation = database.scalar(
                    select(OperationReceipt.id).where(
                        OperationReceipt.status == "reversed",
                        or_(
                            OperationReceipt.event_id == event.id,
                            OperationReceipt.id == event.reversed_operation_receipt_id,
                        ),
                    )
                )
                if historical_operation is not None:
                    continue
                if event.kind in RETAINABLE:
                    observations.append(event.id)
                else:
                    block(
                        "incompatible_result_history",
                        "Later history includes work beyond a retained observation.",
                    )
    eligibility = PropagationReversalEligibility(
        status="blocked" if reasons else "confirmation_required" if observations else "safe",
        operation_receipt_id=receipt.id if receipt else None,
        operation_status=receipt.status if receipt else None,
        source_id=source.id if source else None,
        source_type=source_type,
        reasons=list({(r.code, r.entity_id): r for r in reasons}.values()),
        retained_observation_ids=observations,
    )
    return Evaluation(eligibility, receipt, source, result)


def reverse(
    database: Session,
    result_type: ResultType,
    result_id: UUID,
    *,
    confirm: bool,
    cutting: bool = False,
) -> Evaluation:
    evaluation = evaluate(database, result_type, result_id, lock=True, cutting=cutting)
    eligibility = evaluation.eligibility
    if eligibility.status == "blocked":
        reason = eligibility.reasons[0]
        raise PropagationConflictError(reason.code, reason.message)
    if eligibility.status == "confirmation_required" and not confirm:
        raise PropagationConflictError(
            "propagation_confirmation_required",
            "Confirm that observations remain attached to the historical reversed result.",
        )
    source, receipt = evaluation.source, evaluation.receipt
    if source is None or receipt is None:
        raise RuntimeError("Eligible reversal is missing its receipt or source")
    source.lifecycle = receipt.before_lifecycle
    if isinstance(source, SeedLot):
        source.quantity_kind = receipt.before_quantity_kind
        source.quantity_value = receipt.before_quantity_value
        source.quantity_unit = receipt.before_quantity_unit
        source.quantity_is_approximate = receipt.before_quantity_is_approximate
    if isinstance(source, VegetativeLot):
        source.quantity_value = (
            int(receipt.before_quantity_value)
            if receipt.before_quantity_value is not None
            else None
        )
        source.quantity_is_approximate = receipt.before_quantity_is_approximate
    # Sowing transitions only changed lifecycle. In particular, never rewrite germinated_count.
    evaluation.result.lifecycle = "reversed"
    receipt.status = "reversed"
    database.flush()
    return evaluation
