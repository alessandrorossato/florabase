from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from florabase.events.model import Event
from florabase.locations.model import Location
from florabase.locations.schemas import (
    LocationCreate,
    LocationUpdate,
    LocationUsageCount,
    LocationUsageScope,
    LocationUsageSummary,
)
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing


@dataclass(frozen=True)
class LocationHierarchyError(Exception):
    code: str
    message: str


class LocationNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class LocationIntegrityError(Exception):
    code: str
    message: str


def _all_locations(database: Session, *, lock: bool = False) -> list[Location]:
    statement = select(Location).order_by(func.lower(Location.name), Location.id)
    if lock:
        statement = statement.with_for_update()
    return list(database.scalars(statement))


def list_locations(database: Session) -> list[Location]:
    return _all_locations(database)


def get_location(database: Session, location_id: UUID) -> Location | None:
    return database.get(Location, location_id)


def require_location_for_scope(
    database: Session, location_id: UUID | None, scope: LocationUsageScope
) -> Location | None:
    if location_id is None:
        return None
    location = database.get(Location, location_id, with_for_update=True, populate_existing=True)
    if location is None:
        raise LocationNotFoundError
    supported = {
        LocationUsageScope.PLANTS: location.supports_plants,
        LocationUsageScope.SOWINGS: location.supports_sowings,
        LocationUsageScope.SEED_LOTS: location.supports_seed_lots,
    }[scope]
    if supported is False:
        raise LocationIntegrityError(
            "location_scope_not_supported",
            f"Location does not support {scope.value.replace('_', ' ')} assignments",
        )
    return location


def _grouped_usage(
    database: Session, model: type[Plant] | type[PlantGroup] | type[Sowing] | type[SeedLot]
) -> dict[UUID, LocationUsageCount]:
    rows = database.execute(
        select(
            model.location_id,
            func.count(),
            func.count().filter(model.lifecycle == "active"),
        )
        .where(model.location_id.is_not(None))
        .group_by(model.location_id)
    )
    return {
        location_id: LocationUsageCount(total=total, active=active)
        for location_id, total, active in rows
        if location_id is not None
    }


def location_usage(database: Session) -> dict[UUID, LocationUsageSummary]:
    plants = _grouped_usage(database, Plant)
    groups = _grouped_usage(database, PlantGroup)
    sowings = _grouped_usage(database, Sowing)
    seed_lots = _grouped_usage(database, SeedLot)
    location_ids = set(plants) | set(groups) | set(sowings) | set(seed_lots)
    result: dict[UUID, LocationUsageSummary] = {}
    for location_id in location_ids:
        plant = plants.get(location_id, LocationUsageCount())
        group = groups.get(location_id, LocationUsageCount())
        result[location_id] = LocationUsageSummary(
            plants=LocationUsageCount(
                active=plant.active + group.active,
                total=plant.total + group.total,
            ),
            sowings=sowings.get(location_id, LocationUsageCount()),
            seed_lots=seed_lots.get(location_id, LocationUsageCount()),
        )
    return result


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
    values = payload.model_dump(mode="python", exclude={"usage_scopes"})
    location = Location(
        **values,
        supports_plants=LocationUsageScope.PLANTS in payload.usage_scopes,
        supports_sowings=LocationUsageScope.SOWINGS in payload.usage_scopes,
        supports_seed_lots=LocationUsageScope.SEED_LOTS in payload.usage_scopes,
    )
    database.add(location)
    database.flush()
    return location


def update_location(database: Session, location_id: UUID, payload: LocationUpdate) -> Location:
    locations = _all_locations(database, lock=True)
    location = _require(locations, location_id)
    _validate_parent(location, payload.parent_id, locations)
    usage = location_usage(database).get(location.id, LocationUsageSummary())
    removals = (
        (LocationUsageScope.PLANTS, location.supports_plants, usage.plants.total),
        (LocationUsageScope.SOWINGS, location.supports_sowings, usage.sowings.total),
        (LocationUsageScope.SEED_LOTS, location.supports_seed_lots, usage.seed_lots.total),
    )
    for scope, previously_supported, count in removals:
        if previously_supported and scope not in payload.usage_scopes and count:
            raise LocationIntegrityError(
                "location_scope_in_use",
                f"Cannot remove the {scope.value.replace('_', ' ')} scope while {count} "
                f"record{'s' if count != 1 else ''} still use this Location",
            )
    location.name = payload.name
    location.parent_id = payload.parent_id
    location.supports_plants = LocationUsageScope.PLANTS in payload.usage_scopes
    location.supports_sowings = LocationUsageScope.SOWINGS in payload.usage_scopes
    location.supports_seed_lots = LocationUsageScope.SEED_LOTS in payload.usage_scopes
    location.updated_at = datetime.now(UTC)
    database.flush()
    return location


def delete_location(database: Session, location_id: UUID) -> None:
    locations = _all_locations(database, lock=True)
    location = _require(locations, location_id)
    if any(item.parent_id == location.id for item in locations):
        raise LocationIntegrityError(
            "location_has_children", "Move or delete child Locations before deleting this Location"
        )
    usage = location_usage(database).get(location.id, LocationUsageSummary())
    reference_count = usage.plants.total + usage.sowings.total + usage.seed_lots.total
    event_count = database.scalar(
        select(func.count()).select_from(Event).where(Event.destination_location_id == location.id)
    )
    if reference_count or event_count:
        raise LocationIntegrityError(
            "location_in_use",
            "This Location is retained by collection or Event history and cannot be deleted",
        )
    database.delete(location)
    database.flush()


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
