"""Shared assets, exact links, guarded deletion and bounded directory queries."""

from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Protocol, cast
from uuid import UUID, uuid7

from fastapi import UploadFile
from PIL import Image
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, contains_eager
from sqlalchemy.sql.elements import ColumnElement

from florabase.attachments.model import Attachment, AttachmentState
from florabase.attachments.storage import AttachmentStorage, AttachmentStorageError
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.collection_photos.model import (
    BotanicalIdentityCoverImage,
    CollectionPrimaryPhoto,
    ExternalImageReference,
    LocalCollectionPhoto,
    MediaAsset,
    RecordMediaLink,
)
from florabase.collection_photos.service import TARGET_MODELS, CollectionPhotoError
from florabase.media.schemas import (
    AssetDetailResponse,
    AssetMetadataWrite,
    AssetPageResponse,
    AssetResponse,
    CoverReferenceResponse,
    ExternalAssetCreate,
    LinkResponse,
    LinkWrite,
    MediaTarget,
    MediaTargetFilter,
    TargetChoiceResponse,
    TargetPageResponse,
)
from florabase.suppliers.model import Supplier


class IdentifiedRecord(Protocol):
    id: UUID


class MediaError(CollectionPhotoError):
    def __init__(self, code: str, message: str, status: int = 409) -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(code, message)


def require_asset(database: Session, asset_id: UUID, *, lock: bool = False) -> MediaAsset:
    statement = select(MediaAsset).where(MediaAsset.id == asset_id)
    if lock:
        statement = statement.with_for_update()
    asset = database.scalar(statement.execution_options(populate_existing=True))
    if asset is None:
        raise MediaError("media_asset_not_found", "Media asset not found", 404)
    return asset


def require_active(database: Session, asset: MediaAsset) -> None:
    if asset.state != "active":
        raise MediaError("media_deletion_pending", "Media deletion is pending; retry deletion.")
    if asset.attachment_id is not None:
        attachment = database.get(Attachment, asset.attachment_id)
        if attachment is None or attachment.state != AttachmentState.ACTIVE:
            raise MediaError("media_unavailable", "The local image is unavailable.")


def reference_counts(database: Session, asset_id: UUID) -> tuple[int, int]:
    return (
        int(
            database.scalar(
                select(func.count())
                .select_from(RecordMediaLink)
                .where(RecordMediaLink.media_asset_id == asset_id)
            )
            or 0
        ),
        int(
            database.scalar(
                select(func.count())
                .select_from(BotanicalIdentityCoverImage)
                .where(BotanicalIdentityCoverImage.media_asset_id == asset_id)
            )
            or 0
        ),
    )


