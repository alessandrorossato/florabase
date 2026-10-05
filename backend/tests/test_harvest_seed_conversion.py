from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from florabase.auth.dependencies import AuthenticatedActor
from florabase.db.base import Base
from florabase.events.service import EventDomainConflictError
from florabase.harvests import conversion_api as api
from florabase.harvests import conversion_service as service
from florabase.harvests import inventory_service as stock
from florabase.harvests.conversion_model import HarvestSeedLotConversion
from florabase.harvests.conversion_schemas import ConversionCreate
from florabase.harvests.conversion_service import material_quantity
from florabase.harvests.inventory_model import HarvestMaterialDisposition as Disposition
from florabase.harvests.inventory_model import HarvestMaterialInventory as Inventory
from florabase.harvests.inventory_schemas import DispositionCreate
from florabase.harvests.model import Harvest
from florabase.harvests.schemas import HarvestQuantity
from florabase.plants.model import Plant
from florabase.seed_lots.model import SeedLot
from florabase.seed_lots.schemas import SeedLotCreate, SeedQuantity


@pytest.mark.parametrize(
    ("kind", "unit"), [("seed_count", None), ("weight", "g"), ("weight", "mg")]
)
@pytest.mark.parametrize("approximate", [False, True])
def test_transfer_reuses_seed_quantity_semantics(
    kind: str, unit: str | None, approximate: bool
) -> None:
    value = SeedQuantity.model_validate(
        {"kind": kind, "value": "12", "unit": unit, "is_approximate": approximate}
    )
    material = material_quantity(value)
    assert material is not None
    assert material.kind == ("item_count" if kind == "seed_count" else "weight")
    assert material.value == Decimal(12)
    assert material.unit == unit
    assert material.is_approximate == approximate
    assert material_quantity(None) is None


