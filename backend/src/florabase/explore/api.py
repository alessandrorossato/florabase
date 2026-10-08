from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from florabase.auth.dependencies import AuthenticatedActor, require_authenticated_actor
from florabase.db.session import get_database_session
from florabase.explore import service
from florabase.explore.schemas import (
    RepresentationScope,
    RepresentedIdentity,
    RepresentedIdentityPage,
)

router = APIRouter(prefix="/explore/species-distribution/identities", tags=["explore"])
Database = Annotated[Session, Depends(get_database_session)]
Reader = Annotated[AuthenticatedActor, Depends(require_authenticated_actor)]


@router.get("", response_model=RepresentedIdentityPage, operation_id="listRepresentedIdentities")
def list_all(
    _actor: Reader,
    database: Database,
    q: Annotated[str, Query(max_length=200)] = "",
    scope: RepresentationScope = "all",
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> RepresentedIdentityPage:
    return service.list_identities(database, q=q, scope=scope, offset=offset, limit=limit)


@router.get(
    "/{identity_id}", response_model=RepresentedIdentity, operation_id="getRepresentedIdentity"
)
def read(
    identity_id: UUID, _actor: Reader, database: Database, scope: RepresentationScope = "all"
) -> RepresentedIdentity:
    result = service.get_identity(database, identity_id, scope)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "represented_identity_not_found",
                "message": "Identity is missing or no longer represented in the collection",
            },
        )
    return result
