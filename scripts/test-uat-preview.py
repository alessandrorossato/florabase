#!/usr/bin/env python3
"""No-Docker UAT command and guard regressions; domain/auth evidence is real smoke."""

from __future__ import annotations

import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from uat_preview import UATPreview
from workflow_environment import UAT_PROJECT, Environment, Repository, WorkflowError

ROOT = Path(__file__).resolve().parents[1]


class UATTests(unittest.TestCase):
    def setUp(self) -> None:
        self.preview = UATPreview(Repository(ROOT))

    def test_roles_keep_sources_credentials_projects_and_files_separate(self) -> None:
        repo = self.preview.repository
        for role in ("dev", "review", "quality", "prod"):
            env = Environment(repo, role)
            self.assertNotEqual(env.project, self.preview.project)
            self.assertNotIn("compose.uat.yaml", " ".join(env.command("ps")))
            self.assertNotIn("FLORABASE_WORKFLOW_MODE", env.environment())
        self.assertEqual(self.preview.env_source, Path("/dev/null"))
        self.assertEqual(self.preview.source, ROOT)
        self.assertIn(str(ROOT / "compose.review.yaml"), self.preview.command("ps"))
        self.assertIn(str(ROOT / "compose.uat.yaml"), self.preview.command("ps"))
        self.assertEqual(self.preview.url, "http://localhost:15174")
        with patch.dict("os.environ", {"POSTGRES_DB": "prod", "FRONTEND_PORT": "8080"}):
            self.assertEqual(self.preview.environment()["POSTGRES_DB"], "florabase_uat")
            self.assertEqual(self.preview.environment()["FRONTEND_PORT"], "15174")

    def test_reset_confirmation_refuses_before_any_docker_or_data_action(self) -> None:
        for token in ("", "florabase", "florabase-preview", "florabase-prod"):
            with (
                self.subTest(token=token),
                patch.object(self.preview, "require_identity") as guard,
            ):
                with self.assertRaisesRegex(WorkflowError, "CONFIRM_RESET_UAT_PREVIEW"):
                    self.preview.reset(token)
                guard.assert_not_called()

    def test_reset_deletes_exact_validated_names_then_rebuilds_and_seeds(self) -> None:
        volumes = [
            {"Name": f"{UAT_PROJECT}_{key}"}
            for key in ("postgres_data", "attachment_data", "frontend_node_modules")
        ]
        with (
            patch.object(self.preview, "require_identity"),
            patch.object(self.preview, "resource_volumes", return_value=volumes),
            patch.object(self.preview, "compose") as compose,
            patch("uat_preview.run") as run,
            patch.object(self.preview, "up") as up,
            patch.object(self.preview, "seed") as seed,
            patch.object(self.preview, "status"),
        ):
            self.preview.reset(UAT_PROJECT)
        self.assertEqual(compose.call_args_list[0].args, ("down", "--remove-orphans"))
        self.assertEqual(
            [call.args[0] for call in run.call_args_list],
            [["docker", "volume", "rm", volume["Name"]] for volume in volumes],
        )
        up.assert_called_once()
        seed.assert_called_once()

    def test_remove_confirmation_refuses_before_inspection_or_mutation(self) -> None:
        for token in ("", "wrong", "florabase", "florabase-preview", "florabase-prod"):
            with (
                self.subTest(token=token),
                patch.object(self.preview, "retirement_resources") as guard,
                patch("uat_preview.run") as run,
            ):
                with self.assertRaisesRegex(WorkflowError, "CONFIRM_REMOVE_UAT_PREVIEW"):
                    self.preview.remove(token)
                guard.assert_not_called()
                run.assert_not_called()

    def test_older_owner_can_invoke_corrected_makefile_without_changing_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="uat-old-owner-") as directory:
            result = subprocess.run(
                [
                    "make",
                    "--no-print-directory",
                    "-n",
                    "-f",
                    str(ROOT / "Makefile"),
                    "uat-preview-remove",
                    f"CONFIRM_REMOVE_UAT_PREVIEW={UAT_PROJECT}",
                ],
                cwd=directory,
                check=True,
                capture_output=True,
                text=True,
            )
        self.assertEqual(
            result.stdout.strip(), f'python3 "{ROOT / "scripts/uat_preview.py"}" remove'
        )

    def test_retirement_allows_detached_owner_without_initializing_git(self) -> None:
        repo = self.preview.repository
        # GitHub Actions checks out a primary tree. Model this test's old UAT
        # owner as a linked worktree, without requiring a real worktree on disk.
        with (
            patch.object(repo, "primary", ROOT.parent),
            patch.object(repo, "common", ROOT / ".git-common"),
            patch.object(repo, "metadata", ROOT / ".git-worktrees" / "uat-owner"),
            patch.object(repo, "initialize") as initialize,
        ):
            self.preview.require_context(retiring=True)
        initialize.assert_not_called()
        with (
            patch.object(repo, "primary", ROOT.parent),
            patch.object(repo, "common", ROOT / ".git-common"),
            patch.object(repo, "metadata", ROOT / ".git-worktrees" / "uat-owner"),
            patch.object(repo, "source", ROOT.parent),
        ):
            with self.assertRaisesRegex(WorkflowError, "linked feature worktree"):
                self.preview.require_context(retiring=True)

    def test_retirement_refuses_unrelated_repository_without_docker_actions(self) -> None:
        repo = self.preview.repository
        with (
            patch.object(repo, "primary", ROOT.parent),
            patch.object(repo, "common", ROOT / ".git-common"),
            patch.object(repo, "metadata", ROOT / ".git-worktrees" / "uat-owner"),
            patch.object(repo, "git", return_value="https://github.com/example/other"),
            patch("uat_preview.run") as run,
        ):
            with self.assertRaisesRegex(WorkflowError, "expected Florabase repository"):
                self.preview.remove(UAT_PROJECT)
            run.assert_not_called()

    def test_remove_nonowner_refuses_before_stopping_any_writer(self) -> None:
        repo = self.preview.repository
        with (
            patch.object(repo, "primary", ROOT.parent),
            patch.object(repo, "common", ROOT / ".git-common"),
            patch.object(repo, "metadata", ROOT / ".git-worktrees" / "uat-owner"),
            patch.object(self.preview, "validate"),
            patch.object(self.preview, "require_owner", side_effect=WorkflowError("foreign owner")),
            patch("uat_preview.run") as run,
        ):
            with self.assertRaisesRegex(WorkflowError, "foreign owner"):
                self.preview.remove(UAT_PROJECT)
            run.assert_not_called()

    def test_remove_stops_writers_rechecks_then_deletes_only_scoped_resources(self) -> None:
        volumes = [
            {"Name": f"{UAT_PROJECT}_{key}"}
            for key in sorted(("postgres_data", "attachment_data", "frontend_node_modules"))
        ]
        before = (["uat-container"], volumes, ["uat-network"])
        events = []
        with (
            patch.object(
                self.preview,
                "retirement_resources",
                side_effect=[before, before, ([], volumes, ["uat-network"]), ([], volumes, [])],
            ) as guard,
            patch.object(self.preview, "containers", return_value=[]),
            patch("uat_preview.run", side_effect=lambda command: events.append(command)),
            patch.object(self.preview, "up") as up,
            patch.object(self.preview, "seed") as seed,
            patch.object(self.preview, "compose") as compose,
        ):
            self.preview.remove(UAT_PROJECT)
        self.assertEqual(guard.call_count, 4)
        self.assertEqual(
            events,
            [
                ["docker", "container", "stop", "uat-container"],
                ["docker", "container", "rm", "uat-container"],
                ["docker", "network", "rm", "uat-network"],
                *[["docker", "volume", "rm", item["Name"]] for item in volumes],
            ],
        )
        up.assert_not_called()
        seed.assert_not_called()
        compose.assert_not_called()

    def test_remove_refuses_resources_changed_after_stop(self) -> None:
        with (
            patch.object(
                self.preview,
                "retirement_resources",
                side_effect=[(["uat-container"], [], []), (["replacement"], [], [])],
            ),
            patch("uat_preview.run") as run,
        ):
            with self.assertRaisesRegex(WorkflowError, "changed during retirement"):
                self.preview.remove(UAT_PROJECT)
        run.assert_called_once_with(["docker", "container", "stop", "uat-container"])

    def test_remove_refuses_writer_restarted_after_stop(self) -> None:
        with (
            patch.object(
                self.preview, "retirement_resources", return_value=(["uat-container"], [], [])
            ),
            patch.object(self.preview, "containers", return_value=[{"State": {"Running": True}}]),
            patch("uat_preview.run") as run,
        ):
            with self.assertRaisesRegex(WorkflowError, "still running"):
                self.preview.remove(UAT_PROJECT)
        run.assert_called_once_with(["docker", "container", "stop", "uat-container"])

    def test_retirement_rejects_wrong_network_and_foreign_endpoints(self) -> None:
        valid = {
            "Name": f"{UAT_PROJECT}_internal",
            "Id": "network-id",
            "Containers": {},
            "Labels": {
                "com.docker.compose.project": UAT_PROJECT,
                "com.docker.compose.network": "internal",
            },
        }
        invalid = []
        for key, value in (
            ("Name", "florabase_internal"),
            ("Containers", {"foreign-container": {}}),
        ):
            network = copy.deepcopy(valid)
            network[key] = value
            invalid.append(network)
        for key in ("com.docker.compose.project", "com.docker.compose.network"):
            network = copy.deepcopy(valid)
            network["Labels"][key] = "foreign"
            invalid.append(network)
        for network in invalid:
            with (
                self.subTest(network=network),
                patch.object(self.preview, "require_identity"),
                patch.object(self.preview, "containers", return_value=[]),
                patch.object(self.preview, "resource_volumes", return_value=[]),
                patch("uat_preview.run", side_effect=["network-id", json.dumps([network])]),
            ):
                with self.assertRaisesRegex(WorkflowError, "network identity"):
                    self.preview.retirement_resources()

    def test_retirement_rejects_foreign_volume_writer(self) -> None:
        with (
            patch.object(self.preview, "require_identity"),
            patch.object(self.preview, "containers", return_value=[]),
            patch.object(
                self.preview,
                "resource_volumes",
                return_value=[{"Name": f"{UAT_PROJECT}_postgres_data"}],
            ),
            patch("uat_preview.run", side_effect=["", "foreign-container"]),
        ):
            with self.assertRaisesRegex(WorkflowError, "foreign container user"):
                self.preview.retirement_resources()

    def test_seed_cannot_mutate_when_host_identity_is_wrong(self) -> None:
        with (
            patch.object(self.preview, "require_identity", side_effect=WorkflowError("wrong DB")),
            patch.object(self.preview, "compose") as compose,
        ):
            with self.assertRaisesRegex(WorkflowError, "wrong DB"):
                self.preview.seed()
            compose.assert_not_called()

    def test_volume_guard_rejects_foreign_and_unidentified_resources(self) -> None:
        valid = {
            "Name": f"{UAT_PROJECT}_postgres_data",
            "Labels": {
                "com.docker.compose.project": UAT_PROJECT,
                "com.docker.compose.volume": "postgres_data",
                "io.florabase.source": str(ROOT),
            },
        }
        for key, value in (
            ("com.docker.compose.project", "florabase-prod"),
            ("com.docker.compose.volume", "arbitrary"),
            ("io.florabase.source", "/another/worktree"),
        ):
            volume = copy.deepcopy(valid)
            volume["Labels"][key] = value
            with (
                self.subTest(key=key),
                patch.object(self.preview, "require_context"),
                patch.object(self.preview, "validate"),
                patch.object(self.preview, "require_owner"),
                patch.object(self.preview, "resource_volumes", return_value=[volume]),
                patch.object(self.preview, "compose") as compose,
            ):
                with self.assertRaisesRegex(WorkflowError, "volume identity"):
                    self.preview.reset(UAT_PROJECT)
                with self.assertRaisesRegex(WorkflowError, "volume identity"):
                    self.preview.remove(UAT_PROJECT)
                compose.assert_not_called()

    def test_container_guard_refuses_foreign_role_before_seed(self) -> None:
        container = {
            "Config": {
                "Labels": {
                    "com.docker.compose.service": "backend",
                    "io.florabase.role": "dev",
                }
            }
        }
        with (
            patch.object(self.preview, "require_context"),
            patch.object(self.preview, "validate"),
            patch.object(self.preview, "require_owner"),
            patch.object(self.preview, "resource_volumes", return_value=[]),
            patch.object(self.preview, "containers", return_value=[container]),
            patch.object(self.preview, "compose") as compose,
        ):
            with self.assertRaisesRegex(WorkflowError, "container identity"):
                self.preview.seed()
            with self.assertRaisesRegex(WorkflowError, "container identity"):
                self.preview.remove(UAT_PROJECT)
            compose.assert_not_called()

    def test_stop_preserves_volumes_and_source(self) -> None:
        with (
            patch.object(self.preview, "require_identity"),
            patch.object(self.preview, "compose") as compose,
        ):
            self.preview.stop()
        compose.assert_called_once_with("down", "--remove-orphans")

    def test_fixture_is_explicit_mount_and_never_default_startup(self) -> None:
        with (
            patch.object(self.preview, "require_identity"),
            patch.object(self.preview, "compose") as compose,
        ):
            self.preview.fixture("seed")
        command = compose.call_args.args
        self.assertIn(f"{ROOT / 'scripts/uat_fixture.py'}:/uat/uat_fixture.py:ro", command)
        self.assertNotIn("uat_fixture", (ROOT / "backend/Dockerfile").read_text())
        self.assertNotIn("uat_fixture", (ROOT / "compose.yaml").read_text())

    def test_context_rejects_primary_and_arbitrary_project(self) -> None:
        with (
            patch.object(self.preview.repository, "initialize"),
            patch.object(self.preview.repository, "source", ROOT / "linked-fixture"),
            patch.object(self.preview.repository, "common", ROOT / ".git-common"),
            patch.object(self.preview.repository, "metadata", ROOT / ".git-worktrees" / "fixture"),
        ):
            self.preview.project = "florabase"
            with self.assertRaisesRegex(WorkflowError, "unexpected UAT project"):
                self.preview.require_context()
            self.preview.repository.source = self.preview.repository.primary
            with self.assertRaisesRegex(WorkflowError, "linked feature worktree"):
                self.preview.require_context()


if __name__ == "__main__":
    unittest.main(verbosity=2)
