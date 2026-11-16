#!/usr/bin/env python3
"""Deterministic selector, complete Git inventory and receipt validation regressions."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from verification_gate import checks_for, execute, run_checks, validate_execution
from verification_impact import (
    MAP_PATH,
    WORKFLOW,
    changed_paths,
    discover_repo_tests,
    load_map,
    make_plan,
    plan_paths,
    plan_tier,
)

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
        plan = self.plan(
            "docs/schedule.md",
            "README.md",
            "docs/features.json",
            "docs/review/new/evidence.PNG",
            "docs/design/new/prototype.css",
        )
        self.assertTrue(plan["docs_only"])
        for key in ("backend", "frontend", "integration", "workflow", "builds"):
            self.assertEqual(plan[key], [])
        self.assertEqual(plan["migration"], "skip")
        self.assertEqual(
            [c["id"] for c in checks_for(plan)],
            [
                "feature-graph",
                "doc-links",
                "test-doc-links",
                "whitespace",
                "staged-whitespace",
                "untracked-whitespace",
            ],
        )

    def test_executable_and_unclassified_documentation_paths_escalate(self) -> None:
        for path in (
            "docs/review/taxonomy-visual-001/compose.yaml",
            "docs/review/wcvp-version-001/compose.yaml",
            "docs/review/wcvp-version-001/live-review.py",
            "docs/review/maps-origins-001/capture.cjs",
            "docs/design/ui-system-v1/prototype.js",
            "docs/design/ui-system-v1/prototype.html",
            "docs/security/beta-distribution-001/postgresql-derived-prototype/Dockerfile.prototype",
            "docs/review/new/compose.smoke.yml",
            "docs/review/new/check.PY",
            "docs/new/run.sh",
            "docs/new/unknown",
        ):
            with self.subTest(path=path):
                plan = self.plan("docs/review/new/README.md", path)
                self.assertEqual(plan["mode"], "full")
                self.assertFalse(plan["docs_only"])
                self.assertEqual(
                    plan["escalation_reasons"],
                    [f"executable or unclassified documentation path: {path}"],
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

    def test_product_tier_matrix_and_no_product_check_loss(self) -> None:
        product_paths = [
            "frontend/src/components/TaskDialog.tsx",
            "frontend/src/components/actions/OverflowMenu.tsx",
            "frontend/src/auth/AuthContext.tsx",
            "frontend/src/App.tsx",
            "frontend/src/main.tsx",
            "frontend/src/pwa/register.ts",
            "frontend/src/styles.css",
            "frontend/src/styles/tokens.css",
            "frontend/src/styles/normalization.css",
            "frontend/src/maps/MapWorkspace.tsx",
            "frontend/src/appearance/AppearanceProvider.tsx",
            "frontend/src/native-ranges/geometry.ts",
            "frontend/src/provenance-map/ProvenanceMap.tsx",
            "frontend/src/occurrence-map/OccurrenceMap.tsx",
            "frontend/src/species-distribution/DistributionMap.tsx",
            "frontend/src/test/setup.ts",
            "frontend/src/seed-lots/ReferencePicker.tsx",
            "frontend/src/seed-lots/PartialDateField.tsx",
            "frontend/src/seed-lots/partial-date.css",
            "backend/src/florabase/application_settings/service.py",
            "backend/src/florabase/auth/security.py",
            "backend/src/florabase/core/config.py",
            "backend/src/florabase/cuttings/service.py",
            "backend/src/florabase/db/session.py",
            "backend/src/florabase/api/router.py",
            "backend/src/florabase/main.py",
        ]
        full_reference = checks_for(self.plan("scripts/feature-verify.sh"))
        full_product_checks = [
            c
            for c in full_reference
            if c["id"] != "migration-cycle" and c["id"] not in set(WORKFLOW)
        ]
        for path in product_paths:
            with self.subTest(path=path):
                plan = self.plan(path)
                self.assertEqual(plan_tier(plan), "product")
                self.assertEqual(plan["tier"], "product")
                self.assertEqual(plan["mode"], "product")
                self.assertFalse(plan["docs_only"])
                self.assertEqual(plan["backend"], ["ALL"])
                self.assertEqual(plan["integration"], ["ALL"])
                self.assertEqual(plan["frontend"], ["ALL"])
                self.assertEqual(plan["builds"], ["backend", "frontend"])
                self.assertEqual(plan["workflow"], [])
                self.assertEqual(plan["migration"], "skip")
                self.assertEqual(plan["escalation_reasons"], [])
                self.assertEqual(plan["product_reasons"], [f"shared product path: {path}"])
                self.assertEqual(checks_for(plan), full_product_checks)

    def test_full_escalation_matrix(self) -> None:
        for path in [
            "backend/alembic/versions/new.py",
            "backend/alembic.ini",
            "scripts/feature-verify.sh",
            "Makefile",
            "compose.yaml",
            "compose.dev.yaml",
            ".github/workflows/ci.yml",
            "backend/Dockerfile",
            "frontend/Dockerfile",
            "frontend/pnpm-lock.yaml",
            "backend/requirements.lock",
            "backend/pyproject.toml",
            "backend/src/florabase/__init__.py",
            "deploy/custom.conf",
            "postgres/init.sql",
            "release/manifest.json",
            "AGENTS.md",
            "unknown.config",
            "backend/src/florabase/newcapability/service.py",
            "frontend/src/newcapability/Screen.tsx",
            str(MAP_PATH.relative_to(ROOT)),
        ]:
            with self.subTest(path=path):
                plan = self.plan(path)
                self.assertEqual(plan_tier(plan), "full")
                self.assertEqual(plan["mode"], "full")
                self.assertEqual(plan["workflow"], WORKFLOW)
                self.assertEqual(plan["migration"], "full-cycle")
        self.assertEqual(self.plan("backend/alembic/versions/new.py")["migration"], "full-cycle")
        self.assertEqual(self.plan("scripts/verify-migration-cycle.sh")["migration"], "full-cycle")

    def test_tier_precedence_and_fail_closed_validation(self) -> None:
        mixed_product = self.plan(
            "docs/architecture.md",
            "frontend/src/taxonomy/TaxonomyScreen.tsx",
            "frontend/src/components/TaskDialog.tsx",
        )
        self.assertEqual(plan_tier(mixed_product), "product")
        self.assertEqual(mixed_product["workflow"], [])

        product_generated = self.plan("backend/src/florabase/auth/api.py", "backend/openapi.json")
        self.assertEqual(plan_tier(product_generated), "product")

        for infra_path in (
            "scripts/feature-verify.sh",
            "compose.yaml",
            "frontend/pnpm-lock.yaml",
            "unknown/new_file.txt",
        ):
            with self.subTest(infra_path=infra_path):
                escalated = self.plan("frontend/src/components/TaskDialog.tsx", infra_path)
                self.assertEqual(plan_tier(escalated), "full")
                self.assertEqual(escalated["workflow"], WORKFLOW)
                self.assertEqual(escalated["migration"], "full-cycle")

        forced = plan_paths(["frontend/src/components/TaskDialog.tsx"], "base", force_full=True)
        self.assertEqual(plan_tier(forced), "full")

        product_plan = self.plan("frontend/src/components/TaskDialog.tsx")
        for invalid in (
            {**product_plan, "backend": []},
            {**product_plan, "integration": ["backend/tests/integration/test_taxonomy.py"]},
            {**product_plan, "frontend": []},
            {**product_plan, "builds": ["frontend"]},
            {**product_plan, "workflow": ["test-verification-impact"]},
            {**product_plan, "docs_only": True},
            {**product_plan, "tier": "affected"},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                checks_for(invalid)

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
                any(
                    relative.startswith(p)
                    for p in (*data["full_prefixes"], *data["product_prefixes"])
                )
                or any(
                    relative.startswith(r.get("prefix", "\0")) or r.get("path") == relative
                    for r in data["rules"]
                ),
                relative,
            )
        self.assertIn("backend/src/florabase/__init__.py", data["full_prefixes"])
        self.assertNotIn("backend/src/florabase/__init__.py", data["product_prefixes"])

    def test_test_ownership_inventory_cannot_silently_drift(self) -> None:
        data = load_map()
        discovered = discover_repo_tests()
        self.assertTrue(discovered["backend"])
        self.assertTrue(discovered["integration"])
        self.assertTrue(discovered["frontend"])
        # Every declared frontend_dirs must exist, and every explicit mapped file must exist.
        for entry in (*data["full_tests"], *data["product_tests"]):
            self.assertTrue((ROOT / entry).is_file(), entry)
        for name, scope in data["scopes"].items():
            if "suite_scope" in scope:
                continue
            for directory in scope["frontend_dirs"]:
                self.assertTrue((ROOT / directory).is_dir(), f"{name}: {directory}")
            for layer in ("backend", "integration", "frontend"):
                for entry in scope[layer]:
                    self.assertTrue((ROOT / entry).is_file(), f"{name}.{layer}: {entry}")
        # Every scope with owned frontend_dirs selects every test file inside them.
        for name, scope in data["scopes"].items():
            if "suite_scope" in scope or not scope["frontend_dirs"]:
                continue
            rule = next(
                (
                    r
                    for r in data["rules"]
                    if r["scope"] == name and r["layer"] == "frontend" and "prefix" in r
                ),
                None,
            )
            if rule is None:
                continue
            if any(rule["prefix"].startswith(p) for p in data["product_prefixes"]):
                continue
            plan = self.plan(rule["prefix"] + "probe.ts")
            if plan["mode"] == "affected":
                for directory in scope["frontend_dirs"]:
                    for test_file in (ROOT / directory).rglob("*"):
                        if test_file.is_file() and (
                            ".test." in test_file.name or ".spec." in test_file.name
                        ):
                            self.assertIn(str(test_file.relative_to(ROOT)), plan["frontend"])

    def test_remote_policy_matrix(self) -> None:
        for path in (
            "docs/example.md",
            "docs/review/taxonomy-visual-001/compose.yaml",
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
                    helpers = [
                        c
                        for c in jobs["quality"]
                        if c["id"].startswith("test-") and c["id"] != "test-doc-links"
                    ]
                    self.assertEqual(bool(helpers), plan["mode"] == "full")
        with self.assertRaises(ValueError):
            CI.ci_checks_for(self.plan("docs/example.md"), "unknown")

    def test_cheap_source_checks_precede_every_docker_stage_without_losing_coverage(self) -> None:
        # Before VERIFICATION-FAST-001 whitespace ran last; a trailing Markdown blank line failed
        # a FULL only after every Docker suite. The stage *set* must be exactly preserved.
        full = self.plan("unknown.conf")
        order = [c["id"] for c in checks_for(full)]
        self.assertEqual(
            order,
            [
                "feature-graph",
                "doc-links",
                "test-doc-links",
                "whitespace",
                "staged-whitespace",
                "untracked-whitespace",
                "test-workflow-helpers",
                "test-feature-workflow",
                "test-agent-workflow",
                "test-preview-workflow",
                "test-environment-workflow",
                "test-uat-preview",
                "test-verification-impact",
                "test-workflow-resources",
                "workflow-check",
                "quality",
                "production-builds",
                "migration-cycle",
                "integration",
            ],
        )
        for paths in (
            ("backend/src/florabase/schedule/service.py",),
            ("frontend/src/taxonomy/TaxonomyScreen.tsx",),
            ("backend/alembic/versions/new.py",),
        ):
            with self.subTest(paths=paths):
                ids = [c["id"] for c in checks_for(self.plan(*paths))]
                self.assertEqual(
                    ids[:6],
                    [
                        "feature-graph",
                        "doc-links",
                        "test-doc-links",
                        "whitespace",
                        "staged-whitespace",
                        "untracked-whitespace",
                    ],
                )
                self.assertEqual(len(ids), len(set(ids)))
        affected = checks_for(self.plan("backend/src/florabase/schedule/service.py"))
        ids = [c["id"] for c in affected]
        for cheap, costly in (("api-check", "backend"), ("backend", "production-builds")):
            self.assertLess(ids.index(cheap), ids.index(costly))
        self.assertEqual(ids[-1], "integration")

    def test_make_check_runs_static_and_api_drift_before_unit_suites(self) -> None:
        line = next(
            line
            for line in (ROOT / "Makefile").read_text().splitlines()
            if line.startswith("check:")
        )
        self.assertEqual(
            line.split("##")[0].split(":", 1)[1].split(),
            ["format-check", "lint", "typecheck", "api-check", "test"],
        )

    def test_stages_get_noninteractive_stdin_even_from_a_terminal(self) -> None:
        import pty

        probe = "import sys\nsys.exit(3 if sys.stdin.isatty() or sys.stdin.read(1) else 0)\n"
        program = (
            f"import sys; sys.path.insert(0, {str(ROOT / 'scripts')!r})\n"
            "from verification_gate import run_checks\n"
            "plan = {'mode': 'full', 'affected_scopes': [], 'base': 'x'}\n"
            f"run_checks(plan, [{{'id': 'probe', 'command': [sys.executable, '-c', {probe!r}]}}])\n"
            "print('PROBE_PASSED')\n"
        )
        parent, child = pty.openpty()
        self.addCleanup(os.close, parent)
        self.addCleanup(os.close, child)
        for stdin in (child, subprocess.DEVNULL):
            with self.subTest(terminal=stdin == child):
                result = subprocess.run(
                    [sys.executable, "-c", program], stdin=stdin, text=True, capture_output=True
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("PROBE_PASSED", result.stdout)

    def test_failure_summary_and_journal_name_failed_and_unrun_stages(self) -> None:
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "last-run.json"
            with (
                redirect_stdout(output),
                redirect_stderr(output),
                self.assertRaises(SystemExit),
            ):
                run_checks(
                    self.plan("docs/example.md"),
                    [
                        {"id": "first", "command": ["true"]},
                        {"id": "failed-case", "command": ["false"]},
                        {"id": "expensive", "command": ["true"]},
                    ],
                    journal,
                )
            record = json.loads(journal.read_text())
            self.assertEqual(
                [(s["id"], s["status"]) for s in record["stages"]],
                [("first", "passed"), ("failed-case", "failed")],
            )
            self.assertIn("never verification evidence", record["purpose"])
            self.assertEqual(list(Path(directory).iterdir()), [journal])
        text = output.getvalue()
        self.assertIn("Stage summary", text)
        self.assertRegex(text, r"expensive\s+not run")
        self.assertRegex(text, r"failed-case\s+failed")

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
        self.assertEqual(workflow.count("if: always()"), 4)
        self.assertIn("BASE_SHA: ${{ github.event.before }}", workflow)
        self.assertIn('git merge-base --is-ancestor "$BASE_SHA" "$GITHUB_SHA"', workflow)
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
            for name in ("check-doc-links.py", "test-doc-links.py"):
                (root / "scripts" / name).write_text("# simulated link check\n")
            shutil.copy(ROOT / "docs/features.json", root / "docs/features.json")
            (root / "docs/release").mkdir()
            shutil.copy(ROOT / "docs/release/scope-v1.json", root / "docs/release/scope-v1.json")
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
            event = {
                "pull_request": {
                    "base": {"sha": base},
                    "head": {"sha": head, "ref": "docs/example"},
                }
            }
            event_path.write_text(json.dumps(event))
            environment = {
                "GITHUB_EVENT_NAME": "pull_request",
                "GITHUB_HEAD_REF": "docs/example",
                "GITHUB_EVENT_PATH": str(event_path),
                "GITHUB_SHA": merge,
            }
            outer = patch.dict(os.environ, {"GITHUB_HEAD_REF": "ci/wf-04-batch-01"})
            outer.start()
            self.addCleanup(outer.stop)
            os.chdir(root)
            try:
                with (
                    patch.dict(os.environ, {**environment, "GITHUB_HEAD_REF": "ci/wf-04-batch-01"}),
                    self.assertRaisesRegex(ValueError, "cannot prove exact batch PR parents"),
                ):
                    CI.ci_plan()
                mismatched = subprocess.run(
                    ["python3", "scripts/ci-verify.py", "quality"],
                    env={**os.environ, **environment, "GITHUB_HEAD_REF": "ci/wf-04-batch-01"},
                    text=True,
                    capture_output=True,
                )
                self.assertNotEqual(mismatched.returncode, 0)
                self.assertIn("cannot prove exact batch PR parents", mismatched.stderr)
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
                (root / "docs/surprise.sh").write_text("exit 0\n")
                with patch.dict(os.environ, environment), redirect_stdout(io.StringIO()):
                    self.assertEqual(CI.ci_plan()["mode"], "full")
                git("add", "docs/surprise.sh")
                (root / "docs/surprise.sh").unlink()
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
    def test_documentation_impact_uses_both_paths_and_all_file_modes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            previous = Path.cwd()
            os.chdir(root)
            try:
                self.check_documentation_history()
            finally:
                os.chdir(previous)

    def check_documentation_history(self) -> None:
        def git(*args: str, stdin: str | None = None) -> str:
            return subprocess.run(
                ["git", *args], check=True, text=True, capture_output=True, input=stdin
            ).stdout.strip()

        git("init", "--initial-branch=main")
        git("config", "user.name", "Test")
        git("config", "user.email", "test@localhost")
        git("config", "core.filemode", "true")
        adapter = Path("docs/review/adapter.py")
        note = Path("docs/review/note.md")
        adapter.parent.mkdir(parents=True)
        adapter.write_text("print('review')\n")
        note.write_text("review notes\n")
        git("add", "docs")
        git("commit", "-m", "base")
        base = git("rev-parse", "HEAD")

        def expect(*paths: Path, docs_only: bool = False) -> None:
            plan = make_plan(base)
            self.assertEqual(plan["changed_paths"], sorted(map(str, paths)))
            self.assertEqual(plan["docs_only"], docs_only)
            self.assertEqual(plan["mode"], "affected" if docs_only else "full")

        adapter.write_text("print('changed')\n")
        expect(adapter)
        adapter.unlink()
        expect(adapter)
        git("restore", str(adapter))

        overlay = adapter.with_name("compose.smoke.yaml")
        overlay.write_text("services: {}\n")
        expect(overlay)
        overlay.unlink()

        archived_adapter = adapter.with_suffix(".md")
        git("mv", str(adapter), str(archived_adapter))
        expect(adapter, archived_adapter)
        git("mv", str(archived_adapter), str(adapter))

        executable_note = note.with_suffix(".py")
        git("mv", str(note), str(executable_note))
        git("commit", "-m", "move into executable path")
        expect(note, executable_note)
        git("reset", "--hard", base)

        note.chmod(0o755)
        expect(note)
        git("add", str(note))
        note.chmod(0o644)
        expect(note)  # The worktree revert masks the index mode.
        git("commit", "-m", "set executable bit")
        git("add", str(note))
        expect(note)  # Only HEAD retains the executable mode.
        git("reset", "--hard", base)

        note.unlink()
        note.symlink_to(adapter.name)
        expect(note)
        note.unlink()
        expect(note, docs_only=True)
        note.write_text("updated review notes\n")
        evidence = note.with_name("evidence.json")
        evidence.write_text("{}\n")
        expect(note, evidence, docs_only=True)

        # The raw diff does not expose the executable mode from unmerged stage 3.
        blob = git("rev-parse", f"{base}:{note}")
        git(
            "update-index",
            "--index-info",
            stdin=(
                f"0 {'0' * len(blob)}\t{note}\n"
                f"100644 {blob} 1\t{note}\n"
                f"100644 {blob} 2\t{note}\n"
                f"100755 {blob} 3\t{note}\n"
            ),
        )
        with self.assertRaisesRegex(ValueError, r"unmerged path.*note\.md"):
            make_plan(base)

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

    def test_delivery_rejects_receipts_below_recomputed_tier(self) -> None:
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
            fixture.establish_helper_baseline()

            def run_git(*args: str) -> str:
                return subprocess.run(
                    ["git", "-C", str(fixture.work), *args],
                    check=True,
                    text=True,
                    stdout=subprocess.PIPE,
                ).stdout.strip()

            def digest_tree() -> str:
                return subprocess.run(
                    ["python3", "scripts/feature-tree-fingerprint.py", "digest"],
                    cwd=fixture.work,
                    check=True,
                    text=True,
                    stdout=subprocess.PIPE,
                ).stdout.strip()

            # Verify a docs-only change first to get a genuine docs-tier receipt.
            note = fixture.work / "docs/wf02-note.md"
            note.write_text("# WF-02\n", encoding="utf-8")
            run_git("add", "docs/wf02-note.md")
            run_git("commit", "-m", "Add doc note")
            result = fixture.verify()
            self.assertEqual(result.returncode, 0, result.stderr)
            receipt_path = fixture.work / ".git/info/florabase-feature-verification.json"
            docs_receipt = json.loads(receipt_path.read_text())
            self.assertEqual(docs_receipt["verification"]["tier"], "docs")
            base = run_git("rev-parse", "origin/main")

            # Change a shared component (requiring product tier) without re-verifying;
            # keep working_tree_digest matching to isolate tier enforcement from digest drift.
            shared = fixture.work / "frontend/src/components/TierCheckFixture.tsx"
            shared.parent.mkdir(parents=True, exist_ok=True)
            shared.write_text("export const TierCheckFixture = () => null;\n", encoding="utf-8")
            run_git("add", "frontend/src/components/TierCheckFixture.tsx")
            run_git("commit", "-m", "Add shared component")
            receipt_path.write_text(
                json.dumps({**docs_receipt, "working_tree_digest": digest_tree()})
            )
            verify_cmd = [
                "python3",
                "scripts/feature-tree-fingerprint.py",
                "verify",
                "--branch",
                "ci/ci-002",
                "--base",
                base,
            ]
            rejected = subprocess.run(verify_cmd, cwd=fixture.work, text=True, capture_output=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("below required tier", rejected.stderr)
            self.assertIn("'docs'", rejected.stderr)
            self.assertIn("'product'", rejected.stderr)

            # Higher --full receipt passes delivery verification on a product-tier change.
            full_override = fixture.verify(full=True)
            self.assertEqual(full_override.returncode, 0, full_override.stderr)
            self.assertEqual(
                subprocess.run(verify_cmd, cwd=fixture.work, capture_output=True).returncode, 0
            )

            # Verify at product tier -> passes verify, then escalate via unknown path
            # -> receipt at product tier is rejected as below required full tier.
            product_result = fixture.verify()
            self.assertEqual(product_result.returncode, 0, product_result.stderr)
            product_receipt = json.loads(receipt_path.read_text())
            self.assertEqual(product_receipt["verification"]["tier"], "product")
            self.assertEqual(product_receipt["verification"]["workflow"], [])
            self.assertEqual(product_receipt["migration"]["result"], "skipped_by_impact")

            infra = fixture.work / "unknown.infra"
            infra.write_text("x\n", encoding="utf-8")
            run_git("add", "unknown.infra")
            run_git("commit", "-m", "Add unknown infra path")
            receipt_path.write_text(
                json.dumps({**product_receipt, "working_tree_digest": digest_tree()})
            )
            rejected_full = subprocess.run(
                verify_cmd, cwd=fixture.work, text=True, capture_output=True
            )
            self.assertNotEqual(rejected_full.returncode, 0)
            self.assertIn("below required tier", rejected_full.stderr)
            self.assertIn("'product'", rejected_full.stderr)
            self.assertIn("'full'", rejected_full.stderr)
        finally:
            fixture.tearDown()


class TestOwnershipInventoryTests(unittest.TestCase):
    def _create_fixture_repo(
        self, root: Path, *, seed_explicit_scopes: tuple[str, ...] = ()
    ) -> str:
        def git(*args: str) -> str:
            return subprocess.run(
                ["git", "-C", str(root), *args], check=True, text=True, capture_output=True
            ).stdout.strip()

        (root / "scripts").mkdir(parents=True, exist_ok=True)
        for name in (
            "verification_impact.py",
            "verification-impact.json",
            "verification_gate.py",
            "feature-tree-fingerprint.py",
            "disposable_workflow.py",
            "workflow_resources.py",
        ):
            shutil.copy2(ROOT / "scripts" / name, root / "scripts" / name)
        data = json.loads((root / "scripts/verification-impact.json").read_text(encoding="utf-8"))
        for scope_name in seed_explicit_scopes:
            scope = data["scopes"][scope_name]
            target = data["scopes"][scope.get("suite_scope", scope_name)]
            for layer in ("backend", "integration", "frontend"):
                for rel in target[layer]:
                    file_path = root / rel
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text("# fixture test\n", encoding="utf-8")
            for directory in target["frontend_dirs"]:
                dir_path = root / directory
                dir_path.mkdir(parents=True, exist_ok=True)
                (dir_path / "Existing.test.tsx").write_text("// fixture test\n", encoding="utf-8")
        (root / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
        (root / "docs").mkdir(exist_ok=True)
        (root / "docs/README.md").write_text("# Fixture\n", encoding="utf-8")
        git("init", "--initial-branch=main")
        git("config", "user.name", "Test")
        git("config", "user.email", "test@localhost")
        git("add", ".")
        git("commit", "-m", "base")
        return git("rev-parse", "HEAD")

    def test_new_test_in_owned_directory_is_selected_without_editing_impact_map(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scopes = (
                "taxonomy",
                "botany",
                "collection-views",
                "explore",
                "security-regression",
                "orders",
                "suppliers",
                "seeds",
            )
            base = self._create_fixture_repo(root, seed_explicit_scopes=scopes)
            map_before = (root / "scripts/verification-impact.json").read_text(encoding="utf-8")

            cases = [
                ("frontend/src/taxonomy/NewDirectoryOwned.test.tsx", "frontend", "frontend"),
                ("backend/tests/taxonomy/test_new_directory_owned.py", "backend", "backend"),
                (
                    "backend/tests/integration/taxonomy/test_new_directory_owned.py",
                    "integration",
                    "backend",
                ),
            ]
            for rel_path, suite_layer, expected_build in cases:
                with self.subTest(rel_path=rel_path):
                    file_path = root / rel_path
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text("# new test\n", encoding="utf-8")
                    result = subprocess.run(
                        [
                            sys.executable,
                            "scripts/verification_impact.py",
                            "--base",
                            base,
                            "--json",
                        ],
                        cwd=root,
                        text=True,
                        capture_output=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    plan = json.loads(result.stdout)
                    self.assertEqual(plan["mode"], "affected")
                    self.assertEqual(plan["changed_scopes"], ["taxonomy"])
                    self.assertIn(rel_path, plan[suite_layer])
                    self.assertEqual(plan["builds"], [expected_build])
                    file_path.unlink()

            # A test placed in an owned directory is also selected when source code in that scope
            # changes (without the test file itself changing or editing verification-impact.json).
            new_fe = root / "frontend/src/taxonomy/PersistentOwned.test.tsx"
            new_be = root / "backend/tests/taxonomy/test_persistent_owned.py"
            new_int = root / "backend/tests/integration/taxonomy/test_persistent_owned.py"
            for item in (new_fe, new_be, new_int):
                item.parent.mkdir(parents=True, exist_ok=True)
                item.write_text("# persistent test\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-m", "Add owned tests"],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            new_base = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip()
            src = root / "backend/src/florabase/taxonomy/service.py"
            src.parent.mkdir(parents=True, exist_ok=True)
            src.write_text("VALUE = 1\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "scripts/verification_impact.py", "--base", new_base, "--json"],
                cwd=root,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads(result.stdout)
            self.assertEqual(plan["mode"], "affected")
            self.assertIn("frontend/src/taxonomy/PersistentOwned.test.tsx", plan["frontend"])
            self.assertIn("backend/tests/taxonomy/test_persistent_owned.py", plan["backend"])
            self.assertIn(
                "backend/tests/integration/taxonomy/test_persistent_owned.py", plan["integration"]
            )
            self.assertEqual(
                (root / "scripts/verification-impact.json").read_text(encoding="utf-8"), map_before
            )

            # A test added in a product-owned shared directory selects product tier without edits.
            shared_test = root / "frontend/src/components/NewShared.test.tsx"
            shared_test.parent.mkdir(parents=True, exist_ok=True)
            shared_test.write_text("// shared\n", encoding="utf-8")
            product_result = subprocess.run(
                [sys.executable, "scripts/verification_impact.py", "--base", new_base, "--json"],
                cwd=root,
                text=True,
                capture_output=True,
            )
            self.assertEqual(product_result.returncode, 0, product_result.stderr)
            self.assertEqual(json.loads(product_result.stdout)["tier"], "product")

    def test_unowned_test_file_fails_verification_plan_and_gate_before_docker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            base = self._create_fixture_repo(root)
            fake_bin = Path(temporary) / "bin"
            fake_bin.mkdir()
            docker_log = Path(temporary) / "docker.log"
            for tool in ("docker", "make"):
                script = fake_bin / tool
                script.write_text(
                    f"#!/bin/sh\necho {tool} >> {str(docker_log)!r}\nexit 99\n",
                    encoding="utf-8",
                )
                script.chmod(0o755)
            env = {
                **os.environ,
                "PATH": f"{fake_bin}:{os.environ['PATH']}",
                "FLORABASE_LOCK_DIR": str(Path(temporary) / "locks"),
            }

            # Even a docs-only diff must fail closed before planning/gating if an unowned test
            # file exists anywhere in the repository.
            (root / "docs/README.md").write_text("# Docs edit\n", encoding="utf-8")

            unowned_cases = [
                "frontend/src/unowned_dir/Orphan.test.tsx",
                "frontend/src/Orphan.spec.ts",
                "frontend/OrphanRoot.test.ts",
                "backend/tests/test_unregistered.py",
                "backend/tests/unregistered_test.py",
                "backend/tests/unowned_dir/test_orphan.py",
                "backend/tests/integration/test_unregistered.py",
                "backend/tests/integration/unowned_dir/test_orphan.py",
            ]
            for rel_path in unowned_cases:
                with self.subTest(rel_path=rel_path):
                    target = root / rel_path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("# unowned\n", encoding="utf-8")

                    plan_cmd = subprocess.run(
                        [
                            sys.executable,
                            "scripts/verification_impact.py",
                            "--base",
                            base,
                            "--json",
                        ],
                        cwd=root,
                        env=env,
                        text=True,
                        capture_output=True,
                    )
                    self.assertNotEqual(plan_cmd.returncode, 0)
                    self.assertIn(rel_path, plan_cmd.stderr)
                    self.assertFalse(docker_log.exists())

                    gate_cmd = subprocess.run(
                        [
                            sys.executable,
                            "scripts/verification_gate.py",
                            "--base",
                            base,
                            "--execution",
                            str(Path(temporary) / "execution.json"),
                        ],
                        cwd=root,
                        env=env,
                        text=True,
                        capture_output=True,
                    )
                    self.assertNotEqual(gate_cmd.returncode, 0)
                    self.assertIn(rel_path, gate_cmd.stderr)
                    self.assertFalse(docker_log.exists())

                    target.unlink()

            # A symlinked test file in an unowned location must also be rejected.
            symlink_target = root / "frontend/src/unowned_link/Link.test.tsx"
            symlink_target.parent.mkdir(parents=True, exist_ok=True)
            symlink_target.symlink_to("../docs/README.md")
            symlink_plan = subprocess.run(
                [sys.executable, "scripts/verification_impact.py", "--base", base, "--json"],
                cwd=root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(symlink_plan.returncode, 0)
            self.assertIn("frontend/src/unowned_link/Link.test.tsx", symlink_plan.stderr)
            symlink_target.unlink()

            # Symlinked directories under frontend/ or backend/tests/ must fail closed rather
            # than silently skipping nested tests.
            external_dir = Path(temporary) / "external_tests"
            external_dir.mkdir()
            (external_dir / "Hidden.test.tsx").write_text("// hidden\n", encoding="utf-8")
            for link_rel in (
                "frontend/src/taxonomy/linked_sub",
                "frontend/src/unowned_symlink_dir",
                "backend/tests/linked_sub",
            ):
                with self.subTest(link_rel=link_rel):
                    link_path = root / link_rel
                    link_path.parent.mkdir(parents=True, exist_ok=True)
                    link_path.symlink_to(external_dir, target_is_directory=True)
                    dir_link_plan = subprocess.run(
                        [
                            sys.executable,
                            "scripts/verification_impact.py",
                            "--base",
                            base,
                            "--json",
                        ],
                        cwd=root,
                        env=env,
                        text=True,
                        capture_output=True,
                    )
                    self.assertNotEqual(dir_link_plan.returncode, 0)
                    self.assertIn(link_rel, dir_link_plan.stderr)
                    self.assertFalse(docker_log.exists())
                    link_path.unlink()

            # Top-level frontend/dist and frontend/coverage are build outputs, but nested
            # directories with those names under frontend/src/ are real source trees.
            for ignored_rel in ("frontend/dist/Bundle.test.js", "frontend/coverage/Cov.test.js"):
                ignored_path = root / ignored_rel
                ignored_path.parent.mkdir(parents=True, exist_ok=True)
                ignored_path.write_text("// build output\n", encoding="utf-8")
            ok_plan = subprocess.run(
                [sys.executable, "scripts/verification_impact.py", "--base", base, "--json"],
                cwd=root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(ok_plan.returncode, 0, ok_plan.stderr)

            for nested_rel in (
                "frontend/src/coverage/Nested.test.tsx",
                "frontend/src/dist/Nested.test.tsx",
            ):
                with self.subTest(nested_rel=nested_rel):
                    nested_path = root / nested_rel
                    nested_path.parent.mkdir(parents=True, exist_ok=True)
                    nested_path.write_text("// nested\n", encoding="utf-8")
                    nested_plan = subprocess.run(
                        [
                            sys.executable,
                            "scripts/verification_impact.py",
                            "--base",
                            base,
                            "--json",
                        ],
                        cwd=root,
                        env=env,
                        text=True,
                        capture_output=True,
                    )
                    self.assertNotEqual(nested_plan.returncode, 0)
                    self.assertIn(nested_rel, nested_plan.stderr)
                    nested_path.unlink()

    def test_moved_or_deleted_test_cannot_silently_escape_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scopes = (
                "taxonomy",
                "botany",
                "collection-views",
                "explore",
                "security-regression",
                "orders",
                "suppliers",
                "seeds",
            )
            self._create_fixture_repo(root, seed_explicit_scopes=scopes)
            moved_from = root / "frontend/src/taxonomy/MoveMe.test.tsx"
            moved_from.write_text("// move me\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-m", "Add MoveMe test"],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            base = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip()

            # Moving between two owned directories covers both old and new scopes.
            moved_to = root / "frontend/src/orders/MoveMe.test.tsx"
            subprocess.run(
                ["git", "-C", str(root), "mv", str(moved_from), str(moved_to)],
                check=True,
            )
            previous = Path.cwd()
            os.chdir(root)
            try:
                plan = make_plan(base)
                self.assertEqual(plan["mode"], "affected")
                self.assertIn("taxonomy", plan["changed_scopes"])
                self.assertIn("orders", plan["changed_scopes"])
                self.assertIn("frontend/src/orders/MoveMe.test.tsx", plan["frontend"])

                # Moving into an unowned directory fails closed.
                unowned = root / "frontend/src/unowned/MoveMe.test.tsx"
                unowned.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(
                    ["git", "-C", str(root), "mv", str(moved_to), str(unowned)],
                    check=True,
                )
                with self.assertRaisesRegex(ValueError, r"frontend/src/unowned/MoveMe\.test\.tsx"):
                    make_plan(base)
                subprocess.run(
                    ["git", "-C", str(root), "mv", str(unowned), str(moved_from)],
                    check=True,
                )

                # Deleting an explicitly registered test without updating the map fails closed.
                (root / "backend/tests/test_taxonomy.py").unlink()
                with self.assertRaisesRegex(ValueError, "missing mapped suites"):
                    make_plan(base)
                subprocess.run(
                    ["git", "-C", str(root), "checkout", "--", "backend/tests/test_taxonomy.py"],
                    check=True,
                )

                # Deleting an explicit product_tests entry or a scope entry alongside a product
                # change without updating the map fails closed.
                with self.assertRaisesRegex(ValueError, "missing mapped suites"):
                    plan_paths(["backend/tests/test_health.py"], base)
                (root / "backend/tests/test_taxonomy.py").unlink()
                with self.assertRaisesRegex(ValueError, "missing mapped suites"):
                    plan_paths(
                        ["backend/src/florabase/main.py", "backend/tests/test_taxonomy.py"], base
                    )
                subprocess.run(
                    ["git", "-C", str(root), "checkout", "--", "backend/tests/test_taxonomy.py"],
                    check=True,
                )
            finally:
                os.chdir(previous)

    def test_load_map_rejects_invalid_or_overlapping_test_ownership(self) -> None:
        original = json.loads(MAP_PATH.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temporary:
            temp_map = Path(temporary) / "impact.json"
            with patch("verification_impact.MAP_PATH", temp_map):
                # Overlapping frontend_dirs between two scopes.
                overlapping = json.loads(json.dumps(original))
                overlapping["scopes"]["orders"]["frontend_dirs"] = ["frontend/src/taxonomy/"]
                temp_map.write_text(json.dumps(overlapping), encoding="utf-8")
                with self.assertRaisesRegex(
                    ValueError, "overlapping frontend test directory ownership"
                ):
                    load_map()

                # Nested overlapping backend_dirs.
                nested = json.loads(json.dumps(original))
                nested["scopes"]["orders"]["backend_dirs"] = ["backend/tests/taxonomy/sub/"]
                temp_map.write_text(json.dumps(nested), encoding="utf-8")
                with self.assertRaisesRegex(
                    ValueError, "overlapping backend test directory ownership"
                ):
                    load_map()

                # Root directory cannot be owned by a single scope.
                for scope_key, root_dir in (
                    ("backend_dirs", "backend/tests/"),
                    ("integration_dirs", "backend/tests/integration/"),
                    ("frontend_dirs", "frontend/src/"),
                ):
                    bad_root = json.loads(json.dumps(original))
                    bad_root["scopes"]["taxonomy"][scope_key] = [root_dir]
                    temp_map.write_text(json.dumps(bad_root), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_map()

                # Layer mismatch in explicit suite or directory list.
                mismatch = json.loads(json.dumps(original))
                mismatch["scopes"]["taxonomy"]["backend"].append(
                    "backend/tests/integration/test_taxonomy.py"
                )
                temp_map.write_text(json.dumps(mismatch), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "invalid backend suites"):
                    load_map()

                # Non-test file in product_tests.
                bad_product = json.loads(json.dumps(original))
                bad_product["product_tests"].append("backend/src/florabase/main.py")
                temp_map.write_text(json.dumps(bad_product), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "invalid product_tests"):
                    load_map()


if __name__ == "__main__":
    unittest.main()
