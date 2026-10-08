"""Real mixed-source projection, global pagination, corrections and query bounds."""

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, cast

import pytest
from sqlalchemy import Connection, event, select, text
from sqlalchemy.orm import Session

from florabase.events.model import Event
from florabase.events.schemas import EventCreate, EventUpdate, TransferCreate
from florabase.events.service import create_event, delete_event, transfer_target, update_event
from florabase.geographic_places.model import GeographicPlace
from florabase.harvests import conversion_service as conversions
from florabase.harvests import inventory_service as stock
from florabase.harvests.inventory_schemas import DispositionCreate
from florabase.harvests.model import Harvest
from florabase.harvests.service import write_harvest
from florabase.history.schemas import HistoryCategory as Category
from florabase.history.schemas import HistorySubjectKind as Subject
from florabase.history.service import history_statement, list_history
from florabase.plants.model import Plant
from florabase.plants.schemas import PlantExtractionCreate
from florabase.plants.service import extract_plant, reintegrate_plant
from florabase.propagation.reversal import reverse
from florabase.propagation.schemas import (
    PlantFromSowingCreate,
    PlantGroupFromSowingCreate,
    SeedLotSowingTransitionCreate,
)
from florabase.propagation.service import (
    create_plant_from_sowing,
    create_plant_group_from_sowing,
    create_sowing_from_seed_lot,
)
from florabase.provenance_sites.model import ProvenanceSite
from florabase.reversals.model import OperationReceipt
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import GerminationObservation, Sowing
from florabase.suppliers.model import Supplier

from .test_harvest_inventory import q, setup
from .test_harvest_seed_conversion import payload as conversion_payload
from .test_harvests import data, fixtures
from .test_search import _api_get
from .test_supplier_api import authenticated_browser as authenticated_browser
from .test_supplier_api import request

pytestmark = pytest.mark.integration
STAMP = datetime(2026, 10, 7, 12, tzinfo=UTC)


@pytest.fixture
def db(database_connection: Connection) -> Iterator[Session]:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as session:
        yield session


def propagation(db: Session) -> tuple[SeedLot, Sowing, Plant]:
    _, _, identity = fixtures(db)
    lot = SeedLot(botanical_identity_id=identity.id, label="Source seeds")
    db.add(lot)
    db.flush()
    sowing, _ = create_sowing_from_seed_lot(
        db,
        lot.id,
        SeedLotSowingTransitionCreate.model_validate(
            {
                "sowing": {"label": "Tray", "sowing_date": {"precision": "year", "year": 2020}},
                "source_adjustment": {"mode": "none"},
            }
        ),
    )
    plant, _ = create_plant_from_sowing(
        db,
        sowing.id,
        PlantFromSowingCreate(botanical_identity_id=identity.id, label="Result plant"),
        "completed",
    )
    create_plant_group_from_sowing(
        db,
        sowing.id,
        PlantGroupFromSowingCreate(botanical_identity_id=identity.id, label="Result group"),
        "completed",
    )
    return lot, sowing, plant


def test_event_kinds_receipt_dedup_and_corrections(db: Session) -> None:
    plant, _, _ = fixtures(db)
    ordinary = create_event(
        db,
        "plant",
        plant.id,
        EventCreate.model_validate(
            {"kind": "observation", "occurred_on": {"precision": "year", "year": 2024}}
        ),
    )
    movement = create_event(
        db,
        "plant",
        plant.id,
        EventCreate.model_validate(
            {"kind": "movement", "destination_location_id": plant.location_id}
        ),
    )
    death = create_event(db, "plant", plant.id, EventCreate(kind="death"))
    plant.lifecycle = "active"
    db.flush()
    transfer, _ = transfer_target(db, "plant", plant.id, TransferCreate(recipient="Friend"))
    db.flush()
    rows = list_history(db).items
    assert len(rows) == 4
    assert {row.source_kind for row in rows} == {"event"}
    move = next(row for row in rows if row.source_id == movement.id)
    assert move.date_basis == "recorded"
    assert move.occurred_on is None
    assert move.related[0].kind == "location"
    assert move.related[0].id == plant.location_id
    assert next(row for row in rows if row.source_id == death.id).subtype == "death"
    assert next(row for row in rows if row.source_id == transfer.id).context == "Recipient: Friend"
    before = next(row for row in rows if row.source_id == ordinary.id)
    update_event(
        db,
        ordinary,
        EventUpdate.model_validate(
            {"kind": "flowering", "occurred_on": {"precision": "month", "year": 2025, "month": 7}}
        ),
    )
    db.flush()
    after = next(row for row in list_history(db).items if row.source_id == ordinary.id)
    assert after.key == before.key
    assert after.title == "Flowering"
    assert after.occurred_on
    assert after.occurred_on.precision == "month"
    assert after.occurred_on.day is None
    delete_event(db, ordinary)
    db.flush()
    assert before.key not in {row.key for row in list_history(db).items}