@pytest.mark.parametrize(
    "change",
    [
        {"source_kind": "purchased"},
        {"producer_plant_id": "01a00000-0000-7000-8000-000000000001"},
        {"supplier_id": "01a00000-0000-7000-8000-000000000001"},
        {"quantity": {"kind": "seed_count", "value": "0", "is_approximate": False}},
    ],
)
def test_no_origin_override_or_empty_transfer(change: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ConversionCreate.model_validate({"mode": "partial", **change})


class SessionStub:
    def __init__(self, values: dict[type[Base], object], scalars: list[object] | None = None):
        self.values = values
        self.scalar_values = iter(scalars or [])
        self.added: list[object] = []
        self.rows: list[tuple[object, object, object, object]] = []
        self.flush_count = 0
        self.commit_count = 0

    def get(self, model: type[Base], _key: object) -> object | None:
        return self.values.get(model)

    def scalar(self, _statement: object) -> object | None:
        return next(self.scalar_values)

    def execute(self, _statement: object) -> list[tuple[object, object, object, object]]:
        return self.rows

    def add(self, row: object) -> None:
        self.added.append(row)

    def flush(self) -> None:
        self.flush_count += 1

    def commit(self) -> None:
        self.commit_count += 1


def test_create_uses_exact_harvest_source_and_records_use_all(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inventory_id, harvest_id, source_id, lot_id, disposition_id = (uuid4() for _ in range(5))
    amount = HarvestQuantity(kind="item_count", value=Decimal("10"), is_approximate=False)
    inventory = SimpleNamespace(
        id=inventory_id,
        harvest_id=harvest_id,
        material_kind="seed",
        state="active",
        correction_version=3,
    )
    harvest = Harvest(
        id=harvest_id,
        plant_id=source_id,
        plant_group_id=None,
        occurred_on_precision="month",
        occurred_on_year=2026,
        occurred_on_month=5,
        occurred_on_day=None,
    )
    plant = Plant(id=source_id, botanical_identity_id=uuid4())
    lot = SimpleNamespace(id=lot_id)
    disposition = SimpleNamespace(id=disposition_id)
    database = SessionStub({Harvest: harvest, Plant: plant})
    created_payloads: list[SeedLotCreate] = []
    disposition_payloads: list[DispositionCreate] = []
    monkeypatch.setattr(service, "lock_lineage_writes", lambda _db: None)
    monkeypatch.setattr(stock, "locked_inventory", lambda _db, _id: inventory)
    monkeypatch.setattr(stock, "quantity", lambda _row: amount)
    monkeypatch.setattr(stock, "disposition_result", lambda *_args: (amount, None))

    def record_disposition(_db: object, _id: object, payload: DispositionCreate) -> object:
        disposition_payloads.append(payload)
        return disposition

    def create_lot(_db: object, payload: SeedLotCreate) -> object:
        created_payloads.append(payload)
        return lot

    monkeypatch.setattr(stock, "record_disposition", record_disposition)
    monkeypatch.setattr(service, "create_seed_lot", create_lot)
    monkeypatch.setattr(
        service, "_quantity_values", lambda _quantity: {"quantity_kind": "seed_count"}
    )

    result = service.create(
        cast(Session, database),
        inventory_id,
        ConversionCreate.model_validate(
            {
                "mode": "use_all",
                "quantity": {
                    "kind": "seed_count",
                    "value": "10",
                    "is_approximate": False,
                },
            }
        ),
    )

    assert result.inventory_id == inventory_id
    assert result.disposition_id == disposition_id
    assert result.seed_lot_id == lot_id
    assert result.source_correction_version == 3
    created_payload = created_payloads[0]
    assert created_payload.source_kind == "collection_produced"
    assert created_payload.producer_plant_id == source_id
    assert created_payload.botanical_identity_id == plant.botanical_identity_id
    assert created_payload.harvest_date is not None
    assert created_payload.harvest_date.month == 5
    assert disposition_payloads[0].mode == "use_all"
    assert database.added == [result]
    assert database.flush_count == 1


def test_create_rejects_mismatched_exact_use_all_target(monkeypatch: pytest.MonkeyPatch) -> None:
    inventory_id = uuid4()
    inventory = SimpleNamespace(
        material_kind="seed",
        state="active",
    )
    before = HarvestQuantity(kind="item_count", value=Decimal("10"), is_approximate=False)
    monkeypatch.setattr(service, "lock_lineage_writes", lambda _db: None)
    monkeypatch.setattr(stock, "locked_inventory", lambda _db, _id: inventory)
    monkeypatch.setattr(stock, "quantity", lambda _row: before)

    with pytest.raises(EventDomainConflictError, match="same exact target"):
        service.create(
            cast(Session, SessionStub({})),
            inventory_id,
            ConversionCreate.model_validate(
                {
                    "mode": "use_all",
                    "quantity": {
                        "kind": "seed_count",
                        "value": "9",
                        "is_approximate": False,
                    },
                }
            ),
        )

    monkeypatch.setattr(
        stock,
        "quantity",
        lambda _row: HarvestQuantity(
            kind="weight", value=Decimal("1"), unit="kg", is_approximate=False
        ),
    )
    with pytest.raises(EventDomainConflictError, match="units are not converted"):
        service.create(
            cast(Session, SessionStub({})),
            inventory_id,
            ConversionCreate.model_validate({"mode": "use_all"}),
        )


def test_evaluate_allows_unchanged_conversion_and_lists_blockers() -> None:
    conversion_id, inventory_id, harvest_id, source_id, lot_id, disposition_id = (
        uuid4() for _ in range(6)
    )
    conversion = HarvestSeedLotConversion(
        id=conversion_id,
        inventory_id=inventory_id,
        disposition_id=disposition_id,
        seed_lot_id=lot_id,
        quantity_kind="seed_count",
        quantity_value=Decimal("10"),
        quantity_unit=None,
        quantity_is_approximate=False,
        source_correction_version=2,
        status="applied",
    )
    inventory = SimpleNamespace(
        id=inventory_id,
        harvest_id=harvest_id,
        state="active",
        correction_version=2,
        quantity_kind="item_count",
        quantity_value=Decimal("10"),
        quantity_unit=None,
        quantity_is_approximate=False,
    )
    lot = SimpleNamespace(
        id=lot_id,
        source_kind="collection_produced",
        producer_plant_id=source_id,
        producer_plant_group_id=None,
        lifecycle="active",
        quantity_kind="seed_count",
        quantity_value=Decimal("10"),
        quantity_unit=None,
        quantity_is_approximate=False,
    )
    disposition = SimpleNamespace(
        id=disposition_id,
        after_state="active",
        after_quantity_kind="item_count",
        after_quantity_value=Decimal("10"),
        after_quantity_unit=None,
        after_quantity_is_approximate=False,
    )
    harvest = SimpleNamespace(plant_id=source_id, plant_group_id=None)
    values = {
        HarvestSeedLotConversion: conversion,
        Inventory: inventory,
        SeedLot: lot,
        Disposition: disposition,
        Harvest: harvest,
    }
    safe_db = SessionStub(values, [conversion, lot, None, None, None])
    safe = service.evaluate(cast(Session, safe_db), conversion_id)[-1]
    assert safe.status == "safe"
    assert safe.reasons == []

    conversion.status = "reversed"
    inventory.state = "depleted"
    inventory.correction_version = 4
    lot.source_kind = "purchased"
    lot.lifecycle = "exhausted"
    blocked_db = SessionStub(values, [conversion, lot, uuid4(), uuid4(), uuid4()])
    blocked = service.evaluate(cast(Session, blocked_db), conversion_id)[-1]
    assert blocked.status == "blocked"
    assert len(blocked.reasons) == 6


def test_reverse_restores_snapshots_and_rejects_blocked_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inventory = SimpleNamespace(state="depleted")
    lot = SimpleNamespace(lifecycle="active")
    conversion = SimpleNamespace(status="applied", reversed_at=None)
    disposition = SimpleNamespace(
        before_state="active",
        before_quantity_kind="item_count",
        before_quantity_value=Decimal("4"),
        before_quantity_unit=None,
        before_quantity_is_approximate=False,
    )
    before = HarvestQuantity(kind="item_count", value=Decimal("4"), is_approximate=False)
    monkeypatch.setattr(
        service,
        "evaluate",
        lambda *_args, **_kwargs: (
            conversion,
            inventory,
            lot,
            disposition,
            SimpleNamespace(status="safe", reasons=[]),
        ),
    )
    monkeypatch.setattr(stock, "quantity", lambda *_args: before)
    monkeypatch.setattr(
        stock, "set_quantity", lambda _row, value: setattr(inventory, "restored", value)
    )
    monkeypatch.setattr(service, "utc_now", lambda: "now")
    database = SessionStub({})

    service.reverse(cast(Session, database), uuid4())
    assert conversion.status == "reversed"
    assert inventory.state == "active"
    assert inventory.restored == before
    assert lot.lifecycle == "reversed"
    assert conversion.status == "reversed"
    assert conversion.reversed_at == "now"
    assert database.flush_count == 1

    monkeypatch.setattr(
        service,
        "evaluate",
        lambda *_args, **_kwargs: (
            conversion,
            inventory,
            lot,
            disposition,
            SimpleNamespace(status="blocked", reasons=["later work"]),
        ),
    )
    with pytest.raises(EventDomainConflictError, match="later work"):
        service.reverse(cast(Session, database), uuid4())


def test_conversion_api_success_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    database = SessionStub({})
    actor = cast(AuthenticatedActor, object())
    conversion_id, lot_id, inventory_id = uuid4(), uuid4(), uuid4()
    row = SimpleNamespace(id=conversion_id)
    monkeypatch.setattr(api, "require_owner", lambda _actor: None)
    monkeypatch.setattr(
        service,
        "list_conversions",
        lambda _db, **_filters: [row],
    )
    monkeypatch.setattr(
        service,
        "create",
        lambda _db, _id, _payload: SimpleNamespace(id=conversion_id, seed_lot_id=lot_id),
    )
    monkeypatch.setattr(
        service,
        "evaluate",
        lambda *_args: (None, None, None, None, SimpleNamespace(status="safe", reasons=[])),
    )
    monkeypatch.setattr(
        service, "reverse", lambda *_args: SimpleNamespace(id=conversion_id, seed_lot_id=lot_id)
    )

    listed = api.list_all(cast(Session, database), actor, inventory_id=inventory_id)
    assert [item.id for item in listed] == [row.id]
    created = api.create(
        inventory_id,
        ConversionCreate.model_validate({"mode": "use_all"}),
        cast(Session, database),
        actor,
    )
    assert created.id == row.id
    assert database.commit_count == 1
    assert api.eligibility(conversion_id, cast(Session, database), actor).status == "safe"
    reversed_result = api.reverse(conversion_id, cast(Session, database), actor)
    assert reversed_result.id == row.id
    assert database.commit_count == 2


def test_conversion_api_maps_missing_eligibility(monkeypatch: pytest.MonkeyPatch) -> None:
    database = SessionStub({})

    def missing(*_args: object) -> object:
        raise LookupError("Seed lot conversion not found")

    def mapped(db: object, failure: Exception) -> None:
        assert db is database
        assert isinstance(failure, LookupError)
        raise RuntimeError("mapped conflict")

    monkeypatch.setattr(service, "evaluate", missing)
    monkeypatch.setattr(api, "error", mapped)
    with pytest.raises(RuntimeError, match="mapped conflict"):
        api.eligibility(uuid4(), cast(Session, database), cast(AuthenticatedActor, object()))


def test_list_conversions_projects_typed_source_and_target_snapshots() -> None:
    conversion_id, inventory_id, harvest_id, item_id, disposition_id, lot_id = (
        uuid4() for _ in range(6)
    )
    moment = datetime.now(UTC)
    conversion = SimpleNamespace(
        id=conversion_id,
        inventory_id=inventory_id,
        disposition_id=disposition_id,
        seed_lot_id=lot_id,
        status="applied",
        quantity_kind="seed_count",
        quantity_value=Decimal("7"),
        quantity_unit=None,
        quantity_is_approximate=False,
        created_at=moment,
        reversed_at=None,
    )
    inventory = SimpleNamespace(harvest_id=harvest_id, harvest_item_id=item_id)
    disposition = SimpleNamespace(
        before_state="active",
        before_quantity_kind="item_count",
        before_quantity_value=Decimal("10"),
        before_quantity_unit=None,
        before_quantity_is_approximate=False,
        after_state="active",
        after_quantity_kind="item_count",
        after_quantity_value=Decimal("3"),
        after_quantity_unit=None,
        after_quantity_is_approximate=False,
    )
    lot = SimpleNamespace(label="Packet A")
    database = SessionStub({})
    database.rows = [(conversion, inventory, disposition, lot)]

    rows = service.list_conversions(
        cast(Session, database), inventory_id=inventory_id, seed_lot_id=lot_id
    )

    assert len(rows) == 1
    assert rows[0].harvest_id == harvest_id
    assert rows[0].harvest_item_id == item_id
    assert rows[0].seed_lot_label == "Packet A"
    transferred = rows[0].quantity
    before = rows[0].before.quantity
    after = rows[0].after.quantity
    assert transferred is not None
    assert before is not None
    assert after is not None
    assert transferred.value == 7
    assert before.value == 10
    assert after.value == 3
    assert rows[0].created_at == moment
