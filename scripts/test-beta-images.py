#!/usr/bin/env python3
"""Adversarial release-identity and publication-boundary regressions, without Docker."""

from __future__ import annotations

import copy
import importlib.util
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import Any

from beta_release import check_platform, inputs, validate_manifest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("checks", ROOT / "scripts/beta-release-checks.py")
assert spec and spec.loader
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


def approved() -> dict[str, Any]:
    return {
        "status": "approved",
        "candidate_platform": "linux/amd64",
        "operator": "fixture-operator",
        "screened_at": "2026-11-03",
        "evidence": ["fixture-only"],
        "host": {
            "identity": "fixture-only",
            "os": "linux",
            "architecture": "amd64",
            "runtime": "docker",
            "engine_version": "29.0.0",
            "compose_version": "2.40.0",
        },
    }


def candidate() -> dict[str, Any]:
    locked = inputs(ROOT)
    ref = "ghcr.io/alessandrorossato/florabase-backend@sha256:" + "a" * 64
    image = {
        "reference": ref,
        "index_digest": "sha256:" + "a" * 64,
        "platform_digest": "sha256:" + "b" * 64,
        "platform": "linux/amd64",
    }
    return {
        "schema_version": 1,
        "distribution": "registry-candidate",
        "version": locked["version"],
        "source": {
            "url": "https://github.com/alessandrorossato/florabase",
            "revision": "c" * 40,
            "dirty": False,
        },
        "platforms": ["linux/amd64"],
        "alembic_head": "20261013_0042",
        "images": {
            "backend": image,
            "frontend": {**image, "reference": ref.replace("backend", "frontend")},
        },
        "postgresql": locked["postgresql"],
        "build_inputs": locked,
        "workflow": {"run_id": "1", "run_attempt": "1"},
    }


