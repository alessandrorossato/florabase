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
import time
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
        # The fixture finish is an operator action; an inherited agent AGENT_ID is refused first.
        env = {
            **{key: value for key, value in os.environ.items() if key != "AGENT_ID"},
            "PATH": str(bin_path) + ":" + os.environ["PATH"],
        }
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
            f"dirty primary finish refusal: {failed.stderr.strip()}",
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
        "Makefile",
        "compose.dev.yaml",
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
        for frontend_cmd in (
            ["pnpm", "exec", "eslint", "src/main.tsx"],
            ["pnpm", "typecheck"],
            ["pnpm", "exec", "vitest", "run", "--configLoader", "runner", "src/UX001.test.tsx"],
        ):
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
                    *frontend_cmd,
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
        for service in ("backend", "frontend", "frontend-lockfile"):
            require(
                net_config["services"][service].get("network_mode") == "bridge",
                f"--quality-network did not select bridge for {service}",
            )
            require(
                not net_config["services"][service].get("ports"),
                f"--quality-network published ports for {service}",
            )
        require(
            not net_config["services"]["frontend-lockfile"].get("volumes")
            or all(
                v.get("target") != "/app/node_modules"
                for v in net_config["services"]["frontend-lockfile"]["volumes"]
            ),
            "frontend-lockfile unexpectedly mounts node_modules volume",
        )

        # Unreachable registry env must not trigger network retries during offline Quality commands.
        no_registry_hook = subprocess.run(
            [
                *env_helper,
                "quality",
                "compose",
                "--",
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "-e",
                "npm_config_registry=http://127.0.0.1:9",
                "frontend",
                "pnpm",
                "exec",
                "eslint",
                "src/main.tsx",
            ],
            cwd=linked,
            text=True,
            capture_output=True,
            timeout=30,
        )
        require(
            no_registry_hook.returncode == 0,
            f"offline Quality attempted registry lookup or failed: {no_registry_hook.stderr!r}",
        )

        # Mixed lifecycle: completed networked frontend install clears provenance until make quality-clean.
        subprocess.run(
            [
                *env_helper,
                "--quality-network",
                "quality",
                "compose",
                "--",
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "frontend",
                "pnpm",
                "install",
                "--frozen-lockfile",
                "--prefer-offline",
            ],
            cwd=linked,
            check=True,
        )
        started_at = time.monotonic()
        after_network = subprocess.run(
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
                "src/main.tsx",
            ],
            cwd=linked,
            text=True,
            capture_output=True,
            timeout=15,
        )
        require(
            after_network.returncode != 0
            and "make quality-clean" in after_network.stderr
            and (time.monotonic() - started_at) < 10.0,
            f"offline Quality failed to reject mixed networked volume quickly: rc={after_network.returncode}, stderr={after_network.stderr!r}",
        )
        subprocess.run(["make", "quality-clean"], cwd=linked, check=True)
        require(not any(Resources(quality).inventory().values()), "make quality-clean left state")
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
                "src/main.tsx",
            ],
            cwd=linked,
            check=True,
        )

        # Mixed lifecycle: interrupted networked frontend install clears provenance without hanging later offline runs.
        interrupted_net = subprocess.Popen(
            [
                *env_helper,
                "--quality-network",
                "quality",
                "compose",
                "--",
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "frontend",
                "sh",
                "-c",
                "echo INSTALLING_NET; exec pnpm install --frozen-lockfile --force",
            ],
            cwd=linked,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            require(interrupted_net.stdout is not None, "missing stdout for networked install")
            assert interrupted_net.stdout is not None
            saw_install = False
            for line in iter(interrupted_net.stdout.readline, ""):
                if line.strip() == "INSTALLING_NET":
                    saw_install = True
                    break
            require(saw_install, "networked install did not start")
            time.sleep(0.5)
            os.killpg(interrupted_net.pid, signal.SIGTERM)
            interrupted_net.wait(timeout=15)
        finally:
            if interrupted_net.poll() is None:
                os.killpg(interrupted_net.pid, signal.SIGKILL)
                interrupted_net.wait(timeout=5)
            if interrupted_net.stdout is not None:
                interrupted_net.stdout.close()
            if interrupted_net.stderr is not None:
                interrupted_net.stderr.close()
        started_at = time.monotonic()
        after_interrupt = subprocess.run(
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
                "lint",
            ],
            cwd=linked,
            text=True,
            capture_output=True,
            timeout=15,
        )
        require(
            after_interrupt.returncode != 0
            and "make quality-clean" in after_interrupt.stderr
            and (time.monotonic() - started_at) < 10.0,
            f"offline Quality after interrupted networked install failed unexpectedly: rc={after_interrupt.returncode}, stderr={after_interrupt.stderr!r}",
        )
        subprocess.run(["make", "quality-clean"], cwd=linked, check=True)
        require(not any(Resources(quality).inventory().values()), "make quality-clean left state")
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
                "src/main.tsx",
            ],
            cwd=linked,
            check=True,
        )

        marker_check = subprocess.run(
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
                "sh",
                "-ec",
                'test -s /app/node_modules/.florabase-pnpm-lock.sha256 && test "$(cat /app/node_modules/.florabase-pnpm-lock.sha256)" = "$(sha256sum /app/pnpm-lock.yaml | cut -d" " -f1)" && cat /app/node_modules/.florabase-pnpm-lock.sha256',
            ],
            cwd=linked,
            check=True,
            text=True,
            capture_output=True,
        )
        require(
            bool(marker_check.stdout.strip()),
            "initialized Quality volume missing Florabase lockfile provenance marker",
        )
        changed_lock = root / "changed-pnpm-lock.yaml"
        changed_lock.write_text(
            (linked / "frontend/pnpm-lock.yaml").read_text(encoding="utf-8")
            + "\n# lockfile drift\n",
            encoding="utf-8",
        )
        stale_volume = subprocess.run(
            [
                *env_helper,
                "quality",
                "compose",
                "--",
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "-v",
                f"{changed_lock}:/app/pnpm-lock.yaml:ro",
                "frontend",
                "echo",
                "SHOULD_NOT_RUN",
            ],
            cwd=linked,
            text=True,
            capture_output=True,
        )
        require(
            stale_volume.returncode != 0, "stale Quality volume accepted changed source lockfile"
        )
        require(
            "SHOULD_NOT_RUN" not in stale_volume.stdout, "stale Quality volume ran target command"
        )
        require(
            "Quality frontend dependency marker is missing or out of sync with pnpm-lock.yaml"
            in stale_volume.stderr
            and "make quality-clean" in stale_volume.stderr,
            f"unexpected stale Quality volume error: {stale_volume.stderr!r}",
        )

        frontend_image = f"{quality.project}-frontend-development"
        retained_orphans = subprocess.run(
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
                "mkdir -p /app/node_modules/.pnpm/orphan@1.0.0/node_modules/orphan "
                "&& before=$(stat -c '%Y:%s' /app/node_modules/.florabase-pnpm-lock.sha256) "
                "&& rm -f /app/node_modules/.pnpm/lock.yaml "
                "&& /usr/local/bin/florabase-dev-entrypoint pnpm exec eslint src/main.tsx "
                "&& after=$(stat -c '%Y:%s' /app/node_modules/.florabase-pnpm-lock.sha256) "
                '&& test "$before" = "$after"',
            ],
            text=True,
            capture_output=True,
        )
        require(
            retained_orphans.returncode == 0,
            f"Quality offline mode rejected valid state with orphan/no-internal-lockfile or mutated marker: {retained_orphans.stderr!r}",
        )

        missing_dep = subprocess.run(
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
                "rm -rf /app/node_modules/eslint /app/node_modules/.bin/eslint "
                "&& /usr/local/bin/florabase-dev-entrypoint pnpm lint",
            ],
            text=True,
            capture_output=True,
        )
        require(missing_dep.returncode != 0, "missing required eslint dependency still passed")

        missing_impl = subprocess.run(
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
                "rm -f /app/node_modules/.pnpm/eslint@*/node_modules/eslint/lib/api.js "
                "&& /usr/local/bin/florabase-dev-entrypoint pnpm exec eslint src/main.tsx",
            ],
            text=True,
            capture_output=True,
        )
        require(
            missing_impl.returncode != 0,
            "missing implementation file inside eslint still passed",
        )

        for mismatch_name, extra_args, mismatch_setup in (
            (
                "changed-source-lockfile",
                ["-v", f"{changed_lock}:/app/pnpm-lock.yaml:ro"],
                "true",
            ),
            (
                "mismatched-marker",
                [],
                'printf "0000000000000000000000000000000000000000000000000000000000000000\\n" '
                "> /app/node_modules/.florabase-pnpm-lock.sha256",
            ),
            ("missing-marker", [], "rm -f /app/node_modules/.florabase-pnpm-lock.sha256"),
        ):
            mismatch = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    "none",
                    "-e",
                    "FLORABASE_QUALITY_OFFLINE=1",
                    *extra_args,
                    "--entrypoint",
                    "sh",
                    frontend_image,
                    "-c",
                    mismatch_setup
                    + " && /usr/local/bin/florabase-dev-entrypoint echo SHOULD_NOT_RUN",
                ],
                text=True,
                capture_output=True,
            )
            require(
                mismatch.returncode != 0,
                f"Quality offline mode accepted lockfile mismatch ({mismatch_name})",
            )
            require(
                "SHOULD_NOT_RUN" not in mismatch.stdout,
                f"Quality offline mode ran command despite mismatch ({mismatch_name})",
            )
            require(
                "Quality frontend dependency marker is missing or out of sync with pnpm-lock.yaml"
                in mismatch.stderr
                and "make quality-clean" in mismatch.stderr,
                f"unexpected mismatch error output ({mismatch_name}): {mismatch.stderr!r}",
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
                    + r'mkdir -p /tmp/bin && printf "#!/bin/sh\necho SPY_PNPM CI=\$CI ARGS=\$*\n" > /tmp/bin/pnpm && chmod +x /tmp/bin/pnpm && PATH="/tmp/bin:$PATH" /usr/local/bin/florabase-dev-entrypoint echo CMD_OK',
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

        real_recovery = subprocess.run(
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
                "mkdir /tmp/work && cd /tmp/work "
                "&& cp /app/package.json /app/pnpm-lock.yaml /app/pnpm-workspace.yaml /app/.npmrc . "
                "&& cp -a /app/node_modules /tmp/work/node_modules "
                "&& cp -a /pnpm/store /tmp/store "
                "&& rm -rf /tmp/work/node_modules/react "
                "&& CI=true pnpm install --frozen-lockfile --offline --store-dir=/tmp/store --trust-lockfile "
                "&& test -f /tmp/work/node_modules/react/package.json",
            ],
            text=True,
            capture_output=True,
        )
        require(
            real_recovery.returncode == 0,
            f"authentic pnpm offline recovery failed: {real_recovery.stderr!r}",
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

        # Dependency-update bootstrap regression: package.json changed while pnpm-lock.yaml is still old.
        shutil.rmtree(linked / "frontend" / ".pnpm-store", ignore_errors=True)
        pkg_path = linked / "frontend" / "package.json"
        pkg_data = json.loads(pkg_path.read_text(encoding="utf-8"))
        pkg_data["devDependencies"]["picocolors"] = "1.1.1"
        pkg_path.write_text(json.dumps(pkg_data, indent=2) + "\n", encoding="utf-8")

        stale_build = subprocess.run(
            [*env_helper, "quality", "compose", "--", "build", "frontend"],
            cwd=linked,
            text=True,
            capture_output=True,
        )
        require(
            stale_build.returncode != 0,
            "expected frozen frontend build to fail when package.json diverges from pnpm-lock.yaml",
        )
        frontend_entries_before = sorted(p.name for p in (linked / "frontend").iterdir())
        require(
            ".pnpm-store" not in frontend_entries_before,
            "unexpected .pnpm-store before make dependency-update",
        )
        dep_update = subprocess.run(
            ["make", "dependency-update"],
            cwd=linked,
            text=True,
            capture_output=True,
        )
        require(
            dep_update.returncode == 0,
            f"make dependency-update failed after package.json change: {dep_update.stderr!r}\n{dep_update.stdout!r}",
        )
        updated_lock = (linked / "frontend" / "pnpm-lock.yaml").read_text(encoding="utf-8")
        require(
            "picocolors:" in updated_lock, "updated pnpm-lock.yaml missing added picocolors pin"
        )
        require(
            sorted(p.name for p in (linked / "frontend").iterdir()) == frontend_entries_before,
            "make dependency-update altered directory entries inside frontend worktree",
        )
        require(
            not (linked / "frontend" / ".pnpm-store").exists()
            and (
                not (linked / "frontend" / "node_modules").exists()
                or not any((linked / "frontend" / "node_modules").iterdir())
            ),
            "make dependency-update populated node_modules or .pnpm-store inside frontend worktree",
        )
        require(
            (linked / "frontend" / "pnpm-lock.yaml").stat().st_uid == os.getuid(),
            "updated pnpm-lock.yaml ownership did not match invoking host user",
        )
        untracked = [
            line
            for line in git("status", "--short", cwd=linked).splitlines()
            if line.startswith("??")
        ]
        require(not untracked, f"make dependency-update created untracked files: {untracked}")
        subprocess.run(["make", "quality-clean"], cwd=linked, check=True)
        for frontend_cmd in (
            ["pnpm", "lint"],
            ["pnpm", "typecheck"],
            ["pnpm", "exec", "vitest", "run", "--configLoader", "runner", "src/UX001.test.tsx"],
        ):
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
                    *frontend_cmd,
                ],
                cwd=linked,
                check=True,
            )
        Resources(quality).clean()
        require(
            not any(Resources(quality).inventory().values()),
            "dependency-update follow-up Quality checks left residual resources after clean",
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
