from pydantic import BaseModel

from florabase.botanical_identities.schemas import BotanicalIdentityResponse
from florabase.events.schemas import EventResponse
from florabase.plants.schemas import PlantGroupResponse, PlantResponse
from florabase.seed_lots.schemas import SeedLotResponse
from florabase.sowings.schemas import SowingResponse


class DashboardCounts(BaseModel):
    active_plants: int
    active_plant_groups: int
    active_seed_lots: int
    active_sowings: int
    botanical_identities: int
    events: int


class DashboardResponse(BaseModel):
    counts: DashboardCounts
    recent_events: list[EventResponse]


class BotanicalIdentityCollectionResponse(BaseModel):
    identity: BotanicalIdentityResponse
    seed_lots: list[SeedLotResponse]
    sowings: list[SowingResponse]
    plants: list[PlantResponse]
    plant_groups: list[PlantGroupResponse]
    events: list[EventResponse]
