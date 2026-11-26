from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StrictStr
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from florabase.auth.dependencies import (
    BEARER_CHALLENGE,
    AuthenticatedActor,
    require_authenticated_actor,
    require_bearer_actor,
    require_cookie_actor,
    require_cookie_csrf,
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
    InvalidDeviceLabelError,
    InvalidNewPasswordError,
    LoginThrottledError,
    NewSession,
    PasswordUnchangedError,
    SessionCsrfError,
    authenticate,
    authenticate_device,
    change_password,
    list_active_device_sessions,
    lock_presenting_session,
    revoke_all_device_sessions,
    revoke_device_session_by_id,
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
CookieCsrfActor = Annotated[AuthenticatedActor, Depends(require_cookie_csrf)]
CookieActor = Annotated[AuthenticatedActor, Depends(require_cookie_actor)]
BearerActor = Annotated[AuthenticatedActor, Depends(require_bearer_actor)]
SessionActor = Annotated[AuthenticatedActor, Depends(require_authenticated_actor)]
CsrfHeader = Annotated[str, Header(alias="X-CSRF-Token")]
Utf8String = Annotated[StrictStr, AfterValidator(require_utf8)]


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    login_name: Utf8String = Field(min_length=1, max_length=128)
    password: Utf8String = Field(min_length=1, max_length=1_024, repr=False)


class DeviceSessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    login_name: Utf8String = Field(min_length=1, max_length=128)
    password: Utf8String = Field(min_length=1, max_length=1_024, repr=False)
    device_label: Utf8String = Field(min_length=1, max_length=120)


class DeviceSessionCreateResponse(BaseModel):
    session_id: UUID
    token: str = Field(repr=False)
    device_label: str
    created_at: datetime
    idle_expires_at: datetime
    absolute_expires_at: datetime


class DeviceSessionItem(BaseModel):
    id: UUID
    device_label: str
    created_at: datetime
    last_seen_at: datetime
    idle_expires_at: datetime
    absolute_expires_at: datetime
    current: bool


class DeviceSessionListResponse(BaseModel):
    items: list[DeviceSessionItem]


class DeviceSessionRevokeAllResponse(BaseModel):
    revoked_count: int


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
    demo_readonly: bool = False


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
    "/device-sessions",
    response_model=DeviceSessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createDeviceSession",
)
def create_device_session(
    payload: DeviceSessionCreateRequest,
    request: Request,
    response: Response,
    database: Database,
    settings: AuthSettings,
) -> DeviceSessionCreateResponse | JSONResponse:
    # No Origin check here: this endpoint creates a Bearer-only device session with no cookie
    # side-effects and requires Content-Type: application/json (415 otherwise), so browser form
    # CSRF cannot reach it. Reject if a browser session cookie is also attached.
    if request.cookies.get(session_cookie_name(settings)) is not None:
        return JSONResponse(
            {"detail": "Ambiguous authentication credentials"},
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"Cache-Control": "no-store", **BEARER_CHALLENGE},
        )
    try:
        result = authenticate_device(
            database,
            payload.login_name,
            payload.password,
            payload.device_label,
            settings,
        )
    except InvalidDeviceLabelError:
        return auth_error(422, "Check the login name, password, and device label.")
    except LoginThrottledError as error:
        return _backoff(error, "Too many login attempts")
    except InvalidCredentialsError:
        return auth_error(401, "Invalid login credentials")

    response.headers["Cache-Control"] = "no-store"
    assert result.session.device_label is not None
    return DeviceSessionCreateResponse(
        session_id=result.session.id,
        token=result.token,
        device_label=result.session.device_label,
        created_at=result.session.created_at,
        idle_expires_at=result.session.idle_expires_at,
        absolute_expires_at=result.session.absolute_expires_at,
    )


@router.get(
    "/device-sessions",
    response_model=DeviceSessionListResponse,
    operation_id="listDeviceSessions",
)
def list_device_sessions(
    response: Response,
    actor: SessionActor,
    database: Database,
) -> DeviceSessionListResponse:
    rows = list_active_device_sessions(database, actor.user_id)
    response.headers["Cache-Control"] = "no-store"
    return DeviceSessionListResponse(
        items=[
            DeviceSessionItem(
                id=row.id,
                device_label=row.device_label or "",
                created_at=row.created_at,
                last_seen_at=row.last_seen_at,
                idle_expires_at=row.idle_expires_at,
                absolute_expires_at=row.absolute_expires_at,
                current=actor.transport == "bearer" and row.id == actor.session.id,
            )
            for row in rows
        ]
    )


@router.delete(
    "/device-sessions/current",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="revokeCurrentDeviceSession",
)
def revoke_current_device_session(
    actor: BearerActor,
    database: Database,
) -> Response:
    if not revoke_device_session_by_id(database, actor.user_id, actor.session.id):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Authentication required",
            headers=BEARER_CHALLENGE,
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers={"Cache-Control": "no-store"})


@router.delete(
    "/device-sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="revokeDeviceSession",
)
def revoke_device_session(
    session_id: UUID,
    actor: CsrfActor,
    database: Database,
) -> Response:
    revoked = revoke_device_session_by_id(database, actor.user_id, session_id)
    if not revoked:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device session not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers={"Cache-Control": "no-store"})


@router.delete(
    "/device-sessions",
    response_model=DeviceSessionRevokeAllResponse,
    operation_id="revokeAllDeviceSessions",
)
def revoke_all_owner_device_sessions(
    response: Response,
    actor: CsrfActor,
    database: Database,
) -> DeviceSessionRevokeAllResponse:
    count = revoke_all_device_sessions(database, actor.user_id)
    response.headers["Cache-Control"] = "no-store"
    return DeviceSessionRevokeAllResponse(revoked_count=count)


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
    actor: CookieCsrfActor,
    database: Database,
    settings: AuthSettings,
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> LoginResponse | JSONResponse:
    require_owner(actor)
    if csrf_token is None:
        raise HTTPException(403, "Request forbidden")
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
        demo_readonly=settings.demo_readonly,
    )


@router.post("/csrf", response_model=CsrfResponse, operation_id="recoverCsrf")
def recover_csrf(
    request: Request,
    response: Response,
    actor: CookieActor,
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
    actor: CookieCsrfActor,
    database: Database,
    settings: AuthSettings,
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> LogoutResponse:
    if csrf_token is None:
        raise HTTPException(403, "Request forbidden")
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
