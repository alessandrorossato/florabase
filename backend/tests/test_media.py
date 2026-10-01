import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.datastructures import Headers

from florabase.attachments.model import Attachment
from florabase.attachments.storage import AttachmentStorage, AttachmentStorageError
from florabase.collection_photos.model import ExternalImageReference, MediaAsset, RecordMediaLink
from florabase.media import api, service
from florabase.media.schemas import (
    AssetMetadataWrite,
    AssetPageResponse,
    ExternalAssetCreate,
    LinkCreate,
    LinkWrite,
    TargetPageResponse,
)


def asset(kind: str = "external") -> MediaAsset:
    now = datetime.now(UTC)
    return MediaAsset(
        id=uuid7(),
        kind=kind,
        state="active",
        title="Leaf",
        attribution="Author",
        image_url="https://images.example.test/image.jpg" if kind == "external" else None,
        source_url="https://example.test/source" if kind == "external" else None,
        attachment_id=uuid7() if kind == "local" else None,
        created_at=now,
        updated_at=now,
    )


def external_payload() -> ExternalAssetCreate:
    return ExternalAssetCreate(
        image_url="https://images.example.test/image.jpg",
        source_url="https://example.test/source",
        attribution="Author",
    )


def attachment(row: MediaAsset) -> Attachment:
    return Attachment(
        id=row.attachment_id,
        state="active",
        storage_key="objects/aa/" + "a" * 32,
        original_filename="leaf.png",
        media_type="image/png",
        byte_size=10,
        sha256="a" * 64,
    )


def linked(row: MediaAsset) -> ExternalImageReference:
    now = datetime.now(UTC)
    return ExternalImageReference(
        id=uuid7(),
        media_asset_id=row.id,
        media_asset=row,
        plant_id=uuid7(),
        caption="Plant context",
        display_order=3,
        created_at=now,
        updated_at=now,
    )


def test_asset_availability_metadata_and_reference_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    database = MagicMock()
    database.scalar.return_value = None
    with pytest.raises(service.MediaError, match="not found"):
        service.require_asset(database, uuid7(), lock=True)
    row = asset("local")
    database.scalar.return_value = row
    assert service.require_asset(database, row.id) is row
    database.get.return_value = None
    with pytest.raises(service.MediaError, match="unavailable"):
        service.require_active(database, row)
    file = attachment(row)
    database.get.return_value = file
    service.require_active(database, row)
    file.state = "pending_delete"
    with pytest.raises(service.MediaError, match="unavailable"):
        service.require_active(database, row)
    file.state = "active"
    row.state = "pending_delete"
    with pytest.raises(service.MediaError, match="pending"):
        service.require_active(database, row)
    row.state = "active"
    database.scalar.side_effect = [1, 2]
    assert service.reference_counts(database, row.id) == (1, 2)
    monkeypatch.setattr(service, "require_asset", lambda *_args, **_kwargs: row)
    monkeypatch.setattr(service, "reference_counts", lambda *_args: (0, 1))
    response = service.read_asset(database, row.id)
    assert response.collection_link_count == 0
    assert response.cover_reference_count == 1
    assert not response.can_delete
    assert response.thumbnail_url == f"/api/v1/media-assets/{row.id}/thumbnail"
    row.state = "pending_delete"
    assert service.asset_response(row, file, 0, 0).content_url is None


@pytest.mark.parametrize("association", ["all", "linked", "unlinked"])
def test_gallery_filters_are_bounded_literal_search(association: str) -> None:
    from typing import Literal, cast

    database = MagicMock()
    row = asset()
    database.scalar.return_value = 1
    database.execute.return_value.all.return_value = [(row, None, 0, 1)]
    page = service.list_assets(
        database,
        query="  50%_ ",
        kind="external",
        target="plant",
        association=cast(Literal["all", "linked", "unlinked"], association),
        limit=24,
        offset=24,
    )
    assert page.total == 1
    assert page.offset == 24
    assert not page.items[0].can_delete
    statement = database.execute.call_args.args[0]
    assert statement.compile().params["title_1"] == "%50\\%\\_%"
    assert statement._limit_clause.value == 24
    assert statement._offset_clause.value == 24


