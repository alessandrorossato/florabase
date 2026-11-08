from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from florabase.auth.dependencies import AuthenticatedActor, require_authenticated_actor
from florabase.db.session import get_database_session
from florabase.lineage.schemas import AncestryChildren, AncestryResponse
from florabase.lineage.service import (
    MAX_CHILDREN_PAGE,
    LineageCycleError,
    LineageKey,
    ancestry,
    children,
    exists,
)

router = APIRouter(prefix="/lineage", tags=["lineage"])

Kind = Literal["seed_lot", "sowing", "plant", "plant_group"]
Limit = Annotated[int, Query(ge=1, le=MAX_CHILDREN_PAGE)]


def _subject(database: Session, kind: Kind, item_id: UUID) -> LineageKey:
    if not exists(database, (kind, item_id)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "lineage_record_not_found", "message": "Record not found"},
        )
    return (kind, item_id)


def _conflict(error: LineageCycleError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": error.code, "message": error.message},
    )


@router.get("/{kind}/{item_id}", response_model=AncestryResponse, operation_id="getAncestry")
def read_ancestry(
    kind: Kind,
    item_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
    limit: Limit = 25,
) -> AncestryResponse:
    subject = _subject(database, kind, item_id)
    try:
        return ancestry(database, subject, limit=limit)
    except LineageCycleError as error:
        raise _conflict(error) from error


@router.get(
    "/{kind}/{item_id}/children",
    response_model=AncestryChildren,
    operation_id="getAncestryChildren",
)
def read_children(
    kind: Kind,
    item_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Limit = 25,
) -> AncestryChildren:
    return children(database, _subject(database, kind, item_id), offset=offset, limit=limit)
