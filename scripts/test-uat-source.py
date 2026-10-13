#!/usr/bin/env python3
"""Offline delivered-owner, resource, forward-transition and interruption regressions."""

from __future__ import annotations

import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from uat_preview import VOLUMES, UATPreview
from uat_source import delivered, read_transition, write_transition
from workflow_environment import MEDIA_ROOT, Repository, WorkflowError, run


def git(path: Path, *args: str) -> str:
    return run(["git", "-C", str(path), *args], capture=True)


class SourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="uat delivered owner ")
        self.addCleanup(self.temp.cleanup)
        self.primary = Path(self.temp.name) / "primary"
        self.primary.mkdir()
        git(self.primary, "init", "--initial-branch=main")
        git(self.primary, "config", "user.name", "UAT Test")
        git(self.primary, "config", "user.email", "uat@example.invalid")
        git(
            self.primary,
            "remote",
            "add",
            "origin",
            "https://github.com/alessandrorossato/florabase.git",
        )
        versions = self.primary / "backend/alembic/versions"
        versions.mkdir(parents=True)
        (versions / "base.py").write_text("revision='base'\ndown_revision=None\n")
        git(self.primary, "add", ".")
        git(self.primary, "commit", "-m", "delivered base fixture")
        self.before = git(self.primary, "rev-parse", "HEAD")
        git(self.primary, "update-ref", "refs/remotes/origin/main", "HEAD")
        self.source = Path(self.temp.name) / "owner"
        git(self.primary, "worktree", "add", "--detach", str(self.source))
        self.repo = Repository(self.source)
        self.preview = UATPreview(self.repo)
        self.volumes = [
            {
                "Name": f"{self.preview.project}_{key}",
                "CreatedAt": "original",
                "Labels": {
                    "com.docker.compose.project": self.preview.project,
                    "com.docker.compose.volume": key,
                    "io.florabase.source": str(self.source),
                },
            }
            for key in VOLUMES
        ]
        self.marker = {
            ".uat-identity.json": {
                "project": self.preview.project,
                "source": str(self.source),
                "database": "florabase_uat",
                "origin": self.preview.url,
            },
            ".uat-fixture.json": {
                "state": "ready",
                "version": 4,
                "records": {"supplier:operator": "retained"},
            },
        }

    def newer_main(self) -> str:
        (self.primary / "backend/alembic/versions/next.py").write_text(
            "revision='next'\ndown_revision='base'\n"
        )
        git(self.primary, "add", ".")
        git(self.primary, "commit", "-m", "newer delivered fixture")
        git(self.primary, "update-ref", "refs/remotes/origin/main", "HEAD")
        return git(self.primary, "rev-parse", "HEAD")

    def test_clean_detached_current_and_stale_delivered_context(self) -> None:
        for stale in (False, True):
            if stale:
                self.newer_main()
            with patch.object(self.preview, "resource_volumes", return_value=self.volumes):
                self.preview.require_context()
                self.assertEqual(delivered(self.repo), self.before)

    def test_dirty_detached_and_unestablished_owner_refuse(self) -> None:
        with patch.object(self.preview, "resource_volumes", return_value=[]):
            with self.assertRaisesRegex(WorkflowError, "established persistent UAT owner"):
                self.preview.require_context()
        (self.source / "operator-source-edits").write_text("preserve")
        with patch.object(self.preview, "resource_volumes", return_value=self.volumes):
            with self.assertRaisesRegex(WorkflowError, "must be clean"):
                self.preview.require_context()

    def test_attached_context_and_behind_invalid_feature_refuse(self) -> None:
        git(self.source, "switch", "-c", "ci/uat-test")
        self.preview.require_context()
        git(self.source, "switch", "--detach")
        (self.source / "extra").write_text("unmerged")
        git(self.source, "add", ".")
        git(self.source, "commit", "-m", "ahead fixture")
        with patch("uat_source.run", return_value="[]"):
            with self.assertRaisesRegex(WorkflowError, "ahead/unrelated"):
                delivered(self.repo)

    def test_squash_proof_checks_exact_head_repo_merge_ancestry_with_newer_base(self) -> None:
        git(self.source, "switch", "-c", "feat/squash")
        (self.source / "feature").write_text("same code")
        git(self.source, "add", ".")
        git(self.source, "commit", "-m", "feature fixture")
        head = git(self.source, "rev-parse", "HEAD")
        (self.primary / "concurrent-main-file").write_text("independent delivered main work")
        git(self.primary, "add", ".")
        git(self.primary, "commit", "-m", "concurrent delivered fixture")
        git(self.primary, "merge", "--squash", "feat/squash")
        git(self.primary, "commit", "-m", "delivered squash fixture")
        merge = git(self.primary, "rev-parse", "HEAD")
        git(self.primary, "update-ref", "refs/remotes/origin/main", "HEAD")
        git(self.source, "switch", "--detach")
        git(self.source, "update-ref", "-d", "refs/heads/feat/squash", head)
        pr = {
            "state": "closed",
            "merged_at": "today",
            "head": {"sha": head},
            "base": {"ref": "main", "repo": {"full_name": "alessandrorossato/florabase"}},
            "merge_commit_sha": merge,
        }
        with patch("uat_source.run", return_value=json.dumps([pr])):
            self.assertEqual(delivered(self.repo), merge)
        invalid = []
        for field, value in (
            ("merged_at", None),
            ("merge_commit_sha", head),
            ("head", {"sha": self.before}),
            ("base", {"ref": "main", "repo": {"full_name": "foreign/repo"}}),
        ):
            bad = copy.deepcopy(pr)
            bad[field] = value
            invalid.append([bad])
        invalid.extend([[], [pr, pr]])
        for proposals in invalid:
            with patch("uat_source.run", return_value=json.dumps(proposals)):
                with self.assertRaisesRegex(WorkflowError, "no exact delivered PR proof"):
                    delivered(self.repo)

    def valid_container(self, service: str = "backend") -> dict:
        labels = {
            "com.docker.compose.service": service,
            "com.docker.compose.project": self.preview.project,
            "com.docker.compose.oneoff": "False",
            "io.florabase.role": "uat",
            "io.florabase.source": str(self.source),
            "com.docker.compose.project.working_dir": str(self.source),
            "io.florabase.sha": self.before,
        }
        settings = self.preview.environment()
        settings.update(
            {
                "FLORABASE_WORKFLOW_MODE": "uat",
                "FLORABASE_UAT_PROJECT": self.preview.project,
                "FLORABASE_UAT_SOURCE": str(self.source),
                "FLORABASE_CANONICAL_ORIGIN": self.preview.url,
                "FLORABASE_ENVIRONMENT": "development",
                "FLORABASE_COOKIE_MODE": "loopback-development",
                "FLORABASE_ATTACHMENT_STORAGE_ROOT": MEDIA_ROOT,
            }
        )
        mounts = [
            {
                "Destination": MEDIA_ROOT,
                "Type": "volume",
                "Name": f"{self.preview.project}_attachment_data",
            }
        ]
        for name in (
            "src",
            "alembic",
            "tests",
            "scripts",
            "openapi.json",
            "pyproject.toml",
            "requirements.lock",
            "requirements-dev.lock",
        ):
            mounts.append(
                {
                    "Destination": f"/app/{name}",
                    "Type": "bind",
                    "Source": str(self.source / "backend" / name),
                }
            )
        return {
            "Id": "owned",
            "Image": "validated-image",
            "Config": {
                "Labels": labels,
                "Env": [f"{key}={value}" for key, value in settings.items()],
            },
            "HostConfig": {"PortBindings": {}},
            "NetworkSettings": {"Networks": {f"{self.preview.project}_internal": {}}, "Ports": {}},
            "Mounts": mounts,
            "State": {"Running": False},
        }

    def test_identity_stopped_container_exact_labels_mounts_and_markers(self) -> None:
        valid = self.valid_container()
        with (
            patch.object(self.preview, "validate"),
            patch.object(self.preview, "require_owner"),
            patch.object(self.preview, "resource_volumes", return_value=self.volumes),
            patch.object(self.preview, "containers", return_value=[valid]),
            patch.object(self.preview, "require_resource_users"),
            patch.object(self.preview, "marker_state", return_value=self.marker),
        ):
            self.preview.require_identity()
            for bad in (
                "io.florabase.role",
                "io.florabase.source",
                "io.florabase.sha",
                "com.docker.compose.project",
            ):
                damaged = copy.deepcopy(valid)
                damaged["Config"]["Labels"][bad] = "foreign"
                with patch.object(self.preview, "containers", return_value=[damaged]):
                    with self.assertRaises(WorkflowError):
                        self.preview.require_identity()
            for key, value in (("Name", "foreign"), ("Source", "/foreign/source")):
                damaged = copy.deepcopy(valid)
                damaged["Mounts"][0 if key == "Name" else 1][key] = value
                with patch.object(self.preview, "containers", return_value=[damaged]):
                    with self.assertRaisesRegex(WorkflowError, "mount"):
                        self.preview.require_identity()
            with patch.object(
                self.preview,
                "marker_state",
                return_value={".uat-identity.json": {}, ".uat-fixture.json": {"state": "ready"}},
            ):
                with self.assertRaisesRegex(WorkflowError, "marker"):
                    self.preview.require_identity()

    def test_foreign_volume_user_and_network_endpoint_refuse_ordinary_operations(self) -> None:
        with (
            patch.object(self.preview, "containers", return_value=[{"Id": "owned"}]),
            patch.object(self.preview, "resource_volumes", return_value=self.volumes),
            patch("uat_preview.run", side_effect=["", "foreign"]),
        ):
            with self.assertRaisesRegex(WorkflowError, "foreign container user"):
                self.preview.require_resource_users()
        network = {
            "Name": f"{self.preview.project}_internal",
            "Labels": {
                "com.docker.compose.project": self.preview.project,
                "com.docker.compose.network": "internal",
            },
            "Containers": {"foreign": {}},
        }
        with (
            patch.object(self.preview, "containers", return_value=[]),
            patch("uat_preview.run", side_effect=["network", json.dumps([network])]),
        ):
            with self.assertRaisesRegex(WorkflowError, "foreign endpoint"):
                self.preview.require_resource_users()

    def test_status_current_stale_stopped_and_missing_no_git_mutation(self) -> None:
        for stale in (False, True):
            if stale:
                self.newer_main()
            with (
                patch.object(self.preview, "require_identity"),
                patch.object(self.preview, "resource_volumes", return_value=self.volumes),
                patch.object(self.preview, "containers", return_value=[self.valid_container()]),
                patch.object(self.preview, "marker_state", return_value=self.marker),
                contextlib.redirect_stdout(io.StringIO()) as output,
            ):
                self.preview.status()
            self.assertIn(
                "stale but valid" if stale else "current with origin/main", output.getvalue()
            )
            self.assertIn("backend: stopped", output.getvalue())
            self.assertEqual(git(self.source, "rev-parse", "HEAD"), self.before)
        with (
            patch.object(self.preview, "containers", return_value=[]),
            patch.object(self.preview, "resource_volumes", return_value=[]),
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            self.preview.status()
        self.assertIn("UAT: missing", output.getvalue())

    def sync_patches(
        self, *, revision: str = "base", fail_build: bool = False
    ) -> contextlib.ExitStack:
        stack = contextlib.ExitStack()
        original = self.repo.git
        stack.enter_context(
            patch.object(
                self.repo,
                "git",
                side_effect=lambda *args: "" if args[0] == "fetch" else original(*args),
            )
        )
        stack.enter_context(patch.object(self.preview, "require_identity"))
        stack.enter_context(patch.object(self.preview, "require_marker", return_value=self.marker))
        stack.enter_context(
            patch.object(self.preview, "volume_identity", return_value=[{"original": "preserved"}])
        )
        stack.enter_context(patch.object(self.preview, "stop_writers"))
        stack.enter_context(patch.object(self.preview, "status"))
        stack.enter_context(
            patch.object(
                self.preview,
                "current",
                side_effect=lambda: (
                    ["next"]
                    if getattr(self, "upgraded", False)
                    else ([revision] if revision else [])
                ),
            )
        )
        stack.enter_context(
            patch.object(
                self.preview, "upgrade", side_effect=lambda: setattr(self, "upgraded", True)
            )
        )
        stack.enter_context(
            patch.object(
                self.preview,
                "compose",
                side_effect=lambda *args, **kwargs: (
                    (_ for _ in ()).throw(WorkflowError("interrupted build"))
                    if fail_build and args[0] == "build"
                    else ""
                ),
            )
        )
        return stack

    def test_forward_sync_preserves_volumes_and_uses_no_reset_or_seed(self) -> None:
        target = self.newer_main()
        with (
            self.sync_patches(),
            patch.object(self.preview, "seed") as seed,
            patch.object(self.preview, "remove") as remove,
        ):
            self.preview.sync()
            seed.assert_not_called()
            remove.assert_not_called()
        self.assertEqual(git(self.source, "rev-parse", "HEAD"), target)
        self.assertFalse(self.preview.transition_path.exists())
        self.assertFalse(git(self.source, "status", "--porcelain"))

    def test_ahead_unknown_db_refuses_before_source_switch_or_intent(self) -> None:
        self.newer_main()
        with self.sync_patches(revision="unknown"):
            with self.assertRaisesRegex(WorkflowError, "AHEAD OF OR INCOMPATIBLE"):
                self.preview.sync()
        self.assertEqual(git(self.source, "rev-parse", "HEAD"), self.before)
        self.assertFalse(self.preview.transition_path.exists())

    def test_interrupted_sync_resumes_pinned_target_even_if_main_advances(self) -> None:
        target = self.newer_main()
        with self.sync_patches(fail_build=True):
            with self.assertRaisesRegex(WorkflowError, "interrupted build"):
                self.preview.sync()
        self.assertEqual(git(self.source, "rev-parse", "HEAD"), target)
        self.assertEqual(self.preview.transition()["target"], target)
        with self.assertRaisesRegex(WorkflowError, "interrupted"):
            self.preview.require_idle()
        (self.primary / "later").write_text("later delivered change")
        git(self.primary, "add", ".")
        git(self.primary, "commit", "-m", "later main fixture")
        git(self.primary, "update-ref", "refs/remotes/origin/main", "HEAD")
        with self.sync_patches():
            self.preview.sync()
        self.assertEqual(git(self.source, "rev-parse", "HEAD"), target)
        self.assertFalse(self.preview.transition_path.exists())

    def test_interruption_before_switch_and_ambiguous_transition_refuse(self) -> None:
        target = self.newer_main()
        value = {
            "version": 1,
            "source": str(self.source),
            "project": self.preview.project,
            "before": self.before,
            "target": target,
            "volumes": [{"original": "preserved"}],
        }
        write_transition(self.preview.transition_path, value)
        self.assertEqual(
            read_transition(self.preview.transition_path, self.repo, self.preview.project), value
        )
        with self.sync_patches():
            self.preview.sync()
        self.assertEqual(git(self.source, "rev-parse", "HEAD"), target)
        value["source"] = "/foreign"
        write_transition(self.preview.transition_path, value)
        with self.assertRaisesRegex(WorkflowError, "ambiguous/interrupted"):
            self.preview.transition()

    def test_stale_sync_volume_change_and_unversioned_db_fail_before_switch(self) -> None:
        self.newer_main()
        with self.sync_patches(revision=""):
            with self.assertRaisesRegex(WorkflowError, "unversioned"):
                self.preview.sync()
        with (
            self.sync_patches(),
            patch.object(
                self.preview,
                "volume_identity",
                side_effect=[[{"original": "preserved"}], [{"foreign": "replacement"}]],
            ),
        ):
            with self.assertRaisesRegex(WorkflowError, "volumes changed"):
                self.preview.sync()
        self.assertEqual(git(self.source, "rev-parse", "HEAD"), self.before)
        self.assertFalse(self.preview.transition_path.exists())

    def test_incompatible_status_is_truthful_and_stop_is_still_available(self) -> None:
        container = self.valid_container()
        container["Config"]["Labels"]["com.docker.compose.service"] = "db"
        container["State"]["Running"] = True
        with (
            patch.object(self.preview, "require_identity"),
            patch.object(self.preview, "resource_volumes", return_value=self.volumes),
            patch.object(self.preview, "containers", return_value=[container]),
            patch.object(self.preview, "current", return_value=["ahead"]),
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            with self.assertRaisesRegex(WorkflowError, "AHEAD OF OR INCOMPATIBLE"):
                self.preview.status()
            self.assertIn("incompatible DB/code; stop remains safe", output.getvalue())
            with patch("uat_preview.run") as execute:
                self.preview.stop()
                execute.assert_called_once_with(["docker", "container", "stop", "owned"])

    def test_detached_reset_refuses_before_stopping_or_deleting(self) -> None:
        with (
            patch.object(self.preview, "require_identity") as guard,
            patch.object(self.preview, "compose") as compose,
        ):
            with self.assertRaisesRegex(WorkflowError, "reset requires an attached"):
                self.preview.reset(self.preview.project)
            guard.assert_not_called()
            compose.assert_not_called()

    def test_seed_and_up_refuse_incomplete_sync_and_seed_rejects_old_db(self) -> None:
        with (
            patch.object(self.preview, "transition", return_value={"target": "pending"}),
            patch.object(self.preview, "compose") as compose,
        ):
            for action in (self.preview.up, self.preview.seed):
                with self.assertRaisesRegex(WorkflowError, "interrupted"):
                    action()
            compose.assert_not_called()
        with (
            patch.object(self.preview, "require_identity"),
            patch.object(self.preview, "current", return_value=["unknown"]),
            patch.object(self.preview, "compose") as compose,
        ):
            with self.assertRaisesRegex(WorkflowError, "DB at code head"):
                self.preview.seed()
            compose.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
