from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from florabase.auth.dependencies import AuthenticatedActor, require_authenticated_actor
from florabase.collection_views.schemas import DashboardResponse
from florabase.collection_views.service import dashboard
from florabase.db.session import get_database_session
from florabase.schedule.schemas import CalendarDay

router = APIRouter(prefix="/dashboard", tags=["collection"])


@router.get("", response_model=DashboardResponse, operation_id="getDashboard")
def read_dashboard(
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
    today: Annotated[
        CalendarDay | None, Query(description="Browser local calendar day; defaults to UTC.")
    ] = None,
) -> DashboardResponse:
    return dashboard(database, today)