def test_exact_link_target_locking_duplicate_and_database_conflicts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = MagicMock()
    database.scalar.return_value = None
    with pytest.raises(service.MediaError, match="not found"):
        service.lock_target(database, "plant", uuid7())
    database.scalar.return_value = object()
    assert service.lock_target(database, "plant", uuid7()) is not None
    row = asset()
    monkeypatch.setattr(service, "require_asset", lambda *_args, **_kwargs: row)
    database.scalar.return_value = uuid7()
    with pytest.raises(service.MediaError, match="already links"):
        service.create_link(database, "plant", uuid7(), row.id, LinkWrite())
    monkeypatch.setattr(service, "lock_target", lambda *_args: None)
    database.scalar.return_value = None
    result = service.create_link(
        database, "plant", uuid7(), row.id, LinkWrite(caption="Context"), commit=False
    )
    assert result.media_asset is row
    database.commit.assert_not_called()
    database.flush.side_effect = IntegrityError("duplicate", {}, Exception("duplicate"))
    with pytest.raises(service.MediaError, match="conflicted"):
        service.create_link(database, "plant", uuid7(), row.id, LinkWrite())
    database.rollback.assert_called_once()
    with pytest.raises(service.MediaError, match="no valid"):
        service.target_of(RecordMediaLink())
    link = linked(row)
    assert link.plant_id is not None
    database.scalar.side_effect = [link, link]
    assert service.locked_link(database, link.id, expected=("plant", link.plant_id)) is link
    database.scalar.side_effect = [None]
    assert service.locked_link(database, uuid7()) is None
    database.scalar.side_effect = [link]
    with pytest.raises(service.MediaError, match="does not belong"):
        service.locked_link(database, link.id, expected=("plant", uuid7()))


def test_link_edits_and_unlink_touch_only_link(monkeypatch: pytest.MonkeyPatch) -> None:
    database = MagicMock()
    row = asset()
    link = linked(row)
    assert link.plant_id is not None
    monkeypatch.setattr(service, "locked_link", lambda *_args: None)
    assert not service.unlink(database, uuid7())
    with pytest.raises(service.MediaError, match="not found"):
        service.update_link(database, uuid7(), LinkWrite())
    monkeypatch.setattr(service, "locked_link", lambda *_args: link)
    database.get.return_value = SimpleNamespace(label="Plant A")
    database.scalar.return_value = uuid7()
    response = service.update_link(database, link.id, LinkWrite(caption="Updated", display_order=8))
    assert response.caption == "Updated"
    assert response.display_order == 8
    assert response.is_primary
    assert service.unlink(database, link.id)
    database.delete.assert_called_once_with(link)
    record_id = uuid7()
    event_label = service.target_label(SimpleNamespace(id=record_id, kind="movement"), "event")
    assert event_label == f"Movement event · {str(record_id)[-8:]}"
    seed_label = service.target_label(SimpleNamespace(id=record_id), "seed_lot")
    assert seed_label == f"Seed Lot · {str(record_id)[-8:]}"
    monkeypatch.setattr(service, "lock_target", lambda *_args: None)
    database.scalar.return_value = None
    assert service.next_order(database, "plant", uuid7()) == 0
    database.scalar.return_value = 9
    assert service.next_order(database, "plant", uuid7()) == 10


def test_asset_metadata_validation_and_external_creation(monkeypatch: pytest.MonkeyPatch) -> None:
    database = MagicMock()
    row = asset()
    monkeypatch.setattr(service, "require_asset", lambda *_args, **_kwargs: row)
    with pytest.raises(service.MediaError, match="requires attribution"):
        service.update_asset(database, row.id, AssetMetadataWrite())
    monkeypatch.setattr(
        service, "read_asset", lambda *_args: service.asset_response(row, None, 0, 0)
    )
    response = service.update_asset(
        database, row.id, AssetMetadataWrite(title="New", attribution="Credit")
    )
    assert response.title == "New"
    create = MagicMock()
    monkeypatch.setattr(service, "create_link", create)
    monkeypatch.setattr(service, "next_order", lambda *_args: 4)
    new = service.create_external_asset(
        database, external_payload(), target="plant", target_id=uuid7(), caption="Context"
    )
    assert new.kind == "external"
    assert create.call_args.args[4].display_order == 4
    service.create_external_asset(database, external_payload(), commit=False)
    database.flush.side_effect = SQLAlchemyError("offline")
    with pytest.raises(SQLAlchemyError):
        service.create_external_asset(database, external_payload())
    database.rollback.assert_called_once()