class ReleaseTests(unittest.TestCase):
    def test_current_candidate_inputs_and_pending_publication(self) -> None:
        self.assertEqual(inputs(ROOT)["version"], "0.1.0-beta.1")
        with self.assertRaisesRegex(ValueError, "PUBLICATION BLOCKED"):
            check_platform({"status": "pending"})

    def test_host_screen_requires_every_piece_of_intended_host_evidence(self) -> None:
        check_platform(approved())
        for key in ("status", "candidate_platform", "operator", "screened_at", "evidence", "host"):
            with self.subTest(key=key):
                value = approved()
                del value[key]
                with self.assertRaises(ValueError):
                    check_platform(value)
        for key in approved()["host"]:
            with self.subTest(host=key):
                value = approved()
                del value["host"][key]
                with self.assertRaises(ValueError):
                    check_platform(value)

    def test_unsupported_hosts_and_compose_v1_refuse(self) -> None:
        for key, invalid in (
            ("os", "windows"),
            ("architecture", "arm64"),
            ("runtime", "podman"),
            ("compose_version", "1.29.2"),
        ):
            value = approved()
            value["host"][key] = invalid
            with self.subTest(key=key), self.assertRaises(ValueError):
                check_platform(value)

    def test_immutable_manifest_and_mutations(self) -> None:
        valid = candidate()
        validate_manifest(valid)
        mutations = [
            ("platforms", ["linux/arm64"]),
            ("schema_version", 2),
            ("version", "latest"),
            ("distribution", "local-candidate"),
        ]
        for field, invalid in mutations:
            changed = copy.deepcopy(valid)
            changed[field] = invalid
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_manifest(changed)
        for field, invalid in (
            ("reference", "ghcr.io/example/backend:latest"),
            ("index_digest", "sha256:" + "f" * 64),
            ("platform_digest", "bad"),
            ("platform", "linux/arm64"),
        ):
            changed = copy.deepcopy(valid)
            changed["images"]["backend"][field] = invalid
            with self.subTest(image=field), self.assertRaises(ValueError):
                validate_manifest(changed)
        for field, invalid in (
            ("reference", "postgres:18.6-alpine"),
            ("platform_digest", "bad"),
            ("platform", "linux/arm64"),
        ):
            changed = copy.deepcopy(valid)
            changed["postgresql"][field] = invalid
            with self.subTest(postgres=field), self.assertRaises(ValueError):
                validate_manifest(changed)

    def test_dirty_or_inconsistent_release_metadata_refuses(self) -> None:
        for field, invalid in (("dirty", True), ("revision", "not-a-commit")):
            value = candidate()
            value["source"][field] = invalid
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_manifest(value)
        value = candidate()
        value["build_inputs"]["version"] = "0.1.0-beta.99"
        with self.assertRaises(ValueError):
            validate_manifest(value)

    def test_local_evidence_cannot_claim_registry_pull_acceptance(self) -> None:
        value = candidate()
        value["distribution"] = "local-candidate"
        value["images"] = {
            name: {"reference": "sha256:" + "f" * 64, "platform": "linux/amd64"}
            for name in ("backend", "frontend")
        }
        validate_manifest(value, local=True)
        with self.assertRaises(ValueError):
            validate_manifest(value)

    def test_check_names_from_other_sources_or_commits_do_not_approve_release(self) -> None:
        sha = "c" * 40
        valid = [
            {
                "name": name,
                "head_sha": sha,
                "conclusion": "success",
                "app": {"slug": "github-actions"},
            }
            for name in ("quality", "integration", "build")
        ]
        self.assertTrue(checks.successful_checks(valid, sha))
        self.assertFalse(checks.successful_checks(valid[:2], sha))
        for field, invalid in (
            ("head_sha", "d" * 40),
            ("conclusion", "failure"),
            ("app", {"slug": "external"}),
        ):
            changed = copy.deepcopy(valid)
            changed[0][field] = invalid
            with self.subTest(field=field):
                self.assertFalse(checks.successful_checks(changed, sha))

    def test_interrupted_artifact_parent_allows_child_cleanup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="beta-child-cleanup-test-") as temporary:
            artifact = Path(temporary)
            (artifact / "smoke-beta-images.py").write_text(
                textwrap.dedent("""\
                import signal, time
                from pathlib import Path
                def cleanup(number, frame):
                    Path('cleaned').write_text('owned child cleanup completed')
                    raise SystemExit(128 + number)
                signal.signal(signal.SIGTERM, cleanup)
                Path('started').touch()
                while True:
                    time.sleep(0.1)
                """)
            )
            controller = (
                textwrap.dedent("""\
                import os, signal, sys, threading, time
                from pathlib import Path
                sys.path.insert(0, SCRIPTS)
                from beta_release import run_artifact_smoke
                artifact = Path(ARTIFACT)
                def interrupt(number, frame):
                    raise SystemExit(128 + number)
                signal.signal(signal.SIGTERM, interrupt)
                def send_signal():
                    deadline = time.monotonic() + 5
                    while not (artifact / 'started').exists():
                        if time.monotonic() >= deadline:
                            os.kill(os.getpid(), signal.SIGTERM)
                            return
                        time.sleep(0.01)
                    os.kill(os.getpid(), signal.SIGTERM)
                threading.Thread(target=send_signal, daemon=True).start()
                run_artifact_smoke(artifact, local=True)
                """)
                .replace("SCRIPTS", repr(str(ROOT / "scripts")))
                .replace("ARTIFACT", repr(str(artifact)))
            )
            result = subprocess.run([sys.executable, "-c", controller], check=False, timeout=10)
            self.assertEqual(result.returncode, 143)
            self.assertTrue((artifact / "cleaned").is_file())

    def test_no_automatic_release_trigger_and_least_privilege(self) -> None:
        workflow = (ROOT / ".github/workflows/beta-images.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("pull_request", workflow)
        self.assertNotIn("  push:", workflow)
        self.assertIn("environment: beta-release", workflow)
        self.assertIn("secrets.RELEASE_APPROVED_SHA", workflow)
        self.assertEqual(workflow.count("packages: write"), 1)
        self.assertIn("needs: verify", workflow)
        self.assertIn("--verify-tag", workflow)


if __name__ == "__main__":
    unittest.main()
