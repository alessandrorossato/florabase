import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

import pytest
from fastapi import HTTPException, Response, UploadFile

from florabase.collection_photos import api
from florabase.collection_photos.model import ExternalImageReference
from florabase.collection_photos.schemas import (
    ExternalCoverResponse,
    ExternalCoverWrite,
    ExternalImageCreate,
    ExternalImageUpdate,
    LocalPhotoResponse,
    LocalPhotoUpdate,
)
from florabase.collection_photos.service import CollectionPhotoError


def local_response() -> LocalPhotoResponse:
    now = datetime.now(UTC)
    attachment_id = uuid7()
    return LocalPhotoResponse(
        id=uuid7(),
        attachment_id=attachment_id,
        original_filename="leaf.png",
        media_type="image/png",
        caption=None,
        attribution=None,
        deletion_pending=False,
        content_url=f"/api/v1/attachments/{attachment_id}/content",
        created_at=now,
        updated_at=now,
    )


def external_reference() -> ExternalImageReference:
    now = datetime.now(UTC)
    return ExternalImageReference(
        id=uuid7(),
        plant_id=uuid7(),
        image_url="https://images.example.test/leaf.jpg",
        source_url="https://example.test/source",
        attribution="Author",
        caption=None,
        created_at=now,
        updated_at=now,
    )


def external_cover() -> ExternalCoverResponse:
    now = datetime.now(UTC)
    return ExternalCoverResponse(
        id=uuid7(),
        image_url="https://images.example.test/cover.jpg",
        source_url="https://example.test/cover",
        attribution="Cover author",
        licence_label=None,
        licence_url=None,
        created_at=now,
        updated_at=now,
    )


def test_list_create_and_upload_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    target_id = uuid7()
    local = local_response()
    external = external_reference()
    actor = MagicMock(owner=True)
    database = MagicMock()

    monkeypatch.setattr(api, "list_photos", lambda *_args: [local, external])
    listed = api.list_collection_photos("plant", target_id, actor, database)
    assert [item.kind for item in listed] == ["local", "external"]

    upload = AsyncMock(return_value=local)
    monkeypatch.setattr(api, "upload_local_photo", upload)
    response = Response()
    result = asyncio.run(
        api.upload_collection_photo(
            "plant",
            target_id,
            response,
            actor,
            database,
            MagicMock(),
            MagicMock(spec=UploadFile),
            " caption ",
            " credit ",
        )
    )
    assert result.id == local.id
    assert response.headers["location"].endswith(str(local.id))

    monkeypatch.setattr(api, "create_external_image", lambda *_args: external)
    response = Response()
    created = api.create_external_image_reference(
        "plant",
        target_id,
        ExternalImageCreate(
            image_url=external.image_url,
            source_url=external.source_url,
            attribution=external.attribution,
        ),
        response,
        actor,
        database,
    )
    assert created.id == external.id
    assert response.headers["location"].endswith(str(external.id))


def test_update_and_delete_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    local = local_response()
    external = external_reference()
    actor = MagicMock(owner=True)
    database = MagicMock()
    attachment = MagicMock()
    photo = MagicMock()
    monkeypatch.setattr(api, "get_local_photo", lambda *_args: (photo, attachment))
    monkeypatch.setattr(api, "update_local_photo", lambda *_args: local)
    assert (
        api.update_collection_photo(
            local.id,
            LocalPhotoUpdate(caption="Leaf", attribution=None),
            actor,
            database,
        ).id
        == local.id
    )

    monkeypatch.setattr(api, "get_external_image", lambda *_args: external)
    monkeypatch.setattr(api, "update_external_image", lambda *_args: external)
    updated = api.update_external_image_reference(
        external.id,
        ExternalImageUpdate(
            image_url=external.image_url,
            source_url=external.source_url,
            attribution="Updated author",
        ),
        actor,
        database,
    )
    assert updated.kind == "external"

    monkeypatch.setattr(api, "delete_local_photo", lambda *_args: True)
    assert api.delete_collection_photo(local.id, actor, database, MagicMock()).status_code == 204
    delete_external = MagicMock()
    monkeypatch.setattr(api, "delete_external_image", delete_external)
    assert api.delete_external_image_reference(external.id, actor, database).status_code == 204
    delete_external.assert_called_once_with(database, external)


def test_route_errors_are_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    actor = MagicMock(owner=True)
    database = MagicMock()
    target_id = uuid7()

    def fail(*_args: object) -> None:
        raise CollectionPhotoError("photo_target_not_found", "missing")

    monkeypatch.setattr(api, "list_photos", fail)
    with pytest.raises(HTTPException) as missing_target:
        api.list_collection_photos("event", target_id, actor, database)
    assert missing_target.value.status_code == 404

    monkeypatch.setattr(api, "get_local_photo", lambda *_args: None)
    with pytest.raises(HTTPException) as missing_local:
        api.update_collection_photo(target_id, LocalPhotoUpdate(), actor, database)
    assert missing_local.value.status_code == 404

    monkeypatch.setattr(api, "get_external_image", lambda *_args: None)
    with pytest.raises(HTTPException) as missing_external:
        api.delete_external_image_reference(target_id, actor, database)
    assert missing_external.value.status_code == 404

    monkeypatch.setattr(api, "delete_local_photo", lambda *_args: False)
    with pytest.raises(HTTPException) as delete_missing:
        api.delete_collection_photo(target_id, actor, database, MagicMock())
    assert delete_missing.value.status_code == 404

    with pytest.raises(HTTPException) as forbidden:
        api.delete_collection_photo(target_id, MagicMock(owner=False), database, MagicMock())
    assert forbidden.value.status_code == 403


def test_identity_cover_routes_are_narrow_and_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity_id = uuid7()
    actor = MagicMock(owner=True)
    database = MagicMock()
    storage = MagicMock()
    cover = external_cover()
    monkeypatch.setattr(api, "read_identity_cover", lambda *_args: None)
    assert api.get_botanical_identity_cover_image(identity_id, actor, database) is None

    local = local_response()
    local_upload = AsyncMock(return_value=local)
    monkeypatch.setattr(api, "set_local_identity_cover", local_upload)
    response = Response()
    created = asyncio.run(
        api.set_local_botanical_identity_cover_image(
            identity_id,
            response,
            actor,
            database,
            storage,
            MagicMock(spec=UploadFile),
        )
    )
    assert created.kind == "local"
    assert response.headers["location"].endswith("/cover-image")

    monkeypatch.setattr(api, "set_external_identity_cover", lambda *_args: cover)
    saved = api.set_external_botanical_identity_cover_image(
        identity_id,
        ExternalCoverWrite(
            image_url=cover.image_url,
            source_url=cover.source_url,
            attribution=cover.attribution,
            privacy_acknowledged=True,
        ),
        actor,
        database,
        storage,
    )
    assert saved.kind == "external"

    monkeypatch.setattr(api, "delete_identity_cover", lambda *_args: True)
    assert (
        api.delete_botanical_identity_cover_image(identity_id, actor, database, storage).status_code
        == 204
    )

    monkeypatch.setattr(api, "delete_identity_cover", lambda *_args: False)
    with pytest.raises(HTTPException) as missing:
        api.delete_botanical_identity_cover_image(identity_id, actor, database, storage)
    assert missing.value.status_code == 404
