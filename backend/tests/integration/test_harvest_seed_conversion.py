from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Event as ThreadEvent
from uuid import UUID

import pytest
from sqlalchemy import Connection, Engine, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from florabase.collection_photos.model import RecordMediaLink
from florabase.events.model import Event
from florabase.events.service import EventDomainConflictError
from florabase.harvests import conversion_service as conversions
from florabase.harvests import inventory_service as stock
from florabase.harvests.conversion_model import HarvestSeedLotConversion as Conversion
from florabase.harvests.conversion_schemas import ConversionCreate
from florabase.harvests.inventory_model import HarvestMaterialDisposition as Disposition
from florabase.harvests.inventory_model import HarvestMaterialInventory as Inventory
from florabase.harvests.inventory_schemas import DispositionCreate, InventoryWrite
from florabase.harvests.schemas import HarvestWrite
from florabase.harvests.service import read_harvest, write_harvest
from florabase.lineage.service import lineage
from florabase.propagation.reversal import reverse as reverse_propagation
from florabase.propagation.schemas import SeedLotSowingTransitionCreate
from florabase.propagation.service import create_sowing_from_seed_lot
from florabase.seed_lots.model import SeedLot
from florabase.seed_lots.schemas import SeedLotUpdate
from florabase.seed_lots.service import get_seed_lot, responses, update_seed_lot
from florabase.sowings.model import Sowing
from florabase.sowings.schemas import SowingCreate
from florabase.sowings.service import SowingDomainConflictError, create_sowing

from .test_attachment_api import authenticated_browser as browser_fixture
from .test_attachment_api import request
from .test_harvest_inventory import q, setup, wait_for_lock
from .test_harvests import enforce

pytestmark = pytest.mark.integration
conversion_browser = browser_fixture


def payload(amount: str | None = "3", **changes: object) -> ConversionCreate:
    return ConversionCreate.model_validate(
        {
            "mode": "partial",
            "quantity": {"kind": "seed_count", "value": amount, "is_approximate": False}
            if amount
            else None,
            **changes,
        }
    )


def sow(db: Session, seed_id: UUID) -> None:
    create_sowing_from_seed_lot(
        db,
        seed_id,
        SeedLotSowingTransitionCreate.model_validate(
            {
                "source_adjustment": {"mode": "partial"},
                "sowing": {
                    "quantity": {"kind": "seed_count", "value": "1", "is_approximate": False}
                },
            }
        ),
    )


