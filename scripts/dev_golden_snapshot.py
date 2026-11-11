"""Stream paired DEV Golden snapshots through disposable PostgreSQL and media storage."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tarfile
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from disposable_workflow import compose_invocation
from workflow_environment import WorkflowError
from workflow_resources import Disposable, Owner

PROFILE = "comprehensive"
COPY = "golden_dev_stage"
STAGE_USER = "florabase_integration"
LEDGER = ".golden-dataset.json"
ARTIFACTS = ("collection.dump", "originals.tar", LEDGER)


def command(
    argv: list[str],
    *,
    env: dict[str, str] | None = None,
    source: Path | None = None,
    destination: Path | None = None,
    data: bytes | None = None,
) -> bytes:
    """Keep dump bytes and credentials out of argv and console output."""
    try:
        with (
            source.open("rb") if source is not None else nullcontext() as incoming,
            destination.open("xb") if destination is not None else nullcontext() as outgoing,
        ):
            if outgoing is not None:
                os.fchmod(outgoing.fileno(), 0o600)
            result = subprocess.run(
                argv,
                env=env,
                stdin=incoming,
                input=data,
                stdout=outgoing if outgoing is not None else subprocess.PIPE,
                check=True,
            )
            if outgoing is not None:
                outgoing.flush()
                os.fsync(outgoing.fileno())
            return result.stdout or b""
    except (OSError, subprocess.CalledProcessError) as error:
        raise WorkflowError(f"snapshot command failed ({argv[0]} {argv[1]})") from error


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def checksums(directory: Path) -> dict[str, str]:
    return {name: sha256(directory / name) for name in ARTIFACTS}


def originals_identity(directory: Path) -> dict[str, str]:
    with tarfile.open(directory / ARTIFACTS[1], mode="r:") as archive:
        result: dict[str, str] = {}
        for entry in archive:
            if entry.isfile():
                stream = archive.extractfile(entry)
                if stream is None:
                    raise WorkflowError("Cannot read snapshot original")
                digest = hashlib.sha256()
                with stream:
                    while chunk := stream.read(1024 * 1024):
                        digest.update(chunk)
                result[entry.name] = digest.hexdigest()
        return result


@dataclass
class Stage:
    argv: list[str]
    env: dict[str, str]
    runner: str

    def app(self, *args: str, **kwargs: Any) -> bytes:
        return command(["docker", "exec", "-i", self.runner, *args], **kwargs)

    def database(self, *args: str, **kwargs: Any) -> bytes:
        return command([*self.argv, "exec", "-T", "db", *args], env=self.env, **kwargs)

    def golden(self, action: str) -> dict[str, Any]:
        output = self.app(
            "python",
            "/review/golden_dataset.py",
            action,
            "--copy",
            COPY,
            "--profile",
            PROFILE,
        )
        report: dict[str, Any] = json.loads(output) if output else {}
        return report

    def helper(self, action: str, **kwargs: Any) -> bytes:
        return self.app("python", "/review/dev_golden_payload.py", action, **kwargs)

    def prepare_empty(self) -> None:
        self.golden("create-copy")

    def load(self, directory: Path) -> None:
        self.database("dropdb", "-U", STAGE_USER, "--if-exists", COPY)
        self.database("createdb", "-U", STAGE_USER, "--template=template0", COPY)
        self.database(
            "pg_restore",
            "-U",
            STAGE_USER,
            "-d",
            COPY,
            "--single-transaction",
            "--no-owner",
            "--no-privileges",
            source=directory / ARTIFACTS[0],
        )
        self.helper("stage-media", source=directory / ARTIFACTS[1])
        self.helper("write-ledger", source=directory / LEDGER)
        self.helper("verify-media")

    def export(self, directory: Path) -> None:
        directory.mkdir(mode=0o700)
        self.database(
            "pg_dump",
            "-U",
            STAGE_USER,
            "-d",
            COPY,
            "-Fc",
            "--no-owner",
            "--no-privileges",
            destination=directory / ARTIFACTS[0],
        )
        self.helper("archive", destination=directory / ARTIFACTS[1])
        self.helper("read-ledger", destination=directory / LEDGER)

    def database_identity(self) -> str:
        with tempfile.TemporaryDirectory(prefix="florabase-golden-db-identity-") as temporary:
            dump = Path(temporary) / "collection.sql"
            self.database(
                "pg_dump",
                "-U",
                STAGE_USER,
                "-d",
                COPY,
                "--no-owner",
                "--no-privileges",
                "--restrict-key=FlorabaseDevGoldenRoundTripOnly",
                destination=dump,
            )
            return sha256(dump)


@contextmanager
def isolated_stage(root: Path) -> Iterator[Stage]:
    owner = Owner.disposable("integration", root)
    with tempfile.TemporaryDirectory(prefix="florabase-golden-compose-") as temporary:
        argv, env = compose_invocation("integration", root, owner, [], Path(temporary))
        with Disposable(owner) as lifecycle:
            lifecycle.run([*argv, "up", "-d", "--wait", "--wait-timeout", "120", "db"], env=env)
            lifecycle.run([*argv, "build", "tests"], env=env)
            lifecycle.run(
                [*argv, "run", "-d", "--no-deps", "tests", "sleep", "infinity"],
                env=env,
            )
            inventory = lifecycle.resources.inventory()
            lifecycle.resources.preflight(inventory)
            (runner,) = [
                item["Id"]
                for item in inventory["containers"]
                if item["Config"]["Labels"]["com.docker.compose.service"] == "tests"
            ]
            yield Stage(argv, env, runner)
