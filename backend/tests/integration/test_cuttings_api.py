from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from typing import Any
from uuid import uuid7

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, delete, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.cuttings.model import PropagationAttempt, VegetativeLot
from florabase.cuttings.schemas import AttemptCreate, VegetativeLotCreate
from florabase.cuttings.service import create_lot, start_attempt
from florabase.main import app
from florabase.propagation.service import PropagationConflictError
from florabase.reversals.model import OperationReceipt
from integration.test_seed_lot_api import authenticated_browser as authenticated_browser
from integration.test_seed_lot_api import mutate, request

pytestmark = pytest.mark.integration
FAST = "/api/v1/propagation-attempts/fast-create"
LOTS = "/api/v1/vegetative-lots"
ATTEMPTS = "/api/v1/propagation-attempts"


def _write(
    browser: tuple[str, str],
    method: str,
    path: str,
    body: dict[str, Any],
    expected: int = 201,
) -> Any:
    status, _, response = mutate(browser, method, path, body)
    assert status == expected, response
    return response


def _read(browser: tuple[str, str], path: str) -> Any:
    response = TestClient(app, base_url="https://florabase.example").get(
        path,
        headers={"cookie": browser[0]},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _count(value: int, approximate: bool = False) -> dict[str, object]:
    return {"value": value, "is_approximate": approximate}


def _payload(identity_id: str, **changes: Any) -> dict[str, Any]:
    return {
        "vegetative_lot": {
            "botanical_identity_id": identity_id,
            "material_type": "stem_cutting",
            "initial_quantity": _count(5),
            "taken_on": {"precision": "month", "year": 2026, "month": 10},
            **changes,
        },
        "source_adjustment": {"mode": "use_all"},
        "propagation_attempt": {"quantity": _count(5), "substrate": "Perlite"},
    }


@pytest.fixture
def cutting_identity(database_connection: Connection) -> str:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        identity = BotanicalIdentity(scientific_name="Salvia rosmarinus")
        database.add(identity)
        database.flush()
        identity_id = str(identity.id)
        database.commit()
    return identity_id


def test_fast_creation_preserves_precision_and_rolls_back_on_stock_conflict(
    authenticated_browser: tuple[str, str],
    cutting_identity: str,
    database_connection: Connection,
) -> None:
    browser = authenticated_browser
    payload = _payload(cutting_identity, label="West bench")
    assert request("POST", FAST, body=payload)[0] in {401, 403}
    assert request("POST", FAST, body=payload, headers={"cookie": browser[0]})[0] == 403
    payload["propagation_attempt"]["quantity"] = _count(6)
    _write(browser, "POST", FAST, payload, 409)
    assert database_connection.execute(select(VegetativeLot.id)).all() == []
    assert database_connection.execute(select(PropagationAttempt.id)).all() == []
    assert database_connection.execute(select(OperationReceipt.id)).all() == []
    payload["propagation_attempt"]["quantity"] = _count(5)
    saved = _write(browser, "POST", FAST, payload)
    lot, attempt = saved["vegetative_lot"], saved["propagation_attempt"]
    assert lot["initial_quantity"] == _count(5)
    assert lot["quantity"] == _count(0)
    assert attempt["started_on"] == lot["taken_on"]
    assert attempt["rooted_count"] is None
    assert attempt["rooting_rate_percent"] is None
    assert _read(browser, f"{LOTS}?q=rosmarinus")[0]["id"] == lot["id"]
    listed = _read(browser, f"{ATTEMPTS}?q=Perlite")[0]
    assert listed["id"] == attempt["id"]
    assert listed["botanical_identity_id"] == cutting_identity
    assert "rosmarinus" in listed["botanical_display_label"]


@pytest.mark.parametrize("group", [False, True])
def test_clonal_lineage_db_and_api_cycle_guards_and_downstream_first_undo(
    authenticated_browser: tuple[str, str],
    cutting_identity: str,
    database_connection: Connection,
    group: bool,
) -> None:
    browser = authenticated_browser
    kind = "plant_group" if group else "plant"
    route = "plant-groups" if group else "plants"
    mother = _write(
        browser,
        "POST",
        f"/api/v1/{route}",
        {
            "botanical_identity_id": cutting_identity,
            "label": "Mother",
        },
    )
    maternal_field = f"mother_{kind}_id"
    payload = _payload(
        cutting_identity, source_kind="collection_produced", **{maternal_field: mother["id"]}
    )
    del payload["vegetative_lot"]["botanical_identity_id"]
    transition = _write(browser, "POST", FAST, payload)
    lot, attempt = transition["vegetative_lot"], transition["propagation_attempt"]
    attempt_url = f"{ATTEMPTS}/{attempt['id']}"
    offspring = _write(browser, "POST", f"{attempt_url}/{route}", {"label": "Clone"})
    lineage = _read(browser, f"/api/v1/{route}/{offspring['id']}/lineage")
    assert [item["kind"] for item in lineage["ancestors"]] == [
        "propagation_attempt",
        "vegetative_lot",
        kind,
    ]
    assert lineage["ancestors"][-1]["id"] == mother["id"]
    assert (
        _read(browser, f"/api/v1/{route}/{offspring['id']}")["originating_propagation_attempt_id"]
        == attempt["id"]
    )
    explorer = "/api/v1/lineage"
    chart = _read(browser, f"{explorer}/{kind}/{offspring['id']}")
    assert [node["record"]["id"] for node in chart["ancestors"]] == [
        attempt["id"],
        lot["id"],
        mother["id"],
    ]
    assert [node["descendant_count"] for node in chart["ancestors"]] == [1, 1, 1]
    for parent_kind, parent, child_kind, child in (
        (kind, mother, "vegetative_lot", lot),
        ("vegetative_lot", lot, "propagation_attempt", attempt),
        ("propagation_attempt", attempt, kind, offspring),
    ):
        direct = _read(browser, f"{explorer}/{parent_kind}/{parent['id']}/children?limit=1")
        assert direct["total"] == 1
        assert [(node["record"]["kind"], node["record"]["id"]) for node in direct["items"]] == [
            (child_kind, child["id"])
        ]
    with pytest.raises(IntegrityError, match="acyclic"), database_connection.begin_nested():
        database_connection.execute(
            text(f"UPDATE vegetative_lots SET {maternal_field} = :child WHERE id = :lot"),
            {"child": offspring["id"], "lot": lot["id"]},
        )
    correction = {
        "material_type": lot["material_type"],
        "source_kind": lot["source_kind"],
        maternal_field: offspring["id"],
        "quantity": lot["quantity"],
        "lifecycle": lot["lifecycle"],
        "expected_updated_at": lot["updated_at"],
    }
    assert (
        _write(browser, "PUT", f"{LOTS}/{lot['id']}", correction, 409)["detail"]["code"]
        == "lineage_cycle"
    )
    reverse_start = f"/api/v1/cutting-operations/{transition['operation_receipt_id']}/reversal"
    reverse_child = f"/api/v1/cutting-operations/{offspring['operation_receipt_id']}/reversal"
    assert _read(browser, reverse_start)["status"] == "blocked"
    _write(browser, "POST", reverse_child, {}, 204)
    _write(browser, "POST", f"{attempt_url}/observations", {"stage": "callus"})
    assert _read(browser, reverse_start)["status"] == "confirmation_required"
    _write(browser, "POST", reverse_start, {}, 409)
    _write(browser, "POST", reverse_start, {"confirm_retained_observations": True}, 204)
    assert _read(browser, f"{LOTS}/{lot['id']}")["quantity"] == _count(5)
    reversed_attempt = _read(browser, attempt_url)
    assert reversed_attempt["lifecycle"] == "reversed"
    assert reversed_attempt["observations"][0]["stage"] == "callus"


def test_split_approximate_and_unknown_stock_retains_uncertainty(
    authenticated_browser: tuple[str, str],
    cutting_identity: str,
) -> None:
    browser = authenticated_browser
    lot = _write(
        browser,
        "POST",
        LOTS,
        {
            "botanical_identity_id": cutting_identity,
            "material_type": "leaf_cutting",
            "source_kind": "gift_exchange",
            "initial_quantity": _count(10, True),
        },
    )
    url = f"{LOTS}/{lot['id']}/propagation-attempts"
    payload = {
        "source_adjustment": {"mode": "partial", "resulting_quantity": _count(6, True)},
        "propagation_attempt": {"quantity": _count(4, True)},
    }
    first = _write(browser, "POST", url, payload)
    assert first["vegetative_lot"]["quantity"] == _count(6, True)
    second = _write(
        browser,
        "POST",
        url,
        {
            "source_adjustment": {"mode": "use_all"},
            "propagation_attempt": {},
        },
    )
    assert second["vegetative_lot"]["quantity"] == _count(6, True)
    assert second["vegetative_lot"]["lifecycle"] == "exhausted"
    assert second["propagation_attempt"]["quantity"] is None
    assert len(_read(browser, f"{LOTS}/{lot['id']}")["attempts"]) == 2
    _write(
        browser,
        "PUT",
        f"{ATTEMPTS}/{first['propagation_attempt']['id']}",
        {
            "lifecycle": "completed",
            "expected_updated_at": first["propagation_attempt"]["updated_at"],
            "quantity": _count(4, True),
            "rooted_count": 5,
        },
        200,
    )
    assert (
        _read(browser, f"{ATTEMPTS}/{first['propagation_attempt']['id']}")["rooting_rate_percent"]
        is None
    )
    unknown = _payload(cutting_identity, initial_quantity=None, material_type="root_cutting")
    unknown["propagation_attempt"] = {"started_on": None, "quantity": _count(3)}
    saved = _write(browser, "POST", FAST, unknown)
    assert saved["vegetative_lot"]["quantity"] is None
    assert saved["vegetative_lot"]["taken_on"] is not None
    assert saved["propagation_attempt"]["quantity"] == _count(3)
    assert saved["propagation_attempt"]["started_on"] is None


def test_failed_attempt_history_explore_schedule_and_media(
    authenticated_browser: tuple[str, str],
    cutting_identity: str,
) -> None:
    browser = authenticated_browser
    saved = _write(browser, "POST", FAST, _payload(cutting_identity))
    attempt = saved["propagation_attempt"]
    attempt_id = attempt["id"]
    url = f"{ATTEMPTS}/{attempt_id}"
    work = {
        "title": "Check rooting",
        "activity_kind": "check_rooting",
        "due_on": "2026-11-09",
        "target": {"kind": "propagation_attempt", "id": attempt_id},
    }
    schedule = _write(browser, "POST", "/api/v1/schedule", work)
    _write(
        browser,
        "POST",
        f"/api/v1/schedule/{schedule['id']}/complete",
        {"expected_version": schedule["version"]},
        200,
    )
    _write(
        browser,
        "POST",
        f"{url}/observations",
        {
            "stage": "loss",
            "rooted_count": 0,
            "observed_on": {"precision": "year", "year": 2026},
        },
    )
    media = _write(
        browser,
        "POST",
        f"/api/v1/collection-records/propagation_attempt/{attempt_id}/photos/external",
        {
            "image_url": "https://images.example.test/rot.jpg",
            "source_url": "https://images.example.test/",
            "attribution": "Collection",
        },
    )
    photo_path = f"/api/v1/collection-records/propagation_attempt/{attempt_id}/primary-photo"
    selected = _write(
        browser, "PUT", photo_path, {"kind": "external", "photo_id": media["id"]}, 200
    )
    assert selected["photo_id"] == media["id"]
    assert _read(browser, photo_path)["photo_id"] == media["id"]
    result = _write(
        browser,
        "PUT",
        url,
        {
            "lifecycle": "failed",
            "expected_updated_at": attempt["updated_at"],
            "rooted_count": 0,
            "quantity": _count(5),
            "started_on": attempt["started_on"],
            "ended_on": {"precision": "month", "year": 2026, "month": 11},
        },
        200,
    )
    assert result["rooting_rate_percent"] == 0
    _write(browser, "POST", "/api/v1/schedule", work, 409)
    _write(browser, "POST", f"{url}/plants", {}, 409)
    history = _read(browser, "/api/v1/history?year=2026")
    assert any(
        item["primary"]["id"] == attempt_id and item["source_kind"] == "rooting_observation"
        for item in history["items"]
    )
    assert any(
        item["source_id"] == schedule["id"] and item["related"][0]["id"] == attempt_id
        for item in history["items"]
    )
    assert (
        _read(browser, f"/api/v1/explore/species-distribution/identities/{cutting_identity}")[
            "representation"
        ]
        == "historical"
    )


def test_concurrent_partial_attempts_cannot_overdraw_exact_stock(database_engine: Engine) -> None:
    with Session(database_engine) as database, database.begin():
        identity = BotanicalIdentity(scientific_name=f"Cuttings concurrency {uuid7()}")
        database.add(identity)
        database.flush()
        lot = create_lot(
            database,
            VegetativeLotCreate.model_validate(
                {
                    "botanical_identity_id": identity.id,
                    "material_type": "stem_cutting",
                    "initial_quantity": _count(5),
                }
            ),
        )
        lot_id, identity_id = lot.id, identity.id

    barrier = Barrier(2)
    payload = AttemptCreate.model_validate(
        {
            "source_adjustment": {"mode": "partial"},
            "propagation_attempt": {"quantity": _count(4)},
        }
    )

    def worker() -> str:
        barrier.wait(timeout=10)
        try:
            with Session(database_engine) as database, database.begin():
                database.execute(text("SET LOCAL lock_timeout = '10s'"))
                start_attempt(database, lot_id, payload)
            return "applied"
        except PropagationConflictError as error:
            return error.code

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(lambda _: worker(), range(2))) == [
                "applied",
                "insufficient_stock",
            ]
        with Session(database_engine) as database:
            assert (
                database.scalar(
                    select(VegetativeLot.quantity_value).where(VegetativeLot.id == lot_id)
                )
                == 1
            )
    finally:
        with Session(database_engine) as database, database.begin():
            database.execute(
                delete(OperationReceipt).where(OperationReceipt.vegetative_lot_id == lot_id)
            )
            database.execute(
                delete(PropagationAttempt).where(PropagationAttempt.vegetative_lot_id == lot_id)
            )
            database.execute(delete(VegetativeLot).where(VegetativeLot.id == lot_id))
            database.execute(delete(BotanicalIdentity).where(BotanicalIdentity.id == identity_id))


