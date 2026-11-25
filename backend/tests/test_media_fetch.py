import socket
import ssl
import time
from io import BytesIO
from unittest.mock import MagicMock

import pytest

import florabase
from florabase.media import fetch
from florabase.media.schemas import ExternalAssetCreate

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


def test_user_agent_is_sent_on_first_request_and_after_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = transport(
        monkeypatch,
        [response(status=302, headers={"Location": "/new.png"}), response(b"png")],
    )
    fetch.fetch_image("https://example.test/original.png", 1024)
    requests = factory.return_value.request.call_args_list
    assert len(requests) == 2
    for call in requests:
        assert call.kwargs["headers"] == {
            "Accept": "image/jpeg,image/png,image/webp",
            "User-Agent": fetch.USER_AGENT,
        }
    assert fetch.USER_AGENT.startswith(f"Florabase/{florabase.__version__} media-copy (+https://")


def test_html_page_has_direct_address_message(monkeypatch: pytest.MonkeyPatch) -> None:
    transport(monkeypatch, [response(b"<html>", "text/html; charset=UTF-8")])
    with pytest.raises(fetch.ExternalFetchError, match="web page, not an image") as error:
        fetch.fetch_image("https://example.test/page", 1024)
    assert "example.test" not in str(error.value)


def test_wikimedia_file_page_is_fetched_through_file_path(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = transport(monkeypatch, [response(b"png")])
    fetch.fetch_image("https://it.wikipedia.org/wiki/File:Unk_desert_flower_2.jpg", 1024)
    assert factory.call_args.args[0] == "it.wikipedia.org"
    assert factory.return_value.request.call_args.args[1] == (
        "/wiki/Special:FilePath/Unk_desert_flower_2.jpg"
    )


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "https://it.wikipedia.org/wiki/File:Unk_desert_flower_2.jpg",
            "https://it.wikipedia.org/wiki/Special:FilePath/Unk_desert_flower_2.jpg",
        ),
        (
            "https://en.wikipedia.org/wiki/Image:Rosa%20canina.jpg?uselang=en#top",
            "https://en.wikipedia.org/wiki/Special:FilePath/Rosa_canina.jpg",
        ),
        (
            "https://commons.wikimedia.org/wiki/File:Aloe_vera_(flower).JPG",
            "https://commons.wikimedia.org/wiki/Special:FilePath/Aloe_vera_(flower).JPG",
        ),
        (
            "https://it.m.wikipedia.org/wiki/Immagine:Fiore.png",
            "https://it.m.wikipedia.org/wiki/Special:FilePath/Fiore.png",
        ),
        (
            "https://de.wikipedia.org/wiki/Datei:K%C3%B6nigskerze_%26_Co.jpg",
            "https://de.wikipedia.org/wiki/Special:FilePath/K%C3%B6nigskerze_%26_Co.jpg",
        ),
        (
            "https://fr.wikipedia.org/wiki/fichier:Rose.jpg",
            "https://fr.wikipedia.org/wiki/Special:FilePath/Rose.jpg",
        ),
        (
            "https://nl.wikipedia.org/wiki/Bestand:Tulp 1.jpg",
            "https://nl.wikipedia.org/wiki/Special:FilePath/Tulp_1.jpg",
        ),
        (
            "https://es.wikipedia.org/wiki/Archivo:Flor.jpg",
            "https://es.wikipedia.org/wiki/Special:FilePath/Flor.jpg",
        ),
        (
            "https://pt.wikipedia.org/wiki/Ficheiro:Flor%2Fa.jpg",
            "https://pt.wikipedia.org/wiki/Special:FilePath/Flor%2Fa.jpg",
        ),
    ],
)
def test_wikimedia_file_pages_rewrite_to_file_path(url: str, expected: str) -> None:
    assert fetch.wikimedia_file_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://commons.wikimedia.org/wiki/Special:FilePath/Rose.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/a/ab/Rose.jpg",
        "https://it.wikipedia.org/wiki/Rosa_canina",
        "https://it.wikipedia.org/wiki/File:",
        "https://wikipedia.org.example.test/wiki/File:Rose.jpg",
        "https://example.test/wiki/File:Rose.jpg",
        "https://it.wikipedia.org:8443/wiki/File:Rose.jpg",
        "https://it.wikipedia.org/w/index.php?title=File:Rose.jpg",
        "not a url",
    ],
)
def test_non_wikimedia_file_pages_pass_through(url: str) -> None:
    assert fetch.wikimedia_file_url(url) == url


def test_external_reference_stores_file_path_and_keeps_source_page() -> None:
    page = "https://it.wikipedia.org/wiki/File:Unk_desert_flower_2.jpg"
    created = ExternalAssetCreate(image_url=page, source_url=page, attribution="Unknown")
    assert created.image_url == (
        "https://it.wikipedia.org/wiki/Special:FilePath/Unk_desert_flower_2.jpg"
    )
    assert created.source_url == page
