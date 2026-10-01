"""Persistent external snapshots in the normal protected Attachment storage.

A single durable cleanup pointer is operational recovery state, not media history.
All mutations lock the asset. New bytes are finalized before switching the pointer;
old bytes are removed only after that switch commits. Explicit copy/delete actions
retry any interrupted cleanup before proceeding. No age/link-count cleanup exists.
"""

from contextlib import suppress
from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID, uuid7

from fastapi import UploadFile
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import Headers

from florabase.attachments.model import Attachment, AttachmentState
from florabase.attachments.storage import AttachmentStorage, AttachmentStorageError
from florabase.collection_photos.model import MediaAsset
from florabase.media.fetch import fetch_image
from florabase.media.service import (
    MediaError,
    asset_thumbnail,
    delete_thumbnail,
    require_active,
    require_asset,
)


def cleanup_copy(database: Session, storage: AttachmentStorage, asset: MediaAsset) -> None:
    """Caller holds asset lock; missing bytes are safe on explicit cleanup retry."""
    if asset.copy_cleanup_attachment_id is None:
        return
    attachment = database.scalar(
        select(Attachment)
        .where(Attachment.id == asset.copy_cleanup_attachment_id)
        .with_for_update()
    )
    if attachment is None:
        raise MediaError(
            "media_copy_cleanup_missing", "Local copy cleanup needs operator recovery."
        )
    storage.delete_file(attachment.storage_key)
    # A byte-identical refresh uses the same derivative; retain the current one's cache.
    current = database.get(Attachment, asset.attachment_id) if asset.attachment_id else None
    if current is None or current.sha256 != attachment.sha256:
        delete_thumbnail(storage, asset, attachment)
    asset.copy_cleanup_attachment_id = None
    database.flush()
    database.delete(attachment)
    database.flush()


def _external(database: Session, asset_id: UUID) -> MediaAsset:
    asset = require_asset(database, asset_id, lock=True)
    require_active(database, asset)
    if asset.kind != "external":
        raise MediaError(
            "media_copy_external_only", "Local copies apply to external references.", 422
        )
    return asset


async def save_copy(
    database: Session, storage: AttachmentStorage, asset_id: UUID, *, refresh: bool
) -> None:
    asset = _external(database, asset_id)
    cleanup_copy(database, storage, asset)
    if refresh and asset.attachment_id is None:
        raise MediaError("media_copy_absent", "Save a local copy before refreshing.")
    if not refresh and asset.attachment_id is not None:
        raise MediaError(
            "media_copy_exists", "A local copy is already saved. Use Refresh local copy."
        )
    assert asset.image_url is not None
    payload, media_type = await run_in_threadpool(fetch_image, asset.image_url, storage.max_bytes)
    upload = UploadFile(
        file=BytesIO(payload),
        filename="external-image."
        + {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[media_type],
        headers=Headers({"content-type": media_type}),
    )
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
        with Image.open(stored.path) as image:
            width, height = image.size
        old = database.get(Attachment, asset.attachment_id) if asset.attachment_id else None
        database.add(attachment)
        database.flush()
        # Generate before publishing. Decode/write failures preserve the old pointer and bytes.
        asset_thumbnail(storage, asset, attachment)
        asset.attachment_id = attachment.id
        asset.fetched_at = datetime.now(UTC)
        asset.width, asset.height = width, height
        asset.updated_at = asset.fetched_at
        if old is not None:
            old.state = AttachmentState.PENDING_DELETE
            asset.copy_cleanup_attachment_id = old.id
        database.commit()
    except Exception:
        database.rollback()
        # Re-lock before cleanup: a competing request may have published a copy
        # after our rollback. An ambiguous commit must never delete live bytes.
        current = database.scalar(
            select(MediaAsset)
            .where(MediaAsset.id == asset_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if current is None or current.attachment_id != attachment.id:
            with suppress(AttachmentStorageError):
                storage.delete_file(stored.storage_key)
            previous = (
                database.get(Attachment, current.attachment_id)
                if current and current.attachment_id
                else None
            )
            if previous is None or previous.sha256 != stored.sha256:
                with suppress(AttachmentStorageError):
                    delete_thumbnail(storage, MediaAsset(id=asset_id), attachment)
        raise
    # Reacquire after commit: another operation may have finished cleanup or deleted the asset.
    remaining_asset = database.scalar(
        select(MediaAsset)
        .where(MediaAsset.id == asset_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if remaining_asset is not None:
        cleanup_copy(database, storage, remaining_asset)
        database.commit()


def remove_copy(database: Session, storage: AttachmentStorage, asset_id: UUID) -> None:
    asset = _external(database, asset_id)
    cleanup_copy(database, storage, asset)
    if asset.attachment_id is not None:
        attachment = database.get(Attachment, asset.attachment_id)
        assert attachment is not None
        attachment.state = AttachmentState.PENDING_DELETE
        asset.copy_cleanup_attachment_id = attachment.id
        asset.attachment_id = None
        asset.fetched_at = None
        asset.width = asset.height = None
        asset.updated_at = datetime.now(UTC)
        database.commit()
        asset = require_asset(database, asset_id, lock=True)
        cleanup_copy(database, storage, asset)
    database.commit()
