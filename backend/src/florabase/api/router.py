from fastapi import APIRouter

from florabase.api.health import router as health_router
from florabase.auth.api import router as auth_router
from florabase.botanical_identities.api import router as botanical_identities_router
from florabase.botanical_profiles.api import router as botanical_profiles_router
from florabase.collection_views.api import router as collection_views_router
from florabase.events.api import events_router, plant_groups_events_router, plants_events_router
from florabase.geographic_places.api import router as geographic_places_router
from florabase.locations.api import router as locations_router
from florabase.plants.api import plant_groups_router, plants_router
from florabase.seed_lots.api import router as seed_lots_router
from florabase.sowings.api import router as sowings_router
from florabase.suppliers.api import router as suppliers_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(botanical_identities_router)
api_router.include_router(botanical_profiles_router)
api_router.include_router(collection_views_router)
api_router.include_router(suppliers_router)
api_router.include_router(locations_router)
api_router.include_router(geographic_places_router)
api_router.include_router(seed_lots_router)
api_router.include_router(sowings_router)
api_router.include_router(plants_router)
api_router.include_router(plant_groups_router)
api_router.include_router(plants_events_router)
api_router.include_router(plant_groups_events_router)
api_router.include_router(events_router)
