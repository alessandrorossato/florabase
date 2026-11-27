#!/usr/bin/env python3
"""No-Docker regressions for per-worktree UAT instances; real coexistence is smoke-uat-instance."""

from __future__ import annotations

import ast
import contextlib
import copy
import io
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

import feature_batch
import uat_instance
from uat_instance import PREFIX, UATInstance
from uat_preview import UATPreview
from workflow_environment import MEDIA_ROOT, UAT_PROJECT, Repository, WorkflowError, run
from workflow_resources import ResourceError, machine_lock

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

    @staticmethod
    def identity(branch: str) -> dict[str, str]:
        return {"source": str(ROOT), "branch": branch, "sha": "a" * 40, "dirty": "no"}

    def test_reset_keeps_port_and_may_change_profile_only_when_confirmed(self) -> None:
        # Attached owner, pinned: CI checks out a detached merge commit.
        instance = self.make(volumes(str(ROOT), "feat-example-001", 15182), profile="comprehensive")
        with (
            patch.object(instance.repository, "identity", return_value=self.identity("feat/x")),
            patch.object(UATPreview, "reset") as reset,
            patch.object(instance, "remove_oneoffs") as oneoffs,
            patch.object(instance, "require_context") as context,
        ):
            instance.reset("wrong")  # The base refuses it; the profile must not change first.
            self.assertEqual(instance.profile, "smoke")
            oneoffs.assert_not_called()
            context.assert_not_called()
            reset.reset_mock()
            instance.reset(instance.project)
        context.assert_called_once()
        oneoffs.assert_called_once()
        reset.assert_called_once_with(instance.project)
        self.assertEqual((instance.port, instance.profile), (15182, "comprehensive"))

    def test_detached_owner_reset_is_refused_before_any_cleanup(self) -> None:
        instance = self.make(volumes(str(ROOT), "feat-example-001", 15182), branch="detached")
        with (
            patch.object(instance.repository, "identity", return_value=self.identity("detached")),
            patch.object(instance, "remove_oneoffs") as oneoffs,
            patch.object(instance, "require_context") as context,
            patch.object(instance, "require_identity") as guard,
            patch("uat_preview.run") as run,
            patch("uat_instance.run") as instance_run,
        ):
            # The real base refusal: detached delivered owners use guarded remove instead.
            with self.assertRaisesRegex(WorkflowError, "attached feature owner"):
                instance.reset(instance.project)
        for mock in (oneoffs, context, guard, run, instance_run):
            mock.assert_not_called()

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
        for name in (
            "ci-verify.py",
            "compose_stacks.py",
            "feature_batch.py",
            "feature_worktree.py",
            "smoke-uat-instance.py",
            "test-uat-instance.py",
            "uat_instance.py",
            "uat_preview.py",
            "uat_source.py",
            "verification_gate.py",
            "verification_impact.py",
            "workflow_environment.py",
            "workflow_resources.py",
        ):
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


def git(path: Path, *args: str) -> str:
    return run(["git", "-C", str(path), *args], capture=True)


class StaleLaunchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="uat-instance-stale-")
        self.addCleanup(self.temp.cleanup)
        self.primary = Path(self.temp.name) / "primary"
        self.primary.mkdir()
        git(self.primary, "init", "--initial-branch=main")
        git(self.primary, "config", "user.name", "UAT Test")
        git(self.primary, "config", "user.email", "uat" + "@" + "example.invalid")
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
        git(self.primary, "commit", "-m", "base")
        self.base = git(self.primary, "rev-parse", "HEAD")
        git(self.primary, "update-ref", "refs/remotes/origin/main", "HEAD")

        self.source = Path(self.temp.name) / "batch-14"
        git(self.primary, "worktree", "add", "-b", "ci/batch-14", str(self.source), "origin/main")
        (self.source / "old.txt").write_text("old batch tip\n")
        git(self.source, "add", ".")
        git(self.source, "commit", "-m", "old batch tip")
        self.old_tip = git(self.source, "rev-parse", "HEAD")

        # Sibling worktree with its own commit (present in the shared ODB, absent from this reflog).
        self.other = Path(self.temp.name) / "other"
        git(self.primary, "worktree", "add", "-b", "feat/sibling", str(self.other), "origin/main")
        (self.other / "other.txt").write_text("sibling\n")
        git(self.other, "add", ".")
        git(self.other, "commit", "-m", "sibling tip")
        self.sibling_tip = git(self.other, "rev-parse", "HEAD")

        # Rebuild ci/batch-14 from scratch (as feature-batch-prepare does).
        git(self.source, "reset", "--hard", "origin/main")
        (self.source / "rebuilt.txt").write_text("rebuilt batch tip\n")
        git(self.source, "add", ".")
        git(self.source, "commit", "-m", "rebuilt batch tip")
        self.new_tip = git(self.source, "rev-parse", "HEAD")

        self.repo = Repository(self.source)
        self.vols = [
            {
                "Name": f"{PREFIX}ci-batch-14_{key}",
                "Labels": {
                    "com.docker.compose.project": f"{PREFIX}ci-batch-14",
                    "com.docker.compose.volume": key,
                    "io.florabase.source": str(self.source),
                    "io.florabase.uat.instance": "ci-batch-14",
                    "io.florabase.uat.port": "15180",
                    "io.florabase.uat.profile": "smoke",
                },
            }
            for key in ("postgres_data", "attachment_data", "frontend_node_modules")
        ]
        with patch("uat_instance.instance_volumes", return_value=self.vols):
            self.instance = UATInstance(self.repo)

    def containers_for(self, sha: str, *, running: bool = True) -> list[dict[str, Any]]:
        env = self.instance.environment()
        port = str(self.instance.port)
        items: list[dict[str, Any]] = []
        for service in ("db", "backend", "frontend"):
            labels = {
                "com.docker.compose.service": service,
                "com.docker.compose.project": self.instance.project,
                "com.docker.compose.oneoff": "False",
                "io.florabase.role": "uat-instance",
                "io.florabase.source": str(self.source),
                "com.docker.compose.project.working_dir": str(self.source),
                "io.florabase.sha": sha,
            }
            settings = dict(env)
            if service == "backend":
                settings.update(
                    {
                        "FLORABASE_WORKFLOW_MODE": "uat-instance",
                        "FLORABASE_UAT_PROJECT": self.instance.project,
                        "FLORABASE_UAT_SOURCE": str(self.source),
                        "FLORABASE_CANONICAL_ORIGIN": self.instance.url,
                        "FLORABASE_ENVIRONMENT": "development",
                        "FLORABASE_COOKIE_MODE": "loopback-development",
                        "FLORABASE_ATTACHMENT_STORAGE_ROOT": MEDIA_ROOT,
                    }
                )
            if service == "db":
                mounts = [
                    {
                        "Destination": "/var/lib/postgresql",
                        "Type": "volume",
                        "Name": f"{self.instance.project}_postgres_data",
                    }
                ]
            elif service == "backend":
                mounts = [
                    {
                        "Destination": MEDIA_ROOT,
                        "Type": "volume",
                        "Name": f"{self.instance.project}_attachment_data",
                    }
                ] + [
                    {
                        "Destination": f"/app/{name}",
                        "Type": "bind",
                        "Source": str(self.source / "backend" / name),
                    }
                    for name in (
                        "src",
                        "tests",
                        "alembic",
                        "scripts",
                        "openapi.json",
                        "pyproject.toml",
                        "requirements.lock",
                        "requirements-dev.lock",
                    )
                ]
            else:
                mounts = [
                    {
                        "Destination": "/app/node_modules",
                        "Type": "volume",
                        "Name": f"{self.instance.project}_frontend_node_modules",
                    },
                    {
                        "Destination": "/app",
                        "Type": "bind",
                        "Source": str(self.source / "frontend"),
                    },
                    {
                        "Destination": "/backend/openapi.json",
                        "Type": "bind",
                        "Source": str(self.source / "backend/openapi.json"),
                    },
                ]
            bindings = (
                {"5173/tcp": [{"HostIp": "127.0.0.1", "HostPort": port}]}
                if service == "frontend"
                else {}
            )
            ports = bindings if (service == "frontend" and running) else {}
            items.append(
                {
                    "Id": f"cid-{service}",
                    "Config": {
                        "Labels": labels,
                        "Env": [f"{key}={value}" for key, value in settings.items()],
                    },
                    "HostConfig": {"PortBindings": bindings},
                    "NetworkSettings": {
                        "Networks": {f"{self.instance.project}_internal": {}},
                        "Ports": ports,
                    },
                    "Mounts": mounts,
                    "State": {"Running": running},
                }
            )
        return items

    def identity_patches(self, containers: list[dict[str, Any]]) -> contextlib.ExitStack:
        stack = contextlib.ExitStack()
        stack.enter_context(patch.object(self.instance, "validate"))
        stack.enter_context(patch.object(self.instance, "require_owner"))
        stack.enter_context(patch.object(self.instance, "resource_volumes", return_value=self.vols))
        stack.enter_context(patch.object(self.instance, "containers", return_value=containers))
        stack.enter_context(patch.object(self.instance, "require_resource_users"))
        return stack

    def test_rebuilt_branch_status_stop_up_reset_remove_allowed_and_seed_validate_refused(
        self,
    ) -> None:
        stale_running = self.containers_for(self.old_tip, running=True)
        stale_stopped = self.containers_for(self.old_tip, running=False)
        fresh_running = self.containers_for(self.new_tip, running=True)

        # status reports stale launch + next step, zero gh calls.
        with (
            self.identity_patches(stale_running),
            patch.object(self.instance, "current", return_value=["base"]),
            patch.object(self.instance, "marker_state", return_value={uat_instance.LEDGER: None}),
            patch("uat_source.run") as gh_run,
            contextlib.redirect_stdout(io.StringIO()) as out,
        ):
            self.instance.status()
            gh_run.assert_not_called()
        text = out.getvalue()
        self.assertIn(f"launched HEAD: {self.old_tip} (stale: not in current history)", text)
        self.assertIn("make uat-instance-up", text)
        self.assertIn(f"CONFIRM_RESET_UAT_INSTANCE={self.instance.project}", text)

        # seed and validate refuse while launch is stale, zero gh calls.
        with self.identity_patches(stale_running), patch("uat_source.run") as gh_run:
            with self.assertRaisesRegex(WorkflowError, "run make uat-instance-up first"):
                self.instance.seed()
            with self.assertRaisesRegex(WorkflowError, "run make uat-instance-up first"):
                self.instance.validate_dataset()
            gh_run.assert_not_called()

        # stop works on proved stale containers, zero gh calls.
        with (
            self.identity_patches(stale_running),
            patch("uat_preview.run") as docker_run,
            patch("uat_source.run") as gh_run,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.instance.stop()
            gh_run.assert_not_called()
        docker_run.assert_called_once_with(
            ["docker", "container", "stop", "cid-db", "cid-backend", "cid-frontend"]
        )

        # up rebuilds and relabels from HEAD (pre-rebuild stale_ok, post-up strict HEAD), zero gh.
        state = {"items": stale_running}

        def fake_compose(*args: str, **_: Any) -> str:
            if args[:2] == ("up", "-d"):
                state["items"] = fresh_running
            return ""

        def fake_preview_run(command: list[str], **_: Any) -> str:
            if command[:3] == ["docker", "container", "stop"]:
                state["items"] = stale_stopped
            return ""

        with (
            patch.object(self.instance, "allocate"),
            patch.object(self.instance, "validate"),
            patch.object(self.instance, "require_owner"),
            patch.object(self.instance, "resource_volumes", return_value=self.vols),
            patch.object(self.instance, "containers", side_effect=lambda: state["items"]),
            patch.object(self.instance, "require_resource_users"),
            patch.object(self.instance, "compose", side_effect=fake_compose),
            patch.object(self.instance, "start_database"),
            patch.object(self.instance, "current", return_value=["base"]),
            patch.object(self.instance, "upgrade"),
            patch.object(self.instance, "marker_state", return_value={uat_instance.LEDGER: None}),
            patch("uat_preview.run", side_effect=fake_preview_run),
            patch("uat_source.run") as gh_run,
            contextlib.redirect_stdout(io.StringIO()) as up_out,
        ):
            self.instance.up()
            gh_run.assert_not_called()
        self.assertIn(f"launched HEAD: {self.new_tip}", up_out.getvalue())
        self.assertNotIn("stale: not in current history", up_out.getvalue())

        # Guarded reset succeeds on stale launch, zero gh calls.
        reset_state = {"items": stale_running}

        def reset_compose(*args: str, **_: Any) -> str:
            if args[:1] == ("down",):
                reset_state["items"] = []
            return ""

        with (
            patch.object(self.instance, "remove_oneoffs"),
            patch.object(self.instance, "validate"),
            patch.object(self.instance, "require_owner"),
            patch.object(self.instance, "resource_volumes", return_value=self.vols),
            patch.object(self.instance, "containers", side_effect=lambda: reset_state["items"]),
            patch.object(self.instance, "require_resource_users"),
            patch.object(self.instance, "compose", side_effect=reset_compose),
            patch.object(self.instance, "up") as up_mock,
            patch.object(self.instance, "seed") as seed_mock,
            patch.object(self.instance, "status"),
            patch("uat_preview.run") as preview_run,
            patch("uat_source.run") as gh_run,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.instance.reset(self.instance.project)
            gh_run.assert_not_called()
        up_mock.assert_called_once()
        seed_mock.assert_called_once()
        self.assertEqual(
            [call.args[0] for call in preview_run.call_args_list],
            [["docker", "volume", "rm", item["Name"]] for item in self.vols],
        )

        # Guarded remove succeeds on stale launch, zero gh calls.
        rem_state: dict[str, Any] = {
            "containers": stale_running,
            "volumes": self.vols,
            "networks": [
                {
                    "Id": "net-1",
                    "Name": f"{self.instance.project}_internal",
                    "Labels": {
                        "com.docker.compose.project": self.instance.project,
                        "com.docker.compose.network": "internal",
                    },
                    "Containers": {},
                }
            ],
        }

        def remove_docker(command: list[str], **_: Any) -> str:
            if command[:3] == ["docker", "network", "ls"]:
                return "\n".join(item["Id"] for item in rem_state["networks"])
            if command[:3] == ["docker", "network", "inspect"]:
                return json.dumps(rem_state["networks"])
            if command[:2] == ["docker", "ps"]:
                return ""
            if command[:3] == ["docker", "container", "stop"]:
                rem_state["containers"] = stale_stopped
            elif command[:3] == ["docker", "container", "rm"]:
                rem_state["containers"] = []
            elif command[:3] == ["docker", "network", "rm"]:
                rem_state["networks"] = []
            return ""

        with (
            patch.object(self.instance, "remove_oneoffs"),
            patch.object(self.instance, "validate"),
            patch.object(self.instance, "require_owner"),
            patch.object(
                self.instance, "resource_volumes", side_effect=lambda: rem_state["volumes"]
            ),
            patch.object(self.instance, "containers", side_effect=lambda: rem_state["containers"]),
            patch.object(self.instance, "require_resource_users"),
            patch("uat_preview.run", side_effect=remove_docker),
            patch("uat_instance.run", return_value=""),
            patch("uat_source.run") as gh_run,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.instance.remove(self.instance.project)
            gh_run.assert_not_called()

    def test_up_refuses_incompatible_db_with_reset_hint_and_no_data_deletion(self) -> None:
        stale_running = self.containers_for(self.old_tip, running=True)
        with (
            self.identity_patches(stale_running),
            patch.object(self.instance, "allocate"),
            patch.object(self.instance, "compose") as compose,
            patch.object(self.instance, "start_database"),
            patch.object(self.instance, "current", return_value=["dropped_migration_999"]),
            patch.object(self.instance, "upgrade") as upgrade,
            patch("uat_preview.run") as docker_run,
            patch("uat_source.run") as gh_run,
        ):
            with self.assertRaises(WorkflowError) as ctx:
                self.instance.up()
            gh_run.assert_not_called()
        message = str(ctx.exception)
        self.assertIn("AHEAD OF OR INCOMPATIBLE", message)
        self.assertIn(
            f"make uat-instance-reset CONFIRM_RESET_UAT_INSTANCE={self.instance.project}", message
        )
        upgrade.assert_not_called()
        docker_run.assert_not_called()
        self.assertEqual([call.args for call in compose.call_args_list], [("build",)])

    def test_unknown_and_sibling_sha_refused_and_confirmed_reset_remove_fallback(self) -> None:
        for sha in ("f" * 40, self.sibling_tip):
            containers = self.containers_for(sha, running=True)
            with (
                self.subTest(sha=sha),
                self.identity_patches(containers),
                patch.object(self.instance, "allocate"),
                patch("uat_source.run") as gh_run,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                for action in (
                    self.instance.status,
                    self.instance.stop,
                    self.instance.up,
                    self.instance.seed,
                    self.instance.validate_dataset,
                ):
                    with self.assertRaisesRegex(
                        WorkflowError, "not in this worktree's history or reflog"
                    ):
                        action()
                with self.assertRaisesRegex(WorkflowError, "CONFIRM_RESET_UAT_INSTANCE"):
                    self.instance.reset("")
                with self.assertRaisesRegex(WorkflowError, "CONFIRM_REMOVE_UAT_INSTANCE"):
                    self.instance.remove("")
                gh_run.assert_not_called()

        # End-to-end expired-reflog fallback: confirmed reset/remove reach volume removal/recreate
        # when all other identity checks pass; empty/wrong confirm removes nothing.
        unknown_running = self.containers_for("f" * 40, running=True)
        unknown_stopped = self.containers_for("f" * 40, running=False)
        for bad_token in ("", "wrong"):
            with (
                self.identity_patches(unknown_running),
                patch.object(self.instance, "compose") as compose_mock,
                patch("uat_preview.run") as preview_run,
                patch("uat_instance.run") as inst_run,
                patch("uat_source.run") as gh_run,
            ):
                with self.assertRaisesRegex(WorkflowError, "CONFIRM_RESET_UAT_INSTANCE"):
                    self.instance.reset(bad_token)
                with self.assertRaisesRegex(WorkflowError, "CONFIRM_REMOVE_UAT_INSTANCE"):
                    self.instance.remove(bad_token)
                compose_mock.assert_not_called()
                preview_run.assert_not_called()
                inst_run.assert_not_called()
                gh_run.assert_not_called()

        reset_state = {"items": unknown_running}

        def reset_compose(*args: str, **_: Any) -> str:
            if args[:1] == ("down",):
                reset_state["items"] = []
            return ""

        with (
            patch.object(self.instance, "remove_oneoffs"),
            patch.object(self.instance, "validate"),
            patch.object(self.instance, "require_owner"),
            patch.object(self.instance, "resource_volumes", return_value=self.vols),
            patch.object(self.instance, "containers", side_effect=lambda: reset_state["items"]),
            patch.object(self.instance, "require_resource_users"),
            patch.object(self.instance, "compose", side_effect=reset_compose) as compose_mock,
            patch.object(self.instance, "up") as up_mock,
            patch.object(self.instance, "seed") as seed_mock,
            patch.object(self.instance, "status"),
            patch("uat_preview.run") as preview_run,
            patch("uat_source.run") as gh_run,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.instance.reset(self.instance.project)
            gh_run.assert_not_called()
        compose_mock.assert_called_once_with("down", "--remove-orphans")
        up_mock.assert_called_once()
        seed_mock.assert_called_once()
        self.assertEqual(
            [call.args[0] for call in preview_run.call_args_list],
            [["docker", "volume", "rm", item["Name"]] for item in self.vols],
        )

        rem_state: dict[str, Any] = {
            "containers": unknown_running,
            "volumes": self.vols,
            "networks": [
                {
                    "Id": "net-expired",
                    "Name": f"{self.instance.project}_internal",
                    "Labels": {
                        "com.docker.compose.project": self.instance.project,
                        "com.docker.compose.network": "internal",
                    },
                    "Containers": {},
                }
            ],
        }
        removed_volumes: list[str] = []

        def remove_docker(command: list[str], **_: Any) -> str:
            if command[:3] == ["docker", "network", "ls"]:
                return "\n".join(item["Id"] for item in rem_state["networks"])
            if command[:3] == ["docker", "network", "inspect"]:
                return json.dumps(rem_state["networks"])
            if command[:2] == ["docker", "ps"]:
                return ""
            if command[:3] == ["docker", "container", "stop"]:
                rem_state["containers"] = unknown_stopped
            elif command[:3] == ["docker", "container", "rm"]:
                rem_state["containers"] = []
            elif command[:3] == ["docker", "network", "rm"]:
                rem_state["networks"] = []
            elif command[:3] == ["docker", "volume", "rm"]:
                removed_volumes.append(command[-1])
            return ""

        with (
            patch.object(self.instance, "remove_oneoffs"),
            patch.object(self.instance, "validate"),
            patch.object(self.instance, "require_owner"),
            patch.object(
                self.instance, "resource_volumes", side_effect=lambda: rem_state["volumes"]
            ),
            patch.object(self.instance, "containers", side_effect=lambda: rem_state["containers"]),
            patch.object(self.instance, "require_resource_users"),
            patch("uat_preview.run", side_effect=remove_docker),
            patch("uat_instance.run", return_value=""),
            patch("uat_source.run") as gh_run,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.instance.remove(self.instance.project)
            gh_run.assert_not_called()
        self.assertEqual(removed_volumes, sorted(item["Name"] for item in self.vols))

        # Malformed (non-40-hex) io.florabase.sha is ALWAYS refused, even with allow_expired_sha.
        bad_sha = self.containers_for("foreign", running=True)
        with self.identity_patches(bad_sha), patch("uat_source.run") as gh_run:
            with self.assertRaisesRegex(WorkflowError, "missing/unknown UAT launched Git identity"):
                self.instance.require_identity(stale_ok=True, allow_expired_sha=True)
            gh_run.assert_not_called()

    def test_foreign_identity_with_stale_sha_is_always_refused(self) -> None:
        base_containers = self.containers_for(self.old_tip, running=True)
        mutations: list[tuple[str, str, Any]] = [
            (
                "role",
                "ambiguous UAT container identity",
                lambda c: c[0]["Config"]["Labels"].__setitem__("io.florabase.role", "dev"),
            ),
            (
                "source",
                "ambiguous UAT container identity",
                lambda c: c[0]["Config"]["Labels"].__setitem__("io.florabase.source", OTHER),
            ),
            (
                "project",
                "ambiguous UAT container identity",
                lambda c: c[0]["Config"]["Labels"].__setitem__(
                    "com.docker.compose.project", "florabase-uat-branch-other"
                ),
            ),
            (
                "mount",
                "wrong running UAT source mount",
                lambda c: c[1]["Mounts"][1].__setitem__("Source", OTHER + "/backend/src"),
            ),
            (
                "network",
                "ambiguous UAT network identity",
                lambda c: c[0]["NetworkSettings"].__setitem__("Networks", {"foreign_net": {}}),
            ),
        ]
        for label, pattern, mutate in mutations:
            damaged = copy.deepcopy(base_containers)
            mutate(damaged)
            with (
                self.subTest(case=label),
                self.identity_patches(damaged),
                patch("uat_source.run") as gh_run,
            ):
                with self.assertRaisesRegex(WorkflowError, pattern):
                    self.instance.require_identity(stale_ok=True, allow_expired_sha=True)
                gh_run.assert_not_called()
        # Foreign volume user is also refused even with a valid stale SHA and allow_expired_sha.
        with (
            patch.object(self.instance, "validate"),
            patch.object(self.instance, "require_owner"),
            patch.object(self.instance, "resource_volumes", return_value=self.vols),
            patch.object(self.instance, "containers", return_value=base_containers),
            patch("uat_preview.run", side_effect=["", "foreign-container"]),
            patch("uat_source.run") as gh_run,
        ):
            with self.assertRaisesRegex(WorkflowError, "foreign container user"):
                self.instance.require_identity(stale_ok=True, allow_expired_sha=True)
            gh_run.assert_not_called()

    def test_detached_instance_keeps_delivered_proof_path(self) -> None:
        git(self.source, "switch", "--detach", self.base)
        containers = self.containers_for(self.old_tip, running=False)
        with (
            self.identity_patches(containers),
            patch.object(
                self.instance,
                "marker_state",
                return_value={uat_instance.LEDGER: {"state": "ready", "profile": "smoke"}},
            ),
            patch(
                "uat_source.run", side_effect=WorkflowError("command failed: gh api 422")
            ) as gh_run,
        ):
            with self.assertRaises(WorkflowError) as ctx:
                self.instance.require_identity(retiring=True, stale_ok=True, allow_expired_sha=True)
            message = str(ctx.exception)
            self.assertIn(f"launched SHA {self.old_tip[:12]}", message)
            self.assertIn("make uat-instance-status", message)
            self.assertIn("make uat-instance-remove", message)
            self.assertNotIn("make uat-preview-", message)
            gh_run.assert_called_once()

    def test_feature_batch_prepare_hints_when_worktree_owns_uat_instance(self) -> None:
        # Test the post-prepare hint helper behavior via owned_resources patching.
        source_branch = Path(self.temp.name) / "feat-src"
        git(
            self.primary,
            "worktree",
            "add",
            "-b",
            "feat/sample-1",
            str(source_branch),
            "origin/main",
        )
        (source_branch / "docs").mkdir(exist_ok=True)
        (source_branch / "docs/sample.md").write_text("evidence\n")
        git(source_branch, "add", ".")
        git(source_branch, "commit", "-m", "sample feature")
        src_tip = git(source_branch, "rev-parse", "HEAD")

        batch_wt = Path(self.temp.name) / "batch-hint"
        git(self.primary, "worktree", "add", "-b", "ci/batch-hint", str(batch_wt), "origin/main")
        batch_repo = Repository(batch_wt)
        plan = {
            "version": 1,
            "branch": "ci/batch-hint",
            "summary": "Sample batch for UAT instance stale hint test",
            "base": self.base,
            "sources": [
                {
                    "id": "FN-99",
                    "branch": "feat/sample-1",
                    "tip": src_tip,
                    "reviewer": "independent",
                    "evidence": ["docs/sample.md"],
                }
            ],
            "blockers": [],
        }
        with (
            patch("feature_batch.agent_id", return_value="integrator"),
            patch("feature_batch.require_writer"),
            patch("feature_batch.AgentState") as state_cls,
            patch("feature_batch.proposal", return_value=plan),
            patch(
                "feature_batch.owned_resources",
                return_value={
                    f"{PREFIX}ci-batch-hint": {"containers": 3, "running": 3, "volumes": 3}
                },
            ),
            contextlib.redirect_stdout(io.StringIO()) as out,
        ):
            state_cls.return_value.load.return_value = {"writer": {"agent": "integrator"}}
            feature_batch.prepare(batch_repo, plan)
        self.assertIn(f"owns UAT instance {PREFIX}ci-batch-hint", out.getvalue())
        self.assertIn(
            "its running launch predates these merges; run make uat-instance-up to rebuild from HEAD",
            out.getvalue(),
        )

        # When Docker is unavailable (ResourceError), prepare still succeeds with no hint.
        batch_wt_nodocker = Path(self.temp.name) / "batch-nodocker"
        git(
            self.primary,
            "worktree",
            "add",
            "-b",
            "ci/batch-nodocker",
            str(batch_wt_nodocker),
            "origin/main",
        )
        nodocker_plan = {**plan, "branch": "ci/batch-nodocker"}
        with (
            patch("feature_batch.agent_id", return_value="integrator"),
            patch("feature_batch.require_writer"),
            patch("feature_batch.AgentState") as state_cls,
            patch("feature_batch.proposal", return_value=nodocker_plan),
            patch(
                "feature_batch.owned_resources",
                side_effect=ResourceError("Docker daemon unavailable"),
            ),
            contextlib.redirect_stdout(io.StringIO()) as out_nodocker,
        ):
            state_cls.return_value.load.return_value = {"writer": {"agent": "integrator"}}
            feature_batch.prepare(Repository(batch_wt_nodocker), nodocker_plan)
        self.assertIn("Prepared ci/batch-nodocker", out_nodocker.getvalue())
        self.assertNotIn("owns UAT instance", out_nodocker.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
