from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.cuttings.model import (
    CuttingRecord,
    PropagationAttempt,
    RootingObservation,
    VegetativeLot,
)
from florabase.cuttings.schemas import (
    AttemptCreate,
    AttemptSetup,
    CuttingQuantity,
    EstablishPlant,
    EstablishPlantGroup,
    FastCreate,
    LotSource,
    PositiveCuttingQuantity,
    PropagationAttemptResponse,
    PropagationAttemptUpdate,
    RootingObservationResponse,
    RootingObservationWrite,
    SourceAdjustment,
    VegetativeLotCreate,
    VegetativeLotResponse,
    VegetativeLotUpdate,
)
from florabase.geographic_places.model import GeographicPlace
from florabase.lineage.service import LineageKey, lock_lineage_writes, validate_source_assignment
from florabase.locations.schemas import LocationUsageScope
from florabase.locations.service import require_location_for_scope
from florabase.orders.model import Order
from florabase.plants.model import Plant, PlantGroup
from florabase.plants.schemas import PlantCreate, PlantGroupCreate
from florabase.plants.service import create_plant, create_plant_group
from florabase.propagation.service import PropagationConflictError, PropagationNotFoundError
from florabase.propagation.snapshots import (
    attempt_snapshot,
    cutting_source_snapshot,
    result_snapshot,
)
from florabase.provenance_sites.model import ProvenanceSite
from florabase.reversals.model import OperationKind, OperationReceipt
from florabase.reversals.service import add_receipt, group_quantity
from florabase.seed_lots.schemas import PartialDate
from florabase.suppliers.model import Supplier


def require_record[Record: CuttingRecord](
    database: Session, model: type[Record], item_id: UUID, *, lock: bool = False
) -> Record:
    item = database.get(model, item_id, with_for_update=lock, populate_existing=lock)
    if item is None:
        raise PropagationNotFoundError("cutting_record_not_found", "Cutting record not found")
    return item


def date_values(prefix: str, value: PartialDate | None) -> dict[str, object]:
    return {
        f"{prefix}_precision": value.precision.value if value else None,
        f"{prefix}_year": value.year if value else None,
        f"{prefix}_month": value.month if value else None,
        f"{prefix}_day": value.day if value else None,
    }


def _date(record: CuttingRecord, prefix: str) -> PartialDate | None:
    precision = getattr(record, f"{prefix}_precision")
    if precision is None:
        return None
    return PartialDate.model_validate(
        {
            "precision": precision,
            **{part: getattr(record, f"{prefix}_{part}") for part in ("year", "month", "day")},
        }
    )


def _quantity_values(prefix: str, value: CuttingQuantity | None) -> dict[str, object]:
    return {
        f"{prefix}_value": value.value if value else None,
        f"{prefix}_is_approximate": value.is_approximate if value else None,
    }


def _quantity(record: VegetativeLot | PropagationAttempt, prefix: str) -> CuttingQuantity | None:
    value = getattr(record, f"{prefix}_value")
    if value is None:
        return None
    return (PositiveCuttingQuantity if value > 0 else CuttingQuantity)(
        value=value, is_approximate=getattr(record, f"{prefix}_is_approximate")
    )


def lot_response(lot: VegetativeLot) -> VegetativeLotResponse:
    return VegetativeLotResponse.model_validate(
        {
            **vars(lot),
            "taken_on": _date(lot, "taken_on"),
            "initial_quantity": _quantity(lot, "initial_quantity"),
            "quantity": _quantity(lot, "quantity"),
        },
        extra="ignore",
    )


def attempt_response(attempt: PropagationAttempt) -> PropagationAttemptResponse:
    quantity = _quantity(attempt, "quantity")
    rate = (
        100 * attempt.rooted_count / quantity.value
        if quantity and not quantity.is_approximate and attempt.rooted_count is not None
        else None
    )
    return PropagationAttemptResponse.model_validate(
        {
            **vars(attempt),
            "started_on": _date(attempt, "started_on"),
            "ended_on": _date(attempt, "ended_on"),
            "quantity": quantity.model_dump() if quantity else None,
            "rooting_rate_percent": rate,
        },
        extra="ignore",
    )


def observation_response(observation: RootingObservation) -> RootingObservationResponse:
    return RootingObservationResponse.model_validate(
        {
            **vars(observation),
            "observed_on": _date(observation, "observed_on"),
        },
        extra="ignore",
    )


