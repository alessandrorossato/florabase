from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock
from uuid import UUID, uuid7

import pytest
from fastapi import HTTPException, Response

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.geographic_places.model import GeographicPlace
from florabase.locations.model import Location
from florabase.seed_lots import api, service
from florabase.seed_lots.model import SeedLot
from florabase.seed_lots.schemas import SeedLotCreate, SeedLotUpdate
from florabase.seed_lots.service import SeedLotProjection, SeedLotReferenceNotFoundError
from florabase.suppliers.model import Supplier


def models() -> tuple[SeedLot, BotanicalIdentity, Supplier, GeographicPlace, Location]:
    now = datetime.now(UTC)
    identity = BotanicalIdentity(
        id=uuid7(), scientific_name="Phoenix dactylifera", created_at=now, updated_at=now
    )
    supplier = Supplier(
        id=uuid7(),
        name="Seed source",
        kind="seller",
        created_at=now,
        updated_at=now,
    )
    place = GeographicPlace(
        id=uuid7(),
        name="Oasis",
        parent_id=None,
        place_kind="canonical",
        created_at=now,
        updated_at=now,
    )
    location = Location(id=uuid7(), name="Drawer", created_at=now, updated_at=now)
    lot = SeedLot(
        id=uuid7(),
        botanical_identity_id=identity.id,
        supplier_id=supplier.id,
        material_provenance_place_id=place.id,
        location_id=location.id,
        label="Packet",
        source_kind="other",
        source_detail="Archive",
        acquisition_date_precision="year",
        acquisition_date_year=2020,
        harvest_date_precision="month",
        harvest_date_year=2019,
        harvest_date_month=8,
        quantity_kind="weight",
        quantity_value=Decimal("4.5"),
        quantity_unit="g",
        quantity_is_approximate=False,
        expected_viability_until_precision="day",
        expected_viability_until_year=2025,
        expected_viability_until_month=4,
        expected_viability_until_day=3,
        lifecycle="active",
        notes="Keep",
        created_at=now,
        updated_at=now,
    )
    return lot, identity, supplier, place, location


def full_payload(
    identity_id: UUID, supplier: Supplier, place: GeographicPlace, location: Location
) -> SeedLotCreate:
    return SeedLotCreate(
        botanical_identity_id=identity_id,
        label="Packet",
        source_kind="other",
        source_detail="Archive",
        supplier_id=supplier.id,
        material_provenance_place_id=place.id,
        acquisition_date={"precision": "year", "year": 2020},
        harvest_date={"precision": "month", "year": 2019, "month": 8},
        quantity={"kind": "weight", "value": "4.5", "unit": "g", "is_approximate": False},
        expected_viability_until={
            "precision": "day",
            "year": 2025,
            "month": 4,
            "day": 3,
        },
        location_id=location.id,
        notes="Keep",
    )


def test_seed_lot_service_create_update_query_and_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lot, identity, supplier, place, location = models()
    payload = full_payload(identity.id, supplier, place, location)
    database = MagicMock()
    by_id = {
        identity.id: identity,
        supplier.id: supplier,
        place.id: place,
        location.id: location,
    }
    database.get.side_effect = lambda _model, item_id, **_kwargs: by_id.get(item_id)

    created = service.create_seed_lot(database, payload)
    assert payload.quantity is not None
    assert created.quantity_value == payload.quantity.value
    assert created.acquisition_date_precision == "year"
    database.add.assert_called_once_with(created)

    update = SeedLotUpdate.model_validate(payload.model_dump())
    updated = service.update_seed_lot(database, created, update)
    assert updated.updated_at.tzinfo is UTC

    row = (lot, identity, supplier, place, location)
    database.execute.return_value.one_or_none.return_value = row
    assert service.get_seed_lot(database, lot.id) == SeedLotProjection(*row)
    database.execute.return_value.one_or_none.return_value = None
    assert service.get_seed_lot(database, uuid7()) is None
    database.execute.return_value.__iter__.return_value = iter([row])
    assert service.list_seed_lots(database) == [SeedLotProjection(*row)]

    monkeypatch.setattr(service, "list_geographic_places", lambda _: [place])
    monkeypatch.setattr(service, "list_locations", lambda _: [location])
    response = service.responses(database, [SeedLotProjection(*row)])[0]
    assert response.botanical_identity.display_label == "Phoenix dactylifera"
    assert response.supplier is not None
    assert response.supplier.name == "Seed source"
    assert response.material_provenance is not None
    assert response.material_provenance.display_path == "Oasis"
    assert response.location is not None
    assert response.location.display_path == "Drawer"
    assert response.quantity is not None
    assert str(response.quantity.value) == "4.5"
    assert response.acquisition_date is not None
    assert response.acquisition_date.precision.value == "year"

    minimal = models()
    minimal[0].supplier_id = None
    minimal[0].material_provenance_place_id = None
    minimal[0].location_id = None
    minimal[0].quantity_kind = None
    minimal_projection = SeedLotProjection(minimal[0], minimal[1], None, None, None)
    minimal_response = service.responses(database, [minimal_projection])[0]
    assert minimal_response.supplier is None
    assert minimal_response.material_provenance is None
    assert minimal_response.location is None
    assert minimal_response.quantity is None


