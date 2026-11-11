#!/usr/bin/env python3
"""Full lifecycle exercise on uniquely isolated Compose resources, including interrupted cutover."""

from __future__ import annotations

import json
import shutil
import socket
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from dev_golden import DevGolden, local_docker, require
from dev_golden_snapshot import command
from smoke_lifecycle import SmokeLifecycle, operator_snapshot
from workflow_environment import Environment, Repository, WorkflowError, run
from workflow_resources import docker, machine_lock

FIXTURE_OWNER = "smoke-owner"
FIXTURE_PASSWORD = "dev-golden-isolated-smoke-password"
ROTATED_PASSWORD = "dev-golden-rotated-fixture-password"


def ports() -> dict[str, int]:
    with socket.socket() as db, socket.socket() as backend, socket.socket() as frontend:
        sockets = {"db": db, "backend": backend, "frontend": frontend}
        for listener in sockets.values():
            listener.bind(("127.0.0.1", 0))
        return {name: int(listener.getsockname()[1]) for name, listener in sockets.items()}


class FixtureEnvironment(Environment):
    def __init__(self, repository: Repository, project: str, published: dict[str, int]) -> None:
        super().__init__(repository, "dev")
        self.project = project
        self.published = published
        self.env_source = Path("/dev/null")

    def environment(self) -> dict[str, str]:
        return super().environment() | {
            "POSTGRES_DB": "florabase",
            "POSTGRES_USER": "florabase",
            "POSTGRES_PASSWORD": FIXTURE_PASSWORD,
            "FLORABASE_DATABASE_URL": f"postgresql+psycopg://florabase:{FIXTURE_PASSWORD}@db:5432/florabase",
            "POSTGRES_PORT": str(self.published["db"]),
            "BACKEND_PORT": str(self.published["backend"]),
            "FRONTEND_PORT": str(self.published["frontend"]),
            "FLORABASE_CORS_ORIGINS": "[]",
        }


class InterruptedDev(DevGolden):
    def media(self, action: str, *, token: str, **kwargs: Any) -> bytes:
        if action == "restore-media":
            raise KeyboardInterrupt("simulated interruption between PostgreSQL and media restores")
        return super().media(action, token=token, **kwargs)


def login(origin: str, password: str = FIXTURE_PASSWORD) -> str:
    request = Request(
        origin + "/api/v1/auth/login",
        data=json.dumps({"login_name": FIXTURE_OWNER, "password": password}).encode(),
        headers={"Origin": origin, "Content-Type": "application/json"},
    )
    with urlopen(request, timeout=10) as response:
        cookie: str | None = response.headers.get("Set-Cookie")
        if response.status != 200 or not cookie:
            raise AssertionError("DEV login failed")
        return cookie.split(";", 1)[0]


def rotate_fixture_password(target: DevGolden) -> None:
    command(
        [
            "docker",
            "exec",
            "-i",
            target.service("backend"),
            "python",
            "-c",
            "import sys; from sqlalchemy import update; from sqlalchemy.orm import Session; "
            "from florabase.auth.model import User; from florabase.auth.security import password_hasher; "
            "from florabase.db.session import get_engine; s=Session(get_engine()); "
            "s.execute(update(User).values(password_hash=password_hasher().hash(sys.stdin.read()))); "
            "s.commit()",
        ],
        data=ROTATED_PASSWORD.encode(),
    )


def require_session_revoked(origin: str, cookie: str) -> None:
    request = Request(origin + "/api/v1/auth/session", headers={"Cookie": cookie})
    try:
        with urlopen(request, timeout=10):
            raise AssertionError("archived session survived restoration")
    except HTTPError as error:
        require(error.code == 401, f"expected revoked session, received {error.code}")


def fixture_source(repository: Repository, source: Path) -> None:
    for name in (
        ".gitignore",
        "compose.yaml",
        "compose.dev.yaml",
        "compose.integration.yaml",
    ):
        shutil.copy2(repository.source / name, source / name)
    for name in ("backend", "frontend", "scripts"):
        shutil.copytree(
            repository.source / name,
            source / name,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                "*.pyc",
                ".env",
                ".venv",
                ".coverage",
                ".mypy_cache",
                ".pytest_cache",
                ".ruff_cache",
                "node_modules",
                "dist",
                "coverage",
                "*.tsbuildinfo",
            ),
        )
    run(["git", "-C", str(source), "init", "--initial-branch=main"], capture=True)
    run(["git", "-C", str(source), "add", "."], capture=True)
    commit(source, "Fixture main")


def commit(source: Path, message: str) -> None:
    run(
        [
            "git",
            "-C",
            str(source),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture",
            "commit",
            "-am",
            message,
        ],
        capture=True,
    )


