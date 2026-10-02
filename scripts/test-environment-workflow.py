#!/usr/bin/env python3
"""Source, worktree, migration and destructive-scope regression tests; no Docker required."""

from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow_environment import (
    Environment,
    Repository,
    WorkflowError,
    code_heads,
    migration_graph,
    preserve_media,
    require_upgradeable,
)

ROOT = Path(__file__).resolve().parents[1]


def git(path: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(path), *args],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


class EnvironmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="florabase workflow spaces ")
        self.addCleanup(self.temporary.cleanup)
        self.primary = Path(self.temporary.name) / "primary"
        self.primary.mkdir()
        git(self.primary, "init", "--initial-branch=main")
        git(self.primary, "config", "user.name", "Workflow Test")
        git(self.primary, "config", "user.email", "workflow@example.invalid")
        git(
            self.primary,
            "remote",
            "add",
            "origin",
            "https://github.com/alessandrorossato/florabase.git",
        )
        (self.primary / ".gitignore").write_text(".env\n")
        (self.primary / ".env").write_text("POSTGRES_PASSWORD=fixture-only-never-print\n")
        versions = self.primary / "backend/alembic/versions"
        versions.mkdir(parents=True)
        (versions / "0029.py").write_text(
            "revision: str = '0029'\ndown_revision: str | None = None\n"
        )
        git(self.primary, "add", ".")
        git(self.primary, "commit", "-m", "fixture stable main")
        git(self.primary, "update-ref", "refs/remotes/origin/main", "HEAD")
        self.feature = Path(self.temporary.name) / "linked feature"
        git(self.primary, "worktree", "add", "--detach", str(self.feature))
        self.repo = Repository(self.feature)

    def test_pointer_file_env_fallback_and_explicit_env_path(self) -> None:
        self.assertTrue((self.feature / ".git").is_file())
        self.assertEqual(self.repo.primary, self.primary)
        self.assertEqual(self.repo.env_file(), self.primary / ".env")
        self.assertFalse((self.feature / ".env").exists())
        with patch.dict(os.environ, {"FLORABASE_ENV_FILE": str(self.primary / "missing")}):
            with self.assertRaisesRegex(WorkflowError, "does not exist"):
                self.repo.env_file()
        with patch.dict(os.environ, {"FLORABASE_ENV_FILE": str(self.primary / ".env")}):
            self.assertEqual(self.repo.env_file(), self.primary / ".env")

    def test_init_creates_only_linked_branch_and_is_idempotent_with_dirty_source(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            self.repo.initialize("ci/environment-workflow")
            (self.feature / "dirty.txt").write_text("untracked feature change")
            self.repo.initialize()
        self.assertEqual(git(self.primary, "branch", "--show-current"), "main")
        self.assertEqual(git(self.primary, "status", "--porcelain"), "")
        self.assertEqual(git(self.feature, "branch", "--show-current"), "ci/environment-workflow")
        self.assertEqual(git(self.primary, "worktree", "list", "--porcelain").count("worktree "), 2)

    def test_init_rejects_dirty_detached_wrong_origin_and_invalid_branch(self) -> None:
        with self.assertRaisesRegex(WorkflowError, "provide BRANCH"):
            self.repo.initialize("main")
        (self.feature / "dirty").touch()
        with self.assertRaisesRegex(WorkflowError, "must be clean"):
            self.repo.initialize("ci/example")
        git(self.feature, "remote", "set-url", "origin", "https://github.com/example/wrong")
        with self.assertRaisesRegex(WorkflowError, "expected Florabase"):
            self.repo.initialize("ci/example")

    def test_0029_primary_0030_dirty_linked_review_uses_only_own_database(self) -> None:
        git(self.feature, "switch", "-c", "fix/incident")
        (self.feature / "backend/alembic/versions/0030.py").write_text(
            "revision = '0030'\ndown_revision = '0029'\n"
        )
        dev, review = Environment(self.repo, "dev"), Environment(self.repo, "review")
        self.assertEqual(code_heads(migration_graph(dev.source)), ["0029"])
        self.assertEqual(code_heads(migration_graph(review.source)), ["0030"])
        self.assertEqual(review.source, self.feature)
        self.assertEqual(review.repo.identity()["dirty"], "yes")
        self.assertEqual(dev.source, self.primary)
        self.assertNotEqual(dev.project, review.project)
        self.assertNotEqual(
            f"{dev.project}_frontend_node_modules", f"{review.project}_frontend_node_modules"
        )
        self.assertEqual(review.env_source, self.primary / ".env")
        with (
            patch.object(review, "current", side_effect=[["0029"], ["0030"]]),
            patch.object(review, "compose") as compose,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            review.upgrade()
        self.assertEqual(compose.call_count, 1)
        command = review.command(*compose.call_args.args)
        self.assertIn("florabase-feature-review", command)
        self.assertIn(str(self.feature), command)
        self.assertNotIn(str(self.primary / "compose.yaml"), command)
        self.assertNotIn("downgrade", command)
        self.assertEqual(code_heads(migration_graph(dev.source)), ["0029"])

    def test_db_ahead_detection_refuses_before_any_migration(self) -> None:
        dev = Environment(self.repo, "dev")
        with (
            patch.object(dev, "current", return_value=["0030"]),
            patch.object(dev, "compose") as compose,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            with self.assertRaisesRegex(WorkflowError, "AHEAD OF OR INCOMPATIBLE.*0030.*0029"):
                dev.upgrade()
        compose.assert_not_called()
        require_upgradeable(["0029"], migration_graph(self.primary))

    def test_review_remove_requires_exact_scope_confirmation_before_commands(self) -> None:
        review = Environment(self.repo, "review")
        with patch.object(review, "compose") as compose:
            with self.assertRaisesRegex(WorkflowError, "CONFIRM_REMOVE_REVIEW"):
                review.stop(remove=True)
            compose.assert_not_called()
        with (
            patch.object(review, "validate"),
            patch.object(review, "require_owner"),
            patch.object(review, "compose") as compose,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            review.stop()
            self.assertNotIn("--volumes", compose.call_args.args)
            review.stop(remove=True, confirm=review.project)
            self.assertIn("--volumes", compose.call_args.args)
        with self.assertRaisesRegex(WorkflowError, "ONLY review"):
            Environment(self.repo, "dev").stop(remove=True, confirm=review.project)

    def test_legacy_dev_temporary_media_still_refuses_unsafe_recreation(self) -> None:
        dev = Environment(self.repo, "dev")
        legacy = {
            "Config": {"Env": ["FLORABASE_ATTACHMENT_STORAGE_ROOT=/tmp/florabase-attachments"]},
            "State": {"Running": True},
            "Id": "legacy-backend-id",
            "Name": "legacy-dev-backend",
        }
        with (
            patch.object(dev, "containers", return_value=[legacy]),
            patch("workflow_environment.run", return_value="True"),
        ):
            with self.assertRaisesRegex(WorkflowError, "legacy DEV media.*make dev-stop"):
                dev.require_durable_legacy_media()
        with (
            patch.object(dev, "containers", return_value=[legacy]),
            patch("workflow_environment.run", return_value="False"),
        ):
            dev.require_durable_legacy_media()

    def test_other_worktree_review_refuses_takeover_even_when_stopped(self) -> None:
        review = Environment(self.repo, "review")
        with patch.object(
            review,
            "containers",
            return_value=[{"Config": {"Labels": {"io.florabase.source": str(self.primary)}}}],
        ):
            with self.assertRaisesRegex(WorkflowError, "belongs to"):
                review.require_owner()
        with (
            patch.object(review, "containers", return_value=[]),
            patch(
                "workflow_environment.run",
                side_effect=[
                    f"{review.project}_postgres_data",
                    json.dumps([{"Labels": {"io.florabase.source": str(self.primary)}}]),
                ],
            ),
        ):
            with self.assertRaisesRegex(WorkflowError, "belongs to"):
                review.require_owner()

    def test_isolated_credentials_ports_and_quality_source_cannot_be_overridden(self) -> None:
        with patch.dict(
            os.environ,
            {
                "COMPOSE_PROJECT_NAME": "florabase-prod",
                "COMPOSE_FILE": "wrong.yaml",
                "POSTGRES_DB": "operator",
                "FLORABASE_DATABASE_URL": "operator",
                "FRONTEND_PORT": "5173",
            },
        ):
            review = Environment(self.repo, "review")
            env = review.environment()
            self.assertEqual(env["COMPOSE_PROJECT_NAME"], review.project)
            self.assertNotIn("COMPOSE_FILE", env)
            self.assertEqual(env["POSTGRES_DB"], "florabase_review")
            self.assertEqual(env["FRONTEND_PORT"], "15174")
            self.assertIn("@db:5432/florabase_review", env["FLORABASE_DATABASE_URL"])
            self.assertEqual(Environment(self.repo, "quality").source, self.feature)
            self.assertEqual(Environment(self.repo, "prod").project, "florabase-prod")

    def test_status_reports_code_db_health_source_without_secrets(self) -> None:
        review = Environment(self.repo, "review")
        containers = [
            {
                "Config": {
                    "Labels": {
                        "com.docker.compose.service": service,
                        "io.florabase.source": str(self.feature),
                        "io.florabase.sha": "launch-sha",
                    }
                },
                "State": {"Running": True, "Health": {"Status": "healthy"}},
            }
            for service in ("db", "backend", "frontend")
        ]
        output = io.StringIO()
        with (
            patch.object(review, "validate"),
            patch.object(review, "containers", return_value=containers),
            patch.object(review, "require_owner"),
            patch.object(review, "current", return_value=["0029"]),
            contextlib.redirect_stdout(output),
        ):
            review.status()
        text = output.getvalue()
        for value in (
            str(self.feature),
            "Database current: 0029",
            "Code head: 0029",
            "frontend: healthy",
            "launch-sha",
            "15174",
            "frontend_node_modules",
            "attachment_data",
        ):
            self.assertIn(value, text)
        self.assertNotIn("fixture-only-never-print", text)

    def test_source_mismatch_status_still_reports_running_health_and_revision(self) -> None:
        dev = Environment(self.repo, "dev")
        output = io.StringIO()
        legacy = {
            "Config": {
                "Labels": {
                    "com.docker.compose.service": "db",
                    "com.docker.compose.project.working_dir": str(self.feature),
                }
            },
            "State": {"Running": True, "Health": {"Status": "healthy"}},
        }
        with (
            patch.object(dev, "validate"),
            patch.object(dev, "containers", return_value=[legacy]),
            patch.object(
                dev, "require_owner", side_effect=WorkflowError("project belongs to legacy feature")
            ),
            patch.object(dev, "current", return_value=["0029"]),
            contextlib.redirect_stdout(output),
        ):
            with self.assertRaisesRegex(WorkflowError, "legacy feature"):
                dev.status()
        self.assertIn("SOURCE MISMATCH", output.getvalue())
        self.assertIn(f"db running source: {self.feature}", output.getvalue())
        self.assertIn("db: healthy", output.getvalue())
        self.assertIn("Database current: 0029", output.getvalue())

    def dev_fixture(self, *, foreign: bool = True, legacy: bool = False) -> list[dict[str, object]]:
        owner = str(self.feature if foreign else self.primary)
        mounts = {
            "db": [("/var/lib/postgresql", "postgres_data")],
            "backend": [("/var/lib/florabase/attachments", "attachment_data")],
            "frontend": [("/app/node_modules", "frontend_node_modules")],
        }
        containers: list[dict[str, object]] = []
        for service in ("db", "backend", "frontend"):
            labels = {
                "com.docker.compose.project": "florabase",
                "com.docker.compose.service": service,
                "com.docker.compose.project.working_dir": owner,
                "com.docker.compose.project.config_files": f"{owner}/compose.yaml,{owner}/compose.dev.yaml",
                "com.docker.compose.container-number": "1",
                "com.docker.compose.oneoff": "False",
                "com.docker.compose.config-hash": "fixture",
            }
            if not legacy:
                labels["io.florabase.role"] = "dev"
                labels["io.florabase.source"] = owner
            container_mounts = [
                {"Destination": target, "Name": f"florabase_{key}", "Type": "volume"}
                for target, key in mounts[service]
            ]
            settings = []
            if service == "backend":
                container_mounts.append(
                    {"Destination": "/app/src", "Source": f"{owner}/backend/src", "Type": "bind"}
                )
                root = "/tmp/florabase-attachments" if legacy else "/var/lib/florabase/attachments"
                settings = [
                    "FLORABASE_ENVIRONMENT=development",
                    "FLORABASE_COOKIE_MODE=loopback-development",
                    f"FLORABASE_ATTACHMENT_STORAGE_ROOT={root}",
                ]
            if service == "frontend":
                container_mounts.append(
                    {"Destination": "/app", "Source": f"{owner}/frontend", "Type": "bind"}
                )
            containers.append(
                {
                    "Id": f"{service}-id",
                    "Name": f"florabase-{service}-1",
                    "Config": {"Labels": labels, "Env": settings},
                    "State": {"Running": True, "Paused": False},
                    "Mounts": container_mounts,
                    "NetworkSettings": {"Networks": {"florabase_internal": {}}},
                }
            )
        return containers

    @staticmethod
    def volume_details() -> str:
        return json.dumps(
            [
                {
                    "Name": f"florabase_{key}",
                    "Labels": {
                        "com.docker.compose.project": "florabase",
                        "com.docker.compose.volume": key,
                    },
                }
                for key in ("postgres_data", "attachment_data", "frontend_node_modules")
            ]
        )

    def test_primary_and_foreign_dev_stop_retain_containers_and_every_volume(self) -> None:
        dev = Environment(self.repo, "dev")
        for foreign in (False, True):
            with (
                self.subTest(foreign=foreign),
                patch.object(dev, "containers", return_value=self.dev_fixture(foreign=foreign)),
                patch.object(dev, "compose") as compose,
                patch("workflow_environment.run", return_value=self.volume_details()) as command,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                dev.stop()
                compose.assert_not_called()  # No dependence on old or current Compose/.env files.
                self.assertEqual(
                    [call.args[0] for call in command.call_args_list if call.args[0][1] == "stop"],
                    [
                        ["docker", "stop", f"{service}-id"]
                        for service in ("frontend", "backend", "db")
                    ],
                )
                self.assertFalse(
                    any(
                        "rm" in call.args[0] or "--volumes" in call.args[0]
                        for call in command.call_args_list
                    )
                )

    def test_foreign_status_prints_exact_recovery_command_and_expected_source(self) -> None:
        dev = Environment(self.repo, "dev")
        output = io.StringIO()
        with (
            patch.object(dev, "validate"),
            patch.object(dev, "containers", return_value=self.dev_fixture()),
            patch.object(dev, "current", return_value=["0029"]),
            contextlib.redirect_stdout(output),
        ):
            with self.assertRaisesRegex(WorkflowError, "make dev-stop.*make dev-up"):
                dev.status()
        self.assertIn(f"Source: {self.primary}", output.getvalue())
        self.assertIn(f"backend running source: {self.feature}", output.getvalue())
        self.assertIn("SOURCE MISMATCH", output.getvalue())

    def test_stopped_status_never_reports_retained_health_as_running(self) -> None:
        dev = Environment(self.repo, "dev")
        containers = self.dev_fixture(foreign=False)
        for container in containers:
            container["State"].update(
                {"Running": False, "Status": "exited", "Health": {"Status": "healthy"}}
            )
        output = io.StringIO()
        with (
            patch.object(dev, "containers", return_value=containers),
            patch.object(dev, "validate"),
            patch.object(dev, "current") as current,
            contextlib.redirect_stdout(output),
        ):
            dev.status()
        self.assertIn("frontend: exited", output.getvalue())
        self.assertIn("frontend retained source:", output.getvalue())
        self.assertNotIn("frontend: healthy", output.getvalue())
        self.assertIn("Database current: unavailable", output.getvalue())
        current.assert_not_called()

    def test_media_copy_is_idempotent_and_rejects_symlinks_without_writes(self) -> None:
        source, existing = [Path(self.temporary.name) / name for name in ("legacy", "volume")]
        (source / "nested").mkdir(parents=True)
        existing.mkdir()
        (source / "nested/blob").write_bytes(b"media")
        (existing / "other").write_bytes(b"keep")
        preserve_media(source, existing)
        preserve_media(source, existing)
        self.assertEqual((existing / "nested/blob").read_bytes(), b"media")
        self.assertEqual((existing / "other").read_bytes(), b"keep")
        (source / "bad-link").symlink_to("nested/blob")
        (source / "not-yet-copied").write_bytes(b"new")
        with self.assertRaisesRegex(WorkflowError, "unsupported legacy DEV media"):
            preserve_media(source, existing)
        self.assertFalse((existing / "not-yet-copied").exists())

    def test_legacy_stop_preserves_tmpfs_before_killing_frozen_backend(self) -> None:
        dev = Environment(self.repo, "dev")
        persistent = Path(self.temporary.name) / "media-volume"
        persistent.mkdir()
        (persistent / "already-durable").write_bytes(b"existing")
        source = Path(self.temporary.name) / "tmpfs"
        source.mkdir()
        (source / "legacy-file").write_bytes(b"temporary")
        calls: list[list[str]] = []

        def command(args: list[str], **_kwargs: object) -> str:
            calls.append(args)
            if args[1:3] == ["volume", "inspect"]:
                return self.volume_details()
            if args[1] == "run":
                self.assertIn("container:backend-id", args)
                self.assertIn("type=volume,src=florabase_attachment_data,dst=/state", args)
                self.assertIn("none", args)
                self.assertNotIn("--privileged", args)
                preserve_media(source, persistent)
            return ""

        with (
            patch.object(dev, "containers", return_value=self.dev_fixture(legacy=True)),
            patch("workflow_environment.run", side_effect=command),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            dev.stop()
        self.assertEqual((persistent / "legacy-file").read_bytes(), b"temporary")
        self.assertEqual((persistent / "already-durable").read_bytes(), b"existing")
        pause = calls.index(["docker", "pause", "backend-id"])
        kill = calls.index(["docker", "kill", "--signal", "KILL", "backend-id"])
        self.assertLess(pause, kill)
        self.assertTrue(all(pause < i < kill for i, call in enumerate(calls) if call[1] == "run"))
        self.assertNotIn(["docker", "unpause", "backend-id"], calls)
        self.assertNotIn(["docker", "stop", "backend-id"], calls)

    def test_media_conflicts_and_copy_failures_leave_legacy_backend_alive(self) -> None:
        dev = Environment(self.repo, "dev")
        with (
            patch.object(dev, "containers", return_value=self.dev_fixture(legacy=True)),
            patch(
                "workflow_environment.run",
                side_effect=[self.volume_details(), "", WorkflowError("copy failed"), ""],
            ) as command,
        ):
            with self.assertRaisesRegex(WorkflowError, "copy failed"):
                dev.stop()
        self.assertEqual(command.call_args.args[0], ["docker", "unpause", "backend-id"])
        self.assertFalse(
            any("kill" in call.args[0] or "stop" in call.args[0] for call in command.call_args_list)
        )
        source, existing = [Path(self.temporary.name) / name for name in ("source", "existing")]
        for directory in (source, existing):
            directory.mkdir()
        (source / "new").write_bytes(b"new")
        (source / "conflict").write_bytes(b"temporary")
        (existing / "conflict").write_bytes(b"durable")
        with self.assertRaisesRegex(WorkflowError, "media conflict"):
            preserve_media(source, existing)
        self.assertEqual([path.name for path in existing.iterdir()], ["conflict"])
        self.assertEqual((existing / "conflict").read_bytes(), b"durable")

    def test_primary_restart_accepts_only_validated_stopped_foreign_dev(self) -> None:
        dev = Environment(self.repo, "dev")
        containers = self.dev_fixture()
        with (
            patch.object(dev, "containers", return_value=containers),
            patch("workflow_environment.run", return_value=self.volume_details()),
        ):
            with self.assertRaisesRegex(WorkflowError, "make dev-stop"):
                dev.require_owner(allow_stopped_dev=True)
            for container in containers:
                container["State"]["Running"] = False
            with contextlib.redirect_stdout(io.StringIO()):
                dev.require_owner(allow_stopped_dev=True)
            with self.assertRaisesRegex(WorkflowError, "belongs to"):
                dev.require_owner()  # Raw compose cannot acquire foreign containers.

    def test_dev_ahead_refuses_before_dependency_or_application_startup(self) -> None:
        dev = Environment(self.repo, "dev")
        with (
            patch.object(dev, "validate"),
            patch.object(dev, "require_owner"),
            patch.object(dev, "require_durable_legacy_media"),
            patch.object(dev, "containers", return_value=[]),
            patch.object(dev, "current", return_value=["0030"]),
            patch.object(dev, "compose") as compose,
        ):
            with self.assertRaisesRegex(WorkflowError, "AHEAD OF OR INCOMPATIBLE"):
                dev.up()
        self.assertEqual(
            [call.args for call in compose.call_args_list],
            [
                ("build",),
                ("up", "-d", "--wait", "--wait-timeout", "120", "db"),
            ],
        )

    def test_preserved_foreign_db_is_checked_without_rebinding_its_container(self) -> None:
        dev = Environment(self.repo, "dev")
        containers = self.dev_fixture()
        for container in containers:
            container["State"]["Running"] = False
        with (
            patch.object(dev, "validate"),
            patch.object(dev, "require_durable_legacy_media"),
            patch.object(dev, "containers", return_value=containers),
            patch("workflow_environment.run", return_value=self.volume_details()),
            patch.object(dev, "current", return_value=["0030"]),
            patch.object(dev, "compose") as compose,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            with self.assertRaisesRegex(WorkflowError, "AHEAD OF OR INCOMPATIBLE"):
                dev.up()
        self.assertEqual(
            [call.args for call in compose.call_args_list],
            [
                ("build",),
                ("start", "--wait", "--wait-timeout", "120", "db"),
            ],
        )

    def test_wrong_ambiguous_or_non_dev_metadata_refuses_before_any_stop(self) -> None:
        dev = Environment(self.repo, "dev")
        invalid = []
        for label, value in (
            ("com.docker.compose.project", "florabase-prod"),
            ("io.florabase.role", "review"),
            ("com.docker.compose.oneoff", "True"),
            ("com.docker.compose.project.working_dir", "relative/path"),
            ("com.docker.compose.service", "unknown"),
        ):
            containers = self.dev_fixture()
            containers[0]["Config"]["Labels"][label] = value
            invalid.append(containers)
        invalid.append(self.dev_fixture() + [copy.deepcopy(self.dev_fixture()[0])])
        for containers in invalid:
            with (
                self.subTest(containers=containers),
                patch.object(dev, "containers", return_value=containers),
                patch("workflow_environment.run") as command,
            ):
                with self.assertRaisesRegex(WorkflowError, "identity.*refused"):
                    dev.stop()
                command.assert_not_called()
        with (
            patch.object(dev, "containers", return_value=self.dev_fixture()),
            patch(
                "workflow_environment.run",
                return_value=self.volume_details().replace('"florabase"', '"florabase-preview"'),
            ) as command,
        ):
            with self.assertRaisesRegex(WorkflowError, "volume ownership"):
                dev.stop()
            self.assertEqual(command.call_count, 1)

    def test_dev_url_cannot_migrate_an_external_database(self) -> None:
        dev = Environment(self.repo, "dev")
        config = {
            "name": dev.project,
            "services": {
                "db": {"environment": {"POSTGRES_DB": "dev", "POSTGRES_USER": "dev"}},
                "backend": {
                    "build": {"context": str(self.primary / "backend")},
                    "environment": {
                        "FLORABASE_DATABASE_URL": "postgresql+psycopg://dev:unused@external-db:5432/dev"
                    },
                },
                "frontend": {
                    "build": {"context": str(self.primary / "frontend")},
                    "ports": [{"published": "5173"}],
                },
            },
        }
        with patch.object(dev, "compose", return_value=json.dumps(config)):
            with self.assertRaisesRegex(WorkflowError, "external or mismatched database"):
                dev.validate()

    def test_raw_cli_cannot_override_project_or_bypass_review_removal_confirmation(self) -> None:
        for role, command, message in (
            (
                "quality",
                ["--project-name", "florabase-prod", "down"],
                "project/files/config are fixed",
            ),
            ("review", ["down", "--volumes"], "exact project confirmation"),
            ("dev", ["down", "--volumes"], "raw DEV lifecycle cleanup is refused"),
            ("dev", ["stop"], "make dev-stop"),
        ):
            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts/workflow_environment.py"),
                    role,
                    "compose",
                    "--",
                    *command,
                ],
                cwd=self.feature,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(message, result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