def test_populated_downgrade_refuses_and_empty_schema_round_trips(
    database_connection: Connection,
) -> None:
    from alembic.autogenerate import compare_metadata
    from alembic.config import Config
    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory

    from alembic import command

    config = Config("alembic.ini")
    config.attributes["connection"] = database_connection
    assert ScriptDirectory.from_config(config).get_heads() == ["20261110_0047"]
    assert MigrationContext.configure(database_connection).get_current_heads() == ("20261110_0047",)
    with database_connection.begin_nested():
        command.downgrade(config, "20261110_0046")
        assert MigrationContext.configure(database_connection).get_current_heads() == (
            "20261110_0046",
        )
        database_connection.execute(text("SELECT phenophase FROM events LIMIT 0"))
        command.upgrade(config, "head")
        assert MigrationContext.configure(database_connection).get_current_heads() == (
            "20261110_0047",
        )
        context = MigrationContext.configure(
            database_connection,
            opts={
                "include_object": lambda obj, name, kind, _reflected, _compare: (
                    (
                        name
                        if kind == "table"
                        else getattr(getattr(obj, "table", None), "name", None)
                    )
                    in {"vegetative_lots", "propagation_attempts", "rooting_observations"}
                )
            },
        )
        assert compare_metadata(context, VegetativeLot.metadata) == []
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        identity = BotanicalIdentity(scientific_name="Downgrade guard cutting")
        database.add(identity)
        database.flush()
        create_lot(
            database,
            VegetativeLotCreate(
                botanical_identity_id=identity.id,
                material_type="leaf_cutting",
            ),
        )
        database.commit()
    with (
        pytest.raises(DBAPIError, match="Cannot downgrade CUTTING-001"),
        database_connection.begin_nested(),
    ):
        command.downgrade(config, "-1")


