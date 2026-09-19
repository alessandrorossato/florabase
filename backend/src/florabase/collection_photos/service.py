import warnings
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Literal, cast
from uuid import UUID, uuid7

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import Select, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from florabase.attachments.model import Attachment, AttachmentState
from florabase.attachments.storage import AttachmentStorage, AttachmentStorageError, StoredUpload
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.collection_photos.model import (
    BotanicalIdentityCoverImage,
    ExternalImageReference,
    LocalCollectionPhoto,
)
from florabase.collection_photos.schemas import (
    ExternalCoverResponse,
    ExternalCoverWrite,
    ExternalImageWrite,
    LocalCoverResponse,
    LocalPhotoResponse,
    PhotoMetadataWrite,
)
from florabase.events.model import Event
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing

TargetType = Literal["seed_lot", "sowing", "plant", "plant_group", "event"]
TARGET_MODELS = {
    "seed_lot": (SeedLot, "seed_lot_id"),
    "sowing": (Sowing, "sowing_id"),
    "plant": (Plant, "plant_id"),
    "plant_group": (PlantGroup, "plant_group_id"),
    "event": (Event, "event_id"),
}
IDENTITY_COVER_THUMBNAIL_MAX_EDGE = 320


@dataclass
class CollectionPhotoError(Exception):
    code: str
    message: str


def require_target(database: Session, target_type: TargetType, target_id: UUID) -> None:
    model, _ = TARGET_MODELS[target_type]
    if database.get(model, target_id) is None:
        raise CollectionPhotoError(
            "photo_target_not_found", "The collection record for this photo was not found"
        )


def _target_values(target_type: TargetType, target_id: UUID) -> dict[str, UUID]:
    return {TARGET_MODELS[target_type][1]: target_id}


def _target_filter(
    model: type[LocalCollectionPhoto] | type[ExternalImageReference],
    target_type: TargetType,
    target_id: UUID,
) -> ColumnElement[bool]:
    return cast(ColumnElement[bool], getattr(model, TARGET_MODELS[target_type][1]) == target_id)


def local_response(photo: LocalCollectionPhoto, attachment: Attachment) -> LocalPhotoResponse:
    active = attachment.state == AttachmentState.ACTIVE
    return LocalPhotoResponse(
        id=photo.id,
        attachment_id=attachment.id,
        original_filename=attachment.original_filename,
        media_type=cast(Literal["image/jpeg", "image/png", "image/webp"], attachment.media_type),
        caption=photo.caption,
        attribution=photo.attribution,
        deletion_pending=not active,
        content_url=f"/api/v1/attachments/{attachment.id}/content" if active else None,
        created_at=photo.created_at,
        updated_at=photo.updated_at,
    )


def list_photos(
    database: Session, target_type: TargetType, target_id: UUID
) -> list[LocalPhotoResponse | ExternalImageReference]:
    require_target(database, target_type, target_id)
    local_rows = database.execute(
        select(LocalCollectionPhoto, Attachment)
        .join(Attachment, Attachment.id == LocalCollectionPhoto.attachment_id)
        .where(_target_filter(LocalCollectionPhoto, target_type, target_id))
    ).all()
    external = database.scalars(
        select(ExternalImageReference).where(
            _target_filter(ExternalImageReference, target_type, target_id)
        )
    ).all()
    combined: list[LocalPhotoResponse | ExternalImageReference] = [
        *(local_response(photo, attachment) for photo, attachment in local_rows),
        *external,
    ]
    return sorted(combined, key=lambda item: (item.created_at, item.id))


async def upload_local_photo(
    database: Session,
    storage: AttachmentStorage,
    target_type: TargetType,
    target_id: UUID,
    upload: UploadFile,
    metadata: PhotoMetadataWrite,
) -> LocalPhotoResponse:
    require_target(database, target_type, target_id)
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
    photo = LocalCollectionPhoto(
        id=uuid7(),
        attachment_id=attachment.id,
        caption=metadata.caption,
        attribution=metadata.attribution,
        **_target_values(target_type, target_id),
    )
    try:
        database.add_all([attachment, photo])
        database.commit()
    except Exception as error:
        database.rollback()
        with suppress(OSError):
            stored.path.unlink(missing_ok=True)
        raise CollectionPhotoError(
            "photo_metadata_write_failed", "Could not persist the uploaded photo relationship"
        ) from error
    return local_response(photo, attachment)


def create_external_image(
    database: Session,
    target_type: TargetType,
    target_id: UUID,
    payload: ExternalImageWrite,
) -> ExternalImageReference:
    require_target(database, target_type, target_id)
    reference = ExternalImageReference(
        id=uuid7(), **payload.model_dump(), **_target_values(target_type, target_id)
    )
    database.add(reference)
    database.commit()
    return reference


