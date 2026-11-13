#!/usr/bin/env python3
"""Real exact-target cleanup/Quality finish isolation using disposable synthetic Docker state."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from workflow_resources import Disposable, Owner, Resources, docker

ROOT = Path(__file__).resolve().parent.parent


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError("resource smoke: " + message)


def fixture_subnet(name: str) -> str:
    # Explicit unique ULA fixture networks do not allocate from shared IPv4 default pools.
    value = hashlib.sha256(name.encode()).hexdigest()
    return f"fd{value[:2]}:{value[2:6]}:{value[6:10]}:1::/64"


def create(owner: Owner, *, simulated: str) -> None:
    labels = [
        part for key, value in owner.labels().items() for part in ("--label", f"{key}={value}")
    ]
    docker(
        "network",
        "create",
        "--ipv4=false",
        "--ipv6",
        "--subnet",
        fixture_subnet(owner.project + "_network"),
        *labels,
        owner.project + "_network",
    )
    docker("volume", "create", *labels, owner.project + "_state")
    docker(
        "run",
        "-d",
        "--name",
        owner.project + "-fixture",
        "--network",
        owner.project + "_network",
        "--mount",
        f"type=volume,src={owner.project}_state,dst=/state",
        *labels,
        "--label",
        f"io.florabase.smoke.simulates={simulated}",
        "--entrypoint",
        "sh",
        "python:3.14.7-slim-bookworm",
        "-ec",
        "echo synthetic-only > /state/marker; exec sleep 300",
    )


def signature(resources: Resources) -> dict[str, list[str]]:
    return {
        kind: sorted(str(item.get("Id", item.get("Name"))) for item in items)
        for kind, items in resources.inventory().items()
    }


def real_operator_signature() -> dict[str, Any]:
    result = {}
    for project in (
        "florabase",
        "florabase-feature-review",
        "florabase-uat-preview",
        "florabase-preview",
        "florabase-prod",
    ):
        result[project] = {
            kind: docker(*command, "--filter", f"label=com.docker.compose.project={project}")
            for kind, command in [
                ("containers", ["ps", "-aq", "--no-trunc"]),
                ("networks", ["network", "ls", "-q"]),
                ("volumes", ["volume", "ls", "-q"]),
            ]
        }
    return result


def finish_fixture(root: Path, owner: Owner) -> None:
    """Run real finish Git safeguards against local fixtures; gh returns a proved synthetic merge."""
    seed = root / "seed"
    remote = root / "remote.git"
    primary = root / "primary"
    linked = Path(owner.source)

    def git(*args: str, cwd: Path | None = None) -> str:
        return subprocess.run(
            ["git", *args], cwd=cwd, check=True, text=True, capture_output=True
        ).stdout.strip()

    git("init", "--bare", "--initial-branch=main", str(remote))
    git("init", "--initial-branch=main", str(seed))
    git("config", "user.name", "Smoke", cwd=seed)
    git("config", "user.email", "smoke@example.invalid", cwd=seed)
    (seed / "base").write_text("base")
    git("add", ".", cwd=seed)
    git("commit", "-m", "base", cwd=seed)
    git("remote", "add", "origin", str(remote), cwd=seed)
    git("push", "origin", "main", cwd=seed)
    git("clone", str(remote), str(primary))
    git("config", "user.name", "Smoke", cwd=primary)
    git("config", "user.email", "smoke@example.invalid", cwd=primary)
    # The synthetic owner is computed from this linked metadata after creation by the caller.
    git("worktree", "add", "-b", "ci/smoke", str(linked), cwd=primary)
    (linked / "feature").write_text("feature")
    git("add", ".", cwd=linked)
    git("commit", "-m", "feature", cwd=linked)
    head = git("rev-parse", "HEAD", cwd=linked)
    git("push", "origin", "ci/smoke", cwd=linked)
    git("fetch", "origin", "ci/smoke", cwd=seed)
    git("merge", "--squash", "FETCH_HEAD", cwd=seed)
    git("commit", "-m", "squash", cwd=seed)
    merge = git("rev-parse", "HEAD", cwd=seed)
    git("push", "origin", "main", cwd=seed)
    metadata = Path(git("rev-parse", "--absolute-git-dir", cwd=linked))
    quality = Owner.quality(linked, metadata)
    with Disposable(quality):
        create(quality, simulated="finishing Quality")
        bin_path = root / "bin"
        bin_path.mkdir()
        gh = bin_path / "gh"
        gh.write_text(
            f"#!/bin/sh\nif [ \"$1\" = auth ]; then exit 0; fi\nprintf '%s\\n' 'MERGED|main|ci/smoke|{head}|{merge}'\n"
        )
        gh.chmod(0o755)
        env = {**os.environ, "PATH": str(bin_path) + ":" + os.environ["PATH"]}
        (primary / "base").write_text("staged operator change")
        git("add", "base", cwd=primary)
        failed = subprocess.run(
            [str(ROOT / "scripts/feature-finish.sh")],
            cwd=linked,
            env=env,
            capture_output=True,
            text=True,
        )
        require(
            failed.returncode != 0 and "has staged or working changes" in failed.stderr,
            "dirty primary finish refusal",
        )
        require(
            bool(Resources(quality).inventory()["containers"]), "refused finish preserves Quality"
        )
        git("restore", "--staged", "--worktree", "base", cwd=primary)
        subprocess.run([str(ROOT / "scripts/feature-finish.sh")], cwd=linked, env=env, check=True)
        require(
            not any(Resources(quality).inventory().values()),
            "successful finish retires exact Quality",
        )
        require(
            git("branch", "--show-current", cwd=primary) == "main", "fixture primary stays main"
        )
        require(git("branch", "--show-current", cwd=linked) == "", "fixture feature detached")
        require(git("rev-parse", "HEAD", cwd=primary) == merge, "fixture primary fast-forwarded")


def quality_network_smoke(root: Path) -> None:
    """Verify a fresh isolated worktree runs network-free Quality checks without adding networks."""
    seed = root / "seed"
    remote = root / "remote.git"
    primary = root / "primary"
    linked = root / "linked-quality"

    def git(*args: str, cwd: Path | None = None) -> str:
        return subprocess.run(
            ["git", *args], cwd=cwd, check=True, text=True, capture_output=True
        ).stdout.strip()

    seed.mkdir(parents=True)
    for name in (
        "compose.yaml",
        "compose.dev.yaml",
        "compose.quality.yaml",
        "compose.quality-network.yaml",
        ".env.example",
    ):
        shutil.copy2(ROOT / name, seed / name)
    shutil.copytree(ROOT / "scripts", seed / "scripts")
    shutil.copytree(
        ROOT / "backend",
        seed / "backend",
        ignore=shutil.ignore_patterns(
            ".venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"
        ),
    )
    shutil.copytree(
        ROOT / "frontend",
        seed / "frontend",
        ignore=shutil.ignore_patterns(
            "node_modules", "dist", ".pnpm-store", "coverage", "*.tsbuildinfo"
        ),
    )
    git("init", "--bare", "--initial-branch=main", str(remote))
    git("init", "--initial-branch=main", str(seed))
    git("config", "user.name", "Smoke", cwd=seed)
    git("config", "user.email", "smoke@localhost", cwd=seed)
    git("add", ".", cwd=seed)
    git("commit", "-m", "seed", cwd=seed)
    git("remote", "add", "origin", str(remote), cwd=seed)
    git("push", "origin", "main", cwd=seed)
    git("clone", str(remote), str(primary))
    git("config", "user.name", "Smoke", cwd=primary)
    git("config", "user.email", "smoke@localhost", cwd=primary)
    git("worktree", "add", "-b", "fix/smoke-quality-net", str(linked), cwd=primary)
    metadata = Path(git("rev-parse", "--absolute-git-dir", cwd=linked))
    quality = Owner.quality(linked, metadata)
    with Disposable(quality):
        networks_before = set(docker("network", "ls", "-q", "--no-trunc").splitlines())
        env_helper = [sys.executable, str(linked / "scripts" / "workflow_environment.py")]
        backend_output = subprocess.run(
            [
                *env_helper,
                "quality",
                "compose",
                "--",
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "backend",
                "python",
                "-c",
                "import os; print(','.join(sorted(os.listdir('/sys/class/net'))))",
            ],
            cwd=linked,
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()
        backend_ifaces = backend_output.splitlines()[-1] if backend_output else ""
        require(backend_ifaces == "lo", f"expected only loopback interface, got {backend_output!r}")
        subprocess.run(
            [
                *env_helper,
                "quality",
                "compose",
                "--",
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "frontend",
                "pnpm",
                "exec",
                "eslint",
                "--version",
            ],
            cwd=linked,
            check=True,
        )
        net_config = json.loads(
            subprocess.run(
                [
                    *env_helper,
                    "--quality-network",
                    "quality",
                    "compose",
                    "--",
                    "config",
                    "--format",
                    "json",
                ],
                cwd=linked,
                check=True,
                text=True,
                capture_output=True,
            ).stdout
        )
        for service in ("backend", "frontend"):
            require(
                net_config["services"][service].get("network_mode") == "bridge",
                f"--quality-network did not select bridge for {service}",
            )
            require(
                not net_config["services"][service].get("ports"),
                f"--quality-network published ports for {service}",
            )

        frontend_image = f"{quality.project}-frontend-development"
        incomplete_quality = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "-e",
                "FLORABASE_QUALITY_OFFLINE=1",
                "--entrypoint",
                "sh",
                frontend_image,
                "-c",
                "rm -rf /app/node_modules/react "
                "&& ls -d /app/node_modules/.bin /app/node_modules/.pnpm/lock.yaml >/dev/null "
                "&& /app/dev-entrypoint.sh echo SHOULD_NOT_RUN",
            ],
            text=True,
            capture_output=True,
        )
        require(
            incomplete_quality.returncode != 0,
            "Quality offline mode allowed incomplete frontend dependencies",
        )
        require(
            "SHOULD_NOT_RUN" not in incomplete_quality.stdout,
            "Quality offline mode executed command despite incomplete dependencies",
        )
        require(
            "Quality frontend dependencies are incomplete" in incomplete_quality.stderr,
            f"unexpected Quality offline failure output: {incomplete_quality.stderr!r}",
        )

        for case_name, setup in (
            ("valid", ""),
            (
                "incomplete",
                "rm -rf /app/node_modules/react "
                "&& ls -d /app/node_modules/.bin /app/node_modules/.pnpm/lock.yaml >/dev/null && ",
            ),
        ):
            persistent = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    "none",
                    "--entrypoint",
                    "sh",
                    frontend_image,
                    "-c",
                    setup
                    + r'mkdir -p /tmp/bin && printf "#!/bin/sh\necho SPY_PNPM CI=\$CI ARGS=\$*\n" > /tmp/bin/pnpm && chmod +x /tmp/bin/pnpm && PATH="/tmp/bin:$PATH" /app/dev-entrypoint.sh echo CMD_OK',
                ],
                text=True,
                capture_output=True,
            )
            require(
                persistent.returncode == 0,
                f"persistent frontend {case_name} runtime failed: {persistent.stderr!r}",
            )
            require(
                "SPY_PNPM CI=true ARGS=install --frozen-lockfile --prefer-offline"
                in persistent.stdout,
                f"persistent frontend {case_name} runtime did not invoke offline-preferred pnpm install: {persistent.stdout!r}",
            )
            require(
                "CMD_OK" in persistent.stdout,
                f"persistent frontend {case_name} runtime did not exec target command: {persistent.stdout!r}",
            )

        failing = subprocess.run(
            [
                *env_helper,
                "quality",
                "compose",
                "--",
                "run",
                "--no-deps",
                "-T",
                "backend",
                "python",
                "-c",
                "import sys; print('QUALITY_FAIL_MARKER'); sys.exit(17)",
            ],
            cwd=linked,
            text=True,
            capture_output=True,
        )
        require(failing.returncode != 0, "expected non-zero exit code for failing Quality command")
        require(
            "QUALITY_FAIL_MARKER" in failing.stdout,
            f"failing Quality command did not run target payload: {failing.stdout!r}",
        )
        require(
            bool(Resources(quality).inventory()["containers"]),
            "expected stopped failing container before cleanup",
        )
        require(
            not Resources(quality).inventory()["networks"],
            "failing Quality command allocated unexpected network",
        )
        Resources(quality).clean()
        require(
            not any(Resources(quality).inventory().values()),
            "failing Quality command left residual resources after clean",
        )

        proc = subprocess.Popen(
            [
                *env_helper,
                "quality",
                "compose",
                "--",
                "run",
                "--no-deps",
                "-T",
                "backend",
                "python",
                "-u",
                "-c",
                "import time; print('STARTED', flush=True); time.sleep(30)",
            ],
            cwd=linked,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            require(proc.stdout is not None, "interrupted process missing stdout pipe")
            assert proc.stdout is not None
            started = False
            for line in iter(proc.stdout.readline, ""):
                if line.strip() == "STARTED":
                    started = True
                    break
            require(started, "interrupted Quality command did not emit STARTED before EOF")
            os.killpg(proc.pid, signal.SIGTERM)
            exit_code = proc.wait(timeout=15)
            require(exit_code != 0, f"expected non-zero exit after SIGTERM, got {exit_code}")
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)
            if proc.stdout is not None:
                proc.stdout.close()
            if proc.stderr is not None:
                proc.stderr.close()

        require(
            not Resources(quality).inventory()["networks"],
            "interrupted Quality command allocated unexpected network",
        )
        Resources(quality).clean()
        require(
            not any(Resources(quality).inventory().values()),
            "interrupted Quality command left residual resources after clean",
        )

        networks_after = set(docker("network", "ls", "-q", "--no-trunc").splitlines())
        require(
            networks_after == networks_before,
            f"Quality runs created unexpected networks: {networks_after - networks_before}",
        )
        require(not Resources(quality).inventory()["networks"], "Quality inventory has networks")
    require(not any(Resources(quality).inventory().values()), "quality smoke fixture residual")


def main() -> None:
    before = real_operator_signature()
    with tempfile.TemporaryDirectory(prefix="florabase-resource-smoke-") as temporary:
        root = Path(temporary)
        target = Owner.disposable("integration", root)
        protected = [
            (
                name,
                Owner.quality(root / name, root / (name + "-metadata"))
                if name in {"quality A", "quality B"}
                else Owner.disposable("workflow-smoke", root),
            )
            for name in (
                "another disposable",
                "quality A",
                "quality B",
                "DEV-like",
                "Review-like",
                "UAT-like",
                "Stable-like",
                "Prod-like",
                "unrelated-like",
            )
        ]
        with ExitStack() as stack:
            for name, owner in [("target integration", target), *protected]:
                stack.enter_context(Disposable(owner))
                create(owner, simulated=name)
            # Simulate partially created orphan/stale resources under the exact target identity.
            labels = [
                part
                for key, value in target.labels().items()
                for part in ("--label", f"{key}={value}")
            ]
            docker(
                "network",
                "create",
                "--ipv4=false",
                "--ipv6",
                "--subnet",
                fixture_subnet(target.project + "_stale"),
                *labels,
                target.project + "_stale",
            )
            docker("volume", "create", *labels, target.project + "_orphan")
            survivors = {owner.project: signature(Resources(owner)) for _, owner in protected}
            Resources(target).clean()
            Resources(target).clean()
            require(
                not any(Resources(target).inventory().values()), "target fully retired/idempotent"
            )
            require(
                {owner.project: signature(Resources(owner)) for _, owner in protected} == survivors,
                "every non-target survived",
            )
            # Real finish operates only in a fresh local Git fixture, never the attached feature.
            finish_owner = Owner.disposable("workflow-smoke", root / "finishing")
            finish_fixture(root / "finish", finish_owner)
            require(
                {owner.project: signature(Resources(owner)) for _, owner in protected} == survivors,
                "finish preserves other Quality and persistent simulations",
            )
            quality_network_smoke(root / "quality-net")
            require(
                {owner.project: signature(Resources(owner)) for _, owner in protected} == survivors,
                "Quality network/failure/interruption smoke preserved other Quality and persistent simulations",
            )
            print(
                "TARGET_CLEANUP_SMOKE_PASSED: exact target removed; 9 protected/non-target fixtures survived; stale network/volume cleaned; repeated cleanup safe"
            )
            print(
                "QUALITY_FINISH_SMOKE_PASSED: dirty primary refusal preserved Quality; proved merge retired exact worktree; all other synthetic environments survived"
            )
        for _, owner in [("target", target), *protected]:
            require(not any(Resources(owner).inventory().values()), "smoke fixture residual")
    require(real_operator_signature() == before, "real operator projects changed")
    print(
        "WORKFLOW_RESOURCE_SMOKE_PASSED: all synthetic containers/networks/volumes retired; real DEV/Review/UAT/Stable/Prod resource identities unchanged"
    )


if __name__ == "__main__":
    main()
