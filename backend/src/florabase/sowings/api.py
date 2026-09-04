from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
    require_owner,
)
from florabase.db.session import get_database_session
from florabase.plants.service import (
    PlantReferenceNotFoundError,
    get_plant,
    get_plant_group,
    plant_group_responses,
    plant_responses,
)
from florabase.propagation.schemas import (
    SowingPlantGroupTransitionCreate,
    SowingPlantGroupTransitionResponse,
    SowingPlantTransitionCreate,
    SowingPlantTransitionResponse,
    SowingPropagationSummary,
)
from florabase.propagation.service import (
    PropagationNotFoundError,
    create_plant_from_sowing,
    create_plant_group_from_sowing,
    propagation_summary,
)
from florabase.sowings.schemas import SowingCreate, SowingResponse, SowingUpdate
from florabase.sowings.service import (
    SowingProjection,
    SowingReferenceNotFoundError,
    create_sowing,
    get_sowing,
    list_sowings,
    responses,
    update_sowing,
)

router = APIRouter(prefix="/sowings", tags=["sowings"])


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "sowing_not_found", "message": "Sowing not found"},
    )


def _reference_not_found(error: SowingReferenceNotFoundError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": error.code, "message": error.message},
    )


def _require_sowing(database: Session, sowing_id: UUID) -> SowingProjection:
    projection = get_sowing(database, sowing_id)
    if projection is None:
        raise _not_found()
    return projection


def _response(database: Session, sowing_id: UUID) -> SowingResponse:
    return responses(database, [_require_sowing(database, sowing_id)])[0]


def _propagation_not_found(error: PropagationNotFoundError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": error.code, "message": error.message},
    )


def _plant_reference_not_found(error: PlantReferenceNotFoundError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": error.code, "message": error.message},
    )


@router.get("", response_model=list[SowingResponse], operation_id="listSowings")
def list_all(
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> list[SowingResponse]:
    return responses(database, list_sowings(database))


@router.post(
    "",
    response_model=SowingResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createSowing",
)
def create(
    payload: SowingCreate,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> SowingResponse:
    require_owner(actor)
    try:
        sowing = create_sowing(database, payload)
    except SowingReferenceNotFoundError as error:
        raise _reference_not_found(error) from error
    response.headers["Location"] = f"/api/v1/sowings/{sowing.id}"
    return _response(database, sowing.id)


@router.post(
    "/{sowing_id}/create-plant",
    response_model=SowingPlantTransitionResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createPlantFromSowing",
)
def create_plant_transition(
    sowing_id: UUID,
    payload: SowingPlantTransitionCreate,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> SowingPlantTransitionResponse:
    require_owner(actor)
    try:
        plant, sowing = create_plant_from_sowing(
            database,
            sowing_id,
            payload.plant,
            payload.resulting_sowing_lifecycle.value,
        )
    except PropagationNotFoundError as error:
        raise _propagation_not_found(error) from error
    except PlantReferenceNotFoundError as error:
        raise _plant_reference_not_found(error) from error
    plant_projection = get_plant(database, plant.id)
    if plant_projection is None:
        raise RuntimeError("Created Plant could not be projected")
    response.headers["Location"] = f"/api/v1/plants/{plant.id}"
    return SowingPlantTransitionResponse(
        plant=plant_responses(database, [plant_projection])[0],
        sowing=_response(database, sowing.id),
    )


@router.post(
    "/{sowing_id}/create-plant-group",
    response_model=SowingPlantGroupTransitionResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createPlantGroupFromSowing",
)
def create_plant_group_transition(
    sowing_id: UUID,
    payload: SowingPlantGroupTransitionCreate,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> SowingPlantGroupTransitionResponse:
    require_owner(actor)
    try:
        plant_group, sowing = create_plant_group_from_sowing(
            database,
            sowing_id,
            payload.plant_group,
            payload.resulting_sowing_lifecycle.value,
        )
    except PropagationNotFoundError as error:
        raise _propagation_not_found(error) from error
    except PlantReferenceNotFoundError as error:
        raise _plant_reference_not_found(error) from error
    group_projection = get_plant_group(database, plant_group.id)
    if group_projection is None:
        raise RuntimeError("Created PlantGroup could not be projected")
    response.headers["Location"] = f"/api/v1/plant-groups/{plant_group.id}"
    return SowingPlantGroupTransitionResponse(
        plant_group=plant_group_responses(database, [group_projection])[0],
        sowing=_response(database, sowing.id),
    )


@router.get("/{sowing_id}", response_model=SowingResponse, operation_id="getSowing")
def read(
    sowing_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> SowingResponse:
    return _response(database, sowing_id)


@router.get(
    "/{sowing_id}/propagation-summary",
    response_model=SowingPropagationSummary,
    operation_id="getSowingPropagationSummary",
)
def read_propagation_summary(
    sowing_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> SowingPropagationSummary:
    try:
        return propagation_summary(database, sowing_id)
    except PropagationNotFoundError as error:
        raise _propagation_not_found(error) from error


@router.put("/{sowing_id}", response_model=SowingResponse, operation_id="updateSowing")
def update(
    sowing_id: UUID,
    payload: SowingUpdate,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> SowingResponse:
    require_owner(actor)
    projection = _require_sowing(database, sowing_id)
    try:
        update_sowing(database, projection.sowing, payload)
    except SowingReferenceNotFoundError as error:
        raise _reference_not_found(error) from error
    return _response(database, sowing_id)
