#!/usr/bin/env python3
"""Stage evidence regressions: closure invalidation, corruption, controls, receipts, concurrency.

The real feature-verify.sh, gate and receipt helper run in disposable Git fixtures. A fake
Docker CLI renders fixture Compose models, streams container create events emitted by the fake
stage commands, and answers inspect/version queries; nothing touches the real daemon.
"""

from __future__ import annotations

import importlib.util
import json
import os
import secrets
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.dont_write_bytecode = True

import stage_evidence  # noqa: E402
from stage_evidence import Unknown, model_mounts, observed  # noqa: E402

SPEC = importlib.util.spec_from_file_location(
    "feature_workflow_tests", ROOT / "scripts/test-feature-workflow.py"
)
assert SPEC and SPEC.loader
FEATURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FEATURE)

FAKE_DOCKER = r"""#!/usr/bin/env python3
import json, os, sys, time
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
state = Path(os.environ["FAKE_DOCKER_STATE"])
args = sys.argv[1:]
with open(os.environ["VERIFY_LOG"], "a") as log:
    log.write("docker " + " ".join(args) + "\n")
def load(name):
    return json.loads((state / name).read_text())
def emit(kind):
    root = os.getcwd()
    containers = load("containers.json")
    images = load("images.json")
    project = "florabase-quality-fixture" if kind == "quality" else "florabase-integration-abcdefabcdef"
    specs = {
        "quality": [
            ("backend", "florabase-quality-fixture-backend-development", None,
             [{"Type": "bind", "Source": f"{root}/backend/src", "Destination": "/app/src"},
              {"Type": "bind", "Source": f"{root}/backend/tests", "Destination": "/app/tests"},
              {"Type": "volume", "Name": f"{project}_attachment_data", "Destination": "/var/lib/florabase/attachments"}], {}),
            ("frontend", "florabase-quality-fixture-frontend-development", ["florabase-dev-entrypoint"],
             [{"Type": "bind", "Source": f"{root}/frontend", "Destination": "/app"},
              {"Type": "volume", "Name": f"{project}_frontend_node_modules", "Destination": "/app/node_modules"}], {}),
        ],
        "integration": [
            ("db", "postgres:18.6-alpine", None, [], {"/var/lib/postgresql": ""}),
            ("tests", f"{project}-tests", None,
             [{"Type": "bind", "Source": f"{root}/scripts", "Destination": "/review"}],
             {"/tmp/florabase-attachments": "mode=0700"}),
        ],
    }[kind]
    for service, image, entrypoint, mounts, tmpfs in specs:
        identifier = f"{kind}-{service}-{time.time_ns()}"
        labels = {"com.docker.compose.project": project, "com.docker.compose.service": service,
                  "io.florabase.workflow.source": root, "image": image}
        if kind == "integration":
            labels["io.florabase.workflow.lifecycle"] = "integration"
        containers[identifier] = {"Image": images.get(image, "sha256:built-" + service),
                                  "Mounts": mounts, "HostConfig": {"Tmpfs": tmpfs},
                                  "Config": {"Entrypoint": entrypoint}}
        temporary = state / "containers.json.tmp"
        temporary.write_text(json.dumps(containers))
        os.replace(temporary, state / "containers.json")
        with open(state / "events.jsonl", "a") as events:
            events.write(json.dumps({"Type": "container", "Action": "create", "timeNano": time.time_ns(),
                                     "Actor": {"ID": identifier, "Attributes": labels}}) + "\n")
if args[:1] == ["fake-emit"]:
    emit(args[1])
elif args[:2] == ["volume", "ls"] and "--filter" not in args:
    print("\n".join(load("volumes.json")))
elif args[:1] == ["run"] and "python3" in args:
    volumes = load("volumes.json")
    names = {a.split(":")[1].removeprefix("/evidence/"): a.split(":")[0] for a in args if "/evidence/" in a}
    print(json.dumps({key: volumes[names[key]] for key in args[args.index("-c") + 2:]}))
elif args[:1] == ["version"]:
    print(json.dumps(load("tools.json")["version"]))
elif args[:1] == ["info"]:
    print(json.dumps(load("tools.json")["info"]))
elif args[:2] == ["compose", "version"]:
    print(load("tools.json")["compose"])
elif args[:2] == ["buildx", "version"]:
    print(load("tools.json")["buildx"])
elif args[:1] == ["compose"] and "config" in args:
    kind = "integration" if any(a.endswith("compose.integration.yaml") for a in args) else "quality"
    model = (state / f"model-{kind}.json").read_text().replace("@ROOT@", os.getcwd())
    model = json.loads(model)
    for service in model["services"].values():
        service["labels"] = {"io.florabase.sha": os.environ.get("FLORABASE_SHA", "volatile")}
    model["x-source"] = {"io.florabase.sha": os.environ.get("FLORABASE_SHA", "volatile")}
    print(json.dumps(model))
elif args[:2] == ["image", "inspect"]:
    images = load("images.json")
    layer = images.get(args[-1], args[-1] if args[-1].startswith("sha256:") else None)
    if layer is None:
        sys.exit(1)
    # Like the containerd image store: a fresh ID and Compose labels on every rebuild.
    print(json.dumps([{"Id": f"sha256:{time.time_ns()}", "RootFS": {"Type": "layers", "Layers": [layer]},
                       "Architecture": "amd64", "Os": "linux",
                       "Config": {"Labels": {"com.docker.compose.service": str(time.time_ns())}}}]))
elif args[:1] == ["inspect"]:
    containers = load("containers.json")
    if args[1] not in containers:
        sys.exit(1)
    print(json.dumps([containers[args[1]]]))
elif args[:1] == ["events"]:
    since = int(args[args.index("--since") + 1].replace(".", ""))
    position = 0
    while True:
        with open(state / "events.jsonl") as events:
            events.seek(position)
            for line in events.readlines():
                if json.loads(line)["timeNano"] >= since:
                    print(line, end="", flush=True)
            position = events.tell()
        time.sleep(0.05)
elif any("verify_migration_cycle.py" in a for a in args):
    sys.path.insert(0, "scripts")
    from disposable_workflow import expected_migration_evidence, SCHEMA_REPORT
    print(SCHEMA_REPORT + json.dumps(expected_migration_evidence("origin/main")["verified_revisions"]))
"""