def test_harvest_is_one_fact_with_multiple_items_and_correction(db: Session) -> None:
    plant, _, _ = fixtures(db)
    harvest = write_harvest(
        db,
        data(
            plant,
            label="Collected",
            occurred_on={"precision": "year", "year": 2024},
            items=[{"material_kind": "seed"}, {"material_kind": "leaf"}],
        ),
    )
    before = list_history(db)
    assert before.total == 1
    assert before.items[0].source_kind == "harvest"
    assert before.items[0].context == "2 material lines"
    assert before.items[0].source_id == harvest.id
    assert before.items[0].related[0].id == plant.id
    write_harvest(
        db,
        data(
            plant,
            label="Corrected",
            occurred_on={"precision": "month", "year": 2025, "month": 9},
            items=[{"material_kind": "seed"}],
        ),
        harvest.id,
    )
    after = list_history(db)
    assert after.total == 1
    assert after.items[0].key == before.items[0].key
    assert after.items[0].primary.label == "Corrected"
    assert after.items[0].occurred_on
    assert after.items[0].occurred_on.month == 9


def test_extraction_and_reintegration_keep_event_facts_and_current_display_labels(
    db: Session,
) -> None:
    _, group, identity = fixtures(db)
    group.lifecycle = "active"
    group.quantity_value = 3
    group.quantity_is_approximate = False
    db.flush()
    plant, _, extraction = extract_plant(db, group.id, PlantExtractionCreate())
    db.flush()
    before = list_history(db).items
    assert len(before) == 1
    row = before[0]
    assert row.source_id == extraction.id
    assert row.primary.kind == "plant_group"
    assert row.primary.id == group.id
    assert row.related[0].id == plant.id
    assert row.related[0].label == identity.common_name
    assert row.date_basis == "recorded"
    _, _, reintegration, _ = reintegrate_plant(db, plant.id, confirm_retained_observations=False)
    db.flush()
    after = list_history(db).items
    assert len(after) == 2
    assert {entry.source_kind for entry in after} == {"event"}
    assert next(entry for entry in after if entry.key == row.key).status == "reversed"
    assert (
        next(entry for entry in after if entry.source_id == reintegration.id).subtype
        == "reintegration"
    )


def test_propagation_germination_reversal_status_without_fake_time(db: Session) -> None:
    lot, sowing, _plant = propagation(db)
    db.add(
        GerminationObservation(
            sowing_id=sowing.id, observed_on=date(2026, 9, 8), newly_germinated_count=3
        )
    )
    db.flush()
    rows = list_history(db).items
    assert len(rows) == 4
    receipts = [row for row in rows if row.category == "propagation"]
    assert {row.subtype for row in receipts} == {
        "seed_lot_to_sowing",
        "sowing_to_plant",
        "sowing_to_plant_group",
    }
    assert all(row.date_basis == "recorded" and row.occurred_on is None for row in receipts)
    sowing_row = next(row for row in receipts if row.primary.id == sowing.id)
    assert sowing_row.related[0].id == lot.id
    germ = next(row for row in rows if row.category == "germination")
    assert germ.primary.id == sowing.id
    assert germ.context == "3 newly germinated"
    assert germ.occurred_on
    assert germ.occurred_on.model_dump() == {
        "precision": "day",
        "year": 2026,
        "month": 9,
        "day": 8,
    }
    group = db.scalar(
        select(OperationReceipt).where(OperationReceipt.kind == "sowing_to_plant_group")
    )
    assert group is not None
    assert group.plant_group_id is not None
    reverse(db, "plant_group", group.plant_group_id, confirm=False)
    db.flush()
    after = list_history(db).items
    assert len(after) == 4
    assert next(row for row in after if row.primary.id == group.plant_group_id).status == "reversed"
    assert {row.key for row in after} == {row.key for row in rows}


