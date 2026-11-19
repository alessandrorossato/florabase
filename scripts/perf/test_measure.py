"""Unit tests for PERF-001 isolation, ownership cleanup, strict pin mode and evaluation."""

from __future__ import annotations

import importlib.util
import json
import os
import signal
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

PERF_DIR = Path(__file__).resolve().parent
ROOT = PERF_DIR.parents[1]
if str(PERF_DIR) not in sys.path:
    sys.path.insert(0, str(PERF_DIR))

import comprehensive  # noqa: E402

spec = importlib.util.spec_from_file_location("perf_measure", PERF_DIR / "measure.py")
assert spec and spec.loader
measure = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = measure
spec.loader.exec_module(measure)


def _sample_targets() -> dict[str, str]:
    return {
        name: f"0198f000-0000-7000-8000-{index:012x}"
        for index, name in enumerate([*comprehensive.MANIFEST_SCENARIO_KEYS, "attachment"], start=1)
    }


def _sample_ledger(targets: dict[str, str], pin: dict[str, Any]) -> dict[str, Any]:
    records = {
        scenario_key: targets[name]
        for name, scenario_key in comprehensive.MANIFEST_SCENARIO_KEYS.items()
    }
    return {
        "dataset": pin["dataset"],
        "version": pin["version"],
        "profile": pin["profile"],
        "seed": pin["seed"],
        "anchor_date": pin["anchor_date"],
        "volume": pin["volume"],
        "plan_sha256": pin["plan_sha256"],
        "schema_revision": pin["baseline"]["schema_revision"],
        "state": "ready",
        "records": records,
    }


def _valid_manifest(*, pin_mode: str = comprehensive.PIN_MODE_STRICT) -> dict[str, Any]:
    pin = comprehensive.expected_comprehensive_pin()
    targets = _sample_targets()
    ledger = _sample_ledger(targets, pin)
    manifest = comprehensive.validate_fixture_manifest(
        ledger=ledger,
        verify_baseline={
            "state": "baseline-verified",
            "domain_problems": [],
            "baseline_differences": [],
            "canonical_sha256": pin["baseline"]["canonical_sha256"],
        },
        digest={
            "canonical_sha256": pin["baseline"]["canonical_sha256"],
            "media_files": pin["baseline"]["media_files"],
            "media_sha256": pin["baseline"]["media_sha256"],
            "scenario_keys_sha256": pin["baseline"]["scenario_keys_sha256"],
        },
        validate_report={"domain": "valid"},
        targets=targets,
        live_schema_revision=pin["baseline"]["schema_revision"],
        live_table_counts=dict(pin["tables"]),
        live_canonical_places_count=287,
        live_attachment_count=pin["tables"]["attachments"],
        media_verify_output=(
            f"Verified {pin['tables']['attachments']} stored attachment file(s) "
            "against database metadata\n"
        ),
        expected_pin=pin,
        source_code_head=pin["baseline"]["schema_revision"],
        pin_mode=pin_mode,
    )
    manifest["targets_source"] = "validated_comprehensive_ledger"
    return manifest


def _sample_api_entry(*, median_ms: float = 12.0, queries: int = 5) -> dict[str, Any]:
    samples = [median_ms] * 7
    return {
        "first_ms": median_ms + 3.0,
        "median_ms": median_ms,
        "range_ms": [median_ms, median_ms],
        "samples_ms": samples,
        "bytes": 1024,
        "queries": [queries],
        "query_count_samples": [queries] * 7,
        "sql_statements_count": 1 if queries > 0 else 0,
        "sql_zero_queries_verified": queries == 0,
        "sample_note": "7 samples; not a statistical p95",
    }


def _valid_post_mutation_integrity(manifest: dict[str, Any]) -> dict[str, Any]:
    expected_counts = dict(manifest["table_counts"])
    return comprehensive.evaluate_post_mutation_integrity(
        expected_counts=expected_counts,
        post_counts=expected_counts,
        expected_canonical_places=manifest["canonical_geographic_places"],
        post_canonical_places=manifest["canonical_geographic_places"],
        expected_schema_revision=manifest["schema_revision"],
        post_schema_revision=manifest["schema_revision"],
        created_identity_deleted=True,
        residual_perf_records=0,
        media_verify_output=(
            f"Verified {expected_counts['attachments']} stored attachment file(s) "
            "against database metadata"
        ),
        expected_attachments=expected_counts["attachments"],
    )


def _valid_checkpoint() -> dict[str, Any]:
    return {
        "JSHeapUsedSize": 5_000_000,
        "Nodes": 700,
        "JSEventListeners": 450,
        "Documents": 1,
        "maps": 0,
        "timers": {"intervals": 2, "timeouts": 0},
    }


