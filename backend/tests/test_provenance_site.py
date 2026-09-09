from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock
from uuid import uuid7

import pytest
from fastapi import HTTPException, Response
from pydantic import ValidationError

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.geographic_places.model import GeographicPlace
from florabase.plants.model import Plant, PlantGroup
from florabase.provenance_sites import api
from florabase.provenance_sites import service as site_service
from florabase.provenance_sites.model import ProvenanceSite
from florabase.provenance_sites.schemas import (
    ProvenanceMapResponse,
    ProvenanceSiteCreate,
    ProvenanceSiteResponse,
    ProvenanceSiteUpdate,
    ProvenanceSiteUsage,
)
from florabase.provenance_sites.service import ProvenanceSiteError
from florabase.seed_lots.model import SeedLot


def site(**overrides: object) -> ProvenanceSite:
    values: dict[str, object] = {
        "id": uuid7(),
        "name": "Monte Pellegrino",
        "geographic_place_id": None,
        "latitude": None,
        "longitude": None,
        "coordinate_accuracy_m": None,
        "notes": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    values.update(overrides)
    return ProvenanceSite(**values)


def site_response(item: ProvenanceSite) -> ProvenanceSiteResponse:
    return ProvenanceSiteResponse(
        id=item.id,
        name=item.name,
        geographic_place_id=item.geographic_place_id,
        geographic_place_path=None,
        latitude=item.latitude,
        longitude=item.longitude,
        coordinate_accuracy_m=item.coordinate_accuracy_m,
        notes=item.notes,
        usage=ProvenanceSiteUsage(),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def test_provenance_site_normalizes_partial_data_and_valid_coordinates() -> None:
    payload = ProvenanceSiteCreate(
        name="  Monte   Pellegrino  ",
        geographic_place_id=uuid7(),
        latitude=Decimal("38.166667"),
        longitude=Decimal("13.350000"),
        coordinate_accuracy_m=Decimal("25.5"),
        notes="  ridge\r\npoint  ",
    )
    assert payload.name == "Monte Pellegrino"
    assert payload.notes == "ridge\npoint"
    assert ProvenanceSiteCreate(name="Historical locality").latitude is None


@pytest.mark.parametrize(
    "values",
    [
        {"latitude": 91, "longitude": 0},
        {"latitude": 0, "longitude": -181},
        {"latitude": 10},
        {"longitude": 10},
        {"coordinate_accuracy_m": -1},
        {"coordinate_accuracy_m": 1},
    ],
)
def test_provenance_site_rejects_invalid_coordinate_semantics(
    values: dict[str, int],
) -> None:
    with pytest.raises(ValidationError):
        ProvenanceSiteCreate(name="Site", **values)


def test_provenance_site_service_crud_usage_and_safe_delete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = MagicMock()
    place = GeographicPlace(id=uuid7(), name="Palermo", place_kind="custom")
    database.get.return_value = place
    created = site_service.create_provenance_site(
        database,
        ProvenanceSiteCreate(
            name="Monte Pellegrino",
            geographic_place_id=place.id,
            latitude=38,
            longitude=13,
        ),
    )
    created.id = uuid7()
    database.add.assert_called_once_with(created)
    database.get.return_value = created
    assert site_service.get_provenance_site(database, created.id) is created

    database.scalars.return_value = [created]
    assert site_service.list_provenance_sites(database) == [created]
    updated = site_service.update_provenance_site(
        database,
        created,
        ProvenanceSiteUpdate(name="Monte Pellegrino ridge", notes="Known point"),
    )
    assert updated.name == "Monte Pellegrino ridge"
    assert updated.latitude is None
    assert updated.notes == "Known point"

    used_id = created.id
    database.execute.side_effect = [[(used_id, 2)], [(used_id, 3)], [(used_id, 4)]]
    usage = site_service.site_usage(database)[used_id]
    assert (usage.seed_lots, usage.plants, usage.plant_groups) == (2, 3, 4)

    monkeypatch.setattr(
        site_service,
        "site_usage",
        lambda _: {used_id: ProvenanceSiteUsage(seed_lots=1)},
    )
    with pytest.raises(ProvenanceSiteError) as retained:
        site_service.delete_provenance_site(database, created)
    assert retained.value.code == "provenance_site_in_use"
    monkeypatch.setattr(site_service, "site_usage", lambda _: {})
    site_service.delete_provenance_site(database, created)
    database.delete.assert_called_once_with(created)


def test_provenance_site_service_validates_parent_and_derives_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = MagicMock()
    database.get.return_value = None
    with pytest.raises(ProvenanceSiteError) as missing:
        site_service.create_provenance_site(
            database,
            ProvenanceSiteCreate(name="Site", geographic_place_id=uuid7()),
        )
    assert missing.value.code == "geographic_place_not_found"

    world = GeographicPlace(
        id=uuid7(), name="World", parent_id=None, place_kind="canonical", source_code="001"
    )
    palermo = GeographicPlace(id=uuid7(), name="Palermo", parent_id=world.id, place_kind="custom")
    item = site(geographic_place_id=palermo.id)
    monkeypatch.setattr(site_service, "list_geographic_places", lambda _: [world, palermo])
    monkeypatch.setattr(
        site_service,
        "site_usage",
        lambda _: {item.id: ProvenanceSiteUsage(plants=1)},
    )
    response = site_service.responses(database, [item])[0]
    assert response.geographic_place_path == "World → Palermo"
    assert response.usage.plants == 1


def test_provenance_site_api_success_not_found_and_conflicts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = site()
    rendered = site_response(item)
    actor = cast(Any, SimpleNamespace(owner=True))
    database = MagicMock()
    monkeypatch.setattr(api, "responses", lambda _database, _sites: [rendered])
    monkeypatch.setattr(api, "list_provenance_sites", lambda _: [item])
    assert api.list_all(actor, database) == [rendered]

    monkeypatch.setattr(api, "create_provenance_site", lambda _database, _payload: item)
    http_response = Response()
    assert (
        api.create(ProvenanceSiteCreate(name=item.name), http_response, actor, database) == rendered
    )
    assert http_response.headers["location"].endswith(str(item.id))

    monkeypatch.setattr(api, "get_provenance_site", lambda _database, _id: item)
    assert api.read(item.id, actor, database) == rendered
    monkeypatch.setattr(
        api, "update_provenance_site", lambda _database, existing, _payload: existing
    )
    assert api.update(item.id, ProvenanceSiteUpdate(name=item.name), actor, database) == rendered
    monkeypatch.setattr(api, "delete_provenance_site", lambda _database, _site: None)
    assert api.delete(item.id, actor, database).status_code == 204

    monkeypatch.setattr(api, "get_provenance_site", lambda _database, _id: None)
    with pytest.raises(HTTPException) as not_found:
        api.read(uuid7(), actor, database)
    assert not_found.value.status_code == 404

    monkeypatch.setattr(
        api,
        "create_provenance_site",
        lambda _database, _payload: (_ for _ in ()).throw(
            ProvenanceSiteError("geographic_place_not_found", "Missing")
        ),
    )
    with pytest.raises(HTTPException) as missing_place:
        api.create(ProvenanceSiteCreate(name="Site"), Response(), actor, database)
    assert missing_place.value.status_code == 404

    monkeypatch.setattr(api, "get_provenance_site", lambda _database, _id: item)
    monkeypatch.setattr(
        api,
        "delete_provenance_site",
        lambda _database, _site: (_ for _ in ()).throw(
            ProvenanceSiteError("provenance_site_in_use", "Retained")
        ),
    )
    with pytest.raises(HTTPException) as conflict:
        api.delete(item.id, actor, database)
    assert conflict.value.status_code == 409


def test_collection_provenance_map_bulk_projection_and_ordering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = MagicMock()
    world = GeographicPlace(
        id=uuid7(), name="World", parent_id=None, place_kind="canonical", source_code="001"
    )
    thailand = GeographicPlace(
        id=uuid7(), name="Thailand", parent_id=world.id, place_kind="canonical", source_code="TH"
    )
    mapped = site(
        geographic_place_id=thailand.id,
        latitude=Decimal("18.804900"),
        longitude=Decimal("-98.921600"),
        coordinate_accuracy_m=Decimal("25.500"),
    )
    identity = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Clitoria ternatea",
        cultivar_name="Map blue",
        common_name=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    seed_lot = SeedLot(
        id=uuid7(),
        botanical_identity_id=identity.id,
        provenance_site_id=mapped.id,
        label="Seeds",
        lifecycle="discarded",
    )
    plant = Plant(
        id=uuid7(),
        botanical_identity_id=identity.id,
        provenance_site_id=mapped.id,
        direct_origin_kind="unknown",
        label="Plant",
        lifecycle="active",
    )
    group = PlantGroup(
        id=uuid7(),
        botanical_identity_id=identity.id,
        provenance_site_id=mapped.id,
        direct_origin_kind="unknown",
        label="Group",
        lifecycle="transferred",
    )
    database.scalar.return_value = 2
    database.scalars.return_value = [mapped]

    def rows(values: list[tuple[object, BotanicalIdentity]]) -> MagicMock:
        result = MagicMock()
        result.tuples.return_value = values
        return result

    database.execute.side_effect = [
        rows([(seed_lot, identity)]),
        rows([(plant, identity)]),
        rows([(group, identity)]),
    ]
    monkeypatch.setattr(site_service, "list_geographic_places", lambda _: [world, thailand])

    response = site_service.collection_provenance_map(database)
    assert response.total_provenance_sites == 2
    assert response.coordinate_less_sites == 1
    assert len(response.sites) == 1
    projected = response.sites[0]
    assert projected.geographic_place_path == "World → Thailand"
    assert projected.usage.model_dump() == {
        "seed_lots": 1,
        "plants": 1,
        "plant_groups": 1,
        "total": 3,
    }
    assert [record.record_type for record in projected.records] == [
        "seed_lot",
        "plant",
        "plant_group",
    ]
    assert [record.is_active for record in projected.records] == [False, True, False]
    assert projected.records[0].botanical_identity.display_label == (
        "Clitoria ternatea \u2018Map blue\u2019"
    )
    assert database.execute.call_count == 3


def test_collection_provenance_map_empty_projection_and_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = MagicMock()
    database.scalar.return_value = 0
    database.scalars.return_value = []
    response = site_service.collection_provenance_map(database)
    assert response == ProvenanceMapResponse(
        total_provenance_sites=0, coordinate_less_sites=0, sites=[]
    )
    database.execute.assert_not_called()

    actor = cast(Any, SimpleNamespace(owner=True))
    monkeypatch.setattr(api, "collection_provenance_map", lambda _: response)
    assert api.read_map(actor, database) == response
