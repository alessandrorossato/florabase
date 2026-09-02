from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid7

import pytest
from sqlalchemy import Connection, Engine, delete, func, select
from sqlalchemy.orm import Session

from florabase.auth.service import bootstrap_owner
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.core.config import get_settings
from florabase.db.session import get_database_session
from florabase.events.model import Event
from florabase.events.schemas import EventCreate
from florabase.events.service import create_event
from florabase.locations.model import Location
from florabase.main import app
from florabase.plants.model import Plant
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
def event_references(database_connection: Connection) -> dict[str, str]:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        identity = BotanicalIdentity(scientific_name="Eventus journalis")
        existing_location = Location(name="Old bench")
        database.add_all([identity, existing_location])
        database.commit()
        return {"identity": str(identity.id), "existing_location": str(existing_location.id)}


@pytest.fixture
def event_targets(
    authenticated_browser: tuple[str, str],
    event_references: dict[str, str],
    database_connection: Connection,
) -> Iterator[dict[str, str]]:
    _, _, plant = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/plants",
        {"botanical_identity_id": event_references["identity"]},
    )
    _, _, group = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/plant-groups",
        {"botanical_identity_id": event_references["identity"]},
    )
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        destination = Location(name="Greenhouse")
        second_destination = Location(name="Propagation room")
        database.add_all([destination, second_destination])
        database.commit()
        yield {
            "plant": plant["id"],
            "group": group["id"],
            "destination": str(destination.id),
            "second_destination": str(second_destination.id),
        }


def test_event_partial_dates_listing_targets_and_optional_notes(
    authenticated_browser: tuple[str, str], event_targets: dict[str, str]
) -> None:
    path = f"/api/v1/plants/{event_targets['plant']}/events"
    payloads: list[dict[str, object]] = [
        {"kind": "observation"},
        {"kind": "flowering", "occurred_on": {"precision": "year", "year": 2024}},
        {
            "kind": "fruiting",
            "occurred_on": {"precision": "month", "year": 2024, "month": 5},
        },
        {
            "kind": "harvest",
            "occurred_on": {"precision": "day", "year": 2024, "month": 5, "day": 18},
            "notes": " First.\r\nSecond. ",
        },
    ]
    created = [mutate(authenticated_browser, "POST", path, payload)[2] for payload in payloads]
    assert UUID(created[0]["id"]).version == 7
    assert created[0]["target"] == {
        "type": "plant",
        "id": event_targets["plant"],
        "label": None,
        "lifecycle": "active",
    }
    assert created[-1]["notes"] == "First.\nSecond."
    cookie, _ = authenticated_browser
    status_code, _, listed = request("GET", path, headers={"cookie": cookie})
    assert status_code == 200
    assert [item["kind"] for item in listed] == ["harvest", "fruiting", "flowering", "observation"]
    assert (
        request("GET", f"/api/v1/events/{created[-1]['id']}", headers={"cookie": cookie})[2]
        == created[-1]
    )


def test_movement_creation_is_atomic_and_put_delete_never_reapply_or_reverse(
    authenticated_browser: tuple[str, str], event_targets: dict[str, str]
) -> None:
    plant_path = f"/api/v1/plants/{event_targets['plant']}"
    event_path = f"{plant_path}/events"
    status_code, headers, movement = mutate(
        authenticated_browser,
        "POST",
        event_path,
        {"kind": "movement", "destination_location_id": event_targets["destination"]},
    )
    assert status_code == 201
    assert headers["location"].endswith(movement["id"])
    assert movement["destination_location"]["display_path"] == "Greenhouse"
    cookie, _ = authenticated_browser
    assert (
        request("GET", plant_path, headers={"cookie": cookie})[2]["location_id"]
        == event_targets["destination"]
    )

    status_code, _, corrected = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/events/{movement['id']}",
        {
            "kind": "movement",
            "destination_location_id": event_targets["second_destination"],
            "notes": "Historical correction",
        },
    )
    assert status_code == 200
    assert corrected["destination_location_id"] == event_targets["second_destination"]
    assert (
        request("GET", plant_path, headers={"cookie": cookie})[2]["location_id"]
        == event_targets["destination"]
    )
    assert mutate(authenticated_browser, "DELETE", f"/api/v1/events/{movement['id']}")[0] == 204
    assert (
        request("GET", plant_path, headers={"cookie": cookie})[2]["location_id"]
        == event_targets["destination"]
    )
    assert request("GET", f"/api/v1/events/{movement['id']}", headers={"cookie": cookie})[0] == 404


@pytest.mark.parametrize(
    ("target_key", "route", "kind", "expected"),
    [
        ("plant", "plants", "death", "dead"),
        ("plant", "plants", "loss", "lost"),
        ("plant", "plants", "discarded", "discarded"),
        ("group", "plant-groups", "death", "dead"),
        ("group", "plant-groups", "loss", "lost"),
        ("group", "plant-groups", "discarded", "discarded"),
    ],
)
def test_lifecycle_creation_effects_apply_to_both_targets(
    authenticated_browser: tuple[str, str],
    event_targets: dict[str, str],
    target_key: str,
    route: str,
    kind: str,
    expected: str,
) -> None:
    target_id = event_targets[target_key]
    status_code, _, event = mutate(
        authenticated_browser, "POST", f"/api/v1/{route}/{target_id}/events", {"kind": kind}
    )
    assert status_code == 201
    assert event["target"]["lifecycle"] == expected
    cookie, _ = authenticated_browser
    assert (
        request("GET", f"/api/v1/{route}/{target_id}", headers={"cookie": cookie})[2]["lifecycle"]
        == expected
    )