def test_local_upload_is_atomic_and_failure_cleans_only_new_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = AttachmentStorage(tmp_path)
    database = MagicMock()
    image = BytesIO()
    Image.new("RGB", (640, 320), "green").save(image, "PNG")

    def upload() -> UploadFile:
        return UploadFile(
            filename="leaf.png",
            file=BytesIO(image.getvalue()),
            headers=Headers({"content-type": "image/png"}),
        )

    create = MagicMock()
    monkeypatch.setattr(service, "create_link", create)
    monkeypatch.setattr(service, "next_order", lambda *_args: 5)
    row = asyncio.run(
        service.upload_asset(
            database,
            storage,
            upload(),
            AssetMetadataWrite(),
            target="plant",
            target_id=uuid7(),
            caption="Context",
            commit=False,
        )
    )
    assert row.width == 640
    assert row.height == 320
    assert create.call_args.args[4].display_order == 5
    database.commit.assert_not_called()
    assert len(list(storage.objects.glob("*/*"))) == 1
    database.commit.side_effect = SQLAlchemyError("offline")
    with pytest.raises(SQLAlchemyError):
        asyncio.run(service.upload_asset(database, storage, upload(), AssetMetadataWrite()))
    assert len(list(storage.objects.glob("*/*"))) == 1
    database.rollback.assert_called_once()


