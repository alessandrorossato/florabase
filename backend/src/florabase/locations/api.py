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
from florabase.locations.model import Location
from florabase.locations.schemas import LocationCreate, LocationResponse, LocationUpdate
from florabase.locations.service import (
    LocationHierarchyError,
    LocationIntegrityError,
    LocationNotFoundError,
    create_location,
    delete_location,
    display_path,
    get_location,
    list_locations,
    location_usage,
    set_location_retired,
    update_location,
)

router = APIRouter(prefix="/locations", tags=["locations"])


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "location_not_found", "message": "Location not found"},
    )


def _conflict(error: LocationHierarchyError | LocationIntegrityError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": error.code, "message": error.message},
    )


def _require_location(database: Session, location_id: UUID) -> Location:
    location = get_location(database, location_id)
    if location is None:
        raise _not_found()
    return location


def _response(database: Session, location: Location) -> LocationResponse:
    locations = list_locations(database)
    usage = location_usage(database).get(location.id)
    return LocationResponse.from_model(
        location, display_path=display_path(location, locations), usage=usage
    )


@router.get("", response_model=list[LocationResponse], operation_id="listLocations")
def list_all(
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> list[LocationResponse]:
    locations = list_locations(database)
    usage = location_usage(database)
    responses = [
        LocationResponse.from_model(
            location,
            display_path=display_path(location, locations),
            usage=usage.get(location.id),
        )
        for location in locations
    ]
    return sorted(
        responses,
        key=lambda item: (item.retired_at is not None, item.display_path.casefold(), item.id),
    )


@router.post(
    "",
    response_model=LocationResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createLocation",
)
def create(
    payload: LocationCreate,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> LocationResponse:
    require_owner(actor)
    try:
        location = create_location(database, payload)
    except (LocationHierarchyError, LocationIntegrityError) as error:
        raise _conflict(error) from error
    response.headers["Location"] = f"/api/v1/locations/{location.id}"
    return _response(database, location)


@router.get("/{location_id}", response_model=LocationResponse, operation_id="getLocation")
def read(
    location_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> LocationResponse:
    return _response(database, _require_location(database, location_id))


@router.put("/{location_id}", response_model=LocationResponse, operation_id="updateLocation")
def update(
    location_id: UUID,
    payload: LocationUpdate,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> LocationResponse:
    require_owner(actor)
    try:
        location = update_location(database, location_id, payload)
    except LocationNotFoundError as error:
        raise _not_found() from error
    except (LocationHierarchyError, LocationIntegrityError) as error:
        raise _conflict(error) from error
    return _response(database, location)


@router.delete(
    "/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteLocation",
)
def delete(
    location_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> Response:
    require_owner(actor)
    try:
        delete_location(database, location_id)
    except LocationNotFoundError as error:
        raise _not_found() from error
    except LocationIntegrityError as error:
        raise _conflict(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _set_retired(database: Session, location_id: UUID, *, retired: bool) -> LocationResponse:
    try:
        location = set_location_retired(database, location_id, retired=retired)
    except LocationNotFoundError as error:
        raise _not_found() from error
    except LocationHierarchyError as error:
        raise _conflict(error) from error
    return _response(database, location)


@router.post(
    "/{location_id}/retire", response_model=LocationResponse, operation_id="retireLocation"
)
def retire(
    location_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> LocationResponse:
    require_owner(actor)
    return _set_retired(database, location_id, retired=True)


@router.post(
    "/{location_id}/reactivate",
    response_model=LocationResponse,
    operation_id="reactivateLocation",
)
def reactivate(
    location_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> LocationResponse:
    require_owner(actor)
    return _set_retired(database, location_id, retired=False)
