from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock
from uuid import UUID, uuid7

import pytest
from fastapi import HTTPException, Response
from pydantic import ValidationError

from florabase.locations import api
from florabase.locations import service as location_service
from florabase.locations.model import Location
from florabase.locations.schemas import (
    LocationCreate,
    LocationResponse,
    LocationUpdate,
    LocationUsageCount,
    LocationUsageScope,
    LocationUsageSummary,
)
from florabase.locations.service import (
    LocationHierarchyError,
    LocationIntegrityError,
    LocationNotFoundError,
    create_location,
    delete_location,
    display_path,
    get_location,
    list_locations,
    location_usage,
    require_location_for_scope,
    set_location_retired,
    update_location,
)


def location(**overrides: object) -> Location:
    values: dict[str, object] = {
        "id": uuid7(),
        "name": "Greenhouse",
        "parent_id": None,
        "supports_plants": True,
        "supports_sowings": True,
        "supports_seed_lots": True,
        "retired_at": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    values.update(overrides)
    return Location(**values)


def test_location_payload_normalizes_name_and_rejects_invalid_values() -> None:
    assert LocationCreate(name="  Upper\t shelf ").name == "Upper shelf"
    for name in (" ", "Bad\x00name"):
        with pytest.raises(ValidationError):
            LocationCreate(name=name)
    with pytest.raises(ValidationError):
        LocationCreate.model_validate({"name": "Shelf", "unknown": True})
    with pytest.raises(ValidationError):
        LocationCreate(name="Shelf", usage_scopes=set())


def test_location_response_and_display_path_are_derived() -> None:
    root = location(name="House")
    child = location(name="Basement", parent_id=root.id)
    leaf = location(name="Drawer A", parent_id=child.id)
    assert display_path(leaf, [root, child, leaf]) == "House → Basement → Drawer A"
    response = LocationResponse.from_model(
        leaf, display_path=display_path(leaf, [root, child, leaf])
    )
    assert response.parent_id == child.id
    assert response.display_path == "House → Basement → Drawer A"


def test_location_service_create_get_list_and_update() -> None:
    root = location(name="Greenhouse")
    database = MagicMock()
    database.scalars.return_value = [root]
    created = create_location(
        database,
        LocationCreate(
            name="Shelf 1",
            parent_id=root.id,
            usage_scopes={LocationUsageScope.SEED_LOTS},
        ),
    )
    assert created.name == "Shelf 1"
    assert created.parent_id == root.id
    assert created.supports_seed_lots is True
    assert created.supports_plants is False
    database.add.assert_called_once_with(created)

    database.get.return_value = created
    assert get_location(database, created.id) is created
    assert list_locations(database) == [root]

    database.scalars.return_value = [root, created]
    updated = update_location(
        database, created.id, LocationUpdate(name="Upper shelf", parent_id=None)
    )
    assert updated.name == "Upper shelf"
    assert updated.parent_id is None
    assert updated.updated_at.tzinfo is UTC


def test_location_service_rejects_missing_parent_self_and_descendant_cycles() -> None:
    root = location(name="House")
    child = location(name="Basement", parent_id=root.id)
    leaf = location(name="Drawer A", parent_id=child.id)
    database = MagicMock()
    database.scalars.return_value = [root, child, leaf]

    with pytest.raises(LocationHierarchyError) as missing:
        create_location(database, LocationCreate(name="Shelf", parent_id=uuid7()))
    assert missing.value.code == "location_parent_not_found"

    for parent_id in (root.id, child.id, leaf.id):
        database.scalars.return_value = [root, child, leaf]
        with pytest.raises(LocationHierarchyError) as cycle:
            update_location(database, root.id, LocationUpdate(name="House", parent_id=parent_id))
        assert cycle.value.code == "location_cycle"

    database.scalars.return_value = [root]
    with pytest.raises(LocationNotFoundError):
        update_location(database, uuid7(), LocationUpdate(name="Missing"))


def test_location_service_enforces_retirement_and_reactivation_invariants() -> None:
    root = location(name="House")
    child = location(name="Basement", parent_id=root.id)
    leaf = location(name="Cabinet", parent_id=child.id)
    database = MagicMock()
    database.scalars.return_value = [root, child, leaf]
    with pytest.raises(LocationHierarchyError) as blocked:
        set_location_retired(database, root.id, retired=True)
    assert blocked.value.code == "location_active_descendants"

    leaf.retired_at = datetime.now(UTC)
    child.retired_at = datetime.now(UTC)
    database.scalars.return_value = [root, child, leaf]
    retired = set_location_retired(database, root.id, retired=True)
    assert retired.retired_at is not None

    database.scalars.return_value = [root, child, leaf]
    with pytest.raises(LocationHierarchyError) as ancestor:
        set_location_retired(database, leaf.id, retired=False)
    assert ancestor.value.code == "location_retired_ancestor"

    leaf.retired_at = None
    database.scalars.return_value = [root, child, leaf]
    with pytest.raises(LocationHierarchyError):
        update_location(database, leaf.id, LocationUpdate(name=leaf.name, parent_id=child.id))


def test_location_api_success_conflicts_not_found_and_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = location()
    actor = cast(Any, SimpleNamespace(owner=True))
    database = MagicMock()
    monkeypatch.setattr(api, "list_locations", lambda _: [item])
    assert api.list_all(actor, database)[0].id == item.id

    monkeypatch.setattr(api, "create_location", lambda _database, _payload: item)
    response = Response()
    assert api.create(LocationCreate(name=item.name), response, actor, database).id == item.id
    assert response.headers["location"].endswith(str(item.id))

    monkeypatch.setattr(api, "get_location", lambda _database, _id: item)
    assert api.read(item.id, actor, database).id == item.id
    monkeypatch.setattr(api, "update_location", lambda _database, _id, _payload: item)
    assert api.update(item.id, LocationUpdate(name=item.name), actor, database).id == item.id
    monkeypatch.setattr(api, "set_location_retired", lambda _database, _id, retired: item)
    assert api.retire(item.id, actor, database).id == item.id
    assert api.reactivate(item.id, actor, database).id == item.id

    monkeypatch.setattr(api, "get_location", lambda _database, _id: None)
    with pytest.raises(HTTPException) as not_found:
        api.read(uuid7(), actor, database)
    assert not_found.value.status_code == 404

    monkeypatch.setattr(
        api,
        "update_location",
        lambda _database, _id, _payload: (_ for _ in ()).throw(LocationNotFoundError()),
    )
    with pytest.raises(HTTPException) as missing_update:
        api.update(uuid7(), LocationUpdate(name="Missing"), actor, database)
    assert missing_update.value.status_code == 404

    monkeypatch.setattr(
        api,
        "create_location",
        lambda _database, _payload: (_ for _ in ()).throw(
            LocationHierarchyError("location_cycle", "Cycle")
        ),
    )
    with pytest.raises(HTTPException) as conflict:
        api.create(LocationCreate(name="Shelf"), Response(), actor, database)
    assert conflict.value.status_code == 409
    assert cast(dict[str, str], conflict.value.detail)["code"] == "location_cycle"

    with pytest.raises(HTTPException) as forbidden:
        api.create(
            LocationCreate(name="Shelf"),
            Response(),
            cast(Any, SimpleNamespace(owner=False)),
            database,
        )
    assert forbidden.value.status_code == 403


def test_location_model_uses_uuid_identity() -> None:
    item = location()
    assert isinstance(item.id, UUID)
    assert item.id.version == 7


def test_location_assignment_scope_is_locked_and_authoritative() -> None:
    item = location(supports_plants=False, supports_sowings=True)
    database = MagicMock()
    database.get.return_value = item
    with pytest.raises(LocationIntegrityError) as blocked:
        require_location_for_scope(database, item.id, LocationUsageScope.PLANTS)
    assert blocked.value.code == "location_scope_not_supported"
    assert require_location_for_scope(database, item.id, LocationUsageScope.SOWINGS) is item
    assert database.get.call_args.kwargs == {
        "with_for_update": True,
        "populate_existing": True,
    }


def test_location_usage_combines_plants_and_groups_and_separates_active() -> None:
    location_id = uuid7()
    database = MagicMock()
    database.execute.side_effect = [
        [(location_id, 2, 1)],
        [(location_id, 3, 1)],
        [(location_id, 4, 2)],
        [(location_id, 5, 3)],
    ]
    usage = location_usage(database)[location_id]
    assert usage.plants == LocationUsageCount(active=2, total=5)
    assert usage.sowings == LocationUsageCount(active=2, total=4)
    assert usage.seed_lots == LocationUsageCount(active=3, total=5)


def test_scope_removal_and_delete_preserve_references(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = location()
    child = location(parent_id=item.id)
    database = MagicMock()
    database.scalars.return_value = [item]
    monkeypatch.setattr(
        location_service,
        "location_usage",
        lambda _database: {
            item.id: LocationUsageSummary(plants=LocationUsageCount(active=1, total=2))
        },
    )
    with pytest.raises(LocationIntegrityError) as scope:
        update_location(
            database,
            item.id,
            LocationUpdate(name=item.name, usage_scopes={LocationUsageScope.SOWINGS}),
        )
    assert scope.value.code == "location_scope_in_use"

    database.scalars.return_value = [item, child]
    with pytest.raises(LocationIntegrityError) as children:
        delete_location(database, item.id)
    assert children.value.code == "location_has_children"

    database.scalars.return_value = [item]
    with pytest.raises(LocationIntegrityError) as used:
        delete_location(database, item.id)
    assert used.value.code == "location_in_use"

    monkeypatch.setattr(location_service, "location_usage", lambda _database: {})
    database.scalar.return_value = 0
    delete_location(database, item.id)
    database.delete.assert_called_once_with(item)
