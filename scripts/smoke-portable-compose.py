#!/usr/bin/env python3
"""Exercise the rendered self-initializing compose.yaml on fresh, isolated bind-mounted stacks."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
from contextlib import ExitStack, suppress
from http.client import HTTPMessage
from pathlib import Path

from smoke_beta_runtime_client import Client, png, response_object
from workflow_resources import Disposable

ORIGIN = "https://portable.example.invalid"
OWNER = "portable-owner"
ARTIFACTS = ("python", "/app/scripts/attachment_artifacts.py")
REVISION_SQL = "SELECT version_num FROM alembic_version"
SERVICES = ("prepare", "db", "migrate", "backend", "frontend")
SERVICE_UIDS = {"db": b"70", "backend": b"10001", "frontend": b"101"}
MARKER = "/bind/data/state/installation.env"
SMOKE_REVISION = "29991231_9999"
SMOKE_MIGRATION = '''"""Smoke-only upgrade step; it fails while the sentinel table exists."""

from alembic import op

revision = "{revision}"
down_revision = "{head}"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TABLE smoke_upgrade (id integer)")


def downgrade() -> None:
    op.execute("DROP TABLE smoke_upgrade")
'''


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
            stdout, stderr = process.communicate(data, timeout=300)
        except BaseException:
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


class Stack:
    def __init__(self, root: Path, compose: Path, prefix: str, helper_image: str) -> None:
        self.root = root
        self.compose_file = compose
        self.helper_image = helper_image
        self.project = f"{prefix}-{root.name}"
        root.mkdir(mode=0o700)
        # Operator-created folders: owned by the invoking user and not traversable by others.
        for directory in ("data", "backup"):
            (root / directory).mkdir(mode=0o700)
        self.env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("COMPOSE_", "FLORABASE_"))
        }
        self.env.update(
            FLORABASE_DB_PASSWORD=secrets.token_hex(24) + "@:%",
            FLORABASE_CANONICAL_ORIGIN=ORIGIN,
            FLORABASE_DATA_DIR=str(root / "data"),
            FLORABASE_BACKUP_DIR=str(root / "backup"),
            FLORABASE_HTTP_PORT="0",
        )

    def command(self) -> list[str]:
        return [
            "docker",
            "compose",
            "--env-file",
            "/dev/null",
            "--project-name",
            self.project,
            "--file",
            str(self.compose_file),
        ]

    def owner(self, command: str) -> None:
        """Run a root shell over the stack's folders, standing in for the operator's host."""
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
                self.helper_image,
                "-ec",
                command,
            ],
        )
        require(result.returncode == 0, f"{self.project}: host folder operation failed")

    def compose(
        self,
        *args: str,
        data: bytes | None = None,
        failure: str | None = None,
        check: str | None = None,
        secret: bytes | None = None,
    ) -> bytes:
        result = run([*self.command(), *args], env=self.env, data=data)
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

    def deploy(self) -> None:
        """The whole operator procedure: one docker compose up -d."""
        self.compose("up", "-d", "--wait", "--wait-timeout", "180", check="docker compose up -d")

    def refuse(self, service: str, message: str, operation: str) -> None:
        result = run([*self.command(), "up", "-d", "--wait", "--wait-timeout", "180"], env=self.env)
        require(result.returncode != 0, f"{self.project}: {operation} was not refused")
        logs = self.compose("logs", "--no-color", service)
        if message.encode() not in logs:
            # Service logs carry guard lines only; up output and states name the failing stage.
            state = self.compose("ps", "--all", "--format", "{{.Service}} {{.State}} {{.Status}}")
            sys.stderr.buffer.write((result.stderr or b"")[-4000:] + state + logs[-4000:])
        require(message.encode() in logs, f"{self.project}: {operation}: expected {message!r}")
        self.compose("stop")

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

    def dumps(self) -> list[str]:
        listing = run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--user",
                "0",
                "--entrypoint",
                "ls",
                "--mount",
                f"type=bind,src={self.root},dst=/bind,readonly",
                self.helper_image,
                "-A",
                "/bind/backup/pre-upgrade",
            ]
        )
        require(listing.returncode == 0, f"{self.project}: could not list pre-upgrade backups")
        return sorted(listing.stdout.decode().split())

    def close(self) -> None:
        self.compose("down", "--remove-orphans")
        self.owner("rm -rf /bind/data /bind/backup")
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


def require_no_secret(stack: Stack, values: tuple[str, ...], operation: str) -> None:
    logs = stack.compose("logs", "--no-color", *SERVICES)
    require(all(value.encode() not in logs for value in values), f"{operation}: secret in logs")


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
    stack.deploy()
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
    if not isinstance(services, dict) or set(services) != set(SERVICES):
        raise RuntimeError(
            "Compose configuration: expected prepare, db, migrate, backend, frontend"
        )
    for name in SERVICES:
        service = services[name]
        require(
            isinstance(service, dict) and service.get("image") == images[name],
            f"Compose configuration: incorrect {name} image reference",
        )
    for name in ("db", "backend"):
        command = " ".join(services[name].get("command") or [])
        require("alembic" not in command and "deploy" not in command, f"{name} migrates")


def require_revision(stack: Stack, revision: bytes, operation: str) -> None:
    require(stack.sql(REVISION_SQL) == revision, f"{operation}: unexpected database revision")


def require_media(stack: Stack, password: str, path: str, original: bytes, operation: str) -> None:
    require(
        stack.login(password).request(path)[0] == original, f"{operation}: original media differs"
    )


def build_upgrade_image(backend_image: str, head: str, tag: str, work: Path) -> None:
    """A test-only image one migration ahead that declares this release head as its previous."""
    work.mkdir()
    (work / f"{SMOKE_REVISION}_smoke_upgrade.py").write_text(
        SMOKE_MIGRATION.format(revision=SMOKE_REVISION, head=head)
    )
    (work / "release-upgrade-from.json").write_text(json.dumps({"alembic_head": head}) + "\n")
    (work / "Dockerfile").write_text(
        f"FROM {backend_image}\n"
        # The release pipeline runs under umask 077; the image user must still read both files.
        f"COPY --chmod=0644 {SMOKE_REVISION}_smoke_upgrade.py /app/alembic/versions/\n"
        "COPY --chmod=0644 release-upgrade-from.json /app/alembic/release-upgrade-from.json\n"
    )
    result = run(["docker", "build", "--quiet", "--pull=false", "--tag", tag, str(work)])
    require(result.returncode == 0, "smoke upgrade image build failed")


def refusals_before_any_data(probe: Stack) -> None:
    """Data-directory guards on a folder that never holds real data."""
    absent = probe.env["FLORABASE_DATA_DIR"]
    probe.env["FLORABASE_DATA_DIR"] = str(probe.root / "absent")
    probe.compose("up", "-d", failure="does not exist", check="missing data folder")
    probe.compose("down", "--remove-orphans")
    probe.env["FLORABASE_DATA_DIR"] = absent

    probe.owner("echo stray > /bind/data/stray")
    probe.refuse("prepare", "no installation marker", "non-empty folder without marker")
    probe.owner("rm /bind/data/stray")

    marker = (
        "FLORABASE_INSTALLATION_ID=ab12\\nFLORABASE_PG_MAJOR={major}\\nFLORABASE_PG_SYSTEM_ID=1\\n"
    )
    probe.owner(f"mkdir -p /bind/data/state && printf '{marker.format(major=18)}' > {MARKER}")
    probe.refuse("prepare", "database folder is missing or empty", "marker without database")
    probe.owner(f"printf '{marker.format(major=17)}' > {MARKER}")
    probe.refuse("prepare", "uses PostgreSQL 17", "marker with another PostgreSQL major")
    probe.owner("rm -rf /bind/data/state")

    probe.env["FLORABASE_BACKUP_DIR"] = probe.env["FLORABASE_DATA_DIR"] + "/backup"
    probe.owner("mkdir /bind/data/backup")
    probe.refuse("prepare", "is inside FLORABASE_DATA_DIR", "backup folder inside data folder")
    probe.compose("down", "--remove-orphans")
    probe.owner("rm -rf /bind/data/backup")
    # A trailing slash must not hide the data folder inside the backup folder.
    probe.env["FLORABASE_BACKUP_DIR"] = str(probe.root) + "/"
    probe.refuse("prepare", "is inside FLORABASE_BACKUP_DIR", "data folder inside backup folder")
    probe.compose("down", "--remove-orphans")
    probe.env["FLORABASE_BACKUP_DIR"] = str(probe.root / "backup")


def smoke(
    source: Stack, restore: Stack, images: dict[str, str], head: str, upgrade_compose: Path
) -> None:
    require_services(source, images)
    refusals_before_any_data(restore)

    # A failed first deployment is retried without emptying the folder.
    password = secrets.token_hex(24)
    source.env["FLORABASE_OWNER_LOGIN"] = OWNER
    source.refuse("migrate", "or neither", "owner login without password")
    weak = "w" + secrets.token_hex(4)
    source.env["FLORABASE_OWNER_PASSWORD"] = weak
    source.refuse("migrate", "first owner refused", "owner password below policy")
    require_no_secret(source, (weak,), "refused owner password")
    source.env["FLORABASE_OWNER_PASSWORD"] = password
    source.deploy()
    require_revision(source, head.encode(), "first installation")
    require_no_secret(source, (password,), "first installation")
    for service, uid in SERVICE_UIDS.items():
        require(
            source.compose("exec", "-T", service, "id", "-u").strip() == uid,
            f"{service}: unexpected runtime UID",
        )
    exercise_bundled_headers(source.client())
    source.login(password)

    # Redeploying the same file changes nothing and never creates a second owner.
    source.deploy()
    logs = source.compose("logs", "--no-color", "migrate")
    require(b"users already exist" in logs, "redeploy: owner variables were not ignored")
    require(source.dumps() == [], "redeploy at head wrote a backup")
    del source.env["FLORABASE_OWNER_LOGIN"], source.env["FLORABASE_OWNER_PASSWORD"]

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
    source.compose("restart")
    source.deploy()
    require_media(source, password, path, original, "service restart")

    # The cluster found must be the one the marker recorded.
    source.compose("stop")
    source.owner(f"cp {MARKER} /bind/marker && sed -i 's/_SYSTEM_ID=.*/_SYSTEM_ID=1/' {MARKER}")
    source.refuse("prepare", "another PostgreSQL cluster", "marker of another cluster")
    source.owner(f"mv /bind/marker {MARKER}")

    # The backend process never migrates; migrate refuses an unknown revision.
    source.deploy()
    source.compose("stop", "frontend", "backend")
    source.sql("UPDATE alembic_version SET version_num = 'foreign_revision'")
    source.backend(failure="differs from image head", check="backend schema guard")
    source.refuse("migrate", "neither image head", "unknown database revision")
    source.compose("start", "db")
    source.sql(f"UPDATE alembic_version SET version_num = '{head}'")
    source.deploy()

    verified = b"Verified 1 stored attachment file(s) against database metadata"
    require(
        source.backend(*ARTIFACTS, "verify").strip() == verified,
        "media backup: expected one verified attachment",
    )
    media = source.backend(*ARTIFACTS, "archive")
    require(bool(media), "media backup: missing attachment archive")

    # Upgrades to an image one migration ahead.
    current = source.compose_file
    source.compose_file = upgrade_compose
    # A missing backup folder stops the deployment before migrate can run.
    backup = source.env["FLORABASE_BACKUP_DIR"]
    source.env["FLORABASE_BACKUP_DIR"] = str(source.root / "absent-backup")
    source.compose("up", "-d", failure="does not exist", check="missing backup folder")
    source.env["FLORABASE_BACKUP_DIR"] = backup
    source.compose("start", "db")
    require_revision(source, head.encode(), "refused upgrade")
    source.sql("CREATE TABLE smoke_upgrade (sentinel int)")
    source.refuse("migrate", "SQLSTATE 42P07", "failed upgrade")
    failed = source.dumps()
    require(len(failed) == 1 and failed[0].startswith(f"florabase-{head}-to-"), "failed: no dump")
    source.compose("start", "db")
    require_revision(source, head.encode(), "failed upgrade rollback")
    source.backend(failure="differs from image head", check="backend after failed upgrade")
    source.sql("DROP TABLE smoke_upgrade")
    source.deploy()
    require_revision(source, SMOKE_REVISION.encode(), "upgrade")
    require(len(source.dumps()) == 2, "upgrade: expected a second verified dump")
    require_media(source, password, path, original, "upgrade")

    # An older image refuses the newer database, and nothing starts.
    source.compose_file = current
    source.refuse("migrate", "neither image head", "newer database revision")

    # Isolated restore of the failed attempt's dump and the media archive into a new folder.
    restore.deploy()
    restore.compose("stop", "frontend", "backend")
    dump = run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--user",
            "0",
            "--entrypoint",
            "cat",
            "--mount",
            f"type=bind,src={source.root},dst=/bind,readonly",
            source.helper_image,
            f"/bind/backup/pre-upgrade/{failed[0]}",
        ]
    ).stdout
    require(dump.startswith(b"PGDMP"), "pre-upgrade backup: missing PostgreSQL custom-format dump")
    restore.compose(
        "exec",
        "-T",
        "db",
        "sh",
        "-ec",
        'export PGPASSWORD="$POSTGRES_PASSWORD"; '
        'psql -XAq -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" '
        '-c "DROP SCHEMA public CASCADE" -c "CREATE SCHEMA public"; '
        "exec pg_restore --single-transaction --exit-on-error --no-owner --no-privileges "
        '-U "$POSTGRES_USER" -d "$POSTGRES_DB"',
        data=dump,
        check="database restore",
    )
    restored = restore.backend(*ARTIFACTS, "restore", data=media, check="media restore")
    require(
        restored.strip() == b"Restored 1 attachment file(s)",
        "media restore: expected one restored attachment",
    )
    require(
        restore.backend(*ARTIFACTS, "verify").strip() == verified,
        "media restore: expected one verified attachment",
    )
    restore.deploy()
    require_revision(restore, head.encode(), "isolated restore")
    require_media(restore, password, path, original, "isolated restore")


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
        "prepare": args.postgres_image,
        "db": args.postgres_image,
        "migrate": args.backend_image,
        "backend": args.backend_image,
        "frontend": args.frontend_image,
    }
    if any(not reference or reference.startswith("-") for reference in images.values()):
        parser.error("invalid expected image reference")
    compose = args.compose.resolve()
    text = compose.read_text()
    require(text.count(args.backend_image) == 2, "compose.yaml: expected two backend references")
    prefix = "florabase-portable-" + secrets.token_hex(6)
    root = Path(tempfile.mkdtemp(prefix=prefix + "-"))
    upgrade_tag = f"{prefix}-upgrade:smoke"
    signal.signal(signal.SIGTERM, Disposable.interrupt)
    signal.signal(signal.SIGINT, Disposable.interrupt)
    with ExitStack() as cleanup:
        cleanup.callback(shutil.rmtree, root)
        cleanup.callback(run, ["docker", "image", "rm", "--force", upgrade_tag])
        build_upgrade_image(args.backend_image, args.alembic_head, upgrade_tag, root / "image")
        upgrade_compose = root / "upgrade-compose.yaml"
        upgrade_compose.write_text(text.replace(args.backend_image, upgrade_tag))
        stacks = []
        for name in ("source", "restore"):
            stack = Stack(root / name, compose, prefix, args.backend_image)
            stack.assert_no_resources()
            cleanup.callback(stack.close)
            print(f"Disposable project {stack.project}, folders under {stack.root}", flush=True)
            stacks.append(stack)
        smoke(stacks[0], stacks[1], images, args.alembic_head, upgrade_compose)
    print(
        "compose.yaml smoke passed (self-initializing install, retry, guards, owner, redeploy, "
        "backup and upgrade, failed upgrade, newer refusal, isolated restore)"
    )


if __name__ == "__main__":
    main()
