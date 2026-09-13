from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid7

import pytest
from sqlalchemy.exc import SQLAlchemyError

from florabase.attachments.model import Attachment, AttachmentState
from florabase.attachments.service import AttachmentOperationError, delete_attachment
from florabase.attachments.storage import AttachmentStorageError


def attachment(state: AttachmentState = AttachmentState.ACTIVE) -> Attachment:
    return Attachment(
        id=uuid7(),
        storage_key="objects/aa/" + "a" * 32,
        original_filename="leaf.png",
        media_type="image/png",
        byte_size=5,
        sha256="a" * 64,
        state=state,
        created_at=datetime.now(UTC),
    )


def database_for(item: Attachment) -> MagicMock:
    database = MagicMock()
    database.scalar.return_value = item
    return database


def test_successful_delete_commits_pending_before_unlink_and_removes_row() -> None:
    item = attachment()
    database = database_for(item)
    storage = MagicMock()
    storage.delete_file.return_value = True

    assert delete_attachment(database, storage, item.id) is True
    assert item.state == AttachmentState.PENDING_DELETE
    assert database.commit.call_count == 2
    database.delete.assert_called_once_with(item)


def test_unlink_failure_retains_committed_pending_state_for_retry() -> None:
    item = attachment()
    database = database_for(item)
    storage = MagicMock()
    storage.delete_file.side_effect = AttachmentStorageError(
        "attachment_delete_failed", "Could not remove attachment content"
    )

    with pytest.raises(AttachmentStorageError):
        delete_attachment(database, storage, item.id)
    assert item.state == AttachmentState.PENDING_DELETE
    database.commit.assert_called_once()
    database.delete.assert_not_called()

    storage.delete_file.side_effect = None
    storage.delete_file.return_value = True
    assert delete_attachment(database, storage, item.id) is True
    database.delete.assert_called_once_with(item)


def test_missing_active_content_is_reported_then_pending_retry_completes() -> None:
    item = attachment()
    database = database_for(item)
    storage = MagicMock()
    storage.delete_file.return_value = False

    with pytest.raises(AttachmentOperationError) as caught:
        delete_attachment(database, storage, item.id)
    assert caught.value.code == "attachment_content_missing"
    assert item.state == AttachmentState.PENDING_DELETE
    assert database.commit.call_count == 1

    assert delete_attachment(database, storage, item.id) is True
    assert database.commit.call_count == 2
    database.delete.assert_called_once_with(item)


def test_delete_database_failures_are_truthful() -> None:
    item = attachment()
    database = database_for(item)
    database.commit.side_effect = SQLAlchemyError("unavailable")
    storage = MagicMock()

    with pytest.raises(AttachmentOperationError) as pending_failure:
        delete_attachment(database, storage, item.id)
    assert pending_failure.value.code == "attachment_delete_state_failed"
    storage.delete_file.assert_not_called()
    database.rollback.assert_called_once()

    item.state = AttachmentState.PENDING_DELETE
    database.reset_mock()
    database.scalar.return_value = item
    database.commit.side_effect = SQLAlchemyError("unavailable")
    storage.delete_file.return_value = False
    with pytest.raises(AttachmentOperationError) as metadata_failure:
        delete_attachment(database, storage, item.id)
    assert metadata_failure.value.code == "attachment_metadata_delete_failed"
    database.rollback.assert_called_once()


def test_delete_missing_metadata_returns_false() -> None:
    database = MagicMock()
    database.scalar.return_value = None
    assert delete_attachment(database, MagicMock(), uuid7()) is False
