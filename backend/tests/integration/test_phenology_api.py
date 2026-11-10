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
from integration.test_seed_lot_api import ORIGIN, mutate, request

pytestmark = pytest.mark.integration


def _day(year: int, month: int, day: int) -> dict[str, object]:
    return {"precision": "day", "year": year, "month": month, "day": day}


def _month(year: int, month: int) -> dict[str, object]:
    return {"precision": "month", "year": year, "month": month, "day": None}


def _stage(phase: str, *, approximate: bool = False) -> dict[str, object]:
    return {"phase": phase, "date_is_approximate": approximate}


def _get(browser: tuple[str, str], path: str) -> Any:
    status, _, body = request("GET", path, headers={"cookie": browser[0]})
    assert status == 200
    return body


def _record(
    browser: tuple[str, str],
    events_path: str,
    kind: str,
    occurred_on: dict[str, object] | None,
    phase: str | None,
    *,
    approximate: bool = False,
) -> dict[str, Any]:
    status, _, body = mutate(
        browser,
        "POST",
        events_path,
        {
            "kind": kind,
            "occurred_on": occurred_on,
            "phenology": _stage(phase, approximate=approximate) if phase else None,
        },
    )
    assert status == 201, body
    return cast(dict[str, Any], body)


def test_seasonal_history_scenarios_keep_recorded_evidence_only(
    authenticated_browser: tuple[str, str],
    event_targets: dict[str, str],
    event_references: dict[str, str],
) -> None:
    plant_path = f"/api/v1/plants/{event_targets['plant']}"
    events_path = f"{plant_path}/events"
    before = _get(authenticated_browser, plant_path)

    # 1. Flowering in three successive years, the last only known to the month.
    # 3. Flowering twice in 2025 (a second autumn flush).
    # 4. An incomplete year-only date, an approximate recalled date and an undated observation.
    recorded = [
        _record(
            authenticated_browser, events_path, "flowering", _day(2024, 5, 20), "flowering_onset"
        ),
        _record(
            authenticated_browser, events_path, "flowering", _day(2025, 5, 14), "flowering_onset"
        ),
        _record(
            authenticated_browser, events_path, "flowering", _day(2025, 9, 2), "flowering_onset"
        ),
        _record(
            authenticated_browser, events_path, "flowering", _month(2026, 5), "flowering_onset"
        ),
        _record(authenticated_browser, events_path, "fruiting", _month(2024, 8), "fruit_ripening"),
        _record(
            authenticated_browser,
            events_path,
            "observation",
            _month(2023, 3),
            "bud_break",
            approximate=True,
        ),
        _record(
            authenticated_browser,
            events_path,
            "observation",
            {"precision": "year", "year": 2022},
            "leaf_fall",
        ),
        _record(authenticated_browser, events_path, "observation", None, "dormancy_entry"),
        # An existing-style flowering entry without a stage remains valid.
        _record(authenticated_browser, events_path, "flowering", _day(2023, 6, 1), None),
    ]
    listed = _get(authenticated_browser, events_path)
    # Each observation is one Journal Event; nothing is merged, inferred or duplicated.
    assert sorted(item["id"] for item in listed) == sorted(item["id"] for item in recorded)
    stages = [(item["kind"], item["occurred_on"], item["phenology"]) for item in listed]
    assert stages == [
        ("flowering", _month(2026, 5), _stage("flowering_onset")),
        ("flowering", _day(2025, 9, 2), _stage("flowering_onset")),
        ("flowering", _day(2025, 5, 14), _stage("flowering_onset")),
        ("fruiting", _month(2024, 8), _stage("fruit_ripening")),
        ("flowering", _day(2024, 5, 20), _stage("flowering_onset")),
        ("flowering", _day(2023, 6, 1), None),
        ("observation", _month(2023, 3), _stage("bud_break", approximate=True)),
        (
            "observation",
            {"precision": "year", "year": 2022, "month": None, "day": None},
            _stage("leaf_fall"),
        ),
        ("observation", None, _stage("dormancy_entry")),
    ]
    # 2. Flowering is recorded in 2025 but no fruiting: the API returns no fruiting Event.
    assert not [
        item
        for item in listed
        if item["kind"] == "fruiting" and item["occurred_on"]["year"] == 2025
    ]

    # Phenology never writes current state.
    after = _get(authenticated_browser, plant_path)
    for field in ("lifecycle", "location_id", "updated_at"):
        assert after[field] == before[field]

    # History shows the stage on the one existing Event row; no second source exists.
    status, history = _api_get("/api/v1/history?category=event&q=Stage", authenticated_browser[0])
    assert status == 200
    items = cast(list[dict[str, Any]], history["items"])
    assert len(items) == 8
    assert {item["key"] for item in items} <= {f"event:{item['id']}" for item in recorded}
    assert "Stage: Bud break / new growth (approximate date)" in {item["context"] for item in items}
    assert {item["title"] for item in items} == {"Flowering", "Fruiting", "Observation"}

    # 5. A BotanicalIdentity name correction changes only the label, never the observations.
    identity_path = f"/api/v1/botanical-identities/{event_references['identity']}"
    identity = _get(authenticated_browser, identity_path)
    cookie, csrf = authenticated_browser
    status, _, corrected = request(
        "POST",
        f"{identity_path}/reconciliation/correct-name",
        headers={"cookie": cookie, "origin": ORIGIN, "x-csrf-token": csrf},
        body={
            "scientific_name": "Eventus correctus",
            "source_provider": "operator",
            "identity_updated_at": identity["updated_at"],
        },
    )
    assert status == 200, corrected
    later = _record(
        authenticated_browser, events_path, "flowering", _day(2027, 5, 9), "flowering_onset"
    )
    renamed = _get(authenticated_browser, events_path)
    assert [item["id"] for item in renamed] == [later["id"], *[item["id"] for item in listed]]
    assert {item["target"]["botanical_identity"]["id"] for item in renamed} == {
        event_references["identity"]
    }
    assert {item["target"]["botanical_identity"]["display_label"] for item in renamed} == {
        "Eventus correctus"
    }
    assert [item["phenology"] for item in renamed[1:]] == [item["phenology"] for item in listed]


