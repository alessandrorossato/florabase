from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from florabase import __version__
from florabase.auth.dependencies import AuthenticatedActor, require_authenticated_actor
from florabase.core.config import Settings, get_settings
from florabase.reference_setup.state import SystemReferencesResponse, get_runtime_status

router = APIRouter(prefix="/system", tags=["system"])

API_VERSION = 1
SERVER_CAPABILITIES: tuple[str, ...] = ("device-auth",)


class RuntimeConfigResponse(BaseModel):
    map_online_enabled: bool = False
    map_tile_url: str | None = None
    map_attribution: str | None = None


class SystemInfoResponse(BaseModel):
    server_version: str
    api_version: int
    min_client_version: str
    capabilities: list[str]
    runtime_config: RuntimeConfigResponse


@router.get("/info", response_model=SystemInfoResponse, operation_id="getSystemInfo")
async def system_info(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> SystemInfoResponse:
    response.headers["Cache-Control"] = "no-store"
    return SystemInfoResponse(
        server_version=__version__,
        api_version=API_VERSION,
        min_client_version=settings.min_client_version,
        capabilities=list(SERVER_CAPABILITIES),
        runtime_config=RuntimeConfigResponse(
            map_online_enabled=settings.map_online_enabled,
            map_tile_url=settings.map_tile_url,
            map_attribution=settings.map_attribution,
        ),
    )


@router.get(
    "/references",
    response_model=SystemReferencesResponse,
    operation_id="getSystemReferences",
)
def system_references(
    response: Response,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SystemReferencesResponse:
    response.headers["Cache-Control"] = "no-store"
    return get_runtime_status(settings)
