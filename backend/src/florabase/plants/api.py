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
from florabase.lineage.schemas import LineageResponse
from florabase.lineage.service import LineageCycleError, LineageKey, lineage
from florabase.plants.schemas import (
    PlantCreate,
    PlantExtractionCreate,
    PlantExtractionResponse,
    PlantGroupCreate,
    PlantGroupResponse,
    PlantGroupUpdate,
    PlantResponse,
    PlantUpdate,
)
from florabase.plants.service import (
    PlantDomainConflictError,
    PlantGroupProjection,
    PlantProjection,
    PlantReferenceNotFoundError,
    create_plant,
    create_plant_group,
    extract_plant,
    get_plant,
    get_plant_group,
    list_plant_groups,
    list_plants,
    plant_group_responses,
    plant_responses,
    update_plant,
    update_plant_group,
)

plants_router = APIRouter(prefix="/plants", tags=["plants"])
plant_groups_router = APIRouter(prefix="/plant-groups", tags=["plant-groups"])


def _not_found(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": code, "message": message},
    )


def _reference_not_found(error: PlantReferenceNotFoundError) -> HTTPException:
    return _not_found(error.code, error.message)


def _domain_conflict(error: PlantDomainConflictError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": error.code, "message": error.message},
    )


def _require_plant(database: Session, plant_id: UUID) -> PlantProjection:
    projection = get_plant(database, plant_id)
    if projection is None:
        raise _not_found("plant_not_found", "Plant not found")
    return projection


def _require_plant_group(database: Session, plant_group_id: UUID) -> PlantGroupProjection:
    projection = get_plant_group(database, plant_group_id)
    if projection is None:
        raise _not_found("plant_group_not_found", "PlantGroup not found")
    return projection


def _plant_response(database: Session, plant_id: UUID) -> PlantResponse:
    return plant_responses(database, [_require_plant(database, plant_id)])[0]


def _plant_group_response(database: Session, plant_group_id: UUID) -> PlantGroupResponse:
    return plant_group_responses(database, [_require_plant_group(database, plant_group_id)])[0]


def _lineage_response(database: Session, subject: LineageKey) -> LineageResponse:
    try:
        return lineage(database, subject)
    except LineageCycleError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": error.code, "message": error.message},
        ) from error


@plants_router.get("", response_model=list[PlantResponse], operation_id="listPlants")
def list_all_plants(
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> list[PlantResponse]:
    return plant_responses(database, list_plants(database))


@plants_router.post(
    "",
    response_model=PlantResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createPlant",
)
def create_one_plant(
    payload: PlantCreate,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> PlantResponse:
    require_owner(actor)
    try:
        plant = create_plant(database, payload)
    except PlantReferenceNotFoundError as error:
        raise _reference_not_found(error) from error
    response.headers["Location"] = f"/api/v1/plants/{plant.id}"
    return _plant_response(database, plant.id)


@plants_router.get("/{plant_id}", response_model=PlantResponse, operation_id="getPlant")
def read_plant(
    plant_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> PlantResponse:
    return _plant_response(database, plant_id)


@plants_router.get(
    "/{plant_id}/lineage", response_model=LineageResponse, operation_id="getPlantLineage"
)
def read_plant_lineage(
    plant_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> LineageResponse:
    _require_plant(database, plant_id)
    return _lineage_response(database, ("plant", plant_id))


@plants_router.put("/{plant_id}", response_model=PlantResponse, operation_id="updatePlant")
def update_one_plant(
    plant_id: UUID,
    payload: PlantUpdate,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> PlantResponse:
    require_owner(actor)
    projection = _require_plant(database, plant_id)
    try:
        update_plant(database, projection.plant, payload)
    except PlantReferenceNotFoundError as error:
        raise _reference_not_found(error) from error
    except PlantDomainConflictError as error:
        raise _domain_conflict(error) from error
    return _plant_response(database, plant_id)


@plant_groups_router.get(
    "", response_model=list[PlantGroupResponse], operation_id="listPlantGroups"
)
def list_all_plant_groups(
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> list[PlantGroupResponse]:
    return plant_group_responses(database, list_plant_groups(database))


@plant_groups_router.post(
    "",
    response_model=PlantGroupResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createPlantGroup",
)
def create_one_plant_group(
    payload: PlantGroupCreate,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> PlantGroupResponse:
    require_owner(actor)
    try:
        plant_group = create_plant_group(database, payload)
    except PlantReferenceNotFoundError as error:
        raise _reference_not_found(error) from error
    response.headers["Location"] = f"/api/v1/plant-groups/{plant_group.id}"
    return _plant_group_response(database, plant_group.id)


@plant_groups_router.post(
    "/{plant_group_id}/extract-plant",
    response_model=PlantExtractionResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="extractPlantFromGroup",
)
def extract_one_plant(
    plant_group_id: UUID,
    payload: PlantExtractionCreate,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> PlantExtractionResponse:
    require_owner(actor)
    try:
        plant, plant_group = extract_plant(database, plant_group_id, payload)
    except PlantReferenceNotFoundError as error:
        raise _reference_not_found(error) from error
    except PlantDomainConflictError as error:
        raise _domain_conflict(error) from error
    response.headers["Location"] = f"/api/v1/plants/{plant.id}"
    return PlantExtractionResponse(
        plant=_plant_response(database, plant.id),
        plant_group=_plant_group_response(database, plant_group.id),
    )


@plant_groups_router.get(
    "/{plant_group_id}", response_model=PlantGroupResponse, operation_id="getPlantGroup"
)
def read_plant_group(
    plant_group_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> PlantGroupResponse:
    return _plant_group_response(database, plant_group_id)


@plant_groups_router.get(
    "/{plant_group_id}/lineage",
    response_model=LineageResponse,
    operation_id="getPlantGroupLineage",
)
def read_plant_group_lineage(
    plant_group_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> LineageResponse:
    _require_plant_group(database, plant_group_id)
    return _lineage_response(database, ("plant_group", plant_group_id))


@plant_groups_router.put(
    "/{plant_group_id}", response_model=PlantGroupResponse, operation_id="updatePlantGroup"
)
def update_one_plant_group(
    plant_group_id: UUID,
    payload: PlantGroupUpdate,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> PlantGroupResponse:
    require_owner(actor)
    projection = _require_plant_group(database, plant_group_id)
    try:
        update_plant_group(database, projection.plant_group, payload)
    except PlantReferenceNotFoundError as error:
        raise _reference_not_found(error) from error
    return _plant_group_response(database, plant_group_id)
