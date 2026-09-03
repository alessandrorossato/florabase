from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from florabase.auth.dependencies import AuthenticatedActor, require_authenticated_actor
from florabase.collection_views.schemas import DashboardResponse
from florabase.collection_views.service import dashboard
from florabase.db.session import get_database_session

router = APIRouter(prefix="/dashboard", tags=["collection"])


@router.get("", response_model=DashboardResponse, operation_id="getDashboard")
def read_dashboard(
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> DashboardResponse:
    return dashboard(database)
