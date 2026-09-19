from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from pydantic import ValidationError
from sqlalchemy.orm import Session

from florabase.attachments.api import _http_error as attachment_http_error
from florabase.attachments.api import get_attachment_storage
from florabase.attachments.storage import AttachmentStorage, AttachmentStorageError
from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
    require_owner,
)
from florabase.collection_photos.model import ExternalImageReference
from florabase.collection_photos.schemas import (
    BotanicalIdentityCoverResponse,
    CollectionPhotoResponse,
    ExternalCoverResponse,
    ExternalCoverWrite,
    ExternalImageCreate,
    ExternalImageResponse,
    ExternalImageUpdate,
    LocalCoverResponse,
    LocalPhotoResponse,
    LocalPhotoUpdate,
    PhotoMetadataWrite,
)
from florabase.collection_photos.service import (
    CollectionPhotoError,
    TargetType,
    create_external_image,
    delete_external_image,
    delete_identity_cover,
    delete_local_photo,
    get_external_image,
    get_local_photo,
    list_photos,
    local_identity_cover_attachment,
    read_identity_cover,
    render_identity_cover_thumbnail,
    set_external_identity_cover,
    set_local_identity_cover,
    update_external_image,
    update_local_photo,
    upload_local_photo,
)
from florabase.db.session import get_database_session

router = APIRouter(tags=["collection photos"])


def _error(error: CollectionPhotoError) -> HTTPException:
    response_status = {
        "photo_target_not_found": status.HTTP_404_NOT_FOUND,
        "botanical_identity_not_found": status.HTTP_404_NOT_FOUND,
        "photo_deletion_pending": status.HTTP_409_CONFLICT,
        "attachment_content_missing": status.HTTP_409_CONFLICT,
        "cover_attachment_missing": status.HTTP_409_CONFLICT,
        "cover_external_metadata_missing": status.HTTP_409_CONFLICT,
    }.get(error.code, status.HTTP_503_SERVICE_UNAVAILABLE)
    return HTTPException(
        status_code=response_status,
        detail={"code": error.code, "message": error.message},
    )


def _missing(kind: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": f"{kind}_not_found", "message": "Photo reference not found"},
    )


def _external_response(reference: ExternalImageReference) -> ExternalImageResponse:
    return ExternalImageResponse.model_validate(reference, from_attributes=True)


@router.get(
    "/botanical-identities/{botanical_identity_id}/cover-image",
    response_model=BotanicalIdentityCoverResponse | None,
    operation_id="getBotanicalIdentityCoverImage",
)
def get_botanical_identity_cover_image(
    botanical_identity_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> LocalCoverResponse | ExternalCoverResponse | None:
    try:
        return read_identity_cover(database, botanical_identity_id)
    except CollectionPhotoError as error:
        raise _error(error) from error


@router.get(
    "/botanical-identities/{botanical_identity_id}/cover-image/thumbnail",
    response_class=Response,
    responses={
        200: {
            "content": {"image/webp": {}},
            "description": "Bounded local BotanicalIdentity cover thumbnail",
        }
    },
    operation_id="getBotanicalIdentityCoverThumbnail",
)
def get_botanical_identity_cover_thumbnail(
    botanical_identity_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
    storage: Annotated[AttachmentStorage, Depends(get_attachment_storage)],
    if_none_match: Annotated[str | None, Header()] = None,
) -> Response:
    try:
        attachment = local_identity_cover_attachment(database, botanical_identity_id)
        if attachment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "botanical_identity_cover_thumbnail_not_available",
                    "message": "A local cover thumbnail is not available",
                },
            )
        etag = f'"cover-{attachment.sha256}-320-webp-v1"'
        headers = {
            "Cache-Control": "private, max-age=86400, must-revalidate",
            "ETag": etag,
            "Vary": "Cookie",
            "X-Content-Type-Options": "nosniff",
        }
        validators = {validator.strip() for validator in (if_none_match or "").split(",")}
        if "*" in validators or etag in validators or f"W/{etag}" in validators:
            return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
        path = storage.active_path(attachment.storage_key, attachment.byte_size)
        content = render_identity_cover_thumbnail(path)
        return Response(content=content, media_type="image/webp", headers=headers)
    except AttachmentStorageError as error:
        raise attachment_http_error(error) from error
    except CollectionPhotoError as error:
        raise _error(error) from error


@router.post(
    "/botanical-identities/{botanical_identity_id}/cover-image/local",
    response_model=LocalCoverResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="setLocalBotanicalIdentityCoverImage",
)
async def set_local_botanical_identity_cover_image(
    botanical_identity_id: UUID,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
    storage: Annotated[AttachmentStorage, Depends(get_attachment_storage)],
    file: Annotated[UploadFile, File(description="JPEG, PNG, or WebP identity cover")],
) -> LocalCoverResponse:
    require_owner(actor)
    try:
        result = await set_local_identity_cover(database, storage, botanical_identity_id, file)
    except AttachmentStorageError as error:
        raise attachment_http_error(error) from error
    except CollectionPhotoError as error:
        raise _error(error) from error
    response.headers["Location"] = (
        f"/api/v1/botanical-identities/{botanical_identity_id}/cover-image"
    )
    return result


