#!/usr/bin/env python3
"""No-network regression tests for the isolated stable-preview workflow."""

# ruff: noqa: PT009, PT018, PT027, SIM117 -- matches existing unittest workflow helpers.

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("preview_workflow", ROOT / "scripts/preview.py")
assert SPEC is not None and SPEC.loader is not None
preview_workflow = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preview_workflow)
Preview = preview_workflow.Preview
PreviewError = preview_workflow.PreviewError


def run(*command: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return result.stdout.strip()


class RecordingCommands:
    def __init__(self, responses: dict[tuple[str, ...], str] | None = None) -> None:
        self.calls: list[tuple[tuple[str, ...], dict[str, object]]] = []
        self.responses = responses or {}

    def run(self, command: list[str], **kwargs: object) -> str:
        key = tuple(command)
        self.calls.append((key, kwargs))
        return self.responses.get(key, "")


class PreviewGitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="florabase-preview-test-")
        root = Path(self.temporary.name)
        self.remote = root / "remote.git"
        self.seed = root / "seed"
        self.repository = root / "primary"
        self.preview_path = root / "preview"
        run("git", "init", "--bare", "--initial-branch=main", str(self.remote))
        run("git", "init", "--initial-branch=main", str(self.seed))
        run("git", "config", "user.name", "Preview Test", cwd=self.seed)
        run("git", "config", "user.email", "preview@example.invalid", cwd=self.seed)
        (self.seed / "tracked.txt").write_text("base\n")
        run("git", "add", "tracked.txt", cwd=self.seed)
        run("git", "commit", "-m", "base", cwd=self.seed)
        run("git", "remote", "add", "origin", str(self.remote), cwd=self.seed)
        run("git", "push", "--set-upstream", "origin", "main", cwd=self.seed)
        run("git", "clone", str(self.remote), str(self.repository))
        run("git", "config", "user.name", "Preview Test", cwd=self.repository)
        run("git", "config", "user.email", "preview@example.invalid", cwd=self.repository)
        run("git", "switch", "-c", "feat/current", cwd=self.repository)
        (self.repository / "uncommitted.txt").write_text("preserve me\n")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_default_ref_creates_detached_preview_without_touching_primary(self) -> None:
        primary_branch = run("git", "branch", "--show-current", cwd=self.repository)
        primary_head = run("git", "rev-parse", "HEAD", cwd=self.repository)
        primary_status = run("git", "status", "--porcelain=v1", cwd=self.repository)
        expected = run("git", "rev-parse", "origin/main", cwd=self.repository)

        preview = Preview(self.repository, self.preview_path)
        actual = preview.resolve_and_prepare_worktree(preview_workflow.DEFAULT_REF)

        self.assertEqual(actual, expected)
        self.assertEqual(
            run("git", "branch", "--show-current", cwd=self.repository), primary_branch
        )
        self.assertEqual(run("git", "rev-parse", "HEAD", cwd=self.repository), primary_head)
        self.assertEqual(
            run("git", "status", "--porcelain=v1", cwd=self.repository), primary_status
        )
        self.assertEqual(run("git", "rev-parse", "HEAD", cwd=self.preview_path), expected)
        self.assertEqual(run("git", "branch", "--show-current", cwd=self.preview_path), "")

    def test_dirty_preview_refuses_revision_update(self) -> None:
        preview = Preview(self.repository, self.preview_path)
        preview.resolve_and_prepare_worktree("origin/main")
        (self.preview_path / "tracked.txt").write_text("dirty\n")
        with self.assertRaisesRegex(PreviewError, "local changes"):
            preview.resolve_and_prepare_worktree("origin/main")
        self.assertEqual((self.preview_path / "tracked.txt").read_text(), "dirty\n")

    def test_invalid_ref_fails_clearly_without_touching_primary(self) -> None:
        primary_branch = run("git", "branch", "--show-current", cwd=self.repository)
        primary_head = run("git", "rev-parse", "HEAD", cwd=self.repository)
        primary_status = run("git", "status", "--porcelain=v1", cwd=self.repository)

        preview = Preview(self.repository, self.preview_path)
        with self.assertRaisesRegex(PreviewError, "could not resolve preview ref: missing-ref"):
            preview.resolve_and_prepare_worktree("missing-ref")

        self.assertFalse(self.preview_path.exists())
        self.assertEqual(
            run("git", "branch", "--show-current", cwd=self.repository), primary_branch
        )
        self.assertEqual(run("git", "rev-parse", "HEAD", cwd=self.repository), primary_head)
        self.assertEqual(
            run("git", "status", "--porcelain=v1", cwd=self.repository), primary_status
        )

    def test_existing_clean_preview_moves_to_fetched_explicit_ref(self) -> None:
        preview = Preview(self.repository, self.preview_path)
        first = preview.resolve_and_prepare_worktree("origin/main")
        (self.seed / "tracked.txt").write_text("new origin revision\n")
        run("git", "add", "tracked.txt", cwd=self.seed)
        run("git", "commit", "-m", "new origin revision", cwd=self.seed)
        run("git", "push", "origin", "main", cwd=self.seed)
        expected = run("git", "rev-parse", "HEAD", cwd=self.seed)

        actual = preview.resolve_and_prepare_worktree(expected)

        self.assertNotEqual(first, actual)
        self.assertEqual(actual, expected)
        self.assertEqual(run("git", "rev-parse", "HEAD", cwd=self.preview_path), expected)
        self.assertEqual(run("git", "branch", "--show-current", cwd=self.preview_path), "")

    def test_concurrent_primary_edits_do_not_become_a_preview_precondition(self) -> None:
        preview = Preview(self.repository, self.preview_path)
        with patch.object(preview, "primary_state", side_effect=AssertionError, create=True):
            preview.resolve_and_prepare_worktree("origin/main")
        self.assertTrue((self.preview_path / ".git").exists())


class PreviewIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = ROOT
        self.preview_path = ROOT.parent / "florabase-preview-test-path"

    def test_compose_command_has_explicit_project_and_preview_project_directory(self) -> None:
        preview = Preview(self.repository, self.preview_path, RecordingCommands())
        command = preview.compose_command("ps")
        self.assertIn("--project-name", command)
        self.assertEqual(command[command.index("--project-name") + 1], "florabase-preview")
        self.assertEqual(command[command.index("--project-directory") + 1], str(self.preview_path))
        self.assertEqual(
            command[command.index("--file") + 1], str(self.preview_path / "compose.yaml")
        )
        self.assertNotIn("compose.dev.yaml", " ".join(command))

    def test_git_workflow_contains_no_destructive_primary_operations(self) -> None:
        source = (ROOT / "scripts/preview.py").read_text()
        for operation in ('git("reset"', 'git("stash"', 'git("clean"', 'git("checkout"'):
            self.assertNotIn(operation, source)

    def test_rendered_config_requires_internal_db_backend_and_dedicated_frontend(self) -> None:
        preview = Preview(self.repository, self.preview_path)
        preview.sha = "a" * 40
        rendered = {
            "networks": {"internal": {"name": "florabase-preview_internal"}},
            "services": {
                "db": {},
                "backend": {
                    "build": {"context": str(self.preview_path / "backend")},
                    "environment": {
                        "FLORABASE_ENVIRONMENT": "development",
                        "FLORABASE_CANONICAL_ORIGIN": "http://localhost:15173",
                        "FLORABASE_COOKIE_MODE": "loopback-development",
                    },
                },
                "frontend": {
                    "build": {"context": str(self.preview_path / "frontend")},
                    "ports": [{"host_ip": "127.0.0.1", "published": "15173", "target": 8080}],
                },
            },
            "volumes": {"postgres_data": {"name": "florabase-preview_postgres_data"}},
        }
        with patch.object(preview, "compose", return_value=json.dumps(rendered)):
            preview.validate_compose_config()

        rendered["services"]["db"]["ports"] = [{"published": "5432", "target": 5432}]
        with (
            patch.object(preview, "compose", return_value=json.dumps(rendered)),
            self.assertRaisesRegex(PreviewError, "must not publish"),
        ):
            preview.validate_compose_config()

    def test_preview_and_development_compose_projects_cannot_be_reversed(self) -> None:
        commands = RecordingCommands()
        preview = Preview(self.repository, self.preview_path, commands)
        preview.sha = "b" * 40
        preview.compose("ps")
        preview.dev_compose("ps")
        preview_call = commands.calls[0][0]
        dev_call = commands.calls[1][0]
        self.assertEqual(
            preview_call[preview_call.index("--project-name") + 1], "florabase-preview"
        )
        self.assertEqual(dev_call[dev_call.index("--project-name") + 1], "florabase")
        self.assertIn(str(self.preview_path / "compose.yaml"), preview_call)
        self.assertIn(str(self.repository / "compose.dev.yaml"), dev_call)

    def test_stop_and_remove_commands_preserve_volume_and_local_changes(self) -> None:
        source = (ROOT / "scripts/preview.py").read_text()
        stop_block = source[source.index("    def stop(") : source.index("    def remove(")]
        remove_block = source[
            source.index("    def remove(") : source.index("    def import_development(")
        ]
        self.assertIn('self.compose("down", "--remove-orphans")', stop_block)
        self.assertNotIn("--volumes", stop_block)
        self.assertNotIn("-v", stop_block)
        self.assertIn('git("status", "--porcelain=v1"', remove_block)
        self.assertNotIn("--force", remove_block)

    def test_database_actions_are_preview_only_and_never_downgrade(self) -> None:
        source = (ROOT / "scripts/preview.py").read_text()
        migrate_block = source[
            source.index("    def migrate_forward(") : source.index("    def owner_exists(")
        ]
        bootstrap_block = source[
            source.index("    def bootstrap_owner(") : source.index("    def stop(")
        ]
        import_block = source[
            source.index("    def import_development(") : source.index("    def status(")
        ]
        self.assertIn('"alembic", "upgrade", "head"', migrate_block)
        self.assertNotIn("downgrade", migrate_block)
        self.assertIn("self.compose(", bootstrap_block)
        self.assertNotIn("self.dev_compose(", bootstrap_block)
        self.assertIn("self.dev_compose(", import_block)
        self.assertIn("self.compose(", import_block)
        self.assertIn("CONFIRM_REPLACE_PREVIEW=yes", import_block)
        self.assertNotIn("down", import_block)
        self.assertNotIn("downgrade", import_block)

    def test_import_confirmation_fails_before_any_database_command(self) -> None:
        preview = Preview(self.repository, self.preview_path, RecordingCommands())
        with patch.object(preview, "require_worktree"):
            with self.assertRaisesRegex(PreviewError, "CONFIRM_REPLACE_PREVIEW=yes"):
                preview.import_development("", "")
        self.assertEqual(preview.commands.calls, [])

    def test_import_refuses_unmigrated_source_before_replacing_preview(self) -> None:
        preview = Preview(self.repository, self.preview_path, RecordingCommands())
        with (
            patch.object(preview, "require_worktree"),
            patch.object(preview, "validate_compose_config"),
            patch.object(preview, "compose", side_effect=[None, None, "florabase_preview"]),
            patch.object(preview, "dev_compose", return_value="florabase"),
            patch.object(preview, "database_revisions", return_value=[]),
            self.assertRaisesRegex(PreviewError, "no Alembic revision"),
        ):
            preview.import_development("yes", "florabase_preview")

    def test_success_output_reports_exact_sha_url_and_project(self) -> None:
        preview = Preview(self.repository, self.preview_path, RecordingCommands())

        def prepared(ref: str) -> str:
            preview.ref = ref
            preview.sha = "c" * 40
            return preview.sha

        output = io.StringIO()
        with (
            patch.object(preview, "resolve_and_prepare_worktree", side_effect=prepared),
            patch.object(preview, "validate_compose_config"),
            patch.object(preview, "compose"),
            patch.object(preview, "migrate_forward", return_value=["20260908_0020"]),
            patch.object(preview, "wait_for_readiness"),
            patch.object(preview, "owner_exists", return_value=True),
            patch.object(Path, "is_file", return_value=True),
            contextlib.redirect_stdout(output),
        ):
            preview.start("origin/main")
        rendered = output.getvalue()
        self.assertIn(f"SHA: {'c' * 40}", rendered)
        self.assertIn("URL: http://localhost:15173", rendered)
        self.assertIn("Compose project: florabase-preview", rendered)

    def test_unhealthy_readiness_reports_project_specific_logs(self) -> None:
        preview = Preview(
            self.repository,
            self.preview_path,
            RecordingCommands(),
            sleep=lambda _: None,
            urlopen=lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("unreachable")),
        )
        preview.sha = "d" * 40
        with (
            patch.object(preview_workflow.time, "monotonic", side_effect=[0, 0, 2]),
            self.assertRaisesRegex(PreviewError, "florabase-preview.*logs"),
        ):
            preview.wait_for_readiness(timeout=1)

    def test_status_reports_worktree_project_services_volume_revision_and_url(self) -> None:
        with tempfile.TemporaryDirectory(prefix="florabase-preview-status-") as temporary:
            preview_path = Path(temporary) / "preview"
            (preview_path / ".git").mkdir(parents=True)
            ps_command = (
                "docker",
                "ps",
                "--all",
                "--filter",
                "label=com.docker.compose.project=florabase-preview",
                "--format",
                "{{json .}}",
            )
            inspect_command = (
                "docker",
                "inspect",
                "--format",
                "{{json .Config.Labels}}",
                "db-id",
            )
            volume_command = (
                "docker",
                "volume",
                "inspect",
                "florabase-preview_postgres_data",
                "--format",
                "{{.Name}}",
            )
            commands = RecordingCommands(
                {
                    ps_command: json.dumps(
                        {"ID": "db-id", "Names": "florabase-preview-db-1", "Status": "Up (healthy)"}
                    ),
                    inspect_command: json.dumps({"io.florabase.preview.ref": "origin/main"}),
                    volume_command: "florabase-preview_postgres_data",
                }
            )
            preview = Preview(self.repository, preview_path, commands)
            output = io.StringIO()
            with (
                patch.object(preview, "git", side_effect=["e" * 40, "", "e" * 40]),
                patch.object(preview, "database_revisions", return_value=["20260908_0020"]),
                contextlib.redirect_stdout(output),
            ):
                preview.status()
            rendered = output.getvalue()
            self.assertIn(f"Worktree: {preview_path}", rendered)
            self.assertIn("Ref: origin/main", rendered)
            self.assertIn("Compose project: florabase-preview", rendered)
            self.assertIn("URL: http://localhost:15173", rendered)
            self.assertIn("Database volume: florabase-preview_postgres_data", rendered)
            self.assertIn("Alembic: 20260908_0020", rendered)

    def test_integration_workflow_remains_disposable_and_separate(self) -> None:
        integration = (ROOT / "scripts/test-integration.sh").read_text()
        self.assertIn('compose_project="florabase-integration"', integration)
        self.assertIn("--volumes", integration)
        self.assertNotIn("florabase-preview", integration)
        compose = (ROOT / "compose.integration.yaml").read_text()
        self.assertIn("tmpfs:", compose)
        self.assertNotIn("postgres_data", compose)


if __name__ == "__main__":
    unittest.main(verbosity=2)
