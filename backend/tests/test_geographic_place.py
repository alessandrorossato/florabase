import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock
from uuid import UUID, uuid7

import pytest
from fastapi import HTTPException, Response
from pydantic import ValidationError

from florabase.geographic_places import api
from florabase.geographic_places import service as geographic_service
from florabase.geographic_places.model import GeographicPlace
from florabase.geographic_places.schemas import (
    GeographicPlaceCreate,
    GeographicPlaceResponse,
    GeographicPlaceUpdate,
)
from florabase.geographic_places.service import (
    GeographicPlaceHierarchyError,
    create_geographic_place,
    delete_geographic_place,
    display_path,
    get_geographic_place,
    list_geographic_places,
    set_geographic_place_retired,
    update_geographic_place,
)

SNAPSHOT = Path(__file__).parents[1] / "alembic/data/geographic_places_cldr_48_2_1.json"


def place(**overrides: object) -> GeographicPlace:
    values: dict[str, object] = {
        "id": uuid7(),
        "name": "Thailand",
        "parent_id": None,
        "place_kind": "canonical",
        "source_name": "unicode_cldr",
        "source_version": "48.2.1",
        "source_code_type": "iso_3166_1_alpha_2",
        "source_code": "TH",
        "retired_at": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    values.update(overrides)
    return GeographicPlace(**values)


def test_committed_canonical_dataset_is_one_valid_acyclic_tree() -> None:
    document = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert document["source"] == "unicode_cldr"
    assert document["version"] == "48.2.1"
    assert document["license"] == "Unicode-3.0"
    records = document["records"]
    assert len(records) == 287
    identifiers = [(record["source_code_type"], record["source_code"]) for record in records]
    assert len(identifiers) == len(set(identifiers))
    assert len({record["id"] for record in records}) == len(records)
    by_code = {record["source_code"]: record for record in records}
    roots = [record for record in records if record["parent_source_code"] is None]
    assert [(root["source_code"], root["name"]) for root in roots] == [("001", "World")]
    for record in records:
        assert UUID(record["id"]).version == 7
        if record["parent_source_code"] is not None:
            assert record["parent_source_code"] in by_code
        seen: set[str] = set()
        current = record
        while current["parent_source_code"] is not None:
            assert current["source_code"] not in seen
            seen.add(current["source_code"])
            current = by_code[current["parent_source_code"]]

    assert by_code["BR"]["parent_source_code"] == "005"
    assert by_code["005"]["name"] == "South America"
    assert by_code["005"]["parent_source_code"] == "419"
    assert by_code["419"]["parent_source_code"] == "019"
    assert by_code["TH"]["parent_source_code"] == "035"


def test_payload_response_path_and_custom_hierarchy_rules() -> None:
    assert GeographicPlaceCreate(name="  Chiang\tMai ", parent_id=uuid7()).name == "Chiang Mai"
    for name in (" ", "Bad\x00name"):
        with pytest.raises(ValidationError):
            GeographicPlaceCreate(name=name, parent_id=uuid7())

    world = place(name="World", source_code="001", source_code_type="un_m49")
    asia = place(name="Asia", parent_id=world.id, source_code="142", source_code_type="un_m49")
    thailand = place(parent_id=asia.id)
    custom = place(
        name="Chiang Mai",
        parent_id=thailand.id,
        place_kind="custom",
        source_name=None,
        source_version=None,
        source_code_type=None,
        source_code=None,
    )
    places = [world, asia, thailand, custom]
    assert display_path(custom, places) == "World → Asia → Thailand → Chiang Mai"
    duplicate = place(
        name="Chiang Mai",
        parent_id=world.id,
        place_kind="custom",
        source_name=None,
        source_version=None,
        source_code_type=None,
        source_code=None,
    )
    assert display_path(custom, [*places, duplicate]) != display_path(
        duplicate, [*places, duplicate]
    )
    response = GeographicPlaceResponse.from_model(custom, display_path=display_path(custom, places))
    assert response.place_kind == "custom"
    assert response.source_code is None

    database = MagicMock()
    database.scalars.return_value = places
    created = create_geographic_place(
        database, GeographicPlaceCreate(name="Doi Suthep", parent_id=custom.id)
    )
    assert created.place_kind == "custom"
    assert created.source_code is None

    database.scalars.return_value = places
    with pytest.raises(GeographicPlaceHierarchyError) as immutable:
        update_geographic_place(
            database,
            thailand.id,
            GeographicPlaceUpdate(name="Renamed", parent_id=asia.id),
        )
    assert immutable.value.code == "canonical_geographic_place_immutable"

    database.scalars.return_value = places
    with pytest.raises(GeographicPlaceHierarchyError) as cycle:
        update_geographic_place(
            database,
            custom.id,
            GeographicPlaceUpdate(name="Chiang Mai", parent_id=custom.id),
        )
    assert cycle.value.code == "geographic_place_cycle"

    database.scalars.return_value = places
    with pytest.raises(GeographicPlaceHierarchyError) as canonical_retirement:
        set_geographic_place_retired(database, thailand.id, retired=True)
    assert canonical_retirement.value.code == "canonical_geographic_place_immutable"


def test_custom_update_list_get_retirement_and_reactivation_rules() -> None:
    world = place(name="World", source_code="001", source_code_type="un_m49")
    custom = place(
        name="Region",
        parent_id=world.id,
        place_kind="custom",
        source_name=None,
        source_version=None,
        source_code_type=None,
        source_code=None,
    )
    child = place(
        name="Local",
        parent_id=custom.id,
        place_kind="custom",
        source_name=None,
        source_version=None,
        source_code_type=None,
        source_code=None,
    )
    database = MagicMock()
    database.get.return_value = custom
    database.scalars.return_value = [world, custom, child]
    assert get_geographic_place(database, custom.id) is custom
    assert list_geographic_places(database) == [world, custom, child]

    database.scalars.return_value = [world, custom, child]
    updated = update_geographic_place(
        database,
        custom.id,
        GeographicPlaceUpdate(name="Renamed region", parent_id=world.id),
    )
    assert updated.name == "Renamed region"
    assert updated.updated_at.tzinfo is UTC

    database.scalars.return_value = [world, custom, child]
    with pytest.raises(GeographicPlaceHierarchyError) as descendants:
        set_geographic_place_retired(database, custom.id, retired=True)
    assert descendants.value.code == "geographic_place_active_descendants"

    child.retired_at = datetime.now(UTC)
    database.scalars.return_value = [world, custom, child]
    assert set_geographic_place_retired(database, custom.id, retired=True).retired_at
    database.scalars.return_value = [world, custom, child]
    with pytest.raises(GeographicPlaceHierarchyError) as ancestor:
        set_geographic_place_retired(database, child.id, retired=False)
    assert ancestor.value.code == "geographic_place_retired_ancestor"


def test_geographic_place_api_success_conflict_not_found_and_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = place()
    actor = cast(Any, SimpleNamespace(owner=True))
    database = MagicMock()
    monkeypatch.setattr(api, "list_geographic_places", lambda _: [item])
    assert api.list_all(actor, database)[0].id == item.id

    monkeypatch.setattr(api, "create_geographic_place", lambda _database, _payload: item)
    response = Response()
    payload = GeographicPlaceCreate(name="Local", parent_id=uuid7())
    assert api.create(payload, response, actor, database).id == item.id
    assert response.headers["location"].endswith(str(item.id))

    monkeypatch.setattr(api, "get_geographic_place", lambda _database, _id: item)
    assert api.read(item.id, actor, database).id == item.id
    monkeypatch.setattr(api, "update_geographic_place", lambda _database, _id, _payload: item)
    update = GeographicPlaceUpdate(name="Local", parent_id=uuid7())
    assert api.update(item.id, update, actor, database).id == item.id
    monkeypatch.setattr(api, "set_geographic_place_retired", lambda _database, _id, retired: item)
    assert api.retire(item.id, actor, database).id == item.id
    assert api.reactivate(item.id, actor, database).id == item.id

    monkeypatch.setattr(api, "get_geographic_place", lambda _database, _id: None)
    with pytest.raises(HTTPException) as not_found:
        api.read(uuid7(), actor, database)
    assert not_found.value.status_code == 404

    monkeypatch.setattr(
        api,
        "create_geographic_place",
        lambda _database, _payload: (_ for _ in ()).throw(
            GeographicPlaceHierarchyError("geographic_place_cycle", "Cycle")
        ),
    )
    with pytest.raises(HTTPException) as conflict:
        api.create(payload, Response(), actor, database)
    assert conflict.value.status_code == 409

    with pytest.raises(HTTPException) as forbidden:
        api.create(payload, Response(), cast(Any, SimpleNamespace(owner=False)), database)
    assert forbidden.value.status_code == 403


def test_geographic_usage_and_safe_leaf_delete(monkeypatch: pytest.MonkeyPatch) -> None:
    used_id = uuid7()
    database = MagicMock()
    database.execute.side_effect = [
        [(used_id, 1)],
        [(used_id, 2)],
        [(used_id, 3)],
        [(used_id, 4)],
    ]
    direct, sites = geographic_service.geographic_place_usage(database)
    assert direct[used_id] == 6
    assert sites[used_id] == 4

    world = place(name="World", source_code="001", source_code_type="un_m49")
    custom = place(
        name="Local area",
        parent_id=world.id,
        place_kind="custom",
        source_name=None,
        source_version=None,
        source_code_type=None,
        source_code=None,
    )
    child = place(
        name="Child area",
        parent_id=custom.id,
        place_kind="custom",
        source_name=None,
        source_version=None,
        source_code_type=None,
        source_code=None,
    )

    database.scalars.return_value = [world, custom]
    with pytest.raises(GeographicPlaceHierarchyError) as canonical:
        delete_geographic_place(database, world.id)
    assert canonical.value.code == "canonical_geographic_place_immutable"

    database.scalars.return_value = [world, custom, child]
    with pytest.raises(GeographicPlaceHierarchyError) as children:
        delete_geographic_place(database, custom.id)
    assert children.value.code == "geographic_place_has_children"

    database.scalars.return_value = [world, custom]
    monkeypatch.setattr(
        geographic_service, "geographic_place_usage", lambda _: ({custom.id: 1}, {})
    )
    with pytest.raises(GeographicPlaceHierarchyError) as retained:
        delete_geographic_place(database, custom.id)
    assert retained.value.code == "geographic_place_in_use"

    monkeypatch.setattr(
        geographic_service, "geographic_place_usage", lambda _: ({}, {custom.id: 1})
    )
    with pytest.raises(GeographicPlaceHierarchyError) as site_dependency:
        delete_geographic_place(database, custom.id)
    assert site_dependency.value.code == "geographic_place_has_provenance_sites"

    monkeypatch.setattr(geographic_service, "geographic_place_usage", lambda _: ({}, {}))
    delete_geographic_place(database, custom.id)
    database.delete.assert_called_once_with(custom)
