import asyncio
import io
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

import pytest
from fastapi import UploadFile
from PIL import Image
from pydantic import ValidationError

from florabase.attachments.model import Attachment, AttachmentState
from florabase.collection_photos.model import BotanicalIdentityCoverImage
from florabase.collection_photos.schemas import ExternalCoverWrite
from florabase.collection_photos.service import (
    CollectionPhotoError,
    attachment_image_owner,
    cover_response,
    delete_identity_cover,
    local_identity_cover_attachment,
    read_identity_cover,
    render_identity_cover_thumbnail,
    set_external_identity_cover,
    set_local_identity_cover,
)
from florabase.media import service as media


def external_payload(**changes: object) -> ExternalCoverWrite:
    values: dict[str, object] = {
        "image_url": "https://images.example.test/flower.jpg",
        "source_url": "https://example.test/flower",
        "attribution": "Example photographer",
        "licence_label": None,
        "licence_url": None,
        "privacy_acknowledged": True,
    }
    values.update(changes)
    return ExternalCoverWrite.model_validate(values)


def attachment(*, state: str = AttachmentState.ACTIVE) -> Attachment:
    return Attachment(
        id=uuid7(),
        storage_key="objects/aa/" + "a" * 32,
        original_filename="flower.png",
        media_type="image/png",
        byte_size=5,
        sha256="a" * 64,
        state=state,
        created_at=datetime.now(UTC),
    )


def cover(*, mode: str, owned_attachment: Attachment | None = None) -> BotanicalIdentityCoverImage:
    now = datetime.now(UTC)
    return BotanicalIdentityCoverImage(
        id=uuid7(),
        botanical_identity_id=uuid7(),
        source_mode=mode,
        attachment_id=owned_attachment.id if owned_attachment else None,
        image_url="https://images.example.test/flower.jpg" if mode == "external" else None,
        source_url="https://example.test/flower" if mode == "external" else None,
        attribution="Example photographer" if mode == "external" else None,
        created_at=now,
        updated_at=now,
    )


def test_external_cover_schema_requires_explicit_privacy_and_safe_metadata() -> None:
    payload = external_payload(
        image_url=" https://images.example.test/flower.jpg ",
        attribution=" Photographer ",
        licence_label=" ",
        licence_url=" ",
    )
    assert payload.attribution == "Photographer"
    assert payload.licence_label is None
    assert payload.licence_url is None

    for changes in (
        {"image_url": "http://example.test/flower.jpg"},
        {"source_url": "data:image/png;base64,AAAA"},
        {"licence_url": "file:///licence"},
        {"image_url": "https://localhost/flower.jpg"},
        {"image_url": "https://127.0.0.1/flower.jpg"},
        {"source_url": "https://photos.internal/flower"},
        {"licence_url": "https://licence-server/terms"},
        {"attribution": " "},
        {"privacy_acknowledged": False},
    ):
        with pytest.raises(ValidationError):
            external_payload(**changes)
    assert external_payload().licence_label is None


def test_cover_model_is_separate_and_has_narrow_relational_columns() -> None:
    columns = set(BotanicalIdentityCoverImage.__table__.columns.keys())
    assert {"botanical_identity_id", "source_mode", "media_asset_id"} <= columns
    assert "target_type" not in columns
    assert "caption" not in columns
    assert "attachment_id" not in columns
    assert "image_url" not in columns


def test_cover_response_hides_pending_local_content_and_preserves_external_credit() -> None:
    local_attachment = attachment(state=AttachmentState.PENDING_DELETE)
    local = cover(mode="local", owned_attachment=local_attachment)
    local_result = cover_response(local, local_attachment)
    assert local_result.kind == "local"
    assert local_result.deletion_pending is True
    assert local_result.content_url is None

    external = cover(mode="external")
    external.licence_label = "CC BY 4.0"
    result = cover_response(external, None)
    assert result.kind == "external"
    assert result.attribution == "Example photographer"
    assert result.licence_label == "CC BY 4.0"
    assert result.licence_url is None


