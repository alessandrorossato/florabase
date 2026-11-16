#!/usr/bin/env python3
"""Offline checks of report-only and exact cleanup selection."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import workflow_cleanup as cleanup
from workflow_resources import Owner


class CleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        patcher = patch.dict(os.environ, {"FLORABASE_LOCK_DIR": self.temporary.name})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.owner = Owner.disposable("integration", Path(self.temporary.name))
        self.container = {
            "Id": "a" * 64,
            "Name": "fixture",
            "Config": {"Labels": self.owner.labels()},
        }
        self.inventory = {
            "containers": [self.container],
            "networks": [],
            "volumes": [],
            "images": [],
        }

    def test_completed_marker_selects_only_exact_ownership(self) -> None:
        marker = Path(self.temporary.name) / f"{self.owner.project}.ended.json"
        with (
            patch.object(cleanup, "inspect_project", return_value=self.inventory),
            patch.object(cleanup.Resources, "preflight"),
        ):
            self.assertEqual(cleanup.candidate(self.owner.project)["action"], "report-only")
            marker.write_text(json.dumps(self.owner.labels()))
            first = cleanup.candidate(self.owner.project)
            self.assertEqual(first["action"], "remove-disposable")
            self.container["Config"]["Labels"]["other"] = "changed"
            self.assertNotEqual(first["token"], cleanup.candidate(self.owner.project)["token"])

    def test_protected_projects_never_gain_action(self) -> None:
        with patch.object(cleanup, "inspect_project", return_value=self.inventory):
            self.assertEqual(cleanup.candidate("florabase-prod")["action"], "report-only")

    def test_uat_identity_and_volume_recreation(self) -> None:
        project = "florabase-uat-branch-feat-example"
        source = "/missing/source"
        base = {
            "com.docker.compose.project": project,
            "io.florabase.source": source,
            "io.florabase.uat.instance": "feat-example",
            "io.florabase.uat.port": "15180",
            "io.florabase.uat.profile": "smoke",
        }
        volumes = [
            {
                "Name": f"{project}_{key}",
                "CreatedAt": "first",
                "Labels": {**base, "com.docker.compose.volume": key},
            }
            for key in ("postgres_data", "attachment_data", "frontend_node_modules")
        ]
        labels = {
            "com.docker.compose.project": project,
            "io.florabase.source": source,
            "io.florabase.role": "uat-instance",
            "io.florabase.sha": "a" * 40,
            "com.docker.compose.project.working_dir": source,
            "com.docker.compose.service": "backend",
        }
        container = {"Id": "b" * 64, "Config": {"Labels": labels}, "State": {}}
        inventory = {"containers": [container], "networks": [], "volumes": volumes, "images": []}
        with (
            patch.object(cleanup, "inspect_project", return_value=inventory),
            patch.object(cleanup, "source_finished", return_value=True),
        ):
            first = cleanup.candidate(project)
            self.assertEqual(first["action"], "stop-uat")
            volumes[0]["CreatedAt"] = "replacement"
            self.assertNotEqual(first["token"], cleanup.candidate(project)["token"])
            labels["io.florabase.role"] = "uat"
            self.assertEqual(cleanup.candidate(project)["action"], "report-only")

    def test_wrong_token_never_opens_lock(self) -> None:
        with (
            patch.object(cleanup, "local_daemon"),
            patch.object(cleanup, "report", return_value={"projects": {self.owner.project: {}}}),
            patch.object(cleanup, "inspect_project", return_value=self.inventory),
            patch.object(cleanup.Resources, "preflight"),
            patch.object(cleanup, "machine_lock") as lock,
            patch(
                "sys.argv",
                ["workflow_cleanup.py", "--project", self.owner.project, "--confirm", "wrong"],
            ),
        ):
            self.assertEqual(cleanup.main(), 1)
            lock.assert_not_called()

    def test_finished_claimed_and_foreign_worktree_proof(self) -> None:
        root = Path(self.temporary.name)
        primary, worktree = root / "repo", root / "finished"
        primary.mkdir()

        def git(*args: str) -> str:
            return subprocess.run(
                ["git", "-C", str(primary), *args], check=True, capture_output=True, text=True
            ).stdout.strip()

        git("init", "-b", "main")
        git("config", "user.name", "Fixture")
        git("config", "user.email", "fixture@example.invalid")
        (primary / "README").write_text("fixture\n")
        git("add", "README")
        git("commit", "-m", "fixture")
        sha = git("rev-parse", "HEAD")
        git("update-ref", "refs/remotes/origin/main", sha)
        git("worktree", "add", "--detach", str(worktree), sha)
        metadata = Path(
            subprocess.run(
                ["git", "-C", str(worktree), "rev-parse", "--absolute-git-dir"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        (metadata / "info").mkdir(exist_ok=True)
        (metadata / "info/florabase-finished.json").write_text(
            json.dumps({"branch": "feat/example", "sha": sha, "merge": sha})
        )
        previous = Path.cwd()
        try:
            os.chdir(primary)
            self.assertTrue(cleanup.source_finished(str(worktree), str(metadata)))
            state = metadata / "info/florabase-agent-state.json"
            state.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "writer": {"agent": "fixture", "claim_id": "abc"},
                        "handoff": None,
                    }
                )
            )
            self.assertFalse(cleanup.source_finished(str(worktree), str(metadata)))
            state.unlink()
            os.chdir(previous)
            self.assertFalse(cleanup.source_finished(str(worktree), str(metadata)))
        finally:
            os.chdir(previous)

    def test_without_confirmation_never_mutates(self) -> None:
        with (
            patch.object(cleanup, "local_daemon"),
            patch.object(cleanup, "report", return_value={"projects": {self.owner.project: {}}}),
            patch.object(cleanup, "inspect_project", return_value=self.inventory),
            patch.object(cleanup.Resources, "preflight"),
            patch.object(cleanup, "docker") as docker,
            patch("sys.argv", ["workflow_cleanup.py", "--project", self.owner.project]),
        ):
            self.assertEqual(cleanup.main(), 0)
            docker.assert_not_called()


if __name__ == "__main__":
    unittest.main()