FAKE_MAKE = r"""#!/usr/bin/env bash
set -eu
if [[ "$1" == --version ]]; then echo "GNU Make 4.4 (fixture)"; exit 0; fi
printf '%s\n' "$*" >>"${VERIFY_LOG}"
if [[ "${VERIFY_SLOW_STAGE:-}" == "$1" ]]; then touch "${VERIFY_LOG}.started"; sleep "${VERIFY_SLOW_SECONDS:-4}"; fi
if [[ "${VERIFY_FAIL_STAGE:-}" == "$1" ]]; then exit 7; fi
if [[ "${VERIFY_STAGE_INDEX:-}" == "$1" ]]; then git add pending.txt; fi
if [[ "${VERIFY_MUTATE_IGNORED:-}" == "$1" ]]; then echo generated > frontend/generated.pyc; fi
if [[ "${VERIFY_MUTATE_VOLUME:-}" == "$1" ]]; then echo '{"florabase-quality-fixture_attachment_data": "written"}' > "${FAKE_DOCKER_STATE}/volumes.json"; fi
case "$1" in
  check) docker fake-emit quality ;;
  test-integration) docker fake-emit integration ;;
esac
"""

BACKEND = {"context": "@ROOT@/backend", "dockerfile": "Dockerfile", "target": "development"}
FRONTEND = {"context": "@ROOT@/frontend", "dockerfile": "Dockerfile", "target": "development"}
QUALITY_MODEL = {
    "name": "florabase-quality-fixture",
    "services": {
        "backend": {
            "build": BACKEND,
            "image": "florabase-quality-fixture-backend-development",
            "volumes": [
                {"type": "bind", "source": f"@ROOT@/backend/{path}", "target": f"/app/{path}"}
                for path in ("src", "tests", "alembic", "openapi.json")
            ]
            + [
                {
                    "type": "volume",
                    "source": "attachment_data",
                    "target": "/var/lib/florabase/attachments",
                }
            ],
        },
        "frontend": {
            "build": FRONTEND,
            "image": "florabase-quality-fixture-frontend-development",
            "volumes": [
                {"type": "bind", "source": "@ROOT@/frontend", "target": "/app"},
                {
                    "type": "volume",
                    "source": "frontend_node_modules",
                    "target": "/app/node_modules",
                },
            ],
        },
        "db": {
            "image": "postgres:18.6-alpine",
            "volumes": [
                {"type": "volume", "source": "postgres_data", "target": "/var/lib/postgresql"}
            ],
        },
    },
    "volumes": {"frontend_node_modules": {}, "postgres_data": {}, "attachment_data": {}},
}
INTEGRATION_MODEL = {
    "name": "florabase-integration-000000000000",
    "services": {
        "db": {"image": "postgres:18.6-alpine", "tmpfs": ["/var/lib/postgresql"]},
        "tests": {
            "build": BACKEND,
            "image": "florabase-integration-000000000000-tests",
            "volumes": [
                {"type": "bind", "source": "@ROOT@/scripts", "target": "/review", "read_only": True}
            ],
            "tmpfs": ["/tmp/florabase-attachments:mode=0700"],
        },
    },
}
TOOLS = {
    "version": {"Client": {"Version": "29.0.0"}, "Server": {"Version": "29.0.0"}},
    "info": {"ID": "daemon", "ServerVersion": "29.0.0", "Driver": "overlayfs"},
    "compose": "5.0.0",
    "buildx": "buildx v0.30.0",
}
IMAGES = {
    "florabase-quality-fixture-backend-development": "sha256:backend-1",
    "florabase-quality-fixture-frontend-development": "sha256:frontend-1",
    "postgres:18.6-alpine": "sha256:postgres-1",
}


