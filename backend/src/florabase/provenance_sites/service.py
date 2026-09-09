from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import BotanicalIdentityResponse
from florabase.geographic_places.model import GeographicPlace
from florabase.geographic_places.service import display_path, list_geographic_places
from florabase.plants.model import Plant, PlantGroup
from florabase.provenance_sites.model import ProvenanceSite
from florabase.provenance_sites.schemas import (
    ProvenanceMapBotanicalIdentity,
    ProvenanceMapRecord,
    ProvenanceMapResponse,
    ProvenanceMapSite,
    ProvenanceMapUsage,
    ProvenanceSiteCreate,
    ProvenanceSiteResponse,
    ProvenanceSiteUpdate,
    ProvenanceSiteUsage,
)
from florabase.seed_lots.model import SeedLot


@dataclass(frozen=True)
class ProvenanceSiteError(Exception):
    code: str
    message: str


def _require_place(database: Session, place_id: UUID | None) -> None:
    if place_id is not None and database.get(GeographicPlace, place_id) is None:
        raise ProvenanceSiteError("geographic_place_not_found", "Geographic place not found")


def site_usage(database: Session) -> dict[UUID, ProvenanceSiteUsage]:
    result: dict[UUID, ProvenanceSiteUsage] = {}
    for model, field in (
        (SeedLot, "seed_lots"),
        (Plant, "plants"),
        (PlantGroup, "plant_groups"),
    ):
        rows = database.execute(
            select(model.provenance_site_id, func.count())
            .where(model.provenance_site_id.is_not(None))
            .group_by(model.provenance_site_id)
        )
        for site_id, count in rows:
            if site_id is not None:
                current = result.setdefault(site_id, ProvenanceSiteUsage())
                setattr(current, field, count)
    return result


def list_provenance_sites(database: Session) -> list[ProvenanceSite]:
    return list(
        database.scalars(
            select(ProvenanceSite).order_by(func.lower(ProvenanceSite.name), ProvenanceSite.id)
        )
    )


def get_provenance_site(database: Session, site_id: UUID) -> ProvenanceSite | None:
    return database.get(ProvenanceSite, site_id)


def create_provenance_site(database: Session, payload: ProvenanceSiteCreate) -> ProvenanceSite:
    _require_place(database, payload.geographic_place_id)
    site = ProvenanceSite(**payload.model_dump(mode="python"))
    database.add(site)
    database.flush()
    return site


def update_provenance_site(
    database: Session, site: ProvenanceSite, payload: ProvenanceSiteUpdate
) -> ProvenanceSite:
    database.refresh(site, with_for_update=True)
    _require_place(database, payload.geographic_place_id)
    for field, value in payload.model_dump(mode="python").items():
        setattr(site, field, value)
    site.updated_at = datetime.now(UTC)
    database.flush()
    return site


def delete_provenance_site(database: Session, site: ProvenanceSite) -> None:
    database.refresh(site, with_for_update=True)
    usage = site_usage(database).get(site.id, ProvenanceSiteUsage())
    if usage.seed_lots + usage.plants + usage.plant_groups:
        raise ProvenanceSiteError(
            "provenance_site_in_use",
            "This ProvenanceSite is retained by collection records and cannot be deleted",
        )
    database.delete(site)
    database.flush()


def responses(database: Session, sites: list[ProvenanceSite]) -> list[ProvenanceSiteResponse]:
    places = (
        list_geographic_places(database) if any(site.geographic_place_id for site in sites) else []
    )
    by_id = {place.id: place for place in places}
    usage = site_usage(database)
    return [
        ProvenanceSiteResponse.model_validate(
            {
                "id": site.id,
                "name": site.name,
                "geographic_place_id": site.geographic_place_id,
                "latitude": site.latitude,
                "longitude": site.longitude,
                "coordinate_accuracy_m": site.coordinate_accuracy_m,
                "notes": site.notes,
                "created_at": site.created_at,
                "updated_at": site.updated_at,
                "geographic_place_path": (
                    display_path(by_id[site.geographic_place_id], places)
                    if site.geographic_place_id is not None
                    else None
                ),
                "usage": usage.get(site.id, ProvenanceSiteUsage()),
            }
        )
        for site in sites
    ]


