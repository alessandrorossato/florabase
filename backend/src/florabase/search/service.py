from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Select, case, func, literal, or_, select
from sqlalchemy.orm import Session, aliased

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_profiles.model import BotanicalProfile
from florabase.events.model import Event, EventKind
from florabase.geographic_places.model import GeographicPlace
from florabase.geographic_places.service import display_path as geographic_path
from florabase.geographic_places.service import list_geographic_places
from florabase.locations.model import Location
from florabase.locations.service import display_path as location_path
from florabase.locations.service import list_locations
from florabase.plants.model import (
    Plant,
    PlantGroup,
    PlantGroupLifecycle,
    PlantLifecycle,
)
from florabase.provenance_sites.model import ProvenanceSite
from florabase.search.schemas import SearchGroup, SearchHit, SearchKind, SearchResponse
from florabase.seed_lots.model import SeedLot, SeedLotLifecycle
from florabase.sowings.model import Sowing, SowingLifecycle
from florabase.suppliers.model import Supplier


@dataclass(frozen=True)
class SearchFilters:
    kinds: tuple[SearchKind, ...] = ()
    identity_id: UUID | None = None
    lifecycle: str | None = None
    location_id: UUID | None = None
    supplier_id: UUID | None = None
    provenance_place_id: UUID | None = None
    provenance_site_id: UUID | None = None
    event_kind: EventKind | None = None
    year: int | None = None

    def active(self) -> bool:
        return any(
            (
                self.kinds,
                self.identity_id,
                self.lifecycle,
                self.location_id,
                self.supplier_id,
                self.provenance_place_id,
                self.provenance_site_id,
                self.event_kind,
                self.year,
            )
        )

    def collection_only(self) -> bool:
        return any(
            (
                self.identity_id,
                self.lifecycle,
                self.location_id,
                self.supplier_id,
                self.provenance_place_id,
                self.provenance_site_id,
                self.event_kind,
                self.year,
            )
        )

    def valid_lifecycle(self) -> bool:
        lifecycle_types = {
            SearchKind.SEED_LOT: SeedLotLifecycle,
            SearchKind.SOWING: SowingLifecycle,
            SearchKind.PLANT: PlantLifecycle,
            SearchKind.PLANT_GROUP: PlantGroupLifecycle,
        }
        return self.lifecycle in {item.value for item in lifecycle_types[self.kinds[0]]}


def _matches(query: str, *columns: Any) -> Any:
    return or_(*(column.icontains(query, autoescape=True) for column in columns))


def _identity_label(identity: Any) -> Any:
    return func.concat_ws(" ", identity.scientific_name, identity.cultivar_name)


def _branch(
    database: Session,
    kind: SearchKind,
    statement: Select[Any],
    *,
    offset: int,
    limit: int,
    path_labels: dict[UUID, str] | None = None,
) -> SearchGroup:
    base = statement.subquery()
    total = int(database.scalar(select(func.count()).select_from(base)) or 0)
    rows = database.execute(
        select(base.c.id, base.c.title, base.c.context, base.c.route_id, base.c.route_kind)
        .order_by(func.lower(base.c.title), base.c.id)
        .offset(offset)
        .limit(limit)
    )
    items: list[SearchHit] = []
    for record_id, title, context, route_id, route_kind in rows:
        href = {
            SearchKind.SEED_LOT: f"#/seeds/{record_id}",
            SearchKind.SOWING: f"#/sowings/{record_id}",
            SearchKind.PLANT: f"#/plants/{record_id}",
            SearchKind.PLANT_GROUP: f"#/plant-groups/{record_id}",
            SearchKind.EVENT: (
                f"#/plants/{route_id}?tab=events"
                if route_kind == "plant"
                else f"#/plant-groups/{route_id}?tab=events"
            ),
            SearchKind.BOTANICAL_IDENTITY: f"#/identities/{record_id}",
            SearchKind.BOTANICAL_PROFILE: f"#/identities/{record_id}?tab=reference",
            SearchKind.SUPPLIER: f"#/suppliers/{record_id}",
            SearchKind.LOCATION: f"#/locations/{record_id}",
            SearchKind.GEOGRAPHIC_PLACE: f"#/geography?place={record_id}",
            SearchKind.PROVENANCE_SITE: f"#/geography/{record_id}",
        }[kind]
        items.append(
            SearchHit(
                kind=kind,
                id=record_id,
                title=(path_labels or {}).get(record_id, title),
                context=context or "",
                href=href,
            )
        )
    return SearchGroup(kind=kind, total=total, items=items)