@pytest.mark.parametrize(
    ("field", "code"),
    [
        ("botanical_identity_id", "botanical_identity_not_found"),
        ("supplier_id", "supplier_not_found"),
        ("material_provenance_place_id", "geographic_place_not_found"),
        ("location_id", "location_not_found"),
    ],
)
def test_seed_lot_service_reports_each_missing_reference(field: str, code: str) -> None:
    _, identity, supplier, place, location = models()
    payload = full_payload(identity.id, supplier, place, location)
    database = MagicMock()
    by_id: dict[object, object] = {
        identity.id: identity,
        supplier.id: supplier,
        place.id: place,
        location.id: location,
    }
    missing_id = getattr(payload, field)
    by_id.pop(missing_id)
    database.get.side_effect = lambda _model, item_id, **_kwargs: by_id.get(item_id)
    with pytest.raises(SeedLotReferenceNotFoundError) as error:
        service.create_seed_lot(database, payload)
    assert error.value.code == code


def test_seed_lot_api_success_and_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    lot, identity, supplier, place, location = models()
    projection = SeedLotProjection(lot, identity, supplier, place, location)
    payload = full_payload(identity.id, supplier, place, location)
    actor = cast(Any, SimpleNamespace(owner=True))
    database = MagicMock()
    response_model = service.responses(database, [projection])[0]

    monkeypatch.setattr(api, "list_seed_lots", lambda _: [projection])
    monkeypatch.setattr(api, "responses", lambda _database, _items: [response_model])
    assert api.list_all(actor, database)[0].id == lot.id

    monkeypatch.setattr(api, "create_seed_lot", lambda _database, _payload: lot)
    monkeypatch.setattr(api, "get_seed_lot", lambda _database, _id: projection)
    response = Response()
    assert api.create(payload, response, actor, database).id == lot.id
    assert response.headers["location"].endswith(str(lot.id))
    assert api.read(lot.id, actor, database).id == lot.id

    monkeypatch.setattr(api, "update_seed_lot", lambda _database, item, _payload: item)
    assert (
        api.update(lot.id, SeedLotUpdate.model_validate(payload.model_dump()), actor, database).id
        == lot.id
    )

    monkeypatch.setattr(api, "get_seed_lot", lambda _database, _id: None)
    with pytest.raises(HTTPException) as missing:
        api.read(uuid7(), actor, database)
    assert missing.value.status_code == 404

    reference_error = SeedLotReferenceNotFoundError("supplier_not_found", "Supplier not found")
    monkeypatch.setattr(
        api,
        "create_seed_lot",
        lambda _database, _payload: (_ for _ in ()).throw(reference_error),
    )
    with pytest.raises(HTTPException) as invalid_reference:
        api.create(payload, Response(), actor, database)
    assert invalid_reference.value.status_code == 404

    with pytest.raises(HTTPException) as forbidden:
        api.create(payload, Response(), cast(Any, SimpleNamespace(owner=False)), database)
    assert forbidden.value.status_code == 403
