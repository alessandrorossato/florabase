from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock
from uuid import uuid7

import pytest
from fastapi import HTTPException, Response
from pydantic import ValidationError

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot
from florabase.suppliers import api
from florabase.suppliers.model import Supplier, SupplierKind
from florabase.suppliers.schemas import SupplierCreate, SupplierResponse, SupplierUpdate
from florabase.suppliers.service import (
    create_supplier,
    get_supplier,
    get_supplier_detail,
    list_suppliers,
    set_supplier_retired,
    update_supplier,
)


def supplier(**overrides: object) -> Supplier:
    values: dict[str, object] = {
        "id": uuid7(),
        "name": "Rare Palm Seeds",
        "kind": SupplierKind.SELLER.value,
        "website": None,
        "email": None,
        "phone": None,
        "notes": None,
        "retired_at": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    values.update(overrides)
    return Supplier(**values)


def test_supplier_payload_normalizes_optional_contact_and_notes() -> None:
    payload = SupplierCreate(
        name="  Rare\t Palm   Seeds ",
        kind="seller",
        website=" https://example.com/catalog ",
        email=" sales@example.com ",
        phone=" +39  0123  456 ",
        notes="\r\n International seller.\r\nShips seasonally. \r\n",
    )
    assert payload.model_dump(mode="json") == {
        "name": "Rare Palm Seeds",
        "kind": "seller",
        "website": "https://example.com/catalog",
        "email": "sales@example.com",
        "phone": "+39 0123 456",
        "notes": "International seller.\nShips seasonally.",
    }


def test_supplier_payload_maps_optional_blanks_to_null() -> None:
    payload = SupplierCreate(
        name="Local exchange",
        kind=SupplierKind.EXCHANGE,
        website=" ",
        email="\t",
        phone=" ",
        notes="\r\n",
    )
    assert payload.website is payload.email is payload.phone is payload.notes is None


@pytest.mark.parametrize("kind", list(SupplierKind))
def test_every_supplier_kind_is_supported(kind: SupplierKind) -> None:
    assert SupplierCreate(name="Source", kind=kind).kind is kind


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", " "),
        ("name", "Bad\x00Name"),
        ("kind", "wholesaler"),
        ("website", "ftp://example.com"),
        ("website", "https:///missing-host"),
        ("email", "not-an-email"),
        ("phone", "bad\x07phone"),
        ("notes", "bad\x00notes"),
    ],
)
def test_supplier_payload_rejects_invalid_values(field: str, value: str) -> None:
    values = {"name": "Source", "kind": "other", field: value}
    with pytest.raises(ValidationError):
        SupplierCreate.model_validate(values)


def test_supplier_response_reads_model() -> None:
    item = supplier(email="hello@example.com")
    response = SupplierResponse.from_model(item)
    assert response.id == item.id
    assert response.kind is SupplierKind.SELLER
    assert response.email == "hello@example.com"


def test_supplier_service_create_get_list_update_and_lifecycle() -> None:
    database = MagicMock()
    created = create_supplier(database, SupplierCreate(name="Person", kind="person"))
    assert created.name == "Person"
    assert created.kind == "person"
    database.add.assert_called_once_with(created)
    database.flush.assert_called_once()

    database.get.return_value = created
    assert get_supplier(database, created.id) is created
    listed = [supplier(name="Alpha"), supplier(name="Beta")]
    database.execute.return_value.tuples.return_value = [
        (listed[0], 1, 2, 3, 4, 5, 6),
        (listed[1], 0, 0, 0, 0, 0, 0),
    ]
    summaries = list_suppliers(database)
    assert [item.name for item in summaries] == ["Alpha", "Beta"]
    assert summaries[0].usage_counts.direct_records_active == 9
    assert summaries[0].usage_counts.direct_records_total == 12

    updated = update_supplier(
        database,
        created,
        SupplierUpdate(name="Private person", kind="person", phone="123"),
    )
    assert updated.name == "Private person"
    assert updated.phone == "123"
    assert updated.updated_at.tzinfo is UTC

    retired = set_supplier_retired(database, created, retired=True)
    assert retired.retired_at is not None
    reactivated = set_supplier_retired(database, created, retired=False)
    assert reactivated.retired_at is None


