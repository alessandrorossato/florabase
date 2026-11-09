from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, aliased

from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
    require_owner,
)
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.cuttings import service
from florabase.cuttings.model import (
    AttemptLifecycle,
    LotLifecycle,
    MaterialType,
    PropagationAttempt,
    RootingObservation,
    SourceKind,
    VegetativeLot,
)
from florabase.cuttings.schemas import (
    AttemptCreate,
    AttemptTransitionResponse,
    CuttingPropagationSummary,
    CuttingQuantity,
    EstablishedCutting,
    EstablishmentResponse,
    EstablishPlant,
    EstablishPlantGroup,
    FastCreate,
    PropagationAttemptDetail,
    PropagationAttemptResponse,
    PropagationAttemptUpdate,
    RootingObservationResponse,
    RootingObservationWrite,
    VegetativeLotCreate,
    VegetativeLotDetail,
    VegetativeLotResponse,
    VegetativeLotUpdate,
)
from florabase.db.session import get_database_session
from florabase.lineage.schemas import LineageResponse
from florabase.lineage.service import LineageCycleError, lineage
from florabase.locations.service import LocationIntegrityError, LocationNotFoundError
from florabase.plants.model import Plant, PlantGroup
from florabase.plants.service import PlantDomainConflictError, PlantReferenceNotFoundError
from florabase.propagation.reversal import ResultType, evaluate, reverse
from florabase.propagation.reversal_schemas import (
    PropagationReversalCreate,
    PropagationReversalEligibility,
)
from florabase.propagation.service import PropagationConflictError, PropagationNotFoundError
from florabase.reversals.model import OperationKind, OperationReceipt

router = APIRouter(tags=["cuttings"])
Database = Annotated[Session, Depends(get_database_session, scope="function")]
Reader = Annotated[AuthenticatedActor, Depends(require_authenticated_actor)]
Offset = Annotated[int, Query(ge=0, le=100_000)]
Limit = Annotated[int, Query(ge=1, le=100)]
Search = Annotated[str | None, Query(max_length=200)]


def _owner(actor: Annotated[AuthenticatedActor, Depends(require_csrf)]) -> None:
    require_owner(actor)


Writer = Annotated[None, Depends(_owner)]


@contextmanager
def _domain_errors() -> Iterator[None]:
    try:
        yield
    except (PropagationNotFoundError, PlantReferenceNotFoundError) as error:
        raise HTTPException(404, detail={"code": error.code, "message": error.message}) from error
    except LocationNotFoundError as error:
        raise HTTPException(
            404, detail={"code": "location_not_found", "message": "Location not found"}
        ) from error
    except (
        LineageCycleError,
        LocationIntegrityError,
        PropagationConflictError,
        PlantDomainConflictError,
    ) as error:
        raise HTTPException(409, detail={"code": error.code, "message": error.message}) from error
    except IntegrityError as error:
        if getattr(error.orig, "sqlstate", None) != "23503":
            raise
        raise HTTPException(
            409,
            detail={
                "code": "cutting_reference_conflict",
                "message": "A linked collection record prevents this change",
            },
        ) from error
    except OperationalError as error:
        if getattr(error.orig, "sqlstate", None) not in {"40001", "40P01", "55P03"}:
            raise
        raise HTTPException(
            409,
            detail={
                "code": "cutting_concurrency_conflict",
                "message": "Concurrent work conflicted. Refresh and retry.",
            },
        ) from error