@router.put(
    "/botanical-identities/{botanical_identity_id}/cover-image/external",
    response_model=ExternalCoverResponse,
    operation_id="setExternalBotanicalIdentityCoverImage",
)
def set_external_botanical_identity_cover_image(
    botanical_identity_id: UUID,
    payload: ExternalCoverWrite,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
    storage: Annotated[AttachmentStorage, Depends(get_attachment_storage)],
) -> ExternalCoverResponse:
    require_owner(actor)
    try:
        return set_external_identity_cover(database, storage, botanical_identity_id, payload)
    except AttachmentStorageError as error:
        raise attachment_http_error(error) from error
    except CollectionPhotoError as error:
        raise _error(error) from error


@router.delete(
    "/botanical-identities/{botanical_identity_id}/cover-image",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteBotanicalIdentityCoverImage",
)
def delete_botanical_identity_cover_image(
    botanical_identity_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
    storage: Annotated[AttachmentStorage, Depends(get_attachment_storage)],
) -> Response:
    require_owner(actor)
    try:
        if not delete_identity_cover(database, storage, botanical_identity_id):
            raise _missing("botanical_identity_cover")
    except AttachmentStorageError as error:
        raise attachment_http_error(error) from error
    except CollectionPhotoError as error:
        raise _error(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/collection-records/{target_type}/{target_id}/photos",
    response_model=list[CollectionPhotoResponse],
    operation_id="listCollectionPhotos",
)
def list_collection_photos(
    target_type: TargetType,
    target_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> list[LocalPhotoResponse | ExternalImageResponse]:
    try:
        items = list_photos(database, target_type, target_id)
    except CollectionPhotoError as error:
        raise _error(error) from error
    return [
        item if isinstance(item, LocalPhotoResponse) else _external_response(item) for item in items
    ]


@router.post(
    "/collection-records/{target_type}/{target_id}/photos/local",
    response_model=LocalPhotoResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="uploadCollectionPhoto",
)
async def upload_collection_photo(
    target_type: TargetType,
    target_id: UUID,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
    storage: Annotated[AttachmentStorage, Depends(get_attachment_storage)],
    file: Annotated[UploadFile, File(description="JPEG, PNG, or WebP collection photo")],
    caption: Annotated[str | None, Form(max_length=2000)] = None,
    attribution: Annotated[str | None, Form(max_length=2000)] = None,
) -> LocalPhotoResponse:
    require_owner(actor)
    try:
        metadata = PhotoMetadataWrite(caption=caption, attribution=attribution)
    except ValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "invalid_photo_metadata",
                "message": "Check the photo caption and attribution",
            },
        ) from error
    try:
        result = await upload_local_photo(database, storage, target_type, target_id, file, metadata)
    except AttachmentStorageError as error:
        raise attachment_http_error(error) from error
    except CollectionPhotoError as error:
        raise _error(error) from error
    response.headers["Location"] = f"/api/v1/collection-photos/local/{result.id}"
    return result


@router.post(
    "/collection-records/{target_type}/{target_id}/photos/external",
    response_model=ExternalImageResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createExternalImageReference",
)
def create_external_image_reference(
    target_type: TargetType,
    target_id: UUID,
    payload: ExternalImageCreate,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> ExternalImageResponse:
    require_owner(actor)
    try:
        reference = create_external_image(database, target_type, target_id, payload)
    except CollectionPhotoError as error:
        raise _error(error) from error
    response.headers["Location"] = f"/api/v1/collection-photos/external/{reference.id}"
    return _external_response(reference)


@router.patch(
    "/collection-photos/local/{photo_id}",
    response_model=LocalPhotoResponse,
    operation_id="updateCollectionPhoto",
)
def update_collection_photo(
    photo_id: UUID,
    payload: LocalPhotoUpdate,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> LocalPhotoResponse:
    require_owner(actor)
    row = get_local_photo(database, photo_id)
    if row is None:
        raise _missing("collection_photo")
    try:
        return update_local_photo(database, *row, payload)
    except CollectionPhotoError as error:
        raise _error(error) from error


@router.patch(
    "/collection-photos/external/{reference_id}",
    response_model=ExternalImageResponse,
    operation_id="updateExternalImageReference",
)
def update_external_image_reference(
    reference_id: UUID,
    payload: ExternalImageUpdate,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> ExternalImageResponse:
    require_owner(actor)
    reference = get_external_image(database, reference_id)
    if reference is None:
        raise _missing("external_image_reference")
    return _external_response(update_external_image(database, reference, payload))


@router.delete(
    "/collection-photos/local/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteCollectionPhoto",
)
def delete_collection_photo(
    photo_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
    storage: Annotated[AttachmentStorage, Depends(get_attachment_storage)],
) -> Response:
    require_owner(actor)
    try:
        if not delete_local_photo(database, storage, photo_id):
            raise _missing("collection_photo")
    except AttachmentStorageError as error:
        raise attachment_http_error(error) from error
    except CollectionPhotoError as error:
        raise _error(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/collection-photos/external/{reference_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteExternalImageReference",
)
def delete_external_image_reference(
    reference_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> Response:
    require_owner(actor)
    reference = get_external_image(database, reference_id)
    if reference is None:
        raise _missing("external_image_reference")
    delete_external_image(database, reference)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
