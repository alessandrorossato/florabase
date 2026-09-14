import asyncio
import hashlib
import io
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid7

import httpx
import pytest
from PIL import Image
from sqlalchemy import Connection, select
from sqlalchemy.orm import Session

from florabase.attachments.api import get_attachment_storage
from florabase.attachments.model import Attachment, AttachmentState
from florabase.attachments.storage import AttachmentStorage, AttachmentStorageError
from florabase.auth.service import bootstrap_owner
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.collection_photos.model import (
    BotanicalIdentityCoverImage,
    ExternalImageReference,
    LocalCollectionPhoto,
)
from florabase.core.config import get_settings
from florabase.db.session import get_database_session
from florabase.events.model import Event
from florabase.main import app
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing

from .test_location_api import (
    ORIGIN,
    PASSWORD,
    override_database,
    settings,
)
from .test_location_api import (
    request as json_request,
)

pytestmark = pytest.mark.integration


def png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (4, 3), (30, 120, 40)).save(output, format="PNG")
    return output.getvalue()


async def call(
    method: str,
    path: str,
    *,
    browser: tuple[str, str] | None = None,
    body: dict[str, Any] | None = None,
    file: tuple[str, bytes, str] | None = None,
    mutation_headers: bool = False,
) -> httpx.Response:
    cookies: dict[str, str] = {}
    headers: dict[str, str] = {}
    if browser is not None:
        raw_cookie, csrf = browser
        name, value = raw_cookie.split("=", 1)
        cookies[name] = value
        if mutation_headers:
            headers.update({"Origin": ORIGIN, "X-CSRF-Token": csrf})
    files: dict[str, tuple[str, bytes, str]] | None = None
    if file is not None:
        files = {"file": file}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=ORIGIN, cookies=cookies) as client:
        return await client.request(method, path, headers=headers, files=files, json=body)


def request(*args: Any, **kwargs: Any) -> httpx.Response:
    return asyncio.run(call(*args, **kwargs))


@pytest.fixture
def authenticated_browser(database_connection: Connection) -> Iterator[tuple[str, str]]:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        bootstrap_owner(database, "owner", PASSWORD, "Florabase Owner")
        database.commit()

    def database_override() -> Iterator[Session]:
        yield from override_database(database_connection)

    app.dependency_overrides[get_database_session] = database_override
    app.dependency_overrides[get_settings] = settings
    status_code, response_headers, body = json_request(
        "POST",
        "/api/v1/auth/login",
        body={"login_name": "owner", "password": PASSWORD},
        headers={"origin": ORIGIN},
    )
    assert status_code == 200
    try:
        yield response_headers["set-cookie"].split(";", 1)[0], body["csrf_token"]
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def attachment_browser(
    authenticated_browser: tuple[str, str], tmp_path: Path
) -> tuple[tuple[str, str], AttachmentStorage]:
    storage = AttachmentStorage(tmp_path)
    app.dependency_overrides[get_attachment_storage] = lambda: storage
    return authenticated_browser, storage


def test_authenticated_upload_metadata_content_and_delete(
    attachment_browser: tuple[tuple[str, str], AttachmentStorage],
    database_connection: Connection,
) -> None:
    browser, storage = attachment_browser
    content = png()
    endpoint = "/api/v1/attachments"
    assert request("POST", endpoint, file=("leaf.png", content, "image/png")).status_code == 401
    assert (
        request(
            "POST", endpoint, browser=browser, file=("leaf.png", content, "image/png")
        ).status_code
        == 403
    )

    created = request(
        "POST",
        endpoint,
        browser=browser,
        mutation_headers=True,
        file=("../../leaf photo.png", content, "image/png"),
    )
    assert created.status_code == 201
    metadata = created.json()
    assert created.headers["location"] == f"/api/v1/attachments/{metadata['id']}"
    assert metadata == {
        "id": metadata["id"],
        "original_filename": ".._.._leaf photo.png",
        "media_type": "image/png",
        "byte_size": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "state": "active",
        "created_at": metadata["created_at"],
    }
    assert "storage" not in str(metadata).lower()

    with Session(bind=database_connection) as database:
        row = database.scalar(select(Attachment).where(Attachment.id == metadata["id"]))
        assert row is not None
        assert row.id.version == 7
        assert row.storage_key.startswith("objects/")
        assert "leaf" not in row.storage_key
        stored_path = storage.active_path(row.storage_key, row.byte_size)
        assert stored_path.read_bytes() == content

    assert request("GET", f"{endpoint}/{metadata['id']}").status_code == 401
    read = request("GET", f"{endpoint}/{metadata['id']}", browser=browser)
    assert read.status_code == 200
    assert read.json() == metadata
    assert read.headers["cache-control"] == "private, no-store"
    downloaded = request("GET", f"{endpoint}/{metadata['id']}/content", browser=browser)
    assert downloaded.status_code == 200
    assert downloaded.content == content
    assert downloaded.headers["content-type"] == "image/png"
    assert downloaded.headers["cache-control"] == "private, no-store"
    assert downloaded.headers["x-content-type-options"] == "nosniff"
    assert downloaded.headers["content-disposition"].startswith("inline; filename*=UTF-8''")
    assert "/var/lib" not in str(downloaded.headers)

    assert request("DELETE", f"{endpoint}/{metadata['id']}", browser=browser).status_code == 403
    deleted = request(
        "DELETE", f"{endpoint}/{metadata['id']}", browser=browser, mutation_headers=True
    )
    assert deleted.status_code == 204
    assert request("GET", f"{endpoint}/{metadata['id']}", browser=browser).status_code == 404
    assert not stored_path.exists()


