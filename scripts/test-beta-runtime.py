#!/usr/bin/env python3
"""Offline BETA-RUNTIME-001 checks: stack contract and controller safety rules.

Standard library only so the controller rules also run under the DSM-equivalent Python 3.8:
  python3 scripts/test-beta-runtime.py [--compose "docker compose"] [--controller-only]
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable, Iterator

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "deploy" / "beta"
COMPOSE: list[str] = ["docker", "compose"]


def load_controller() -> Any:
    # FLORABASECTL_UNDER_TEST runs these rules against another controller copy (for example a
    # reviewed older commit) to prove a regression test fails there.
    path = Path(os.environ.get("FLORABASECTL_UNDER_TEST") or BUNDLE / "florabasectl.py")
    spec = importlib.util.spec_from_file_location("florabasectl", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ctl = load_controller()


def digest(seed: str) -> str:
    return "sha256:" + hashlib.sha256(seed.encode()).hexdigest()


def manifest() -> dict[str, Any]:
    pg_index = digest("pg-index")
    images = {}
    for name in ("backend", "frontend"):
        index = digest(name + "-index")
        images[name] = {
            "reference": "ghcr.io/alessandrorossato/florabase-" + name + "@" + index,
            "index_digest": index,
            "platform_digest": digest(name + "-platform"),
            "platform": "linux/amd64",
        }
    return {
        "schema_version": 2,
        "distribution": "registry-candidate",
        "version": "0.1.0-beta.1",
        "source": {"url": ctl.SOURCE_URL, "revision": "a" * 40, "dirty": False},
        "platforms": ["linux/amd64"],
        "alembic_head": "20261013_0042",
        "postgresql": {
            "repository": "ghcr.io/alessandrorossato/florabase-postgres",
            "version": "18.6-alpine-florabase.1",
            "reference": "ghcr.io/alessandrorossato/florabase-postgres:18.6-alpine-florabase.1@"
            + pg_index,
            "index_digest": pg_index,
            "platform_digest": digest("pg-platform"),
            "platform": "linux/amd64",
            "source_date_epoch": 1762387200,
            "upstream": {
                "repository": "docker.io/library/postgres",
                "version": "18.6-alpine",
                "reference": "docker.io/library/postgres:18.6-alpine@" + digest("upstream-index"),
                "index_digest": digest("upstream-index"),
                "platform_digest": digest("upstream-platform"),
                "platform": "linux/amd64",
            },
        },
        "images": images,
        "build_inputs": {},
        "workflow": {"run_id": "1", "run_attempt": "1"},
    }


@contextlib.contextmanager
def environment(**values: str) -> Iterator[None]:
    saved = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class ManifestRules(unittest.TestCase):
    def test_valid_manifest(self) -> None:
        ctl.validate_manifest(manifest())

    def test_rejections(self) -> None:
        cases: dict[str, Callable[[dict[str, Any]], object]] = {
            "dirty": lambda m: m["source"].update(dirty=True),
            "distribution": lambda m: m.update(distribution="local-candidate"),
            "tag reference": lambda m: m["images"]["backend"].update(
                reference="ghcr.io/alessandrorossato/florabase-backend:0.1.0-beta.1"
            ),
            "digest mismatch": lambda m: m["images"]["frontend"].update(
                index_digest=digest("other")
            ),
            "foreign registry": lambda m: m["images"]["backend"].update(
                reference="docker.io/evil/florabase-backend@"
                + m["images"]["backend"]["index_digest"]
            ),
            "arm64": lambda m: m.update(platforms=["linux/arm64"]),
            "postgres tag": lambda m: m["postgresql"].update(reference="postgres:18.6-alpine"),
            "loopback without test": lambda m: m["images"]["backend"].update(
                reference="127.0.0.1:5000/florabase-backend@"
                + m["images"]["backend"]["index_digest"]
            ),
        }
        for name, mutate in cases.items():
            with self.subTest(name):
                value = manifest()
                mutate(value)
                with self.assertRaises(ctl.Refusal):
                    ctl.validate_manifest(value)

    def test_test_candidate_needs_mode_and_loopback(self) -> None:
        value = manifest()
        value["distribution"] = "test-candidate"
        for name in ("backend", "frontend"):
            entry = value["images"][name]
            entry["reference"] = "127.0.0.1:5000/florabase-" + name + "@" + entry["index_digest"]
        ctl.validate_manifest(value, test_candidate=True)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "m.json"
            path.write_text(json.dumps(value))
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            with environment(FLORABASECTL_TEST_MODE="0"), self.assertRaises(ctl.Refusal):
                ctl.load_manifest(path, sha, True)
            with environment(FLORABASECTL_TEST_MODE="1"):
                self.assertEqual(ctl.load_manifest(path, sha, True)[1], sha)

    def test_operator_digest_is_mandatory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "m.json"
            path.write_text(json.dumps(manifest()))
            with self.assertRaises(ctl.Refusal):
                ctl.load_manifest(path, "0" * 64, False)
            with self.assertRaises(ctl.Refusal):
                ctl.load_manifest(path, "short", False)


class PureRules(unittest.TestCase):
    def test_classify(self) -> None:
        base = {"heads": ["b"], "known": [], "tables": [], "current": []}
        self.assertEqual(ctl.classify(base), "empty")
        self.assertEqual(ctl.classify(dict(base, tables=["users"])), "unmanaged")
        self.assertEqual(ctl.classify(dict(base, current=["x"], tables=["t"])), "unknown")
        self.assertEqual(
            ctl.classify(dict(base, current=["a"], known=["a"], tables=["t"])), "behind"
        )
        self.assertEqual(
            ctl.classify(dict(base, current=["b"], known=["b"], tables=["t"])), "current"
        )

    def test_repository_normalization(self) -> None:
        self.assertEqual(
            ctl.normalize_repository("docker.io/library/postgres:18.6-alpine"), "postgres"
        )
        self.assertEqual(ctl.normalize_repository("postgres"), "postgres")
        self.assertEqual(
            ctl.normalize_repository("127.0.0.1:5000/florabase-backend"),
            "127.0.0.1:5000/florabase-backend",
        )

    def test_versions(self) -> None:
        self.assertEqual(ctl.parse_version("Docker Compose version v2.20.1"), (2, 20, 1))
        self.assertGreaterEqual(ctl.parse_version("24.0.2")[:2], ctl.MIN_ENGINE)
        self.assertLess(ctl.parse_version("2.19.1")[:2], ctl.MIN_COMPOSE)

    def test_retention_keeps_newest_daily_weekly_and_upgrades(self) -> None:
        sets = []
        for day in range(1, 31):
            sets.append(
                {
                    "set_id": f"d{day:02d}",
                    "kind": "manual",
                    "created_at": f"2026-10-{day:02d}T03:00:00Z",
                }
            )
        sets.append({"set_id": "up", "kind": "pre-upgrade", "created_at": "2026-09-01T03:00:00Z"})
        keep, remove = ctl.select_retained(sets, daily=7, weekly=4, upgrades=1)
        self.assertIn("d30", keep)
        self.assertIn("up", keep)
        self.assertEqual(len([s for s in keep if s.startswith("d")]), len(set(keep)) - 1)
        self.assertTrue({"d24", "d25", "d26", "d27", "d28", "d29", "d30"} <= set(keep))
        self.assertIn("d02", remove)
        self.assertEqual(sorted(keep + remove), sorted(s["set_id"] for s in sets))
        self.assertEqual(ctl.select_retained(sets[:1], 0, 0, 0), (["d01"], []))

    def test_redaction(self) -> None:
        self.assertEqual(ctl.redact("rest:https://user:pw@host/repo"), "rest:https://***@host/repo")

    def test_fault_point_is_inert_outside_test_mode(self) -> None:
        with environment(FLORABASECTL_TEST_MODE="0", FLORABASECTL_TEST_FAULT="validated"):
            ctl.fault_point("validated")

    def test_atomic_json_is_private(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "x.json"
            ctl.write_json(path, {"a": 1})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(ctl.read_json(path), {"a": 1})


class HttpAcceptance(unittest.TestCase):
    """The shell, its script assets and API 404s are checked on every acceptance run."""

    SHELL = (
        b'<!doctype html><html><head><script src="/appearance.js"></script>'
        b'<script type="module" crossorigin src="/assets/index-abc.js"></script></head>'
        b'<body><div id="root"></div></body></html>'
    )
    CURRENT = {"version": "0.1.0-beta.1", "source_revision": "a" * 40}

    def responses(self, **overrides: tuple[int, str, bytes]) -> dict[str, tuple[int, str, bytes]]:
        release = json.dumps({"version": "0.1.0-beta.1", "revision": "a" * 40}).encode()
        values = {
            "/healthz": (200, "text/plain", b"ok"),
            "/api/v1/health": (200, "application/json", b"{}"),
            "/api/v1/ready": (200, "application/json", b"{}"),
            "/release.json": (200, "application/json", release),
            "/": (200, "text/html", self.SHELL),
            "/appearance.js": (200, "application/javascript", b""),
            "/assets/index-abc.js": (200, "application/javascript", b""),
            "/api/v1/florabase-acceptance-unknown": (404, "application/json", b"{}"),
            "/api/v1/auth/session": (401, "application/json", b"{}"),
        }
        values.update({key.replace("_", "/"): value for key, value in overrides.items()})
        return values

    def run_acceptance(self, values: dict[str, tuple[int, str, bytes]]) -> None:
        def fake(url: str, method: str = "GET", body: Any = None, headers: Any = None) -> Any:
            status, content_type, payload = values[url[len("http://x") :]]
            return status, {"Content-Type": content_type}, payload

        original = ctl.http_request
        ctl.http_request = fake
        try:
            ctl.http_acceptance("http://x", self.CURRENT)
        finally:
            ctl.http_request = original

    def test_healthy_release_passes(self) -> None:
        self.run_acceptance(self.responses())

    def test_spa_fallback_for_api_is_refused(self) -> None:
        values = self.responses()
        values["/api/v1/florabase-acceptance-unknown"] = (200, "text/html", self.SHELL)
        with self.assertRaisesRegex(ctl.Failure, "unknown API path"):
            self.run_acceptance(values)

    def test_missing_shell_or_asset_is_refused(self) -> None:
        values = self.responses()
        values["/"] = (200, "text/html", b"<html>maintenance</html>")
        with self.assertRaisesRegex(ctl.Failure, "application shell"):
            self.run_acceptance(values)
        values = self.responses()
        values["/assets/index-abc.js"] = (200, "text/html", self.SHELL)
        with self.assertRaisesRegex(ctl.Failure, "index-abc.js"):
            self.run_acceptance(values)


def recovery_set(
    directory: Path, set_id: str | None = None, created_at: str = "2026-11-01T03:00:00Z"
) -> None:
    """A structurally valid synthetic set; destructive tests use only temporary directories."""
    directory.mkdir(mode=0o700)
    directory.chmod(0o700)  # as the controller creates sets, independent of the caller's umask
    for name, data in (
        ("database.dump", b"dump"),
        ("attachments.tar", b"tar"),
        ("compose.yaml", b"compose"),
    ):
        (directory / name).write_bytes(data)
    artifacts = {
        name: {"sha256": hashlib.sha256((directory / name).read_bytes()).hexdigest()}
        for name in ("database.dump", "attachments.tar", "compose.yaml")
    }
    name = directory.name if set_id is None else set_id
    kind = "pre-upgrade" if "-pre-upgrade-" in name else "manual"
    metadata = {"artifacts": artifacts, "set_id": name, "kind": kind, "created_at": created_at}
    (directory / "metadata.json").write_text(json.dumps(metadata))
    write_sums(directory)


def write_sums(directory: Path) -> None:
    (directory / "SHA256SUMS").write_text(
        "".join(
            hashlib.sha256((directory / name).read_bytes()).hexdigest() + "  " + name + "\n"
            for name in ("attachments.tar", "compose.yaml", "database.dump", "metadata.json")
        )
    )


def set_name(day: int, kind: str = "manual") -> str:
    return f"202610{day:02d}T030000Z-{kind}-{day:06x}"


class RecoverySets(unittest.TestCase):
    def test_checksums(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "set"
            recovery_set(directory)
            ctl.verify_checksums(directory)
            (directory / "database.dump").write_bytes(b"tampered")
            with self.assertRaises(ctl.Failure):
                ctl.verify_checksums(directory)

    def test_unsafe_or_incomplete_sums(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "set"
            recovery_set(directory)
            sums = directory / "SHA256SUMS"
            lines = sums.read_text().splitlines()
            sums.write_text("\n".join(lines[1:]) + "\n")
            with self.assertRaises(ctl.Failure):
                ctl.verify_checksums(directory)
            sums.write_text(lines[0] + "\n" + "0" * 64 + "  ../escape\n")
            with self.assertRaises(ctl.Refusal):
                ctl.verify_checksums(directory)


class Retention(unittest.TestCase):
    """R2: deletion targets come only from verified, contained directory identities."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.root = self.base / "install"
        self.controller = ctl.Controller(self.root, FakeRunner())
        self.backups = self.controller.layout.backups
        self.backups.mkdir(parents=True)
        self.backups.chmod(0o700)  # the protected root init creates
        self.controller.layout.state.mkdir()
        # Victims outside and beside the backup root must survive every attack below.
        self.victims = [self.base / "victim", self.root / "postgres", self.backups / "unrelated"]
        for victim in self.victims:
            victim.mkdir()
            (victim / "keep").write_text("data")

    def tearDown(self) -> None:
        if self.controller._lock is not None:
            self.controller._lock.close()
        self.temporary.cleanup()

    def retention(self, *args: Any) -> list[str]:
        try:
            return list(self.controller.retention(*args))
        finally:
            if self.controller._lock is not None:
                self.controller._lock.close()
                self.controller._lock = None

    def assert_victims_intact(self) -> None:
        for victim in self.victims:
            self.assertEqual((victim / "keep").read_text(), "data", victim)

    def valid(self, day: int, kind: str = "manual") -> Path:
        directory = self.backups / set_name(day, kind)
        recovery_set(directory, created_at=f"2026-10-{day:02d}T03:00:00Z")
        return Path(directory)

    def test_traversal_absolute_and_mismatched_ids_are_never_deleted(self) -> None:
        self.valid(30)
        attacks = {
            set_name(1): "../../victim",
            set_name(2): str(self.base / "victim"),
            set_name(3): "../postgres",
            set_name(4): set_name(5),
        }
        for directory, claimed in attacks.items():
            recovery_set(
                self.backups / directory, set_id=claimed, created_at="2026-09-01T03:00:00Z"
            )
        (self.backups / "unrelated" / "metadata.json").write_text(
            json.dumps(
                {"set_id": "../victim", "kind": "manual", "created_at": "2026-01-01T00:00:00Z"}
            )
        )
        removed = self.retention(1, 0, 0, True)
        self.assertEqual(removed, [])
        self.assert_victims_intact()
        for directory in attacks:
            self.assertTrue((self.backups / directory).is_dir(), "unverifiable set kept untouched")

    def test_symlinked_set_pointing_outside_is_refused(self) -> None:
        self.valid(30)
        outside = self.base / "outside-set"
        recovery_set(outside, set_id=set_name(1), created_at="2026-09-01T03:00:00Z")
        (self.backups / set_name(1)).symlink_to(outside)
        self.assertEqual(self.retention(1, 0, 0, True), [])
        self.assertTrue((outside / "database.dump").exists())
        self.assert_victims_intact()

    def test_tampered_missing_or_invalid_metadata_is_not_eligible(self) -> None:
        self.valid(30)
        tampered = self.valid(1)
        (tampered / "database.dump").write_bytes(b"changed")
        missing = self.valid(2)
        (missing / "metadata.json").unlink()
        wrong_kind = self.valid(3)
        metadata = json.loads((wrong_kind / "metadata.json").read_text())
        metadata["kind"] = "pre-upgrade"
        (wrong_kind / "metadata.json").write_text(json.dumps(metadata))
        write_sums(wrong_kind)
        bad_sums = self.valid(4)
        (bad_sums / "SHA256SUMS").write_text("0" * 64 + "  ../../victim/keep\n")
        writable = self.valid(5)
        writable.chmod(0o777)
        self.assertEqual(self.retention(1, 0, 0, True), [])
        for directory in (tampered, missing, wrong_kind, bad_sums, writable):
            self.assertTrue(directory.is_dir())
        self.assert_victims_intact()

    def test_malformed_policy_is_refused(self) -> None:
        self.valid(30)
        for policy in ((0, 0, 0), (-1, 4, 3), (7, -1, 3), (7, 4, 99999), (True, 4, 3)):
            with self.subTest(policy), self.assertRaises(ctl.Refusal):
                self.retention(*policy, True)
        self.assertTrue((self.backups / set_name(30)).is_dir())

    def test_last_valid_set_survives_and_retention_is_idempotent(self) -> None:
        for day in range(1, 11):
            self.valid(day)
        first = self.retention(1, 0, 0, True)
        self.assertEqual(sorted(first), sorted(set_name(day) for day in range(1, 10)))
        self.assertEqual(self.retention(1, 0, 0, True), [])
        self.assertTrue((self.backups / set_name(10)).is_dir())
        self.assert_victims_intact()

    def substitute_after_validation(self, target: Path, replace: Any) -> None:
        """Swap the target right after deletion-time validation passes (TOCTOU attempt)."""
        original = ctl.inspect_set
        calls = {"count": 0}

        def racing(root: Path, name: str) -> Any:
            result = original(root, name)
            if name == target.name:
                calls["count"] += 1
                if calls["count"] == 2:  # 1st: listing; 2nd: inside remove_set
                    replace(Path(root) / name)
            return result

        ctl.inspect_set = racing
        self.addCleanup(setattr, ctl, "inspect_set", original)

    def test_symlink_substitution_after_validation_fails_closed(self) -> None:
        self.valid(30)
        target = self.valid(1)
        outside = self.base / "victim"

        def to_symlink(path: Path) -> None:
            path.rename(self.base / "moved-away")
            path.symlink_to(outside)

        self.substitute_after_validation(target, to_symlink)
        with self.assertRaises(ctl.Failure):
            self.retention(1, 0, 0, True)
        self.assertTrue(target.is_symlink())
        self.assertTrue((self.base / "moved-away" / "database.dump").exists())
        self.assert_victims_intact()

    def test_directory_substitution_after_validation_fails_closed(self) -> None:
        self.valid(30)
        target = self.valid(1)

        def to_other_directory(path: Path) -> None:
            path.rename(self.base / "moved-away")
            path.mkdir(mode=0o700)
            (path / "keep").write_text("attacker-chosen data")

        self.substitute_after_validation(target, to_other_directory)
        with self.assertRaisesRegex(ctl.Failure, "changed while it was being verified"):
            self.retention(1, 0, 0, True)
        self.assertEqual((target / "keep").read_text(), "attacker-chosen data")
        self.assertTrue((self.base / "moved-away" / "database.dump").exists())
        self.assert_victims_intact()

    def test_unprotected_backup_root_refuses_deletion(self) -> None:
        self.valid(30)
        self.valid(1)
        self.backups.chmod(0o755)
        with self.assertRaisesRegex(ctl.Failure, "mode 0700"):
            self.retention(1, 0, 0, True)
        self.assertTrue((self.backups / set_name(1)).is_dir())

    def test_dry_run_deletes_nothing(self) -> None:
        for day in range(1, 4):
            self.valid(day)
        self.assertEqual(len(self.retention(1, 0, 0, False)), 2)
        self.assertEqual(len(list(self.backups.glob("202610*"))), 3)


