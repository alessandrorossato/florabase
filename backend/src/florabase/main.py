from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from florabase import __version__
from florabase.api.router import api_router
from florabase.attachments.storage import AttachmentStorage
from florabase.auth.demo_readonly import DemoReadOnlyMiddleware
from florabase.auth.http_safety import AuthSafetyMiddleware
from florabase.core.config import Environment, get_settings
from florabase.core.cors import NativeAppCorsMiddleware
from florabase.core.logging import configure_logging
from florabase.reference_setup.runner import ReferenceSetupCoordinator


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings_provider = application.dependency_overrides.get(get_settings, get_settings)
    settings = settings_provider()
    configure_logging(settings)
    AttachmentStorage.from_settings(settings)
    coordinator = ReferenceSetupCoordinator(settings)
    application.state.reference_setup = coordinator
    coordinator.start()
    try:
        yield
    finally:
        await coordinator.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    expose_docs = settings.environment is not Environment.PRODUCTION
    application = FastAPI(
        title="Florabase API",
        version=__version__,
        lifespan=lifespan,
        openapi_url="/openapi.json" if expose_docs else None,
        docs_url="/docs" if expose_docs else None,
        redoc_url="/redoc" if expose_docs else None,
    )
    application.add_middleware(AuthSafetyMiddleware)
    if settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "X-CSRF-Token"],
        )
    application.add_middleware(NativeAppCorsMiddleware)
    if settings.demo_readonly:
        application.add_middleware(DemoReadOnlyMiddleware)
    application.include_router(api_router)
    return application


app = create_app()
