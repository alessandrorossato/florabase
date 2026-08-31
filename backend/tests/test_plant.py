from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock
from uuid import uuid7

import pytest
from fastapi import HTTPException, Response

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.geographic_places.model import GeographicPlace
from florabase.locations.model import Location
from florabase.plants import api, service
from florabase.plants.model import Plant, PlantGroup
from florabase.plants.schemas import PlantCreate, PlantGroupCreate, PlantGroupUpdate, PlantUpdate
from florabase.plants.service import (
    PlantGroupProjection,
    PlantProjection,
    PlantReferenceNotFoundError,
)
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing
from florabase.suppliers.model import Supplier


def models() -> tuple[
    Plant,
    PlantGroup,
    BotanicalIdentity,
    Sowing,
    SeedLot,
    BotanicalIdentity,
    Supplier,
    GeographicPlace,
    Location,
]:
    now = datetime.now(UTC)
    identity = BotanicalIdentity(
        id=uuid7(), scientific_name="Solanum quitoense", created_at=now, updated_at=now
    )
    upstream_identity = BotanicalIdentity(
        id=uuid7(), scientific_name="Solanum sp.", created_at=now, updated_at=now
    )
    lot = SeedLot(
        id=uuid7(),
        botanical_identity_id=upstream_identity.id,
        label="Packet",
        created_at=now,
        updated_at=now,
    )
    sowing = Sowing(
        id=uuid7(),
        seed_lot_id=lot.id,
        label="Tray",
        lifecycle="failed",
        created_at=now,
        updated_at=now,
    )
    supplier = Supplier(id=uuid7(), name="Nursery", created_at=now, updated_at=now)
    place = GeographicPlace(
        id=uuid7(),
        name="Ecuador",
        place_kind="custom",
        created_at=now,
        updated_at=now,
    )
    location = Location(id=uuid7(), name="Bench", created_at=now, updated_at=now)
    plant = Plant(
        id=uuid7(),
        botanical_identity_id=identity.id,
        originating_sowing_id=sowing.id,
        direct_origin_kind=None,
        label="Individual",
        collection_entry_date_precision="month",
        collection_entry_date_year=2026,
        collection_entry_date_month=8,
        location_id=location.id,
        lifecycle="dead",
        created_at=now,
        updated_at=now,
    )
    group = PlantGroup(
        id=uuid7(),
        botanical_identity_id=identity.id,
        direct_origin_kind="purchased",
        supplier_id=supplier.id,
        material_provenance_place_id=place.id,
        location_id=location.id,
        quantity_value=12,
        quantity_is_approximate=True,
        lifecycle="active",
        created_at=now,
        updated_at=now,
    )
    return plant, group, identity, sowing, lot, upstream_identity, supplier, place, location


def direct_payload(
    identity: BotanicalIdentity, supplier: Supplier, place: GeographicPlace, location: Location
) -> PlantCreate:
    return PlantCreate(
        botanical_identity_id=identity.id,
        direct_origin_kind="other",
        direct_origin_detail="exchange table",
        supplier_id=supplier.id,
        material_provenance_place_id=place.id,
        label="Individual",
        collection_entry_date={"precision": "day", "year": 2026, "month": 8, "day": 31},
        location_id=location.id,
        lifecycle="lost",
        notes="Retained.",
    )


def database_with_references(items: tuple[object, ...]) -> MagicMock:
    database = MagicMock()
    lookup = {(type(item), item.id): item for item in items if hasattr(item, "id")}
    database.get.side_effect = lambda model, item_id: lookup.get((model, item_id))
    return database


def test_services_create_update_project_and_preserve_independent_lineage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plant, group, identity, sowing, lot, upstream, supplier, place, location = models()
    database = database_with_references(
        (identity, sowing, lot, upstream, supplier, place, location)
    )
    created = service.create_plant(database, direct_payload(identity, supplier, place, location))
    assert created.direct_origin_detail == "exchange table"
    assert created.collection_entry_date_day == 31
    sowing_payload = PlantUpdate(botanical_identity_id=identity.id, originating_sowing_id=sowing.id)
    service.update_plant(database, created, sowing_payload)
    assert created.originating_sowing_id == sowing.id
    assert created.direct_origin_kind is None
    assert created.updated_at.tzinfo is UTC

    group_payload = PlantGroupCreate(
        botanical_identity_id=identity.id,
        quantity={"value": 5, "is_approximate": False},
    )
    created_group = service.create_plant_group(database, group_payload)
    assert created_group.quantity_value == 5
    corrected = PlantGroupUpdate(
        botanical_identity_id=identity.id,
        quantity={"value": 0, "is_approximate": False},
        lifecycle="dead",
    )
    service.update_plant_group(database, created_group, corrected)
    assert created_group.lifecycle == "dead"
    assert created_group.quantity_value == 0

    plant_row = (plant, identity, sowing, lot, upstream, None, None, location)
    group_row = (group, identity, None, None, None, supplier, place, location)
    database.execute.return_value.one_or_none.side_effect = [plant_row, group_row]
    assert service.get_plant(database, plant.id) == PlantProjection(*plant_row)
    assert service.get_plant_group(database, group.id) == PlantGroupProjection(*group_row)
    database.execute.return_value.__iter__.side_effect = [iter([plant_row]), iter([group_row])]
    assert service.list_plants(database) == [PlantProjection(*plant_row)]
    assert service.list_plant_groups(database) == [PlantGroupProjection(*group_row)]

    monkeypatch.setattr(service, "list_locations", lambda _: [location])
    monkeypatch.setattr(service, "list_geographic_places", lambda _: [place])
    plant_response = service.plant_responses(database, [PlantProjection(*plant_row)])[0]
    assert plant_response.botanical_identity.display_label == "Solanum quitoense"
    assert plant_response.originating_sowing is not None
    assert plant_response.originating_sowing.botanical_identity_display_label == "Solanum sp."
    assert plant_response.location is not None
    assert plant_response.location.display_path == "Bench"
    group_response = service.plant_group_responses(database, [PlantGroupProjection(*group_row)])[0]
    assert group_response.quantity is not None
    assert group_response.quantity.value == 12
    assert group_response.supplier is not None
    assert group_response.material_provenance is not None
    assert group_response.material_provenance.display_path == "Ecuador"


