from collections.abc import Iterator
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid7

import pytest
from sqlalchemy import Connection
from sqlalchemy.orm import Session

from florabase.auth.service import bootstrap_owner
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.core.config import get_settings
from florabase.db.session import get_database_session
from florabase.main import app
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing
from integration.test_seed_lot_api import (
    ORIGIN,
    mutate,
    override_database,
    request,
    settings,
)

pytestmark = pytest.mark.integration

PASSWORD = "correct horse battery staple"


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
        headers={"origin": ORIGIN},
    )
    assert status_code == 200
    try:
        yield response_headers["set-cookie"].split(";", 1)[0], body["csrf_token"]
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def lineage_records(database_connection: Connection) -> dict[str, str]:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        root_identity = BotanicalIdentity(scientific_name="Solanum sp.")
        producer_identity = BotanicalIdentity(scientific_name="Solanum quitoense")
        descendant_identity = BotanicalIdentity(scientific_name="Solanum descendant")
        database.add_all([root_identity, producer_identity, descendant_identity])
        database.flush()
        root_lot = SeedLot(
            botanical_identity_id=root_identity.id,
            label="Generation A seed",
            quantity_kind="seed_count",
            quantity_value=Decimal("50"),
            quantity_is_approximate=False,
        )
        database.add(root_lot)
        database.flush()
        root_sowing = Sowing(
            seed_lot_id=root_lot.id,
            label="Generation A sowing",
            quantity_kind="seed_count",
            quantity_value=Decimal("10"),
            quantity_is_approximate=False,
            germinated_count=4,
            lifecycle="completed",
        )
        database.add(root_sowing)
        database.flush()
        plant_a = Plant(
            botanical_identity_id=producer_identity.id,
            direct_origin_kind="unknown",
            label="Plant A",
            lifecycle="dead",
        )
        group_a = PlantGroup(
            botanical_identity_id=producer_identity.id,
            direct_origin_kind="unknown",
            label="Group A",
            lifecycle="completed",
        )
        direct_plant = Plant(
            botanical_identity_id=producer_identity.id,
            direct_origin_kind="unknown",
            label="Direct root",
        )
        direct_group = PlantGroup(
            botanical_identity_id=producer_identity.id,
            direct_origin_kind="unknown",
            label="Direct group root",
        )
        database.add_all([plant_a, group_a, direct_plant, direct_group])
        database.flush()
        plant_a.originating_sowing_id = root_sowing.id
        plant_a.direct_origin_kind = None
        group_a.originating_sowing_id = root_sowing.id
        group_a.direct_origin_kind = None
        database.flush()
        extracted_plant = Plant(
            botanical_identity_id=descendant_identity.id,
            originating_plant_group_id=group_a.id,
            direct_origin_kind=None,
            label="Extracted A",
        )
        database.add(extracted_plant)
        database.flush()
        lot_b = SeedLot(
            botanical_identity_id=descendant_identity.id,
            label="Generation B seed",
            source_kind="collection_produced",
            producer_plant_id=plant_a.id,
        )
        database.add(lot_b)
        database.flush()
        sowing_b = Sowing(seed_lot_id=lot_b.id, label="Generation B sowing", lifecycle="failed")
        database.add(sowing_b)
        database.flush()
        plant_b = Plant(
            botanical_identity_id=descendant_identity.id,
            direct_origin_kind="unknown",
            label="Plant B",
            lifecycle="lost",
        )
        database.add(plant_b)
        database.flush()
        plant_b.originating_sowing_id = sowing_b.id
        plant_b.direct_origin_kind = None
        database.commit()
        return {
            "root_identity": str(root_identity.id),
            "producer_identity": str(producer_identity.id),
            "descendant_identity": str(descendant_identity.id),
            "root_lot": str(root_lot.id),
            "root_sowing": str(root_sowing.id),
            "plant_a": str(plant_a.id),
            "group_a": str(group_a.id),
            "direct_plant": str(direct_plant.id),
            "direct_group": str(direct_group.id),
            "extracted_plant": str(extracted_plant.id),
            "lot_b": str(lot_b.id),
            "sowing_b": str(sowing_b.id),
            "plant_b": str(plant_b.id),
        }


