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
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, contains_eager
from sqlalchemy.sql.elements import ColumnElement

from florabase.attachments.model import Attachment, AttachmentState
from florabase.attachments.storage import AttachmentStorage, AttachmentStorageError
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.collection_photos.model import (
    BotanicalIdentityCoverImage,
    ExternalImageReference,
    LocalCollectionPhoto,
    MediaAsset,
    RecordMediaLink,
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
from florabase.harvests.model import Harvest
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing
from florabase.suppliers.model import Supplier

TargetType = Literal["seed_lot", "sowing", "plant", "plant_group", "event", "harvest", "supplier"]
TARGET_MODELS: dict[
    str,
    tuple[
        type[SeedLot]
        | type[Sowing]
        | type[Plant]
        | type[PlantGroup]
        | type[Event]
        | type[Harvest]
        | type[Supplier],
        str,
    ],
] = {
    "seed_lot": (SeedLot, "seed_lot_id"),
    "sowing": (Sowing, "sowing_id"),
    "plant": (Plant, "plant_id"),
    "plant_group": (PlantGroup, "plant_group_id"),
    "event": (Event, "event_id"),
    "harvest": (Harvest, "harvest_id"),
    "supplier": (Supplier, "supplier_id"),
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
        media_asset_id=photo.media_asset_id,
        display_order=photo.display_order or 0,
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
        .join(MediaAsset, MediaAsset.id == LocalCollectionPhoto.media_asset_id)
        .options(contains_eager(LocalCollectionPhoto.media_asset))
        .join(Attachment, Attachment.id == MediaAsset.attachment_id)
        .where(_target_filter(LocalCollectionPhoto, target_type, target_id))
    ).all()
    external = database.scalars(
        select(ExternalImageReference)
        .join(MediaAsset, MediaAsset.id == ExternalImageReference.media_asset_id)
        .options(contains_eager(ExternalImageReference.media_asset))
        .where(_target_filter(ExternalImageReference, target_type, target_id))
    ).all()
    combined: list[LocalPhotoResponse | ExternalImageReference] = [
        *(local_response(photo, attachment) for photo, attachment in local_rows),
        *external,
    ]
    return sorted(combined, key=lambda item: (item.display_order, item.created_at, item.id))


async def upload_local_photo(
    database: Session,
    storage: AttachmentStorage,
    target_type: TargetType,
    target_id: UUID,
    upload: UploadFile,
    metadata: PhotoMetadataWrite,
) -> LocalPhotoResponse:
    from florabase.media.schemas import AssetMetadataWrite
    from florabase.media.service import upload_asset

    try:
        asset = await upload_asset(
            database,
            storage,
            upload,
            AssetMetadataWrite(attribution=metadata.attribution),
            target=target_type,
            target_id=target_id,
            caption=metadata.caption,
        )
    except AttachmentStorageError, CollectionPhotoError:
        raise
    except Exception as error:
        raise CollectionPhotoError(
            "photo_metadata_write_failed", "Could not persist the uploaded media and record link"
        ) from error
    photo = database.scalar(
        select(LocalCollectionPhoto)
        .where(LocalCollectionPhoto.media_asset_id == asset.id)
        .options(contains_eager(LocalCollectionPhoto.media_asset))
        .join(MediaAsset, MediaAsset.id == LocalCollectionPhoto.media_asset_id)
    )
    attachment = database.get(Attachment, asset.attachment_id)
    assert photo is not None
    assert attachment is not None
    return local_response(photo, attachment)


def create_external_image(
    database: Session, target_type: TargetType, target_id: UUID, payload: ExternalImageWrite
) -> ExternalImageReference:
    from florabase.media.schemas import ExternalAssetCreate
    from florabase.media.service import create_external_asset

    asset = create_external_asset(
        database,
        ExternalAssetCreate(
            image_url=payload.image_url,
            source_url=payload.source_url,
            attribution=payload.attribution,
        ),
        target=target_type,
        target_id=target_id,
        caption=payload.caption,
    )
    reference = database.scalar(
        select(ExternalImageReference)
        .join(MediaAsset, MediaAsset.id == ExternalImageReference.media_asset_id)
        .options(contains_eager(ExternalImageReference.media_asset))
        .where(ExternalImageReference.media_asset_id == asset.id)
    )
    assert reference is not None
    return reference


def get_local_photo(
    database: Session, photo_id: UUID
) -> tuple[LocalCollectionPhoto, Attachment] | None:
    row = database.execute(
        select(LocalCollectionPhoto, Attachment)
        .join(MediaAsset, MediaAsset.id == LocalCollectionPhoto.media_asset_id)
        .options(contains_eager(LocalCollectionPhoto.media_asset))
        .join(Attachment, Attachment.id == MediaAsset.attachment_id)
        .where(LocalCollectionPhoto.id == photo_id)
    ).one_or_none()
    return None if row is None else (row[0], row[1])


def get_external_image(database: Session, reference_id: UUID) -> ExternalImageReference | None:
    return database.scalar(
        select(ExternalImageReference)
        .join(MediaAsset, MediaAsset.id == ExternalImageReference.media_asset_id)
        .options(contains_eager(ExternalImageReference.media_asset))
        .where(ExternalImageReference.id == reference_id)
    )


def update_local_photo(
    database: Session,
    photo: LocalCollectionPhoto,
    attachment: Attachment,
    payload: PhotoMetadataWrite,
) -> LocalPhotoResponse:
    from florabase.media.service import locked_link, require_active

    locked = locked_link(database, photo.id)
    if locked is None or not isinstance(locked, LocalCollectionPhoto):
        raise CollectionPhotoError("primary_photo_not_found", "Collection photo not found")
    require_active(database, locked.media_asset)
    if payload.display_order is not None:
        locked.display_order = payload.display_order
    locked.caption = payload.caption
    locked.attribution = payload.attribution
    locked.updated_at = datetime.now(UTC)
    database.commit()
    return local_response(locked, attachment)


def update_external_image(
    database: Session, reference: ExternalImageReference, payload: ExternalImageWrite
) -> ExternalImageReference:
    from florabase.media.service import MediaError, locked_link, reference_counts, require_active

    locked = locked_link(database, reference.id)
    if not isinstance(locked, ExternalImageReference):
        raise MediaError("media_link_not_found", "Media link not found", 404)
    require_active(database, locked.media_asset)
    if reference_counts(database, locked.media_asset_id)[1] and (
        payload.image_url != locked.image_url or payload.source_url != locked.source_url
    ):
        raise MediaError(
            "cover_privacy_requires_replacement",
            "This media is used as an identity cover. Replace the cover with a newly "
            "approved external reference to change its URLs.",
        )
    for field, value in payload.model_dump().items():
        if field != "display_order" or value is not None:
            setattr(locked, field, value)
    locked.updated_at = datetime.now(UTC)
    database.commit()
    return locked


def delete_local_photo(database: Session, storage: AttachmentStorage, photo_id: UUID) -> bool:
    from florabase.media.service import unlink

    return unlink(database, photo_id)


def delete_external_image(database: Session, reference: ExternalImageReference) -> None:
    from florabase.media.service import unlink

    unlink(database, reference.id)


def target_photo_count(database: Session, target_type: TargetType, target_id: UUID) -> int:
    from sqlalchemy import func

    return int(
        database.scalar(
            select(func.count())
            .select_from(RecordMediaLink)
            .where(getattr(RecordMediaLink, TARGET_MODELS[target_type][1]) == target_id)
        )
        or 0
    )


def attachment_has_photo(database: Session, attachment_id: UUID) -> bool:
    return (
        database.scalar(
            select(RecordMediaLink.id)
            .join(MediaAsset, MediaAsset.id == RecordMediaLink.media_asset_id)
            .where(MediaAsset.attachment_id == attachment_id)
        )
        is not None
    )


def attachment_image_owner(database: Session, attachment_id: UUID) -> str | None:
    if attachment_has_photo(database, attachment_id):
        return "collection_photo"
    cover = database.scalar(
        select(BotanicalIdentityCoverImage.id)
        .join(MediaAsset, MediaAsset.id == BotanicalIdentityCoverImage.media_asset_id)
        .where(MediaAsset.attachment_id == attachment_id)
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
        .join(MediaAsset, MediaAsset.id == BotanicalIdentityCoverImage.media_asset_id)
        .options(contains_eager(BotanicalIdentityCoverImage.media_asset))
        .outerjoin(Attachment, Attachment.id == MediaAsset.attachment_id)
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
            media_asset_id=cover.media_asset_id,
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
        content_url=cover.content_url,
        thumbnail_url=cover.thumbnail_url,
        fetched_at=cover.fetched_at,
        id=cover.id,
        media_asset_id=cover.media_asset_id,
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
    if row is None or row[0].attachment_id is None:
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


async def set_local_identity_cover(
    database: Session, storage: AttachmentStorage, botanical_identity_id: UUID, upload: UploadFile
) -> LocalCoverResponse:
    from florabase.media.schemas import AssetMetadataWrite
    from florabase.media.service import upload_asset

    require_botanical_identity(database, botanical_identity_id, lock=True)
    row = get_identity_cover(database, botanical_identity_id, lock=True)
    asset = await upload_asset(database, storage, upload, AssetMetadataWrite(), commit=False)
    new_attachment = database.get(Attachment, asset.attachment_id)
    assert new_attachment is not None
    new_storage_key = new_attachment.storage_key
    try:
        cover = (
            row[0]
            if row
            else BotanicalIdentityCoverImage(
                id=uuid7(), botanical_identity_id=botanical_identity_id
            )
        )
        cover.source_mode = "local"
        cover.media_asset = asset
        cover.updated_at = datetime.now(UTC)
        database.add(cover)
        database.commit()
    except Exception as error:
        database.rollback()
        with suppress(AttachmentStorageError):
            storage.delete_file(new_storage_key)
        raise CollectionPhotoError(
            "cover_metadata_write_failed", "Could not save the local cover reference"
        ) from error
    attachment = database.get(Attachment, asset.attachment_id)
    return cast(LocalCoverResponse, cover_response(cover, attachment))


def set_external_identity_cover(
    database: Session,
    storage: AttachmentStorage,
    botanical_identity_id: UUID,
    payload: ExternalCoverWrite,
) -> ExternalCoverResponse:
    from florabase.media.schemas import ExternalAssetCreate
    from florabase.media.service import create_external_asset

    require_botanical_identity(database, botanical_identity_id, lock=True)
    row = get_identity_cover(database, botanical_identity_id, lock=True)
    asset = create_external_asset(
        database,
        ExternalAssetCreate(**payload.model_dump(exclude={"privacy_acknowledged"})),
        commit=False,
    )
    try:
        cover = (
            row[0]
            if row
            else BotanicalIdentityCoverImage(
                id=uuid7(), botanical_identity_id=botanical_identity_id
            )
        )
        cover.source_mode = "external"
        cover.media_asset = asset
        cover.updated_at = datetime.now(UTC)
        database.add(cover)
        database.commit()
    except Exception as error:
        database.rollback()
        raise CollectionPhotoError(
            "cover_metadata_write_failed", "Could not save the external cover reference"
        ) from error
    return cast(ExternalCoverResponse, cover_response(cover, None))


def delete_identity_cover(
    database: Session, storage: AttachmentStorage, botanical_identity_id: UUID
) -> bool:
    from florabase.media.service import require_asset

    require_botanical_identity(database, botanical_identity_id, lock=True)
    row = get_identity_cover(database, botanical_identity_id)
    if row is None:
        return False
    require_asset(database, row[0].media_asset_id, lock=True)
    database.delete(row[0])
    try:
        database.commit()
    except SQLAlchemyError as error:
        database.rollback()
        raise CollectionPhotoError(
            "cover_metadata_delete_failed",
            "Could not remove the cover reference. Refresh and retry.",
        ) from error
    return True
