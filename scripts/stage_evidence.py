#!/usr/bin/env python3
"""Reusable local stage evidence for the canonical gate: exact input closure, fail-closed reuse.

Only the Quality and PostgreSQL integration stages are candidates. A record is written to this
worktree's own Git metadata only after the stage exits 0 and none of its inputs changed while it
ran. Reuse recomputes every recorded input class from current state; anything unknown,
unprovable, corrupt or stale runs the stage fresh. BuildKit layers, the pnpm store and the
node_modules volume are caches, never evidence. Remote CI never reads or writes records.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import stat
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any

sys.dont_write_bytecode = True

SCHEMA = 1
KIND = "florabase-stage-evidence"
DIRECTORY = "florabase-stage-evidence"
MODES = ("off", "reuse", "dry-run", "fresh")
MAX_EVIDENCE_AGE = timedelta(hours=24)
SOURCE_LABELS = ("io.florabase.workflow.source", "io.florabase.source")
LIFECYCLE_LABEL = "io.florabase.workflow.lifecycle"
DIGEST_LIFECYCLE = "stage-evidence-digest"
DISPOSABLE_INTEGRATION = re.compile(r"florabase-integration-[0-9a-f]{12}")
# Launch controls and shell bookkeeping never reach a stage command's behaviour.
IGNORED_ENVIRONMENT = frozenset({"REUSE", "FRESH", "_", "OLDPWD", "PWD", "SHLVL"})
# Named volumes are mutable state, so each one is an input by content digest (before and after the
# stage, and again at reuse). The one exception is the dependency install target, which also holds
# tool caches: it is reinstalled from the bound lockfile, tied to the entrypoints that make it so.
# Both entrypoints ship in the ./frontend build context, which is part of the closure.
RECONCILED_VOLUMES = {
    "frontend_node_modules": {
        "florabase-dev-entrypoint": "reinstalled by pnpm install --frozen-lockfile",
        "florabase-dev-state-init": "ownership reset only",
    }
}
# Runs read-only, without network, in one of the stage's own built images.
VOLUME_DIGEST = """
import hashlib, json, os, stat, sys
def entry(path):
    info = os.lstat(path)
    if stat.S_ISLNK(info.st_mode):
        return ["link", os.readlink(path)]
    meta = [stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid]
    if stat.S_ISDIR(info.st_mode):
        return ["dir", *meta]
    if stat.S_ISREG(info.st_mode):
        with open(path, "rb") as stream:
            return ["file", *meta, hashlib.sha256(stream.read()).hexdigest()]
    sys.exit(3)
result = {}
for key in sys.argv[1:]:
    root = "/evidence/" + key
    entries = {".": entry(root)}
    for directory, _dirs, files in os.walk(root):
        for name in _dirs + files:
            path = os.path.join(directory, name)
            entries[os.path.relpath(path, root)] = entry(path)
    text = json.dumps(entries, sort_keys=True, separators=(",", ":"))
    result[key] = hashlib.sha256(text.encode()).hexdigest()