def get_local_photo(
    database: Session, photo_id: UUID
) -> tuple[LocalCollectionPhoto, Attachment] | None:
    row = database.execute(
        select(LocalCollectionPhoto, Attachment)
        .join(Attachment, Attachment.id == LocalCollectionPhoto.attachment_id)
        .where(LocalCollectionPhoto.id == photo_id)
    ).one_or_none()
    return None if row is None else (row[0], row[1])


def get_external_image(database: Session, reference_id: UUID) -> ExternalImageReference | None:
    return database.get(ExternalImageReference, reference_id)


def update_local_photo(
    database: Session,
    photo: LocalCollectionPhoto,
    attachment: Attachment,
    payload: PhotoMetadataWrite,
) -> LocalPhotoResponse:
    if attachment.state != AttachmentState.ACTIVE:
        raise CollectionPhotoError(
            "photo_deletion_pending", "This photo is pending deletion and can only be retried"
        )
    photo.caption = payload.caption
    photo.attribution = payload.attribution
    photo.updated_at = datetime.now(UTC)
    database.commit()
    return local_response(photo, attachment)


def update_external_image(
    database: Session, reference: ExternalImageReference, payload: ExternalImageWrite
) -> ExternalImageReference:
    for field, value in payload.model_dump().items():
        setattr(reference, field, value)
    reference.updated_at = datetime.now(UTC)
    database.commit()
    return reference


def delete_local_photo(database: Session, storage: AttachmentStorage, photo_id: UUID) -> bool:
    row = database.execute(
        select(LocalCollectionPhoto, Attachment)
        .join(Attachment, Attachment.id == LocalCollectionPhoto.attachment_id)
        .where(LocalCollectionPhoto.id == photo_id)
        .with_for_update()
    ).one_or_none()
    if row is None:
        return False
    photo, attachment = row
    was_active = attachment.state == AttachmentState.ACTIVE
    if was_active:
        attachment.state = AttachmentState.PENDING_DELETE
        try:
            database.commit()
        except SQLAlchemyError as error:
            database.rollback()
            raise CollectionPhotoError(
                "photo_delete_state_failed", "Could not begin photo deletion"
            ) from error
    try:
        removed = storage.delete_file(attachment.storage_key)
    except AttachmentStorageError:
        raise
    if was_active and not removed:
        raise CollectionPhotoError(
            "attachment_content_missing",
            "Photo content was already missing; deletion is pending a retry",
        )
    try:
        database.delete(photo)
        database.flush()
        database.delete(attachment)
        database.commit()
    except SQLAlchemyError as error:
        database.rollback()
        raise CollectionPhotoError(
            "photo_metadata_delete_failed",
            "Photo content is gone but relationship cleanup must be retried",
        ) from error
    return True


def delete_external_image(database: Session, reference: ExternalImageReference) -> None:
    database.delete(reference)
    database.commit()


def target_photo_count(database: Session, target_type: TargetType, target_id: UUID) -> int:
    local = database.scalars(
        select(LocalCollectionPhoto.id).where(
            _target_filter(LocalCollectionPhoto, target_type, target_id)
        )
    ).all()
    external = database.scalars(
        select(ExternalImageReference.id).where(
            _target_filter(ExternalImageReference, target_type, target_id)
        )
    ).all()
    return len(local) + len(external)


def attachment_has_photo(database: Session, attachment_id: UUID) -> bool:
    statement: Select[tuple[UUID]] = select(LocalCollectionPhoto.id).where(
        LocalCollectionPhoto.attachment_id == attachment_id
    )
    return database.scalar(statement) is not None


def attachment_image_owner(database: Session, attachment_id: UUID) -> str | None:
    if attachment_has_photo(database, attachment_id):
        return "collection_photo"
    cover = database.scalar(
        select(BotanicalIdentityCoverImage.id).where(
            BotanicalIdentityCoverImage.attachment_id == attachment_id
        )
    )
    return "botanical_identity_cover" if cover is not None else None


def require_botanical_identity(
    database: Session, botanical_identity_id: UUID, *, lock: bool = False
) -> BotanicalIdentity:
    statement = select(BotanicalIdentity).where(BotanicalIdentity.id == botanical_identity_id)
    if lock:
        statement = statement.with_for_update()
    identity = database.scalar(statement)
    if identity is None:
        raise CollectionPhotoError("botanical_identity_not_found", "Botanical identity not found")
    return identity


