from collections.abc import Iterator

import pytest
from sqlalchemy import Connection
from sqlalchemy.orm import Session

from florabase.auth.service import bootstrap_owner
from florabase.core.config import get_settings
from florabase.db.session import get_database_session
from florabase.main import app

from .test_location_api import PASSWORD, mutate, override_database, request, settings

pytestmark = pytest.mark.integration


@pytest.fixture
def authenticated_browser(database_connection: Connection) -> Iterator[tuple[str, str]]:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        bootstrap_owner(database, "owner", PASSWORD, "Florabase Owner")
        database.commit()

    def database_override() -> Iterator[Session]:
        yield from override_database(database_connection)

    app.dependency_overrides[get_database_session] = database_override
    app.dependency_overrides[get_settings] = settings
    status_code, response_headers, body = request(
        "POST",
        "/api/v1/auth/login",
        body={"login_name": "owner", "password": PASSWORD},
        headers={"origin": "https://florabase.example"},
    )
    assert status_code == 200
    try:
        yield response_headers["set-cookie"].split(";", 1)[0], body["csrf_token"]
    finally:
        app.dependency_overrides.clear()


def _canonical(browser: tuple[str, str], code: str) -> dict[str, object]:
    cookie, _ = browser
    status, _, places = request("GET", "/api/v1/geographic-places", headers={"cookie": cookie})
    assert status == 200
    return next(place for place in places if place["source_code"] == code)


def test_directory_selection_custom_depth_rename_reparent_and_lifecycle(
    authenticated_browser: tuple[str, str], database_connection: Connection
) -> None:
    cookie, _ = authenticated_browser
    first_status, _, first = request("GET", "/api/v1/geographic-places", headers={"cookie": cookie})
    second_status, _, second = request(
        "GET", "/api/v1/geographic-places", headers={"cookie": cookie}
    )
    assert first_status == second_status == 200
    assert first == second
    paths = {place["source_code"]: place["display_path"] for place in first}
    assert paths["005"].endswith("South America")
    assert paths["BR"] == paths["005"] + " → Brazil"
    assert paths["TH"] == "World → Asia → Southeast Asia → Thailand"

    thailand = next(place for place in first if place["source_code"] == "TH")
    status, headers, chiang_mai = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/geographic-places",
        {"name": "Chiang Mai", "parent_id": thailand["id"]},
    )
    assert status == 201
    assert headers["location"].endswith(chiang_mai["id"])
    assert chiang_mai["place_kind"] == "custom"
    assert chiang_mai["source_code"] is None

    _, _, doi_suthep = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/geographic-places",
        {"name": "Doi Suthep", "parent_id": chiang_mai["id"]},
    )
    assert doi_suthep["display_path"].endswith("Thailand → Chiang Mai → Doi Suthep")

    brazil = next(place for place in first if place["source_code"] == "BR")
    status, _, moved = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/geographic-places/{chiang_mai['id']}",
        {"name": "Chiang Mai Province", "parent_id": brazil["id"]},
    )
    assert status == 200
    assert moved["display_path"].endswith("Brazil → Chiang Mai Province")

    cycle_status, _, cycle = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/geographic-places/{chiang_mai['id']}",
        {"name": "Chiang Mai", "parent_id": doi_suthep["id"]},
    )
    assert cycle_status == 409
    assert cycle["detail"]["code"] == "geographic_place_cycle"

    assert (
        mutate(
            authenticated_browser,
            "POST",
            f"/api/v1/geographic-places/{doi_suthep['id']}/retire",
        )[0]
        == 200
    )
    retired_status, _, retired = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/geographic-places/{chiang_mai['id']}/retire",
    )
    assert retired_status == 200
    assert retired["retired_at"] is not None
    assert (
        mutate(
            authenticated_browser,
            "POST",
            f"/api/v1/geographic-places/{chiang_mai['id']}/reactivate",
        )[0]
        == 200
    )


def test_canonical_mutations_and_security_boundaries(
    authenticated_browser: tuple[str, str],
) -> None:
    thailand = _canonical(authenticated_browser, "TH")
    asia = _canonical(authenticated_browser, "142")
    for method, path, payload in (
        (
            "PUT",
            f"/api/v1/geographic-places/{thailand['id']}",
            {"name": "Renamed", "parent_id": asia["id"]},
        ),
        ("POST", f"/api/v1/geographic-places/{thailand['id']}/retire", None),
        ("POST", f"/api/v1/geographic-places/{thailand['id']}/reactivate", None),
    ):
        status, _, body = mutate(authenticated_browser, method, path, payload)
        assert status == 409
        assert body["detail"]["code"] == "canonical_geographic_place_immutable"

    assert request("GET", "/api/v1/geographic-places")[0] == 401
    cookie, csrf = authenticated_browser
    payload = {"name": "Local", "parent_id": thailand["id"]}
    for headers in (
        {"origin": "https://florabase.example", "x-csrf-token": csrf},
        {"cookie": cookie, "origin": "https://florabase.example"},
        {"cookie": cookie, "x-csrf-token": csrf},
        {
            "cookie": cookie,
            "origin": "https://evil.example",
            "x-csrf-token": csrf,
        },
    ):
        assert request("POST", "/api/v1/geographic-places", body=payload, headers=headers)[0] in {
            401,
            403,
        }
