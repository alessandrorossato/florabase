#!/usr/bin/env python3
"""Two disposable coexisting UAT instances: isolation, golden profiles, refusals, exact cleanup."""

from __future__ import annotations

import hashlib
import http.cookiejar
import json
import shutil
import socket
import subprocess
import tempfile
import uuid
from contextlib import ExitStack
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen

from smoke_lifecycle import SmokeLifecycle, operator_snapshot
from uat_instance import LABEL_INSTANCE, LEDGER, PREFIX, UATInstance, instance_volumes
from workflow_environment import Repository, WorkflowError, run
from workflow_resources import machine_lock


def require(condition: bool, message: str) -> None:
    if not condition:
        raise WorkflowError(f"UAT instance smoke: {message}")


class SmokeInstance(UATInstance):
    def __init__(
        self, repository: Repository, profile: str, ports: tuple[int, ...], name: str = ""
    ) -> None:
        self.smoke_name = name or "smoke-" + uuid.uuid4().hex[:12]
        self.PORTS = ports  # Ephemeral fixture slots; never the operator range 15180-15183.
        super().__init__(repository, profile)

    def derived_name(self) -> str:
        return self.smoke_name


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def worktree(source: Path, root: Path, branch: str) -> Path:
    """A linked worktree carrying this source's exact dirty and untracked state."""
    path = root / branch.rsplit("-", 1)[1]
    run(["git", "-C", str(source), "worktree", "add", "--quiet", "-b", branch, str(path), "HEAD"])
    diff = subprocess.run(
        ["git", "-C", str(source), "diff", "HEAD", "--binary"],
        check=True,
        capture_output=True,
    ).stdout
    if diff:
        subprocess.run(["git", "-C", str(path), "apply", "--binary"], input=diff, check=True)
    untracked = run(
        ["git", "-C", str(source), "ls-files", "--others", "--exclude-standard"], capture=True
    )
    for name in untracked.splitlines():
        (path / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, path / name)
    return path


def retire_worktree(source: Path, path: Path, branch: str) -> None:
    run(["git", "-C", str(source), "worktree", "remove", "--force", str(path)])
    run(["git", "-C", str(source), "branch", "-D", branch])


def database_digest(instance: UATInstance) -> str:
    dump = instance.compose(
        "exec",
        "-T",
        "db",
        "sh",
        "-ec",
        'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --data-only --inserts --no-owner',
        capture=True,
    )
    # PostgreSQL dump restriction tokens are random; exclude them from the checksum.
    lines = (line for line in dump.splitlines() if not line.startswith(("\\restrict", "\\unrest")))
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def http_ok(instance: UATInstance) -> bool:
    try:
        with urlopen(instance.url + "/", timeout=10) as response:
            return bool(response.status == 200)
    except OSError:
        return False


def login(instance: UATInstance, *, expected: int = 200) -> None:
    opener = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
    request = Request(
        instance.url + "/api/v1/auth/login",
        data=json.dumps(
            {"login_name": "golden-owner", "password": "disposable-golden-owner-password"}
        ).encode(),
        headers={"Content-Type": "application/json", "Origin": instance.url},
    )
    try:
        with opener.open(request, timeout=10) as response:
            require(response.status == expected, f"{instance.project} login status")
        with opener.open(instance.url + "/api/v1/seed-lots", timeout=10) as response:
            require(response.status == 200, "golden owner session reads the collection")
    except HTTPError as error:
        require(error.code == expected, f"login unexpectedly returned {error.code}")


def refused(action: object, message: str) -> None:
    try:
        action()  # type: ignore[operator]
    except WorkflowError as error:
        require(message in str(error), f"refusal {message!r} got {error}")
        return
    raise WorkflowError(f"UAT instance smoke: expected refusal {message!r}")


def resources(project: str) -> dict[str, list[str]]:
    return {
        kind: run(
            ["docker", *listing, "-q", "--filter", f"label=com.docker.compose.project={project}"],
            capture=True,
        ).splitlines()
        for kind, listing in (
            ("containers", ["ps", "-a"]),
            ("networks", ["network", "ls"]),
            ("volumes", ["volume", "ls"]),
        )
    } | {
        "images": [
            tag
            for tag in (f"{project}-backend-development", f"{project}-frontend-development")
            if run(["docker", "image", "ls", "-q", tag], capture=True)
        ]
    }


def unchanged(before: dict[str, Any], after: dict[str, Any], context: str) -> None:
    """Docker and Git identity must be exact; a live DB another session uses is only reported."""
    require(after["git"] == before["git"], f"{context}: primary checkout identity changed")
    for project, old in before["projects"].items():
        new = after["projects"][project]
        for key in ("containers", "volumes"):
            require(new[key] == old[key], f"{context}: {project} {key} changed")
        if new.get("database_digest") != old.get("database_digest"):
            # Same containers, same start times, no exec by this smoke: the owner wrote to it.
            print(f"NOTE {context}: live {project} database content changed by its own session")