def _valid_report(*, pin_mode: str = comprehensive.PIN_MODE_STRICT) -> dict[str, Any]:
    manifest = _valid_manifest(pin_mode=pin_mode)
    session_state = {
        "count": 1,
        "last_seen_at": "2026-11-18T00:00:00Z",
        "idle_expires_at": "2026-11-19T00:00:00Z",
    }
    reads = {endpoint: _sample_api_entry() for endpoint in comprehensive.REQUIRED_API_ENDPOINTS}
    workload = [
        {
            "name": name,
            "ms": 520,
            "requests": [{"path": f"/{name}", "method": "GET"}],
            "external": 0,
            "maps": 1 if name in {"provenance", "occurrence"} else 0,
        }
        for name in comprehensive.REQUIRED_BROWSER_ROUTES
    ]
    idle_samples = [
        {
            "at": 1700000000.0 + index * 10.0,
            "containers": [{"Name": "backend"}, {"Name": "frontend"}, {"Name": "db"}],
            "connections": {"total": 5, "idle": 5},
            "sessions": session_state,
        }
        for index in range(13)
    ]
    return {
        "schema_version": 2,
        "generated_at": "2026-11-19T22:00:00+00:00",
        "pin_mode": pin_mode,
        "warmup_s": 20,
        "errors": [],
        "environment": {
            "pin_mode": pin_mode,
            "startup": dict.fromkeys(comprehensive.REQUIRED_STARTUP_KEYS, 1.5),
            "manifest": manifest,
            "runtime_config": {
                "storage_mode": "tmpfs",
                "tmpfs_disclosure": "Runs on tmpfs; disk durability excluded.",
            },
            "process_counts": {
                svc: {"count": 2, "commands": [svc]} for svc in comprehensive.REQUIRED_SERVICES
            },
            "images": [
                {
                    "id": "sha256:aaa",
                    "repo_tags": ["florabase-perf-backend:own1"],
                    "source_head": "abc",
                },
                {
                    "id": "sha256:bbb",
                    "repo_tags": ["florabase-perf-frontend:own1"],
                    "source_head": "abc",
                },
                {"id": "sha256:ccc", "repo_tags": ["postgres:18.6-alpine"]},
            ],
            "source": {"head": "abc", "tree": "def", "base": "000", "dirty": False},
        },
        "api": {
            "manifest": manifest,
            "sql_instrumentation": {
                "extension_installed": True,
                "shared_preload_libraries": "pg_stat_statements",
                "reset_executed_per_sample": True,
                "probe_query_captured": True,
                "sample_count_per_endpoint": 7,
                "endpoints_measured": len(reads),
            },
            "reads": reads,
            "statements": {
                endpoint: [{"query": "SELECT 1", "calls": 5, "ms": 1.0}] for endpoint in reads
            },
            "create_edit_delete_ms": 15.0,
            "fixture_integrity_after_mutation": _valid_post_mutation_integrity(manifest),
        },
        "transfer": {
            "static_assets": {
                "/assets/index-abc.js": {
                    "raw_bytes": 1000,
                    "gzip_bytes": 400,
                    "vary": "Accept-Encoding",
                },
                "/assets/index-abc.css": {
                    "raw_bytes": 800,
                    "gzip_bytes": 300,
                    "vary": "Accept-Encoding",
                },
            },
            "runtime_configuration": {"compressed": False},
            "health": {"compressed": False},
            "protected_api_compressed": False,
        },
        "browser": {
            "initial": {
                "ms": 720,
                "requests": [{"path": "/api/v1/dashboard", "method": "GET"}],
                "resources": [
                    {"path": "/assets/index-abc.js", "bytes": 106_000, "transfer": 36_000}
                ],
            },
            "errors": [],
            "workload": workload,
            "cycles": [_valid_checkpoint() for _ in range(7)],
            "cycleRequests": [38, 38, 38, 38, 38, 38],
            "final": _valid_checkpoint(),
            "idleSeconds": 120,
            "idleRequests": [],
            "idle": idle_samples,
            "resources": [{"path": "/assets/index-abc.js", "bytes": 210_000, "transfer": 70_000}],
        },
        "chunk_recovery": {
            "stale_asset_path": "/assets/PERF-review-stale-chunk.js",
            "nginx_fallback": {"status": 200, "contentType": "text/html"},
            "shell_retained": True,
            "automatic_reload": False,
            "page_errors": [],
        },
        "cleanup": {
            "project": "florabase-perf",
            "owner_id": "owner-123",
            "ownership_verified": True,
            "containers_remaining": 0,
            "networks_remaining": 0,
            "volumes_remaining": 0,
            "images_remaining": 0,
            "named_volumes_deleted": 0,
        },
    }


class IsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_lock_dir = tempfile.TemporaryDirectory(prefix="florabase-test-locks-")
        self._env_patch = patch.dict(os.environ, {"FLORABASE_LOCK_DIR": self._tmp_lock_dir.name})
        self._env_patch.start()

    def tearDown(self) -> None:
        self._env_patch.stop()
        self._tmp_lock_dir.cleanup()

    def config(self, **service_changes: Any) -> dict[str, Any]:
        services = {name: {"tmpfs": ["/disposable"]} for name in ("db", "backend")}
        services["db"].update(service_changes)
        return {"name": "florabase-perf", "services": services}

    def test_rejects_durable_volumes_before_starting(self) -> None:
        with patch.object(
            measure,
            "compose",
            return_value=json.dumps(self.config(volumes=[{"source": "operator_data"}])),
        ) as compose:
            with self.assertRaisesRegex(RuntimeError, "isolation"):
                measure.start()
            self.assertEqual(compose.call_count, 1)

    def test_rejects_published_database_before_starting(self) -> None:
        with patch.object(
            measure, "compose", return_value=json.dumps(self.config(ports=[5432]))
        ) as compose:
            with self.assertRaisesRegex(RuntimeError, "isolation"):
                measure.start()
            self.assertEqual(compose.call_count, 1)

    def test_rejects_existing_project_containers_without_replacing_data(self) -> None:
        with patch.object(
            measure,
            "compose",
            side_effect=[json.dumps(self.config()), "existing-container"],
        ) as compose:
            with self.assertRaisesRegex(RuntimeError, "already exist"):
                measure.start()
            self.assertEqual(compose.call_count, 2)
            compose.assert_called_with("ps", "--all", "-q")

    def test_rejects_existing_project_networks_without_replacing_data(self) -> None:
        with (
            patch.object(measure, "compose", side_effect=[json.dumps(self.config()), ""]),
            patch.object(measure, "_existing_project_networks", return_value=["net-123"]),
        ):
            with self.assertRaisesRegex(RuntimeError, "networks already exist"):
                measure.start()

    def test_rejects_wrong_project(self) -> None:
        config = self.config()
        config["name"] = "florabase"
        with patch.object(measure, "compose", return_value=json.dumps(config)) as compose:
            with self.assertRaisesRegex(RuntimeError, "Unexpected project"):
                measure.start()
            self.assertEqual(compose.call_count, 1)

    def test_concurrent_invocation_refused_by_machine_lock_without_cleanup(self) -> None:
        with measure._perf_lock():
            with patch.object(measure, "_stop_owned") as stop_mock:
                report = measure.run_rehearsal(warmup_s=0)
        stop_mock.assert_not_called()
        self.assertTrue(any("already running" in err for err in report["errors"]))
        self.assertEqual(report["evaluation"]["harness_status"], "incomplete")

    def test_sample_succeeds_while_lifecycle_lock_held(self) -> None:
        stats_line = json.dumps({"Name": "florabase-perf-backend-1"})
        with measure._perf_lock():
            with (
                patch.object(measure, "compose") as compose_mock,
                patch.object(
                    measure.subprocess,
                    "check_output",
                    side_effect=[
                        f"{stats_line}\n",
                        '{"total": 5, "idle": 5}',
                        '{"count": 1, "last_seen_at": "2026-11-19T00:00:00Z", "idle_expires_at": "2026-11-20T00:00:00Z"}',
                    ],
                ),
            ):
                result = measure.sample()
        compose_mock.assert_not_called()
        self.assertEqual(result["connections"]["total"], 5)
        self.assertEqual(result["sessions"]["count"], 1)

    def test_golden_dataset_target_guards_remain_unmodified(self) -> None:
        source = (ROOT / "scripts/golden_dataset.py").read_text(encoding="utf-8")
        self.assertIn("COPY_NAME = re.compile", source)
        self.assertIn("settings.environment is Environment.TEST", source)
        self.assertIn('UAT_INSTANCE_PROJECT = re.compile(r"florabase-uat-branch-', source)
        self.assertNotIn("florabase_perf", source)

    def test_provision_refuses_non_golden_copy_name(self) -> None:
        with self.assertRaisesRegex(comprehensive.FixtureValidationError, "Disallowed golden copy"):
            comprehensive.provision_comprehensive_bundle(ROOT, copy_name="florabase_perf")


