from unittest.mock import MagicMock
from uuid import uuid7

import pytest

from florabase.attachments.model import Attachment, AttachmentState
from florabase.attachments.storage import AttachmentStorageError
from florabase.collection_photos import primary
from florabase.collection_photos.model import (
    CollectionPrimaryPhoto,
    ExternalImageReference,
    LocalCollectionPhoto,
)
from florabase.collection_photos.schemas import PrimaryPhotoResponse, PrimaryPhotoSelection
from florabase.collection_photos.service import CollectionPhotoError


def test_primary_summary_fails_closed_for_missing_inactive_or_wrong_target() -> None:
    target_id, photo_id = uuid7(), uuid7()
    designation = CollectionPrimaryPhoto(plant_id=target_id, local_collection_photo_id=photo_id)
    assert primary._summary(designation, "plant", {}, {}) is None

    photo = LocalCollectionPhoto(id=photo_id, plant_id=target_id)
    inactive = Attachment(state=AttachmentState.PENDING_DELETE)
    assert primary._summary(designation, "plant", {photo_id: (photo, inactive)}, {}) is None

    active = Attachment(state=AttachmentState.ACTIVE)
    wrong_target = LocalCollectionPhoto(id=photo_id, plant_id=uuid7())
    assert primary._summary(designation, "plant", {photo_id: (wrong_target, active)}, {}) is None


def test_target_lookup_locks_and_primary_read_is_target_scoped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_id = uuid7()
    database = MagicMock()
    database.scalar.return_value = target_id
    for target in ("seed_lot", "plant", "plant_group"):
        primary._require_target(database, target, target_id, lock=True)
        primary._require_target(database, target, target_id, lock=False)

    database.scalar.return_value = None
    with pytest.raises(CollectionPhotoError, match="Collection record not found"):
        primary._require_target(database, "plant", target_id, lock=False)

    response = PrimaryPhotoResponse(kind="external", photo_id=uuid7(), thumbnail_url=None)
    monkeypatch.setattr(primary, "primary_summaries", lambda *_args: {target_id: response})
    database.scalar.return_value = target_id
    assert primary.read_primary(database, "plant", target_id) == response


def test_primary_summary_builds_local_and_external_responses() -> None:
    target_id, local_id, external_id = uuid7(), uuid7(), uuid7()
    local_row = CollectionPrimaryPhoto(plant_id=target_id, local_collection_photo_id=local_id)
    local = LocalCollectionPhoto(id=local_id, plant_id=target_id)
    attachment = Attachment(state=AttachmentState.ACTIVE)
    result = primary._summary(local_row, "plant", {local_id: (local, attachment)}, {})
    assert result is not None
    assert result.kind == "local"
    assert result.thumbnail_url is not None

    external_row = CollectionPrimaryPhoto(
        plant_id=target_id, external_image_reference_id=external_id
    )
    external = ExternalImageReference(id=external_id, plant_id=target_id)
    result = primary._summary(external_row, "plant", {}, {external_id: external})
    assert result is not None
    assert result.kind == "external"
    assert result.thumbnail_url is None
    wrong = ExternalImageReference(id=external_id, plant_id=uuid7())
    assert primary._summary(external_row, "plant", {}, {external_id: wrong}) is None


def test_primary_summaries_batches_external_photos() -> None:
    target_id, external_id = uuid7(), uuid7()
    external_row = CollectionPrimaryPhoto(
        plant_id=target_id, external_image_reference_id=external_id
    )
    external = ExternalImageReference(id=external_id, plant_id=target_id)
    database = MagicMock()
    database.scalars.side_effect = [
        MagicMock(all=MagicMock(return_value=[external_row])),
        [external],
    ]

    assert primary.primary_summaries(database, "plant", []) == {}
    summaries = primary.primary_summaries(database, "plant", [target_id])
    assert [summary.kind for summary in summaries.values()] == ["external"]
    assert database.scalars.call_count == 2


def test_primary_mutation_errors_and_clear_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    target_id, photo_id = uuid7(), uuid7()
    selection = PrimaryPhotoSelection(kind="external", photo_id=photo_id)
    database = MagicMock()
    monkeypatch.setattr(primary, "_require_target", lambda *_args, **_kwargs: None)
    from florabase.media import service as media

    monkeypatch.setattr(
        media, "locked_link", lambda database, *_args, **_kwargs: database.scalar("locked link")
    )
    monkeypatch.setattr(media, "require_active", lambda *_args: None)
    database.scalar.return_value = None
    with pytest.raises(CollectionPhotoError, match="Collection photo not found"):
        primary.set_primary(database, MagicMock(), "plant", target_id, selection)

    photo = ExternalImageReference(id=photo_id, plant_id=uuid7())
    database.scalar.return_value = photo
    with pytest.raises(CollectionPhotoError, match="does not belong"):
        primary.set_primary(database, MagicMock(), "plant", target_id, selection)

    local_selection = PrimaryPhotoSelection(kind="local", photo_id=photo_id)
    local = LocalCollectionPhoto(id=photo_id, plant_id=target_id, attachment_id=uuid7())
    database.scalar.side_effect = [local, None]
    with pytest.raises(CollectionPhotoError, match="unavailable"):
        primary.set_primary(database, MagicMock(), "plant", target_id, local_selection)

    database.scalar.side_effect = [local, Attachment(state=AttachmentState.ACTIVE), None]
    storage = MagicMock()
    storage.active_path.side_effect = AttachmentStorageError("missing", "not found")
    with pytest.raises(CollectionPhotoError, match="content is unavailable"):
        primary.set_primary(database, storage, "plant", target_id, local_selection)

    database.scalar.side_effect = [local, Attachment(state=AttachmentState.ACTIVE), None]
    storage.active_path.side_effect = None
    response = primary.set_primary(database, storage, "plant", target_id, local_selection)
    assert response.kind == "local"
    assert response.photo_id == photo_id
    database.add.assert_called_once()
    database.commit.assert_called_once()

    existing = CollectionPrimaryPhoto(plant_id=target_id)
    monkeypatch.setattr(primary, "_designation", lambda *_args: existing)
    database.scalar.side_effect = [ExternalImageReference(id=photo_id, plant_id=target_id)]
    response = primary.set_primary(database, MagicMock(), "plant", target_id, selection)
    assert response.kind == "external"
    assert existing.local_collection_photo_id is None

    monkeypatch.setattr(primary, "_require_target", lambda *_args, **_kwargs: None)
    database.delete.reset_mock()
    monkeypatch.setattr(primary, "_designation", lambda *_args: existing)
    primary.clear_primary(database, "plant", target_id)
    database.delete.assert_called_once_with(existing)
    monkeypatch.setattr(primary, "_designation", lambda *_args: None)
    primary.clear_primary(database, "plant", target_id)

    database.scalar.side_effect = None
    database.scalar.return_value = existing
    primary.clear_photo_primary(database, "external", photo_id)
    database.delete.assert_called_with(existing)
    database.flush.assert_called_once()
