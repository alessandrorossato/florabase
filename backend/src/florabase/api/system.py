from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from florabase import __version__
from florabase.core.config import Settings, get_settings

router = APIRouter(prefix="/system", tags=["system"])

API_VERSION = 1
SERVER_CAPABILITIES: tuple[str, ...] = ("device-auth",)


class SystemInfoResponse(BaseModel):
    server_version: str
    api_version: int
    min_client_version: str
    capabilities: list[str]


@router.get("/info", response_model=SystemInfoResponse, operation_id="getSystemInfo")
async def system_info(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> SystemInfoResponse:
    response.headers["Cache-Control"] = "no-store"
    capabilities = list(SERVER_CAPABILITIES)
    if settings.demo_readonly:
        capabilities.append("demo-readonly")
    return SystemInfoResponse(
        server_version=__version__,
        api_version=API_VERSION,
        min_client_version=settings.min_client_version,
        capabilities=capabilities,
    )
