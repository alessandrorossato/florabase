from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from florabase.attachments.model import Attachment
from florabase.attachments.schemas import AttachmentResponse
from florabase.attachments.service import (
    AttachmentOperationError,
    attachment_content_path,
    create_attachment,
    delete_attachment,
    require_active_attachment,
)
from florabase.attachments.storage import AttachmentStorage, AttachmentStorageError
from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
    require_owner,
)
from florabase.core.config import Settings, get_settings
from florabase.db.session import get_database_session

router = APIRouter(prefix="/attachments", tags=["attachments"])


def get_attachment_storage(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AttachmentStorage:
    try:
        return AttachmentStorage.from_settings(settings)
    except AttachmentStorageError as error:
        raise _http_error(error) from error


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "attachment_not_found", "message": "Attachment not found"},
    )


def _http_error(error: AttachmentStorageError | AttachmentOperationError) -> HTTPException:
    response_status = {
        "attachment_too_large": status.HTTP_413_CONTENT_TOO_LARGE,
        "unsupported_media_type": status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        "attachment_content_missing": status.HTTP_409_CONFLICT,
        "attachment_content_mismatch": status.HTTP_409_CONFLICT,
        "unsafe_storage_key": status.HTTP_409_CONFLICT,
        "unsafe_storage_path": status.HTTP_409_CONFLICT,
    }.get(error.code, status.HTTP_503_SERVICE_UNAVAILABLE)
    if error.code in {
        "invalid_filename",
        "empty_attachment",
        "invalid_image",
        "animated_image_not_supported",
        "unsafe_image_dimensions",
        "media_type_mismatch",
    }:
        response_status = status.HTTP_422_UNPROCESSABLE_CONTENT
    return HTTPException(
        status_code=response_status,
        detail={"code": error.code, "message": error.message},
    )


def _active(database: Session, attachment_id: UUID) -> Attachment:
    attachment = require_active_attachment(database, attachment_id)
    if attachment is None:
        raise _not_found()
    return attachment


@router.post(
    "",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createAttachment",
)
async def create(
    response: Response,
    file: Annotated[UploadFile, File(description="JPEG, PNG, or WebP attachment")],
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
    storage: Annotated[AttachmentStorage, Depends(get_attachment_storage)],
) -> AttachmentResponse:
    require_owner(actor)
    try:
        attachment = await create_attachment(database, storage, file)
    except (AttachmentStorageError, AttachmentOperationError) as error:
        raise _http_error(error) from error
    response.headers["Location"] = f"/api/v1/attachments/{attachment.id}"
    return AttachmentResponse.from_model(attachment)


@router.get("/{attachment_id}", response_model=AttachmentResponse, operation_id="getAttachment")
def read(
    attachment_id: UUID,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> AttachmentResponse:
    require_owner(actor)
    response.headers["Cache-Control"] = "private, no-store"
    return AttachmentResponse.from_model(_active(database, attachment_id))


@router.get(
    "/{attachment_id}/content",
    response_class=FileResponse,
    responses={
        200: {
            "content": {
                "image/jpeg": {},
                "image/png": {},
                "image/webp": {},
            },
            "description": "Validated local attachment content",
        }
    },
    operation_id="getAttachmentContent",
)
def read_content(
    attachment_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
    storage: Annotated[AttachmentStorage, Depends(get_attachment_storage)],
) -> FileResponse:
    require_owner(actor)
    attachment = _active(database, attachment_id)
    try:
        path = attachment_content_path(storage, attachment)
    except AttachmentStorageError as error:
        raise _http_error(error) from error
    encoded_filename = quote(attachment.original_filename, safe="")
    return FileResponse(
        path,
        media_type=attachment.media_type,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}",
        },
    )


@router.delete(
    "/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteAttachment",
)
def delete(
    attachment_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
    storage: Annotated[AttachmentStorage, Depends(get_attachment_storage)],
) -> Response:
    require_owner(actor)
    try:
        if not delete_attachment(database, storage, attachment_id):
            raise _not_found()
    except (AttachmentStorageError, AttachmentOperationError) as error:
        raise _http_error(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
