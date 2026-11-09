from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Connection, Engine, inspect, text
from sqlalchemy.exc import DBAPIError

from alembic import command
from integration.test_event_api import (
    authenticated_browser as authenticated_browser,
)
from integration.test_event_api import (
    event_references as event_references,
)
from integration.test_event_api import (
    event_targets as event_targets,
)
from integration.test_event_migration import _plant
from integration.test_search import _api_get
from integration.test_seed_lot_api import mutate, request

pytestmark = pytest.mark.integration

MARCH = {"precision": "day", "year": 2026, "month": 3, "day": 14}
JUNE = {"precision": "month", "year": 2026, "month": 6}


def _height(value: str, unit: str = "cm", *, approximate: bool = False) -> dict[str, object]:
    return {"quantity": "height", "value": value, "unit": unit, "is_approximate": approximate}


def _get(browser: tuple[str, str], path: str) -> Any:
    status, _, body = request("GET", path, headers={"cookie": browser[0]})
    assert status == 200
    return body


def test_height_history_correction_and_invalid_measurements(
    authenticated_browser: tuple[str, str],
    event_targets: dict[str, str],
) -> None:
    plant_path = f"/api/v1/plants/{event_targets['plant']}"
    before = _get(authenticated_browser, plant_path)

    # Two measurements on different dates, one only known to the month and estimated.
    status, _, first = mutate(
        authenticated_browser,
        "POST",
        f"{plant_path}/events",
        {"kind": "measurement", "occurred_on": MARCH, "measurement": _height("12.50")},
    )
    assert status == 201
    assert first["measurement"] == _height("12.50")
    status, _, second = mutate(
        authenticated_browser,
        "POST",
        f"{plant_path}/events",
        {
            "kind": "measurement",
            "occurred_on": JUNE,
            "notes": "Eyeballed against the stake.",
            "measurement": _height("0.3", "m", approximate=True),
        },
    )
    assert status == 201
    listed = _get(authenticated_browser, f"{plant_path}/events")
    assert [(item["id"], item["occurred_on"], item["measurement"]) for item in listed] == [
        (second["id"], JUNE | {"day": None}, _height("0.3", "m", approximate=True)),
        (first["id"], MARCH, _height("12.50")),
    ]

    # Correction rewrites the same Event; resolution and unit are what was recorded.
    status, _, corrected = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/events/{first['id']}",
        {"kind": "measurement", "occurred_on": MARCH, "measurement": _height("125", "mm")},
    )
    assert status == 200
    assert corrected["id"] == first["id"]
    assert corrected["measurement"] == _height("125", "mm")
    assert corrected["updated_at"] > first["updated_at"]

    status, history = _api_get("/api/v1/history?category=event&q=Height", authenticated_browser[0])
    assert status == 200
    items = cast(list[dict[str, str]], history["items"])
    assert sorted(item["context"] for item in items) == [
        "Height: 0.3 m (approximate)",
        "Height: 125 mm",
    ]
    assert {item["title"] for item in items} == {"Measurement"}

    # Invalid measurements are refused without writing.
    group_events = f"/api/v1/plant-groups/{event_targets['group']}/events"
    refused: list[tuple[str, str, dict[str, object], int]] = [
        ("POST", f"{plant_path}/events", {"kind": "measurement", "measurement": _height("4")}, 422),
        (
            "POST",
            f"{plant_path}/events",
            {"kind": "measurement", "occurred_on": MARCH, "measurement": _height("4", "kg")},
            422,
        ),
        (
            "POST",
            f"{plant_path}/events",
            {"kind": "measurement", "occurred_on": MARCH, "measurement": _height("-4")},
            422,
        ),
        (
            "POST",
            group_events,
            {"kind": "measurement", "occurred_on": MARCH, "measurement": _height("4")},
            409,
        ),
    ]
    for method, path, body, expected in refused:
        assert mutate(authenticated_browser, method, path, body)[0] == expected
    _, _, group_note = mutate(authenticated_browser, "POST", group_events, {"kind": "observation"})
    status, _, conflict = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/events/{group_note['id']}",
        {"kind": "measurement", "occurred_on": MARCH, "measurement": _height("4")},
    )
    assert (status, conflict["detail"]["code"]) == (409, "measurement_requires_plant")
    assert len(_get(authenticated_browser, f"{plant_path}/events")) == 2

    # Measurements never write current Plant state.
    after = _get(authenticated_browser, plant_path)
    for field in ("lifecycle", "location_id", "updated_at"):
        assert after[field] == before[field]

    # Changing the kind away from measurement clears the payload.
    status, _, note = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/events/{second['id']}",
        {"kind": "observation", "occurred_on": JUNE},
    )
    assert (status, note["measurement"]) == (200, None)


