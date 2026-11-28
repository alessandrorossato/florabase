"""Authenticated full data export download and its size summary (DATA-EXPORT-001)."""

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
    responses={200: {"content": {"application/zip": {}}, "description": "The export ZIP"}},
)
def export_full_data(
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
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