print(json.dumps(result))
"""
BUILD_KEYS = frozenset({"context", "dockerfile", "target", "args", "labels"})
UNCLASSIFIED_SERVICE_KEYS = ("configs", "secrets", "extends", "env_file", "devices")


class Unknown(Exception):
    """An input that cannot be proven; the stage must run fresh."""


# Named tuples keep these handlers valid on the host Python 3.12 that runs workflow suites in CI.
UNREADABLE = (Unknown, ValueError)
RECORD_ERRORS = (OSError, ValueError, AttributeError)
TIMESTAMP_ERRORS = (KeyError, OverflowError, TypeError, ValueError)


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def capture(*command: str, env: dict[str, str] | None = None) -> str:
    try:
        return subprocess.run(
            command,
            check=True,
            text=True,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            env=env,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise Unknown(f"command failed: {' '.join(command[:3])}") from error


def locate() -> tuple[Path, Path]:
    repo = Path(capture("git", "rev-parse", "--show-toplevel").strip()).resolve()
    return repo, Path(capture("git", "rev-parse", "--absolute-git-dir").strip())


def record_path(metadata: Path, stage: str) -> Path:
    if not re.fullmatch(r"[a-z][a-z0-9-]*", stage):
        raise Unknown(f"unsafe stage id: {stage}")
    return metadata / DIRECTORY / f"{stage}.json"


def entry(path: Path) -> list[Any]:
    """Type, mode, owner and content of one entry, never following symlinks."""
    try:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            return ["link", os.readlink(path)]
        meta = [stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid]
        if stat.S_ISDIR(info.st_mode):
            return ["dir", *meta]
        if stat.S_ISREG(info.st_mode):
            with path.open("rb") as stream:
                return ["file", *meta, hashlib.file_digest(stream, "sha256").hexdigest()]
    except OSError as error:
        raise Unknown(f"unreadable closure entry {path}: {error.strerror}") from error
    raise Unknown(f"unsupported file type in closure: {path}")


def tree_digest(
    repo: Path, relative: str, excluded: tuple[str, ...] = (), skip: frozenset[str] = frozenset()
) -> str:
    """Every entry Docker would expose at this source, including Git-ignored and untracked files."""
    start = repo / relative
    if not start.exists() and not start.is_symlink():
        return digest(["missing", relative])
    entries: dict[str, list[Any]] = {}
    pending = [start]
    while pending:
        path = pending.pop()
        name = path.relative_to(repo).as_posix()
        if name in excluded:
            continue
        entries[name] = entry(path)
        if entries[name][0] == "dir":
            try:
                children = sorted(os.scandir(path), key=lambda child: child.name)
            except OSError as error:
                raise Unknown(f"unreadable closure directory {name}") from error
            pending.extend(
                Path(child.path)
                for child in children
                if not (child.name in skip and child.is_dir(follow_symlinks=False))
            )
    return digest(entries)


def host_closure(repo: Path) -> dict[str, str]:
    """Host-side stage programs: the Makefile and Compose files at top level and every script.

    Host processes are not sandboxed, so every top-level file and the whole scripts tree count.
    CPython validates __pycache__ against its adjacent source, so it is not an input.
    """
    top = {
        child.name: entry(child)
        for child in sorted(repo.iterdir())
        if child.is_symlink() or not child.is_dir()
    }
    links = [repo / name for name in top if top[name][0] == "link"]
    for directory, _dirs, files in os.walk(repo / "scripts"):
        links += [Path(directory, f) for f in _dirs + files if Path(directory, f).is_symlink()]
    for link in links:
        try:
            target = link.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise Unknown(f"unresolvable host program symlink: {link.relative_to(repo)}") from error
        if not target.is_relative_to(repo):
            raise Unknown(f"host program symlink leaves the repository: {link.relative_to(repo)}")
        relative = target.relative_to(repo)
        hashed_script = relative.parts[:1] == ("scripts",) and "__pycache__" not in relative.parts
        hashed_top_file = len(relative.parts) == 1 and top.get(relative.name, [None])[0] == "file"
        if not target.is_file() or not (hashed_script or hashed_top_file):
            raise Unknown(
                f"host program symlink leaves the input closure: {link.relative_to(repo)}"
            )
    return {
        "scripts": tree_digest(repo, "scripts", skip=frozenset({"__pycache__"})),
        "top-level files": digest(top),
    }


def inside(repo: Path, source: str) -> str:
    path = Path(source)
    if not path.is_absolute():
        raise Unknown(f"relative mount source: {source}")
    try:
        return path.resolve().relative_to(repo).as_posix() or "."
    except ValueError as error:
        raise Unknown(f"mount source outside the repository: {source}") from error


def shadowed(target: str, targets: list[str], relative: str) -> tuple[str, ...]:
    """Source paths hidden inside the container by another mount below this target."""
    base = PurePosixPath(target)
    return tuple(
        sorted(
            f"{relative}/{PurePosixPath(other).relative_to(base).as_posix()}"
            for other in targets
            if PurePosixPath(other) != base and PurePosixPath(other).is_relative_to(base)
        )
    )


def root_key(relative: str, excluded: tuple[str, ...]) -> str:
    return relative + (f" (excluding {', '.join(excluded)})" if excluded else "")


def config(command: list[str], env: dict[str, str]) -> dict[str, Any]:
    """Render Compose exactly as the stage helper invokes it; labels are ownership metadata only."""
    try:
        model: dict[str, Any] = json.loads(capture(*command, "config", "--format", "json", env=env))
    except ValueError as error:
        raise Unknown("unparseable rendered Compose configuration") from error
    # Compose ignores top-level x-* extension fields; here they only carry label anchors such as
    # the commit SHA and dirty flag, which would otherwise invalidate evidence on every commit.
    model = {key: value for key, value in model.items() if not key.startswith("x-")}
    for section in ("services", "networks", "volumes"):
        for item in (model.get(section) or {}).values():
            if isinstance(item, dict):
                item.pop("labels", None)
                if isinstance(item.get("build"), dict):
                    item["build"].pop("labels", None)
    return model


def stage_models(stage: str, command: list[str], repo: Path) -> dict[str, dict[str, Any]]:
    """Each Docker model the stage's own helper uses, rendered from the current tree."""
    if stage == "quality" and command == ["make", "check"]:
        from workflow_environment import Environment, Repository

        environment = Environment(Repository(repo), "quality")
        return {
            "quality": {
                "model": config(environment.command(), environment.environment()),
                "env_file": str(environment.env_source),
                "persistent": True,
            }
        }
    full = command == ["make", "test-integration"]
    if stage == "integration" and (
        full or (command[:1] == ["./scripts/test-integration.sh"] and len(command) > 1)
    ):
        from disposable_workflow import compose_invocation, safe_suites
        from workflow_resources import Owner

        selected = [] if full else safe_suites(command[1:], repo)
        # A fixed placeholder owner: the real run differs only in labels and its image tag.
        owner = Owner("florabase-integration-" + "0" * 12, "integration", str(repo), "0" * 32)
        with tempfile.TemporaryDirectory(prefix="florabase-evidence-config-") as temporary:
            argv, env = compose_invocation("integration", repo, owner, selected, Path(temporary))
            model = config(argv, env)
        return {"integration": {"model": model, "env_file": "/dev/null", "persistent": False}}
    raise Unknown(f"{stage} with this command is not a reuse candidate")


