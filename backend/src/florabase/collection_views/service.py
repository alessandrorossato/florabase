from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import BotanicalIdentityResponse
from florabase.botanical_identities.service import get_botanical_identity
from florabase.collection_views.dashboard import overview, photographs
from florabase.collection_views.schemas import (
    BotanicalIdentityCollectionResponse,
    DashboardCounts,
    DashboardResponse,
)
from florabase.events.model import Event
from florabase.events.service import event_responses, list_all_events
from florabase.harvests.service import list_harvests
from florabase.plants.model import Plant, PlantGroup
from florabase.plants.service import (
    list_plant_groups,
    list_plants,
    plant_group_responses,
    plant_responses,
)
from florabase.seed_lots.model import SeedLot
from florabase.seed_lots.service import list_seed_lots
from florabase.seed_lots.service import responses as seed_lot_responses
from florabase.sowings.model import Sowing
from florabase.sowings.service import list_sowings
from florabase.sowings.service import responses as sowing_responses


def dashboard(database: Session, today: date | None = None) -> DashboardResponse:
    # One round trip for independent counts; no row-multiplying joins.
    counts = (
        database.execute(
            select(
                *[
                    select(func.count())
                    .select_from(model)
                    .where(*criteria)
                    .scalar_subquery()
                    .label(name)
                    for name, model, criteria in (
                        ("active_plants", Plant, (Plant.lifecycle == "active",)),
                        ("active_plant_groups", PlantGroup, (PlantGroup.lifecycle == "active",)),
                        ("active_seed_lots", SeedLot, (SeedLot.lifecycle == "active",)),
                        ("active_sowings", Sowing, (Sowing.lifecycle == "active",)),
                        ("botanical_identities", BotanicalIdentity, ()),
                        ("events", Event, ()),
                    )
                ]
            )
        )
        .mappings()
        .one()
    )
    return DashboardResponse(
        counts=DashboardCounts.model_validate(dict(counts)),
        overview=overview(database, today or datetime.now(UTC).date()),
        recent_events=event_responses(database, list_all_events(database, limit=6)),
        photos=photographs(database),
    )


def botanical_identity_collection(
    database: Session, botanical_identity_id: UUID
) -> BotanicalIdentityCollectionResponse | None:
    identity = get_botanical_identity(database, botanical_identity_id)
    if identity is None:
        return None
    return BotanicalIdentityCollectionResponse(
        identity=BotanicalIdentityResponse.from_model(identity),
        seed_lots=seed_lot_responses(database, list_seed_lots(database, botanical_identity_id)),
        sowings=sowing_responses(database, list_sowings(database, botanical_identity_id)),
        plants=plant_responses(database, list_plants(database, botanical_identity_id)),
        plant_groups=plant_group_responses(
            database, list_plant_groups(database, botanical_identity_id)
        ),
        harvests=list_harvests(database, botanical_identity_id=botanical_identity_id),
        events=event_responses(
            database,
            list_all_events(database, botanical_identity_id=botanical_identity_id),
        ),
    )
