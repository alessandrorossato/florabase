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
from florabase.events.schemas import (
    EventResponse,
    PlantExtractionResponse,
    PlantGroupTransferResponse,
    PlantReintegrationResponse,
    PlantTransferResponse,
    TransferCreate,
)
from florabase.events.service import (
    EventDomainConflictError,
    EventReferenceNotFoundError,
    event_responses,
    get_event,
    transfer_target,
)
from florabase.lineage.schemas import LineageResponse
from florabase.lineage.service import LineageCycleError, LineageKey, lineage
from florabase.plants.schemas import (
    PlantCreate,
    PlantExtractionCreate,
    PlantGroupCreate,
    PlantGroupResponse,
    PlantGroupUpdate,
    PlantReintegrationCreate,
    PlantReintegrationEligibility,
    PlantResponse,
    PlantUpdate,
    RetainedObservation,
)
from florabase.plants.service import (
    PlantDomainConflictError,
    PlantGroupProjection,
    PlantProjection,
    PlantReferenceNotFoundError,
    create_plant,
    create_plant_group,
    evaluate_reintegration,
    extract_plant,
    get_plant,
    get_plant_group,
    list_plant_groups,
    list_plants,
    plant_group_responses,
    plant_responses,
    reintegrate_plant,
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


def _event_response(database: Session, event_id: UUID) -> EventResponse:
    projection = get_event(database, event_id)
    if projection is None:
        raise RuntimeError("Newly created Event could not be read")
    return event_responses(database, [projection])[0]


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
    except PlantDomainConflictError as error:
        raise _domain_conflict(error) from error
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


@plants_router.get(
    "/{plant_id}/reintegration",
    response_model=PlantReintegrationEligibility,
    operation_id="getPlantReintegrationEligibility",
)
def read_plant_reintegration_eligibility(
    plant_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> PlantReintegrationEligibility:
    try:
        evaluation = evaluate_reintegration(database, plant_id)
    except PlantReferenceNotFoundError as error:
        raise _reference_not_found(error) from error
    plant = _plant_response(database, plant_id)
    return PlantReintegrationEligibility(
        status=evaluation.status,
        operation_receipt_id=evaluation.receipt.id if evaluation.receipt else None,
        source_plant_group=plant.originating_plant_group,
        reasons=list(evaluation.reasons),
        retained_observations=[
            RetainedObservation.model_validate(
                {
                    "id": event.id,
                    "kind": event.kind,
                    "occurred_on": (
                        {
                            "precision": event.occurred_on_precision,
                            "year": event.occurred_on_year,
                            "month": event.occurred_on_month,
                            "day": event.occurred_on_day,
                        }
                        if event.occurred_on_precision
                        else None
                    ),
                    "notes": event.notes,
                }
            )
            for event in evaluation.retained_observations
        ],
    )


@plants_router.post(
    "/{plant_id}/reintegrate",
    response_model=PlantReintegrationResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="reintegratePlant",
)
def reintegrate_one_plant(
    plant_id: UUID,
    payload: PlantReintegrationCreate,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> PlantReintegrationResponse:
    require_owner(actor)
    try:
        plant, plant_group, event, _receipt = reintegrate_plant(
            database,
            plant_id,
            confirm_retained_observations=payload.confirm_retained_observations,
        )
    except PlantDomainConflictError as error:
        raise _domain_conflict(error) from error
    except PlantReferenceNotFoundError as error:
        raise _reference_not_found(error) from error
    response.headers["Location"] = f"/api/v1/events/{event.id}"
    return PlantReintegrationResponse(
        plant=_plant_response(database, plant.id),
        plant_group=_plant_group_response(database, plant_group.id),
        event=_event_response(database, event.id),
    )


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
    except PlantDomainConflictError as error:
        raise _domain_conflict(error) from error
    except PlantReferenceNotFoundError as error:
        raise _reference_not_found(error) from error
    return _plant_response(database, plant_id)


@plants_router.post(
    "/{plant_id}/transfer",
    response_model=PlantTransferResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="transferPlant",
)
def transfer_one_plant(
    plant_id: UUID,
    payload: TransferCreate,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> PlantTransferResponse:
    require_owner(actor)
    try:
        event, _target = transfer_target(database, "plant", plant_id, payload)
    except EventReferenceNotFoundError as error:
        raise _not_found(error.code, error.message) from error
    except EventDomainConflictError as error:
        raise _domain_conflict(PlantDomainConflictError(error.code, error.message)) from error
    response.headers["Location"] = f"/api/v1/events/{event.id}"
    return PlantTransferResponse(
        plant=_plant_response(database, plant_id),
        event=_event_response(database, event.id),
    )


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
    except PlantDomainConflictError as error:
        raise _domain_conflict(error) from error
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
        plant, plant_group, event = extract_plant(database, plant_group_id, payload)
    except PlantDomainConflictError as error:
        raise _domain_conflict(error) from error
    except PlantReferenceNotFoundError as error:
        raise _reference_not_found(error) from error
    response.headers["Location"] = f"/api/v1/plants/{plant.id}"
    return PlantExtractionResponse(
        plant=_plant_response(database, plant.id),
        plant_group=_plant_group_response(database, plant_group.id),
        event=_event_response(database, event.id),
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
    except PlantDomainConflictError as error:
        raise _domain_conflict(error) from error
    except PlantReferenceNotFoundError as error:
        raise _reference_not_found(error) from error
    return _plant_group_response(database, plant_group_id)


@plant_groups_router.post(
    "/{plant_group_id}/transfer",
    response_model=PlantGroupTransferResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="transferPlantGroup",
)
def transfer_one_plant_group(
    plant_group_id: UUID,
    payload: TransferCreate,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> PlantGroupTransferResponse:
    require_owner(actor)
    try:
        event, _target = transfer_target(database, "plant_group", plant_group_id, payload)
    except EventReferenceNotFoundError as error:
        raise _not_found(error.code, error.message) from error
    except EventDomainConflictError as error:
        raise _domain_conflict(PlantDomainConflictError(error.code, error.message)) from error
    response.headers["Location"] = f"/api/v1/events/{event.id}"
    return PlantGroupTransferResponse(
        plant_group=_plant_group_response(database, plant_group_id),
        event=_event_response(database, event.id),
    )
