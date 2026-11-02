#!/usr/bin/env python3
"""Provider-neutral feature worktree creation, attachment, writer handoff and retirement.

Git and Docker remain the source of truth. The only added state lives beside the verification
receipt in this worktree's own Git metadata, and disappears with the worktree.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, cast

from workflow_environment import (
    BRANCH_PATTERN,
    REVIEW_PROJECT,
    SOURCING_PROJECT,
    UAT_PROJECT,
    Repository,
    WorkflowError,
)
from workflow_resources import FileLock, ResourceError, docker, verification_lock

AGENT_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
OPERATOR = "operator"
REPORT_LISTS = ("completed", "tests", "defects")
MAX_REPORT_BYTES = 64 * 1024
# Regenerable local output. Anything else ignored (.env, backups, source caches) blocks retirement.
DISPOSABLE_IGNORED = (
    "__pycache__",
    "*.py[cod]",
    "*.egg-info",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".coverage",
    "htmlcov",
    "node_modules",
    ".pnpm-store",
    "dist",
    "coverage",
    "*.tsbuildinfo",
    "build",
)


def now() -> str:
    return datetime.now(UTC).isoformat()


def agent_id(required: bool = False) -> str:
    value = os.environ.get("AGENT_ID", "")
    if value and not AGENT_PATTERN.fullmatch(value):
        raise WorkflowError("AGENT_ID must be a safe lowercase name, for example codex or codex-2")
    if required and not value:
        raise WorkflowError("AGENT_ID is required, for example AGENT_ID=codex")
    return value


def feature_id(branch: str) -> str:
    if not BRANCH_PATTERN.fullmatch(branch):
        raise WorkflowError("BRANCH must use feat/, fix/, docs/, or ci/ and a safe lowercase name")
    return branch.split("/", 1)[1]


def worktree_root(repo: Repository) -> Path:
    configured = os.environ.get("FLORABASE_WORKTREE_ROOT")
    return Path(configured) if configured else repo.primary.parent / "florabase-worktrees"


def worktrees(repo: Repository) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for block in repo.git("worktree", "list", "--porcelain", "-z").split("\0\0"):
        record: dict[str, str] = {}
        for field in block.split("\0"):
            key, _, value = field.partition(" ")
            if key:
                record[key] = value
        if record.get("worktree"):
            records.append(record)
    return records


def base_of(repo: Repository) -> str:
    try:
        return repo.git("merge-base", "HEAD", "origin/main")
    except WorkflowError as error:
        raise WorkflowError(
            f"wrong base: {repo.source} shares no history with origin/main"
        ) from error


def worktree_digest(repo: Repository) -> str:
    helper = Path(__file__).with_name("feature-tree-fingerprint.py")
    return subprocess.run(
        [sys.executable, str(helper), "digest"],
        cwd=repo.source,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()


def receipt_state(repo: Repository, branch: str, base: str) -> str:
    """Recompute receipt validity; a previous agent's claim about verification is never evidence."""
    if not branch:
        return "not applicable"
    # The receipt is judged by the target's own policy, not by the invoking checkout's version.
    helper = repo.source / "scripts/feature-tree-fingerprint.py"
    if not helper.is_file():
        helper = Path(__file__).with_name("feature-tree-fingerprint.py")
    command = [sys.executable, str(helper), "verify", "--branch", branch, "--base", base]
    worktree = subprocess.run(
        [*command, "--worktree"], cwd=repo.source, text=True, capture_output=True
    )
    if worktree.returncode:
        return "invalid: " + worktree.stderr.strip().removeprefix("feature receipt: ")
    committed = subprocess.run(command, cwd=repo.source, text=True, capture_output=True)
    return "valid, commit pending" if committed.returncode else "valid for committed HEAD"


def label_rows(*listing: str) -> list[list[str]]:
    return [line.split("\t") for line in docker(*listing).splitlines() if line]


def owned_resources(repo: Repository) -> dict[str, dict[str, int]]:
    """Count containers/volumes labelled with this exact source; raises when Docker is unavailable."""
    owned: dict[str, dict[str, int]] = {}
    project = '{{.Label "com.docker.compose.project"}}'
    for label in ("io.florabase.source", "io.florabase.workflow.source"):
        selector = f"label={label}={repo.source}"
        for row in label_rows(
            "ps", "-a", "--filter", selector, "--format", project + "\t{{.State}}"
        ):
            item = owned.setdefault(row[0], {"containers": 0, "running": 0, "volumes": 0})
            item["containers"] += 1
            item["running"] += int(row[1:] == ["running"])
        for row in label_rows(
            "volume", "ls", "--filter", selector, "--format", project + "\t{{.Name}}"
        ):
            item = owned.setdefault(row[0], {"containers": 0, "running": 0, "volumes": 0})
            item["volumes"] += 1
    return owned