@pytest.mark.parametrize("mode", ["partial", "use_all"])
@pytest.mark.parametrize("dated", [False, True])
def test_dispositions_conversion_and_real_reversal(db: Session, mode: str, dated: bool) -> None:
    inventory, _ = setup(db)
    d = stock.record_disposition(
        db,
        inventory.id,
        DispositionCreate.model_validate(
            {
                "kind": "gifted",
                "mode": mode,
                **({"quantity": q("2").model_dump()} if mode == "partial" else {}),
                **(
                    {"occurred_on": {"precision": "month", "year": 2024, "month": 6}}
                    if dated
                    else {}
                ),
            }
        ),
    )
    db.flush()
    row = next(row for row in list_history(db).items if row.source_kind == "disposition")
    assert row.source_id == d.id
    assert row.primary.id == inventory.id
    assert row.primary.harvest_id == inventory.harvest_id
    assert row.date_basis == ("occurred" if dated else "recorded")
    assert ("Use all" if mode == "use_all" else "Partial use") in row.context
    if mode == "use_all":
        return
    conversion = conversions.create(db, inventory.id, conversion_payload())
    db.flush()
    before = list_history(db)
    assert before.total == 3  # Harvest, gift, conversion; owned disposition suppressed
    applied = next(row for row in before.items if row.source_kind == "conversion")
    assert applied.key == f"conversion:{conversion.id}:applied"
    assert applied.primary.id == conversion.seed_lot_id
    assert applied.date_basis == "recorded"
    assert applied.related[0].id == inventory.id
    conversions.reverse(db, conversion.id)
    db.flush()
    after = list_history(db)
    assert after.total == 4
    entries = [row for row in after.items if row.source_kind == "conversion"]
    assert len(entries) == 2
    assert all(row.status == "reversed" for row in entries)
    reversal = next(row for row in entries if row.subtype == "reversed")
    assert reversal.occurred_at == conversion.reversed_at
    assert reversal.date_basis == "occurred"
    assert reversal.recorded_at == conversion.created_at


def test_current_fields_and_updated_at_do_not_fabricate_history(db: Session) -> None:
    inventory, _ = setup(db)
    lot, sowing, plant = propagation(db)
    before = list_history(db).model_dump()
    supplier = Supplier(name="Current supplier", kind="other")
    site = ProvenanceSite(name="Current site")
    db.add_all([supplier, site])
    db.flush()
    lot.supplier_id = supplier.id
    lot.material_provenance_place_id = db.scalar(
        select(GeographicPlace.id).where(GeographicPlace.place_kind == "country").limit(1)
    )
    lot.provenance_site_id = site.id
    # Mutations of current state have no durable operation fact of their own.
    lot.lifecycle = "discarded"
    sowing.lifecycle = "completed"
    plant.location_id = None
    inventory.quantity_value = Decimal(9)
    for record in (lot, sowing, plant, inventory):
        record.updated_at = STAMP + timedelta(days=100)
    db.flush()
    assert list_history(db).model_dump() == before
    assert not {
        "updated_at",
        "supplier_id",
        "material_provenance_place_id",
        "provenance_site_id",
    } & set(history_statement().selected_columns.keys())