@router.get("/vegetative-lots", operation_id="listVegetativeLots")
def list_lots(
    _actor: Reader,
    database: Database,
    q: Search = None,
    material_type: MaterialType | None = None,
    source_kind: SourceKind | None = None,
    lifecycle: LotLifecycle | None = None,
    botanical_identity_id: UUID | None = None,
    mother_plant_id: UUID | None = None,
    mother_plant_group_id: UUID | None = None,
    location_id: UUID | None = None,
    has_known_mother: bool | None = None,
    offset: Offset = 0,
    limit: Limit = 50,
) -> list[VegetativeLotResponse]:
    statement = select(VegetativeLot)
    for column, value in (
        (VegetativeLot.material_type, material_type),
        (VegetativeLot.source_kind, source_kind),
        (VegetativeLot.lifecycle, lifecycle),
        (VegetativeLot.botanical_identity_id, botanical_identity_id),
        (VegetativeLot.mother_plant_id, mother_plant_id),
        (VegetativeLot.mother_plant_group_id, mother_plant_group_id),
        (VegetativeLot.location_id, location_id),
    ):
        if value is not None:
            statement = statement.where(column == value)
    if has_known_mother is not None:
        known = or_(
            VegetativeLot.mother_plant_id.is_not(None),
            VegetativeLot.mother_plant_group_id.is_not(None),
        )
        statement = statement.where(known if has_known_mother else ~known)
    if q and q.strip():
        mother, group = aliased(Plant), aliased(PlantGroup)
        needle = q.strip()
        statement = (
            statement.join(
                BotanicalIdentity, BotanicalIdentity.id == VegetativeLot.botanical_identity_id
            )
            .outerjoin(mother, mother.id == VegetativeLot.mother_plant_id)
            .outerjoin(group, group.id == VegetativeLot.mother_plant_group_id)
            .where(
                or_(
                    *(
                        column.icontains(needle, autoescape=True)
                        for column in (
                            VegetativeLot.label,
                            BotanicalIdentity.scientific_name,
                            BotanicalIdentity.common_name,
                            BotanicalIdentity.cultivar_name,
                            mother.label,
                            group.label,
                        )
                    )
                )
            )
        )
    return [
        service.lot_response(row)
        for row in database.scalars(
            statement.order_by(VegetativeLot.id.desc()).offset(offset).limit(limit)
        )
    ]


@router.get("/propagation-attempts", operation_id="listPropagationAttempts")
def list_attempts(
    _actor: Reader,
    database: Database,
    q: Search = None,
    vegetative_lot_id: UUID | None = None,
    lifecycle: AttemptLifecycle | None = None,
    botanical_identity_id: UUID | None = None,
    mother_plant_id: UUID | None = None,
    mother_plant_group_id: UUID | None = None,
    location_id: UUID | None = None,
    offset: Offset = 0,
    limit: Limit = 50,
) -> list[PropagationAttemptResponse]:
    statement = select(PropagationAttempt).join(
        VegetativeLot, VegetativeLot.id == PropagationAttempt.vegetative_lot_id
    )
    for column, value in (
        (PropagationAttempt.vegetative_lot_id, vegetative_lot_id),
        (PropagationAttempt.lifecycle, lifecycle),
        (PropagationAttempt.location_id, location_id),
        (VegetativeLot.botanical_identity_id, botanical_identity_id),
        (VegetativeLot.mother_plant_id, mother_plant_id),
        (VegetativeLot.mother_plant_group_id, mother_plant_group_id),
    ):
        if value is not None:
            statement = statement.where(column == value)
    if q and q.strip():
        needle = q.strip()
        statement = statement.join(
            BotanicalIdentity, BotanicalIdentity.id == VegetativeLot.botanical_identity_id
        ).where(
            or_(
                *(
                    column.icontains(needle, autoescape=True)
                    for column in (
                        PropagationAttempt.label,
                        PropagationAttempt.substrate,
                        VegetativeLot.label,
                        BotanicalIdentity.scientific_name,
                        BotanicalIdentity.common_name,
                        BotanicalIdentity.cultivar_name,
                    )
                )
            )
        )
    return [
        service.attempt_response(row)
        for row in database.scalars(
            statement.order_by(PropagationAttempt.id.desc()).offset(offset).limit(limit)
        )
    ]


@router.post("/vegetative-lots", status_code=201, operation_id="createVegetativeLot")
def create_lot(
    payload: VegetativeLotCreate, _actor: Writer, database: Database
) -> VegetativeLotResponse:
    with _domain_errors():
        return service.lot_response(service.create_lot(database, payload))


