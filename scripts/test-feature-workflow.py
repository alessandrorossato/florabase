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
        (self.seed / "backend/alembic/versions/0001_base.py").write_text(
            'revision: str = "0001"\ndown_revision: str | None = None\n'
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
        ):
            shutil.copy2(ROOT / "scripts" / name, scripts / name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        (self.bin / "make").write_text(
            "#!/usr/bin/env bash\nset -eu\nprintf '%s\\n' \"$*\" >>\"${VERIFY_LOG}\"\n"
            "if [[ \"${VERIFY_FAIL_STAGE:-}\" == \"$1\" ]]; then exit 7; fi\n"
        )
        (self.bin / "docker").write_text(
            "#!/usr/bin/env bash\nset -eu\nprintf '%s\\n' \"$*\" >>\"${VERIFY_LOG}\"\n"
        )
        os.chmod(self.bin / "make", 0o755)
        os.chmod(self.bin / "docker", 0o755)
        self.log = self.root / "verify.log"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def shell(*command: str) -> None:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def verify(self, **environment: str) -> subprocess.CompletedProcess[str]:
        env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "VERIFY_LOG": str(self.log),
            **environment,
        }
        return subprocess.run(
            [str(self.work / "scripts/feature-verify.sh")],
            cwd=self.work,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_success_without_migration_writes_receipt_and_pass_marker(self) -> None:
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("FEATURE_VERIFICATION_PASSED", result.stdout)
        self.assertIn("no Alembic revisions added", result.stdout)
        self.assertTrue((self.work / ".git/info/florabase-feature-verification.json").exists())
        self.assertNotIn("down --volumes", self.log.read_text())

    def test_stage_failure_propagates_failure_marker(self) -> None:
        result = self.verify(VERIFY_FAIL_STAGE="check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stage failed: quality", result.stderr)
        self.assertIn("FEATURE_VERIFICATION_FAILED", result.stderr)

    def test_added_migration_selects_disposable_cycle(self) -> None:
        migration = self.work / "backend/alembic/versions/0002_feature.py"
        migration.write_text('revision: str = "0002"\ndown_revision: str | None = "0001"\n')
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.log.read_text()
        self.assertIn("alembic upgrade '0001'; alembic upgrade head; alembic downgrade '0001'; alembic upgrade head", log)
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
    head: str = "ci/ci-002",
    base: str = "main",
) -> str:
    return json.dumps(
        {
            "number": number,
            "node_id": "PR_node",
            "state": state,
            "head": {"ref": head, "sha": sha},
            "base": {"ref": base},
            "merge_commit_sha": merge,
            "html_url": "https://example.invalid/pr/7",
        }
    )


class DeliveryTests(unittest.TestCase):
    def delivery(self) -> feature_deliver.Delivery:
        return feature_deliver.Delivery(FakeCommands({}), sleep=lambda _: None)

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
                feature_deliver.Delivery(commands).preflight(), ("ci/ci-002", "base-sha", "feature-sha")
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
        pull = feature_deliver.PullRequest(7, "PR_node", "OPEN", "feature-sha", None, "")
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
        delivery.wait_for_checks(pull, "feature-sha")
        self.assertEqual(calls, ["feature-sha", "feature-sha"])

    def test_missing_checks_eventually_time_out_safely(self) -> None:
        delivery = self.delivery()
        delivery.startup_timeout_seconds = 0
        pull = feature_deliver.PullRequest(7, "PR_node", "OPEN", "feature-sha", None, "")
        delivery.current_pr = lambda _: pull  # type: ignore[method-assign]
        delivery.check_runs = lambda _: {}  # type: ignore[method-assign]
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(feature_deliver.DeliveryError):
            delivery.wait_for_checks(pull, "feature-sha")

    def test_failed_cancelled_and_timed_out_checks_block_delivery(self) -> None:
        for conclusion in ("failure", "cancelled", "timed_out"):
            delivery = self.delivery()
            pull = feature_deliver.PullRequest(7, "PR_node", "OPEN", "feature-sha", None, "")
            delivery.current_pr = lambda _: pull  # type: ignore[method-assign]
            delivery.check_runs = lambda _: {  # type: ignore[method-assign]
                name: {"status": "completed", "conclusion": conclusion, "details_url": "url"}
                for name in feature_deliver.REQUIRED_CHECKS
            }
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(feature_deliver.DeliveryError):
                delivery.wait_for_checks(pull, "feature-sha")

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
        delivery.wait_for_checks(ready, "new-sha")
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
        merged = feature_deliver.PullRequest(7, "node", "MERGED", "feature", "main-sha", "")
        delivery.current_pr = lambda _: merged  # type: ignore[method-assign]
        self.assertEqual(delivery.wait_for_merge(merged, "feature").merge_sha, "main-sha")

    def test_remote_branch_deletion_is_confirmed(self) -> None:
        commands = FakeCommands(
            {("git", "ls-remote", "--heads", "origin", "refs/heads/ci/ci-002"): ["stale-ref", ""]}
        )
        feature_deliver.Delivery(commands, sleep=lambda _: None).confirm_deleted_branch("ci/ci-002")


if __name__ == "__main__":
    unittest.main(verbosity=2)
