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


def test_provenance_site_crud_coordinates_and_place_usage(
    authenticated_browser: tuple[str, str],
) -> None:
    cookie, _ = authenticated_browser
    _, _, places = request("GET", "/api/v1/geographic-places", headers={"cookie": cookie})
    thailand = next(place for place in places if place["source_code"] == "TH")
    status, _, site = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/provenance-sites",
        {
            "name": "Doi Suthep collection ridge",
            "geographic_place_id": thailand["id"],
            "latitude": "18.804900",
            "longitude": "98.921600",
            "coordinate_accuracy_m": "12.5",
            "notes": "Historical label retained",
        },
    )
    assert status == 201
    assert site["geographic_place_path"].endswith("Thailand")
    assert site["latitude"] == "18.804900"
    assert site["usage"] == {"seed_lots": 0, "plants": 0, "plant_groups": 0}

    status, _, updated = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/provenance-sites/{site['id']}",
        {"name": "Doi Suthep", "geographic_place_id": None},
    )
    assert status == 200
    assert updated["latitude"] is None
    assert updated["geographic_place_path"] is None
    assert (
        mutate(authenticated_browser, "DELETE", f"/api/v1/provenance-sites/{site['id']}")[0] == 204
    )


def test_provenance_site_validation_and_parent_delete_conflict(
    authenticated_browser: tuple[str, str], database_connection: Connection
) -> None:
    del database_connection
    for payload in (
        {"name": "Half", "latitude": 1},
        {"name": "Latitude", "latitude": 91, "longitude": 0},
        {"name": "Longitude", "latitude": 0, "longitude": 181},
        {"name": "Accuracy", "coordinate_accuracy_m": -1},
    ):
        assert mutate(authenticated_browser, "POST", "/api/v1/provenance-sites", payload)[0] == 422

    cookie, _ = authenticated_browser
    _, _, places = request("GET", "/api/v1/geographic-places", headers={"cookie": cookie})
    world = next(place for place in places if place["parent_id"] is None)
    _, _, local = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/geographic-places",
        {"name": "Locality", "parent_id": world["id"], "place_type": "locality"},
    )
    _, _, site = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/provenance-sites",
        {
            "name": "Known origin",
            "geographic_place_id": local["id"],
            "latitude": 10,
            "longitude": 20,
        },
    )
    thailand = next(place for place in places if place["source_code"] == "TH")
    assert (
        mutate(
            authenticated_browser,
            "PUT",
            f"/api/v1/geographic-places/{local['id']}",
            {"name": "Locality", "parent_id": thailand["id"], "place_type": "locality"},
        )[0]
        == 200
    )
    _, _, sites = request("GET", "/api/v1/provenance-sites", headers={"cookie": cookie})
    moved_site = next(item for item in sites if item["id"] == site["id"])
    assert moved_site["latitude"] == "10.000000"
    assert moved_site["longitude"] == "20.000000"
    assert moved_site["geographic_place_path"].endswith("Thailand → Locality")
    status, _, conflict = mutate(
        authenticated_browser, "DELETE", f"/api/v1/geographic-places/{local['id']}"
    )
    assert status == 409
    assert conflict["detail"]["code"] == "geographic_place_has_provenance_sites"


def test_referenced_provenance_site_cannot_be_deleted(
    authenticated_browser: tuple[str, str],
) -> None:
    _, _, site = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/provenance-sites",
        {"name": "Retained origin"},
    )
    _, _, identity = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/botanical-identities",
        {"scientific_name": "Testa geographica"},
    )
    status, _, lot = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/seed-lots",
        {
            "botanical_identity_id": identity["id"],
            "source_kind": "self_collected",
            "provenance_site_id": site["id"],
        },
    )
    assert status == 201
    assert lot["provenance_site"]["name"] == "Retained origin"
    status, _, conflict = mutate(
        authenticated_browser, "DELETE", f"/api/v1/provenance-sites/{site['id']}"
    )
    assert status == 409
    assert conflict["detail"]["code"] == "provenance_site_in_use"