def asset_response(
    asset: MediaAsset, attachment: Attachment | None, links: int, covers: int
) -> AssetResponse:
    active = asset.state == "active" and (
        asset.attachment_id is None or (attachment is not None and attachment.state == "active")
    )
    return AssetResponse(
        id=asset.id,
        kind=cast(Literal["local", "external"], asset.kind),
        title=asset.title,
        attribution=asset.attribution,
        licence_label=asset.licence_label,
        licence_url=asset.licence_url,
        image_url=asset.image_url,
        source_url=asset.source_url,
        original_filename=attachment.original_filename if attachment else None,
        media_type=attachment.media_type if attachment else None,
        byte_size=attachment.byte_size if attachment else None,
        width=asset.width,
        height=asset.height,
        fetched_at=asset.fetched_at,
        local_copy_cleanup_pending=asset.copy_cleanup_attachment_id is not None,
        deletion_pending=not active,
        content_url=f"/api/v1/attachments/{attachment.id}/content"
        if active and attachment
        else None,
        thumbnail_url=f"/api/v1/media-assets/{asset.id}/thumbnail"
        + (f"?v={attachment.sha256}" if asset.kind == "external" and attachment else "")
        if active and attachment
        else None,
        collection_link_count=links,
        cover_reference_count=covers,
        can_delete=links == 0 and covers == 0,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


def read_asset(database: Session, asset_id: UUID) -> AssetResponse:
    asset = require_asset(database, asset_id)
    attachment = database.get(Attachment, asset.attachment_id) if asset.attachment_id else None
    return asset_response(asset, attachment, *reference_counts(database, asset_id))


def asset_text_match(query: str) -> ColumnElement[bool]:
    """Direct library metadata only; callers join the asset's own Attachment."""
    needle = "%" + query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    return or_(
        MediaAsset.title.ilike(needle, escape="\\"),
        MediaAsset.attribution.ilike(needle, escape="\\"),
        Attachment.original_filename.ilike(needle, escape="\\"),
    )


def list_assets(
    database: Session,
    *,
    query: str = "",
    kind: Literal["local", "external"] | None = None,
    association: Literal["all", "linked", "unlinked"] = "all",
    target: MediaTargetFilter | None = None,
    limit: int = 24,
    offset: int = 0,
) -> AssetPageResponse:
    link_counts = (
        select(RecordMediaLink.media_asset_id.label("asset_id"), func.count().label("total"))
        .group_by(RecordMediaLink.media_asset_id)
        .subquery()
    )
    cover_counts = (
        select(
            BotanicalIdentityCoverImage.media_asset_id.label("asset_id"),
            func.count().label("total"),
        )
        .group_by(BotanicalIdentityCoverImage.media_asset_id)
        .subquery()
    )
    filters = []
    if query.strip():
        filters.append(asset_text_match(query))
    if kind:
        filters.append(MediaAsset.kind == kind)
    has_links = (
        select(RecordMediaLink.id).where(RecordMediaLink.media_asset_id == MediaAsset.id).exists()
    )
    if association == "linked":
        filters.append(has_links)
    elif association == "unlinked":
        filters.append(~has_links)
    if target:
        filters.append(
            select(RecordMediaLink.id)
            .where(
                RecordMediaLink.media_asset_id == MediaAsset.id,
                or_(
                    *[
                        getattr(RecordMediaLink, column).is_not(None)
                        for column in (
                            "seed_lot_id",
                            "sowing_id",
                            "plant_id",
                            "plant_group_id",
                            "event_id",
                            "harvest_id",
                        )
                    ]
                )
                if target == "collection"
                else getattr(RecordMediaLink, TARGET_MODELS[target][1]).is_not(None),
            )
            .exists()
        )
    base = (
        select(MediaAsset)
        .outerjoin(Attachment, Attachment.id == MediaAsset.attachment_id)
        .where(*filters)
    )
    total = int(database.scalar(select(func.count()).select_from(base.subquery())) or 0)
    rows = database.execute(
        select(
            MediaAsset,
            Attachment,
            func.coalesce(link_counts.c.total, 0),
            func.coalesce(cover_counts.c.total, 0),
        )
        .outerjoin(Attachment, Attachment.id == MediaAsset.attachment_id)
        .outerjoin(link_counts, link_counts.c.asset_id == MediaAsset.id)
        .outerjoin(cover_counts, cover_counts.c.asset_id == MediaAsset.id)
        .where(*filters)
        .order_by(MediaAsset.created_at.desc(), MediaAsset.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return AssetPageResponse(
        items=[
            asset_response(asset, attachment, links, covers)
            for asset, attachment, links, covers in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


def target_of(link: RecordMediaLink) -> tuple[MediaTarget, UUID]:
    for target, (_, column) in TARGET_MODELS.items():
        value = getattr(link, column)
        if value is not None:
            return cast(MediaTarget, target), cast(UUID, value)
    raise MediaError("invalid_media_target", "The media link has no valid record target.")


def target_label(record: object, target: MediaTarget, *, include_id: bool = True) -> str:
    if target == "supplier":
        return cast(Supplier, record).name
    label = (
        getattr(record, "display_title", None)
        if target == "harvest"
        else getattr(record, "label", None)
    )
    if label:
        return str(label)
    if target == "event":
        label = f"{getattr(record, 'kind', 'Observation').replace('_', ' ').capitalize()} event"
    else:
        label = target.replace("_", " ").title()
    # UUIDv7's leading characters are a timestamp, shared by nearby creations.
    return f"{label} · {str(cast(IdentifiedRecord, record).id)[-8:]}" if include_id else label


def target_url(target: MediaTarget, target_id: UUID) -> str:
    routes = {
        "seed_lot": "seeds",
        "sowing": "sowings",
        "plant": "plants",
        "plant_group": "plant-groups",
        "event": "events",
        "harvest": "harvests",
        "supplier": "suppliers",
    }
    return f"#/{routes[target]}/{target_id}"


def link_response(link: RecordMediaLink, record: object, primary: bool) -> LinkResponse:
    target, target_id = target_of(link)
    return LinkResponse(
        id=link.id,
        media_asset_id=link.media_asset_id,
        target_type=target,
        target_id=target_id,
        target_label=target_label(record, target),
        target_url=target_url(target, target_id),
        caption=link.caption,
        display_order=link.display_order,
        is_primary=primary,
        created_at=link.created_at,
        updated_at=link.updated_at,
    )


def asset_detail(database: Session, asset_id: UUID) -> AssetDetailResponse:
    summary = read_asset(database, asset_id)
    links = database.scalars(
        select(RecordMediaLink)
        .where(RecordMediaLink.media_asset_id == asset_id)
        .order_by(RecordMediaLink.created_at, RecordMediaLink.id)
    ).all()
    # At most one batched target lookup per supported type, never one per link.
    records: dict[tuple[str, UUID], object] = {}
    for target, (model, column) in TARGET_MODELS.items():
        ids = [getattr(link, column) for link in links if getattr(link, column) is not None]
        if ids:
            if target == "harvest":
                from florabase.harvests.service import list_harvests

                records.update(
                    {(target, row.id): row for row in list_harvests(database, harvest_ids=ids)}
                )
            else:
                records.update(
                    {
                        (target, cast(IdentifiedRecord, row).id): row
                        for row in database.scalars(select(model).where(model.id.in_(ids)))
                    }
                )
    ids = [link.id for link in links]
    designations = (
        database.scalars(
            select(CollectionPrimaryPhoto).where(
                or_(
                    CollectionPrimaryPhoto.local_collection_photo_id.in_(ids),
                    CollectionPrimaryPhoto.external_image_reference_id.in_(ids),
                )
            )
        ).all()
        if ids
        else []
    )
    primary_ids = {
        row.local_collection_photo_id or row.external_image_reference_id for row in designations
    }
    covers = database.execute(
        select(BotanicalIdentityCoverImage, BotanicalIdentity)
        .join(
            BotanicalIdentity,
            BotanicalIdentity.id == BotanicalIdentityCoverImage.botanical_identity_id,
        )
        .where(BotanicalIdentityCoverImage.media_asset_id == asset_id)
    ).all()
    return AssetDetailResponse(
        **summary.model_dump(),
        links=[
            link_response(link, records[target_of(link)], link.id in primary_ids) for link in links
        ],
        covers=[
            CoverReferenceResponse(
                id=cover.id,
                botanical_identity_id=identity.id,
                label=identity.scientific_name,
                url=f"#/identities/{identity.id}",
            )
            for cover, identity in covers
        ],
    )


def lock_target(database: Session, target: MediaTarget, target_id: UUID) -> object:
    model, _ = TARGET_MODELS[target]
    record = database.scalar(select(model).where(model.id == target_id).with_for_update())
    if record is None:
        raise MediaError(
            "photo_target_not_found", "The record for this media link was not found.", 404
        )
    return record


def create_link(
    database: Session,
    target: MediaTarget,
    target_id: UUID,
    asset_id: UUID,
    metadata: LinkWrite,
    *,
    commit: bool = True,
) -> RecordMediaLink:
    lock_target(database, target, target_id)
    asset = require_asset(database, asset_id, lock=True)
    require_active(database, asset)
    _, column = TARGET_MODELS[target]
    if database.scalar(
        select(RecordMediaLink.id).where(
            RecordMediaLink.media_asset_id == asset_id,
            getattr(RecordMediaLink, column) == target_id,
        )
    ):
        raise MediaError("duplicate_media_link", "This record already links to that media asset.")
    cls = LocalCollectionPhoto if asset.kind == "local" else ExternalImageReference
    link = cls(id=uuid7(), media_asset=asset, **{column: target_id}, **metadata.model_dump())
    database.add(link)
    try:
        database.flush()
        if commit:
            database.commit()
    except IntegrityError as error:
        database.rollback()
        raise MediaError(
            "media_link_conflict",
            "The media link conflicted with another change. Refresh and try again.",
        ) from error
    return link


def locked_link(
    database: Session, link_id: UUID, *, expected: tuple[MediaTarget, UUID] | None = None
) -> RecordMediaLink | None:
    # Discover immutable identity, then lock target -> asset -> link consistently.
    link = database.scalar(select(RecordMediaLink).where(RecordMediaLink.id == link_id))
    if link is None:
        return None
    target, target_id = target_of(link)
    if expected is not None and expected != (target, target_id):
        raise MediaError(
            "primary_photo_wrong_target", "Photo does not belong to this collection record"
        )
    lock_target(database, target, target_id)
    require_asset(database, link.media_asset_id, lock=True)
    return database.scalar(
        select(RecordMediaLink)
        .join(MediaAsset, MediaAsset.id == RecordMediaLink.media_asset_id)
        .options(contains_eager(RecordMediaLink.media_asset))
        .where(RecordMediaLink.id == link_id)
        .with_for_update(of=RecordMediaLink)
        .execution_options(populate_existing=True)
    )


def unlink(database: Session, link_id: UUID) -> bool:
    link = locked_link(database, link_id)
    if link is None:
        return False
    # PostgreSQL CASCADE clears only designations referencing this exact link.
    database.delete(link)
    database.commit()
    return True


def update_link(database: Session, link_id: UUID, metadata: LinkWrite) -> LinkResponse:
    link = locked_link(database, link_id)
    if link is None:
        raise MediaError("media_link_not_found", "Media link not found.", 404)
    require_active(database, link.media_asset)
    link.caption, link.display_order = metadata.caption, metadata.display_order
    link.updated_at = datetime.now(UTC)
    target, target_id = target_of(link)
    record = database.get(TARGET_MODELS[target][0], target_id)
    primary = (
        database.scalar(
            select(CollectionPrimaryPhoto.id).where(
                or_(
                    CollectionPrimaryPhoto.local_collection_photo_id == link_id,
                    CollectionPrimaryPhoto.external_image_reference_id == link_id,
                )
            )
        )
        is not None
    )
    database.commit()
    return link_response(link, record, primary)


def next_order(database: Session, target: MediaTarget, target_id: UUID) -> int:
    lock_target(database, target, target_id)
    value = database.scalar(
        select(func.max(RecordMediaLink.display_order)).where(
            getattr(RecordMediaLink, TARGET_MODELS[target][1]) == target_id
        )
    )
    return int(value) + 1 if value is not None else 0


async def upload_asset(
    database: Session,
    storage: AttachmentStorage,
    upload: UploadFile,
    metadata: AssetMetadataWrite,
    *,
    target: MediaTarget | None = None,
    target_id: UUID | None = None,
    caption: str | None = None,
    commit: bool = True,
) -> MediaAsset:
    order = next_order(database, target, target_id) if target and target_id else 0
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
        asset = MediaAsset(
            id=uuid7(),
            kind="local",
            attachment_id=attachment.id,
            width=width,
            height=height,
            state="active",
            **metadata.model_dump(),
        )
        database.add(attachment)
        database.flush()
        database.add(asset)
        database.flush()
        if target and target_id:
            create_link(
                database,
                target,
                target_id,
                asset.id,
                LinkWrite(caption=caption, display_order=order),
                commit=False,
            )
        if commit:
            database.commit()
    except Exception:
        database.rollback()
        with suppress(OSError):
            stored.path.unlink(missing_ok=True)
        raise
    return asset


def create_external_asset(
    database: Session,
    metadata: ExternalAssetCreate,
    *,
    target: MediaTarget | None = None,
    target_id: UUID | None = None,
    caption: str | None = None,
    commit: bool = True,
) -> MediaAsset:
    order = next_order(database, target, target_id) if target and target_id else 0
    asset = MediaAsset(id=uuid7(), kind="external", state="active", **metadata.model_dump())
    try:
        database.add(asset)
        database.flush()
        if target and target_id:
            create_link(
                database,
                target,
                target_id,
                asset.id,
                LinkWrite(caption=caption, display_order=order),
                commit=False,
            )
        if commit:
            database.commit()
    except Exception:
        database.rollback()
        raise
    return asset


def update_asset(database: Session, asset_id: UUID, metadata: AssetMetadataWrite) -> AssetResponse:
    asset = require_asset(database, asset_id, lock=True)
    require_active(database, asset)
    if asset.kind == "external" and not metadata.attribution:
        raise MediaError("media_attribution_required", "External media requires attribution.", 422)
    for field, value in metadata.model_dump().items():
        setattr(asset, field, value)
    asset.updated_at = datetime.now(UTC)
    database.commit()
    return read_asset(database, asset_id)


def delete_asset(database: Session, storage: AttachmentStorage, asset_id: UUID) -> None:
    asset = require_asset(database, asset_id, lock=True)
    links, covers = reference_counts(database, asset_id)
    if links or covers:
        raise MediaError(
            "media_asset_referenced",
            f"Cannot delete this media asset: {links} record link(s) and "
            f"{covers} BotanicalIdentity cover reference(s) remain. "
            "Unlink or remove those references first.",
        )
    if asset.kind == "external":
        from florabase.media.copies import cleanup_copy

        cleanup_copy(database, storage, asset)
    if asset.attachment_id is None:
        database.delete(asset)
        database.commit()
        return
    attachment = database.scalar(
        select(Attachment).where(Attachment.id == asset.attachment_id).with_for_update()
    )
    if attachment is None:
        raise MediaError(
            "media_attachment_missing",
            "Stored image metadata is missing; operator recovery is required.",
        )
    was_active = attachment.state == AttachmentState.ACTIVE
    if asset.state == "active" or was_active:
        asset.state = "pending_delete"
        attachment.state = AttachmentState.PENDING_DELETE
        database.commit()
    asset = require_asset(database, asset_id, lock=True)
    attachment = database.scalar(
        select(Attachment).where(Attachment.id == asset.attachment_id).with_for_update()
    )
    assert attachment is not None
    removed = storage.delete_file(attachment.storage_key)
    if was_active and not removed:
        raise MediaError(
            "attachment_content_missing",
            "Image content was already missing; deletion is pending a retry.",
        )
    delete_thumbnail(storage, asset, attachment)
    database.delete(asset)
    database.flush()
    database.delete(attachment)
    database.commit()


def target_choices(
    database: Session, target: MediaTarget, query: str, limit: int, offset: int
) -> TargetPageResponse:
    from sqlalchemy import String
    from sqlalchemy import cast as sql_cast
    from sqlalchemy.orm import InstrumentedAttribute

    from florabase.events.model import Event
    from florabase.harvests.model import Harvest
    from florabase.plants.model import Plant, PlantGroup
    from florabase.seed_lots.model import SeedLot
    from florabase.sowings.model import Sowing

    if target == "supplier":
        suppliers = select(Supplier)
        if query.strip():
            needle = (
                "%"
                + query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                + "%"
            )
            suppliers = suppliers.where(Supplier.name.ilike(needle, escape="\\"))
        total = int(database.scalar(select(func.count()).select_from(suppliers.subquery())) or 0)
        supplier_rows = database.scalars(
            suppliers.order_by(func.lower(Supplier.name), Supplier.id).limit(limit).offset(offset)
        ).all()
        return TargetPageResponse(
            items=[
                TargetChoiceResponse(
                    id=row.id, label=row.name + (" · Retired" if row.retired_at else "")
                )
                for row in supplier_rows
            ],
            total=total,
            limit=limit,
            offset=offset,
        )

    identity_id: ColumnElement[UUID] | InstrumentedAttribute[UUID]
    model, _ = TARGET_MODELS[target]
    statement = select(model, BotanicalIdentity)
    if target == "sowing":
        statement = statement.join(SeedLot, SeedLot.id == Sowing.seed_lot_id)
        identity_id = SeedLot.botanical_identity_id
    elif target in {"event", "harvest"}:
        statement = statement.outerjoin(
            Plant, Plant.id == (Event.plant_id if target == "event" else Harvest.plant_id)
        ).outerjoin(
            PlantGroup,
            PlantGroup.id
            == (Event.plant_group_id if target == "event" else Harvest.plant_group_id),
        )
        identity_id = func.coalesce(Plant.botanical_identity_id, PlantGroup.botanical_identity_id)
    elif target == "seed_lot":
        identity_id = SeedLot.botanical_identity_id
    elif target == "plant":
        identity_id = Plant.botanical_identity_id
    else:
        identity_id = PlantGroup.botanical_identity_id
    statement = statement.outerjoin(BotanicalIdentity, BotanicalIdentity.id == identity_id)
    if query.strip():
        needle = (
            "%" + query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        )
        conditions = [
            sql_cast(model.id, String).ilike(needle, escape="\\"),
            BotanicalIdentity.scientific_name.ilike(needle, escape="\\"),
            BotanicalIdentity.common_name.ilike(needle, escape="\\"),
            BotanicalIdentity.cultivar_name.ilike(needle, escape="\\"),
        ]
        label_column = getattr(model, "label", None)
        if label_column is not None:
            conditions.append(label_column.ilike(needle, escape="\\"))
        if target == "harvest":
            conditions.extend(
                [
                    Plant.label.ilike(needle, escape="\\"),
                    PlantGroup.label.ilike(needle, escape="\\"),
                ]
            )
        if target == "event":
            conditions.append(Event.kind.ilike(needle, escape="\\"))
        statement = statement.where(or_(*conditions))
    total = int(database.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = database.execute(
        statement.order_by(model.created_at.desc(), model.id).limit(limit).offset(offset)
    ).all()
    harvest_titles: dict[UUID, str] = {}
    if target == "harvest" and rows:
        from florabase.harvests.service import list_harvests

        harvest_titles = {
            row.id: row.display_title
            for row in list_harvests(database, harvest_ids=[record.id for record, _ in rows])
        }
    choices = []
    for record, identity in rows:
        label = target_label(record, target, include_id=False)
        if not getattr(record, "label", None) and identity is not None:
            label = identity.common_name or identity.cultivar_name or identity.scientific_name
            if target == "event":
                label = f"{target_label(record, target, include_id=False)} · {label}"
        if target == "harvest":
            label = harvest_titles[record.id]
        lifecycle = getattr(record, "lifecycle", "active")
        if lifecycle != "active":
            label += f" · {lifecycle}"
        suffix = str(record.id)[-8:]
        choices.append(TargetChoiceResponse(id=record.id, label=f"{label} · {suffix}"))
    return TargetPageResponse(items=choices, total=total, limit=limit, offset=offset)


def asset_thumbnail(storage: AttachmentStorage, asset: MediaAsset, attachment: Attachment) -> bytes:
    """One regenerable derivative per asset, separate from backed-up originals.

    Caller holds the asset row lock. This also makes first generation single-writer
    across record/cover/gallery requests and all backend processes.
    """
    import os
    import tempfile

    from florabase.collection_photos.service import render_identity_cover_thumbnail

    original = storage.active_path(attachment.storage_key, attachment.byte_size)
    directory = storage._owned_directory(".thumbnails")
    cache = directory / f"{asset.id.hex}-320-webp-v1-{attachment.sha256}.webp"
    if cache.is_symlink():
        raise AttachmentStorageError("unsafe_storage_path", "Stored thumbnail location is unsafe")
    if cache.exists():
        try:
            return cache.read_bytes()
        except OSError as error:
            raise AttachmentStorageError(
                "attachment_content_unavailable", "Could not read stored thumbnail."
            ) from error
    content = render_identity_cover_thumbnail(original)
    temporary: str | None = None
    try:
        descriptor, temporary = tempfile.mkstemp(prefix="thumbnail-", dir=directory)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
        os.replace(temporary, cache)
    except OSError as error:
        raise AttachmentStorageError(
            "attachment_content_unavailable", "Could not store thumbnail; retry loading."
        ) from error
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)
    return content


def delete_thumbnail(storage: AttachmentStorage, asset: MediaAsset, attachment: Attachment) -> None:
    cache = storage._owned_directory(".thumbnails") / (
        f"{asset.id.hex}-320-webp-v1-{attachment.sha256}.webp"
    )
    if cache.is_symlink():
        raise AttachmentStorageError("unsafe_storage_path", "Stored thumbnail location is unsafe")
    try:
        cache.unlink(missing_ok=True)
    except OSError as error:
        raise AttachmentStorageError(
            "attachment_delete_failed", "Could not remove thumbnail; retry deletion."
        ) from error