class BindAddress(unittest.TestCase):
    """R3: the published address is not configurable anywhere in the controller."""

    def test_bind_option_is_gone(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            ctl.parser().parse_args(
                [
                    "--root",
                    "/srv/x",
                    "init",
                    "--origin",
                    "https://florabase.example.invalid",
                    "--bind-address",
                    "0.0.0.0",
                ]
            )

    def test_rendered_env_never_sets_an_address(self) -> None:
        controller = ctl.Controller(Path("/srv/florabase"), FakeRunner())
        installation = {
            "canonical_origin": "https://x.example.invalid",
            "bind_address": "0.0.0.0",  # a stale/edited value is ignored, not rendered
            "http_port": 8080,
            "limits": {
                "db_memory": "1g",
                "db_cpus": "0",
                "backend_memory": "1g",
                "backend_cpus": "0",
            },
        }
        images = {
            "backend": "b",
            "frontend": "f",
            "postgres": "p",
            "version": "v",
            "alembic_head": "h",
        }
        rendered = controller.render_env(installation, images, controller.layout).decode()
        self.assertNotIn("BIND", rendered)
        self.assertNotIn("0.0.0.0", rendered)


class FakeRunner:
    compose = ["docker", "compose"]

    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, argv: list[str], **_: Any) -> str:
        self.commands.append(list(argv))
        return ""

    def docker_json(self, *args: str) -> Any:
        raise ctl.Failure("no docker in offline tests")


