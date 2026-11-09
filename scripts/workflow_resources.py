#!/usr/bin/env python3
"""Positive ownership and exact lifecycle retirement for Florabase Docker resources."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import pwd
import re
import signal
import subprocess
import sys
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import FrameType
from typing import IO, Any, cast

PROJECT_LABEL = "com.docker.compose.project"
OWNER_LABEL = "io.florabase.workflow.owner"
SOURCE_LABEL = "io.florabase.workflow.source"
ROLE_LABEL = "io.florabase.workflow.lifecycle"
QUALITY_VOLUMES = {"postgres_data", "attachment_data", "frontend_node_modules"}


class ResourceError(RuntimeError):
    pass


def docker(*args: str) -> str:
    try:
        return subprocess.run(
            ["docker", *args], check=True, text=True, stdout=subprocess.PIPE
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ResourceError(
            f"Docker command failed: docker {' '.join(args)}; run make workflow-resources (address pools/disk/cache/volume capacity may require exact-project recovery)"
        ) from error


class FileLock(AbstractContextManager["FileLock"]):
    """Non-blocking advisory lock; the kernel releases it on crash, SIGKILL or normal exit.

    Python descriptors are not inherited, so a surviving child can never keep a dead owner's lock.
    The file's holder text is diagnostics only and is never used to decide ownership.
    """

    def __init__(self, path: Path, purpose: str) -> None:
        self.path = path
        self.purpose = purpose
        self.handle: IO[str] | None = None

    def __enter__(self) -> FileLock:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            handle = self.path.open("a+", encoding="utf-8")
        except OSError as error:
            raise ResourceError(f"cannot open lock {self.path}: {error}") from error
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            handle.seek(0)
            holder = handle.read().strip() or "another process"
            handle.close()
            raise ResourceError(
                f"{self.purpose} is already running ({holder}); wait for it and retry"
            ) from error
        handle.truncate(0)
        identity = {
            "pid": os.getpid(),
            # Shared capacity locks have several kinds of holder; name this one for the loser.
            "purpose": self.purpose,
            "source": str(Path.cwd()),
            "started_at": datetime.now(UTC).isoformat(),
        }
        handle.write(json.dumps(identity, sort_keys=True))
        handle.flush()
        self.handle = handle
        return self

    def __exit__(self, *exception: object) -> None:
        if self.handle:
            self.handle.truncate(0)
            self.handle.close()
            self.handle = None


def machine_lock(name: str, purpose: str) -> FileLock:
    """Coordinate every checkout and clone of this user; Git metadata would miss separate clones."""
    configured = os.environ.get("FLORABASE_LOCK_DIR")
    # The account's home, not $HOME/XDG: sandboxed tool launches must still share one lock.
    home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    root = Path(configured) if configured else home / ".local/state/florabase/locks"
    return FileLock(root / f"{name}.lock", purpose)


def verification_lock(metadata: Path) -> FileLock:
    return FileLock(metadata / "florabase-verification.lock", "verification of this worktree")


@dataclass(frozen=True)
class Owner:
    project: str
    role: str
    source: str
    identity: str

    @classmethod
    def quality(cls, source: Path, metadata: Path) -> Owner:
        identity = str(metadata.resolve())
        suffix = hashlib.sha256(identity.encode()).hexdigest()[:12]
        return cls(f"florabase-quality-{suffix}", "quality", str(source.resolve()), identity)

    @classmethod
    def disposable(cls, role: str, source: Path) -> Owner:
        if role not in {"integration", "feature-migration", "verification-build", "workflow-smoke"}:
            raise ResourceError("unsupported disposable lifecycle")
        identity = uuid.uuid4().hex
        return cls(f"florabase-{role}-{identity[:12]}", role, str(source.resolve()), identity)

    @classmethod
    def smoke_fixture(cls, project: str, source: Path) -> Owner:
        owner = cls(project, "workflow-smoke", str(source.resolve()), uuid.uuid4().hex)
        owner.validate()
        return owner

    def labels(self) -> dict[str, str]:
        return {
            PROJECT_LABEL: self.project,
            OWNER_LABEL: self.identity,
            SOURCE_LABEL: self.source,
            ROLE_LABEL: self.role,
        }

    def validate(self) -> None:
        if self.role == "quality":
            expected = Owner.quality(Path(self.source), Path(self.identity))
            if expected != self:
                raise ResourceError("quality identity does not match exact worktree metadata")
        elif self.role in {
            "integration",
            "feature-migration",
            "verification-build",
            "workflow-smoke",
        }:
            safe_smoke = self.role == "workflow-smoke" and re.fullmatch(
                r"florabase-(?:dev-recovery-smoke|dev-upgrade-smoke|preview-smoke|feature-review-smoke|uat-preview-smoke|uat-branch-smoke)-[a-f0-9]{12}",
                self.project,
            )
            if not re.fullmatch(r"[a-f0-9]{32}", self.identity) or (
                self.project != f"florabase-{self.role}-{self.identity[:12]}" and not safe_smoke
            ):
                raise ResourceError("invalid disposable run identity")
        else:
            raise ResourceError("persistent/unknown environments cannot use automatic retirement")
        if not Path(self.source).is_absolute():
            raise ResourceError("source must be absolute")


class Resources:
    def __init__(self, owner: Owner, command: Callable[..., str] = docker) -> None:
        owner.validate()
        self.owner = owner
        self.command = command

    def inventory(self) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {}
        for kind, listing, _inspection in (
            ("containers", ["ps", "-aq", "--no-trunc"], ["inspect"]),
            ("networks", ["network", "ls", "-q"], ["network", "inspect"]),
            ("volumes", ["volume", "ls", "-q"], ["volume", "inspect"]),
            ("images", ["image", "ls", "-q"], ["image", "inspect"]),
        ):
            label = PROJECT_LABEL if kind != "images" else OWNER_LABEL
            value = self.owner.project if kind != "images" else self.owner.identity
            identifiers = sorted(
                set(self.command(*listing, "--filter", f"label={label}={value}").splitlines())
            )
            result[kind] = []
            for identifier in identifiers:
                item = self.inspect_present(kind, identifier)
                if item is not None:
                    result[kind].append(item)
        return result

    def inspect_present(self, kind: str, identifier: str) -> dict[str, Any] | None:
        inspection = ["inspect"] if kind == "containers" else [kind[:-1], "inspect"]
        try:
            items = json.loads(self.command(*inspection, identifier))
            if items:
                return cast(dict[str, Any], items[0])
        except ResourceError:
            if kind != "containers":
                raise
        if kind != "containers":
            raise ResourceError("missing resource inspection evidence")
        # Only a successful fresh all-container inventory proves disappearance.
        if any(
            full == identifier or full.startswith(identifier)
            for full in self.command("ps", "-aq", "--no-trunc").splitlines()
        ):
            raise ResourceError("container remains but inspection failed; refusing cleanup")
        return None

    @staticmethod
    def labels(item: dict[str, Any], kind: str) -> dict[str, str]:
        return cast(
            dict[str, str],
            (item.get("Config", {}) if kind in {"containers", "images"} else item).get("Labels")
            or {},
        )

    def prove(self, item: dict[str, Any], kind: str) -> None:
        labels = self.labels(item, kind)
        if all(labels.get(k) == v for k, v in self.owner.labels().items()):
            return
        # Established QUALITY has a deterministic project derived from this exact Git metadata
        # path. Legacy Compose labels prove its networks/known volumes; containers also prove source.
        if (
            self.owner.role == "quality"
            and labels.get(PROJECT_LABEL) == self.owner.project
            and not labels.get(OWNER_LABEL)
        ):
            if (
                kind == "containers"
                and (
                    labels.get("io.florabase.source")
                    or labels.get("com.docker.compose.project.working_dir")
                )
                == self.owner.source
                and labels.get("io.florabase.role") == "quality"
            ):
                return
            if (
                kind == "networks"
                and labels.get("com.docker.compose.network") == "internal"
                and item.get("Name") == f"{self.owner.project}_internal"
            ):
                return
            if (
                kind == "volumes"
                and labels.get("com.docker.compose.volume") in QUALITY_VOLUMES
                and item.get("Name")
                == f"{self.owner.project}_{labels['com.docker.compose.volume']}"
            ):
                return
        raise ResourceError(
            f"ownership unproved for {kind} {item.get('Name', item.get('Id', 'unknown'))}; nothing deleted; run make workflow-resources"
        )

    def users(self, filter_name: str, value: str) -> set[str]:
        return set(
            self.command(
                "ps", "-aq", "--no-trunc", "--filter", f"{filter_name}={value}"
            ).splitlines()
        )

    def preflight(self, inventory: dict[str, list[dict[str, Any]]]) -> None:
        owned = {str(item["Id"]) for item in inventory["containers"]}
        for kind, items in inventory.items():
            for item in items:
                self.prove(item, kind)
                if kind in {"volumes", "networks"}:
                    users = self.users(
                        "volume" if kind == "volumes" else "network", str(item["Name"])
                    )
                    if users - owned:
                        raise ResourceError(
                            f"foreign container uses {kind} {item['Name']}; cleanup refused before mutation"
                        )

    def clean(self) -> dict[str, int]:
        inventory = self.inventory()
        self.preflight(inventory)
        counts: dict[str, int] = {}
        for kind, remove in (
            ("containers", ["rm", "-f"]),
            ("networks", ["network", "rm"]),
            ("volumes", ["volume", "rm"]),
        ):
            counts[kind] = 0
            for item in inventory[kind]:
                # Reinspect ownership immediately before each removal; never remove by prefix.
                identifier = str(item["Id"] if kind != "volumes" else item["Name"])
                current = self.inspect_present(kind, identifier)
                if current is None:
                    continue
                self.prove(current, kind)
                if kind in {"volumes", "networks"} and self.users(
                    "volume" if kind == "volumes" else "network", str(current["Name"])
                ):
                    raise ResourceError(
                        f"resource acquired a container user: {identifier}; cleanup stopped"
                    )
                self.command(*remove, identifier)
                counts[kind] += 1
        counts["images"] = 0
        retained: list[str] = []
        for item in inventory["images"]:
            identifier = str(item["Id"])
            current = json.loads(self.command("image", "inspect", identifier))[0]
            self.prove(current, "images")
            tags = current.get("RepoTags") or []
            if (
                len(tags) > 1
                or self.users("ancestor", identifier)
                or any(not tag.startswith(self.owner.project + "-") for tag in tags)
            ):
                retained.append(identifier)
                continue
            # No force: Docker refuses any concurrent use. Keep shared/base/cache objects.
            self.command("image", "rm", identifier)
            counts["images"] += 1
        remaining = self.inventory()
        if any(remaining[kind] for kind in ("containers", "networks", "volumes")):
            raise ResourceError(
                f"owned resources remain in {self.owner.project}; cleanup failed; run make workflow-resources"
            )
        print(
            f"RESOURCE_CLEANUP_PASSED project={self.owner.project} removed={json.dumps(counts, sort_keys=True)} residual_containers_networks_volumes=0 retained_images={len(retained)} shared_build_cache=retained"
        )
        return counts


class Disposable(AbstractContextManager["Disposable"]):
    """Register before the first resource creation; caught INT/TERM unwind through cleanup."""

    def __init__(self, owner: Owner, command: Callable[..., str] = docker) -> None:
        self.owner = owner
        self.quiescence_failed = False
        self.resources = Resources(owner, command)
        self.handlers: dict[signal.Signals, Any] = {}

    def __enter__(self) -> Disposable:
        if any(self.resources.inventory().values()):
            raise ResourceError(
                f"new run already has resources: {self.owner.project}; refusing adoption"
            )
        for number in (signal.SIGINT, signal.SIGTERM):
            self.handlers[number] = signal.signal(number, self.interrupt)
        print(
            f"Cleanup registered: {self.owner.project} owner={self.owner.identity} source={self.owner.source}",
            flush=True,
        )
        return self

    def run(
        self, command: list[str], *, stdin: str | None = None, env: dict[str, str] | None = None
    ) -> str:
        """Quiesce the complete Compose process group before resource cleanup."""
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            env=env,
            start_new_session=True,
        )
        try:
            output, _ = process.communicate(stdin)
        except BaseException:
            self.quiescence_failed = True
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.communicate(timeout=30)
            except subprocess.TimeoutExpired as error:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate(timeout=5)
                self.quiescence_failed = True
                raise ResourceError(
                    "owned command shutdown timed out; cleanup refused; recover exact run after checking creators"
                ) from error
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                self.quiescence_failed = False
            else:
                raise ResourceError(
                    "owned process group still exists; cleanup refused until manual recovery"
                )
            raise
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, command)
        return output.strip()

    @staticmethod
    def interrupt(number: int, _frame: FrameType | None) -> None:
        raise SystemExit(128 + number)

    def __exit__(self, *exception: object) -> None:
        try:
            for number in self.handlers:
                signal.signal(number, signal.SIG_IGN)
            if self.quiescence_failed:
                raise ResourceError(
                    "cleanup requires manual recovery after owned subprocess shutdown failure"
                )
            self.resources.clean()
        finally:
            for number, handler in self.handlers.items():
                signal.signal(number, handler)


def report() -> dict[str, Any]:
    """List labels first; inspect only known/Florabase-labelled resource identities."""
    known = {
        "florabase": "DEV",
        "florabase-prod": "Production",
        "florabase-preview": "Stable Preview",
        "florabase-feature-review": "Feature Review",
        "florabase-uat-preview": "UAT Preview",
    }
    projects: dict[str, Any] = {}
    observed_projects = set(known)
    for kind, listing, inspection in (
        ("containers", ["ps", "-a"], ["inspect"]),
        ("networks", ["network", "ls"], ["network", "inspect"]),
        ("volumes", ["volume", "ls"], ["volume", "inspect"]),
        ("images", ["image", "ls"], ["image", "inspect"]),
    ):
        identifiers: set[str] = set()
        if kind != "images":
            raw = docker(*listing, "--filter", f"label={PROJECT_LABEL}", "--format", "{{json .}}")
            for line in raw.splitlines():
                summary = json.loads(line)
                labels = dict(
                    value.split("=", 1)
                    for value in summary.get("Labels", "").split(",")
                    if "=" in value
                )
                project = labels.get(PROJECT_LABEL, "")
                if project in known or project.startswith("florabase-"):
                    observed_projects.add(project)
                    identifiers.add(str(summary.get("ID") or summary["Name"]))
        else:
            # Legacy orphan outputs may have no remaining containers/networks. Listing their
            # Compose label plus Florabase tag identifies candidates for reporting only.
            raw = docker(*listing, "--filter", f"label={PROJECT_LABEL}", "--format", "{{json .}}")
            for line in raw.splitlines():
                summary = json.loads(line)
                if str(summary.get("Repository", "")).startswith("florabase-"):
                    identifiers.add(str(summary["ID"]))
            for project in sorted(observed_projects):
                identifiers.update(
                    docker(
                        *listing, "-q", "--filter", f"label={PROJECT_LABEL}={project}"
                    ).splitlines()
                )
        for label in (OWNER_LABEL, SOURCE_LABEL, "io.florabase.source"):
            identifiers.update(docker(*listing, "-q", "--filter", f"label={label}").splitlines())
        for identifier in sorted(identifiers):
            item = json.loads(docker(*inspection, identifier))[0]
            labels = Resources.labels(item, kind)
            project = labels.get(PROJECT_LABEL, "")
            group = known.get(
                project,
                labels.get(ROLE_LABEL)
                or (
                    "Quality (legacy)"
                    if project.startswith("florabase-quality-")
                    else "UAT instance"
                    if project.startswith("florabase-uat-branch-")
                    else "Unknown Florabase-labelled resources"
                ),
            )
            record = projects.setdefault(
                project or "unknown",
                {
                    "environment": group,
                    "source": set(),
                    "containers": [],
                    "networks": [],
                    "volumes": [],
                    "images": [],
                },
            )
            source = (
                labels.get(SOURCE_LABEL)
                or labels.get("io.florabase.source")
                or labels.get("com.docker.compose.project.working_dir")
            )
            if source:
                record["source"].add(source)
            summary = {
                "id": item.get("Id", item.get("Name")),
                "name": item.get("Name", item.get("RepoTags")),
                "status": item.get("State", {}).get("Status"),
            }
            if summary not in record[kind]:
                record[kind].append(summary)
    for record in projects.values():
        record["source"] = sorted(record["source"])
    return {
        "projects": dict(sorted(projects.items())),
        "build_cache": "shared default builder: retained; no safe per-project ownership",
        "unknown_policy": "report only",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=["report", "quality-status", "quality-clean", "cleanup-disposable"]
    )
    parser.add_argument("--project")
    parser.add_argument("--role")
    parser.add_argument("--owner")
    parser.add_argument("--source", help="exact recorded source label; need not still exist")
    args = parser.parse_args()
    try:
        from workflow_environment import Repository

        repo = Repository(Path.cwd())
        if args.action == "report":
            print(json.dumps(report(), indent=2, sort_keys=True))
        elif args.action.startswith("quality-"):
            owner = Owner.quality(repo.source, repo.metadata)
            if args.action == "quality-clean":
                Resources(owner).clean()
            else:
                inv = Resources(owner).inventory()
                print(
                    json.dumps(
                        {
                            "project": owner.project,
                            "source": owner.source,
                            "metadata": owner.identity,
                            "resources": {k: len(v) for k, v in inv.items()},
                        },
                        sort_keys=True,
                        indent=2,
                    )
                )
        else:
            if args.role not in {
                "integration",
                "feature-migration",
                "verification-build",
                "workflow-smoke",
            }:
                raise ResourceError(
                    "recovery cannot target Quality or persistent environments; use make quality-clean in its exact owning worktree"
                )
            if not args.project or not args.role or not args.owner:
                raise ResourceError(
                    "recovery requires exact --project, --role and --owner from the failed run"
                )
            Resources(
                Owner(args.project, args.role, args.source or str(repo.source), args.owner)
            ).clean()
    except ResourceError as error:
        print(f"RESOURCE_CLEANUP_FAILED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
