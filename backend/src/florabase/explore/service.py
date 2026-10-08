"""Bounded local projection; never imports or calls a botanical provider."""

from uuid import UUID

from sqlalchemy import Row, Select, case, func, literal, or_, select, union_all
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.explore.schemas import (
    RepresentationScope,
    RepresentedIdentity,
    RepresentedIdentityPage,
)
from florabase.external_botany.model import ExternalTaxonLink
from florabase.harvests.inventory_model import HarvestMaterialInventory
from florabase.harvests.model import Harvest
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing


def projection() -> Select[tuple[BotanicalIdentity, int, int, int, str | None, int]]:
    records = union_all(
        *[
            select(
                model.botanical_identity_id.label("identity_id"),
                case((model.lifecycle == "active", 1), else_=0).label("current"),
                case((model.lifecycle == "active", 1 if living else 0), else_=0).label("living"),
            )
            for model, living in ((SeedLot, False), (Plant, True), (PlantGroup, True))
        ],
        select(
            SeedLot.botanical_identity_id,
            case((Sowing.lifecycle == "active", 1), else_=0),
            literal(0),
        ).join(SeedLot, SeedLot.id == Sowing.seed_lot_id),
        select(
            func.coalesce(Plant.botanical_identity_id, PlantGroup.botanical_identity_id),
            case((HarvestMaterialInventory.state == "active", 1), else_=0),
            literal(0),
        )
        .select_from(HarvestMaterialInventory)
        .join(Harvest, Harvest.id == HarvestMaterialInventory.harvest_id)
        .outerjoin(Plant, Plant.id == Harvest.plant_id)
        .outerjoin(PlantGroup, PlantGroup.id == Harvest.plant_group_id),
    ).subquery()
    counts = (
        select(
            records.c.identity_id,
            func.count().label("retained"),
            func.sum(records.c.current).label("current"),
            func.sum(records.c.living).label("living"),
        )
        .group_by(records.c.identity_id)
        .subquery()
    )
    links = (
        select(
            ExternalTaxonLink.botanical_identity_id.label("identity_id"),
            func.max(
                case((ExternalTaxonLink.provider == "gbif", ExternalTaxonLink.external_id))
            ).label("gbif_id"),
            func.count().label("links"),
        )
        .group_by(ExternalTaxonLink.botanical_identity_id)
        .subquery()
    )
    return (
        select(
            BotanicalIdentity,
            counts.c.retained,
            counts.c.current,
            counts.c.living,
            links.c.gbif_id,
            func.coalesce(links.c.links, 0),
        )
        .join(counts, counts.c.identity_id == BotanicalIdentity.id)
        .outerjoin(links, links.c.identity_id == BotanicalIdentity.id)
    )


def _matches(scope: RepresentationScope, current: int, living: int) -> bool:
    return (
        scope == "all"
        or (scope == "living" and living > 0)
        or (scope == "current" and current > 0)
        or (scope == "historical" and current == 0)
    )


def response(
    row: Row[tuple[BotanicalIdentity, int, int, int, str | None, int]], scope: RepresentationScope
) -> RepresentedIdentity:
    identity, retained, current, living, gbif_id, links = row
    label = identity.scientific_name
    if identity.cultivar_name is not None:
        label += f" \u2018{identity.cultivar_name}\u2019"
    return RepresentedIdentity(
        id=identity.id,
        display_label=label,
        scientific_name=identity.scientific_name,
        cultivar_name=identity.cultivar_name,
        common_name=identity.common_name,
        representation="living" if living else "current" if current else "historical",
        retained_records=retained,
        current_records=current,
        living_records=living,
        occurrence_eligibility="available"
        if gbif_id is not None
        else "incompatible"
        if links
        else "not_linked",
        external_taxon_id=gbif_id,
        matches_scope=_matches(scope, current, living),
    )


def list_identities(
    database: Session,
    *,
    q: str = "",
    scope: RepresentationScope = "all",
    offset: int = 0,
    limit: int = 50,
) -> RepresentedIdentityPage:
    statement = projection()
    columns = statement.selected_columns
    if scope == "living":
        statement = statement.where(columns["living"] > 0)
    elif scope == "current":
        statement = statement.where(columns["current"] > 0)
    elif scope == "historical":
        statement = statement.where(columns["current"] == 0)
    if q.strip():
        label = func.concat(
            BotanicalIdentity.scientific_name, " \u2018", BotanicalIdentity.cultivar_name, "\u2019"
        )
        statement = statement.where(
            or_(
                *[
                    field.icontains(q.strip(), autoescape=True)
                    for field in (
                        BotanicalIdentity.scientific_name,
                        BotanicalIdentity.cultivar_name,
                        BotanicalIdentity.common_name,
                        label,
                    )
                ]
            )
        )
    filtered = statement.subquery()
    total, ready = database.execute(
        select(func.count(), func.count(filtered.c.gbif_id)).select_from(filtered)
    ).one()
    rows = database.execute(
        statement.order_by(
            func.lower(BotanicalIdentity.scientific_name),
            func.lower(BotanicalIdentity.cultivar_name).nulls_first(),
            BotanicalIdentity.id,
        )
        .offset(offset)
        .limit(limit)
    ).all()
    return RepresentedIdentityPage(
        items=[response(row, scope) for row in rows],
        total=total,
        occurrence_ready=ready,
        offset=offset,
        limit=limit,
    )


def get_identity(
    database: Session, identity_id: UUID, scope: RepresentationScope
) -> RepresentedIdentity | None:
    row = database.execute(projection().where(BotanicalIdentity.id == identity_id)).one_or_none()
    return response(row, scope) if row else None