class EvidenceFixture(FEATURE.VerifyHelperTests):
    """The real gate in a Git fixture with Docker-shaped backend/frontend trees."""

    def setUp(self) -> None:
        super().setUp()
        work = self.work
        (work / "scripts/stage_evidence.py").write_bytes(
            (ROOT / "scripts/stage_evidence.py").read_bytes()
        )
        files = {
            "backend/src/app.py": "VALUE = 1\n",
            "backend/tests/test_app.py": "def test_value():\n    assert True\n",
            "backend/openapi.json": '{"openapi": "3.1.0"}\n',
            "backend/Dockerfile": (
                "# syntax=docker/dockerfile:1.7@sha256:aaaa\n"
                "FROM python:3.14@sha256:bbbb AS development\n"
            ),
            "backend/requirements.lock": "fastapi==1\n",
            "frontend/src/main.ts": "export const value = 1;\n",
            "frontend/src/api/schema.d.ts": "export interface paths {}\n",
            "frontend/pnpm-lock.yaml": "lockfileVersion: '9.0'\n",
            "frontend/Dockerfile": "FROM node:24@sha256:cccc AS development\n",
            "docs/notes.md": "# Notes\n",
            "Makefile": "check:\n\ttrue\n",
        }
        for name, content in files.items():
            (work / name).parent.mkdir(parents=True, exist_ok=True)
            (work / name).write_text(content)
        self.shell("git", "-C", str(work), "add", ".")
        self.shell("git", "-C", str(work), "commit", "-m", "fixture tree")
        self.shell("git", "-C", str(work), "push", "origin", "HEAD:main")
        self.shell("git", "-C", str(work), "fetch", "origin", "main")
        self.state = self.root / "docker"
        self.state.mkdir()
        for name, value in (
            ("model-quality.json", QUALITY_MODEL),
            ("model-integration.json", INTEGRATION_MODEL),
            ("tools.json", TOOLS),
            ("images.json", IMAGES),
            ("containers.json", {}),
            ("volumes.json", {"florabase-quality-fixture_attachment_data": "content-1"}),
        ):
            (self.state / name).write_text(json.dumps(value))
        (self.state / "events.jsonl").write_text("")
        for name, content in (("docker", FAKE_DOCKER), ("make", FAKE_MAKE)):
            (self.bin / name).write_text(content)
            os.chmod(self.bin / name, 0o755)
        self.metadata = Path(
            subprocess.run(
                ["git", "-C", str(work), "rev-parse", "--absolute-git-dir"],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip()
        )
        self.evidence = self.metadata / "florabase-stage-evidence"

    def environment(self, **extra: str) -> dict[str, str]:
        env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "VERIFY_LOG": str(self.log),
            "FAKE_DOCKER_STATE": str(self.state),
            "FLORABASE_LOCK_DIR": str(self.root / "locks"),
            "PYTHONDONTWRITEBYTECODE": "1",
            **extra,
        }
        for name in ("AGENT_ID", "REUSE", "FRESH", "GITHUB_ACTIONS", "MAKEFLAGS", "MFLAGS"):
            if name not in extra:
                env.pop(name, None)
        return env

    def gate(self, **extra: str) -> subprocess.CompletedProcess[str]:
        self.log.write_text("")
        return subprocess.run(
            [str(self.work / "scripts/feature-verify.sh"), "--full"],
            cwd=self.work,
            env=self.environment(**extra),
            stdin=subprocess.DEVNULL,
            text=True,
            capture_output=True,
        )

    def passed(self, **extra: str) -> subprocess.CompletedProcess[str]:
        result = self.gate(**extra)
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-3000:])
        return result

    def decisions(self, cwd: Path | None = None, **extra: str) -> dict[str, str]:
        result = subprocess.run(
            [sys.executable, "scripts/stage_evidence.py", "--full", "--base", "origin/main"],
            cwd=cwd or self.work,
            env=self.environment(**extra),
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = [line for line in result.stdout.splitlines() if line.startswith("stage evidence")]
        return {line.split()[3].rstrip(":"): line for line in lines}

    def stage_ran(self, target: str) -> bool:
        return target in self.log.read_text().splitlines()

    def fingerprint(self, *args: str) -> subprocess.CompletedProcess[str]:
        base = subprocess.run(
            ["git", "-C", str(self.work), "rev-parse", "origin/main"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()
        return subprocess.run(
            [
                sys.executable,
                "scripts/feature-tree-fingerprint.py",
                "verify",
                "--branch",
                "ci/ci-002",
                "--base",
                base,
                *args,
            ],
            cwd=self.work,
            env=self.environment(),
            text=True,
            capture_output=True,
        )

    def commit_all(self, message: str) -> None:
        self.shell("git", "-C", str(self.work), "add", "-A")
        self.shell("git", "-C", str(self.work), "commit", "--allow-empty", "-m", message)

    # The base class's own tests are run by test-feature-workflow.py, not repeated here.
    for name in [n for n in dir(FEATURE.VerifyHelperTests) if n.startswith("test_")]:
        locals()[name] = None


class GateEvidenceTests(EvidenceFixture):
    def test_cache_hit_reuses_only_quality_and_integration_and_never_delivers(self) -> None:
        first = self.passed(REUSE="1")
        self.assertIn("stage evidence: quality runs fresh: miss: no record", first.stdout)
        self.assertIn("stage evidence recorded: quality", first.stdout)
        self.assertIn("stage evidence recorded: integration", first.stdout)
        self.assertTrue(self.stage_ran("check") and self.stage_ran("test-integration"))
        second = self.passed(REUSE="1")
        self.assertIn("stage evidence: quality reused from run", second.stdout)
        self.assertIn("stage evidence: integration reused from run", second.stdout)
        self.assertFalse(self.stage_ran("check"))
        self.assertFalse(self.stage_ran("test-integration"))
        # Every always-fresh stage still executed, including the real migration cycle.
        for target in (
            "test-agent-workflow",
            "workflow-check",
            "verify-build SERVICES=backend frontend",
        ):
            self.assertTrue(self.stage_ran(target), target)
        self.assertIn("MIGRATION_CYCLE_PASSED", second.stdout)
        receipt = self.receipt()
        self.assertEqual(receipt["version"], 3)
        self.assertEqual(
            receipt["stage_evidence"], {"mode": "reuse", "reused": ["quality", "integration"]}
        )
        reused = {c["id"]: c["reused_from"] for c in receipt["completed"] if "reused_from" in c}
        self.assertEqual(set(reused), {"quality", "integration"})
        record = json.loads((self.evidence / "quality.json").read_text())
        self.assertEqual(reused["quality"]["key"], record["key"])
        self.assertEqual(record["command"], ["make", "check"])
        review = self.fingerprint("--worktree")
        self.assertEqual(review.returncode, 0, review.stderr)
        self.assertIn("reused stage evidence: quality, integration", review.stdout)
        # Reused stages are not delivery proof (separate operator policy), even once committed.
        self.commit_all("verified tree")
        delivery = self.fingerprint()
        self.assertNotEqual(delivery.returncode, 0)
        self.assertIn("not delivery proof", delivery.stderr)
        fresh = self.passed()
        self.assertTrue(self.stage_ran("check"))
        self.assertNotIn("stage evidence", fresh.stdout)
        self.assertEqual(self.fingerprint().returncode, 0)

    def test_docs_only_edit_after_full_reuses_proven_stages_and_reruns_the_rest(self) -> None:
        self.passed(REUSE="1")
        self.commit_all("verified")
        (self.work / "docs/notes.md").write_text("# Notes\n\nPost-gate wording.\n")
        result = self.passed(REUSE="1")
        self.assertIn("quality reused", result.stdout)
        self.assertIn("integration reused", result.stdout)
        log = self.log.read_text()
        for target in FEATURE_WORKFLOW_SUITES:
            self.assertIn(f"\n{target}\n", "\n" + log)
        self.assertIn("verify_migration_cycle.py", log)
        self.assertEqual(self.receipt()["verification"]["changed_paths"], ["docs/notes.md"])

    def test_default_fresh_dry_run_and_invalid_controls(self) -> None:
        default = self.passed()
        self.assertNotIn("stage evidence", default.stdout)
        self.assertFalse(self.evidence.exists())
        self.assertEqual(self.receipt()["stage_evidence"], {"mode": "off", "reused": []})
        fresh = self.passed(FRESH="1", REUSE="1")
        self.assertIn("quality runs fresh: fresh requested", fresh.stdout)
        self.assertTrue(self.stage_ran("check"))
        self.assertTrue((self.evidence / "quality.json").is_file())
        dry = self.passed(REUSE="dry-run")
        self.assertIn("stage evidence (dry-run): quality would be reused", dry.stdout)
        self.assertTrue(self.stage_ran("check") and self.stage_ran("test-integration"))
        self.assertEqual(self.receipt()["stage_evidence"], {"mode": "dry-run", "reused": []})
        for env in ({"REUSE": "yes"}, {"FRESH": "2"}):
            refused = self.gate(**env)
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("must be", refused.stderr)
        remote = self.gate(REUSE="1", GITHUB_ACTIONS="true")
        self.assertNotEqual(remote.returncode, 0)
        self.assertIn("remote CI never reads or writes local stage evidence", remote.stderr)

    def test_failed_interrupted_and_self_mutating_stages_leave_no_record(self) -> None:
        self.passed(REUSE="1")
        failed = self.gate(FRESH="1", VERIFY_FAIL_STAGE="check")
        self.assertNotEqual(failed.returncode, 0)
        self.assertFalse((self.evidence / "quality.json").exists())
        self.assertTrue((self.evidence / "integration.json").exists())
        self.assertIn("quality runs fresh: miss", self.decisions()["quality"])
        self.passed(REUSE="1")
        self.log.write_text("")
        process = subprocess.Popen(
            [str(self.work / "scripts/feature-verify.sh"), "--full"],
            cwd=self.work,
            env=self.environment(FRESH="1", VERIFY_SLOW_STAGE="check", VERIFY_SLOW_SECONDS="20"),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        started = Path(f"{self.log}.started")
        deadline = time.monotonic() + 60
        while not started.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        self.assertTrue(started.exists())
        os.killpg(process.pid, signal.SIGINT)
        self.assertNotEqual(process.wait(30), 0)
        self.assertFalse((self.evidence / "quality.json").exists())
        self.assertEqual([p.name for p in self.evidence.iterdir()], ["integration.json"])
        mutated = self.passed(REUSE="1", VERIFY_MUTATE_IGNORED="check")
        self.assertIn(
            "stage evidence not recorded: quality: inputs changed while the stage ran",
            mutated.stdout,
        )
        self.assertFalse((self.evidence / "quality.json").exists())
        written = self.passed(REUSE="1", VERIFY_MUTATE_VOLUME="check")
        self.assertIn(
            "inputs changed while the stage ran: volume_content: quality/attachment_data",
            written.stdout,
        )
        self.assertFalse((self.evidence / "quality.json").exists())

    def test_concurrent_gates_in_one_worktree_refuse_and_records_stay_intact(self) -> None:
        self.passed(REUSE="1")
        before = (self.evidence / "integration.json").read_bytes()
        self.log.write_text("")
        first = subprocess.Popen(
            [str(self.work / "scripts/feature-verify.sh"), "--full"],
            cwd=self.work,
            env=self.environment(FRESH="1", VERIFY_SLOW_STAGE="check", VERIFY_SLOW_SECONDS="6"),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        started = Path(f"{self.log}.started")
        deadline = time.monotonic() + 60
        while not started.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        second = subprocess.run(
            [str(self.work / "scripts/feature-verify.sh"), "--full"],
            cwd=self.work,
            env=self.environment(REUSE="1"),
            stdin=subprocess.DEVNULL,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("verification of this worktree is already running", second.stderr)
        output, errors = first.communicate(timeout=120)
        self.assertEqual(first.returncode, 0, output[-2000:] + errors[-2000:])
        self.assertNotEqual((self.evidence / "integration.json").read_bytes(), before)
        self.assertEqual(
            sorted(p.name for p in self.evidence.iterdir()), ["integration.json", "quality.json"]
        )
        # The winning gate's records are keyed by its own environment.
        decisions = self.decisions(VERIFY_SLOW_STAGE="check", VERIFY_SLOW_SECONDS="6")
        for name in ("quality", "integration"):
            self.assertIn("would be reused", decisions[name])

    def test_new_commit_and_index_or_head_drift_never_inherit_a_receipt(self) -> None:
        self.passed(REUSE="1")
        self.commit_all("verified")
        (self.work / "backend/src/app.py").write_text("VALUE = 2\n")
        self.commit_all("new commit")
        for args in ((), ("--worktree",)):
            self.assertNotEqual(self.fingerprint(*args).returncode, 0)
        result = self.passed(REUSE="1")
        self.assertIn("quality runs fresh: invalidated: mounts", result.stdout)
        receipt = self.receipt()
        self.assertEqual(receipt["stage_evidence"]["reused"], [])
        # An index change during a reuse run refuses the receipt (frozen HEAD/index/worktree).
        (self.work / "pending.txt").write_text("pending\n")
        drift = self.gate(REUSE="1", VERIFY_STAGE_INDEX="test-workflow-helpers")
        self.assertNotEqual(drift.returncode, 0)
        self.assertIn("working tree, index or HEAD", drift.stderr)
        self.assertFalse((self.work / ".git/info/florabase-feature-verification.json").exists())

    def test_receipt_version_3_and_version_2_compatibility(self) -> None:
        path = self.work / ".git/info/florabase-feature-verification.json"
        self.passed(REUSE="1")
        self.passed(REUSE="1")
        reused = json.loads(path.read_text())
        self.passed()
        fresh = json.loads(path.read_text())
        self.assertEqual(fresh["version"], 3)

        def verdict(receipt: dict[str, Any]) -> int:
            path.write_text(json.dumps(receipt))
            return self.fingerprint("--worktree").returncode

        def without_summary(receipt: dict[str, Any], **changes: Any) -> dict[str, Any]:
            return {k: v for k, v in receipt.items() if k != "stage_evidence"} | changes

        def reference(receipt: dict[str, Any], stage: str, **changes: Any) -> dict[str, Any]:
            completed = [
                {
                    **c,
                    "reused_from": {
                        **c.get("reused_from", reused["completed"][-1]["reused_from"]),
                        **changes,
                    },
                }
                if c["id"] == stage
                else c
                for c in receipt["completed"]
            ]
            return {**receipt, "completed": completed}

        # A version 2 receipt written before this feature stays valid without a rerun.
        self.assertEqual(verdict(without_summary(fresh, version=2)), 0)
        self.assertEqual(verdict(fresh), 0)
        self.assertEqual(verdict(reused), 0)
        invalid = {
            "version 2 cannot carry reuse": without_summary(reused, version=2),
            "version 3 requires the summary": without_summary(fresh),
            "reuse without reuse mode": {
                **reused,
                "stage_evidence": {"mode": "off", "reused": ["quality", "integration"]},
            },
            "summary hides a reused stage": {
                **reused,
                "stage_evidence": {"mode": "reuse", "reused": ["quality"]},
            },
            "unknown mode": {**fresh, "stage_evidence": {"mode": "cached", "reused": []}},
            "always-fresh stage reused": reference(fresh, "migration-cycle"),
            "malformed key": reference(reused, "quality", key="short"),
            "naive timestamp": reference(reused, "quality", finished_at="2026-11-10T00:00:00"),
            "extra reference field": reference(reused, "quality", trusted="yes"),
        }
        for name, receipt in invalid.items():
            with self.subTest(name):
                self.assertNotEqual(verdict(receipt), 0)
        self.assertEqual(verdict(fresh), 0)

    def test_records_never_store_environment_or_env_file_values(self) -> None:
        env_file_value = secrets.token_hex(16)
        env_value = secrets.token_hex(16)
        (self.work / ".env").write_text(f"POSTGRES_PASSWORD={env_file_value}\n")
        self.passed(REUSE="1", FIXTURE_TOKEN=env_value)
        text = "".join(p.read_text() for p in self.evidence.iterdir())
        self.assertNotIn(env_value, text)
        self.assertNotIn(env_file_value, text)
        self.assertIn("FIXTURE_TOKEN", text)


class InvalidationTests(EvidenceFixture):
    def setUp(self) -> None:
        super().setUp()
        self.passed(REUSE="1")
        decisions = self.decisions()
        self.assertIn("quality would be reused", decisions["quality"])
        self.assertIn("integration would be reused", decisions["integration"])

    def test_dry_run_requires_fresh_and_valid_timestamps(self) -> None:
        path = self.evidence / "quality.json"
        body = json.loads(path.read_text())
        body.pop("digest")
        now = datetime.now(UTC)
        offset = timezone(timedelta(hours=5, minutes=30))
        valid = {
            "started_at": (now - timedelta(hours=2)).astimezone(offset).isoformat(),
            "finished_at": (now - timedelta(hours=1)).astimezone(offset).isoformat(),
        }
        for changes, message in (
            (valid, "would be reused"),
            (
                {
                    "started_at": (now - timedelta(hours=26)).isoformat(),
                    "finished_at": (now - timedelta(hours=25)).isoformat(),
                },
                "expired: completion is older than 24 hours (UTC)",
            ),
            ({"started_at": None}, "missing or malformed timestamp"),
            ({"finished_at": None}, "missing or malformed timestamp"),
            ({"finished_at": "yesterday"}, "missing or malformed timestamp"),
            (
                {"started_at": now.replace(tzinfo=None).isoformat()},
                "missing or malformed timestamp",
            ),
            (
                {"finished_at": (now + timedelta(hours=1)).isoformat()},
                "future-dated timestamp",
            ),
            (
                {"started_at": (now + timedelta(hours=1)).isoformat()},
                "future-dated timestamp",
            ),
            (
                {"started_at": (now - timedelta(minutes=30)).isoformat()},
                "starts after its completion",
            ),
        ):
            with self.subTest(changes=changes):
                record = {**body, **valid, **changes}
                for key, value in changes.items():
                    if value is None:
                        record.pop(key)
                stage_evidence.write_record(path, record)
                decision = self.decisions()["quality"]
                self.assertIn(message, decision)
                if message != "would be reused":
                    self.assertIn("runs fresh: invalidated", decision)

    def check(self, mutate: Any, quality: str, integration: str | None, **env: str) -> None:
        """Mutate one input, require the exact invalidation, revert and require reuse again."""
        restore = mutate()
        try:
            decisions = self.decisions(**env)
            self.assertIn(f"quality runs fresh: {quality}", decisions["quality"])
            if integration is None:
                self.assertIn("integration would be reused", decisions["integration"])
            else:
                self.assertIn(f"integration runs fresh: {integration}", decisions["integration"])
        finally:
            restore()

    def edit(self, path: str, content: str | None = None, mode: int | None = None) -> Any:
        target = self.work / path

        def mutate() -> Any:
            original = target.read_bytes() if target.exists() else None
            original_mode = target.stat().st_mode if target.exists() else None
            target.parent.mkdir(parents=True, exist_ok=True)
            if content is not None:
                target.write_text(content)
            if mode is not None:
                target.chmod(mode)

            def restore() -> None:
                if original is None:
                    target.unlink()
                else:
                    target.write_bytes(original)
                    assert original_mode is not None
                    target.chmod(original_mode)

            return restore

        return mutate

    def docker_state(self, name: str, change: Any) -> Any:
        path = self.state / name

        def mutate() -> Any:
            original = path.read_text()
            value = json.loads(original)
            change(value)
            path.write_text(json.dumps(value))
            return lambda: path.write_text(original)

        return mutate

    def test_application_sources_tests_contracts_and_migrations(self) -> None:
        both = "invalidated: mounts: backend"
        cases = [
            ("python source", self.edit("backend/src/app.py", "VALUE = 2\n"), both, both),
            (
                "python test",
                self.edit("backend/tests/test_app.py", "def test_value():\n    assert 1\n"),
                both,
                both,
            ),
            (
                "migration",
                self.edit("backend/alembic/versions/0002_new.py", 'revision = "0002"\n'),
                both,
                both,
            ),
            (
                "generated OpenAPI",
                self.edit("backend/openapi.json", '{"openapi": "3.1.1"}\n'),
                both,
                both,
            ),
            (
                "generated TypeScript",
                self.edit("frontend/src/api/schema.d.ts", "export interface paths { x: 1 }\n"),
                "invalidated: mounts: frontend",
                None,
            ),
            (
                "typescript source",
                self.edit("frontend/src/main.ts", "export const value = 2;\n"),
                "invalidated: mounts: frontend",
                None,
            ),
            (
                "lockfile",
                self.edit("frontend/pnpm-lock.yaml", "lockfileVersion: '9.1'\n"),
                "invalidated: mounts: frontend",
                None,
            ),
            (
                "backend lockfile",
                self.edit("backend/requirements.lock", "fastapi==2\n"),
                both,
                both,
            ),
            (
                "Dockerfile",
                self.edit("backend/Dockerfile", "FROM python:3.14@sha256:dddd AS development\n"),
                both,
                both,
            ),
            ("file mode", self.edit("backend/src/app.py", mode=0o755), both, both),
            ("untracked file", self.edit("backend/src/new_module.py", "X = 1\n"), both, both),
            (
                "Git-ignored file in a bind mount",
                self.edit("frontend/src/stale.pyc", "x"),
                "invalidated: mounts: frontend",
                None,
            ),
        ]
        link = self.work / "frontend/src/link.ts"

        def symlink() -> Any:
            link.symlink_to("main.ts")
            return link.unlink

        cases.append(("symlink", symlink, "invalidated: mounts: frontend", None))
        for name, mutate, quality, integration in cases:
            with self.subTest(name):
                self.check(mutate, quality, integration)
        # Every mutation was reverted exactly: the original evidence is valid again.
        decisions = self.decisions()
        self.assertIn("would be reused", decisions["quality"])
        self.assertIn("would be reused", decisions["integration"])

    def test_configuration_environment_tools_images_and_policy(self) -> None:
        def add_environment(model: dict[str, Any]) -> None:
            model["services"]["backend"]["environment"] = {"FEATURE": "on"}

        def replace_image(images: dict[str, str]) -> None:
            images["postgres:18.6-alpine"] = "sha256:postgres-2"
            images["florabase-quality-fixture-backend-development"] = "sha256:backend-2"

        def tool(tools: dict[str, Any]) -> None:
            tools["compose"] = "5.0.1"

        gate = (self.work / "scripts/verification_gate.py").read_text()
        cases = [
            (
                "Compose configuration",
                self.docker_state("model-quality.json", add_environment),
                "invalidated: compose",
                None,
                {},
            ),
            (
                "Compose integration configuration",
                self.docker_state(
                    "model-integration.json",
                    lambda m: m["services"]["db"].update(image="postgres:19"),
                ),
                "",
                "invalidated: compose",
                {},
            ),
            (
                "environment variable",
                lambda: lambda: None,
                "invalidated: environment: FLORABASE_EXAMPLE",
                "invalidated: environment: FLORABASE_EXAMPLE",
                {"FLORABASE_EXAMPLE": "1"},
            ),
            (
                "env file",
                self.edit(".env", "POSTGRES_DB=other\n"),
                "invalidated: env_files: quality; policy: top-level files",
                "invalidated: policy: top-level files",
                {},
            ),
            (
                "tool identity",
                self.docker_state("tools.json", tool),
                "invalidated: tools",
                "invalidated: tools",
                {},
            ),
            (
                "image identity",
                self.docker_state("images.json", replace_image),
                "invalidated: images: florabase-quality-fixture-backend-development",
                "invalidated: images: postgres:18.6-alpine",
                {},
            ),
            (
                "verification policy",
                self.edit("scripts/verification_gate.py", gate + "# policy note\n"),
                "invalidated: policy: scripts",
                "invalidated: mounts: scripts; policy: scripts",
                {},
            ),
            (
                "volume content",
                self.docker_state(
                    "volumes.json",
                    lambda v: v.update({"florabase-quality-fixture_attachment_data": "content-2"}),
                ),
                "invalidated: volume_content: quality/attachment_data",
                None,
                {},
            ),
            (
                "volume created",
                self.docker_state(
                    "volumes.json",
                    lambda v: v.update({"florabase-quality-fixture_postgres_data": "content-1"}),
                ),
                "invalidated: volume_content: quality/postgres_data",
                None,
                {},
            ),
            (
                "Makefile",
                self.edit("Makefile", "check:\n\tfalse\n"),
                "invalidated: policy: top-level files",
                "invalidated: policy: top-level files",
                {},
            ),
        ]
        for name, mutate, quality, integration, env in cases:
            with self.subTest(name):
                restore = mutate()
                try:
                    decisions = self.decisions(**env)
                    for stage, expected in (("quality", quality), ("integration", integration)):
                        if expected == "":
                            continue
                        if expected is None:
                            self.assertIn("would be reused", decisions[stage])
                        else:
                            self.assertIn(f"{stage} runs fresh: {expected}", decisions[stage])
                finally:
                    restore()
        decisions = self.decisions()
        self.assertIn("would be reused", decisions["quality"])
        self.assertIn("would be reused", decisions["integration"])

    def test_documentation_and_volatile_labels_do_not_invalidate(self) -> None:
        (self.work / "docs/notes.md").write_text("# Notes\n\nChanged.\n")
        self.commit_all("docs and a new SHA in Compose labels")
        decisions = self.decisions()
        self.assertIn("would be reused", decisions["quality"])
        self.assertIn("would be reused", decisions["integration"])

    def test_corrupt_truncated_tampered_schema_and_foreign_records_run_fresh(self) -> None:
        path = self.evidence / "quality.json"
        original = path.read_text()
        record = json.loads(original)
        body = {k: v for k, v in record.items() if k != "digest"}

        def signed(**changes: Any) -> str:
            value = {**body, **changes}
            return json.dumps({**value, "digest": stage_evidence.digest(value)})

        tampered = json.loads(original)
        tampered["manifest"]["mounts"]["backend/src"] = "0" * 64
        cases = [
            (
                "truncated",
                original[: len(original) // 2],
                "corrupt: unreadable or truncated record",
            ),
            ("empty", "", "corrupt: unreadable or truncated record"),
            ("tampered manifest", json.dumps(tampered), "corrupt: record digest mismatch"),
            ("schema", signed(schema=99), "schema: unsupported evidence schema 99"),
            ("failed result", signed(result="failed"), "corrupt: record is not a passed execution"),
            ("forged key", signed(key="f" * 64), "corrupt: record key mismatch"),
            (
                "other worktree",
                signed(worktree="/elsewhere/.git/worktrees/x"),
                "invalidated: record belongs to another worktree",
            ),
            (
                "other command",
                signed(command=["make", "test"]),
                "invalidated: stage command changed",
            ),
        ]
        for name, content, expected in cases:
            with self.subTest(name):
                path.write_text(content)
                self.assertIn(f"quality runs fresh: {expected}", self.decisions()["quality"])
        path.write_text(original)
        self.assertIn("would be reused", self.decisions()["quality"])

    def test_distinct_worktrees_never_share_evidence(self) -> None:
        linked = self.root / "linked"
        self.shell("git", "-C", str(self.work), "worktree", "add", "-b", "ci/linked", str(linked))
        other = Path(
            subprocess.run(
                ["git", "-C", str(linked), "rev-parse", "--absolute-git-dir"],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip()
        )
        self.assertNotEqual(other, self.metadata)
        decisions = self.decisions(cwd=linked)
        self.assertIn("quality runs fresh: miss: no record", decisions["quality"])
        (other / "florabase-stage-evidence").mkdir()
        for name in ("quality.json", "integration.json"):
            (other / "florabase-stage-evidence" / name).write_bytes(
                (self.evidence / name).read_bytes()
            )
        decisions = self.decisions(cwd=linked)
        for stage in ("quality", "integration"):
            self.assertIn(
                f"{stage} runs fresh: invalidated: record belongs to another worktree",
                decisions[stage],
            )


class ClosureClassificationTests(unittest.TestCase):
    """Unprovable mounts, volumes, images and Compose inputs must refuse a record."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name).resolve()
        (self.repo / "backend/src").mkdir(parents=True)
        (self.repo / "backend/Dockerfile").write_text("FROM python@sha256:aaaa AS development\n")
        self.quality = json.loads(json.dumps(QUALITY_MODEL).replace("@ROOT@", str(self.repo)))
        self.integration = json.loads(
            json.dumps(INTEGRATION_MODEL).replace("@ROOT@", str(self.repo))
        )
        self.models = {"quality": {"model": self.quality, "persistent": True}}
        self.mounts = model_mounts("quality", self.quality, self.repo)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def container(self, **overrides: Any) -> dict[str, Any]:
        labels = {
            "com.docker.compose.project": "florabase-quality-fixture",
            "com.docker.compose.service": "backend",
            "image": "florabase-quality-fixture-backend-development",
        }
        details = {
            "Image": "sha256:backend",
            "Mounts": [
                {"Type": "bind", "Source": f"{self.repo}/backend/src", "Destination": "/app/src"}
            ],
            "HostConfig": {},
            "Config": {"Entrypoint": None},
        }
        labels.update(overrides.pop("labels", {}))
        details.update(overrides)
        return {"labels": labels, "inspect": details, "image": "identity-" + details["Image"]}

    def refuses(self, containers: list[dict[str, Any]], message: str, models: Any = None) -> None:
        with self.assertRaises(Unknown) as error:
            observed(models or self.models, containers, self.repo, dict.fromkeys(self.mounts, "x"))
        self.assertIn(message, str(error.exception))

    def test_known_containers_classify(self) -> None:
        frontend = self.container(
            labels={
                "com.docker.compose.service": "frontend",
                "image": "florabase-quality-fixture-frontend-development",
            },
            Mounts=[
                {"Type": "bind", "Source": f"{self.repo}/frontend", "Destination": "/app"},
                {
                    "Type": "volume",
                    "Name": "florabase-quality-fixture_frontend_node_modules",
                    "Destination": "/app/node_modules",
                },
            ],
            Config={"Entrypoint": ["florabase-dev-entrypoint"]},
        )
        backend = self.container(
            Mounts=[
                {
                    "Type": "volume",
                    "Name": "florabase-quality-fixture_attachment_data",
                    "Destination": "/var/lib/florabase/attachments",
                }
            ]
        )
        result = observed(
            self.models, [backend, frontend], self.repo, dict.fromkeys(self.mounts, "x")
        )
        self.assertEqual(
            sorted(result["images"]),
            sorted(
                [
                    "florabase-quality-fixture-backend-development",
                    "florabase-quality-fixture-frontend-development",
                ]
            ),
        )
        self.assertEqual(
            result["volumes"],
            [
                "quality/backend: attachment_data (content digest)",
                "quality/frontend: frontend_node_modules (reinstalled by pnpm install --frozen-lockfile)",
            ],
        )
        with self.assertRaises(Unknown):
            stage_evidence.volume_digests(
                "integration",
                {"model": {**self.integration, "volumes": {"x": {}}}, "persistent": False},
            )

    def test_unprovable_runtime_inputs_refuse(self) -> None:
        outside = [{"Type": "bind", "Source": "/etc", "Destination": "/host"}]
        extra = [{"Type": "bind", "Source": f"{self.repo}/docs", "Destination": "/docs"}]
        mutable = [
            {
                "Type": "volume",
                "Name": "florabase-feature-review_postgres_data",
                "Destination": "/var/lib/postgresql",
            }
        ]
        anonymous = [{"Type": "volume", "Name": "a" * 64, "Destination": "/data"}]
        node_modules = [
            {
                "Type": "volume",
                "Name": "florabase-quality-fixture_frontend_node_modules",
                "Destination": "/m",
            }
        ]
        cases = [
            ([self.container(Mounts=outside)], "outside the repository"),
            ([self.container(Mounts=extra)], "not derivable from Compose configuration"),
            ([self.container(Mounts=mutable)], "unclassified mutable volume"),
            ([self.container(Mounts=anonymous)], "unclassified mutable volume"),
            (
                [self.container(Mounts=node_modules, Config={"Entrypoint": ["sh"]})],
                "unclassified mutable volume",
            ),
            (
                [self.container(Mounts=[{"Type": "npipe", "Source": "x", "Destination": "/x"}])],
                "unclassified npipe mount",
            ),
            (
                [self.container(labels={"com.docker.compose.project": "florabase-feature-review"})],
                "outside the stage's Compose models",
            ),
            (
                [self.container(labels={"com.docker.compose.service": "worker"})],
                "service outside the rendered model",
            ),
            (
                [self.container(), self.container(Image="sha256:rebuilt")],
                "changed while the stage ran",
            ),
            ([], "no container observed for quality"),
        ]
        for containers, message in cases:
            with self.subTest(message):
                self.refuses(containers, message)

    def test_disposable_images_require_digest_pinned_bases(self) -> None:
        models = {"integration": {"model": self.integration, "persistent": False}}
        tests = self.container(
            labels={
                "com.docker.compose.project": "florabase-integration-abcdefabcdef",
                "com.docker.compose.service": "tests",
                "io.florabase.workflow.lifecycle": "integration",
                "image": "florabase-integration-abcdefabcdef-tests",
            },
            Mounts=[],
        )
        mounts = model_mounts("integration", self.integration, self.repo)
        result = observed(models, [tests], self.repo, dict.fromkeys(mounts, "x"))
        self.assertEqual(
            result["images"], {"built integration/tests": "rebuilt from the pinned build context"}
        )
        for dockerfile in (
            "FROM python:3.14 AS development\n",
            "# syntax=docker/dockerfile:1\nFROM python@sha256:a\n",
            "#Syntax = docker/dockerfile:1\nFROM python@sha256:a\n",
            "FROM python@sha256:a AS base\nCOPY --from=ghcr.io/x/tool:latest /t /t\n",
            "FROM python@sha256:a AS base\nCOPY \\\n  # source\n  --from=node:24 /t /t\n",
            "# escape=\x60\nFROM python@sha256:a AS base\n",
            "FROM 123 AS development\n",
            "FROM python@sha256:a\nRUN --mount=type=cache,from=alpine,target=/c true\n",
            "FROM python@sha256:a\nADD https://example.invalid/x /x\n",
            'FROM python@sha256:a\nADD ["https://example.invalid/x", "/x"]\n',
        ):
            with self.subTest(dockerfile):
                (self.repo / "backend/Dockerfile").write_text(dockerfile)
                with self.assertRaises(Unknown):
                    observed(models, [tests], self.repo, dict.fromkeys(mounts, "x"))

    def test_unclassified_compose_inputs_refuse(self) -> None:
        cases = [
            ({"secrets": {"x": {"file": "/x"}}}, None, "configs/secrets"),
            ({}, {"env_file": ["x.env"]}, "env_file is not a classified input"),
            (
                {},
                {"build": {**self.quality["services"]["backend"]["build"], "ssh": ["default"]}},
                "unclassified build inputs",
            ),
            (
                {},
                {"volumes": [{"type": "npipe", "source": "x", "target": "/x"}]},
                "unclassified mount type",
            ),
            (
                {},
                {"volumes": [{"type": "bind", "source": "/var/run/docker.sock", "target": "/s"}]},
                "outside the repository",
            ),
        ]
        for top, service, message in cases:
            with self.subTest(message):
                model = json.loads(json.dumps(self.quality))
                model.update(top)
                if service:
                    model["services"]["backend"].update(service)
                with self.assertRaises(Unknown) as error:
                    model_mounts("quality", model, self.repo)
                self.assertIn(message, str(error.exception))

    def test_shadowed_bind_paths_and_tree_digest_cover_modes_links_and_ignored_files(self) -> None:
        mounts = model_mounts("quality", self.quality, self.repo)
        self.assertIn("frontend (excluding frontend/node_modules)", mounts)
        (self.repo / "frontend/node_modules").mkdir(parents=True)
        before = stage_evidence.tree_digest(self.repo, "frontend", ("frontend/node_modules",))
        (self.repo / "frontend/node_modules/cache").write_text("volume-shadowed")
        self.assertEqual(
            before, stage_evidence.tree_digest(self.repo, "frontend", ("frontend/node_modules",))
        )
        self.assertNotEqual(before, stage_evidence.tree_digest(self.repo, "frontend"))
        source = self.repo / "backend/src/app.py"
        source.write_text("x")
        digests = {stage_evidence.tree_digest(self.repo, "backend/src")}
        source.chmod(0o755)
        digests.add(stage_evidence.tree_digest(self.repo, "backend/src"))
        (self.repo / "backend/src/link").symlink_to("app.py")
        digests.add(stage_evidence.tree_digest(self.repo, "backend/src"))
        os.mkfifo(self.repo / "backend/src/pipe")
        self.assertEqual(len(digests), 3)
        with self.assertRaises(Unknown):
            stage_evidence.tree_digest(self.repo, "backend/src")

    def test_pinned_internal_sources_pass_and_host_symlinks_cannot_leave_the_repository(
        self,
    ) -> None:
        (self.repo / "backend/Dockerfile").write_text(
            "# syntax=docker/dockerfile:1.7@sha256:a\nFROM python@sha256:b AS base\n"
            "FROM base AS development\nCOPY --from=base /x /x\n"
            "COPY --from=node@sha256:c /n /n\n"
        )
        stage_evidence.require_pinned(self.repo, self.quality["services"]["backend"]["build"])
        (self.repo / "scripts").mkdir()
        (self.repo / "scripts/tool.py").write_text("x")
        self.assertIn("scripts", stage_evidence.host_closure(self.repo))
        (self.repo / "scripts/escape").symlink_to("/etc/hostname")
        with self.assertRaises(Unknown) as error:
            stage_evidence.host_closure(self.repo)
        self.assertIn("leaves the repository", str(error.exception))

    def test_atomic_write_leaves_complete_record_or_previous_state(self) -> None:
        path = self.repo / "evidence/quality.json"
        stage_evidence.write_record(path, {"value": 1})
        with unittest.mock.patch("os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                stage_evidence.write_record(path, {"value": 2})
        self.assertEqual(json.loads(path.read_text())["value"], 1)
        self.assertEqual([p.name for p in path.parent.iterdir()], ["quality.json"])

    def test_host_program_symlink_requires_a_measured_target(self) -> None:
        scripts = self.repo / "scripts"
        scripts.mkdir()
        (scripts / "tool.sh").write_text("exit 0")
        (scripts / "measured").symlink_to("tool.sh")
        first = stage_evidence.host_closure(self.repo)
        (scripts / "tool.sh").write_text("exit 1")
        self.assertNotEqual(stage_evidence.host_closure(self.repo), first)

        docs = self.repo / "docs"
        docs.mkdir()
        (scripts / "another.sh").write_text("exit 2")
        alias = docs / "alias"
        alias.symlink_to("../scripts/tool.sh")
        (scripts / "indirect").symlink_to("../docs/alias")
        first = stage_evidence.host_closure(self.repo)
        alias.unlink()
        alias.symlink_to("../scripts/another.sh")
        self.assertNotEqual(stage_evidence.host_closure(self.repo), first)

        (docs / "unmeasured.sh").write_text("exit 0")
        (scripts / "unmeasured").symlink_to("../docs/unmeasured.sh")
        with self.assertRaisesRegex(Unknown, "host program symlink leaves the input closure"):
            stage_evidence.host_closure(self.repo)


FEATURE_WORKFLOW_SUITES = [
    "test-workflow-helpers",
    "test-feature-workflow",
    "test-agent-workflow",
    "test-preview-workflow",
    "test-environment-workflow",
    "test-uat-preview",
    "test-verification-impact",
    "test-workflow-resources",
    "workflow-check",
    "verify-build SERVICES=backend frontend",
]

del EvidenceFixture

if __name__ == "__main__":
    unittest.main()
