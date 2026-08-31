import secrets
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from florabase.auth.model import AuthSession
from florabase.auth.service import InvalidCredentialsError, resolve_session, verify_csrf
from florabase.core.config import CookieMode, Settings, get_settings
from florabase.db.session import get_database_session

SECURE_COOKIE_NAME = "__Host-florabase-session"
DEVELOPMENT_COOKIE_NAME = "florabase-session-dev"


@dataclass(frozen=True)
class AuthenticatedActor:
    user_id: UUID
    login_name: str
    display_name: str | None
    owner: bool
    session: AuthSession


def session_cookie_name(settings: Settings) -> str:
    if settings.cookie_mode is CookieMode.LOOPBACK_DEVELOPMENT:
        return DEVELOPMENT_COOKIE_NAME
    return SECURE_COOKIE_NAME


def require_origin(request: Request, settings: Settings) -> None:
    origin = request.headers.get("origin")
    if (
        origin is None
        or settings.canonical_origin is None
        or not secrets.compare_digest(origin, settings.canonical_origin)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Request forbidden")


def require_authenticated_actor(
    request: Request,
    database: Annotated[Session, Depends(get_database_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedActor:
    raw_token = request.cookies.get(session_cookie_name(settings))
    if raw_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    try:
        user, auth_session = resolve_session(database, raw_token, settings)
    except (InvalidCredentialsError, UnicodeEncodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        ) from exc
    return AuthenticatedActor(
        user_id=user.id,
        login_name=user.login_name,
        display_name=user.display_name,
        owner=user.owner,
        session=auth_session,
    )


def require_csrf(
    request: Request,
    actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> AuthenticatedActor:
    require_origin(request, settings)
    if csrf_token is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Request forbidden")
    try:
        valid = verify_csrf(actor.session, csrf_token)
    except UnicodeEncodeError:
        valid = False
    if not valid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Request forbidden")
    return actor


def require_owner(
    actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
) -> AuthenticatedActor:
    if not actor.owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Request forbidden")
    return actor
