from collections.abc import Iterator
from decimal import Decimal
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
