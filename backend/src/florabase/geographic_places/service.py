from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from florabase.geographic_places.model import GeographicPlace
from florabase.geographic_places.schemas import GeographicPlaceCreate, GeographicPlaceUpdate
from florabase.plants.model import Plant, PlantGroup
from florabase.provenance_sites.model import ProvenanceSite
from florabase.seed_lots.model import SeedLot


@dataclass(frozen=True)
class GeographicPlaceHierarchyError(Exception):
    code: str
    message: str


class GeographicPlaceNotFoundError(Exception):
    pass


def geographic_place_usage(database: Session) -> tuple[dict[UUID, int], dict[UUID, int]]:
    direct: dict[UUID, int] = {}
    for model in (SeedLot, Plant, PlantGroup):
        rows = database.execute(
            select(model.material_provenance_place_id, func.count())
            .where(model.material_provenance_place_id.is_not(None))
            .group_by(model.material_provenance_place_id)
        )
        for place_id, count in rows:
            if place_id is not None:
                direct[place_id] = direct.get(place_id, 0) + count
    sites = {
        place_id: count
        for place_id, count in database.execute(
            select(ProvenanceSite.geographic_place_id, func.count())
            .where(ProvenanceSite.geographic_place_id.is_not(None))
            .group_by(ProvenanceSite.geographic_place_id)
        )
        if place_id is not None
    }
    return direct, sites


def _all_places(database: Session, *, lock: bool = False) -> list[GeographicPlace]:
    statement = select(GeographicPlace).order_by(
        func.lower(GeographicPlace.name), GeographicPlace.id
    )
    if lock:
        statement = statement.with_for_update()
    return list(database.scalars(statement))


def list_geographic_places(database: Session) -> list[GeographicPlace]:
    return _all_places(database)


def get_geographic_place(database: Session, place_id: UUID) -> GeographicPlace | None:
    return database.get(GeographicPlace, place_id)


def _require(places: list[GeographicPlace], place_id: UUID) -> GeographicPlace:
    try:
        return next(place for place in places if place.id == place_id)
    except StopIteration as exc:
        raise GeographicPlaceNotFoundError from exc


def _ancestors(place: GeographicPlace, by_id: dict[UUID, GeographicPlace]) -> list[GeographicPlace]:
    ancestors: list[GeographicPlace] = []
    seen = {place.id}
    parent_id = place.parent_id
    while parent_id is not None:
        if parent_id in seen:
            raise RuntimeError("Persisted geographic-place hierarchy contains a cycle")
        seen.add(parent_id)
        parent = by_id.get(parent_id)
        if parent is None:
            raise RuntimeError("Persisted geographic-place hierarchy has a missing parent")
        ancestors.append(parent)
        parent_id = parent.parent_id
    return ancestors


def display_path(place: GeographicPlace, places: list[GeographicPlace]) -> str:
    by_id = {item.id: item for item in places}
    return " → ".join(
        [ancestor.name for ancestor in reversed(_ancestors(place, by_id))] + [place.name]
    )


def _validate_parent(
    place: GeographicPlace | None,
    parent_id: UUID,
    places: list[GeographicPlace],
) -> None:
    by_id = {item.id: item for item in places}
    parent = by_id.get(parent_id)
    if parent is None:
        raise GeographicPlaceHierarchyError(
            "geographic_place_parent_not_found", "Parent geographic place not found"
        )
    if place is not None and (
        parent.id == place.id
        or any(ancestor.id == place.id for ancestor in _ancestors(parent, by_id))
    ):
        raise GeographicPlaceHierarchyError(
            "geographic_place_cycle",
            "A geographic place cannot be moved beneath itself or a descendant",
        )
    if parent.retired_at is not None or any(
        ancestor.retired_at is not None for ancestor in _ancestors(parent, by_id)
    ):
        raise GeographicPlaceHierarchyError(
            "geographic_place_retired_ancestor",
            "An active geographic place cannot have a retired ancestor",
        )


def create_geographic_place(database: Session, payload: GeographicPlaceCreate) -> GeographicPlace:
    places = _all_places(database, lock=True)
    _validate_parent(None, payload.parent_id, places)
    place = GeographicPlace(**payload.model_dump(mode="python"), place_kind="custom")
    database.add(place)
    database.flush()
    return place


def update_geographic_place(
    database: Session, place_id: UUID, payload: GeographicPlaceUpdate
) -> GeographicPlace:
    places = _all_places(database, lock=True)
    place = _require(places, place_id)
    if place.place_kind == "canonical":
        raise GeographicPlaceHierarchyError(
            "canonical_geographic_place_immutable",
            "Canonical geographic places cannot be changed",
        )
    _validate_parent(place, payload.parent_id, places)
    place.name = payload.name
    place.parent_id = payload.parent_id
    place.place_type = payload.place_type
    place.updated_at = datetime.now(UTC)
    database.flush()
    return place


def delete_geographic_place(database: Session, place_id: UUID) -> None:
    places = _all_places(database, lock=True)
    place = _require(places, place_id)
    if place.place_kind == "canonical":
        raise GeographicPlaceHierarchyError(
            "canonical_geographic_place_immutable",
            "Canonical geographic places cannot be deleted",
        )
    if any(item.parent_id == place.id for item in places):
        raise GeographicPlaceHierarchyError(
            "geographic_place_has_children",
            "Move or delete child GeographicPlaces before deleting this place",
        )
    direct, sites = geographic_place_usage(database)
    if direct.get(place.id, 0):
        raise GeographicPlaceHierarchyError(
            "geographic_place_in_use",
            "This geographic place is retained by collection records and cannot be deleted",
        )
    if sites.get(place.id, 0):
        raise GeographicPlaceHierarchyError(
            "geographic_place_has_provenance_sites",
            "Move or delete dependent ProvenanceSites before deleting this place",
        )
    database.delete(place)
    database.flush()


def set_geographic_place_retired(
    database: Session, place_id: UUID, *, retired: bool
) -> GeographicPlace:
    places = _all_places(database, lock=True)
    place = _require(places, place_id)
    if place.place_kind == "canonical":
        raise GeographicPlaceHierarchyError(
            "canonical_geographic_place_immutable",
            "Canonical geographic places cannot be retired or reactivated",
        )
    by_id = {item.id: item for item in places}
    if retired:
        active_descendants = [
            item
            for item in places
            if item.retired_at is None
            and item.id != place.id
            and any(ancestor.id == place.id for ancestor in _ancestors(item, by_id))
        ]
        if active_descendants:
            raise GeographicPlaceHierarchyError(
                "geographic_place_active_descendants",
                "Retire active descendants before retiring this geographic place",
            )
    elif any(ancestor.retired_at is not None for ancestor in _ancestors(place, by_id)):
        raise GeographicPlaceHierarchyError(
            "geographic_place_retired_ancestor",
            "Reactivate retired ancestors before reactivating this geographic place",
        )
    now = datetime.now(UTC)
    place.retired_at = now if retired else None
    place.updated_at = now
    database.flush()
    return place
