"""Live PostgreSQL proof of reuse, retention, relational guards and bounded reads."""

import asyncio
from io import BytesIO
from pathlib import Path
from uuid import uuid7

import pytest
from fastapi import UploadFile
from PIL import Image
from sqlalchemy import Connection, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from florabase.attachments.model import Attachment
from florabase.attachments.storage import AttachmentStorage
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.collection_photos.model import (
    BotanicalIdentityCoverImage,
    CollectionPrimaryPhoto,
    MediaAsset,
    RecordMediaLink,
)
from florabase.collection_photos.primary import primary_summaries, set_primary
from florabase.collection_photos.schemas import PrimaryPhotoSelection
from florabase.collection_photos.service import CollectionPhotoError
from florabase.main import app  # noqa: F401
from florabase.media import service
from florabase.media.schemas import AssetMetadataWrite, ExternalAssetCreate, LinkWrite
from florabase.plants.model import Plant
from florabase.provenance_sites.model import ProvenanceSite  # noqa: F401

from .test_attachment_api import attachment_browser, authenticated_browser  # noqa: F401

pytestmark = pytest.mark.integration


def fixture(database: Session) -> tuple[Plant, Plant, BotanicalIdentity]:
    identity = BotanicalIdentity(scientific_name="Media test species")
    database.add(identity)
    database.flush()
    a = Plant(botanical_identity_id=identity.id, direct_origin_kind="unknown", label="Plant A")
    b = Plant(botanical_identity_id=identity.id, direct_origin_kind="unknown", label="Plant B")
    database.add_all([a, b])
    database.flush()
    return a, b, identity


def external(database: Session) -> MediaAsset:
    return service.create_external_asset(
        database,
        ExternalAssetCreate(
            image_url="https://images.example.test/photo.jpg",
            source_url="https://example.test/source",
            attribution="Author",
        ),
    )


