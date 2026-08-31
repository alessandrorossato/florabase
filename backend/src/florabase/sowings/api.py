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


@router.get("/{sowing_id}", response_model=SowingResponse, operation_id="getSowing")
def read(
    sowing_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> SowingResponse:
    return _response(database, sowing_id)


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
