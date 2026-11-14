#!/usr/bin/env python3
"""Exercise the rendered release asset on two fresh, isolated bind-mounted stacks."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import signal
import subprocess
import tempfile
from contextlib import ExitStack, suppress
from http.cookies import SimpleCookie
from pathlib import Path

from smoke_beta_runtime_client import Client, png
from workflow_resources import Disposable

ORIGIN = "https://portable.example.invalid"
OWNER = "portable-owner"
SCHEMA = ("python", "-m", "florabase.db.release_schema")
ARTIFACTS = ("python", "/app/scripts/attachment_artifacts.py")
DB_INIT = (
    'entries=$(ls -A /var/lib/postgresql); test -z "$entries" || { echo "PostgreSQL bind directory is not empty" >&2; exit 1; }; '
    "exec docker-ensure-initdb.sh"
)


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
        if result.returncode:
            raise RuntimeError(result.stderr.decode())

    def compose(self, *args: str, data: bytes | None = None, failure: str | None = None) -> bytes:
        result = run([*self.command, *args], env=self.env, data=data)
        if failure is not None:
            if result.returncode == 0 or failure.encode() not in result.stderr:
                raise AssertionError(f"expected {failure!r}: {result.stderr.decode()}")
        elif result.returncode:
            raise RuntimeError(f"{args}: {result.stderr.decode()}")
        return result.stdout

    def backend(self, *args: str, data: bytes | None = None, failure: str | None = None) -> bytes:
        return self.compose(
            "run",
            "--rm",
            "--no-deps",
            "-T",
            "backend",
            *args,
            data=data,
            failure=failure,
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
        )
        if failure is None:
            self.up("db")

    def up(self, *services: str) -> None:
        self.compose("up", "-d", "--wait", "--wait-timeout", "90", *services)

    def client(self) -> Client:
        port = self.compose("port", "frontend", "8080").decode().strip().rsplit(":", 1)[1]
        return Client(f"http://127.0.0.1:{port}", ORIGIN)

    def login(self, password: str) -> Client:
        client = self.client()
        client.request("/api/v1/ready")
        client.login(OWNER, password)
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


def exercise_credentials(stack: Stack, password: str) -> str:
    first = stack.login(password)
    other = stack.login(password)
    changed_password = secrets.token_hex(24)
    reset_password = secrets.token_hex(24)
    path = "/api/v1/auth/password"
    payload = json.dumps({"current_password": password, "new_password": changed_password})
    data, headers = first.request(path, "POST", payload.encode(), "application/json")
    replacement = json.loads(data)["csrf_token"]
    cookies: SimpleCookie = SimpleCookie()
    cookies.load(headers["Set-Cookie"])
    bearer = cookies["__Host-florabase-session"]
    old_cookie = first.cookie
    first.cookie = bearer.key + "=" + bearer.value
    first.csrf = replacement
    first.request("/api/v1/auth/session")
    other.request("/api/v1/auth/session", expected=401)
    old_csrf = other.csrf

    # A rejected query is still observed by both access loggers.
    query_canary = "auth-query-" + secrets.token_hex(12)
    first.request(path + "?check=" + query_canary, "POST", b"{}", "application/json", 400)
    first.json("/api/v1/auth/login", "POST", {"login_name": OWNER, "password": password}, 401)
    stack.login(changed_password)
    logs = stack.compose("logs", "--no-color", "frontend", "backend").decode()
    assert logs.count(path) >= 4
    for secret in (
        query_canary,
        password,
        changed_password,
        old_csrf,
        replacement,
        old_cookie,
        bearer.value,
    ):
        assert secret not in logs

    stack.compose("stop", "frontend", "backend")
    result = stack.backend(
        "python",
        "-m",
        "florabase.auth.reset_password",
        OWNER,
        "--password-json-stdin",
        data=json.dumps(reset_password).encode(),
    )
    assert b"reset committed" in result
    assert reset_password.encode() not in result
    stack.up()
    restarted = stack.client()
    restarted.cookie = first.cookie
    restarted.request("/api/v1/auth/session", expected=401)
    restarted.json(
        "/api/v1/auth/login", "POST", {"login_name": OWNER, "password": changed_password}, 401
    )
    stack.login(reset_password)
    print("Portable credential change and offline reset passed", flush=True)
    return reset_password


def smoke(source: Stack, restore: Stack) -> None:
    assert set(source.compose("config", "--services").split()) == {b"db", b"backend", b"frontend"}
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
    head = source.backend("alembic", "heads").split()[0].decode()
    assert source.sql("SELECT version_num FROM alembic_version") == head.encode()
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
    for service, uid in (("db", b"70"), ("backend", b"10001"), ("frontend", b"101")):
        assert source.compose("exec", "-T", service, "id", "-u").strip() == uid
    password = exercise_credentials(source, password)
    original = png(19, 37, 59)
    client = source.login(password)
    asset = client.upload(original, "portable-smoke")
    path = asset["content_url"]

    # Real service restarts preserve both state roots and never run Alembic.
    source.compose("restart")
    source.up()
    assert source.login(password).request(path)[0] == original
    assert source.sql("SELECT version_num FROM alembic_version") == head.encode()

    source.compose("stop", "frontend", "backend")
    source.sql("UPDATE alembic_version SET version_num = 'foreign_revision'")
    source.backend(failure="foreign_revision")
    source.backend(*SCHEMA, "upgrade", "foreign_revision", failure="migration history")
    assert source.sql("SELECT version_num FROM alembic_version") == b"foreign_revision"
    source.sql(f"UPDATE alembic_version SET version_num = '{head}'")
    dump = source.compose(
        "exec",
        "-T",
        "db",
        "sh",
        "-ec",
        'export PGPASSWORD="$POSTGRES_PASSWORD"; '
        'exec pg_dump -Fc --no-owner --no-privileges -U "$POSTGRES_USER" "$POSTGRES_DB"',
    )
    source.backend(*ARTIFACTS, "verify")
    media = source.backend(*ARTIFACTS, "archive")

    # Deliberately create a conflicting relation at the parent of the last migration.
    # Only this disposable fixture is downgraded to construct that historical schema.
    source.backend("alembic", "downgrade", "20261009_0041")
    source.sql("CREATE TABLE application_settings (sentinel int)")
    source.backend(failure="differs from image head")
    source.backend(*SCHEMA, "upgrade", "20261009_0041", failure="SQLSTATE 42P07")
    assert source.sql("SELECT version_num FROM alembic_version") == b"20261009_0041"
    assert source.sql("SELECT count(sentinel) FROM application_settings") == b"0"
    source.backend(failure="differs from image head")
    source.sql("DROP TABLE application_settings")
    source.backend(*SCHEMA, "upgrade", "20261009_0041")
    source.up()
    assert source.login(password).request(path)[0] == original

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
    )
    restore.backend(
        "sh",
        "-ec",
        'entries=$(ls -A "$FLORABASE_ATTACHMENT_STORAGE_ROOT"); test -z "$entries"; '
        "exec python /app/scripts/attachment_artifacts.py restore",
        data=media,
    )
    restore.backend(*ARTIFACTS, "verify")
    restore.up()
    assert restore.login(password).request(path)[0] == original
    assert source.login(password).request(path)[0] == original


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("compose", type=Path)
    parser.add_argument("backend_image")
    args = parser.parse_args()
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
        smoke(*stacks)
    print(
        "Portable Compose smoke passed (fresh install, restart, refusal, failed upgrade, restore)"
    )


if __name__ == "__main__":
    main()