@pytest.mark.parametrize("group", [False, True])
def test_exact_conversion_origin_history_and_reversal(
    database_connection: Connection, group: bool
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        inventory, harvest_payload = setup(db, group=group)
        harvest_payload = HarvestWrite.model_validate(
            {
                **harvest_payload.model_dump(),
                "occurred_on": {"precision": "month", "year": 2026, "month": 8},
                "items": [
                    {**harvest_payload.items[0].model_dump(), "id": inventory.harvest_item_id}
                ],
            }
        )
        write_harvest(db, harvest_payload, inventory.harvest_id)
        events = db.scalar(select(func.count()).select_from(Event))
        sowings = db.scalar(select(func.count()).select_from(Sowing))
        media_links = db.scalar(select(func.count()).select_from(RecordMediaLink))
        record = conversions.create(db, inventory.id, payload(label="Packet"))
        lot = db.get(SeedLot, record.seed_lot_id)
        assert lot is not None
        source = read_harvest(db, inventory.harvest_id).source
        assert lot.source_kind == "collection_produced"
        assert (lot.producer_plant_group_id if group else lot.producer_plant_id) == source.id
        assert lot.botanical_identity_id == source.botanical_identity.id
        assert lot.supplier_id is lot.material_provenance_place_id is lot.provenance_site_id is None
        assert lot.quantity_value == 3
        assert lot.harvest_date_precision == "month"
        assert lot.harvest_date_year == 2026
        assert lot.harvest_date_month == 8
        assert lot.harvest_date_day is None
        assert inventory.quantity_value == 7
        assert lineage(db, ("seed_lot", lot.id)).ancestors[0].id == source.id
        projection = get_seed_lot(db, lot.id)
        assert projection is not None
        response = responses(db, [projection])[0]
        changes = response.model_dump(include=set(SeedLotUpdate.model_fields))
        changes.update(label="Corrected label", notes="Descriptive correction")
        update_seed_lot(db, lot, SeedLotUpdate.model_validate(changes))
        assert conversions.evaluate(db, record.id)[-1].status == "safe"
        with pytest.raises(EventDomainConflictError, match="protected"):
            write_harvest(
                db,
                harvest_payload.model_copy(
                    update={
                        "plant_id": None if not group else source.id,
                        "plant_group_id": source.id if not group else None,
                    }
                ),
                inventory.harvest_id,
            )
        original = conversions.list_conversions(db, inventory_id=inventory.id)[0]
        assert original.quantity is not None
        assert original.before.quantity is not None
        assert original.after.quantity is not None
        assert original.quantity.value == 3
        assert original.before.quantity.value == 10
        assert original.after.quantity.value == 7
        conversions.reverse(db, record.id)
        assert lot.lifecycle == "reversed"
        assert inventory.quantity_value == 10
        assert lot.producer_plant_id or lot.producer_plant_group_id
        assert record.status == "reversed"
        assert record.reversed_at is not None
        disposition = db.get(Disposition, record.disposition_id)
        assert disposition is not None
        assert disposition.kind == "used_for_propagation"
        assert db.scalar(select(func.count()).select_from(Event)) == events
        assert db.scalar(select(func.count()).select_from(Sowing)) == sowings
        assert db.scalar(select(func.count()).select_from(RecordMediaLink)) == media_links
        with pytest.raises(EventDomainConflictError, match="already"):
            conversions.reverse(db, record.id)
        with pytest.raises(SowingDomainConflictError, match="reversed"):
            create_sowing(db, SowingCreate(seed_lot_id=lot.id))
        enforce(db)


@pytest.mark.parametrize(
    ("precision", "mode", "amount"),
    [
        ("exact", "partial", "3"),
        ("exact", "use_all", "10"),
        ("approximate", "partial", "3"),
        ("unknown", "partial", "3"),
        ("approximate", "use_all", None),
        ("unknown", "use_all", None),
        ("unknown", "use_all", "8"),
    ],
)
def test_quantity_precision_roundtrip(
    database_connection: Connection, precision: str, mode: str, amount: str | None
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        inventory, _ = setup(
            db, approximate=precision == "approximate", unknown=precision == "unknown"
        )
        before = stock.quantity(inventory)
        result = (
            q("7", approximate=True) if mode == "partial" and precision == "approximate" else None
        )
        record = conversions.create(
            db, inventory.id, payload(amount, mode=mode, resulting_quantity=result)
        )
        assert inventory.state == ("depleted" if mode == "use_all" else "active")
        if mode == "partial":
            assert stock.quantity(inventory) == (q("7") if precision == "exact" else result)
        conversions.reverse(db, record.id)
        assert stock.quantity(inventory) == before
        assert inventory.state == "active"
        enforce(db)


def test_eligibility_overuse_atomicity_and_result_correction(
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        inventory, _ = setup(db)
        before_count = db.scalar(select(func.count()).select_from(SeedLot))
        for amount in ["10", "11"]:
            with pytest.raises(EventDomainConflictError, match="smaller"):
                conversions.create(db, inventory.id, payload(amount))
        with pytest.raises(EventDomainConflictError, match="same exact"):
            conversions.create(db, inventory.id, payload("3", mode="use_all"))
        assert db.scalar(select(func.count()).select_from(SeedLot)) == before_count
        db.rollback()
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        inventory, _ = setup(db)
        record = conversions.create(db, inventory.id, payload())
        lot = db.get(SeedLot, record.seed_lot_id)
        assert lot is not None
        lot.quantity_value = Decimal(2)
        db.flush()
        assert conversions.evaluate(db, record.id)[-1].status == "blocked"
        lot.quantity_value = Decimal(3)
        db.flush()
        stock.record_disposition(
            db, inventory.id, DispositionCreate(kind="consumed", mode="partial", quantity=q("1"))
        )
        assert conversions.evaluate(db, record.id)[-1].status == "blocked"
        enforce(db)


def test_resolved_sowing_and_multiple_conversions(database_connection: Connection) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        inventory, _ = setup(db)
        first = conversions.create(db, inventory.id, payload())
        second = conversions.create(db, inventory.id, payload("2"))
        assert conversions.evaluate(db, first.id)[-1].status == "blocked"
        conversions.reverse(db, second.id)
        assert conversions.evaluate(db, first.id)[-1].status == "safe"
        sow(db, first.seed_lot_id)
        assert conversions.evaluate(db, first.id)[-1].status == "blocked"
        from florabase.sowings.model import Sowing

        sowing = db.scalar(select(Sowing).where(Sowing.seed_lot_id == first.seed_lot_id))
        assert sowing is not None
        reverse_propagation(db, "sowing", sowing.id, confirm=False)
        assert conversions.evaluate(db, first.id)[-1].status == "safe"
        conversions.reverse(db, first.id)
        enforce(db)


def test_source_correction_cannot_be_hidden_by_matching_snapshot(
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        inventory, _ = setup(db)
        record = conversions.create(db, inventory.id, payload())
        stock.correct(db, inventory.id, InventoryWrite(state="active", quantity=q("6")))
        stock.correct(db, inventory.id, InventoryWrite(state="active", quantity=q("7")))
        assert conversions.evaluate(db, record.id)[-1].status == "blocked"
        with pytest.raises(EventDomainConflictError, match="corrected"):
            conversions.reverse(db, record.id)
        assert inventory.quantity_value == 7
        enforce(db)


@pytest.mark.parametrize(
    "race",
    [
        "partial",
        "disposition",
        "use_all",
        "duplicate_all",
        "correct",
        "harvest",
        "lineage",
        "reverse_disposition",
        "reverse_conversion",
        "reverse_use",
        "reverse_duplicate",
        "reverse_correct",
    ],
)
def test_real_conversion_races(database_engine: Engine, race: str) -> None:
    with Session(database_engine) as db:
        inventory, harvest_payload = setup(db)
        inventory_id, harvest_id = inventory.id, inventory.harvest_id
        source = read_harvest(db, harvest_id).source
        identity_id = source.botanical_identity.id
        from florabase.plants.model import Plant

        source_plant = db.get(Plant, source.id)
        assert source_plant is not None
        source_location_id = source_plant.location_id
        record = (
            conversions.create(db, inventory_id, payload("7"))
            if race.startswith("reverse_")
            else None
        )
        conversion_id, seed_id = (record.id, record.seed_lot_id) if record else (None, None)
        db.commit()
    ready, release = ThreadEvent(), ThreadEvent()
    pid: list[int] = []

    def contender() -> str:
        with Session(database_engine) as db:
            db.get(Inventory, inventory_id)
            pid.append(db.scalar(text("SELECT pg_backend_pid()")))
            ready.set()
            assert release.wait(10)
            try:
                if race in {"partial", "reverse_conversion"}:
                    conversions.create(db, inventory_id, payload("7" if race == "partial" else "2"))
                elif race == "duplicate_all":
                    conversions.create(db, inventory_id, payload("10", mode="use_all"))
                elif race in {"disposition", "reverse_disposition", "use_all"}:
                    stock.record_disposition(
                        db,
                        inventory_id,
                        DispositionCreate(
                            kind="consumed",
                            mode="use_all" if race == "use_all" else "partial",
                            quantity=None if race == "use_all" else q("7"),
                        ),
                    )
                elif race in {"correct", "reverse_correct"}:
                    stock.correct(db, inventory_id, InventoryWrite(state="active", quantity=q("8")))
                elif race == "harvest":
                    from florabase.plants.model import PlantGroup

                    other_source = db.scalar(
                        select(PlantGroup.id).where(
                            PlantGroup.botanical_identity_id
                            == read_harvest(db, harvest_id).source.botanical_identity.id
                        )
                    )
                    assert other_source is not None
                    write_harvest(
                        db,
                        harvest_payload.model_copy(
                            update={"plant_id": None, "plant_group_id": other_source}
                        ),
                        harvest_id,
                    )
                elif race == "lineage":
                    from florabase.plants.model import Plant
                    from florabase.plants.schemas import PlantUpdate
                    from florabase.plants.service import update_plant
                    from florabase.sowings.model import Sowing

                    assert seed_id is not None
                    sow(db, seed_id)
                    sowing = db.scalar(select(Sowing).where(Sowing.seed_lot_id == seed_id))
                    source = db.get(Plant, harvest_payload.plant_id)
                    assert source is not None
                    assert sowing is not None
                    update_plant(
                        db,
                        source,
                        PlantUpdate(
                            botanical_identity_id=source.botanical_identity_id,
                            lifecycle="dead",
                            originating_sowing_id=sowing.id,
                        ),
                    )
                elif race == "reverse_use":
                    assert seed_id is not None
                    sow(db, seed_id)
                else:
                    assert conversion_id is not None
                    conversions.reverse(db, conversion_id)
                db.commit()
                return "accepted"
            except EventDomainConflictError, IntegrityError, ValueError:
                db.rollback()
                return "conflict"
            except Exception as failure:
                from florabase.plants.service import PlantDomainConflictError
                from florabase.propagation.service import PropagationConflictError

                if isinstance(failure, (PropagationConflictError, PlantDomainConflictError)):
                    db.rollback()
                    return "conflict"
                raise

    try:
        with ThreadPoolExecutor(max_workers=1) as pool, Session(database_engine) as winner:
            if race.startswith("reverse_"):
                assert conversion_id is not None
                conversions.reverse(winner, conversion_id)
            else:
                created = conversions.create(
                    winner,
                    inventory_id,
                    payload("10", mode="use_all") if race == "duplicate_all" else payload("7"),
                )
                seed_id = created.seed_lot_id
            future = pool.submit(contender)
            assert ready.wait(10)
            release.set()
            wait_for_lock(database_engine, pid[0])
            winner.commit()
            expected = (
                "conflict"
                if race
                in {
                    "partial",
                    "disposition",
                    "duplicate_all",
                    "harvest",
                    "lineage",
                    "reverse_duplicate",
                    "reverse_use",
                }
                else "accepted"
            )
            assert future.result(timeout=10) == expected
        with Session(database_engine) as db:
            current = db.get(Inventory, inventory_id)
            assert current is not None
            if race == "partial":
                assert current.quantity_value == 3
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(Conversion)
                        .where(Conversion.inventory_id == inventory_id)
                    )
                    == 1
                )
    finally:
        release.set()
        # Only rows owned by this disposable fixture are removed; application history
        # has no deletion API. The tmpfs project itself is also removed at completion.
        with database_engine.begin() as conn:
            conn.execute(
                text("DELETE FROM harvest_seed_lot_conversions WHERE inventory_id=:id"),
                {"id": inventory_id},
            )
            conn.execute(
                text("DELETE FROM harvest_material_dispositions WHERE inventory_id=:id"),
                {"id": inventory_id},
            )
            conn.execute(
                text("DELETE FROM harvest_material_inventory WHERE id=:id"), {"id": inventory_id}
            )
            conn.execute(
                text(
                    "DELETE FROM seed_lots WHERE producer_plant_id="
                    "(SELECT plant_id FROM harvests WHERE id=:id)"
                ),
                {"id": harvest_id},
            )
        with Session(database_engine) as db:
            from florabase.harvests.service import delete_harvest

            delete_harvest(db, harvest_id)
            db.execute(
                text("DELETE FROM plants WHERE botanical_identity_id=:id"), {"id": identity_id}
            )
            db.execute(
                text("DELETE FROM plant_groups WHERE botanical_identity_id=:id"),
                {"id": identity_id},
            )
            db.execute(text("DELETE FROM locations WHERE id=:id"), {"id": source_location_id})
            db.execute(text("DELETE FROM botanical_identities WHERE id=:id"), {"id": identity_id})
            db.commit()


@pytest.mark.parametrize(
    "material", ["fruit", "flower", "leaf", "root", "stem_or_shoot", "whole_plant", "other"]
)
def test_non_seed_and_untracked_are_not_convertible(
    database_connection: Connection, material: str
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        inventory, harvest_payload = setup(db)
        item_id, harvest_id = inventory.harvest_item_id, inventory.harvest_id
        stock.remove_tracking(db, inventory.id)
        with pytest.raises(LookupError):
            conversions.create(db, inventory.id, payload())
        harvest_payload = HarvestWrite.model_validate(
            {
                **harvest_payload.model_dump(),
                "items": [
                    {
                        **harvest_payload.items[0].model_dump(),
                        "id": item_id,
                        "material_kind": material,
                    }
                ],
            }
        )
        write_harvest(db, harvest_payload, harvest_id)
        inventory = stock.track(db, item_id, InventoryWrite(state="active", quantity=q()))
        with pytest.raises(EventDomainConflictError, match="seed material"):
            conversions.create(db, inventory.id, payload())
        assert (
            db.scalar(select(Conversion.id).where(Conversion.inventory_id == inventory.id)) is None
        )
        enforce(db)


def test_location_dates_identity_and_origin_protection(database_connection: Connection) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        from florabase.botanical_identities.model import BotanicalIdentity
        from florabase.locations.schemas import LocationCreate
        from florabase.locations.service import create_location, location_usage_aggregation
        from florabase.seed_lots.service import SeedLotDomainConflictError

        inventory, harvest_payload = setup(db)
        storage = create_location(db, LocationCreate(name="Seed storage"))
        target = create_location(db, LocationCreate(name="New packet drawer"))
        stock.correct(
            db, inventory.id, InventoryWrite(state="active", quantity=q(), location_id=storage.id)
        )
        write_harvest(
            db, harvest_payload.model_copy(update={"occurred_on": None}), inventory.harvest_id
        )
        identity = BotanicalIdentity(scientific_name="Corrected offspring identity")
        db.add(identity)
        db.flush()
        record = conversions.create(
            db, inventory.id, payload(botanical_identity_id=identity.id, location_id=target.id)
        )
        lot = db.get(SeedLot, record.seed_lot_id)
        assert lot is not None
        assert lot.botanical_identity_id == identity.id
        assert lot.harvest_date_precision is None
        assert lot.location_id == target.id
        assert inventory.location_id == storage.id
        projection = get_seed_lot(db, lot.id)
        assert projection is not None
        response = responses(db, [projection])[0]
        assert response.harvest_conversion_id == record.id
        values = response.model_dump(include=set(SeedLotUpdate.model_fields))
        with pytest.raises(SeedLotDomainConflictError, match="origin"):
            update_seed_lot(
                db, lot, SeedLotUpdate.model_validate({**values, "producer_plant_id": None})
            )
        conversions.reverse(db, record.id)
        usage = location_usage_aggregation(db)[target.id].direct.seed_lots
        assert usage.active == 0
        assert usage.total == 1
        with pytest.raises(SeedLotDomainConflictError, match="cannot be changed"):
            update_seed_lot(db, lot, SeedLotUpdate.model_validate(values))
        enforce(db)


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE harvest_seed_lot_conversions SET quantity_value=2 WHERE id=:conversion",
        "UPDATE seed_lots SET producer_plant_id=NULL WHERE id=:lot",
        "UPDATE harvests SET plant_id=NULL WHERE id=:harvest",
        "DELETE FROM seed_lots WHERE id=:lot",
        (
            "UPDATE harvest_seed_lot_conversions SET status='reversed',reversed_at=now() "
            "WHERE id=:conversion"
        ),
        (
            "INSERT INTO harvest_seed_lot_conversions SELECT "
            "gen_random_uuid(),inventory_id,disposition_id,seed_lot_id,"
            "source_correction_version,status,quantity_kind,quantity_value,"
            "quantity_unit,quantity_is_approximate,created_at,reversed_at"
            " FROM harvest_seed_lot_conversions WHERE id=:conversion"
        ),
    ],
)
def test_sql_protection(database_connection: Connection, sql: str) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        inventory, _ = setup(db)
        record = conversions.create(db, inventory.id, payload())
        enforce(db)
        with pytest.raises(IntegrityError), db.begin_nested():  # noqa: PT012 - rollback proof
            db.execute(
                text(sql),
                {
                    "conversion": record.id,
                    "lot": record.seed_lot_id,
                    "harvest": inventory.harvest_id,
                },
            )
            enforce(db)


def test_depleted_missing_and_weight_conversion(database_connection: Connection) -> None:
    from uuid import uuid7

    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        inventory, _ = setup(db)
        with pytest.raises(LookupError):
            conversions.create(db, uuid7(), payload())
        stock.correct(db, inventory.id, InventoryWrite(state="depleted", quantity=None))
        with pytest.raises(EventDomainConflictError, match="Depleted"):
            conversions.create(db, inventory.id, payload())
        stock.correct(
            db,
            inventory.id,
            InventoryWrite(
                state="active", quantity=q("100", kind="weight", unit="g", approximate=True)
            ),
        )
        record = conversions.create(
            db,
            inventory.id,
            payload(
                None,
                quantity={"kind": "weight", "value": "35", "unit": "g", "is_approximate": False},
                resulting_quantity=q("65", kind="weight", unit="g", approximate=True),
            ),
        )
        summary = conversions.list_conversions(db, seed_lot_id=record.seed_lot_id)[0]
        assert summary.quantity is not None
        assert summary.quantity.value == 35
        assert stock.quantity(inventory) == q("65", kind="weight", unit="g", approximate=True)
        conversions.reverse(db, record.id)
        assert stock.quantity(inventory) == q("100", kind="weight", unit="g", approximate=True)
        enforce(db)


def test_conversion_http_security_links_and_reversal(
    database_connection: Connection, conversion_browser: tuple[str, str]
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        inventory, _ = setup(db)
        inventory_id = inventory.id
        db.commit()
    path = f"/api/v1/harvest-inventory/{inventory_id}/create-seed-lot"
    body = payload().model_dump(mode="json")
    assert request("GET", "/api/v1/harvest-seed-conversions").status_code == 401
    assert request("POST", path, browser=conversion_browser, body=body).status_code == 403
    assert (
        request(
            "POST",
            path,
            browser=conversion_browser,
            body=body,
            request_headers={
                "Origin": "https://untrusted.example",
                "X-CSRF-Token": conversion_browser[1],
            },
        ).status_code
        == 403
    )
    response = request("POST", path, browser=conversion_browser, body=body, mutation_headers=True)
    assert response.status_code == 201
    result = response.json()
    conversion_id = result["id"]
    lot_id = result["seed_lot_id"]
    assert (
        request(
            "GET",
            f"/api/v1/harvest-seed-conversions?seed_lot_id={lot_id}",
            browser=conversion_browser,
        ).json()[0]["id"]
        == conversion_id
    )
    assert (
        request(
            "GET",
            f"/api/v1/harvest-seed-conversions/{conversion_id}/reversal",
            browser=conversion_browser,
        ).json()["status"]
        == "safe"
    )
    reverse_path = f"/api/v1/harvest-seed-conversions/{conversion_id}/reverse"
    assert request("POST", reverse_path, browser=conversion_browser).status_code == 403
    assert (
        request("POST", reverse_path, browser=conversion_browser, mutation_headers=True).json()[
            "status"
        ]
        == "reversed"
    )
    assert (
        request("POST", reverse_path, browser=conversion_browser, mutation_headers=True).status_code
        == 409
    )
    assert (
        request("GET", f"/api/v1/seed-lots/{lot_id}", browser=conversion_browser).json()[
            "lifecycle"
        ]
        == "reversed"
    )


def test_atomic_rollback_after_target_creation(
    database_connection: Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        inventory, _ = setup(db)
        lots_before = db.scalar(select(func.count()).select_from(SeedLot))

        def fail(*_args: object, **_kwargs: object) -> Disposition:
            raise EventDomainConflictError("test_failure", "Failure after Seed lot creation")

        with pytest.raises(EventDomainConflictError, match="Failure"), db.begin_nested():  # noqa: PT012 - rollback proof
            monkeypatch.setattr(stock, "record_disposition", fail)
            conversions.create(db, inventory.id, payload())
        assert db.scalar(select(func.count()).select_from(SeedLot)) == lots_before
        assert (
            db.scalar(select(Conversion.id).where(Conversion.inventory_id == inventory.id)) is None
        )
        assert (
            db.scalar(select(Disposition.id).where(Disposition.inventory_id == inventory.id))
            is None
        )
        db.refresh(inventory)
        assert inventory.quantity_value == 10
        enforce(db)
