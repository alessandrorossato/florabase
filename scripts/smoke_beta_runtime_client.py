#!/usr/bin/env python3
"""HTTP client for smoke-beta-runtime.py; runs beside the stack under the DSM-equivalent Python 3.8.

seed:     create relationship/media fixtures through the public API as the owner.
snapshot: canonical owner-visible state (assets, links, original SHA-256) for exact comparison.
Password on stdin. Explicit secure-cookie replay over loopback HTTP tests server policy only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
import urllib.error
import urllib.request
import zlib
from http.client import HTTPMessage
from http.cookies import CookieError, SimpleCookie
from typing import Any


def png(red: int, green: int, blue: int) -> bytes:
    """A valid 1x1 RGB PNG; distinct colours give distinct original digests."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    pixels = zlib.compress(bytes([0, red, green, blue]))
    return (
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", pixels) + chunk(b"IEND", b"")
    )


def response_object(data: bytes, operation: str) -> dict[str, Any]:
    try:
        value = json.loads(data)
    except ValueError:
        raise RuntimeError(f"{operation}: invalid JSON response") from None
    if not isinstance(value, dict):
        raise RuntimeError(f"{operation}: expected a JSON object")
    return value


class ExactStatus(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        return None


class Client:
    def __init__(self, base: str, origin: str) -> None:
        self.base = base.rstrip("/")
        self.origin = origin
        self.cookie = ""
        self.csrf = ""
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), ExactStatus())

    def request(
        self,
        path: str,
        method: str = "GET",
        body: bytes | None = None,
        content_type: str | None = None,
        expected: int = 200,
    ) -> tuple[bytes, HTTPMessage]:
        headers: dict[str, str] = {}
        if self.cookie:
            headers["Cookie"] = self.cookie
        if method != "GET":
            headers["Origin"] = self.origin
            if self.csrf:
                headers["X-CSRF-Token"] = self.csrf
        if content_type:
            headers["Content-Type"] = content_type
        request = urllib.request.Request(self.base + path, body, headers, method=method)
        try:
            response = self.opener.open(request, timeout=30)
        except urllib.error.HTTPError as error:
            response = error
        except (OSError, ValueError):
            raise RuntimeError(f"{method} {path.partition('?')[0]}: request failed") from None
        with response:
            if response.status != expected:
                raise RuntimeError(
                    f"{method} {path.partition('?')[0]}: expected {expected}, got {response.status}"
                )
            return response.read(), response.headers

    def json(self, path: str, method: str = "GET", payload: Any = None, expected: int = 200) -> Any:
        body = None if payload is None else json.dumps(payload).encode()
        data, _ = self.request(
            path, method, body, "application/json" if body is not None else None, expected
        )
        return json.loads(data.decode()) if data else None

    def login(self, login: str, password: str) -> None:
        data, headers = self.request(
            "/api/v1/auth/login",
            "POST",
            json.dumps({"login_name": login, "password": password}).encode(),
            "application/json",
        )
        self.accept_session(data, headers, "login")

    def accept_session(self, data: bytes, headers: HTTPMessage, operation: str) -> None:
        csrf = response_object(data, operation).get("csrf_token")
        if not isinstance(csrf, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", csrf):
            raise RuntimeError(f"{operation}: missing or invalid CSRF token")
        jar: SimpleCookie = SimpleCookie()
        try:
            for value in headers.get_all("Set-Cookie", []):
                jar.load(value)
        except CookieError:
            raise RuntimeError(f"{operation}: invalid session cookie") from None
        morsel = jar.get("__Host-florabase-session")
        if (
            morsel is None
            or not re.fullmatch(r"[A-Za-z0-9_-]+", morsel.value)
            or not morsel["secure"]
            or not morsel["httponly"]
            or morsel["samesite"].lower() != "strict"
            or morsel["path"] != "/"
            or morsel["domain"]
        ):
            raise RuntimeError(f"{operation}: missing or invalid secure session cookie")
        self.cookie = morsel.key + "=" + morsel.value
        self.csrf = csrf

    def upload(self, content: bytes, name: str) -> dict[str, Any]:
        boundary = "florabase-runtime-smoke"
        body = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="title"\r\n\r\n{name}\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}.png"\r\n'
            "Content-Type: image/png\r\n\r\n".encode()
            + content
            + f"\r\n--{boundary}--\r\n".encode()
        )
        data, _ = self.request(
            "/api/v1/media-assets/local",
            "POST",
            body,
            "multipart/form-data; boundary=" + boundary,
            201,
        )
        return response_object(data, "media upload")


def seed(client: Client) -> dict[str, Any]:
    suppliers = [
        client.json("/api/v1/suppliers", "POST", {"name": name, "kind": "nursery"}, 201)["id"]
        for name in ("Runtime smoke nursery A", "Runtime smoke nursery B")
    ]
    unlinked = client.upload(png(200, 30, 30), "unlinked-original")["id"]
    shared = client.upload(png(30, 160, 60), "shared-original")["id"]
    for supplier in suppliers:
        client.json(
            f"/api/v1/collection-records/supplier/{supplier}/media-links",
            "POST",
            {"media_asset_id": shared},
            201,
        )
    external = client.json(
        "/api/v1/media-assets/external",
        "POST",
        {
            "image_url": "https://example.invalid/runtime-smoke.png",
            "source_url": "https://example.invalid/runtime-smoke",
            "attribution": "Runtime smoke",
        },
        201,
    )["id"]
    client.json(
        f"/api/v1/collection-records/supplier/{suppliers[0]}/media-links",
        "POST",
        {"media_asset_id": external},
        201,
    )
    return {"suppliers": suppliers, "unlinked": unlinked, "shared": shared, "external": external}


def snapshot(client: Client) -> dict[str, Any]:
    assets: dict[str, Any] = {}
    offset = 0
    while True:
        page = client.json(f"/api/v1/media-assets?limit=100&offset={offset}")
        for item in page["items"]:
            detail = client.json("/api/v1/media-assets/" + item["id"])
            digest = None
            if detail["content_url"]:
                content, _ = client.request(detail["content_url"])
                digest = hashlib.sha256(content).hexdigest()
            assets[item["id"]] = {
                "kind": detail["kind"],
                "title": detail["title"],
                "byte_size": detail["byte_size"],
                "sha256": digest,
                "links": sorted(
                    (link["target_type"], link["target_id"]) for link in detail["links"]
                ),
            }
        offset += len(page["items"])
        if offset >= page["total"] or not page["items"]:
            break
    return {"assets": assets, "owner": client.json("/api/v1/auth/session")["owner"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("seed", "snapshot"))
    parser.add_argument("--base", required=True)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--login", required=True)
    args = parser.parse_args()
    client = Client(args.base, args.origin)
    client.login(args.login, sys.stdin.readline().rstrip("\n"))
    result = seed(client) if args.action == "seed" else snapshot(client)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
