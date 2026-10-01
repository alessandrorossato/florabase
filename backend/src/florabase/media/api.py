import asyncio
from typing import Annotated, Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from florabase.attachments.api import _http_error as attachment_error
from florabase.attachments.api import get_attachment_storage
from florabase.attachments.model import Attachment
from florabase.attachments.storage import AttachmentStorage, AttachmentStorageError
from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
    require_owner,
)
from florabase.collection_photos.service import TARGET_MODELS
from florabase.db.session import get_database_session
from florabase.media import service
from florabase.media.schemas import (
    AssetDetailResponse,
    AssetMetadataWrite,
    AssetPageResponse,
    AssetResponse,
    ExternalAssetCreate,
    LinkCreate,
    LinkResponse,
    LinkWrite,
    MediaTarget,
    TargetPageResponse,
)

router = APIRouter(tags=["media library"])
Database = Annotated[Session, Depends(get_database_session)]
Storage = Annotated[AttachmentStorage, Depends(get_attachment_storage)]
Reader = Annotated[AuthenticatedActor, Depends(require_authenticated_actor)]
Writer = Annotated[AuthenticatedActor, Depends(require_csrf)]


def _write_error() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "code": "media_write_failed",
            "message": "Could not save this media change. Refresh and retry.",
        },
    )


def _error(error: service.MediaError) -> HTTPException:
    return HTTPException(
        status_code=error.status, detail={"code": error.code, "message": error.message}
    )


@router.get("/media-assets", response_model=AssetPageResponse, operation_id="listMediaAssets")
def list_media(
    database: Database,
    _actor: Reader,
    query: str = Query(default="", max_length=200),
    kind: Literal["local", "external"] | None = None,
    association: Literal["all", "linked", "unlinked"] = "all",
    target: MediaTarget | None = None,
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AssetPageResponse:
    return service.list_assets(
        database,
        query=query,
        kind=kind,
        association=association,
        target=target,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/media-targets/{target_type}",
    response_model=TargetPageResponse,
    operation_id="listMediaTargets",
)
def list_targets(
    target_type: MediaTarget,
    database: Database,
    _actor: Reader,
    query: str = Query(default="", max_length=200),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> TargetPageResponse:
    return service.target_choices(database, target_type, query, limit, offset)


@router.get(
    "/media-assets/{asset_id}", response_model=AssetDetailResponse, operation_id="getMediaAsset"
)
def get_media(asset_id: UUID, database: Database, _actor: Reader) -> AssetDetailResponse:
    try:
        return service.asset_detail(database, asset_id)
    except service.MediaError as error:
        raise _error(error) from error


@router.post(
    "/media-assets/local",
    response_model=AssetResponse,
    status_code=201,
    operation_id="uploadMediaAsset",
)
async def upload_media(
    database: Database,
    storage: Storage,
    actor: Writer,
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form(max_length=2000)] = None,
    attribution: Annotated[str | None, Form(max_length=2000)] = None,
) -> AssetResponse:
    require_owner(actor)
    try:
        metadata = AssetMetadataWrite(title=title, attribution=attribution)
        asset = await service.upload_asset(database, storage, file, metadata)
        return service.read_asset(database, asset.id)
    except ValidationError as error:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_media_metadata",
                "message": "Check the media title and attribution.",
            },
        ) from error
    except AttachmentStorageError as error:
        raise attachment_error(error) from error
    except SQLAlchemyError as error:
        database.rollback()
        raise HTTPException(
            status_code=503,
            detail={"code": "media_write_failed", "message": "Could not save this media asset."},
        ) from error


@router.post(
    "/media-assets/external",
    response_model=AssetResponse,
    status_code=201,
    operation_id="createExternalMediaAsset",
)
def create_external(
    payload: ExternalAssetCreate, database: Database, actor: Writer
) -> AssetResponse:
    require_owner(actor)
    try:
        asset = service.create_external_asset(database, payload)
        return service.read_asset(database, asset.id)
    except service.MediaError as error:
        raise _error(error) from error
    except SQLAlchemyError as error:
        database.rollback()
        raise _write_error() from error


@router.patch(
    "/media-assets/{asset_id}", response_model=AssetResponse, operation_id="updateMediaAsset"
)
def edit_media(
    asset_id: UUID, payload: AssetMetadataWrite, database: Database, actor: Writer
) -> AssetResponse:
    require_owner(actor)
    try:
        return service.update_asset(database, asset_id, payload)
    except service.MediaError as error:
        raise _error(error) from error
    except SQLAlchemyError as error:
        database.rollback()
        raise _write_error() from error


@router.delete("/media-assets/{asset_id}", status_code=204, operation_id="deleteMediaAsset")
def delete_media(asset_id: UUID, database: Database, storage: Storage, actor: Writer) -> Response:
    require_owner(actor)
    try:
        service.delete_asset(database, storage, asset_id)
    except service.MediaError as error:
        raise _error(error) from error
    except AttachmentStorageError as error:
        raise attachment_error(error) from error
    except SQLAlchemyError as error:
        database.rollback()
        raise HTTPException(
            status_code=503,
            detail={
                "code": "media_delete_failed",
                "message": "Deletion could not complete; refresh and retry.",
            },
        ) from error
    return Response(status_code=204)


