from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import BotanicalIdentityResponse
from florabase.botanical_identities.service import get_botanical_identity
from florabase.collection_views.schemas import (
    BotanicalIdentityCollectionResponse,
    DashboardCounts,
    DashboardResponse,
)
from florabase.events.model import Event
from florabase.events.service import event_responses, list_all_events
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


def _count(database: Session, model: type[object], *criteria: Any) -> int:
    value = database.scalar(select(func.count()).select_from(model).where(*criteria))
    return int(value or 0)


def dashboard(database: Session) -> DashboardResponse:
    return DashboardResponse(
        counts=DashboardCounts(
            active_plants=_count(database, Plant, Plant.lifecycle == "active"),
            active_plant_groups=_count(database, PlantGroup, PlantGroup.lifecycle == "active"),
            active_seed_lots=_count(database, SeedLot, SeedLot.lifecycle == "active"),
            active_sowings=_count(database, Sowing, Sowing.lifecycle == "active"),
            botanical_identities=_count(database, BotanicalIdentity),
            events=_count(database, Event),
        ),
        recent_events=event_responses(database, list_all_events(database, limit=6)),
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
        events=event_responses(
            database,
            list_all_events(database, botanical_identity_id=botanical_identity_id),
        ),
    )
