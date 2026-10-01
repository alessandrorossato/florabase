import asyncio
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import Connection, Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from florabase.attachments.model import Attachment
from florabase.attachments.storage import AttachmentStorage, AttachmentStorageError
from florabase.botanical_identities.service import list_botanical_identity_directory
from florabase.collection_photos.model import (
    BotanicalIdentityCoverImage,
    MediaAsset,
    RecordMediaLink,
)
from florabase.collection_photos.primary import primary_summaries, set_primary
from florabase.collection_photos.schemas import PrimaryPhotoSelection
from florabase.collection_photos.service import list_photos, read_identity_cover
from florabase.media import copies, service
from florabase.media.fetch import ExternalFetchError
from florabase.media.schemas import LinkWrite

from .test_attachment_api import attachment_browser, authenticated_browser  # noqa: F401
from .test_shared_media import external, fixture

pytestmark = pytest.mark.integration


def png(color: str = "green") -> bytes:
    stream = BytesIO()
    Image.new("RGB", (640, 320), color).save(stream, "PNG")
    return stream.getvalue()


def test_external_snapshot_lifecycle_retains_identity_links_primary_and_covers(
    database_connection: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = png()
    monkeypatch.setattr(copies, "fetch_image", lambda *_args: (payload, "image/png"))
    storage = AttachmentStorage(tmp_path)
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        plant, _, identity = fixture(database)
        asset = external(database)
        asset_id = asset.id
        link = service.create_link(
            database, "plant", plant.id, asset_id, LinkWrite(caption="Retained", display_order=7)
        )
        link_id = link.id
        set_primary(
            database,
            storage,
            "plant",
            plant.id,
            PrimaryPhotoSelection(kind="external", photo_id=link_id),
        )
        cover = BotanicalIdentityCoverImage(
            botanical_identity_id=identity.id, source_mode="external", media_asset=asset
        )
        database.add(cover)
        database.commit()
        before = service.asset_detail(database, asset_id)
        asyncio.run(copies.save_copy(database, storage, asset_id, refresh=False))
        saved = service.read_asset(database, asset_id)
        assert saved.id == asset_id
        assert saved.kind == "external"
        assert saved.fetched_at
        assert saved.image_url == before.image_url
        assert saved.attribution == before.attribution
        assert saved.content_url
        assert saved.thumbnail_url
        assert not saved.can_delete
        attachment = database.get(
            Attachment, service.require_asset(database, asset_id).attachment_id
        )
        assert attachment is not None
        path = storage.active_path(attachment.storage_key, attachment.byte_size)
        assert path.read_bytes() == payload
        first_thumb = service.asset_thumbnail(storage, asset, attachment)
        assert primary_summaries(database, "plant", [plant.id])[plant.id].thumbnail_url
        photo = list_photos(database, "plant", plant.id)[0]
        assert isinstance(photo, RecordMediaLink)
        assert photo.thumbnail_url
        saved_cover = read_identity_cover(database, identity.id)
        assert saved_cover
        assert saved_cover.kind == "external"
        assert saved_cover.content_url
        directory = list_botanical_identity_directory(database)
        assert directory[0][1] == "local"
        assert directory[0][2] is not None
        assert directory[0][2].startswith("/api/v1/media-assets/")
        assert service.list_assets(database).items[0].content_url == saved.content_url
        with pytest.raises(service.MediaError, match="already saved"):
            asyncio.run(copies.save_copy(database, storage, asset_id, refresh=False))
        database.rollback()
        payload = png("red")
        asyncio.run(copies.save_copy(database, storage, asset_id, refresh=True))
        refreshed = service.asset_detail(database, asset_id)
        assert refreshed.links == before.links
        assert refreshed.covers == before.covers
        assert refreshed.content_url != saved.content_url
        assert refreshed.thumbnail_url != saved.thumbnail_url
        assert not path.exists()
        new_attachment = database.get(
            Attachment, service.require_asset(database, asset_id).attachment_id
        )
        assert new_attachment is not None
        new_path = storage.active_path(new_attachment.storage_key, new_attachment.byte_size)
        assert new_path.read_bytes() == payload
        assert service.asset_thumbnail(storage, asset, new_attachment) != first_thumb
        assert len(list((tmp_path / ".thumbnails").glob("*.webp"))) == 1

        def failed(*_args: object) -> tuple[bytes, str]:
            raise ExternalFetchError("The external image is unavailable.")

        monkeypatch.setattr(copies, "fetch_image", failed)
        with pytest.raises(ExternalFetchError):
            asyncio.run(copies.save_copy(database, storage, asset_id, refresh=True))
        database.rollback()
        assert service.read_asset(database, asset_id).content_url == refreshed.content_url
        assert new_path.read_bytes() == payload
        copies.remove_copy(database, storage, asset_id)
        removed = service.asset_detail(database, asset_id)
        assert removed.content_url is None
        assert removed.fetched_at is None
        assert removed.links == before.links
        assert removed.covers == before.covers
        assert not new_path.exists()
        assert primary_summaries(database, "plant", [plant.id])[plant.id].thumbnail_url is None
        assert service.require_asset(database, asset_id).image_url == before.image_url
        monkeypatch.setattr(copies, "fetch_image", lambda *_args: (payload, "image/png"))
        asyncio.run(copies.save_copy(database, storage, asset_id, refresh=False))
        service.unlink(database, link_id)
        database.delete(cover)
        database.commit()
        service.delete_asset(database, storage, asset_id)
        assert database.get(MediaAsset, asset_id) is None
        assert not [path for path in storage.objects.rglob("*") if path.is_file()]
        assert not list((tmp_path / ".thumbnails").glob("*.webp"))


@pytest.mark.parametrize("invalid", [b"not an image", png()[:-20]], ids=["invalid", "truncated"])
def test_invalid_refresh_retains_snapshot(
    database_connection: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalid: bytes
) -> None:
    storage = AttachmentStorage(tmp_path)
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        asset = external(database)
        monkeypatch.setattr(copies, "fetch_image", lambda *_args: (png(), "image/png"))
        asyncio.run(copies.save_copy(database, storage, asset.id, refresh=False))
        before = service.read_asset(database, asset.id)
        monkeypatch.setattr(copies, "fetch_image", lambda *_args: (invalid, "image/png"))
        with pytest.raises(AttachmentStorageError):
            asyncio.run(copies.save_copy(database, storage, asset.id, refresh=True))
        database.rollback()
        assert service.read_asset(database, asset.id).content_url == before.content_url
        assert len([path for path in storage.objects.rglob("*") if path.is_file()]) == 1


def test_cleanup_marker_cannot_alias_the_active_snapshot(
    database_connection: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = AttachmentStorage(tmp_path)
    monkeypatch.setattr(copies, "fetch_image", lambda *_args: (png(), "image/png"))
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        asset = external(database)
        asyncio.run(copies.save_copy(database, storage, asset.id, refresh=False))
        current = service.require_asset(database, asset.id).attachment_id
        assert current is not None
        asset.copy_cleanup_attachment_id = current
        with pytest.raises(IntegrityError, match="ck_media_assets_distinct_copy_cleanup"):
            database.flush()
        database.rollback()


def test_external_copy_http_explicit_auth_csrf_protected_storage(
    attachment_browser: tuple[tuple[str, str], AttachmentStorage],  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from .test_attachment_api import request

    browser, storage = attachment_browser
    created = request(
        "POST",
        "/api/v1/media-assets/external",
        browser=browser,
        mutation_headers=True,
        body={
            "image_url": "https://images.example.test/test.png",
            "source_url": "https://example.test/source",
            "attribution": "Author",
        },
    )
    endpoint = f"/api/v1/media-assets/{created.json()['id']}"
    calls: list[str] = []

    def fetch(url: str, _limit: int) -> tuple[bytes, str]:
        calls.append(url)
        return png(), "image/png"

    monkeypatch.setattr(copies, "fetch_image", fetch)
    for method, path in [
        ("POST", "/save-local-copy"),
        ("POST", "/refresh-local-copy"),
        ("DELETE", "/local-copy"),
    ]:
        assert request(method, endpoint + path).status_code == 401
        assert request(method, endpoint + path, browser=browser).status_code == 403
    assert not calls
    saved = request("POST", endpoint + "/save-local-copy", browser=browser, mutation_headers=True)
    assert saved.status_code == 200
    assert len(calls) == 1
    content = saved.json()["content_url"]
    assert request("GET", content).status_code == 401
    assert request("GET", content, browser=browser).content == png()
    assert request("GET", saved.json()["thumbnail_url"], browser=browser).status_code == 200
    assert request("GET", endpoint, browser=browser).json()["fetched_at"]
    assert len(calls) == 1
    assert (
        request(
            "POST", endpoint + "/refresh-local-copy", browser=browser, mutation_headers=True
        ).status_code
        == 200
    )
    assert len(calls) == 2
    assert (
        request("DELETE", endpoint + "/local-copy", browser=browser, mutation_headers=True).json()[
            "content_url"
        ]
        is None
    )
    assert len(calls) == 2
    assert not [path for path in storage.objects.rglob("*") if path.is_file()]
    assert request("DELETE", endpoint, browser=browser, mutation_headers=True).status_code == 204


@pytest.mark.parametrize(
    ("first_action", "second"),
    [
        ("refresh", "save"),
        ("refresh", "refresh"),
        ("refresh", "remove"),
        ("refresh", "delete"),
        ("save", "save"),
    ],
)
def test_copy_mutations_serialize_with_refresh(
    database_engine: Engine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    second: str,
    first_action: str,
) -> None:
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor

    from sqlalchemy import text

    storage = AttachmentStorage(tmp_path)
    with Session(database_engine) as database:
        asset_id = external(database).id
        monkeypatch.setattr(copies, "fetch_image", lambda *_args: (png(), "image/png"))
        if first_action == "refresh":
            asyncio.run(copies.save_copy(database, storage, asset_id, refresh=False))
    entered = threading.Event()
    release = threading.Event()
    calls: list[int] = []

    def delayed(*_args: object) -> tuple[bytes, str]:
        calls.append(1)
        if len(calls) == 1:
            entered.set()
            assert release.wait(timeout=10)
        return png("red"), "image/png"

    monkeypatch.setattr(copies, "fetch_image", delayed)
    worker_pid: dict[str, int] = {}
    started = threading.Event()

    def refreshing() -> None:
        with Session(database_engine) as database:
            asyncio.run(
                copies.save_copy(database, storage, asset_id, refresh=first_action == "refresh")
            )

    def competing() -> str:
        with Session(database_engine) as database:
            pid = database.scalar(text("SELECT pg_backend_pid()"))
            assert pid is not None
            worker_pid["pid"] = pid
            started.set()
            try:
                if second == "delete":
                    service.delete_asset(database, storage, asset_id)
                elif second == "remove":
                    copies.remove_copy(database, storage, asset_id)
                else:
                    asyncio.run(
                        copies.save_copy(database, storage, asset_id, refresh=second == "refresh")
                    )
                return "done"
            except service.MediaError as error:
                return error.code

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(refreshing)
            assert entered.wait(timeout=5)
            other = executor.submit(competing)
            try:
                assert started.wait(timeout=5)
                deadline = time.monotonic() + 5
                waiting = False
                while time.monotonic() < deadline and not other.done():
                    with database_engine.connect() as observer:
                        waiting = (
                            observer.scalar(
                                text(
                                    "SELECT wait_event_type FROM pg_stat_activity WHERE pid = :pid"
                                ),
                                {"pid": worker_pid["pid"]},
                            )
                            == "Lock"
                        )
                    if waiting:
                        break
                assert waiting
            finally:
                release.set()
            first.result(timeout=10)
            assert other.result(timeout=10) == ("media_copy_exists" if second == "save" else "done")
        with Session(database_engine) as database:
            asset = database.get(MediaAsset, asset_id)
            if second == "delete":
                assert asset is None
            else:
                assert asset is not None
                assert asset.copy_cleanup_attachment_id is None
                assert (asset.attachment_id is None) == (second == "remove")
            expected = 0 if second in {"remove", "delete"} else 1
            assert len([path for path in storage.objects.rglob("*") if path.is_file()]) == expected
            assert len(list((tmp_path / ".thumbnails").glob("*.webp"))) == expected
    finally:
        release.set()
        with Session(database_engine) as database:
            if database.get(MediaAsset, asset_id):
                service.delete_asset(database, storage, asset_id)


def test_remove_cleanup_failure_is_durable_and_retryable(
    database_connection: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = AttachmentStorage(tmp_path)
    monkeypatch.setattr(copies, "fetch_image", lambda *_args: (png(), "image/png"))
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        asset = external(database)
        asset_id = asset.id
        asyncio.run(copies.save_copy(database, storage, asset_id, refresh=False))
        original_delete = storage.delete_file

        def unavailable(_key: str) -> bool:
            raise AttachmentStorageError(
                "attachment_delete_failed", "Could not remove attachment content"
            )

        monkeypatch.setattr(storage, "delete_file", unavailable)
        with pytest.raises(AttachmentStorageError):
            copies.remove_copy(database, storage, asset_id)
        database.rollback()
        current = service.read_asset(database, asset_id)
        assert current.content_url is None
        assert current.local_copy_cleanup_pending
        assert service.require_asset(database, asset_id).kind == "external"
        monkeypatch.setattr(storage, "delete_file", original_delete)
        copies.remove_copy(database, storage, asset_id)
        assert not service.read_asset(database, asset_id).local_copy_cleanup_pending
        assert not [path for path in storage.objects.rglob("*") if path.is_file()]


def test_pixel_bomb_refresh_retains_valid_copy(
    database_connection: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = AttachmentStorage(tmp_path)
    payload = png()
    monkeypatch.setattr(copies, "fetch_image", lambda *_args: (payload, "image/png"))
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        asset_id = external(database).id
        asyncio.run(copies.save_copy(database, storage, asset_id, refresh=False))
        before = service.read_asset(database, asset_id)
        monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)
        with pytest.raises(AttachmentStorageError, match="safe decoding limit"):
            asyncio.run(copies.save_copy(database, storage, asset_id, refresh=True))
        database.rollback()
        assert service.read_asset(database, asset_id).content_url == before.content_url
        assert len([path for path in storage.objects.rglob("*") if path.is_file()]) == 1


def test_refresh_database_failure_keeps_old_copy(
    database_connection: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlalchemy.exc import SQLAlchemyError

    storage = AttachmentStorage(tmp_path)
    monkeypatch.setattr(copies, "fetch_image", lambda *_args: (png(), "image/png"))
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        asset_id = external(database).id
        asyncio.run(copies.save_copy(database, storage, asset_id, refresh=False))
        before = service.read_asset(database, asset_id)
        monkeypatch.setattr(copies, "fetch_image", lambda *_args: (png("red"), "image/png"))
        commit = database.commit

        def failed() -> None:
            raise SQLAlchemyError("simulated metadata failure")

        monkeypatch.setattr(database, "commit", failed)
        with pytest.raises(SQLAlchemyError):
            asyncio.run(copies.save_copy(database, storage, asset_id, refresh=True))
        monkeypatch.setattr(database, "commit", commit)
        assert service.read_asset(database, asset_id).content_url == before.content_url
        assert len([path for path in storage.objects.rglob("*") if path.is_file()]) == 1
        assert len(list((tmp_path / ".thumbnails").glob("*.webp"))) == 1


def test_external_snapshot_downgrade_is_guarded(
    database_engine: Engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from alembic.config import Config

    from alembic import command

    config = Config("alembic.ini")
    storage = AttachmentStorage(tmp_path)
    monkeypatch.setattr(copies, "fetch_image", lambda *_args: (png(), "image/png"))
    with Session(database_engine) as database:
        asset_id = external(database).id
        asyncio.run(copies.save_copy(database, storage, asset_id, refresh=False))
    try:
        with pytest.raises(RuntimeError, match="Remove external local copies"):
            command.downgrade(config, "20261001_0027")
        with Session(database_engine) as database:
            assert service.read_asset(database, asset_id).content_url
            copies.remove_copy(database, storage, asset_id)
        command.downgrade(config, "20261001_0027")
        command.upgrade(config, "head")
        with Session(database_engine) as database:
            asset = service.require_asset(database, asset_id)
            assert asset.kind == "external"
            assert asset.attachment_id is None
            assert asset.fetched_at is None
    finally:
        command.upgrade(config, "head")
        with Session(database_engine) as database:
            service.delete_asset(database, storage, asset_id)
