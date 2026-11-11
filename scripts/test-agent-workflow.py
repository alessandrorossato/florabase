#!/usr/bin/env python3
"""Offline regressions for provider-neutral worktrees, writers, handoffs, locks and retirement.

Real Git and real kernel locks run on disposable fixtures. Provider identities are only AGENT_ID
values, GitHub and Docker are PATH mocks, and every Docker argument is recorded and asserted.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import itertools
import json
import os
import pty
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import unittest
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock, patch

import feature_worktree
import sourcing_preview
import workflow_environment
from workflow_environment import (
    COMPOSE_MUTATING,
    COMPOSE_READ_ONLY,
    Environment,
    Repository,
)
from workflow_resources import ResourceError, machine_lock

ROOT = Path(__file__).resolve().parent.parent
HELPER = ROOT / "scripts/feature_worktree.py"
GITHUB = "https://github.com/alessandrorossato/florabase.git"
ENVIRONMENT = ROOT / "scripts/workflow_environment.py"
SOURCING = ROOT / "scripts/sourcing_preview.py"
# A copy that is valid on every route, so only the guard under test can refuse it.
SAFE_COPY = ["cp", "./file", "backend:/tmp/file"]
REPORT = {
    "completed": ["implemented lifecycle"],
    "tests": ["make test-agent-workflow"],
    "defects": [],
    "next_action": "independent QA",
}


class AgentWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="florabase agent workflow ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.remote = self.root / "remote.git"
        self.primary = self.root / "florabase"
        self.managed = self.root / "florabase-worktrees"
        self.docker_log = self.root / "docker.log"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.reports = itertools.count()
        self.git(self.root, "init", "--bare", "--initial-branch=main", str(self.remote))
        self.git(self.root, "init", "--initial-branch=main", str(self.primary))
        for key, value in (
            ("user.name", "Workflow Test"),
            ("user.email", "workflow@example.invalid"),
            (f"url.{self.remote}.insteadOf", GITHUB),
        ):
            self.git(self.primary, "config", key, value)
        self.git(self.primary, "remote", "add", "origin", GITHUB)
        (self.primary / ".gitignore").write_text(".env\n__pycache__/\n")
        (self.primary / "tracked.txt").write_text("base\n")
        self.git(self.primary, "add", ".")
        self.git(self.primary, "commit", "-m", "base")
        self.git(self.primary, "push", "-u", "origin", "main")
        self.write_tool(
            "docker",
            'printf \'%s\\n\' "$*" >>"${DOCKER_LOG}"\n'
            'if [[ -n "${MOCK_DOCKER_FAIL:-}" ]]; then exit 1; fi\n'
            'if [[ "$1 ${2:-}" == "ps -a" && "$*" == *"source=${MOCK_OWNED_SOURCE:-none}"* ]]; then\n'
            "  printf 'florabase-feature-review\\trunning\\n'\nfi\n"
            'if [[ "$1 ${2:-}" == "volume ls" && "$*" == *"source=${MOCK_VOLUME_SOURCE:-none}"* ]]; then\n'
            "  printf 'florabase-uat-preview\\tflorabase-uat-preview_postgres_data\\n'\nfi\n",
        )

    def write_tool(self, name: str, body: str) -> None:
        path = self.bin / name
        path.write_text("#!/usr/bin/env bash\nset -eu\n" + body)
        path.chmod(0o755)

    @staticmethod
    def git(path: Path, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(path), *args],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        ).stdout.strip()

    def env(self, **values: str) -> dict[str, str]:
        env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "DOCKER_LOG": str(self.docker_log),
            "FLORABASE_LOCK_DIR": str(self.root / "locks"),
            **values,
        }
        for key in (
            "AGENT_ID",
            "BRANCH",
            "TAKEOVER",
            "TO",
            "REPORT",
            "FEATURE",
            "CONFIRM_RETIRE",
            "FLORABASE_WORKTREE_ROOT",
        ):
            if key not in values:
                env.pop(key, None)
        return env

    def helper(
        self, cwd: Path, command: str, *args: str, **values: str
    ) -> subprocess.CompletedProcess[str]:
        # Never inherit the runner's stdin: a gate launched from a terminal would otherwise turn
        # every agent call into an operator call. Only terminal() supplies a real PTY.
        return subprocess.run(
            [sys.executable, str(HELPER), command, *args],
            cwd=cwd,
            env=self.env(**values),
            stdin=subprocess.DEVNULL,
            text=True,
            capture_output=True,
        )

    def ok(self, cwd: Path, command: str, *args: str, **values: str) -> str:
        result = self.helper(cwd, command, *args, **values)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def refused(self, needle: str, cwd: Path, command: str, **values: str) -> None:
        result = self.helper(cwd, command, **values)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn(needle, result.stderr)

    def terminal(self, cwd: Path, command: str, **values: str) -> subprocess.CompletedProcess[str]:
        """Run as an operator at a real pseudo-terminal, which takeover requires."""
        parent, child = pty.openpty()
        self.addCleanup(os.close, parent)
        self.addCleanup(os.close, child)
        return subprocess.run(
            [sys.executable, str(HELPER), command],
            cwd=cwd,
            env=self.env(**values),
            stdin=child,
            text=True,
            capture_output=True,
        )

    def create(self, branch: str = "feat/example-001") -> Path:
        self.ok(self.primary, "create", BRANCH=branch)
        return self.managed / branch.split("/", 1)[1]

    def report(self, **changes: object) -> str:
        path = self.root / f"report-{next(self.reports)}.json"
        path.write_text(json.dumps({**REPORT, **changes}))
        return str(path)

    def context(self, cwd: Path) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(self.ok(cwd, "context", "--json")))

    def advance_main(self) -> str:
        seed = self.root / "seed"
        if not seed.exists():
            self.git(self.root, "clone", str(self.remote), str(seed))
            self.git(seed, "config", "user.name", "Workflow Test")
            self.git(seed, "config", "user.email", "workflow@example.invalid")
        self.git(seed, "pull", "--ff-only")
        (seed / "main.txt").write_text(
            str(self.docker_log.stat().st_mtime_ns if self.docker_log.exists() else 0)
        )
        self.git(seed, "add", ".")
        self.git(seed, "commit", "-m", "main moved")
        self.git(seed, "push", "origin", "main")
        return self.git(seed, "rev-parse", "HEAD")

    # Creation --------------------------------------------------------------------------------

    def test_new_feature_is_created_from_fetched_main_beside_untouched_primary(self) -> None:
        moved = self.advance_main()
        worktree = self.create()
        self.assertEqual(self.git(worktree, "rev-parse", "HEAD"), moved)
        self.assertEqual(self.git(worktree, "branch", "--show-current"), "feat/example-001")
        with self.assertRaises(subprocess.CalledProcessError):
            self.git(worktree, "rev-parse", "--abbrev-ref", "@{upstream}")
        self.assertEqual(self.git(self.primary, "branch", "--show-current"), "main")
        self.assertEqual(self.git(self.primary, "status", "--porcelain"), "")
        value = self.context(worktree)
        self.assertEqual(value["base"], moved)
        self.assertEqual(value["feature_id"], "example-001")
        self.assertEqual(value["primary"], str(self.primary))
        self.assertIsNone(value["writer"])

    def test_invalid_and_colliding_names_are_refused_without_new_state(self) -> None:
        for branch in ("", "main", "feat/../../evil", "feature/x", "feat/UPPER"):
            self.refused("BRANCH must use", self.primary, "create", BRANCH=branch)
        self.create("feat/same")
        before = self.git(self.primary, "worktree", "list")
        self.refused("branch already exists", self.primary, "create", BRANCH="feat/same")
        self.refused("worktree path already exists", self.primary, "create", BRANCH="fix/same")
        self.assertEqual(self.git(self.primary, "worktree", "list"), before)
        self.assertEqual(self.git(self.primary, "branch", "--list", "fix/same"), "")
        self.git(self.primary, "push", "origin", "main:refs/heads/feat/remote-only")
        self.refused(
            "remote branch already exists", self.primary, "create", BRANCH="feat/remote-only"
        )

    def test_primary_off_main_or_diverged_main_is_refused(self) -> None:
        (self.primary / "tracked.txt").write_text("diverged\n")
        self.git(self.primary, "commit", "-am", "local only")
        self.advance_main()
        self.refused("diverged", self.primary, "create", BRANCH="feat/diverged")
        self.git(self.primary, "switch", "-c", "feat/primary-moved")
        self.refused("must stay on main", self.primary, "create", BRANCH="feat/other")

    def test_wrong_origin_is_refused(self) -> None:
        self.git(self.primary, "remote", "set-url", "origin", "https://github.com/example/wrong")
        self.refused("expected Florabase", self.primary, "create", BRANCH="feat/origin")

    # Attachment ------------------------------------------------------------------------------

    def test_attach_is_read_only_and_allows_dirty_existing_worktrees(self) -> None:
        worktree = self.create()
        (worktree / "wip.txt").write_text("uncommitted\n")
        digest = self.context(worktree)["worktree_digest"]
        for cwd in (self.primary, worktree):
            output = self.ok(cwd, "attach", BRANCH="feat/example-001")
            self.assertIn(f"worktree: {worktree}", output)
            self.assertIn("dirty: True", output)
        self.assertEqual(self.context(worktree)["worktree_digest"], digest)
        self.assertIsNone(self.context(worktree)["writer"])

    def test_attach_refuses_missing_primary_and_unexpected_branch(self) -> None:
        self.refused("no worktree has", self.primary, "attach", BRANCH="feat/absent")
        self.refused("BRANCH must use", self.primary, "attach", BRANCH="main")
        worktree = self.create()
        self.refused("unexpected branch", worktree, "context", BRANCH="feat/other")
        self.git(self.primary, "switch", "-c", "feat/in-primary")
        self.refused("primary must stay on main", worktree, "attach", BRANCH="feat/in-primary")
        self.git(self.primary, "switch", "main")

    def test_unrelated_history_is_a_wrong_base_and_stale_base_is_reported(self) -> None:
        worktree = self.create()
        self.advance_main()
        self.git(worktree, "fetch", "origin", "main")
        self.assertEqual(self.context(worktree)["behind_main"], 1)
        self.git(worktree, "switch", "--orphan", "feat/unrelated")
        (worktree / "other.txt").write_text("other\n")
        self.git(worktree, "add", ".")
        self.git(worktree, "commit", "-m", "unrelated")
        self.refused("wrong base", worktree, "context")
        self.refused("wrong base", worktree, "claim", AGENT_ID="codex")
        metadata = Path(self.git(worktree, "rev-parse", "--absolute-git-dir"))
        self.assertFalse((metadata / "info/florabase-agent-state.json").exists())

    # Writer ownership and handoff ------------------------------------------------------------

    def test_claude_to_codex_to_opencode_sequential_handoff(self) -> None:
        worktree = self.create()
        self.ok(worktree, "claim", AGENT_ID="claude-code")
        self.refused("claude-code holds", worktree, "claim", AGENT_ID="codex")
        again = self.ok(worktree, "claim", AGENT_ID="claude-code")  # New session, same writer.
        self.assertIn("each session needs its own AGENT_ID", again)
        (worktree / "wip.txt").write_text("dirty work crosses the handoff\n")
        self.refused(
            "only the current writer",
            worktree,
            "handoff",
            AGENT_ID="codex",
            TO="opencode",
            REPORT=self.report(),
        )
        self.ok(worktree, "handoff", AGENT_ID="claude-code", TO="codex", REPORT=self.report())
        # Released but not accepted: nobody can run gates, and a third party cannot claim.
        self.refused("is pending", worktree, "require-writer", AGENT_ID="claude-code")
        self.refused("is pending", worktree, "require-operator")
        self.refused("addressed to codex", worktree, "claim", AGENT_ID="opencode")
        accepted = self.ok(worktree, "claim", AGENT_ID="codex")
        self.assertIn("REPORTED by the previous agent, not verified", accepted)
        self.assertIn("receipt: invalid", accepted)  # The report cannot assert verification.
        self.ok(worktree, "require-writer", AGENT_ID="codex")
        self.refused("codex holds", worktree, "require-writer", AGENT_ID="claude-code")
        self.refused("codex holds", worktree, "require-writer")

        self.ok(worktree, "handoff", AGENT_ID="codex", TO="opencode", REPORT=self.report())
        self.ok(worktree, "claim", AGENT_ID="opencode")
        value = self.context(worktree)
        self.assertEqual(value["writer"]["agent"], "opencode")
        self.assertEqual(value["handoff"]["from"], "codex")
        self.assertEqual(value["handoff"]["head"], value["head"])
        self.assertEqual(value["handoff"]["head_tree"], value["head_tree"])
        self.assertEqual(value["handoff"]["base"], value["base"])
        self.assertEqual(value["handoff"]["report"], REPORT)

    def test_receiver_detects_tree_or_commit_drift_after_handoff(self) -> None:
        worktree = self.create()
        self.ok(worktree, "claim", AGENT_ID="claude-code")
        self.ok(worktree, "handoff", AGENT_ID="claude-code", TO="codex", REPORT=self.report())
        (worktree / "tracked.txt").write_text("changed after handoff\n")
        self.refused("worktree_digest", worktree, "claim", AGENT_ID="codex")
        self.git(worktree, "commit", "-am", "changed after handoff")
        self.refused("head", worktree, "claim", AGENT_ID="codex")
        handoff = self.context(worktree)["handoff"]["id"]
        self.refused("interactive terminal", worktree, "claim", AGENT_ID="codex", TAKEOVER=handoff)
        wrong = self.terminal(worktree, "claim", AGENT_ID="codex", TAKEOVER="wrong")
        self.assertEqual(wrong.returncode, 1)
        self.assertIn("worktree_digest", wrong.stderr)
        self.assertNotIn(handoff, wrong.stderr)
        accepted = self.terminal(worktree, "claim", AGENT_ID="codex", TAKEOVER=handoff)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertEqual(self.context(worktree)["writer"]["takeover_of"], handoff)

    def test_invalid_handoff_reports_and_identities_leave_writer_unchanged(self) -> None:
        worktree = self.create()
        self.refused("AGENT_ID is required", worktree, "claim")
        self.refused("safe lowercase", worktree, "claim", AGENT_ID="Bad Name")
        self.ok(worktree, "claim", AGENT_ID="codex")
        for report, needle in (
            (self.report(unknown="x"), "needs exactly"),
            (self.report(tests="make check"), "list of strings"),
            (self.report(next_action=" "), "next permitted action"),
            (str(self.root / "missing.json"), "must be a file"),
        ):
            self.refused(
                needle, worktree, "handoff", AGENT_ID="codex", TO="opencode", REPORT=report
            )
        self.refused("TO must name", worktree, "handoff", AGENT_ID="codex", REPORT=self.report())
        inside = worktree / "report.json"
        inside.write_text(json.dumps(REPORT))
        self.refused(
            "outside the worktree",
            worktree,
            "handoff",
            AGENT_ID="codex",
            TO="opencode",
            REPORT=str(inside),
        )
        inside.unlink()
        self.assertEqual(self.context(worktree)["writer"]["agent"], "codex")
        self.assertIsNone(self.context(worktree)["handoff"])

    def test_interrupted_writer_requires_exact_takeover_and_corrupt_state_fails_closed(
        self,
    ) -> None:
        worktree = self.create()
        self.ok(worktree, "claim", AGENT_ID="claude-code")
        claim = self.context(worktree)["writer"]["claim_id"]
        # A dead session leaves its claim. Nothing expires it silently, and refusals never reveal it.
        refused = self.helper(worktree, "claim", AGENT_ID="codex")
        self.assertNotIn(claim, refused.stderr + refused.stdout)
        self.refused("interactive terminal", worktree, "claim", AGENT_ID="codex", TAKEOVER=claim)
        guess = self.terminal(worktree, "claim", AGENT_ID="codex", TAKEOVER="guess")
        self.assertEqual(guess.returncode, 1)
        taken = self.terminal(worktree, "claim", AGENT_ID="codex", TAKEOVER=claim)
        self.assertEqual(taken.returncode, 0, taken.stderr)
        self.assertEqual(self.context(worktree)["writer"]["takeover_of"], claim)
        metadata = Path(self.git(worktree, "rev-parse", "--absolute-git-dir"))
        (metadata / "info/florabase-agent-state.json").write_text("{ interrupted")
        self.refused("unreadable writer state", worktree, "require-writer", AGENT_ID="codex")
        self.refused("unreadable writer state", worktree, "claim", AGENT_ID="codex")

    def test_parallel_features_and_read_only_reviewers_are_independent(self) -> None:
        first, second = self.create("feat/first"), self.create("fix/second")
        self.ok(first, "claim", AGENT_ID="claude-code")
        self.ok(second, "claim", AGENT_ID="codex")
        self.assertEqual(self.context(first)["writer"]["agent"], "claude-code")
        self.assertEqual(self.context(second)["writer"]["agent"], "codex")
        # A reviewer's detached checkout has its own metadata and never affects the writer.
        review = self.root / "review"
        self.git(self.primary, "worktree", "add", "--detach", str(review), "feat/first")
        self.assertIsNone(self.context(review)["writer"])
        self.ok(review, "require-writer", AGENT_ID="opencode")
        self.assertEqual(self.context(first)["writer"]["agent"], "claude-code")

    def test_simultaneous_claims_have_exactly_one_writer(self) -> None:
        worktree = self.create()
        claims = [
            subprocess.Popen(
                [sys.executable, str(HELPER), "claim"],
                cwd=worktree,
                env=self.env(AGENT_ID=f"agent-{index}"),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            for index in range(6)
        ]
        results = [claim.wait() for claim in claims]
        self.assertEqual(results.count(0), 1, results)
        winner = results.index(0)
        self.assertEqual(self.context(worktree)["writer"]["agent"], f"agent-{winner}")

    # Locks -----------------------------------------------------------------------------------

    def hold(self, cwd: Path, expression: str) -> subprocess.Popen[str]:
        program = (
            f"import sys; sys.path.insert(0, {str(ROOT / 'scripts')!r})\n"
            "from pathlib import Path\n"
            "from workflow_resources import FileLock, machine_lock, verification_lock\n"
            f"with {expression}:\n"
            "    print('held', flush=True)\n"
            "    sys.stdin.read()\n"
        )
        holder = subprocess.Popen(
            [sys.executable, "-c", program],
            cwd=cwd,
            env=self.env(),
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        assert holder.stdin and holder.stdout
        self.addCleanup(holder.wait)
        self.addCleanup(holder.stdin.close)
        self.addCleanup(holder.stdout.close)
        self.assertEqual(holder.stdout.readline().strip(), "held")
        return holder

    @staticmethod
    def release(holder: subprocess.Popen[str]) -> None:
        assert holder.stdin
        holder.stdin.close()
        holder.wait()

    def test_running_gate_blocks_handoff_takeover_delivery_and_retire_until_killed(self) -> None:
        worktree = self.create()
        self.ok(worktree, "claim", AGENT_ID="claude-code")
        claim = self.context(worktree)["writer"]["claim_id"]
        metadata = Path(self.git(worktree, "rev-parse", "--absolute-git-dir"))
        holder = self.hold(worktree, f"verification_lock(Path({str(metadata)!r}))")
        running = "verification of this worktree is already running"
        blocked = self.terminal(worktree, "claim", AGENT_ID="codex", TAKEOVER=claim)
        self.assertEqual(blocked.returncode, 1)
        self.assertIn(running, blocked.stderr)
        self.refused(
            running, worktree, "handoff", AGENT_ID="claude-code", TO="codex", REPORT=self.report()
        )
        self.refused(running, worktree, "require-operator")
        self.assertEqual(self.context(worktree)["writer"]["agent"], "claude-code")
        os.kill(holder.pid, signal.SIGKILL)
        holder.wait()
        # SIGKILL cannot run cleanup; the kernel released the lock and state is still explicit.
        self.ok(worktree, "require-operator")
        taken = self.terminal(worktree, "claim", AGENT_ID="codex", TAKEOVER=claim)
        self.assertEqual(taken.returncode, 0, taken.stderr)

    def test_machine_lock_spans_separate_clones(self) -> None:
        clone = self.root / "separate clone"
        self.git(self.root, "clone", str(self.remote), str(clone))
        holder = self.hold(self.primary, "machine_lock('verification-full', 'canonical FULL')")
        program = (
            f"import sys; sys.path.insert(0, {str(ROOT / 'scripts')!r})\n"
            "from workflow_resources import machine_lock\n"
            "with machine_lock('verification-full', 'canonical FULL'): pass\n"
        )
        contended = subprocess.run(
            [sys.executable, "-c", program],
            cwd=clone,
            env=self.env(),
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(contended.returncode, 0)
        self.assertIn(f'"pid": {holder.pid}', contended.stderr)
        self.assertIn(str(self.primary), contended.stderr)
        self.release(holder)
        recovered = subprocess.run(
            [sys.executable, "-c", program], cwd=clone, env=self.env(), capture_output=True
        )
        self.assertEqual(recovered.returncode, 0, recovered.stderr)

    def test_review_lifecycle_is_serialized_across_sources_before_any_docker_change(self) -> None:
        first, second = self.create("feat/first"), self.create("fix/second")
        holder = self.hold(first, "machine_lock('florabase-feature-review', 'review lifecycle')")
        self.docker_log.unlink(missing_ok=True)
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/workflow_environment.py"), "review", "up"],
            cwd=second,
            env=self.env(),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("review lifecycle is already running", result.stderr)
        self.assertFalse(self.docker_log.exists(), "contended Review must not reach Docker")
        self.release(holder)

    def test_review_compose_mutations_need_lock_and_writer_but_reads_do_not(self) -> None:
        worktree = self.create()
        environment = str(ROOT / "scripts/workflow_environment.py")
        compose = [sys.executable, environment, "review", "compose", "--", "run", "backend", "true"]
        self.ok(worktree, "claim", AGENT_ID="codex")
        self.docker_log.unlink(missing_ok=True)
        result = subprocess.run(
            compose, cwd=worktree, env=self.env(), capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("codex holds this worktree", result.stderr)
        self.assertFalse(self.docker_log.exists())
        holder = self.hold(worktree, "machine_lock('florabase-feature-review', 'review lifecycle')")
        result = subprocess.run(
            compose, cwd=worktree, env=self.env(AGENT_ID="codex"), capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("review lifecycle is already running", result.stderr)
        self.assertFalse(self.docker_log.exists())
        self.release(holder)

    def test_uat_lifecycle_is_serialized_across_sources_before_any_docker_change(self) -> None:
        first, second = self.create("feat/first"), self.create("fix/second")
        holder = self.hold(first, "machine_lock('florabase-uat-preview', 'uat lifecycle')")
        self.docker_log.unlink(missing_ok=True)
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/uat_preview.py"), "up"],
            cwd=second,
            env=self.env(),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("lifecycle is already running", result.stderr)
        self.assertFalse(self.docker_log.exists())
        self.release(holder)

    def test_shared_environment_owner_is_reported_for_a_foreign_review(self) -> None:
        worktree = self.create()
        self.write_tool(
            "docker",
            'if [[ "$*" == *"project=florabase-feature-review"* ]]; then echo /other/source; fi\n',
        )
        value = self.context(worktree)["shared_environment_owners"]
        self.assertEqual(value["florabase-feature-review"], ["/other/source"])
        self.assertEqual(value["florabase-uat-preview"], [])

    def test_agent_identity_does_not_break_nested_operator_fixtures(self) -> None:
        # A claimed worktree's FULL exports AGENT_ID through make into every workflow suite.
        env = self.env(AGENT_ID="codex")
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/test-feature-workflow.py"),
                "VerifyHelperTests.test_delivery_preflight_rejects_invalid_full_cycle_and_historical_v2",
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_mark_finished_cannot_clear_an_active_writer(self) -> None:
        worktree = self.create()
        self.ok(worktree, "claim", AGENT_ID="codex")
        sha = self.git(worktree, "rev-parse", "HEAD")
        args = ("--branch", "feat/example-001", "--sha", sha, "--merge", sha)
        self.assertEqual(self.helper(worktree, "mark-finished", *args).returncode, 1)
        self.git(worktree, "switch", "--detach")
        moved = ("--branch", "feat/example-001", "--sha", "0" * 40, "--merge", sha)
        self.assertEqual(self.helper(worktree, "mark-finished", *moved).returncode, 1)
        self.refused("codex holds", worktree, "require-writer")

    def test_mark_finished_enforces_handoff_lock_and_symlink_guards(self) -> None:
        worktree = self.create("feat/example-002")
        self.ok(worktree, "claim", AGENT_ID="claude-code")
        sha = self.git(worktree, "rev-parse", "HEAD")
        merge = self.git(self.primary, "rev-parse", "HEAD")
        self.ok(worktree, "handoff", AGENT_ID="claude-code", TO="codex", REPORT=self.report())
        self.git(worktree, "switch", "--detach")
        metadata = Path(self.git(worktree, "rev-parse", "--absolute-git-dir"))
        state_file = metadata / "info/florabase-agent-state.json"
        proof_file = metadata / "info/florabase-finished.json"
        args = ("mark-finished", "--branch", "feat/example-002", "--sha", sha, "--merge", merge)

        def assert_refused(needle: str, expected_state: str) -> None:
            result = self.helper(worktree, *args, AGENT_ID="operator")
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn(needle, result.stderr)
            self.assertEqual(state_file.read_text(), expected_state)

        state_before = state_file.read_text()
        assert_refused("is pending", state_before)
        self.assertFalse(proof_file.exists())

        # Accept the handoff on the branch, detach again, then test lock and symlink refusal.
        self.git(worktree, "switch", "feat/example-002")
        self.ok(worktree, "claim", AGENT_ID="codex")
        self.git(worktree, "switch", "--detach")
        claimed_state = state_file.read_text()

        holder = self.hold(worktree, f"verification_lock(Path({str(metadata)!r}))")
        try:
            assert_refused("already running", claimed_state)
            self.assertFalse(proof_file.exists())
        finally:
            self.release(holder)

        outside = self.root / "outside-proof.json"
        outside.write_text("sentinel\n")
        proof_file.parent.mkdir(parents=True, exist_ok=True)
        proof_file.symlink_to(outside)
        assert_refused("symlinked finish proof", claimed_state)
        self.assertEqual(outside.read_text(), "sentinel\n")
        proof_file.unlink()

        self.ok(worktree, *args, AGENT_ID="operator")
        self.assertTrue(proof_file.is_file())
        self.assertFalse(state_file.exists())

    # Compose passthrough -----------------------------------------------------------------------

    def compose_cli(
        self, cwd: Path, role: str, *command: str, **values: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ENVIRONMENT), role, "compose", "--", *command],
            cwd=cwd,
            env=self.env(**values),
            capture_output=True,
            text=True,
        )

    def compose_refused(
        self, needle: str, cwd: Path, role: str, *command: str, **values: str
    ) -> None:
        """A refusal must name its reason and leave Docker, including persistent state, untouched."""
        self.docker_log.unlink(missing_ok=True)
        result = self.compose_cli(cwd, role, *command, **values)
        self.assertEqual(result.returncode, 1, (role, command, result.stdout))
        self.assertIn(needle, result.stderr, (role, command))
        self.assertFalse(self.docker_log.exists(), (role, command, "reached Docker"))

    def compose_allowed(
        self, cwd: Path, role: str, *command: str, **values: str
    ) -> list[tuple[str, ...]]:
        """Run main() in process with Docker mocked at the Compose call, returning those calls."""
        with (
            contextlib.chdir(cwd),
            patch.dict(os.environ, self.env(**values), clear=True),
            patch("sys.argv", ["workflow", role, "compose", "--", *command]),
            patch.object(Environment, "validate"),
            patch.object(Environment, "require_owner"),
            patch.object(Environment, "prepare_initializer"),
            patch.object(Environment, "compose") as compose,
            contextlib.redirect_stderr(io.StringIO()) as stderr,
        ):
            self.assertEqual(workflow_environment.main(), 0, stderr.getvalue())
        return [call.args for call in compose.call_args_list]

    def test_compose_policy_classifies_every_installed_verb_exactly_once(self) -> None:
        # docker compose --help, Docker Compose v5.6.1. A new verb is refused until classified.
        installed = set(
            "attach bridge build commit config cp create down events exec export images kill logs "
            "ls pause port ps publish pull push restart rm run scale start stats stop top unpause "
            "up version volumes wait watch".split()
        )
        self.assertEqual(COMPOSE_READ_ONLY | COMPOSE_MUTATING, installed)
        self.assertEqual(COMPOSE_READ_ONLY & COMPOSE_MUTATING, set())

    def test_every_mutating_verb_needs_the_writer_on_review_and_sourcing(self) -> None:
        worktree = self.create()
        self.ok(worktree, "claim", AGENT_ID="codex")
        for role in ("review", "sourcing"):
            for verb in sorted(COMPOSE_MUTATING):
                # cp and watch were the verbs that bypassed the original denylist.
                command = SAFE_COPY if verb == "cp" else [verb]
                self.compose_refused("codex holds this worktree", worktree, role, *command)
                self.compose_refused(
                    "codex holds this worktree", worktree, role, *command, AGENT_ID="opencode"
                )

    def test_doubled_separator_cannot_disguise_a_mutating_verb(self) -> None:
        worktree = self.create()
        self.ok(worktree, "claim", AGENT_ID="codex")
        self.docker_log.unlink(missing_ok=True)
        for command in (["--", *SAFE_COPY], ["--", "watch"]):
            result = self.compose_cli(worktree, "review", *command, AGENT_ID="opencode")
            self.assertEqual(result.returncode, 1, command)
            self.assertFalse(self.docker_log.exists(), command)

    def test_cp_and_watch_are_blocked_by_a_pending_handoff(self) -> None:
        worktree = self.create()
        self.ok(worktree, "claim", AGENT_ID="codex")
        self.ok(worktree, "handoff", AGENT_ID="codex", TO="opencode", REPORT=self.report())
        for command in (SAFE_COPY, ["watch"]):
            self.compose_refused("is pending", worktree, "review", *command, AGENT_ID="codex")
            self.compose_refused("is pending", worktree, "review", *command, AGENT_ID="opencode")

    def test_every_mutating_verb_respects_lifecycle_lock_contention(self) -> None:
        other, worktree = self.create("feat/other"), self.create("fix/current")
        self.ok(worktree, "claim", AGENT_ID="codex")
        for role, project in (
            ("review", "florabase-feature-review"),
            ("sourcing", "florabase-sourcing-preview"),
        ):
            holder = self.hold(other, f"machine_lock({project!r}, 'held lifecycle')")
            for verb in sorted(COMPOSE_MUTATING):
                command = SAFE_COPY if verb == "cp" else [verb]
                self.compose_refused(
                    "lifecycle is already running", worktree, role, *command, AGENT_ID="codex"
                )
            self.release(holder)
        holder = self.hold(other, "machine_lock('florabase', 'held lifecycle')")
        for verb in ("build", "exec", "pull", "run"):
            self.compose_refused("lifecycle is already running", worktree, "dev", verb)
        self.release(holder)

    def test_unknown_and_flag_first_subcommands_fail_closed_on_every_route(self) -> None:
        worktree = self.create()
        for role in ("review", "sourcing", "dev", "quality", "prod"):
            for verb in ("frobnicate", "alpha", "CP", "volume"):
                self.compose_refused("unknown Compose subcommand", worktree, role, verb)
            for command in (
                ["--project-name", "florabase-prod", "cp"],
                ["-f", "other.yaml", "watch"],
                ["--dry-run", "down"],
            ):
                self.compose_refused("provide a Compose subcommand", worktree, role, *command)
        self.docker_log.unlink(missing_ok=True)
        result = subprocess.run(
            [sys.executable, str(ENVIRONMENT), "review", "compose"],
            cwd=worktree,
            env=self.env(),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.docker_log.exists())

    def test_config_writing_a_host_file_is_guarded_but_config_flags_stay_readable(self) -> None:
        worktree = self.create()
        self.ok(worktree, "claim", AGENT_ID="codex")
        for option in (
            ["-o", "out"],
            ["--output", "out"],
            ["--output=out"],
            ["-qo", "out"],
            ["-oout"],
        ):
            self.compose_refused("codex holds", worktree, "review", "config", *option)
        for option in (
            ["--volumes"],
            ["--services"],
            ["-q"],
            ["--no-normalize"],
            ["--format", "json"],
        ):
            self.assertEqual(
                self.compose_allowed(worktree, "review", "config", *option),
                [("config", *option)],
            )

    def test_volume_deletion_forms_are_refused_even_for_the_writer(self) -> None:
        worktree = self.create()
        self.ok(worktree, "claim", AGENT_ID="codex")
        for role in ("review", "sourcing"):
            for command in (
                ["down", "-v"],
                ["down", "--volumes"],
                ["down", "--volumes=true"],
                ["down", "--remove-orphans", "-v"],
                ["rm", "-v"],
                ["rm", "-fsv"],
                ["rm", "--volumes", "backend"],
            ):
                self.compose_refused(
                    "exact project confirmation", worktree, role, *command, AGENT_ID="codex"
                )
        self.assertEqual(
            self.compose_allowed(worktree, "review", "rm", "-f", "backend", AGENT_ID="codex"),
            [("rm", "-f", "backend")],
        )

    def test_cp_cannot_reach_persistent_paths_on_any_route_or_in_any_form(self) -> None:
        worktree = self.create()
        self.ok(worktree, "claim", AGENT_ID="codex")
        for role in ("review", "sourcing", "dev", "quality", "prod"):
            for command in (
                ["./f", "db:/var/lib/postgresql/data/base"],
                ["./f", "db:/var/lib/postgresql"],
                ["./f", "db:/var/lib"],
                ["./f", "db:/"],
                ["./f", "db://var/lib/postgresql/data"],
                ["./f", "db:/tmp/../var/lib/postgresql/data"],
                ["./f", "backend:/var/lib/florabase/attachments/x"],
                ["./f", "backend:/tmp/florabase-attachments/x"],
                ["./f", "frontend:/app/node_modules/x"],
                ["-", "db:/var/lib/postgresql/data"],
                ["--archive", "./f", "db:/var/lib/postgresql/data"],
                ["./f", "db:/var/lib/postgresql/data", "--index", "1"],
                ["db:/var/lib/postgresql/data", "./exfiltrated"],
            ):
                self.compose_refused(
                    "persistent container state", worktree, role, "cp", *command, AGENT_ID="codex"
                )
            for target in ("frontend:node_modules/x", "db:../var/lib/postgresql", "backend:."):
                self.compose_refused(
                    "absolute container path", worktree, role, "cp", "./f", target, AGENT_ID="codex"
                )

    # Every form the installed parser accepted when probed with --dry-run on an empty project.
    VOLUME_DELETION = (
        ["down", "-v"],
        ["down", "--volumes"],
        ["down", "--volumes=true"],
        ["down", "--volumes=false"],
        ["down", "-v=true"],
        ["down", "-v=1"],
        ["down", "-vt5"],
        ["down", "-t5", "-v"],
        ["down", "--remove-orphans", "-v"],
        ["down", "--", "-v"],
        ["rm", "-v"],
        ["rm", "--volumes"],
        ["rm", "--volumes=true", "-f"],
        ["rm", "-fv"],
        ["rm", "-f", "-v"],
        ["rm", "-fsv"],
        ["rm", "-vf=true"],
        ["rm", "-f", "backend", "-v"],
    )

    def test_production_cli_never_deletes_volumes_and_has_no_override(self) -> None:
        worktree = self.create()
        for command in self.VOLUME_DELETION:
            self.compose_refused("cannot delete volumes through prod", worktree, "prod", *command)
            # Neither an operator identity nor a confirmation variable unlocks production.
            self.compose_refused(
                "cannot delete volumes through prod",
                worktree,
                "prod",
                *command,
                AGENT_ID="operator",
                CONFIRM_REMOVE_REVIEW="florabase-feature-review",
            )

    def test_review_and_sourcing_cli_keep_refusing_with_their_remove_action(self) -> None:
        worktree = self.create()
        self.ok(worktree, "claim", AGENT_ID="codex")
        for role in ("review", "sourcing"):
            for command in self.VOLUME_DELETION:
                self.compose_refused(
                    "exact project confirmation", worktree, role, *command, AGENT_ID="codex"
                )

    def test_other_persistent_roles_expose_no_equivalent_deletion_path(self) -> None:
        worktree = self.create()
        for command in self.VOLUME_DELETION:
            self.compose_refused("raw DEV lifecycle cleanup", worktree, "dev", *command)
            self.compose_refused("make quality-clean", worktree, "quality", *command)
        for role in ("review", "sourcing", "prod", "quality"):
            for command in (
                ["up", "-V"],
                ["up", "--renew-anon-volumes"],
                ["up", "--renew-anon-volumes=true"],
                ["up", "-dV"],
                ["up", "-V=true"],
                ["up", "--detach", "backend", "-V"],
            ):
                self.compose_refused("renew-anon-volumes", worktree, role, *command)

    def test_cp_follow_link_and_tar_streams_are_refused_on_every_cli_route(self) -> None:
        worktree = self.create()
        self.ok(worktree, "claim", AGENT_ID="codex")
        for role in ("review", "sourcing", "dev", "quality", "prod"):
            for command in (
                ["-L", *SAFE_COPY[1:]],
                ["--follow-link", *SAFE_COPY[1:]],
                ["--follow-link=true", *SAFE_COPY[1:]],
                ["--follow-link=false", *SAFE_COPY[1:]],
                ["-L=true", *SAFE_COPY[1:]],
                ["-aL", *SAFE_COPY[1:]],
                ["-La", *SAFE_COPY[1:]],
                ["--archive", "-L", *SAFE_COPY[1:]],
                [*SAFE_COPY[1:], "-L"],
                [SAFE_COPY[1], "--follow-link", SAFE_COPY[2]],
                ["backend:/tmp/link", "./out", "-L"],
            ):
                self.compose_refused(
                    "follow-link", worktree, role, "cp", *command, AGENT_ID="codex"
                )
            for command in (["-", "backend:/tmp/x"], ["backend:/tmp/x", "-"]):
                self.compose_refused(
                    "tar streams", worktree, role, "cp", *command, AGENT_ID="codex"
                )
        # The read-only Sourcing make route refuses these before Docker as well.
        self.docker_log.unlink(missing_ok=True)
        for argument in ("cp -L ./f backend:/tmp/f", "down -v=true", "rm -fv", "up -V"):
            result = subprocess.run(
                [sys.executable, str(SOURCING), "compose", "--cmd", argument],
                cwd=worktree,
                env=self.env(),
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1, argument)
            self.assertFalse(self.docker_log.exists(), argument)

    def test_legitimate_commands_are_not_mistaken_for_deletion_or_follow_link(self) -> None:
        worktree = self.create()
        self.ok(worktree, "claim", AGENT_ID="codex")
        for role, command in (
            ("prod", ["exec", "-T", "db", "pg_restore", "--list"]),
            ("prod", ["exec", "-T", "db", "sh", "-c", "printf %s -v"]),
            ("prod", ["start", "backend"]),
            ("prod", ["stop", "backend"]),
            ("prod", ["run", "--rm", "--no-deps", "backend", "python", "-v"]),
            ("prod", ["up", "--detach", "--build"]),
            ("prod", ["down"]),
            ("prod", ["down", "--remove-orphans"]),
            ("prod", ["down", "--rmi", "local"]),
            ("prod", ["down", "-t5"]),
            ("prod", ["down", "--timeout=5"]),
            ("prod", ["rm", "-fs", "backend"]),
            ("prod", ["rm", "-f", "vendor-service"]),
            ("prod", ["cp", "-a", "./f", "backend:/tmp/f"]),
            ("prod", ["cp", "--archive", "--index", "1", "./f", "backend:/tmp/f"]),
            ("quality", ["run", "--rm", "--no-deps", "backend", "pytest", "-v"]),
            (
                "dev",
                ["run", "--rm", "backend", "python", "-m", "florabase.auth.bootstrap", "owner"],
            ),
        ):
            self.assertEqual(
                self.compose_allowed(worktree, role, *command), [tuple(command)], command
            )
        for command in (
            ["rm", "-fs", "backend"],
            ["down", "--remove-orphans"],
            ["cp", "-a", *SAFE_COPY[1:]],
        ):
            self.assertEqual(
                self.compose_allowed(worktree, "review", *command, AGENT_ID="codex"),
                [tuple(command)],
                command,
            )
        # The established make down recipe stays a plain, volume-preserving down.
        makefile = (ROOT / "Makefile").read_text()
        self.assertIn("$(COMPOSE) down\n", makefile)
        self.assertIn("$(COMPOSE) up --detach --build\n", makefile)

    def test_dev_route_refuses_unsupported_mutations_and_keeps_operator_flows(self) -> None:
        worktree = self.create()
        for verb in (
            "cp",
            "watch",
            "create",
            "scale",
            "pause",
            "attach",
            "commit",
            "wait",
            "publish",
        ):
            command = SAFE_COPY if verb == "cp" else [verb]
            self.compose_refused("not supported against DEV", worktree, "dev", *command)
        for verb in ("up", "down", "start", "stop", "restart", "kill", "rm"):
            self.compose_refused("raw DEV lifecycle cleanup is refused", worktree, "dev", verb)
        bootstrap = ("run", "--rm", "backend", "python", "-m", "florabase.auth.bootstrap", "owner")
        self.assertEqual(self.compose_allowed(worktree, "dev", *bootstrap), [bootstrap])

    def test_read_only_verbs_stay_available_without_identity_or_lock(self) -> None:
        worktree = self.create()
        self.ok(worktree, "claim", AGENT_ID="codex")
        holders = [
            self.hold(worktree, f"machine_lock({name!r}, 'held')")
            for name in ("florabase-feature-review", "florabase-sourcing-preview", "florabase")
        ]
        for role in ("review", "sourcing", "dev", "quality", "prod"):
            for verb in sorted(COMPOSE_READ_ONLY):
                self.assertEqual(
                    self.compose_allowed(worktree, role, verb, AGENT_ID="opencode"), [(verb,)]
                )
        for holder in holders:
            self.release(holder)

    def test_authorized_writer_reaches_compose_only_while_holding_the_lock(self) -> None:
        worktree = self.create()
        self.ok(worktree, "claim", AGENT_ID="codex")

        def held(*_args: str, **_kwargs: object) -> None:
            with self.assertRaises(ResourceError):
                with machine_lock("florabase-feature-review", "probe"):
                    pass

        for command in (
            SAFE_COPY,
            ["watch"],
            ["exec", "-T", "frontend", "pnpm", "build"],
            ["run", "--rm", "backend", "alembic", "revision", "--autogenerate", "-m", "x"],
            ["config", "-o", "../out.yaml"],
        ):
            with (
                contextlib.chdir(worktree),
                patch.dict(os.environ, self.env(AGENT_ID="codex"), clear=True),
                patch("sys.argv", ["workflow", "review", "compose", "--", *command]),
                patch.object(Environment, "validate"),
                patch.object(Environment, "require_owner"),
                patch.object(Environment, "compose", side_effect=held) as compose,
            ):
                self.assertEqual(workflow_environment.main(), 0)
            compose.assert_called_once_with(*command)
        # Never-claimed worktrees keep working with no identity at all.
        unclaimed = self.create("fix/unclaimed")
        self.assertEqual(self.compose_allowed(unclaimed, "review", *SAFE_COPY), [tuple(SAFE_COPY)])

    def test_quality_and_production_routes_keep_their_established_contract(self) -> None:
        worktree = self.create()
        self.ok(worktree, "claim", AGENT_ID="codex")
        # Gate stages and backup/restore scripts use these without a writer identity.
        for role, command in (
            ("quality", ["run", "--rm", "--no-deps", "backend", "pytest"]),
            ("prod", ["exec", "-T", "db", "pg_restore", "--list"]),
            ("prod", ["stop", "backend"]),
            ("prod", ["start", "backend"]),
        ):
            self.assertEqual(self.compose_allowed(worktree, role, *command), [tuple(command)])
        for verb in ("down", "rm", "stop", "kill"):
            self.compose_refused("make quality-clean", worktree, "quality", verb)

    def test_sourcing_preview_passthrough_is_truly_read_only(self) -> None:
        worktree = self.create()

        def cli(argument: str, **values: str) -> subprocess.CompletedProcess[str]:
            self.docker_log.unlink(missing_ok=True)
            return subprocess.run(
                [sys.executable, str(SOURCING), "compose", "--cmd", argument],
                cwd=worktree,
                env=self.env(**values),
                capture_output=True,
                text=True,
            )

        for verb in sorted(COMPOSE_MUTATING):
            argument = " ".join(SAFE_COPY) if verb == "cp" else verb
            result = cli(argument)
            self.assertEqual(result.returncode, 1, verb)
            self.assertIn("is read-only", result.stderr, verb)
            self.assertFalse(self.docker_log.exists(), verb)
        for argument, needle in (
            ("config -o out", "is read-only"),
            ("frobnicate", "unknown Compose subcommand"),
            ("--project-name other ps", "provide a Compose subcommand"),
            ("down -v", "exact project confirmation"),
        ):
            result = cli(argument)
            self.assertEqual(result.returncode, 1, argument)
            self.assertIn(needle, result.stderr, argument)
            self.assertFalse(self.docker_log.exists(), argument)
        with (
            contextlib.chdir(worktree),
            patch.dict(os.environ, self.env(AGENT_ID="opencode"), clear=True),
            patch("sys.argv", ["sourcing", "compose", "--cmd", "ps -a"]),
            patch.object(sourcing_preview.SourcingPreview, "require_context"),
            patch.object(sourcing_preview.SourcingPreview, "validate"),
            patch.object(sourcing_preview.SourcingPreview, "require_owner"),
            patch.object(sourcing_preview.SourcingPreview, "compose") as compose,
        ):
            self.assertEqual(sourcing_preview.main(), 0)
        compose.assert_called_once_with("ps", "-a")

    def test_sourcing_make_lifecycle_needs_the_writer_before_docker(self) -> None:
        worktree = self.create()
        self.ok(worktree, "claim", AGENT_ID="codex")
        for action in ("up", "seed", "bootstrap-owner", "remove"):
            self.docker_log.unlink(missing_ok=True)
            result = subprocess.run(
                [sys.executable, str(SOURCING), action],
                cwd=worktree,
                env=self.env(AGENT_ID="opencode"),
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1, action)
            self.assertIn("codex holds this worktree", result.stderr, action)
            self.assertFalse(self.docker_log.exists(), action)

    def test_sourcing_lifecycle_is_serialized_before_any_docker_change(self) -> None:
        worktree = self.create()
        holder = self.hold(worktree, "machine_lock('florabase-sourcing-preview', 'lifecycle')")
        self.docker_log.unlink(missing_ok=True)
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/sourcing_preview.py"), "up"],
            cwd=worktree,
            env=self.env(),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("lifecycle is already running", result.stderr)
        self.assertFalse(self.docker_log.exists())
        self.release(holder)

    def test_review_up_refuses_other_writer_before_any_docker_change(self) -> None:
        worktree = self.create()
        self.ok(worktree, "claim", AGENT_ID="claude-code")
        self.docker_log.unlink(missing_ok=True)
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/workflow_environment.py"), "review", "up"],
            cwd=worktree,
            env=self.env(AGENT_ID="codex"),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("claude-code holds this worktree", result.stderr)
        self.assertFalse(self.docker_log.exists())

    # Delivery prerequisites --------------------------------------------------------------------

    def test_delivery_and_finish_are_operator_only(self) -> None:
        worktree = self.create()
        self.ok(worktree, "claim", AGENT_ID="codex")
        for agent in ("claude-code", "codex", "opencode"):
            self.refused("operator actions", worktree, "require-operator", AGENT_ID=agent)
        self.ok(worktree, "require-operator")
        self.ok(worktree, "require-operator", AGENT_ID="operator")
        # Real entry points stop at the guard: nothing is pushed and the branch is retained.
        self.write_tool("gh", "exit 0\n")
        scripts = worktree / "scripts"
        scripts.mkdir()
        for name in ("feature_worktree.py", "workflow_environment.py", "workflow_resources.py"):
            shutil.copy2(ROOT / "scripts" / name, scripts / name)
        (self.primary / ".git/info/exclude").write_text("scripts/\n")
        for script in ("feature-finish.sh", "feature-deliver.py"):
            attempt = subprocess.run(
                [str(ROOT / "scripts" / script)],
                cwd=worktree,
                env=self.env(AGENT_ID="codex"),
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(attempt.returncode, 0, script)
            self.assertIn("operator actions", attempt.stderr, script)
        self.assertEqual(self.git(worktree, "branch", "--show-current"), "feat/example-001")
        self.assertEqual(self.git(self.remote, "branch", "--list", "feat/example-001"), "")

    # Finish and retirement ---------------------------------------------------------------------

    def finished(self, branch: str = "feat/example-001", *, frontend: bool = False) -> Path:
        worktree = self.create(branch)
        self.ok(worktree, "claim", AGENT_ID="claude-code")
        content = "feature\n" if branch == "feat/example-001" else f"{branch}\n"
        (worktree / "feature.txt").write_text(content)
        if frontend:
            (worktree / "frontend").mkdir()
            (worktree / "frontend/package.json").write_text("{}\n")
        self.git(worktree, "add", ".")
        self.git(worktree, "commit", "-m", "feature")
        feature = self.git(worktree, "rev-parse", "HEAD")
        self.git(worktree, "push", "origin", branch)
        seed = self.root / "seed"
        self.advance_main()
        self.git(seed, "fetch", "origin", branch)
        self.git(seed, "merge", "--squash", f"origin/{branch}")
        self.git(seed, "commit", "-m", "squash")
        self.git(seed, "push", "origin", "main")
        merge = self.git(seed, "rev-parse", "HEAD")
        self.write_tool(
            "gh",
            'if [[ "$1" == "auth" ]]; then exit 0; fi\n'
            f"printf 'MERGED|main|{branch}|{feature}|{merge}\\n'\n",
        )
        result = subprocess.run(
            [str(ROOT / "scripts/feature-finish.sh")],
            cwd=worktree,
            env=self.env(),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("feature-retire", result.stdout)
        self.assertEqual(self.git(self.primary, "rev-parse", "HEAD"), merge)
        self.assertEqual(self.git(worktree, "branch", "--show-current"), "")
        return worktree

    def test_linked_finish_then_explicit_retirement_preserves_environments(self) -> None:
        worktree = self.finished()
        self.assertIsNone(self.context(worktree)["writer"])
        self.refused("requires CONFIRM_RETIRE", self.primary, "retire", FEATURE="example-001")
        self.refused(
            "not the retiring worktree",
            worktree,
            "retire",
            FEATURE="example-001",
            CONFIRM_RETIRE="example-001",
        )
        self.docker_log.unlink(missing_ok=True)
        self.ok(self.primary, "retire", FEATURE="example-001", CONFIRM_RETIRE="example-001")
        self.assertFalse(worktree.exists())
        self.assertEqual(self.git(self.primary, "status", "--porcelain"), "")
        # DEV/Review/UAT preservation: only exact read-only inventory/inspection commands.
        for line in self.docker_log.read_text().splitlines():
            self.assertTrue(
                line == "ps --quiet --no-trunc"
                or line.startswith(
                    (
                        "ps -a --filter",
                        "volume ls --filter",
                        "inspect --type container --format",
                        "volume inspect --format",
                    )
                ),
                line,
            )

    def test_retirement_refuses_every_unsafe_state(self) -> None:
        worktree = self.finished()
        args = {"FEATURE": "example-001", "CONFIRM_RETIRE": "example-001"}
        (worktree / "wip.txt").write_text("local\n")
        self.refused("has changes", self.primary, "retire", **args)
        (worktree / "wip.txt").unlink()
        (worktree / ".env").write_text("SECRET=fixture\n")
        self.refused("need a decision first: .env", self.primary, "retire", **args)
        (worktree / ".env").unlink()
        (worktree / "__pycache__").mkdir()
        (worktree / "__pycache__/module.pyc").write_text("regenerable\n")
        self.refused(
            "still owns Docker", self.primary, "retire", MOCK_OWNED_SOURCE=str(worktree), **args
        )
        self.refused(
            "still owns Docker", self.primary, "retire", MOCK_VOLUME_SOURCE=str(worktree), **args
        )
        self.refused("Docker command failed", self.primary, "retire", MOCK_DOCKER_FAIL="1", **args)
        metadata = Path(self.git(worktree, "rev-parse", "--absolute-git-dir"))
        holder = self.hold(worktree, f"verification_lock(Path({str(metadata)!r}))")
        self.refused("already running", self.primary, "retire", **args)
        self.release(holder)
        state = metadata / "info/florabase-agent-state.json"
        state.write_text("{}")
        self.refused("writer state", self.primary, "retire", **args)
        state.unlink()
        proof_path = metadata / "info/florabase-finished.json"
        proof = proof_path.read_text()
        proof_path.write_text(json.dumps({**json.loads(proof), "merge": "0" * 40}))
        self.assertEqual(self.helper(self.primary, "retire", **args).returncode, 1)
        proof_path.write_text(proof)
        locked = worktree / "__pycache__"
        locked.chmod(0o500)
        self.refused("fix its ownership", self.primary, "retire", **args)
        locked.chmod(0o700)
        self.git(worktree, "commit", "--allow-empty", "-m", "moved after finish")
        self.refused("moved after finish", self.primary, "retire", **args)
        self.assertTrue(worktree.is_dir())

    def test_regenerable_caches_do_not_block_retirement(self) -> None:
        worktree = self.finished()
        (worktree / "__pycache__").mkdir()
        (worktree / "__pycache__/module.pyc").write_text("regenerable\n")
        self.ok(self.primary, "retire", FEATURE="example-001", CONFIRM_RETIRE="example-001")
        self.assertFalse(worktree.exists())

    def test_empty_unwritable_directory_does_not_block_retirement(self) -> None:
        worktree = self.finished(frontend=True)
        cache = worktree / "frontend/node_modules"
        cache.mkdir()
        cache.chmod(0o555)
        self.assertFalse(os.access(cache, os.W_OK))
        self.ok(self.primary, "retire", FEATURE="example-001", CONFIRM_RETIRE="example-001")
        self.assertFalse(worktree.exists())

    def test_nonempty_unwritable_directory_keeps_registration_and_content(self) -> None:
        worktree = self.finished(frontend=True)
        cache = worktree / "frontend/node_modules"
        cache.mkdir()
        (cache / "unexpected.txt").write_text("retain me")
        # Simulate the repository's ignored dependency cache.
        (self.primary / ".git/info/exclude").write_text("node_modules/\n")
        cache.chmod(0o555)
        try:
            self.refused(
                "fix its ownership",
                self.primary,
                "retire",
                FEATURE="example-001",
                CONFIRM_RETIRE="example-001",
            )
            self.assertEqual((cache / "unexpected.txt").read_text(), "retain me")
            self.assertIn(str(worktree), self.git(self.primary, "worktree", "list"))
        finally:
            cache.chmod(0o755)

    def test_retirement_preflight_refuses_links_and_mounts(self) -> None:
        worktree = self.finished(frontend=True)
        cache = worktree / "frontend/node_modules"
        cache.mkdir()
        outside = self.root / "shared"
        outside.mkdir()
        (outside / "keep").write_text("shared data")
        link = cache / "linked"
        link.symlink_to(outside, target_is_directory=True)
        (self.primary / ".git/info/exclude").write_text("node_modules/\n")
        self.refused(
            "symlink",
            self.primary,
            "retire",
            FEATURE="example-001",
            CONFIRM_RETIRE="example-001",
        )
        link.unlink()
        # Include escaped spaces/backslashes and a same-device bind mount, which is_mount misses.
        mounted = cache / "space and\\slash"
        mounted.mkdir()
        escaped = str(mounted).replace("\\", r"\134").replace(" ", r"\040")
        with patch.object(
            Path,
            "read_text",
            return_value=f"20 1 8:1 / {escaped} rw - ext4 /dev/a rw\n",
        ):
            with self.assertRaisesRegex(workflow_environment.WorkflowError, "mounted path"):
                feature_worktree.validate_retirement_tree(worktree)
        with patch.object(Path, "read_text", side_effect=PermissionError("unavailable")):
            with self.assertRaisesRegex(workflow_environment.WorkflowError, "safe removal"):
                feature_worktree.validate_retirement_tree(worktree)
        for evidence in ("invalid\n", ""):
            with patch.object(Path, "read_text", return_value=evidence):
                with self.assertRaisesRegex(workflow_environment.WorkflowError, "safe removal"):
                    feature_worktree.validate_retirement_tree(worktree)
        self.assertTrue(worktree.exists())
        self.assertEqual((outside / "keep").read_text(), "shared data")
        self.assertIn(str(worktree), self.git(self.primary, "worktree", "list"))

    def test_retirement_preflight_requires_traversal_and_removable_parent(self) -> None:
        candidate = self.root / "candidate"
        parent = candidate / "frontend"
        cache = parent / "node_modules"
        cache.mkdir(parents=True)
        cache.chmod(0o000)
        try:
            with self.assertRaisesRegex(workflow_environment.WorkflowError, "safe removal"):
                feature_worktree.validate_retirement_tree(candidate)
        finally:
            cache.chmod(0o755)
        parent.chmod(0o555)
        try:
            with self.assertRaisesRegex(workflow_environment.WorkflowError, "fix its ownership"):
                feature_worktree.validate_retirement_tree(candidate)
        finally:
            parent.chmod(0o755)
        original_stat = Path.stat

        def sticky_parent(path: Path, *, follow_symlinks: bool = True) -> os.stat_result:
            result = original_stat(path, follow_symlinks=follow_symlinks)
            if path == parent:
                fields = list(result)
                fields[0] = result.st_mode | stat.S_ISVTX
                fields[4] = os.getuid() + 2
                return os.stat_result(fields)
            return result

        with (
            patch.object(Path, "stat", sticky_parent),
            patch.object(os, "geteuid", return_value=os.getuid() + 1),
        ):
            with self.assertRaisesRegex(workflow_environment.WorkflowError, "sticky parent"):
                feature_worktree.validate_retirement_tree(candidate)
        self.assertTrue(cache.is_dir())

    @unittest.skipUnless(
        os.environ.get("FLORABASE_RETIRE_DOCKER_SMOKE") == "1",
        "opt-in real Docker mountpoint smoke; offline suite uses PATH mocks",
    )
    def test_real_docker_root_owned_empty_mountpoint_retirement(self) -> None:
        worktree = self.finished(frontend=True)
        cache = worktree / "frontend/node_modules"
        # Docker prepares the nested mountpoint in the host bind as root, even with a non-root
        # process. Only this disposable fixture is mounted; no network or persistent volume.
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--pull=never",
                "--network=none",
                "--read-only",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "--mount",
                f"type=bind,src={worktree / 'frontend'},dst=/fixture",
                "--tmpfs",
                "/fixture/node_modules:rw",
                "--entrypoint",
                "/bin/true",
                "node:24.19.0-bookworm-slim",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(cache.stat().st_uid, 0)
        self.assertEqual(list(cache.iterdir()), [])
        self.assertFalse(os.access(cache, os.W_OK))  # Original preflight refuses here.
        self.ok(self.primary, "retire", FEATURE="example-001", CONFIRM_RETIRE="example-001")
        self.assertFalse(worktree.exists())
        self.assertNotIn(str(worktree), self.git(self.primary, "worktree", "list"))

    def test_running_mount_guard_resolves_overlap_and_allows_unrelated_sources(self) -> None:
        candidate = self.root / "candidate"
        candidate.mkdir()
        child = candidate / "child"
        child.mkdir()
        unrelated = self.root / "candidate-other"
        unrelated.mkdir()
        alias = self.root / "alias"
        alias.symlink_to(child, target_is_directory=True)
        identifier = "a" * 64
        for source in (candidate, child, candidate.parent, alias, unrelated):
            record = {
                "Id": identifier,
                "Running": True,
                "Mounts": [{"Type": "bind", "Source": str(source), "Destination": "/data"}],
            }
            with (
                self.subTest(source=source),
                patch.object(
                    feature_worktree,
                    "docker",
                    side_effect=[identifier, json.dumps(record), identifier],
                ) as commands,
            ):
                if source == unrelated:
                    feature_worktree.require_no_running_mounts(candidate)
                    self.assertEqual(commands.call_count, 3)
                else:
                    with self.assertRaisesRegex(
                        workflow_environment.WorkflowError, "running container"
                    ):
                        feature_worktree.require_no_running_mounts(candidate)
            self.assertTrue(child.is_dir())

    def test_running_mount_guard_fails_closed_on_incomplete_or_changing_evidence(self) -> None:
        identifier = "a" * 64
        cases: list[list[str]] = [
            ["short-id"],
            [identifier, ""],
            [identifier, "{}"],
            [identifier, json.dumps({"Id": identifier, "Running": True})],
            [identifier, json.dumps({"Id": identifier, "Running": False, "Mounts": []})],
            [identifier, json.dumps({"Id": identifier, "Running": True, "Mounts": [{}]})],
            [
                identifier,
                json.dumps(
                    {
                        "Id": identifier,
                        "Running": True,
                        "Mounts": [{"Type": "bind", "Destination": "/data", "Source": "relative"}],
                    }
                ),
            ],
            [
                identifier,
                json.dumps(
                    {
                        "Id": identifier,
                        "Running": True,
                        "Mounts": [
                            {
                                "Type": "bind",
                                "Destination": "/data",
                                "Source": str(self.root / "gone"),
                            }
                        ],
                    }
                ),
            ],
            [identifier, json.dumps({"Id": identifier, "Running": True, "Mounts": []}), "b" * 64],
        ]
        for answers in cases:
            with (
                self.subTest(answers=answers),
                patch.object(feature_worktree, "docker", side_effect=answers),
            ):
                with self.assertRaises(workflow_environment.WorkflowError):
                    feature_worktree.require_no_running_mounts(self.root)
        with patch.object(
            feature_worktree, "docker", side_effect=ResourceError("Docker unavailable")
        ):
            with self.assertRaises(ResourceError):
                feature_worktree.require_no_running_mounts(self.root)

    def test_running_mount_guard_checks_volume_backing_and_tmpfs(self) -> None:
        candidate = self.root / "candidate"
        candidate.mkdir()
        source = self.root / "docker-data/volumes/fixture/_data"
        source.mkdir(parents=True)
        identifier = "a" * 64
        record = {
            "Id": identifier,
            "Running": True,
            "Mounts": [
                {
                    "Type": "volume",
                    "Name": "fixture",
                    "Source": str(source),
                    "Destination": "/data",
                },
                {"Type": "tmpfs", "Destination": "/tmp"},
            ],
        }
        volume = {"Name": "fixture", "Driver": "local", "Mountpoint": str(source), "Options": None}
        for changes, allowed in (
            ({}, True),
            ({"Options": {"device": str(candidate)}}, False),
            ({"Driver": "unknown"}, False),
            ({"Mountpoint": "/other"}, False),
        ):
            with (
                self.subTest(changes=changes),
                patch.object(
                    feature_worktree,
                    "docker",
                    side_effect=[
                        identifier,
                        json.dumps(record),
                        json.dumps({**volume, **changes}),
                        identifier,
                    ],
                ),
            ):
                if allowed:
                    feature_worktree.require_no_running_mounts(candidate)
                else:
                    with self.assertRaisesRegex(
                        workflow_environment.WorkflowError, "volume backing"
                    ):
                        feature_worktree.require_no_running_mounts(candidate)

    def assert_offline_retirement_blocked(self, worktree: Path, reason: str) -> None:
        original_git = Repository.git
        removals: list[tuple[str, ...]] = []

        def guarded_git(repo: Repository, *args: str) -> str:
            if args[:2] == ("worktree", "remove"):
                removals.append(args)
                raise AssertionError("Git removal reached before safe refusal")
            return original_git(repo, *args)

        with patch.object(Repository, "git", guarded_git):
            with self.assertRaisesRegex(workflow_environment.WorkflowError, reason):
                feature_worktree.retire(Repository(self.primary), "example-001", "example-001")
        self.assertEqual(removals, [])
        self.assertIn(str(worktree), self.git(self.primary, "worktree", "list"))
        self.assertEqual((worktree / "feature.txt").read_text(), "feature\n")
        self.assertEqual((worktree / "frontend/package.json").read_text(), "{}\n")

    def offline_sticky_child(self, *, fifo: bool) -> None:
        worktree = self.finished(frontend=True)
        (self.primary / ".git/info/exclude").write_text("node_modules/\n")
        cache = worktree / "frontend/node_modules"
        cache.mkdir()
        child = cache / "foreign"
        if fifo:
            os.mkfifo(child)
        else:
            child.write_text("retained")
        original_stat, original_scan = Path.stat, os.scandir
        foreign_uid = os.geteuid() + 1

        def foreign_stat(path: Path, *, follow_symlinks: bool = True) -> os.stat_result:
            result = original_stat(path, follow_symlinks=follow_symlinks)
            if path in (cache, child):
                fields = list(result)
                fields[4] = foreign_uid
                if path == cache:
                    fields[0] = stat.S_IFDIR | 0o1777
                return os.stat_result(fields)
            return result

        @contextlib.contextmanager
        def foreign_scan(path: Path) -> Iterator[list[Any]]:
            with original_scan(path) as entries:
                children = []
                for entry in entries:
                    if Path(entry.path) == child:
                        entry = Mock(wraps=entry, stat=Mock(return_value=foreign_stat(child)))
                    children.append(entry)
                yield children

        with (
            patch.object(Path, "stat", foreign_stat),
            patch.object(os, "scandir", foreign_scan),
            patch.object(feature_worktree, "docker", return_value=""),
        ):
            self.assert_offline_retirement_blocked(worktree, "sticky parent")
        self.assertTrue(child.exists())
        if fifo:
            self.assertTrue(stat.S_ISFIFO(child.stat().st_mode))
        else:
            self.assertEqual(child.read_text(), "retained")

    def test_offline_retire_rejects_sticky_foreign_regular_file(self) -> None:
        self.offline_sticky_child(fifo=False)

    def test_offline_retire_rejects_sticky_foreign_fifo(self) -> None:
        self.offline_sticky_child(fifo=True)

    def test_offline_retire_invokes_running_unlabelled_mount_guard(self) -> None:
        worktree = self.finished(frontend=True)
        identifier = "a" * 64
        record = {
            "Id": identifier,
            "Running": True,
            "Mounts": [
                {"Type": "bind", "Source": str(worktree / "frontend"), "Destination": "/data"},
            ],
        }

        def inventory(*args: str) -> str:
            if args == ("ps", "--quiet", "--no-trunc"):
                return identifier
            if args[:3] == ("inspect", "--type", "container"):
                return json.dumps(record)
            if args[:2] in (("ps", "-a"), ("volume", "ls")):
                return ""  # No Florabase labels: existing ownership checks pass.
            raise AssertionError(f"Unexpected Docker command: {args}")

        with (
            patch.object(feature_worktree, "docker", side_effect=inventory),
            patch.object(
                feature_worktree,
                "require_no_running_mounts",
                wraps=feature_worktree.require_no_running_mounts,
            ) as guard,
        ):
            self.assert_offline_retirement_blocked(worktree, "running container")
            guard.assert_called_once_with(worktree)

    def docker_fixture(self, *args: str) -> str:
        """Actual Docker, outside the offline PATH mock; only exact disposable targets mutate."""
        return subprocess.run(
            ["docker", *args], check=True, capture_output=True, text=True
        ).stdout.strip()

    @unittest.skipUnless(
        os.environ.get("FLORABASE_RETIRE_DOCKER_SMOKE") == "1",
        "opt-in real Docker filesystem smoke",
    )
    def test_real_sticky_foreign_objects_preserve_registration_and_contents(self) -> None:
        worktree = self.finished(frontend=True)
        frontend = worktree / "frontend"
        cache = frontend / "node_modules"
        (self.primary / ".git/info/exclude").write_text("node_modules/\n")
        for name, create in (
            ("rootfile", "printf retained > /fixture/node_modules/rootfile"),
            ("rootfifo", "mkfifo /fixture/node_modules/rootfifo"),
        ):
            with self.subTest(child=name):
                self.docker_fixture(
                    "run",
                    "--rm",
                    "--pull=never",
                    "--network=none",
                    "--read-only",
                    "--mount",
                    f"type=bind,src={frontend},dst=/fixture",
                    "--entrypoint",
                    "sh",
                    "node:24.19.0-bookworm-slim",
                    "-ec",
                    "mkdir -m 1777 /fixture/node_modules; " + create,
                )
                try:
                    self.assertEqual(cache.stat().st_uid, 0)
                    self.assertEqual(cache.stat().st_mode & 0o7777, 0o1777)
                    self.assertEqual((cache / name).stat().st_uid, 0)
                    self.refused(
                        "sticky parent",
                        self.primary,
                        "retire",
                        FEATURE="example-001",
                        CONFIRM_RETIRE="example-001",
                    )
                    self.assertIn(str(worktree), self.git(self.primary, "worktree", "list"))
                    self.assertEqual((worktree / "feature.txt").read_text(), "feature\n")
                    self.assertEqual((frontend / "package.json").read_text(), "{}\n")
                    if name == "rootfile":
                        self.assertEqual((cache / name).read_text(), "retained")
                    else:
                        self.assertTrue(stat.S_ISFIFO((cache / name).stat().st_mode))
                finally:
                    # Exact fixture objects only: no recursive permission repair/deletion fallback.
                    self.docker_fixture(
                        "run",
                        "--rm",
                        "--pull=never",
                        "--network=none",
                        "--read-only",
                        "--mount",
                        f"type=bind,src={frontend},dst=/fixture",
                        "--entrypoint",
                        "sh",
                        "node:24.19.0-bookworm-slim",
                        "-ec",
                        f"rm /fixture/node_modules/{name}; rmdir /fixture/node_modules",
                    )

    @unittest.skipUnless(
        os.environ.get("FLORABASE_RETIRE_DOCKER_SMOKE") == "1", "opt-in real Docker mount smoke"
    )
    def test_real_unlabelled_parent_mount_preserves_live_nested_data(self) -> None:
        worktree = self.finished(frontend=True)
        name = f"florabase-retire-smoke-{uuid.uuid4().hex[:12]}"
        # Exercise the real read-only Docker checks in retirement, not its PATH fixture mock.
        (self.bin / "docker").unlink()
        (self.bin / "docker").symlink_to(shutil.which("docker") or "docker")
        container = self.docker_fixture(
            "run",
            "-d",
            "--name",
            name,
            "--pull=never",
            "--network=none",
            "--read-only",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--mount",
            f"type=bind,src={self.managed},dst=/fixture",
            "--tmpfs",
            f"/fixture/example-001/frontend/node_modules:rw,uid={os.getuid()}",
            "--entrypoint",
            "sleep",
            "node:24.19.0-bookworm-slim",
            "300",
        )
        try:
            self.docker_fixture(
                "exec",
                container,
                "sh",
                "-ec",
                "printf live > /fixture/example-001/frontend/node_modules/data",
            )
            cache = worktree / "frontend/node_modules"
            self.assertEqual(list(cache.iterdir()), [])  # Hidden by the container's tmpfs.
            self.refused(
                "running container",
                self.primary,
                "retire",
                FEATURE="example-001",
                CONFIRM_RETIRE="example-001",
            )
            self.assertIn(str(worktree), self.git(self.primary, "worktree", "list"))
            self.assertEqual((worktree / "feature.txt").read_text(), "feature\n")
            self.assertEqual(
                self.docker_fixture(
                    "exec", container, "cat", "/fixture/example-001/frontend/node_modules/data"
                ),
                "live",
            )
            self.assertEqual(
                self.docker_fixture("inspect", "--format", "{{.State.Running}}", container), "true"
            )
        finally:
            self.docker_fixture("stop", "--time", "1", container)
            self.docker_fixture("rm", container)
            self.assertEqual(self.docker_fixture("ps", "-aq", "--filter", f"name=^/{name}$"), "")

    def test_tool_worktree_is_refused_even_under_a_redirected_root(self) -> None:
        tools = self.root / "codex/worktrees"
        provider = tools / "abcd"
        self.git(self.primary, "worktree", "add", "--detach", str(provider))
        metadata = Path(self.git(provider, "rev-parse", "--absolute-git-dir"))
        sha = self.git(provider, "rev-parse", "HEAD")
        (metadata / "info").mkdir(exist_ok=True)
        (metadata / "info/florabase-finished.json").write_text(
            json.dumps({"branch": "feat/gone", "sha": sha, "merge": sha})
        )
        self.refused(
            "not created by make feature-worktree",
            self.primary,
            "retire",
            FEATURE="abcd",
            CONFIRM_RETIRE="abcd",
            FLORABASE_WORKTREE_ROOT=str(tools),
        )
        self.assertTrue(provider.is_dir())

    def test_retirement_only_targets_finished_managed_worktrees(self) -> None:
        active = self.create("feat/active")
        args = {"FEATURE": "active", "CONFIRM_RETIRE": "active"}
        self.refused("still on a branch", self.primary, "retire", **args)
        self.git(active, "switch", "--detach")
        self.refused("no make feature-finish proof", self.primary, "retire", **args)
        # A provider-managed worktree outside the managed root can never be selected.
        provider = self.root / "codex/worktrees/abcd/florabase"
        self.git(self.primary, "worktree", "add", "--detach", str(provider))
        for name in ("../codex/worktrees/abcd/florabase", "abcd", "../florabase"):
            self.refused(
                "feature worktree id" if "/" in name else "not a registered",
                self.primary,
                "retire",
                FEATURE=name,
                CONFIRM_RETIRE=name,
            )
        self.assertTrue(provider.is_dir())

    def assert_finished_intact(self, worktree: Path) -> None:
        self.assertTrue(worktree.is_dir())
        self.assertTrue((worktree / "feature.txt").is_file())
        self.assertIn(str(worktree), self.git(self.primary, "worktree", "list"))
        metadata = Path(self.git(worktree, "rev-parse", "--absolute-git-dir"))
        self.assertTrue((metadata / "info/florabase-managed-worktree").is_file())
        self.assertTrue((metadata / "info/florabase-finished.json").is_file())

    def test_retirement_enforces_operator_identity_at_all_entry_points_without_side_effects(
        self,
    ) -> None:
        worktree = self.finished()
        metadata = Path(self.git(worktree, "rev-parse", "--absolute-git-dir"))
        common = Path(self.git(self.primary, "rev-parse", "--absolute-git-dir"))
        args = {"FEATURE": "example-001", "CONFIRM_RETIRE": "example-001"}
        self.docker_log.unlink(missing_ok=True)
        lock_stat = (metadata / "florabase-verification.lock").stat()
        for agent in ("claude-code", "codex", "opencode", "operator-2"):
            self.refused("operator actions", self.primary, "retire", AGENT_ID=agent, **args)
            self.assertFalse(self.docker_log.exists())
            self.assertEqual(list(common.glob("florabase-retire-*.lock")), [])
            self.assertEqual((metadata / "florabase-verification.lock").stat(), lock_stat)
            self.assert_finished_intact(worktree)
            with patch.dict(os.environ, self.env(AGENT_ID=agent), clear=True):
                with self.assertRaisesRegex(workflow_environment.WorkflowError, "operator actions"):
                    feature_worktree.retire(Repository(self.primary), "example-001", "example-001")
            self.assert_finished_intact(worktree)
            mark_refused = self.helper(
                worktree,
                "mark-finished",
                "--branch",
                "feat/example-001",
                "--sha",
                self.git(worktree, "rev-parse", "HEAD"),
                "--merge",
                self.git(self.primary, "rev-parse", "HEAD"),
                AGENT_ID=agent,
            )
            self.assertEqual(mark_refused.returncode, 1, mark_refused.stdout)
            self.assertIn("operator actions", mark_refused.stderr)
        # Makefile target enforces the same operator boundary and allows explicit AGENT_ID=operator.
        shutil.copy2(ROOT / "Makefile", self.primary / "Makefile")
        scripts_copy = self.primary / "scripts"
        shutil.copytree(
            ROOT / "scripts", scripts_copy, ignore=shutil.ignore_patterns("__pycache__")
        )
        for cmd in (
            [
                "make",
                "feature-retire",
                "FEATURE=example-001",
                "CONFIRM_RETIRE=example-001",
                "AGENT_ID=codex",
            ],
            [
                "make",
                "feature-retire",
                "FEATURE=example-001",
                "CONFIRM_RETIRE=example-001",
                "AGENT_ID=Bad Name",
            ],
        ):
            refused = subprocess.run(
                cmd, cwd=self.primary, env=self.env(), capture_output=True, text=True
            )
            self.assertNotEqual(refused.returncode, 0, cmd)
            self.assertFalse(self.docker_log.exists())
            self.assert_finished_intact(worktree)
        allowed = subprocess.run(
            [
                "make",
                "feature-retire",
                "FEATURE=example-001",
                "CONFIRM_RETIRE=example-001",
                "AGENT_ID=operator",
            ],
            cwd=self.primary,
            env=self.env(),
            capture_output=True,
            text=True,
        )
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        self.assertIn("FEATURE WORKTREE RETIRED", allowed.stdout)
        self.assertFalse(worktree.exists())

    def test_retirement_refuses_missing_and_invalid_identities_with_no_side_effects(self) -> None:
        worktree = self.finished()
        common = Path(self.git(self.primary, "rev-parse", "--absolute-git-dir"))
        self.docker_log.unlink(missing_ok=True)
        for bad_agent in ("Bad Name", "OPERATOR", " ", "../evil", "-bad", "a" * 65, "operator\n"):
            self.refused(
                "safe lowercase",
                self.primary,
                "retire",
                AGENT_ID=bad_agent,
                FEATURE="example-001",
                CONFIRM_RETIRE="example-001",
            )
        for bad_feature in ("", " ", "../evil", "UPPER", "feat/example-001", "-dash"):
            self.refused(
                "feature worktree id",
                self.primary,
                "retire",
                AGENT_ID="operator",
                FEATURE=bad_feature,
                CONFIRM_RETIRE=bad_feature,
            )
        self.refused(
            "requires CONFIRM_RETIRE",
            self.primary,
            "retire",
            AGENT_ID="operator",
            FEATURE="example-001",
            CONFIRM_RETIRE="",
        )
        self.refused(
            "not a registered",
            self.primary,
            "retire",
            AGENT_ID="operator",
            FEATURE="absent-001",
            CONFIRM_RETIRE="absent-001",
        )
        self.assertFalse(self.docker_log.exists())
        self.assertEqual(list(common.glob("florabase-retire-*.lock")), [])
        self.assert_finished_intact(worktree)
        # Explicit empty AGENT_ID clears an ambient agent setting like the other operator commands.
        self.ok(
            self.primary,
            "retire",
            AGENT_ID="",
            FEATURE="example-001",
            CONFIRM_RETIRE="example-001",
        )
        self.assertFalse(worktree.exists())

    def test_retirement_refuses_pending_handoffs_and_corrupt_writer_state(self) -> None:
        pending_wt = self.create("feat/pending-001")
        self.ok(pending_wt, "claim", AGENT_ID="claude-code")
        self.ok(pending_wt, "handoff", AGENT_ID="claude-code", TO="codex", REPORT=self.report())
        pending_meta = Path(self.git(pending_wt, "rev-parse", "--absolute-git-dir"))
        state_before = (pending_meta / "info/florabase-agent-state.json").read_text()
        self.refused(
            "is pending",
            self.primary,
            "retire",
            AGENT_ID="operator",
            FEATURE="pending-001",
            CONFIRM_RETIRE="pending-001",
        )
        self.assertTrue(pending_wt.is_dir())
        self.assertEqual(
            (pending_meta / "info/florabase-agent-state.json").read_text(), state_before
        )

        finished_wt = self.finished("feat/pending-002")
        finished_meta = Path(self.git(finished_wt, "rev-parse", "--absolute-git-dir"))
        state_file = finished_meta / "info/florabase-agent-state.json"
        state_file.write_text(state_before)
        self.refused(
            "is pending",
            self.primary,
            "retire",
            AGENT_ID="operator",
            FEATURE="pending-002",
            CONFIRM_RETIRE="pending-002",
        )
        self.assert_finished_intact(finished_wt)
        for bad_state in (
            "{ interrupted",
            json.dumps({"version": 1}),
            json.dumps({"version": True, "writer": None, "handoff": None}),
            json.dumps({"version": 1, "writer": "corrupt", "handoff": None}),
            json.dumps({"version": 1, "writer": None, "handoff": "corrupt"}),
            json.dumps({"version": 1, "writer": None, "handoff": {}}),
            json.dumps({"version": 1, "writer": None, "handoff": {"id": "abc"}}),
        ):
            state_file.write_text(bad_state)
            self.refused("writer state", finished_wt, "require-operator", AGENT_ID="operator")
            self.refused(
                "writer state",
                self.primary,
                "retire",
                AGENT_ID="operator",
                FEATURE="pending-002",
                CONFIRM_RETIRE="pending-002",
            )
            self.assert_finished_intact(finished_wt)
        state_file.unlink()
        outside = self.root / "outside.json"
        outside.write_text(state_before)
        state_file.symlink_to(outside)
        self.refused(
            "writer state",
            self.primary,
            "retire",
            AGENT_ID="operator",
            FEATURE="pending-002",
            CONFIRM_RETIRE="pending-002",
        )
        state_file.unlink()
        self.ok(
            self.primary,
            "retire",
            AGENT_ID="operator",
            FEATURE="pending-002",
            CONFIRM_RETIRE="pending-002",
        )
        self.assertFalse(finished_wt.exists())

    def test_retirement_refuses_unmerged_branches_and_damaged_delivery_proof(self) -> None:
        unmerged = self.create("feat/unmerged-001")
        (unmerged / "unmerged.txt").write_text("unmerged\n")
        self.git(unmerged, "add", ".")
        self.git(unmerged, "commit", "-m", "unmerged")
        unmerged_sha = self.git(unmerged, "rev-parse", "HEAD")
        args = {"FEATURE": "unmerged-001", "CONFIRM_RETIRE": "unmerged-001", "AGENT_ID": "operator"}
        self.refused("still on a branch", self.primary, "retire", **args)
        self.git(unmerged, "switch", "--detach")
        self.refused("no make feature-finish proof", self.primary, "retire", **args)
        metadata = Path(self.git(unmerged, "rev-parse", "--absolute-git-dir"))
        proof_path = metadata / "info/florabase-finished.json"
        for bad_proof, needle in (
            ("[]", "damaged"),
            (json.dumps({"branch": "", "sha": unmerged_sha, "merge": unmerged_sha}), "damaged"),
            (
                json.dumps({"branch": "feat/unmerged-001", "sha": "bad", "merge": unmerged_sha}),
                "damaged",
            ),
            (
                json.dumps(
                    {
                        "branch": "feat/unmerged-001",
                        "sha": unmerged_sha,
                        "merge": unmerged_sha,
                    }
                ),
                "still exists",
            ),
        ):
            proof_path.write_text(bad_proof)
            self.refused(needle, self.primary, "retire", **args)
        self.git(self.primary, "branch", "-D", "feat/unmerged-001")
        proof_path.write_text(
            json.dumps(
                {
                    "branch": "feat/unmerged-001",
                    "sha": unmerged_sha,
                    "merge": unmerged_sha,
                }
            )
        )
        self.refused("not verified on origin/main", self.primary, "retire", **args)
        proof_path.unlink()
        outside = self.root / "forged-proof.json"
        main_sha = self.git(self.primary, "rev-parse", "HEAD")
        outside.write_text(
            json.dumps({"branch": "feat/unmerged-001", "sha": unmerged_sha, "merge": main_sha})
        )
        proof_path.symlink_to(outside)
        self.refused("damaged", self.primary, "retire", **args)
        self.assertTrue(unmerged.is_dir())
        self.assertEqual((unmerged / "unmerged.txt").read_text(), "unmerged\n")

    def test_retirement_refuses_review_and_uat_resources(self) -> None:
        worktree = self.finished()
        args = {"FEATURE": "example-001", "CONFIRM_RETIRE": "example-001", "AGENT_ID": "operator"}
        for project, kind in (
            ("florabase-feature-review", "container"),
            ("florabase-uat-preview", "volume"),
            ("florabase-uat-branch-feat-example-001", "container"),
            ("florabase-uat-branch-feat-example-001", "volume"),
        ):
            with self.subTest(project=project, kind=kind):
                if kind == "container":
                    self.write_tool(
                        "docker",
                        'printf \'%s\\n\' "$*" >>"${DOCKER_LOG}"\n'
                        f'if [[ "$1 $2" == "ps -a" && "$*" == *"source={worktree}"* ]]; then '
                        f"printf '{project}\\texited\\n'; fi\n",
                    )
                else:
                    self.write_tool(
                        "docker",
                        'printf \'%s\\n\' "$*" >>"${DOCKER_LOG}"\n'
                        f'if [[ "$1 $2" == "volume ls" && "$*" == *"source={worktree}"* ]]; then '
                        f"printf '{project}\\t{project}_postgres_data\\n'; fi\n",
                    )
                self.refused(project, self.primary, "retire", **args)
                self.assert_finished_intact(worktree)

    def test_retirement_refuses_missing_or_damaged_worktree_metadata(self) -> None:
        args = {"FEATURE": "example-001", "CONFIRM_RETIRE": "example-001", "AGENT_ID": "operator"}
        # 1. Locked worktree refuses cleanly.
        worktree = self.finished()
        self.git(self.primary, "worktree", "lock", str(worktree))
        self.refused("metadata is missing, damaged, or locked", self.primary, "retire", **args)
        self.assert_finished_intact(worktree)
        self.git(self.primary, "worktree", "unlock", str(worktree))

        # 2. Missing .git file in worktree (prunable) refuses cleanly.
        metadata = Path(self.git(worktree, "rev-parse", "--absolute-git-dir"))
        git_pointer = worktree / ".git"
        git_pointer_text = git_pointer.read_text()
        git_pointer.unlink()
        self.refused("metadata is missing, damaged, or locked", self.primary, "retire", **args)
        self.assertTrue(worktree.is_dir())
        git_pointer.write_text(git_pointer_text)

        # 3. Symlinked .git pointer refuses cleanly.
        real_pointer = self.root / "real-git-pointer"
        real_pointer.write_text(git_pointer_text)
        git_pointer.unlink()
        git_pointer.symlink_to(real_pointer)
        self.refused("metadata is missing or damaged", self.primary, "retire", **args)
        git_pointer.unlink()
        git_pointer.write_text(git_pointer_text)

        # 4. Cross-wired gitdir back-pointer refuses cleanly.
        other = self.finished("feat/other-002")
        other_meta = Path(self.git(other, "rev-parse", "--absolute-git-dir"))
        git_pointer.write_text(f"gitdir: {other_meta}\n")
        self.refused("metadata is missing or damaged", self.primary, "retire", **args)
        git_pointer.write_text(git_pointer_text)

        # 5. Missing managed marker refuses cleanly.
        marker = metadata / "info/florabase-managed-worktree"
        marker_text = marker.read_text()
        marker.unlink()
        self.refused("not created by make feature-worktree", self.primary, "retire", **args)
        marker.write_text(marker_text)

        # 6. Symlinked worktree path refuses cleanly.
        moved = self.root / "moved-worktree"
        worktree.rename(moved)
        worktree.symlink_to(moved)
        self.refused("not a registered managed worktree", self.primary, "retire", **args)
        worktree.unlink()
        moved.rename(worktree)

        # 7. Missing worktree directory (prunable) refuses cleanly.
        shutil.rmtree(worktree)
        self.refused("metadata is missing, damaged, or locked", self.primary, "retire", **args)

    def test_concurrent_retirement_is_serialized_per_target_and_blocks_active_verification(
        self,
    ) -> None:
        first = self.finished("feat/first-001")
        second = self.finished("feat/second-002")
        common = Path(self.git(self.primary, "rev-parse", "--absolute-git-dir"))
        first_suffix = hashlib.sha256(str(first.resolve()).encode("utf-8")).hexdigest()[:12]
        first_lock = common / f"florabase-retire-{first_suffix}.lock"
        holder = self.hold(
            self.primary, f"FileLock(Path({str(first_lock)!r}), 'retirement of {first}')"
        )
        self.docker_log.unlink(missing_ok=True)
        self.refused(
            "already running",
            self.primary,
            "retire",
            AGENT_ID="operator",
            FEATURE="first-001",
            CONFIRM_RETIRE="first-001",
        )
        self.assertFalse(self.docker_log.exists())
        self.assert_finished_intact(first)
        # Retiring a different worktree proceeds without contention.
        self.ok(
            self.primary,
            "retire",
            AGENT_ID="operator",
            FEATURE="second-002",
            CONFIRM_RETIRE="second-002",
        )
        self.assertFalse(second.exists())
        self.release(holder)

        # Real concurrent processes targeting the same worktree: at most one succeeds.
        results = [
            subprocess.Popen(
                [sys.executable, str(HELPER), "retire"],
                cwd=self.primary,
                env=self.env(AGENT_ID="operator", FEATURE="first-001", CONFIRM_RETIRE="first-001"),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for _ in range(3)
        ]
        outcomes = [(proc.communicate()[1], proc.returncode) for proc in results]
        codes = [code for _, code in outcomes]
        self.assertEqual(codes.count(0), 1, outcomes)
        for err, code in outcomes:
            if code != 0:
                self.assertTrue(
                    "already running" in err or "not a registered managed worktree" in err, err
                )
        self.assertFalse(first.exists())
        self.assertFalse((common / "worktrees/first-001").exists())

        # Active retirement holds target verification lock during Docker/mount preflight.
        third = self.finished("feat/third-003")
        third_meta = Path(self.git(third, "rev-parse", "--absolute-git-dir"))
        verify_during_retire: list[int] = []

        def probe_lock(target_repo: Repository) -> dict[str, dict[str, int]]:
            probe = subprocess.run(
                [sys.executable, str(HELPER), "require-operator"],
                cwd=third,
                env=self.env(AGENT_ID="operator"),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
            )
            verify_during_retire.append(probe.returncode)
            self.assertIn("verification of this worktree is already running", probe.stderr)
            return {}

        with (
            contextlib.chdir(self.primary),
            patch.dict(os.environ, self.env(AGENT_ID="operator"), clear=True),
            patch.object(feature_worktree, "owned_resources", side_effect=probe_lock),
            patch.object(feature_worktree, "require_no_running_mounts"),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            feature_worktree.retire(Repository(self.primary), "third-003", "third-003")
        self.assertEqual(verify_during_retire, [1])
        self.assertFalse(third.exists())
        self.assertFalse(third_meta.exists())

    # Instructions ------------------------------------------------------------------------------

    def test_agents_md_is_the_only_instruction_source_and_is_provider_neutral(self) -> None:
        for competing in ("CLAUDE.md", ".claude/CLAUDE.md", "AGENTS.override.md", "opencode.json"):
            self.assertFalse((ROOT / competing).exists(), competing)
        text = (ROOT / "AGENTS.md").read_text()
        for phrase in ("make feature-worktree", "make feature-claim", "make feature-handoff"):
            self.assertIn(phrase, text)
        self.assertNotIn("Codex-managed", text)
        self.assertNotIn("detached Codex", text)
        workflow = (ROOT / "docs/development-workflow.md").read_text()
        for stale in ("Codex manages its own worktrees", "Codex owns archiving", "(Sol)", "(Luna)"):
            self.assertNotIn(stale, workflow)


if __name__ == "__main__":
    unittest.main()
