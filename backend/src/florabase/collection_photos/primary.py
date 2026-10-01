"""Explicit representative photos for concrete collection records."""

from datetime import UTC, datetime
from typing import Literal, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, contains_eager

from florabase.attachments.model import Attachment, AttachmentState
from florabase.attachments.storage import AttachmentStorage, AttachmentStorageError
from florabase.collection_photos.model import (
    CollectionPrimaryPhoto,
    ExternalImageReference,
    LocalCollectionPhoto,
    MediaAsset,
)
from florabase.collection_photos.schemas import PrimaryPhotoResponse, PrimaryPhotoSelection
from florabase.collection_photos.service import CollectionPhotoError
from florabase.harvests.model import Harvest
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot

PrimaryTarget = Literal["seed_lot", "plant", "plant_group", "harvest"]
TARGETS: dict[str, tuple[type[SeedLot] | type[Plant] | type[PlantGroup] | type[Harvest], str]] = {
    "seed_lot": (SeedLot, "seed_lot_id"),
    "plant": (Plant, "plant_id"),
    "plant_group": (PlantGroup, "plant_group_id"),
    "harvest": (Harvest, "harvest_id"),
}


def _target_column(target: PrimaryTarget) -> str:
    return TARGETS[target][1]


def _require_target(
    database: Session, target: PrimaryTarget, target_id: UUID, *, lock: bool
) -> None:
    column = TARGETS[target][0].id
    statement = select(column).where(column == target_id)
    if lock:
        statement = statement.with_for_update()
    if database.scalar(statement) is None:
        raise CollectionPhotoError("photo_target_not_found", "Collection record not found")


def _designation(
    database: Session, target: PrimaryTarget, target_id: UUID
) -> CollectionPrimaryPhoto | None:
    return database.scalar(
        select(CollectionPrimaryPhoto)
        .where(getattr(CollectionPrimaryPhoto, _target_column(target)) == target_id)
        .with_for_update()
    )


def _summary(
    designation: CollectionPrimaryPhoto,
    target: PrimaryTarget,
    locals_by_id: dict[UUID, tuple[LocalCollectionPhoto, Attachment]],
    externals_by_id: dict[UUID, ExternalImageReference],
) -> PrimaryPhotoResponse | None:
    if designation.local_collection_photo_id is not None:
        pair = locals_by_id.get(designation.local_collection_photo_id)
        if (
            pair is None
            or pair[1].state != AttachmentState.ACTIVE
            or getattr(pair[0], _target_column(target))
            != getattr(designation, _target_column(target))
        ):
            return None
        return PrimaryPhotoResponse(
            kind="local",
            photo_id=pair[0].id,
            thumbnail_url=f"/api/v1/media-assets/{pair[0].media_asset_id}/thumbnail",
        )
    if designation.external_image_reference_id is not None:
        reference = externals_by_id.get(designation.external_image_reference_id)
        if reference is not None and getattr(reference, _target_column(target)) == getattr(
            designation, _target_column(target)
        ):
            return PrimaryPhotoResponse(
                kind="external", photo_id=reference.id, thumbnail_url=reference.thumbnail_url
            )
    return None


