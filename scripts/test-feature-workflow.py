#!/usr/bin/env python3
"""Focused no-network tests for feature verification and delivery helpers."""

from __future__ import annotations

import importlib.util
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
DELIVER_PATH = ROOT / "scripts/feature-deliver.py"
SPEC = importlib.util.spec_from_file_location("feature_deliver", DELIVER_PATH)
assert SPEC and SPEC.loader
feature_deliver = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = feature_deliver
SPEC.loader.exec_module(feature_deliver)


class VerifyHelperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.remote = self.root / "remote.git"
        self.seed = self.root / "seed"
        self.work = self.root / "work"
        self.shell("git", "init", "--bare", "--initial-branch=main", str(self.remote))
        self.shell("git", "init", "--initial-branch=main", str(self.seed))
        self.shell("git", "-C", str(self.seed), "config", "user.name", "Test")
        self.shell("git", "-C", str(self.seed), "config", "user.email", "test@example.invalid")
        (self.seed / ".gitignore").write_text("__pycache__/\n*.pyc\n")
        (self.seed / "docs").mkdir()
        (self.seed / "backend/alembic/versions").mkdir(parents=True)
        (self.seed / "docs/features.json").write_text(
            json.dumps(
                {
                    "allowed_statuses": ["planned", "implemented"],
                    "features": [
                        {
                            "id": "CI-002",
                            "category": "testing",
                            "description": "test",
                            "acceptance_criteria": ["test"],
                            "dependencies": [],
                            "priority": "P0",
                            "status": "implemented",
                        }
                    ],
                }
            )
        )
        # Real Alembic revisions use ordinary assignments; the migration-cycle
        # verifier must also accept annotated declarations used by some fixtures.
        (self.seed / "backend/alembic/versions/0001_base.py").write_text(
            'revision = "0001"\ndown_revision = None\n'
        )
        self.shell("git", "-C", str(self.seed), "add", ".")
        self.shell("git", "-C", str(self.seed), "commit", "-m", "base")
        self.shell("git", "-C", str(self.seed), "remote", "add", "origin", str(self.remote))
        self.shell("git", "-C", str(self.seed), "push", "-u", "origin", "main")
        self.shell("git", "clone", str(self.remote), str(self.work))
        self.shell("git", "-C", str(self.work), "config", "user.name", "Test")
        self.shell("git", "-C", str(self.work), "config", "user.email", "test@example.invalid")
        self.shell("git", "-C", str(self.work), "switch", "-c", "ci/ci-002")
        scripts = self.work / "scripts"
        scripts.mkdir()
        for name in (
            "feature-verify.sh",
            "feature-tree-fingerprint.py",
            "check-features.py",
            "verify-migration-cycle.sh",
            "verification_impact.py", "verification_gate.py", "verification-impact.json",
            "disposable_workflow.py", "workflow_resources.py",
        ):
            shutil.copy2(ROOT / "scripts" / name, scripts / name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        (self.bin / "make").write_text(
            "#!/usr/bin/env bash\nset -eu\nprintf '%s\\n' \"$*\" >>\"${VERIFY_LOG}\"\n"
            "if [[ \"${VERIFY_FAIL_STAGE:-}\" == \"$1\" ]]; then exit 7; fi\n"
            "if [[ \"${VERIFY_MUTATE_STAGE:-}\" == \"$1\" ]]; then echo changed > during-verify.txt; fi\n"
        )
        (self.bin / "docker").write_text(
            "#!/usr/bin/env bash\nset -eu\nprintf '%s\\n' \"$*\" >>\"${VERIFY_LOG}\"\n"
            "if [[ \"$*\" == *scripts/verify_migration_cycle.py* ]]; then\n"
            "  if [[ \"${VERIFY_MIGRATION_FAIL:-}\" == 1 ]]; then exit 7; fi\n"
            "  if [[ \"${VERIFY_MIGRATION_SKIP:-}\" == 1 ]]; then exit 0; fi\n"
            "  python3 - <<'EVIDENCE'\n"
            "import json, sys\nsys.path.insert(0, 'scripts')\n"
            "from disposable_workflow import expected_migration_evidence, SCHEMA_REPORT\n"
            "print(SCHEMA_REPORT + json.dumps(expected_migration_evidence('origin/main')['verified_revisions']))\n"
            "EVIDENCE\nfi\n"
        )
        os.chmod(self.bin / "make", 0o755)
        os.chmod(self.bin / "docker", 0o755)
        self.log = self.root / "verify.log"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def shell(*command: str) -> None:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def verify(self, *, full: bool = False, **environment: str) -> subprocess.CompletedProcess[str]:
        env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "VERIFY_LOG": str(self.log),
            **environment,
        }
        return subprocess.run(
            [str(self.work / "scripts/feature-verify.sh"), *(["--full"] if full else [])],
            cwd=self.work,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def establish_helper_baseline(self) -> None:
        # Put unchanged helpers into disposable origin/main: the only feature diff can now be a lock.
        (self.work / "frontend").mkdir()
        (self.work / "frontend/pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n")
        self.shell("git", "-C", str(self.work), "add", ".")
        self.shell("git", "-C", str(self.work), "commit", "-m", "fixture helpers")
        self.shell("git", "-C", str(self.work), "push", "origin", "HEAD:main")
        self.shell("git", "-C", str(self.work), "fetch", "origin", "main")

    def receipt(self) -> dict:
        return json.loads((self.work / ".git/info/florabase-feature-verification.json").read_text())

    def test_dependency_only_full_executes_exhaustive_stages_without_revision_diff(self) -> None:
        self.establish_helper_baseline()
        lock = self.work / "frontend/pnpm-lock.yaml"
        lock.write_text(lock.read_text() + "# synthetic dependency change\n")
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = self.receipt()
        self.assertEqual(receipt["verification"]["changed_paths"], ["frontend/pnpm-lock.yaml"])
        self.assertEqual(receipt["verification"]["mode"], "full")
        migration = next(c for c in receipt["completed"] if c["id"] == "migration-cycle")
        self.assertIn("--force-cycle", migration["command"])
        self.assertEqual(migration["evidence"]["verified_revisions"], ["0001"] * 4)
        self.assertEqual(receipt["migration"]["decision"], "full-cycle")
        self.assertTrue(receipt["migration"]["cycle_executed"])
        log = self.log.read_text().splitlines()
        for command in ("check", "test-integration", "verify-build SERVICES=backend frontend"):
            self.assertIn(command, log)
        self.assertIn("MIGRATION_CYCLE_PASSED", result.stdout)
        self.assertNotIn("no Alembic revisions added", result.stdout)

    def test_docs_affected_skips_and_explicit_full_executes_same_cycle(self) -> None:
        self.establish_helper_baseline()
        (self.work / "docs/iteration.md").write_text("synthetic documentation\n")
        affected = self.verify()
        self.assertEqual(affected.returncode, 0, affected.stderr)
        self.assertEqual(self.receipt()["migration"], {
            "decision": "skip", "cycle_required": False, "cycle_executed": False,
            "result": "skipped_by_impact", "evidence": None,
        })
        self.assertNotIn("cycling", affected.stdout)
        self.assertFalse(self.log.exists())
        full = self.verify(full=True)
        self.assertEqual(full.returncode, 0, full.stderr)
        self.assertEqual(self.receipt()["migration"]["decision"], "full-cycle")
        self.assertEqual(self.receipt()["migration"]["evidence"]["verified_revisions"], ["0001"] * 4)
        self.assertIn("--force-cycle", full.stdout)

    def test_full_cannot_accept_skipped_or_failed_migration_runner(self) -> None:
        self.establish_helper_baseline()
        for environment in ({"VERIFY_MIGRATION_SKIP": "1"}, {"VERIFY_MIGRATION_FAIL": "1"}):
            with self.subTest(environment=environment):
                result = self.verify(full=True, **environment)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("FEATURE_VERIFICATION_PASSED", result.stdout)
                self.assertFalse((self.work / ".git/info/florabase-feature-verification.json").exists())

    def test_delivery_preflight_rejects_invalid_full_cycle_and_historical_v2(self) -> None:
        self.establish_helper_baseline()
        (self.work / "frontend/pnpm-lock.yaml").write_text("# synthetic lock\n")
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.shell("git", "-C", str(self.work), "add", ".")
        self.shell("git", "-C", str(self.work), "commit", "-m", "fixture feature")
        original = self.receipt()
        base = subprocess.check_output(["git", "-C", str(self.work), "rev-parse", "origin/main"], text=True).strip()
        fixture = self

        class LocalPreflightCommands(FakeCommands):
            def run(self, *command: str, capture: bool = False) -> str:
                if command[0] == "python3":
                    result = subprocess.run(command, cwd=fixture.work, text=True, capture_output=True)
                    if result.returncode:
                        raise feature_deliver.DeliveryError(result.stderr)
                    return result.stdout
                return super().run(*command, capture=capture)

        responses = {
            ("gh", "api", "repos/alessandrorossato/florabase"): "{}",
            ("git", "branch", "--show-current"): "ci/ci-002",
            ("git", "remote", "get-url", "origin"): "https://github.com/alessandrorossato/florabase.git",
            ("git", "merge-base", "origin/main", "HEAD"): base,
        }
        feature_deliver.Delivery(LocalPreflightCommands(responses)).preflight()
        invalid = []
        for key, value in (("cycle_executed", False), ("cycle_executed", 1), ("result", "skipped_by_impact"), ("evidence", None), ("decision", "skip")):
            invalid.append({**original, "migration": {**original["migration"], key: value}})
        missing = dict(original)
        del missing["migration"]
        invalid.append(missing)
        historical = dict(missing)
        historical["migration_result"] = "passed"
        historical["verification"] = {**historical["verification"], "migration": True, "migration_cycle": False}
        invalid.append(historical)
        for key, value in (("cleanup_verified", False), ("cleanup_verified", 1), ("verified_revisions", ["0001"]), ("cycle_executed", False), ("cycle_executed", 1)):
            completed = [dict(c) for c in original["completed"]]
            cycle = next(c for c in completed if c["id"] == "migration-cycle")
            cycle["evidence"] = {**cycle["evidence"], key: value}
            invalid.append({**original, "completed": completed})
        for receipt in invalid:
            (self.work / ".git/info/florabase-feature-verification.json").write_text(json.dumps(receipt))
            commands = LocalPreflightCommands(responses)
            with self.assertRaises(feature_deliver.DeliveryError):
                feature_deliver.Delivery(commands).preflight()
            self.assertFalse(any(c[:2] == ("git", "push") for c in commands.calls))

    def test_success_without_migration_writes_receipt_and_pass_marker(self) -> None:
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("FEATURE_VERIFICATION_PASSED", result.stdout)
        self.assertIn("cycling 0001 -> head -> 0001 -> head", result.stdout)
        self.assertTrue((self.work / ".git/info/florabase-feature-verification.json").exists())
        self.assertNotIn("down --volumes", self.log.read_text())

    def test_stage_failure_propagates_failure_marker(self) -> None:
        self.assertEqual(self.verify().returncode, 0)
        result = self.verify(VERIFY_FAIL_STAGE="check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stage failed: quality", result.stderr)
        self.assertIn("FEATURE_VERIFICATION_FAILED", result.stderr)
        self.assertFalse((self.work / ".git/info/florabase-feature-verification.json").exists())

    def test_concurrent_source_change_cannot_receive_a_verification_receipt(self) -> None:
        result = self.verify(VERIFY_MUTATE_STAGE="check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source tree changed during verification", result.stderr)
        self.assertFalse((self.work / ".git/info/florabase-feature-verification.json").exists())

    def test_linked_worktree_keeps_its_receipt_in_its_own_git_directory(self) -> None:
        primary = self.work
        linked = self.root / "linked"
        self.shell("git", "-C", str(primary), "switch", "main")
        self.shell("git", "-C", str(primary), "worktree", "add", "-b", "fix/worktree-receipt", str(linked))
        shutil.copytree(primary / "scripts", linked / "scripts")
        migration = linked / "backend/alembic/versions/0002_dirty.py"
        migration.write_text('revision = "0002"\ndown_revision = "0001"\n')
        (linked / "symlink.txt").symlink_to("backend/alembic/versions/0002_dirty.py")
        self.work = linked
        self.assertTrue((linked / ".git").is_file())
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("FEATURE_VERIFICATION_PASSED", result.stdout)
        git_directory = Path(subprocess.run(
            ["git", "rev-parse", "--absolute-git-dir"], cwd=linked,
            check=True, text=True, stdout=subprocess.PIPE,
        ).stdout.strip())
        receipt = git_directory / "info/florabase-feature-verification.json"
        self.assertEqual(json.loads(receipt.read_text())["branch"], "fix/worktree-receipt")
        self.assertFalse((primary / ".git/info/florabase-feature-verification.json").exists())
        base = self.shell_output("git", "-C", str(linked), "rev-parse", "origin/main")
        receipt_command = [
            sys.executable, str(linked / "scripts/feature-tree-fingerprint.py"), "verify",
            "--branch", "fix/worktree-receipt", "--base", base,
        ]
        before_commit = subprocess.run(
            [*receipt_command, "--worktree"], cwd=linked, text=True, capture_output=True,
        )
        self.assertEqual(before_commit.returncode, 0, before_commit.stderr)
        delivery_before_commit = subprocess.run(receipt_command, cwd=linked, text=True, capture_output=True)
        self.assertNotEqual(delivery_before_commit.returncode, 0)
        self.assertIn("commit the verified tree", delivery_before_commit.stderr)
        # Commit only this temporary fixture to exercise the delivery-time read path.
        self.shell("git", "-C", str(linked), "add", ".")
        self.shell("git", "-C", str(linked), "commit", "-m", "fixture helpers")
        base = subprocess.run(
            ["git", "rev-parse", "origin/main"], cwd=linked,
            check=True, text=True, stdout=subprocess.PIPE,
        ).stdout.strip()
        checked = subprocess.run(
            [sys.executable, str(linked / "scripts/feature-tree-fingerprint.py"), "verify",
             "--branch", "fix/worktree-receipt", "--base", base],
            cwd=linked, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(self.shell_output("git", "-C", str(primary), "branch", "--show-current"), "main")
        # Dirty/untracked source after commit must invalidate even direct receipt verification.
        migration.write_text(migration.read_text() + "# changed after verification\n")
        invalid = subprocess.run(checked.args, cwd=linked, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn("working tree differs", invalid.stderr)
        dirty_worktree_check = subprocess.run(
            [*receipt_command, "--worktree"], cwd=linked, text=True, capture_output=True,
        )
        self.assertNotEqual(dirty_worktree_check.returncode, 0)
        self.assertIn("working tree differs", dirty_worktree_check.stderr)

    @staticmethod
    def shell_output(*command: str) -> str:
        return subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE).stdout.strip()

    def test_added_migration_selects_disposable_cycle(self) -> None:
        migration = self.work / "backend/alembic/versions/0002_feature.py"
        migration.write_text('revision: str = "0002"\ndown_revision: str | None = "0001"\n')
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.log.read_text()
        self.assertIn("python scripts/verify_migration_cycle.py 0001", log)
        self.assertIn("florabase-feature-migration-", log)
        self.assertNotIn("down --volumes", log)


class FakeCommands:
    def __init__(self, responses: dict[tuple[str, ...], list[str] | str]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, ...]] = []

    def run(self, *command: str, capture: bool = False) -> str:
        self.calls.append(command)
        response = self.responses.get(command, "")
        if isinstance(response, list):
            return response.pop(0) if response else ""
        return response


class FailingCommands(FakeCommands):
    def __init__(self, responses: dict[tuple[str, ...], list[str] | str], fail_on: tuple[str, ...]) -> None:
        super().__init__(responses)
        self.fail_on = fail_on

    def run(self, *command: str, capture: bool = False) -> str:
        if command == self.fail_on:
            raise feature_deliver.DeliveryError("mock command failure")
        return super().run(*command, capture=capture)


def pr(
    number: int = 7,
    sha: str = "feature-sha",
    state: str = "open",
    merge: str | None = None,
    merged: bool = False,
    head: str = "ci/ci-002",
    base: str = "main",
) -> str:
    return json.dumps(
        {
            "number": number,
            "node_id": "PR_node",
            "state": state,
            "head": {
                "ref": head,
                "sha": sha,
                "repo": {"full_name": "alessandrorossato/florabase"},
            },
            "base": {"ref": base},
            "merge_commit_sha": merge,
            "merged": merged,
            "html_url": "https://example.invalid/pr/7",
        }
    )


def associated_pr(
    number: int = 7,
    sha: str = "feature-sha",
    head: str = "ci/ci-002",
    base: str = "main",
    repository: str = "alessandrorossato/florabase",
) -> dict[str, object]:
    return {
        "number": number,
        "headRefName": head,
        "headRefOid": sha,
        "baseRefName": base,
        "headRepository": {"nameWithOwner": repository},
    }


def completed_delivery_lookup(nodes: list[dict[str, object]] | None) -> dict[str, object]:
    return {
        "data": {
            "repository": {
                "object": None
                if nodes is None
                else {"associatedPullRequests": {"nodes": nodes, "pageInfo": {"hasNextPage": False}}}
            }
        }
    }


class DeliveryTests(unittest.TestCase):
    def delivery(self) -> feature_deliver.Delivery:
        return feature_deliver.Delivery(FakeCommands({}), sleep=lambda _: None)

    def test_real_missing_gh_command_has_actionable_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            Path(temporary, "git").symlink_to(shutil.which("git"))
            result = subprocess.run(
                [sys.executable, str(DELIVER_PATH)], cwd=ROOT,
                env={**os.environ, "PATH": temporary}, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("GitHub CLI `gh` is required but was not found in PATH", result.stderr)

    def test_preflight_rejects_main_dirty_wrong_origin_and_missing_gh(self) -> None:
        for branch, dirty, origin, error in (
            ("main", "", "https://github.com/alessandrorossato/florabase.git", "not main"),
            ("feat/test", " M changed", "https://github.com/alessandrorossato/florabase.git", "not clean"),
            ("feat/test", "", "https://github.com/example/wrong.git", "not the expected"),
        ):
            commands = FakeCommands(
                {
                    ("git", "--version"): "git",
                    ("gh", "--version"): "gh",
                    ("git", "branch", "--show-current"): branch,
                    ("git", "status", "--porcelain"): dirty,
                    ("git", "remote", "get-url", "origin"): origin,
                }
            )
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaisesRegex(
                feature_deliver.DeliveryError, error
            ):
                feature_deliver.Delivery(commands).preflight()

    def test_preflight_accepts_only_a_clean_verified_feature(self) -> None:
        commands = FakeCommands(
            {
                ("git", "--version"): "git",
                ("gh", "--version"): "gh",
                ("git", "branch", "--show-current"): "ci/ci-002",
                ("git", "status", "--porcelain"): "",
                ("git", "remote", "get-url", "origin"): "git@github.com:alessandrorossato/florabase.git",
                ("git", "rev-parse", "--verify", "HEAD^{commit}"): "feature-sha",
                ("gh", "auth", "status"): "",
                ("git", "fetch", "origin", "main"): "",
                ("git", "show-ref", "--verify", "--quiet", "refs/remotes/origin/main"): "",
                ("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"): "",
                ("git", "merge-base", "origin/main", "HEAD"): "base-sha",
                ("gh", "api", "repos/alessandrorossato/florabase"): "{}",
                ("git", "ls-remote", "--heads", "origin", "refs/heads/ci/ci-002"): "",
                ("git", "rev-parse", "HEAD"): "feature-sha",
            }
        )
        with patch("subprocess.run") as fingerprint:
            fingerprint.return_value = subprocess.CompletedProcess([], 0)
            self.assertEqual(
                feature_deliver.Delivery(commands).preflight(),
                feature_deliver.Preflight(
                    branch="ci/ci-002",
                    base_sha="base-sha",
                    delivery_sha="feature-sha",
                ),
            )

    def test_missing_gh_and_divergent_remote_branch_stop_before_push(self) -> None:
        with self.assertRaises(feature_deliver.DeliveryError):
            feature_deliver.Delivery(FailingCommands({}, ("gh", "--version"))).preflight()

        commands = FailingCommands(
            {
                ("git", "--version"): "git",
                ("gh", "--version"): "gh",
                ("git", "branch", "--show-current"): "ci/ci-002",
                ("git", "status", "--porcelain"): "",
                ("git", "remote", "get-url", "origin"): "https://github.com/alessandrorossato/florabase.git",
                ("git", "rev-parse", "--verify", "HEAD^{commit}"): "feature-sha",
                ("gh", "auth", "status"): "",
                ("git", "fetch", "origin", "main"): "",
                ("git", "show-ref", "--verify", "--quiet", "refs/remotes/origin/main"): "",
                ("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"): "",
                ("git", "merge-base", "origin/main", "HEAD"): "base-sha",
                ("gh", "api", "repos/alessandrorossato/florabase"): "{}",
                ("git", "ls-remote", "--heads", "origin", "refs/heads/ci/ci-002"): "remote-sha\trefs/heads/ci/ci-002",
                ("git", "fetch", "origin", "refs/heads/ci/ci-002:refs/remotes/origin/ci/ci-002"): "",
            },
            ("git", "merge-base", "--is-ancestor", "remote-sha", "HEAD"),
        )
        with patch("subprocess.run") as fingerprint, contextlib.redirect_stderr(io.StringIO()), self.assertRaises(
            feature_deliver.DeliveryError
        ):
            fingerprint.return_value = subprocess.CompletedProcess([], 0)
            feature_deliver.Delivery(commands).preflight()
        self.assertNotIn("push", " ".join(part for call in commands.calls for part in call))

    def test_current_sha_checks_ignore_stale_results_and_handle_startup_delay(self) -> None:
        delivery = self.delivery()
        pull = feature_deliver.Delivery.pr_from(json.loads(pr()))
        calls: list[str] = []
        delivery.current_pr = lambda _: pull  # type: ignore[method-assign]
        responses = [
            {},
            {
                name: {"status": "completed", "conclusion": "success"}
                for name in feature_deliver.REQUIRED_CHECKS
            },
        ]
        delivery.check_runs = lambda sha: (calls.append(sha) or responses.pop(0))  # type: ignore[method-assign]
        delivery.wait_for_checks(pull, "ci/ci-002", "feature-sha")
        self.assertEqual(calls, ["feature-sha", "feature-sha"])

    def test_merged_pr_still_requires_successful_current_sha_checks(self) -> None:
        delivery = self.delivery()
        merged = feature_deliver.Delivery.pr_from(
            json.loads(pr(state="closed", merge="main-sha", merged=True))
        )
        calls: list[str] = []
        delivery.current_pr = lambda _: merged  # type: ignore[method-assign]
        delivery.check_runs = lambda sha: (  # type: ignore[method-assign]
            calls.append(sha)
            or {
                name: {"status": "completed", "conclusion": "success"}
                for name in feature_deliver.REQUIRED_CHECKS
            }
        )
        delivery.wait_for_checks(merged, "ci/ci-002", "feature-sha")
        self.assertEqual(calls, ["feature-sha"])

    def test_check_and_merge_polls_revalidate_branch_repository_and_base(self) -> None:
        for method in ("checks", "merge"):
            for malformed in (
                json.loads(pr(head="ci/unexpected")),
                json.loads(pr(base="release")),
                {
                    **json.loads(pr()),
                    "head": {
                        **json.loads(pr())["head"],
                        "repo": {"full_name": "someone-else/florabase"},
                    },
                },
            ):
                with self.subTest(method=method, malformed=malformed):
                    delivery = self.delivery()
                    pull = feature_deliver.Delivery.pr_from(json.loads(pr()))
                    delivery.current_pr = lambda _, malformed=malformed: feature_deliver.Delivery.pr_from(  # type: ignore[method-assign]
                        malformed
                    )
                    if method == "checks":
                        delivery.check_runs = lambda _: {  # type: ignore[method-assign]
                            name: {"status": "completed", "conclusion": "success"}
                            for name in feature_deliver.REQUIRED_CHECKS
                        }
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(
                        feature_deliver.DeliveryError
                    ):
                        if method == "checks":
                            delivery.wait_for_checks(pull, "ci/ci-002", "feature-sha")
                        else:
                            delivery.wait_for_merge(pull, "ci/ci-002", "feature-sha")

    def test_merged_recovery_blocks_missing_or_failed_required_checks(self) -> None:
        for checks in (
            {},
            {
                name: {"status": "completed", "conclusion": "failure"}
                for name in feature_deliver.REQUIRED_CHECKS
            },
        ):
            with self.subTest(checks=checks):
                delivery = self.delivery()
                delivery.startup_timeout_seconds = 0
                merged = feature_deliver.Delivery.pr_from(
                    json.loads(pr(state="closed", merge="main-sha", merged=True))
                )
                delivery.current_pr = lambda _: merged  # type: ignore[method-assign]
                delivery.check_runs = lambda _, checks=checks: checks  # type: ignore[method-assign]
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(
                    feature_deliver.DeliveryError
                ):
                    delivery.wait_for_checks(merged, "ci/ci-002", "feature-sha")

    def test_missing_checks_eventually_time_out_safely(self) -> None:
        delivery = self.delivery()
        delivery.startup_timeout_seconds = 0
        pull = feature_deliver.Delivery.pr_from(json.loads(pr()))
        delivery.current_pr = lambda _: pull  # type: ignore[method-assign]
        delivery.check_runs = lambda _: {}  # type: ignore[method-assign]
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(feature_deliver.DeliveryError):
            delivery.wait_for_checks(pull, "ci/ci-002", "feature-sha")

    def test_failed_cancelled_and_timed_out_checks_block_delivery(self) -> None:
        for conclusion in ("failure", "cancelled", "timed_out"):
            delivery = self.delivery()
            pull = feature_deliver.Delivery.pr_from(json.loads(pr()))
            delivery.current_pr = lambda _: pull  # type: ignore[method-assign]
            delivery.check_runs = lambda _: {  # type: ignore[method-assign]
                name: {"status": "completed", "conclusion": conclusion, "details_url": "url"}
                for name in feature_deliver.REQUIRED_CHECKS
            }
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(feature_deliver.DeliveryError):
                delivery.wait_for_checks(pull, "ci/ci-002", "feature-sha")

    def test_new_pr_creation_existing_reuse_and_normal_push(self) -> None:
        delivery = self.delivery()
        api_calls: list[tuple[str, str]] = []
        delivery.api = lambda endpoint, method="GET", fields=None: (  # type: ignore[method-assign]
            api_calls.append((method, endpoint)) or ([] if method == "GET" else json.loads(pr()))
        )
        created = delivery.find_or_create_pr("ci/ci-002", "feature-sha", False)
        self.assertEqual(created.number, 7)
        delivery.api = lambda endpoint, method="GET", fields=None: [json.loads(pr(sha="follow-up-sha"))]  # type: ignore[method-assign]
        reused = delivery.find_or_create_pr("ci/ci-002", "follow-up-sha", False)
        self.assertEqual(reused.number, 7)
        self.assertIn(("POST", "repos/alessandrorossato/florabase/pulls"), api_calls)
        commands = FakeCommands(
            {
                ("git", "rev-parse", "HEAD"): "feature-sha",
                ("git", "push", "--set-upstream", "origin", "ci/ci-002"): "",
            }
        )
        feature_deliver.Delivery(commands).push("ci/ci-002", "feature-sha")
        self.assertNotIn("--force", " ".join(part for call in commands.calls for part in call))

    def test_normal_delivery_still_follows_push_pr_checks_and_merge_sequence(self) -> None:
        delivery = self.delivery()
        open_pr = feature_deliver.Delivery.pr_from(json.loads(pr()))
        merged_pr = feature_deliver.Delivery.pr_from(
            json.loads(pr(state="closed", merge="main-sha", merged=True))
        )
        calls: list[str] = []
        delivery.preflight = lambda: feature_deliver.Preflight("ci/ci-002", "base-sha", "feature-sha")  # type: ignore[method-assign]
        delivery.migration_detected = lambda *_: False  # type: ignore[method-assign]
        delivery.is_ancestor = lambda *_: True  # type: ignore[method-assign]
        delivery.completed_pr_for_delivery = lambda *_: None  # type: ignore[method-assign]
        delivery.push = lambda *_: calls.append("push")  # type: ignore[method-assign]
        delivery.find_or_create_pr = lambda *_: calls.append("pr") or open_pr  # type: ignore[method-assign]
        delivery.wait_for_pr_head = lambda *_: calls.append("head") or open_pr  # type: ignore[method-assign]
        delivery.enable_auto_merge = lambda *_: calls.append("auto-merge")  # type: ignore[method-assign]
        delivery.wait_for_checks = lambda *_: calls.append("checks")  # type: ignore[method-assign]
        delivery.wait_for_merge = lambda *_: calls.append("merge") or merged_pr  # type: ignore[method-assign]
        delivery.complete_delivery = lambda *_: calls.append("complete")  # type: ignore[method-assign]
        delivery.execute()
        self.assertEqual(calls, ["push", "pr", "head", "auto-merge", "checks", "merge", "complete"])

    def test_local_only_sha_continues_from_recovery_to_normal_push(self) -> None:
        delivery = self.delivery()
        open_pr = feature_deliver.Delivery.pr_from(json.loads(pr()))
        merged_pr = feature_deliver.Delivery.pr_from(
            json.loads(pr(state="closed", merge="main-sha", merged=True))
        )
        calls: list[str] = []
        queries: list[dict[str, str]] = []
        delivery.preflight = lambda: feature_deliver.Preflight("ci/ci-002", "base-sha", "feature-sha")  # type: ignore[method-assign]
        delivery.migration_detected = lambda *_: False  # type: ignore[method-assign]
        delivery.is_ancestor = lambda *_: True  # type: ignore[method-assign]
        delivery.graphql = lambda _, fields: queries.append(fields) or completed_delivery_lookup(None)  # type: ignore[method-assign]
        delivery.push = lambda *_: calls.append("push")  # type: ignore[method-assign]
        delivery.find_or_create_pr = lambda *_: calls.append("pr") or open_pr  # type: ignore[method-assign]
        delivery.wait_for_pr_head = lambda *_: open_pr  # type: ignore[method-assign]
        delivery.enable_auto_merge = lambda *_: None  # type: ignore[method-assign]
        delivery.wait_for_checks = lambda *_: None  # type: ignore[method-assign]
        delivery.wait_for_merge = lambda *_: merged_pr  # type: ignore[method-assign]
        delivery.complete_delivery = lambda *_: calls.append("complete")  # type: ignore[method-assign]
        delivery.execute()
        self.assertEqual(queries, [{"owner": "alessandrorossato", "name": "florabase", "expression": "feature-sha"}])
        self.assertEqual(calls, ["push", "pr", "complete"])

    def test_completed_delivery_lookup_failure_does_not_become_a_normal_push(self) -> None:
        delivery = self.delivery()
        calls: list[str] = []
        delivery.preflight = lambda: feature_deliver.Preflight("ci/ci-002", "base-sha", "feature-sha")  # type: ignore[method-assign]
        delivery.migration_detected = lambda *_: False  # type: ignore[method-assign]
        delivery.is_ancestor = lambda *_: True  # type: ignore[method-assign]
        delivery.graphql = lambda *_: (_ for _ in ()).throw(feature_deliver.DeliveryError("GitHub unavailable"))  # type: ignore[method-assign]
        delivery.push = lambda *_: calls.append("push")  # type: ignore[method-assign]
        with self.assertRaises(feature_deliver.DeliveryError):
            delivery.execute()
        self.assertEqual(calls, [])

    def test_lowercase_rest_open_state_is_accepted_for_created_and_reused_prs(self) -> None:
        delivery = self.delivery()
        api_calls: list[tuple[str, str]] = []
        delivery.api = lambda endpoint, method="GET", fields=None: (  # type: ignore[method-assign]
            api_calls.append((method, endpoint)) or ([] if method == "GET" else json.loads(pr(state="open")))
        )
        created = delivery.find_or_create_pr("ci/ci-002", "feature-sha", False)
        self.assertEqual(created.state, "OPEN")
        delivery.api = lambda endpoint, method="GET", fields=None: [json.loads(pr(state="oPeN"))]  # type: ignore[method-assign]
        reused = delivery.find_or_create_pr("ci/ci-002", "feature-sha", False)
        self.assertEqual(reused.state, "OPEN")
        self.assertEqual(api_calls.count(("POST", "repos/alessandrorossato/florabase/pulls")), 1)

    def test_pr_head_propagation_waits_for_current_delivery_sha_without_duplicate_pr(self) -> None:
        sleeps: list[int] = []
        delivery = feature_deliver.Delivery(FakeCommands({}), sleep=sleeps.append)
        api_calls: list[tuple[str, str]] = []
        stale = json.loads(pr(sha="old-sha"))
        delivery.api = lambda endpoint, method="GET", fields=None: (  # type: ignore[method-assign]
            api_calls.append((method, endpoint)) or [stale]
        )
        reused = delivery.find_or_create_pr("ci/ci-002", "new-sha", False)
        snapshots = iter(
            [
                feature_deliver.Delivery.pr_from(json.loads(pr(sha="old-sha"))),
                feature_deliver.Delivery.pr_from(json.loads(pr(sha="old-sha"))),
                feature_deliver.Delivery.pr_from(json.loads(pr(sha="new-sha"))),
            ]
        )
        delivery.current_pr = lambda _: next(snapshots)  # type: ignore[method-assign]
        with contextlib.redirect_stdout(io.StringIO()) as output:
            current = delivery.wait_for_pr_head(reused, "ci/ci-002", "new-sha")
        self.assertEqual(current.head_sha, "new-sha")
        self.assertEqual(sleeps, [delivery.pr_head_poll_seconds] * 3)
        self.assertIn("waiting for PR #7 head to update to new-sha", output.getvalue())
        self.assertNotIn(("POST", "repos/alessandrorossato/florabase/pulls"), api_calls)

    def test_pr_head_already_current_does_not_poll(self) -> None:
        sleeps: list[int] = []
        delivery = feature_deliver.Delivery(FakeCommands({}), sleep=sleeps.append)
        current = feature_deliver.Delivery.pr_from(json.loads(pr(sha="new-sha")))
        delivery.current_pr = lambda _: self.fail("current PR should not be read")  # type: ignore[method-assign]
        self.assertIs(delivery.wait_for_pr_head(current, "ci/ci-002", "new-sha"), current)
        self.assertEqual(sleeps, [])

    def test_pr_head_propagation_times_out_safely(self) -> None:
        delivery = self.delivery()
        delivery.pr_head_timeout_seconds = 0
        stale = feature_deliver.Delivery.pr_from(json.loads(pr(sha="old-sha")))
        delivery.current_pr = lambda _: self.fail("timeout must occur before another REST read")  # type: ignore[method-assign]
        with contextlib.redirect_stderr(io.StringIO()) as error, self.assertRaises(feature_deliver.DeliveryError):
            delivery.wait_for_pr_head(stale, "ci/ci-002", "new-sha")
        self.assertIn("DELIVERY_BLOCKED", error.getvalue())

    def test_wrong_pr_head_or_base_fails_before_propagation_polling(self) -> None:
        for kwargs in ({"head": "ci/wrong"}, {"base": "release"}):
            sleeps: list[int] = []
            delivery = feature_deliver.Delivery(FakeCommands({}), sleep=sleeps.append)
            unexpected = feature_deliver.Delivery.pr_from(json.loads(pr(sha="old-sha", **kwargs)))
            delivery.current_pr = lambda _: self.fail("unexpected PR must not be polled")  # type: ignore[method-assign]
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(feature_deliver.DeliveryError):
                delivery.wait_for_pr_head(unexpected, "ci/ci-002", "new-sha")
            self.assertEqual(sleeps, [])

    def test_check_polling_starts_only_after_pr_head_reaches_delivery_sha(self) -> None:
        delivery = self.delivery()
        stale = feature_deliver.Delivery.pr_from(json.loads(pr(sha="old-sha")))
        snapshots = iter(
            [
                feature_deliver.Delivery.pr_from(json.loads(pr(sha="old-sha"))),
                feature_deliver.Delivery.pr_from(json.loads(pr(sha="new-sha"))),
            ]
        )
        delivery.current_pr = lambda _: next(snapshots)  # type: ignore[method-assign]
        check_calls: list[str] = []
        delivery.check_runs = lambda sha: (  # type: ignore[method-assign]
            check_calls.append(sha)
            or {name: {"status": "completed", "conclusion": "success"} for name in feature_deliver.REQUIRED_CHECKS}
        )
        ready = delivery.wait_for_pr_head(stale, "ci/ci-002", "new-sha")
        self.assertEqual(check_calls, [])
        delivery.current_pr = lambda _: ready  # type: ignore[method-assign]
        delivery.wait_for_checks(ready, "ci/ci-002", "new-sha")
        self.assertEqual(check_calls, ["new-sha"])

    def test_closed_merged_and_mismatched_prs_are_ignored_when_matching_open_pr_exists(self) -> None:
        delivery = self.delivery()
        responses = [
            json.loads(pr(number=4, state="closed")),
            json.loads(pr(number=5, state="merged")),
            json.loads(pr(number=6, state="open", head="ci/other")),
            json.loads(pr(number=7, state="open", base="release")),
            json.loads(pr(number=8, state="open", sha="feature-sha")),
        ]
        delivery.api = lambda endpoint, method="GET", fields=None: responses  # type: ignore[method-assign]
        reused = delivery.find_or_create_pr("ci/ci-002", "feature-sha", False)
        self.assertEqual(reused.number, 8)

    def test_created_pr_with_wrong_head_or_base_is_rejected(self) -> None:
        for kwargs in ({"head": "ci/wrong"}, {"base": "release"}):
            delivery = self.delivery()
            delivery.api = lambda endpoint, method="GET", fields=None, kwargs=kwargs: (  # type: ignore[method-assign]
                [] if method == "GET" else json.loads(pr(**kwargs))
            )
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(feature_deliver.DeliveryError):
                delivery.find_or_create_pr("ci/ci-002", "feature-sha", False)

    def test_auto_merge_uses_the_exact_delivery_sha(self) -> None:
        commands = FakeCommands({})
        delivery = feature_deliver.Delivery(commands)
        delivery.enable_auto_merge(feature_deliver.PullRequest(7, "PR_node", "OPEN", "feature", None, ""), "feature")
        rendered = " ".join(part for call in commands.calls for part in call)
        self.assertIn("expectedHeadOid", rendered)
        self.assertIn("head=feature", rendered)

    def test_migration_detection_and_merge_confirmation(self) -> None:
        commands = FakeCommands(
            {
                ("git", "diff", "--name-only", "base...feature", "--", "backend/alembic/versions"): "backend/alembic/versions/0002_feature.py",
            }
        )
        delivery = feature_deliver.Delivery(commands, sleep=lambda _: None)
        self.assertTrue(delivery.migration_detected("base", "feature"))
        commands.responses[("git", "diff", "--name-only", "base...no-migration", "--", "backend/alembic/versions")] = "docs/readme.md"
        self.assertFalse(delivery.migration_detected("base", "no-migration"))
        merged = feature_deliver.Delivery.pr_from(
            json.loads(pr(state="closed", merge="main-sha", merged=True))
        )
        delivery.current_pr = lambda _: merged  # type: ignore[method-assign]
        self.assertEqual(delivery.wait_for_merge(merged, "ci/ci-002", "feature-sha").merge_sha, "main-sha")

    def test_open_pr_continues_until_closed_merged(self) -> None:
        delivery = self.delivery()
        snapshots = iter(
            [
                feature_deliver.Delivery.pr_from(json.loads(pr(state="open"))),
                feature_deliver.Delivery.pr_from(
                    json.loads(pr(state="closed", merge="squash-sha", merged=True))
                ),
            ]
        )
        delivery.current_pr = lambda _: next(snapshots)  # type: ignore[method-assign]
        result = delivery.wait_for_merge(
            feature_deliver.Delivery.pr_from(json.loads(pr(state="open"))), "ci/ci-002", "feature-sha"
        )
        self.assertEqual(result.merge_sha, "squash-sha")

    def test_closed_unmerged_pr_blocks_delivery(self) -> None:
        delivery = self.delivery()
        closed = feature_deliver.Delivery.pr_from(json.loads(pr(state="closed", merged=False)))
        delivery.current_pr = lambda _: closed  # type: ignore[method-assign]
        with contextlib.redirect_stderr(io.StringIO()) as error, self.assertRaises(
            feature_deliver.DeliveryError
        ):
            delivery.wait_for_merge(closed, "ci/ci-002", "feature-sha")
        self.assertIn("DELIVERY_BLOCKED", error.getvalue())

    def test_auto_merge_between_check_and_merge_polls_returns_resulting_main_sha(self) -> None:
        delivery = self.delivery()
        open_pr = feature_deliver.Delivery.pr_from(json.loads(pr(state="open", sha="feature-sha")))
        merged_pr = feature_deliver.Delivery.pr_from(
            json.loads(pr(state="closed", sha="feature-sha", merge="main-sha", merged=True))
        )
        snapshots = iter([open_pr, merged_pr])
        delivery.current_pr = lambda _: next(snapshots)  # type: ignore[method-assign]
        delivery.check_runs = lambda _: {  # type: ignore[method-assign]
            name: {"status": "completed", "conclusion": "success"}
            for name in feature_deliver.REQUIRED_CHECKS
        }
        delivery.wait_for_checks(open_pr, "ci/ci-002", "feature-sha")
        result = delivery.wait_for_merge(open_pr, "ci/ci-002", "feature-sha")
        self.assertEqual(result.merge_sha, "main-sha")

    def test_closed_merged_rest_response_is_parsed_as_completed_delivery(self) -> None:
        parsed = feature_deliver.Delivery.pr_from(
            json.loads(pr(state="closed", merge="main-sha", merged=True))
        )
        self.assertEqual(parsed.state, "CLOSED")
        self.assertTrue(parsed.merged)
        self.assertEqual(parsed.merge_sha, "main-sha")

    def test_completed_delivery_requires_exact_merged_pr_identity(self) -> None:
        for candidate in (
            associated_pr(sha="other-sha"),
            associated_pr(head="ci/unexpected"),
            associated_pr(base="release"),
            associated_pr(repository="someone-else/florabase"),
        ):
            with self.subTest(candidate=candidate):
                delivery = self.delivery()
                delivery.graphql = lambda _, fields, candidate=candidate: completed_delivery_lookup([candidate])  # type: ignore[method-assign]
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(
                    feature_deliver.DeliveryError
                ):
                    delivery.completed_pr_for_delivery("ci/ci-002", "feature-sha")

        delivery = self.delivery()
        delivery.graphql = lambda *_: completed_delivery_lookup([associated_pr()])  # type: ignore[method-assign]
        delivery.current_pr = lambda _: feature_deliver.Delivery.pr_from(  # type: ignore[method-assign]
            json.loads(pr(state="closed", merged=False))
        )
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(feature_deliver.DeliveryError):
            delivery.completed_pr_for_delivery("ci/ci-002", "feature-sha")

    def test_rerun_after_exact_squash_merge_and_branch_deletion_completes(self) -> None:
        merged = pr(state="closed", merge="main-sha", merged=True)
        checks = json.dumps(
            {
                "check_runs": [
                    {"name": name, "status": "completed", "conclusion": "success"}
                    for name in feature_deliver.REQUIRED_CHECKS
                ]
            }
        )
        commands = FailingCommands(
            {
                ("git", "--version"): "git",
                ("gh", "--version"): "gh",
                ("git", "branch", "--show-current"): "ci/ci-002",
                ("git", "status", "--porcelain"): "",
                ("git", "rev-parse", "--verify", "HEAD^{commit}"): "feature-sha",
                ("git", "remote", "get-url", "origin"): "https://github.com/alessandrorossato/florabase.git",
                ("gh", "auth", "status"): "",
                ("git", "fetch", "origin", "main"): "",
                ("git", "show-ref", "--verify", "--quiet", "refs/remotes/origin/main"): "",
                ("git", "merge-base", "origin/main", "HEAD"): "base-sha",
                ("gh", "api", "repos/alessandrorossato/florabase"): "{}",
                ("git", "ls-remote", "--heads", "origin", "refs/heads/ci/ci-002"): "",
                ("git", "rev-parse", "HEAD"): "feature-sha",
                (
                    "git",
                    "diff",
                    "--name-only",
                    "base-sha...feature-sha",
                    "--",
                    "backend/alembic/versions",
                ): "",
                ("gh", "api", "repos/alessandrorossato/florabase/pulls/7"): [merged, merged],
                (
                    "gh",
                    "api",
                    "repos/alessandrorossato/florabase/commits/feature-sha/check-runs?per_page=100",
                ): checks,
                ("git", "merge-base", "--is-ancestor", "main-sha", "origin/main"): "",
            },
            ("git", "merge-base", "--is-ancestor", "origin/main", "feature-sha"),
        )
        delivery = feature_deliver.Delivery(commands, sleep=lambda _: None)
        delivery.graphql = lambda *_: completed_delivery_lookup([associated_pr()])  # type: ignore[method-assign]
        with contextlib.redirect_stdout(io.StringIO()) as output:
            delivery.execute()
        self.assertIn("DELIVERY_COMPLETE", output.getvalue())
        self.assertIn("Feature SHA: feature-sha", output.getvalue())
        self.assertIn("Main SHA: main-sha", output.getvalue())
        self.assertNotIn(
            ("git", "push", "--set-upstream", "origin", "ci/ci-002"),
            commands.calls,
        )

    def test_completed_delivery_requires_merge_sha_on_origin_main(self) -> None:
        commands = FailingCommands(
            {},
            ("git", "merge-base", "--is-ancestor", "main-sha", "origin/main"),
        )
        delivery = feature_deliver.Delivery(commands, sleep=lambda _: None)
        merged = feature_deliver.Delivery.pr_from(
            json.loads(pr(state="closed", merge="main-sha", merged=True))
        )
        with contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()), self.assertRaises(
            feature_deliver.DeliveryError
        ):
            delivery.complete_delivery(merged, "ci/ci-002", "feature-sha", False)
        self.assertNotIn("DELIVERY_COMPLETE", output.getvalue())

    def test_remote_branch_deletion_is_confirmed(self) -> None:
        commands = FakeCommands(
            {("git", "ls-remote", "--heads", "origin", "refs/heads/ci/ci-002"): ["stale-ref", ""]}
        )
        feature_deliver.Delivery(commands, sleep=lambda _: None).confirm_deleted_branch("ci/ci-002")


if __name__ == "__main__":
    unittest.main(verbosity=2)