def get_identity_cover(
    database: Session, botanical_identity_id: UUID, *, lock: bool = False
) -> tuple[BotanicalIdentityCoverImage, Attachment | None] | None:
    statement = (
        select(BotanicalIdentityCoverImage, Attachment)
        .outerjoin(Attachment, Attachment.id == BotanicalIdentityCoverImage.attachment_id)
        .where(BotanicalIdentityCoverImage.botanical_identity_id == botanical_identity_id)
    )
    if lock:
        statement = statement.with_for_update(of=BotanicalIdentityCoverImage)
    row = database.execute(statement).one_or_none()
    return None if row is None else (row[0], row[1])


def cover_response(
    cover: BotanicalIdentityCoverImage, attachment: Attachment | None
) -> LocalCoverResponse | ExternalCoverResponse:
    if cover.source_mode == "local":
        if attachment is None or cover.attachment_id is None:
            raise CollectionPhotoError(
                "cover_attachment_missing", "The local cover attachment metadata is missing"
            )
        active = attachment.state == AttachmentState.ACTIVE
        return LocalCoverResponse(
            id=cover.id,
            attachment_id=attachment.id,
            original_filename=attachment.original_filename,
            media_type=cast(
                Literal["image/jpeg", "image/png", "image/webp"], attachment.media_type
            ),
            deletion_pending=not active,
            content_url=(f"/api/v1/attachments/{attachment.id}/content" if active else None),
            created_at=cover.created_at,
            updated_at=cover.updated_at,
        )
    if cover.image_url is None or cover.source_url is None or cover.attribution is None:
        raise CollectionPhotoError(
            "cover_external_metadata_missing", "The external cover metadata is incomplete"
        )
    return ExternalCoverResponse(
        id=cover.id,
        image_url=cover.image_url,
        source_url=cover.source_url,
        attribution=cover.attribution,
        licence_label=cover.licence_label,
        licence_url=cover.licence_url,
        created_at=cover.created_at,
        updated_at=cover.updated_at,
    )


def read_identity_cover(
    database: Session, botanical_identity_id: UUID
) -> LocalCoverResponse | ExternalCoverResponse | None:
    require_botanical_identity(database, botanical_identity_id)
    row = get_identity_cover(database, botanical_identity_id)
    return None if row is None else cover_response(*row)


def local_identity_cover_attachment(
    database: Session, botanical_identity_id: UUID
) -> Attachment | None:
    require_botanical_identity(database, botanical_identity_id)
    row = get_identity_cover(database, botanical_identity_id)
    if row is None or row[0].source_mode != "local":
        return None
    cover, attachment = row
    if attachment is None or cover.attachment_id is None:
        raise CollectionPhotoError(
            "cover_attachment_missing", "The local cover attachment metadata is missing"
        )
    if attachment.state != AttachmentState.ACTIVE:
        return None
    return attachment


def render_identity_cover_thumbnail(path: Path) -> bytes:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as source:
                source.load()
                oriented = ImageOps.exif_transpose(source)
                mode = "RGBA" if "A" in oriented.getbands() else "RGB"
                thumbnail = oriented.convert(mode)
                thumbnail.thumbnail(
                    (
                        IDENTITY_COVER_THUMBNAIL_MAX_EDGE,
                        IDENTITY_COVER_THUMBNAIL_MAX_EDGE,
                    ),
                    Image.Resampling.LANCZOS,
                )
                output = BytesIO()
                thumbnail.save(output, format="WEBP", quality=82, method=4)
                return output.getvalue()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise AttachmentStorageError(
            "unsafe_image_dimensions", "Image dimensions exceed the safe decoding limit"
        ) from error
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
        raise AttachmentStorageError(
            "invalid_image", "Attachment content is malformed or truncated"
        ) from error


def _new_attachment(stored: StoredUpload) -> Attachment:
    return Attachment(
        id=uuid7(),
        storage_key=stored.storage_key,
        original_filename=stored.original_filename,
        media_type=stored.media_type,
        byte_size=stored.byte_size,
        sha256=stored.sha256,
        state=AttachmentState.ACTIVE,
    )


def _remove_stored_upload(stored: StoredUpload) -> None:
    with suppress(OSError):
        stored.path.unlink(missing_ok=True)


def _begin_cover_attachment_delete(database: Session, attachment: Attachment) -> bool:
    was_active = attachment.state == AttachmentState.ACTIVE
    if was_active:
        attachment.state = AttachmentState.PENDING_DELETE
        try:
            database.commit()
        except SQLAlchemyError as error:
            database.rollback()
            raise CollectionPhotoError(
                "cover_delete_state_failed", "Could not begin local cover deletion"
            ) from error
    return was_active


