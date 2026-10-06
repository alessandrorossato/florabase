#!/usr/bin/env python3
"""Explicit source/config/resource boundaries for local Florabase environments."""

from __future__ import annotations

import argparse
import ast
import hashlib
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote, urlsplit

DEV_PROJECT = "florabase"  # Preserve existing operator volumes; never silently rename them.
REVIEW_PROJECT = "florabase-feature-review"
UAT_PROJECT = "florabase-uat-preview"
PORTS = {"dev": "5173", "review": "15174", "preview": "15173"}
BRANCH_PATTERN = re.compile(r"^(feat|fix|docs|ci)/[a-z0-9][a-z0-9._-]*$")
MEDIA_ROOT = "/var/lib/florabase/attachments"
LEGACY_MEDIA_ROOT = "/tmp/florabase-attachments"


class WorkflowError(RuntimeError):
    pass


def local_identity(environment: dict[str, str]) -> dict[str, str]:
    """Use the bind-mount owner's invoking identity, never a workstation/CI-specific UID."""
    get_uid, get_gid = getattr(os, "getuid", None), getattr(os, "getgid", None)
    if callable(get_uid) and callable(get_gid):
        uid, gid = str(get_uid()), str(get_gid())
    else:
        uid, gid = environment.get("LOCAL_UID", ""), environment.get("LOCAL_GID", "")
        if not re.fullmatch(r"[0-9]+", uid) or not re.fullmatch(r"[0-9]+", gid):
            raise WorkflowError(
                "host UID/GID APIs are unavailable; explicitly set LOCAL_UID and LOCAL_GID "
                "to the non-root Docker identity that can write the development bind mounts"
            )
    if int(uid) == 0:
        raise WorkflowError(
            "DEV/Review/QUALITY require a non-root invoking user who owns the checkout; "
            "run these commands as that user without sudo"
        )
    return {"LOCAL_UID": str(int(uid)), "LOCAL_GID": str(int(gid))}