@router.get("/vegetative-lots/{lot_id}", operation_id="getVegetativeLot")
def get_lot(lot_id: UUID, _actor: Reader, database: Database) -> VegetativeLotDetail:
    with _domain_errors():
        lot = service.require_record(database, VegetativeLot, lot_id)
        attempts = database.scalars(
            select(PropagationAttempt)
            .where(PropagationAttempt.vegetative_lot_id == lot_id)
            .order_by(PropagationAttempt.id.desc())
        )
        return VegetativeLotDetail(
            **service.lot_response(lot).model_dump(),
            attempts=[service.attempt_response(attempt) for attempt in attempts],
        )


@router.put("/vegetative-lots/{lot_id}", operation_id="updateVegetativeLot")
def update_lot(
    lot_id: UUID,
    payload: VegetativeLotUpdate,
    _actor: Writer,
    database: Database,
) -> VegetativeLotResponse:
    with _domain_errors():
        return service.lot_response(service.update_lot(database, lot_id, payload))


@router.delete("/vegetative-lots/{lot_id}", status_code=204, operation_id="deleteVegetativeLot")
def delete_lot(lot_id: UUID, _actor: Writer, database: Database) -> Response:
    with _domain_errors():
        service.delete_lot(database, lot_id)
        return Response(status_code=204)


def _transition(
    result: tuple[VegetativeLot, PropagationAttempt, OperationReceipt],
) -> AttemptTransitionResponse:
    lot, attempt, receipt = result
    return AttemptTransitionResponse(
        vegetative_lot=service.lot_response(lot),
        propagation_attempt=service.attempt_response(attempt),
        operation_receipt_id=receipt.id,
    )


@router.post(
    "/propagation-attempts/fast-create", status_code=201, operation_id="fastCreateCuttings"
)
def fast_create(
    payload: FastCreate, _actor: Writer, database: Database
) -> AttemptTransitionResponse:
    with _domain_errors():
        return _transition(service.fast_create(database, payload))


@router.post(
    "/vegetative-lots/{lot_id}/propagation-attempts",
    status_code=201,
    operation_id="startRootingAttempt",
)
def start_attempt(
    lot_id: UUID,
    payload: AttemptCreate,
    _actor: Writer,
    database: Database,
) -> AttemptTransitionResponse:
    with _domain_errors():
        return _transition(service.start_attempt(database, lot_id, payload))


@router.get("/propagation-attempts/{attempt_id}", operation_id="getPropagationAttempt")
def get_attempt(attempt_id: UUID, _actor: Reader, database: Database) -> PropagationAttemptDetail:
    with _domain_errors():
        attempt = service.require_record(database, PropagationAttempt, attempt_id)
        lot = service.require_record(database, VegetativeLot, attempt.vegetative_lot_id)
        observations = database.scalars(
            select(RootingObservation)
            .where(RootingObservation.propagation_attempt_id == attempt.id)
            .order_by(
                RootingObservation.observed_on_year.desc().nulls_last(),
                RootingObservation.observed_on_month.desc().nulls_last(),
                RootingObservation.observed_on_day.desc().nulls_last(),
                RootingObservation.id.desc(),
            )
        )
        return PropagationAttemptDetail(
            **service.attempt_response(attempt).model_dump(),
            vegetative_lot=service.lot_response(lot),
            operation_receipt_id=database.scalar(
                select(OperationReceipt.id).where(
                    OperationReceipt.propagation_attempt_id == attempt.id,
                    OperationReceipt.kind == OperationKind.VEGETATIVE_LOT_TO_PROPAGATION_ATTEMPT,
                )
            ),
            observations=[
                service.observation_response(observation) for observation in observations
            ],
        )


@router.put("/propagation-attempts/{attempt_id}", operation_id="updatePropagationAttempt")
def update_attempt(
    attempt_id: UUID,
    payload: PropagationAttemptUpdate,
    _actor: Writer,
    database: Database,
) -> PropagationAttemptResponse:
    with _domain_errors():
        return service.attempt_response(service.update_attempt(database, attempt_id, payload))


