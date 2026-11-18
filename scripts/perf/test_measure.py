"""Unit tests for PERF-001 isolation guards, COMPREHENSIVE manifest validation, evaluation and cleanup."""

from __future__ import annotations

import importlib.util
import json
import sys
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


def _valid_manifest() -> dict[str, Any]:
    pin = comprehensive.expected_comprehensive_pin()
    targets = _sample_targets()
    ledger = _sample_ledger(targets, pin)
    return comprehensive.validate_fixture_manifest(
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
    )


def _valid_report() -> dict[str, Any]:
    manifest = _valid_manifest()
    session_state = {
        "count": 1,
        "last_seen_at": "2026-11-18T00:00:00Z",
        "idle_expires_at": "2026-11-19T00:00:00Z",
    }
    return {
        "environment": {"manifest": manifest},
        "api": {
            "reads": {"/dashboard": {"first_ms": 12.0, "median_ms": 8.0, "queries": [5]}},
            "create_edit_delete_ms": 15.0,
        },
        "transfer": {
            "static_assets": {"/assets/index-abc.js": {"raw_bytes": 1000, "gzip_bytes": 400}},
            "runtime_configuration": {"compressed": False},
            "health": {"compressed": False},
            "protected_api_compressed": False,
        },
        "browser": {
            "errors": [],
            "workload": [
                {"name": "today", "external": 0, "maps": 0},
                {"name": "occurrence", "external": 0, "maps": 1},
            ],
            "cycles": [{"maps": 0, "timers": {"intervals": 2, "timeouts": 0}} for _ in range(7)],
            "cycleRequests": [140, 120, 120, 120, 120, 120],
            "idleSeconds": 120,
            "idleRequests": [],
            "idle": [{"sessions": session_state} for _ in range(13)],
            "resources": [{"path": "/assets/index-abc.js", "bytes": 210_000, "transfer": 70_000}],
        },
        "chunk_recovery": {
            "stale_asset_path": "/assets/PERF-review-stale-chunk.js",
            "nginx_fallback": {"status": 200, "contentType": "text/html"},
            "shell_retained": True,
            "automatic_reload": False,
            "page_errors": [],
        },
        "cleanup": {"containers_remaining": 0, "networks_remaining": 0, "volumes_remaining": 0},
    }


class IsolationTests(unittest.TestCase):
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

    def test_rejects_existing_project_without_replacing_data(self) -> None:
        with patch.object(
            measure,
            "compose",
            side_effect=[json.dumps(self.config()), "existing-container"],
        ) as compose:
            with self.assertRaisesRegex(RuntimeError, "already exist"):
                measure.start()
            self.assertEqual(compose.call_count, 2)
            compose.assert_called_with("ps", "--all", "-q")

    def test_rejects_wrong_project(self) -> None:
        config = self.config()
        config["name"] = "florabase"
        with patch.object(measure, "compose", return_value=json.dumps(config)) as compose:
            with self.assertRaisesRegex(RuntimeError, "Unexpected project"):
                measure.start()
            self.assertEqual(compose.call_count, 1)

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
    def test_validates_pinned_comprehensive_manifest(self) -> None:
        manifest = _valid_manifest()
        self.assertTrue(manifest["valid"])
        self.assertEqual(manifest["profile"], "comprehensive")
        self.assertEqual(manifest["baseline_state"], "baseline-verified")
        self.assertEqual(manifest["differences_from_pin"], [])
        self.assertEqual(len(manifest["targets"]), len(comprehensive.MANIFEST_SCENARIO_KEYS) + 1)

    def test_rejects_schema_revision_mismatch(self) -> None:
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
                media_verify_output=(
                    f"Verified {pin['tables']['attachments']} stored attachment file(s)"
                ),
                expected_pin=pin,
                source_code_head=pin["baseline"]["schema_revision"],
            )

    def test_rejects_canonical_digest_mismatch(self) -> None:
        pin = comprehensive.expected_comprehensive_pin()
        targets = _sample_targets()
        ledger = _sample_ledger(targets, pin)
        with self.assertRaisesRegex(
            comprehensive.FixtureValidationError, "canonical_sha256 mismatch"
        ):
            comprehensive.validate_fixture_manifest(
                ledger=ledger,
                verify_baseline={"state": "baseline-verified"},
                digest={"canonical_sha256": "0" * 64},
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

    def test_rejects_table_count_mismatch(self) -> None:
        pin = comprehensive.expected_comprehensive_pin()
        targets = _sample_targets()
        ledger = _sample_ledger(targets, pin)
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
                media_verify_output=(
                    f"Verified {pin['tables']['attachments']} stored attachment file(s)"
                ),
                expected_pin=pin,
                source_code_head=pin["baseline"]["schema_revision"],
            )

    def test_rejects_missing_target_scenario_key(self) -> None:
        targets = _sample_targets()
        pin = comprehensive.expected_comprehensive_pin()
        ledger = _sample_ledger(targets, pin)
        del ledger["records"][comprehensive.MANIFEST_SCENARIO_KEYS["cutting_lot"]]
        with self.assertRaisesRegex(
            comprehensive.FixtureValidationError, "missing required scenario"
        ):
            comprehensive.resolve_targets(ledger["records"])

    def test_rejects_unverified_media(self) -> None:
        pin = comprehensive.expected_comprehensive_pin()
        targets = _sample_targets()
        ledger = _sample_ledger(targets, pin)
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

    def test_records_invariant_valid_baseline_drift_when_allowed(self) -> None:
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
                f"Verified {pin['tables']['attachments']} stored attachment file(s) "
                "against database metadata\n"
            ),
            expected_pin=pin,
            source_code_head=pin["baseline"]["schema_revision"],
            allow_baseline_drift=True,
        )
        self.assertTrue(manifest["valid"])
        self.assertFalse(manifest["baseline_pin_matches"])
        self.assertEqual(manifest["baseline_state"], "invariant-valid-baseline-modified")
        self.assertEqual(len(manifest["differences_from_pin"]), 2)

    def test_load_validated_manifest_rejects_unvalidated_manifest(self) -> None:
        with patch.object(
            measure,
            "compose",
            return_value=json.dumps({"valid": False, "profile": "smoke", "targets": {}}),
        ):
            with self.assertRaisesRegex(comprehensive.FixtureValidationError, "missing valid"):
                measure._load_validated_manifest()


