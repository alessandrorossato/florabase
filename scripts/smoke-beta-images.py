#!/usr/bin/env python3
"""Run image-only acceptance using disposable owned state and no source mounts."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any

from beta_release import (
    POSTGRES_ENTRYPOINT,
    read,
    registry_record,
    run,
    validate_manifest,
)
from workflow_resources import Disposable, Owner

ORIGIN = "https://beta-image.invalid"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGOQSFAAAAEsAJmSJ0w1AAAAAElFTkSuQmCC"
)


def check_postgres_image(reference: str, pg: dict[str, Any]) -> None:
    """Derived PostgreSQL: pinned base label, non-root only, gosu absent, root refused early."""
    image = json.loads(run("docker", "image", "inspect", reference))[0]
    config = image["Config"]
    labels = config.get("Labels") or {}
    if (
        config.get("User") != "70:70"
        or config.get("Entrypoint") != [POSTGRES_ENTRYPOINT]
        or labels.get("org.opencontainers.image.base.digest") != pg["upstream"]["index_digest"]
        or labels.get("org.opencontainers.image.version") != pg["version"]
    ):
        raise ValueError("PostgreSQL image identity, user or entrypoint mismatch")
    probe = ["docker", "run", "--rm", "--network", "none"]
    files = run(
        *probe,
        "--entrypoint",
        "sh",
        reference,
        "-c",
        "test ! -e /usr/local/bin/gosu && ! command -v gosu && id -u && postgres --version",
    )
    if files.split()[0] != "70" or "PostgreSQL) 18.6" not in files:
        raise ValueError("PostgreSQL image must run as 70 without gosu: " + files)
    # Every entry point, including overridden ones, refuses root before touching the disk.
    for entrypoint in (
        [],
        ["--entrypoint", "docker-entrypoint.sh"],
        ["--entrypoint", "docker-ensure-initdb.sh"],
    ):
        refused = subprocess.run(
            [*probe, "--user", "0", *entrypoint, reference, "postgres"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if refused.returncode != 64 or "refusing to run as root" not in refused.stderr:
            raise ValueError("PostgreSQL image did not refuse root: " + " ".join(entrypoint))


def smoke(
    manifest: dict[str, Any],
    local: bool = False,
    postgres_image: str | None = None,
    registry_host: str = "ghcr.io",
) -> None:
    validate_manifest(manifest, local, registry_host)
    if local and not postgres_image:
        raise ValueError("a locally built PostgreSQL image is required for --local")
    native = run("docker", "version", "--format", "{{.Server.Os}}/{{.Server.Arch}}")
    if native != "linux/amd64":
        raise ValueError("native linux/amd64 Docker required; emulation is not acceptance")
    images = {name: image["reference"] for name, image in manifest["images"].items()}
    images["db"] = postgres_image or manifest["postgresql"]["reference"]
    for service, reference in images.items():
        if not local:
            subprocess.run(["docker", "pull", "--platform", native, reference], check=True)
        image = json.loads(run("docker", "image", "inspect", reference))[0]
        if f"{image['Os']}/{image['Architecture']}" != native:
            raise ValueError("image platform mismatch")
        if service == "db":
            pg = manifest["postgresql"]
            if not local:
                # The pulled index must be exactly the pinned, reproducible identity.
                pg_reference = postgres_image or f"{pg['repository']}@{pg['index_digest']}"
                record = registry_record(pg_reference, native, registry_host)
                if (record["index_digest"], record["platform_digest"]) != (
                    pg["index_digest"],
                    pg["platform_digest"],
                ):
                    raise ValueError("PostgreSQL index/platform identity mismatch")
            check_postgres_image(reference, pg)
            continue
        if (
            not local
            and registry_record(reference, native, registry_host) != manifest["images"][service]
        ):
            raise ValueError("application platform/index identity mismatch")
        labels = image["Config"]["Labels"]
        for key, expected in {
            "version": manifest["version"],
            "revision": manifest["source"]["revision"],
            "source": manifest["source"]["url"],
            "licenses": "AGPL-3.0-or-later",
        }.items():
            if labels.get("org.opencontainers.image." + key) != expected:
                raise ValueError(f"{service} OCI identity mismatch: {key}")
        if not image["Config"].get("Healthcheck") or image["Config"].get("User", "").split(":")[
            0
        ] in {"", "root", "0"}:
            raise ValueError("image must declare a non-root user and healthcheck")
    # Source is a temporary artifact directory, never a mounted application checkout.
    with tempfile.TemporaryDirectory(prefix="florabase-image-smoke-") as temporary:
        root = Path(temporary)
        owner = Owner.disposable("workflow-smoke", root)
        labels = owner.labels()
        password = secrets.token_urlsafe(32)
        db_password = secrets.token_hex(24)
        backend_env = {
            "FLORABASE_ENVIRONMENT": "production",
            "FLORABASE_DATABASE_URL": f"postgresql+psycopg://image_smoke:{db_password}@db:5432/image_smoke",
            "FLORABASE_CANONICAL_ORIGIN": ORIGIN,
            "FLORABASE_COOKIE_MODE": "secure",
            "FLORABASE_CORS_ORIGINS": "[]",
            "FLORABASE_ATTACHMENT_STORAGE_ROOT": "/var/lib/florabase/attachments",
        }
        services: dict[str, Any] = {
            "db": {
                "image": images["db"],
                "environment": {
                    "POSTGRES_DB": "image_smoke",
                    "POSTGRES_USER": "image_smoke",
                    "POSTGRES_PASSWORD": db_password,
                },
                "tmpfs": ["/var/lib/postgresql:rw"],
                "healthcheck": {
                    "test": ["CMD-SHELL", "pg_isready -U image_smoke -d image_smoke"],
                    "interval": "1s",
                    "timeout": "3s",
                    "retries": 60,
                },
            },
            "backend": {
                "image": images["backend"],
                "environment": backend_env,
                "volumes": ["media:/var/lib/florabase/attachments"],
                "init": True,
                "read_only": True,
                "cap_drop": ["ALL"],
                "security_opt": ["no-new-privileges:true"],
                "tmpfs": ["/tmp:rw,noexec,nosuid,size=64m"],
            },
            "frontend": {
                "image": images["frontend"],
                "ports": ["127.0.0.1::8080"],
                "init": True,
                "read_only": True,
                "cap_drop": ["ALL"],
                "security_opt": ["no-new-privileges:true"],
                "tmpfs": ["/tmp:rw,noexec,nosuid,size=64m"],
            },
        }
        for service in services.values():
            service.update(labels=labels, platform=native, networks=["isolated"])
        config = {
            "services": services,
            "volumes": {"media": {"labels": labels}},
            "networks": {"isolated": {"labels": labels}},
        }
        path = root / "compose.json"
        path.write_text(json.dumps(config))
        path.chmod(0o600)
        command = [
            "docker",
            "compose",
            "--env-file",
            "/dev/null",
            "--project-name",
            owner.project,
            "--project-directory",
            str(root),
            "--file",
            str(path),
        ]
        env = {k: v for k, v in os.environ.items() if not k.startswith("COMPOSE_")}

        def compose(*args: str, stdin: str | None = None) -> str:
            return lifetime.run([*command, *args], stdin=stdin, env=env)

        with Disposable(owner) as lifetime:
            compose("up", "--detach", "--wait", "--wait-timeout", "120", "db")
            code_head = compose("run", "--rm", "--no-deps", "-T", "backend", "alembic", "heads")
            if code_head != manifest["alembic_head"] + " (head)":
                raise ValueError("manifest and image migration heads differ")
            empty = compose("run", "--rm", "--no-deps", "-T", "backend", "alembic", "current")
            if empty:
                raise ValueError("disposable database must start empty")
            compose("run", "--rm", "--no-deps", "-T", "backend", "alembic", "upgrade", "head")
            current = compose("run", "--rm", "--no-deps", "-T", "backend", "alembic", "current")
            if current != code_head:
                raise ValueError("database revision is not release head")
            runtime_check = (
                "import importlib.util; import florabase; from importlib.metadata import version; assert florabase.__version__ == "
                + repr(manifest["version"])
                + "; assert all(importlib.util.find_spec(p) is None for p in ('pytest', 'ruff', 'mypy', 'pip'))"
            )
            compose("run", "--rm", "--no-deps", "-T", "backend", "python", "-c", runtime_check)
            # Repeat an explicit upgrade: already-current databases must remain compatible.
            compose("run", "--rm", "--no-deps", "-T", "backend", "alembic", "upgrade", "head")
            compose("up", "--detach", "--wait", "--wait-timeout", "120", "backend", "frontend")
            port = compose("port", "frontend", "8080").rsplit(":", 1)[1]
            base = "http://127.0.0.1:" + port
            cookie = ""

            def request(
                path: str,
                method: str = "GET",
                body: bytes | None = None,
                headers: dict[str, str] | None = None,
                expected: int = 200,
                authenticated: bool = True,
            ) -> tuple[bytes, Any]:
                final_headers = dict(headers or {})
                if cookie and authenticated:
                    final_headers["Cookie"] = cookie
                req = urllib.request.Request(
                    base + path, data=body, headers=final_headers, method=method
                )
                try:
                    response = urllib.request.urlopen(req, timeout=15)
                except urllib.error.HTTPError as error:
                    response = error
                with response:
                    data = response.read()
                    if response.status != expected:
                        raise AssertionError(
                            f"{method} {path}: expected {expected}, got {response.status}"
                        )
                    return data, response.headers

            def login(expected: int = 200) -> tuple[bytes, Any]:
                return request(
                    "/api/v1/auth/login",
                    "POST",
                    json.dumps({"login_name": "image-owner", "password": password}).encode(),
                    {"Origin": ORIGIN, "Content-Type": "application/json"},
                    expected,
                )

            request("/")
            request("/LICENSE")
            request("/THIRD_PARTY_NOTICES.txt")
            request("/healthz")
            request("/api/v1/health")
            request("/api/v1/ready")
            request("/api/v1/auth/session", expected=401)
            login(401)  # No owner is baked into the images.
            compose(
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "backend",
                "python",
                "-m",
                "florabase.auth.bootstrap",
                "image-owner",
                "--password-stdin",
                stdin=password + "\n",
            )
            body, headers = login()
            jar = SimpleCookie()
            jar.load(headers["Set-Cookie"])
            morsel = jar["__Host-florabase-session"]
            if (
                not morsel["secure"]
                or not morsel["httponly"]
                or morsel["samesite"].lower() != "strict"
                or morsel["path"] != "/"
            ):
                raise AssertionError("production cookie contract")
            # Explicit replay over isolated HTTP tests server policy; real HTTPS is runtime UAT.
            cookie = morsel.key + "=" + morsel.value
            csrf = json.loads(body)["csrf_token"]
            session = json.loads(request("/api/v1/auth/session")[0])
            if session["owner"] is not True or session["canonical_origin"] != ORIGIN:
                raise AssertionError("owner session readiness")
            request("/api/v1/auth/logout", "POST", b"", {"Origin": ORIGIN}, expected=403)
            request(
                "/api/v1/auth/logout",
                "POST",
                b"",
                {"Origin": "https://foreign.invalid", "X-CSRF-Token": csrf},
                expected=403,
            )
            metadata = json.loads(request("/release.json")[0])
            if metadata != {
                "version": manifest["version"],
                "revision": manifest["source"]["revision"],
                "source": manifest["source"]["url"],
            }:
                raise AssertionError("frontend release surface")
            boundary = "florabase-image-smoke"
            upload = (
                f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="smoke.png"\r\nContent-Type: image/png\r\n\r\n'.encode()
                + PNG
                + f"\r\n--{boundary}--\r\n".encode()
            )
            asset = json.loads(
                request(
                    "/api/v1/media-assets/local",
                    "POST",
                    upload,
                    {
                        "Origin": ORIGIN,
                        "X-CSRF-Token": csrf,
                        "Content-Type": "multipart/form-data; boundary=" + boundary,
                    },
                    201,
                )[0]
            )
            content_url = asset["content_url"]
            binary = request(content_url)[0]
            if hashlib.sha256(binary).digest() != hashlib.sha256(PNG).digest():
                raise AssertionError("original media digest")
            request(content_url, expected=401, authenticated=False)
            for service in ("backend", "frontend"):
                cid = compose("ps", "-q", service)
                details = json.loads(run("docker", "inspect", cid))[0]
                if any(m["Type"] == "bind" for m in details["Mounts"]):
                    raise AssertionError("source/host bind in image-only runtime")
                uid = compose("exec", "-T", service, "id", "-u")
                privileged = compose(
                    "exec",
                    "-T",
                    service,
                    "sh",
                    "-c",
                    "find /usr /bin /sbin -xdev -type f -perm /6000 -print",
                )
                if privileged:
                    raise AssertionError("unnecessary setuid/setgid files in application runtime")
                if uid == "0":
                    raise AssertionError("root runtime")
            compose(
                "up",
                "--detach",
                "--force-recreate",
                "--wait",
                "--wait-timeout",
                "120",
                "backend",
                "frontend",
            )
            port = compose("port", "frontend", "8080").rsplit(":", 1)[1]
            base = "http://127.0.0.1:" + port
            request("/api/v1/auth/session")
            if request(content_url)[0] != PNG:
                raise AssertionError("media lost after image recreation")
            request("/api/v1/auth/logout", "POST", b"", {"Origin": ORIGIN, "X-CSRF-Token": csrf})
            request("/api/v1/auth/session", expected=401)
            compose("stop", "db")
            time.sleep(
                1.5
            )  # outlast the backend's one-second cache of a successful readiness probe
            request("/api/v1/ready", expected=503)
            print("BETA_IMAGE_SMOKE_PASSED distribution=" + manifest["distribution"], flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument(
        "--local", action="store_true", help="local candidate only; never registry-pull evidence"
    )
    parser.add_argument("--postgres-image", help="Override the manifest PostgreSQL reference")
    parser.add_argument("--registry-host", default="ghcr.io")
    args = parser.parse_args()
    smoke(read(args.manifest), args.local, args.postgres_image, args.registry_host)


if __name__ == "__main__":
    main()