def test_measurement_database_constraint_is_all_or_nothing(
    database_connection: Connection,
) -> None:
    plant_id = _plant(database_connection)
    now = datetime.now(UTC)
    group_id = uuid7()
    database_connection.execute(
        text(
            "INSERT INTO plant_groups (id, botanical_identity_id, direct_origin_kind, "
            "created_at, updated_at) SELECT :id, botanical_identity_id, 'unknown', :now, :now "
            "FROM plants WHERE id = :plant"
        ),
        {"id": group_id, "plant": plant_id, "now": now},
    )
    insert_valid_bound = {"measurement_value": "200", "measurement_unit": "m"}

    def insert(**values: object) -> None:
        row: dict[str, object] = {
            "id": uuid7(),
            "plant_id": plant_id,
            "kind": "measurement",
            "occurred_on_precision": "year",
            "occurred_on_year": 2026,
            "measurement_quantity": "height",
            "measurement_value": "12.50",
            "measurement_unit": "cm",
            "measurement_is_approximate": False,
            "created_at": now,
            "updated_at": now,
            **values,
        }
        row = {key: value for key, value in row.items() if value is not None}
        database_connection.execute(
            text(
                f"INSERT INTO events ({', '.join(row)}) "
                f"VALUES ({', '.join(f':{key}' for key in row)})"
            ),
            row,
        )

    insert()
    insert(**insert_valid_bound)
    assert (
        database_connection.scalar(
            text(
                "SELECT measurement_value::text FROM events "
                "WHERE plant_id = :id AND measurement_unit = 'cm'"
            ),
            {"id": plant_id},
        )
        == "12.50"
    )
    for invalid in (
        {"measurement_unit": "g"},
        {"measurement_quantity": "weight"},
        {"measurement_value": "0"},
        {"measurement_value": "1.2345"},
        {"occurred_on_precision": None, "occurred_on_year": None},
        {"measurement_is_approximate": None},
        {"kind": "observation"},
        {"measurement_value": None},
        {"measurement_value": "200.001", "measurement_unit": "m"},
        {"plant_id": None, "plant_group_id": group_id},
    ):
        with pytest.raises(DBAPIError), database_connection.begin_nested():
            insert(**invalid)


def test_measurement_migration_round_trip_refuses_downgrade_with_measurements(
    database_engine: Engine,
) -> None:
    config = Config("alembic.ini")
    columns = {
        "measurement_quantity",
        "measurement_value",
        "measurement_unit",
        "measurement_is_approximate",
    }
    try:
        command.downgrade(config, "20261013_0042")
        assert not columns & {c["name"] for c in inspect(database_engine).get_columns("events")}
        command.upgrade(config, "head")
        inspector = inspect(database_engine)
        assert columns <= {c["name"] for c in inspector.get_columns("events")}
        assert "ck_events_measurement" in {
            item["name"] for item in inspector.get_check_constraints("events")
        }
        with database_engine.begin() as connection:
            plant_id = _plant(connection)
            now = datetime.now(UTC)
            connection.execute(
                text(
                    "INSERT INTO events (id, plant_id, kind, occurred_on_precision, "
                    "occurred_on_year, measurement_quantity, measurement_value, measurement_unit, "
                    "measurement_is_approximate, created_at, updated_at) VALUES (:id, :plant, "
                    "'measurement', 'year', 2026, 'height', 12, 'cm', false, :now, :now)"
                ),
                {"id": uuid7(), "plant": plant_id, "now": now},
            )
        with pytest.raises(RuntimeError, match="Measurement Events exist"):
            command.downgrade(config, "20261013_0042")
        with database_engine.begin() as connection:
            connection.execute(text("DELETE FROM events WHERE kind = 'measurement'"))
            identity_id = connection.scalar(
                text("DELETE FROM plants WHERE id = :id RETURNING botanical_identity_id"),
                {"id": plant_id},
            )
            connection.execute(
                text("DELETE FROM botanical_identities WHERE id = :id"), {"id": identity_id}
            )
        command.downgrade(config, "20261013_0042")
    finally:
        command.upgrade(config, "head")