def search(
    database: Session,
    query: str,
    filters: SearchFilters,
    *,
    offset: int = 0,
    limit: int = 20,
) -> SearchResponse:
    if not query and not filters.active():
        return SearchResponse(query="", total=0, offset=offset, limit=limit, groups=[])

    locations = list_locations(database) if query or filters.location_id else []
    places = list_geographic_places(database) if query else []
    location_paths = {item.id: location_path(item, locations) for item in locations}
    place_paths = {item.id: geographic_path(item, places) for item in places}
    location_matches = (
        [
            record_id
            for record_id, path in location_paths.items()
            if query.casefold() in path.casefold()
        ]
        if query
        else []
    )
    place_matches = (
        [
            record_id
            for record_id, path in place_paths.items()
            if query.casefold() in path.casefold()
        ]
        if query
        else []
    )
    location_scope: list[UUID] = []
    if filters.location_id:
        scope = {filters.location_id}
        while True:
            children = {
                item.id
                for item in locations
                if item.parent_id is not None and item.parent_id in scope
            }
            if children <= scope:
                break
            scope.update(children)
        location_scope = list(scope)

    groups: list[SearchGroup] = []

    def add(kind: SearchKind, statement: Select[Any], paths: dict[UUID, str] | None = None) -> None:
        if filters.kinds and kind not in filters.kinds:
            return
        group = _branch(database, kind, statement, offset=offset, limit=limit, path_labels=paths)
        if group.total:
            groups.append(group)

    identity = aliased(BotanicalIdentity)
    supplier = aliased(Supplier)
    location = aliased(Location)
    place = aliased(GeographicPlace)
    site = aliased(ProvenanceSite)

    for kind, model_type in (
        (SearchKind.SEED_LOT, SeedLot),
        (SearchKind.SOWING, Sowing),
        (SearchKind.PLANT, Plant),
        (SearchKind.PLANT_GROUP, PlantGroup),
    ):
        if filters.kinds and kind not in filters.kinds:
            continue
        if kind == SearchKind.SOWING and (
            filters.provenance_place_id or filters.provenance_site_id
        ):
            continue
        model = cast(Any, model_type)
        seed = aliased(SeedLot) if kind == SearchKind.SOWING else None
        identity_fk = (
            seed.botanical_identity_id if seed is not None else model.botanical_identity_id
        )
        statement = select(
            model.id.label("id"),
            func.coalesce(model.label, _identity_label(identity)).label("title"),
            _identity_label(identity).label("context"),
            model.id.label("route_id"),
            literal("").label("route_kind"),
        ).select_from(model)
        if seed is not None:
            statement = statement.join(seed, seed.id == Sowing.seed_lot_id)
        statement = (
            statement.join(identity, identity.id == identity_fk)
            .outerjoin(location, location.id == model.location_id)
            .outerjoin(
                supplier,
                supplier.id == (seed.supplier_id if seed is not None else model.supplier_id),
            )
            .outerjoin(
                place,
                place.id
                == (
                    seed.material_provenance_place_id
                    if seed is not None
                    else model.material_provenance_place_id
                ),
            )
            .outerjoin(
                site,
                site.id
                == (seed.provenance_site_id if seed is not None else model.provenance_site_id),
            )
        )
        if query:
            criteria = _matches(
                query,
                model.label,
                model.notes,
                identity.scientific_name,
                identity.cultivar_name,
                identity.common_name,
                supplier.name,
                location.name,
                place.name,
                site.name,
            )
            if location_matches:
                criteria = or_(criteria, model.location_id.in_(location_matches))
            if place_matches:
                criteria = or_(
                    criteria,
                    (
                        seed.material_provenance_place_id
                        if seed is not None
                        else model.material_provenance_place_id
                    ).in_(place_matches),
                )
            if seed is not None:
                criteria = or_(criteria, _matches(query, seed.label, seed.notes))
            statement = statement.where(criteria)
        if filters.identity_id:
            statement = statement.where(identity_fk == filters.identity_id)
        if filters.location_id:
            statement = statement.where(model.location_id.in_(location_scope))
        if filters.supplier_id:
            statement = statement.where(
                (seed.supplier_id if seed is not None else model.supplier_id) == filters.supplier_id
            )
        if filters.provenance_place_id:
            statement = statement.where(
                model.material_provenance_place_id == filters.provenance_place_id
            )
        if filters.provenance_site_id:
            statement = statement.where(model.provenance_site_id == filters.provenance_site_id)
        if filters.lifecycle:
            statement = statement.where(model.lifecycle == filters.lifecycle)
        if filters.year is not None:
            year_column = (
                Sowing.sowing_date_year
                if kind == SearchKind.SOWING
                else SeedLot.acquisition_date_year
                if kind == SearchKind.SEED_LOT
                else model.collection_entry_date_year
            )
            statement = statement.where(year_column == filters.year)
        if filters.event_kind:
            continue
        add(kind, statement)

    if not (
        filters.location_id
        or filters.supplier_id
        or filters.provenance_place_id
        or filters.provenance_site_id
        or filters.lifecycle
    ) and (not filters.kinds or SearchKind.EVENT in filters.kinds):
        plant = aliased(Plant)
        group = aliased(PlantGroup)
        plant_identity = aliased(BotanicalIdentity)
        group_identity = aliased(BotanicalIdentity)
        target_label = func.coalesce(
            plant.label, group.label, plant_identity.scientific_name, group_identity.scientific_name
        )
        statement = (
            select(
                Event.id.label("id"),
                func.concat(func.initcap(Event.kind), " · ", target_label).label("title"),
                case(
                    (Event.plant_id.is_not(None), _identity_label(plant_identity)),
                    else_=_identity_label(group_identity),
                ).label("context"),
                func.coalesce(Event.plant_id, Event.plant_group_id).label("route_id"),
                case((Event.plant_id.is_not(None), "plant"), else_="group").label("route_kind"),
            )
            .outerjoin(plant, plant.id == Event.plant_id)
            .outerjoin(group, group.id == Event.plant_group_id)
            .outerjoin(plant_identity, plant_identity.id == plant.botanical_identity_id)
            .outerjoin(group_identity, group_identity.id == group.botanical_identity_id)
        )
        if query:
            statement = statement.where(
                _matches(
                    query,
                    Event.kind,
                    Event.notes,
                    plant.label,
                    group.label,
                    plant_identity.scientific_name,
                    plant_identity.common_name,
                    group_identity.scientific_name,
                    group_identity.common_name,
                )
            )
        if filters.identity_id:
            statement = statement.where(
                or_(
                    plant.botanical_identity_id == filters.identity_id,
                    group.botanical_identity_id == filters.identity_id,
                )
            )
        if filters.event_kind:
            statement = statement.where(Event.kind == filters.event_kind.value)
        if filters.year is not None:
            statement = statement.where(Event.occurred_on_year == filters.year)
        add(SearchKind.EVENT, statement)

    if not filters.collection_only():
        statement = select(
            BotanicalIdentity.id.label("id"),
            _identity_label(BotanicalIdentity).label("title"),
            func.coalesce(BotanicalIdentity.common_name, "Botanical identity").label("context"),
            BotanicalIdentity.id.label("route_id"),
            literal("").label("route_kind"),
        )
        if query:
            statement = statement.where(
                _matches(
                    query,
                    BotanicalIdentity.scientific_name,
                    BotanicalIdentity.cultivar_name,
                    BotanicalIdentity.common_name,
                )
            )
        add(SearchKind.BOTANICAL_IDENTITY, statement)

        statement = select(
            BotanicalProfile.botanical_identity_id.label("id"),
            _identity_label(identity).label("title"),
            literal("Reference knowledge").label("context"),
            BotanicalProfile.botanical_identity_id.label("route_id"),
            literal("").label("route_kind"),
        ).join(identity, identity.id == BotanicalProfile.botanical_identity_id)
        if query:
            statement = statement.where(
                _matches(
                    query,
                    BotanicalProfile.description,
                    BotanicalProfile.origin_distribution,
                    BotanicalProfile.cultivation,
                    BotanicalProfile.uses,
                    BotanicalProfile.warnings,
                )
            )
        add(SearchKind.BOTANICAL_PROFILE, statement)

        statement = select(
            Supplier.id.label("id"),
            Supplier.name.label("title"),
            Supplier.kind.label("context"),
            Supplier.id.label("route_id"),
            literal("").label("route_kind"),
        )
        if query:
            statement = statement.where(_matches(query, Supplier.name, Supplier.notes))
        add(SearchKind.SUPPLIER, statement)

        statement = select(
            Location.id.label("id"),
            Location.name.label("title"),
            literal("Collection location").label("context"),
            Location.id.label("route_id"),
            literal("").label("route_kind"),
        )
        if query:
            statement = statement.where(
                or_(_matches(query, Location.name), Location.id.in_(location_matches))
            )
        add(SearchKind.LOCATION, statement, location_paths)

        statement = select(
            GeographicPlace.id.label("id"),
            GeographicPlace.name.label("title"),
            literal("Geographic place").label("context"),
            GeographicPlace.id.label("route_id"),
            literal("").label("route_kind"),
        )
        if query:
            statement = statement.where(
                or_(_matches(query, GeographicPlace.name), GeographicPlace.id.in_(place_matches))
            )
        add(SearchKind.GEOGRAPHIC_PLACE, statement, place_paths)

        statement = select(
            ProvenanceSite.id.label("id"),
            ProvenanceSite.name.label("title"),
            literal("Provenance site").label("context"),
            ProvenanceSite.id.label("route_id"),
            literal("").label("route_kind"),
        ).outerjoin(place, place.id == ProvenanceSite.geographic_place_id)
        if query:
            statement = statement.where(
                or_(
                    _matches(query, ProvenanceSite.name, place.name),
                    ProvenanceSite.geographic_place_id.in_(place_matches),
                )
            )
        add(SearchKind.PROVENANCE_SITE, statement)

    return SearchResponse(
        query=query,
        total=sum(group.total for group in groups),
        offset=offset,
        limit=limit,
        groups=groups,
    )