@router.post(
    "/propagation-attempts/{attempt_id}/observations",
    status_code=201,
    operation_id="createRootingObservation",
)
def create_observation(
    attempt_id: UUID,
    payload: RootingObservationWrite,
    _actor: Writer,
    database: Database,
) -> RootingObservationResponse:
    with _domain_errors():
        return service.observation_response(service.save_observation(database, attempt_id, payload))


@router.put(
    "/propagation-attempts/{attempt_id}/observations/{observation_id}",
    operation_id="updateRootingObservation",
)
def update_observation(
    attempt_id: UUID,
    observation_id: UUID,
    payload: RootingObservationWrite,
    _actor: Writer,
    database: Database,
) -> RootingObservationResponse:
    with _domain_errors():
        return service.observation_response(
            service.save_observation(database, attempt_id, payload, observation_id)
        )


@router.delete(
    "/propagation-attempts/{attempt_id}/observations/{observation_id}",
    status_code=204,
    operation_id="deleteRootingObservation",
)
def delete_observation(
    attempt_id: UUID,
    observation_id: UUID,
    _actor: Writer,
    database: Database,
) -> Response:
    with _domain_errors():
        attempt = service.require_record(database, PropagationAttempt, attempt_id, lock=True)
        if attempt.lifecycle == "reversed":
            raise PropagationConflictError("attempt_reversed", "A reversed attempt is historical")
        database.delete(service.require_observation(database, attempt_id, observation_id))
        database.flush()
        return Response(status_code=204)


@router.get("/vegetative-lots/{lot_id}/lineage", operation_id="getVegetativeLotLineage")
def lot_lineage(lot_id: UUID, _actor: Reader, database: Database) -> LineageResponse:
    with _domain_errors():
        service.require_record(database, VegetativeLot, lot_id)
        return lineage(database, ("vegetative_lot", lot_id))


@router.get(
    "/propagation-attempts/{attempt_id}/lineage", operation_id="getPropagationAttemptLineage"
)
def attempt_lineage(attempt_id: UUID, _actor: Reader, database: Database) -> LineageResponse:
    with _domain_errors():
        service.require_record(database, PropagationAttempt, attempt_id)
        return lineage(database, ("propagation_attempt", attempt_id))


def _establish(
    database: Session, attempt_id: UUID, payload: EstablishPlant
) -> EstablishmentResponse:
    with _domain_errors():
        result, receipt = service.establish(database, attempt_id, payload)
        return EstablishmentResponse(
            id=result.id,
            kind="plant" if isinstance(result, Plant) else "plant_group",
            operation_receipt_id=receipt.id,
        )


@router.post(
    "/propagation-attempts/{attempt_id}/plants",
    status_code=201,
    operation_id="establishCuttingPlant",
)
def establish_plant(
    attempt_id: UUID,
    payload: EstablishPlant,
    _actor: Writer,
    database: Database,
) -> EstablishmentResponse:
    return _establish(database, attempt_id, payload)


@router.post(
    "/propagation-attempts/{attempt_id}/plant-groups",
    status_code=201,
    operation_id="establishCuttingPlantGroup",
)
def establish_group(
    attempt_id: UUID,
    payload: EstablishPlantGroup,
    _actor: Writer,
    database: Database,
) -> EstablishmentResponse:
    return _establish(database, attempt_id, payload)


def _cutting_result(database: Session, receipt_id: UUID) -> tuple[ResultType, UUID]:
    receipt = database.get(OperationReceipt, receipt_id)
    if receipt is not None:
        if (
            receipt.kind == OperationKind.VEGETATIVE_LOT_TO_PROPAGATION_ATTEMPT
            and receipt.propagation_attempt_id is not None
        ):
            return "propagation_attempt", receipt.propagation_attempt_id
        if receipt.kind == OperationKind.PROPAGATION_ATTEMPT_TO_PLANT and receipt.plant_id:
            return "plant", receipt.plant_id
        if (
            receipt.kind == OperationKind.PROPAGATION_ATTEMPT_TO_PLANT_GROUP
            and receipt.plant_group_id
        ):
            return "plant_group", receipt.plant_group_id
    raise PropagationNotFoundError("cutting_operation_not_found", "Cutting operation not found")


