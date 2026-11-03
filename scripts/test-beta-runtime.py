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
    spec = importlib.util.spec_from_file_location("florabasectl", BUNDLE / "florabasectl.py")
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
        "schema_version": 1,
        "distribution": "registry-candidate",
        "version": "0.1.0-beta.1",
        "source": {"url": ctl.SOURCE_URL, "revision": "a" * 40, "dirty": False},
        "platforms": ["linux/amd64"],
        "alembic_head": "20261013_0042",
        "postgresql": {
            "repository": "docker.io/library/postgres",
            "version": "18.6-alpine",
            "reference": "docker.io/library/postgres:18.6-alpine@" + pg_index,
            "index_digest": pg_index,
            "platform_digest": digest("pg-platform"),
            "platform": "linux/amd64",
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


def recovery_set(directory: Path) -> None:
    directory.mkdir()
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
    (directory / "metadata.json").write_text(json.dumps({"artifacts": artifacts}))
    (directory / "SHA256SUMS").write_text(
        "".join(
            hashlib.sha256((directory / name).read_bytes()).hexdigest() + "  " + name + "\n"
            for name in ("attachments.tar", "compose.yaml", "database.dump", "metadata.json")
        )
    )


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
            "bind_address": "127.0.0.1",
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
            self.installation, dict(record["images"], version=record["version"]), compose
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
DISCLOSURE_FILES = [
    "deploy/beta/compose.yaml",
    "deploy/beta/florabasectl.py",
    "deploy/beta/florabase.env.example",
    "docs/beta-runtime-001.md",
    "docs/beta-runtime-001-evidence.json",
    "docs/beta-runtime-001-qa-handoff.md",
    "scripts/smoke-beta-runtime.py",
    "scripts/smoke_beta_runtime_client.py",
    "scripts/test-beta-runtime.py",
]
# disclosure-fixtures-begin: patterns and samples are the only exempt lines.
DISCLOSURE_PATTERNS = {
    "private or CGNAT IPv4": r"\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01])|"
    r"100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])|169\.254)\.\d{1,3}\.\d{1,3}\b",
    "concrete tailnet name": r"[A-Za-z0-9-]+\.(?!tailnet\.)[A-Za-z0-9-]+\.ts\.net",
    "personal home path": r"/(?:home|Users)/[A-Za-z0-9._-]+",
    "email address": r"[A-Za-z0-9._%+-]+@(?!sha256)[A-Za-z0-9-]+\.[A-Za-z]{2,}",
    "private key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "access token": r"\b(?:ghp_|gho_|github_pat_|glpat-|AKIA|xox[bp]-|sk-[A-Za-z0-9]{20})",
    "literal credential": r"(?:POSTGRES_PASSWORD|RESTIC_PASSWORD)=(?!\{|<)[^\s\"']+",
}


class Disclosure(unittest.TestCase):
    """Dedicated privacy/sanitization gate over every runtime file that will be committed."""

    def test_no_infrastructure_or_secret_disclosure(self) -> None:
        findings = []
        for name in DISCLOSURE_FILES:
            path = ROOT / name
            if not path.exists():
                findings.append(name + ": missing from the scan list")
                continue
            exempt = False
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if name.endswith("test-beta-runtime.py") and "disclosure-fixtures-" in line:
                    exempt = "disclosure-fixtures-begin" in line
                    continue
                for label, pattern in DISCLOSURE_PATTERNS.items():
                    if not exempt and re.search(pattern, line):
                        findings.append(f"{name}:{number}: {label}")
        self.assertEqual(findings, [])

    def test_patterns_detect_examples(self) -> None:
        samples = {
            "private or CGNAT IPv4": "192.168.1.20",
            "concrete tailnet name": "nas.tail1234.ts.net",
            "personal home path": "/home/someone/backups",
            "email address": "someone@example.org",
            "literal credential": "POSTGRES_PASSWORD=hunter2",
        }
        for label, sample in samples.items():
            self.assertRegex(sample, DISCLOSURE_PATTERNS[label])
        for allowed in ("https://<node>.<tailnet>.ts.net", "127.0.0.1:8080", "@sha256:abc"):
            self.assertFalse(
                any(re.search(p, allowed) for p in DISCLOSURE_PATTERNS.values()), allowed
            )
        # disclosure-fixtures-end

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
            "bind_address": "127.0.0.1",
            "http_port": 8080,
            "limits": {
                "db_memory": "1g",
                "db_cpus": "0",
                "backend_memory": "768m",
                "backend_cpus": "0",
            },
        }
        images = {"backend": "b", "frontend": "f", "postgres": "p", "version": "v"}
        controller = ctl.Controller(Path("/srv/florabase"), FakeRunner())
        rendered = controller.render_env(installation, images, controller.layout).decode()
        self.assertEqual(keys(example), keys(rendered))


def compose_config(
    directory: Path, env: str, profile: bool = False
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
        self.assertEqual(set(self.config["services"]), {"db", "schema-gate", "backend", "frontend"})
        self.assertEqual(
            set(self.maintenance["services"]),
            {"db", "schema-gate", "backend", "frontend", "migrate", "tools"},
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
        self.assertEqual(
            services["backend"]["depends_on"]["schema-gate"]["condition"],
            "service_completed_successfully",
        )
        self.assertEqual(services["backend"]["depends_on"]["db"]["condition"], "service_healthy")
        self.assertEqual(
            services["frontend"]["depends_on"]["backend"]["condition"], "service_healthy"
        )
        self.assertIsNone(services["backend"].get("command"))
        self.assertIn("is not image head", " ".join(services["schema-gate"]["command"]))
        for name, service in services.items():
            command = " ".join(service.get("command") or [])
            if "upgrade" in command:
                self.assertEqual(name, "migrate")
        self.assertEqual(services["migrate"]["profiles"], ["maintenance"])
        self.assertEqual(services["schema-gate"]["restart"], "no")

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
    cases = [ManifestRules, PureRules, RecoverySets, ControllerRules, Disclosure]
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