def test_collection_provenance_map_dataset_and_direct_origin_semantics(
    authenticated_browser: tuple[str, str],
) -> None:
    cookie, _ = authenticated_browser
    assert request("GET", "/api/v1/provenance-sites/map")[0] == 401
    _, _, places = request("GET", "/api/v1/geographic-places", headers={"cookie": cookie})
    thailand = next(place for place in places if place["source_code"] == "TH")
    _, _, coordinate_less = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/provenance-sites",
        {"name": "Recorded without coordinates"},
    )
    _, _, site = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/provenance-sites",
        {
            "name": "Doi Suthep ridge",
            "geographic_place_id": thailand["id"],
            "latitude": "18.804900",
            "longitude": "-98.921600",
            "coordinate_accuracy_m": "25.500",
        },
    )
    _, _, _edge_site = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/provenance-sites",
        {"name": "Antimeridian edge", "latitude": 90, "longitude": -180},
    )
    _, _, identity = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/botanical-identities",
        {"scientific_name": "Clitoria ternatea", "cultivar_name": "Map blue"},
    )
    _, _, lot = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/seed-lots",
        {
            "botanical_identity_id": identity["id"],
            "label": "Chiang Mai seeds",
            "source_kind": "self_collected",
            "provenance_site_id": site["id"],
            "lifecycle": "discarded",
        },
    )
    _, _, plant = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/plants",
        {
            "botanical_identity_id": identity["id"],
            "label": "Direct plant",
            "direct_origin_kind": "gift_exchange",
            "provenance_site_id": site["id"],
            "lifecycle": "transferred",
        },
    )
    _, _, group = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/plant-groups",
        {
            "botanical_identity_id": identity["id"],
            "label": "Direct group",
            "direct_origin_kind": "purchased",
            "provenance_site_id": site["id"],
        },
    )
    _, _, extraction = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/plant-groups/{group['id']}/extract-plant",
        {},
    )
    extracted = extraction["plant"]
    _, _, sowing = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/sowings",
        {"seed_lot_id": lot["id"], "label": "Derived sowing"},
    )
    _, _, propagated = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/plants",
        {"botanical_identity_id": identity["id"], "originating_sowing_id": sowing["id"]},
    )

    status, _, dataset = request("GET", "/api/v1/provenance-sites/map", headers={"cookie": cookie})
    assert status == 200
    assert dataset["total_provenance_sites"] == 3
    assert dataset["coordinate_less_sites"] == 1
    assert [item["name"] for item in dataset["sites"]] == [
        "Antimeridian edge",
        "Doi Suthep ridge",
    ]
    mapped = dataset["sites"][1]
    assert mapped["id"] == site["id"]
    assert mapped["latitude"] == "18.804900"
    assert mapped["longitude"] == "-98.921600"
    assert mapped["coordinate_accuracy_m"] == "25.500"
    assert mapped["geographic_place_path"].endswith("Thailand")
    assert mapped["usage"] == {"seed_lots": 1, "plants": 1, "plant_groups": 1, "total": 3}
    assert [(record["record_type"], record["id"]) for record in mapped["records"]] == [
        ("seed_lot", lot["id"]),
        ("plant", plant["id"]),
        ("plant_group", group["id"]),
    ]
    assert all(
        record["botanical_identity"]["display_label"] == "Clitoria ternatea \u2018Map blue\u2019"
        for record in mapped["records"]
    )
    assert [record["lifecycle"] for record in mapped["records"]] == [
        "discarded",
        "transferred",
        "active",
    ]
    assert [record["is_active"] for record in mapped["records"]] == [False, False, True]
    assert propagated["id"] not in {record["id"] for record in mapped["records"]}
    assert extracted["id"] not in {record["id"] for record in mapped["records"]}
    assert coordinate_less["id"] not in {item["id"] for item in dataset["sites"]}
    assert dataset["sites"][0]["latitude"] == "90.000000"
    assert dataset["sites"][0]["longitude"] == "-180.000000"
