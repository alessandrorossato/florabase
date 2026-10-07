from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch
from uuid import uuid7

import pytest
from sqlalchemy import Connection, event, func, select
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.bulk import service
from florabase.bulk.schemas import (
    BulkLocationApplyRequest,
    BulkLocationPreviewRequest,
    BulkReference,
)
from florabase.events.model import Event
from florabase.events.service import EventDomainConflictError, create_event
from florabase.harvests.inventory_model import HarvestMaterialInventory as Inventory
from florabase.harvests.inventory_service import list_inventory
from florabase.locations.model import Location
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing

from .test_attachment_api import authenticated_browser as authenticated_browser
from .test_attachment_api import request
from .test_harvest_inventory import setup as inventory_setup

pytestmark = pytest.mark.integration


@pytest.fixture
def db(database_connection: Connection) -> Iterator[Session]:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as session:
        yield session


def setup(db: Session) -> tuple[list[Any], Location, Location]:
    identity = BotanicalIdentity(scientific_name=f"Bulk species {uuid7().hex}")
    source = Location(name="Terrace", supports_harvest_inventory=True)
    target = Location(name="Greenhouse", supports_harvest_inventory=True)
    db.add_all([identity, source, target])
    db.flush()
    seed = SeedLot(botanical_identity_id=identity.id, label="Basil packet", location_id=source.id)
    plant = Plant(
        botanical_identity_id=identity.id,
        label="Basil plant",
        location_id=source.id,
        direct_origin_kind="unknown",
    )
    group = PlantGroup(
        botanical_identity_id=identity.id,
        label="Basil group",
        location_id=target.id,
        direct_origin_kind="unknown",
    )
    db.add_all([seed, plant, group])
    db.flush()
    sowing = Sowing(seed_lot_id=seed.id, label="Basil tray", location_id=source.id)
    db.add(sowing)
    inventory, _ = inventory_setup(db)
    inventory.location_id = source.id
    db.flush()
    return [seed, sowing, plant, group, inventory], source, target


def refs(rows: list[Any]) -> list[dict[str, str]]:
    kinds = {
        SeedLot: "seed_lot",
        Sowing: "sowing",
        Plant: "plant",
        PlantGroup: "plant_group",
        Inventory: "harvest_inventory",
    }
    return [{"kind": kinds[type(row)], "id": str(row.id)} for row in rows]


def apply_body(preview: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_location_id": preview["target_location_id"],
        "expected_target_updated_at": preview["target_updated_at"],
        "records": [
            {"kind": row["kind"], "id": row["id"], "expected_updated_at": row["updated_at"]}
            for row in preview["rows"]
        ],
    }


def test_real_mixed_transaction_history_projections_and_repeat(
    db: Session, authenticated_browser: tuple[str, str]
) -> None:
    rows, source, target = setup(db)
    untouched = SeedLot(botanical_identity_id=rows[0].botanical_identity_id, location_id=source.id)
    db.add(untouched)
    db.commit()
    before_events = db.scalar(select(func.count()).select_from(Event))
    assert before_events is not None
    payload = {"records": refs(rows), "target_location_id": str(target.id)}
    preview = request(
        "POST",
        "/api/v1/bulk/location/preview",
        browser=authenticated_browser,
        mutation_headers=True,
        body=payload,
    )
    assert preview.status_code == 200
    result = preview.json()
    assert (result["selected_count"], result["move_count"], result["unchanged_count"]) == (5, 4, 1)
    assert len(result["rows"]) == 5
    assert result["can_apply"]
    version = rows[4].correction_version
    applied = request(
        "POST",
        "/api/v1/bulk/location/apply",
        browser=authenticated_browser,
        mutation_headers=True,
        body=apply_body(result),
    )
    assert applied.status_code == 200
    assert applied.json() == {"moved_count": 4, "unchanged_count": 1}
    db.expire_all()
    assert all(row.location_id == target.id for row in rows)
    assert untouched.location_id == source.id
    assert rows[4].correction_version == version
    assert rows[4].state == "active"
    assert rows[4].quantity_value == 10
    assert db.scalar(select(func.count()).select_from(Event)) == before_events + 1
    movement = db.scalar(select(Event).where(Event.plant_id == rows[2].id))
    assert movement
    assert movement.kind == "movement"
    assert movement.destination_location_id == target.id
    assert movement.occurred_on_precision is None
    inventory = next(row for row in list_inventory(db) if row.id == rows[4].id)
    assert inventory.location
    assert inventory.location.id == target.id
    repeated = request(
        "POST",
        "/api/v1/bulk/location/apply",
        browser=authenticated_browser,
        mutation_headers=True,
        body=apply_body(result),
    )
    assert repeated.status_code == 409
    assert repeated.json()["detail"]["code"] == "stale_preview"
    assert db.scalar(select(func.count()).select_from(Event)) == before_events + 1


