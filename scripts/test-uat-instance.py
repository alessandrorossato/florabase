#!/usr/bin/env python3
"""No-Docker regressions for per-worktree UAT instances; real coexistence is smoke-uat-instance."""

from __future__ import annotations

import ast
import json
import os
import re
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

import uat_instance
from uat_instance import PREFIX, UATInstance
from uat_preview import UATPreview
from workflow_environment import UAT_PROJECT, Repository, WorkflowError
from workflow_resources import machine_lock

ROOT = Path(__file__).resolve().parents[1]
OTHER = "/elsewhere/florabase-other"


def volumes(source: str, name: str, port: int, profile: str = "smoke") -> list[dict[str, Any]]:
    return [
        {
            "Name": f"{PREFIX}{name}_{key}",
            "Labels": {
                "io.florabase.source": source,
                "io.florabase.uat.instance": name,
                "io.florabase.uat.port": str(port),
                "io.florabase.uat.profile": profile,
            },
        }
        for key in ("postgres_data", "attachment_data", "frontend_node_modules")
    ]


class InstanceTests(unittest.TestCase):
    def make(
        self,
        existing: list[dict[str, Any]] | None = None,
        branch: str = "feat/example-001",
        **kw: Any,
    ) -> UATInstance:
        repository = Repository(ROOT)
        identity = {"source": str(ROOT), "branch": branch, "sha": "a" * 40, "dirty": "no"}
        with (
            patch.object(repository, "identity", return_value=identity),
            patch("uat_instance.instance_volumes", return_value=existing or []),
        ):
            return UATInstance(repository, **kw)

    def test_identity_is_derived_from_branch_and_never_overlaps_the_singleton(self) -> None:
        instance = self.make()
        self.assertEqual(instance.project, "florabase-uat-branch-feat-example-001")
        self.assertIsNone(instance.port)
        self.assertEqual(instance.profile, "smoke")
        self.assertFalse(re.fullmatch(UATPreview.PROJECT_PATTERN, instance.project))
        self.assertFalse(re.fullmatch(UATInstance.PROJECT_PATTERN, UAT_PROJECT))
        self.assertEqual(instance.env_source, Path("/dev/null"))
        for branch in ("detached", "feat/under_score", "feat/dotted.name", "feat/" + "x" * 40):
            with self.subTest(branch=branch), self.assertRaises(WorkflowError):
                self.make(branch=branch)
        with self.assertRaisesRegex(WorkflowError, "PROFILE must be"):
            self.make(profile="stress")

    def test_environment_is_isolated_and_overlay_is_last(self) -> None:
        instance = self.make(volumes(str(ROOT), "feat-example-001", 15181, "comprehensive"))
        self.assertEqual((instance.port, instance.profile), (15181, "comprehensive"))
        with patch.dict(os.environ, {"POSTGRES_DB": "florabase", "FRONTEND_PORT": "5173"}):
            env = instance.environment()
        self.assertEqual(env["COMPOSE_PROJECT_NAME"], instance.project)
        self.assertEqual((env["POSTGRES_DB"], env["POSTGRES_USER"]), ("golden_uat", "golden_uat"))
        self.assertTrue(env["FLORABASE_DATABASE_URL"].endswith("@db:5432/golden_uat"))
        self.assertEqual(env["FRONTEND_PORT"], "15181")
        self.assertEqual(env["FLORABASE_ROLE"], "uat-instance")
        self.assertEqual(env["FLORABASE_UAT_PROFILE"], "comprehensive")
        command = instance.command("ps")
        files = [command[index + 1] for index, part in enumerate(command) if part == "--file"]
        self.assertEqual(
            [Path(item).name for item in files],
            [
                "compose.yaml",
                "compose.dev.yaml",
                "compose.review.yaml",
                "compose.uat.yaml",
                "compose.uat-instance.yaml",
            ],
        )
        self.assertEqual(command[-1], "ps")
        self.assertEqual(instance.url, "http://localhost:15181")

    def test_recorded_allocation_refuses_ambiguity_and_profile_change(self) -> None:
        mixed = volumes(str(ROOT), "feat-a", 15180)[:2] + volumes(str(ROOT), "feat-b", 15181)[:1]
        bad_port = volumes(str(ROOT), "feat-a", 15174)
        foreign_name = volumes(str(ROOT), "feat-a", 15180)
        foreign_name[0]["Name"] = "florabase_postgres_data"
        for case in (mixed, bad_port, foreign_name):
            with self.subTest(case=case[0]["Name"]), self.assertRaises(WorkflowError):
                self.make(case)
        # A different requested profile is accepted at construction (reset needs it) but up and
        # seed refuse it with the reset instruction.
        changed = self.make(volumes(str(ROOT), "feat-a", 15180, "smoke"), profile="comprehensive")
        self.assertEqual(changed.profile, "smoke")
        for action in (changed.up, changed.seed):
            with self.subTest(action=action.__name__):
                with (
                    patch.object(changed, "require_identity") as guard,
                    self.assertRaisesRegex(WorkflowError, "CONFIRM_RESET_UAT_INSTANCE"),
                ):
                    action()
                guard.assert_not_called()
        # A detached (finished) owner still finds its instance through the volume record.
        instance = self.make(volumes(str(ROOT), "feat-a", 15182), branch="detached")
        self.assertEqual((instance.project, instance.port), (f"{PREFIX}feat-a", 15182))

    def allocate(
        self,
        instance: UATInstance,
        others: list[dict[str, Any]],
        busy: set[int] = frozenset(),  # type: ignore[assignment]
        unbindable: set[int] = frozenset(),  # type: ignore[assignment]
        probe_fails: bool = False,
    ) -> list[list[str]]:
        calls: list[list[str]] = []
        created: list[str] = []

        def docker(command: list[str], **_: Any) -> str:
            calls.append(command)
            if command[:3] == ["docker", "network", "create"] and probe_fails:
                raise WorkflowError("all predefined address pools have been fully subnetted")
            if command[:3] == ["docker", "network", "create"]:
                created.append(command[-1])
            listed = command[:3] == ["docker", "network", "ls"] and "pool-probe" in command[-1]
            return "probe-id" if listed and created else ""

        with (
            patch("uat_instance.instance_volumes", return_value=others),
            patch("uat_instance.published_ports", return_value=set(busy)),
            patch("uat_instance.bindable", side_effect=lambda port: port not in unbindable),
            patch.object(instance, "containers", return_value=[]),
            patch("uat_instance.run", side_effect=docker),
        ):
            instance.allocate()
        return calls

    def test_allocation_skips_claimed_published_and_bound_ports(self) -> None:
        instance = self.make()
        calls = self.allocate(
            instance, volumes(OTHER, "feat-other", 15180), busy={15181}, unbindable={15182}
        )
        self.assertEqual(instance.port, 15183)
        self.assertEqual(instance.url, "http://localhost:15183")
        # The address-pool probe creates and removes exactly its own uniquely named network.
        create = next(call for call in calls if call[:3] == ["docker", "network", "create"])
        self.assertTrue(create[-1].startswith(instance.project + "-pool-probe-"))
        self.assertIn(["docker", "network", "rm", create[-1]], calls)

    def test_out_of_pool_instances_do_not_consume_operator_slots(self) -> None:
        smoke = volumes(OTHER, "smoke-0123456789ab", 40001)
        three = [
            item
            for index, port in enumerate(list(uat_instance.PORTS)[:3])
            for item in volumes(f"{OTHER}-{index}", f"feat-o{index}", port)
        ]
        instance = self.make()
        self.allocate(instance, smoke + three)
        self.assertEqual(instance.port, uat_instance.PORTS[-1])

    def test_allocation_refuses_collisions_capacity_and_exhausted_pools(self) -> None:
        full = [
            item
            for index, port in enumerate(uat_instance.PORTS)
            for item in volumes(f"{OTHER}-{index}", f"feat-o{index}", port)
        ]
        cases: list[tuple[str, UATInstance, dict[str, Any]]] = [
            ("slots are allocated", self.make(), {"others": full}),
            ("belongs to", self.make(), {"others": volumes(OTHER, "feat-example-001", 15183)}),
            ("no free", self.make(), {"others": [], "busy": set(uat_instance.PORTS)}),
            (
                "claimed by another",
                self.make(volumes(str(ROOT), "feat-example-001", 15180)),
                {"others": volumes(OTHER, "feat-x", 15180)},
            ),
            (
                "another listener",
                self.make(volumes(str(ROOT), "feat-example-001", 15180)),
                {"others": [], "unbindable": {15180}},
            ),
            ("address pools", self.make(), {"others": [], "probe_fails": True}),
        ]
        for message, instance, options in cases:
            with self.subTest(message=message), self.assertRaisesRegex(WorkflowError, message):
                self.allocate(instance, **options)

    def test_destructive_actions_require_exact_own_project_before_any_docker(self) -> None:
        instance = self.make(volumes(str(ROOT), "feat-example-001", 15180))
        tokens = ("", UAT_PROJECT, "florabase", "florabase-prod", f"{PREFIX}feat-other")
        for token in tokens:
            with (
                self.subTest(token=token),
                patch.object(instance, "require_identity") as guard,
                patch.object(instance, "retirement_resources") as retirement,
                patch("uat_preview.run") as run,
                patch("uat_instance.run") as instance_run,
            ):
                with self.assertRaisesRegex(WorkflowError, "CONFIRM_RESET_UAT_INSTANCE"):
                    instance.reset(token)
                with self.assertRaisesRegex(WorkflowError, "CONFIRM_REMOVE_UAT_INSTANCE"):
                    instance.remove(token)
                for mock in (guard, retirement, run, instance_run):
                    mock.assert_not_called()
        missing = self.make()
        for action in (missing.stop, missing.seed, missing.validate_dataset):
            with self.subTest(action=action.__name__), self.assertRaises(WorkflowError):
                action()

    def test_reset_keeps_port_and_may_change_profile_only_when_confirmed(self) -> None:
        instance = self.make(volumes(str(ROOT), "feat-example-001", 15182), profile="comprehensive")
        with (
            patch.object(UATPreview, "reset") as reset,
            patch.object(instance, "remove_oneoffs") as oneoffs,
            patch.object(instance, "require_context") as context,
        ):
            instance.reset("wrong")  # The base refuses it; the profile must not change first.
            self.assertEqual(instance.profile, "smoke")
            oneoffs.assert_not_called()
            reset.reset_mock()
            instance.reset(instance.project)
        oneoffs.assert_called_once()
        context.assert_called_once()
        reset.assert_called_once_with(instance.project)
        self.assertEqual((instance.port, instance.profile), (15182, "comprehensive"))

    def test_interrupted_oneoffs_are_removed_only_when_exactly_owned(self) -> None:
        instance = self.make(volumes(str(ROOT), "feat-example-001", 15180))
        owned = {
            "Id": "one",
            "Config": {
                "Labels": {
                    "com.docker.compose.project": instance.project,
                    "com.docker.compose.service": "backend",
                    "io.florabase.source": str(ROOT),
                    "com.docker.compose.project.working_dir": str(ROOT),
                }
            },
        }
        foreign = json.loads(json.dumps(owned))
        foreign["Config"]["Labels"]["io.florabase.source"] = OTHER
        for items, removed in (([owned], ["one"]), ([owned, foreign], None)):
            calls: list[list[str]] = []

            def docker(
                command: list[str],
                found: list[Any] = items,
                log: list[list[str]] = calls,
                **_: Any,
            ) -> str:
                log.append(command)
                if command[:2] == ["docker", "ps"]:
                    return "\n".join(item["Id"] for item in found)
                return json.dumps(found) if command[:2] == ["docker", "inspect"] else ""

            with patch("uat_instance.run", side_effect=docker):
                if removed is None:
                    with self.assertRaisesRegex(WorkflowError, "one-off"):
                        instance.remove_oneoffs()
                else:
                    instance.remove_oneoffs()
            rm = [call[-1] for call in calls if call[:2] == ["docker", "rm"]]
            self.assertEqual(rm, removed or [])

    def test_manifest_is_read_through_the_current_project_image(self) -> None:
        instance = self.make(volumes(str(ROOT), "feat-example-001", 15180))
        backend = {"Config": {"Labels": {"com.docker.compose.service": "backend"}}}
        backend["Image"] = "sha256:" + "0" * 64  # Retained, possibly no longer existing, ID.
        with (
            patch.object(instance, "containers", return_value=[backend]),
            patch.object(
                instance, "environment", return_value={"LOCAL_UID": "1", "LOCAL_GID": "1"}
            ),
            patch("uat_instance.run", return_value="null") as run,
        ):
            self.assertEqual(instance.marker_state(), {uat_instance.LEDGER: None})
        command = run.call_args.args[0]
        self.assertIn(f"{instance.project}-backend-development", command)
        self.assertNotIn(backend["Image"], command)
        self.assertIn(
            f"src={instance.project}_attachment_data,dst=/var/lib/florabase/attachments,readonly",
            " ".join(command),
        )

    def test_host_run_modules_parse_on_the_ci_python(self) -> None:
        # CI runs these with Python 3.12; the formatter targets 3.14 and may rewrite `except (A, B)`.
        for name in ("uat_instance.py", "test-uat-instance.py", "smoke-uat-instance.py"):
            with self.subTest(name=name):
                source = (ROOT / "scripts" / name).read_text()
                ast.parse(source, name, feature_version=(3, 12))

    def test_remove_retires_only_exact_own_image_tags(self) -> None:
        instance = self.make(volumes(str(ROOT), "feat-example-001", 15180))
        calls: list[list[str]] = []

        def docker(command: list[str], **_: Any) -> str:
            calls.append(command)
            return "sha256:x" if command[:3] == ["docker", "image", "ls"] else ""

        with (
            patch.object(UATPreview, "remove") as remove,
            patch.object(instance, "require_context") as context,
            patch("uat_instance.run", side_effect=docker),
        ):
            instance.remove(instance.project)
        context.assert_called_once_with(retiring=True)
        remove.assert_called_once_with(instance.project)
        self.assertEqual(
            [call for call in calls if call[:3] == ["docker", "image", "rm"]],
            [
                ["docker", "image", "rm", f"{instance.project}-backend-development"],
                ["docker", "image", "rm", f"{instance.project}-frontend-development"],
            ],
        )

    def test_heavy_actions_share_the_full_capacity_lock_and_status_does_not(self) -> None:
        repository = Repository(ROOT)
        identity = {
            "source": str(ROOT),
            "branch": "feat/example-001",
            "sha": "a" * 40,
            "dirty": "no",
        }
        with tempfile.TemporaryDirectory(prefix="uat-instance-locks-") as directory:
            with (
                patch.dict(os.environ, {"FLORABASE_LOCK_DIR": directory}),
                patch.object(repository, "identity", return_value=identity),
                patch("uat_instance.Repository", return_value=repository),
                patch("uat_instance.instance_volumes", return_value=[]),
                patch.object(UATInstance, "up") as up,
                patch.object(UATInstance, "seed") as seed,
                patch.object(UATInstance, "status") as status,
                patch.object(UATInstance, "stop") as stop,
                machine_lock("verification-full", "canonical FULL verification"),
            ):
                for action in ("up", "seed", "status", "stop"):
                    with patch("sys.argv", ["uat_instance.py", action]):
                        code = uat_instance.main()
                    self.assertEqual(code, 1 if action in {"up", "seed"} else 0, action)
            up.assert_not_called()
            seed.assert_not_called()
            status.assert_called_once()
            stop.assert_called_once()
            holder = json.loads((Path(directory) / "verification-full.lock").read_text() or "{}")
            self.assertEqual(holder, {})  # Released and truncated after the holder exited.

    def test_published_ports_reads_running_and_stopped_bindings(self) -> None:
        inspected = [
            {
                "Id": "b",
                "HostConfig": {"PortBindings": {"5173/tcp": [{"HostPort": "15180"}]}},
                "NetworkSettings": {"Ports": {}},
            },
            {
                "Id": "c",
                "HostConfig": {"PortBindings": {"80/tcp": [{"HostIp": "", "HostPort": ""}]}},
                "NetworkSettings": {"Ports": {"80/tcp": [{"HostPort": "15182"}], "9/udp": None}},
            },
        ]

        def docker(command: list[str], **_: Any) -> str:
            return "a\nb\nc" if command[:2] == ["docker", "ps"] else json.dumps(inspected)

        with patch("uat_instance.run", side_effect=docker) as run:
            self.assertEqual(uat_instance.published_ports({"a"}), {15180, 15182})
        self.assertEqual(run.call_args_list[-1].args[0], ["docker", "inspect", "b", "c"])
        with socket.socket() as holder:
            holder.bind(("127.0.0.1", 0))
            holder.listen()
            self.assertFalse(uat_instance.bindable(holder.getsockname()[1]))

    def test_make_targets_pass_profile_and_exact_confirmation(self) -> None:
        result = subprocess.run(
            [
                "make",
                "--no-print-directory",
                "-n",
                "-f",
                str(ROOT / "Makefile"),
                "uat-instance-reset",
                "PROFILE=comprehensive",
                f"CONFIRM_RESET_UAT_INSTANCE={PREFIX}feat-x",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.stdout.strip(),
            f'python3 "{ROOT / "scripts/uat_instance.py"}" reset --profile "comprehensive"',
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
