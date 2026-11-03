#!/usr/bin/env python3
"""Disposable BETA-RUNTIME-001 acceptance on Synology-equivalent Docker 24.0.2 + Compose 2.20.1.

An owned, network-isolated docker:24.0.2-dind daemon runs the real distribution stack on
disk-backed owned volumes. The controller runs from a copied bundle (no checkout) under Python 3.8
in a container sharing only that daemon's loopback. Candidate images are built from this source;
derived test-only backends prove compatible, failing, crashing and forward-fix upgrades. Every
resource carries exact run ownership and is retired on exit; nothing touches another environment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from workflow_resources import Disposable, Owner

ROOT = Path(__file__).resolve().parents[1]
DIND_IMAGE = (
    "docker:24.0.2-dind@sha256:1d148deae16a6bb4c89224c636e1fd1799a4d5925f545861ce0d7bea3a527b5d"
)
OPERATOR_IMAGE = (
    "python:3.8.20-slim-bookworm"
    "@sha256:1d52838af602b4b5a831beb13a0e4d073280665ea7be7f69ce2382f29c5a613f"
)
REGISTRY_IMAGE = (
    "registry:2.8.3@sha256:a3d8aaa63ed8681a604f1dea0aa03f100d5895b6a58ace528858a7b332415373"
)
RESTIC_IMAGE = (
    "restic/restic:0.17.3@sha256:8f5a62b422a2cb1277ea0dd6e826fe1acf649e5b9f02d60e5268d5fd1976255a"
)
COMPOSE_URL = (
    "https://github.com/docker/compose/releases/download/v2.20.1/docker-compose-linux-x86_64"
)
COMPOSE_SHA256 = "804aa825c58b375901ba9dc9d0aa1648ce305d903a58f2a5c42bb5c6873b02bf"
COMPOSE_CACHE = Path.home() / ".cache/florabase/beta-runtime-tools/compose-2.20.1"
DATA = "/srv/florabase-runtime-smoke"
INSTALL = DATA + "/root"
ORIGIN = "https://florabase-runtime-smoke.invalid"
LIVE_PORT = 18080
DRILL_PORT = 18081
REGISTRY = "127.0.0.1:5000"
OWNER_LOGIN = "runtime-owner"

MIGRATION = '''"""BETA-RUNTIME-001 smoke revision {revision}: test-only, never shipped."""

import sqlalchemy as sa
from alembic import op

revision = "{revision}"
down_revision = "{down}"
branch_labels = None
depends_on = None


def upgrade() -> None:
{body}


def downgrade() -> None:
    raise NotImplementedError("test-only revision")
'''
BODIES = {
    "runtime_smoke_b": '    op.create_table("runtime_smoke_b", sa.Column("id", sa.Integer, primary_key=True))',
    "runtime_smoke_c": (
        '    op.create_table("runtime_smoke_c", sa.Column("id", sa.Integer, primary_key=True))\n'
        '    raise RuntimeError("injected migration failure")'
    ),
    "runtime_smoke_d": '    op.add_column("runtime_smoke_b", sa.Column("note", sa.Text(), nullable=True))',
}
# Test seam only: save an external asset's local copy without contacting the network.
SAVE_COPY = r"""
import asyncio, struct, sys, uuid, zlib
import florabase.media.copies as copies
from sqlalchemy.orm import Session
from florabase.attachments.storage import AttachmentStorage
from florabase.core.config import get_settings
from florabase.db.session import get_engine
def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
PNG = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
       + chunk(b"IDAT", zlib.compress(bytes([0, 40, 60, 210]))) + chunk(b"IEND", b""))
copies.fetch_image = lambda url, max_bytes: (PNG, "image/png")
with Session(get_engine()) as database:
    asyncio.run(copies.save_copy(database, AttachmentStorage.from_settings(get_settings()),
                                 uuid.UUID(sys.argv[1]), refresh=False))