def test_stale_lot_edit_does_not_restore_consumed_stock(
    authenticated_browser: tuple[str, str],
    cutting_identity: str,
) -> None:
    browser = authenticated_browser
    original = _write(browser, "POST", LOTS, _payload(cutting_identity)["vegetative_lot"])
    path = f"{LOTS}/{original['id']}"
    _write(
        browser,
        "POST",
        f"{path}/propagation-attempts",
        {
            "source_adjustment": {"mode": "partial"},
            "propagation_attempt": {"quantity": _count(4)},
        },
    )
    rejected = _write(
        browser,
        "PUT",
        path,
        {
            "botanical_identity_id": cutting_identity,
            "material_type": "stem_cutting",
            "lifecycle": "active",
            "quantity": _count(5),
            "expected_updated_at": original["updated_at"],
            "notes": "A stale update",
        },
        409,
    )
    assert rejected["detail"]["code"] == "cutting_record_changed"
    assert _read(browser, path)["quantity"] == _count(1)


def test_rooted_group_correction_keeps_clonal_origin(
    authenticated_browser: tuple[str, str],
    cutting_identity: str,
) -> None:
    browser = authenticated_browser
    saved = _write(browser, "POST", FAST, _payload(cutting_identity))
    attempt = saved["propagation_attempt"]
    group = _write(
        browser, "POST", f"{ATTEMPTS}/{attempt['id']}/plant-groups", {"quantity": _count(3)}
    )
    path = f"/api/v1/plant-groups/{group['id']}"
    values = {
        "botanical_identity_id": cutting_identity,
        "label": "Three clones",
        "quantity": _count(3),
    }
    corrected = _write(browser, "PUT", path, values, 200)
    assert corrected["originating_propagation_attempt_id"] == attempt["id"]
    _write(browser, "PUT", path, {**values, "direct_origin_kind": "purchased"}, 409)


