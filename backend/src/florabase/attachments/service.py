from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid7

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from florabase.attachments.model import Attachment, AttachmentState
from florabase.attachments.storage import AttachmentStorage, AttachmentStorageError


@dataclass
class AttachmentOperationError(Exception):
    code: str
    message: str


async def create_attachment(
    database: Session, storage: AttachmentStorage, upload: UploadFile
) -> Attachment:
    stored = await storage.store_upload(upload)
    attachment = Attachment(
        id=uuid7(),
        storage_key=stored.storage_key,
        original_filename=stored.original_filename,
        media_type=stored.media_type,
        byte_size=stored.byte_size,
        sha256=stored.sha256,
        state=AttachmentState.ACTIVE,
    )
    try:
        database.add(attachment)
        database.commit()
    except Exception as error:
        database.rollback()
        with suppress(OSError):
            stored.path.unlink(missing_ok=True)
        raise AttachmentOperationError(
            "attachment_metadata_write_failed", "Could not persist attachment metadata"
        ) from error
    return attachment


def get_attachment(
    database: Session, attachment_id: UUID, *, lock: bool = False
) -> Attachment | None:
    statement = select(Attachment).where(Attachment.id == attachment_id)
    if lock:
        statement = statement.with_for_update()
    return database.scalar(statement)


def require_active_attachment(database: Session, attachment_id: UUID) -> Attachment | None:
    attachment = get_attachment(database, attachment_id)
    if attachment is None or attachment.state != AttachmentState.ACTIVE:
        return None
    return attachment


def attachment_content_path(storage: AttachmentStorage, attachment: Attachment) -> Path:
    return storage.active_path(attachment.storage_key, attachment.byte_size)


def delete_attachment(database: Session, storage: AttachmentStorage, attachment_id: UUID) -> bool:
    attachment = get_attachment(database, attachment_id, lock=True)
    if attachment is None:
        return False

    from florabase.collection_photos.service import attachment_image_owner

    image_owner = attachment_image_owner(database, attachment_id)
    if image_owner == "collection_photo":
        raise AttachmentOperationError(
            "attachment_owned_by_photo",
            "This attachment is owned by a collection photo; remove the photo instead",
        )
    if image_owner == "botanical_identity_cover":
        raise AttachmentOperationError(
            "attachment_owned_by_identity_cover",
            "This attachment is owned by a botanical identity cover; remove the cover instead",
        )

    storage_key = attachment.storage_key
    was_active = attachment.state == AttachmentState.ACTIVE
    if was_active:
        attachment.state = AttachmentState.PENDING_DELETE
        try:
            database.commit()
        except SQLAlchemyError as error:
            database.rollback()
            raise AttachmentOperationError(
                "attachment_delete_state_failed", "Could not begin attachment deletion"
            ) from error

    try:
        removed = storage.delete_file(storage_key)
    except AttachmentStorageError:
        raise
    if was_active and not removed:
        raise AttachmentOperationError(
            "attachment_content_missing",
            "Attachment content was already missing; deletion is pending a retry",
        )

    try:
        database.delete(attachment)
        database.commit()
    except SQLAlchemyError as error:
        database.rollback()
        raise AttachmentOperationError(
            "attachment_metadata_delete_failed",
            "Attachment content is gone but metadata cleanup must be retried",
        ) from error
    return True