def smoke() -> None:
    repo = Repository(Path.cwd())
    before = operator_snapshot(repo)
    project = f"florabase-dev-golden-smoke-{uuid.uuid4().hex[:12]}"
    published = ports()
    with tempfile.TemporaryDirectory(prefix="florabase-dev-golden-smoke-") as temp:
        source = Path(temp) / "source"
        source.mkdir()
        fixture_source(repo, source)
        env = FixtureEnvironment(Repository(source), project, published)
        pending = Path(temp) / "evidence" / "pending.json"
        target = DevGolden(env, pending, ports=published)
        with SmokeLifecycle(env):
            started = time.monotonic()
            env.upgrade_state()
            env.up()
            print(f"Disposable DEV startup: {time.monotonic() - started:.1f}s", flush=True)
            target.validate()
            command(
                [
                    "docker",
                    "exec",
                    "-i",
                    target.service("backend"),
                    "python",
                    "-c",
                    "import json,sys; from sqlalchemy.orm import Session; "
                    "from florabase.auth.service import bootstrap_owner; "
                    "from florabase.db.session import get_engine; "
                    "s=Session(get_engine()); bootstrap_owner(s, *json.load(sys.stdin)); s.commit()",
                ],
                data=json.dumps([FIXTURE_OWNER, FIXTURE_PASSWORD]).encode(),
            )
            old_cookie = login(target.origin)
            target.status()
            target.status()

            foreign = docker(
                "run",
                "-d",
                "--network",
                "none",
                "--label",
                f"com.docker.compose.project={project}-foreign",
                "--mount",
                f"type=volume,source={target.volume('attachment_data')},target=/foreign,readonly",
                target.images["backend"],
                "sleep",
                "infinity",
            )
            try:
                try:
                    target.validate()
                except WorkflowError as error:
                    require("Foreign container uses DEV volume" in str(error), str(error))
                else:
                    raise AssertionError("foreign volume consumer accepted")
            finally:
                docker("rm", "--force", foreign)
            target.change("init")
            (initial_backup,) = list(pending.parent.glob("*/before.json"))
            login(target.origin)
            require(
                target.verify() == target.verify() == 0,
                "repeat verify changed the baseline",
            )

            database = target.service("db")
            target.scalar(
                database,
                "UPDATE plants SET label='Golden edited in DEV' WHERE id=(SELECT min(id::text)::uuid FROM plants)",
            )
            edited = "SELECT count(*) FROM plants WHERE label='Golden edited in DEV'"
            require(target.scalar(database, edited) == "1", "fixture edit missing")
            try:
                target.change("init")
            except WorkflowError as error:
                require("collection is occupied" in str(error), str(error))
            else:
                raise AssertionError("occupied DEV was initialized")
            require(
                target.scalar(database, edited) == "1",
                "refused init changed the collection",
            )

            interrupted = InterruptedDev(env, pending, ports=published)
            try:
                interrupted.change("reset")
            except KeyboardInterrupt:
                require(
                    json.loads(pending.read_text())["phase"] == "replace",
                    "recovery phase missing",
                )
            else:
                raise AssertionError("failure was not injected")
            target.recover()
            require(target.scalar(database, edited) == "1", "recovery lost pre-reset edit")
            login(target.origin)

            target.change("reset")
            require(
                target.scalar(database, edited) == "0",
                "reset retained modified collection",
            )
            login(target.origin)
            require(target.verify() == 0, "reset failed baseline verification")
            target.scalar(
                database,
                "UPDATE plants SET label='Golden edited in DEV' WHERE id=(SELECT min(id::text)::uuid FROM plants)",
            )
            env.stop_dev()
            env.compose("start", "--wait", "--wait-timeout", "180", "db", "backend", "frontend")
            require(target.scalar(database, edited) == "1", "restart lost edits")
            (source / "main-update-marker").write_text("main update\n")
            run(["git", "-C", str(source), "add", "main-update-marker"])
            commit(source, "Simulated main update")
            env.up()
            target.validate()
            require(
                target.scalar(target.service("db"), edited) == "1",
                "main update reseeded DEV",
            )
            require(target.verify() == 3, "operator edit should differ from baseline")
            rotate_fixture_password(target)
            target.restore_backup(initial_backup.parent.name)
            require(
                target.scalar(target.service("db"), "SELECT count(*) FROM plants") == "0",
                "archived pair did not restore the pre-Golden collection",
            )
            require(
                not target.media("read-ledger", token=uuid.uuid4().hex),
                "pre-Golden restore retained a ledger",
            )
            require_session_revoked(target.origin, old_cookie)
            login(target.origin, ROTATED_PASSWORD)
            require(operator_snapshot(repo) == before, "persistent environments changed")
    require(operator_snapshot(repo) == before, "cleanup changed persistent environments")
    print("DEV_GOLDEN_SMOKE_PASSED")


if __name__ == "__main__":
    local_docker()
    with machine_lock("verification-full", "disposable DEV Golden lifecycle smoke"):
        smoke()
