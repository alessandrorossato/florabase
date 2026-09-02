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
from florabase.events.schemas import EventCreate, EventResponse, EventUpdate
from florabase.events.service import (
    EventDomainConflictError,
    EventProjection,
    EventReferenceNotFoundError,
    TargetType,
    create_event,
    delete_event,
    event_responses,
    get_event,
    list_events,
    update_event,
)

plants_events_router = APIRouter(prefix="/plants", tags=["events"])
plant_groups_events_router = APIRouter(prefix="/plant-groups", tags=["events"])
events_router = APIRouter(prefix="/events", tags=["events"])


def _not_found(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=404, detail={"code": code, "message": message})


def _translate(error: EventReferenceNotFoundError | EventDomainConflictError) -> HTTPException:
    code = 404 if isinstance(error, EventReferenceNotFoundError) else 409
    return HTTPException(status_code=code, detail={"code": error.code, "message": error.message})


def _require_event(database: Session, event_id: UUID) -> EventProjection:
    projection = get_event(database, event_id)
    if projection is None:
        raise _not_found("event_not_found", "Event not found")
    return projection


def _event_response(database: Session, event_id: UUID) -> EventResponse:
    return event_responses(database, [_require_event(database, event_id)])[0]


def _list_target_events(
    database: Session, target_type: TargetType, target_id: UUID
) -> list[EventResponse]:
    try:
        return event_responses(database, list_events(database, target_type, target_id))
    except EventReferenceNotFoundError as error:
        raise _translate(error) from error


def _create_target_event(
    database: Session,
    target_type: TargetType,
    target_id: UUID,
    payload: EventCreate,
    response: Response,
) -> EventResponse:
    try:
        event = create_event(database, target_type, target_id, payload)
    except (EventReferenceNotFoundError, EventDomainConflictError) as error:
        raise _translate(error) from error
    response.headers["Location"] = f"/api/v1/events/{event.id}"
    return _event_response(database, event.id)


@plants_events_router.get(
    "/{plant_id}/events", response_model=list[EventResponse], operation_id="listPlantEvents"
)
def list_plant_events(
    plant_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> list[EventResponse]:
    return _list_target_events(database, "plant", plant_id)


@plants_events_router.post(
    "/{plant_id}/events",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createPlantEvent",
)
def create_plant_event(
    plant_id: UUID,
    payload: EventCreate,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> EventResponse:
    require_owner(actor)
    return _create_target_event(database, "plant", plant_id, payload, response)


@plant_groups_events_router.get(
    "/{plant_group_id}/events",
    response_model=list[EventResponse],
    operation_id="listPlantGroupEvents",
)
def list_plant_group_events(
    plant_group_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> list[EventResponse]:
    return _list_target_events(database, "plant_group", plant_group_id)


@plant_groups_events_router.post(
    "/{plant_group_id}/events",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createPlantGroupEvent",
)
def create_plant_group_event(
    plant_group_id: UUID,
    payload: EventCreate,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> EventResponse:
    require_owner(actor)
    return _create_target_event(database, "plant_group", plant_group_id, payload, response)


@events_router.get("/{event_id}", response_model=EventResponse, operation_id="getEvent")
def read_event(
    event_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> EventResponse:
    return _event_response(database, event_id)


@events_router.put("/{event_id}", response_model=EventResponse, operation_id="updateEvent")
def update_one_event(
    event_id: UUID,
    payload: EventUpdate,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> EventResponse:
    require_owner(actor)
    projection = _require_event(database, event_id)
    try:
        update_event(database, projection.event, payload)
    except EventReferenceNotFoundError as error:
        raise _translate(error) from error
    return _event_response(database, event_id)


@events_router.delete(
    "/{event_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="deleteEvent"
)
def delete_one_event(
    event_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> Response:
    require_owner(actor)
    delete_event(database, _require_event(database, event_id).event)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