def _mother(database: Session, payload: LotSource, lot_id: UUID) -> Plant | PlantGroup | None:
    mother: Plant | PlantGroup | None = None
    source: LineageKey | None = None
    if payload.mother_plant_id is not None:
        mother = database.get(Plant, payload.mother_plant_id, with_for_update=True)
        source = ("plant", payload.mother_plant_id)
    elif payload.mother_plant_group_id is not None:
        mother = database.get(PlantGroup, payload.mother_plant_group_id, with_for_update=True)
        source = ("plant_group", payload.mother_plant_group_id)
    if source is not None:
        if mother is None:
            raise PropagationNotFoundError("mother_not_found", "Mother specimen not found")
        if mother.lifecycle in {"reversed", "reintegrated"}:
            raise PropagationConflictError(
                "historical_mother", "This specimen cannot be assigned as mother"
            )
        validate_source_assignment(database, ("vegetative_lot", lot_id), source)
    return mother


def _lot_values(
    database: Session, payload: LotSource, lot_id: UUID, previous: VegetativeLot | None = None
) -> dict[str, object]:
    mother = _mother(database, payload, lot_id)
    identity_id = payload.botanical_identity_id or (
        mother.botanical_identity_id if mother else None
    )
    references = (
        (BotanicalIdentity, identity_id, "botanical_identity"),
        (Supplier, payload.supplier_id, "supplier"),
        (GeographicPlace, payload.material_provenance_place_id, "geographic_place"),
        (ProvenanceSite, payload.provenance_site_id, "provenance_site"),
    )
    for model, reference, kind in references:
        if reference is not None and database.get(model, reference) is None:
            raise PropagationNotFoundError(
                f"{kind}_not_found", f"{kind.replace('_', ' ').capitalize()} not found"
            )
    if payload.order_id is not None:
        order = database.get(Order, payload.order_id, with_for_update=True)
        if order is None:
            raise PropagationNotFoundError("order_not_found", "Order not found")
        if payload.supplier_id and order.supplier_id and payload.supplier_id != order.supplier_id:
            raise PropagationConflictError(
                "order_supplier_mismatch", "The cutting supplier differs from the order supplier"
            )
    if previous is None or previous.location_id != payload.location_id:
        require_location_for_scope(
            database, payload.location_id, LocationUsageScope.VEGETATIVE_LOTS
        )
    return {
        **payload.model_dump(
            exclude={"initial_quantity", "quantity", "taken_on", "expected_updated_at"}
        ),
        "botanical_identity_id": identity_id,
        **date_values("taken_on", payload.taken_on),
    }


def create_lot(database: Session, payload: VegetativeLotCreate) -> VegetativeLot:
    lock_lineage_writes(database)
    lot_id = uuid7()
    lot = VegetativeLot(
        id=lot_id,
        **_lot_values(database, payload, lot_id),
        **_quantity_values("initial_quantity", payload.initial_quantity),
        **_quantity_values("quantity", payload.initial_quantity),
    )
    database.add(lot)
    database.flush()
    return lot


def _check_revision(record: CuttingRecord, expected: datetime) -> None:
    if record.updated_at != expected:
        raise PropagationConflictError(
            "cutting_record_changed",
            "This record changed. Refresh the record before saving.",
        )


def update_lot(database: Session, lot_id: UUID, payload: VegetativeLotUpdate) -> VegetativeLot:
    lock_lineage_writes(database)
    lot = require_record(database, VegetativeLot, lot_id, lock=True)
    _check_revision(lot, payload.expected_updated_at)
    if lot.lifecycle == "reversed":
        raise PropagationConflictError("lot_reversed", "A reversed lot is historical")
    for key, value in {
        **_lot_values(database, payload, lot_id, lot),
        **_quantity_values("quantity", payload.quantity),
    }.items():
        setattr(lot, key, value)
    database.flush()
    return lot


def delete_lot(database: Session, lot_id: UUID) -> None:
    lock_lineage_writes(database)
    lot = require_record(database, VegetativeLot, lot_id, lock=True)
    database.delete(lot)
    database.flush()


def apply_adjustment(
    lot: VegetativeLot, quantity: CuttingQuantity | None, adjustment: SourceAdjustment
) -> None:
    if lot.lifecycle != "active":
        raise PropagationConflictError("lot_not_active", "Only an active lot can start an attempt")
    if adjustment.mode == "none":
        return
    available = lot.quantity_value
    exact = available is not None and lot.quantity_is_approximate is False
    if adjustment.mode == "use_all":
        if exact:
            if quantity is not None and not quantity.is_approximate and quantity.value != available:
                raise PropagationConflictError(
                    "use_all_quantity_mismatch",
                    "Exact attempt quantity must match exact lot stock when using all",
                )
            lot.quantity_value = 0
        lot.lifecycle = "exhausted"
        return
    remainder = adjustment.resulting_quantity
    if available is None:
        if remainder is not None:
            raise PropagationConflictError(
                "unknown_stock", "An unknown lot must retain an unknown remainder"
            )
        return
    if quantity is None:
        raise PropagationConflictError(
            "attempt_quantity_required", "Partial use of known stock requires a starting quantity"
        )
    if exact:
        if quantity.is_approximate or remainder is not None:
            raise PropagationConflictError(
                "exact_stock_requires_exact_use",
                "Exact stock requires exact usage and a calculated remainder",
            )
        if quantity.value > available:
            raise PropagationConflictError(
                "insufficient_stock", "Starting quantity exceeds the available cuttings"
            )
        lot.quantity_value = available - quantity.value
        if lot.quantity_value == 0:
            lot.lifecycle = "exhausted"
        return
    if remainder is None or not remainder.is_approximate:
        raise PropagationConflictError(
            "approximate_remainder_required", "Confirm an approximate remaining quantity"
        )
    lot.quantity_value = remainder.value


