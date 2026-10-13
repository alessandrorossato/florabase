#!/usr/bin/env python3
"""Delivered-source proof and resumable, same-path UAT source transitions."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from workflow_environment import Repository, WorkflowError, migration_graph, run

REPOSITORY = "alessandrorossato/florabase"


def ancestor(repo: Repository, before: str, after: str) -> bool:
    try:
        repo.git("merge-base", "--is-ancestor", before, after)
    except WorkflowError:
        return False
    return True


def delivered(repo: Repository, sha: str | None = None) -> str:
    """Return delivered main identity; squash delivery requires the exact merged PR head."""
    identity = repo.identity()
    if identity["dirty"] != "no":
        raise WorkflowError("delivered UAT source must be clean; preserve/resolve owner edits")
    sha = sha or identity["sha"]
    if ancestor(repo, sha, "origin/main"):
        return sha
    proposals = json.loads(
        run(["gh", "api", f"repos/{REPOSITORY}/commits/{sha}/pulls"], capture=True)
    )
    matches = []
    for pr in proposals:
        merge = pr.get("merge_commit_sha")
        if (
            pr.get("state") == "closed"
            and pr.get("merged_at")
            and pr.get("head", {}).get("sha") == sha
            and pr.get("base", {}).get("ref") == "main"
            and pr.get("base", {}).get("repo", {}).get("full_name") == REPOSITORY
            and isinstance(merge, str)
            and ancestor(repo, merge, "origin/main")
        ):
            matches.append(merge)
    if len(matches) != 1:
        raise WorkflowError("detached source is ahead/unrelated or has no exact delivered PR proof")
    return str(matches[0])


def graph_at(repo: Repository, sha: str) -> dict[str, list[str]]:
    """Inspect target revisions before changing source or touching persistent DB state."""
    names = repo.git("ls-tree", "-r", "--name-only", sha, "backend/alembic/versions").splitlines()
    with tempfile.TemporaryDirectory(prefix="florabase-uat-graph-") as directory:
        root = Path(directory)
        for name in names:
            if name.endswith(".py"):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(repo.git("show", f"{sha}:{name}"))
        return migration_graph(root)


def read_transition(path: Path, repo: Repository, project: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    value = json.loads(path.read_text())
    if (
        not isinstance(value, dict)
        or set(value) != {"version", "source", "project", "before", "target", "volumes"}
        or value["version"] != 1
        or value["source"] != str(repo.source)
        or value["project"] != project
        or not isinstance(value["volumes"], list)
        or any(not isinstance(value[key], str) for key in ("before", "target"))
        or repo.git("rev-parse", "HEAD") not in {value["before"], value["target"]}
        or not ancestor(repo, value["target"], "origin/main")
    ):
        raise WorkflowError(
            "ambiguous/interrupted UAT transition metadata; preserve and inspect it"
        )
    return value


def write_transition(path: Path, value: dict[str, Any]) -> None:
    """Atomic durable intent BEFORE stopping writers or switching the source."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
            os.replace(temporary, path)
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temporary.unlink(missing_ok=True)
