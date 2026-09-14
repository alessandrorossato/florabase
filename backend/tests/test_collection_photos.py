import asyncio
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

import pytest
from fastapi import UploadFile
from pydantic import ValidationError

from florabase.attachments.model import Attachment, AttachmentState
from florabase.attachments.storage import StoredUpload
from florabase.collection_photos.model import ExternalImageReference, LocalCollectionPhoto
from florabase.collection_photos.schemas import (
    ExternalImageCreate,
    LocalPhotoResponse,
    LocalPhotoUpdate,
)
from florabase.collection_photos.service import (
    CollectionPhotoError,
    attachment_has_photo,
    create_external_image,
    delete_external_image,
    delete_local_photo,
    get_external_image,
    get_local_photo,
    list_photos,
    local_response,
    target_photo_count,
    update_external_image,
    update_local_photo,
    upload_local_photo,
)


def test_external_image_schema_normalizes_text_and_requires_safe_https_urls() -> None:
    payload = ExternalImageCreate(
        image_url="  https://images.example.test/leaf.jpg  ",
        source_url="https://example.test/source",
        attribution="  Ada Example  ",
        caption="  A leaf  ",
    )
    assert payload.image_url == "https://images.example.test/leaf.jpg"
    assert payload.attribution == "Ada Example"
    assert payload.caption == "A leaf"

    for invalid in (
        "http://example.test/image.jpg",
        "https://",
        "https://user:password@example.test/image.jpg",
        "not a URL",
    ):
        with pytest.raises(ValidationError):
            ExternalImageCreate(
                image_url=invalid,
                source_url="https://example.test/source",
                attribution="Author",
            )
    with pytest.raises(ValidationError):
        ExternalImageCreate(
            image_url="https://example.test/image.jpg",
            source_url="https://example.test/source",
            attribution="  ",
        )
    with pytest.raises(ValidationError):
        ExternalImageCreate(
            image_url="https://example.test/image.jpg",
            source_url="http://example.test/source",
            attribution="Author",
        )
    with pytest.raises(ValidationError):
        ExternalImageCreate(
            image_url="https://example.test/image.jpg",
            source_url="https://example.test/source",
            attribution="x" * 2001,
        )
    with pytest.raises(ValidationError):
        LocalPhotoUpdate(caption="x" * 2001)
    assert LocalPhotoUpdate(caption="  ", attribution="\n Credit \n").model_dump() == {
        "caption": None,
        "attribution": "Credit",
    }


def test_local_response_hides_pending_content() -> None:
    now = datetime.now(UTC)
    attachment = Attachment(
        id=uuid7(),
        storage_key="objects/aa/" + "a" * 32,
        original_filename="leaf.png",
        media_type="image/png",
        byte_size=5,
        sha256="a" * 64,
        state=AttachmentState.PENDING_DELETE,
        created_at=now,
    )
    photo = LocalCollectionPhoto(
        id=uuid7(), attachment_id=attachment.id, plant_id=uuid7(), created_at=now, updated_at=now
    )
    response = local_response(photo, attachment)
    assert response.deletion_pending is True
    assert response.content_url is None


def test_upload_relation_failure_removes_newly_stored_file(tmp_path: Path) -> None:
    stored_path = tmp_path / "stored"
    stored_path.write_bytes(b"image")
    storage = MagicMock()
    storage.store_upload = AsyncMock(
        return_value=StoredUpload(
            storage_key="objects/aa/" + "a" * 32,
            original_filename="leaf.png",
            media_type="image/png",
            byte_size=5,
            sha256="a" * 64,
            path=stored_path,
        )
    )
    database = MagicMock()
    database.get.return_value = object()
    database.commit.side_effect = RuntimeError("write failed")

    with pytest.raises(CollectionPhotoError) as caught:
        asyncio.run(
            upload_local_photo(
                database,
                storage,
                "plant",
                uuid7(),
                MagicMock(spec=UploadFile),
                LocalPhotoUpdate(caption=None, attribution=None),
            )
        )
    assert caught.value.code == "photo_metadata_write_failed"
    assert not stored_path.exists()
    database.rollback.assert_called_once()


def test_local_delete_retains_relation_until_retry() -> None:
    now = datetime.now(UTC)
    attachment = Attachment(
        id=uuid7(),
        storage_key="objects/aa/" + "a" * 32,
        original_filename="leaf.png",
        media_type="image/png",
        byte_size=5,
        sha256="a" * 64,
        state=AttachmentState.ACTIVE,
        created_at=now,
    )
    photo = LocalCollectionPhoto(
        id=uuid7(), attachment_id=attachment.id, event_id=uuid7(), created_at=now, updated_at=now
    )
    database = MagicMock()
    database.execute.return_value.one_or_none.return_value = (photo, attachment)
    storage = MagicMock()
    storage.delete_file.side_effect = OSError("blocked")
    with pytest.raises(OSError, match="blocked"):
        delete_local_photo(database, storage, photo.id)
    assert attachment.state == AttachmentState.PENDING_DELETE
    database.delete.assert_not_called()

    storage.delete_file.side_effect = None
    storage.delete_file.return_value = False
    assert delete_local_photo(database, storage, photo.id) is True
    assert database.delete.call_args_list[0].args == (photo,)
    assert database.delete.call_args_list[1].args == (attachment,)
    database.flush.assert_called_once()


