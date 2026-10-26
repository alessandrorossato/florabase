#!/usr/bin/env python3
"""Deterministic selector, complete Git inventory and receipt validation regressions."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from verification_gate import checks_for, execute, run_checks, validate_execution
from verification_impact import MAP_PATH, changed_paths, load_map, plan_paths

ROOT = Path(__file__).resolve().parent.parent
CI_SPEC = importlib.util.spec_from_file_location("ci_verification", ROOT / "scripts/ci-verify.py")
assert CI_SPEC and CI_SPEC.loader
CI = importlib.util.module_from_spec(CI_SPEC)
CI_SPEC.loader.exec_module(CI)


class SelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous = Path.cwd()
        os.chdir(ROOT)

    def tearDown(self) -> None:
        os.chdir(self.previous)

    def plan(self, *paths: str) -> dict:
        return plan_paths(list(paths), "base")

    def test_docs_only_never_selects_product_or_docker_stages(self) -> None:
        plan = self.plan("docs/schedule.md", "README.md", "docs/features.json")
        self.assertTrue(plan["docs_only"])
        for key in ("backend", "frontend", "integration", "workflow", "builds"):
            self.assertEqual(plan[key], [])
        self.assertEqual(plan["migration"], "skip")
        self.assertEqual(
            [c["id"] for c in checks_for(plan)],
            ["feature-graph", "whitespace", "staged-whitespace", "untracked-whitespace"],
        )

    def test_schedule_regression_boundaries_are_explicit(self) -> None:
        plan = self.plan("backend/src/florabase/schedule/service.py")
        self.assertEqual(plan["mode"], "affected")
        self.assertIn("events-regression", plan["affected_scopes"])
        self.assertIn("activity", plan["affected_scopes"])
        self.assertIn("security-regression", plan["affected_scopes"])
        self.assertIn("backend/tests/integration/test_schedule.py", plan["integration"])
        self.assertIn("backend/tests/integration/test_event_api.py", plan["integration"])
        self.assertIn("backend/tests/integration/test_authentication.py", plan["integration"])
        self.assertIn("frontend/src/App.test.tsx", plan["frontend"])
        self.assertEqual(plan["workflow"], [])

    def test_taxonomy_avoids_orders_and_labels(self) -> None:
        plan = self.plan("backend/src/florabase/taxonomy/service.py")
        self.assertEqual(plan["mode"], "affected")
        self.assertIn(
            "explore-regression", plan["affected_scopes"]
        )  # two-edge projection relationship
        self.assertNotIn("backend/tests/test_orders.py", plan["backend"])
        self.assertNotIn("frontend/src/orders/OrderScreen.test.tsx", plan["frontend"])
        self.assertNotIn("frontend/src/labels/LabelsScreen.test.tsx", plan["frontend"])

    def test_frontend_only_builds_only_independent_frontend(self) -> None:
        plan = self.plan("frontend/src/taxonomy/TaxonomyScreen.tsx")
        self.assertEqual(plan["backend"], [])
        self.assertEqual(plan["integration"], [])
        self.assertEqual(plan["builds"], ["frontend"])
        self.assertIn("frontend/src/taxonomy/TaxonomyScreen.test.tsx", plan["frontend"])

    def test_backend_only_builds_backend_with_frontend_regression_tests(self) -> None:
        plan = self.plan("backend/src/florabase/taxonomy/schemas.py")
        # Independent build contexts: frontend regressions run but unchanged assets need no build.
        self.assertEqual(plan["builds"], ["backend"])

    def test_full_escalation_matrix(self) -> None:
        for path in [
            "frontend/src/components/TaskDialog.tsx",
            "frontend/src/components/actions/OverflowMenu.tsx",
            "frontend/src/styles/tokens.css",
            "frontend/src/styles/normalization.css",
            "frontend/src/maps/MapWorkspace.tsx",
            "frontend/src/native-ranges/geometry.ts",
            "frontend/src/provenance-map/ProvenanceMap.tsx",
            "frontend/src/seed-lots/ReferencePicker.tsx",
            "frontend/src/seed-lots/PartialDateField.tsx",
            "frontend/src/seed-lots/partial-date.css",
            "backend/src/florabase/db/session.py",
            "backend/src/florabase/auth/security.py",
            "backend/alembic/versions/new.py",
            "scripts/feature-verify.sh",
            "frontend/pnpm-lock.yaml",
            "backend/requirements.lock",
            "unknown.config",
            "backend/src/florabase/newcapability/service.py",
            str(MAP_PATH.relative_to(ROOT)),
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.plan(path)["mode"], "full")
        self.assertEqual(self.plan("backend/alembic/versions/new.py")["migration"], "full-cycle")
        self.assertEqual(self.plan("scripts/verify-migration-cycle.sh")["migration"], "full-cycle")

    def test_migration_decision_matrix_and_execution(self) -> None:
        for paths, forced, decision in (
            (["docs/test.md"], False, "skip"),
            (["frontend/src/taxonomy/TaxonomyScreen.tsx"], False, "skip"),
            (["backend/src/florabase/taxonomy/service.py"], False, "skip"),
            (["backend/alembic/versions/new.py"], False, "full-cycle"),
            (["frontend/pnpm-lock.yaml"], False, "full-cycle"),
            (["docs/test.md"], True, "full-cycle"),
            (["backend/alembic/versions/new.py"], True, "full-cycle"),
        ):
            with self.subTest(paths=paths, forced=forced):
                plan = plan_paths(paths, "base", force_full=forced)
                self.assertEqual(plan["migration"], decision)
                evidence = {
                    "cycle_executed": True,
                    "result": "passed",
                    "verified_revisions": ["0001"] * 4,
                    "cleanup_verified": True,
                }
                output = "MIGRATION_CYCLE_PASSED " + json.dumps(evidence) + "\n"
                with (
                    tempfile.TemporaryDirectory() as temporary,
                    patch("verification_gate.expected_migration_evidence", return_value=evidence),
                    patch(
                        "verification_gate.subprocess.run",
                        return_value=subprocess.CompletedProcess([], 0, output),
                    ) as runner,
                ):
                    result_path = Path(temporary) / "execution.json"
                    execute(plan, result_path)
                    execution = json.loads(result_path.read_text())
                    calls = [
                        call.args[0]
                        for call in runner.call_args_list
                        if call.args[0][0] == "./scripts/verify-migration-cycle.sh"
                    ]
                    self.assertEqual(
                        calls,
                        []
                        if decision == "skip"
                        else [["./scripts/verify-migration-cycle.sh", "base", "--force-cycle"]],
                    )
                    self.assertEqual(execution["migration"]["cycle_executed"], decision != "skip")
                    self.assertEqual(
                        execution["migration"]["result"],
                        "skipped_by_impact" if decision == "skip" else "passed",
                    )

    def test_affected_cycle_instruction_is_unconditional_when_required(self) -> None:
        # Current Alembic rules conservatively escalate FULL. Exercise the supported decision
        # without relaxing those rules or introducing a force-narrow mode.
        plan = {**self.plan("docs/test.md"), "migration": "affected-cycle"}
        cycle = next(c for c in checks_for(plan) if c["id"] == "migration-cycle")
        self.assertEqual(
            cycle["command"], ["./scripts/verify-migration-cycle.sh", "base", "--force-cycle"]
        )

    def test_full_cannot_downgrade_its_migration_decision(self) -> None:
        plan = self.plan("frontend/pnpm-lock.yaml")
        for decision in ("skip", "affected-cycle", True, None):
            with (
                self.subTest(decision=decision),
                self.assertRaisesRegex(ValueError, "invalid migration"),
            ):
                checks_for({**plan, "migration": decision})

    def test_full_executor_rejects_successful_exit_without_cycle_evidence(self) -> None:
        plan = self.plan("frontend/pnpm-lock.yaml")
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch(
                "verification_gate.subprocess.run",
                return_value=subprocess.CompletedProcess(
                    [], 0, "migration verification: no Alembic revisions added\n"
                ),
            ),
        ):
            result_path = Path(temporary) / "execution.json"
            with self.assertRaisesRegex(ValueError, "did not report"):
                execute(plan, result_path)
            self.assertFalse(result_path.exists())

    def test_documentation_does_not_hide_unknown_configuration(self) -> None:
        plan = self.plan("docs/architecture.md", "runtime.yaml")
        self.assertEqual(plan["mode"], "full")
        self.assertFalse(plan["docs_only"])

    def test_union_and_order_are_deterministic(self) -> None:
        paths = ["frontend/src/taxonomy/api.ts", "frontend/src/orders/api.ts"]
        self.assertEqual(self.plan(*paths), self.plan(*reversed(paths), paths[0]))
        self.assertIn("taxonomy", self.plan(*paths)["changed_scopes"])
        self.assertIn("orders", self.plan(*paths)["changed_scopes"])

    def test_generated_contract_alone_escalates(self) -> None:
        self.assertEqual(
            self.plan("backend/openapi.json", "frontend/src/api/schema.d.ts")["mode"], "full"
        )
        self.assertEqual(
            self.plan("backend/src/florabase/schedule/api.py", "backend/openapi.json")["mode"],
            "affected",
        )

    def test_new_untracked_frontend_test_is_explicitly_selected(self) -> None:
        path = "frontend/src/taxonomy/NewBoundary.test.tsx"
        # Virtual file isolates the selector test from the actual feature source.
        with patch.object(Path, "is_file", return_value=True):
            plan = self.plan(path)
        self.assertEqual(plan["mode"], "affected")
        self.assertIn(path, plan["frontend"])

    def test_missing_selected_test_fails_instead_of_skipping(self) -> None:
        with patch.object(Path, "is_file", return_value=False):
            with self.assertRaisesRegex(ValueError, "missing mapped suites"):
                self.plan("frontend/src/taxonomy/TaxonomyScreen.tsx")

    def test_execution_validation_rejects_missing_failed_reordered_or_extra_checks(self) -> None:
        plan = self.plan("docs/test.md")
        completed = [{**c, "result": "passed"} for c in checks_for(plan)]
        validate_execution(plan, completed)
        for value in (
            completed[:-1],
            list(reversed(completed)),
            completed + [completed[0]],
            [{**completed[0], "result": "failed"}, *completed[1:]],
        ):
            with self.assertRaises(ValueError):
                validate_execution(plan, value)

    def test_map_covers_every_current_production_module_or_escalates(self) -> None:
        data = load_map()
        for path in sorted((ROOT / "backend/src/florabase").rglob("*.py")):
            relative = str(path.relative_to(ROOT))
            self.assertTrue(
                any(relative.startswith(p) for p in data["full_prefixes"])
                or any(
                    relative.startswith(r.get("prefix", "\0")) or r.get("path") == relative
                    for r in data["rules"]
                ),
                relative,
            )

    def test_classified_frontend_test_inventory_cannot_silently_drift(self) -> None:
        data = load_map()
        for rule in data["rules"]:
            if rule["layer"] != "frontend" or "prefix" not in rule:
                continue
            for path in Path(rule["prefix"]).rglob("*"):
                if path.is_file() and ".test." in path.name:
                    self.assertIn(str(path), data["scopes"][rule["scope"]]["frontend"])

    def test_remote_policy_matrix(self) -> None:
        for path in (
            "docs/example.md",
            "frontend/src/taxonomy/taxonomy.css",
            "frontend/src/taxonomy/TaxonomyScreen.tsx",
            "frontend/src/components/Controls.tsx",
            "frontend/src/styles/tokens.css",
            "backend/src/florabase/taxonomy/service.py",
            "backend/openapi.json",
            "frontend/package.json",
            "backend/alembic/versions/new.py",
            "backend/src/florabase/auth/service.py",
            ".github/workflows/ci.yml",
            "unknown.conf",
        ):
            with self.subTest(path=path):
                plan = self.plan(path)
                jobs = {
                    job: CI.ci_checks_for(plan, job) for job in ("quality", "integration", "build")
                }
                if plan["docs_only"]:
                    self.assertTrue(all(checks == checks_for(plan) for checks in jobs.values()))
                else:
                    self.assertIn({"id": "quality", "command": ["make", "check"]}, jobs["quality"])
                    self.assertEqual(
                        jobs["integration"][0]["command"], ["make", "test-integration"]
                    )
                    self.assertEqual(
                        jobs["build"][0]["command"],
                        ["make", "verify-build", "SERVICES=backend frontend"],
                    )
                    helpers = [c for c in jobs["quality"] if c["id"].startswith("test-")]
                    self.assertEqual(bool(helpers), plan["mode"] == "full")
        with self.assertRaises(ValueError):
            CI.ci_checks_for(self.plan("docs/example.md"), "unknown")

    def test_failure_keeps_output_exit_status_and_prior_stages(self) -> None:
        output = io.StringIO()
        with (
            redirect_stdout(output),
            redirect_stderr(output),
            self.assertRaises(SystemExit) as error,
        ):
            run_checks(
                self.plan("docs/example.md"),
                [
                    {"id": "first", "command": ["true"]},
                    {"id": "failed-case", "command": ["bash", "-c", "exit 7"]},
                    {"id": "never", "command": ["false"]},
                ],
            )
        self.assertEqual(error.exception.code, 7)
        self.assertIn("exit=7", output.getvalue())
        self.assertIn("prior stages passed=first", output.getvalue())
        self.assertIn("no new receipt issued", output.getvalue())
        self.assertNotIn("stage passed: never", output.getvalue())

    def test_workflow_preserves_required_jobs_and_pipe_failures(self) -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        self.assertNotIn("continue-on-error", workflow)
        self.assertNotIn("needs:", workflow)
        for job in ("quality", "integration", "build"):
            self.assertIn(f"    name: {job}\n", workflow)
            self.assertIn(f"python3 scripts/ci-verify.py {job} 2>&1 | tee", workflow)
        self.assertEqual(workflow.count("set -o pipefail"), 3)
        self.assertEqual(workflow.count("fetch-depth: 2"), 3)
        self.assertEqual(workflow.count("if: always()"), 3)
        result = subprocess.run(["bash", "-o", "pipefail", "-c", "exit 7 | cat"])
        self.assertEqual(result.returncode, 7)


class RemoteHistoryTests(unittest.TestCase):
    def test_real_merge_event_docs_smoke_and_fail_closed_revisions(self) -> None:
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def git(*args: str) -> str:
                return subprocess.run(
                    ["git", "-C", str(root), *args], check=True, text=True, capture_output=True
                ).stdout.strip()

            (root / "scripts").mkdir()
            (root / "docs").mkdir()
            for name in (
                "ci-verify.py",
                "verification_gate.py",
                "verification_impact.py",
                "verification-impact.json",
                "feature-tree-fingerprint.py",
                "disposable_workflow.py",
                "workflow_resources.py",
                "check-features.py",
            ):
                shutil.copy(ROOT / "scripts" / name, root / "scripts" / name)
            shutil.copy(ROOT / "docs/features.json", root / "docs/features.json")
            (root / ".gitignore").write_text("__pycache__/\n")
            (root / "README.md").write_text("base\n")
            git("init", "--initial-branch=main")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.invalid")
            git("add", ".")
            git("commit", "-m", "base")
            base = git("rev-parse", "HEAD")
            git("checkout", "-b", "docs/example")
            (root / "README.md").write_text("feature\n")
            git("commit", "-am", "docs")
            head = git("rev-parse", "HEAD")
            git("checkout", "main")
            git("merge", "--no-ff", "docs/example", "-m", "synthetic PR merge")
            merge = git("rev-parse", "HEAD")
            event_path = root / ".git/event.json"
            event = {"pull_request": {"base": {"sha": base}, "head": {"sha": head}}}
            event_path.write_text(json.dumps(event))
            environment = {
                "GITHUB_EVENT_NAME": "pull_request",
                "GITHUB_EVENT_PATH": str(event_path),
                "GITHUB_SHA": merge,
            }
            os.chdir(root)
            try:
                shallow = root / ".git/shallow-fixture"
                subprocess.run(
                    ["git", "clone", "--depth", "2", root.as_uri(), str(shallow)],
                    check=True,
                    capture_output=True,
                )
                os.chdir(shallow)
                with patch.dict(os.environ, environment), redirect_stdout(io.StringIO()):
                    self.assertTrue(CI.ci_plan()["docs_only"])
                os.chdir(root)
                with patch.dict(os.environ, environment), redirect_stdout(io.StringIO()):
                    self.assertTrue(CI.ci_plan()["docs_only"])
                    # A moving remote ref cannot replace the event's immutable base.
                    git("update-ref", "refs/remotes/origin/main", merge)
                    self.assertEqual(CI.ci_plan()["base"], base)
                for job in ("quality", "integration", "build"):
                    started = time.monotonic()
                    result = subprocess.run(
                        ["python3", "scripts/ci-verify.py", job],
                        env={**os.environ, **environment},
                        text=True,
                        capture_output=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn(f"CI_JOB_PASSED: {job}", result.stdout)
                    self.assertNotIn("Command: make", result.stdout)
                    print(f"CI004_DOCS_SMOKE: {job} {time.monotonic() - started:.3f}s")
                self.assertFalse((root / ".git/info/florabase-feature-verification.json").exists())
                for changes in (
                    {"GITHUB_EVENT_NAME": "push"},
                    {"GITHUB_EVENT_NAME": "unknown"},
                    {"GITHUB_EVENT_PATH": "/missing"},
                ):
                    with (
                        patch.dict(os.environ, {**environment, **changes}),
                        redirect_stdout(io.StringIO()),
                    ):
                        self.assertEqual(CI.ci_plan()["mode"], "full")
                with (
                    patch.dict(os.environ, {**environment, "GITHUB_EVENT_NAME": "push"}),
                    patch.object(CI, "make_plan", side_effect=AssertionError("unneeded inventory")),
                    redirect_stdout(io.StringIO()),
                ):
                    full = CI.ci_plan()
                    self.assertEqual(full["mode"], "full")
                    self.assertEqual(
                        CI.ci_checks_for(full, "integration")[0]["command"],
                        ["make", "test-integration"],
                    )
                bad_map = root / ".git/bad-map.json"
                bad_map.write_text('{"version": 0}')
                for policy in (bad_map, root / ".git/missing-map.json"):
                    with (
                        patch.dict(os.environ, {**environment, "GITHUB_EVENT_NAME": "push"}),
                        patch("verification_impact.MAP_PATH", policy),
                        redirect_stdout(io.StringIO()),
                        self.assertRaises((ValueError, OSError)),
                    ):
                        CI.ci_plan()
                for sha in (head, "", "invalid"):
                    with patch.dict(os.environ, {**environment, "GITHUB_SHA": sha}):
                        with self.assertRaisesRegex(ValueError, "exact platform GITHUB_SHA"):
                            CI.ci_plan()
                result = subprocess.run(
                    ["python3", "scripts/ci-verify.py", "quality"],
                    env={**os.environ, **environment, "GITHUB_SHA": head},
                    text=True,
                    capture_output=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("Command:", result.stdout)
                self.assertNotIn("CI_JOB_PASSED", result.stdout)
                for bad in (
                    {},
                    {"pull_request": None},
                    {"pull_request": {"base": {"sha": head}, "head": {"sha": head}}},
                ):
                    event_path.write_text(json.dumps(bad))
                    with patch.dict(os.environ, environment), redirect_stdout(io.StringIO()):
                        self.assertEqual(CI.ci_plan()["mode"], "full")
                event_path.write_text(json.dumps(event))
                # Merge resolutions and unexpected untracked/index/dirty files participate.
                (root / "surprise.config").write_text("unsafe\n")
                with patch.dict(os.environ, environment), redirect_stdout(io.StringIO()):
                    self.assertEqual(CI.ci_plan()["mode"], "full")
                git("add", "surprise.config")
                (root / "surprise.config").unlink()
                with patch.dict(os.environ, environment), redirect_stdout(io.StringIO()):
                    self.assertEqual(CI.ci_plan()["mode"], "full")
                fake_bin = root / ".git/fake-bin"
                fake_bin.mkdir()
                fake_make = fake_bin / "make"
                fake_make.write_text("#!/bin/sh\necho original-command-failure >&2\nexit 7\n")
                fake_make.chmod(0o755)
                result = subprocess.run(
                    ["python3", "scripts/ci-verify.py", "quality"],
                    env={**os.environ, **environment, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
                self.assertIn("original-command-failure", result.stderr)
                self.assertIn("exit=7", result.stderr)
                self.assertNotIn("CI_JOB_PASSED", result.stdout)
                self.assertFalse((root / ".git/info/florabase-feature-verification.json").exists())
            finally:
                os.chdir(previous)


class InventoryTests(unittest.TestCase):
    def test_complete_tree_includes_commit_index_worktree_untracked_rename_delete_and_modes(
        self,
    ) -> None:
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def git(*args: str) -> str:
                return subprocess.run(
                    ["git", "-C", str(root), *args], check=True, text=True, capture_output=True
                ).stdout.strip()

            git("init", "--initial-branch=main")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.invalid")
            for path in ["committed", "staged", "dirty", "old-name", "deleted", "executable"]:
                (root / path).write_text("base")
            git("add", ".")
            git("commit", "-m", "base")
            base = git("rev-parse", "HEAD")
            (root / "committed").write_text("committed change")
            git("commit", "-am", "feature")
            (root / "staged").write_text("index")
            git("add", "staged")
            (root / "dirty").write_text("worktree")
            (root / "untracked production.py").write_text("new")
            git("mv", "old-name", "new-name")
            (root / "deleted").unlink()
            (root / "executable").chmod(0o755)
            os.chdir(root)
            try:
                self.assertEqual(
                    changed_paths(base),
                    sorted(
                        [
                            "committed",
                            "staged",
                            "dirty",
                            "old-name",
                            "new-name",
                            "deleted",
                            "executable",
                            "untracked production.py",
                        ]
                    ),
                )
                # Staged production changes cannot be hidden by an unstaged base-content revert.
                (root / "staged").write_text("base")
                self.assertIn("staged", changed_paths(base))
                (root / "committed").write_text("base")
                self.assertIn("committed", changed_paths(base))
                (root / "symbolic").symlink_to("committed")
                self.assertIn("symbolic", changed_paths(base))
            finally:
                os.chdir(previous)

    def test_real_receipt_rejects_policy_or_completion_tampering_and_stale_base(self) -> None:
        # Existing orchestration fixtures exercise write/read against primary and linked Git trees.
        spec = __import__("importlib.util", fromlist=["spec_from_file_location"])
        module_spec = spec.spec_from_file_location(
            "feature_tests", ROOT / "scripts/test-feature-workflow.py"
        )
        assert module_spec and module_spec.loader
        module = spec.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        fixture = module.VerifyHelperTests()
        fixture.setUp()
        try:
            result = fixture.verify()
            self.assertEqual(result.returncode, 0, result.stderr)
            receipt_path = fixture.work / ".git/info/florabase-feature-verification.json"
            original = json.loads(receipt_path.read_text())
            base = fixture.shell_output("git", "-C", str(fixture.work), "rev-parse", "origin/main")
            command = [
                "python3",
                "scripts/feature-tree-fingerprint.py",
                "verify",
                "--worktree",
                "--branch",
                "ci/ci-002",
                "--base",
                base,
            ]
            for key, value in [
                ("version", 99),
                ("completed", []),
                ("base", "other"),
                ("migration", {"result": "failed"}),
                ("build_result", "failed"),
            ]:
                receipt_path.write_text(json.dumps({**original, key: value}))
                checked = subprocess.run(command, cwd=fixture.work, text=True, capture_output=True)
                self.assertNotEqual(checked.returncode, 0, checked.stdout)
            receipt = dict(original)
            receipt["verification"] = {**receipt["verification"], "impact_map_digest": "old"}
            receipt_path.write_text(json.dumps(receipt))
            self.assertNotEqual(
                subprocess.run(command, cwd=fixture.work, capture_output=True).returncode, 0
            )
            receipt_path.write_text(json.dumps(original))
            self.assertEqual(
                subprocess.run(command, cwd=fixture.work, capture_output=True).returncode, 0
            )
        finally:
            fixture.tearDown()


if __name__ == "__main__":
    unittest.main()
