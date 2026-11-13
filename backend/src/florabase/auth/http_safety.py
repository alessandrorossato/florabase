"""Request and response safeguards for the four auth mutations."""

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import HTTPException as FastAPIHTTPException
from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException
from starlette.requests import ClientDisconnect
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

AUTH_MUTATIONS = frozenset(
    f"/api/v1/auth/{action}" for action in ("login", "password", "csrf", "logout")
)
MAX_PASSWORD_BODY = 32 * 1024
PASSWORD_PATH = "/api/v1/auth/password"


def auth_error(status_code: int, detail: str | dict[str, str]) -> JSONResponse:
    return JSONResponse(
        {"detail": detail}, status_code=status_code, headers={"Cache-Control": "no-store"}
    )


def password_error(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def invalid_password_request() -> JSONResponse:
    return auth_error(422, password_error("invalid_password_request", "Check the password fields."))


class CredentialRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def handle(request: Request) -> Response:
            try:
                return await handler(request)
            except RequestValidationError:
                # Preserve an exception through dependency teardown so staged changes roll back.
                if request.url.path == PASSWORD_PATH:
                    raise FastAPIHTTPException(
                        422,
                        password_error("invalid_password_request", "Check the password fields."),
                    ) from None
                raise FastAPIHTTPException(422, "Check the login name and password.") from None
            except HTTPException as error:
                if request.url.path == PASSWORD_PATH and error.status_code == 400:
                    raise FastAPIHTTPException(
                        422,
                        password_error("invalid_password_request", "Check the password fields."),
                    ) from None
                raise

        return handle


class AuthSafetyMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "POST":
            await self.app(scope, receive, send)
            return
        path = scope["path"]
        if path.rstrip("/") not in AUTH_MUTATIONS:
            await self.app(scope, receive, send)
            return
        if path not in AUTH_MUTATIONS:
            await auth_error(404, "Not found")(scope, receive, send)
            return
        if scope["query_string"]:
            await auth_error(400, "Query parameters are not accepted")(scope, receive, send)
            return

        started = False

        async def send_auth_response(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                message["headers"] = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != b"cache-control"
                ] + [(b"cache-control", b"no-store")]
                status = message["status"]
                logger.info("auth_%s status=%d", path.rsplit("/", 1)[1], status)
            await send(message)

        try:
            if path == PASSWORD_PATH:
                request = Request(scope, receive)
                media_type = request.headers.get("content-type", "").split(";")
                encoding = request.headers.get("content-encoding", "identity").lower()
                if (
                    media_type[0].strip().lower() != "application/json"
                    or any(value.strip().lower() != "charset=utf-8" for value in media_type[1:])
                    or encoding != "identity"
                ):
                    await auth_error(415, "Expected a UTF-8 JSON body")(scope, receive, send)
                    return
                body = bytearray()
                async for chunk in request.stream():
                    if len(body) + len(chunk) > MAX_PASSWORD_BODY:
                        await auth_error(413, "Request body is too large")(scope, receive, send)
                        return
                    body.extend(chunk)
                # JSON never contains a raw NUL. Reject it before the downstream JSON
                # parser can auto-detect a UTF-16/32 byte stream as a different encoding.
                if b"\0" in body:
                    await invalid_password_request()(scope, receive, send)
                    return
                try:
                    body.decode("utf-8")
                except UnicodeDecodeError:
                    await invalid_password_request()(scope, receive, send)
                    return

                buffered = True

                async def receive_bounded() -> Message:
                    nonlocal buffered
                    if not buffered:
                        return await receive()
                    buffered = False
                    return {"type": "http.request", "body": bytes(body), "more_body": False}

                await self.app(scope, receive_bounded, send_auth_response)
            else:
                await self.app(scope, receive, send_auth_response)
        except ClientDisconnect:
            return
        except Exception:
            logger.error("auth_%s failed", path.rsplit("/", 1)[1])
            if not started:
                await auth_error(500, "Authentication operation failed")(scope, receive, send)
            else:
                raise RuntimeError("Authentication response failed") from None
