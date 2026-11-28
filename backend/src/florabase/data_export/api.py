"""Authenticated full data export download and its size summary (DATA-EXPORT-001)."""

import threading
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from florabase.attachments.storage import AttachmentStorage, AttachmentStorageError
from florabase.auth.dependencies import AuthenticatedActor, require_authenticated_actor
from florabase.core.config import Settings, get_settings
from florabase.data_export.service import ExportOptions, stream_export, summary
from florabase.db.session import get_database_session, get_engine

router = APIRouter(tags=["import-export"])

# Each download holds one pooled connection and an open snapshot for as long as the client takes,
# so only a few may run at once in this process; the rest answer 429 instead of starving the pool.
MAX_CONCURRENT_EXPORTS = 2
EXPORT_SLOTS = threading.BoundedSemaphore(MAX_CONCURRENT_EXPORTS)


def reserve_export_slot() -> Iterator[None]:
    """Held until the response has been sent or the client went away (request scope)."""
    if not EXPORT_SLOTS.acquire(blocking=False):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "export_in_progress",
                "message": "Another full export is running. Try again when it has finished.",
            },
            headers={"Retry-After": "30"},
        )
    try:
        yield
    finally:
        EXPORT_SLOTS.release()


def get_export_session() -> Iterator[Session]:
    """One read-only REPEATABLE READ snapshot that stays open while the ZIP streams.

    Request scope (the default) keeps it open until the response has been sent; it never writes,
    so it is independent of the request's transaction-owning session.
    """
    with Session(get_engine()) as session:
        session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        try:
            yield session
        finally:
            session.rollback()


def get_export_storage(settings: Annotated[Settings, Depends(get_settings)]) -> AttachmentStorage:
    try:
        return AttachmentStorage.from_settings(settings)
    except AttachmentStorageError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": error.code, "message": "Attachment storage is unavailable"},
        ) from error


class FullExportSummary(BaseModel):
    records: int
    attachments: int
    attachment_bytes: int
    files_allowed: bool


@router.get(
    "/exports/full/summary",
    operation_id="getFullExportSummary",
    response_model=FullExportSummary,
)
def read_full_export_summary(
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
    settings: Annotated[Settings, Depends(get_settings)],
) -> FullExportSummary:
    result = summary(database)
    return FullExportSummary(
        records=result.records,
        attachments=result.attachments,
        attachment_bytes=result.attachment_bytes,
        files_allowed=not settings.demo_readonly,
    )


@router.get(
    "/exports/full.zip",
    operation_id="exportFullDataZip",
    response_class=StreamingResponse,
    responses={
        200: {"content": {"application/zip": {}}, "description": "The export ZIP"},
        429: {"description": "Too many full exports are running"},
    },
)
def export_full_data(
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    # Declared before the snapshot, so a refused request never opens a database connection.
    _slot: Annotated[None, Depends(reserve_export_slot)],
    database: Annotated[Session, Depends(get_export_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    include_files: Annotated[bool, Query()] = False,
) -> StreamingResponse:
    # Demo mode allows the export but never hands out the shared photo files.
    files = include_files and not settings.demo_readonly
    storage = get_export_storage(settings) if files else None
    stamp = datetime.now(UTC)
    filename = f"florabase-export-{stamp:%Y%m%dT%H%M%SZ}.zip"
    return StreamingResponse(
        stream_export(
            database, ExportOptions(include_files=files), storage=storage, now=lambda: stamp
        ),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
