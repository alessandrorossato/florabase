#!/usr/bin/env python3
"""Deterministic selector, complete Git inventory and receipt validation regressions."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from verification_gate import checks_for, validate_execution
from verification_impact import MAP_PATH, changed_paths, load_map, plan_paths

ROOT = Path(__file__).resolve().parent.parent


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
        self.assertFalse(plan["migration"])
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
            "frontend/src/seed-lots/ReferencePicker.tsx",
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
        self.assertTrue(self.plan("backend/alembic/versions/new.py")["migration"])
        self.assertTrue(self.plan("scripts/verify-migration-cycle.sh")["migration_cycle"])

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
                ("migration_result", "failed"),
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
