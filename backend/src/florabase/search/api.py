from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from florabase.auth.dependencies import AuthenticatedActor, require_authenticated_actor
from florabase.db.session import get_database_session
from florabase.events.model import EventKind
from florabase.search.schemas import SearchKind, SearchResponse
from florabase.search.service import SearchFilters, search, validate_filters

router = APIRouter(prefix="/search", tags=["collection"])


@router.get("", response_model=SearchResponse, operation_id="searchCollection")
def read_search(
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
    q: Annotated[str, Query(max_length=120)] = "",
    kind: Annotated[list[SearchKind] | None, Query()] = None,
    identity_id: UUID | None = None,
    lifecycle: str | None = None,
    location_id: UUID | None = None,
    supplier_id: UUID | None = None,
    provenance_place_id: UUID | None = None,
    provenance_site_id: UUID | None = None,
    event_kind: EventKind | None = None,
    year: Annotated[int | None, Query(ge=1, le=9999)] = None,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> SearchResponse:
    kinds = tuple(dict.fromkeys(kind or []))
    filters = SearchFilters(
        kinds=kinds,
        identity_id=identity_id,
        lifecycle=lifecycle,
        location_id=location_id,
        supplier_id=supplier_id,
        provenance_place_id=provenance_place_id,
        provenance_site_id=provenance_site_id,
        event_kind=event_kind,
        year=year,
    )
    try:
        validate_filters(filters)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return search(database, q.strip(), filters, offset=offset, limit=limit)