def primary_summaries(
    database: Session, target: PrimaryTarget, ids: list[UUID]
) -> dict[UUID, PrimaryPhotoResponse]:
    if not ids:
        return {}
    column = _target_column(target)
    designations = database.scalars(
        select(CollectionPrimaryPhoto).where(getattr(CollectionPrimaryPhoto, column).in_(ids))
    ).all()
    local_ids = [
        row.local_collection_photo_id for row in designations if row.local_collection_photo_id
    ]
    external_ids = [
        row.external_image_reference_id for row in designations if row.external_image_reference_id
    ]
    locals_by_id: dict[UUID, tuple[LocalCollectionPhoto, Attachment]] = {}
    if local_ids:
        locals_by_id = {
            photo.id: (photo, attachment)
            for photo, attachment in database.execute(
                select(LocalCollectionPhoto, Attachment)
                .join(MediaAsset, MediaAsset.id == LocalCollectionPhoto.media_asset_id)
                .options(contains_eager(LocalCollectionPhoto.media_asset))
                .join(Attachment, Attachment.id == MediaAsset.attachment_id)
                .where(LocalCollectionPhoto.id.in_(local_ids))
            )
        }
    externals_by_id = (
        {
            reference.id: reference
            for reference in database.scalars(
                select(ExternalImageReference)
                .join(MediaAsset, MediaAsset.id == ExternalImageReference.media_asset_id)
                .options(contains_eager(ExternalImageReference.media_asset))
                .where(ExternalImageReference.id.in_(external_ids))
            )
        }
        if external_ids
        else {}
    )
    result: dict[UUID, PrimaryPhotoResponse] = {}
    for row in designations:
        target_id = cast(UUID, getattr(row, column))
        summary = _summary(row, target, locals_by_id, externals_by_id)
        if summary is not None:
            result[target_id] = summary
    return result


def read_primary(
    database: Session, target: PrimaryTarget, target_id: UUID
) -> PrimaryPhotoResponse | None:
    _require_target(database, target, target_id, lock=False)
    return primary_summaries(database, target, [target_id]).get(target_id)


def set_primary(
    database: Session,
    storage: AttachmentStorage,
    target: PrimaryTarget,
    target_id: UUID,
    selection: PrimaryPhotoSelection,
) -> PrimaryPhotoResponse:
    _require_target(database, target, target_id, lock=True)
    model = LocalCollectionPhoto if selection.kind == "local" else ExternalImageReference
    from florabase.media.service import locked_link, require_active

    photo = locked_link(database, selection.photo_id, expected=(target, target_id))
    if photo is None or not isinstance(photo, model):
        raise CollectionPhotoError("primary_photo_not_found", "Collection photo not found")
    if getattr(photo, _target_column(target)) != target_id:
        raise CollectionPhotoError(
            "primary_photo_wrong_target", "Photo does not belong to this collection record"
        )
    require_active(database, photo.media_asset)
    if photo.attachment_id is not None:
        attachment = database.scalar(
            select(Attachment).where(Attachment.id == photo.attachment_id).with_for_update()
        )
        if attachment is None or attachment.state != AttachmentState.ACTIVE:
            raise CollectionPhotoError(
                "primary_photo_unavailable", "Uploaded photo is unavailable or pending deletion"
            )
        try:
            storage.active_path(attachment.storage_key, attachment.byte_size)
        except AttachmentStorageError as error:
            raise CollectionPhotoError(
                "primary_photo_unavailable", "Uploaded photo content is unavailable"
            ) from error
    row = _designation(database, target, target_id)
    if row is None:
        row = CollectionPrimaryPhoto(**{_target_column(target): target_id})
        database.add(row)
    row.local_collection_photo_id = selection.photo_id if selection.kind == "local" else None
    row.external_image_reference_id = selection.photo_id if selection.kind == "external" else None
    row.updated_at = datetime.now(UTC)
    database.commit()
    return PrimaryPhotoResponse(
        kind=selection.kind,
        photo_id=selection.photo_id,
        thumbnail_url=photo.thumbnail_url,
    )


def clear_primary(database: Session, target: PrimaryTarget, target_id: UUID) -> None:
    _require_target(database, target, target_id, lock=True)
    row = _designation(database, target, target_id)
    if row is not None:
        database.delete(row)
        database.commit()


def clear_photo_primary(
    database: Session, kind: Literal["local", "external"], photo_id: UUID
) -> None:
    column = (
        CollectionPrimaryPhoto.local_collection_photo_id
        if kind == "local"
        else CollectionPrimaryPhoto.external_image_reference_id
    )
    row = database.scalar(
        select(CollectionPrimaryPhoto).where(column == photo_id).with_for_update()
    )
    if isinstance(row, CollectionPrimaryPhoto):
        database.delete(row)
        database.flush()
