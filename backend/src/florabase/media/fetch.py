"""Explicit external-image fetches only; validated addresses are pinned to sockets."""

import ipaddress
import socket
import ssl
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from http.client import HTTPConnection, HTTPException
from io import BytesIO
from threading import Timer
from urllib.parse import quote, urljoin, urlsplit

from florabase.attachments.model import SUPPORTED_MEDIA_TYPES

FETCH_TIMEOUT = 15.0
MAX_REDIRECTS = 3
_DNS = ThreadPoolExecutor(max_workers=4, thread_name_prefix="media-dns")


class ExternalFetchError(Exception):
    """Deliberately contains no destination, resolver or connection details."""


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ExternalFetchError("Could not fetch the external image safely. Try again.")
    return remaining


def _destination(url: str, deadline: float) -> tuple[str, int, str, str]:
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or any(ord(character) <= 32 or ord(character) == 127 for character in url)
    ):
        raise ExternalFetchError("This external image destination is not allowed.")
    host = parsed.hostname.encode("idna").decode("ascii")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if "%" in host:
        raise ExternalFetchError("This external image destination is not allowed.")
    # Bound DNS latency and concurrency. All returned addresses must be public;
    # the chosen numeric address is connected directly, never resolved a second time.
    future = _DNS.submit(socket.getaddrinfo, host, port, 0, socket.SOCK_STREAM)
    try:
        addresses = future.result(timeout=_remaining(deadline))
    finally:
        future.cancel()
    if not addresses:
        raise ExternalFetchError("This external image destination is not allowed.")
    for address in addresses:
        ip = ipaddress.ip_address(str(address[4][0]))
        mapped = getattr(ip, "ipv4_mapped", None)
        if (
            not ip.is_global
            or ip.is_multicast
            or ip.is_reserved
            or (mapped is not None and not mapped.is_global)
            or (
                isinstance(ip, ipaddress.IPv6Address)
                and (
                    ip.sixtofour
                    or ip.teredo
                    or ip in ipaddress.ip_network("64:ff9b::/96")
                    or ip in ipaddress.ip_network("64:ff9b:1::/48")
                )
            )
        ):
            raise ExternalFetchError("This external image destination is not allowed.")
    return host, port, str(addresses[0][4][0]), parsed.scheme


class _PinnedConnection(HTTPConnection):
    def __init__(self, host: str, port: int, address: str, scheme: str, timeout: float) -> None:
        super().__init__(host, port, timeout=timeout)
        self.address = address
        self.scheme = scheme
        self.connected_socket: socket.socket | None = None

    def connect(self) -> None:
        family = socket.AF_INET6 if ":" in self.address else socket.AF_INET
        connection = socket.socket(family, socket.SOCK_STREAM)
        self.sock = connection
        connection.settimeout(self.timeout)
        try:
            self.connected_socket = connection
            connection.connect((self.address, self.port))
            if self.scheme == "https":
                # Certificate verification and SNI use the canonical hostname,
                # while the TCP socket uses only the validated numeric address.
                self.sock = ssl.create_default_context().wrap_socket(
                    connection, server_hostname=self.host
                )
                self.connected_socket = self.sock
        except BaseException:
            connection.close()
            raise

    def expire(self) -> None:
        if self.connected_socket is not None:
            with suppress(OSError):
                self.connected_socket.shutdown(socket.SHUT_RDWR)
            self.connected_socket.close()


def fetch_image(url: str, max_bytes: int) -> tuple[bytes, str]:
    """No proxy environment, cookies, credentials, automatic redirects or retries."""
    deadline = time.monotonic() + FETCH_TIMEOUT
    try:
        for redirect in range(MAX_REDIRECTS + 1):
            host, port, address, scheme = _destination(url, deadline)
            connection = _PinnedConnection(host, port, address, scheme, _remaining(deadline))
            timer = Timer(_remaining(deadline), connection.expire)
            timer.daemon = True
            timer.start()
            try:
                parsed = urlsplit(url)
                path = quote(parsed.path or "/", safe="/%:@!$&'()*+,;=-._~")
                if parsed.query:
                    path += "?" + quote(parsed.query, safe="/%?:@!$&'()*+,;=-._~")
                connection.request(
                    "GET", path, headers={"Accept": "image/jpeg,image/png,image/webp"}
                )
                response = connection.getresponse()
                if response.status in {301, 302, 303, 307, 308}:
                    location = response.getheader("Location")
                    if not location or redirect == MAX_REDIRECTS:
                        raise ExternalFetchError("The external image redirected too many times.")
                    url = urljoin(url, location)
                    continue
                if response.status != 200:
                    raise ExternalFetchError("The external image is unavailable. Try again.")
                media_type = (
                    (response.getheader("Content-Type") or "").split(";", 1)[0].strip().lower()
                )
                if media_type not in SUPPORTED_MEDIA_TYPES:
                    raise ExternalFetchError("Only JPEG, PNG, and WebP images can be saved.")
                if response.getheader("Content-Encoding", "identity") != "identity":
                    raise ExternalFetchError("The external image response is unsupported.")
                length = response.getheader("Content-Length")
                if length is not None and (int(length) < 1 or int(length) > max_bytes):
                    raise ExternalFetchError("The external image exceeds the allowed size.")
                payload = BytesIO()
                while True:
                    _remaining(deadline)
                    chunk = response.read(min(64 * 1024, max_bytes + 1 - payload.tell()))
                    if not chunk:
                        break
                    payload.write(chunk)
                    if payload.tell() > max_bytes:
                        raise ExternalFetchError("The external image exceeds the allowed size.")
                _remaining(deadline)
                if length is not None and payload.tell() != int(length):
                    raise ExternalFetchError("The external image response is incomplete.")
                if not payload.tell():
                    raise ExternalFetchError("The external image is empty.")
                return payload.getvalue(), media_type
            finally:
                timer.cancel()
                connection.close()
    except ExternalFetchError:
        raise
    except (OSError, ValueError, UnicodeError, HTTPException, TimeoutError) as error:
        raise ExternalFetchError("Could not fetch the external image safely. Try again.") from error
    raise ExternalFetchError("The external image is unavailable.")
