from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from florabase.botanical_identities.schemas import BotanicalIdentityResponse
from florabase.events.schemas import EventResponse
from florabase.harvests.schemas import HarvestResponse
from florabase.history.schemas import HistoryEntry
from florabase.plants.schemas import PlantGroupResponse, PlantResponse
from florabase.schedule.schemas import ScheduleResponse
from florabase.seed_lots.schemas import SeedLotResponse
from florabase.sowings.schemas import SowingResponse


class DashboardCounts(BaseModel):
    active_plants: int
    active_plant_groups: int
    active_seed_lots: int
    active_sowings: int
    botanical_identities: int
    events: int


class DashboardOverview(BaseModel):
    today: date
    current_identities: int
    identities_with_wfo: int
    identities_with_profile: int
    sowings_unknown_germination: int
    sowings_with_germination: int
    sowings_zero_germination: int
    purchase_packets_without_order: int
    overdue: int
    due_today: int
    next_seven_days: int
    upcoming: list[ScheduleResponse]
    recent_activity: list[HistoryEntry]


class DashboardImage(BaseModel):
    thumbnail_url: str
    attribution: str | None
    licence_label: str | None
    licence_url: str | None
    source_url: str | None


class DashboardPhoto(BaseModel):
    """One actual individual Plant, with separately identified permitted imagery."""

    id: UUID
    title: str
    scientific_name: str
    image: DashboardImage | None
    reference_image: DashboardImage | None


class DashboardResponse(BaseModel):
    overview: DashboardOverview
    counts: DashboardCounts
    recent_events: list[EventResponse]
    photos: list[DashboardPhoto] = Field(default_factory=list)


class BotanicalIdentityCollectionResponse(BaseModel):
    identity: BotanicalIdentityResponse
    seed_lots: list[SeedLotResponse]
    sowings: list[SowingResponse]
    plants: list[PlantResponse]
    plant_groups: list[PlantGroupResponse]
    events: list[EventResponse]
    harvests: list[HarvestResponse]