@router.get(
    "/cutting-operations/{receipt_id}/reversal", operation_id="getCuttingReversalEligibility"
)
def reversal_eligibility(
    receipt_id: UUID,
    _actor: Reader,
    database: Database,
) -> PropagationReversalEligibility:
    with _domain_errors():
        kind, result_id = _cutting_result(database, receipt_id)
        return evaluate(database, kind, result_id, cutting=True).eligibility


@router.post(
    "/cutting-operations/{receipt_id}/reversal",
    status_code=204,
    operation_id="reverseCuttingOperation",
)
def reverse_cutting_operation(
    receipt_id: UUID,
    payload: PropagationReversalCreate,
    _actor: Writer,
    database: Database,
) -> Response:
    with _domain_errors():
        kind, result_id = _cutting_result(database, receipt_id)
        reverse(
            database, kind, result_id, cutting=True, confirm=payload.confirm_retained_observations
        )
        return Response(status_code=204)


@router.get(
    "/propagation-attempts/{attempt_id}/propagation-summary",
    operation_id="getCuttingPropagationSummary",
)
def propagation_summary(
    attempt_id: UUID,
    _actor: Reader,
    database: Database,
) -> CuttingPropagationSummary:
    with _domain_errors():
        attempt = service.require_record(database, PropagationAttempt, attempt_id)
        offspring: list[EstablishedCutting] = []
        for model, receipt_column, kind, operation in (
            (Plant, OperationReceipt.plant_id, "plant", OperationKind.PROPAGATION_ATTEMPT_TO_PLANT),
            (
                PlantGroup,
                OperationReceipt.plant_group_id,
                "plant_group",
                OperationKind.PROPAGATION_ATTEMPT_TO_PLANT_GROUP,
            ),
        ):
            for record, receipt_id in database.execute(
                select(model, OperationReceipt.id)
                .outerjoin(
                    OperationReceipt,
                    (receipt_column == model.id) & (OperationReceipt.kind == operation),
                )
                .where(model.originating_propagation_attempt_id == attempt.id)
                .order_by(model.id)
            ):
                quantity = None
                if isinstance(record, PlantGroup) and record.quantity_value is not None:
                    quantity = CuttingQuantity(
                        value=record.quantity_value,
                        is_approximate=bool(record.quantity_is_approximate),
                    )
                offspring.append(
                    EstablishedCutting(
                        id=record.id,
                        kind=kind,
                        label=record.label,
                        lifecycle=record.lifecycle,
                        quantity=quantity,
                        operation_receipt_id=receipt_id,
                    )
                )
        # Count descendants extracted from rooted groups through the existing explicit links.
        live = [item for item in offspring if item.lifecycle != "reversed"]
        groups = [item for item in live if item.kind == "plant_group"]
        extracted = (
            database.scalar(
                select(func.count())
                .select_from(Plant)
                .where(
                    Plant.originating_plant_group_id.in_([item.id for item in groups]),
                    Plant.lifecycle.not_in(("reversed", "reintegrated")),
                )
            )
            or 0
        )
        return CuttingPropagationSummary(
            attempt_id=attempt.id,
            lifecycle=attempt.lifecycle,
            rooted_count=attempt.rooted_count,
            offspring=offspring,
            exact_descendant_count=extracted
            + sum(
                1
                if item.kind == "plant"
                else item.quantity.value
                if item.quantity and not item.quantity.is_approximate
                else 0
                for item in live
            ),
            approximate_plant_group_count=sum(
                item.quantity is not None and item.quantity.is_approximate for item in groups
            ),
            unknown_plant_group_count=sum(item.quantity is None for item in groups),
        )
