"""Plain-ASCII container startup banner read directly from environment variables."""

import re
import sys
from collections.abc import Mapping
from typing import TextIO
from urllib.parse import urlsplit

from florabase import __version__

BANNER_PROJECT_URL = "https://github.com/alessandrorossato/florabase"
BANNER_MAX_WIDTH = 72
DEFAULT_PLACEHOLDER_ORIGIN = "https://florabase.example.org"

# Generated once with `figlet -f standard Florabase` and a minimal botanical sprout motif.
BANNER_ART = (
    "   _      _____ _                 _\n"
    "  / \\    |  ___| | ___  _ __ __ _| |__   __ _ ___  ___\n"
    " ( | )   | |_  | |/ _ \\| '__/ _` | '_ \\ / _` / __|/ _ \\\n"
    "  \\|/    |  _| | | (_) | | | (_| | |_) | (_| \\__ \\  __/\n"
    "   |     |_|   |_|\\___/|_|  \\__,_|_.__/ \\__,_|___/\\___|"
)

_HEX_REVISION = re.compile(r"[0-9a-fA-F]{8,64}")


def _is_printable_ascii_token(value: str) -> bool:
    return bool(value) and all(33 <= ord(char) <= 126 for char in value)


def _sanitize_ascii(value: str, *, default: str, max_len: int) -> str:
    cleaned = value.strip()
    if not _is_printable_ascii_token(cleaned):
        return default
    return cleaned[:max_len]


def _format_revision(environ: Mapping[str, str]) -> str:
    raw = environ.get("FLORABASE_REVISION", "").strip()
    if not raw:
        return "unknown"
    if _HEX_REVISION.fullmatch(raw):
        return raw[:7].lower()
    return _sanitize_ascii(raw, default="unknown", max_len=12)


def _format_origin(environ: Mapping[str, str], placeholder: str) -> str:
    raw = environ.get("FLORABASE_CANONICAL_ORIGIN", "").strip()
    if not raw:
        return "not set"
    parsed = urlsplit(raw)
    try:
        port = parsed.port
    except ValueError:
        return "invalid"
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname
    if scheme not in {"http", "https"} or not hostname or not _is_printable_ascii_token(hostname):
        return "invalid"
    host = f"[{hostname}]" if ":" in hostname else hostname
    authority = f"{host}:{port}" if port is not None else host
    reduced = f"{scheme}://{authority}"
    if reduced == placeholder:
        return "placeholder, not configured"
    max_origin_len = BANNER_MAX_WIDTH - len("Origin:      ")
    if len(reduced) > max_origin_len:
        return reduced[: max_origin_len - 3] + "..."
    return reduced


def render_startup_banner(
    environ: Mapping[str, str],
    *,
    version: str = __version__,
    placeholder_origin: str = DEFAULT_PLACEHOLDER_ORIGIN,
) -> str:
    """Render the plain-ASCII startup banner without touching Settings or leaking secrets."""
    revision = _format_revision(environ)
    origin = _format_origin(environ, placeholder_origin)
    environment = _sanitize_ascii(
        environ.get("FLORABASE_ENVIRONMENT", ""), default="production", max_len=24
    )
    log_format = _sanitize_ascii(
        environ.get("FLORABASE_LOG_FORMAT", ""), default="json", max_len=16
    )
    lines = [
        *BANNER_ART.splitlines(),
        "",
        f"Florabase {version} ({revision})",
        f"Origin:      {origin}",
        f"Environment: {environment} (log: {log_format})",
        f"Project:     {BANNER_PROJECT_URL}",
    ]
    return "\n".join(lines) + "\n"


def print_startup_banner(
    environ: Mapping[str, str],
    *,
    stream: TextIO | None = None,
) -> None:
    target = sys.stdout if stream is None else stream
    target.write(render_startup_banner(environ))
    target.flush()
