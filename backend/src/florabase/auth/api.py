from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StrictStr
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
    require_origin,
    require_owner,
    session_cookie_name,
)
from florabase.auth.http_safety import CredentialRoute, auth_error, password_error
from florabase.auth.security import require_utf8
from florabase.auth.service import (
    InvalidCredentialsError,
    InvalidCurrentPasswordError,
    InvalidNewPasswordError,
    LoginThrottledError,
    NewSession,
    PasswordUnchangedError,
    SessionCsrfError,
    authenticate,
    change_password,
    lock_presenting_session,
    revoke_session,
    rotate_csrf,
)
from florabase.core.config import CookieMode, Settings, get_settings
from florabase.db.session import get_database_session

router = APIRouter(prefix="/auth", tags=["authentication"])
credentials = APIRouter(route_class=CredentialRoute)
Database = Annotated[Session, Depends(get_database_session, scope="function")]
AuthSettings = Annotated[Settings, Depends(get_settings)]
CsrfActor = Annotated[AuthenticatedActor, Depends(require_csrf)]
SessionActor = Annotated[AuthenticatedActor, Depends(require_authenticated_actor)]
CsrfHeader = Annotated[str, Header(alias="X-CSRF-Token")]
Utf8String = Annotated[StrictStr, AfterValidator(require_utf8)]


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    login_name: Utf8String = Field(min_length=1, max_length=128)
    password: Utf8String = Field(min_length=1, max_length=1_024, repr=False)


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: Utf8String = Field(
        min_length=1, max_length=1_024, repr=False, json_schema_extra={"writeOnly": True}
    )
    new_password: Utf8String = Field(
        min_length=12, max_length=1_024, repr=False, json_schema_extra={"writeOnly": True}
    )


class PasswordError(BaseModel):
    code: str
    message: str


class AuthErrorResponse(BaseModel):
    detail: str | PasswordError


class LoginResponse(BaseModel):
    csrf_token: str


class CsrfResponse(BaseModel):
    csrf_token: str


class SessionResponse(BaseModel):
    user_id: str
    login_name: str
    display_name: str | None
    owner: bool
    canonical_origin: str | None


class LogoutResponse(BaseModel):
    status: str


def _session_response(response: Response, result: NewSession, settings: Settings) -> LoginResponse:
    response.set_cookie(
        key=session_cookie_name(settings),
        value=result.session_token,
        secure=settings.cookie_mode is CookieMode.SECURE,
        httponly=True,
        samesite="strict",
        path="/",
        max_age=settings.session_absolute_seconds,
    )
    response.headers["Cache-Control"] = "no-store"
    return LoginResponse(csrf_token=result.csrf_token)


def _backoff(error: LoginThrottledError, detail: str) -> JSONResponse:
    response = auth_error(429, detail)
    response.headers["Retry-After"] = str(error.retry_after)
    return response


@credentials.post("/login", response_model=LoginResponse, operation_id="login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    database: Database,
    settings: AuthSettings,
) -> LoginResponse | JSONResponse:
    require_origin(request, settings)
    try:
        result = authenticate(database, payload.login_name, payload.password, settings)
    except LoginThrottledError as error:
        return _backoff(error, "Too many login attempts")
    except InvalidCredentialsError:
        return auth_error(401, "Invalid login credentials")
    return _session_response(response, result, settings)


@credentials.post(
    "/password",
    response_model=LoginResponse,
    operation_id="changePassword",
    responses={
        400: {"model": AuthErrorResponse},
        401: {"model": AuthErrorResponse},
        403: {"model": AuthErrorResponse},
        413: {"model": AuthErrorResponse},
        415: {"model": AuthErrorResponse},
        422: {"model": AuthErrorResponse},
        429: {
            "model": AuthErrorResponse,
            "headers": {"Retry-After": {"schema": {"type": "integer"}}},
        },
        500: {"model": AuthErrorResponse},
    },
)
def change_owner_password(
    payload: ChangePasswordRequest,
    response: Response,
    actor: CsrfActor,
    database: Database,
    settings: AuthSettings,
    csrf_token: CsrfHeader,
) -> LoginResponse | JSONResponse:
    require_owner(actor)
    try:
        result = change_password(
            database,
            actor.session,
            csrf_token,
            payload.current_password,
            payload.new_password,
            settings,
        )
    except InvalidCredentialsError:
        raise HTTPException(401, "Authentication required") from None
    except SessionCsrfError:
        raise HTTPException(403, "Request forbidden") from None
    except InvalidCurrentPasswordError:
        return auth_error(
            403, password_error("invalid_current_password", "Current password is incorrect.")
        )
    except InvalidNewPasswordError:
        raise HTTPException(
            422, password_error("invalid_new_password", "Check the new password.")
        ) from None
    except PasswordUnchangedError:
        raise HTTPException(
            422, password_error("password_unchanged", "Choose a different password.")
        ) from None
    except LoginThrottledError as error:
        return _backoff(error, "Too many password change attempts")
    return _session_response(response, result, settings)


@router.get("/session", response_model=SessionResponse, operation_id="getSession")
def get_session(response: Response, actor: SessionActor, settings: AuthSettings) -> SessionResponse:
    response.headers["Cache-Control"] = "no-store"
    return SessionResponse(
        user_id=str(actor.user_id),
        login_name=actor.login_name,
        display_name=actor.display_name,
        owner=actor.owner,
        canonical_origin=settings.canonical_origin,
    )


@router.post("/csrf", response_model=CsrfResponse, operation_id="recoverCsrf")
def recover_csrf(
    request: Request,
    response: Response,
    actor: SessionActor,
    settings: AuthSettings,
    database: Database,
) -> CsrfResponse:
    require_origin(request, settings)
    try:
        session = lock_presenting_session(database, actor.session)
    except InvalidCredentialsError:
        raise HTTPException(401, "Authentication required") from None
    csrf_token = rotate_csrf(session, settings)
    response.headers["Cache-Control"] = "no-store"
    return CsrfResponse(csrf_token=csrf_token)


@router.post("/logout", response_model=LogoutResponse, operation_id="logout")
def logout(
    response: Response,
    actor: CsrfActor,
    database: Database,
    settings: AuthSettings,
    csrf_token: CsrfHeader,
) -> LogoutResponse:
    try:
        session = lock_presenting_session(database, actor.session, csrf_token)
    except InvalidCredentialsError:
        raise HTTPException(401, "Authentication required") from None
    except SessionCsrfError:
        raise HTTPException(403, "Request forbidden") from None
    revoke_session(database, session)
    response.delete_cookie(
        key=session_cookie_name(settings),
        path="/",
        secure=settings.cookie_mode is CookieMode.SECURE,
        httponly=True,
        samesite="strict",
    )
    response.headers["Cache-Control"] = "no-store"
    return LogoutResponse(status="ok")


router.include_router(credentials)
