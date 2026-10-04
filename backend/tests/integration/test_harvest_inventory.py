from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Event as ThreadEvent
from time import monotonic
from typing import cast
from uuid import uuid7

import pytest
from sqlalchemy import Connection, Engine, delete, event, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.events.model import Event
from florabase.events.service import EventDomainConflictError
from florabase.harvests.inventory_model import HarvestMaterialInventory as Inventory
from florabase.harvests.inventory_schemas import DispositionCreate, InventoryWrite
from florabase.harvests.inventory_service import (
    correct,
    history,
    list_inventory,
    record_disposition,
    remove_tracking,
    track,
)
from florabase.harvests.schemas import HarvestQuantity, HarvestWrite
from florabase.harvests.service import delete_harvest, read_harvest, write_harvest
from florabase.locations.model import Location
from florabase.locations.schemas import LocationCreate, LocationUpdate
from florabase.locations.service import (
    create_location,
    delete_location,
    location_usage_aggregation,
    update_location,
)
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot

from .test_attachment_api import authenticated_browser as browser_fixture
from .test_attachment_api import request
from .test_harvests import data, enforce


def q(
    value: str = "10",
    *,
    approximate: bool = False,
    kind: str = "item_count",
    unit: str | None = None,
) -> HarvestQuantity:
    return HarvestQuantity.model_validate(
        {"kind": kind, "value": value, "unit": unit, "is_approximate": approximate}
    )


inventory_browser = browser_fixture
pytestmark = pytest.mark.integration


def setup(
    db: Session, *, approximate: bool = False, unknown: bool = False, group: bool = False
) -> tuple[Inventory, HarvestWrite]:
    identity = BotanicalIdentity(scientific_name=f"Stock species {uuid7().hex}")
    source_location = Location(name="Source bench")
    db.add_all([identity, source_location])
    db.flush()
    plant = Plant(
        botanical_identity_id=identity.id,
        direct_origin_kind="unknown",
        lifecycle="dead",
        location_id=source_location.id,
    )
    plants = PlantGroup(
        botanical_identity_id=identity.id,
        direct_origin_kind="unknown",
        lifecycle="active",
        quantity_value=12,
        quantity_is_approximate=True,
        location_id=source_location.id,
    )
    db.add_all([plant, plants])
    db.flush()
    payload = data(
        plants if group else plant,
        items=[
            {
                "material_kind": "seed",
                "quantity": None if unknown else q("10", approximate=approximate).model_dump(),
            }
        ],
    )
    harvest = write_harvest(db, payload)
    item = read_harvest(db, harvest.id).items[0]
    inventory = track(
        db,
        item.id,
        InventoryWrite(
            state="active", quantity=None if unknown else q("10", approximate=approximate)
        ),
    )
    return inventory, payload.model_copy(
        update={"items": [payload.items[0].model_copy(update={"id": item.id})]}
    )


