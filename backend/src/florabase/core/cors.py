"""Scoped, credential-free CORS middleware for bundled Capacitor native app origins."""

from __future__ import annotations

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

NATIVE_APP_CORS_ORIGINS: frozenset[str] = frozenset(
    {
        "https://localhost",
        "capacitor://localhost",
    }
)
NATIVE_APP_ALLOW_METHODS: tuple[str, ...] = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
NATIVE_APP_ALLOW_METHODS_SET: frozenset[str] = frozenset(NATIVE_APP_ALLOW_METHODS)
NATIVE_APP_ALLOW_HEADERS: tuple[str, ...] = ("Authorization", "Content-Type", "X-Request-Id")
NATIVE_APP_ALLOW_HEADERS_LOWER: frozenset[str] = frozenset(
    header.lower() for header in NATIVE_APP_ALLOW_HEADERS
)
NATIVE_APP_EXPOSE_HEADERS: tuple[str, ...] = ("Content-Disposition", "Retry-After")


class NativeAppCorsMiddleware:
    """Allow credential-free Bearer requests from the fixed Capacitor WebView origins.

    Requests from any other origin pass through untouched so existing same-origin production
    behaviour and optional development `FLORABASE_CORS_ORIGINS` handling remain unchanged.
    `Access-Control-Allow-Credentials` is never emitted by this middleware.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        origin = headers.get("origin")
        if origin is None or origin not in NATIVE_APP_CORS_ORIGINS:
            await self.app(scope, receive, send)
            return

        if (
            scope["method"] == "OPTIONS"
            and headers.get("access-control-request-method") is not None
        ):
            response = self._preflight_response(origin, headers)
            await response(scope, receive, send)
            return

        async def send_with_cors(message: Message) -> None:
            if message["type"] == "http.response.start":
                mutable = MutableHeaders(scope=message)
                mutable["Access-Control-Allow-Origin"] = origin
                mutable["Access-Control-Expose-Headers"] = ", ".join(NATIVE_APP_EXPOSE_HEADERS)
                mutable.add_vary_header("Origin")
                # Never advertise credentials on the native Bearer CORS path.
                if "access-control-allow-credentials" in mutable:
                    del mutable["access-control-allow-credentials"]
            await send(message)

        await self.app(scope, receive, send_with_cors)

    def _preflight_response(self, origin: str, request_headers: Headers) -> PlainTextResponse:
        requested_method = request_headers.get("access-control-request-method", "").strip().upper()
        requested_headers_raw = request_headers.get("access-control-request-headers", "")
        requested_headers = [
            item.strip().lower() for item in requested_headers_raw.split(",") if item.strip()
        ]

        failures: list[str] = []
        if requested_method not in NATIVE_APP_ALLOW_METHODS_SET:
            failures.append("method")
        disallowed_headers = [
            header for header in requested_headers if header not in NATIVE_APP_ALLOW_HEADERS_LOWER
        ]
        if disallowed_headers:
            failures.append("headers")

        base_headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": ", ".join(NATIVE_APP_ALLOW_METHODS),
            "Access-Control-Allow-Headers": ", ".join(NATIVE_APP_ALLOW_HEADERS),
            "Access-Control-Max-Age": "600",
            "Vary": "Origin, Access-Control-Request-Method, Access-Control-Request-Headers",
        }
        if failures:
            return PlainTextResponse(
                f"Disallowed CORS {', '.join(failures)}",
                status_code=400,
                headers={"Vary": base_headers["Vary"]},
            )
        return PlainTextResponse("OK", status_code=200, headers=base_headers)