def test_global_mixed_pages_partial_dates_ties_filters_and_query_bound(db: Session) -> None:
    inventory, _ = setup(db)
    _lot, sowing, plant = propagation(db)
    db.add(
        GerminationObservation(
            sowing_id=sowing.id, observed_on=date(2026, 10, 7), newly_germinated_count=1
        )
    )
    stock.record_disposition(
        db, inventory.id, DispositionCreate(kind="consumed", mode="partial", quantity=q("1"))
    )
    conversions.create(db, inventory.id, conversion_payload())
    events = [
        Event(
            plant_id=plant.id,
            kind="observation",
            created_at=STAMP,
            occurred_on_precision=precision,
            occurred_on_year=2026 if precision else None,
            occurred_on_month=10 if precision in {"month", "day"} else None,
            occurred_on_day=7 if precision == "day" else None,
        )
        for precision in ("year", "month", "day", None)
    ]
    db.add_all(events)
    db.flush()
    # Control mutable facts' recording dates. Immutable receipts retain their real timestamps.
    for model in (Event, Harvest, GerminationObservation):
        for record in db.scalars(select(model)):
            cast(Any, record).created_at = STAMP
    db.flush()
    complete = list_history(db, limit=100)
    assert complete.total == 11
    keys = [item.key for item in complete.items]
    assert len(keys) == len(set(keys))
    pages = [list_history(db, offset=i, limit=3) for i in (0, 3, 6, 9)]
    assert all(page.total == 11 for page in pages)
    assert [item.key for page in pages for item in page.items] == keys
    assert list_history(db, offset=100).total == 11
    assert list_history(db, offset=100).items == []
    assert list_history(db, categories=(Category.EVENT,)).total == 4
    assert list_history(db, categories=(Category.EVENT, Category.HARVEST)).total == 5
    assert all(
        item.primary.kind == "sowing"
        for item in list_history(db, subject_kind=Subject.SOWING).items
    )
    assert list_history(db, year=1900).total == 0
    expected_year = {
        item.key
        for item in complete.items
        if (item.occurred_on.year if item.occurred_on else item.recorded_at.year) == 2026
    }
    assert {item.key for item in list_history(db, year=2026, limit=100).items} == expected_year
    partials = [next(item for item in complete.items if item.source_id == e.id) for e in events]
    assert [p.occurred_on.precision if p.occurred_on else None for p in partials] == [
        "year",
        "month",
        "day",
        None,
    ]
    assert keys.index(partials[2].key) < keys.index(partials[1].key) < keys.index(partials[0].key)
    assert partials[0].occurred_on
    assert partials[0].occurred_on.month is None
    assert partials[1].occurred_on
    assert partials[1].occurred_on.day is None
    statements: list[str] = []

    def capture(
        _conn: Any, _cursor: Any, statement: str, _params: Any, _context: Any, _many: bool
    ) -> None:
        statements.append(statement)

    event.listen(db.bind, "before_cursor_execute", capture)
    try:
        for options in ({}, {"categories": (Category.EVENT,)}, {"offset": 3}, {"limit": 100}):
            statements.clear()
            list_history(db, **options)
            assert len(statements) == 1
    finally:
        event.remove(db.bind, "before_cursor_execute", capture)
    # Representative actual PostgreSQL plan, with no speculative index addition.
    compiled = history_statement(limit=100).compile(
        db.get_bind(), compile_kwargs={"literal_binds": True}
    )
    plan = (
        db.connection()
        .exec_driver_sql("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + str(compiled))
        .scalar_one()
    )
    assert plan[0]["Plan"]["Actual Rows"] == 11
    assert "Execution Time" in plan[0]


def test_authenticated_read_only_api_and_bounds(authenticated_browser: tuple[str, str]) -> None:
    cookie, _ = authenticated_browser
    assert request("GET", "/api/v1/history")[0] == 401
    status, body = _api_get("/api/v1/history", cookie)
    assert status == 200
    assert body["limit"] == 50
    assert body["offset"] == 0
    for query in (
        "limit=101",
        "limit=0",
        "offset=-1",
        "offset=100001",
        "category=no",
        "subject_kind=no",
        "year=0",
        "year=10000",
    ):
        assert _api_get(f"/api/v1/history?{query}", cookie)[0] == 422
    assert _api_get("/api/v1/history?category=event&category=harvest&limit=100", cookie)[0] == 200
    assert request("POST", "/api/v1/history", headers={"cookie": cookie})[0] == 405


def test_maximum_page_tie_order_is_stable_with_one_query(db: Session) -> None:
    plant, _, _ = fixtures(db)
    db.add_all(
        [
            Event(
                plant_id=plant.id,
                kind="observation",
                created_at=STAMP,
                occurred_on_precision="day",
                occurred_on_year=2026,
                occurred_on_month=10,
                occurred_on_day=7,
            )
            for _ in range(105)
        ]
    )
    db.flush()
    queries: list[str] = []

    def capture(
        _conn: Any, _cursor: Any, statement: str, _params: Any, _context: Any, _many: bool
    ) -> None:
        queries.append(statement)

    event.listen(db.bind, "before_cursor_execute", capture)
    try:
        first = list_history(db, limit=100)
        assert len(queries) == 1
        assert len(first.items) == 100
        queries.clear()
        second = list_history(db, offset=100, limit=100)
        assert len(queries) == 1
        assert len(second.items) == 5
    finally:
        event.remove(db.bind, "before_cursor_execute", capture)
    keys = [row.key for row in first.items + second.items]
    assert keys == sorted(keys)
    assert len(set(keys)) == 105
    assert first.total == second.total == 105


def test_recorded_year_is_utc_even_when_database_timezone_differs(db: Session) -> None:
    plant, _, _ = fixtures(db)
    db.add(
        Event(
            plant_id=plant.id,
            kind="observation",
            created_at=datetime(2026, 12, 31, 23, 30, tzinfo=UTC),
        )
    )
    db.flush()
    db.execute(text("SET LOCAL TIME ZONE 'Pacific/Auckland'"))
    assert list_history(db, year=2026).total == 1
    assert list_history(db, year=2027).total == 0
