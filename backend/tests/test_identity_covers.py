import asyncio
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

import pytest
from fastapi import UploadFile
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from florabase.attachments.model import Attachment, AttachmentState
from florabase.attachments.storage import StoredUpload
from florabase.collection_photos.model import BotanicalIdentityCoverImage
from florabase.collection_photos.schemas import ExternalCoverWrite
from florabase.collection_photos.service import (
    CollectionPhotoError,
    attachment_image_owner,
    cover_response,
    delete_identity_cover,
    read_identity_cover,
    set_external_identity_cover,
    set_local_identity_cover,
)


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
    assert {
        "botanical_identity_id",
        "source_mode",
        "attachment_id",
        "image_url",
        "source_url",
        "attribution",
        "licence_label",
        "licence_url",
    } <= columns
    assert "target_type" not in columns
    assert "caption" not in columns


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


def test_external_replacement_handles_external_and_local_sources_without_network() -> None:
    database = MagicMock()
    database.scalar.return_value = object()
    storage = MagicMock()
    existing_external = cover(mode="external")
    database.execute.return_value.one_or_none.return_value = (existing_external, None)

    updated = set_external_identity_cover(
        database,
        storage,
        existing_external.botanical_identity_id,
        external_payload(attribution="Updated credit", licence_label="CC0"),
    )
    assert updated.attribution == "Updated credit"
    assert updated.licence_label == "CC0"
    storage.delete_file.assert_not_called()

    old_attachment = attachment()
    existing_local = cover(mode="local", owned_attachment=old_attachment)
    database.reset_mock()
    database.scalar.return_value = object()
    database.execute.return_value.one_or_none.return_value = (existing_local, old_attachment)
    storage.delete_file.return_value = True
    replaced = set_external_identity_cover(
        database,
        storage,
        existing_local.botanical_identity_id,
        external_payload(),
    )
    assert replaced.kind == "external"
    assert old_attachment.state == AttachmentState.PENDING_DELETE
    storage.delete_file.assert_called_once_with(old_attachment.storage_key)
    database.delete.assert_called_once_with(old_attachment)
    assert database.commit.call_count == 2


@pytest.mark.parametrize("former_mode", ["external", "local"])
def test_local_replacement_cleans_the_former_mode(tmp_path: Path, former_mode: str) -> None:
    stored_path = tmp_path / "new-cover"
    stored_path.write_bytes(b"image")
    stored = StoredUpload(
        storage_key="objects/bb/" + "b" * 32,
        original_filename="new.png",
        media_type="image/png",
        byte_size=5,
        sha256="b" * 64,
        path=stored_path,
    )
    storage = MagicMock()
    storage.store_upload = AsyncMock(return_value=stored)
    storage.delete_file.return_value = True
    database = MagicMock()
    database.scalar.return_value = object()
    old_attachment = attachment() if former_mode == "local" else None
    existing = cover(mode=former_mode, owned_attachment=old_attachment)
    database.execute.return_value.one_or_none.return_value = (existing, old_attachment)

    result = asyncio.run(
        set_local_identity_cover(
            database,
            storage,
            existing.botanical_identity_id,
            MagicMock(spec=UploadFile),
        )
    )
    assert result.kind == "local"
    assert existing.source_mode == "local"
    assert existing.image_url is None
    if old_attachment is None:
        storage.delete_file.assert_not_called()
        assert database.commit.call_count == 1
    else:
        storage.delete_file.assert_called_once_with(old_attachment.storage_key)
        database.delete.assert_called_once_with(old_attachment)
        assert database.commit.call_count == 2


def test_local_cover_unlink_failure_is_truthful_and_retryable() -> None:
    owned = attachment()
    existing = cover(mode="local", owned_attachment=owned)
    database = MagicMock()
    database.scalar.return_value = object()
    database.execute.return_value.one_or_none.return_value = (existing, owned)
    storage = MagicMock()
    storage.delete_file.side_effect = OSError("blocked")

    with pytest.raises(OSError, match="blocked"):
        delete_identity_cover(database, storage, existing.botanical_identity_id)
    assert owned.state == AttachmentState.PENDING_DELETE
    database.delete.assert_not_called()

    storage.delete_file.side_effect = None
    storage.delete_file.return_value = False
    assert delete_identity_cover(database, storage, existing.botanical_identity_id) is True
    assert database.delete.call_args_list[0].args == (existing,)
    assert database.delete.call_args_list[1].args == (owned,)


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


