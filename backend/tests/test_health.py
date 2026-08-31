import asyncio
import json

from starlette.types import Message, Scope

from florabase.api.health import database_readiness
from florabase.main import app


async def request(path: str) -> tuple[int, dict[str, str]]:
    messages: list[Message] = []
    request_sent = False

    async def receive() -> Message:
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        messages.append(message)

    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
        "state": {},
    }
    await app(scope, receive, send)

    start = next(message for message in messages if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"") for message in messages if message["type"] == "http.response.body"
    )
    return int(start["status"]), json.loads(body)


def test_health_is_liveness_only() -> None:
    status_code, payload = asyncio.run(request("/api/v1/health"))

    assert status_code == 200
    assert payload == {"status": "ok"}


def test_readiness_succeeds_when_database_dependency_succeeds() -> None:
    async def database_is_ready() -> None:
        return None

    app.dependency_overrides[database_readiness] = database_is_ready
    try:
        status_code, payload = asyncio.run(request("/api/v1/ready"))
    finally:
        app.dependency_overrides.clear()

    assert status_code == 200
    assert payload == {"status": "ok"}
