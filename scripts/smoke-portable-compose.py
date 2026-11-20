#!/usr/bin/env python3
"""Exercise the rendered release asset on two fresh, isolated bind-mounted stacks."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import tempfile
from contextlib import ExitStack, suppress
from http.client import HTTPMessage
from pathlib import Path

from smoke_beta_runtime_client import Client, png, response_object
from workflow_resources import Disposable

ORIGIN = "https://portable.example.invalid"
OWNER = "portable-owner"
SCHEMA = ("python", "-m", "florabase.db.release_schema")
ARTIFACTS = ("python", "/app/scripts/attachment_artifacts.py")
REVISION_SQL = "SELECT version_num FROM alembic_version"
SERVICE_UIDS = {"db": b"70", "backend": b"10001", "frontend": b"101"}
DB_INIT = (
    'entries=$(ls -A /var/lib/postgresql); test -z "$entries" || { echo "PostgreSQL bind directory is not empty" >&2; exit 1; }; '
    "exec docker-ensure-initdb.sh"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run(
    command: list[str], env: dict[str, str] | None = None, data: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    with subprocess.Popen(
        command,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    ) as process:
        try:
            stdout, stderr = process.communicate(data, timeout=180)
        except BaseException:
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


class Stack:
    def __init__(self, root: Path, compose: Path, prefix: str, backend_image: str) -> None:
        self.root = root
        self.backend_image = backend_image
        self.project = f"{prefix}-{root.name}"
        root.mkdir(mode=0o700)
        for directory in ("db", "media"):
            (root / directory).mkdir(mode=0o700)
        self.env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("COMPOSE_", "FLORABASE_"))
        }
        self.env.update(
            FLORABASE_DB_PASSWORD=secrets.token_hex(24) + "@:%",
            FLORABASE_CANONICAL_ORIGIN=ORIGIN,
            FLORABASE_POSTGRES_DIR=str(root / "db"),
            FLORABASE_MEDIA_DIR=str(root / "media"),
            FLORABASE_HTTP_PORT="0",
        )
        self.command = [
            "docker",
            "compose",
            "--env-file",
            "/dev/null",
            "--project-name",
            self.project,
            "--file",
            str(compose),
        ]

    def owner(self, command: str) -> None:
        result = run(
            [
                "docker",
                "run",
                "--rm",
                "--label",
                f"com.docker.compose.project={self.project}",
                "--network",
                "none",
                "--user",
                "0",
                "--entrypoint",
                "sh",
                "--mount",
                f"type=bind,src={self.root},dst=/bind",
                self.backend_image,
                "-ec",
                command,
            ],
        )
        require(result.returncode == 0, f"{self.project}: bind preparation/cleanup failed")

    def compose(
        self,
        *args: str,
        data: bytes | None = None,
        failure: str | None = None,
        check: str | None = None,
        secret: bytes | None = None,
    ) -> bytes:
        result = run([*self.command, *args], env=self.env, data=data)
        operation = f"{self.project}: {check or 'compose ' + args[0]}"
        if secret is not None:
            require(
                secret not in result.stdout and secret not in result.stderr,
                f"{operation}: password in output",
            )
        if failure is not None:
            require(
                0 < result.returncode < 125 and failure.encode() in result.stderr,
                f"{operation}: expected refusal containing {failure!r} (exit {result.returncode})",
            )
        else:
            # Do not echo command arguments or output, which can carry credentials or dump bytes.
            require(result.returncode == 0, f"{operation} failed (exit {result.returncode})")
        return result.stdout

    def backend(
        self,
        *args: str,
        data: bytes | None = None,
        failure: str | None = None,
        check: str | None = None,
        secret: bytes | None = None,
    ) -> bytes:
        return self.compose(
            "run",
            "--rm",
            "--no-deps",
            "-T",
            "backend",
            *args,
            data=data,
            failure=failure,
            check=check,
            secret=secret,
        )

    def sql(self, statement: str) -> bytes:
        return self.compose(
            "exec",
            "-T",
            "db",
            "sh",
            "-ec",
            'export PGPASSWORD="$POSTGRES_PASSWORD"; exec psql -XAt -v ON_ERROR_STOP=1 '
            '-U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "$1"',
            "sh",
            statement,
            check="PostgreSQL query",
        ).strip()

    def init_cluster(self, failure: str | None = None) -> None:
        self.compose("stop", "db")
        self.compose(
            "run",
            "--rm",
            "--no-deps",
            "-T",
            "-e",
            "POSTGRES_INITDB_ARGS=--auth=scram-sha-256",
            "--entrypoint",
            "sh",
            "db",
            "-ec",
            DB_INIT,
            failure=failure,
            check="PostgreSQL cluster initialization",
        )
        if failure is None:
            self.up("db")

    def up(self, *services: str) -> None:
        self.compose("up", "-d", "--wait", "--wait-timeout", "90", *services)

    def client(self) -> Client:
        address = self.compose("port", "frontend", "8080").strip()
        match = re.fullmatch(rb"127\.0\.0\.1:([0-9]{1,5})", address)
        if match is None or not 0 < int(match[1]) <= 65535:
            raise RuntimeError("frontend: missing valid loopback port")
        return Client(f"http://{address.decode()}", ORIGIN)

    def login(self, password: str) -> Client:
        client = self.client()
        ready = response_object(client.request("/api/v1/ready")[0], "readiness")
        require(ready.get("status") == "ok", "readiness: missing or incorrect status")
        client.login(OWNER, password)
        require_owner_session(client)
        return client

    def close(self) -> None:
        self.compose("down", "--remove-orphans")
        self.owner("rm -rf /bind/db /bind/media")
        self.assert_no_resources()

    def assert_no_resources(self) -> None:
        label = f"label=com.docker.compose.project={self.project}"
        for kind, options in (("container", ["--all"]), ("network", []), ("volume", [])):
            result = run(["docker", kind, "ls", "--quiet", "--filter", label, *options])
            if result.returncode or result.stdout:
                raise RuntimeError(f"{self.project}: could not confirm zero {kind} resources")


def require_owner_session(client: Client) -> None:
    session = response_object(client.request("/api/v1/auth/session")[0], "owner session")
    require(
        session.get("owner") is True and session.get("login_name") == OWNER,
        "owner session: incorrect owner",
    )
    require(session.get("canonical_origin") == ORIGIN, "owner session: incorrect canonical origin")


def exercise_credentials(stack: Stack, password: str) -> str:
    first = stack.login(password)
    other = stack.login(password)
    changed_password = secrets.token_hex(24)
    reset_password = secrets.token_hex(24)
    path = "/api/v1/auth/password"
    payload = json.dumps({"current_password": password, "new_password": changed_password})
    data, headers = first.request(path, "POST", payload.encode(), "application/json")
    old_cookie = first.cookie
    old_csrf = first.csrf
    first.accept_session(data, headers, "password change")
    require(
        first.cookie != old_cookie and first.csrf != old_csrf,
        "password change: session credentials did not rotate",
    )
    require_owner_session(first)
    other.request("/api/v1/auth/session", expected=401)

    # A rejected query is still observed by both access loggers.
    query_canary = "auth-query-" + secrets.token_hex(12)
    first.request(path + "?check=" + query_canary, "POST", b"{}", "application/json", 400)
    first.json("/api/v1/auth/login", "POST", {"login_name": OWNER, "password": password}, 401)
    stack.login(changed_password)
    credential_values = (
        query_canary,
        password,
        changed_password,
        old_csrf,
        other.csrf,
        first.csrf,
        *(cookie.partition("=")[2] for cookie in (old_cookie, other.cookie, first.cookie)),
    )
    for service in ("frontend", "backend"):
        logs = stack.compose("logs", "--no-color", service)
        require(
            all(value.encode() not in logs for value in credential_values),
            f"{service}: sensitive value in credential logs",
        )
        require(
            logs.count(path.encode()) >= 2,
            f"{service}: credential access log evidence is incomplete",
        )

    stack.compose("stop", "frontend", "backend")
    result = stack.backend(
        "python",
        "-m",
        "florabase.auth.reset_password",
        OWNER,
        "--password-json-stdin",
        data=json.dumps(reset_password).encode(),
        check="offline password reset",
        secret=reset_password.encode(),
    )
    require(b"reset committed" in result, "offline password reset: missing commit confirmation")
    stack.up()
    restarted = stack.client()
    restarted.cookie = first.cookie
    restarted.request("/api/v1/auth/session", expected=401)
    restarted.json(
        "/api/v1/auth/login", "POST", {"login_name": OWNER, "password": changed_password}, 401
    )
    stack.login(reset_password)
    return reset_password


def require_response_header(
    path: str, headers: HTTPMessage, name: str, expected: str | None
) -> None:
    values = headers.get_all(name, [])
    expected_values = [] if expected is None else [expected]
    if values != expected_values:
        raise RuntimeError(f"GET {path}: expected {name} {expected_values!r}")


def require_bundled_headers(path: str, headers: HTTPMessage) -> None:
    security_headers = {
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "X-Frame-Options": "DENY",
        "Content-Security-Policy": (
            "default-src 'none'; script-src 'self'; style-src 'self'; style-src-attr 'unsafe-inline'; "
            "img-src 'self' data: blob: https:; font-src 'self'; connect-src 'self'; "
            "manifest-src 'self'; worker-src 'self'; object-src 'none'; base-uri 'none'; "
            "form-action 'self'; frame-ancestors 'none'"
        ),
    }
    for name, value in security_headers.items():
        require_response_header(path, headers, name, value)


def exercise_bundled_headers(client: Client) -> None:
    for path, status, cache in (
        ("/", 200, "no-cache"),
        ("/spa-fallback-probe", 200, "no-cache"),
        ("/index.html", 200, "no-cache"),
        ("/appearance.js", 200, "no-cache"),
        ("/runtime-config.js", 200, "no-store"),
        ("/release.json", 200, "no-store"),
        ("/sw.js", 200, "no-cache, no-store, must-revalidate"),
        ("/manifest.webmanifest", 200, "no-cache"),
        ("/offline.html", 200, "no-cache"),
        ("/offline.css", 200, "no-cache"),
        ("/offline.js", 200, "no-cache"),
        ("/icons/florabase-192.png", 200, "public, max-age=86400"),
        ("/favicon.ico", 200, "public, max-age=86400"),
        ("/icons/missing-eng02-icon.png", 404, None),
        ("/healthz", 200, None),
        ("/api/v1/ready", 200, None),
        ("/api/v1/media-assets", 401, None),
        ("/api/v1/missing-eng02-route", 404, None),
        ("/api/v1/auth/session", 401, None),
    ):
        _, headers = client.request(path, expected=status)
        require_bundled_headers(path, headers)
        if not path.startswith("/api/"):
            require_response_header(path, headers, "Cache-Control", cache)


def exercise_authenticated_thumbnail(client: Client, path: str) -> None:
    _, headers = client.request(path)
    require_bundled_headers(path, headers)
    require_response_header(
        path, headers, "Cache-Control", "private, max-age=86400, must-revalidate"
    )


def require_services(stack: Stack, images: dict[str, str]) -> None:
    config = response_object(stack.compose("config", "--format", "json"), "Compose configuration")
    services = config.get("services")
    if not isinstance(services, dict) or services.keys() != SERVICE_UIDS.keys():
        raise RuntimeError("Compose configuration: expected db, backend and frontend services")
    for name in SERVICE_UIDS:
        service = services[name]
        require(
            isinstance(service, dict) and service.get("image") == images[name],
            f"Compose configuration: incorrect {name} image reference",
        )


def require_revision(stack: Stack, revision: bytes, operation: str) -> None:
    require(stack.sql(REVISION_SQL) == revision, f"{operation}: unexpected database revision")


def require_media(stack: Stack, password: str, path: str, original: bytes, operation: str) -> None:
    require(
        stack.login(password).request(path)[0] == original, f"{operation}: original media differs"
    )


def smoke(source: Stack, restore: Stack, images: dict[str, str], head: str) -> None:
    require_services(source, images)
    require_services(restore, images)
    source.compose("run", "--rm", "--no-deps", "-T", "db", failure="Run initdb")
    source.init_cluster()
    source.init_cluster(failure="PostgreSQL bind directory is not empty")
    source.up("db")
    source.backend(failure="differs from image head")
    source.sql("CREATE TABLE unmanaged (id int)")
    source.backend(*SCHEMA, "init", failure="requires an empty")
    source.sql("DROP TABLE unmanaged")
    source.backend(*SCHEMA, "init")
    source.backend(*SCHEMA, "init", failure="requires an empty")
    require(
        source.backend("alembic", "heads").strip() == f"{head} (head)".encode(),
        "backend image: unexpected Alembic head",
    )
    require_revision(source, head.encode(), "schema initialization")
    password = secrets.token_hex(24)
    source.backend(
        "python",
        "-m",
        "florabase.auth.bootstrap",
        OWNER,
        "--password-stdin",
        data=(password + "\n").encode(),
    )
    source.up()
    for service, uid in SERVICE_UIDS.items():
        require(
            source.compose("exec", "-T", service, "id", "-u").strip() == uid,
            f"{service}: unexpected runtime UID",
        )
    exercise_bundled_headers(source.client())
    password = exercise_credentials(source, password)
    original = png(19, 37, 59)
    client = source.login(password)
    asset = client.upload(original, "portable-smoke")
    thumbnail = asset.get("thumbnail_url")
    path = asset.get("content_url")
    if not isinstance(thumbnail, str) or not re.fullmatch(
        r"/api/v1/media-assets/[0-9a-f-]{36}/thumbnail", thumbnail
    ):
        raise RuntimeError("media upload: missing or invalid thumbnail URL")
    if not isinstance(path, str) or not re.fullmatch(
        r"/api/v1/attachments/[0-9a-f-]{36}/content", path
    ):
        raise RuntimeError("media upload: missing or invalid content URL")
    exercise_authenticated_thumbnail(client, thumbnail)

    # Real service restarts preserve both state roots and never run Alembic.
    source.compose("restart")
    source.up()
    require_media(source, password, path, original, "service restart")
    require_revision(source, head.encode(), "service restart")

    source.compose("stop", "frontend", "backend")
    source.sql("UPDATE alembic_version SET version_num = 'foreign_revision'")
    source.backend(failure="foreign_revision")
    source.backend(*SCHEMA, "upgrade", "foreign_revision", failure="migration history")
    require_revision(source, b"foreign_revision", "foreign revision refusal")
    source.sql(f"UPDATE alembic_version SET version_num = '{head}'")
    dump = source.compose(
        "exec",
        "-T",
        "db",
        "sh",
        "-ec",
        'export PGPASSWORD="$POSTGRES_PASSWORD"; '
        'exec pg_dump -Fc --no-owner --no-privileges -U "$POSTGRES_USER" "$POSTGRES_DB"',
        check="database backup",
    )
    require(dump.startswith(b"PGDMP"), "database backup: missing PostgreSQL custom-format dump")
    verified = b"Verified 1 stored attachment file(s) against database metadata"
    require(
        source.backend(*ARTIFACTS, "verify").strip() == verified,
        "media backup: expected one verified attachment",
    )
    media = source.backend(*ARTIFACTS, "archive")
    require(bool(media), "media backup: missing attachment archive")

    # Deliberately create a conflicting relation at the parent of the last migration.
    # Only this disposable fixture is downgraded to construct that historical schema.
    source.backend("alembic", "downgrade", "20261009_0041")
    source.sql("CREATE TABLE application_settings (sentinel int)")
    source.backend(failure="differs from image head")
    source.backend(*SCHEMA, "upgrade", "20261009_0041", failure="SQLSTATE 42P07")
    require_revision(source, b"20261009_0041", "failed upgrade rollback")
    require(
        source.sql("SELECT count(sentinel) FROM application_settings") == b"0",
        "failed upgrade rollback: sentinel table changed",
    )
    source.backend(failure="differs from image head")
    source.sql("DROP TABLE application_settings")
    source.backend(*SCHEMA, "upgrade", "20261009_0041")
    source.up()
    require_revision(source, head.encode(), "upgrade recovery")
    require_media(source, password, path, original, "upgrade recovery")

    restore.init_cluster()
    restore.backend(failure="differs from image head")
    restore.compose(
        "exec",
        "-T",
        "db",
        "sh",
        "-ec",
        'export PGPASSWORD="$POSTGRES_PASSWORD"; '
        "exec pg_restore --single-transaction --exit-on-error --no-owner --no-privileges "
        '-U "$POSTGRES_USER" -d "$POSTGRES_DB"',
        data=dump,
        check="database restore",
    )
    restored = restore.backend(
        "sh",
        "-ec",
        'entries=$(ls -A "$FLORABASE_ATTACHMENT_STORAGE_ROOT"); test -z "$entries"; '
        "exec python /app/scripts/attachment_artifacts.py restore",
        data=media,
        check="media restore",
    )
    require(
        restored.strip() == b"Restored 1 attachment file(s)",
        "media restore: expected one restored attachment",
    )
    require(
        restore.backend(*ARTIFACTS, "verify").strip() == verified,
        "media restore: expected one verified attachment",
    )
    restore.up()
    require_revision(restore, head.encode(), "isolated restore")
    require_media(restore, password, path, original, "isolated restore")
    require_media(source, password, path, original, "source after isolated restore")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("compose", type=Path)
    parser.add_argument("backend_image")
    parser.add_argument("--frontend-image", required=True)
    parser.add_argument("--postgres-image", required=True)
    parser.add_argument("--alembic-head", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_]+", args.alembic_head):
        parser.error("invalid Alembic head")
    images = {
        "backend": args.backend_image,
        "frontend": args.frontend_image,
        "db": args.postgres_image,
    }
    if any(not reference or reference.startswith("-") for reference in images.values()):
        parser.error("invalid expected image reference")
    compose = args.compose.resolve()
    prefix = "florabase-portable-" + secrets.token_hex(6)
    root = Path(tempfile.mkdtemp(prefix=prefix + "-"))
    signal.signal(signal.SIGTERM, Disposable.interrupt)
    signal.signal(signal.SIGINT, Disposable.interrupt)
    with ExitStack() as cleanup:
        cleanup.callback(shutil.rmtree, root)
        stacks = []
        for name in ("source", "restore"):
            stack = Stack(root / name, compose, prefix, args.backend_image)
            stack.assert_no_resources()
            cleanup.callback(stack.close)
            print(f"Disposable project {stack.project}, binds under {stack.root}", flush=True)
            stack.owner("chown 70:70 /bind/db && chown 10001:10001 /bind/media")
            stacks.append(stack)
        smoke(stacks[0], stacks[1], images, args.alembic_head)
    print(
        "Portable Compose smoke passed (fresh install, restart, refusal, failed upgrade, restore)"
    )


if __name__ == "__main__":
    main()
