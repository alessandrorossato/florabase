import socket
import ssl
import time
from io import BytesIO
from unittest.mock import MagicMock

import pytest

from florabase.media import fetch

PUBLIC_IP = "93.184.216.34"


def resolve(monkeypatch: pytest.MonkeyPatch, addresses: list[str]) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_args: [
            (socket.AF_INET6 if ":" in ip else socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443))
            for ip in addresses
        ],
    )


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",
        "10.0.0.1",
        "172.16.0.1",
        "192.168.0.1",
        "169.254.169.254",
        "0.0.0.0",
        "224.0.0.1",
        "100.64.0.1",
        "198.18.0.1",
        "::1",
        "::",
        "fc00::1",
        "fe80::1",
        "ff02::1",
        "2001:db8::1",
        "::ffff:127.0.0.1",
        "64:ff9b::a00:1",
    ],
)
def test_rejects_non_public_addresses(monkeypatch: pytest.MonkeyPatch, ip: str) -> None:
    resolve(monkeypatch, [ip])
    with pytest.raises(fetch.ExternalFetchError, match="not allowed"):
        fetch.fetch_image("https://localhost/image.png", 1024)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.test/img",
        "https://user:pass@example.test/img",
        "https://example.test/\nheader",
        "https://[fe80::1%25eth0]/img",
        "https://example.test:bad/img",
    ],
)
def test_rejects_url_credentials_protocols_controls_and_ports(url: str) -> None:
    with pytest.raises(fetch.ExternalFetchError):
        fetch.fetch_image(url, 1024)


def test_validates_all_dns_results_and_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    resolve(monkeypatch, [PUBLIC_IP, "127.0.0.1"])
    with pytest.raises(fetch.ExternalFetchError, match="not allowed"):
        fetch.fetch_image("https://example.test/img", 1024)
    monkeypatch.setattr(fetch, "FETCH_TIMEOUT", 0.001)

    def slow(*_args: object) -> list[object]:
        time.sleep(0.02)
        return []

    monkeypatch.setattr(socket, "getaddrinfo", slow)
    with pytest.raises(fetch.ExternalFetchError, match="safely"):
        fetch.fetch_image("https://example.test/img", 1024)


def response(
    body: bytes = b"image",
    media_type: str = "image/png",
    status: int = 200,
    headers: dict[str, str] | None = None,
) -> MagicMock:
    result = MagicMock(status=status)
    source = BytesIO(body)
    result.read.side_effect = source.read
    metadata = {"Content-Type": media_type, **(headers or {})}
    result.getheader.side_effect = lambda key, default=None: metadata.get(key, default)
    return result


def transport(monkeypatch: pytest.MonkeyPatch, responses: list[MagicMock]) -> MagicMock:
    resolve(monkeypatch, [PUBLIC_IP])
    connection = MagicMock()
    connection.getresponse.side_effect = responses
    factory = MagicMock(return_value=connection)
    monkeypatch.setattr(fetch, "_PinnedConnection", factory)
    return factory


def test_public_fetch_and_redirect_are_pinned_and_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = transport(
        monkeypatch,
        [
            response(status=302, headers={"Location": "/new.png"}),
            response(b"png", "image/png; charset=binary"),
        ],
    )
    assert fetch.fetch_image("https://example.test/original.png", 3) == (b"png", "image/png")
    assert factory.call_count == 2
    assert factory.call_args.args[:4] == ("example.test", 443, PUBLIC_IP, "https")
    transport(
        monkeypatch, [response(status=302, headers={"Location": "https://example.test/again"})] * 4
    )
    with pytest.raises(fetch.ExternalFetchError, match="too many"):
        fetch.fetch_image("https://example.test/img", 1024)


def test_public_redirect_to_private_address_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    transport(monkeypatch, [response(status=302, headers={"Location": "http://127.0.0.1/private"})])
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, *_args: [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                (PUBLIC_IP if host == "example.test" else "127.0.0.1", 80),
            )
        ],
    )
    with pytest.raises(fetch.ExternalFetchError, match="not allowed"):
        fetch.fetch_image("https://example.test/img", 1024)


@pytest.mark.parametrize(
    "remote",
    [
        response(b"12345"),
        response(headers={"Content-Length": "99999"}),
        response(headers={"Content-Length": "bad"}),
        response(media_type="image/svg+xml"),
        response(status=500),
        response(b""),
        response(headers={"Content-Encoding": "gzip"}),
        response(status=302),
    ],
)
def test_size_mime_empty_status_encoding_and_missing_redirect(
    monkeypatch: pytest.MonkeyPatch, remote: MagicMock
) -> None:
    transport(monkeypatch, [remote])
    with pytest.raises(fetch.ExternalFetchError):
        fetch.fetch_image("https://example.test/img", 4)


def test_connection_timeout_has_generic_error(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = transport(monkeypatch, [])
    factory.return_value.request.side_effect = TimeoutError("private details")
    with pytest.raises(fetch.ExternalFetchError, match="safely") as error:
        fetch.fetch_image("https://example.test/img", 1024)
    assert "private details" not in str(error.value)


def test_socket_connect_pins_ip_but_tls_checks_hostname(monkeypatch: pytest.MonkeyPatch) -> None:
    sock = MagicMock()
    context = MagicMock()
    monkeypatch.setattr(socket, "socket", MagicMock(return_value=sock))
    monkeypatch.setattr(ssl, "create_default_context", lambda: context)
    connection = fetch._PinnedConnection("example.test", 443, PUBLIC_IP, "https", 1)
    connection.connect()
    sock.connect.assert_called_once_with((PUBLIC_IP, 443))
    context.wrap_socket.assert_called_once_with(sock, server_hostname="example.test")
    connection.expire()
    context.wrap_socket.return_value.shutdown.assert_called_once_with(socket.SHUT_RDWR)
    connection.close()
