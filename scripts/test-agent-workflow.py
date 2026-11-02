#!/usr/bin/env python3
"""Offline regressions for provider-neutral worktrees, writers, handoffs, locks and retirement.

Real Git and real kernel locks run on disposable fixtures. Provider identities are only AGENT_ID
values, GitHub and Docker are PATH mocks, and every Docker argument is recorded and asserted.
"""

from __future__ import annotations

import itertools
import json
import os
import pty
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parent.parent
HELPER = ROOT / "scripts/feature_worktree.py"
GITHUB = "https://github.com/alessandrorossato/florabase.git"
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
        return subprocess.run(
            [sys.executable, str(HELPER), command, *args],
            cwd=cwd,
            env=self.env(**values),
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
            "from workflow_resources import machine_lock, verification_lock\n"
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

    def finished(self, branch: str = "feat/example-001") -> Path:
        worktree = self.create(branch)
        self.ok(worktree, "claim", AGENT_ID="claude-code")
        (worktree / "feature.txt").write_text("feature\n")
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
        # DEV/Review/UAT data preservation: retirement only ever lists Docker state.
        for line in self.docker_log.read_text().splitlines():
            self.assertTrue(line.startswith(("ps -a --filter", "volume ls --filter")), line)

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