@pytest.mark.parametrize(("links", "covers"), [(1, 0), (0, 1), (2, 1)])
def test_delete_guards_both_reference_types(
    links: int, covers: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    row = asset()
    database, storage = MagicMock(), MagicMock()
    monkeypatch.setattr(service, "require_asset", lambda *_args, **_kwargs: row)
    monkeypatch.setattr(service, "reference_counts", lambda *_args: (links, covers))
    with pytest.raises(service.MediaError, match=f"{links} collection link"):
        service.delete_asset(database, storage, row.id)
    database.delete.assert_not_called()
    storage.delete_file.assert_not_called()


def test_explicit_asset_deletion_pending_missing_and_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    row = asset()
    database, storage = MagicMock(), MagicMock()
    monkeypatch.setattr(service, "require_asset", lambda *_args, **_kwargs: row)
    monkeypatch.setattr(service, "reference_counts", lambda *_args: (0, 0))
    service.delete_asset(database, storage, row.id)
    database.delete.assert_called_once_with(row)
    storage.delete_file.assert_not_called()
    row = asset("local")
    file = attachment(row)
    database.reset_mock()
    database.scalar.return_value = None
    with pytest.raises(service.MediaError, match="metadata is missing"):
        service.delete_asset(database, storage, row.id)
    database.scalar.return_value = file
    storage.delete_file.return_value = False
    with pytest.raises(service.MediaError, match="pending a retry"):
        service.delete_asset(database, storage, row.id)
    assert row.state == "pending_delete"
    assert file.state == "pending_delete"
    cleanup = MagicMock()
    monkeypatch.setattr(service, "delete_thumbnail", cleanup)
    service.delete_asset(database, storage, row.id)
    cleanup.assert_called_once_with(storage, row, file)
    assert database.delete.call_args_list[-1].args == (file,)


def test_shared_thumbnail_cache_bounds_symlinks_and_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = AttachmentStorage(tmp_path)
    row = asset("local")
    file = attachment(row)
    path = storage.objects / "aa" / ("a" * 32)
    path.parent.mkdir()
    content = BytesIO()
    Image.new("RGB", (640, 320), "green").save(content, "PNG")
    path.write_bytes(content.getvalue())
    file.byte_size = path.stat().st_size
    first = service.asset_thumbnail(storage, row, file)
    from florabase.collection_photos import service as photos

    render = MagicMock(side_effect=AssertionError("cache must be reused"))
    monkeypatch.setattr(photos, "render_identity_cover_thumbnail", render)
    assert service.asset_thumbnail(storage, row, file) == first
    render.assert_not_called()
    cache = next((tmp_path / ".thumbnails").glob("*.webp"))
    with Image.open(BytesIO(first)) as image:
        assert image.size == (320, 160)
    service.delete_thumbnail(storage, row, file)
    assert not cache.exists()
    cache.symlink_to(path)
    with pytest.raises(AttachmentStorageError, match="unsafe"):
        service.asset_thumbnail(storage, row, file)
    with pytest.raises(AttachmentStorageError, match="unsafe"):
        service.delete_thumbnail(storage, row, file)


def test_media_api_routes_preserve_reader_writer_error_contracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, storage, actor = MagicMock(), MagicMock(), MagicMock(owner=True)
    row = asset()
    response = service.asset_response(row, None, 0, 0)
    monkeypatch.setattr(
        service,
        "list_assets",
        lambda *_args, **_kwargs: AssetPageResponse(items=[], total=0, limit=24, offset=0),
    )
    assert api.list_media(database, actor, "", None, "all", None, 24, 0).total == 0
    monkeypatch.setattr(
        service,
        "target_choices",
        lambda *_args: TargetPageResponse(items=[], total=0, limit=20, offset=0),
    )
    assert api.list_targets("plant", database, actor, "", 20, 0).total == 0
    monkeypatch.setattr(service, "asset_detail", lambda *_args: response)
    assert api.get_media(row.id, database, actor) is response
    monkeypatch.setattr(service, "create_external_asset", lambda *_args: row)
    monkeypatch.setattr(service, "read_asset", lambda *_args: response)
    assert api.create_external(external_payload(), database, actor) is response
    monkeypatch.setattr(service, "update_asset", lambda *_args: response)
    assert api.edit_media(row.id, AssetMetadataWrite(), database, actor) is response
    link = linked(row)
    assert link.plant_id is not None
    monkeypatch.setattr(service, "create_link", lambda *_args: link)
    record = SimpleNamespace(id=link.plant_id)
    database.get.return_value = record
    assert (
        api.link_media(
            "plant", link.plant_id, LinkCreate(media_asset_id=row.id), database, actor
        ).id
        == link.id
    )
    monkeypatch.setattr(
        service, "update_link", lambda *_args: service.link_response(link, record, False)
    )
    assert api.edit_link(link.id, LinkWrite(), database, actor).id == link.id
    monkeypatch.setattr(service, "unlink", lambda *_args: True)
    assert api.unlink_media(link.id, database, actor).status_code == 204
    monkeypatch.setattr(service, "unlink", lambda *_args: False)
    with pytest.raises(HTTPException) as missing:
        api.unlink_media(link.id, database, actor)
    assert missing.value.status_code == 404
    monkeypatch.setattr(service, "delete_asset", lambda *_args: None)
    assert api.delete_media(row.id, database, storage, actor).status_code == 204

    def conflict(*_args: object, **_kwargs: object) -> None:
        raise service.MediaError("referenced", "References remain")

    for method in ("asset_detail", "update_asset", "create_link", "update_link", "delete_asset"):
        monkeypatch.setattr(service, method, conflict)
    plant_id = link.plant_id
    assert plant_id is not None
    calls: list[Callable[[], object]] = [
        lambda: api.get_media(row.id, database, actor),
        lambda: api.edit_media(row.id, AssetMetadataWrite(), database, actor),
        lambda: api.link_media(
            "plant", plant_id, LinkCreate(media_asset_id=row.id), database, actor
        ),
        lambda: api.edit_link(link.id, LinkWrite(), database, actor),
        lambda: api.delete_media(row.id, database, storage, actor),
    ]
    for call in calls:
        with pytest.raises(HTTPException) as blocked:
            call()
        assert blocked.value.status_code == 409


def test_thumbnail_api_privacy_validator_and_no_external_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, storage, actor = MagicMock(), MagicMock(), MagicMock()
    row = asset("local")
    file = attachment(row)
    database.get.return_value = file
    monkeypatch.setattr(service, "require_asset", lambda *_args, **_kwargs: row)
    monkeypatch.setattr(service, "asset_thumbnail", lambda *_args: b"webp")
    response = api.thumbnail(row.id, database, storage, actor)
    assert response.body == b"webp"
    assert response.headers["vary"] == "Cookie"
    assert response.headers["cache-control"].startswith("private")
    assert (
        api.thumbnail(row.id, database, storage, actor, response.headers["etag"]).status_code == 304
    )
    row.kind = "external"
    row.attachment_id = None
    with pytest.raises(HTTPException) as unloaded:
        api.thumbnail(row.id, database, storage, actor)
    assert unloaded.value.status_code == 404
    row.state = "pending_delete"
    with pytest.raises(HTTPException) as pending:
        api.thumbnail(row.id, database, storage, actor)
    assert pending.value.status_code == 409


def test_upload_api_validation_and_write_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    database, storage, actor = MagicMock(), MagicMock(), MagicMock(owner=True)
    row = asset()
    response = service.asset_response(row, None, 0, 0)
    upload = MagicMock(spec=UploadFile)
    monkeypatch.setattr(service, "upload_asset", AsyncMock(return_value=row))
    monkeypatch.setattr(service, "read_asset", lambda *_args: response)
    assert (
        asyncio.run(api.upload_media(database, storage, actor, upload, "Title", None)) is response
    )
    with pytest.raises(HTTPException) as invalid:
        asyncio.run(api.upload_media(database, storage, actor, upload, "a" * 2001, None))
    assert invalid.value.status_code == 422
    for error in (
        AttachmentStorageError("unsupported_image_type", "Invalid image"),
        SQLAlchemyError("offline"),
    ):
        monkeypatch.setattr(service, "upload_asset", AsyncMock(side_effect=error))
        with pytest.raises(HTTPException):
            asyncio.run(api.upload_media(database, storage, actor, upload, None, None))
    for error in (
        AttachmentStorageError("attachment_delete_failed", "Failed"),
        SQLAlchemyError("offline"),
    ):
        monkeypatch.setattr(service, "delete_asset", MagicMock(side_effect=error))
        with pytest.raises(HTTPException):
            api.delete_media(row.id, database, storage, actor)


def test_asset_detail_batches_targets_and_reports_cover_references(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from florabase.collection_photos.model import (
        BotanicalIdentityCoverImage,
        CollectionPrimaryPhoto,
    )

    database = MagicMock()
    row = asset()
    link = linked(row)
    record = SimpleNamespace(id=link.plant_id, label="Plant A")
    cover = BotanicalIdentityCoverImage(
        id=uuid7(), botanical_identity_id=uuid7(), media_asset_id=row.id, source_mode="external"
    )
    identity = SimpleNamespace(id=cover.botanical_identity_id, scientific_name="Sunflower")
    summary = service.asset_response(row, None, 1, 1)
    monkeypatch.setattr(service, "read_asset", lambda *_args: summary)
    database.scalars.side_effect = [
        SimpleNamespace(all=lambda: [link]),
        [record],
        SimpleNamespace(all=lambda: [CollectionPrimaryPhoto(external_image_reference_id=link.id)]),
    ]
    database.execute.return_value.all.return_value = [(cover, identity)]
    detail = service.asset_detail(database, row.id)
    assert detail.links[0].is_primary
    assert detail.links[0].target_label == "Plant A"
    assert detail.covers[0].label == "Sunflower"
    database.scalars.side_effect = [SimpleNamespace(all=list)]
    database.execute.return_value.all.return_value = []
    assert service.asset_detail(database, row.id).links == []


@pytest.mark.parametrize("target", ["seed_lot", "sowing", "plant", "plant_group", "event"])
def test_target_picker_is_paged_searchable_and_uses_explicit_target_types(target: str) -> None:
    from typing import cast

    from florabase.media.schemas import MediaTarget

    database = MagicMock()
    database.scalar.return_value = 1
    record = SimpleNamespace(id=uuid7(), label=None, lifecycle="dead", kind="observation")
    identity = SimpleNamespace(
        common_name="Sunflower", cultivar_name=None, scientific_name="Helianthus"
    )
    database.execute.return_value.all.return_value = [(record, identity)]
    page = service.target_choices(database, cast(MediaTarget, target), "Sun%_", 20, 20)
    assert page.total == 1
    assert page.offset == 20
    assert "Sunflower" in page.items[0].label
    assert "dead" in page.items[0].label
    assert page.items[0].label.endswith(str(record.id)[-8:])
    assert service.target_label(record, cast(MediaTarget, target)).endswith(str(record.id)[-8:])
    record.label = "Named target"
    assert (
        "Named target"
        in service.target_choices(database, cast(MediaTarget, target), "", 20, 0).items[0].label
    )
