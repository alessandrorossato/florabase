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
from florabase.media import service as media


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
        "display_order": None,
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


def test_record_removal_unlinks_without_touching_local_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, storage = MagicMock(), MagicMock()
    unlink = MagicMock(return_value=True)
    monkeypatch.setattr(media, "unlink", unlink)
    photo_id = uuid7()
    assert delete_local_photo(database, storage, photo_id)
    unlink.assert_called_once_with(database, photo_id)
    storage.delete_file.assert_not_called()


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
        display_order=0,
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


def test_external_crud_and_photo_lookup_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    target_id = uuid7()
    database = MagicMock()
    database.get.return_value = object()
    payload = ExternalImageCreate(
        image_url="https://images.example.test/leaf.jpg",
        source_url="https://example.test/source",
        attribution="Author",
        caption="Leaf",
    )

    reference = ExternalImageReference(
        id=uuid7(),
        plant_id=target_id,
        display_order=0,
        **payload.model_dump(exclude={"display_order"}),
    )
    asset = reference.media_asset
    database.scalar.return_value = reference
    create_asset = MagicMock(return_value=asset)
    monkeypatch.setattr(media, "create_external_asset", create_asset)
    reference = create_external_image(database, "plant", target_id, payload)
    assert reference.plant_id == target_id
    assert create_asset.call_args.kwargs["caption"] == "Leaf"
    assert get_external_image(database, reference.id) is reference
    monkeypatch.setattr(media, "locked_link", lambda *_args: reference)
    monkeypatch.setattr(media, "reference_counts", lambda *_args: (1, 0))

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
    unlink = MagicMock(return_value=True)
    monkeypatch.setattr(media, "unlink", unlink)
    delete_external_image(database, reference)
    unlink.assert_called_once_with(database, reference.id)

    photo = MagicMock()
    attachment = MagicMock()
    database.execute.return_value.one_or_none.return_value = (photo, attachment)
    assert get_local_photo(database, uuid7()) == (photo, attachment)
    database.execute.return_value.one_or_none.return_value = None
    assert get_local_photo(database, uuid7()) is None

    database.scalar.return_value = 3
    assert target_photo_count(database, "plant", target_id) == 3
    database.scalar.return_value = uuid7()
    assert attachment_has_photo(database, uuid7()) is True


def test_local_metadata_update_rejects_pending_photo(monkeypatch: pytest.MonkeyPatch) -> None:
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
    database.get.return_value = attachment
    monkeypatch.setattr(media, "locked_link", lambda *_args: photo)
    response = update_local_photo(
        database, photo, attachment, LocalPhotoUpdate(caption=" Leaf ", attribution=None)
    )
    assert response.caption == "Leaf"
    database.commit.assert_called_once()

    attachment.state = AttachmentState.PENDING_DELETE
    with pytest.raises(CollectionPhotoError, match="unavailable"):
        update_local_photo(database, photo, attachment, LocalPhotoUpdate())
