#!/usr/bin/env python3
"""Report and explicitly retire proven leftovers, one exact project at a time."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, cast

from workflow_resources import (
    OWNER_LABEL,
    PROJECT_LABEL,
    ROLE_LABEL,
    SOURCE_LABEL,
    FileLock,
    Owner,
    ResourceError,
    Resources,
    docker,
    inventory_identity,
    lock_root,
    machine_lock,
    report,
    verification_lock,
)

EXPECTED_ERRORS = (ResourceError, OSError, ValueError, KeyError)


def local_daemon() -> None:
    if os.environ.get("DOCKER_HOST") or os.environ.get("DOCKER_CONTEXT"):
        raise ResourceError("explicit Docker host/context cannot prove local source paths")
    context = docker("context", "show")
    details = json.loads(docker("context", "inspect", context))
    if (
        len(details) != 1
        or details[0].get("Endpoints", {}).get("docker", {}).get("Host")
        != "unix:///var/run/docker.sock"
    ):
        raise ResourceError("orphan proof requires the local Docker socket")


def source_finished(source: str, metadata: str = "") -> bool:
    path = Path(source)
    if not path.is_absolute():
        return False
    try:
        path.stat()
    except FileNotFoundError:
        # A surviving registration, claim or metadata cannot be dismissed as an orphan.
        if metadata:
            try:
                Path(metadata).stat()
                return False
            except FileNotFoundError:
                pass
        from workflow_environment import Repository

        try:
            repo = Repository(Path.cwd())
            worktrees = repo.git("worktree", "list", "--porcelain", "-z").split("\0")
            return f"worktree {source}" not in worktrees
        except Exception:
            return False
    try:
        from feature_worktree import AgentState, require_clean_finished_proof
        from workflow_environment import Repository

        repo = Repository(path)
        current = Repository(Path.cwd())
        if (
            repo.source.resolve() != path.resolve()
            or repo.common.resolve() != current.common.resolve()
        ):
            return False
        if metadata and str(repo.metadata.resolve()) != metadata:
            return False
        state = AgentState(repo).load()
        if state["writer"] is not None or state["handoff"] is not None:
            return False
        require_clean_finished_proof(repo, path)
        return True
    except Exception:
        return False


def inspect_project(project: str) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for kind, listing, inspect in (
        ("containers", ("ps", "-aq", "--no-trunc"), ("inspect",)),
        ("networks", ("network", "ls", "-q"), ("network", "inspect")),
        ("volumes", ("volume", "ls", "-q"), ("volume", "inspect")),
        ("images", ("image", "ls", "-q"), ("image", "inspect")),
    ):
        ids = sorted(
            set(docker(*listing, "--filter", f"label={PROJECT_LABEL}={project}").splitlines())
        )
        result[kind] = [json.loads(docker(*inspect, identifier))[0] for identifier in ids]
    return result


def candidate(project: str) -> dict[str, Any]:
    inventory = inspect_project(project)
    items = [(kind, item) for kind, group in inventory.items() for item in group]
    if not items:
        raise ResourceError("project has no remaining resources")
    labels = [Resources.labels(item, kind) for kind, item in items]
    sources = {label.get(SOURCE_LABEL, "") for label in labels if label.get(SOURCE_LABEL)}
    roles = {label.get(ROLE_LABEL, "") for label in labels if label.get(ROLE_LABEL)}
    owners = {label.get(OWNER_LABEL, "") for label in labels if label.get(OWNER_LABEL)}
    result: dict[str, Any] = {
        "project": project,
        "action": "report-only",
        "reason": "unproved identity",
    }
    protected = {
        "florabase",
        "florabase-prod",
        "florabase-preview",
        "florabase-feature-review",
        "florabase-uat-preview",
        "florabase-sourcing-preview",
    }
    result["sources"] = sorted(sources)
    result["roles"] = sorted(roles)
    if project in protected or project == "unknown":
        return result
    if len(sources) == len(roles) == len(owners) == 1:
        source, role, identity = (
            next(iter(sources)),
            next(iter(roles)),
            next(iter(owners)),
        )
        try:
            owner = Owner(project, role, source, identity)
            owner.validate()
            resources = Resources(owner)
            resources.preflight(inventory)
            if role == "quality" and source_finished(source, identity):
                result.update(action="remove-quality", reason="source missing or finished")
            elif role != "quality":
                marker = lock_root() / f"{project}.ended.json"
                if not marker.is_symlink() and json.loads(marker.read_text()) == owner.labels():
                    result.update(action="remove-disposable", reason="normal completion recorded")
        except EXPECTED_ERRORS:
            pass
    # UAT allocations are proved from their immutable volumes; never remove them.
    if project.startswith("florabase-uat-branch-"):
        name = project.removeprefix("florabase-uat-branch-")
        volumes = inventory["volumes"]
        volume_labels = [item.get("Labels") or {} for item in volumes]
        source_set = {label.get("io.florabase.source", "") for label in volume_labels}
        ports = {label.get("io.florabase.uat.port", "") for label in volume_labels}
        profiles = {label.get("io.florabase.uat.profile", "") for label in volume_labels}
        expected = {
            f"{project}_{key}"
            for key in ("postgres_data", "attachment_data", "frontend_node_modules")
        }
        if (
            re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?", name)
            and {item["Name"] for item in volumes} == expected
            and len(source_set) == 1
            and len(ports) == 1
            and next(iter(ports)) in {"15180", "15181", "15182", "15183"}
            and len(profiles) == 1
            and next(iter(profiles)) in {"smoke", "comprehensive"}
            and all(
                label.get(PROJECT_LABEL) == project
                and label.get("io.florabase.uat.instance") == name
                and label.get("com.docker.compose.volume")
                in {"postgres_data", "attachment_data", "frontend_node_modules"}
                for label in volume_labels
            )
        ):
            source = next(iter(source_set))
            containers = inventory["containers"]
            services = [
                Resources.labels(item, "containers").get("com.docker.compose.service")
                for item in containers
            ]
            if (
                len(services) == len(set(services))
                and source_finished(source)
                and all(
                    (label := Resources.labels(item, "containers")).get(PROJECT_LABEL) == project
                    and label.get("io.florabase.role") == "uat-instance"
                    and label.get("io.florabase.source") == source
                    and label.get("com.docker.compose.project.working_dir") == source
                    and label.get("com.docker.compose.oneoff", "False") == "False"
                    and re.fullmatch(r"[0-9a-f]{40}", label.get("io.florabase.sha", ""))
                    and not any(
                        item.get("State", {}).get(state)
                        for state in ("Paused", "Restarting", "Dead")
                    )
                    and label.get("com.docker.compose.service")
                    in {"db", "backend", "frontend", "dev-state-init"}
                    for item in containers
                )
            ):
                result.update(action="stop-uat", reason="source missing or finished")
    result["inventory"] = {
        kind: sorted(str(item.get("Id") or item.get("Name")) for item in group)
        for kind, group in inventory.items()
    }
    result["fingerprint"] = hashlib.sha256(
        json.dumps(inventory_identity(inventory), sort_keys=True).encode()
    ).hexdigest()
    result["token"] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()[:16]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project")
    parser.add_argument("--confirm")
    args = parser.parse_args()
    try:
        if not args.project or not args.confirm:
            local_daemon()
            candidates = []
            for project in report()["projects"]:
                try:
                    candidates.append(candidate(project))
                except EXPECTED_ERRORS:
                    candidates.append(
                        {"project": project, "action": "report-only", "reason": "inspection failed"}
                    )
            print(json.dumps(candidates, indent=2, sort_keys=True))
            return 0
        from feature_worktree import require_operator_identity

        try:
            require_operator_identity()
        except Exception as error:
            raise ResourceError(str(error)) from error
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", args.project):
            raise ResourceError("invalid project name")
        local_daemon()
        selected_report = candidate(args.project)
        if (
            selected_report.get("action") == "report-only"
            or selected_report.get("token") != args.confirm
        ):
            raise ResourceError("confirmation or eligibility changed; report again")
        with contextlib.ExitStack() as locks:
            locks.enter_context(machine_lock(args.project, f"{args.project} lifecycle"))
            initial = inspect_project(args.project)
            labels = [
                Resources.labels(item, kind) for kind, group in initial.items() for item in group
            ]
            sources = {
                label.get(SOURCE_LABEL) or label.get("io.florabase.source") for label in labels
            }
            sources.discard(None)
            source_path = Path(cast(str, next(iter(sources)))) if len(sources) == 1 else None
            try:
                source_path.stat() if source_path else None
                source_present = source_path is not None
            except FileNotFoundError:
                source_present = False
            if source_present and source_path is not None:
                from workflow_environment import Repository

                repo = Repository(source_path)
                if repo.source.resolve() != source_path.resolve():
                    raise ResourceError("source is not a worktree root")
                locks.enter_context(
                    FileLock(repo.metadata / "florabase-agent-state.lock", "agent state")
                )
                locks.enter_context(verification_lock(repo.metadata))
            selected = candidate(args.project)
            if selected["token"] != args.confirm or selected["action"] == "report-only":
                raise ResourceError("confirmation or eligibility changed; report again")
            inventory = inspect_project(args.project)
            fingerprint = hashlib.sha256(
                json.dumps(inventory_identity(inventory), sort_keys=True).encode()
            ).hexdigest()
            if fingerprint != selected["fingerprint"]:
                raise ResourceError("inventory changed; report again")
            if selected["action"] == "stop-uat":
                ids = [str(item["Id"]) for item in inventory["containers"]]
                for item in inventory["containers"]:
                    current = json.loads(docker("inspect", str(item["Id"])))[0]
                    if inventory_identity({"containers": [current]}) != inventory_identity(
                        {"containers": [item]}
                    ):
                        raise ResourceError("container changed; report again")
                if ids:
                    docker("container", "stop", *ids)
            else:
                first: dict[str, str] = next(
                    (
                        Resources.labels(item, kind)
                        for kind, group in inventory.items()
                        for item in group
                        if Resources.labels(item, kind).get(OWNER_LABEL)
                    ),
                    {},
                )
                owner = Owner(
                    args.project,
                    first[ROLE_LABEL],
                    first[SOURCE_LABEL],
                    first[OWNER_LABEL],
                )
                Resources(owner).clean(expected=inventory)
                if owner.role != "quality":
                    (lock_root() / f"{owner.project}.ended.json").unlink(missing_ok=True)
        print(f"retired {args.project}: {selected['action']}")
    except EXPECTED_ERRORS as error:
        print(f"cleanup refused: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
