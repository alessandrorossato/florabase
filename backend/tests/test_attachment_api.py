import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

import pytest
from fastapi import HTTPException, Response, UploadFile

from florabase.attachments import api
from florabase.attachments.model import Attachment, AttachmentState
from florabase.attachments.service import AttachmentOperationError
from florabase.attachments.storage import AttachmentStorage, AttachmentStorageError


def attachment() -> Attachment:
    return Attachment(
        id=uuid7(),
        storage_key="objects/aa/" + "a" * 32,
        original_filename="leaf photo.png",
        media_type="image/png",
        byte_size=5,
        sha256="a" * 64,
        state=AttachmentState.ACTIVE,
        created_at=datetime.now(UTC),
    )


def test_storage_dependency_and_error_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = MagicMock()
    storage = MagicMock()
    monkeypatch.setattr(AttachmentStorage, "from_settings", lambda _settings: storage)
    assert api.get_attachment_storage(settings) is storage

    cases = {
        "attachment_too_large": 413,
        "unsupported_media_type": 415,
        "attachment_content_missing": 409,
        "invalid_filename": 422,
        "attachment_storage_unavailable": 503,
    }
    for code, expected_status in cases.items():
        error = api._http_error(AttachmentStorageError(code, "visible"))
        assert error.status_code == expected_status
        assert cast(dict[str, str], error.detail) == {"code": code, "message": "visible"}

    storage_error = AttachmentStorageError("attachment_storage_unavailable", "unavailable")

    def fail(_settings: object) -> None:
        raise storage_error

    monkeypatch.setattr(AttachmentStorage, "from_settings", fail)
    with pytest.raises(HTTPException) as caught:
        api.get_attachment_storage(settings)
    assert caught.value.status_code == 503


def test_active_metadata_and_content_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    item = attachment()
    database = MagicMock()
    actor = MagicMock()
    storage = MagicMock()
    expected_path = Path("/var/lib/florabase/attachments") / item.storage_key
    monkeypatch.setattr(api, "require_active_attachment", lambda *_args: item)
    monkeypatch.setattr(api, "attachment_content_path", lambda *_args: expected_path)

    response = Response()
    metadata = api.read(item.id, response, actor, database)
    assert metadata.id == item.id
    assert metadata.original_filename == "leaf photo.png"
    assert response.headers["cache-control"] == "private, no-store"
    content = api.read_content(item.id, actor, database, storage)
    assert Path(content.path) == expected_path
    assert content.media_type == "image/png"
    assert content.headers["cache-control"] == "private, no-store"
    assert content.headers["x-content-type-options"] == "nosniff"
    assert content.headers["content-disposition"] == ("inline; filename*=UTF-8''leaf%20photo.png")

    monkeypatch.setattr(api, "require_active_attachment", lambda *_args: None)
    with pytest.raises(HTTPException) as missing:
        api.read(item.id, Response(), actor, database)
    assert missing.value.status_code == 404

    monkeypatch.setattr(api, "require_active_attachment", lambda *_args: item)
    with pytest.raises(HTTPException) as forbidden:
        api.read(item.id, Response(), MagicMock(owner=False), database)
    assert forbidden.value.status_code == 403

    with pytest.raises(HTTPException) as content_forbidden:
        api.read_content(item.id, MagicMock(owner=False), database, storage)
    assert content_forbidden.value.status_code == 403


def test_content_route_maps_storage_inconsistency(monkeypatch: pytest.MonkeyPatch) -> None:
    item = attachment()
    monkeypatch.setattr(api, "require_active_attachment", lambda *_args: item)

    def fail(*_args: object) -> None:
        raise AttachmentStorageError("attachment_content_mismatch", "mismatch")

    monkeypatch.setattr(api, "attachment_content_path", fail)
    with pytest.raises(HTTPException) as caught:
        api.read_content(item.id, MagicMock(), MagicMock(), MagicMock())
    assert caught.value.status_code == 409


def test_create_route_returns_metadata_and_maps_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    item = attachment()
    create_mock = AsyncMock(return_value=item)
    monkeypatch.setattr(api, "create_attachment", create_mock)
    response = Response()
    actor = MagicMock(owner=True)
    upload = MagicMock(spec=UploadFile)

    result = asyncio.run(api.create(response, upload, actor, MagicMock(), MagicMock()))
    assert result.id == item.id
    assert response.headers["location"] == f"/api/v1/attachments/{item.id}"

    create_mock.side_effect = AttachmentOperationError(
        "attachment_metadata_write_failed", "unavailable"
    )
    with pytest.raises(HTTPException) as caught:
        asyncio.run(api.create(Response(), upload, actor, MagicMock(), MagicMock()))
    assert caught.value.status_code == 503

    with pytest.raises(HTTPException) as forbidden:
        asyncio.run(
            api.create(Response(), upload, MagicMock(owner=False), MagicMock(), MagicMock())
        )
    assert forbidden.value.status_code == 403


def test_delete_route_handles_success_missing_and_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    attachment_id = uuid7()
    actor = MagicMock(owner=True)
    database = MagicMock()
    storage = MagicMock()
    delete_mock = MagicMock(return_value=True)
    monkeypatch.setattr(api, "delete_attachment", delete_mock)

    response = api.delete(attachment_id, actor, database, storage)
    assert response.status_code == 204

    delete_mock.return_value = False
    with pytest.raises(HTTPException) as missing:
        api.delete(attachment_id, actor, database, storage)
    assert missing.value.status_code == 404

    delete_mock.side_effect = AttachmentStorageError("attachment_delete_failed", "unavailable")
    with pytest.raises(HTTPException) as unavailable:
        api.delete(attachment_id, actor, database, storage)
    assert unavailable.value.status_code == 503

    with pytest.raises(HTTPException) as forbidden:
        api.delete(attachment_id, MagicMock(owner=False), database, storage)
    assert forbidden.value.status_code == 403