class ControllerRules(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "florabase"
        self.runner = FakeRunner()
        self.controller = ctl.Controller(self.root, self.runner)
        layout = self.controller.layout
        for path in (layout.state, layout.stack, layout.backups, layout.secrets):
            path.mkdir(parents=True)
        self.installation = {
            "format": 1,
            "installation_id": "1" * 32,
            "canonical_origin": "https://florabase.example.invalid",
            "http_port": 8080,
            "database": {"name": "florabase", "user": "florabase"},
            "limits": {
                "db_memory": "1g",
                "db_cpus": "0",
                "backend_memory": "768m",
                "backend_cpus": "0",
            },
            "reference": {},
        }
        ctl.write_json(layout.installation_file, self.installation)
        record = ctl.release_record(manifest(), "f" * 64)
        compose = (BUNDLE / "compose.yaml").read_bytes()
        record["stack_sha256"] = self.controller.write_stack(
            self.installation, ctl.pins(record), compose
        )
        ctl.write_json(layout.current_file, record)
        self.current = record
        self.manifest_path = Path(self.temporary.name) / "next.json"
        self.next = manifest()
        self.next["images"]["backend"]["reference"] = (
            "ghcr.io/alessandrorossato/florabase-backend@" + digest("next")
        )
        self.next["images"]["backend"]["index_digest"] = digest("next")
        self.write_next()
        self.controller.verify_release = lambda _manifest: None
        self.controller.check_volumes = lambda *_args: None
        self.probe = {
            "heads": ["n"],
            "known": ["20261013_0042"],
            "tables": ["t"],
            "current": ["20261013_0042"],
        }
        self.controller.stack.probe = lambda image=None, counts=False: copy.deepcopy(self.probe)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_next(self) -> None:
        self.manifest_path.write_text(json.dumps(self.next))

    def promote(self, *extra: str) -> None:
        sha = hashlib.sha256(self.manifest_path.read_bytes()).hexdigest()
        args = ctl.parser().parse_args(
            [
                "--root",
                str(self.root),
                "promote",
                "--manifest",
                str(self.manifest_path),
                "--manifest-sha256",
                sha,
            ]
            + list(extra)
        )
        try:
            self.controller.promote(args)
        finally:
            if self.controller._lock is not None:
                self.controller._lock.close()
                self.controller._lock = None

    def test_rendered_stack_has_no_empty_optional_paths(self) -> None:
        stack = self.controller.layout.stack
        self.assertEqual(
            (stack / "reference.env").read_text(),
            "# Optional read-only reference datasets, rendered by florabasectl.\n",
        )
        env = (stack / ".env").read_text()
        self.assertIn("FLORABASE_BACKEND_IMAGE=" + self.current["images"]["backend"], env)
        self.assertNotIn("SNAPSHOT", env)
        self.assertNotIn("PASSWORD", env)
        rendered = ctl.Controller.render_reference(
            dict(self.installation, reference={"wfo": {"file": "wfo.sqlite"}})
        ).decode()
        self.assertIn(
            "FLORABASE_WFO_SNAPSHOT_PATH=/var/lib/florabase/reference/wfo.sqlite", rendered
        )
        self.assertNotIn("WCVP", rendered)

    def test_drift_refused(self) -> None:
        env = self.controller.layout.stack / ".env"
        env.write_text(env.read_text().replace("8080", "9090"))
        with self.assertRaisesRegex(ctl.Refusal, "differ"):
            self.promote("--confirm-migration")

    def test_postgres_identity_change_refused(self) -> None:
        self.next["postgresql"]["platform_digest"] = digest("rebuilt")
        self.write_next()
        with self.assertRaisesRegex(ctl.Refusal, "PostgreSQL"):
            self.promote("--confirm-migration")

    def test_unknown_or_ahead_schema_refused(self) -> None:
        self.probe["current"] = ["from_the_future"]
        with self.assertRaisesRegex(ctl.Refusal, "unknown"):
            self.promote("--confirm-migration")
        self.assertFalse(self.controller.layout.operation_file.exists())

    def test_migration_needs_confirmation(self) -> None:
        with self.assertRaisesRegex(ctl.Refusal, "confirm-migration"):
            self.promote()
        self.assertFalse(self.controller.layout.operation_file.exists())

    def test_same_pair_refused(self) -> None:
        self.next = manifest()
        self.write_next()
        with self.assertRaisesRegex(ctl.Refusal, "already deployed"):
            self.promote()

    def test_active_operation_refuses_promote_and_lock_is_exclusive(self) -> None:
        ctl.write_json(
            self.controller.layout.operation_file,
            {"id": "op", "status": "in_progress", "phase": "migrated", "phase_index": 3},
        )
        with self.assertRaisesRegex(ctl.Refusal, "resume or abort"):
            self.promote("--confirm-migration")
        ctl.write_json(
            self.controller.layout.operation_file,
            {"id": "op", "status": "failed", "phase": "pinned", "phase_index": 4},
        )
        with self.assertRaisesRegex(ctl.Refusal, "after-failed"):
            self.promote("--confirm-migration")
        first = ctl.Controller(self.root, self.runner)
        first.lock()
        try:
            with self.assertRaisesRegex(ctl.Refusal, "host lock"):
                ctl.Controller(self.root, self.runner).lock()
        finally:
            assert first._lock is not None
            first._lock.close()

    def test_failed_promotion_stops_writers_and_records_journal(self) -> None:
        def broken_backup(*_args: Any, **_kwargs: Any) -> str:
            raise ctl.Failure("disk full")

        self.controller.backup = broken_backup
        self.controller.database_release = lambda candidates: candidates[0]
        with self.assertRaisesRegex(ctl.Failure, "Writers are stopped"):
            self.promote("--confirm-migration")
        operation = ctl.read_json(self.controller.layout.operation_file)
        self.assertEqual((operation["status"], operation["phase"]), ("failed", "quiesced"))
        stops = [c for c in self.runner.commands if c[-3:] == ["stop", "frontend", "backend"]]
        self.assertGreaterEqual(len(stops), 2)
        events = [
            json.loads(line)["event"]
            for line in self.controller.layout.journal_file.read_text().splitlines()
        ]
        self.assertEqual(events[-3:], ["promote-start", "phase", "promote-failed"])

    def test_abort_refuses_changed_schema(self) -> None:
        ctl.write_json(
            self.controller.layout.operation_file,
            {
                "id": "op",
                "status": "failed",
                "phase": "pinned",
                "phase_index": 4,
                "previous": self.current,
                "backup": "set",
            },
        )
        self.probe["current"] = ["n"]
        self.probe["known"] = []
        with self.assertRaisesRegex(ctl.Refusal, "cannot downgrade"):
            self.controller.abort()

    def test_restore_replace_requires_exact_confirmation(self) -> None:
        args = ctl.parser().parse_args(
            [
                "--root",
                str(self.root),
                "restore-replace",
                "20261103T000000Z-manual-abcdef",
                "--confirm-installation",
                "wrong",
                "--confirm-database",
                "florabase",
            ]
        )
        with self.assertRaisesRegex(ctl.Refusal, "confirm-installation"):
            self.controller.restore_replace(args)

    def test_foreign_or_plain_volume_is_never_adopted(self) -> None:
        layout = self.controller.layout
        volumes: dict[str, dict[str, Any]] = {
            "florabase-prod_postgres_data": {"Options": None},
            "florabase-prod_attachment_data": {
                "Options": {"type": "none", "o": "bind", "device": str(layout.media)}
            },
        }

        class VolumeRunner(FakeRunner):
            def run(self, argv: list[str], **_: Any) -> str:
                return "\n".join(volumes)

            def docker_json(self, *args: str) -> Any:
                return [volumes[args[-1]]]

        controller = ctl.Controller(self.root, VolumeRunner())
        with self.assertRaisesRegex(ctl.Refusal, "plain Docker volume"):
            controller.check_volumes()
        volumes["florabase-prod_postgres_data"] = {
            "Options": {"type": "none", "o": "bind", "device": "/elsewhere"}
        }
        with self.assertRaisesRegex(ctl.Refusal, "/elsewhere"):
            controller.check_volumes()
        volumes["florabase-prod_postgres_data"] = {
            "Options": {"type": "none", "o": "bind", "device": str(layout.postgres)}
        }
        controller.check_volumes()

    def test_interrupted_replacement_restore_blocks_mutation(self) -> None:
        ctl.write_json(self.controller.layout.restore_marker, {"set_id": "s"})
        with self.assertRaisesRegex(ctl.Refusal, "re-run restore-replace"):
            self.promote("--confirm-migration")
        for action in (self.controller.resume, self.controller.abort, self.controller.apply):
            with self.subTest(action.__name__), self.assertRaisesRegex(ctl.Refusal, "interrupted"):
                try:
                    action()
                finally:
                    if self.controller._lock is not None:
                        self.controller._lock.close()
                        self.controller._lock = None

    def test_init_refuses_adoption(self) -> None:
        args = ctl.parser().parse_args(
            ["--root", str(self.root), "init", "--origin", "https://florabase.example.invalid"]
        )
        with self.assertRaises(ctl.Refusal):
            ctl.Controller(self.root, self.runner).init(args)


# Everything BETA-RUNTIME-001 adds is public: it must not describe any real installation.
class GitError(AssertionError):
    """A failed or ambiguous Git read: the disclosure gate refuses rather than passes."""


def git_in(repo: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True, errors="replace"
        )
    except OSError as error:
        raise GitError(f"git {args[0]}: {error}") from error
    if result.returncode:
        raise GitError(f"git {' '.join(args[:3])} failed: {result.stderr.strip()[:300]}")
    return result.stdout


def disclosure_base(repo: Path) -> str:
    """The feature's fork point, never an arbitrary history range."""
    override = os.environ.get("FLORABASE_DISCLOSURE_BASE")
    if override:
        return git_in(repo, "rev-parse", "--verify", override + "^{commit}").strip()
    for ref in ("origin/main", "main"):
        try:
            git_in(repo, "rev-parse", "--verify", "--quiet", ref + "^{commit}")
        except GitError:
            continue
        return git_in(repo, "merge-base", "HEAD", ref).strip()
    parents = git_in(repo, "rev-list", "--parents", "-n", "1", "HEAD").split()
    if len(parents) == 3:
        return parents[1]  # CI pull-request merge checkout: first parent is the PR base
    if len(parents) == 2:
        return parents[1]  # main without a main ref (shallow CI): the newest commit only
    raise GitError("cannot determine the feature base; set FLORABASE_DISCLOSURE_BASE")


def added_lines(repo: Path, scope: str, *diff: str) -> list[tuple[str, str, int, str]]:
    """Added lines of one diff, read from Git objects (index/commits), not the worktree."""
    output = git_in(
        repo, "diff", "--unified=0", "--no-color", "--no-ext-diff", "--text", "-M", *diff, "--"
    )
    found: list[tuple[str, str, int, str]] = []
    path: str | None = None
    number = 0
    for line in output.splitlines():
        if line.startswith("+++ "):
            path = None if line == "+++ /dev/null" else line[len("+++ b/") :]
        elif line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            if match is None:
                raise GitError("unparseable diff hunk: " + line)
            number = int(match.group(1))
        elif line.startswith("+") and path is not None:
            found.append((scope, path, number, line[1:]))
            number += 1
    return found


def disclosure_lines(repo: Path, base: str) -> list[tuple[str, str, int, str]]:
    """Committed feature changes, the staged index, unstaged edits and untracked candidates."""
    lines = added_lines(repo, "committed", base, "HEAD")
    lines += added_lines(repo, "staged", "--cached")
    lines += added_lines(repo, "unstaged")
    for path in git_in(repo, "ls-files", "-z", "--others", "--exclude-standard").split("\0"):
        if path and (repo / path).is_file() and not (repo / path).is_symlink():
            text = (repo / path).read_text(errors="replace").splitlines()
            lines += [("untracked", path, n, line) for n, line in enumerate(text, 1)]
    return lines


def disclosure_findings(repo: Path, base: str) -> list[str]:
    return [
        f"{scope} {path}:{number}: {label}"
        for scope, path, number, line in disclosure_lines(repo, base)
        for label, pattern in DISCLOSURE_PATTERNS.items()
        if re.search(pattern, line)
    ]


# No exemptions: patterns and samples are assembled so that their own source never matches.
DISCLOSURE_PATTERNS = {
    "private or CGNAT IPv4": r"\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01])|"
    r"100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])|169\.254)\.\d{1,3}\.\d{1,3}\b",
    "concrete tailnet name": r"[A-Za-z0-9-]+\.(?!tailnet\.)[A-Za-z0-9-]+\.ts\.net",
    "personal home path": r"/(?:home|Users)/[A-Za-z0-9._-]+",
    "email address": r"[A-Za-z0-9._%+-]+@(?!sha256)[A-Za-z0-9-]+\.[A-Za-z]{2,}",
    "private key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "access token": r"\b(?:g"
    r"hp_|g"
    r"ho_|github"
    r"_pat_|gl"
    r"pat-|AK"
    r"IA|xo"
    r"x[bp]-|s"
    r"k-[A-Za-z0-9]{20})",
    "literal credential": r"(?:POSTGRES_PASSWORD|RESTIC_PASSWORD)=(?!\{|<)[^\s\"']+",
}
SYNTHETIC = {
    "private or CGNAT IPv4": "10.20." + "30.40",
    "concrete tailnet name": "nas.tail" + "1234.ts.net",
    "personal home path": "/ho" + "me/someone/backups",
    "email address": "someone" + "@" + "example.org",
    "access token": "gh" + "p_" + "x" * 20,
    "literal credential": "POSTGRES_" + "PASSWORD=" + "hunter2",
}


def scratch_repository(root: Path) -> Path:
    """A disposable repository with isolated configuration and a main fork point."""
    repo = root / "repo"
    repo.mkdir()
    for args in (("init", "-q", "-b", "main"), ("config", "commit.gpgsign", "false")):
        git_in(repo, *args)
    (repo / "history.md").write_text(
        "old private note " + SYNTHETIC["private or CGNAT IPv4"] + "\n"
    )
    (repo / "README.md").write_text("public\n")
    git_in(repo, "add", "-A")
    git_in(repo, "commit", "-q", "-m", "base")
    git_in(repo, "checkout", "-q", "-b", "feature")
    return repo


class Disclosure(unittest.TestCase):
    """R4: dedicated privacy gate over every changed blob of the feature, staged ones included."""

    def setUp(self) -> None:
        if shutil.which("git") is None:
            self.skipTest(
                "Git unavailable (container run); the host run of this suite is mandatory"
            )
        identity = "runtime-test" + "@" + "example.invalid"
        self.environment = environment(
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_CONFIG_NOSYSTEM="1",
            GIT_AUTHOR_NAME="t",
            GIT_AUTHOR_EMAIL=identity,
            GIT_COMMITTER_NAME="t",
            GIT_COMMITTER_EMAIL=identity,
        )
        self.environment.__enter__()

    def tearDown(self) -> None:
        self.environment.__exit__(None, None, None)

    def test_no_infrastructure_or_secret_disclosure(self) -> None:
        self.assertEqual(disclosure_findings(ROOT, disclosure_base(ROOT)), [])

    def test_scope_is_the_whole_feature_diff(self) -> None:
        """Every change since the fork point, with its provenance; nothing from before it."""
        with tempfile.TemporaryDirectory() as temporary:
            repo = scratch_repository(Path(temporary))
            (repo / "first.md").write_text("first commit\n")
            git_in(repo, "add", "first.md")
            git_in(repo, "commit", "-q", "-m", "first feature commit")
            (repo / "nested").mkdir()
            (repo / "nested" / "second.md").write_text("second commit\n")
            git_in(repo, "add", "nested/second.md")
            git_in(repo, "commit", "-q", "-m", "second feature commit")
            # main moves on after the fork point; comparing with its tip instead of the
            # fork point would report the file it deletes as a feature addition
            git_in(repo, "checkout", "-q", "main")
            git_in(repo, "rm", "-q", "README.md")
            git_in(repo, "commit", "-q", "-m", "main after fork")
            git_in(repo, "checkout", "-q", "feature")
            (repo / "staged.md").write_text("staged\n")
            git_in(repo, "add", "staged.md")
            with (repo / "first.md").open("a") as tracked:
                tracked.write("unstaged\n")
            (repo / "untracked.md").write_text("untracked\n")
            lines = disclosure_lines(repo, disclosure_base(repo))
        self.assertEqual(
            sorted(lines),
            [
                ("committed", "first.md", 1, "first commit"),
                ("committed", "nested/second.md", 1, "second commit"),
                ("staged", "staged.md", 1, "staged"),
                ("unstaged", "first.md", 2, "unstaged"),
                ("untracked", "untracked.md", 1, "untracked"),
            ],
        )

    def test_patterns_detect_synthetic_samples_and_not_their_source(self) -> None:
        for label, sample in SYNTHETIC.items():
            self.assertRegex(sample, DISCLOSURE_PATTERNS[label])
        source = Path(__file__).read_text()
        for label, pattern in DISCLOSURE_PATTERNS.items():
            self.assertIsNone(re.search(pattern, source), label)
        for allowed in ("https://<node>.<tailnet>.ts.net", "127.0.0.1:8080", "@sha256:abc"):
            self.assertFalse(any(re.search(p, allowed) for p in DISCLOSURE_PATTERNS.values()))

    def test_staged_blob_is_scanned_even_when_worktree_is_clean(self) -> None:
        """Codex bypass: stage sensitive content, then put a safe placeholder in the worktree."""
        with tempfile.TemporaryDirectory() as temporary:
            repo = scratch_repository(Path(temporary))
            note = repo / "notes.md"
            note.write_text("endpoint " + SYNTHETIC["private or CGNAT IPv4"] + "\n")
            git_in(repo, "add", "notes.md")
            note.write_text("endpoint <placeholder>\n")
            findings = disclosure_findings(repo, disclosure_base(repo))
            self.assertEqual(findings, ["staged notes.md:1: private or CGNAT IPv4"])

    def test_unstaged_worktree_is_scanned_when_index_is_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = scratch_repository(Path(temporary))
            note = repo / "notes.md"
            note.write_text("endpoint <placeholder>\n")
            git_in(repo, "add", "notes.md")
            note.write_text("token " + SYNTHETIC["access token"] + "\n")
            findings = disclosure_findings(repo, disclosure_base(repo))
            self.assertEqual(findings, ["unstaged notes.md:1: access token"])

    def test_committed_untracked_rename_and_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = scratch_repository(Path(temporary))
            (repo / "leak.md").write_text("\n" + SYNTHETIC["personal home path"] + "\n")
            git_in(repo, "add", "leak.md")
            git_in(repo, "commit", "-q", "-m", "leak")
            git_in(repo, "rm", "-q", "leak.md")  # a later staged deletion does not hide the commit
            git_in(repo, "mv", "history.md", "moved.md")  # pure rename: old content is not new
            (repo / "candidate.txt").write_text(SYNTHETIC["email address"] + "\n")
            findings = disclosure_findings(repo, disclosure_base(repo))
            self.assertEqual(
                findings,
                [
                    "committed leak.md:2: personal home path",
                    "untracked candidate.txt:1: email address",
                ],
            )

    def test_failed_git_reads_refuse(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = scratch_repository(Path(temporary))
            with self.assertRaises(GitError):
                disclosure_findings(repo, "0" * 40)
            with environment(FLORABASE_DISCLOSURE_BASE="no-such-ref"), self.assertRaises(GitError):
                disclosure_base(repo)
            with self.assertRaises(GitError):
                disclosure_findings(Path(temporary) / "missing", "HEAD")


class EnvTemplate(unittest.TestCase):
    """The sanitized template documents exactly what the controller renders."""

    def test_env_example_matches_rendered_keys(self) -> None:
        def keys(text: str) -> list[str]:
            return [
                line.split("=", 1)[0]
                for line in text.splitlines()
                if line and not line.startswith("#")
            ]

        example = (BUNDLE / "florabase.env.example").read_text()
        installation = {
            "canonical_origin": "https://florabase.example.invalid",
            "http_port": 8080,
            "limits": {
                "db_memory": "1g",
                "db_cpus": "0",
                "backend_memory": "768m",
                "backend_cpus": "0",
            },
        }
        images = {
            "backend": "b",
            "frontend": "f",
            "postgres": "p",
            "version": "v",
            "alembic_head": "h",
        }
        controller = ctl.Controller(Path("/srv/florabase"), FakeRunner())
        rendered = controller.render_env(installation, images, controller.layout).decode()
        self.assertEqual(keys(example), keys(rendered))


def compose_config(
    directory: Path, env: str, profile: bool = False, ambient: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    (directory / ".env").write_text(env)
    command = COMPOSE + [
        "--project-directory",
        str(directory),
        "--file",
        str(directory / "compose.yaml"),
        "--env-file",
        str(directory / ".env"),
    ]
    if profile:
        command += ["--profile", "maintenance"]
    clean = {k: v for k, v in os.environ.items() if not k.startswith(("COMPOSE_", "FLORABASE_"))}
    clean.update(ambient or {})
    return subprocess.run(
        command + ["config", "--format", "json"], capture_output=True, text=True, env=clean
    )


class StackContract(unittest.TestCase):
    """The distribution Compose must stay image-only, private and update-excluded."""

    temporary: tempfile.TemporaryDirectory[str]
    directory: Path
    images: dict[str, str]
    env: str
    config: dict[str, Any]
    maintenance: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temporary.name)
        (cls.directory / "compose.yaml").write_bytes((BUNDLE / "compose.yaml").read_bytes())
        (cls.directory / "reference.env").write_text("")
        secrets = cls.directory / "secrets"
        secrets.mkdir()
        (secrets / "db.env").write_text("POSTGRES_DB=florabase\n")
        (secrets / "backend.env").write_text("FLORABASE_DATABASE_URL=postgresql+psycopg://x@db/x\n")
        cls.images = {
            "FLORABASE_BACKEND_IMAGE": "ghcr.io/alessandrorossato/florabase-backend@" + digest("b"),
            "FLORABASE_FRONTEND_IMAGE": "ghcr.io/alessandrorossato/florabase-frontend@"
            + digest("f"),
            "FLORABASE_POSTGRES_IMAGE": "docker.io/library/postgres:18.6-alpine@" + digest("p"),
        }
        values = dict(
            cls.images,
            FLORABASE_SECRETS_DIR=str(secrets),
            FLORABASE_POSTGRES_DIR="/srv/florabase/postgres",
            FLORABASE_MEDIA_DIR="/srv/florabase/media",
            FLORABASE_REFERENCE_DIR="/srv/florabase/reference",
            FLORABASE_CANONICAL_ORIGIN="https://florabase.example.invalid",
            FLORABASE_EXPECTED_ALEMBIC_HEAD="20261013_0042",
        )
        cls.env = "".join(key + "=" + value + "\n" for key, value in values.items())
        result = compose_config(cls.directory, cls.env)
        if result.returncode:
            raise AssertionError(result.stderr)
        cls.config = json.loads(result.stdout)
        result = compose_config(cls.directory, cls.env, profile=True)
        if result.returncode:
            raise AssertionError(result.stderr)
        cls.maintenance = json.loads(result.stdout)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_project_and_services(self) -> None:
        self.assertEqual(self.config["name"], "florabase-prod")
        self.assertEqual(set(self.config["services"]), {"db", "backend", "frontend"})
        self.assertEqual(
            set(self.maintenance["services"]),
            {"db", "backend", "frontend", "migrate", "tools"},
        )

    def test_image_only_and_pinned(self) -> None:
        expected = {
            "db": self.images["FLORABASE_POSTGRES_IMAGE"],
            "frontend": self.images["FLORABASE_FRONTEND_IMAGE"],
        }
        for name, service in self.maintenance["services"].items():
            with self.subTest(name):
                self.assertNotIn("build", service)
                self.assertIn("@sha256:", service["image"])
                self.assertEqual(
                    service["image"], expected.get(name, self.images["FLORABASE_BACKEND_IMAGE"])
                )
                for mount in service.get("volumes", []):
                    self.assertEqual(mount["type"], "volume", "no host/source bind mounts")

    def test_private_exposure(self) -> None:
        for name, service in self.maintenance["services"].items():
            with self.subTest(name):
                if name == "frontend":
                    self.assertEqual(
                        [(p["host_ip"], p["published"], p["target"]) for p in service["ports"]],
                        [("127.0.0.1", "8080", 8080)],
                    )
                else:
                    self.assertFalse(service.get("ports"), "database/backend are never published")

    def test_hostile_bind_variables_cannot_widen_publication(self) -> None:
        """R3: ambient shell or .env values (as Dockhand might inject) keep 127.0.0.1."""
        hostile = {"FLORABASE_BIND_ADDRESS": "0.0.0.0", "APP_BIND_ADDRESS": "0.0.0.0"}
        cases = [
            ("ambient", self.env, hostile),
            ("dotenv", self.env + "FLORABASE_BIND_ADDRESS=0.0.0.0\n", {}),
            ("both+ipv6", self.env, {"FLORABASE_BIND_ADDRESS": "::"}),
        ]
        for name, env, ambient in cases:
            with self.subTest(name):
                result = compose_config(self.directory, env, profile=True, ambient=ambient)
                self.assertEqual(result.returncode, 0, result.stderr)
                services = json.loads(result.stdout)["services"]
                ports = services["frontend"]["ports"]
                self.assertEqual(
                    [(p["host_ip"], p["target"]) for p in ports], [("127.0.0.1", 8080)]
                )
                for other in ("db", "backend", "migrate", "tools"):
                    self.assertFalse(services[other].get("ports"))
        for port in ("0.0.0.0:8080", "8080:8080", "[::]:8080"):
            with self.subTest(port=port):
                result = compose_config(
                    self.directory, self.env, ambient={"FLORABASE_HTTP_PORT": port}
                )
                if result.returncode == 0:
                    ports = json.loads(result.stdout)["services"]["frontend"]["ports"]
                    self.assertEqual({p["host_ip"] for p in ports}, {"127.0.0.1"})
        compose_config(self.directory, self.env)

    def test_hardening_labels_and_logging(self) -> None:
        for name, service in self.maintenance["services"].items():
            with self.subTest(name):
                self.assertEqual(service["labels"]["dockhand.update"], "false")
                self.assertTrue(service["read_only"])
                self.assertEqual(service["cap_drop"], ["ALL"])
                self.assertIn("no-new-privileges:true", service["security_opt"])
                self.assertEqual(
                    service["logging"],
                    {"driver": "json-file", "options": {"max-size": "10m", "max-file": "5"}},
                )
                self.assertTrue(service.get("mem_limit"))

    def test_startup_gating_and_no_implicit_migration(self) -> None:
        services = self.maintenance["services"]
        backend = services["backend"]
        self.assertEqual(set(backend["depends_on"]), {"db"})
        self.assertEqual(backend["depends_on"]["db"]["condition"], "service_healthy")
        self.assertEqual(
            services["frontend"]["depends_on"]["backend"]["condition"], "service_healthy"
        )
        for name, service in services.items():
            command = " ".join((service.get("entrypoint") or []) + (service.get("command") or []))
            if "upgrade" in command:
                self.assertEqual(name, "migrate")
        self.assertEqual(services["migrate"]["profiles"], ["maintenance"])

    def test_schema_guard_runs_inside_every_backend_start(self) -> None:
        """R1: no one-shot success container can authorize a backend start."""
        services = self.maintenance["services"]
        self.assertNotIn("schema-gate", services)
        for service in services.values():
            for dependency in (service.get("depends_on") or {}).values():
                self.assertNotEqual(dependency["condition"], "service_completed_successfully")
        backend = services["backend"]
        guard = " ".join(backend["entrypoint"])
        self.assertEqual(backend["entrypoint"][:2], ["python", "-c"])
        for required in (
            "FLORABASE_EXPECTED_ALEMBIC_HEAD",
            "get_current_heads",
            "refusing to start",
            "os.execvp",
            "heads != [expected]",
            "except Exception",
            # Actionable refusals: invalid settings, empty, pending and newer/foreign schemas.
            "get_settings()",
            "invalid configuration",
            "walk_revisions()",
            "florabasectl.py install",
            "a migration is pending",
            "florabasectl.py promote",
            "never downgrade blindly",
            "This container never migrates",
        ):
            self.assertIn(required, guard)
        # Settings errors may echo submitted values (the database URL holds the password).
        self.assertNotIn("str(error)", guard)
        self.assertNotIn('"input"', guard)
        self.assertNotIn("upgrade", guard)
        self.assertEqual(backend["command"][:2], ["uvicorn", "florabase.main:app"])
        self.assertEqual(backend["environment"]["FLORABASE_EXPECTED_ALEMBIC_HEAD"], "20261013_0042")
        health = " ".join(backend["healthcheck"]["test"])
        for required in (
            "/api/v1/ready",
            "get_current_heads",
            "FLORABASE_EXPECTED_ALEMBIC_HEAD",
            "os.kill(1",
        ):
            self.assertIn(required, health)
        self.assertEqual(backend["restart"], "unless-stopped")
        for task in ("migrate", "tools"):
            self.assertNotIn("FLORABASE_EXPECTED_ALEMBIC_HEAD", services[task]["environment"])

    def test_guard_refuses_missing_expected_head(self) -> None:
        env = "".join(
            line + "\n"
            for line in self.env.splitlines()
            if not line.startswith("FLORABASE_EXPECTED_ALEMBIC_HEAD=")
        )
        result = compose_config(self.directory, env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FLORABASE_EXPECTED_ALEMBIC_HEAD", result.stderr)
        compose_config(self.directory, self.env)

    def test_production_settings_without_empty_optional_paths(self) -> None:
        environment = self.config["services"]["backend"]["environment"]
        self.assertEqual(environment["FLORABASE_ENVIRONMENT"], "production")
        self.assertEqual(environment["FLORABASE_COOKIE_MODE"], "secure")
        self.assertEqual(environment["FLORABASE_CORS_ORIGINS"], "[]")
        self.assertEqual(
            environment["FLORABASE_CANONICAL_ORIGIN"], "https://florabase.example.invalid"
        )
        self.assertNotIn("FLORABASE_WFO_SNAPSHOT_PATH", environment)
        reference = [
            m
            for m in self.config["services"]["backend"]["volumes"]
            if m["source"] == "reference_data"
        ]
        self.assertTrue(reference[0]["read_only"])

    def test_stable_bind_backed_volumes(self) -> None:
        volumes = self.config["volumes"]
        self.assertEqual(volumes["postgres_data"]["name"], "florabase-prod_postgres_data")
        self.assertEqual(volumes["attachment_data"]["name"], "florabase-prod_attachment_data")
        self.assertEqual(
            volumes["postgres_data"]["driver_opts"],
            {"type": "none", "o": "bind", "device": "/srv/florabase/postgres"},
        )
        self.assertNotIn("external", {k for k, v in volumes.items() if v.get("external")})

    def test_sanitized_env_example_is_valid_compose(self) -> None:
        secrets = self.directory / "secrets"
        env = (BUNDLE / "florabase.env.example").read_text()
        env = env.replace("/srv/florabase/secrets", str(secrets))
        env = re.sub(r"sha256:<[^>]+>", "sha256:" + "0" * 64, env).replace("<version>", "18")
        result = compose_config(self.directory, env)
        self.assertEqual(result.returncode, 0, result.stderr)
        compose_config(self.directory, self.env)

    def test_missing_pin_or_path_fails_closed(self) -> None:
        for key in ("FLORABASE_BACKEND_IMAGE", "FLORABASE_POSTGRES_DIR", "FLORABASE_SECRETS_DIR"):
            with self.subTest(key):
                env = "".join(
                    line + "\n" for line in self.env.splitlines() if not line.startswith(key + "=")
                )
                result = compose_config(self.directory, env)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(key, result.stderr)
        compose_config(self.directory, self.env)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compose", default="docker compose", help="Compose command to test")
    parser.add_argument("--controller-only", action="store_true", help="skip Compose checks")
    args, rest = parser.parse_known_args()
    COMPOSE[:] = args.compose.split()
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    cases = [
        ManifestRules,
        PureRules,
        HttpAcceptance,
        RecoverySets,
        Retention,
        BindAddress,
        ControllerRules,
        Disclosure,
        EnvTemplate,
    ]
    if not args.controller_only:
        cases.append(StackContract)
    for case in cases:
        suite.addTests(loader.loadTestsFromTestCase(case))
    buffer = io.StringIO()
    stream = buffer if "-q" in rest else sys.stderr
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    if not result.wasSuccessful():
        sys.stderr.write(buffer.getvalue())
        raise SystemExit(1)
    print(
        "BETA_RUNTIME_OFFLINE_PASSED tests={} python={} compose={}".format(
            result.testsRun,
            sys.version.split()[0],
            "skipped" if args.controller_only else " ".join(COMPOSE),
        )
    )


if __name__ == "__main__":
    main()
