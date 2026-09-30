from uuid import uuid7

import pytest
from sqlalchemy import Connection, text

from florabase.attachments.storage import AttachmentStorage, AttachmentStorageError

from .test_attachment_api import attachment_browser as photo_browser  # noqa: F401
from .test_attachment_api import (
    authenticated_browser,  # noqa: F401
    png,
    request,
)

pytestmark = pytest.mark.integration


def _plant(connection: Connection) -> str:
    identity_id, plant_id = uuid7(), uuid7()
    connection.execute(
        text(
            "INSERT INTO botanical_identities (id, scientific_name, created_at, updated_at) "
            "VALUES (:id, :name, now(), now())"
        ),
        {"id": identity_id, "name": f"Primary test {identity_id}"},
    )
    connection.execute(
        text(
            "INSERT INTO plants (id, botanical_identity_id, direct_origin_kind, lifecycle, "
            "created_at, updated_at) VALUES (:id, :identity, 'unknown', 'active', now(), now())"
        ),
        {"id": plant_id, "identity": identity_id},
    )
    return str(plant_id)


def test_explicit_primary_photo_lifecycle_and_thumbnail(
    photo_browser: tuple[tuple[str, str], AttachmentStorage],  # noqa: F811
    database_connection: Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    browser, storage = photo_browser
    plant_id = _plant(database_connection)
    other_id = _plant(database_connection)
    base = f"/api/v1/collection-records/plant/{plant_id}"
    other = f"/api/v1/collection-records/plant/{other_id}"
    assert request("GET", f"{base}/primary-photo", browser=browser).json() is None

    local = request(
        "POST",
        f"{base}/photos/local",
        browser=browser,
        mutation_headers=True,
        file=("leaf.png", png(), "image/png"),
    )
    assert local.status_code == 201
    local_id = local.json()["id"]
    assert request("GET", f"{base}/primary-photo", browser=browser).json() is None
    assert (
        request(
            "PUT",
            f"{other}/primary-photo",
            browser=browser,
            mutation_headers=True,
            body={"kind": "local", "photo_id": local_id},
        ).json()["detail"]["code"]
        == "primary_photo_wrong_target"
    )
    # A cross-table mismatch introduced outside the service must fail closed on reads.
    corrupt_id = uuid7()
    database_connection.execute(
        text(
            "INSERT INTO collection_primary_photos "
            "(id, plant_id, local_collection_photo_id, created_at, updated_at) "
            "VALUES (:id, :plant, :photo, now(), now())"
        ),
        {"id": corrupt_id, "plant": other_id, "photo": local_id},
    )
    assert request("GET", f"{other}/primary-photo", browser=browser).json() is None
    database_connection.execute(
        text("DELETE FROM collection_primary_photos WHERE id = :id"), {"id": corrupt_id}
    )
    selected = request(
        "PUT",
        f"{base}/primary-photo",
        browser=browser,
        mutation_headers=True,
        body={"kind": "local", "photo_id": local_id},
    )
    assert selected.status_code == 200
    assert selected.json()["thumbnail_url"].endswith(f"/{local_id}/thumbnail")
    thumb = request("GET", selected.json()["thumbnail_url"], browser=browser)
    assert thumb.status_code == 200
    assert thumb.headers["content-type"] == "image/webp"
    assert thumb.headers["cache-control"].startswith("private")
    assert request("GET", selected.json()["thumbnail_url"]).status_code == 401

    external = request(
        "POST",
        f"{base}/photos/external",
        browser=browser,
        mutation_headers=True,
        body={
            "image_url": "https://images.example.test/leaf.jpg",
            "source_url": "https://example.test/leaf",
            "attribution": "Author",
        },
    )
    assert external.status_code == 201
    external_id = external.json()["id"]
    assert request("GET", f"{base}/primary-photo", browser=browser).json()["kind"] == "local"
    switched = request(
        "PUT",
        f"{base}/primary-photo",
        browser=browser,
        mutation_headers=True,
        body={"kind": "external", "photo_id": external_id},
    )
    assert switched.json() == {
        "kind": "external",
        "photo_id": external_id,
        "thumbnail_url": None,
    }
    assert len(request("GET", f"{base}/photos", browser=browser).json()) == 2
    assert (
        request(
            "DELETE",
            f"/api/v1/collection-photos/external/{external_id}",
            browser=browser,
            mutation_headers=True,
        ).status_code
        == 204
    )
    assert request("GET", f"{base}/primary-photo", browser=browser).json() is None
    assert (
        request(
            "PUT",
            f"{base}/primary-photo",
            browser=browser,
            mutation_headers=True,
            body={"kind": "local", "photo_id": local_id},
        ).status_code
        == 200
    )
    assert (
        request(
            "DELETE",
            f"{base}/primary-photo",
            browser=browser,
            mutation_headers=True,
        ).status_code
        == 204
    )
    assert len(request("GET", f"{base}/photos", browser=browser).json()) == 1
    assert (
        request(
            "PUT",
            f"{base}/primary-photo",
            browser=browser,
            mutation_headers=True,
            body={"kind": "local", "photo_id": local_id},
        ).status_code
        == 200
    )
    delete_file = storage.delete_file

    def failed_unlink(_key: str) -> bool:
        raise AttachmentStorageError("attachment_delete_failed", "Could not remove photo content")

    monkeypatch.setattr(storage, "delete_file", failed_unlink)
    assert (
        request(
            "DELETE",
            f"/api/v1/collection-photos/local/{local_id}",
            browser=browser,
            mutation_headers=True,
        ).status_code
        == 503
    )
    assert request("GET", f"{base}/primary-photo", browser=browser).json() is None
    assert request("GET", f"{base}/photos", browser=browser).json()[0]["deletion_pending"]
    monkeypatch.setattr(storage, "delete_file", delete_file)
    assert (
        request(
            "DELETE",
            f"/api/v1/collection-photos/local/{local_id}",
            browser=browser,
            mutation_headers=True,
        ).status_code
        == 204
    )
    assert request("GET", f"{base}/photos", browser=browser).json() == []
    for unsupported in ("sowing", "event", "botanical_identity"):
        assert (
            request(
                "PUT",
                f"/api/v1/collection-records/{unsupported}/{plant_id}/primary-photo",
                browser=browser,
                mutation_headers=True,
                body={"kind": "local", "photo_id": local_id},
            ).status_code
            == 422
        )


def test_dashboard_events_show_only_the_exact_targets_designated_photo(
    photo_browser: tuple[tuple[str, str], AttachmentStorage],  # noqa: F811
    database_connection: Connection,
) -> None:
    browser, _ = photo_browser
    plant_id = _plant(database_connection)
    other_id = _plant(database_connection)
    for target_id in (plant_id, other_id):
        assert (
            request(
                "POST",
                f"/api/v1/plants/{target_id}/events",
                browser=browser,
                mutation_headers=True,
                body={"kind": "observation"},
            ).status_code
            == 201
        )
    base = f"/api/v1/collection-records/plant/{plant_id}"
    photo = request(
        "POST",
        f"{base}/photos/local",
        browser=browser,
        mutation_headers=True,
        file=("leaf.png", png(), "image/png"),
    ).json()

    def targets() -> dict[str, object]:
        dashboard = request("GET", "/api/v1/dashboard", browser=browser)
        assert dashboard.status_code == 200
        return {
            event["target"]["id"]: event["target"]["primary_photo"]
            for event in dashboard.json()["recent_events"]
        }

    assert targets() == {plant_id: None, other_id: None}
    selected = request(
        "PUT",
        f"{base}/primary-photo",
        browser=browser,
        mutation_headers=True,
        body={"kind": "local", "photo_id": photo["id"]},
    )
    assert selected.status_code == 200
    assert targets() == {plant_id: selected.json(), other_id: None}
    thumbnail = request("GET", selected.json()["thumbnail_url"], browser=browser)
    assert thumbnail.status_code == 200
    assert request("GET", selected.json()["thumbnail_url"]).status_code == 401
    assert (
        request(
            "DELETE", f"{base}/primary-photo", browser=browser, mutation_headers=True
        ).status_code
        == 204
    )
    assert targets() == {plant_id: None, other_id: None}