class ManifestValidationTests(unittest.TestCase):
    def test_validates_pinned_comprehensive_manifest_in_strict_mode(self) -> None:
        manifest = _valid_manifest()
        self.assertTrue(manifest["valid"])
        self.assertEqual(manifest["pin_mode"], comprehensive.PIN_MODE_STRICT)
        self.assertTrue(manifest["strict_pin_enforced"])
        self.assertFalse(manifest["certification_eligible"])
        self.assertEqual(manifest["baseline_state"], "baseline-verified")
        self.assertEqual(manifest["differences_from_pin"], [])
        self.assertEqual(len(manifest["targets"]), len(comprehensive.MANIFEST_SCENARIO_KEYS) + 1)

    def test_strict_mode_rejects_modified_baseline_by_default(self) -> None:
        pin = comprehensive.expected_comprehensive_pin()
        targets = _sample_targets()
        ledger = _sample_ledger(targets, pin)
        with self.assertRaisesRegex(
            comprehensive.FixtureValidationError,
            "strict pin violation.*invariant-valid-baseline-modified",
        ):
            comprehensive.validate_fixture_manifest(
                ledger=ledger,
                verify_baseline={
                    "state": "invariant-valid-baseline-modified",
                    "domain_problems": [],
                    "baseline_differences": ["table native_range_proposals: changed"],
                },
                digest={
                    "canonical_sha256": "1" * 64,
                    "media_files": pin["baseline"]["media_files"],
                    "media_sha256": pin["baseline"]["media_sha256"],
                    "scenario_keys_sha256": pin["baseline"]["scenario_keys_sha256"],
                },
                validate_report={"domain": "valid"},
                targets=targets,
                live_schema_revision=pin["baseline"]["schema_revision"],
                live_table_counts=dict(pin["tables"]),
                live_canonical_places_count=287,
                live_attachment_count=pin["tables"]["attachments"],
                media_verify_output=(
                    f"Verified {pin['tables']['attachments']} stored attachment file(s)"
                ),
                expected_pin=pin,
                source_code_head=pin["baseline"]["schema_revision"],
            )

    def test_explicit_allow_modified_mode_records_drift_and_bars_certification(self) -> None:
        pin = comprehensive.expected_comprehensive_pin()
        targets = _sample_targets()
        ledger = _sample_ledger(targets, pin)
        manifest = comprehensive.validate_fixture_manifest(
            ledger=ledger,
            verify_baseline={
                "state": "invariant-valid-baseline-modified",
                "domain_problems": [],
                "baseline_differences": ["table native_range_proposals: changed"],
            },
            digest={
                "canonical_sha256": "1" * 64,
                "media_files": pin["baseline"]["media_files"],
                "media_sha256": pin["baseline"]["media_sha256"],
                "scenario_keys_sha256": pin["baseline"]["scenario_keys_sha256"],
            },
            validate_report={"domain": "valid"},
            targets=targets,
            live_schema_revision=pin["baseline"]["schema_revision"],
            live_table_counts=dict(pin["tables"]),
            live_canonical_places_count=287,
            live_attachment_count=pin["tables"]["attachments"],
            media_verify_output=(
                f"Verified {pin['tables']['attachments']} stored attachment file(s)"
            ),
            expected_pin=pin,
            source_code_head=pin["baseline"]["schema_revision"],
            pin_mode=comprehensive.PIN_MODE_ALLOW_MODIFIED,
        )
        self.assertTrue(manifest["valid"])
        self.assertEqual(manifest["pin_mode"], comprehensive.PIN_MODE_ALLOW_MODIFIED)
        self.assertFalse(manifest["strict_pin_enforced"])
        self.assertFalse(manifest["baseline_pin_matches"])
        self.assertFalse(manifest["certification_eligible"])
        self.assertEqual(len(manifest["differences_from_pin"]), 2)

    def test_allow_modified_mode_still_rejects_domain_invalid(self) -> None:
        pin = comprehensive.expected_comprehensive_pin()
        targets = _sample_targets()
        ledger = _sample_ledger(targets, pin)
        with self.assertRaisesRegex(comprehensive.FixtureValidationError, "domain-invalid"):
            comprehensive.validate_fixture_manifest(
                ledger=ledger,
                verify_baseline={
                    "state": "domain-invalid",
                    "domain_problems": ["missing entity"],
                    "baseline_differences": [],
                },
                digest={"canonical_sha256": pin["baseline"]["canonical_sha256"]},
                validate_report={"domain": "valid"},
                targets=targets,
                live_schema_revision=pin["baseline"]["schema_revision"],
                live_table_counts=dict(pin["tables"]),
                live_canonical_places_count=287,
                live_attachment_count=pin["tables"]["attachments"],
                media_verify_output=(
                    f"Verified {pin['tables']['attachments']} stored attachment file(s)"
                ),
                expected_pin=pin,
                source_code_head=pin["baseline"]["schema_revision"],
                pin_mode=comprehensive.PIN_MODE_ALLOW_MODIFIED,
            )

    def test_rejects_schema_revision_and_count_and_media_mismatches(self) -> None:
        pin = comprehensive.expected_comprehensive_pin()
        targets = _sample_targets()
        ledger = _sample_ledger(targets, pin)
        with self.assertRaisesRegex(
            comprehensive.FixtureValidationError, "live DB Alembic revision"
        ):
            comprehensive.validate_fixture_manifest(
                ledger=ledger,
                verify_baseline={"state": "baseline-verified"},
                digest={"canonical_sha256": pin["baseline"]["canonical_sha256"]},
                validate_report={"domain": "valid"},
                targets=targets,
                live_schema_revision="20990101_9999",
                live_table_counts=dict(pin["tables"]),
                live_canonical_places_count=287,
                live_attachment_count=pin["tables"]["attachments"],
                media_verify_output=f"Verified {pin['tables']['attachments']} stored attachment file(s)",
                expected_pin=pin,
                source_code_head=pin["baseline"]["schema_revision"],
            )
        bad_counts = dict(pin["tables"])
        bad_counts["seed_lots"] -= 1
        with self.assertRaisesRegex(comprehensive.FixtureValidationError, "live table seed_lots"):
            comprehensive.validate_fixture_manifest(
                ledger=ledger,
                verify_baseline={"state": "baseline-verified"},
                digest={"canonical_sha256": pin["baseline"]["canonical_sha256"]},
                validate_report={"domain": "valid"},
                targets=targets,
                live_schema_revision=pin["baseline"]["schema_revision"],
                live_table_counts=bad_counts,
                live_canonical_places_count=287,
                live_attachment_count=pin["tables"]["attachments"],
                media_verify_output=f"Verified {pin['tables']['attachments']} stored attachment file(s)",
                expected_pin=pin,
                source_code_head=pin["baseline"]["schema_revision"],
            )
        with self.assertRaisesRegex(comprehensive.FixtureValidationError, "media verification"):
            comprehensive.validate_fixture_manifest(
                ledger=ledger,
                verify_baseline={"state": "baseline-verified"},
                digest={"canonical_sha256": pin["baseline"]["canonical_sha256"]},
                validate_report={"domain": "valid"},
                targets=targets,
                live_schema_revision=pin["baseline"]["schema_revision"],
                live_table_counts=dict(pin["tables"]),
                live_canonical_places_count=287,
                live_attachment_count=pin["tables"]["attachments"],
                media_verify_output="Verified 0 stored attachment file(s)",
                expected_pin=pin,
                source_code_head=pin["baseline"]["schema_revision"],
            )

    def test_load_validated_manifest_rejects_unvalidated_or_invalid_pin_mode(self) -> None:
        with patch.object(
            measure,
            "compose",
            return_value=json.dumps({"valid": False, "profile": "smoke", "targets": {}}),
        ):
            with self.assertRaisesRegex(comprehensive.FixtureValidationError, "missing valid"):
                measure._load_validated_manifest()
        bad_manifest = _valid_manifest()
        bad_manifest["pin_mode"] = "bypass"
        with patch.object(measure, "compose", return_value=json.dumps(bad_manifest)):
            with self.assertRaisesRegex(comprehensive.FixtureValidationError, "invalid pin_mode"):
                measure._load_validated_manifest()


