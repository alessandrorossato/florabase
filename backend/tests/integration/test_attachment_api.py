import asyncio
import hashlib
import io
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from PIL import Image
from sqlalchemy import Connection, select
from sqlalchemy.orm import Session

from florabase.attachments.api import get_attachment_storage
from florabase.attachments.model import Attachment, AttachmentState
from florabase.attachments.storage import AttachmentStorage, AttachmentStorageError
from florabase.auth.service import bootstrap_owner
from florabase.core.config import get_settings
from florabase.db.session import get_database_session
from florabase.main import app

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
        return await client.request(method, path, headers=headers, files=files)


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
