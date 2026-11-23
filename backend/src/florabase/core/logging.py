import json
import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import unquote

from florabase.core.config import LogFormat, Settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


_HEALTH_PROBE_PATHS = frozenset({"/api/v1/health", "/api/v1/ready"})


def _is_loopback_client(client_addr: str) -> bool:
    if client_addr in {"127.0.0.1", "::1"}:
        return True
    host, separator, port = client_addr.rpartition(":")
    if not separator or not port.isdigit():
        return False
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    return host in {"127.0.0.1", "::1"}


class AuthAccessFilter(logging.Filter):
    """Remove query strings from pinned Uvicorn auth access records before formatting."""

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if not isinstance(args, tuple) or len(args) != 5 or not isinstance(args[2], str):
            # The server's access logger should only emit the standard five-argument record.
            return False
        path = args[2].partition("?")[0]
        if unquote(path).startswith("/api/v1/auth/"):
            record.args = (*args[:2], path, *args[3:])
        return True


class HealthProbeAccessFilter(logging.Filter):
    """Drop successful loopback health and readiness probe records from Uvicorn access logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if not isinstance(args, tuple) or len(args) != 5:
            return True
        client, method, path, _, status = args
        return not (
            isinstance(client, str)
            and _is_loopback_client(client)
            and method == "GET"
            and isinstance(path, str)
            and path in _HEALTH_PROBE_PATHS
            and isinstance(status, int)
            and not isinstance(status, bool)
            and 200 <= status < 300
        )


def configure_logging(settings: Settings) -> None:
    handler = logging.StreamHandler()
    if settings.log_format is LogFormat.JSON:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())
    access = logging.getLogger("uvicorn.access")
    if not any(isinstance(item, AuthAccessFilter) for item in access.filters):
        access.addFilter(AuthAccessFilter())
    if not any(isinstance(item, HealthProbeAccessFilter) for item in access.filters):
        access.addFilter(HealthProbeAccessFilter())