def _producer_payload(identity_id: str, **overrides: object) -> dict[str, object]:
    return {
        "botanical_identity_id": identity_id,
        "source_kind": "collection_produced",
        **overrides,
    }


def test_producer_create_update_summaries_inactive_identity_independence_and_no_mutation(
    authenticated_browser: tuple[str, str],
    lineage_records: dict[str, str],
    database_connection: Connection,
) -> None:
    unknown_status, _, unknown = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/seed-lots",
        _producer_payload(
            lineage_records["descendant_identity"],
            quantity={"kind": "seed_count", "value": "7", "is_approximate": False},
        ),
    )
    assert unknown_status == 201
    assert unknown["producer_plant"] is None
    assert unknown["producer_plant_group"] is None

    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        root = database.get(SeedLot, UUID(lineage_records["root_lot"]))
        sowing = database.get(Sowing, UUID(lineage_records["root_sowing"]))
        plant = database.get(Plant, UUID(lineage_records["plant_a"]))
        group = database.get(PlantGroup, UUID(lineage_records["group_a"]))
        assert root is not None
        assert sowing is not None
        assert plant is not None
        assert group is not None
        before = (
            root.quantity_value,
            sowing.quantity_value,
            sowing.germinated_count,
            plant.lifecycle,
            plant.botanical_identity_id,
            group.lifecycle,
        )

    plant_status, _, plant_lot = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/seed-lots",
        _producer_payload(
            lineage_records["descendant_identity"],
            producer_plant_id=lineage_records["plant_a"],
        ),
    )
    assert plant_status == 201
    assert plant_lot["producer_plant"] == {
        "id": lineage_records["plant_a"],
        "label": "Plant A",
        "lifecycle": "dead",
        "botanical_identity": {
            "id": lineage_records["producer_identity"],
            "display_label": "Solanum quitoense",
        },
    }
    assert (
        plant_lot["botanical_identity_id"]
        != plant_lot["producer_plant"]["botanical_identity"]["id"]
    )

    group_payload = _producer_payload(
        lineage_records["descendant_identity"],
        producer_plant_group_id=lineage_records["group_a"],
    )
    group_status, _, group_lot = mutate(
        authenticated_browser, "POST", "/api/v1/seed-lots", group_payload
    )
    assert group_status == 201
    assert group_lot["producer_plant_group"]["lifecycle"] == "completed"

    base = _producer_payload(
        lineage_records["descendant_identity"],
        quantity={"kind": "seed_count", "value": "7", "is_approximate": False},
    )
    assert (
        mutate(
            authenticated_browser,
            "PUT",
            f"/api/v1/seed-lots/{unknown['id']}",
            {**base, "producer_plant_id": lineage_records["plant_a"]},
        )[0]
        == 200
    )
    assert (
        mutate(
            authenticated_browser,
            "PUT",
            f"/api/v1/seed-lots/{unknown['id']}",
            {**base, "producer_plant_group_id": lineage_records["group_a"]},
        )[0]
        == 200
    )
    cleared = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/seed-lots/{unknown['id']}",
        base,
    )[2]
    assert cleared["quantity"] == {
        "kind": "seed_count",
        "value": "7",
        "unit": None,
        "is_approximate": False,
    }
    corrected_status, _, corrected = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/seed-lots/{unknown['id']}",
        {**base, "source_kind": "other"},
    )
    assert corrected_status == 200
    assert corrected["source_kind"] == "other"
    assert corrected["quantity"] == cleared["quantity"]

    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        root = database.get(SeedLot, UUID(lineage_records["root_lot"]))
        sowing = database.get(Sowing, UUID(lineage_records["root_sowing"]))
        plant = database.get(Plant, UUID(lineage_records["plant_a"]))
        group = database.get(PlantGroup, UUID(lineage_records["group_a"]))
        assert root is not None
        assert sowing is not None
        assert plant is not None
        assert group is not None
        after = (
            root.quantity_value,
            sowing.quantity_value,
            sowing.germinated_count,
            plant.lifecycle,
            plant.botanical_identity_id,
            group.lifecycle,
        )
    assert after == before