def test_lifecycle_event_put_and_delete_do_not_reverse_or_apply_new_state(
    authenticated_browser: tuple[str, str], event_targets: dict[str, str]
) -> None:
    target_path = f"/api/v1/plant-groups/{event_targets['group']}"
    _, _, event = mutate(authenticated_browser, "POST", f"{target_path}/events", {"kind": "death"})
    _, _, corrected = mutate(
        authenticated_browser, "PUT", f"/api/v1/events/{event['id']}", {"kind": "observation"}
    )
    assert corrected["kind"] == "observation"
    cookie, _ = authenticated_browser
    assert request("GET", target_path, headers={"cookie": cookie})[2]["lifecycle"] == "dead"
    mutate(authenticated_browser, "DELETE", f"/api/v1/events/{event['id']}")
    assert request("GET", target_path, headers={"cookie": cookie})[2]["lifecycle"] == "dead"

    _, _, ordinary = mutate(
        authenticated_browser, "POST", f"{target_path}/events", {"kind": "observation"}
    )
    mutate(authenticated_browser, "PUT", f"/api/v1/events/{ordinary['id']}", {"kind": "loss"})
    assert request("GET", target_path, headers={"cookie": cookie})[2]["lifecycle"] == "dead"


def test_event_security_validation_missing_references_and_rollback(
    authenticated_browser: tuple[str, str],
    event_references: dict[str, str],
    event_targets: dict[str, str],
    database_connection: Connection,
) -> None:
    path = f"/api/v1/plants/{event_targets['plant']}/events"
    cookie, csrf = authenticated_browser
    assert request("GET", path)[0] == 401
    assert request("POST", path, body={"kind": "observation"})[0] == 401
    assert (
        request(
            "POST", path, body={"kind": "observation"}, headers={"cookie": cookie, "origin": ORIGIN}
        )[0]
        == 403
    )
    assert (
        request(
            "POST",
            path,
            body={"kind": "observation"},
            headers={"cookie": cookie, "origin": "https://evil.example", "x-csrf-token": csrf},
        )[0]
        == 403
    )
    assert mutate(authenticated_browser, "POST", path, {"kind": "movement"})[0] == 422
    assert (
        mutate(
            authenticated_browser,
            "POST",
            path,
            {"kind": "movement", "destination_location_id": str(uuid7())},
        )[0]
        == 404
    )
    assert (
        mutate(
            authenticated_browser,
            "POST",
            f"/api/v1/plants/{uuid7()}/events",
            {"kind": "observation"},
        )[0]
        == 404
    )
    assert request("GET", f"/api/v1/events/{uuid7()}", headers={"cookie": cookie})[0] == 404
    assert (
        mutate(authenticated_browser, "PUT", f"/api/v1/events/{uuid7()}", {"kind": "other"})[0]
        == 404
    )
    assert mutate(authenticated_browser, "DELETE", f"/api/v1/events/{uuid7()}")[0] == 404

    _, _, exact_zero_group = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/plant-groups",
        {
            "botanical_identity_id": event_references["identity"],
            "quantity": {"value": 0, "is_approximate": False},
            "lifecycle": "completed",
        },
    )
    failed_path = f"/api/v1/plant-groups/{exact_zero_group['id']}/events"
    assert mutate(authenticated_browser, "POST", failed_path, {"kind": "loss"})[0] == 409
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        assert (
            database.scalar(
                select(func.count())
                .select_from(Event)
                .where(Event.plant_group_id == UUID(exact_zero_group["id"]))
            )
            == 0
        )


def test_concurrent_state_changing_creation_serializes_and_retains_both_events(
    database_engine: Engine,
) -> None:
    identity_id = uuid7()
    plant_id = uuid7()
    location_ids = (uuid7(), uuid7())
    with Session(database_engine) as database:
        database.add(
            BotanicalIdentity(id=identity_id, scientific_name=f"Concurrent {identity_id.hex}")
        )
        database.add_all(
            [
                Location(id=location_ids[0], name="Concurrent A"),
                Location(id=location_ids[1], name="Concurrent B"),
            ]
        )
        database.add(
            Plant(id=plant_id, botanical_identity_id=identity_id, direct_origin_kind="unknown")
        )
        database.commit()
    barrier = Barrier(2)

    def move(location_id: UUID) -> None:
        with Session(database_engine) as database:
            barrier.wait()
            create_event(
                database,
                "plant",
                plant_id,
                EventCreate(kind="movement", destination_location_id=location_id),
            )
            database.commit()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(move, location_ids))
        with Session(database_engine) as database:
            plant = database.get(Plant, plant_id)
            assert plant is not None
            assert plant.location_id in location_ids
            assert (
                database.scalar(
                    select(func.count()).select_from(Event).where(Event.plant_id == plant_id)
                )
                == 2
            )
    finally:
        with Session(database_engine) as database:
            database.execute(delete(Event).where(Event.plant_id == plant_id))
            database.execute(delete(Plant).where(Plant.id == plant_id))
            database.execute(delete(Location).where(Location.id.in_(location_ids)))
            database.execute(delete(BotanicalIdentity).where(BotanicalIdentity.id == identity_id))
            database.commit()
