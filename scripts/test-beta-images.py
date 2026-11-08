#!/usr/bin/env python3
"""Adversarial release-identity and publication-boundary regressions, without Docker."""

from __future__ import annotations

import ast
import base64
import copy
import email.message
import hashlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import textwrap
import unittest
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Any
from unittest.mock import patch

import beta_release
from beta_release import (
    build_application_image,
    check_platform,
    inputs,
    install_bundle,
    read,
    registry_record,
    release_attestation_inputs,
    release_finalization_inputs,
    save_postgres_oci_evidence,
    saved_descriptors,
    validate_manifest,
    validate_release_assets,
    validate_scan,
)

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("checks", ROOT / "scripts/beta-release-checks.py")
assert spec and spec.loader
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


def load_tool(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tooling = load_tool("release-tools")
publisher = load_tool("publish-beta-images")


def policy() -> dict[str, Any]:
    return {
        "candidate_platform": "linux/amd64",
        "publication": {"host_approval_required": False},
        "deployment_acceptance": {"status": "pending"},
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
        "schema_version": 2,
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
            "frontend": {
                **image,
                "reference": ref.replace("backend", "frontend").replace("a" * 64, "d" * 64),
                "index_digest": "sha256:" + "d" * 64,
                "platform_digest": "sha256:" + "e" * 64,
            },
        },
        "postgresql": locked["postgresql"],
        "install_bundle": install_bundle(ROOT),
        "build_inputs": locked,
        "workflow": {"run_id": "1", "run_attempt": "1"},
    }


def ctl_bundle_names() -> tuple[str, ...]:
    source = (ROOT / "deploy/beta/florabasectl.py").read_text()
    match = re.search(r"^INSTALL_BUNDLE = \(([^)]*)\)", source, re.MULTILINE)
    assert match is not None
    return tuple(re.findall(r'"([^"]+)"', match.group(1)))


