from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from florabase.auth.dependencies import AuthenticatedActor, require_authenticated_actor
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.db.session import get_database_session
from florabase.lineage.schemas import (
    AncestryChildren,
    AncestryResponse,
    IdentityLineageGraph,
    LineageKind,
)
from florabase.lineage.service import (
    MAX_CHILDREN_PAGE,
    MAX_IDENTITY_GRAPH,
    LineageCycleError,
    LineageKey,
    ancestry,
    children,
    exists,
    identity_graph,
)

router = APIRouter(prefix="/lineage", tags=["lineage"])

Limit = Annotated[int, Query(ge=1, le=MAX_CHILDREN_PAGE)]


def _subject(database: Session, kind: LineageKind, item_id: UUID) -> LineageKey:
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


@router.get(
    "/identities/{identity_id}/graph",
    response_model=IdentityLineageGraph,
    operation_id="getIdentityLineageGraph",
)
def read_identity_graph(
    identity_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
    limit: Annotated[int, Query(ge=1, le=MAX_IDENTITY_GRAPH)] = MAX_IDENTITY_GRAPH,
) -> IdentityLineageGraph:
    identity = database.get(BotanicalIdentity, identity_id)
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "botanical_identity_not_found",
                "message": "Botanical identity not found",
            },
        )
    return identity_graph(database, identity, limit=limit)


@router.get("/{kind}/{item_id}", response_model=AncestryResponse, operation_id="getAncestry")
def read_ancestry(
    kind: LineageKind,
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
    kind: LineageKind,
    item_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Limit = 25,
) -> AncestryChildren:
    return children(database, _subject(database, kind, item_id), offset=offset, limit=limit)
