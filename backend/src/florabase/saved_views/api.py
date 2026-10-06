from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
)
from florabase.db.session import get_database_session
from florabase.saved_views import service
from florabase.saved_views.model import SavedView
from florabase.saved_views.schemas import SavedViewCreate, SavedViewResponse, SavedViewUpdate
from florabase.saved_views.state import SavedViewSurface

router = APIRouter(prefix="/saved-views", tags=["saved-views"])
Database = Annotated[Session, Depends(get_database_session)]
Reader = Annotated[AuthenticatedActor, Depends(require_authenticated_actor)]
Writer = Annotated[AuthenticatedActor, Depends(require_csrf)]


def _require(database: Session, owner_id: UUID, view_id: UUID) -> SavedView:
    record = service.get_view(database, owner_id, view_id)
    if record is None:
        raise HTTPException(
            404, {"code": "saved_view_not_found", "message": "Saved View not found"}
        )
    return record


def _conflict(error: service.SavedViewConflictError) -> HTTPException:
    return HTTPException(409, {"code": "saved_view_name_conflict", "message": str(error)})


@router.get("", response_model=list[SavedViewResponse], operation_id="listSavedViews")
def list_all(
    actor: Reader,
    database: Database,
    surface: SavedViewSurface | None = None,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
) -> list[SavedViewResponse]:
    return [
        SavedViewResponse.from_model(view)
        for view in service.list_views(database, actor.user_id, surface, offset)
    ]


@router.post("", response_model=SavedViewResponse, status_code=201, operation_id="createSavedView")
def create(payload: SavedViewCreate, actor: Writer, database: Database) -> SavedViewResponse:
    try:
        return SavedViewResponse.from_model(service.create_view(database, actor.user_id, payload))
    except service.SavedViewConflictError as exc:
        raise _conflict(exc) from exc


@router.patch("/{view_id}", response_model=SavedViewResponse, operation_id="updateSavedView")
def update(
    view_id: UUID, payload: SavedViewUpdate, actor: Writer, database: Database
) -> SavedViewResponse:
    record = _require(database, actor.user_id, view_id)
    try:
        return SavedViewResponse.from_model(service.update_view(database, record, payload))
    except service.SavedViewConflictError as exc:
        raise _conflict(exc) from exc
    except ValueError as exc:
        raise HTTPException(422, {"code": "invalid_saved_view_state", "message": str(exc)}) from exc


@router.delete("/{view_id}", status_code=204, operation_id="deleteSavedView")
def delete(view_id: UUID, actor: Writer, database: Database) -> Response:
    database.delete(_require(database, actor.user_id, view_id))
    database.flush()
    return Response(status_code=204)