def test_duplicate_identity_merge_keeps_phenology_on_the_same_records(
    authenticated_browser: tuple[str, str],
    event_targets: dict[str, str],
    event_references: dict[str, str],
) -> None:
    cookie, csrf = authenticated_browser
    headers = {"cookie": cookie, "origin": ORIGIN, "x-csrf-token": csrf}
    plant_events = f"/api/v1/plants/{event_targets['plant']}/events"
    group_events = f"/api/v1/plant-groups/{event_targets['group']}/events"
    on_plant = _record(
        authenticated_browser, plant_events, "flowering", _day(2025, 5, 14), "flowering_onset"
    )
    on_group = _record(
        authenticated_browser, group_events, "fruiting", _month(2025, 8), "fruit_set"
    )
    status, _, survivor = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/botanical-identities",
        {"scientific_name": "Eventus acceptus"},
    )
    assert status == 201
    duplicate = _get(
        authenticated_browser, f"/api/v1/botanical-identities/{event_references['identity']}"
    )
    status, _, merged = request(
        "POST",
        f"/api/v1/botanical-identities/{duplicate['id']}/reconciliation/merge-duplicate",
        headers=headers,
        body={
            "survivor_identity_id": survivor["id"],
            "duplicate_updated_at": duplicate["updated_at"],
            "survivor_updated_at": survivor["updated_at"],
        },
    )
    assert status == 200, merged
    # The same Events, stages and dates now display the survivor's accepted name.
    for path, original in ((plant_events, on_plant), (group_events, on_group)):
        [after] = [
            item for item in _get(authenticated_browser, path) if item["id"] == original["id"]
        ]
        assert (after["phenology"], after["occurred_on"]) == (
            original["phenology"],
            original["occurred_on"],
        )
        assert after["target"]["botanical_identity"]["id"] == survivor["id"]


