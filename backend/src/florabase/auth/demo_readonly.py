"""Opt-in public read-only demo guards and ephemeral read-only actor resolution."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from florabase.auth.model import AuthSession, User

if TYPE_CHECKING:
    from florabase.auth.dependencies import AuthenticatedActor

DEMO_READONLY_CODE = "demo_read_only"
DEMO_READONLY_MESSAGE = (
    "This public demo is read-only. Install Florabase to create or edit records."
)
SAFE_HTTP_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
EPHEMERAL_DEMO_SESSION_ID = UUID(int=0)


def demo_readonly_error_detail() -> dict[str, str]:
    return {"code": DEMO_READONLY_CODE, "message": DEMO_READONLY_MESSAGE}


def demo_readonly_response() -> JSONResponse:
    return JSONResponse(
        {"detail": demo_readonly_error_detail()},
        status_code=status.HTTP_403_FORBIDDEN,
        headers={"Cache-Control": "no-store"},
    )


def raise_demo_readonly() -> None:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=demo_readonly_error_detail(),
    )


class DemoReadOnlyMiddleware:
    """Reject every non-safe HTTP method when FLORABASE_DEMO_READONLY is enabled."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"].upper() not in SAFE_HTTP_METHODS:
            await demo_readonly_response()(scope, receive, send)
            return
        await self.app(scope, receive, send)


def resolve_demo_actor(database: Session) -> AuthenticatedActor:
    """Resolve the single enabled demo owner without writing any session row."""
    from florabase.auth.dependencies import AuthenticatedActor

    owner = database.scalars(
        select(User)
        .where(User.enabled.is_(True), User.owner.is_(True))
        .order_by(User.created_at.asc())
        .limit(1)
    ).one_or_none()
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Demo collection is not initialized",
        )
    now = datetime.now(UTC)
    ephemeral_session = AuthSession(
        id=EPHEMERAL_DEMO_SESSION_ID,
        user_id=owner.id,
        transport="cookie",
        device_label=None,
        token_digest=b"\x00" * 32,
        csrf_digest=None,
        created_at=now,
        last_seen_at=now,
        idle_expires_at=now + timedelta(hours=1),
        absolute_expires_at=now + timedelta(hours=2),
    )
    return AuthenticatedActor(
        user_id=owner.id,
        login_name=owner.login_name,
        display_name=owner.display_name,
        owner=owner.owner,
        session=ephemeral_session,
        transport="cookie",
    )