@pytest.mark.parametrize("group", [False, True])
def test_tracking_dispositions_corrections_and_source_isolation(
    database_connection: Connection, group: bool
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        before_events = db.scalar(select(func.count()).select_from(Event))
        before_seeds = list(db.scalars(select(SeedLot.id)))
        inventory, payload = setup(db, group=group)
        response = list_inventory(db)[0]
        assert response.material_kind == "seed"
        assert not response.has_dispositions
        source_state = response.source.lifecycle
        record_disposition(
            db,
            inventory.id,
            DispositionCreate(
                kind="consumed",
                mode="partial",
                quantity=q("7"),
                occurred_on={"precision": "year", "year": 2026},
            ),
        )
        assert inventory.quantity_value == 3
        before_history = [row.model_dump() for row in history(db, inventory.id)]
        correct(db, inventory.id, InventoryWrite(state="active", quantity=q("9", approximate=True)))
        source = cast(
            Plant | PlantGroup, db.get(PlantGroup if group else Plant, response.source.id)
        )
        assert source is not None
        other = cast(
            Plant | PlantGroup,
            db.scalar(
                select(Plant if group else PlantGroup).where(
                    (Plant if group else PlantGroup).botanical_identity_id
                    == source.botanical_identity_id
                )
            ),
        )
        assert other is not None
        other_state = other.lifecycle
        write_harvest(
            db,
            payload.model_copy(
                update={
                    "notes": "Corrected historical notes",
                    "plant_id": other.id if group else None,
                    "plant_group_id": None if group else other.id,
                    "items": [payload.items[0].model_copy(update={"quantity": q("2")})],
                }
            ),
            response.harvest_id,
        )
        assert inventory.quantity_value == 9
        assert [row.model_dump() for row in history(db, inventory.id)] == before_history
        assert read_harvest(db, response.harvest_id).items[0].quantity == q("2")
        record_disposition(
            db, inventory.id, DispositionCreate(kind="used_for_propagation", mode="use_all")
        )
        assert inventory.state == "depleted"
        assert inventory.quantity_value is None
        with pytest.raises(EventDomainConflictError, match="Depleted"):
            record_disposition(
                db, inventory.id, DispositionCreate(kind="discarded", mode="use_all")
            )
        with pytest.raises(EventDomainConflictError, match="retained"):
            remove_tracking(db, inventory.id)
        assert source.lifecycle == source_state
        assert other.lifecycle == other_state
        assert list_inventory(db)[0].source.id == other.id
        with pytest.raises(IntegrityError), db.begin_nested():
            db.execute(
                text(
                    "UPDATE harvest_material_dispositions SET notes='tampered' "
                    "WHERE inventory_id=:id"
                ),
                {"id": inventory.id},
            )
        assert db.scalar(select(func.count()).select_from(Event)) == before_events + 1
        assert list(db.scalars(select(SeedLot.id))) == before_seeds
        assert len(history(db, inventory.id)) == 2
        enforce(db)


@pytest.mark.parametrize("unknown", [False, True])
def test_estimate_and_unknown_history(database_connection: Connection, unknown: bool) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        inventory, _ = setup(db, approximate=True, unknown=unknown)
        confirmed = None if unknown else q("6", approximate=True)
        record_disposition(
            db,
            inventory.id,
            DispositionCreate(
                kind="processed", mode="partial", quantity=q("2"), resulting_quantity=confirmed
            ),
        )
        assert (inventory.quantity_value, inventory.quantity_is_approximate) == (
            (None, None) if unknown else (6, True)
        )
        record_disposition(db, inventory.id, DispositionCreate(kind="gifted", mode="use_all"))
        assert inventory.state == "depleted"
        snapshots = history(db, inventory.id)
        assert snapshots[0].before.quantity == confirmed
        assert snapshots[0].quantity == confirmed
        enforce(db)


def test_unique_initial_compatibility_removal_and_harvest_guards(
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        inventory, payload = setup(db)
        item_id = inventory.harvest_item_id
        harvest_id = list_inventory(db)[0].harvest_id
        with pytest.raises(EventDomainConflictError, match="already tracked"):
            track(db, item_id, InventoryWrite(state="active", quantity=q("2")))
        with pytest.raises(EventDomainConflictError):
            delete_harvest(db, harvest_id)
        for items in [[{"material_kind": "root"}], [{"id": item_id, "material_kind": "root"}]]:
            with pytest.raises(EventDomainConflictError):
                write_harvest(
                    db,
                    HarvestWrite.model_validate({**payload.model_dump(), "items": items}),
                    harvest_id,
                )
        remove_tracking(db, inventory.id)
        for current in [q("11"), q("2", kind="weight", unit="g")]:
            with pytest.raises(EventDomainConflictError):
                track(db, item_id, InventoryWrite(state="active", quantity=current))
        tracked = track(db, item_id, InventoryWrite(state="active", quantity=None))
        remove_tracking(db, tracked.id)
        delete_harvest(db, harvest_id)
        enforce(db)


@pytest.mark.parametrize(
    "sql",
    [
        (
            "UPDATE harvest_material_inventory SET state='active', "
            "quantity_kind='item_count', quantity_value=0, "
            "quantity_is_approximate=false WHERE id=:id"
        ),
        "UPDATE harvest_material_inventory SET state='depleted' WHERE id=:id",
        "UPDATE harvest_material_inventory SET quantity_unit='g' WHERE id=:id",
        "UPDATE harvest_material_inventory SET quantity_value='NaN'::numeric WHERE id=:id",
        "DELETE FROM harvest_items WHERE id=:item",
        "UPDATE harvest_items SET material_kind='root' WHERE id=:item",
        (
            "INSERT INTO harvest_material_inventory SELECT gen_random_uuid(), "
            "harvest_item_id, location_id, harvest_id, material_kind, state, "
            "quantity_kind, quantity_value, quantity_unit, "
            "quantity_is_approximate, created_at, updated_at FROM "
            "harvest_material_inventory WHERE id=:id"
        ),
    ],
)
def test_database_guards(database_connection: Connection, sql: str) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        inventory, _ = setup(db)
        with pytest.raises(IntegrityError), db.begin_nested():  # noqa: PT012 - DB rollback proof
            db.execute(text(sql), {"id": inventory.id, "item": inventory.harvest_item_id})
            enforce(db)


def test_location_counts_query_bounds_reparenting_and_retention(
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        roots = [create_location(db, LocationCreate(name=f"Stock root {n}")) for n in range(2)]
        child = create_location(db, LocationCreate(name="Stock child", parent_id=roots[0].id))
        leaf = create_location(db, LocationCreate(name="Stock leaf", parent_id=child.id))
        empty = create_location(db, LocationCreate(name="Empty stock branch"))
        inventories = []
        for n in range(12):
            inventory, _ = setup(db, group=n % 2 == 0)
            correct(
                db, inventory.id, InventoryWrite(state="active", quantity=q(), location_id=leaf.id)
            )
            if n % 2 == 0:
                record_disposition(
                    db, inventory.id, DispositionCreate(kind="discarded", mode="use_all")
                )
            inventories.append(inventory)
        statements = []

        def capture(_conn: object, _cursor: object, statement: str, *_args: object) -> None:
            statements.append(statement)

        event.listen(database_connection, "before_cursor_execute", capture)
        try:
            usages = location_usage_aggregation(db)
            rows = list_inventory(db)
        finally:
            event.remove(database_connection, "before_cursor_execute", capture)
        assert len(statements) <= 10
        assert len(rows) == 12
        assert all(row.has_dispositions == (row.state == "depleted") for row in rows)
        assert usages[roots[0].id].including_descendants.harvest_inventory.model_dump() == {
            "active": 6,
            "total": 12,
        }
        assert usages[roots[0].id].direct.harvest_inventory.total == 0
        assert roots[1].id not in usages
        assert empty.id not in usages
        update_location(db, child.id, LocationUpdate(name=child.name, parent_id=roots[1].id))
        usages = location_usage_aggregation(db)
        assert roots[0].id not in usages
        assert usages[roots[1].id].including_descendants.harvest_inventory.active == 6
        with pytest.raises(Exception, match="scope"):
            update_location(db, leaf.id, LocationUpdate(name=leaf.name, usage_scopes={"plants"}))
        with pytest.raises(Exception, match="retained"):
            delete_location(db, leaf.id)


def test_http_owner_csrf_origin_and_conflicts(
    database_connection: Connection, inventory_browser: tuple[str, str]
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        inventory, _ = setup(db)
        db.commit()
        inventory_id = inventory.id
    path = f"/api/v1/harvest-inventory/{inventory_id}/dispositions"
    body = {"kind": "consumed", "mode": "partial", "quantity": q("7").model_dump(mode="json")}
    assert request("GET", "/api/v1/harvest-inventory").status_code == 401
    assert request("POST", path, browser=inventory_browser, body=body).status_code == 403
    assert (
        request(
            "POST",
            path,
            browser=inventory_browser,
            body=body,
            request_headers={
                "Origin": "https://untrusted.example",
                "X-CSRF-Token": inventory_browser[1],
            },
        ).status_code
        == 403
    )
    assert (
        request(
            "POST", path, browser=inventory_browser, body=body, mutation_headers=True
        ).status_code
        == 201
    )
    assert (
        request(
            "POST", path, browser=inventory_browser, body=body, mutation_headers=True
        ).status_code
        == 409
    )
    assert (
        request(
            "DELETE",
            f"/api/v1/harvest-inventory/{inventory_id}",
            browser=inventory_browser,
            mutation_headers=True,
        ).status_code
        == 409
    )


def wait_for_lock(engine: Engine, pid: int) -> None:
    deadline = monotonic() + 10
    with engine.connect() as observer:
        while monotonic() < deadline:
            observer.execute(text("SELECT pg_stat_clear_snapshot()"))
            if observer.scalar(
                text("SELECT wait_event_type='Lock' FROM pg_stat_activity WHERE pid=:pid"),
                {"pid": pid},
            ):
                return
    raise AssertionError("Competing transaction did not reach a PostgreSQL lock wait")


@pytest.mark.parametrize(
    "race", ["consume", "correct", "remove_source", "change_material", "duplicate_track", "use_all"]
)
def test_real_locked_transactions_refresh_stale_state(database_engine: Engine, race: str) -> None:
    with Session(database_engine) as db:
        inventory, payload = setup(db)
        response = list_inventory(db, inventory_id=inventory.id)[0]
        inventory_id, item_id, harvest_id = (
            inventory.id,
            inventory.harvest_item_id,
            response.harvest_id,
        )
        source = db.get(Plant, response.source.id)
        assert source is not None
        identity_id, location_id = source.botanical_identity_id, source.location_id
        db.commit()
    ready = ThreadEvent()
    release = ThreadEvent()
    waiter_pid = []

    def waiting() -> str:
        with Session(database_engine) as db:
            # Preload stale inventory to prove populate_existing after acquiring the lock.
            preloaded = db.get(Inventory, inventory_id)
            if race in ("consume", "correct", "use_all"):
                assert preloaded is not None
                assert preloaded.quantity_value == 10
            waiter_pid.append(db.scalar(text("SELECT pg_backend_pid()")))
            ready.set()
            assert release.wait(10)
            try:
                if race == "consume":
                    record_disposition(
                        db,
                        inventory_id,
                        DispositionCreate(kind="consumed", mode="partial", quantity=q("7")),
                    )
                elif race == "correct":
                    correct(db, inventory_id, InventoryWrite(state="active", quantity=q("8")))
                elif race == "remove_source":
                    delete_harvest(db, harvest_id)
                elif race == "duplicate_track":
                    track(db, item_id, InventoryWrite(state="active", quantity=q()))
                elif race == "use_all":
                    record_disposition(
                        db, inventory_id, DispositionCreate(kind="discarded", mode="use_all")
                    )
                else:
                    write_harvest(
                        db,
                        HarvestWrite.model_validate(
                            {
                                **payload.model_dump(),
                                "items": [{"id": item_id, "material_kind": "root"}],
                            }
                        ),
                        harvest_id,
                    )
                db.commit()
                return "accepted"
            except EventDomainConflictError:
                db.rollback()
                return "conflict"

    try:
        if race in ("remove_source", "change_material", "duplicate_track"):
            # Start without tracking, then let creation hold the owner lock while a
            # mutation or competing creator waits.
            with Session(database_engine) as db:
                remove_tracking(db, inventory_id)
                db.commit()
        with ThreadPoolExecutor(max_workers=1) as executor, Session(database_engine) as winner:
            if race in ("consume", "correct", "use_all"):
                record_disposition(
                    winner,
                    inventory_id,
                    DispositionCreate(
                        kind="discarded" if race == "use_all" else "consumed",
                        mode="use_all" if race == "use_all" else "partial",
                        quantity=q("7") if race != "use_all" else None,
                    ),
                )
            else:
                inventory = track(winner, item_id, InventoryWrite(state="active", quantity=q()))
                inventory_id = inventory.id
            future = executor.submit(waiting)
            assert ready.wait(10)
            release.set()
            assert waiter_pid[0] is not None
            wait_for_lock(database_engine, waiter_pid[0])
            winner.commit()
            assert future.result(timeout=10) == ("accepted" if race == "correct" else "conflict")
        with Session(database_engine) as db:
            result = db.get(Inventory, inventory_id)
            assert result is not None
            if race == "use_all":
                assert (result.state, result.quantity_value) == ("depleted", None)
            else:
                assert result.quantity_value == Decimal(
                    "8" if race == "correct" else "3" if race == "consume" else "10"
                )
            assert len(history(db, inventory_id)) == (
                1 if race in ("consume", "correct", "use_all") else 0
            )
    finally:
        release.set()
        with database_engine.begin() as conn:
            conn.execute(
                text("DELETE FROM harvest_material_dispositions WHERE inventory_id=:id"),
                {"id": inventory_id},
            )
        with Session(database_engine) as db:
            remove_tracking(db, inventory_id)
            delete_harvest(db, harvest_id)
            db.execute(delete(PlantGroup).where(PlantGroup.botanical_identity_id == identity_id))
            db.execute(delete(Plant).where(Plant.botanical_identity_id == identity_id))
            db.execute(delete(BotanicalIdentity).where(BotanicalIdentity.id == identity_id))
            db.execute(delete(Location).where(Location.id == location_id))
            db.commit()