def test_phenology_correction_deletion_groups_inactive_and_measurements(
    authenticated_browser: tuple[str, str],
    event_targets: dict[str, str],
) -> None:
    plant_events = f"/api/v1/plants/{event_targets['plant']}/events"
    group_events = f"/api/v1/plant-groups/{event_targets['group']}/events"

    # A PlantGroup observation means the stage was seen in the group.
    group_flowering = _record(
        authenticated_browser, group_events, "flowering", _month(2025, 4), "flowering_ongoing"
    )
    assert group_flowering["target"]["type"] == "plant_group"
    assert group_flowering["phenology"] == _stage("flowering_ongoing")

    # Correction updates the same Event in place, including stage and approximation.
    first = _record(authenticated_browser, plant_events, "fruiting", _day(2025, 7, 1), "fruit_set")
    status, _, corrected = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/events/{first['id']}",
        {
            "kind": "fruiting",
            "occurred_on": _month(2025, 7),
            "phenology": _stage("fruit_ripe", approximate=True),
        },
    )
    assert status == 200
    assert (corrected["id"], corrected["phenology"]) == (
        first["id"],
        _stage("fruit_ripe", approximate=True),
    )
    assert corrected["updated_at"] > first["updated_at"]
    # A stage that does not belong to the kind is refused; changing kind clears the stage.
    refused = [
        (
            "PUT",
            f"/api/v1/events/{first['id']}",
            {"kind": "flowering", "phenology": _stage("fruit_ripe")},
        ),
        ("POST", plant_events, {"kind": "pruning", "phenology": _stage("bud_break")}),
        ("POST", plant_events, {"kind": "flowering", "phenology": {"phase": "blooming"}}),
        (
            "POST",
            plant_events,
            {"kind": "flowering", "phenology": _stage("flowering_end", approximate=True)},
        ),
    ]
    for method, path, body in refused:
        assert mutate(authenticated_browser, method, path, body)[0] == 422
    status, _, cleared = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/events/{first['id']}",
        {
            "kind": "observation",
            "occurred_on": _month(2025, 7),
            "notes": "Not phenology after all.",
        },
    )
    assert (status, cleared["phenology"]) == (200, None)
    assert mutate(authenticated_browser, "DELETE", f"/api/v1/events/{first['id']}")[0] == 204

    # Measurements coexist on the same Plant; neither payload leaks into the other.
    status, _, height = mutate(
        authenticated_browser,
        "POST",
        plant_events,
        {
            "kind": "measurement",
            "occurred_on": _day(2025, 6, 1),
            "measurement": {"quantity": "height", "value": "40", "unit": "cm"},
        },
    )
    assert (status, height["phenology"]) == (201, None)
    status, _, _ = mutate(
        authenticated_browser,
        "POST",
        plant_events,
        {
            "kind": "measurement",
            "occurred_on": _day(2025, 6, 1),
            "measurement": {"quantity": "height", "value": "40", "unit": "cm"},
            "phenology": _stage("bud_break"),
        },
    )
    assert status == 422

    # A dead Plant keeps its phenology and may still receive late-recorded observations.
    spring = _record(
        authenticated_browser, plant_events, "observation", _day(2025, 3, 2), "bud_break"
    )
    status, _, _ = mutate(
        authenticated_browser,
        "POST",
        plant_events,
        {"kind": "death", "occurred_on": _day(2025, 11, 1)},
    )
    assert status == 201
    assert (
        _get(authenticated_browser, f"/api/v1/plants/{event_targets['plant']}")["lifecycle"]
        == "dead"
    )
    late = _record(
        authenticated_browser, plant_events, "observation", _month(2025, 10), "leaf_color_change"
    )
    retained = {item["id"]: item["phenology"] for item in _get(authenticated_browser, plant_events)}
    assert retained[spring["id"]] == _stage("bud_break")
    assert retained[late["id"]] == _stage("leaf_color_change")

    # Unauthenticated and CSRF-less writes are refused.
    cookie, _ = authenticated_browser
    body = {"kind": "flowering", "phenology": _stage("flowering_onset")}
    assert request("GET", plant_events)[0] == 401
    assert request("POST", plant_events, body=body)[0] == 401
    assert (
        request("POST", plant_events, body=body, headers={"cookie": cookie, "origin": ORIGIN})[0]
        == 403
    )