class ReportEvaluationTests(unittest.TestCase):
    def test_passes_complete_valid_rehearsal(self) -> None:
        evaluation = comprehensive.evaluate_report(_valid_report())
        self.assertEqual(evaluation["execution_stage"], "preliminary_source_rehearsal")
        self.assertFalse(evaluation["rc_g_perf_certification"])
        self.assertEqual(evaluation["harness_status"], "passed")
        self.assertEqual(evaluation["invariant_status"], "passed")
        self.assertEqual(evaluation["failures"], [])
        self.assertEqual(evaluation["operator_g_perf_thresholds"]["status"], "unset_until_g_perf")

    def test_flags_missing_sections_and_missing_api_metrics(self) -> None:
        report = _valid_report()
        del report["browser"]
        report["api"]["reads"]["/dashboard"] = {"first_ms": 10.0}
        evaluation = comprehensive.evaluate_report(report)
        self.assertEqual(evaluation["harness_status"], "incomplete")
        self.assertEqual(evaluation["invariant_status"], "failed")
        self.assertIn("browser", evaluation["missing_sections"])
        self.assertTrue(any("api_measurements_complete" in item for item in evaluation["failures"]))

    def test_flags_oversized_chunk_against_vite_advisory(self) -> None:
        report = _valid_report()
        report["browser"]["resources"].append(
            {"path": "/assets/huge.js", "bytes": 550_000, "transfer": 200_000}
        )
        evaluation = comprehensive.evaluate_report(report)
        self.assertEqual(evaluation["invariant_status"], "failed")
        self.assertTrue(
            any(
                "frontend_largest_chunk_under_vite_advisory" in item
                for item in evaluation["failures"]
            )
        )

    def test_flags_idle_requests_and_map_leaks(self) -> None:
        report = _valid_report()
        report["browser"]["idleRequests"] = [{"path": "/api/v1/dashboard", "method": "GET"}]
        report["browser"]["cycles"][3]["maps"] = 1
        evaluation = comprehensive.evaluate_report(report)
        self.assertEqual(evaluation["invariant_status"], "failed")
        self.assertTrue(
            any("browser_idle_120s_stability" in item for item in evaluation["failures"])
        )
        self.assertTrue(
            any("browser_six_cycles_stability" in item for item in evaluation["failures"])
        )

    def test_flags_timer_growth_and_unbounded_request_growth(self) -> None:
        report = _valid_report()
        report["browser"]["cycles"][4]["timers"]["intervals"] = 3
        report["browser"]["cycleRequests"] = [38, 38, 42, 46, 50, 54]
        evaluation = comprehensive.evaluate_report(report)
        self.assertEqual(evaluation["invariant_status"], "failed")
        self.assertTrue(
            any("browser_six_cycles_stability" in item for item in evaluation["failures"])
        )

    def test_flags_chunk_recovery_failure(self) -> None:
        report = _valid_report()
        report["chunk_recovery"]["automatic_reload"] = True
        evaluation = comprehensive.evaluate_report(report)
        self.assertEqual(evaluation["invariant_status"], "failed")
        self.assertTrue(
            any("lazy_chunk_recovery_verified" in item for item in evaluation["failures"])
        )


class LifecycleAndCleanupTests(unittest.TestCase):
    def test_run_rehearsal_always_stops_perf_containers_on_failure(self) -> None:
        stop_result = {"containers_remaining": 0, "networks_remaining": 0, "volumes_remaining": 0}
        with (
            patch.object(measure, "start", return_value={"manifest": _valid_manifest()}),
            patch.object(measure, "api", side_effect=RuntimeError("simulated api failure")),
            patch.object(measure, "compose", return_value="container-id"),
            patch.object(measure, "stop", return_value=stop_result) as stop_mock,
        ):
            report = measure.run_rehearsal(warmup_s=0)
        stop_mock.assert_called_once()
        self.assertEqual(report["errors"], ["RuntimeError: simulated api failure"])
        self.assertEqual(report["evaluation"]["harness_status"], "incomplete")

    def test_stop_verifies_zero_remaining_resources(self) -> None:
        with (
            patch.object(measure, "compose", return_value="") as compose_mock,
            patch.object(measure.subprocess, "check_output", return_value="") as docker_mock,
        ):
            result = measure.stop()
        compose_mock.assert_called_once_with("down")
        self.assertEqual(docker_mock.call_count, 3)
        self.assertEqual(result["containers_remaining"], 0)
        self.assertEqual(result["networks_remaining"], 0)
        self.assertEqual(result["volumes_remaining"], 0)

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
        exec_calls: list[list[str]] = []

        def fake_run_checked(argv: list[str], **_: Any) -> str:
            exec_calls.append(argv)
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
