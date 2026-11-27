"""QUICK-ADD-001: identity, optional WFO link and Plant/PlantGroup in one transaction."""

from pathlib import Path
from typing import Any
from uuid import uuid7

import pytest
from sqlalchemy import Connection, func, select
from sqlalchemy.orm import Session
from test_taxonomy import META, SPECIES, SYNONYM, data

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.main import app
from florabase.plants.model import Plant, PlantGroup
from florabase.taxonomy.api import source_dependency
from florabase.taxonomy.model import WfoLink
from florabase.taxonomy.snapshot import build_index
from florabase.taxonomy.source import WfoSource

from .test_supplier_api import ORIGIN, request
from .test_supplier_api import authenticated_browser as authenticated_browser

pytestmark = pytest.mark.integration
URL = "/api/v1/quick-add/plant"


@pytest.fixture
def source(tmp_path: Path) -> Any:
    destination = tmp_path / "wfo.sqlite"
    build_index(destination, *data(), META)
    app.dependency_overrides[source_dependency] = lambda: WfoSource(destination)
    yield
    app.dependency_overrides.pop(source_dependency, None)


def post(browser: tuple[str, str], body: dict[str, Any]) -> tuple[int, dict[str, str], Any]:
    cookie, csrf = browser
    return request(
        "POST", URL, body=body, headers={"cookie": cookie, "origin": ORIGIN, "x-csrf-token": csrf}
    )


def counts(connection: Connection) -> tuple[int, int, int, int]:
    with Session(bind=connection) as db:
        return tuple(  # type: ignore[return-value]
            db.scalar(select(func.count()).select_from(model)) or 0
            for model in (BotanicalIdentity, WfoLink, Plant, PlantGroup)
        )


def test_new_wfo_identity_link_and_plant_in_one_request(
    database_connection: Connection, authenticated_browser: tuple[str, str], source: None
) -> None:
    before = counts(database_connection)
    status, headers, body = post(
        authenticated_browser,
        {
            "identity": {
                "new": {"scientific_name": "Genus species", "wfo": {"source_taxon_id": SPECIES}}
            },
            "label": "Market basil",
            "direct_origin_kind": "purchased",
            "collection_entry_date": {"precision": "day", "year": 2026, "month": 11, "day": 27},
        },
    )
    assert status == 201, body
    assert body["record_kind"] == "plant"
    assert body["identity_created"]
    assert body["wfo_linked"]
    assert headers["location"] == f"/api/v1/plants/{body['record_id']}"
    assert counts(database_connection) == (before[0] + 1, before[1] + 1, before[2] + 1, before[3])
    with Session(bind=database_connection) as db:
        link = db.get(WfoLink, body["identity_id"])
        assert link is not None
        assert link.external_id == SPECIES
        plant = db.get(Plant, body["record_id"])
        assert plant is not None
        assert str(plant.botanical_identity_id) == body["identity_id"]
        assert plant.label == "Market basil"


def test_duplicate_name_reuses_identity_without_relinking(
    database_connection: Connection, authenticated_browser: tuple[str, str], source: None
) -> None:
    name = "Quick " + uuid7().hex
    first = post(authenticated_browser, {"identity": {"new": {"scientific_name": name}}})
    assert first[0] == 201
    assert first[2]["identity_created"]
    assert not first[2]["wfo_linked"]
    status, _, body = post(
        authenticated_browser,
        {
            "identity": {"new": {"scientific_name": f"  {name} "}},
            "material": "plant_group",
            "quantity": {"value": 12, "is_approximate": True},
        },
    )
    assert status == 201, body
    assert body["identity_id"] == first[2]["identity_id"]
    assert not body["identity_created"]
    assert not body["wfo_linked"]
    assert body["record_kind"] == "plant_group"
    with Session(bind=database_connection) as db:
        group = db.get(PlantGroup, body["record_id"])
        assert group is not None
        assert (group.quantity_value, group.quantity_is_approximate) == (12, True)


def test_existing_identity_and_failures_leave_nothing_behind(
    database_connection: Connection, authenticated_browser: tuple[str, str], source: None
) -> None:
    created = post(
        authenticated_browser, {"identity": {"new": {"scientific_name": "Genus second"}}}
    )
    assert created[0] == 201
    existing = created[2]["identity_id"]
    ok = post(authenticated_browser, {"identity": {"existing_id": existing}})
    assert ok[0] == 201
    assert ok[2]["identity_id"] == existing
    assert not ok[2]["identity_created"]
    before = counts(database_connection)
    failures: list[tuple[dict[str, Any], int, str | None]] = [
        # Picked WFO name no longer matches the typed name.
        (
            {
                "identity": {
                    "new": {
                        "scientific_name": "Other " + uuid7().hex,
                        "wfo": {"source_taxon_id": SPECIES},
                    }
                }
            },
            422,
            "wfo_name_mismatch",
        ),
        # Unknown WFO taxon.
        (
            {
                "identity": {
                    "new": {
                        "scientific_name": "Genus x",
                        "wfo": {"source_taxon_id": "wfo-9999999999"},
                    }
                }
            },
            422,
            "wfo_name_mismatch",
        ),
        # A missing Location rolls back the freshly created identity and link.
        (
            {
                "identity": {
                    "new": {"scientific_name": "Old species", "wfo": {"source_taxon_id": SYNONYM}}
                },
                "location_id": str(uuid7()),
            },
            404,
            None,
        ),
        ({"identity": {"existing_id": str(uuid7())}}, 404, "botanical_identity_not_found"),
        (
            {
                "identity": {"existing_id": existing},
                "quantity": {"value": 2, "is_approximate": False},
            },
            422,
            None,
        ),
        ({"identity": {"existing_id": existing, "new": {"scientific_name": "X"}}}, 422, None),
        ({"identity": {}}, 422, None),
        (
            {
                "identity": {"existing_id": existing},
                "material": "plant_group",
                "quantity": {"value": 0, "is_approximate": False},
            },
            422,
            None,
        ),
    ]
    for body, expected, code in failures:
        status, _, response = post(authenticated_browser, body)
        assert status == expected, (body, response)
        if code:
            assert response["detail"]["code"] == code
    assert counts(database_connection) == before


def test_requires_csrf_and_owner(authenticated_browser: tuple[str, str], source: None) -> None:
    cookie, _csrf = authenticated_browser
    body = {"identity": {"new": {"scientific_name": "Genus species"}}}
    assert request("POST", URL, body=body)[0] == 401
    assert request("POST", URL, body=body, headers={"cookie": cookie, "origin": ORIGIN})[0] == 403


def test_unavailable_index_refuses_wfo_choice_but_not_free_text(
    database_connection: Connection, authenticated_browser: tuple[str, str]
) -> None:
    app.dependency_overrides[source_dependency] = lambda: WfoSource(None)
    try:
        before = counts(database_connection)
        status, _, body = post(
            authenticated_browser,
            {
                "identity": {
                    "new": {
                        "scientific_name": "Genus " + uuid7().hex,
                        "wfo": {"source_taxon_id": SPECIES},
                    }
                }
            },
        )
        assert status == 503
        assert body["detail"]["code"] == "taxonomy_unavailable"
        assert counts(database_connection) == before
        assert (
            post(
                authenticated_browser,
                {"identity": {"new": {"scientific_name": "Free " + uuid7().hex}}},
            )[0]
            == 201
        )
    finally:
        app.dependency_overrides.pop(source_dependency, None)