def test_phenology_database_constraint(database_connection: Connection) -> None:
    plant_id = _plant(database_connection)
    now = datetime.now(UTC)

    def insert(**values: object) -> None:
        row: dict[str, object] = {
            "id": uuid7(),
            "plant_id": plant_id,
            "kind": "flowering",
            "occurred_on_precision": "month",
            "occurred_on_year": 2025,
            "occurred_on_month": 5,
            "phenophase": "flowering_onset",
            "phenophase_date_is_approximate": True,
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
    insert(kind="observation", phenophase="dormancy_exit")
    insert(kind="fruiting", phenophase="fruit_set", phenophase_date_is_approximate=False)
    insert(phenophase=None, phenophase_date_is_approximate=None)  # Stage-less flowering.
    insert(
        occurred_on_precision=None,
        occurred_on_year=None,
        occurred_on_month=None,
        phenophase_date_is_approximate=False,
    )
    for invalid in (
        {"phenophase": "fruit_set"},
        {"kind": "observation"},
        {"kind": "other", "phenophase": "bud_break"},
        {"phenophase": "blooming"},
        {"phenophase_date_is_approximate": None},
        {"phenophase": None},
        {"occurred_on_precision": None, "occurred_on_year": None, "occurred_on_month": None},
    ):
        with pytest.raises(DBAPIError), database_connection.begin_nested():
            insert(**invalid)


def test_phenology_migration_round_trip_refuses_downgrade_with_stages(
    database_engine: Engine,
) -> None:
    config = Config("alembic.ini")
    columns = {"phenophase", "phenophase_date_is_approximate"}
    try:
        command.downgrade(config, "20261109_0045")
        assert not columns & {c["name"] for c in inspect(database_engine).get_columns("events")}
        with database_engine.begin() as connection:
            # Populated pre-upgrade data: stage-less flowering stays valid after upgrade.
            plant_id = _plant(connection)
            now = datetime.now(UTC)
            connection.execute(
                text(
                    "INSERT INTO events (id, plant_id, kind, occurred_on_precision, "
                    "occurred_on_year, created_at, updated_at) "
                    "VALUES (:id, :plant, 'flowering', 'year', 2024, :now, :now)"
                ),
                {"id": uuid7(), "plant": plant_id, "now": now},
            )
        command.upgrade(config, "head")
        inspector = inspect(database_engine)
        assert columns <= {c["name"] for c in inspector.get_columns("events")}
        assert "ck_events_phenology" in {
            item["name"] for item in inspector.get_check_constraints("events")
        }
        with database_engine.begin() as connection:
            assert (
                connection.scalar(
                    text("SELECT count(*) FROM events WHERE plant_id = :id AND phenophase IS NULL"),
                    {"id": plant_id},
                )
                == 1
            )
            connection.execute(
                text(
                    "INSERT INTO events (id, plant_id, kind, phenophase, "
                    "phenophase_date_is_approximate, created_at, updated_at) "
                    "VALUES (:id, :plant, 'fruiting', 'fruit_set', false, :now, :now)"
                ),
                {"id": uuid7(), "plant": plant_id, "now": now},
            )
        with pytest.raises(RuntimeError, match="Phenology observations exist"):
            command.downgrade(config, "20261109_0045")
        with database_engine.begin() as connection:
            connection.execute(text("DELETE FROM events WHERE plant_id = :id"), {"id": plant_id})
            identity_id = connection.scalar(
                text("DELETE FROM plants WHERE id = :id RETURNING botanical_identity_id"),
                {"id": plant_id},
            )
            connection.execute(
                text("DELETE FROM botanical_identities WHERE id = :id"), {"id": identity_id}
            )
        command.downgrade(config, "20261109_0045")
    finally:
        command.upgrade(config, "head")
