"""Authenticated API routes for bulk care preview, apply, and batch undo."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from florabase.auth.dependencies import AuthenticatedActor, require_csrf, require_owner
from florabase.bulk import care_service
from florabase.bulk.care_schemas import (
    BulkCareApplyRequest,
    BulkCareApplyResponse,
    BulkCarePreviewRequest,
    BulkCarePreviewResponse,
    BulkCareUndoResponse,
)
from florabase.db.session import get_database_session
from florabase.events.service import EventDomainConflictError, EventReferenceNotFoundError

router = APIRouter(prefix="/bulk/care", tags=["bulk care"])
Database = Annotated[Session, Depends(get_database_session, scope="function")]
Writer = Annotated[AuthenticatedActor, Depends(require_csrf)]


def _failure(
    database: Session,
    error: Exception,
    *,
    concurrency_message: str = "No care entries logged. Refresh and preview again.",
) -> HTTPException:
    database.rollback()
    if isinstance(error, care_service.BulkCareError):
        status = (
            404
            if error.code in {"location_not_found", "batch_not_found"}
            else 422
            if error.code in {"nothing_to_log", "too_many_targets"}
            else 409
        )
        return HTTPException(
            status,
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
            "message": concurrency_message,
        },
    )


@router.post("/preview", response_model=BulkCarePreviewResponse, operation_id="previewBulkCare")
def preview(
    payload: BulkCarePreviewRequest, database: Database, actor: Writer
) -> BulkCarePreviewResponse:
    require_owner(actor)
    try:
        return care_service.preview_bulk_care(database, payload)
    except care_service.BulkCareError as error:
        raise _failure(database, error) from error


@router.post("/apply", response_model=BulkCareApplyResponse, operation_id="applyBulkCare")
def apply(
    payload: BulkCareApplyRequest, database: Database, actor: Writer
) -> BulkCareApplyResponse:
    require_owner(actor)
    try:
        result = care_service.apply_bulk_care(database, payload)
        database.commit()
        return result
    except (
        care_service.BulkCareError,
        EventDomainConflictError,
        EventReferenceNotFoundError,
        IntegrityError,
        OperationalError,
    ) as error:
        raise _failure(database, error) from error


@router.delete(
    "/batches/{batch_id}",
    response_model=BulkCareUndoResponse,
    operation_id="undoBulkCare",
)
def undo(batch_id: UUID, database: Database, actor: Writer) -> BulkCareUndoResponse:
    require_owner(actor)
    try:
        result = care_service.undo_bulk_care(database, batch_id)
        database.commit()
        return result
    except (
        care_service.BulkCareError,
        EventDomainConflictError,
        IntegrityError,
        OperationalError,
    ) as error:
        raise _failure(
            database,
            error,
            concurrency_message="Undo did not complete. Refresh and try again.",
        ) from error