def test_self_collected_cuttings_appear_on_origin_map_and_retain_references(
    authenticated_browser: tuple[str, str],
    cutting_identity: str,
) -> None:
    browser = authenticated_browser
    site = _write(
        browser,
        "POST",
        "/api/v1/provenance-sites",
        {
            "name": "Cutting origin fixture",
            "latitude": 43.1,
            "longitude": 11.1,
        },
    )
    lot = _write(
        browser,
        "POST",
        LOTS,
        {
            "material_type": "root_cutting",
            "source_kind": "self_collected",
            "botanical_identity_id": cutting_identity,
            "provenance_site_id": site["id"],
        },
    )
    mapped = _read(browser, "/api/v1/provenance-sites/map")
    marker = next(item for item in mapped["sites"] if item["id"] == site["id"])
    assert marker["usage"]["vegetative_lots"] == 1
    assert [(row["record_type"], row["id"]) for row in marker["records"]] == [
        ("vegetative_lot", lot["id"])
    ]
    _write(browser, "DELETE", f"/api/v1/provenance-sites/{site['id']}", {}, 409)
    _write(browser, "DELETE", f"/api/v1/botanical-identities/{cutting_identity}", {}, 409)


def test_purchase_reference_and_saved_view_contracts(
    authenticated_browser: tuple[str, str],
    cutting_identity: str,
) -> None:
    browser = authenticated_browser
    original = _write(
        browser, "POST", "/api/v1/suppliers", {"name": "Cuttings Nursery", "kind": "seller"}
    )
    different = _write(
        browser, "POST", "/api/v1/suppliers", {"name": "Another Nursery", "kind": "seller"}
    )
    order = _write(browser, "POST", "/api/v1/orders", {"supplier_id": original["id"]})
    _write(
        browser,
        "POST",
        LOTS,
        {
            "material_type": "stem_cutting",
            "source_kind": "purchased",
            "botanical_identity_id": cutting_identity,
            "supplier_id": original["id"],
            "order_id": order["id"],
        },
    )
    order_path = f"/api/v1/orders/{order['id']}"
    _write(browser, "PATCH", order_path, {"supplier_id": different["id"]}, 409)
    _write(browser, "DELETE", order_path, {}, 409)

    state = {"record_type": "attempts", "lifecycle": "failed"}
    view = _write(
        browser,
        "POST",
        "/api/v1/saved-views",
        {
            "name": "Failed attempts",
            "surface": "cuttings",
            "state": state,
            "state_version": 1,
        },
    )
    assert view["state"] == state
    assert view["compatibility"] == "supported"