def _unlink_cover_attachment(
    storage: AttachmentStorage, attachment: Attachment, was_active: bool
) -> None:
    removed = storage.delete_file(attachment.storage_key)
    if was_active and not removed:
        raise CollectionPhotoError(
            "attachment_content_missing",
            "Cover content was already missing; cleanup is pending a retry",
        )


async def set_local_identity_cover(
    database: Session,
    storage: AttachmentStorage,
    botanical_identity_id: UUID,
    upload: UploadFile,
) -> LocalCoverResponse:
    require_botanical_identity(database, botanical_identity_id, lock=True)
    stored = await storage.store_upload(upload)
    new_attachment = _new_attachment(stored)
    row = get_identity_cover(database, botanical_identity_id, lock=True)
    cover = row[0] if row is not None else None
    old_attachment = row[1] if row is not None else None

    if cover is not None and cover.source_mode == "local":
        if old_attachment is None:
            _remove_stored_upload(stored)
            raise CollectionPhotoError(
                "cover_attachment_missing", "The local cover attachment metadata is missing"
            )
        was_active = _begin_cover_attachment_delete(database, old_attachment)
        try:
            _unlink_cover_attachment(storage, old_attachment, was_active)
        except Exception:
            _remove_stored_upload(stored)
            raise

    try:
        database.add(new_attachment)
        if cover is None:
            cover = BotanicalIdentityCoverImage(
                id=uuid7(),
                botanical_identity_id=botanical_identity_id,
                source_mode="local",
                attachment_id=new_attachment.id,
            )
            database.add(cover)
        else:
            cover.source_mode = "local"
            cover.attachment_id = new_attachment.id
            cover.image_url = None
            cover.source_url = None
            cover.attribution = None
            cover.licence_label = None
            cover.licence_url = None
            cover.updated_at = datetime.now(UTC)
            database.flush()
            if old_attachment is not None:
                database.delete(old_attachment)
        database.commit()
    except Exception as error:
        database.rollback()
        _remove_stored_upload(stored)
        raise CollectionPhotoError(
            "cover_metadata_write_failed", "Could not persist the local cover"
        ) from error
    return cast(LocalCoverResponse, cover_response(cover, new_attachment))


def set_external_identity_cover(
    database: Session,
    storage: AttachmentStorage,
    botanical_identity_id: UUID,
    payload: ExternalCoverWrite,
) -> ExternalCoverResponse:
    require_botanical_identity(database, botanical_identity_id, lock=True)
    row = get_identity_cover(database, botanical_identity_id, lock=True)
    cover = row[0] if row is not None else None
    old_attachment = row[1] if row is not None else None
    if cover is not None and cover.source_mode == "local":
        if old_attachment is None:
            raise CollectionPhotoError(
                "cover_attachment_missing", "The local cover attachment metadata is missing"
            )
        was_active = _begin_cover_attachment_delete(database, old_attachment)
        _unlink_cover_attachment(storage, old_attachment, was_active)

    values = payload.model_dump(exclude={"privacy_acknowledged"})
    try:
        if cover is None:
            cover = BotanicalIdentityCoverImage(
                id=uuid7(),
                botanical_identity_id=botanical_identity_id,
                source_mode="external",
                **values,
            )
            database.add(cover)
        else:
            cover.source_mode = "external"
            cover.attachment_id = None
            for field, value in values.items():
                setattr(cover, field, value)
            cover.updated_at = datetime.now(UTC)
            database.flush()
            if old_attachment is not None:
                database.delete(old_attachment)
        database.commit()
    except Exception as error:
        database.rollback()
        raise CollectionPhotoError(
            "cover_metadata_write_failed", "Could not persist the external cover"
        ) from error
    return cast(ExternalCoverResponse, cover_response(cover, None))


def delete_identity_cover(
    database: Session, storage: AttachmentStorage, botanical_identity_id: UUID
) -> bool:
    require_botanical_identity(database, botanical_identity_id, lock=True)
    row = get_identity_cover(database, botanical_identity_id, lock=True)
    if row is None:
        return False
    cover, attachment = row
    if cover.source_mode == "local":
        if attachment is None:
            raise CollectionPhotoError(
                "cover_attachment_missing", "The local cover attachment metadata is missing"
            )
        was_active = _begin_cover_attachment_delete(database, attachment)
        _unlink_cover_attachment(storage, attachment, was_active)
    try:
        database.delete(cover)
        database.flush()
        if attachment is not None:
            database.delete(attachment)
        database.commit()
    except SQLAlchemyError as error:
        database.rollback()
        raise CollectionPhotoError(
            "cover_metadata_delete_failed",
            "Cover content is gone but metadata cleanup must be retried",
        ) from error
    return True
