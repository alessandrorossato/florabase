#!/usr/bin/env python3
"""Fast DEV Golden command and ownership regressions. No Docker writes."""

import os
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock, patch

import dev_golden as golden
import workflow_environment as workflow
from workflow_environment import WorkflowError


class DevGoldenTests(unittest.TestCase):
    def test_exact_confirmation_precedes_docker(self) -> None:
        for action, token, recovery in (
            ("init", "replace-florabase-dev", "0"),
            ("reset", "initialize-florabase-dev", "0"),
            ("reset", "replace-florabase-dev", "1"),
        ):
            with (
                self.subTest(action=action, recovery=recovery),
                patch("sys.argv", ["dev_golden.py", action]),
                patch.dict(os.environ, {"CONFIRM_DEV_GOLDEN": token, "RECOVER": recovery}),
                patch.object(golden, "local_docker") as docker,
            ):
                self.assertEqual(golden.main(), 1)
                docker.assert_not_called()

    def test_linked_checkout_refused(self) -> None:
        repository = Mock(source=Path("/feature"), primary=Path("/main"))
        with (
            patch("sys.argv", ["dev_golden.py", "status"]),
            patch.object(golden, "local_docker"),
            patch.object(golden, "Repository", return_value=repository),
            patch.object(golden, "Environment") as environment,
        ):
            self.assertEqual(golden.main(), 1)
            environment.assert_not_called()

    def test_pending_recovery_can_run_after_tracking_ref_moves(self) -> None:
        repository = Mock(source=Path("/main"), primary=Path("/main"))
        repository.git.side_effect = lambda *args: {
            ("branch", "--show-current"): "main",
            ("status", "--porcelain"): "",
            ("rev-parse", "HEAD"): "journal-source",
            ("rev-parse", "origin/main"): "new-source",
        }[args]
        with tempfile.TemporaryDirectory() as directory:
            pending = Path(directory) / "pending.json"
            pending.touch()
            with (
                patch("sys.argv", ["dev_golden.py", "reset"]),
                patch.dict(
                    os.environ,
                    {
                        "CONFIRM_DEV_GOLDEN": "recover-florabase-dev",
                        "RECOVER": "1",
                        "BACKUP": "",
                    },
                ),
                patch.object(golden, "local_docker"),
                patch.object(golden, "Repository", return_value=repository),
                patch.object(
                    golden, "Environment", return_value=Mock(project=workflow.DEV_PROJECT)
                ),
                patch.object(golden, "dev_golden_pending", return_value=pending),
                patch.object(golden, "machine_lock", side_effect=lambda *_: nullcontext()),
                patch.object(golden, "DevGolden") as target,
            ):
                self.assertEqual(golden.main(), 0)
                target.return_value.recover.assert_called_once_with()

    def test_pending_recovery_blocks_normal_dev_writers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pending = Path(directory) / "pending.json"
            pending.touch()
            with (
                patch("sys.argv", ["workflow_environment.py", "dev", "up"]),
                patch.object(workflow, "Repository"),
                patch.object(
                    workflow, "Environment", return_value=Mock(project=workflow.DEV_PROJECT)
                ),
                patch.object(workflow, "dev_golden_pending", return_value=pending),
                patch.object(workflow, "machine_lock", return_value=nullcontext()),
                patch.object(workflow, "dispatch") as dispatch,
            ):
                self.assertEqual(workflow.main(), 1)
                dispatch.assert_not_called()

    def test_only_workstation_docker_socket(self) -> None:
        for host in (
            "tcp://localhost:2375",
            "ssh://nas",
            "unix:///tmp/alternate-docker.sock",
        ):
            with (
                self.subTest(host=host),
                patch.dict(os.environ, {"DOCKER_HOST": host, "DOCKER_CONTEXT": ""}),
                self.assertRaises(WorkflowError),
            ):
                golden.local_docker()

    def test_only_exact_loopback_publication(self) -> None:
        for address, published, accepted in (
            ("0.0.0.0", "5173", False),
            ("127.0.0.1", "15183", False),
            ("127.0.0.1", "5173", True),
        ):
            self.assertEqual(
                golden.exact_port(
                    {
                        "HostConfig": {
                            "PortBindings": {
                                "5173/tcp": [{"HostIp": address, "HostPort": published}]
                            },
                        },
                    },
                    5173,
                ),
                accepted,
            )

    def test_foreign_volume_or_network_use_refused(self) -> None:
        for kind in ("network", "volume"):
            with (
                self.subTest(kind=kind),
                patch.object(golden, "docker", return_value="owned\nforeign"),
                self.assertRaisesRegex(WorkflowError, f"Foreign container uses DEV {kind}"),
            ):
                golden.DevGolden.require_users(kind, "dev", {"owned"})


if __name__ == "__main__":
    unittest.main()