@pytest.mark.parametrize("source_kind", ["purchased", "gift_exchange", "unknown"])
def test_producer_validation_missing_references_and_atomic_source_correction(
    authenticated_browser: tuple[str, str],
    lineage_records: dict[str, str],
    source_kind: str,
) -> None:
    invalid = {
        "botanical_identity_id": lineage_records["descendant_identity"],
        "source_kind": source_kind,
        "producer_plant_id": lineage_records["plant_a"],
    }
    assert mutate(authenticated_browser, "POST", "/api/v1/seed-lots", invalid)[0] == 422

    both = _producer_payload(
        lineage_records["descendant_identity"],
        producer_plant_id=lineage_records["plant_a"],
        producer_plant_group_id=lineage_records["group_a"],
    )
    assert mutate(authenticated_browser, "POST", "/api/v1/seed-lots", both)[0] == 422

    field = "producer_plant_id" if source_kind == "purchased" else "producer_plant_group_id"
    missing_status, _, missing = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/seed-lots",
        _producer_payload(lineage_records["descendant_identity"], **{field: str(uuid7())}),
    )
    assert missing_status == 404
    assert missing["detail"]["code"] == (
        "producer_plant_not_found"
        if field == "producer_plant_id"
        else "producer_plant_group_not_found"
    )

    created = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/seed-lots",
        _producer_payload(
            lineage_records["descendant_identity"],
            producer_plant_id=lineage_records["plant_a"],
        ),
    )[2]
    retained = {**invalid, "source_kind": source_kind}
    assert (
        mutate(authenticated_browser, "PUT", f"/api/v1/seed-lots/{created['id']}", retained)[0]
        == 422
    )


def test_direct_and_multigeneration_cycles_are_rejected_but_valid_chain_is_traversable(
    authenticated_browser: tuple[str, str], lineage_records: dict[str, str]
) -> None:
    root_update = _producer_payload(
        lineage_records["root_identity"], producer_plant_id=lineage_records["plant_a"]
    )
    plant_cycle = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/seed-lots/{lineage_records['root_lot']}",
        root_update,
    )
    assert plant_cycle[0] == 409
    assert plant_cycle[2]["detail"]["code"] == "lineage_cycle"

    group_cycle = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/seed-lots/{lineage_records['root_lot']}",
        _producer_payload(
            lineage_records["root_identity"], producer_plant_group_id=lineage_records["group_a"]
        ),
    )
    assert group_cycle[0] == 409

    long_cycle = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/seed-lots/{lineage_records['root_lot']}",
        _producer_payload(
            lineage_records["root_identity"], producer_plant_id=lineage_records["plant_b"]
        ),
    )
    assert long_cycle[0] == 409

    extracted_cycle = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/seed-lots/{lineage_records['root_lot']}",
        _producer_payload(
            lineage_records["root_identity"],
            producer_plant_id=lineage_records["extracted_plant"],
        ),
    )
    assert extracted_cycle[0] == 409

    valid_status, _, valid = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/seed-lots",
        _producer_payload(
            lineage_records["root_identity"],
            producer_plant_id=lineage_records["plant_b"],
            label="Generation C seed",
        ),
    )
    assert valid_status == 201
    cookie, _ = authenticated_browser
    status_code, _, traversal = request(
        "GET", f"/api/v1/seed-lots/{valid['id']}/lineage", headers={"cookie": cookie}
    )
    assert status_code == 200
    assert traversal["subject"]["kind"] == "seed_lot"
    assert [node["kind"] for node in traversal["ancestors"]] == [
        "plant",
        "sowing",
        "seed_lot",
        "plant",
        "sowing",
        "seed_lot",
    ]
    assert [node["id"] for node in traversal["ancestors"]] == [
        lineage_records["plant_b"],
        lineage_records["sowing_b"],
        lineage_records["lot_b"],
        lineage_records["plant_a"],
        lineage_records["root_sowing"],
        lineage_records["root_lot"],
    ]