def model_mounts(
    name: str, model: dict[str, Any], repo: Path
) -> dict[str, tuple[str, tuple[str, ...]]]:
    """Every bind source and build context of every service; unknown input kinds refuse."""
    if model.get("configs") or model.get("secrets"):
        raise Unknown(f"{name}: Compose configs/secrets are not classified inputs")
    mounts: dict[str, tuple[str, tuple[str, ...]]] = {}
    for service_name, service in (model.get("services") or {}).items():
        for key in UNCLASSIFIED_SERVICE_KEYS:
            if service.get(key):
                raise Unknown(f"{name}/{service_name}: {key} is not a classified input")
        volumes = service.get("volumes") or []
        targets = [m["target"] for m in volumes] + [
            t.split(":", 1)[0] for t in service.get("tmpfs") or []
        ]
        for mount in volumes:
            if mount.get("type") == "bind":
                relative = inside(repo, mount["source"])
                excluded = shadowed(mount["target"], targets, relative)
                mounts[root_key(relative, excluded)] = (relative, excluded)
            elif mount.get("type") not in {"volume", "tmpfs"}:
                raise Unknown(f"{name}/{service_name}: unclassified mount type")
        build = service.get("build")
        if build is not None:
            if not isinstance(build, dict) or set(build) - BUILD_KEYS:
                raise Unknown(f"{name}/{service_name}: unclassified build inputs")
            context = inside(repo, build["context"])
            mounts[root_key(context, ())] = (context, ())
            dockerfile = inside(
                repo, str(Path(build["context"]) / build.get("dockerfile", "Dockerfile"))
            )
            if context != "." and not PurePosixPath(dockerfile).is_relative_to(context):
                mounts[root_key(dockerfile, ())] = (dockerfile, ())
    return mounts