def test_shared_external_links_independent_primary_order_caption_and_retention(
    database_connection: Connection, tmp_path: Path
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        a, b, _ = fixture(database)
        asset = external(database)
        storage = AttachmentStorage(tmp_path)
        assert service.read_asset(database, asset.id).can_delete
        first = service.create_link(
            database, "plant", a.id, asset.id, LinkWrite(caption="First plant", display_order=4)
        )
        second = service.create_link(
            database, "plant", b.id, asset.id, LinkWrite(caption="Second plant", display_order=9)
        )
        first_id, second_id, asset_id = first.id, second.id, asset.id
        set_primary(
            database,
            storage,
            "plant",
            a.id,
            PrimaryPhotoSelection(kind="external", photo_id=first_id),
        )
        summary = primary_summaries(database, "plant", [a.id, b.id])
        assert summary[a.id].photo_id == first_id
        assert b.id not in summary
        detail = service.asset_detail(database, asset_id)
        assert [(link.caption, link.display_order, link.is_primary) for link in detail.links] == [
            ("First plant", 4, True),
            ("Second plant", 9, False),
        ]
        with pytest.raises(service.MediaError, match="2 record"):
            service.delete_asset(database, storage, asset_id)
        database.rollback()
        # The outer fixture transaction remains valid after the deliberately refused delete.
        assert service.unlink(database, first_id)
        assert service.require_asset(database, asset_id).kind == "external"
        assert database.get(RecordMediaLink, second_id) is not None
        assert primary_summaries(database, "plant", [a.id, b.id]) == {}
        assert service.unlink(database, second_id)
        assert service.read_asset(database, asset_id).can_delete
        assert service.list_assets(database, association="unlinked").total == 1
        service.delete_asset(database, storage, asset_id)
        assert database.get(MediaAsset, asset_id) is None


def test_local_reuse_stores_one_original_and_one_derivative_cover_guard(
    database_connection: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        a, b, identity = fixture(database)
        stream = BytesIO()
        Image.new("RGB", (640, 320), "green").save(stream, "PNG")
        from starlette.datastructures import Headers

        upload = UploadFile(
            filename="landscape.png",
            file=BytesIO(stream.getvalue()),
            headers=Headers({"content-type": "image/png"}),
        )
        storage = AttachmentStorage(tmp_path)
        asset = asyncio.run(
            service.upload_asset(
                database,
                storage,
                upload,
                AssetMetadataWrite(attribution="Gardener"),
                target="plant",
                target_id=a.id,
                caption="Plant A",
            )
        )
        asset_id = asset.id
        first = database.scalar(
            select(RecordMediaLink).where(RecordMediaLink.media_asset_id == asset_id)
        )
        assert first is not None
        second = service.create_link(
            database, "plant", b.id, asset_id, LinkWrite(caption="Plant B")
        )
        attachment = database.get(Attachment, asset.attachment_id)
        assert attachment is not None
        original = storage.active_path(attachment.storage_key, attachment.byte_size)
        assert original.read_bytes() == stream.getvalue()
        assert len([path for path in storage.objects.rglob("*") if path.is_file()]) == 1
        from florabase.collection_photos import service as photos

        original_renderer = photos.render_identity_cover_thumbnail
        calls = []

        def render(path: Path) -> bytes:
            calls.append(path)
            return original_renderer(path)

        monkeypatch.setattr(photos, "render_identity_cover_thumbnail", render)
        service.require_asset(database, asset_id, lock=True)
        thumbnail = service.asset_thumbnail(storage, asset, attachment)
        assert service.asset_thumbnail(storage, asset, attachment) == thumbnail
        assert len(calls) == 1
        assert len(list((tmp_path / ".thumbnails").glob("*.webp"))) == 1
        with Image.open(BytesIO(thumbnail)) as result:
            assert result.size == (320, 160)
        cover = BotanicalIdentityCoverImage(
            botanical_identity_id=identity.id, source_mode="local", media_asset=asset
        )
        database.add(cover)
        database.commit()
        assert service.unlink(database, first.id)
        assert service.unlink(database, second.id)
        unlinked = service.read_asset(database, asset_id)
        assert unlinked.collection_link_count == 0
        assert unlinked.cover_reference_count == 1
        assert not unlinked.can_delete
        with pytest.raises(service.MediaError, match="1 BotanicalIdentity"):
            service.delete_asset(database, storage, asset_id)
        assert original.exists()
        database.delete(cover)
        database.commit()
        service.delete_asset(database, storage, asset_id)
        assert not original.exists()


def test_database_duplicate_target_primary_source_and_pending_guards(
    database_connection: Connection, tmp_path: Path
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        a, b, _ = fixture(database)
        asset = external(database)
        link = service.create_link(database, "plant", a.id, asset.id, LinkWrite())
        with pytest.raises(service.MediaError, match="already links"):
            service.create_link(database, "plant", a.id, asset.id, LinkWrite())
        with pytest.raises(service.MediaError, match="not found"):
            service.create_link(database, "plant", uuid7(), asset.id, LinkWrite())
        for target in ({"plant_id": a.id}, {"plant_id": a.id, "seed_lot_id": uuid7()}, {}):
            with database.begin_nested():
                database.add(type(link)(media_asset=asset, **target))
                with pytest.raises(IntegrityError):
                    database.flush()
                    # The savepoint context rolls back the failed flush.
        with database.begin_nested():
            database.add(CollectionPrimaryPhoto(plant_id=b.id, external_image_reference_id=link.id))
            with pytest.raises(IntegrityError):
                database.flush()
                # The savepoint context rolls back the failed flush.
        with database.begin_nested():
            database.add(CollectionPrimaryPhoto(plant_id=a.id, local_collection_photo_id=link.id))
            with pytest.raises(IntegrityError, match="source kind"):
                database.flush()
                # The savepoint context rolls back the failed flush.
        with database.begin_nested():
            database.delete(asset)
            with pytest.raises(IntegrityError):
                database.flush()
                # The savepoint context rolls back the failed flush.
        storage = AttachmentStorage(tmp_path)
        with pytest.raises(CollectionPhotoError, match="does not belong"):
            set_primary(
                database,
                storage,
                "plant",
                b.id,
                PrimaryPhotoSelection(kind="external", photo_id=link.id),
            )
        service.unlink(database, link.id)
        asset.state = "pending_delete"
        database.commit()
        with database.begin_nested():
            database.add(type(link)(media_asset=asset, plant_id=a.id))
            with pytest.raises(IntegrityError, match="unavailable"):
                database.flush()
                # The savepoint context rolls back the failed flush.


def test_gallery_and_primary_summaries_remain_batched(database_connection: Connection) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        a, b, _ = fixture(database)
        for index in range(30):
            asset = external(database)
            asset.title = f"Media {index}"
            service.create_link(
                database, "plant", a.id if index % 2 else b.id, asset.id, LinkWrite()
            )
        plant_ids = [a.id, b.id]
        statements = []

        def record(
            _connection: object,
            _cursor: object,
            statement: str,
            _parameters: object,
            _context: object,
            _executemany: bool,
        ) -> None:
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        event.listen(database_connection, "before_cursor_execute", record)
        try:
            page = service.list_assets(database, query="Media", association="linked", limit=24)
            assert len(page.items) == 24
            assert page.total == 30
            assert all(item.collection_link_count == 1 for item in page.items)
            assert len(statements) == 2
            statements.clear()
            assert primary_summaries(database, "plant", plant_ids) == {}
            assert len(statements) == 1
            statements.clear()
            choices = service.target_choices(database, "plant", "Media test species", 20, 0)
            assert choices.total == 2
            assert len(statements) == 2
        finally:
            event.remove(database_connection, "before_cursor_execute", record)


@pytest.mark.parametrize("target", ["plant", "supplier"])
def test_media_http_auth_csrf_validation_and_reference_guards(
    attachment_browser: tuple[tuple[str, str], AttachmentStorage],  # noqa: F811
    database_connection: Connection,
    target: str,
) -> None:
    from .test_attachment_api import request

    browser, _storage = attachment_browser
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        a, b, _identity = fixture(database)
        if target == "supplier":
            from florabase.suppliers.model import Supplier

            suppliers = [
                Supplier(name="HTTP supplier A", kind="nursery"),
                Supplier(name="HTTP supplier B", kind="seller"),
            ]
            database.add_all(suppliers)
            database.flush()
            plant_ids = [supplier.id for supplier in suppliers]
        else:
            plant_ids = [a.id, b.id]
        database.commit()
    payload = {
        "image_url": "https://images.example.test/image.jpg",
        "source_url": "https://example.test/source",
        "attribution": "Author",
    }
    assert request("GET", "/api/v1/media-assets").status_code == 401
    assert request("GET", f"/api/v1/media-targets/{target}").status_code == 401
    assert (
        request("POST", "/api/v1/media-assets/external", browser=browser, body=payload).status_code
        == 403
    )
    created = request(
        "POST",
        "/api/v1/media-assets/external",
        browser=browser,
        mutation_headers=True,
        body=payload,
    )
    assert created.status_code == 201
    asset_id = created.json()["id"]
    endpoint = f"/api/v1/media-assets/{asset_id}"
    assert request("GET", endpoint).status_code == 401
    assert request("GET", endpoint + "/thumbnail").status_code == 401
    assert request("GET", endpoint + "/thumbnail", browser=browser).status_code == 404
    assert (
        request("PATCH", endpoint, browser=browser, body={"attribution": "Credit"}).status_code
        == 403
    )
    assert (
        request(
            "PATCH",
            endpoint,
            browser=browser,
            mutation_headers=True,
            body={"title": "Title", "attribution": "Credit"},
        ).status_code
        == 200
    )
    links = []
    for plant_id in plant_ids:
        link_endpoint = f"/api/v1/collection-records/{target}/{plant_id}/media-links"
        value = {"media_asset_id": asset_id, "caption": "Context", "display_order": 4}
        assert request("POST", link_endpoint, browser=browser, body=value).status_code == 403
        linked = request("POST", link_endpoint, browser=browser, mutation_headers=True, body=value)
        assert linked.status_code == 201
        links.append(linked.json()["id"])
        assert (
            request(
                "POST", link_endpoint, browser=browser, mutation_headers=True, body=value
            ).status_code
            == 409
        )
    assert (
        request(
            "POST",
            f"/api/v1/collection-records/logo/{plant_ids[0]}/media-links",
            browser=browser,
            mutation_headers=True,
            body={"media_asset_id": asset_id},
        ).status_code
        == 422
    )
    assert request("DELETE", endpoint, browser=browser).status_code == 403
    blocked = request("DELETE", endpoint, browser=browser, mutation_headers=True)
    assert blocked.status_code == 409
    assert "2 record link" in blocked.json()["detail"]["message"]
    for link_id in links:
        link_endpoint = f"/api/v1/media-links/{link_id}"
        assert (
            request(
                "PATCH",
                link_endpoint,
                browser=browser,
                body={"caption": "Changed", "display_order": 1},
            ).status_code
            == 403
        )
        assert (
            request(
                "PATCH",
                link_endpoint,
                browser=browser,
                mutation_headers=True,
                body={"caption": "Changed", "display_order": 1},
            ).status_code
            == 200
        )
        assert request("DELETE", link_endpoint, browser=browser).status_code == 403
        assert (
            request("DELETE", link_endpoint, browser=browser, mutation_headers=True).status_code
            == 204
        )
    assert request("GET", endpoint, browser=browser).json()["can_delete"]
    assert request("DELETE", endpoint, browser=browser, mutation_headers=True).status_code == 204
    assert request("GET", endpoint, browser=browser).status_code == 404