def test_traversal_roots_sowing_group_partial_identity_and_security(
    authenticated_browser: tuple[str, str], lineage_records: dict[str, str]
) -> None:
    cookie, _ = authenticated_browser
    for route, item_id, kind in (
        ("plants", lineage_records["direct_plant"], "plant"),
        ("plant-groups", lineage_records["direct_group"], "plant_group"),
    ):
        status_code, _, body = request(
            "GET", f"/api/v1/{route}/{item_id}/lineage", headers={"cookie": cookie}
        )
        assert status_code == 200
        assert body["subject"]["kind"] == kind
        assert body["ancestors"] == []

    unknown_status, _, unknown = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/seed-lots",
        _producer_payload(lineage_records["root_identity"]),
    )
    assert unknown_status == 201
    assert (
        request("GET", f"/api/v1/seed-lots/{unknown['id']}/lineage", headers={"cookie": cookie})[2][
            "ancestors"
        ]
        == []
    )

    for route, item_id, subject_kind in (
        ("plants", lineage_records["plant_a"], "plant"),
        ("plant-groups", lineage_records["group_a"], "plant_group"),
    ):
        status_code, _, body = request(
            "GET", f"/api/v1/{route}/{item_id}/lineage", headers={"cookie": cookie}
        )
        assert status_code == 200
        assert body["subject"]["kind"] == subject_kind
        assert [node["kind"] for node in body["ancestors"]] == ["sowing", "seed_lot"]
        assert body["ancestors"][1]["botanical_identity"]["id"] == lineage_records["root_identity"]

    extracted = request(
        "GET",
        f"/api/v1/plants/{lineage_records['extracted_plant']}/lineage",
        headers={"cookie": cookie},
    )[2]
    assert [node["kind"] for node in extracted["ancestors"]] == [
        "plant_group",
        "sowing",
        "seed_lot",
    ]
    assert extracted["ancestors"][0]["id"] == lineage_records["group_a"]

    produced = request(
        "GET",
        f"/api/v1/seed-lots/{lineage_records['lot_b']}/lineage",
        headers={"cookie": cookie},
    )[2]
    assert [node["kind"] for node in produced["ancestors"]] == [
        "plant",
        "sowing",
        "seed_lot",
    ]
    assert (
        produced["subject"]["botanical_identity"]["id"]
        != produced["ancestors"][0]["botanical_identity"]["id"]
    )

    assert request("GET", f"/api/v1/plants/{lineage_records['plant_a']}/lineage")[0] == 401
    assert request("GET", f"/api/v1/plants/{uuid7()}/lineage", headers={"cookie": cookie})[0] == 404