@router.post(
    "/collection-records/{target_type}/{target_id}/media-links",
    response_model=LinkResponse,
    status_code=201,
    operation_id="linkRecordMedia",
)
def link_media(
    target_type: MediaTarget,
    target_id: UUID,
    payload: LinkCreate,
    database: Database,
    actor: Writer,
) -> LinkResponse:
    require_owner(actor)
    try:
        link = service.create_link(
            database,
            target_type,
            target_id,
            payload.media_asset_id,
            LinkWrite(caption=payload.caption, display_order=payload.display_order),
        )
        record = database.get(TARGET_MODELS[target_type][0], target_id)
        return service.link_response(link, record, False)
    except service.MediaError as error:
        raise _error(error) from error
    except SQLAlchemyError as error:
        database.rollback()
        raise _write_error() from error


@router.patch(
    "/media-links/{link_id}", response_model=LinkResponse, operation_id="updateRecordMediaLink"
)
def edit_link(link_id: UUID, payload: LinkWrite, database: Database, actor: Writer) -> LinkResponse:
    require_owner(actor)
    try:
        return service.update_link(database, link_id, payload)
    except service.MediaError as error:
        raise _error(error) from error
    except SQLAlchemyError as error:
        database.rollback()
        raise _write_error() from error


@router.delete("/media-links/{link_id}", status_code=204, operation_id="unlinkRecordMedia")
def unlink_media(link_id: UUID, database: Database, actor: Writer) -> Response:
    require_owner(actor)
    try:
        if not service.unlink(database, link_id):
            raise service.MediaError("media_link_not_found", "Media link not found.", 404)
    except service.MediaError as error:
        raise _error(error) from error
    except SQLAlchemyError as error:
        database.rollback()
        raise _write_error() from error
    return Response(status_code=204)


@router.get(
    "/media-assets/{asset_id}/thumbnail",
    response_class=Response,
    responses={
        200: {"content": {"image/webp": {}}, "description": "Shared bounded local thumbnail"}
    },
    operation_id="getMediaAssetThumbnail",
)
def thumbnail(
    asset_id: UUID,
    database: Database,
    storage: Storage,
    _actor: Reader,
    if_none_match: Annotated[str | None, Header()] = None,
) -> Response:
    try:
        asset = service.require_asset(database, asset_id, lock=True)
        service.require_active(database, asset)
        if asset.attachment_id is None:
            raise service.MediaError(
                "media_thumbnail_unavailable", "This reference has no saved local copy.", 404
            )
        attachment = database.get(Attachment, asset.attachment_id)
        assert attachment is not None
        storage.active_path(attachment.storage_key, attachment.byte_size)
        etag = f'"media-{attachment.sha256}-320-webp-v1"'
        headers = {
            "Cache-Control": "private, max-age=86400, must-revalidate",
            "ETag": etag,
            "Vary": "Cookie",
            "X-Content-Type-Options": "nosniff",
        }
        validators = {value.strip() for value in (if_none_match or "").split(",")}
        if "*" in validators or etag in validators or f"W/{etag}" in validators:
            return Response(status_code=304, headers=headers)
        content = service.asset_thumbnail(storage, asset, attachment)
        return Response(content=content, media_type="image/webp", headers=headers)
    except service.MediaError as error:
        raise _error(error) from error
    except AttachmentStorageError as error:
        raise attachment_error(error) from error


def _copy_operation(
    asset_id: UUID, database: Database, storage: Storage, actor: Writer, *, refresh: bool
) -> AssetResponse:
    from florabase.media.copies import save_copy
    from florabase.media.fetch import ExternalFetchError

    require_owner(actor)
    try:
        asyncio.run(save_copy(database, storage, asset_id, refresh=refresh))
        return service.read_asset(database, asset_id)
    except ExternalFetchError as error:
        database.rollback()
        raise HTTPException(
            status_code=422, detail={"code": "external_fetch_failed", "message": str(error)}
        ) from error
    except service.MediaError as error:
        database.rollback()
        raise _error(error) from error
    except AttachmentStorageError as error:
        database.rollback()
        raise attachment_error(error) from error
    except SQLAlchemyError as error:
        database.rollback()
        raise _write_error() from error


@router.post(
    "/media-assets/{asset_id}/save-local-copy",
    response_model=AssetResponse,
    operation_id="saveExternalMediaLocalCopy",
)
def save_local_copy(
    asset_id: UUID, database: Database, storage: Storage, actor: Writer
) -> AssetResponse:
    return _copy_operation(asset_id, database, storage, actor, refresh=False)


@router.post(
    "/media-assets/{asset_id}/refresh-local-copy",
    response_model=AssetResponse,
    operation_id="refreshExternalMediaLocalCopy",
)
def refresh_local_copy(
    asset_id: UUID, database: Database, storage: Storage, actor: Writer
) -> AssetResponse:
    return _copy_operation(asset_id, database, storage, actor, refresh=True)


@router.delete(
    "/media-assets/{asset_id}/local-copy",
    response_model=AssetResponse,
    operation_id="removeExternalMediaLocalCopy",
)
def remove_local_copy(
    asset_id: UUID, database: Database, storage: Storage, actor: Writer
) -> AssetResponse:
    from florabase.media.copies import remove_copy

    require_owner(actor)
    try:
        remove_copy(database, storage, asset_id)
        return service.read_asset(database, asset_id)
    except service.MediaError as error:
        database.rollback()
        raise _error(error) from error
    except AttachmentStorageError as error:
        database.rollback()
        raise attachment_error(error) from error
    except SQLAlchemyError as error:
        database.rollback()
        raise _write_error() from error
