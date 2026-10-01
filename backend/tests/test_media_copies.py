import asyncio
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID, uuid7

import pytest
from fastapi import HTTPException
from PIL import Image
from sqlalchemy import Select
from sqlalchemy.exc import SQLAlchemyError

from florabase.attachments.model import Attachment
from florabase.attachments.storage import AttachmentStorage, AttachmentStorageError
from florabase.collection_photos.model import MediaAsset
from florabase.media import api, copies, service
from florabase.media.fetch import ExternalFetchError


def image(color: str = "green") -> bytes:
    stream = BytesIO()
    Image.new("RGB", (640, 320), color).save(stream, "PNG")
    return stream.getvalue()


def setup(monkeypatch: pytest.MonkeyPatch) -> tuple[MagicMock, MediaAsset, dict[UUID, Attachment]]:
    row = MediaAsset(
        id=uuid7(),
        kind="external",
        state="active",
        image_url="https://example.test/img.png",
        source_url="https://example.test/source",
        attribution="Author",
    )
    files: dict[UUID, Attachment] = {}
    database = MagicMock()
    database.get.side_effect = lambda _model, identifier: files.get(identifier)
    database.add.side_effect = lambda file: files.update({file.id: file})

    def scalar(
        statement: Select[tuple[MediaAsset]] | Select[tuple[Attachment]],
    ) -> MediaAsset | Attachment | None:
        if statement.column_descriptions[0]["entity"] is MediaAsset:
            return row
        return files.get(row.copy_cleanup_attachment_id) if row.copy_cleanup_attachment_id else None

    database.scalar.side_effect = scalar
    monkeypatch.setattr(copies, "require_asset", lambda *_args, **_kwargs: row)
    monkeypatch.setattr(copies, "fetch_image", lambda *_args: (image(), "image/png"))
    return database, row, files


def test_save_refresh_remove_snapshot_and_byte_identical_derivative(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    database, row, files = setup(monkeypatch)
    storage = AttachmentStorage(tmp_path)
    asyncio.run(copies.save_copy(database, storage, row.id, refresh=False))
    first_id = row.attachment_id
    assert first_id is not None
    first = files[first_id]
    assert storage.active_path(first.storage_key, first.byte_size).read_bytes() == image()
    assert row.fetched_at is not None
    assert row.kind == "external"
    asyncio.run(copies.save_copy(database, storage, row.id, refresh=True))
    assert row.attachment_id != first_id
    assert not (tmp_path / first.storage_key).exists()
    assert len(list((tmp_path / ".thumbnails").glob("*.webp"))) == 1
    monkeypatch.setattr(copies, "fetch_image", lambda *_args: (image("red"), "image/png"))
    asyncio.run(copies.save_copy(database, storage, row.id, refresh=True))
    assert len(list((tmp_path / ".thumbnails").glob("*.webp"))) == 1
    copies.remove_copy(database, storage, row.id)
    assert row.attachment_id is None
    assert row.copy_cleanup_attachment_id is None
    assert row.fetched_at is None
    assert not list((tmp_path / ".thumbnails").glob("*.webp"))
    copies.remove_copy(database, storage, row.id)


def test_copy_preconditions_fail_without_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    database, row, _ = setup(monkeypatch)
    fetch = MagicMock(side_effect=AssertionError("must not fetch"))
    monkeypatch.setattr(copies, "fetch_image", fetch)
    storage = AttachmentStorage(tmp_path)
    row.kind = "local"
    with pytest.raises(service.MediaError, match="external references"):
        asyncio.run(copies.save_copy(database, storage, row.id, refresh=False))
    row.kind = "external"
    with pytest.raises(service.MediaError, match="before refreshing"):
        asyncio.run(copies.save_copy(database, storage, row.id, refresh=True))
    row.attachment_id = uuid7()
    monkeypatch.setattr(copies, "require_active", lambda *_args: None)
    with pytest.raises(service.MediaError, match="already saved"):
        asyncio.run(copies.save_copy(database, storage, row.id, refresh=False))
    fetch.assert_not_called()
    row.copy_cleanup_attachment_id = uuid7()
    database.scalar.return_value = None
    database.scalar.side_effect = None
    with pytest.raises(service.MediaError, match="operator recovery"):
        copies.cleanup_copy(database, storage, row)


def test_failed_derivative_preserves_previous_snapshot_and_cleans_candidate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    database, row, files = setup(monkeypatch)
    storage = AttachmentStorage(tmp_path)
    asyncio.run(copies.save_copy(database, storage, row.id, refresh=False))
    before = row.attachment_id
    assert before is not None
    monkeypatch.setattr(copies, "fetch_image", lambda *_args: (image("red"), "image/png"))

    def failed(*_args: object) -> bytes:
        raise AttachmentStorageError("attachment_storage_write_failed", "Could not store thumbnail")

    monkeypatch.setattr(copies, "asset_thumbnail", failed)
    with pytest.raises(AttachmentStorageError):
        asyncio.run(copies.save_copy(database, storage, row.id, refresh=True))
    assert row.attachment_id == before
    assert (
        storage.active_path(files[before].storage_key, files[before].byte_size).read_bytes()
        == image()
    )
    assert len([path for path in storage.objects.rglob("*") if path.is_file()]) == 1
    assert len(list((tmp_path / ".thumbnails").glob("*.webp"))) == 1
    database.rollback.assert_called()


@pytest.mark.parametrize(
    "failure",
    [
        ExternalFetchError("Could not fetch safely"),
        service.MediaError("conflict", "Changed"),
        AttachmentStorageError("invalid_image", "Malformed"),
        SQLAlchemyError("database failure"),
    ],
)
def test_copy_api_errors_roll_back_and_explain(
    monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    async def failed(*_args: object, **_kwargs: object) -> None:
        raise failure

    monkeypatch.setattr(copies, "save_copy", failed)
    monkeypatch.setattr(api, "require_owner", lambda *_args: None)
    database = MagicMock()
    with pytest.raises(HTTPException) as error:
        api.save_local_copy(uuid7(), database, MagicMock(), MagicMock())
    assert error.value.status_code in {409, 422, 503}
    database.rollback.assert_called_once()


@pytest.mark.parametrize(
    "failure",
    [
        service.MediaError("conflict", "Changed"),
        AttachmentStorageError("attachment_delete_failed", "Retry cleanup"),
        SQLAlchemyError("database failure"),
    ],
)
def test_remove_api_errors_roll_back(monkeypatch: pytest.MonkeyPatch, failure: Exception) -> None:
    def failed(*_args: object, **_kwargs: object) -> None:
        raise failure

    monkeypatch.setattr(copies, "remove_copy", failed)
    monkeypatch.setattr(api, "require_owner", lambda *_args: None)
    database = MagicMock()
    with pytest.raises(HTTPException):
        api.remove_local_copy(uuid7(), database, MagicMock(), MagicMock())
    database.rollback.assert_called_once()
