from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from florabase.auth.dependencies import AuthenticatedActor, require_authenticated_actor
from florabase.db.session import get_database_session
from florabase.history.schemas import HistoryCategory, HistoryResponse, HistorySubjectKind
from florabase.history.service import list_history

router = APIRouter(prefix="/history", tags=["collection"])


@router.get("", response_model=HistoryResponse, operation_id="listHistory")
def read_history(
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
    category: Annotated[list[HistoryCategory] | None, Query()] = None,
    subject_kind: HistorySubjectKind | None = None,
    year: Annotated[int | None, Query(ge=1, le=9999)] = None,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> HistoryResponse:
    return list_history(
        database,
        categories=tuple(dict.fromkeys(category or [])),
        subject_kind=subject_kind,
        year=year,
        offset=offset,
        limit=limit,
    )