@pytest.mark.parametrize(
    ("filename", "content", "media_type", "expected_status", "code"),
    [
        ("active.svg", b"<svg/>", "image/svg+xml", 415, "unsupported_media_type"),
        ("animation.gif", b"GIF89a", "image/gif", 415, "unsupported_media_type"),
        ("photo.heic", b"ftypheic", "image/heic", 415, "unsupported_media_type"),
        ("photo.avif", b"ftypavif", "image/avif", 415, "unsupported_media_type"),
        ("empty.png", b"", "image/png", 422, "empty_attachment"),
        ("bad.png", b"\x89PNG\r\n\x1a\ntruncated", "image/png", 422, "invalid_image"),
        ("spoof.jpg", png(), "image/jpeg", 422, "media_type_mismatch"),
    ],
)
def test_upload_validation_errors_are_controlled_and_leave_no_files(
    attachment_browser: tuple[tuple[str, str], AttachmentStorage],
    filename: str,
    content: bytes,
    media_type: str,
    expected_status: int,
    code: str,
) -> None:
    browser, storage = attachment_browser
    response = request(
        "POST",
        "/api/v1/attachments",
        browser=browser,
        mutation_headers=True,
        file=(filename, content, media_type),
    )
    assert response.status_code == expected_status
    assert response.json()["detail"]["code"] == code
    assert not list(storage.temporary.iterdir())
    assert not [item for item in storage.objects.rglob("*") if item.is_file()]