@pytest.mark.parametrize("route", ["plants", "plant-groups", "sowings"])
def test_source_corrections_cannot_close_a_producer_cycle(
    authenticated_browser: tuple[str, str], lineage_records: dict[str, str], route: str
) -> None:
    records = lineage_records
    if route == "sowings":
        item_id = records["root_sowing"]
        payload = {"seed_lot_id": records["lot_b"]}
    elif route == "plants":
        item_id = records["plant_a"]
        payload = {
            "botanical_identity_id": records["producer_identity"],
            "originating_sowing_id": records["sowing_b"],
            "lifecycle": "dead",
        }
    else:
        item_id = records["group_a"]
        lot_status, _, lot = mutate(
            authenticated_browser,
            "POST",
            "/api/v1/seed-lots",
            _producer_payload(records["root_identity"], producer_plant_group_id=item_id),
        )
        assert lot_status == 201
        sowing_status, _, sowing = mutate(
            authenticated_browser, "POST", "/api/v1/sowings", {"seed_lot_id": lot["id"]}
        )
        assert sowing_status == 201
        payload = {
            "botanical_identity_id": records["producer_identity"],
            "originating_sowing_id": sowing["id"],
            "lifecycle": "completed",
        }
    suffix = "" if route == "sowings" else "/lineage"
    before = request(
        "GET", f"/api/v1/{route}/{item_id}{suffix}", headers={"cookie": authenticated_browser[0]}
    )[2]
    status, _, error = mutate(authenticated_browser, "PUT", f"/api/v1/{route}/{item_id}", payload)
    assert status == 409
    assert error["detail"]["code"] == "lineage_cycle"
    after_status, _, after = request(
        "GET", f"/api/v1/{route}/{item_id}{suffix}", headers={"cookie": authenticated_browser[0]}
    )
    assert after_status == 200
    assert after == before


def _explore(cookie: str, path: str) -> tuple[int, Any]:
    status_code, _, body = request("GET", f"/api/v1/lineage/{path}", headers={"cookie": cookie})
    return status_code, body


def _keys(nodes: list[dict[str, Any]]) -> list[tuple[str, str]]:
    return [(node["record"]["kind"], node["record"]["id"]) for node in nodes]


def test_ancestry_explorer_branches_pages_and_keeps_unknown_and_inactive_honest(
    authenticated_browser: tuple[str, str], lineage_records: dict[str, str]
) -> None:
    cookie, _ = authenticated_browser
    records = lineage_records

    status_code, root = _explore(cookie, f"seed_lot/{records['root_lot']}")
    assert status_code == 200
    assert root["focus"]["origin"] == "unknown"
    assert root["focus"]["harvest_conversion"] is None
    assert root["ancestors"] == []
    assert root["focus"]["descendant_count"] == root["children"]["total"] == 1
    assert _keys(root["children"]["items"]) == [("sowing", records["root_sowing"])]
    assert root["children"]["items"][0]["descendant_count"] == 2

    # Branching: groups before plants, each with its own expandable count; paging is bounded.
    _, branch = _explore(cookie, f"sowing/{records['root_sowing']}/children")
    assert branch["total"] == 2
    assert _keys(branch["items"]) == [
        ("plant_group", records["group_a"]),
        ("plant", records["plant_a"]),
    ]
    assert [item["descendant_count"] for item in branch["items"]] == [1, 1]
    _, second = _explore(cookie, f"sowing/{records['root_sowing']}/children?offset=1&limit=1")
    assert (second["total"], second["offset"], second["limit"]) == (2, 1, 1)
    assert _keys(second["items"]) == [("plant", records["plant_a"])]
    _, beyond = _explore(cookie, f"sowing/{records['root_sowing']}/children?offset=9")
    assert (beyond["total"], beyond["items"]) == (2, [])

    _, extracted = _explore(cookie, f"plant_group/{records['group_a']}/children")
    assert _keys(extracted["items"]) == [("plant", records["extracted_plant"])]
    _, produced = _explore(cookie, f"plant/{records['plant_a']}/children")
    assert _keys(produced["items"]) == [("seed_lot", records["lot_b"])]
    # A directly recorded producer, without a Harvest conversion, says so.
    assert produced["items"][0]["origin"] == "collection_produced"
    assert produced["items"][0]["harvest_conversion"] is None

    # Backward: the full recorded chain, nearest first, with inactive lifecycles retained.
    _, leaf = _explore(cookie, f"plant/{records['plant_b']}")
    assert leaf["focus"]["origin"] is None
    assert leaf["focus"]["record"]["lifecycle"] == "lost"
    assert _keys(leaf["ancestors"]) == [
        ("sowing", records["sowing_b"]),
        ("seed_lot", records["lot_b"]),
        ("plant", records["plant_a"]),
        ("sowing", records["root_sowing"]),
        ("seed_lot", records["root_lot"]),
    ]
    assert [node["record"]["lifecycle"] for node in leaf["ancestors"]] == [
        "failed",
        "active",
        "dead",
        "completed",
        "active",
    ]

    # Independent material of the same identity is never attached to anyone's lineage.
    _, direct = _explore(cookie, f"plant/{records['direct_plant']}")
    assert direct["focus"]["origin"] == "unknown"
    assert direct["ancestors"] == []
    assert direct["children"] == {"total": 0, "offset": 0, "limit": 25, "items": []}
    for path in (
        f"seed_lot/{records['root_lot']}",
        f"sowing/{records['root_sowing']}/children",
        f"plant/{records['plant_a']}/children",
    ):
        assert records["direct_plant"] not in str(_explore(cookie, path)[1])

    # A collection-produced SeedLot whose producer was never recorded stays an unknown parent.
    _, _, unknown = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/seed-lots",
        _producer_payload(records["root_identity"]),
    )
    _, orphan = _explore(cookie, f"seed_lot/{unknown['id']}")
    assert orphan["focus"]["origin"] == "collection_produced"
    assert orphan["ancestors"] == []