def shared_owners() -> dict[str, list[str]]:
    source = '{{.Label "io.florabase.source"}}'
    owners: dict[str, list[str]] = {}
    for project in (REVIEW_PROJECT, UAT_PROJECT, SOURCING_PROJECT):
        selector = f"label=com.docker.compose.project={project}"
        found = {
            row[0]
            for listing in (("ps", "-a"), ("volume", "ls"))
            for row in label_rows(*listing, "--filter", selector, "--format", source)
        }
        owners[project] = sorted(found)
    return owners


class AgentState:
    """Per-worktree writer and handoff record; missing means the unclaimed legacy workflow."""

    def __init__(self, repo: Repository) -> None:
        self.path = repo.metadata / "info/florabase-agent-state.json"
        self.lock = repo.metadata / "florabase-agent-state.lock"

    def load(self) -> dict[str, Any]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {"version": 1, "writer": None, "handoff": None}
        except (OSError, json.JSONDecodeError) as error:
            raise WorkflowError(f"unreadable writer state {self.path}; inspect it") from error
        if not isinstance(value, dict) or value.get("version") != 1:
            raise WorkflowError(f"unknown writer state {self.path}; inspect it")
        return value

    def save(self, value: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f"{self.path.name}.{uuid.uuid4().hex}")
        temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        # Atomic: an interrupted writer leaves the previous complete state.
        os.replace(temporary, self.path)


def snapshot(repo: Repository) -> dict[str, str]:
    return {
        "branch": repo.git("branch", "--show-current"),
        "head": repo.git("rev-parse", "HEAD"),
        "head_tree": repo.git("rev-parse", "HEAD^{tree}"),
        "worktree_digest": worktree_digest(repo),
        "base": base_of(repo),
    }


def context(repo: Repository) -> dict[str, Any]:
    current = snapshot(repo)
    resources: Any
    environments: Any
    try:
        resources, environments = owned_resources(repo), shared_owners()
    except ResourceError:
        resources, environments = "docker unavailable", "docker unavailable"
    state = AgentState(repo).load()
    return {
        **current,
        "feature_id": current["branch"].partition("/")[2],
        "worktree": str(repo.source),
        "primary": str(repo.primary),
        "dirty": bool(repo.git("status", "--porcelain")),
        "origin_main": repo.git("rev-parse", "origin/main"),
        "behind_main": int(repo.git("rev-list", "--count", "HEAD..origin/main")),
        "receipt": receipt_state(repo, current["branch"], current["base"]),
        "writer": state["writer"],
        "handoff": state["handoff"],
        "owned_resources": resources,
        "shared_environment_owners": environments,
    }


def print_context(value: dict[str, Any]) -> None:
    for key, item in value.items():
        rendered = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else item
        print(f"{key}: {rendered}")