@pytest.mark.parametrize(
    "change",
    ["location", "notes", "state", "deleted", "target_deleted", "target_scope", "target_renamed"],
)
def test_stale_or_missing_selection_rolls_back_every_record(
    db: Session, authenticated_browser: tuple[str, str], change: str
) -> None:
    rows, source, target = setup(db)
    db.commit()
    preview = request(
        "POST",
        "/api/v1/bulk/location/preview",
        browser=authenticated_browser,
        mutation_headers=True,
        body={"records": refs([rows[0], rows[2]]), "target_location_id": str(target.id)},
    ).json()
    if change == "location":
        rows[2].location_id = None
    elif change == "notes":
        rows[2].notes = "Changed independently"
    elif change == "state":
        rows[2].lifecycle = "reversed"
    elif change == "deleted":
        db.delete(rows[2])
    elif change == "target_deleted":
        rows[3].location_id = source.id
        db.flush()
        db.delete(target)
    elif change == "target_scope":
        # Remove a scope with no current assignment to target.
        target.supports_seed_lots = False
    else:
        target.name = "Renamed greenhouse"
    db.commit()
    applied = request(
        "POST",
        "/api/v1/bulk/location/apply",
        browser=authenticated_browser,
        mutation_headers=True,
        body=apply_body(preview),
    )
    assert applied.status_code in {404, 409}
    db.expire_all()
    assert rows[0].location_id == source.id
    assert (
        db.scalar(select(func.count()).select_from(Event).where(Event.plant_id == rows[2].id)) == 0
    )


def test_rollback_includes_previously_created_movement_event(
    db: Session, authenticated_browser: tuple[str, str]
) -> None:
    rows, source, target = setup(db)
    rows[3].location_id = source.id
    db.commit()
    preview = request(
        "POST",
        "/api/v1/bulk/location/preview",
        browser=authenticated_browser,
        mutation_headers=True,
        body={"records": refs([rows[2], rows[3]]), "target_location_id": str(target.id)},
    ).json()
    create = create_event
    calls = 0

    def conflict(*args: Any, **kwargs: Any) -> Event:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise EventDomainConflictError("test_domain_conflict", "A domain conflict occurred")
        return create(*args, **kwargs)

    with patch.object(service, "create_event", side_effect=conflict):
        applied = request(
            "POST",
            "/api/v1/bulk/location/apply",
            browser=authenticated_browser,
            mutation_headers=True,
            body=apply_body(preview),
        )
    assert applied.status_code == 409
    db.expire_all()
    assert rows[2].location_id == rows[3].location_id == source.id
    assert (
        db.scalar(select(func.count()).select_from(Event).where(Event.plant_id == rows[2].id)) == 0
    )


@pytest.mark.parametrize("kind", list(service.MODELS))
def test_each_supported_domain_multiple_locations_and_noop(db: Session, kind: str) -> None:
    rows, _source, target = setup(db)
    row = next(
        row
        for row in rows
        if isinstance(
            row,
            service.MODELS[BulkReference.model_validate({"kind": kind, "id": uuid7()}).kind],
        )
    )
    row.location_id = None
    db.flush()
    preview = service.preview(
        db,
        BulkLocationPreviewRequest.model_validate(
            {"records": refs([row]), "target_location_id": target.id}
        ),
    )
    assert preview.move_count == 1
    body = apply_body(preview.model_dump(mode="json"))
    service.apply(db, BulkLocationApplyRequest.model_validate(body))
    assert row.location_id == target.id
    if kind in {"plant", "plant_group"}:
        column = Event.plant_id if kind == "plant" else Event.plant_group_id
        assert (
            db.scalar(
                select(func.count())
                .select_from(Event)
                .where(column == row.id, Event.kind == "movement")
            )
            == 1
        )
    fresh = service.preview(
        db,
        BulkLocationPreviewRequest.model_validate(
            {"records": refs([row]), "target_location_id": target.id}
        ),
    )
    assert fresh.unchanged_count == 1
    assert not fresh.can_apply
    with pytest.raises(service.BulkConflictError, match="all_unchanged"):
        service.apply(
            db, BulkLocationApplyRequest.model_validate(apply_body(fresh.model_dump(mode="json")))
        )


