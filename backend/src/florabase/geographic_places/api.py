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
from florabase.geographic_places.model import GeographicPlace
from florabase.geographic_places.schemas import (
    GeographicPlaceCreate,
    GeographicPlaceResponse,
    GeographicPlaceUpdate,
)
from florabase.geographic_places.service import (
    GeographicPlaceHierarchyError,
    GeographicPlaceNotFoundError,
    create_geographic_place,
    display_path,
    get_geographic_place,
    list_geographic_places,
    set_geographic_place_retired,
    update_geographic_place,
)

router = APIRouter(prefix="/geographic-places", tags=["geographic-places"])


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "geographic_place_not_found", "message": "Geographic place not found"},
    )


def _conflict(error: GeographicPlaceHierarchyError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": error.code, "message": error.message},
    )


def _require_place(database: Session, place_id: UUID) -> GeographicPlace:
    place = get_geographic_place(database, place_id)
    if place is None:
        raise _not_found()
    return place


def _response(database: Session, place: GeographicPlace) -> GeographicPlaceResponse:
    places = list_geographic_places(database)
    return GeographicPlaceResponse.from_model(place, display_path=display_path(place, places))


@router.get("", response_model=list[GeographicPlaceResponse], operation_id="listGeographicPlaces")
def list_all(
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> list[GeographicPlaceResponse]:
    places = list_geographic_places(database)
    responses = [
        GeographicPlaceResponse.from_model(place, display_path=display_path(place, places))
        for place in places
    ]
    return sorted(
        responses,
        key=lambda item: (item.retired_at is not None, item.display_path.casefold(), item.id),
    )


@router.post(
    "",
    response_model=GeographicPlaceResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createGeographicPlace",
)
def create(
    payload: GeographicPlaceCreate,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> GeographicPlaceResponse:
    require_owner(actor)
    try:
        place = create_geographic_place(database, payload)
    except GeographicPlaceHierarchyError as error:
        raise _conflict(error) from error
    response.headers["Location"] = f"/api/v1/geographic-places/{place.id}"
    return _response(database, place)


@router.get(
    "/{place_id}", response_model=GeographicPlaceResponse, operation_id="getGeographicPlace"
)
def read(
    place_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> GeographicPlaceResponse:
    return _response(database, _require_place(database, place_id))


@router.put(
    "/{place_id}", response_model=GeographicPlaceResponse, operation_id="updateGeographicPlace"
)
def update(
    place_id: UUID,
    payload: GeographicPlaceUpdate,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> GeographicPlaceResponse:
    require_owner(actor)
    try:
        place = update_geographic_place(database, place_id, payload)
    except GeographicPlaceNotFoundError as error:
        raise _not_found() from error
    except GeographicPlaceHierarchyError as error:
        raise _conflict(error) from error
    return _response(database, place)


def _set_retired(database: Session, place_id: UUID, *, retired: bool) -> GeographicPlaceResponse:
    try:
        place = set_geographic_place_retired(database, place_id, retired=retired)
    except GeographicPlaceNotFoundError as error:
        raise _not_found() from error
    except GeographicPlaceHierarchyError as error:
        raise _conflict(error) from error
    return _response(database, place)


@router.post(
    "/{place_id}/retire",
    response_model=GeographicPlaceResponse,
    operation_id="retireGeographicPlace",
)
def retire(
    place_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> GeographicPlaceResponse:
    require_owner(actor)
    return _set_retired(database, place_id, retired=True)


@router.post(
    "/{place_id}/reactivate",
    response_model=GeographicPlaceResponse,
    operation_id="reactivateGeographicPlace",
)
def reactivate(
    place_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> GeographicPlaceResponse:
    require_owner(actor)
    return _set_retired(database, place_id, retired=False)