def create(repo: Repository, branch: str) -> None:
    identifier = feature_id(branch)
    repo.require_origin()
    if repo.git("-C", str(repo.primary), "branch", "--show-current") != "main":
        raise WorkflowError(f"primary checkout {repo.primary} must stay on main")
    repo.git("fetch", "origin", "main")
    base = repo.git("rev-parse", "--verify", "origin/main")
    try:
        repo.git("merge-base", "--is-ancestor", "main", base)
    except WorkflowError as error:
        raise WorkflowError("local main has diverged from origin/main; resolve it first") from error
    target = worktree_root(repo) / identifier
    if repo.git("branch", "--list", branch):
        raise WorkflowError(f"branch already exists: {branch}; use make feature-attach")
    if repo.git("ls-remote", "--heads", "origin", f"refs/heads/{branch}"):
        raise WorkflowError(f"remote branch already exists: origin/{branch}")
    if os.path.lexists(target):
        raise WorkflowError(f"worktree path already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    repo.git("worktree", "add", "-b", branch, str(target), base)
    created = Repository(target)
    # Retirement proof that this helper made it; a path alone cannot distinguish a tool's worktree.
    managed_marker(created).parent.mkdir(parents=True, exist_ok=True)
    managed_marker(created).write_text(now() + "\n", encoding="utf-8")
    print("FEATURE WORKTREE CREATED")
    print_context(context(created))


def managed_marker(repo: Repository) -> Path:
    return repo.metadata / "info/florabase-managed-worktree"


def attach(repo: Repository, branch: str) -> None:
    feature_id(branch)
    match = next(
        (item for item in worktrees(repo) if item.get("branch") == f"refs/heads/{branch}"), None
    )
    if match is None:
        raise WorkflowError(f"no worktree has {branch}; use make feature-worktree for new work")
    path = Path(match["worktree"])
    if not path.is_dir():
        raise WorkflowError(f"worktree for {branch} is missing: {path}; nothing was changed")
    if path == repo.primary:
        raise WorkflowError(f"{branch} is checked out in primary {path}; primary must stay on main")
    attached = Repository(path)
    print("FEATURE WORKTREE ATTACHED (read-only; make feature-claim before writing)")
    print_context(context(attached))


def require_idle_verification(repo: Repository) -> None:
    with verification_lock(repo.metadata):
        pass


def changed_since(repo: Repository, handoff: dict[str, Any]) -> list[str]:
    current = snapshot(repo)
    return [key for key in ("branch", "head", "worktree_digest") if current[key] != handoff[key]]


def claim(repo: Repository, agent: str, takeover: str) -> None:
    branch = repo.git("branch", "--show-current")
    feature_id(branch)
    base_of(repo)  # A wrong base refuses before any claim is recorded.
    if takeover and not sys.stdin.isatty():
        raise WorkflowError("TAKEOVER is an operator action and needs an interactive terminal")
    state = AgentState(repo)
    with FileLock(state.lock, "writer state update"):
        value = state.load()
        writer, handoff = value["writer"], value["handoff"]
        pending = handoff if handoff and not handoff.get("accepted_at") else None
        takeover_of = ""
        if writer and writer["agent"] == agent:
            print(f"WRITER CONFIRMED: {agent} (claimed {writer['claimed_at']})")
            print(
                "If another live session uses this name, stop: each session needs its own AGENT_ID."
            )
            print_context(context(repo))
            return
        if writer:
            if takeover != writer["claim_id"]:
                raise WorkflowError(
                    f"{writer['agent']} holds this worktree; use make feature-handoff, or ask the "
                    "operator to confirm that session is gone and take over"
                )
            require_idle_verification(repo)
            takeover_of = writer["claim_id"]
        if pending:
            drift = changed_since(repo, pending)
            if takeover != pending["id"]:
                if pending["to"] != agent:
                    raise WorkflowError(
                        f"the pending handoff is addressed to {pending['to']}, not {agent}"
                    )
                if drift:
                    raise WorkflowError(
                        f"repository changed after the handoff: {', '.join(drift)}; "
                        "ask the operator to inspect it and take over"
                    )
            require_idle_verification(repo)
            pending["accepted_by"] = agent
            pending["accepted_at"] = now()
            takeover_of = pending["id"] if takeover == pending["id"] else ""
        value["writer"] = {
            "agent": agent,
            "claim_id": uuid.uuid4().hex[:12],
            "claimed_at": now(),
            **({"takeover_of": takeover_of} if takeover_of else {}),
        }
        state.save(value)
    print(f"WRITER CLAIMED: {agent} (claim {value['writer']['claim_id']})")
    print_context(context(repo))
    if pending:
        print("Handoff report below is REPORTED by the previous agent, not verified:")
        print(json.dumps(pending["report"], indent=2, sort_keys=True))


def read_report(repo: Repository, path: str) -> dict[str, Any]:
    if not path:
        raise WorkflowError("REPORT=<json file> is required for a handoff")
    file = Path(path)
    if file.resolve().is_relative_to(repo.source.resolve()):
        raise WorkflowError(
            "keep the handoff report outside the worktree; it would change the tree"
        )
    if not file.is_file() or file.stat().st_size > MAX_REPORT_BYTES:
        raise WorkflowError(f"handoff report must be a file up to {MAX_REPORT_BYTES} bytes: {path}")
    try:
        report = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise WorkflowError(f"handoff report is not valid JSON: {path}") from error
    if not isinstance(report, dict) or set(report) != {*REPORT_LISTS, "next_action"}:
        raise WorkflowError(f"handoff report needs exactly {[*REPORT_LISTS, 'next_action']}")
    for key in REPORT_LISTS:
        items = report[key]
        if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
            raise WorkflowError(f"handoff report {key} must be a list of strings")
    if not isinstance(report["next_action"], str) or not report["next_action"].strip():
        raise WorkflowError("handoff report next_action must state the next permitted action")
    return cast(dict[str, Any], report)


def handoff(repo: Repository, agent: str, target: str, report_path: str) -> None:
    if not AGENT_PATTERN.fullmatch(target):
        raise WorkflowError("TO must name the receiving agent, for example TO=opencode")
    report = read_report(repo, report_path)
    state = AgentState(repo)
    with FileLock(state.lock, "writer state update"):
        value = state.load()
        writer = value["writer"]
        if not writer or writer["agent"] != agent:
            holder = writer["agent"] if writer else "nobody"
            raise WorkflowError(f"only the current writer can hand off; holder is {holder}")
        require_idle_verification(repo)
        identifier = uuid.uuid4().hex[:12]
        value["handoff"] = {
            "id": identifier,
            "from": agent,
            "to": target,
            "created_at": now(),
            "report": report,
            **snapshot(repo),
        }
        value["writer"] = None
        state.save(value)
    print(f"HANDOFF RECORDED: {identifier} from {agent} to {target}")
    print("Writer released. Receiver runs: make feature-claim AGENT_ID=" + target)


def require_writer(repo: Repository) -> None:
    value = AgentState(repo).load()
    pending = value["handoff"] and not value["handoff"].get("accepted_at")
    if pending:
        raise WorkflowError(
            f"a handoff to {value['handoff']['to']} is pending; "
            "the receiver must run make feature-claim first"
        )
    writer = value["writer"]
    if writer and agent_id() != writer["agent"]:
        raise WorkflowError(
            f"{writer['agent']} holds this worktree; pass its AGENT_ID or use make feature-handoff"
        )


def require_operator(repo: Repository) -> None:
    """Delivery and finish stay operator actions; an agent that identifies itself is refused."""
    if agent_id() not in ("", OPERATOR):
        raise WorkflowError(
            f"delivery and finish are operator actions; {agent_id()} must stop at READY_FOR_DELIVERY"
        )
    value = AgentState(repo).load()
    if value["handoff"] and not value["handoff"].get("accepted_at"):
        raise WorkflowError("a handoff is pending; its receiver must accept it first")
    require_idle_verification(repo)


def mark_finished(repo: Repository, branch: str, sha: str, merge: str) -> None:
    current = repo.git("branch", "--show-current")
    if current == branch or (not current and repo.git("rev-parse", "HEAD") != sha):
        raise WorkflowError(
            "mark-finished belongs to make feature-finish after the branch was left"
        )
    repo.git("merge-base", "--is-ancestor", merge, "origin/main")
    state = AgentState(repo)
    state.path.parent.mkdir(parents=True, exist_ok=True)
    proof = {"branch": branch, "sha": sha, "merge": merge, "finished_at": now()}
    (repo.metadata / "info/florabase-finished.json").write_text(
        json.dumps(proof, sort_keys=True) + "\n", encoding="utf-8"
    )
    state.path.unlink(missing_ok=True)


def undisposable_ignored(target: Repository) -> list[str]:
    raw = target.git("status", "--porcelain", "--ignored", "-z")
    paths = [item[3:].rstrip("/") for item in raw.split("\0") if item.startswith("!! ")]
    return [
        path
        for path in paths
        if not any(fnmatch(Path(path).name, pattern) for pattern in DISPOSABLE_IGNORED)
    ]


def require_no_running_mounts(path: Path) -> None:
    """Inspect every running container; host mountinfo cannot see other mount namespaces."""

    def running() -> set[str]:
        identifiers = docker("ps", "--quiet", "--no-trunc").splitlines()
        if any(not re.fullmatch(r"[0-9a-f]{64}", item) for item in identifiers):
            raise WorkflowError("incomplete running Docker container inventory; retry retirement")
        return set(identifiers)

    try:
        candidate = path.resolve(strict=True)
        identifiers = running()
        volumes: dict[str, Path] = {}
        for identifier in sorted(identifiers):
            record = json.loads(
                docker(
                    "inspect",
                    "--type",
                    "container",
                    "--format",
                    '{"Id":{{json .Id}},"Running":{{json .State.Running}},"Mounts":{{json .Mounts}}}',
                    identifier,
                )
            )
            if (
                not isinstance(record, dict)
                or record.get("Id") != identifier
                or record.get("Running") is not True
                or not isinstance(record.get("Mounts"), list)
            ):
                raise ValueError("incomplete or changed running container mount information")
            for mount in record["Mounts"]:
                if (
                    not isinstance(mount, dict)
                    or not isinstance(mount.get("Destination"), str)
                    or not Path(mount["Destination"]).is_absolute()
                ):
                    raise ValueError("incomplete container mount")
                kind, source = mount.get("Type"), mount.get("Source", "")
                if kind == "tmpfs" and source == "":
                    continue
                if not isinstance(source, str) or not Path(source).is_absolute():
                    raise ValueError("missing absolute mount source")
                if kind == "bind":
                    resolved = Path(source).resolve(strict=True)
                elif kind == "volume":
                    name = mount.get("Name")
                    if not isinstance(name, str) or not re.fullmatch(
                        r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", name
                    ):
                        raise ValueError("missing volume identity")
                    if name not in volumes:
                        volume = json.loads(
                            docker(
                                "volume",
                                "inspect",
                                "--format",
                                '{"Name":{{json .Name}},"Driver":{{json .Driver}},'
                                '"Mountpoint":{{json .Mountpoint}},"Options":{{json .Options}}}',
                                name,
                            )
                        )
                        # Default local volumes have daemon-managed canonical mountpoints. They
                        # need not be host-readable. Custom backing mounts need operator review.
                        if (
                            not isinstance(volume, dict)
                            or volume.get("Name") != name
                            or volume.get("Driver") != "local"
                            or "Options" not in volume
                            or volume["Options"] not in (None, {})
                            or volume.get("Mountpoint") != source
                        ):
                            raise ValueError("cannot establish volume backing path")
                        volumes[name] = Path(source).resolve()
                    resolved = volumes[name]
                    if resolved != Path(source).resolve():
                        raise ValueError("inconsistent volume mount source")
                else:
                    raise ValueError("unsupported container mount type")
                # A parent bind exposes the entire candidate, including nested mounts hidden
                # from host mountinfo. Check both directions on canonical paths.
                if (
                    resolved == candidate
                    or resolved.is_relative_to(candidate)
                    or candidate.is_relative_to(resolved)
                ):
                    raise WorkflowError(
                        f"running container {identifier} mounts {resolved}; stop its use before retirement"
                    )
        if running() != identifiers:
            raise ValueError("running container inventory changed during inspection")
    except (OSError, ValueError, TypeError) as error:
        raise WorkflowError(f"cannot establish safe Docker mount information: {error}") from error


def validate_retirement_tree(path: Path) -> None:
    """Preflight Git removal without following links or crossing even same-device bind mounts."""
    try:
        # is_mount() alone misses same-device bind mounts. Fail closed without mount evidence.
        mounts = Path("/proc/self/mountinfo").read_text(encoding="utf-8")
        if not mounts.strip():
            raise ValueError("empty mountinfo")
        for line in mounts.splitlines():
            fields = line.split()
            if len(fields) < 6 or " - " not in line:
                raise ValueError("invalid mountinfo record")
            mount = Path(re.sub(r"\\([0-7]{3})", lambda m: chr(int(m[1], 8)), fields[4]))
            if mount == path or mount.is_relative_to(path):
                raise WorkflowError(f"cannot remove mounted path {mount}; unmount it first")

        def scan(directory: Path) -> None:
            if directory.is_symlink():
                raise WorkflowError(f"cannot remove symlink {directory}; inspect it first")
            parent = directory.parent
            if not os.access(parent, os.W_OK | os.X_OK):
                raise WorkflowError(f"cannot remove {directory}; fix its ownership first")
            parent_stat = parent.stat()
            if parent_stat.st_mode & stat.S_ISVTX and os.geteuid() not in (
                0,
                parent_stat.st_uid,
                directory.stat().st_uid,
            ):
                raise WorkflowError(f"cannot remove {directory}; sticky parent forbids removal")
            with os.scandir(directory) as entries:
                children = list(entries)
            # rmdir needs writable/searchable parent, not a writable empty child.
            # Nonempty directories still need write/search permission to remove their contents.
            if children and not os.access(directory, os.W_OK | os.X_OK):
                raise WorkflowError(f"cannot remove {directory}; fix its ownership first")
            directory_stat = directory.stat()
            for child in children:
                if child.is_symlink():
                    raise WorkflowError(f"cannot remove symlink {child.path}; inspect it first")
                if directory_stat.st_mode & stat.S_ISVTX and os.geteuid() not in (
                    0,
                    directory_stat.st_uid,
                    child.stat(follow_symlinks=False).st_uid,
                ):
                    raise WorkflowError(
                        f"cannot remove {child.path}; sticky parent forbids removal"
                    )
                if child.is_dir(follow_symlinks=False):
                    scan(Path(child.path))

        scan(path)
    except (OSError, ValueError) as error:
        raise WorkflowError(f"cannot establish safe removal of {path}: {error}") from error


def retire(repo: Repository, identifier: str, confirmation: str) -> None:
    """Remove one finished managed worktree; provider-managed and foreign paths always refuse."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", identifier):
        raise WorkflowError("FEATURE must be a feature worktree id, for example event-001")
    root = worktree_root(repo).resolve()
    path = root / identifier
    if confirmation != identifier:
        raise WorkflowError(f"retirement requires CONFIRM_RETIRE={identifier}")
    record = next(
        (item for item in worktrees(repo) if Path(item["worktree"]).resolve() == path), None
    )
    if record is None or path == repo.primary.resolve():
        raise WorkflowError(f"{path} is not a registered managed worktree under {root}")
    if Path.cwd().resolve().is_relative_to(path):
        raise WorkflowError("run retirement from the primary checkout, not the retiring worktree")
    target = Repository(path)
    if not managed_marker(target).is_file():
        raise WorkflowError(f"{path} was not created by make feature-worktree; retire it elsewhere")
    if target.git("branch", "--show-current"):
        raise WorkflowError(f"{path} is still on a branch; run make feature-finish after merge")
    if target.git("status", "--porcelain"):
        raise WorkflowError(f"{path} has changes; preserve or resolve them first")
    blocked = undisposable_ignored(target)
    if blocked:
        raise WorkflowError(f"ignored local files need a decision first: {', '.join(blocked)}")
    try:
        proof = json.loads(
            (target.metadata / "info/florabase-finished.json").read_text(encoding="utf-8")
        )
        branch, sha, merge = proof["branch"], proof["sha"], proof["merge"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise WorkflowError(f"{path} has no make feature-finish proof") from error
    if sha != target.git("rev-parse", "HEAD") or target.git("branch", "--list", branch):
        raise WorkflowError(f"{path} moved after finish or {branch} still exists")
    target.git("merge-base", "--is-ancestor", merge, "origin/main")
    if AgentState(target).path.exists():
        raise WorkflowError(f"{path} has writer state again; inspect it")
    require_idle_verification(target)
    owned = owned_resources(target)
    if owned:
        raise WorkflowError(
            f"{path} still owns Docker resources {sorted(owned)}; retire them from it first"
        )
    # Git unregisters before deleting, so an unremovable directory would leave an orphan.
    require_no_running_mounts(path)
    validate_retirement_tree(path)
    # No --force: Git must still refuse anything it considers unsafe.
    repo.git("worktree", "remove", str(path))
    print(f"FEATURE WORKTREE RETIRED: {path}; volumes, branches and other worktrees unchanged")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in (
        "create",
        "attach",
        "claim",
        "handoff",
        "require-writer",
        "require-operator",
        "retire",
    ):
        commands.add_parser(name)
    show = commands.add_parser("context")
    show.add_argument("--json", action="store_true")
    finished = commands.add_parser("mark-finished")
    for option in ("--branch", "--sha", "--merge"):
        finished.add_argument(option, required=True)
    args = parser.parse_args()
    environment = os.environ
    try:
        repo = Repository(Path.cwd())
        if args.command == "create":
            create(repo, environment.get("BRANCH", ""))
        elif args.command == "attach":
            attach(repo, environment.get("BRANCH", ""))
        elif args.command == "context":
            expected = environment.get("BRANCH", "")
            if expected and repo.git("branch", "--show-current") != expected:
                raise WorkflowError(f"unexpected branch: this worktree is not on {expected}")
            value = context(repo)
            if args.json:
                print(json.dumps(value, indent=2, sort_keys=True))
            else:
                print_context(value)
        elif args.command == "claim":
            claim(repo, agent_id(required=True), environment.get("TAKEOVER", ""))
        elif args.command == "handoff":
            handoff(
                repo,
                agent_id(required=True),
                environment.get("TO", ""),
                environment.get("REPORT", ""),
            )
        elif args.command == "require-writer":
            require_writer(repo)
        elif args.command == "require-operator":
            require_operator(repo)
        elif args.command == "mark-finished":
            mark_finished(repo, args.branch, args.sha, args.merge)
        else:
            retire(repo, environment.get("FEATURE", ""), environment.get("CONFIRM_RETIRE", ""))
    except (WorkflowError, ResourceError) as error:
        print(f"feature-worktree: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