def test_new_local_and_external_covers_create_one_current_row(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    stored_path = tmp_path / "new-local-cover"
    stored_path.write_bytes(b"image")
    stored = StoredUpload(
        storage_key="objects/cc/" + "c" * 32,
        original_filename="new.png",
        media_type="image/png",
        byte_size=5,
        sha256="c" * 64,
        path=stored_path,
    )
    local_database = MagicMock()
    local_database.scalar.return_value = object()
    local_database.execute.return_value.one_or_none.return_value = None

    def populate_timestamps(value: object) -> None:
        if isinstance(value, BotanicalIdentityCoverImage):
            value.created_at = now
            value.updated_at = now

    local_database.add.side_effect = populate_timestamps
    local_storage = MagicMock()
    local_storage.store_upload = AsyncMock(return_value=stored)
    local_result = asyncio.run(
        set_local_identity_cover(local_database, local_storage, uuid7(), MagicMock(spec=UploadFile))
    )
    assert local_result.kind == "local"
    assert stored_path.exists()
    assert local_database.add.call_count == 2

    external_database = MagicMock()
    external_database.scalar.return_value = object()
    external_database.execute.return_value.one_or_none.return_value = None
    external_database.add.side_effect = populate_timestamps
    external_storage = MagicMock()
    external_result = set_external_identity_cover(
        external_database, external_storage, uuid7(), external_payload()
    )
    assert external_result.kind == "external"
    assert external_result.licence_label is None
    external_storage.delete_file.assert_not_called()


def test_cover_write_failures_clean_new_content_and_report_corrupt_ownership(
    tmp_path: Path,
) -> None:
    stored_path = tmp_path / "failed-local-cover"
    stored_path.write_bytes(b"image")
    stored = StoredUpload(
        storage_key="objects/dd/" + "d" * 32,
        original_filename="failed.png",
        media_type="image/png",
        byte_size=5,
        sha256="d" * 64,
        path=stored_path,
    )
    local_database = MagicMock()
    local_database.scalar.return_value = object()
    local_database.execute.return_value.one_or_none.return_value = None
    local_database.commit.side_effect = RuntimeError("database unavailable")
    storage = MagicMock()
    storage.store_upload = AsyncMock(return_value=stored)
    with pytest.raises(CollectionPhotoError, match="Could not persist the local cover"):
        asyncio.run(
            set_local_identity_cover(local_database, storage, uuid7(), MagicMock(spec=UploadFile))
        )
    assert not stored_path.exists()
    local_database.rollback.assert_called_once()

    external_database = MagicMock()
    external_database.scalar.return_value = object()
    external_database.execute.return_value.one_or_none.return_value = None
    external_database.commit.side_effect = RuntimeError("database unavailable")
    with pytest.raises(CollectionPhotoError, match="Could not persist the external cover"):
        set_external_identity_cover(external_database, MagicMock(), uuid7(), external_payload())
    external_database.rollback.assert_called_once()

    corrupt_database = MagicMock()
    corrupt_database.scalar.return_value = object()
    corrupt_local = cover(mode="local")
    corrupt_database.execute.return_value.one_or_none.return_value = (corrupt_local, None)
    with pytest.raises(CollectionPhotoError, match="metadata is missing"):
        set_external_identity_cover(
            corrupt_database,
            MagicMock(),
            corrupt_local.botanical_identity_id,
            external_payload(),
        )


def test_cover_delete_handles_absence_corruption_and_metadata_retry() -> None:
    absent_database = MagicMock()
    absent_database.scalar.return_value = object()
    absent_database.execute.return_value.one_or_none.return_value = None
    assert delete_identity_cover(absent_database, MagicMock(), uuid7()) is False

    corrupt_database = MagicMock()
    corrupt_database.scalar.return_value = object()
    corrupt_local = cover(mode="local")
    corrupt_database.execute.return_value.one_or_none.return_value = (corrupt_local, None)
    with pytest.raises(CollectionPhotoError, match="metadata is missing"):
        delete_identity_cover(corrupt_database, MagicMock(), corrupt_local.botanical_identity_id)

    failed_database = MagicMock()
    failed_database.scalar.return_value = object()
    external = cover(mode="external")
    failed_database.execute.return_value.one_or_none.return_value = (external, None)
    failed_database.flush.side_effect = SQLAlchemyError("write failed")
    with pytest.raises(CollectionPhotoError, match="metadata cleanup must be retried"):
        delete_identity_cover(failed_database, MagicMock(), external.botanical_identity_id)
    failed_database.rollback.assert_called_once()