def test_bounded_grouped_queries_for_100_seeds(db: Session) -> None:
    rows, source, target = setup(db)
    seeds = [
        SeedLot(
            botanical_identity_id=rows[0].botanical_identity_id,
            label=f"Packet {number}",
            location_id=source.id,
        )
        for number in range(100)
    ]
    db.add_all(seeds)
    db.flush()
    queries: list[str] = []
    connection = db.connection()

    def record(_connection: Any, _cursor: Any, statement: str, *_args: Any) -> None:
        queries.append(statement)

    event.listen(connection, "before_cursor_execute", record)
    try:
        preview = service.preview(
            db,
            BulkLocationPreviewRequest.model_validate(
                {"records": refs(seeds), "target_location_id": target.id}
            ),
        )
        assert preview.move_count == 100
        assert len(queries) == 3
        queries.clear()
        service.apply(
            db, BulkLocationApplyRequest.model_validate(apply_body(preview.model_dump(mode="json")))
        )
        assert len(queries) <= 7
    finally:
        event.remove(connection, "before_cursor_execute", record)


@pytest.mark.parametrize("path", ["preview", "apply"])
def test_bulk_auth_origin_csrf_and_typed_validation(
    db: Session, authenticated_browser: tuple[str, str], path: str
) -> None:
    rows, _source, target = setup(db)
    db.commit()
    preview = request(
        "POST",
        "/api/v1/bulk/location/preview",
        browser=authenticated_browser,
        mutation_headers=True,
        body={"records": refs([rows[0]]), "target_location_id": str(target.id)},
    ).json()
    payload = (
        apply_body(preview)
        if path == "apply"
        else {"records": refs([rows[0]]), "target_location_id": str(target.id)}
    )
    endpoint = f"/api/v1/bulk/location/{path}"
    assert request("POST", endpoint, body=payload).status_code == 401
    assert request("POST", endpoint, browser=authenticated_browser, body=payload).status_code == 403
    assert (
        request(
            "POST",
            endpoint,
            browser=authenticated_browser,
            request_headers={"Origin": "http://foreign", "X-CSRF-Token": authenticated_browser[1]},
            body=payload,
        ).status_code
        == 403
    )
    assert (
        request(
            "POST",
            endpoint,
            browser=authenticated_browser,
            mutation_headers=True,
            body=payload | {"action": "delete"},
        ).status_code
        == 422
    )
    malformed = dict(payload, records=[{"kind": "harvest", "id": str(uuid7())}])
    assert (
        request(
            "POST", endpoint, browser=authenticated_browser, mutation_headers=True, body=malformed
        ).status_code
        == 422
    )


def test_preview_reports_every_missing_and_ineligible_reference(db: Session) -> None:
    rows, _source, target = setup(db)
    rows[0].lifecycle = "exhausted"
    db.flush()
    preview = service.preview(
        db,
        BulkLocationPreviewRequest.model_validate(
            {
                "records": [*refs([rows[0]]), {"kind": "plant", "id": str(uuid7())}],
                "target_location_id": target.id,
            }
        ),
    )
    assert [row.code for row in preview.rows] == ["record_not_active", "record_not_found"]
    assert not preview.can_apply


def test_apply_timestamp_precondition_uses_persisted_state(db: Session) -> None:
    rows, _source, target = setup(db)
    preview = service.preview(
        db,
        BulkLocationPreviewRequest.model_validate(
            {"records": refs([rows[0]]), "target_location_id": target.id}
        ),
    )
    body = apply_body(preview.model_dump(mode="json"))
    body["records"][0]["expected_updated_at"] = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    with pytest.raises(service.BulkConflictError, match="stale_preview"):
        service.apply(db, BulkLocationApplyRequest.model_validate(body))
    assert rows[0].location_id != target.id