def test_ancestry_explorer_requires_authentication_and_validates_inputs(
    authenticated_browser: tuple[str, str], lineage_records: dict[str, str]
) -> None:
    cookie, _ = authenticated_browser
    plant = lineage_records["plant_a"]
    assert request("GET", f"/api/v1/lineage/plant/{plant}")[0] == 401
    assert request("GET", f"/api/v1/lineage/plant/{plant}/children")[0] == 401
    assert _explore(cookie, f"plant/{uuid7()}")[0] == 404
    assert _explore(cookie, f"plant/{uuid7()}/children")[0] == 404
    # Concrete types scope UUIDs: a Plant ID is not a SeedLot.
    assert _explore(cookie, f"seed_lot/{plant}")[0] == 404
    assert _explore(cookie, f"harvest/{plant}")[0] == 422
    assert _explore(cookie, f"plant/{plant}/children?limit=101")[0] == 422
    assert _explore(cookie, f"plant/{plant}/children?offset=-1")[0] == 422


# Every view the explorer offers over the fixture: chains from both ends and each branch level.
_VIEWS = (
    "seed_lot/{root_lot}",
    "sowing/{root_sowing}/children",
    "plant_group/{group_a}",
    "plant_group/{group_a}/children",
    "plant/{plant_a}/children",
    "plant/{extracted_plant}",
    "plant/{plant_b}",
)


def _shape(value: Any) -> Any:
    """The ancestry with identity labels removed: edges, order, counts, origins, lifecycles."""
    if isinstance(value, dict):
        return {key: _shape(item) for key, item in value.items() if key != "botanical_identity"}
    if isinstance(value, list):
        return [_shape(item) for item in value]
    return value


def _identities(value: Any) -> dict[str, tuple[str, str]]:
    found: dict[str, tuple[str, str]] = {}
    if isinstance(value, dict):
        identity = value.get("botanical_identity")
        if "id" in value and isinstance(identity, dict):
            found[value["id"]] = (identity["id"], identity["display_label"])
        for item in value.values():
            found |= _identities(item)
    elif isinstance(value, list):
        for item in value:
            found |= _identities(item)
    return found


def _identity(cookie: str, identity_id: str) -> Any:
    status_code, _, body = request(
        "GET", f"/api/v1/botanical-identities/{identity_id}", headers={"cookie": cookie}
    )
    assert status_code == 200, body
    return body


def _view(cookie: str, path: str) -> Any:
    status_code, body = _explore(cookie, path)
    assert status_code == 200, (path, body)
    return body