def _setup_values(payload: AttemptSetup) -> dict[str, object]:
    return {
        **payload.model_dump(exclude={"started_on", "ended_on", "quantity", "expected_updated_at"}),
        **date_values("started_on", payload.started_on),
        **_quantity_values("quantity", payload.quantity),
    }


def start_attempt(
    database: Session, lot_id: UUID, payload: AttemptCreate
) -> tuple[VegetativeLot, PropagationAttempt, OperationReceipt]:
    lock_lineage_writes(database)
    lot = require_record(database, VegetativeLot, lot_id, lock=True)
    setup = payload.propagation_attempt
    require_location_for_scope(database, setup.location_id, LocationUsageScope.PROPAGATION_ATTEMPTS)
    before_lifecycle, before_quantity = lot.lifecycle, group_quantity(lot)
    apply_adjustment(lot, setup.quantity, payload.source_adjustment)
    attempt = PropagationAttempt(vegetative_lot_id=lot.id, **_setup_values(setup))
    database.add(attempt)
    database.flush()
    receipt = add_receipt(
        database,
        kind=OperationKind.VEGETATIVE_LOT_TO_PROPAGATION_ATTEMPT,
        vegetative_lot_id=lot.id,
        propagation_attempt_id=attempt.id,
        adjustment_mode=payload.source_adjustment.mode,
        before_lifecycle=before_lifecycle,
        before_quantity=before_quantity,
        after_lifecycle=lot.lifecycle,
        after_quantity=group_quantity(lot),
        propagation_snapshot={
            **attempt_snapshot(attempt, lot),
            **cutting_source_snapshot(lot, lot),
        },
    )
    return lot, attempt, receipt


def fast_create(
    database: Session, payload: FastCreate
) -> tuple[VegetativeLot, PropagationAttempt, OperationReceipt]:
    lot = create_lot(database, payload.vegetative_lot)
    setup = payload.propagation_attempt
    if "started_on" not in setup.model_fields_set:
        setup = setup.model_copy(update={"started_on": payload.vegetative_lot.taken_on})
    return start_attempt(
        database,
        lot.id,
        AttemptCreate(
            propagation_attempt=setup,
            source_adjustment=payload.source_adjustment,
        ),
    )


def _offspring_exists(database: Session, attempt_id: UUID) -> bool:
    return any(
        database.scalar(
            select(
                select(model.id)
                .where(
                    model.originating_propagation_attempt_id == attempt_id,
                    model.lifecycle != "reversed",
                )
                .exists()
            )
        )
        for model in (Plant, PlantGroup)
    )


def update_attempt(
    database: Session, attempt_id: UUID, payload: PropagationAttemptUpdate
) -> PropagationAttempt:
    attempt = require_record(database, PropagationAttempt, attempt_id, lock=True)
    _check_revision(attempt, payload.expected_updated_at)
    if attempt.lifecycle == "reversed":
        raise PropagationConflictError("attempt_reversed", "A reversed attempt is historical")
    if payload.lifecycle == "failed" and _offspring_exists(database, attempt.id):
        raise PropagationConflictError(
            "attempt_has_descendants",
            "An attempt with established descendants cannot be marked failed",
        )
    if payload.location_id != attempt.location_id:
        require_location_for_scope(
            database, payload.location_id, LocationUsageScope.PROPAGATION_ATTEMPTS
        )
    if payload.quantity is not None and not payload.quantity.is_approximate:
        maximum = database.scalar(
            select(func.max(RootingObservation.rooted_count)).where(
                RootingObservation.propagation_attempt_id == attempt.id
            )
        )
        if maximum is not None and maximum > payload.quantity.value:
            raise PropagationConflictError(
                "observed_count_exceeds_quantity", "An observation exceeds the exact starting count"
            )
    for key, value in {
        **_setup_values(payload),
        **date_values("ended_on", payload.ended_on),
    }.items():
        setattr(attempt, key, value)
    database.flush()
    return attempt