class ReportEvaluationTests(unittest.TestCase):
    def test_passes_complete_valid_rehearsal(self) -> None:
        report = _valid_report()
        evaluation = comprehensive.evaluate_report(report)
        self.assertEqual(evaluation["execution_stage"], "preliminary_source_rehearsal")
        self.assertEqual(evaluation["pin_mode"], comprehensive.PIN_MODE_STRICT)
        self.assertFalse(evaluation["rc_g_perf_certification"])
        self.assertFalse(evaluation["certification_eligible"])
        self.assertEqual(evaluation["harness_status"], "passed")
        self.assertEqual(evaluation["application_status"], "passed")
        self.assertEqual(evaluation["invariant_status"], "passed")
        self.assertEqual(evaluation["failure_classification"], "none")
        self.assertEqual(evaluation["failures"], [])
        self.assertEqual(evaluation["operator_g_perf_thresholds"]["status"], "unset_until_g_perf")

    def test_evaluate_rejects_modified_baseline_in_strict_mode_and_allows_explicit_opt_in(
        self,
    ) -> None:
        report = _valid_report(pin_mode=comprehensive.PIN_MODE_ALLOW_MODIFIED)
        manifest = report["environment"]["manifest"]
        manifest["baseline_state"] = "invariant-valid-baseline-modified"
        manifest["baseline_pin_matches"] = False
        manifest["differences_from_pin"] = ["table native_range_proposals: changed"]

        strict_eval = comprehensive.evaluate_report(report, pin_mode=comprehensive.PIN_MODE_STRICT)
        self.assertEqual(strict_eval["invariant_status"], "failed")
        self.assertEqual(strict_eval["failure_classification"], "harness_invalid")

        optin_eval = comprehensive.evaluate_report(report)
        self.assertEqual(optin_eval["invariant_status"], "passed")
        self.assertEqual(optin_eval["execution_stage"], "preliminary_modified_baseline_rehearsal")
        self.assertFalse(optin_eval["rc_g_perf_certification"])
        self.assertFalse(optin_eval["certification_eligible"])

    def test_rejects_incomplete_or_malformed_api_endpoint_inventory(self) -> None:
        report = _valid_report()
        del report["api"]["reads"]["/schedule"]
        report["api"]["reads"]["/dashboard"] = {"first_ms": 10.0, "median_ms": 9.0}
        evaluation = comprehensive.evaluate_report(report)
        self.assertEqual(evaluation["harness_status"], "failed")
        self.assertEqual(evaluation["failure_classification"], "harness_invalid")
        self.assertTrue(
            any("api_measurements_complete" in item for item in evaluation["harness_failures"])
        )

    def test_distinguishes_legitimate_zero_query_route_from_missing_instrumentation(self) -> None:
        legit = _valid_report()
        legit["api"]["reads"]["/history"] = _sample_api_entry(median_ms=4.0, queries=0)
        legit_eval = comprehensive.evaluate_report(legit)
        self.assertEqual(legit_eval["invariant_status"], "passed")

        broken_inst = _valid_report()
        broken_inst["api"]["sql_instrumentation"]["probe_query_captured"] = False
        broken_eval = comprehensive.evaluate_report(broken_inst)
        self.assertEqual(broken_eval["invariant_status"], "failed")
        self.assertTrue(
            any(
                "api_sql_instrumentation_complete" in item
                for item in broken_eval["harness_failures"]
            )
        )

        all_zero = _valid_report()
        for ep in all_zero["api"]["reads"]:
            all_zero["api"]["reads"][ep] = _sample_api_entry(median_ms=5.0, queries=0)
        all_zero_eval = comprehensive.evaluate_report(all_zero)
        self.assertEqual(all_zero_eval["invariant_status"], "failed")
        self.assertTrue(
            any(
                "api_sql_instrumentation_complete" in item
                for item in all_zero_eval["harness_failures"]
            )
        )

    def test_rejects_errors_and_duplicate_or_missing_browser_routes(self) -> None:
        report = _valid_report()
        report["errors"] = ["RuntimeError: simulated failure"]
        report["browser"]["workload"] = report["browser"]["workload"][:-1]
        report["browser"]["workload"].append(dict(report["browser"]["workload"][0]))
        evaluation = comprehensive.evaluate_report(report)
        self.assertEqual(evaluation["harness_status"], "failed")
        self.assertTrue(
            any("harness_execution_no_errors" in item for item in evaluation["failures"])
        )
        self.assertTrue(any("browser_workload_complete" in item for item in evaluation["failures"]))

    def test_rejects_document_count_growth_and_accepts_constant_two_documents(self) -> None:
        report = _valid_report()
        for cp in [*report["browser"]["cycles"], report["browser"]["final"]]:
            cp["Documents"] = 2
        self.assertEqual(comprehensive.evaluate_report(report)["invariant_status"], "passed")

        report["browser"]["cycles"][4]["Documents"] = 3
        leaked_eval = comprehensive.evaluate_report(report)
        self.assertEqual(leaked_eval["application_status"], "failed")
        self.assertTrue(
            any(
                "browser_six_cycles_stability" in item
                for item in leaked_eval["application_failures"]
            )
        )

    def test_distinguishes_application_failure_from_valid_harness(self) -> None:
        report = _valid_report()
        report["browser"]["idleRequests"] = [{"path": "/api/v1/dashboard", "method": "GET"}]
        report["browser"]["cycles"][3]["maps"] = 1
        report["browser"]["resources"].append(
            {"path": "/assets/huge.js", "bytes": 550_000, "transfer": 200_000}
        )
        report["chunk_recovery"]["automatic_reload"] = True
        evaluation = comprehensive.evaluate_report(report)
        self.assertEqual(evaluation["harness_status"], "passed")
        self.assertEqual(evaluation["application_status"], "failed")
        self.assertEqual(evaluation["failure_classification"], "application_failure")
        for expected in (
            "browser_idle_120s_stability",
            "browser_six_cycles_stability",
            "frontend_largest_chunk_under_vite_advisory",
            "lazy_chunk_recovery_verified",
        ):
            self.assertTrue(any(expected in item for item in evaluation["application_failures"]))

    def test_rejects_null_sessions_in_idle_samples(self) -> None:
        report = _valid_report()
        for sample_item in report["browser"]["idle"]:
            sample_item["sessions"] = None
        evaluation = comprehensive.evaluate_report(report)
        self.assertEqual(evaluation["application_status"], "failed")
        self.assertTrue(
            any(
                "browser_idle_120s_stability" in item for item in evaluation["application_failures"]
            )
        )

    def test_post_mutation_integrity_allows_audit_growth_and_rejects_domain_drift(self) -> None:
        report = _valid_report()
        manifest = report["environment"]["manifest"]
        expected = dict(manifest["table_counts"])
        with_audit = dict(expected)
        with_audit["operation_receipts"] += 1
        report["api"]["fixture_integrity_after_mutation"] = (
            comprehensive.evaluate_post_mutation_integrity(
                expected_counts=expected,
                post_counts=with_audit,
                expected_canonical_places=manifest["canonical_geographic_places"],
                post_canonical_places=manifest["canonical_geographic_places"],
                expected_schema_revision=manifest["schema_revision"],
                post_schema_revision=manifest["schema_revision"],
                created_identity_deleted=True,
                residual_perf_records=0,
                media_verify_output=(
                    f"Verified {expected['attachments']} stored attachment file(s)"
                ),
                expected_attachments=expected["attachments"],
            )
        )
        self.assertEqual(comprehensive.evaluate_report(report)["invariant_status"], "passed")

        drifted = dict(expected)
        drifted["botanical_identities"] += 1
        report["api"]["fixture_integrity_after_mutation"] = (
            comprehensive.evaluate_post_mutation_integrity(
                expected_counts=expected,
                post_counts=drifted,
                expected_canonical_places=manifest["canonical_geographic_places"],
                post_canonical_places=manifest["canonical_geographic_places"],
                expected_schema_revision=manifest["schema_revision"],
                post_schema_revision=manifest["schema_revision"],
                created_identity_deleted=False,
                residual_perf_records=1,
                media_verify_output=(
                    f"Verified {expected['attachments']} stored attachment file(s)"
                ),
                expected_attachments=expected["attachments"],
            )
        )
        drifted_eval = comprehensive.evaluate_report(report)
        self.assertEqual(drifted_eval["invariant_status"], "failed")
        self.assertTrue(
            any(
                "fixture_post_mutation_integrity_verified" in item
                for item in drifted_eval["harness_failures"]
            )
        )

    def test_summarize_report_compacts_raw_data_and_stays_evaluable(self) -> None:
        full_report = _valid_report()
        full_report["profile_summary"] = "large profile" * 100
        full_report["query_plans"] = {"seeds": [{"plan": {}}], "recent_events": [], "geography": []}
        summary = comprehensive.summarize_report(
            full_report,
            full_artifact={
                "sha256": "a" * 64,
                "bytes": 788494,
                "external_location": "$XDG_STATE_HOME/florabase/perf-evidence/test-full.json",
            },
        )
        self.assertNotIn("statements", summary["api"])
        self.assertNotIn("query_plans", summary)
        self.assertTrue(summary["api"]["statements_externalized"])
        self.assertEqual(summary["evaluation"]["invariant_status"], "passed")
        self.assertEqual(summary["evaluation"]["harness_status"], "passed")


class LifecycleAndCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_lock_dir = tempfile.TemporaryDirectory(prefix="florabase-test-locks-")
        self._env_patch = patch.dict(os.environ, {"FLORABASE_LOCK_DIR": self._tmp_lock_dir.name})
        self._env_patch.start()

    def tearDown(self) -> None:
        self._env_patch.stop()
        self._tmp_lock_dir.cleanup()

    def test_rejected_foreign_project_performs_zero_destructive_calls(self) -> None:
        foreign_config = json.dumps(
            {
                "name": "florabase-perf",
                "services": {"db": {"tmpfs": ["/t"]}, "backend": {"tmpfs": ["/t"]}},
            }
        )
        with (
            patch.object(
                measure, "compose", side_effect=[foreign_config, "foreign-ctr-id"]
            ) as compose_mock,
            patch.object(measure, "_stop_owned") as stop_mock,
            patch.object(measure, "_docker_output") as docker_mock,
        ):
            report = measure.run_rehearsal(warmup_s=0)
        stop_mock.assert_not_called()
        docker_mock.assert_not_called()
        self.assertEqual(compose_mock.call_count, 2)
        self.assertTrue(any("already exist" in err for err in report["errors"]))
        self.assertIsNone(report["cleanup"])
        self.assertEqual(report["evaluation"]["harness_status"], "incomplete")

    def test_stop_owned_refuses_foreign_container_without_down_or_rmi(self) -> None:
        foreign_inspect = {"Config": {"Labels": {measure.OWNER_LABEL: "foreign-owner-999"}}}
        with (
            patch.object(
                measure,
                "_docker_lines",
                side_effect=[["ctr-foreign"], [], []],
            ),
            patch.object(measure, "_docker_inspect_one", return_value=foreign_inspect),
            patch.object(measure, "compose") as compose_mock,
            patch.object(measure, "_docker_output") as docker_out_mock,
        ):
            with self.assertRaisesRegex(RuntimeError, "Refusing cleanup.*foreign or unowned"):
                measure._stop_owned(owner_id="my-owner-123")
        compose_mock.assert_not_called()
        docker_out_mock.assert_not_called()

    def test_partial_startup_failure_and_strict_rejection_clean_only_owned_before_measured_stages(
        self,
    ) -> None:
        stop_result = {
            "project": "florabase-perf",
            "ownership_verified": True,
            "containers_remaining": 0,
            "networks_remaining": 0,
            "volumes_remaining": 0,
            "images_remaining": 0,
        }

        def fake_partial_start(*, pin_mode: str, build_images: bool, invocation: Any) -> Any:
            self.assertEqual(pin_mode, comprehensive.PIN_MODE_STRICT)
            invocation.images_built = True
            invocation.owns_resources = True
            raise comprehensive.FixtureValidationError("strict pin violation (strict)")

        with (
            patch.object(measure, "start", side_effect=fake_partial_start),
            patch.object(measure, "api") as api_mock,
            patch.object(measure, "_stop_owned", return_value=stop_result) as stop_mock,
        ):
            report = measure.run_rehearsal(warmup_s=0)
        api_mock.assert_not_called()
        stop_mock.assert_called_once()
        kwargs = stop_mock.call_args.kwargs
        self.assertIsNotNone(kwargs["owner_id"])
        self.assertEqual(len(kwargs["image_tags"]), 2)
        self.assertTrue(any("strict pin violation" in err for err in report["errors"]))
        self.assertEqual(report["cleanup"], stop_result)

    def test_failure_after_owned_resources_always_stops_owned(self) -> None:
        stop_result = {
            "project": "florabase-perf",
            "ownership_verified": True,
            "containers_remaining": 0,
            "networks_remaining": 0,
            "volumes_remaining": 0,
            "images_remaining": 0,
        }

        def fake_start(*, pin_mode: str, build_images: bool, invocation: Any) -> dict[str, Any]:
            invocation.images_built = True
            invocation.owns_resources = True
            return {"manifest": _valid_manifest(pin_mode=pin_mode), "pin_mode": pin_mode}

        with (
            patch.object(measure, "start", side_effect=fake_start),
            patch.object(measure, "api", side_effect=RuntimeError("simulated api failure")),
            patch.object(measure, "_stop_owned", return_value=stop_result) as stop_mock,
        ):
            report = measure.run_rehearsal(warmup_s=0)
        stop_mock.assert_called_once()
        self.assertEqual(report["errors"], ["RuntimeError: simulated api failure"])
        self.assertEqual(report["evaluation"]["harness_status"], "incomplete")

    def test_interrupted_execution_unwinds_owned_cleanup_and_restores_signal_handlers(self) -> None:
        stop_result = {
            "project": "florabase-perf",
            "ownership_verified": True,
            "containers_remaining": 0,
            "networks_remaining": 0,
            "volumes_remaining": 0,
            "images_remaining": 0,
        }
        prev_int = signal.getsignal(signal.SIGINT)
        prev_term = signal.getsignal(signal.SIGTERM)

        def fake_start(*, pin_mode: str, build_images: bool, invocation: Any) -> dict[str, Any]:
            invocation.owns_resources = True
            raise KeyboardInterrupt("SIGINT during startup")

        with (
            patch.object(measure, "start", side_effect=fake_start),
            patch.object(measure, "_stop_owned", return_value=stop_result) as stop_mock,
        ):
            report = measure.run_rehearsal(warmup_s=0)
        stop_mock.assert_called_once()
        self.assertEqual(signal.getsignal(signal.SIGINT), prev_int)
        self.assertEqual(signal.getsignal(signal.SIGTERM), prev_term)
        self.assertTrue(any("KeyboardInterrupt" in err for err in report["errors"]))

    def test_repeated_stop_owned_is_idempotent_and_never_touches_foreign_tags(self) -> None:
        owner = "owner-abc"
        owned_ctr = {"Config": {"Labels": {measure.OWNER_LABEL: owner}}}
        owned_net = {"Labels": {measure.OWNER_LABEL: owner}}
        owned_img = {
            "Config": {"Labels": {measure.OWNER_LABEL: owner}},
            "RepoTags": [f"florabase-perf-backend:{owner}", "florabase-perf-backend:latest"],
        }

        def fake_inspect(kind: str, identifier: str) -> dict[str, Any]:
            if kind == "containers":
                return owned_ctr
            if kind == "networks":
                return owned_net
            if identifier.startswith("removed:"):
                raise measure.subprocess.CalledProcessError(1, "docker image inspect")
            return owned_img

        removed: set[str] = set()

        def fake_docker_output(*args: str) -> str:
            if args[:2] == ("image", "rm"):
                removed.add(args[2])
            return ""

        inspect_calls = 0

        def fake_inspect_seq(kind: str, identifier: str) -> dict[str, Any]:
            nonlocal inspect_calls
            inspect_calls += 1
            if kind == "images" and identifier in removed:
                raise measure.subprocess.CalledProcessError(1, "docker image inspect")
            return fake_inspect(kind, identifier)

        with (
            patch.object(
                measure,
                "_docker_lines",
                side_effect=[
                    ["ctr-1"],
                    ["net-1"],
                    [],  # first verify
                    [],
                    [],
                    [],
                    [],  # first remaining
                    [],
                    [],
                    [],  # second verify (already empty)
                    [],
                    [],
                    [],
                    [],  # second remaining
                ],
            ),
            patch.object(measure, "_docker_inspect_one", side_effect=fake_inspect_seq),
            patch.object(measure, "compose", return_value="") as compose_mock,
            patch.object(measure, "_docker_output", side_effect=fake_docker_output),
        ):
            first = measure._stop_owned(
                owner_id=owner,
                image_tags=(f"florabase-perf-backend:{owner}", f"florabase-perf-frontend:{owner}"),
            )
            second = measure._stop_owned(
                owner_id=owner,
                image_tags=(f"florabase-perf-backend:{owner}", f"florabase-perf-frontend:{owner}"),
            )
        compose_mock.assert_called_once_with("down")
        self.assertTrue(all(f":{owner}" in tag for tag in removed))
        self.assertFalse(any(":latest" in tag for tag in removed))
        self.assertEqual(first["containers_remaining"], 0)
        self.assertEqual(second["containers_remaining"], 0)
        self.assertEqual(second["images_removed"], [])
        self.assertEqual(second["compose_down_output"], "")

    def test_invocation_override_uses_unique_tags_never_latest(self) -> None:
        inv = measure.PerfInvocation(owner_id="inv001", source="/repo", source_head="deadbeef")
        with tempfile.TemporaryDirectory(prefix="perf-override-test-") as tmp:
            path = measure._write_invocation_override(inv, Path(tmp))
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        self.assertEqual(data["services"]["backend"]["image"], "florabase-perf-backend:inv001")
        self.assertEqual(data["services"]["frontend"]["image"], "florabase-perf-frontend:inv001")
        self.assertEqual(
            data["services"]["backend"]["build"]["labels"][measure.REVISION_LABEL], "deadbeef"
        )
        self.assertNotIn(":latest", raw)

    def test_standalone_start_cleans_owned_resources_on_partial_startup_failure(self) -> None:
        clean_config = json.dumps(
            {
                "name": "florabase-perf",
                "services": {"db": {"tmpfs": ["/t"]}, "backend": {"tmpfs": ["/t"]}},
            }
        )

        def fake_partial_build(*, invocation: Any, pin_mode: str, build_images: bool) -> Any:
            invocation.images_built = True
            invocation.owns_resources = True
            raise RuntimeError("simulated db restore failure")

        with (
            patch.object(measure, "compose", side_effect=[clean_config, ""]),
            patch.object(measure, "_existing_project_networks", return_value=[]),
            patch.object(measure, "_build_and_start_services", side_effect=fake_partial_build),
            patch.object(
                measure, "_stop_owned", return_value={"containers_remaining": 0}
            ) as stop_mock,
        ):
            with self.assertRaisesRegex(RuntimeError, "simulated db restore failure"):
                measure.start()
        stop_mock.assert_called_once()
        self.assertEqual(len(stop_mock.call_args.kwargs["image_tags"]), 2)

    def test_provision_retires_golden_copy_on_validation_failure(self) -> None:
        fake_owner = MagicMock()
        fake_owner.project = "florabase-integration-abcdef123456"
        fake_disposable = MagicMock()
        fake_disposable.__enter__.return_value = fake_disposable
        fake_disposable.resources.inventory.return_value = {
            "containers": [
                {
                    "Id": "runner-123",
                    "Config": {"Labels": {"com.docker.compose.service": "tests"}},
                }
            ]
        }

        def fake_run_checked(argv: list[str], **_: Any) -> str:
            if "verify-baseline" in argv:
                raise comprehensive.FixtureValidationError("baseline modified")
            return "{}"

        retire_calls: list[list[str]] = []

        def fake_subprocess_run(argv: list[str], **_: Any) -> MagicMock:
            retire_calls.append(argv)
            return MagicMock(returncode=0)

        with (
            patch("workflow_resources.Owner.disposable", return_value=fake_owner),
            patch.object(comprehensive, "Disposable", return_value=fake_disposable),
            patch.object(
                comprehensive,
                "compose_invocation",
                return_value=(["docker", "compose"], {}),
            ),
            patch.object(comprehensive, "_run_checked", side_effect=fake_run_checked),
            patch("subprocess.run", side_effect=fake_subprocess_run),
        ):
            with self.assertRaisesRegex(comprehensive.FixtureValidationError, "baseline modified"):
                comprehensive.provision_comprehensive_bundle(ROOT)

        self.assertTrue(
            any("retire-copy" in argv and "golden_perf" in argv for argv in retire_calls)
        )


if __name__ == "__main__":
    unittest.main()
