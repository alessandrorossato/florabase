from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
    require_owner,
)
from florabase.db.session import get_database_session
from florabase.plants.api import _plant_group_response, _plant_response
from florabase.plants.service import (
    PlantDomainConflictError,
    PlantReferenceNotFoundError,
    get_plant,
    plant_responses,
)
from florabase.propagation.reversal import Evaluation, ResultType, evaluate, reverse
from florabase.propagation.reversal_schemas import (
    PlantCreationReversalResponse,
    PlantGroupCreationReversalResponse,
    PropagationReversalCreate,
    PropagationReversalEligibility,
    SowingCreationReversalResponse,
)
from florabase.propagation.schemas import SowingPotOnCreate, SowingPotOnResponse
from florabase.propagation.service import (
    PropagationConflictError,
    PropagationNotFoundError,
    create_plants_from_sowing_batch,
)
from florabase.seed_lots.api import _response as seed_lot_response
from florabase.sowings.api import _response as sowing_response

router = APIRouter(tags=["propagation"])


def _evaluate(
    database: Session,
    kind: ResultType,
    result_id: UUID,
    payload: PropagationReversalCreate | None = None,
) -> Evaluation:
    try:
        return (
            evaluate(database, kind, result_id)
            if payload is None
            else reverse(database, kind, result_id, confirm=payload.confirm_retained_observations)
        )
    except PropagationNotFoundError as error:
        raise HTTPException(404, detail={"code": error.code, "message": error.message}) from error
    except PropagationConflictError as error:
        raise HTTPException(409, detail={"code": error.code, "message": error.message}) from error
    except OperationalError as error:
        if getattr(error.orig, "sqlstate", None) not in {"40001", "40P01", "55P03"}:
            raise
        raise HTTPException(
            409,
            detail={
                "code": "propagation_concurrency_conflict",
                "message": "Concurrent work conflicted. Refresh eligibility and retry.",
            },
        ) from error


@router.get(
    "/sowings/{result_id}/creation-reversal",
    response_model=PropagationReversalEligibility,
    operation_id="getSowingCreationReversalEligibility",
)
def sowing_eligibility(
    result_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
) -> PropagationReversalEligibility:
    return _evaluate(database, "sowing", result_id).eligibility


@router.post(
    "/sowings/{result_id}/reverse-creation",
    response_model=SowingCreationReversalResponse,
    operation_id="reverseSowingCreation",
)
def reverse_sowing_creation(
    result_id: UUID,
    payload: PropagationReversalCreate,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
) -> SowingCreationReversalResponse:
    require_owner(actor)
    evaluation = _evaluate(database, "sowing", result_id, payload)
    assert evaluation.source is not None
    assert evaluation.receipt is not None
    return SowingCreationReversalResponse(
        sowing=sowing_response(database, result_id),
        seed_lot=seed_lot_response(database, evaluation.source.id),
        operation_receipt_id=evaluation.receipt.id,
    )


@router.get(
    "/plants/{result_id}/creation-reversal",
    response_model=PropagationReversalEligibility,
    operation_id="getPlantCreationReversalEligibility",
)
def plant_eligibility(
    result_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
) -> PropagationReversalEligibility:
    return _evaluate(database, "plant", result_id).eligibility


@router.post(
    "/plants/{result_id}/reverse-creation",
    response_model=PlantCreationReversalResponse,
    operation_id="reversePlantCreation",
)
def reverse_plant_creation(
    result_id: UUID,
    payload: PropagationReversalCreate,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
) -> PlantCreationReversalResponse:
    require_owner(actor)
    evaluation = _evaluate(database, "plant", result_id, payload)
    assert evaluation.source is not None
    assert evaluation.receipt is not None
    return PlantCreationReversalResponse(
        plant=_plant_response(database, result_id),
        sowing=sowing_response(database, evaluation.source.id),
        operation_receipt_id=evaluation.receipt.id,
    )


@router.get(
    "/plant-groups/{result_id}/creation-reversal",
    response_model=PropagationReversalEligibility,
    operation_id="getPlantGroupCreationReversalEligibility",
)
def plant_group_eligibility(
    result_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
) -> PropagationReversalEligibility:
    return _evaluate(database, "plant_group", result_id).eligibility


@router.post(
    "/plant-groups/{result_id}/reverse-creation",
    response_model=PlantGroupCreationReversalResponse,
    operation_id="reversePlantGroupCreation",
)
def reverse_plant_group_creation(
    result_id: UUID,
    payload: PropagationReversalCreate,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
) -> PlantGroupCreationReversalResponse:
    require_owner(actor)
    evaluation = _evaluate(database, "plant_group", result_id, payload)
    assert evaluation.source is not None
    assert evaluation.receipt is not None
    return PlantGroupCreationReversalResponse(
        plant_group=_plant_group_response(database, result_id),
        sowing=sowing_response(database, evaluation.source.id),
        operation_receipt_id=evaluation.receipt.id,
    )


@router.post(
    "/sowings/{sowing_id}/pot-on",
    response_model=SowingPotOnResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="potOnSowing",
)
def pot_on_sowing(
    sowing_id: UUID,
    payload: SowingPotOnCreate,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
) -> SowingPotOnResponse:
    require_owner(actor)
    try:
        plants, sowing = create_plants_from_sowing_batch(database, sowing_id, payload)
    except PropagationNotFoundError as error:
        raise HTTPException(404, detail={"code": error.code, "message": error.message}) from error
    except PropagationConflictError as error:
        raise HTTPException(409, detail={"code": error.code, "message": error.message}) from error
    except PlantReferenceNotFoundError as error:
        raise HTTPException(404, detail={"code": error.code, "message": error.message}) from error
    except PlantDomainConflictError as error:
        raise HTTPException(409, detail={"code": error.code, "message": error.message}) from error
    except OperationalError as error:
        if getattr(error.orig, "sqlstate", None) not in {"40001", "40P01", "55P03"}:
            raise
        raise HTTPException(
            409,
            detail={
                "code": "propagation_concurrency_conflict",
                "message": "Concurrent work conflicted. Refresh and retry.",
            },
        ) from error
    projections = []
    for plant in plants:
        projection = get_plant(database, plant.id)
        if projection is None:
            raise RuntimeError("Created Plant could not be projected")
        projections.append(projection)
    return SowingPotOnResponse(
        sowing=sowing_response(database, sowing.id),
        plants=plant_responses(database, projections),
    )