@pytest.mark.parametrize("mode", ["external", "local"])
def test_external_replacement_retains_former_asset_without_network(mode: str) -> None:
    database, storage = MagicMock(), MagicMock()
    database.scalar.return_value = object()
    old_attachment = attachment() if mode == "local" else None
    existing = cover(mode=mode, owned_attachment=old_attachment)
    former_asset = existing.media_asset
    database.execute.return_value.one_or_none.return_value = (existing, old_attachment)
    result = set_external_identity_cover(
        database,
        storage,
        existing.botanical_identity_id,
        external_payload(attribution="Updated credit", licence_label="CC0"),
    )
    assert result.attribution == "Updated credit"
    assert result.licence_label == "CC0"
    assert existing.media_asset is not former_asset
    assert former_asset.state == "active"
    if old_attachment is not None:
        assert old_attachment.state == "active"
    storage.delete_file.assert_not_called()
    database.delete.assert_not_called()
    database.commit.assert_called_once()


@pytest.mark.parametrize("former_mode", ["external", "local"])
def test_local_replacement_retains_former_media(
    former_mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    database, storage = MagicMock(), MagicMock()
    database.scalar.return_value = object()
    original_file = attachment() if former_mode == "local" else None
    existing = cover(mode=former_mode, owned_attachment=original_file)
    former_asset = existing.media_asset
    database.execute.return_value.one_or_none.return_value = (existing, original_file)
    new_file = attachment()
    new_cover = cover(mode="local", owned_attachment=new_file)
    database.get.return_value = new_file
    monkeypatch.setattr(media, "upload_asset", AsyncMock(return_value=new_cover.media_asset))
    result = asyncio.run(
        set_local_identity_cover(
            database, storage, existing.botanical_identity_id, MagicMock(spec=UploadFile)
        )
    )
    assert result.kind == "local"
    assert existing.media_asset is not former_asset
    assert former_asset.state == "active"
    assert existing.source_mode == "local"
    storage.delete_file.assert_not_called()
    database.delete.assert_not_called()
    database.commit.assert_called_once()


def test_cover_removal_retains_local_file_and_asset_without_unlink(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, storage = MagicMock(), MagicMock()
    database.scalar.return_value = object()
    original = attachment()
    existing = cover(mode="local", owned_attachment=original)
    asset = existing.media_asset
    database.execute.return_value.one_or_none.return_value = (existing, original)
    monkeypatch.setattr(media, "require_asset", lambda *_args, **_kwargs: asset)
    assert delete_identity_cover(database, storage, existing.botanical_identity_id)
    database.delete.assert_called_once_with(existing)
    database.commit.assert_called_once()
    assert original.state == "active"
    assert asset.state == "active"
    storage.delete_file.assert_not_called()


def test_attachment_owner_distinguishes_collection_photo_and_identity_cover() -> None:
    database = MagicMock()
    database.scalar.side_effect = [None, uuid7()]
    assert attachment_image_owner(database, uuid7()) == "botanical_identity_cover"
    database.scalar.side_effect = [uuid7()]
    assert attachment_image_owner(database, uuid7()) == "collection_photo"

    broken = cover(mode="local", owned_attachment=attachment())
    with pytest.raises(CollectionPhotoError, match="metadata is missing"):
        cover_response(broken, None)


def test_cover_lookup_distinguishes_absence_from_a_missing_identity() -> None:
    database = MagicMock()
    database.scalar.return_value = object()
    database.execute.return_value.one_or_none.return_value = None
    assert read_identity_cover(database, uuid7()) is None

    database.scalar.return_value = None
    with pytest.raises(CollectionPhotoError, match="Botanical identity not found"):
        read_identity_cover(database, uuid7())


def test_local_cover_thumbnail_is_bounded_and_never_upscaled(tmp_path: Path) -> None:
    large_path = tmp_path / "large.png"
    Image.new("RGB", (800, 400), (30, 120, 40)).save(large_path, format="PNG")
    rendered = render_identity_cover_thumbnail(large_path)
    with Image.open(io.BytesIO(rendered)) as thumbnail:
        assert thumbnail.format == "WEBP"
        assert thumbnail.size == (320, 160)

    small_path = tmp_path / "small.png"
    Image.new("RGBA", (40, 30), (30, 120, 40, 120)).save(small_path, format="PNG")
    rendered_small = render_identity_cover_thumbnail(small_path)
    with Image.open(io.BytesIO(rendered_small)) as thumbnail:
        assert thumbnail.size == (40, 30)


def test_local_thumbnail_source_rejects_external_and_pending_covers() -> None:
    database = MagicMock()
    database.scalar.return_value = object()
    external = cover(mode="external")
    database.execute.return_value.one_or_none.return_value = (external, None)
    assert local_identity_cover_attachment(database, external.botanical_identity_id) is None

    pending = attachment(state=AttachmentState.PENDING_DELETE)
    local = cover(mode="local", owned_attachment=pending)
    database.execute.return_value.one_or_none.return_value = (local, pending)
    assert local_identity_cover_attachment(database, local.botanical_identity_id) is None


def test_new_local_and_external_covers_create_one_current_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(UTC)
    database, storage = MagicMock(), MagicMock()
    database.scalar.return_value = object()
    database.execute.return_value.one_or_none.return_value = None

    def timestamps(value: object) -> None:
        if isinstance(value, BotanicalIdentityCoverImage):
            value.created_at = now
            value.updated_at = now

    database.add.side_effect = timestamps
    stored_file = attachment()
    database.get.return_value = stored_file
    new_cover = cover(mode="local", owned_attachment=stored_file)
    monkeypatch.setattr(media, "upload_asset", AsyncMock(return_value=new_cover.media_asset))
    local = asyncio.run(
        set_local_identity_cover(database, storage, uuid7(), MagicMock(spec=UploadFile))
    )
    assert local.kind == "local"
    database.add.assert_called_once()
    database.reset_mock()
    external = set_external_identity_cover(database, storage, uuid7(), external_payload())
    assert external.kind == "external"
    assert external.licence_label is None
    storage.delete_file.assert_not_called()


def test_cover_write_failure_rolls_back_and_cleans_only_new_upload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, storage = MagicMock(), MagicMock()
    database.scalar.return_value = object()
    database.execute.return_value.one_or_none.return_value = None
    database.commit.side_effect = RuntimeError("database unavailable")
    stored_file = attachment()
    database.get.return_value = stored_file
    new_cover = cover(mode="local", owned_attachment=stored_file)
    monkeypatch.setattr(media, "upload_asset", AsyncMock(return_value=new_cover.media_asset))
    with pytest.raises(CollectionPhotoError, match="Could not save the local cover"):
        asyncio.run(
            set_local_identity_cover(database, storage, uuid7(), MagicMock(spec=UploadFile))
        )
    database.rollback.assert_called_once()
    storage.delete_file.assert_called_once_with(stored_file.storage_key)
    database.reset_mock()
    with pytest.raises(CollectionPhotoError, match="Could not save the external cover"):
        set_external_identity_cover(database, storage, uuid7(), external_payload())
    database.rollback.assert_called_once()


def test_cover_delete_handles_absence_and_retains_asset(monkeypatch: pytest.MonkeyPatch) -> None:
    database, storage = MagicMock(), MagicMock()
    database.scalar.return_value = object()
    database.execute.return_value.one_or_none.return_value = None
    assert not delete_identity_cover(database, storage, uuid7())
    existing = cover(mode="external")
    database.execute.return_value.one_or_none.return_value = (existing, None)
    monkeypatch.setattr(media, "require_asset", lambda *_args, **_kwargs: existing.media_asset)
    assert delete_identity_cover(database, storage, existing.botanical_identity_id)
    database.delete.assert_called_once_with(existing)
    storage.delete_file.assert_not_called()