def environment_digests(salt: str) -> dict[str, str]:
    """Salted per-variable digests: changes are detectable, values are never stored."""
    values: dict[str, str] = {}
    for name, value in os.environ.items():
        if name in IGNORED_ENVIRONMENT:
            continue
        if name in {"MAKEFLAGS", "MFLAGS"}:
            words = [w for w in value.split() if not re.match(r"(REUSE|FRESH)=", w)]
            value = " ".join(words[:-1] if words[-1:] == ["--"] else words)
        values[name] = hmac.new(
            bytes.fromhex(salt), f"{name}={value}".encode(), "sha256"
        ).hexdigest()
    return values


def tools() -> dict[str, Any]:
    info = json.loads(capture("docker", "info", "--format", "{{json .}}"))
    return {
        "docker": json.loads(capture("docker", "version", "--format", "{{json .}}")),
        "daemon": {
            key: info.get(key)
            for key in (
                "ID",
                "Name",
                "ServerVersion",
                "Driver",
                "OperatingSystem",
                "KernelVersion",
                "Architecture",
                "CgroupVersion",
                "SecurityOptions",
            )
        },
        "compose": capture("docker", "compose", "version", "--short").strip(),
        "buildx": capture("docker", "buildx", "version").strip(),
        "python": sys.version,
        "git": capture("git", "--version").strip(),
        "make": version_line("make"),
    }


def version_line(program: str) -> str:
    lines = capture(program, "--version").splitlines()
    if not lines or not lines[0].strip():
        raise Unknown(f"{program} version is unavailable")
    return lines[0]