print("SAVED_EXTERNAL_COPY")
"""


def run(*args: str, **kwargs: Any) -> str:
    result = subprocess.run(list(args), check=True, stdout=subprocess.PIPE, text=True, **kwargs)
    return str(result.stdout).strip()


def compose_binary() -> Path:
    """Official Compose 2.20.1, verified against the recorded release digest."""
    COMPOSE_CACHE.mkdir(parents=True, exist_ok=True)
    binary = COMPOSE_CACHE / "docker-compose-linux-x86_64"
    if not binary.exists():
        partial = binary.with_suffix(".partial")
        subprocess.run(["curl", "-fsSL", "-o", str(partial), COMPOSE_URL], check=True)
        partial.rename(binary)
    actual = hashlib.sha256(binary.read_bytes()).hexdigest()
    if actual != COMPOSE_SHA256:
        raise SystemExit(f"Compose 2.20.1 digest mismatch: {actual}; refusing to use it")
    return binary


class Smoke:
    def __init__(self, lifetime: Disposable, owner: Owner, tools: Path) -> None:
        self.lifetime = lifetime
        self.owner = owner
        self.tools = tools
        self.labels = [arg for k, v in owner.labels().items() for arg in ("--label", f"{k}={v}")]
        self.dind = owner.project + "-dind"
        self.operator = owner.project + "-operator"
        self.password = secrets.token_urlsafe(24)
        self.evidence: dict[str, Any] = {"steps": []}
        self.started = time.monotonic()

    # ---- host and nested daemon helpers

    def owned(self, *args: str, stdin: str | None = None) -> str:
        return str(self.lifetime.run(list(args), stdin=stdin))

    def nested(self, *args: str) -> str:
        return run("docker", "exec", self.dind, "docker", *args)

    def nested_json(self, *args: str) -> Any:
        return json.loads(self.nested(*args))

    def step(self, name: str, **details: Any) -> None:
        elapsed = round(time.monotonic() - self.started, 1)
        self.evidence["steps"].append(dict(details, step=name, elapsed_seconds=elapsed))
        print(
            f"RUNTIME_SMOKE_STEP {name} {json.dumps(details, sort_keys=True)}",
            flush=True,
        )

    def ctl(
        self,
        *args: str,
        expect: int | tuple[int, ...] = 0,
        stdin: str | None = None,
        fault: str | None = None,
    ) -> str:
        env = ["-e", "FLORABASECTL_TEST_MODE=1"]
        if fault:
            env += ["-e", "FLORABASECTL_TEST_FAULT=" + fault]
        command = ["docker", "exec", "-i", *env, self.operator, "python3", "-I"]
        command += ["/opt/florabase/bundle/florabasectl.py", "--root", INSTALL, *args]
        result = subprocess.run(
            command,
            input=stdin,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if result.returncode not in (expect if isinstance(expect, tuple) else (expect,)):
            raise SystemExit(
                f"florabasectl {' '.join(args)}: exit {result.returncode}, expected {expect}\n"
                + result.stdout[-4000:]
            )
        return result.stdout

    def operator_sh(self, script: str) -> str:
        return run("docker", "exec", self.operator, "sh", "-c", script)

    def stack(self, *args: str, stdin: str | None = None) -> str:
        base = [
            "docker",
            "exec",
            "-i",
            self.operator,
            "docker",
            "compose",
            "--project-name",
            "florabase-prod",
            "--project-directory",
            INSTALL + "/stack",
            "--file",
            INSTALL + "/stack/compose.yaml",
            "--env-file",
            INSTALL + "/stack/.env",
        ]
        return run(*base, *args, input=stdin)

    def client(self, action: str, port: int = LIVE_PORT) -> dict[str, Any]:
        output = run(
            "docker",
            "exec",
            "-i",
            self.operator,
            "python3",
            "-I",
            "/opt/florabase/bundle/smoke_beta_runtime_client.py",
            action,
            "--base",
            f"http://127.0.0.1:{port}",
            "--origin",
            ORIGIN,
            "--login",
            OWNER_LOGIN,
            input=self.password + "\n",
        )
        value = json.loads(output.splitlines()[-1])
        assert isinstance(value, dict)
        return value

    def db_container(self) -> dict[str, str]:
        identifier = self.stack("ps", "-q", "db")
        details = self.nested_json("inspect", identifier)[0]
        return {
            "id": details["Id"],
            "image": details["Image"],
            "started": details["State"]["StartedAt"],
        }

    def status(self) -> dict[str, Any]:
        output = self.ctl("status", "--json", expect=0)
        value = json.loads(output[output.index("{") :])
        assert isinstance(value, dict)
        return value

    # ---- environment

    def build_candidates(self) -> dict[str, str]:
        inputs = json.loads((ROOT / "release/inputs.json").read_text())
        revision = run("git", "-C", str(ROOT), "rev-parse", "HEAD")
        tags = {}
        for service in ("backend", "frontend"):
            tag = f"{self.owner.project}-{service}-a"
            self.owned(
                "docker",
                "build",
                "--platform",
                "linux/amd64",
                "--target",
                "runtime",
                "--tag",
                tag,
                "--build-arg",
                "VERSION=" + inputs["version"],
                "--build-arg",
                "REVISION=" + revision,
                *self.labels,
                str(ROOT / service),
            )
            tags[service] = tag
        head = run(
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--entrypoint",
            "python",
            tags["backend"],
            "-c",
            "from alembic.config import Config\nfrom alembic.script import ScriptDirectory\n"
            "print(ScriptDirectory.from_config(Config('alembic.ini')).get_heads()[0])",
        )
        variants = {
            "b": (["runtime_smoke_b"], None),
            "c": (["runtime_smoke_b", "runtime_smoke_c"], None),
            "d": (
                ["runtime_smoke_b", "runtime_smoke_d"],
                "injected application failure",
            ),
            "e": (["runtime_smoke_b", "runtime_smoke_d"], None),
        }
        downs = {
            "runtime_smoke_b": head,
            "runtime_smoke_c": "runtime_smoke_b",
            "runtime_smoke_d": "runtime_smoke_b",
        }
        for name, (revisions, crash) in variants.items():
            context = self.tools / ("build-" + name)
            context.mkdir()
            for revision_id in revisions:
                (context / f"zz_{revision_id}.py").write_text(
                    MIGRATION.format(
                        revision=revision_id,
                        down=downs[revision_id],
                        body=BODIES[revision_id],
                    )
                )
            lines = [f"FROM {tags['backend']}", "COPY zz_*.py /app/alembic/versions/"]
            if crash:
                # Compose owns the backend command, so the crash must live in the application.
                (context / "crash.py").write_text(f"\nraise SystemExit({crash!r})\n")
                lines += [
                    "USER root",
                    "COPY crash.py /tmp/crash.py",
                    'RUN python -c "import importlib.util as u, pathlib; '
                    "p = pathlib.Path(u.find_spec('florabase.main').origin); "
                    "p.write_text(p.read_text() + pathlib.Path('/tmp/crash.py').read_text())\" "
                    "&& rm /tmp/crash.py",
                    "USER florabase",
                ]
            (context / "Dockerfile").write_text("\n".join(lines) + "\n")
            tag = f"{self.owner.project}-backend-{name}"
            self.owned("docker", "build", "--tag", tag, *self.labels, str(context))
            tags["backend-" + name] = tag
        self.evidence["candidates"] = {
            "revision": revision,
            "version": inputs["version"],
            "a_head": head,
        }
        self.heads = {
            "a": head,
            "b": "runtime_smoke_b",
            "c": "runtime_smoke_c",
            "d": "runtime_smoke_d",
            "e": "runtime_smoke_d",
        }
        self.version, self.revision = inputs["version"], revision
        self.postgres = inputs["postgresql"]
        return tags

    def start_daemon(self) -> None:
        for volume in ("docker", "data"):
            self.owned(
                "docker",
                "volume",
                "create",
                *self.labels,
                f"{self.owner.project}-{volume}",
            )
        # No network: the nested daemon and its loopback API are reachable from nowhere else.
        self.owned(
            "docker",
            "run",
            "-d",
            "--privileged",
            "--network",
            "none",
            "--name",
            self.dind,
            *self.labels,
            "-e",
            "DOCKER_TLS_CERTDIR=",
            "-v",
            f"{self.owner.project}-docker:/var/lib/docker",
            "-v",
            f"{self.owner.project}-data:{DATA}",
            DIND_IMAGE,
            "dockerd",
            "--host",
            "unix:///var/run/docker.sock",
            "--host",
            "tcp://127.0.0.1:2375",
            "--tls=false",
        )
        self.wait_daemon()
        self.start_operator()

    def wait_daemon(self, since: str = "") -> None:
        """Never exec into the container before dockerd listens.

        The DinD entrypoint moves every process out of the root cgroup before enabling cgroup v2
        controllers; an early `docker exec` lands there and makes that write fail, killing it.
        """
        logs = ""
        for _ in range(120):
            logs = subprocess.run(
                ["docker", "logs", *(["--since", since] if since else []), self.dind],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            ).stdout
            state = run("docker", "inspect", "-f", "{{.State.Status}}", self.dind)
            if state != "running":
                break
            if "API listen on /var/run/docker.sock" in logs:
                probe = subprocess.run(
                    ["docker", "exec", self.dind, "docker", "info"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if probe.returncode == 0:
                    return
            time.sleep(1)
        raise SystemExit("nested Docker 24.0.2 daemon did not start:\n" + logs[-4000:])

    def start_operator(self) -> None:
        self.owned(
            "docker",
            "run",
            "-d",
            "--init",
            "--name",
            self.operator,
            *self.labels,
            "--network",
            "container:" + self.dind,
            "-v",
            f"{self.owner.project}-data:{DATA}",
            "-v",
            f"{self.tools}:/opt/florabase:ro",
            "-e",
            "DOCKER_HOST=tcp://127.0.0.1:2375",
            "-e",
            "DOCKER_CONFIG=/opt/florabase/docker-config",
            "-e",
            "PATH=/opt/florabase/bin:/usr/local/bin:/usr/bin:/bin",
            OPERATOR_IMAGE,
            "sleep",
            "infinity",
        )

    def restart_daemon(self) -> None:
        """Daemon restart; the operator shares the daemon namespace and is rejoined after it."""
        since = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.owned("docker", "restart", self.dind)
        # Only log lines from the new start count; stale ones must not pass readiness.
        self.wait_daemon(since=since)
        self.owned("docker", "restart", self.operator)

    def transfer(self, reference: str) -> str:
        save = ["docker", "save", "--platform", "linux/amd64", reference]
        archive = self.tools / "transfer.tar"
        with archive.open("wb") as stream:
            subprocess.run(save, check=True, stdout=stream)
        with archive.open("rb") as stream:
            output = subprocess.run(
                ["docker", "exec", "-i", self.dind, "docker", "load"],
                check=True,
                stdin=stream,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout
        archive.unlink()
        match = re.search(r"Loaded image(?: ID)?: (\S+)", output)
        if not match:
            raise SystemExit("could not load " + reference)
        return match.group(1)

    def push(self, local: str, repository: str, tag: str) -> str:
        target = f"{REGISTRY}/{repository}:{tag}"
        self.nested("tag", local, target)
        output = self.nested("push", target)
        match = re.search(r"digest: (sha256:[a-f0-9]{64})", output)
        if not match:
            raise SystemExit("push did not report a digest for " + target)
        return f"{REGISTRY}/{repository}@{match.group(1)}"

    def publish(self, tags: dict[str, str]) -> dict[str, str]:
        registry = self.transfer(REGISTRY_IMAGE)
        self.nested(
            "run",
            "-d",
            "--restart",
            "always",
            "--name",
            "registry",
            "-p",
            f"{REGISTRY}:5000",
            registry,
        )
        for _ in range(30):
            if (
                subprocess.run(
                    [
                        "docker",
                        "exec",
                        self.dind,
                        "wget",
                        "-q",
                        "-O-",
                        f"http://{REGISTRY}/v2/",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ).returncode
                == 0
            ):
                break
            time.sleep(1)
        refs = {}
        for name, tag in tags.items():
            repository = "florabase-frontend" if name == "frontend" else "florabase-backend"
            refs[name] = self.push(self.transfer(tag), repository, name)
        postgres = self.push(
            self.transfer(self.postgres["reference"]),
            "postgres",
            self.postgres["version"],
        )
        refs["postgres"] = postgres.replace(
            "/postgres@", "/postgres:" + self.postgres["version"] + "@"
        )
        refs["restic"] = self.push(self.transfer(RESTIC_IMAGE), "restic", "0.17.3")
        # Unrelated sentinel workload: must be unchanged by every controller action.
        self.nested("volume", "create", "sentinel")
        self.nested(
            "run",
            "--rm",
            "-v",
            "sentinel:/data",
            "--entrypoint",
            "sh",
            registry,
            "-c",
            "echo sentinel > /data/value",
        )
        self.nested(
            "run",
            "-d",
            "--restart",
            "unless-stopped",
            "--name",
            "sentinel",
            "-v",
            "sentinel:/data",
            registry,
        )
        self.evidence["references"] = refs
        return refs

    def manifest(self, name: str, refs: dict[str, str]) -> tuple[str, str]:
        def entry(reference: str) -> dict[str, str]:
            digest = reference.rsplit("@", 1)[1]
            return {
                "reference": reference,
                "index_digest": digest,
                "platform_digest": digest,
                "platform": "linux/amd64",
            }

        backend = refs["backend" if name == "a" else "backend-" + name]
        value = {
            "schema_version": 1,
            "distribution": "test-candidate",
            "version": self.version,
            "source": {
                "url": "https://github.com/alessandrorossato/florabase",
                "revision": self.revision,
                "dirty": False,
            },
            "platforms": ["linux/amd64"],
            "alembic_head": self.heads[name],
            "postgresql": dict(
                entry(refs["postgres"]),
                repository=f"{REGISTRY}/postgres",
                version=self.postgres["version"],
            ),
            "images": {"backend": entry(backend), "frontend": entry(refs["frontend"])},
            "build_inputs": {},
            "workflow": {"run_id": "0", "run_attempt": "0"},
        }
        path = self.tools / "manifests" / (name + ".json")
        path.write_text(json.dumps(value, indent=2))
        return "/opt/florabase/manifests/" + name + ".json", hashlib.sha256(
            path.read_bytes()
        ).hexdigest()

    def promote(self, name: str, *extra: str, expect: int = 0, fault: str | None = None) -> str:
        path, digest = self.manifests[name]
        return self.ctl(
            "promote",
            "--manifest",
            path,
            "--manifest-sha256",
            digest,
            "--allow-test-candidate",
            *extra,
            expect=expect,
            fault=fault,
        )

    # ---- acceptance sequence

    def scenario(self, refs: dict[str, str]) -> None:
        self.manifests = {name: self.manifest(name, refs) for name in "abcde"}
        host_before = host_inventory()
        sentinel = self.nested_json("inspect", "sentinel")[0]["Id"]

        # Host-dependent capacity checks may fail on a workstation; runtime checks may not.
        output = self.ctl("preflight", "--evidence", DATA + "/preflight.json", expect=(0, 1))
        preflight = json.loads(self.operator_sh(f"cat {DATA}/preflight.json"))
        required = {
            "linux",
            "amd64",
            "python>=3.8",
            "engine>=24.0",
            "compose>=2.20",
            "memory-cgroup",
            "pids-limit",
        }
        checks = {item["name"]: item for item in preflight["checks"]}
        if not all(checks[name]["ok"] for name in required):
            raise SystemExit("runtime preflight failed:\n" + output)
        if (preflight["engine"], preflight["compose"], preflight["python"]) != (
            "24.0.2",
            "2.20.1",
            "3.8.20",
        ):
            raise SystemExit("smoke must run Engine 24.0.2, Compose 2.20.1 and Python 3.8.20")
        self.step(
            "preflight",
            engine=preflight["engine"],
            compose=preflight["compose"],
            python=preflight["python"],
            host_dependent={n: c["ok"] for n, c in checks.items() if n not in required},
        )

        for unsafe in ("0.0.0.0", "::", "192.0.2.10"):
            self.ctl("init", "--origin", ORIGIN, "--bind-address", unsafe, expect=2)
        self.ctl("init", "--origin", ORIGIN, "--http-port", str(LIVE_PORT))
        self.ctl("init", "--origin", ORIGIN, expect=2)
        path, digest = self.manifests["a"]
        self.ctl(
            "install",
            "--manifest",
            path,
            "--manifest-sha256",
            "0" * 64,
            "--allow-test-candidate",
            expect=2,
        )
        self.ctl(
            "install",
            "--manifest",
            path,
            "--manifest-sha256",
            digest,
            "--allow-test-candidate",
        )
        modes = self.operator_sh(
            f"stat -c '%n %u:%g %a' {INSTALL}/postgres {INSTALL}/media {INSTALL}/secrets "
            f"{INSTALL}/secrets/db.env {INSTALL}/secrets/backend.env"
        ).splitlines()
        self.step("install", release="a", ownership=modes)
        self.ctl("bootstrap-owner", OWNER_LOGIN, stdin=self.password + "\n")
        self.ctl("acceptance", "--owner", OWNER_LOGIN, stdin=self.password + "\n")

        seeded = self.client("seed")
        self.stack(
            "--profile",
            "maintenance",
            "run",
            "--rm",
            "--no-deps",
            "-T",
            "tools",
            "python",
            "-c",
            SAVE_COPY,
            seeded["external"],
        )
        baseline = self.client("snapshot")
        assets = baseline["assets"]
        if not (
            assets[seeded["unlinked"]]["links"] == []
            and len(assets[seeded["shared"]]["links"]) == 2
            and assets[seeded["external"]]["sha256"]
            and all(asset["sha256"] for asset in assets.values())
        ):
            raise SystemExit("seeded unlinked/shared/saved-copy relationships missing")
        self.step("seed", assets=len(assets), seeded=seeded)

        self.stack("up", "-d", "--force-recreate", "--no-deps", "backend", "frontend")
        self.ctl("acceptance")
        before_restart = self.db_container()
        self.restart_daemon()
        self.ctl("acceptance", "--owner", OWNER_LOGIN, stdin=self.password + "\n")
        if self.client("snapshot") != baseline:
            raise SystemExit("data changed across recreation and daemon restart")
        after_restart = self.db_container()
        if before_restart["id"] != after_restart["id"]:
            raise SystemExit("daemon restart replaced the PostgreSQL container")
        self.step(
            "persistence",
            recreated=["backend", "frontend"],
            daemon_restart=True,
            db_restarted_at=after_restart["started"],
        )

        self.schema_guard_drill(baseline)

        set_one = re.findall(r"BACKUP_COMPLETE (\S+)", self.ctl("backup"))[0]
        self.ctl("verify-backup", set_one)
        if self.client("snapshot") != baseline:
            raise SystemExit("backup changed data or did not restart writers")
        tamper = f"{INSTALL}/backups/{set_one}/attachments.tar"
        self.operator_sh(f"cp {tamper} {DATA}/pristine.tar && printf x >> {tamper}")
        self.ctl("verify-backup", set_one, expect=1)
        self.operator_sh(f"cp {DATA}/pristine.tar {tamper} && rm {DATA}/pristine.tar")
        metadata = json.loads(self.operator_sh(f"cat {INSTALL}/backups/{set_one}/metadata.json"))
        self.step(
            "backup",
            set_id=set_one,
            tables=len(metadata["table_counts"]),
            attachments=metadata["table_counts"].get("attachments"),
            revision=metadata["alembic_revision"],
            tamper_detected=True,
        )

        live_db = self.db_container()
        began = time.monotonic()
        output = self.ctl(
            "restore-isolated",
            set_one,
            "--http-port",
            str(DRILL_PORT),
            "--owner",
            OWNER_LOGIN,
            stdin=self.password + "\n",
        )
        restore_seconds = round(time.monotonic() - began, 1)
        project = re.findall(r"project=(florabase-restore-[a-f0-9]{8})", output)[0]
        if self.client("snapshot", DRILL_PORT) != baseline:
            raise SystemExit("isolated restore differs from the source data")
        if self.client("snapshot") != baseline or self.db_container() != live_db:
            raise SystemExit("isolated restore touched the live installation")
        self.ctl("restore-remove", "--project", project, "--confirm", "wrong", expect=2)
        self.ctl("restore-remove", "--project", project, "--confirm", project)
        if self.nested("ps", "-aq", "--filter", "label=com.docker.compose.project=" + project):
            raise SystemExit("isolated restore containers remain")
        self.step("restore-isolated", set_id=set_one, project=project, seconds=restore_seconds)

        self.operator_sh(
            f"umask 077; mkdir -p {DATA}/work && head -c 32 /dev/urandom | od -An -tx1 "
            f"| tr -d ' \\n' > {DATA}/work/restic-password"
        )
        restic = [
            "--repository",
            DATA + "/offhost/repo",
            "--password-file",
            DATA + "/work/restic-password",
            "--restic-image",
            refs["restic"],
        ]
        self.ctl("export", set_one, *restic, "--init")
        self.operator_sh(f"mv {INSTALL}/backups/{set_one} {DATA}/work/{set_one}")
        self.ctl("import-set", set_one, *restic)
        self.ctl("verify-backup", set_one)
        self.operator_sh(f"diff -r {DATA}/work/{set_one} {INSTALL}/backups/{set_one}")
        self.step("offhost-export", set_id=set_one, encrypted="restic", import_identical=True)

        volumes_before = self.volumes()
        self.promote("b", expect=2)  # migration requires explicit confirmation
        self.promote("b", "--confirm-migration")
        self.ctl("acceptance", "--owner", OWNER_LOGIN, stdin=self.password + "\n")
        if self.db_container() != live_db or self.volumes() != volumes_before:
            raise SystemExit("application promotion changed PostgreSQL or volume identity")
        if self.client("snapshot") != baseline:
            raise SystemExit("compatible upgrade changed data")
        self.step("promote-compatible", release="b", postgres_container=live_db["id"][:12])

        refused = self.promote("a", expect=2)
        self.step("refuse-ahead-schema", message=refused.strip().splitlines()[-1])

        failed = self.promote("c", "--confirm-migration", expect=1)
        if json.loads(self.status_operation())["phase"] != "backed_up":
            raise SystemExit("failed migration did not stop before the migrated phase")
        self.ctl("abort")
        self.ctl("acceptance", "--owner", OWNER_LOGIN, stdin=self.password + "\n")
        if self.client("snapshot") != baseline:
            raise SystemExit("failed migration drill changed data")
        self.step(
            "failed-migration",
            aborted=True,
            error=failed.strip().splitlines()[-1][:200],
        )

        self.promote("d", "--confirm-migration", expect=1)
        operation = json.loads(self.operator_sh(f"cat {INSTALL}/state/operation.json"))
        pre_upgrade = operation["backup"]
        if operation["phase"] != "pinned" or operation["status"] != "failed":
            raise SystemExit("application failure was not recorded after migration")
        refused_abort = self.ctl("abort", expect=2)
        self.promote("e", expect=2)  # forward fix must be explicit
        self.promote("e", "--after-failed")
        self.ctl("acceptance", "--owner", OWNER_LOGIN, stdin=self.password + "\n")
        if self.client("snapshot") != baseline or self.db_container() != live_db:
            raise SystemExit("forward fix changed data or PostgreSQL identity")
        self.step(
            "failed-application",
            pre_upgrade_set=pre_upgrade,
            forward_fix="e",
            abort_refused=refused_abort.strip().splitlines()[-1][:200],
        )

        installation = json.loads(self.operator_sh(f"cat {INSTALL}/state/installation.json"))
        identity = installation["installation_id"]
        replace = ["restore-replace", pre_upgrade]
        self.ctl(
            *replace,
            "--confirm-installation",
            "0" * 32,
            "--confirm-database",
            "florabase",
            expect=2,
        )
        self.ctl(
            *replace,
            "--confirm-installation",
            identity,
            "--confirm-database",
            "wrong",
            expect=2,
        )
        began = time.monotonic()
        output = self.ctl(
            *replace,
            "--confirm-installation",
            identity,
            "--confirm-database",
            "florabase",
        )
        replace_seconds = round(time.monotonic() - began, 1)
        sessions = self.stack(
            "exec",
            "-T",
            "db",
            "sh",
            "-c",
            'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM auth_sessions"',
        )
        if sessions != "0":
            raise SystemExit("restored sessions were not invalidated")
        if self.status()["release"]["images"]["backend"] != refs["backend-b"]:
            raise SystemExit("replacement restore did not return to the pre-upgrade pair")
        self.ctl("acceptance", "--owner", OWNER_LOGIN, stdin=self.password + "\n")
        if self.client("snapshot") != baseline:
            raise SystemExit("replacement restore differs from the pre-upgrade data")
        preserved = re.findall(r"previous data kept in (\S+)\)", output)[0]
        self.operator_sh(f"test -d {preserved}/postgres && test -d {preserved}/media")
        self.step(
            "restore-replace",
            set_id=pre_upgrade,
            seconds=replace_seconds,
            sessions_invalidated=True,
            failed_state_preserved=preserved,
        )

        self.promote("e", "--confirm-migration", expect=137, fault="migrated")
        self.promote("e", "--confirm-migration", expect=2)
        operation = json.loads(self.status_operation())
        interrupted = {k: operation[k] for k in ("status", "phase")}
        if interrupted != {"status": "in_progress", "phase": "migrated"}:
            raise SystemExit("interrupted promotion was not left at the migrated phase")
        self.ctl("resume")
        self.ctl("acceptance", "--owner", OWNER_LOGIN, stdin=self.password + "\n")
        if self.client("snapshot") != baseline or self.db_container()["image"] != live_db["image"]:
            raise SystemExit("interrupted upgrade recovery changed data or PostgreSQL image")
        self.step(
            "interrupted-upgrade",
            killed_after="migrated",
            observed=interrupted,
            resumed=True,
        )

        # Optional datasets: recorded by digest, mounted read-only, absent settings stay unset.
        dataset = INSTALL + "/reference/wfo-smoke.sqlite"
        self.operator_sh(f"head -c 4096 /dev/urandom > {dataset} && chmod 0644 {dataset}")
        digest = self.operator_sh(f"sha256sum {dataset}").split()[0]
        reference = ["reference", "set", "--kind", "wfo", "--file", "wfo-smoke.sqlite"]
        self.ctl(*reference, "--sha256", "0" * 64, expect=2)
        self.ctl(*reference, "--sha256", digest, "--provenance", "runtime smoke fixture")
        mounted = "/var/lib/florabase/reference/wfo-smoke.sqlite"
        environment = self.stack("exec", "-T", "backend", "env")
        if f"FLORABASE_WFO_SNAPSHOT_PATH={mounted}" not in environment.splitlines() or (
            "FLORABASE_WCVP_V16_SNAPSHOT_PATH" in environment
        ):
            raise SystemExit("reference dataset settings were not rendered exactly")
        self.stack(
            "exec",
            "-T",
            "backend",
            "sh",
            "-c",
            f"test -r {mounted} && ! touch {mounted} 2>/dev/null",
        )
        self.ctl("reference", "clear", "--kind", "wfo")
        if "SNAPSHOT_PATH" in self.stack("exec", "-T", "backend", "env"):
            raise SystemExit("cleared reference dataset is still configured")
        self.step("reference-datasets", kind="wfo", read_only=True, cleared=True)

        self.retention_drill()
        retention = self.ctl("retention")
        status = self.status()
        if status["problems"] or status["release"]["images"]["backend"] != refs["backend-e"]:
            raise SystemExit("final status is not clean: " + json.dumps(status))
        labels = {
            service: self.nested_json("inspect", self.stack("ps", "-q", service))[0]["Config"][
                "Labels"
            ]["dockhand.update"]
            for service in ("db", "backend", "frontend")
        }
        journal = self.operator_sh(f"wc -l < {INSTALL}/state/journal.jsonl")
        if (
            self.nested_json("inspect", "sentinel")[0]["Id"] != sentinel
            or self.nested(
                "run",
                "--rm",
                "-v",
                "sentinel:/data",
                "--entrypoint",
                "cat",
                self.nested_json("inspect", "sentinel")[0]["Image"],
                "/data/value",
            )
            != "sentinel"
        ):
            raise SystemExit("unrelated workload changed")
        if host_inventory() != host_before:
            raise SystemExit("host florabase-prod resources changed")
        self.step(
            "final",
            status={k: v for k, v in status.items() if k != "disk_free"},
            dockhand_labels=labels,
            journal_entries=int(journal),
            retention_dry_run=retention.strip().splitlines()[-1],
            unrelated_workload_unchanged=True,
            host_florabase_prod_unchanged=True,
        )

    def http_status(self, path: str) -> int:
        script = (
            "import sys, urllib.error, urllib.request\n"
            "try:\n"
            f"    print(urllib.request.urlopen('http://127.0.0.1:{LIVE_PORT}' + sys.argv[1],"
            " timeout=5).status)\n"
            "except urllib.error.HTTPError as error:\n    print(error.code)\n"
            "except OSError:\n    print(0)\n"
        )
        return int(run("docker", "exec", self.operator, "python3", "-c", script, path))

    def backend(self) -> dict[str, Any]:
        details = self.nested_json("inspect", self.stack("ps", "-aq", "backend"))[0]
        assert isinstance(details, dict)
        return details

    def psql(self, sql: str) -> str:
        return self.stack(
            "exec",
            "-T",
            "db",
            "sh",
            "-c",
            'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -Atc "' + sql + '"',
        )

    def never_ready(self, phase: str, seconds: int = 45) -> dict[str, Any]:
        """The incompatible backend must not become healthy or serve readiness."""
        deadline = time.monotonic() + seconds
        observed = set()
        while time.monotonic() < deadline:
            state = self.backend()["State"]
            health = (state.get("Health") or {}).get("Status")
            observed.add(str(health or state["Status"]))
            if health == "healthy" or self.http_status("/api/v1/ready") == 200:
                raise SystemExit(f"incompatible backend became ready after {phase}")
            time.sleep(3)
        logs = run(
            "docker",
            "exec",
            self.dind,
            "docker",
            "logs",
            "--tail",
            "50",
            self.backend()["Id"],
            stderr=subprocess.STDOUT,
        )
        if "refusing to start" not in logs:
            raise SystemExit(f"guard refusal not logged after {phase}")
        return {"phase": phase, "states": sorted(observed)}

    def schema_guard_drill(self, baseline: dict[str, Any]) -> None:
        """R1: no stale success, restart or recreation lets a mismatched schema serve."""
        backend = self.backend()
        logs = run(
            "docker", "exec", self.dind, "docker", "logs", backend["Id"], stderr=subprocess.STDOUT
        )
        if "schema-guard: database at release head " + self.heads["a"] not in logs:
            raise SystemExit("compatible start did not record the guard's success")
        self.psql("UPDATE alembic_version SET version_num = 'runtime_smoke_forged'")
        # Already running: the schema-aware healthcheck must stop it, not keep serving.
        deadline = time.monotonic() + 90
        while self.backend()["RestartCount"] == backend["RestartCount"] and (
            self.backend()["State"]["StartedAt"] == backend["State"]["StartedAt"]
        ):
            if time.monotonic() > deadline:
                raise SystemExit("running backend kept serving a changed schema")
            time.sleep(3)
        results = [self.never_ready("running backend schema change")]
        plain = subprocess.run(
            [
                "docker",
                "exec",
                self.operator,
                "timeout",
                "150",
                "docker",
                "compose",
                "--project-name",
                "florabase-prod",
                "--project-directory",
                INSTALL + "/stack",
                "--file",
                INSTALL + "/stack/compose.yaml",
                "--env-file",
                INSTALL + "/stack/.env",
                "up",
                "-d",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        results.append(dict(self.never_ready("plain docker compose up -d"), compose_exit=plain))
        self.nested("restart", self.backend()["Id"])
        results.append(self.never_ready("docker restart"))
        self.stack("up", "-d", "--no-deps", "--force-recreate", "backend")
        results.append(self.never_ready("recreation (Dockhand-equivalent redeploy)"))
        self.psql(f"UPDATE alembic_version SET version_num = '{self.heads['a']}'")
        self.stack("up", "-d", "--no-deps", "--force-recreate", "backend")
        self.ctl("acceptance", "--owner", OWNER_LOGIN, stdin=self.password + "\n")
        if self.client("snapshot") != baseline:
            raise SystemExit("schema guard drill changed data")
        self.step("schema-guard", refused=results, compatible_after_restore=True)

    def retention_drill(self) -> None:
        """R2 on real sets: a planted traversal entry is never eligible; newest set survives."""
        backups = INSTALL + "/backups"
        valid = sorted(
            line.split()[0] for line in self.ctl("list-backups").splitlines() if "  " in line
        )
        planted = "20260101T000000Z-manual-0000aa"
        self.operator_sh(
            f"cp -a {backups}/{valid[-1]} {backups}/{planted} && cd {backups}/{planted} && "
            "python3 -c \"import json; m=json.load(open('metadata.json')); "
            "m['set_id']='../postgres'; m['created_at']='2026-01-01T00:00:00Z'; "
            "json.dump(m, open('metadata.json', 'w'))\" && "
            "sha256sum attachments.tar compose.yaml database.dump metadata.json > SHA256SUMS"
        )
        output = self.ctl(
            "retention", "--daily", "1", "--weekly", "0", "--upgrades", "0", "--apply"
        )
        remaining = self.operator_sh(f"ls {backups}").split()
        self.operator_sh(f"test -d {INSTALL}/postgres && test -d {backups}/{planted}")
        if valid[-1] not in remaining or "keeping unverifiable entry" not in output:
            raise SystemExit("retention did not keep the newest set or skip the planted entry")
        self.ctl("retention", "--daily", "1", "--weekly", "0", "--upgrades", "0", "--apply")
        self.operator_sh(f"rm -rf {backups}/{planted}")
        self.ctl("acceptance")
        self.step(
            "retention-boundary",
            before=len(valid),
            kept=valid[-1],
            planted_traversal_kept_untouched=True,
            idempotent=True,
        )

    def status_operation(self) -> str:
        return self.operator_sh(f"cat {INSTALL}/state/operation.json 2>/dev/null || true")

    def volumes(self) -> dict[str, Any]:
        result = {}
        for volume in ("postgres_data", "attachment_data", "reference_data"):
            details = self.nested_json("volume", "inspect", "florabase-prod_" + volume)[0]
            result[volume] = (
                details["Name"],
                details["Options"]["device"],
                details["CreatedAt"],
            )
        return result


def host_inventory() -> dict[str, str]:
    label = "label=com.docker.compose.project=florabase-prod"
    return {
        kind: run("docker", *command, "--filter", label)
        for kind, command in (
            ("containers", ["ps", "-aq", "--no-trunc"]),
            ("volumes", ["volume", "ls", "-q"]),
            ("networks", ["network", "ls", "-q"]),
        )
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    compose = compose_binary()
    source = {
        "commit": run("git", "-C", str(ROOT), "rev-parse", "HEAD"),
        "tree": run("git", "-C", str(ROOT), "rev-parse", "HEAD^{tree}"),
        "clean": run("git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all")
        == "",
    }
    if not source["clean"]:
        print("WARNING: dirty source tree; this run is not evidence for a commit", flush=True)
    if run("docker", "version", "--format", "{{.Server.Os}}/{{.Server.Arch}}") != "linux/amd64":
        raise SystemExit("native linux/amd64 Docker is required")
    with tempfile.TemporaryDirectory(prefix="florabase-runtime-smoke-") as temporary:
        tools = Path(temporary)
        os.chmod(tools, 0o755)
        bundle = tools / "bundle"
        bundle.mkdir()
        for name in ("compose.yaml", "florabasectl.py"):
            shutil.copyfile(ROOT / "deploy/beta" / name, bundle / name)
        shutil.copyfile(
            ROOT / "scripts/smoke_beta_runtime_client.py",
            bundle / "smoke_beta_runtime_client.py",
        )
        (tools / "manifests").mkdir()
        plugins = tools / "docker-config" / "cli-plugins"
        plugins.mkdir(parents=True)
        shutil.copyfile(compose, plugins / "docker-compose")
        (plugins / "docker-compose").chmod(0o755)
        (tools / "bin").mkdir()
        owner = Owner.disposable("workflow-smoke", tools)
        with Disposable(owner) as lifetime:
            smoke = Smoke(lifetime, owner, tools)
            with (tools / "bin" / "docker").open("wb") as stream:
                subprocess.run(
                    [
                        "docker",
                        "run",
                        "--rm",
                        *smoke.labels,
                        "--network",
                        "none",
                        "--entrypoint",
                        "cat",
                        DIND_IMAGE,
                        "/usr/local/bin/docker",
                    ],
                    check=True,
                    stdout=stream,
                )
            (tools / "bin" / "docker").chmod(0o755)
            tags = smoke.build_candidates()
            smoke.start_daemon()
            refs = smoke.publish(tags)
            smoke.scenario(refs)
            smoke.evidence.update(
                source=source,
                runtime={
                    "engine": "24.0.2",
                    "compose": "2.20.1",
                    "compose_sha256": COMPOSE_SHA256,
                    "dind": DIND_IMAGE,
                    "operator_python": OPERATOR_IMAGE,
                    "registry": REGISTRY_IMAGE,
                    "restic": RESTIC_IMAGE,
                },
                project=owner.project,
                total_seconds=round(time.monotonic() - smoke.started, 1),
            )
            args.evidence.write_text(json.dumps(smoke.evidence, indent=2, sort_keys=True) + "\n")
    print("BETA_RUNTIME_SMOKE_PASSED evidence=" + str(args.evidence), flush=True)


if __name__ == "__main__":
    main()