def _map_records(
    database: Session, sites: list[ProvenanceSite]
) -> dict[UUID, list[ProvenanceMapRecord]]:
    by_site: dict[UUID, list[ProvenanceMapRecord]] = {site.id: [] for site in sites}
    if not sites:
        return by_site
    site_ids = list(by_site)

    def append_record(
        record: SeedLot | Plant | PlantGroup,
        identity: BotanicalIdentity,
        record_type: Literal["seed_lot", "plant", "plant_group"],
    ) -> None:
        if record.provenance_site_id is None:
            return
        by_site[record.provenance_site_id].append(
            ProvenanceMapRecord(
                record_type=record_type,
                id=record.id,
                label=record.label,
                botanical_identity=ProvenanceMapBotanicalIdentity(
                    id=identity.id,
                    display_label=BotanicalIdentityResponse.from_model(identity).display_label,
                ),
                lifecycle=record.lifecycle,
                is_active=record.lifecycle == "active",
            )
        )

    seed_lots = (
        select(SeedLot, BotanicalIdentity)
        .join(BotanicalIdentity, BotanicalIdentity.id == SeedLot.botanical_identity_id)
        .where(SeedLot.provenance_site_id.in_(site_ids))
    )
    for seed_lot, identity in database.execute(seed_lots).tuples():
        append_record(seed_lot, identity, "seed_lot")

    plants = (
        select(Plant, BotanicalIdentity)
        .join(BotanicalIdentity, BotanicalIdentity.id == Plant.botanical_identity_id)
        .where(
            Plant.provenance_site_id.in_(site_ids),
            Plant.originating_sowing_id.is_(None),
            Plant.originating_plant_group_id.is_(None),
        )
    )
    for plant, identity in database.execute(plants).tuples():
        append_record(plant, identity, "plant")

    plant_groups = (
        select(PlantGroup, BotanicalIdentity)
        .join(BotanicalIdentity, BotanicalIdentity.id == PlantGroup.botanical_identity_id)
        .where(
            PlantGroup.provenance_site_id.in_(site_ids),
            PlantGroup.originating_sowing_id.is_(None),
        )
    )
    for plant_group, identity in database.execute(plant_groups).tuples():
        append_record(plant_group, identity, "plant_group")
    record_type_order = {"seed_lot": 0, "plant": 1, "plant_group": 2}
    for records in by_site.values():
        records.sort(
            key=lambda item: (
                record_type_order[item.record_type],
                item.botanical_identity.display_label.casefold(),
                (item.label or "").casefold(),
                str(item.id),
            )
        )
    return by_site


def collection_provenance_map(database: Session) -> ProvenanceMapResponse:
    total_sites = database.scalar(select(func.count()).select_from(ProvenanceSite)) or 0
    sites = list(
        database.scalars(
            select(ProvenanceSite)
            .where(
                ProvenanceSite.latitude.is_not(None),
                ProvenanceSite.longitude.is_not(None),
            )
            .order_by(func.lower(ProvenanceSite.name), ProvenanceSite.id)
        )
    )
    places = (
        list_geographic_places(database) if any(site.geographic_place_id for site in sites) else []
    )
    places_by_id = {place.id: place for place in places}
    records_by_site = _map_records(database, sites)
    mapped_sites: list[ProvenanceMapSite] = []
    for site in sites:
        if site.latitude is None or site.longitude is None:
            continue
        records = records_by_site[site.id]
        seed_lots = sum(record.record_type == "seed_lot" for record in records)
        plants = sum(record.record_type == "plant" for record in records)
        plant_groups = sum(record.record_type == "plant_group" for record in records)
        mapped_sites.append(
            ProvenanceMapSite(
                id=site.id,
                name=site.name,
                latitude=site.latitude,
                longitude=site.longitude,
                coordinate_accuracy_m=site.coordinate_accuracy_m,
                geographic_place_id=site.geographic_place_id,
                geographic_place_path=(
                    display_path(places_by_id[site.geographic_place_id], places)
                    if site.geographic_place_id is not None
                    else None
                ),
                usage=ProvenanceMapUsage(
                    seed_lots=seed_lots,
                    plants=plants,
                    plant_groups=plant_groups,
                    total=len(records),
                ),
                records=records,
            )
        )
    return ProvenanceMapResponse(
        total_provenance_sites=total_sites,
        coordinate_less_sites=total_sites - len(sites),
        sites=mapped_sites,
    )
