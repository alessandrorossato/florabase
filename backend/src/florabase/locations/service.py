from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from florabase.locations.model import Location
from florabase.locations.schemas import LocationCreate, LocationUpdate


@dataclass(frozen=True)
class LocationHierarchyError(Exception):
    code: str
    message: str


class LocationNotFoundError(Exception):
    pass


def _all_locations(database: Session, *, lock: bool = False) -> list[Location]:
    statement = select(Location).order_by(func.lower(Location.name), Location.id)
    if lock:
        statement = statement.with_for_update()
    return list(database.scalars(statement))


def list_locations(database: Session) -> list[Location]:
    return _all_locations(database)


def get_location(database: Session, location_id: UUID) -> Location | None:
    return database.get(Location, location_id)


def _require(locations: list[Location], location_id: UUID) -> Location:
    try:
        return next(location for location in locations if location.id == location_id)
    except StopIteration as exc:
        raise LocationNotFoundError from exc


def _ancestors(location: Location, by_id: dict[UUID, Location]) -> list[Location]:
    ancestors: list[Location] = []
    seen = {location.id}
    parent_id = location.parent_id
    while parent_id is not None:
        if parent_id in seen:
            raise RuntimeError("Persisted location hierarchy contains a cycle")
        seen.add(parent_id)
        parent = by_id.get(parent_id)
        if parent is None:
            raise RuntimeError("Persisted location hierarchy has a missing parent")
        ancestors.append(parent)
        parent_id = parent.parent_id
    return ancestors


def display_path(location: Location, locations: list[Location]) -> str:
    by_id = {item.id: item for item in locations}
    return " → ".join(
        [ancestor.name for ancestor in reversed(_ancestors(location, by_id))] + [location.name]
    )


def _validate_parent(
    location: Location | None,
    parent_id: UUID | None,
    locations: list[Location],
) -> None:
    if parent_id is None:
        return
    by_id = {item.id: item for item in locations}
    parent = by_id.get(parent_id)
    if parent is None:
        raise LocationHierarchyError("location_parent_not_found", "Parent location not found")
    if location is not None and (
        parent.id == location.id
        or any(ancestor.id == location.id for ancestor in _ancestors(parent, by_id))
    ):
        raise LocationHierarchyError(
            "location_cycle", "A location cannot be moved beneath itself or a descendant"
        )
    if (location is None or location.retired_at is None) and (
        parent.retired_at is not None
        or any(ancestor.retired_at is not None for ancestor in _ancestors(parent, by_id))
    ):
        raise LocationHierarchyError(
            "location_retired_ancestor", "An active location cannot have a retired ancestor"
        )


def create_location(database: Session, payload: LocationCreate) -> Location:
    locations = _all_locations(database, lock=True)
    _validate_parent(None, payload.parent_id, locations)
    location = Location(**payload.model_dump(mode="python"))
    database.add(location)
    database.flush()
    return location


def update_location(database: Session, location_id: UUID, payload: LocationUpdate) -> Location:
    locations = _all_locations(database, lock=True)
    location = _require(locations, location_id)
    _validate_parent(location, payload.parent_id, locations)
    location.name = payload.name
    location.parent_id = payload.parent_id
    location.updated_at = datetime.now(UTC)
    database.flush()
    return location


def set_location_retired(database: Session, location_id: UUID, *, retired: bool) -> Location:
    locations = _all_locations(database, lock=True)
    location = _require(locations, location_id)
    by_id = {item.id: item for item in locations}
    if retired:
        active_descendants = [
            item
            for item in locations
            if item.retired_at is None
            and item.id != location.id
            and any(ancestor.id == location.id for ancestor in _ancestors(item, by_id))
        ]
        if active_descendants:
            raise LocationHierarchyError(
                "location_active_descendants",
                "Retire active descendants before retiring this location",
            )
    elif any(ancestor.retired_at is not None for ancestor in _ancestors(location, by_id)):
        raise LocationHierarchyError(
            "location_retired_ancestor",
            "Reactivate retired ancestors before reactivating this location",
        )
    now = datetime.now(UTC)
    location.retired_at = now if retired else None
    location.updated_at = now
    database.flush()
    return location
