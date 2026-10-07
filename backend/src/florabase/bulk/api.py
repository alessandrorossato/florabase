from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from florabase.auth.dependencies import AuthenticatedActor, require_csrf, require_owner
from florabase.bulk import service
from florabase.bulk.schemas import (
    BulkLocationApplyRequest,
    BulkLocationPreview,
    BulkLocationPreviewRequest,
    BulkLocationResult,
)
from florabase.db.session import get_database_session
from florabase.events.service import EventDomainConflictError, EventReferenceNotFoundError

router = APIRouter(prefix="/bulk/location", tags=["bulk location"])
Database = Annotated[Session, Depends(get_database_session)]
Writer = Annotated[AuthenticatedActor, Depends(require_csrf)]


def failure(database: Session, error: Exception) -> HTTPException:
    database.rollback()
    if isinstance(error, service.BulkConflictError):
        return HTTPException(
            404 if error.code == "target_location_not_found" else 409,
            detail={
                "code": error.code,
                "message": error.message,
                "rows": [row.model_dump(mode="json") for row in error.rows],
            },
        )
    if isinstance(error, (EventDomainConflictError, EventReferenceNotFoundError)):
        return HTTPException(409, detail={"code": error.code, "message": error.message})
    return HTTPException(
        409,
        detail={
            "code": "concurrent_change",
            "message": "No records moved. Refresh and preview again.",
        },
    )


@router.post("/preview", response_model=BulkLocationPreview, operation_id="previewBulkLocation")
def preview(
    payload: BulkLocationPreviewRequest, database: Database, actor: Writer
) -> BulkLocationPreview:
    require_owner(actor)
    try:
        return service.preview(database, payload)
    except service.BulkConflictError as error:
        raise failure(database, error) from error


@router.post("/apply", response_model=BulkLocationResult, operation_id="applyBulkLocation")
def apply(
    payload: BulkLocationApplyRequest, database: Database, actor: Writer
) -> BulkLocationResult:
    require_owner(actor)
    try:
        result = service.apply(database, payload)
        database.commit()
        return result
    except (
        service.BulkConflictError,
        EventDomainConflictError,
        EventReferenceNotFoundError,
        IntegrityError,
        OperationalError,
    ) as error:
        raise failure(database, error) from error
