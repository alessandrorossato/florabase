from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from florabase.geographic_places.model import GeographicPlace
from florabase.geographic_places.service import display_path, list_geographic_places
from florabase.plants.model import Plant, PlantGroup
from florabase.provenance_sites.model import ProvenanceSite
from florabase.provenance_sites.schemas import (
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