def save_observation(
    database: Session,
    attempt_id: UUID,
    payload: RootingObservationWrite,
    observation_id: UUID | None = None,
) -> RootingObservation:
    attempt = require_record(database, PropagationAttempt, attempt_id, lock=True)
    if attempt.lifecycle == "reversed":
        raise PropagationConflictError("attempt_reversed", "A reversed attempt is historical")
    if (
        payload.rooted_count is not None
        and attempt.quantity_is_approximate is False
        and attempt.quantity_value is not None
        and payload.rooted_count > attempt.quantity_value
    ):
        raise PropagationConflictError(
            "observed_count_exceeds_quantity", "Observation exceeds the exact starting count"
        )
    observation = (
        RootingObservation(propagation_attempt_id=attempt_id)
        if observation_id is None
        else require_observation(database, attempt_id, observation_id)
    )
    for key, value in {
        **payload.model_dump(exclude={"observed_on"}),
        **date_values("observed_on", payload.observed_on),
    }.items():
        setattr(observation, key, value)
    database.add(observation)
    database.flush()
    return observation


def require_observation(
    database: Session, attempt_id: UUID, observation_id: UUID
) -> RootingObservation:
    observation = require_record(database, RootingObservation, observation_id)
    if observation.propagation_attempt_id != attempt_id:
        raise PropagationNotFoundError("observation_not_found", "Rooting observation not found")
    return observation


def _exact_established_count(database: Session, attempt_id: UUID) -> int:
    groups = select(PlantGroup.id).where(
        PlantGroup.originating_propagation_attempt_id == attempt_id,
        PlantGroup.lifecycle != "reversed",
    )
    individual_count = (
        database.scalar(
            select(func.count())
            .select_from(Plant)
            .where(
                (Plant.originating_propagation_attempt_id == attempt_id)
                | Plant.originating_plant_group_id.in_(groups),
                Plant.lifecycle.not_in(("reversed", "reintegrated")),
            )
        )
        or 0
    )
    group_count = (
        database.scalar(
            select(func.sum(PlantGroup.quantity_value)).where(
                PlantGroup.id.in_(groups),
                PlantGroup.quantity_is_approximate.is_(False),
            )
        )
        or 0
    )
    return individual_count + group_count


def establish(
    database: Session, attempt_id: UUID, payload: EstablishPlant
) -> tuple[Plant | PlantGroup, OperationReceipt]:
    lock_lineage_writes(database)
    attempt = require_record(database, PropagationAttempt, attempt_id, lock=True)
    lot = require_record(database, VegetativeLot, attempt.vegetative_lot_id)
    if attempt.lifecycle != "active" or attempt.rooted_count == 0:
        raise PropagationConflictError(
            "attempt_cannot_establish",
            "Establishment requires an active attempt without a recorded zero rooted count",
        )
    if isinstance(payload, EstablishPlantGroup):
        count = (
            payload.quantity.value
            if payload.quantity and not payload.quantity.is_approximate
            else None
        )
    else:
        count = 1
    if (
        attempt.rooted_count is not None
        and count is not None
        and (count + _exact_established_count(database, attempt.id) > attempt.rooted_count)
    ):
        raise PropagationConflictError(
            "rooted_count_exceeded",
            "Establishment exceeds the recorded number of rooted cuttings",
        )
    before_lifecycle = attempt.lifecycle
    values = {
        **payload.model_dump(exclude={"resulting_attempt_lifecycle", "quantity"}),
        "botanical_identity_id": lot.botanical_identity_id,
    }
    result: Plant | PlantGroup
    if isinstance(payload, EstablishPlantGroup):
        result = create_plant_group(
            database,
            PlantGroupCreate(
                **values, quantity=payload.quantity.model_dump() if payload.quantity else None
            ),
            propagation_attempt_id=attempt.id,
        )
        kind = OperationKind.PROPAGATION_ATTEMPT_TO_PLANT_GROUP
    else:
        result = create_plant(database, PlantCreate(**values), propagation_attempt_id=attempt.id)
        kind = OperationKind.PROPAGATION_ATTEMPT_TO_PLANT
    attempt.lifecycle = payload.resulting_attempt_lifecycle
    database.flush()
    receipt = add_receipt(
        database,
        kind=kind,
        propagation_attempt_id=attempt.id,
        source_vegetative_lot_id=lot.id,
        plant_id=result.id if isinstance(result, Plant) else None,
        plant_group_id=result.id if isinstance(result, PlantGroup) else None,
        before_lifecycle=before_lifecycle,
        before_quantity=group_quantity(attempt),
        after_lifecycle=attempt.lifecycle,
        after_quantity=group_quantity(attempt),
        propagation_snapshot={**result_snapshot(result), **cutting_source_snapshot(attempt, lot)},
    )
    return result, receipt