def run(command: list[str], *, capture: bool = False, env: dict[str, str] | None = None) -> str:
    try:
        result = subprocess.run(
            command,
            check=True,
            text=True,
            stdout=subprocess.PIPE if capture else None,
            env=env,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        # Commands never contain credentials or rendered Compose configuration.
        raise WorkflowError(f"command failed: {' '.join(command)}") from error
    return result.stdout.strip() if capture else ""


class Repository:
    def __init__(self, path: Path) -> None:
        self.source = Path(
            run(["git", "-C", str(path), "rev-parse", "--show-toplevel"], capture=True)
        )
        self.common = Path(self.git("rev-parse", "--path-format=absolute", "--git-common-dir"))
        self.metadata = Path(self.git("rev-parse", "--absolute-git-dir"))
        # Git's first worktree record is the main checkout, even when .git is a pointer file.
        records = self.git("worktree", "list", "--porcelain", "-z").split("\0")
        self.primary = Path(records[0].removeprefix("worktree "))

    def git(self, *args: str) -> str:
        return run(["git", "-C", str(self.source), *args], capture=True)

    def identity(self) -> dict[str, str]:
        return {
            "source": str(self.source),
            "branch": self.git("branch", "--show-current") or "detached",
            "sha": self.git("rev-parse", "HEAD"),
            "dirty": "yes" if self.git("status", "--porcelain") else "no",
        }

    def env_file(self) -> Path:
        explicit = os.environ.get("FLORABASE_ENV_FILE")
        if explicit:
            path = Path(explicit).expanduser().resolve()
            if not path.is_file():
                raise WorkflowError(f"FLORABASE_ENV_FILE does not exist: {path}")
            return path
        for directory in (self.source, self.primary):
            path = directory / ".env"
            if path.is_file():
                return path
        return Path("/dev/null")

    def initialize(self, branch: str = "") -> None:
        origin = self.git("remote", "get-url", "origin")
        normalized = re.sub(r"^git@github\.com:", "https://github.com/", origin)
        normalized = re.sub(r"^ssh://git@github\.com/", "https://github.com/", normalized)
        if (
            normalized.rstrip("/").removesuffix(".git")
            != "https://github.com/alessandrorossato/florabase"
        ):
            raise WorkflowError("origin is not the expected Florabase repository")
        current = self.git("branch", "--show-current")
        base = self.git("rev-parse", "--verify", "origin/main")
        if not current:
            if not BRANCH_PATTERN.fullmatch(branch):
                raise WorkflowError(
                    "detached worktree: provide BRANCH=ci/example (feat/fix/docs/ci)"
                )
            if self.git("status", "--porcelain") or self.git("rev-parse", "HEAD") != base:
                raise WorkflowError(
                    "attach a branch deliberately: detached tree must be clean at origin/main"
                )
            if self.git("branch", "--list", branch) or self.git(
                "branch", "-r", "--list", f"origin/{branch}"
            ):
                raise WorkflowError(f"branch already exists: {branch}")
            self.git("switch", "--create", branch)
            current = branch
        if not BRANCH_PATTERN.fullmatch(current) or (branch and branch != current):
            raise WorkflowError(
                "current branch must match BRANCH and use feat/, fix/, docs/, or ci/"
            )
        self.git("merge-base", "--is-ancestor", "origin/main", "HEAD")
        print("FEATURE CONTEXT READY")
        for name, value in self.identity().items():
            print(f"{name.title()}: {value}")
        print(f"Primary: {self.primary}")
        print(f"Origin/main: {base}")
        print(f"Feature base: {self.git('merge-base', 'HEAD', 'origin/main')}")
        print(f"Common metadata: {self.common}")


def migration_graph(source: Path) -> dict[str, list[str]]:
    """Read literal Alembic metadata without importing application code on the host."""
    graph: dict[str, list[str]] = {}
    for path in sorted((source / "backend/alembic/versions").glob("*.py")):
        values: dict[str, object] = {}
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                name, value = node.target.id, node.value
            elif (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
            ):
                name, value = node.targets[0].id, node.value
            else:
                continue
            if name in {"revision", "down_revision"} and value is not None:
                values[name] = ast.literal_eval(value)
        revision, parent = values.get("revision"), values.get("down_revision")
        if not isinstance(revision, str) or revision in graph:
            raise WorkflowError(f"missing or duplicate literal revision: {path}")
        if isinstance(parent, str):
            graph[revision] = [parent]
        elif parent is None:
            graph[revision] = []
        elif isinstance(parent, (list, tuple)) and all(isinstance(item, str) for item in parent):
            graph[revision] = list(parent)
        else:
            raise WorkflowError(f"invalid literal down_revision: {path}")
    if not graph or any(parent not in graph for parents in graph.values() for parent in parents):
        raise WorkflowError("code migration graph is empty or has missing parents")
    return graph


def code_heads(graph: dict[str, list[str]]) -> list[str]:
    heads = sorted(set(graph) - {parent for parents in graph.values() for parent in parents})
    if len(heads) != 1:
        raise WorkflowError(f"expected one code Alembic head; found {heads}")
    return heads


def require_upgradeable(current: list[str], graph: dict[str, list[str]]) -> None:
    pending = code_heads(graph)
    ancestors: set[str] = set()
    while pending:
        revision = pending.pop()
        if revision not in ancestors:
            ancestors.add(revision)
            pending.extend(graph[revision])
    unknown = set(current) - ancestors
    if unknown:
        raise WorkflowError(
            f"DB CURRENT IS AHEAD OF OR INCOMPATIBLE WITH CODE: {','.join(sorted(unknown))}; "
            f"code head: {','.join(code_heads(graph))}. Use the owning checkout with these revisions "
            "or update main after merge; never downgrade automatically."
        )


def preserve_media(source: Path, existing: Path) -> None:
    """Preflight conflicts, exclusively copy missing files, verify; never overwrite/delete."""
    entries: dict[Path, list[Path]] = {}
    for root in (source, existing):
        if not root.is_dir():
            raise WorkflowError("legacy DEV media root is unavailable; stop refused")
        paths: list[Path] = []

        def fail_walk(error: OSError) -> None:
            raise WorkflowError("cannot read legacy DEV media tree; stop refused") from error

        for directory, directories, files in os.walk(root, onerror=fail_walk):
            paths.extend(Path(directory) / name for name in (*directories, *files))
        if any(path.is_symlink() or not (path.is_file() or path.is_dir()) for path in paths):
            raise WorkflowError(
                "unsupported legacy DEV media entry; stop refused with media intact"
            )
        entries[root] = paths
    original = {path: file_digest(path) for path in entries[existing] if path.is_file()}
    missing: list[Path] = []
    for path in entries[source]:
        target = existing / path.relative_to(source)
        if target.exists():
            if path.is_dir() != target.is_dir() or (
                path.is_file() and file_digest(path) != file_digest(target)
            ):
                raise WorkflowError(
                    "legacy and durable DEV media conflict; stop refused; both copies remain intact"
                )
        elif path.is_file():
            if any(parent.exists() and not parent.is_dir() for parent in target.parents):
                raise WorkflowError("legacy DEV media path conflict; stop refused")
            missing.append(path)
    for path in missing:
        target = existing / path.relative_to(source)
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with path.open("rb") as reader, target.open("xb") as writer:
            os.chmod(target, 0o600)
            shutil.copyfileobj(reader, writer)
            writer.flush()
            os.fsync(writer.fileno())
    for path in entries[source]:
        if path.is_file() and file_digest(path) != file_digest(existing / path.relative_to(source)):
            raise WorkflowError("legacy DEV media preservation verification failed; stop refused")
    if any(file_digest(path) != value for path, value in original.items()):
        raise WorkflowError("existing durable DEV media changed; stop refused")


def file_digest(path: Path) -> bytes:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").digest()


class Environment:
    def __init__(self, repository: Repository, role: str) -> None:
        self.repository = repository
        self.role = role
        self.source = repository.primary if role == "dev" else repository.source
        self.repo = Repository(self.source)
        suffix = hashlib.sha256(str(repository.metadata).encode()).hexdigest()[:12]
        self.project = {
            "dev": DEV_PROJECT,
            "review": REVIEW_PROJECT,
            "uat": UAT_PROJECT,
            "quality": f"florabase-quality-{suffix}",
            "prod": "florabase-prod",
        }[role]
        self.url = f"http://localhost:{PORTS.get('review' if role == 'uat' else role, '8080')}"
        self.env_source = self.repo.env_file() if role in {"dev", "prod"} else repository.env_file()

    def environment(self) -> dict[str, str]:
        env = dict(os.environ)
        # Prevent implicit project/files/config from overriding this environment contract.
        for key in list(env):
            if key.startswith("COMPOSE_"):
                env.pop(key)
        identity = self.repo.identity()
        env.update({f"FLORABASE_{key.upper()}": value for key, value in identity.items()})
        env["COMPOSE_PROJECT_NAME"] = self.project
        env["FLORABASE_ROLE"] = self.role
        if self.role in {"dev", "review", "uat", "quality"}:
            # Shell values override .env and Compose's defaults, including stale 1000:1000
            # settings. Runtime users and dev-state-init receive the same numeric identity.
            env.update(local_identity(env))
        if self.role in {"review", "uat", "quality"}:
            database = {
                "review": "florabase_review",
                "uat": "florabase_uat",
                "quality": "florabase_quality",
            }[self.role]
            env.update(
                {
                    "POSTGRES_DB": database,
                    "POSTGRES_USER": database,
                    "POSTGRES_PASSWORD": "local-isolated-only-password",
                    "FLORABASE_DATABASE_URL": f"postgresql+psycopg://{database}:local-isolated-only-password@db:5432/{database}",
                    "FRONTEND_PORT": PORTS.get(
                        "review" if self.role == "uat" else self.role, "5173"
                    ),
                    "FLORABASE_CORS_ORIGINS": "[]",
                }
            )
        return env

    def command(self, *args: str) -> list[str]:
        files = ["compose.yaml"]
        if self.role != "prod":
            files.append("compose.dev.yaml")
        if self.role in {"review", "uat"}:
            files.append("compose.review.yaml")
        if self.role == "uat":
            files.append("compose.uat.yaml")
        return [
            "docker",
            "compose",
            "--env-file",
            str(self.env_source),
            "--project-name",
            self.project,
            "--project-directory",
            str(self.source),
            *[part for name in files for part in ("--file", str(self.source / name))],
            *args,
        ]

    def compose(self, *args: str, capture: bool = False) -> str:
        return run(self.command(*args), capture=capture, env=self.environment())

    def containers(self) -> list[dict[str, Any]]:
        ids = run(
            [
                "docker",
                "ps",
                "-aq",
                "--filter",
                f"label=com.docker.compose.project={self.project}",
            ],
            capture=True,
        ).splitlines()
        return (
            cast(
                list[dict[str, Any]],
                json.loads(run(["docker", "inspect", *ids], capture=True)),
            )
            if ids
            else []
        )

    def require_owner(self, *, allow_stopped_dev: bool = False) -> None:
        containers = self.containers()
        if allow_stopped_dev and self.role == "dev" and containers:
            self.dev_containers(containers)
            if all(not item["State"].get("Running") for item in containers):
                print("Stopped DEV identity validated; primary may reuse its preserved volumes.")
                return
        for container in containers:
            labels = container["Config"].get("Labels", {})
            owner = labels.get("io.florabase.source") or labels.get(
                "com.docker.compose.project.working_dir"
            )
            if owner and Path(owner).resolve() != self.source.resolve():
                raise WorkflowError(
                    f"{self.project} belongs to {owner}; "
                    + (
                        "run make dev-stop, then make dev-up to start primary DEV with preserved data"
                        if self.role == "dev"
                        else "stop/remove it from that checkout before using " + str(self.source)
                    )
                )
        if self.role in {"review", "uat"}:
            names = run(
                [
                    "docker",
                    "volume",
                    "ls",
                    "-q",
                    "--filter",
                    f"name=^{self.project}_",
                ],
                capture=True,
            ).splitlines()
            for name in names:
                details = json.loads(run(["docker", "volume", "inspect", name], capture=True))[0]
                owner = (details.get("Labels") or {}).get("io.florabase.source")
                if owner != str(self.source):
                    raise WorkflowError(
                        f"review volume {name} belongs to {owner or 'unknown source'}; remove explicitly from its owner first"
                    )

    def dev_containers(self, containers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Validate exact Docker identity, without reading the former checkout/configuration."""
        services: dict[str, dict[str, Any]] = {}
        owners: set[str] = set()
        legacy = False
        volumes: set[str] = set()
        expected_mounts = {
            "db": {"/var/lib/postgresql": "postgres_data"},
            "backend": {MEDIA_ROOT: "attachment_data"},
            "frontend": {"/app/node_modules": "frontend_node_modules"},
            "dev-state-init": {
                "/app/node_modules": "frontend_node_modules",
                "/state/attachments": "attachment_data",
            },
        }
        for container in containers:
            labels = container["Config"].get("Labels") or {}
            service = labels.get("com.docker.compose.service")
            owner = labels.get("com.docker.compose.project.working_dir", "")
            role = labels.get("io.florabase.role")
            if (
                labels.get("com.docker.compose.project") != self.project
                or service not in expected_mounts
                or service in services
                or labels.get("com.docker.compose.oneoff", "").lower() != "false"
                or labels.get("com.docker.compose.container-number") != "1"
                or not labels.get("com.docker.compose.config-hash")
                or not Path(owner).is_absolute()
                or labels.get("io.florabase.source", owner) != owner
                or role not in {None, "dev"}
                or container["State"].get("Paused")
                or container["State"].get("Restarting")
                or container["State"].get("Dead")
                or set(container.get("NetworkSettings", {}).get("Networks", {}))
                != {f"{self.project}_internal"}
            ):
                raise WorkflowError("ambiguous DEV container identity; recovery refused")
            if role is None:
                legacy = True
                if labels.get("com.docker.compose.project.config_files") != (
                    f"{owner}/compose.yaml,{owner}/compose.dev.yaml"
                ):
                    raise WorkflowError("unrecognized legacy DEV configuration; recovery refused")
            owners.add(owner)
            mounts = {item["Destination"]: item for item in container.get("Mounts", [])}
            for target, key in expected_mounts[service].items():
                mount = mounts.get(target, {})
                name = f"{self.project}_{key}"
                if mount.get("Type") != "volume" or mount.get("Name") != name:
                    raise WorkflowError("DEV storage identity is ambiguous; recovery refused")
                volumes.add(name)
            if service in {"backend", "frontend"}:
                target, suffix = (
                    ("/app/src", "backend/src") if service == "backend" else ("/app", "frontend")
                )
                mount = mounts.get(target, {})
                if mount.get("Type") != "bind" or mount.get("Source") != f"{owner}/{suffix}":
                    raise WorkflowError(
                        "DEV source mounts disagree with metadata; recovery refused"
                    )
            if service == "backend":
                settings = container["Config"].get("Env", [])
                if (
                    "FLORABASE_ENVIRONMENT=development" not in settings
                    or "FLORABASE_COOKIE_MODE=loopback-development" not in settings
                    or not any(
                        f"FLORABASE_ATTACHMENT_STORAGE_ROOT={root}" in settings
                        for root in (MEDIA_ROOT, LEGACY_MEDIA_ROOT)
                    )
                ):
                    raise WorkflowError(
                        "container is not a recognized DEV backend; recovery refused"
                    )
            services[service] = container
        if len(owners) != 1 or (legacy and not {"db", "backend", "frontend"} <= services.keys()):
            raise WorkflowError("mixed or incomplete DEV identity; recovery refused")
        details = json.loads(run(["docker", "volume", "inspect", *sorted(volumes)], capture=True))
        if {item["Name"] for item in details} != volumes:
            raise WorkflowError("DEV volume identity is incomplete; recovery refused")
        for volume in details:
            labels = volume.get("Labels") or {}
            if (
                labels.get("com.docker.compose.project") != self.project
                or volume["Name"] != f"{self.project}_{labels.get('com.docker.compose.volume')}"
            ):
                raise WorkflowError("DEV volume ownership is ambiguous; recovery refused")
        return services

    def stop_dev(self) -> None:
        containers = self.containers()
        if not containers:
            print(f"{self.project}: already stopped; no containers or volumes changed")
            return
        services = self.dev_containers(containers)
        backend = services.get("backend")
        preserved_backend = ""
        if (
            backend
            and backend["State"].get("Running")
            and f"FLORABASE_ATTACHMENT_STORAGE_ROOT={LEGACY_MEDIA_ROOT}"
            in backend["Config"].get("Env", [])
        ):
            # Docker tmpfs is lost even on STOP. Freeze all backend writers, preserve media
            # through the existing durable mount, then kill without reopening a write window.
            identifier = str(backend["Id"])
            run(["docker", "pause", identifier])
            try:
                # Docker cp cannot see live tmpfs. A fixed helper shares only the paused
                # backend's PID namespace and the already-validated DEV media volume.
                program = "\n".join(
                    [
                        "import hashlib, os, shutil\nfrom pathlib import Path",
                        inspect.getsource(WorkflowError),
                        inspect.getsource(file_digest),
                        inspect.getsource(preserve_media),
                        f"preserve_media(Path('/proc/1/root{LEGACY_MEDIA_ROOT}'), Path('/state'))",
                    ]
                )
                run(
                    [
                        "docker",
                        "run",
                        "--rm",
                        "--network",
                        "none",
                        "--read-only",
                        "--pid",
                        f"container:{identifier}",
                        "--cap-drop",
                        "ALL",
                        "--cap-add",
                        "SYS_PTRACE",
                        "--cap-add",
                        "DAC_OVERRIDE",
                        "--mount",
                        f"type=volume,src={self.project}_attachment_data,dst=/state",
                        "--entrypoint",
                        "python",
                        "python:3.14.7-slim-bookworm",
                        "-c",
                        program,
                    ]
                )
                run(["docker", "kill", "--signal", "KILL", identifier])
                preserved_backend = identifier
            except BaseException:
                # A failed copy/check must leave the legacy writer and its original tmpfs alive.
                run(["docker", "unpause", identifier])
                raise
            print("Legacy DEV tmpfs media preserved in the existing DEV attachment volume.")
        for service in ("frontend", "backend", "dev-state-init", "db"):
            container = services.get(service)
            if container and container["State"].get("Running"):
                if str(container["Id"]) == preserved_backend:
                    continue
                run(["docker", "stop", str(container["Id"])])
        print(f"{self.project}: stopped; containers, networks and ALL volumes retained")
        print("Next: make dev-up (primary source; ahead/incompatible DB revisions refuse startup)")

    def require_durable_legacy_media(self) -> None:
        if self.role != "dev":
            return
        for container in self.containers():
            settings = container["Config"].get("Env", [])
            if (
                container["State"].get("Running")
                and "FLORABASE_ATTACHMENT_STORAGE_ROOT=/tmp/florabase-attachments" in settings
            ):
                populated = run(
                    [
                        "docker",
                        "exec",
                        str(container["Id"]),
                        "python",
                        "-c",
                        "from pathlib import Path; print(any(p.is_file() for p in Path('/tmp/florabase-attachments').rglob('*')))",
                    ],
                    capture=True,
                )
                if populated == "True":
                    raise WorkflowError(
                        f"legacy DEV media is in temporary storage in {container['Name']}; "
                        "run make dev-stop to preserve media before replacing DEV. "
                        "Do not recreate or remove the legacy container before preservation."
                    )

    def validate(self, *, require_durable_dev: bool = False) -> None:
        config = json.loads(self.compose("config", "--format", "json", capture=True))
        if config.get("name") != self.project:
            raise WorkflowError("unexpected Compose project")
        for kind in ("volumes", "networks"):
            for key, item in config.get(kind, {}).items():
                if item.get("external") or item.get("name") != f"{self.project}_{key}":
                    raise WorkflowError(f"{kind} {key} is not isolated by project {self.project}")
        services = config["services"]
        for service in ("backend", "frontend"):
            if Path(services[service]["build"]["context"]).resolve() != self.source / service:
                raise WorkflowError(f"wrong {service} source context")
        if self.role in {"review", "uat"}:
            if services["db"].get("ports") or services["backend"].get("ports"):
                raise WorkflowError("review database/backend must remain internal")
            ports = services["frontend"].get("ports", [])
            if (
                len(ports) != 1
                or ports[0].get("host_ip") != "127.0.0.1"
                or str(ports[0].get("published"))
                != (str(urlsplit(self.url).port) if self.role == "uat" else PORTS["review"])
            ):
                raise WorkflowError("review must publish only localhost:15174")
            db = services["db"]["environment"]
            backend = services["backend"]["environment"]
            if (
                db.get("POSTGRES_DB") != self.environment()["POSTGRES_DB"]
                or backend.get("FLORABASE_DATABASE_URL")
                != self.environment()["FLORABASE_DATABASE_URL"]
            ):
                raise WorkflowError("review database configuration is not isolated")
        if self.role == "dev":
            media = services["backend"]["environment"].get("FLORABASE_ATTACHMENT_STORAGE_ROOT")
            media_mounts = services["backend"].get("volumes", [])
            if require_durable_dev and (
                media != MEDIA_ROOT
                or not any(
                    item.get("type") == "volume"
                    and item.get("source") == "attachment_data"
                    and item.get("target") == MEDIA_ROOT
                    for item in media_mounts
                )
            ):
                raise WorkflowError(
                    "primary DEV configuration must use durable attachment storage; "
                    "update primary main with this workflow before starting recovered DEV"
                )
            db = services["db"]["environment"]
            database_url = urlsplit(services["backend"]["environment"]["FLORABASE_DATABASE_URL"])
            if (
                database_url.hostname != "db"
                or database_url.port not in {None, 5432}
                or unquote(database_url.path.lstrip("/")) != db["POSTGRES_DB"]
                or unquote(database_url.username or "") != db["POSTGRES_USER"]
            ):
                raise WorkflowError(
                    "DEV database URL must target this project's db service and matching POSTGRES_DB/USER; external or mismatched database configuration is refused"
                )
            port = services["frontend"]["ports"][0]["published"]
            self.url = f"http://localhost:{port}"

    def current(self) -> list[str]:
        query = "SELECT to_regclass('public.alembic_version');"
        prefix = 'psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --tuples-only --no-align --command '
        table = self.compose(
            "exec", "-T", "db", "sh", "-ec", prefix + '"' + query + '"', capture=True
        )
        if not table:
            return []
        raw = self.compose(
            "exec",
            "-T",
            "db",
            "sh",
            "-ec",
            prefix + '"SELECT version_num FROM alembic_version ORDER BY version_num;"',
            capture=True,
        )
        return raw.splitlines()

    def upgrade(self) -> None:
        graph = migration_graph(self.source)
        revisions = self.current()
        print(f"Database current: {','.join(revisions) or 'unversioned'}")
        print(f"Code head: {','.join(code_heads(graph))}")
        require_upgradeable(revisions, graph)
        self.compose("run", "--rm", "-T", "--no-deps", "backend", "alembic", "upgrade", "head")
        result = self.current()
        if result != code_heads(graph):
            raise WorkflowError("database did not reach this source's code head")
        print(f"Database current after upgrade: {','.join(result)}")

    def prepare_initializer(self, *services: str) -> str:
        # Frontend and initializer share this image. Always build the selected source,
        # even when a historical tag exists. Probe the rendered image directly so
        # preflight cannot mount or initialize persistent application volumes.
        self.compose("build", *services, "dev-state-init")
        config = json.loads(self.compose("config", "--format", "json", capture=True))
        image = config.get("services", {}).get("dev-state-init", {}).get("image")
        if not isinstance(image, str) or not image:
            raise WorkflowError(
                "DEV initializer image is missing from rendered Compose configuration"
            )
        run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--entrypoint",
                "sh",
                image,
                "-ec",
                'test -x "$(command -v florabase-dev-state-init)"',
            ],
            env=self.environment(),
        )
        return image

    def upgrade_state(self) -> None:
        self.validate(require_durable_dev=self.role == "dev")
        self.require_owner(allow_stopped_dev=self.role == "dev")
        self.require_durable_legacy_media()
        self.prepare_initializer("backend")
        self.start_database()
        self.upgrade()
        self.compose("run", "--rm", "-T", "--no-deps", "dev-state-init")

    def start_database(self) -> None:
        if self.role == "dev" and any(
            item["Config"].get("Labels", {}).get("com.docker.compose.service") == "db"
            for item in self.containers()
        ):
            # Read the preserved DB before any container rebinding. An ahead refusal must
            # retain coherent old-source metadata, so dev-stop remains usable afterward.
            self.compose("start", "--wait", "--wait-timeout", "120", "db")
        else:
            self.compose("up", "-d", "--wait", "--wait-timeout", "120", "db")

    def up(self) -> None:
        if self.role in {"review", "uat"}:
            self.repository.initialize()
        self.validate(require_durable_dev=self.role == "dev")
        self.require_owner(allow_stopped_dev=self.role == "dev")
        self.require_durable_legacy_media()
        self.compose("build")
        self.start_database()
        if self.role in {"review", "uat"}:
            self.compose("run", "--rm", "-T", "--no-deps", "dev-state-init")
            self.upgrade()
        else:
            require_upgradeable(self.current(), migration_graph(self.source))
            self.compose("run", "--rm", "-T", "--no-deps", "dev-state-init")
        self.compose("up", "-d", "--wait", "--wait-timeout", "180")
        print(f"{self.role.upper()} READY")
        self.status()

    def status(self) -> None:
        self.validate()
        identity = self.repo.identity()
        print(f"Environment: {self.role}")
        for key, value in identity.items():
            print(f"{key.title()}: {value}")
        print(
            f"Env source: {self.env_source} (isolated DB overrides)"
            if self.role == "review"
            else f"Env source: {self.env_source}"
        )
        print(
            f"Compose project: {self.project}\nURL: {self.url}\nDatabase volume: {self.project}_postgres_data\nMedia volume: {self.project}_attachment_data"
        )
        print(
            f"Dependencies volume: {self.project}_frontend_node_modules\nNetwork: {self.project}_internal"
        )
        containers = self.containers()
        owner_error: WorkflowError | None = None
        try:
            self.require_owner()
        except WorkflowError as error:
            owner_error = error
            print(f"SOURCE MISMATCH: {error}")
        db_running = False
        for container in containers:
            labels = container["Config"].get("Labels", {})
            service = labels.get("com.docker.compose.service", "unknown")
            state = container["State"]
            health = state.get("Status", "unknown")
            if state.get("Paused"):
                health = "paused"
            elif state.get("Running"):
                health = state.get("Health", {}).get("Status", health)
            print(f"{service}: {health}")
            running_source = labels.get("io.florabase.source") or labels.get(
                "com.docker.compose.project.working_dir"
            )
            if running_source:
                activity = "running" if state.get("Running") else "retained"
                print(f"{service} {activity} source: {running_source}")
            if service == "backend":
                for setting in container["Config"].get("Env", []):
                    if setting.startswith("FLORABASE_ATTACHMENT_STORAGE_ROOT="):
                        print(f"Running media root: {setting.split('=', 1)[1]}")
            if service == "frontend":
                print(
                    f"Container source: {labels.get('io.florabase.source', labels.get('com.docker.compose.project.working_dir'))}"
                )
                print(f"Launched HEAD: {labels.get('io.florabase.sha', 'unrecorded (legacy DEV)')}")
                print(
                    "DEV/Review source binds are live; current identity above includes edits since launch."
                )
            db_running |= service == "db" and state.get("Running", False)
        graph = migration_graph(self.source)
        print(f"Code head: {','.join(code_heads(graph))} (selected source above)")
        if db_running:
            revisions = self.current()
            print(f"Database current: {','.join(revisions) or 'unversioned'}")
            require_upgradeable(revisions, graph)
        else:
            print("Database current: unavailable (database stopped)")
        if owner_error:
            raise owner_error

    def stop(self, *, remove: bool = False, confirm: str = "") -> None:
        if remove and (self.role != "review" or confirm != REVIEW_PROJECT):
            raise WorkflowError(
                f"remove deletes ONLY review DB/media/dependencies; set CONFIRM_REMOVE_REVIEW={REVIEW_PROJECT}"
            )
        if self.role == "dev":
            self.stop_dev()
            return
        self.validate()
        self.require_owner()
        self.require_durable_legacy_media()
        if remove:
            print(
                f"Deleting {self.project}_postgres_data, {self.project}_attachment_data, {self.project}_frontend_node_modules and review containers/network"
            )
        self.compose("down", "--remove-orphans", *(["--volumes"] if remove else []))
        print(f"{self.project}: {'removed' if remove else 'stopped; all volumes preserved'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=["dev", "review", "quality", "prod", "init"])
    parser.add_argument("action", nargs="?", default="status")
    parser.add_argument("args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        repo = Repository(Path.cwd())
        if args.role == "init":
            repo.initialize(os.environ.get("BRANCH", ""))
            return 0
        env = Environment(repo, args.role)
        if args.action == "compose":
            command = args.args[1:] if args.args[:1] == ["--"] else args.args
            if not command or command[0].startswith("-"):
                raise WorkflowError(
                    "provide a Compose subcommand; project/files/config are fixed by role"
                )
            if (
                env.role == "review"
                and command[0] == "down"
                and any(item in command for item in ("-v", "--volumes"))
            ):
                raise WorkflowError("use feature-review-remove with its exact project confirmation")
            if env.role == "dev" and command[0] in {
                "up",
                "down",
                "start",
                "stop",
                "restart",
                "kill",
                "rm",
            }:
                raise WorkflowError(
                    "use make dev-up or make dev-stop; raw DEV lifecycle cleanup is refused"
                )
            if env.role in {"review", "dev"}:
                env.validate()
                env.require_owner()
                if env.role == "dev" and command[0] in {
                    "up",
                    "down",
                    "stop",
                    "restart",
                }:
                    env.require_durable_legacy_media()
            if env.role == "quality" and command[:1] == ["run"] and "frontend" in command:
                env.prepare_initializer()
                env.compose("run", "--rm", "-T", "--no-deps", "dev-state-init")
            env.compose(*command)
        elif args.action == "status":
            env.status()
        elif args.action == "up":
            env.up()
        elif args.action == "upgrade":
            env.upgrade_state()
        elif args.action in {"stop", "remove"}:
            env.stop(
                remove=args.action == "remove",
                confirm=os.environ.get("CONFIRM_REMOVE_REVIEW", ""),
            )
        else:
            raise WorkflowError(f"unsupported action: {args.action}")
    except (WorkflowError, ValueError, KeyError) as error:
        print(f"workflow: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
