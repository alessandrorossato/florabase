#!/usr/bin/env python3
"""No-daemon ownership, retirement, runner failure and signal cleanup regressions."""

from __future__ import annotations

import copy
import json
import os
import signal
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from disposable_workflow import execute, safe_suites
from workflow_resources import Disposable, Owner, ResourceError, Resources

ROOT = Path(__file__).resolve().parent.parent


class FakeDocker:
    def __init__(self) -> None:
        self.objects: dict[str, list[dict]] = {
            kind: [] for kind in ("containers", "networks", "volumes", "images")
        }
        self.foreign_users: dict[str, set[str]] = {}
        self.fail_remove = False
        self.removed: list[str] = []

    def add(self, owner: Owner, kind: str, name: str) -> None:
        labels = owner.labels()
        item = {"Id": name, "Name": name, "Labels": labels}
        if kind in {"containers", "images"}:
            item["Config"] = {"Labels": labels}
            item.pop("Labels")
        if kind == "images":
            item["RepoTags"] = [owner.project + "-tests:latest"]
        self.objects[kind].append(item)

    def __call__(self, *args: str) -> str:
        kind = {
            "ps": "containers",
            "inspect": "containers",
            "rm": "containers",
            "network": "networks",
            "volume": "volumes",
            "image": "images",
        }[args[0]]
        if "--filter" in args:
            condition = args[args.index("--filter") + 1]
            if condition.startswith("label="):
                key, value = condition.removeprefix("label=").split("=", 1)
                return "\n".join(
                    str(item["Name"])
                    for item in self.objects[kind]
                    if Resources.labels(item, kind).get(key) == value
                )
            _, value = condition.split("=", 1)
            return "\n".join(self.foreign_users.get(value, set()))
        if "inspect" in args:
            wanted = args[args.index("inspect") + 1 :]
            return json.dumps(
                [
                    item
                    for item in self.objects[kind]
                    if item["Id"] in wanted or item["Name"] in wanted
                ]
            )
        if "rm" in args:
            if self.fail_remove:
                raise ResourceError("synthetic removal failure")
            identifier = args[-1]
            self.removed.append(identifier)
            self.objects[kind] = [item for item in self.objects[kind] if item["Id"] != identifier]
            return ""
        raise AssertionError(args)


class ResourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.owner = Owner.disposable("integration", ROOT)
        self.other = Owner.disposable("integration", ROOT)
        self.fake = FakeDocker()

    def populate(self, owner: Owner | None = None) -> None:
        owner = owner or self.owner
        for kind in self.fake.objects:
            self.fake.add(owner, kind, owner.project + "-" + kind)

    def test_exact_project_cleans_stale_network_volume_orphans_and_images(self) -> None:
        self.populate()
        self.populate(self.other)
        other = copy.deepcopy(
            {
                k: [
                    v
                    for v in values
                    if Resources.labels(v, k)["io.florabase.workflow.owner"] == self.other.identity
                ]
                for k, values in self.fake.objects.items()
            }
        )
        Resources(self.owner, self.fake).clean()
        self.assertEqual(self.fake.objects, other)
        Resources(self.owner, self.fake).clean()  # already clean, idempotent
        self.assertEqual(len(self.fake.removed), 4)

    def test_partial_creation_is_cleaned(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "creation failed"):
            with Disposable(self.owner, self.fake):
                self.fake.add(self.owner, "networks", "partial-network")
                self.fake.add(self.owner, "volumes", "partial-volume")
                raise RuntimeError("creation failed")
        self.assertTrue(all(not values for values in self.fake.objects.values()))

    def test_success_failure_and_caught_interruptions_cleanup(self) -> None:
        for failure in (None, RuntimeError("tests failed"), SystemExit(130), SystemExit(143)):
            with self.subTest(failure=failure):
                self.fake = FakeDocker()
                if failure:
                    with self.assertRaises(type(failure)):
                        with Disposable(self.owner, self.fake):
                            self.populate()
                            raise failure
                else:
                    with Disposable(self.owner, self.fake):
                        self.populate()
                self.assertTrue(all(not values for values in self.fake.objects.values()))
        for number in (signal.SIGINT, signal.SIGTERM):
            with self.assertRaises(SystemExit) as error:
                Disposable.interrupt(number, None)
            self.assertEqual(error.exception.code, 128 + number)

    def test_actual_caught_int_term_unwind_and_restore_handlers(self) -> None:
        for number in (signal.SIGINT, signal.SIGTERM):
            original = signal.getsignal(number)
            self.fake = FakeDocker()
            with self.assertRaises(SystemExit) as error:
                with Disposable(self.owner, self.fake):
                    self.populate()
                    os.kill(os.getpid(), number)
            self.assertEqual(error.exception.code, 128 + number)
            self.assertEqual(signal.getsignal(number), original)
            self.assertTrue(all(not value for value in self.fake.objects.values()))

    def test_unknown_ownership_fails_before_any_removal(self) -> None:
        self.populate()
        self.fake.objects["volumes"][0]["Labels"].pop("io.florabase.workflow.owner")
        with self.assertRaisesRegex(ResourceError, "ownership unproved"):
            Resources(self.owner, self.fake).clean()
        self.assertEqual(self.fake.removed, [])

    def test_foreign_volume_or_network_user_fails_before_mutation(self) -> None:
        for kind in ("volumes", "networks"):
            with self.subTest(kind=kind):
                self.fake = FakeDocker()
                self.populate()
                self.fake.foreign_users[self.fake.objects[kind][0]["Name"]] = {"foreign-container"}
                with self.assertRaisesRegex(ResourceError, "foreign container"):
                    Resources(self.owner, self.fake).clean()
                self.assertEqual(self.fake.removed, [])

    def test_shared_image_is_retained(self) -> None:
        self.populate()
        image = self.fake.objects["images"][0]
        image["RepoTags"].append("persistent-frontend:latest")
        Resources(self.owner, self.fake).clean()
        self.assertEqual(self.fake.objects["images"], [image])

    def test_cleanup_failure_does_not_report_gate_success(self) -> None:
        with self.assertRaisesRegex(ResourceError, "removal failure"):
            with Disposable(self.owner, self.fake):
                self.populate()
                self.fake.fail_remove = True

    def test_persistent_roles_and_invalid_or_another_quality_identity_refuse(self) -> None:
        for role in ("dev", "review", "uat", "prod", "preview", "unknown"):
            with self.assertRaises(ResourceError):
                Resources(Owner("florabase", role, str(ROOT), "test"), self.fake)
        owner = Owner.quality(ROOT, Path("/tmp/worktree-A"))
        wrong = Owner(owner.project, owner.role, owner.source, "/tmp/worktree-B")
        with self.assertRaises(ResourceError):
            Resources(wrong, self.fake)

    def test_legacy_quality_requires_exact_metadata_project_and_known_compose_keys(self) -> None:
        owner = Owner.quality(ROOT, Path("/tmp/quality-metadata"))
        self.fake.add(owner, "volumes", owner.project + "_frontend_node_modules")
        item = self.fake.objects["volumes"][0]
        item["Labels"] = {
            "com.docker.compose.project": owner.project,
            "com.docker.compose.volume": "frontend_node_modules",
        }
        Resources(owner, self.fake).clean()
        self.assertEqual(self.fake.objects["volumes"], [])
        self.fake.add(owner, "volumes", owner.project + "_unrecognized")
        self.fake.objects["volumes"][0]["Labels"] = {
            "com.docker.compose.project": owner.project,
            "com.docker.compose.volume": "unrecognized",
        }
        with self.assertRaises(ResourceError):
            Resources(owner, self.fake).clean()

    def test_recovery_refuses_changed_source(self) -> None:
        self.populate()
        changed = Owner(
            self.owner.project, self.owner.role, "/tmp/other-worktree", self.owner.identity
        )
        with self.assertRaises(ResourceError):
            Resources(changed, self.fake).clean()

    def test_runner_integration_migration_success_and_failure_retire(self) -> None:
        # Commands are real runner orchestration; Docker metadata/removal alone is simulated.
        for role in ("integration", "feature-migration"):
            for failure in (False, True):
                with self.subTest(role=role, failure=failure):
                    self.fake = FakeDocker()

                    def context(owner: Owner) -> Disposable:
                        self.owner = owner
                        return Disposable(owner, self.fake)

                    def command(*args: object, failure: bool = failure, **kwargs: object) -> None:
                        self.populate()
                        if failure:
                            raise subprocess.CalledProcessError(7, ["synthetic-tests"])

                    with (
                        patch("disposable_workflow.Disposable", side_effect=context),
                        patch("disposable_workflow.subprocess.run", side_effect=command),
                        patch("disposable_workflow.base_revision", return_value="0001"),
                    ):
                        if failure:
                            with self.assertRaises(subprocess.CalledProcessError):
                                execute(role, base="base")
                        else:
                            execute(role, base="base")
                    self.assertTrue(all(not v for v in self.fake.objects.values()))

    def test_integration_selection_refuses_options_escape_and_missing_files(self) -> None:
        for path in (
            "--disable-security",
            "../../data",
            "backend/tests/test_schedule.py",
            "backend/tests/integration/no.py",
        ):
            with self.assertRaises(ResourceError):
                safe_suites([path], ROOT)
        self.assertEqual(
            safe_suites(["backend/tests/integration/test_schedule.py"], ROOT),
            ["tests/integration/test_schedule.py"],
        )


if __name__ == "__main__":
    unittest.main()
