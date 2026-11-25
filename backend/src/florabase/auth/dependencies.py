import secrets
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from florabase.auth.model import AuthSession
from florabase.auth.service import (
    InvalidCredentialsError,
    SessionTransport,
    resolve_session,
    verify_csrf,
)
from florabase.core.config import CookieMode, Settings, get_settings
from florabase.db.session import get_database_session

SECURE_COOKIE_NAME = "__Host-florabase-session"
DEVELOPMENT_COOKIE_NAME = "florabase-session-dev"
BEARER_CHALLENGE = {"WWW-Authenticate": "Bearer"}


@dataclass(frozen=True)
class AuthenticatedActor:
    user_id: UUID
    login_name: str
    display_name: str | None
    owner: bool
    session: AuthSession
    transport: SessionTransport = "cookie"


def session_cookie_name(settings: Settings) -> str:
    if settings.cookie_mode is CookieMode.LOOPBACK_DEVELOPMENT:
        return DEVELOPMENT_COOKIE_NAME
    return SECURE_COOKIE_NAME


def require_origin(request: Request, settings: Settings) -> None:
    origins = request.headers.getlist("origin")
    expected = settings.canonical_origin
    if (
        len(origins) != 1
        or not origins[0].isascii()
        or expected is None
        or not expected.isascii()
        or not secrets.compare_digest(origins[0], expected)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Request forbidden")


def _extract_bearer_token(auth_headers: list[str]) -> str | None:
    if len(auth_headers) != 1:
        return None
    raw = auth_headers[0].strip()
    scheme, separator, token = raw.partition(" ")
    if not separator or scheme.lower() != "bearer":
        return None
    token = token.strip()
    if not token or not token.isascii() or any(char.isspace() for char in token):
        return None
    return token


def require_authenticated_actor(
    request: Request,
    database: Annotated[Session, Depends(get_database_session, scope="function")],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedActor:
    cookie_token = request.cookies.get(session_cookie_name(settings))
    auth_headers = request.headers.getlist("authorization")
    has_auth_header = any(header.strip() != "" for header in auth_headers)

    if cookie_token is not None and has_auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ambiguous authentication credentials",
            headers=BEARER_CHALLENGE,
        )

    if has_auth_header:
        raw_bearer = _extract_bearer_token(auth_headers)
        if raw_bearer is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers=BEARER_CHALLENGE,
            )
        try:
            user, auth_session = resolve_session(
                database, raw_bearer, settings, expected_transport="bearer"
            )
        except (InvalidCredentialsError, UnicodeEncodeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers=BEARER_CHALLENGE,
            ) from exc
        return AuthenticatedActor(
            user_id=user.id,
            login_name=user.login_name,
            display_name=user.display_name,
            owner=user.owner,
            session=auth_session,
            transport="bearer",
        )

    if cookie_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    try:
        user, auth_session = resolve_session(
            database, cookie_token, settings, expected_transport="cookie"
        )
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
        transport="cookie",
    )


def require_cookie_actor(
    actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
) -> AuthenticatedActor:
    if actor.transport != "cookie":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Request forbidden")
    return actor


def require_bearer_actor(
    actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
) -> AuthenticatedActor:
    if actor.transport != "bearer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Request forbidden")
    return actor


def require_csrf(
    request: Request,
    actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> AuthenticatedActor:
    if actor.transport == "bearer":
        # Bearer tokens are not ambient browser credentials, so CSRF and Origin checks do not apply.
        return actor
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


def require_cookie_csrf(
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
) -> AuthenticatedActor:
    if actor.transport != "cookie":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Request forbidden")
    return actor


def require_owner(
    actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
) -> AuthenticatedActor:
    if not actor.owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Request forbidden")
    return actor
