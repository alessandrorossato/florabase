from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock
from uuid import uuid7

import pytest
from fastapi import HTTPException, Response

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.locations.model import Location
from florabase.seed_lots.model import SeedLot
from florabase.sowings import api, service
from florabase.sowings.model import Sowing
from florabase.sowings.schemas import SowingCreate, SowingUpdate
from florabase.sowings.service import SowingProjection, SowingReferenceNotFoundError


def models() -> tuple[Sowing, SeedLot, BotanicalIdentity, Location]:
    now = datetime.now(UTC)
    identity = BotanicalIdentity(
        id=uuid7(), scientific_name="Testa plant", created_at=now, updated_at=now
    )
    lot = SeedLot(
        id=uuid7(),
        botanical_identity_id=identity.id,
        label="Packet",
        lifecycle="exhausted",
        quantity_kind="seed_count",
        quantity_value=Decimal("100"),
        quantity_is_approximate=False,
        created_at=now,
        updated_at=now,
    )
    location = Location(id=uuid7(), name="Bench", created_at=now, updated_at=now)
    sowing = Sowing(
        id=uuid7(),
        seed_lot_id=lot.id,
        label="Tray",
        sowing_date_precision="month",
        sowing_date_year=2026,
        sowing_date_month=8,
        quantity_kind="seed_count",
        quantity_value=Decimal("20"),
        quantity_is_approximate=False,
        germinated_count=12,
        location_id=location.id,
        lifecycle="failed",
        temperature_min_c=Decimal("20.5"),
        created_at=now,
        updated_at=now,
    )
    return sowing, lot, identity, location


def payload(lot: SeedLot, location: Location) -> SowingCreate:
    return SowingCreate(
        seed_lot_id=lot.id,
        label="Tray",
        sowing_date={"precision": "day", "year": 2026, "month": 8, "day": 31},
        quantity={"kind": "seed_count", "value": 20, "is_approximate": False},
        germinated_count=12,
        location_id=location.id,
        temperature_min_c="20.5",
        lifecycle="failed",
    )


def test_sowing_service_create_update_projection_and_inventory_regression(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sowing, lot, identity, location = models()
    write = payload(lot, location)
    database = MagicMock()
    database.get.side_effect = lambda model, item_id: (
        lot
        if model is SeedLot and item_id == lot.id
        else location
        if model is Location and item_id == location.id
        else None
    )
    original_quantity = lot.quantity_value
    created = service.create_sowing(database, write)
    assert created.sowing_date_day == 31
    assert lot.quantity_value == original_quantity
    updated = service.update_sowing(
        database, created, SowingUpdate.model_validate(write.model_dump())
    )
    assert updated.updated_at.tzinfo is UTC
    assert lot.quantity_value == original_quantity
    row = (sowing, lot, identity, location)
    database.execute.return_value.one_or_none.return_value = row
    assert service.get_sowing(database, sowing.id) == SowingProjection(*row)
    database.execute.return_value.__iter__.return_value = iter([row])
    assert service.list_sowings(database) == [SowingProjection(*row)]
    monkeypatch.setattr(service, "list_locations", lambda _: [location])
    response = service.responses(database, [SowingProjection(*row)])[0]
    assert response.seed_lot.botanical_identity_display_label == "Testa plant"
    assert response.seed_lot.lifecycle == "exhausted"
    assert response.location is not None
    assert response.location.display_path == "Bench"
    assert response.quantity is not None
    assert response.quantity.value == Decimal("20")


@pytest.mark.parametrize(
    ("missing", "code"), [("lot", "seed_lot_not_found"), ("location", "location_not_found")]
)
def test_sowing_service_reports_missing_references(missing: str, code: str) -> None:
    _, lot, _, location = models()
    write = payload(lot, location)
    database = MagicMock()
    database.get.side_effect = lambda model, _id: (
        None
        if (missing == "lot" and model is SeedLot) or (missing == "location" and model is Location)
        else lot
    )
    with pytest.raises(SowingReferenceNotFoundError) as error:
        service.create_sowing(database, write)
    assert error.value.code == code


def test_sowing_api_routes_and_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    sowing, lot, identity, location = models()
    projection = SowingProjection(sowing, lot, identity, location)
    write = payload(lot, location)
    actor = cast(Any, SimpleNamespace(owner=True))
    database = MagicMock()
    response_model = service.responses(database, [projection])[0]
    monkeypatch.setattr(api, "list_sowings", lambda _: [projection])
    monkeypatch.setattr(api, "responses", lambda _db, _items: [response_model])
    monkeypatch.setattr(api, "get_sowing", lambda _db, _id: projection)
    monkeypatch.setattr(api, "create_sowing", lambda _db, _payload: sowing)
    monkeypatch.setattr(api, "update_sowing", lambda _db, item, _payload: item)
    assert api.list_all(actor, database)[0].id == sowing.id
    response = Response()
    assert api.create(write, response, actor, database).id == sowing.id
    assert response.headers["location"].endswith(str(sowing.id))
    assert api.read(sowing.id, actor, database).id == sowing.id
    assert (
        api.update(sowing.id, SowingUpdate.model_validate(write.model_dump()), actor, database).id
        == sowing.id
    )
    monkeypatch.setattr(api, "get_sowing", lambda _db, _id: None)
    with pytest.raises(HTTPException) as missing:
        api.read(uuid7(), actor, database)
    assert missing.value.status_code == 404
    error = SowingReferenceNotFoundError("seed_lot_not_found", "SeedLot not found")
    monkeypatch.setattr(api, "create_sowing", lambda _db, _payload: (_ for _ in ()).throw(error))
    with pytest.raises(HTTPException) as invalid:
        api.create(write, Response(), actor, database)
    assert invalid.value.status_code == 404
    with pytest.raises(HTTPException) as forbidden:
        api.create(write, Response(), cast(Any, SimpleNamespace(owner=False)), database)
    assert forbidden.value.status_code == 403