@pytest.mark.parametrize(
    ("missing_type", "code"),
    [
        (BotanicalIdentity, "botanical_identity_not_found"),
        (Sowing, "sowing_not_found"),
        (Supplier, "supplier_not_found"),
        (GeographicPlace, "geographic_place_not_found"),
        (Location, "location_not_found"),
    ],
)
def test_service_friendly_missing_reference(missing_type: type[object], code: str) -> None:
    _, _, identity, sowing, _, _, supplier, place, location = models()
    payload = PlantCreate(
        botanical_identity_id=identity.id,
        originating_sowing_id=sowing.id,
        location_id=location.id,
    )
    if missing_type in (Supplier, GeographicPlace):
        payload = direct_payload(identity, supplier, place, location)
    database = database_with_references((identity, sowing, supplier, place, location))
    original = database.get.side_effect
    database.get.side_effect = lambda model, item_id: (
        None if model is missing_type else original(model, item_id)
    )
    with pytest.raises(PlantReferenceNotFoundError) as error:
        service.create_plant(database, payload)
    assert error.value.code == code


def test_api_routes_success_not_found_reference_and_owner_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plant, group, identity, sowing, lot, upstream, supplier, place, location = models()
    plant_projection = PlantProjection(plant, identity, sowing, lot, upstream, None, None, location)
    group_projection = PlantGroupProjection(
        group, identity, None, None, None, supplier, place, location
    )
    database = MagicMock()
    monkeypatch.setattr(service, "list_locations", lambda _: [location])
    monkeypatch.setattr(service, "list_geographic_places", lambda _: [place])
    plant_response = service.plant_responses(database, [plant_projection])[0]
    group_response = service.plant_group_responses(database, [group_projection])[0]
    monkeypatch.setattr(api, "list_plants", lambda _: [plant_projection])
    monkeypatch.setattr(api, "list_plant_groups", lambda _: [group_projection])
    monkeypatch.setattr(api, "plant_responses", lambda _db, _items: [plant_response])
    monkeypatch.setattr(api, "plant_group_responses", lambda _db, _items: [group_response])
    monkeypatch.setattr(api, "get_plant", lambda _db, _id: plant_projection)
    monkeypatch.setattr(api, "get_plant_group", lambda _db, _id: group_projection)
    monkeypatch.setattr(api, "create_plant", lambda _db, _payload: plant)
    monkeypatch.setattr(api, "create_plant_group", lambda _db, _payload: group)
    monkeypatch.setattr(api, "update_plant", lambda _db, item, _payload: item)
    monkeypatch.setattr(api, "update_plant_group", lambda _db, item, _payload: item)
    actor = cast(Any, SimpleNamespace(owner=True))
    plant_write = PlantCreate(botanical_identity_id=identity.id, originating_sowing_id=sowing.id)
    group_write = PlantGroupCreate(botanical_identity_id=identity.id)

    assert api.list_all_plants(actor, database)[0].id == plant.id
    assert api.list_all_plant_groups(actor, database)[0].id == group.id
    response = Response()
    assert api.create_one_plant(plant_write, response, actor, database).id == plant.id
    assert response.headers["location"].endswith(str(plant.id))
    assert api.read_plant(plant.id, actor, database).id == plant.id
    assert (
        api.update_one_plant(
            plant.id, PlantUpdate.model_validate(plant_write.model_dump()), actor, database
        ).id
        == plant.id
    )
    assert api.create_one_plant_group(group_write, Response(), actor, database).id == group.id
    assert api.read_plant_group(group.id, actor, database).id == group.id
    assert (
        api.update_one_plant_group(
            group.id, PlantGroupUpdate.model_validate(group_write.model_dump()), actor, database
        ).id
        == group.id
    )

    monkeypatch.setattr(api, "get_plant", lambda _db, _id: None)
    with pytest.raises(HTTPException) as missing:
        api.read_plant(uuid7(), actor, database)
    assert missing.value.status_code == 404
    monkeypatch.setattr(api, "get_plant_group", lambda _db, _id: None)
    with pytest.raises(HTTPException) as missing_group:
        api.read_plant_group(uuid7(), actor, database)
    assert missing_group.value.status_code == 404

    error = PlantReferenceNotFoundError("location_not_found", "Location not found")
    monkeypatch.setattr(api, "create_plant", lambda _db, _payload: (_ for _ in ()).throw(error))
    with pytest.raises(HTTPException) as invalid:
        api.create_one_plant(plant_write, Response(), actor, database)
    assert invalid.value.status_code == 404
    with pytest.raises(HTTPException) as forbidden:
        api.create_one_plant(
            plant_write, Response(), cast(Any, SimpleNamespace(owner=False)), database
        )
    assert forbidden.value.status_code == 403
