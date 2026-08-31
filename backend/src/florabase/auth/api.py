from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
    require_origin,
    session_cookie_name,
)
from florabase.auth.service import (
    InvalidCredentialsError,
    LoginThrottledError,
    authenticate,
    revoke_session,
    rotate_csrf,
)
from florabase.core.config import CookieMode, Settings, get_settings
from florabase.db.session import get_database_session

router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    login_name: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1_024)


class LoginResponse(BaseModel):
    csrf_token: str


class CsrfResponse(BaseModel):
    csrf_token: str


class SessionResponse(BaseModel):
    user_id: str
    login_name: str
    display_name: str | None
    owner: bool


class LogoutResponse(BaseModel):
    status: str


@router.post("/login", response_model=LoginResponse, operation_id="login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    database: Annotated[Session, Depends(get_database_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    require_origin(request, settings)
    try:
        result = authenticate(database, payload.login_name, payload.password, settings)
    except LoginThrottledError as exc:
        database.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    except InvalidCredentialsError as exc:
        database.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login credentials",
        ) from exc
    secure = settings.cookie_mode is CookieMode.SECURE
    response.set_cookie(
        key=session_cookie_name(settings),
        value=result.session_token,
        secure=secure,
        httponly=True,
        samesite="strict",
        path="/",
        max_age=settings.session_absolute_seconds,
    )
    response.headers["Cache-Control"] = "no-store"
    return LoginResponse(csrf_token=result.csrf_token)


@router.get("/session", response_model=SessionResponse, operation_id="getSession")
def get_session(
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
) -> SessionResponse:
    response.headers["Cache-Control"] = "no-store"
    return SessionResponse(
        user_id=str(actor.user_id),
        login_name=actor.login_name,
        display_name=actor.display_name,
        owner=actor.owner,
    )


@router.post("/csrf", response_model=CsrfResponse, operation_id="recoverCsrf")
def recover_csrf(
    request: Request,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CsrfResponse:
    require_origin(request, settings)
    csrf_token = rotate_csrf(actor.session)
    response.headers["Cache-Control"] = "no-store"
    return CsrfResponse(csrf_token=csrf_token)


@router.post("/logout", response_model=LogoutResponse, operation_id="logout")
def logout(
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LogoutResponse:
    revoke_session(database, actor.session)
    response.delete_cookie(
        key=session_cookie_name(settings),
        path="/",
        secure=settings.cookie_mode is CookieMode.SECURE,
        httponly=True,
        samesite="strict",
    )
    response.headers["Cache-Control"] = "no-store"
    return LogoutResponse(status="ok")