def test_supplier_detail_builds_direct_links_counts_and_known_recent_dates() -> None:
    now = datetime.now(UTC)
    item = supplier()
    identity = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Clitoria ternatea",
        cultivar_name=None,
        common_name=None,
        created_at=now,
        updated_at=now,
    )
    seed_lot = SeedLot(
        id=uuid7(),
        botanical_identity_id=identity.id,
        label="Thai seeds",
        source_kind="purchased",
        supplier_id=item.id,
        acquisition_date_precision="day",
        acquisition_date_year=2026,
        acquisition_date_month=8,
        acquisition_date_day=30,
        lifecycle="active",
    )
    plant = Plant(
        id=uuid7(),
        botanical_identity_id=identity.id,
        direct_origin_kind="purchased",
        supplier_id=item.id,
        collection_entry_date_precision=None,
        collection_entry_date_year=None,
        collection_entry_date_month=None,
        collection_entry_date_day=None,
        lifecycle="transferred",
    )
    group = PlantGroup(
        id=uuid7(),
        botanical_identity_id=identity.id,
        direct_origin_kind="gift_exchange",
        supplier_id=item.id,
        collection_entry_date_precision="month",
        collection_entry_date_year=2026,
        collection_entry_date_month=9,
        collection_entry_date_day=None,
        lifecycle="active",
    )
    count_result = MagicMock()
    count_result.one.return_value = (1, 1, 0, 1, 1, 1)
    seed_result = MagicMock()
    seed_result.tuples.return_value = [(seed_lot, identity)]
    plant_result = MagicMock()
    plant_result.tuples.return_value = [(plant, identity)]
    group_result = MagicMock()
    group_result.tuples.return_value = [(group, identity)]
    database = MagicMock()
    database.execute.side_effect = [count_result, seed_result, plant_result, group_result]

    detail = get_supplier_detail(database, item)

    assert detail.usage_counts.direct_records_active == 2
    assert detail.usage_counts.direct_records_total == 3
    assert detail.seed_lots[0].botanical_identity.display_label == "Clitoria ternatea"
    assert detail.plants[0].collection_entry_date is None
    assert [recent.record_type for recent in detail.recent_acquisitions] == [
        "plant_group",
        "seed_lot",
    ]


def test_supplier_api_success_and_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    item = supplier()
    actor = cast(Any, SimpleNamespace(owner=True))
    database = MagicMock()
    summary = SimpleNamespace(id=item.id)
    monkeypatch.setattr(api, "list_suppliers", lambda _: [summary])
    assert api.list_all(actor, database)[0].id == item.id

    monkeypatch.setattr(api, "create_supplier", lambda _database, _payload: item)
    response = Response()
    created = api.create(SupplierCreate(name=item.name, kind="seller"), response, actor, database)
    assert created.id == item.id
    assert response.headers["location"].endswith(str(item.id))

    monkeypatch.setattr(api, "get_supplier", lambda _database, _id: item)
    detail = SimpleNamespace(id=item.id)
    monkeypatch.setattr(api, "get_supplier_detail", lambda _database, _supplier: detail)
    assert api.read(item.id, actor, database).id == item.id
    monkeypatch.setattr(api, "update_supplier", lambda _database, existing, _payload: existing)
    assert (
        api.update(item.id, SupplierUpdate(name=item.name, kind="seller"), actor, database).id
        == item.id
    )

    monkeypatch.setattr(api, "set_supplier_retired", lambda _database, existing, retired: existing)
    assert api.retire(item.id, actor, database).id == item.id
    assert api.reactivate(item.id, actor, database).id == item.id

    monkeypatch.setattr(api, "get_supplier", lambda _database, _id: None)
    with pytest.raises(HTTPException) as error:
        api.read(uuid7(), actor, database)
    assert error.value.status_code == 404
    assert cast(dict[str, str], error.value.detail)["code"] == "supplier_not_found"


def test_supplier_api_requires_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    actor = cast(Any, SimpleNamespace(owner=False))
    with pytest.raises(HTTPException) as error:
        api.create(SupplierCreate(name="Source", kind="other"), Response(), actor, MagicMock())
    assert error.value.status_code == 403
