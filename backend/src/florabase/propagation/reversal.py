"""Purpose-specific, downstream-first propagation compensation; never inverse arithmetic."""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from florabase.events.model import Event
from florabase.plants.model import Plant, PlantGroup
from florabase.propagation.reversal_schemas import (
    PropagationReversalEligibility,
    ReversalReason,
    ReversalReasonCode,
)
from florabase.propagation.service import PropagationConflictError, PropagationNotFoundError
from florabase.propagation.snapshots import result_snapshot
from florabase.reversals.model import OperationKind, OperationReceipt
from florabase.reversals.service import seed_quantity
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing

ResultType = Literal["sowing", "plant", "plant_group"]
RESULTS: dict[ResultType, tuple[type[Sowing] | type[Plant] | type[PlantGroup], OperationKind]] = {
    "sowing": (Sowing, OperationKind.SEED_LOT_TO_SOWING),
    "plant": (Plant, OperationKind.SOWING_TO_PLANT),
    "plant_group": (PlantGroup, OperationKind.SOWING_TO_PLANT_GROUP),
}
RETAINABLE = {"observation", "flowering", "fruiting"}


@dataclass(frozen=True)
class Evaluation:
    eligibility: PropagationReversalEligibility
    receipt: OperationReceipt | None
    source: SeedLot | Sowing | None
    result: Sowing | Plant | PlantGroup


def evaluate(
    database: Session, result_type: ResultType, result_id: UUID, *, lock: bool = False
) -> Evaluation:
    model, kind = RESULTS[result_type]
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
    source_model = SeedLot if result_type == "sowing" else Sowing
    source_id = (
        (receipt.seed_lot_id if result_type == "sowing" else receipt.sowing_id) if receipt else None
    )
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
    assert isinstance(result, (Sowing, Plant, PlantGroup))
    assert source is None or isinstance(source, (SeedLot, Sowing))
    reasons: list[ReversalReason] = []
    observations: list[UUID] = []

    def block(
        code: ReversalReasonCode,
        message: str,
        entity_type: ResultType | Literal["seed_lot"] | None = None,
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
                result.seed_lot_id if isinstance(result, Sowing) else result.originating_sowing_id
            )
            if parent_id != source.id or (
                isinstance(result, Plant) and result.originating_plant_group_id is not None
            ):
                block(
                    "receipt_relationship_mismatch",
                    "The result no longer has its recorded source relationship.",
                )
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
            if any(
                getattr(receipt, field) != value
                for field, value in seed_quantity(source).columns("after").items()
            ):
                block(
                    "source_quantity_changed",
                    "Source quantity changed later; restoring the old snapshot would overwrite it.",
                )
            if source.location_id != receipt.source_location_id or (
                isinstance(source, Sowing) and source.seed_lot_id != receipt.source_seed_lot_id
            ):
                block(
                    "source_structural_state_changed",
                    "The source location or SeedLot relationship changed after this operation.",
                )

        # Later operations sharing the mutable source must be compensated first even if
        # their expected state happens to equal ours (e.g. two active -> active transitions).
        source_column = (
            OperationReceipt.seed_lot_id
            if isinstance(source, SeedLot)
            else OperationReceipt.sowing_id
        )
        source_kinds = (
            ["seed_lot_to_sowing"]
            if isinstance(source, SeedLot)
            else ["sowing_to_plant", "sowing_to_plant_group"]
        )
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
                "plant" if item.plant_id else "plant_group" if item.plant_group_id else "sowing"
            )
            child_id = item.plant_id or item.plant_group_id or item.sowing_id
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

        if isinstance(result, Sowing):
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
        source_type="seed_lot" if result_type == "sowing" else "sowing",
        reasons=list({(r.code, r.entity_id): r for r in reasons}.values()),
        retained_observation_ids=observations,
    )
    return Evaluation(eligibility, receipt, source, result)


def reverse(
    database: Session, result_type: ResultType, result_id: UUID, *, confirm: bool
) -> Evaluation:
    evaluation = evaluate(database, result_type, result_id, lock=True)
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
    # Sowing transitions only changed lifecycle. In particular, never rewrite germinated_count.
    evaluation.result.lifecycle = "reversed"
    receipt.status = "reversed"
    database.flush()
    return evaluation