def test_pending_delete_is_hidden_and_retried_after_unlink_failure(
    attachment_browser: tuple[tuple[str, str], AttachmentStorage],
    database_connection: Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    browser, storage = attachment_browser
    created = request(
        "POST",
        "/api/v1/attachments",
        browser=browser,
        mutation_headers=True,
        file=("leaf.png", png(), "image/png"),
    ).json()
    original_delete = storage.delete_file

    def fail_unlink(_: str) -> bool:
        raise AttachmentStorageError("attachment_delete_failed", "Could not remove content")

    monkeypatch.setattr(storage, "delete_file", fail_unlink)
    failed = request(
        "DELETE",
        f"/api/v1/attachments/{created['id']}",
        browser=browser,
        mutation_headers=True,
    )
    assert failed.status_code == 503
    assert (
        request("GET", f"/api/v1/attachments/{created['id']}", browser=browser).status_code == 404
    )
    assert (
        request("GET", f"/api/v1/attachments/{created['id']}/content", browser=browser).status_code
        == 404
    )
    with Session(bind=database_connection) as database:
        row = database.scalar(select(Attachment).where(Attachment.id == created["id"]))
        assert row is not None
        assert row.state == AttachmentState.PENDING_DELETE

    monkeypatch.setattr(storage, "delete_file", original_delete)
    retried = request(
        "DELETE",
        f"/api/v1/attachments/{created['id']}",
        browser=browser,
        mutation_headers=True,
    )
    assert retried.status_code == 204


def test_missing_active_file_requires_explicit_pending_retry(
    attachment_browser: tuple[tuple[str, str], AttachmentStorage],
    database_connection: Connection,
) -> None:
    browser, storage = attachment_browser
    created = request(
        "POST",
        "/api/v1/attachments",
        browser=browser,
        mutation_headers=True,
        file=("leaf.png", png(), "image/png"),
    ).json()
    with Session(bind=database_connection) as database:
        row = database.scalar(select(Attachment).where(Attachment.id == created["id"]))
        assert row is not None
        storage.active_path(row.storage_key, row.byte_size).unlink()

    content = request("GET", f"/api/v1/attachments/{created['id']}/content", browser=browser)
    assert content.status_code == 409
    assert content.json()["detail"]["code"] == "attachment_content_missing"
    first_delete = request(
        "DELETE",
        f"/api/v1/attachments/{created['id']}",
        browser=browser,
        mutation_headers=True,
    )
    assert first_delete.status_code == 409
    assert first_delete.json()["detail"]["code"] == "attachment_content_missing"
    second_delete = request(
        "DELETE",
        f"/api/v1/attachments/{created['id']}",
        browser=browser,
        mutation_headers=True,
    )
    assert second_delete.status_code == 204


def test_collection_photo_targets_external_privacy_and_owned_local_deletion(
    attachment_browser: tuple[tuple[str, str], AttachmentStorage],
    database_connection: Connection,
) -> None:
    browser, storage = attachment_browser
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        identity = BotanicalIdentity(scientific_name="Testa photographica")
        database.add(identity)
        database.flush()
        seed_lot = SeedLot(botanical_identity_id=identity.id, source_kind="unknown")
        database.add(seed_lot)
        database.flush()
        sowing = Sowing(seed_lot_id=seed_lot.id)
        plant = Plant(botanical_identity_id=identity.id, direct_origin_kind="unknown")
        group = PlantGroup(botanical_identity_id=identity.id, direct_origin_kind="unknown")
        database.add_all([sowing, plant, group])
        database.flush()
        event = Event(plant_id=plant.id, kind="observation")
        database.add(event)
        database.commit()
        targets = {
            "seed_lot": seed_lot.id,
            "sowing": sowing.id,
            "plant": plant.id,
            "plant_group": group.id,
            "event": event.id,
        }

    for target_type, target_id in targets.items():
        created = request(
            "POST",
            f"/api/v1/collection-records/{target_type}/{target_id}/photos/external",
            browser=browser,
            mutation_headers=True,
            body={
                "image_url": f"https://images.example.test/{target_type}.jpg",
                "source_url": "https://example.test/source",
                "attribution": "Example photographer",
                "caption": f"Photo for {target_type}",
            },
        )
        assert created.status_code == 201
        assert created.json()["kind"] == "external"

    target_id = targets["event"]
    local = request(
        "POST",
        f"/api/v1/collection-records/event/{target_id}/photos/local",
        browser=browser,
        mutation_headers=True,
        file=("evidence.png", png(), "image/png"),
    )
    assert local.status_code == 201
    local_body = local.json()
    assert local_body["kind"] == "local"
    assert local_body["content_url"].endswith(f"/{local_body['attachment_id']}/content")
    listed = request("GET", f"/api/v1/collection-records/event/{target_id}/photos", browser=browser)
    assert listed.status_code == 200
    assert [item["kind"] for item in listed.json()] == ["external", "local"]
    assert "storage" not in str(listed.json()).lower()

    direct_delete = request(
        "DELETE",
        f"/api/v1/attachments/{local_body['attachment_id']}",
        browser=browser,
        mutation_headers=True,
    )
    assert direct_delete.status_code == 409
    assert direct_delete.json()["detail"]["code"] == "attachment_owned_by_photo"

    event_delete = request(
        "DELETE", f"/api/v1/events/{target_id}", browser=browser, mutation_headers=True
    )
    assert event_delete.status_code == 409
    assert event_delete.json()["detail"]["code"] == "event_has_photos"

    removed_local = request(
        "DELETE",
        f"/api/v1/collection-photos/local/{local_body['id']}",
        browser=browser,
        mutation_headers=True,
    )
    assert removed_local.status_code == 204
    with Session(bind=database_connection) as database:
        assert database.get(LocalCollectionPhoto, local_body["id"]) is None
        assert not [path for path in storage.objects.rglob("*") if path.is_file()]

    external_id = listed.json()[0]["id"]
    assert (
        request(
            "DELETE",
            f"/api/v1/collection-photos/external/{external_id}",
            browser=browser,
            mutation_headers=True,
        ).status_code
        == 204
    )
    assert (
        request(
            "DELETE", f"/api/v1/events/{target_id}", browser=browser, mutation_headers=True
        ).status_code
        == 204
    )


def test_external_image_validation_never_contacts_remote_hosts(
    attachment_browser: tuple[tuple[str, str], AttachmentStorage],
    database_connection: Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    browser, storage = attachment_browser
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        identity = BotanicalIdentity(scientific_name="Testa externa")
        database.add(identity)
        database.flush()
        plant = Plant(botanical_identity_id=identity.id, direct_origin_kind="unknown")
        database.add(plant)
        database.commit()
        plant_id = plant.id

    endpoint = f"/api/v1/collection-records/plant/{plant_id}/photos"
    assert request("GET", endpoint).status_code == 401
    assert (
        request(
            "POST",
            f"{endpoint}/external",
            browser=browser,
            body={
                "image_url": "https://example.test/image.jpg",
                "source_url": "https://example.test/source",
                "attribution": "Author",
            },
        ).status_code
        == 403
    )
    missing_target = request(
        "POST",
        f"/api/v1/collection-records/plant/{uuid7()}/photos/local",
        browser=browser,
        mutation_headers=True,
        file=("leaf.png", png(), "image/png"),
    )
    assert missing_target.status_code == 404
    assert not [path for path in storage.objects.rglob("*") if path.is_file()]

    network = MagicMock(side_effect=AssertionError("backend network access is forbidden"))
    monkeypatch.setattr(httpx, "get", network)
    for image_url in ("http://example.test/image.jpg", "not-a-url"):
        result = request(
            "POST",
            f"/api/v1/collection-records/plant/{plant_id}/photos/external",
            browser=browser,
            mutation_headers=True,
            body={
                "image_url": image_url,
                "source_url": "https://example.test/source",
                "attribution": "Author",
            },
        )
        assert result.status_code == 422
    missing_attribution = request(
        "POST",
        f"/api/v1/collection-records/plant/{plant_id}/photos/external",
        browser=browser,
        mutation_headers=True,
        body={
            "image_url": "https://example.test/image.jpg",
            "source_url": "https://example.test/source",
            "attribution": " ",
        },
    )
    assert missing_attribution.status_code == 422
    network.assert_not_called()
    with Session(bind=database_connection) as database:
        assert database.query(ExternalImageReference).count() == 0


def test_local_photo_unlink_failure_is_hidden_and_retried_through_photo_route(
    attachment_browser: tuple[tuple[str, str], AttachmentStorage],
    database_connection: Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    browser, storage = attachment_browser
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        identity = BotanicalIdentity(scientific_name="Testa deletionis")
        database.add(identity)
        database.flush()
        plant = Plant(
            botanical_identity_id=identity.id,
            direct_origin_kind="unknown",
            lifecycle="dead",
        )
        database.add(plant)
        database.commit()
        plant_id = plant.id

    created = request(
        "POST",
        f"/api/v1/collection-records/plant/{plant_id}/photos/local",
        browser=browser,
        mutation_headers=True,
        file=("history.png", png(), "image/png"),
    ).json()
    original_delete = storage.delete_file

    def fail_unlink(_: str) -> bool:
        raise AttachmentStorageError("attachment_delete_failed", "Could not remove content")

    monkeypatch.setattr(storage, "delete_file", fail_unlink)
    failed = request(
        "DELETE",
        f"/api/v1/collection-photos/local/{created['id']}",
        browser=browser,
        mutation_headers=True,
    )
    assert failed.status_code == 503
    listed = request(
        "GET", f"/api/v1/collection-records/plant/{plant_id}/photos", browser=browser
    ).json()
    assert listed[0]["deletion_pending"] is True
    assert listed[0]["content_url"] is None
    assert (
        request(
            "GET", f"/api/v1/attachments/{created['attachment_id']}/content", browser=browser
        ).status_code
        == 404
    )

    monkeypatch.setattr(storage, "delete_file", original_delete)
    retried = request(
        "DELETE",
        f"/api/v1/collection-photos/local/{created['id']}",
        browser=browser,
        mutation_headers=True,
    )
    assert retried.status_code == 204
    assert (
        request(
            "GET", f"/api/v1/collection-records/plant/{plant_id}/photos", browser=browser
        ).json()
        == []
    )

    missing_file = request(
        "POST",
        f"/api/v1/collection-records/plant/{plant_id}/photos/local",
        browser=browser,
        mutation_headers=True,
        file=("missing.png", png(), "image/png"),
    ).json()
    stored_files = [path for path in storage.objects.rglob("*") if path.is_file()]
    assert len(stored_files) == 1
    stored_files[0].unlink()
    first_missing_delete = request(
        "DELETE",
        f"/api/v1/collection-photos/local/{missing_file['id']}",
        browser=browser,
        mutation_headers=True,
    )
    assert first_missing_delete.status_code == 409
    assert first_missing_delete.json()["detail"]["code"] == "attachment_content_missing"
    pending = request(
        "GET", f"/api/v1/collection-records/plant/{plant_id}/photos", browser=browser
    ).json()
    assert pending[0]["deletion_pending"] is True
    assert (
        request(
            "DELETE",
            f"/api/v1/collection-photos/local/{missing_file['id']}",
            browser=browser,
            mutation_headers=True,
        ).status_code
        == 204
    )


def test_external_identity_cover_is_explicit_private_metadata_and_guards_identity_delete(
    attachment_browser: tuple[tuple[str, str], AttachmentStorage],
    database_connection: Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    browser, _storage = attachment_browser
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        identity = BotanicalIdentity(scientific_name="Testa cover externa")
        database.add(identity)
        database.commit()
        identity_id = identity.id
    endpoint = f"/api/v1/botanical-identities/{identity_id}/cover-image"
    assert request("GET", endpoint).status_code == 401
    assert request("GET", endpoint, browser=browser).json() is None

    payload = {
        "image_url": "https://images.example.test/cover.jpg",
        "source_url": "https://example.test/cover-page",
        "attribution": "Example photographer",
        "licence_label": None,
        "licence_url": None,
        "privacy_acknowledged": True,
    }
    assert request("PUT", f"{endpoint}/external", browser=browser, body=payload).status_code == 403
    for invalid in (
        {**payload, "privacy_acknowledged": False},
        {**payload, "image_url": "http://example.test/cover.jpg"},
        {**payload, "image_url": "https://127.0.0.1/cover.jpg"},
        {**payload, "source_url": "https://photos.internal/cover"},
        {**payload, "source_url": "javascript:alert(1)"},
        {**payload, "attribution": " "},
        {**payload, "licence_url": "http://example.test/licence"},
    ):
        assert (
            request(
                "PUT",
                f"{endpoint}/external",
                browser=browser,
                mutation_headers=True,
                body=invalid,
            ).status_code
            == 422
        )

    network = MagicMock(side_effect=AssertionError("backend external fetch is forbidden"))
    monkeypatch.setattr(httpx, "get", network)
    created = request(
        "PUT",
        f"{endpoint}/external",
        browser=browser,
        mutation_headers=True,
        body=payload,
    )
    assert created.status_code == 200
    first = created.json()
    assert first["kind"] == "external"
    assert first["licence_label"] is None
    assert "storage" not in str(first).lower()

    updated = request(
        "PUT",
        f"{endpoint}/external",
        browser=browser,
        mutation_headers=True,
        body={
            **payload,
            "image_url": "https://images.example.test/new-cover.jpg",
            "attribution": "Updated credit",
            "licence_label": "CC BY 4.0",
            "licence_url": "https://creativecommons.org/licenses/by/4.0/",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["id"] == first["id"]
    assert updated.json()["licence_label"] == "CC BY 4.0"
    assert request("GET", endpoint, browser=browser).json()["attribution"] == "Updated credit"

    blocked = request(
        "DELETE",
        f"/api/v1/botanical-identities/{identity_id}",
        browser=browser,
        mutation_headers=True,
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "botanical_identity_has_cover"
    assert request("DELETE", endpoint, browser=browser, mutation_headers=True).status_code == 204
    assert request("GET", endpoint, browser=browser).json() is None
    assert (
        request(
            "DELETE",
            f"/api/v1/botanical-identities/{identity_id}",
            browser=browser,
            mutation_headers=True,
        ).status_code
        == 204
    )
    network.assert_not_called()


def test_identity_cover_replaces_every_source_mode_and_owns_local_binary(
    attachment_browser: tuple[tuple[str, str], AttachmentStorage],
    database_connection: Connection,
) -> None:
    browser, storage = attachment_browser
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        identity = BotanicalIdentity(scientific_name="Testa cover replacement")
        database.add(identity)
        database.commit()
        identity_id = identity.id
    endpoint = f"/api/v1/botanical-identities/{identity_id}/cover-image"

    first_local = request(
        "POST",
        f"{endpoint}/local",
        browser=browser,
        mutation_headers=True,
        file=("first.png", png(), "image/png"),
    )
    assert first_local.status_code == 201
    first = first_local.json()
    assert first["kind"] == "local"
    assert first["content_url"].endswith(f"/{first['attachment_id']}/content")
    protected = request(
        "DELETE",
        f"/api/v1/attachments/{first['attachment_id']}",
        browser=browser,
        mutation_headers=True,
    )
    assert protected.status_code == 409
    assert protected.json()["detail"]["code"] == "attachment_owned_by_identity_cover"

    second = request(
        "POST",
        f"{endpoint}/local",
        browser=browser,
        mutation_headers=True,
        file=("second.png", png(), "image/png"),
    ).json()
    assert second["id"] == first["id"]
    assert second["attachment_id"] != first["attachment_id"]
    with Session(bind=database_connection) as database:
        assert database.get(Attachment, first["attachment_id"]) is None
    assert len([path for path in storage.objects.rglob("*") if path.is_file()]) == 1

    external_payload = {
        "image_url": "https://images.example.test/external.jpg",
        "source_url": "https://example.test/source",
        "attribution": "External author",
        "licence_label": None,
        "licence_url": None,
        "privacy_acknowledged": True,
    }
    external = request(
        "PUT",
        f"{endpoint}/external",
        browser=browser,
        mutation_headers=True,
        body=external_payload,
    ).json()
    assert external["id"] == first["id"]
    assert external["kind"] == "external"
    with Session(bind=database_connection) as database:
        assert database.get(Attachment, second["attachment_id"]) is None
        cover = database.get(BotanicalIdentityCoverImage, external["id"])
        assert cover is not None
        assert cover.attachment_id is None
    assert not [path for path in storage.objects.rglob("*") if path.is_file()]

    final_local = request(
        "POST",
        f"{endpoint}/local",
        browser=browser,
        mutation_headers=True,
        file=("final.png", png(), "image/png"),
    ).json()
    assert final_local["id"] == first["id"]
    assert final_local["kind"] == "local"
    assert request("DELETE", endpoint, browser=browser, mutation_headers=True).status_code == 204
    with Session(bind=database_connection) as database:
        assert database.get(Attachment, final_local["attachment_id"]) is None
        assert database.get(BotanicalIdentityCoverImage, first["id"]) is None
    assert not [path for path in storage.objects.rglob("*") if path.is_file()]


def test_local_identity_cover_unlink_failure_and_missing_file_remain_retryable(
    attachment_browser: tuple[tuple[str, str], AttachmentStorage],
    database_connection: Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    browser, storage = attachment_browser
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        identity = BotanicalIdentity(scientific_name="Testa cover retry")
        database.add(identity)
        database.commit()
        identity_id = identity.id
    endpoint = f"/api/v1/botanical-identities/{identity_id}/cover-image"
    created_response = request(
        "POST",
        f"{endpoint}/local",
        browser=browser,
        mutation_headers=True,
        file=("retry.png", png(), "image/png"),
    )
    assert created_response.status_code == 201
    original_delete = storage.delete_file

    def fail_unlink(_: str) -> bool:
        raise AttachmentStorageError("attachment_delete_failed", "Could not remove content")

    monkeypatch.setattr(storage, "delete_file", fail_unlink)
    failed = request("DELETE", endpoint, browser=browser, mutation_headers=True)
    assert failed.status_code == 503
    pending = request("GET", endpoint, browser=browser).json()
    assert pending["kind"] == "local"
    assert pending["deletion_pending"] is True
    assert pending["content_url"] is None

    monkeypatch.setattr(storage, "delete_file", original_delete)
    assert request("DELETE", endpoint, browser=browser, mutation_headers=True).status_code == 204

    missing = request(
        "POST",
        f"{endpoint}/local",
        browser=browser,
        mutation_headers=True,
        file=("missing.png", png(), "image/png"),
    ).json()
    with Session(bind=database_connection) as database:
        row = database.get(Attachment, missing["attachment_id"])
        assert row is not None
        storage.active_path(row.storage_key, row.byte_size).unlink()
    first_delete = request("DELETE", endpoint, browser=browser, mutation_headers=True)
    assert first_delete.status_code == 409
    assert first_delete.json()["detail"]["code"] == "attachment_content_missing"
    assert request("DELETE", endpoint, browser=browser, mutation_headers=True).status_code == 204