def test_external_models_have_explicit_target_columns() -> None:
    target_columns = {"seed_lot_id", "sowing_id", "plant_id", "plant_group_id", "event_id"}
    assert target_columns <= set(LocalCollectionPhoto.__table__.columns.keys())
    assert target_columns <= set(ExternalImageReference.__table__.columns.keys())
    assert "target_type" not in LocalCollectionPhoto.__table__.columns


def test_list_combines_local_and_external_photos_in_stable_order() -> None:
    now = datetime.now(UTC)
    target_id = uuid7()
    attachment = Attachment(
        id=uuid7(),
        storage_key="objects/aa/" + "a" * 32,
        original_filename="leaf.png",
        media_type="image/png",
        byte_size=5,
        sha256="a" * 64,
        state=AttachmentState.ACTIVE,
        created_at=now,
    )
    local = LocalCollectionPhoto(
        id=uuid7(),
        attachment_id=attachment.id,
        plant_id=target_id,
        created_at=now,
        updated_at=now,
    )
    external = ExternalImageReference(
        id=uuid7(),
        plant_id=target_id,
        image_url="https://images.example.test/leaf.jpg",
        source_url="https://example.test/source",
        attribution="Author",
        created_at=now,
        updated_at=now,
    )
    local.id = min(local.id, external.id)
    external.id = max(uuid7(), local.id)
    database = MagicMock()
    database.get.return_value = object()
    database.execute.return_value.all.return_value = [(local, attachment)]
    database.scalars.return_value.all.return_value = [external]

    result = list_photos(database, "plant", target_id)

    assert [item.id for item in result] == [local.id, external.id]
    assert isinstance(result[0], LocalPhotoResponse)
    assert result[0].content_url is not None


def test_external_crud_and_photo_lookup_helpers() -> None:
    target_id = uuid7()
    database = MagicMock()
    database.get.return_value = object()
    payload = ExternalImageCreate(
        image_url="https://images.example.test/leaf.jpg",
        source_url="https://example.test/source",
        attribution="Author",
        caption="Leaf",
    )

    reference = create_external_image(database, "plant", target_id, payload)
    assert reference.plant_id == target_id
    database.add.assert_called_once_with(reference)
    assert get_external_image(database, reference.id) is database.get.return_value

    updated = update_external_image(
        database,
        reference,
        ExternalImageCreate(
            image_url="https://images.example.test/new.jpg",
            source_url="https://example.test/new",
            attribution="New author",
        ),
    )
    assert updated.attribution == "New author"
    delete_external_image(database, reference)
    database.delete.assert_called_once_with(reference)

    photo = MagicMock()
    attachment = MagicMock()
    database.execute.return_value.one_or_none.return_value = (photo, attachment)
    assert get_local_photo(database, uuid7()) == (photo, attachment)
    database.execute.return_value.one_or_none.return_value = None
    assert get_local_photo(database, uuid7()) is None

    database.scalars.return_value.all.side_effect = [[uuid7()], [uuid7(), uuid7()]]
    assert target_photo_count(database, "plant", target_id) == 3
    database.scalar.return_value = uuid7()
    assert attachment_has_photo(database, uuid7()) is True


def test_local_metadata_update_rejects_pending_photo() -> None:
    now = datetime.now(UTC)
    photo = LocalCollectionPhoto(
        id=uuid7(),
        attachment_id=uuid7(),
        plant_id=uuid7(),
        created_at=now,
        updated_at=now,
    )
    attachment = Attachment(
        id=photo.attachment_id,
        storage_key="objects/aa/" + "a" * 32,
        original_filename="leaf.png",
        media_type="image/png",
        byte_size=5,
        sha256="a" * 64,
        state=AttachmentState.ACTIVE,
        created_at=now,
    )
    database = MagicMock()
    response = update_local_photo(
        database, photo, attachment, LocalPhotoUpdate(caption=" Leaf ", attribution=None)
    )
    assert response.caption == "Leaf"
    database.commit.assert_called_once()

    attachment.state = AttachmentState.PENDING_DELETE
    with pytest.raises(CollectionPhotoError, match="pending deletion"):
        update_local_photo(database, photo, attachment, LocalPhotoUpdate())