def test_identity_merge_repoints_cuttings_and_keeps_receipt_snapshots(
    authenticated_browser: tuple[str, str],
    cutting_identity: str,
) -> None:
    browser = authenticated_browser
    duplicate = _read(browser, f"/api/v1/botanical-identities/{cutting_identity}")
    survivor = _write(
        browser,
        "POST",
        "/api/v1/botanical-identities",
        {
            "scientific_name": "Salvia rosmarinus cultivar group",
        },
    )
    payload = _payload(cutting_identity)
    payload["source_adjustment"] = {"mode": "none"}
    operation = _write(browser, "POST", FAST, payload)
    lot_id = operation["vegetative_lot"]["id"]
    attempt_id = operation["propagation_attempt"]["id"]
    reverse_url = f"/api/v1/cutting-operations/{operation['operation_receipt_id']}/reversal"
    assert _read(browser, reverse_url)["status"] == "safe"

    reconciled = _write(
        browser,
        "POST",
        f"/api/v1/botanical-identities/{cutting_identity}/reconciliation/merge-duplicate",
        {
            "survivor_identity_id": survivor["id"],
            "duplicate_updated_at": duplicate["updated_at"],
            "survivor_updated_at": survivor["updated_at"],
        },
        200,
    )
    assert reconciled["reconciliations"][0]["evidence"]["repointed_records"][
        "vegetative_lot_ids"
    ] == [lot_id]
    counts = reconciled["identity"]["collection_counts"]
    assert counts["vegetative_lots"] == 1
    assert counts["propagation_attempts"] == 1
    attempt = _read(browser, f"{ATTEMPTS}/{attempt_id}")
    assert attempt["vegetative_lot"]["botanical_identity_id"] == survivor["id"]
    receipt = _read(browser, reverse_url)
    assert receipt["status"] == "blocked"
    assert "source_structural_state_changed" in {item["code"] for item in receipt["reasons"]}
    _write(browser, "POST", FAST, _payload(cutting_identity), 404)
