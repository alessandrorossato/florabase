from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from florabase.auth.dependencies import AuthenticatedActor, require_authenticated_actor
from florabase.db.session import get_database_session
from florabase.explore import native_ranges, service
from florabase.explore.schemas import (
    CollectionRecordCategory,
    NativeRangeIdentityPage,
    NativeRangeOverview,
    NativeRangeSelection,
    RepresentationScope,
    RepresentedIdentity,
    RepresentedIdentityPage,
    SelectedNativeRanges,
)

router = APIRouter(prefix="/explore", tags=["explore"])
Database = Annotated[Session, Depends(get_database_session)]
Reader = Annotated[AuthenticatedActor, Depends(require_authenticated_actor)]


@router.get(
    "/species-distribution/identities",
    response_model=RepresentedIdentityPage,
    operation_id="listRepresentedIdentities",
)
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
    "/species-distribution/identities/{identity_id}",
    response_model=RepresentedIdentity,
    operation_id="getRepresentedIdentity",
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


@router.get(
    "/native-ranges/identities",
    response_model=NativeRangeIdentityPage,
    operation_id="listNativeRangeIdentities",
)
def native_identities(
    _actor: Reader,
    database: Database,
    q: Annotated[str, Query(max_length=200)] = "",
    scope: RepresentationScope = "all",
    with_range: bool = False,
    record: Annotated[list[CollectionRecordCategory] | None, Query(max_length=5)] = None,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> NativeRangeIdentityPage:
    return native_ranges.list_identities(
        database,
        q=q,
        scope=scope,
        with_range=with_range,
        record=record or (),
        offset=offset,
        limit=limit,
    )


@router.get(
    "/native-ranges/overview",
    response_model=NativeRangeOverview,
    operation_id="getNativeRangeOverview",
)
def native_overview(
    _actor: Reader,
    database: Database,
    q: Annotated[str, Query(max_length=200)] = "",
    scope: RepresentationScope = "all",
    with_range: bool = False,
    record: Annotated[list[CollectionRecordCategory] | None, Query(max_length=5)] = None,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> NativeRangeOverview:
    return native_ranges.overview(
        database,
        q=q,
        scope=scope,
        with_range=with_range,
        record=record or (),
        offset=offset,
        limit=limit,
    )


@router.get(
    "/native-ranges/identities/{identity_id}",
    response_model=SelectedNativeRanges,
    operation_id="getSelectedNativeRanges",
)
def native_selected(
    identity_id: UUID,
    _actor: Reader,
    database: Database,
    scope: RepresentationScope = "all",
    q: Annotated[str, Query(max_length=200)] = "",
    with_range: bool = False,
    record: Annotated[list[CollectionRecordCategory] | None, Query(max_length=5)] = None,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> SelectedNativeRanges:
    result = native_ranges.selected(
        database,
        identity_id,
        scope,
        q=q,
        with_range=with_range,
        record=record or (),
        offset=offset,
        limit=limit,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "represented_identity_not_found",
                "message": "Identity is missing or no longer represented in the collection",
            },
        )
    return result


@router.get(
    "/native-ranges/selection",
    response_model=NativeRangeSelection,
    operation_id="getNativeRangeSelection",
)
def native_selection(
    _actor: Reader,
    database: Database,
    identity: Annotated[list[UUID], Query(max_length=20)],
    scope: RepresentationScope = "all",
    q: Annotated[str, Query(max_length=200)] = "",
    with_range: bool = False,
    record: Annotated[list[CollectionRecordCategory] | None, Query(max_length=5)] = None,
) -> NativeRangeSelection:
    return native_ranges.selection(
        database, identity, scope=scope, q=q, with_range=with_range, record=record or ()
    )