class ReleaseTests(unittest.TestCase):
    def test_current_candidate_inputs_and_platform_policy(self) -> None:
        self.assertEqual(inputs(ROOT)["version"], "0.1.0-beta.3")
        self.assertEqual(
            inputs(ROOT)["buildkit"],
            "moby/buildkit:v0.34.2@sha256:c5f8862f52499773af85bc07695b2379ef08e8002352b0df2c4864c91d78dabe",
        )
        committed = json.loads((ROOT / "release/platform.json").read_text())
        check_platform(committed)
        inputs(ROOT, publication=True)
        # Publication does not depend on any host; actual-host acceptance is not claimed.
        self.assertEqual(committed["deployment_acceptance"]["status"], "pending")
        self.assertNotIn("host", committed)
        self.assertNotIn("operator", committed)

    def test_postgres_oci_evidence_hash_checks_index_manifest_and_config(self) -> None:
        config = json.dumps({"created": "2025-11-06T00:00:00Z"}, separators=(",", ":")).encode()
        config_digest = "sha256:" + hashlib.sha256(config).hexdigest()
        platform = {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {"digest": config_digest, "size": len(config)},
            "layers": [{"digest": "sha256:" + "a" * 64, "size": 42}],
        }
        platform_raw = json.dumps(platform, separators=(",", ":")).encode()
        platform_digest = "sha256:" + hashlib.sha256(platform_raw).hexdigest()
        index = {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.index.v1+json",
            "manifests": [
                {
                    "mediaType": "application/vnd.oci.image.manifest.v1+json",
                    "digest": platform_digest,
                    "size": len(platform_raw),
                    "platform": {"architecture": "amd64", "os": "linux"},
                }
            ],
        }
        index_raw = json.dumps(index, separators=(",", ":")).encode()
        index_digest = "sha256:" + hashlib.sha256(index_raw).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            with (
                patch(
                    "beta_release.subprocess.check_output",
                    side_effect=[index_raw + b"\n", platform_raw + b"\n"],
                ),
                patch(
                    "beta_release.run",
                    return_value=json.dumps({"digest": index_digest}),
                ),
                patch("beta_release.urllib.request.urlopen", return_value=FakeResponse(config, {})),
            ):
                save_postgres_oci_evidence(
                    "127.0.0.1:5055/florabase-postgres:18.6-alpine-florabase.1",
                    5055,
                    Path(temporary),
                )
            evidence = json.loads((Path(temporary) / "postgres-oci-evidence.json").read_text())
        self.assertEqual(evidence["index_digest"], index_digest)
        self.assertEqual(evidence["platform_digest"], platform_digest)
        self.assertEqual(evidence["configuration_digest"], config_digest)
        self.assertEqual(evidence["layer_descriptors"], platform["layers"])
        raw = evidence["raw_documents_base64"]
        self.assertEqual(base64.b64decode(raw["index"]), index_raw)
        self.assertEqual(base64.b64decode(raw["platform_manifest"]), platform_raw)
        self.assertEqual(base64.b64decode(raw["configuration"]), config)

    def test_production_build_keeps_disposable_registry_port_in_digest_reference(self) -> None:
        digest = "sha256:" + "a" * 64
        with tempfile.TemporaryDirectory() as temporary:
            metadata = Path(temporary) / "metadata.json"

            def build(*args: Any, **kwargs: Any) -> None:
                metadata.write_text(json.dumps({"containerimage.digest": digest}))

            with patch("beta_release.subprocess.run", side_effect=build) as invocation:
                reference = build_application_image(
                    ROOT,
                    "rehearsal-builder",
                    "backend",
                    "127.0.0.1:5055/alessandrorossato/florabase-backend:candidate",
                    "0.1.0-beta.3",
                    "c" * 40,
                    1762387200,
                    "scanner@sha256:" + "b" * 64,
                    metadata,
                )
        self.assertEqual(
            reference,
            "127.0.0.1:5055/alessandrorossato/florabase-backend@" + digest,
        )
        command = invocation.call_args.args[0]
        self.assertIn("--provenance=mode=max", command)
        self.assertIn("--target", command)
        self.assertEqual(command[command.index("--target") + 1], "runtime")

    def test_attestation_inputs_are_exact_immutable_subjects_without_creating_attestations(
        self,
    ) -> None:
        value = candidate()
        host = "127.0.0.1:5055"
        refs = {
            "backend": f"{host}/alessandrorossato/florabase-backend@sha256:{'a' * 64}",
            "frontend": f"{host}/alessandrorossato/florabase-frontend@sha256:{'d' * 64}",
            "postgresql": f"{host}/alessandrorossato/florabase-postgres@sha256:{'f' * 64}",
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "release-manifest.json"
            path.write_text(json.dumps(value))
            result = release_attestation_inputs(
                value,
                refs,
                path,
                value["source"]["revision"],
                ".github/workflows/beta-images.yml",
                value["install_bundle"],
                host,
            )
        self.assertEqual(result["source_sha"], value["source"]["revision"])
        self.assertEqual(set(result["subjects"]), {"backend", "frontend", "postgresql"})
        self.assertEqual(result["file_subjects"], value["install_bundle"])
        self.assertFalse(result["attestations_created"])
        with self.assertRaises(ValueError):
            release_attestation_inputs(
                value,
                {**refs, "backend": refs["backend"].replace("a" * 64, "z" * 64)},
                path,
                value["source"]["revision"],
                ".github/workflows/beta-images.yml",
                value["install_bundle"],
                host,
            )

    def test_rehearsal_uses_the_locked_postgres_repository_namespace(self) -> None:
        rehearsal = (ROOT / "scripts/rehearse-beta-release.py").read_text()
        builder = (ROOT / "scripts/beta_release.py").read_text()
        self.assertIn('locked["postgresql"]["repository"].removeprefix("ghcr.io/")', rehearsal)
        self.assertIn('pg["repository"].removeprefix("ghcr.io/")', builder)

    def test_release_finalization_inputs_match_protected_draft_request_without_api_call(
        self,
    ) -> None:
        value = candidate()
        sha = value["source"]["revision"]
        assets = {
            "RELEASE.md": (21, "sha256:" + "a" * 64),
            "compose.yaml": (42, "sha256:" + "b" * 64),
        }
        result = release_finalization_inputs(value, sha, assets)
        self.assertEqual(result["tag"], "v" + value["version"])
        self.assertEqual(result["target_commitish"], sha)
        self.assertTrue(result["draft"])
        self.assertTrue(result["prerelease"])
        self.assertTrue(result["verify_tag"])
        self.assertFalse(result["release_api_called"])
        self.assertEqual(result["release_notes_sha256"], assets["RELEASE.md"][1])
        with self.assertRaises(ValueError):
            release_finalization_inputs(value, "d" * 40, assets)
        with self.assertRaises(ValueError):
            release_finalization_inputs(value, sha, {"../RELEASE.md": assets["RELEASE.md"]})

    def test_platform_policy_requires_supported_platform_and_separate_deployment(self) -> None:
        check_platform(policy())
        accepted = policy()
        accepted["deployment_acceptance"]["status"] = "accepted"
        accepted["deployment_acceptance"]["evidence"] = [{"host": "h", "reference": "r"}]
        check_platform(accepted)
        invalid = []
        for key in ("candidate_platform", "publication", "deployment_acceptance"):
            value = policy()
            del value[key]
            invalid.append(value)
        for platform in ("linux/arm64", "windows/amd64", None):
            value = policy()
            value["candidate_platform"] = platform
            invalid.append(value)
        for required in (True, None, "false"):
            value = policy()
            value["publication"]["host_approval_required"] = required
            invalid.append(value)
        for status in ("", "approved", None):
            value = policy()
            value["deployment_acceptance"]["status"] = status
            invalid.append(value)
        bad_evidence: list[Any] = [
            None,
            [],
            "text",
            [{}],
            ["text"],
            [{"host": "h"}],
            [{"host": "h", "reference": " "}],
            [{"host": 1, "reference": "r"}],
            [{"host": "h", "reference": "r"}, {"host": "h"}],
        ]
        for evidence in bad_evidence:
            value = policy()
            value["deployment_acceptance"]["status"] = "accepted"
            if evidence is not None:
                value["deployment_acceptance"]["evidence"] = evidence
            invalid.append(value)
        for key in ("publication", "deployment_acceptance"):
            malformed_values: list[Any] = [None, [], "x", 1, True]
            for malformed in malformed_values:
                value = policy()
                value[key] = malformed
                invalid.append(value)
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "PUBLICATION BLOCKED"):
                    check_platform(value)

    def test_platform_file_missing_or_not_an_object_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "platform.json"
            with self.assertRaises(FileNotFoundError):
                read(path)
            for text in ("[]", '"x"', "1", "null", "{", ""):
                path.write_text(text)
                with self.subTest(text=text), self.assertRaises(ValueError):
                    check_platform(read(path))
            path.write_text("{}")
            with self.assertRaisesRegex(ValueError, "PUBLICATION BLOCKED"):
                check_platform(read(path))

    def test_immutable_manifest_and_mutations(self) -> None:
        valid = candidate()
        validate_manifest(valid)
        mutations = [
            ("platforms", ["linux/arm64"]),
            ("schema_version", 1),
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
            ("repository", "docker.io/library/postgres"),
            ("version", "18.6-alpine"),
            ("platform_digest", "bad"),
            ("platform", "linux/arm64"),
            ("source_date_epoch", "1762387200"),
        ):
            changed = copy.deepcopy(valid)
            changed["postgresql"][field] = invalid
            changed["build_inputs"]["postgresql"] = changed["postgresql"]
            with self.subTest(postgres=field), self.assertRaises(ValueError):
                validate_manifest(changed)
        for field, invalid in (
            ("repository", "ghcr.io/example/postgres"),
            ("index_digest", "sha256:" + "f" * 64),
            ("platform", "linux/arm64"),
        ):
            changed = copy.deepcopy(valid)
            changed["postgresql"]["upstream"][field] = invalid
            changed["build_inputs"]["postgresql"] = changed["postgresql"]
            with self.subTest(upstream=field), self.assertRaises(ValueError):
                validate_manifest(changed)
        for change in (
            {},
            {"compose.yaml": "sha256:" + "a" * 64},
            {**install_bundle(ROOT), "extra": "sha256:" + "a" * 64},
            {**install_bundle(ROOT), "florabasectl.py": "unpinned"},
        ):
            changed = copy.deepcopy(valid)
            changed["install_bundle"] = change
            with self.subTest(bundle=sorted(change)), self.assertRaises(ValueError):
                validate_manifest(changed)
        # The official image itself is no longer an acceptable release database identity.
        changed = copy.deepcopy(valid)
        changed["postgresql"] = dict(changed["postgresql"]["upstream"])
        with self.assertRaises(ValueError):
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
                "status": "completed",
            }
            for name in ("quality", "integration", "build")
        ]
        self.assertTrue(checks.approved_ci_jobs(valid, sha))
        self.assertFalse(checks.approved_ci_jobs(valid[:2], sha))
        for field, invalid in (
            ("head_sha", "d" * 40),
            ("conclusion", "failure"),
            ("status", "in_progress"),
        ):
            changed = copy.deepcopy(valid)
            changed[0][field] = invalid
            with self.subTest(field=field):
                self.assertFalse(checks.approved_ci_jobs(changed, sha))

    def test_canonical_ci_producer_identity(self) -> None:
        valid = {
            "path": ".github/workflows/ci.yml",
            "head_sha": "a" * 40,
            "head_branch": "main",
            "event": "push",
            "status": "completed",
            "conclusion": "success",
            "repository": {"full_name": "owner/repo"},
            "head_repository": {"full_name": "owner/repo"},
        }
        self.assertTrue(checks.approved_ci_run(valid, "a" * 40, "owner/repo"))
        for field in valid:
            changed = {**valid, field: None}
            with self.subTest(field=field):
                self.assertFalse(checks.approved_ci_run(changed, "a" * 40, "owner/repo"))
        self.assertFalse(
            checks.approved_ci_run(
                {**valid, "path": ".github/workflows/spoof.yml"}, "a" * 40, "owner/repo"
            )
        )

    def test_release_identity_refuses_before_registry_access(self) -> None:
        sha = "c" * 40
        valid = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_SHA": sha,
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_REPOSITORY": "alessandrorossato/florabase",
            "GITHUB_WORKFLOW_REF": "alessandrorossato/florabase/.github/workflows/beta-images.yml@refs/heads/main",
            "RUNNER_ENVIRONMENT": "github-hosted",
            "APPROVED_SHA": sha,
        }
        with (
            patch.dict(os.environ, valid, clear=True),
            patch.object(publisher, "run", return_value=""),
        ):
            publisher.require_publication_identity(sha)
            for field in valid:
                with (
                    self.subTest(field=field),
                    patch.dict(os.environ, {field: ""}),
                    self.assertRaises(ValueError),
                ):
                    publisher.require_publication_identity(sha)
        with (
            patch.dict(os.environ, valid, clear=True),
            patch.object(publisher, "run", return_value=" M file"),
            self.assertRaises(ValueError),
        ):
            publisher.require_publication_identity(sha)

    def test_failed_security_or_smoke_cannot_promote_a_pair(self) -> None:
        sha = "c" * 40
        environment = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_SHA": sha,
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_REPOSITORY": "alessandrorossato/florabase",
            "GITHUB_WORKFLOW_REF": "alessandrorossato/florabase/.github/workflows/beta-images.yml@refs/heads/main",
            "RUNNER_ENVIRONMENT": "github-hosted",
            "APPROVED_SHA": sha,
            "GITHUB_RUN_ID": "1",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_ACTOR": "fixture",
            "REGISTRY_TOKEN": "fixture-only",
        }

        def output(*args: str) -> str:
            if args[:2] == ("git", "rev-parse"):
                return sha
            if args[:2] == ("git", "status"):
                return ""
            return "0"

        def execute(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
            if "--metadata-file" in command:
                path = Path(command[command.index("--metadata-file") + 1])
                path.write_text(
                    json.dumps(
                        {
                            "containerimage.digest": "sha256:"
                            + ("a" if "backend" == command[-1] else "d") * 64
                        }
                    )
                )
            return subprocess.CompletedProcess(command, 0)

        for failing, phase in (
            ("local_postgres_identity", "preflight"),
            ("scan_images", "frontend_candidate_pushed"),
            ("run_artifact_smoke", "security_passed"),
        ):
            with self.subTest(failing=failing), tempfile.TemporaryDirectory() as temporary:
                target = Path(temporary) / "output"
                with (
                    patch.dict(os.environ, environment, clear=True),
                    patch.object(sys, "argv", ["publish", "--output", str(target)]),
                    patch.object(publisher, "inputs", return_value=inputs(ROOT)),
                    patch.object(publisher, "run", side_effect=output),
                    patch.object(publisher, "manifest", return_value=candidate()),
                    patch.object(publisher, "published_digest", return_value=None),
                    patch.object(publisher, "scan_images"),
                    patch.object(publisher, "run_artifact_smoke"),
                    patch.object(publisher, "software_bill_of_materials"),
                    patch.object(
                        publisher,
                        "local_postgres_identity",
                        return_value={
                            field: inputs(ROOT)["postgresql"][field]
                            for field in ("index_digest", "platform_digest")
                        },
                    ),
                    patch.object(
                        publisher, failing, side_effect=ValueError("fixture gate blocked")
                    ),
                    patch.object(publisher.subprocess, "run", side_effect=execute) as commands,
                ):
                    with self.assertRaisesRegex(ValueError, "fixture gate blocked"):
                        publisher.main()
                    self.assertEqual(
                        json.loads((target / "publication-state.json").read_text())["phase"], phase
                    )
                    self.assertFalse((target / "RELEASE.md").exists())
                    self.assertFalse(
                        any(
                            call.args[0][:4] == ["docker", "buildx", "imagetools", "create"]
                            for call in commands.call_args_list
                        )
                    )

    def test_scan_requires_complete_unsuppressed_exact_bytes(self) -> None:
        digest = "sha256:" + "a" * 64
        valid: dict[str, Any] = {
            "SchemaVersion": 2,
            "ArtifactType": "container_image",
            "Metadata": {"ImageID": digest},
            "Results": [{"Class": "os-pkgs", "Packages": [{"Name": "fixture"}]}],
        }
        validate_scan(valid, digest)
        for service in ("backend", "frontend", "postgresql"):
            with self.subTest(service=service), self.assertRaisesRegex(ValueError, "inventory"):
                validate_scan(valid, digest, service)
        for change in (
            {},
            {**valid, "Results": []},
            {**valid, "Metadata": {"ImageID": "wrong"}},
            {**valid, "Results": [{"Class": "os-pkgs"}]},
            {**valid, "ExperimentalModifiedFindings": ["ignored"]},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_scan(change, digest)
        for field in ("Secrets", "Vulnerabilities", "ExperimentalModifiedFindings"):
            changed = copy.deepcopy(valid)
            changed["Results"][0][field] = [{"Severity": "HIGH"}]
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_scan(changed, digest)

    def test_postgres_scan_requires_alpine_inventory_and_no_gosu(self) -> None:
        digest = "sha256:" + "a" * 64
        alpine = {
            "Class": "os-pkgs",
            "Type": "alpine",
            "Packages": [{"Name": name} for name in ("musl", "busybox", "libssl3", "tzdata")],
        }
        valid: dict[str, Any] = {
            "SchemaVersion": 2,
            "ArtifactType": "container_image",
            "Metadata": {"ImageID": digest},
            "Results": [alpine],
        }
        validate_scan(valid, digest, "postgresql")
        with_gosu = copy.deepcopy(valid)
        with_gosu["Results"].append(
            {
                "Target": "usr/local/bin/gosu",
                "Class": "lang-pkgs",
                "Type": "gobinary",
                "Packages": [{"Name": "stdlib"}],
            }
        )
        with self.assertRaisesRegex(ValueError, "gosu"):
            validate_scan(with_gosu, digest, "postgresql")
        partial = copy.deepcopy(valid)
        partial["Results"][0]["Packages"] = [{"Name": "musl"}]
        with self.assertRaisesRegex(ValueError, "inventory"):
            validate_scan(partial, digest, "postgresql")

    def test_postgres_inputs_bind_dockerfile_and_reproducible_pins(self) -> None:
        import beta_release

        pinned = inputs(ROOT)["postgresql"]
        self.assertEqual(pinned["repository"], beta_release.POSTGRES_REPOSITORY)
        self.assertEqual(pinned["upstream"]["repository"], "docker.io/library/postgres")
        dockerfile = (ROOT / "postgres/Dockerfile").read_text()
        self.assertIn("\nFROM " + pinned["upstream"]["reference"] + "\n", dockerfile)
        self.assertIn("    && rm /usr/local/bin/gosu \\\n", dockerfile)
        # The upstream entrypoint (sourced first by docker-ensure-initdb.sh) refuses root too.
        self.assertIn("sed -i '1a florabase-postgres-refuse-root || exit 64'", dockerfile)
        self.assertIn('= "florabase-postgres-refuse-root || exit 64"', dockerfile)
        self.assertIn("^source /usr/local/bin/docker-entrypoint.sh$", dockerfile)
        self.assertIn("USER 70:70\n", dockerfile)
        self.assertIn('ENTRYPOINT ["florabase-postgres-entrypoint"]', dockerfile)
        for drift in (
            dockerfile.replace(pinned["upstream"]["index_digest"], "sha256:" + "f" * 64, 1),
            dockerfile.replace('version="18.6-alpine-florabase.1"', 'version="other"'),
            dockerfile.replace("FROM ", "ARG BASE\nFROM ", 1),
        ):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                for path in (
                    "release/inputs.json",
                    "frontend/package.json",
                    "backend/src/florabase/__init__.py",
                    "backend/pyproject.toml",
                    "backend/Dockerfile",
                    "frontend/Dockerfile",
                    "LICENSE",
                    "backend/LICENSE",
                    "frontend/LICENSE",
                    "postgres/LICENSE",
                    "postgres/Dockerfile",
                ):
                    (root / path).parent.mkdir(parents=True, exist_ok=True)
                    (root / path).write_bytes((ROOT / path).read_bytes())
                inputs(root)
                (root / "postgres/Dockerfile").write_text(drift)
                with self.assertRaisesRegex(ValueError, "PostgreSQL Dockerfile|base image"):
                    inputs(root)
        beta_release.require_pinned_postgres(
            {"index_digest": pinned["index_digest"], "platform_digest": pinned["platform_digest"]},
            pinned,
        )
        with self.assertRaisesRegex(ValueError, "not reproducible"):
            beta_release.require_pinned_postgres(
                {
                    "index_digest": "sha256:" + "f" * 64,
                    "platform_digest": pinned["platform_digest"],
                },
                pinned,
            )

    def test_postgres_entrypoint_refuses_root_before_upstream_entrypoint(self) -> None:
        guard = ROOT / "postgres/florabase-postgres-entrypoint.sh"
        for uid, expected in (("0", 64), ("70", 0)):
            with self.subTest(uid=uid), tempfile.TemporaryDirectory() as temporary:
                bin_dir = Path(temporary)
                (bin_dir / "id").write_text(f"#!/bin/sh\necho {uid}\n")
                (bin_dir / "docker-entrypoint.sh").write_text(
                    '#!/bin/sh\necho upstream-entrypoint "$@" > "$MARKER"\n'
                )
                (bin_dir / "florabase-postgres-refuse-root").write_bytes(
                    (ROOT / "postgres/florabase-postgres-refuse-root.sh").read_bytes()
                )
                for name in ("id", "docker-entrypoint.sh", "florabase-postgres-refuse-root"):
                    (bin_dir / name).chmod(0o755)
                marker = bin_dir / "marker"
                result = subprocess.run(
                    ["/bin/sh", str(guard), "postgres"],
                    env={"PATH": f"{bin_dir}:/usr/bin:/bin", "MARKER": str(marker)},
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, expected)
                if uid == "0":
                    self.assertIn("refusing to run as root", result.stderr)
                    self.assertFalse(marker.exists(), "upstream entrypoint must not run as root")
                else:
                    self.assertEqual(marker.read_text(), "upstream-entrypoint postgres\n")

    def test_publication_attests_and_pins_postgres(self) -> None:
        workflow = (ROOT / ".github/workflows/beta-images.yml").read_text()
        self.assertIn("subject-digest: ${{ steps.pair.outputs.postgresql_digest }}", workflow)
        source = (ROOT / "scripts/publish-beta-images.py").read_text()
        self.assertIn("subject-path: |", workflow)
        for name in ("compose.yaml", "florabasectl.py", "florabase.env.example"):
            self.assertIn("${{ runner.temp }}/beta-release/" + name, workflow)
        # The rebuild check must not gate every release: the publisher runs it only for an
        # unpublished identity, so a superseded Alpine pin never blocks application releases.
        self.assertNotIn("postgres-identity --check", workflow)
        self.assertEqual(workflow.count("version: v0.38.1"), 2)
        # An unpublished identity is built and verified in a loopback registry before GHCR.
        self.assertLess(source.index("local_postgres_identity("), source.index("scan_images("))
        self.assertIn("destination=POSTGRES_REPOSITORY", source)
        # Existence is decided by registry manifest lookups, never by stderr text or the packages
        # REST API (which rejects the workflow's GITHUB_TOKEN with HTTP 400).
        self.assertNotIn("not found|manifest unknown", source)
        self.assertNotIn("/packages", source)
        self.assertLess(source.index("scan_images("), source.index("software_bill_of_materials("))
        self.assertLess(
            source.index("software_bill_of_materials("),
            source.index('checkpoint("security_passed")'),
        )
        self.assertLess(
            source.index("run_artifact_smoke("),
            source.index('checkpoint("postgresql_version_promoted")'),
        )
        self.assertIn('"postgresql": POSTGRES_REPOSITORY + "@" + pg["index_digest"]', source)

    def test_shared_or_symlinked_executable_cache_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cache = root / "cache"
            tooling.secure_cache(cache)
            self.assertEqual(cache.stat().st_mode & 0o777, 0o700)
            cache.chmod(0o777)
            with self.assertRaisesRegex(ValueError, "unsafe release cache"):
                tooling.secure_cache(cache)
            cache.chmod(0o700)
            link = root / "symlink"
            link.symlink_to(cache, target_is_directory=True)
            with self.assertRaises(ValueError):
                tooling.secure_cache(link)
            (cache / "lock").symlink_to(root / "victim")
            with self.assertRaises((ValueError, FileNotFoundError)):
                tooling.secure_cache(cache)
            (cache / "lock").unlink()
            (cache / "python").write_text("malicious executable")
            (cache / "python").chmod(0o777)
            with self.assertRaises(ValueError):
                tooling.secure_cache(cache)

    def test_authenticated_paginated_draft_lookup_and_id_revalidation(self) -> None:
        import beta_release

        self.assertTrue(
            hasattr(beta_release, "locate_draft_release"),
            "draft lookup must use listing and numeric ID",
        )
        tag, sha, repo = "v0.1.0-beta.1", "c" * 40, "alessandrorossato/florabase"
        draft = {
            "id": 42,
            "tag_name": tag,
            "draft": True,
            "target_commitish": sha,
            "url": f"https://api.github.com/repos/{repo}/releases/42",
            "assets": [],
        }

        def api(*args: str) -> str:
            if "/tags/" in args[-1]:
                raise subprocess.CalledProcessError(
                    1, args, stderr="404 published release not found"
                )
            if "--paginate" in args:
                self.assertIn("--slurp", args)
                return json.dumps([[{"tag_name": "unrelated"}], [draft]])
            self.assertEqual(args[-1], f"repos/{repo}/releases/42")
            return json.dumps(draft)

        with (
            patch.dict(os.environ, {"GH_TOKEN": "fixture"}),
            patch("beta_release.run", side_effect=api),
        ):
            self.assertEqual(beta_release.locate_draft_release(repo, tag, sha), draft)
        mutations = [
            {**draft, "id": 43},
            {**draft, "draft": False},
            {**draft, "tag_name": "stale"},
            {**draft, "target_commitish": "main"},
            {**draft, "url": "foreign"},
            {**draft, "assets": [{"id": 1, "state": "new"}]},
        ]
        for value in mutations:
            with (
                self.subTest(value=value),
                patch.dict(os.environ, {"GH_TOKEN": "fixture"}),
                patch("beta_release.run", side_effect=[json.dumps([[draft]]), json.dumps(value)]),
                self.assertRaises(ValueError),
            ):
                beta_release.locate_draft_release(repo, tag, sha)
        for pages in [[], [[]], [[draft], [draft]], [[{**draft, "draft": False}]]]:
            with (
                self.subTest(pages=pages),
                patch.dict(os.environ, {"GH_TOKEN": "fixture"}),
                patch("beta_release.run", return_value=json.dumps(pages)),
                self.assertRaises(ValueError),
            ):
                beta_release.locate_draft_release(repo, tag, sha)
        with (
            patch.dict(os.environ, {"GH_TOKEN": "fixture"}),
            patch("beta_release.run", side_effect=subprocess.CalledProcessError(1, "gh")),
            self.assertRaises(subprocess.CalledProcessError),
        ):
            beta_release.locate_draft_release(repo, tag, sha)

    def test_actual_workflow_draft_finalization_with_published_tag_404(self) -> None:
        repo, sha, tag = "alessandrorossato/florabase", "c" * 40, "v0.1.0-beta.1"
        workflow = (ROOT / ".github/workflows/beta-images.yml").read_text()
        code = textwrap.dedent(workflow.split("<<'PY'\n")[-1].split("          PY")[0])
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output / "fixture.json").write_bytes(b"fixture")
            release: dict[str, Any] = {
                "id": 42,
                "tag_name": tag,
                "draft": True,
                "target_commitish": sha,
                "url": f"https://api.github.com/repos/{repo}/releases/42",
                "assets": [
                    {
                        "id": 7,
                        "state": "uploaded",
                        "name": "fixture.json",
                        "size": 7,
                        "digest": "sha256:" + hashlib.sha256(b"fixture").hexdigest(),
                    }
                ],
            }
            for valid in (True, False):
                value = copy.deepcopy(release)
                if not valid:
                    value["assets"][0]["digest"] = "wrong"
                with (
                    patch.dict(
                        os.environ,
                        {"GH_TOKEN": "fixture", "GITHUB_REPOSITORY": repo, "GITHUB_SHA": sha},
                    ),
                    patch.object(sys, "argv", ["probe", temporary, tag]),
                    patch(
                        "beta_release.run",
                        side_effect=[json.dumps([[], [value]]), json.dumps(value)],
                    ),
                    patch(
                        "subprocess.check_output",
                        side_effect=subprocess.CalledProcessError(
                            1, "published-tag-lookup", stderr="404"
                        ),
                    ),
                    patch("subprocess.run") as mutation,
                ):
                    if valid:
                        exec(code, {})
                        self.assertEqual(
                            mutation.call_args.args[0][:5],
                            ["gh", "api", "--method", "PATCH", f"repos/{repo}/releases/42"],
                        )
                    else:
                        with self.assertRaises(ValueError):
                            exec(code, {})
                        mutation.assert_not_called()

    def test_draft_validation_and_promotion_order(self) -> None:
        source = (ROOT / "scripts/publish-beta-images.py").read_text()
        self.assertLess(
            source.index("prepare_release_assets(Path.cwd(), output"),
            source.index('"--prefer-index=false"'),
        )
        import beta_release

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output / "unexpected-directory").mkdir()
            with self.assertRaises(ValueError):
                beta_release.release_asset_inventory(output)
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("beta_release.run") as api,
            self.assertRaises(ValueError),
        ):
            beta_release.locate_draft_release(
                "alessandrorossato/florabase", "v0.1.0-beta.1", "c" * 40
            )
        api.assert_not_called()

    def test_install_bundle_is_attached_before_inventory_and_never_latest(self) -> None:
        source = (ROOT / "scripts/publish-beta-images.py").read_text()
        copy = source.index("prepare_release_assets(Path.cwd(), output")
        self.assertLess(copy, source.index('"--prefer-index=false"'))
        self.assertLess(copy, source.index('"--prefer-index=false"'))
        import beta_release

        names = list(beta_release.INSTALL_BUNDLE)
        self.assertEqual(names, ["compose.yaml", "florabasectl.py", "florabase.env.example"])
        # The controller pins the same names it verifies against the manifest.
        self.assertEqual(tuple(names), ctl_bundle_names())
        for name in names:
            self.assertTrue((ROOT / "deploy/beta" / name).is_file(), name)
        # Prerelease promotion writes only the exact version tag.
        self.assertNotIn(":latest", source)
        self.assertIn("promote_image(ref, version)", source)

    def test_workflow_draft_lookup_never_uses_published_tag_endpoint(self) -> None:
        workflow = (ROOT / ".github/workflows/beta-images.yml").read_text()
        self.assertNotIn("/releases/tags/", workflow)
        self.assertIn("locate_draft_release", workflow)
        self.assertIn('--target "$GITHUB_SHA"', workflow)
        self.assertIn('"--method", "PATCH"', workflow)

    def test_partial_or_wrong_release_assets_cannot_be_published(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output / "manifest.json").write_bytes(b"fixture")
            asset = {
                "name": "manifest.json",
                "size": 7,
                "digest": "sha256:" + hashlib.sha256(b"fixture").hexdigest(),
            }
            valid = {"draft": True, "assets": [asset]}
            validate_release_assets(valid, output)
            for change in (
                {"draft": False, "assets": [asset]},
                {"draft": True, "assets": []},
                {"draft": True, "assets": [{**asset, "digest": None}]},
                {"draft": True, "assets": [{**asset, "size": 0}]},
            ):
                with self.subTest(change=change), self.assertRaises(ValueError):
                    validate_release_assets(change, output)

    def test_saved_native_descriptor_is_bound_to_configuration(self) -> None:
        config = "sha256:" + "a" * 64
        native = json.dumps({"config": {"digest": config}}).encode()
        native_digest = "sha256:" + hashlib.sha256(native).hexdigest()
        index = json.dumps(
            {
                "manifests": [
                    {"digest": native_digest, "platform": {"os": "linux", "architecture": "amd64"}}
                ]
            }
        ).encode()
        index_digest = "sha256:" + hashlib.sha256(index).hexdigest()
        with tempfile.TemporaryFile() as data:
            with tarfile.open(fileobj=data, mode="w") as saved:
                for name, value in {
                    "index.json": json.dumps({"manifests": [{"digest": index_digest}]}).encode(),
                    "blobs/sha256/" + index_digest[7:]: index,
                    "blobs/sha256/" + native_digest[7:]: native,
                }.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(value)
                    saved.addfile(info, io.BytesIO(value))
            data.seek(0)
            with tarfile.open(fileobj=data) as saved:
                self.assertEqual(saved_descriptors(saved, config)["platform_digest"], native_digest)
                with self.assertRaisesRegex(ValueError, "identity mismatch"):
                    saved_descriptors(saved, "sha256:" + "b" * 64)

    def test_classic_registry_export_binds_native_config_without_oci_store(self) -> None:
        config = "sha256:" + "a" * 64
        native = json.dumps({"config": {"digest": config}}).encode()
        native_digest = "sha256:" + hashlib.sha256(native).hexdigest()
        index = json.dumps(
            {
                "manifests": [
                    {"digest": native_digest, "platform": {"os": "linux", "architecture": "amd64"}}
                ]
            }
        ).encode()
        index_digest = "sha256:" + hashlib.sha256(index).hexdigest()
        reference = "ghcr.io/owner/image@" + index_digest
        with tempfile.TemporaryFile() as data:
            with tarfile.open(fileobj=data, mode="w"):
                pass
            data.seek(0)
            with tarfile.open(fileobj=data) as saved:
                with patch(
                    "beta_release.subprocess.check_output",
                    side_effect=[index + b"\n", native + b"\n"],
                ):
                    self.assertEqual(
                        saved_descriptors(saved, config, reference)["platform_digest"],
                        native_digest,
                    )
                with (
                    patch("beta_release.subprocess.check_output", return_value=b"{}"),
                    self.assertRaisesRegex(ValueError, "digest mismatch"),
                ):
                    saved_descriptors(saved, config, reference)
                with (
                    patch("beta_release.subprocess.check_output", side_effect=[index, native]),
                    self.assertRaisesRegex(ValueError, "config identity mismatch"),
                ):
                    saved_descriptors(saved, "sha256:" + "b" * 64, reference)
                with self.assertRaisesRegex(ValueError, "OCI image store required"):
                    saved_descriptors(saved, config, "local-candidate")

    def test_registry_descriptor_requires_distinct_native_identity(self) -> None:
        digest = "sha256:" + "a" * 64
        native = {
            "digest": "sha256:" + "b" * 64,
            "platform": {"os": "linux", "architecture": "amd64"},
        }
        valid = {"digest": digest, "manifests": [native]}
        reference = "ghcr.io/owner/image@" + digest
        with patch("beta_release.run", return_value=json.dumps(valid)):
            self.assertEqual(
                registry_record(reference, "linux/amd64")["platform_digest"], native["digest"]
            )
        for manifests in (
            [],
            [native, native],
            [{**native, "digest": digest}],
            [native, {**native, "platform": {"os": "linux", "architecture": "arm64"}}],
        ):
            with (
                self.subTest(manifests=manifests),
                patch(
                    "beta_release.run", return_value=json.dumps({**valid, "manifests": manifests})
                ),
                self.assertRaises(ValueError),
            ):
                registry_record(reference, "linux/amd64")

    def test_disposable_registry_manifest_uses_the_same_release_schema(self) -> None:
        value = candidate()
        host = "127.0.0.1:5055"
        for image in value["images"].values():
            image["reference"] = image["reference"].replace("ghcr.io", host)
        beta_release.validate_manifest(value, registry_host=host)
        with patch(
            "beta_release.run",
            return_value=json.dumps(
                {
                    "digest": value["images"]["backend"]["index_digest"],
                    "manifests": [
                        {
                            "digest": value["images"]["backend"]["platform_digest"],
                            "platform": {"os": "linux", "architecture": "amd64"},
                        }
                    ],
                }
            ),
        ):
            self.assertEqual(
                registry_record(
                    value["images"]["backend"]["reference"],
                    "linux/amd64",
                    registry_host=host,
                )["index_digest"],
                value["images"]["backend"]["index_digest"],
            )

    def test_release_rehearsal_is_hosted_read_only_and_reuses_pipeline(self) -> None:
        workflow = (ROOT / ".github/workflows/beta-release-rehearsal.yml").read_text()
        self.assertIn("runs-on: ubuntu-24.04", workflow)
        self.assertIn("version: v0.38.1", workflow)
        self.assertIn("packages: read", workflow)
        self.assertIn('| tee "$log"', workflow)
        self.assertIn("if: always()", workflow)
        self.assertNotIn("packages: write", workflow)
        self.assertNotIn("actions/attest-build-provenance@", workflow)
        source = (ROOT / "scripts/rehearse-beta-release.py").read_text()
        for helper in (
            "local_postgres_identity(",
            "build_application_image(",
            "manifest(",
            "scan_images(",
            "software_bill_of_materials(",
            "run_artifact_smoke(",
            "prepare_release_assets(",
            "promote_image(",
            "release_attestation_inputs(",
        ):
            self.assertIn(helper, source)
        self.assertIn("local_postgres_identity(", source)
        self.assertIn("registry_port", source)
        self.assertIn('"127.0.0.1:{registry_port}:5000"', source)
        self.assertNotIn('"docker", "login", "ghcr.io"', source)
        self.assertIn("pg_builds[0] != pg_builds[1]", source)
        self.assertIn("PREVIOUS_BUILDKit", source)
        self.assertIn("first_component_byte_difference", source)

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
                run_artifact_smoke(artifact, local=True, postgres_image="sha256:" + "0" * 64)
                """)
                .replace("SCRIPTS", repr(str(ROOT / "scripts")))
                .replace("ARTIFACT", repr(str(artifact)))
            )
            result = subprocess.run([sys.executable, "-c", controller], check=False, timeout=10)
            self.assertEqual(result.returncode, 143)
            self.assertTrue((artifact / "cleaned").is_file())

    def test_distinct_digests_and_trusted_build_inputs(self) -> None:
        for field in ("index_digest", "platform_digest"):
            value = candidate()
            value["images"]["frontend"][field] = value["images"]["backend"][field]
            if field == "index_digest":
                value["images"]["frontend"]["reference"] = (
                    "ghcr.io/alessandrorossato/florabase-frontend@"
                    + value["images"]["backend"][field]
                )
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_manifest(value)
        value = candidate()
        value["build_inputs"]["base_images"]["python"] = "python:3.14@sha256:" + "f" * 64
        with self.assertRaises(ValueError):
            validate_manifest(value)

    def test_published_schema_is_enforced(self) -> None:
        base = candidate()
        mutations = []
        for field in base:
            v = copy.deepcopy(base)
            del v[field]
            mutations.append(v)
        for field in ("run_id", "run_attempt"):
            v = copy.deepcopy(base)
            v["workflow"][field] = None
            mutations.append(v)
        for owner in ("foreign", "alessandrorossato"):
            v = copy.deepcopy(base)
            v["images"]["frontend"]["reference"] = v["images"]["backend"]["reference"].replace(
                "alessandrorossato", owner
            )
            mutations.append(v)
        for field in ("scanner", "buildkit", "sbom_generator", "dockerfile_frontend"):
            v = copy.deepcopy(base)
            v["build_inputs"][field] = "example:latest"
            mutations.append(v)
        v = copy.deepcopy(base)
        v["build_inputs"]["base_images"]["python"] = "python:latest"
        mutations.append(v)
        for i, value in enumerate(mutations):
            with self.subTest(case=i), self.assertRaises(ValueError):
                validate_manifest(value)

    def test_attestation_policy_cannot_be_repo_only(self) -> None:
        policy = (ROOT / "docs/beta-image-001.md").read_text()
        for flag in (
            "--signer-workflow",
            "--source-ref",
            "--deny-self-hosted-runners",
            "--source-digest",
        ):
            self.assertIn(flag, policy)

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


INDEX_TYPE = "application/vnd.oci.image.index.v1+json"


class FakeResponse:
    def __init__(self, body: bytes, headers: dict[str, str]) -> None:
        self.body = body
        self.headers = headers

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def token_response() -> FakeResponse:
    return FakeResponse(b'{"token": "registry-fixture"}', {})


def manifest_response(body: bytes = b'{"schemaVersion": 2, "manifests": []}') -> FakeResponse:
    digest = "sha256:" + hashlib.sha256(body).hexdigest()
    return FakeResponse(body, {"Docker-Content-Digest": digest, "Content-Type": INDEX_TYPE})


def http_error(code: int, body: bytes = b"") -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://ghcr.io/fixture",
        code,
        "fixture",
        email.message.Message(),
        io.BytesIO(body),
    )


def registry(*answers: object) -> Any:
    """Answer the token request, then the manifest request, in order."""
    queue = list(answers)

    def urlopen(request: Any, timeout: float) -> Any:
        answer = queue.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        return answer

    return patch.object(publisher.urllib.request, "urlopen", side_effect=urlopen)


class RegistryPreflightTests(unittest.TestCase):
    """GHCR existence checks: only a definite registry "unknown" counts as absent."""

    def lookup(self, *answers: object, actions: str = "pull,push") -> str | None:
        with registry(*answers) as opener:
            result: str | None = publisher.published_digest(
                "alessandrorossato/florabase-backend",
                "0.1.0-beta.3",
                "actor",
                "secret",
                actions=actions,
            )
        token, manifest = (call.args[0] for call in opener.call_args_list)
        self.assertIn(
            "scope=repository%3Aalessandrorossato%2Fflorabase-backend%3A"
            + urllib.parse.quote(actions, safe=""),
            token.full_url,
        )
        self.assertTrue(token.get_header("Authorization").startswith("Basic "))
        self.assertEqual(manifest.get_header("Authorization"), "Bearer registry-fixture")
        self.assertIn(INDEX_TYPE, manifest.get_header("Accept"))
        self.assertTrue(
            manifest.full_url.endswith(
                "/v2/alessandrorossato/florabase-backend/manifests/0.1.0-beta.3"
            )
        )
        return result

    def test_existing_application_version_returns_its_digest(self) -> None:
        response = manifest_response()
        self.assertEqual(
            self.lookup(token_response(), response), response.headers["Docker-Content-Digest"]
        )

    def test_definitely_absent_image(self) -> None:
        for code in ("MANIFEST_UNKNOWN", "NAME_UNKNOWN"):
            body = json.dumps({"errors": [{"code": code, "message": "unknown"}]}).encode()
            with self.subTest(code=code):
                self.assertIsNone(self.lookup(token_response(), http_error(404, body)))

    def test_rehearsal_ghcr_probe_requests_pull_only(self) -> None:
        body = json.dumps({"errors": [{"code": "MANIFEST_UNKNOWN", "message": "unknown"}]}).encode()
        self.assertIsNone(self.lookup(token_response(), http_error(404, body), actions="pull"))

    def test_unauthorized_registry_refuses(self) -> None:
        denied = b'{"errors": [{"code": "DENIED", "message": "denied"}]}'
        for answers in (
            (http_error(401),),
            (http_error(403, denied),),
            (token_response(), http_error(401, denied)),
            (token_response(), http_error(403, denied)),
            # A 404 that is really an authorization refusal is not an absence.
            (token_response(), http_error(404, denied)),
        ):
            with self.subTest(answers=answers), registry(*answers), self.assertRaises(ValueError):
                publisher.published_digest("owner/image", "1", "actor", "secret")

    def test_unavailable_registry_refuses(self) -> None:
        for answers in (
            (urllib.error.URLError("unreachable"),),
            (TimeoutError(),),
            (token_response(), http_error(500)),
            (token_response(), http_error(503)),
            (token_response(), http_error(429)),
            (token_response(), urllib.error.URLError("reset")),
        ):
            with self.subTest(answers=answers), registry(*answers), self.assertRaises(ValueError):
                publisher.published_digest("owner/image", "1", "actor", "secret")

    def test_malformed_response_refuses(self) -> None:
        good = manifest_response()
        for answers in (
            (FakeResponse(b"not json", {}),),
            (FakeResponse(b'{"token": ""}', {}),),
            (FakeResponse(b"[]", {}),),
            (token_response(), http_error(404, b"not json")),
            (token_response(), http_error(404, b'{"errors": []}')),
            (token_response(), http_error(404, b'{"errors": [{"message": "x"}]}')),
            (token_response(), FakeResponse(b"not json", good.headers)),
            (
                token_response(),
                FakeResponse(good.body, {**good.headers, "Docker-Content-Digest": ""}),
            ),
            (token_response(), FakeResponse(b'{"schemaVersion": 2, "x": 1}', good.headers)),
            (
                token_response(),
                FakeResponse(good.body, {**good.headers, "Content-Type": "text/html"}),
            ),
            (
                token_response(),
                FakeResponse(
                    b'{"schemaVersion": 1}', {**manifest_response(b'{"schemaVersion": 1}').headers}
                ),
            ),
        ):
            with self.subTest(answers=answers), registry(*answers), self.assertRaises(ValueError):
                publisher.published_digest("owner/image", "1", "actor", "secret")

    def test_release_scripts_parse_on_the_runner_python(self) -> None:
        # The protected workflow runs these with ubuntu-24.04's Python 3.12, while the repository
        # formatter targets 3.14 (it rewrites `except (A, B):` into 3.14-only syntax).
        for name in (
            "publish-beta-images.py",
            "rehearse-beta-release.py",
            "beta_release.py",
            "beta-release-checks.py",
            "release-tools.py",
            "smoke-beta-images.py",
            "disposable_workflow.py",
            "workflow_resources.py",
        ):
            with self.subTest(name=name):
                source = (ROOT / "scripts" / name).read_text()
                ast.parse(source, name, feature_version=(3, 12))

    def test_invalid_reference_is_refused_before_any_request(self) -> None:
        for repository, tag in (("Owner/Image", "1"), ("owner/image", "1/../x"), ("o", "")):
            with self.subTest(repository=repository), registry() as opener:
                with self.assertRaises(ValueError):
                    publisher.published_digest(repository, tag, "actor", "secret")
                opener.assert_not_called()

    def publish(self, lookups: dict[str, str | Exception | None]) -> tuple[Any, Any, Path]:
        sha = "c" * 40
        environment = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_SHA": sha,
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_REPOSITORY": "alessandrorossato/florabase",
            "GITHUB_WORKFLOW_REF": "alessandrorossato/florabase/.github/workflows/beta-images.yml@refs/heads/main",
            "RUNNER_ENVIRONMENT": "github-hosted",
            "APPROVED_SHA": sha,
            "GITHUB_RUN_ID": "1",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_ACTOR": "fixture",
            "REGISTRY_TOKEN": "fixture-only",
        }
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        target = Path(temporary.name) / "output"

        def output(*args: str) -> str:
            return {"rev-parse": sha, "status": ""}.get(args[1], "0") if args[0] == "git" else "0"

        def lookup(repository: str, tag: str, actor: str, secret: str) -> str | None:
            self.assertEqual((actor, secret), ("fixture", "fixture-only"))
            answer = lookups[repository]
            if isinstance(answer, Exception):
                raise answer
            return answer

        def execute(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
            if command[:3] == ["docker", "buildx", "build"]:
                raise ValueError("stop at build")
            return subprocess.CompletedProcess(command, 0)

        with (
            patch.dict(os.environ, environment, clear=True),
            patch.object(sys, "argv", ["publish", "--output", str(target)]),
            patch.object(publisher, "inputs", return_value=inputs(ROOT)),
            patch.object(publisher, "run", side_effect=output),
            patch.object(publisher, "published_digest", side_effect=lookup),
            patch.object(
                publisher, "local_postgres_identity", side_effect=ValueError("stop after preflight")
            ) as rebuild,
            patch.object(
                publisher.subprocess,
                "run",
                side_effect=execute,
            ) as commands,
            self.assertRaises(ValueError) as raised,
        ):
            publisher.main()
        self.raised = str(raised.exception)
        return commands, rebuild, target

    @staticmethod
    def ran(commands: Any, prefix: list[str]) -> bool:
        return any(call.args[0][: len(prefix)] == prefix for call in commands.call_args_list)

    def lookups(self, **changes: str | Exception | None) -> dict[str, str | Exception | None]:
        value: dict[str, str | Exception | None] = {
            "alessandrorossato/florabase-backend": None,
            "alessandrorossato/florabase-frontend": None,
            "alessandrorossato/florabase-postgres": None,
        }
        value.update({"alessandrorossato/florabase-" + key: item for key, item in changes.items()})
        return value

    def test_existing_application_version_blocks_and_cleans_up(self) -> None:
        for service in ("backend", "frontend"):
            with self.subTest(service=service):
                commands, rebuild, target = self.publish(
                    self.lookups(**{service: "sha256:" + "e" * 64})
                )
                self.assertIn("already exists", self.raised)
                rebuild.assert_not_called()
                self.assertEqual(
                    json.loads((target / "publication-state.json").read_text())["phase"],
                    "preflight",
                )
                # Cleanup after an early error: no builder existed, so none is removed; the
                # registry login is always revoked.
                self.assertFalse(self.ran(commands, ["docker", "buildx", "create"]))
                self.assertFalse(self.ran(commands, ["docker", "buildx", "rm"]))
                self.assertTrue(self.ran(commands, ["docker", "logout", "ghcr.io"]))

    def test_registry_failure_blocks_publication_and_cleans_up(self) -> None:
        failure = ValueError("cannot determine whether fixture exists (HTTP 401)")
        for service in ("backend", "frontend", "postgres"):
            with self.subTest(service=service):
                commands, rebuild, _ = self.publish(self.lookups(**{service: failure}))
                self.assertIn("cannot determine", self.raised)
                rebuild.assert_not_called()
                self.assertFalse(self.ran(commands, ["docker", "buildx", "create"]))
                self.assertFalse(self.ran(commands, ["docker", "buildx", "rm"]))
                self.assertTrue(self.ran(commands, ["docker", "logout", "ghcr.io"]))

    def test_existing_postgres_tag_with_pinned_digest_is_reused(self) -> None:
        pinned = inputs(ROOT)["postgresql"]["index_digest"]
        commands, rebuild, _ = self.publish(self.lookups(postgres=pinned))
        self.assertEqual(self.raised, "stop at build")
        # The published identity is reused: no rebuild into the registry.
        rebuild.assert_not_called()
        self.assertTrue(self.ran(commands, ["docker", "buildx", "create"]))
        # The builder was created, so cleanup removes it.
        self.assertTrue(self.ran(commands, ["docker", "buildx", "rm"]))
        self.assertTrue(self.ran(commands, ["docker", "logout", "ghcr.io"]))

    def test_existing_postgres_tag_with_other_digest_blocks(self) -> None:
        commands, rebuild, _ = self.publish(self.lookups(postgres="sha256:" + "f" * 64))
        self.assertIn("differs from the pinned identity", self.raised)
        rebuild.assert_not_called()
        self.assertFalse(self.ran(commands, ["docker", "buildx", "create"]))
        self.assertTrue(self.ran(commands, ["docker", "logout", "ghcr.io"]))

    def test_absent_postgres_tag_builds_the_pinned_identity(self) -> None:
        commands, rebuild, _ = self.publish(self.lookups())
        self.assertEqual(self.raised, "stop after preflight")
        rebuild.assert_called_once()
        self.assertTrue(self.ran(commands, ["docker", "buildx", "rm"]))


if __name__ == "__main__":
    unittest.main()