def inputs(
    stage: str, command: list[str], repo: Path, salt: str
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    models = stage_models(stage, command, repo)
    mounts: dict[str, tuple[str, tuple[str, ...]]] = {}
    for name, item in models.items():
        mounts.update(model_mounts(name, item["model"], repo))
    env_files: dict[str, str] = {}
    for name, item in models.items():
        try:
            env_files[name] = digest([item["env_file"], Path(item["env_file"]).read_bytes().hex()])
        except OSError as error:
            raise Unknown(f"unreadable env file for {name}") from error
    return {
        "compose": {name: digest(item["model"]) for name, item in models.items()},
        "mounts": {key: tree_digest(repo, *spec) for key, spec in sorted(mounts.items())},
        "policy": host_closure(repo),
        "environment": environment_digests(salt),
        "env_files": env_files,
        "volume_content": {
            key: value
            for name, item in models.items()
            for key, value in volume_digests(name, item).items()
        },
        "tools": tools(),
    }, models


def volume_name(model: dict[str, Any], key: str) -> str:
    return str(
        ((model.get("volumes") or {}).get(key) or {}).get("name") or f"{model['name']}_{key}"
    )


def volume_digests(name: str, item: dict[str, Any]) -> dict[str, str]:
    """Content of every named volume except the reconciled dependency target."""
    model = item["model"]
    keys = sorted(set(model.get("volumes") or {}) - set(RECONCILED_VOLUMES))
    if not keys:
        return {}
    if not item["persistent"]:
        raise Unknown(f"{name}: named volumes of a disposable project are not classified")
    existing = set(capture("docker", "volume", "ls", "-q").split())
    result = {f"{name}/{key}": "absent" for key in keys if volume_name(model, key) not in existing}
    present = [key for key in keys if volume_name(model, key) in existing]
    if not present:
        return result
    mounts = [a for k in present for a in ("-v", f"{volume_name(model, k)}:/evidence/{k}:ro")]
    images = sorted(
        str(s["image"]) for s in model["services"].values() if "build" in s and s.get("image")
    )
    for image in images:
        try:
            output = capture(
                "docker",
                "run",
                "--rm",
                "--label",
                f"{LIFECYCLE_LABEL}={DIGEST_LIFECYCLE}",
                "--network",
                "none",
                "--read-only",
                "--user",
                "0:0",
                *mounts,
                "--entrypoint",
                "python3",
                image,
                "-c",
                VOLUME_DIGEST,
                *present,
            )
            values = json.loads(output)
        except UNREADABLE:
            continue
        return result | {f"{name}/{key}": str(values[key]) for key in present}
    raise Unknown(f"{name}: named volume content cannot be digested")


def image_id(reference: str) -> str:
    """Content identity: layer diff IDs, platform and runtime config, without labels.

    With Docker's containerd image store every cached rebuild mints a new image ID, and Compose
    stamps per-service labels on images that share a tag; neither changes what a container runs.
    """
    try:
        details = json.loads(capture("docker", "image", "inspect", reference))[0]
        config = {k: v for k, v in (details.get("Config") or {}).items() if k != "Labels"}
        return digest([details["RootFS"], details.get("Architecture"), details.get("Os"), config])
    except (ValueError, KeyError, IndexError, TypeError) as error:
        raise Unknown(f"unreadable image identity: {reference}") from error


def require_pinned(repo: Path, build: dict[str, Any]) -> None:
    """A rebuilt disposable image is identified by its context only if every base is a digest."""
    path = Path(build["context"]) / build.get("dockerfile", "Dockerfile")
    name = inside(repo, str(path))
    aliases: set[str] = set()

    def pinned(reference: str) -> bool:
        return "@sha256:" in reference or reference in aliases

    source = path.read_text(encoding="utf-8-sig")
    if re.search(r"(?im)^[ \t]*#\s*escape\s*=", source):
        raise Unknown(f"unsupported Dockerfile escape directive in {name}")
    # Docker joins backslash continuations and ignores blank and comment lines within them.
    source = re.sub(r"\\[ \t]*\n(?:[ \t]*(?:#[^\n]*)?\n)*", "", source)
    for line in source.splitlines():
        line = line.lstrip()
        words = line.split()
        if re.match(r"#\s*syntax\s*=", line, re.IGNORECASE) and "@sha256:" not in line:
            raise Unknown(f"unpinned Dockerfile frontend in {name}")
        instruction = words[0].upper() if words else ""
        if instruction == "FROM":
            words = [w for w in words[1:] if not w.startswith("--")]
            if not pinned(words[0]):
                raise Unknown(f"unpinned base image in {name}: {words[0]}")
            if len(words) == 3 and words[1].upper() == "AS":
                aliases.add(words[2])
        # External sources reached by later instructions must be pinned too.
        for match in re.finditer(r"(?:--from=|[,=][ \t]*from=)([^\s,]+)", line):
            if instruction in {"COPY", "ADD", "RUN"} and not pinned(match.group(1)):
                raise Unknown(f"unpinned build source in {name}: {match.group(1)}")
        if instruction == "ADD" and re.search(r'[\s"\[](https?://|ssh://|git://|git@)', line):
            raise Unknown(f"remote ADD source in {name}")


class Observer:
    """Containers created for this worktree while a stage runs, inspected while they exist."""

    def __init__(self, repo: Path, images: set[str]) -> None:
        self.repo = repo
        self.images = images
        self.containers: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self.since = time.time_ns()
        self.process = subprocess.Popen(
            [
                "docker",
                "events",
                "--since",
                f"{self.since // 10**9}.{self.since % 10**9:09d}",
                "--format",
                "{{json .}}",
                "--filter",
                "type=container",
                "--filter",
                "event=create",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        self.thread = threading.Thread(target=self.read, daemon=True)
        self.thread.start()

    def read(self) -> None:
        assert self.process.stdout
        for line in self.process.stdout:
            try:
                event = json.loads(line)
                if int(event["timeNano"]) < self.since:
                    continue
                attributes = event["Actor"]["Attributes"]
                if not (
                    any(attributes.get(label) == str(self.repo) for label in SOURCE_LABELS)
                    or attributes.get("image") in self.images
                ):
                    continue
                if attributes.get(LIFECYCLE_LABEL) == DIGEST_LIFECYCLE:
                    continue  # a concurrent read-only volume digest, never part of a stage
                details = json.loads(capture("docker", "inspect", event["Actor"]["ID"]))[0]
                identity = image_id(details["Image"])  # while the container pins that image
                self.containers.append(
                    {"labels": attributes, "inspect": details, "image": identity}
                )
            except (ValueError, KeyError, TypeError, IndexError, Unknown) as error:
                self.errors.append(f"container not provable: {error}")

    def stop(self) -> list[str]:
        time.sleep(0.5)  # the daemon streams create events within milliseconds
        if self.process.poll() is not None:
            self.errors.append("docker events observer stopped while the stage ran")
        self.process.terminate()
        try:
            self.process.wait(5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.thread.join(5)
        if self.thread.is_alive():
            self.errors.append("docker events observer did not finish")
        return self.errors


def observed(
    models: dict[str, dict[str, Any]],
    containers: list[dict[str, Any]],
    repo: Path,
    mounts: dict[str, str],
) -> dict[str, Any]:
    """Classify what actually ran: model, service, mounts, volumes and exact image identity."""
    images: dict[str, str] = {}
    volumes: set[str] = set()
    seen: set[str] = set()
    for container in containers:
        labels, details = container["labels"], container["inspect"]
        project = labels.get("com.docker.compose.project")
        name = next(
            (
                model_name
                for model_name, item in models.items()
                if (item["persistent"] and project == item["model"].get("name"))
                or (
                    not item["persistent"]
                    and project
                    and DISPOSABLE_INTEGRATION.fullmatch(project)
                    and labels.get("io.florabase.workflow.lifecycle") == "integration"
                )
                or (
                    project is None
                    and item["persistent"]
                    and labels.get("image")
                    in {s.get("image") for s in item["model"]["services"].values() if "build" in s}
                )
            ),
            None,
        )
        if name is None:
            raise Unknown(f"container outside the stage's Compose models: {labels.get('name')}")
        item = models[name]
        service_name = labels.get("com.docker.compose.service")
        service = item["model"]["services"].get(service_name) if service_name else None
        if service_name and service is None:
            raise Unknown(f"service outside the rendered model: {name}/{service_name}")
        seen.add(f"{name}/{service_name or 'image ' + str(labels.get('image'))}")
        mount_list = details.get("Mounts") or []
        targets = [m["Destination"] for m in mount_list] + list(
            (details.get("HostConfig") or {}).get("Tmpfs") or {}
        )
        entrypoint = ((details.get("Config") or {}).get("Entrypoint") or [""])[0]
        for mount in mount_list:
            if mount["Type"] == "bind":
                relative = inside(repo, mount["Source"])
                key = root_key(relative, shadowed(mount["Destination"], targets, relative))
                if key not in mounts:
                    raise Unknown(f"bind mount not derivable from Compose configuration: {key}")
            elif mount["Type"] == "volume":
                volume = str(mount.get("Name", ""))
                volume_key = next(
                    (
                        k
                        for k in item["model"].get("volumes") or {}
                        if item["persistent"] and volume_name(item["model"], k) == volume
                    ),
                    None,
                )
                reason = (
                    RECONCILED_VOLUMES[volume_key].get(entrypoint)
                    if volume_key in RECONCILED_VOLUMES
                    else "content digest"
                    if volume_key
                    else None
                )
                if not reason:
                    raise Unknown(f"unclassified mutable volume at {mount['Destination']}")
                volumes.add(f"{name}/{service_name}: {volume_key} ({reason})")
            elif mount["Type"] != "tmpfs":
                raise Unknown(f"unclassified {mount['Type']} mount at {mount['Destination']}")
        reference = str(labels.get("image", ""))
        if service is not None and "build" in service and not item["persistent"]:
            require_pinned(repo, service["build"])
            images[f"built {name}/{service_name}"] = "rebuilt from the pinned build context"
        else:
            if images.setdefault(reference, container["image"]) != container["image"]:
                raise Unknown(f"image {reference} changed while the stage ran")
    missing = [n for n in models if not any(s.startswith(n + "/") for s in seen)]
    if missing:
        raise Unknown(f"no container observed for {', '.join(missing)}")
    return {"images": images, "volumes": sorted(volumes), "containers": sorted(seen)}


def changes(recorded: dict[str, Any], current: dict[str, Any]) -> list[str]:
    reasons = []
    for name in sorted(recorded.keys() | current.keys()):
        old, new = recorded.get(name), current.get(name)
        if old == new:
            continue
        if isinstance(old, dict) and isinstance(new, dict):
            keys = sorted(k for k in old.keys() | new.keys() if old.get(k) != new.get(k))
            reasons.append(f"{name}: {', '.join(keys)}")
        else:
            reasons.append(name)
    return reasons


def write_record(path: Path, body: dict[str, Any]) -> None:
    """Atomic and durable: a crash leaves the previous state or the complete new record."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(
                json.dumps({**body, "digest": digest(body)}, sort_keys=True, indent=1) + "\n"
            )
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    sync_directory(path.parent)


def sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def remove_record(path: Path) -> None:
    path.unlink(missing_ok=True)
    if path.parent.is_dir():
        sync_directory(path.parent)


def evidence_age_issue(started_at: datetime, finished_at: datetime) -> str | None:
    now = datetime.now(UTC)
    if max(started_at, finished_at) > now:
        return "record has a future-dated timestamp"
    if now - finished_at > MAX_EVIDENCE_AGE:
        return "record expired: completion is older than 24 hours (UTC)"
    return None


def evaluate(stage: str, command: list[str]) -> tuple[str, str, dict[str, str] | None]:
    """Decision, reason and the reused_from reference; every doubt means a fresh run."""
    try:
        repo, metadata = locate()
        path = record_path(metadata, stage)
    except Unknown as error:
        return "unknown", str(error), None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        body = {key: value for key, value in record.items() if key != "digest"}
        intact = record.get("digest") == digest(body)
    except FileNotFoundError:
        return "miss", "no record", None
    except RECORD_ERRORS:
        return "corrupt", "unreadable or truncated record", None
    if not intact:
        return "corrupt", "record digest mismatch", None
    if record.get("kind") != KIND or record.get("schema") != SCHEMA:
        return "schema", f"unsupported evidence schema {record.get('schema')!r}", None
    if record.get("worktree") != str(metadata):
        return "invalidated", "record belongs to another worktree", None
    if record.get("stage") != stage or record.get("command") != command:
        return "invalidated", "stage command changed", None
    try:
        started_at = datetime.fromisoformat(record["started_at"])
        finished_at = datetime.fromisoformat(record["finished_at"])
        if started_at.tzinfo is None or finished_at.tzinfo is None:
            raise ValueError("timestamp needs an offset")
        started_at, finished_at = (
            started_at.astimezone(UTC),
            finished_at.astimezone(UTC),
        )
    except TIMESTAMP_ERRORS:
        return (
            "invalidated",
            "record has a missing or malformed timestamp (UTC offset required)",
            None,
        )
    if issue := evidence_age_issue(started_at, finished_at):
        return "invalidated", issue, None
    if started_at > finished_at:
        return "invalidated", "record starts after its completion", None
    try:
        manifest = record["manifest"]
        if record["result"] != "passed" or record["exit_code"] != 0:
            return "corrupt", "record is not a passed execution", None
        if record["key"] != digest([SCHEMA, stage, command, str(metadata), manifest]):
            return "corrupt", "record key mismatch", None
        current, _models = inputs(stage, command, repo, record["salt"])
        current["images"] = {
            ref: value if ref.startswith("built ") else image_id(ref)
            for ref, value in manifest["images"].items()
        }
        # Observation-only classes follow from the classes above, which select every container.
        current["volumes"], current["containers"] = (
            manifest["volumes"],
            manifest["containers"],
        )
        reused = {
            "run_id": record["run_id"],
            "key": record["key"],
            "finished_at": record["finished_at"],
        }
    except Exception as error:  # any doubt, including helper failures, runs the stage fresh
        return "unknown", str(error) or type(error).__name__, None
    reasons = changes(manifest, current)
    if reasons:
        return "invalidated", "; ".join(reasons), None
    if issue := evidence_age_issue(started_at, finished_at):
        return "invalidated", issue, None
    return "reuse", "", reused


def decide(check: dict[str, Any], mode: str) -> dict[str, str] | None:
    """Report the reuse decision; return reused_from only when this run may skip the stage."""
    stage = check["id"]
    if mode == "fresh":
        print(f"stage evidence: {stage} runs fresh: fresh requested (FRESH=1)", flush=True)
        return None
    decision, reason, reused = evaluate(stage, check["command"])
    label = "stage evidence (dry-run)" if mode == "dry-run" else "stage evidence"
    if decision == "reuse" and reused:
        verb = "would be reused" if mode == "dry-run" else "reused"
        print(
            f"{label}: {stage} {verb} from run {reused['run_id']} "
            f"(finished {reused['finished_at']}, key {reused['key'][:12]})",
            flush=True,
        )
        return reused if mode == "reuse" else None
    print(f"{label}: {stage} runs fresh: {decision}: {reason}", flush=True)
    return None


class Recording:
    """Capture one fresh execution; any stale record for the stage is gone before it starts."""

    def __init__(self, check: dict[str, Any]) -> None:
        self.stage, self.command = check["id"], check["command"]
        self.repo, self.metadata = locate()
        self.path = record_path(self.metadata, self.stage)
        remove_record(self.path)
        self.salt = secrets.token_hex(16)
        self.started_at = datetime.now(UTC).isoformat()
        self.before, self.models = inputs(self.stage, self.command, self.repo, self.salt)
        persistent_images = {
            str(service["image"])
            for item in self.models.values()
            if item["persistent"]
            for service in item["model"]["services"].values()
            if "build" in service and service.get("image")
        }
        self.observer = Observer(self.repo, persistent_images)

    def abort(self) -> None:
        self.observer.stop()

    def finish(self) -> str:
        errors = self.observer.stop()
        if errors:
            raise Unknown(errors[0])
        after, models = inputs(self.stage, self.command, self.repo, self.salt)
        if after != self.before or models != self.models:
            reasons = changes(self.before, after) or ["compose"]
            raise Unknown("inputs changed while the stage ran: " + "; ".join(reasons))
        seen = observed(self.models, self.observer.containers, self.repo, after["mounts"])
        for reference, value in seen["images"].items():
            if not reference.startswith("built ") and image_id(reference) != value:
                raise Unknown(f"image {reference} was replaced after the stage used it")
        manifest = {**after, **seen}
        key = digest([SCHEMA, self.stage, self.command, str(self.metadata), manifest])
        write_record(
            self.path,
            {
                "kind": KIND,
                "schema": SCHEMA,
                "stage": self.stage,
                "command": self.command,
                "worktree": str(self.metadata),
                "key": key,
                "manifest": manifest,
                "salt": self.salt,
                "result": "passed",
                "exit_code": 0,
                "run_id": uuid.uuid4().hex,
                "started_at": self.started_at,
                "finished_at": datetime.now(UTC).isoformat(),
            },
        )
        return key


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    from verification_gate import REUSABLE_STAGES, checks_for
    from verification_impact import make_plan

    plan = make_plan(args.base, force_full=args.full)
    candidates = [c for c in checks_for(plan) if c["id"] in REUSABLE_STAGES]
    if not candidates:
        print("stage evidence (dry-run): no reusable stage in this plan")
    for check in candidates:
        decide(check, "dry-run")


if __name__ == "__main__":
    main()