def test_taxonomy_reconciliation_keeps_lineage_measurements_and_uuids_intact(
    authenticated_browser: tuple[str, str], lineage_records: dict[str, str]
) -> None:
    cookie, _ = authenticated_browser
    records = lineage_records
    views = [view.format(**records) for view in _VIEWS]
    measured = records["extracted_plant"]
    events_path = f"/api/v1/plants/{measured}/events"
    march = {"precision": "day", "year": 2026, "month": 3, "day": 14}
    height = {"quantity": "height", "value": "12.5", "unit": "cm", "is_approximate": False}
    status_code, _, event = mutate(
        authenticated_browser,
        "POST",
        events_path,
        {"kind": "measurement", "occurred_on": march, "measurement": height},
    )
    assert status_code == 201, event
    status_code, _, event = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/events/{event['id']}",
        {"kind": "measurement", "occurred_on": march, "measurement": height | {"value": "13"}},
    )
    assert status_code == 200, event
    events_status, _, events_before = request("GET", events_path, headers={"cookie": cookie})
    assert events_status == 200, events_before

    before = {view: _view(cookie, view) for view in views}
    identities_before = _identities(list(before.values()))
    assert identities_before[records["plant_b"]][0] == records["descendant_identity"]

    # 1. Accepted-name correction in place: same identity UUID, new name, old name in the ledger.
    root = _identity(cookie, records["root_identity"])
    status_code, _, corrected = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/botanical-identities/{root['id']}/reconciliation/correct-name",
        {"scientific_name": "Solanum lycopersicum", "identity_updated_at": root["updated_at"]},
    )
    assert status_code == 200, corrected
    assert [name["scientific_name"] for name in corrected["former_names"]] == ["Solanum sp."]

    # 2. Duplicate merge: every descendant-identity holding is repointed to the survivor.
    duplicate = _identity(cookie, records["descendant_identity"])
    survivor = _identity(cookie, records["producer_identity"])
    status_code, _, merged = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/botanical-identities/{duplicate['id']}/reconciliation/merge-duplicate",
        {
            "survivor_identity_id": survivor["id"],
            "duplicate_updated_at": duplicate["updated_at"],
            "survivor_updated_at": survivor["updated_at"],
            "profile_resolution": "keep_survivor",
        },
    )
    assert status_code == 200, merged
    assert _identity(cookie, duplicate["id"])["merged_into_id"] == survivor["id"]

    after = {view: _view(cookie, view) for view in views}
    for view in views:
        # Identity work neither creates, removes nor reorders any edge, count or lifecycle,
        # and keeps every Plant, PlantGroup, Sowing and SeedLot UUID.
        assert _shape(after[view]) == _shape(before[view]), view

    identities_after = _identities(list(after.values()))
    assert identities_after.keys() == identities_before.keys()
    for record_id, (identity_id, label) in identities_before.items():
        if identity_id == records["descendant_identity"]:
            assert identities_after[record_id] == (survivor["id"], survivor["display_label"])
        elif identity_id == records["root_identity"]:
            assert identities_after[record_id] == (root["id"], "Solanum lycopersicum")
        else:
            assert identities_after[record_id] == (identity_id, label)
    # The retired duplicate and the historical name are not nodes or labels anywhere.
    for body in after.values():
        assert duplicate["id"] not in str(body)
        assert "Solanum sp." not in str(body)
        assert "Solanum descendant" not in str(body)

    # Measurement history stays on the same Plant UUID, untouched and outside the ancestry.
    events_status, _, events_after = request("GET", events_path, headers={"cookie": cookie})
    assert events_status == 200, events_after
    # Same events, values, dates and correction trail on the same Plant UUID; only the
    # Plant's displayed identity follows the merge to the survivor.
    assert _shape(events_after) == _shape(events_before)
    assert _identities(events_after) == {measured: (survivor["id"], survivor["display_label"])}
    assert [item["measurement"]["value"] for item in events_after] == ["13"]
    assert len(events_after[0]["measurement_corrections"]) == 1
    for body in after.values():
        assert event["id"] not in str(body)