def main() -> None:
    source = Repository(Path.cwd()).source
    token = uuid.uuid4().hex[:8]
    ports = (free_port(), free_port())
    require(len(set(ports)) == 2, "two distinct fixture ports")
    operator_instances = tuple(
        sorted(
            {
                PREFIX + (item.get("Labels") or {}).get(LABEL_INSTANCE, "")
                for item in instance_volumes()
            }
        )
    )
    before = operator_snapshot(Repository(source), operator_instances)
    with ExitStack() as stack:
        # Heavy builds and seeds share canonical FULL's capacity lock, like uat-instance-up.
        stack.enter_context(machine_lock("verification-full", "UAT instance smoke (heavy builds)"))
        root = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="uat-instance-smoke-")))
        paths: dict[str, Path] = {}
        for letter in ("a", "b", "c"):
            branch = f"feat/uat-instance-smoke-{token}-{letter}"
            paths[letter] = worktree(source, root, branch)
            stack.callback(retire_worktree, source, paths[letter], branch)
        a = SmokeInstance(Repository(paths["a"]), "smoke", ports)
        b = SmokeInstance(Repository(paths["b"]), "comprehensive", ports)
        require(not resources(a.project)["volumes"] and not resources(b.project)["volumes"], "new")

        # 1. Two different feature sources coexist with independent identity, port and state.
        a.allocate()
        stack.enter_context(SmokeLifecycle(a))
        a.up()
        b.allocate()
        stack.enter_context(SmokeLifecycle(b))
        b.up()
        require((a.port, b.port) == ports, "second instance skips the first's claimed slot")
        a.require_identity(running=True)
        b.require_identity(running=True)
        require(http_ok(a) and http_ok(b), "both instances serve their own port")
        names = {kind: set(resources(a.project)[kind]) for kind in ("volumes", "networks")}
        require(
            not names["volumes"] & set(resources(b.project)["volumes"])
            and not names["networks"] & set(resources(b.project)["networks"])
            and len(names["volumes"]) == 3,
            "no shared writable volume or network",
        )
        login(a, expected=401)

        # 2. Explicit golden profiles, validated against the reviewed baselines.
        a.seed()
        a.seed()  # Idempotent repeat.
        b.seed()
        require(a.validate_dataset() == 0, "SMOKE instance is baseline-verified")
        require(b.validate_dataset() == 0, "COMPREHENSIVE instance is baseline-verified")
        a.status()
        b.status()
        login(a)
        login(b)
        a_digest, b_digest = database_digest(a), database_digest(b)
        require(a_digest != b_digest, "profiles produce different collections")

        # 3. Refusals change nothing: capacity, ownership, port collision, wrong confirmation.
        c = SmokeInstance(Repository(paths["c"]), "smoke", ports)
        refused(c.allocate, "slots are allocated")
        refused(
            SmokeInstance(Repository(paths["c"]), "smoke", ports, a.instance).allocate, "belongs to"
        )
        with socket.socket() as holder:
            holder.bind(("127.0.0.1", 0))
            holder.listen()
            held = int(holder.getsockname()[1])
            refused(
                SmokeInstance(Repository(paths["c"]), "smoke", (*ports, held)).allocate, "no free"
            )
        refused(lambda: b.reset(a.project), "CONFIRM_RESET_UAT_INSTANCE")
        refused(lambda: b.remove(a.project), "CONFIRM_REMOVE_UAT_INSTANCE")
        refused(lambda: b.remove(""), "CONFIRM_REMOVE_UAT_INSTANCE")
        require(
            not [
                item
                for item in instance_volumes()
                if (item.get("Labels") or {}).get("io.florabase.source") == str(paths["c"])
            ],
            "refused instance created no volume",
        )
        require(
            not run(
                ["docker", "network", "ls", "-q", "--filter", "label=io.florabase.role=pool-probe"],
                capture=True,
            ),
            "no leaked address-pool probe network",
        )
        require(database_digest(a) == a_digest, "refusals left instance A unchanged")
        require(database_digest(b) == b_digest, "refusals left instance B unchanged")
        unchanged(
            before, operator_snapshot(Repository(source), operator_instances), "after refusals"
        )

        # 4. A write in B is visible only in B; its validation reports the change.
        b.compose(
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            "golden_uat",
            "-d",
            "golden_uat",
            "-qc",
            "UPDATE botanical_identities SET common_name = 'Smoke operator edit' "
            "WHERE id = (SELECT id FROM botanical_identities ORDER BY id LIMIT 1);",
        )
        require(b.validate_dataset() in {1, 3}, "B detects the operator edit")
        require(a.validate_dataset() == 0 and database_digest(a) == a_digest, "A is unaffected")

        # 5. Stopping A preserves B; removing B preserves A exactly.
        b_digest = database_digest(b)
        a.stop()
        require(http_ok(b) and not http_ok(a), "B keeps serving after A stops")
        require(database_digest(b) == b_digest, "stopping A left B unchanged")
        b.remove(b.project)
        require(
            resources(b.project) == {"containers": [], "networks": [], "volumes": [], "images": []},
            "B retired exactly: containers, network, volumes and image tags",
        )
        require(len(resources(a.project)["volumes"]) == 3, "A's volumes survive B's removal")
        a.up()
        require(database_digest(a) == a_digest, "A's data survives B's removal and restart")
        require(a.validate_dataset() == 0, "A still baseline-verified")
        # Rebuilt images must not hide the manifest (status and detached owners read it).
        require(a.require_marker()[LEDGER]["profile"] == "smoke", "A's manifest after restart")
        login(a)
    for project in (a.project, b.project, c.project):
        require(
            resources(project) == {"containers": [], "networks": [], "volumes": [], "images": []},
            f"{project} left no Docker state",
        )
    unchanged(before, operator_snapshot(Repository(source), operator_instances), "after cleanup")
    print(
        "REAL UAT INSTANCE SMOKE PASSED: two linked sources coexist on distinct ports/projects/"
        "volumes; golden SMOKE and COMPREHENSIVE seeded, repeated and baseline-verified; real "
        "login; capacity/ownership/port/confirmation refusals changed nothing; writes stay in their "
        "instance; stop A keeps B; remove B keeps A exactly; zero residual state; persistent "
        "environments unchanged"
    )


if __name__ == "__main__":
    main()
