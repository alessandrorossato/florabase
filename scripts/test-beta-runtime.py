#!/usr/bin/env python3
"""Offline release checks: the repository disclosure gate and the production compose.yaml contract.

python3 scripts/test-beta-runtime.py [--compose "docker compose"]
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMPOSE: list[str] = ["docker", "compose"]


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


class GitError(AssertionError):
    """A failed or ambiguous Git read: the disclosure gate refuses rather than passes."""


def git_in(repo: Path, *args: str) -> str:
    try:
        result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    except OSError as error:
        raise GitError(f"git {args[0]}: {error}") from error
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()[:300]
        raise GitError(f"git {' '.join(args[:3])} failed: {detail}")
    return result.stdout.decode("utf-8", errors="replace")


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
    # Git separates patch records with LF. Forced text diffs can contain other
    # line separators inside the payload of a record.
    for line in output.split("\n"):
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

    def test_staged_binary_payload_keeps_git_record_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = scratch_repository(Path(temporary))
            (repo / "asset.bin").write_bytes(
                b"\x00\r@@ asset\v@@ metadata " + SYNTHETIC["email address"].encode("ascii") + b"\n"
            )
            git_in(repo, "add", "asset.bin")
            self.assertEqual(
                disclosure_findings(repo, disclosure_base(repo)),
                ["staged asset.bin:1: email address"],
            )

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


def rendered_compose(directory: Path) -> Path:
    """The tracked template with immutable fixture references, as the release renders it."""
    text = (ROOT / "compose.yaml").read_text().replace("@VERSION@", "0.1.0-beta.99")
    for token, reference in IMAGES.items():
        text = text.replace(token, reference)
    path = directory / "compose.yaml"
    path.write_text(text)
    return path


def compose_config(
    compose: Path, env: dict[str, str], ambient: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    clean = {k: v for k, v in os.environ.items() if not k.startswith(("COMPOSE_", "FLORABASE_"))}
    clean.update(env)
    clean.update(ambient or {})
    return subprocess.run(
        COMPOSE + ["--env-file", "/dev/null", "--file", str(compose), "config", "--format", "json"],
        capture_output=True,
        text=True,
        env=clean,
    )


IMAGES = {
    "@BACKEND@": "ghcr.io/alessandrorossato/florabase-backend@sha256:" + "b" * 64,
    "@FRONTEND@": "ghcr.io/alessandrorossato/florabase-frontend@sha256:" + "f" * 64,
    "@POSTGRESQL@": "ghcr.io/alessandrorossato/florabase-postgres@sha256:" + "a" * 64,
}
ENV = {
    "FLORABASE_DATA_DIR": "/volume1/docker/florabase/data",
    "FLORABASE_BACKUP_DIR": "/volume1/backup/florabase",
    "FLORABASE_DB_PASSWORD": "fixture-database-password",
    "FLORABASE_CANONICAL_ORIGIN": "https://florabase.example.invalid",
}


class StackContract(unittest.TestCase):
    """The production compose.yaml stays image-only, private, hardened and self-initializing."""

    temporary: tempfile.TemporaryDirectory[str]
    compose: Path
    config: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.compose = rendered_compose(Path(cls.temporary.name))
        result = compose_config(cls.compose, ENV)
        if result.returncode:
            raise AssertionError(result.stderr)
        cls.config = json.loads(result.stdout)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_services_and_immutable_images(self) -> None:
        services = self.config["services"]
        self.assertEqual(set(services), {"prepare", "db", "migrate", "backend", "frontend"})
        expected = {
            "prepare": "@POSTGRESQL@",
            "db": "@POSTGRESQL@",
            "migrate": "@BACKEND@",
            "backend": "@BACKEND@",
            "frontend": "@FRONTEND@",
        }
        for name, service in services.items():
            with self.subTest(name):
                self.assertNotIn("build", service)
                self.assertEqual(service["image"], IMAGES[expected[name]])
                self.assertEqual(service["platform"], "linux/amd64")

    def test_private_exposure(self) -> None:
        for name, service in self.config["services"].items():
            with self.subTest(name):
                if name == "frontend":
                    self.assertEqual(
                        [(p["host_ip"], p["published"], p["target"]) for p in service["ports"]],
                        [("127.0.0.1", "8080", 8080)],
                    )
                else:
                    self.assertFalse(service.get("ports"), "only the frontend publishes")
        self.assertEqual(self.config["services"]["prepare"]["network_mode"], "none")
        self.assertTrue(self.config["networks"]["internal"]["internal"])
        self.assertEqual(self.config["services"]["db"]["networks"], {"internal": None})

    def test_hostile_bind_variables_cannot_widen_publication(self) -> None:
        """Ambient values a Compose manager might inject keep the loopback-only port."""
        for ambient in (
            {"FLORABASE_BIND_ADDRESS": "0.0.0.0", "APP_BIND_ADDRESS": "0.0.0.0"},
            {"FLORABASE_BIND_ADDRESS": "::"},
        ):
            with self.subTest(ambient=ambient):
                result = compose_config(self.compose, ENV, ambient)
                self.assertEqual(result.returncode, 0, result.stderr)
                ports = json.loads(result.stdout)["services"]["frontend"]["ports"]
                self.assertEqual({p["host_ip"] for p in ports}, {"127.0.0.1"})
        for port in ("0.0.0.0:8080", "8080:8080", "[::]:8080"):
            with self.subTest(port=port):
                result = compose_config(self.compose, ENV, {"FLORABASE_HTTP_PORT": port})
                if result.returncode == 0:
                    ports = json.loads(result.stdout)["services"]["frontend"]["ports"]
                    self.assertEqual({p["host_ip"] for p in ports}, {"127.0.0.1"})

    def test_hardening(self) -> None:
        for name, service in self.config["services"].items():
            with self.subTest(name):
                self.assertTrue(service["read_only"])
                self.assertEqual(service["cap_drop"], ["ALL"])
                self.assertIn("no-new-privileges:true", service["security_opt"])
                self.assertEqual(
                    service.get("cap_add", []),
                    ["CHOWN", "DAC_OVERRIDE", "FOWNER"] if name == "prepare" else [],
                )
                self.assertEqual(service.get("user") == "0:0", name == "prepare")

    def test_host_folders_are_never_created_and_stay_separate(self) -> None:
        services = self.config["services"]
        targets = {
            "prepare": {"/data", "/backup"},
            "db": {"/var/lib/postgresql"},
            "migrate": {"/var/lib/florabase/data", "/var/lib/florabase/backup"},
            "backend": {"/var/lib/florabase/data"},
            "frontend": set(),
        }
        for name, service in services.items():
            with self.subTest(name):
                mounts = service.get("volumes", [])
                self.assertEqual({m["target"] for m in mounts}, targets[name])
                for mount in mounts:
                    self.assertEqual(mount["type"], "bind")
                    self.assertFalse(mount["bind"].get("create_host_path", True))
                    self.assertIn(
                        mount["source"], {ENV["FLORABASE_DATA_DIR"], ENV["FLORABASE_BACKUP_DIR"]}
                    )
        self.assertNotIn("volumes", self.config)

    def test_one_shots_gate_startup_and_only_migrate_migrates(self) -> None:
        services = self.config["services"]
        self.assertEqual(
            services["db"]["depends_on"]["prepare"]["condition"], "service_completed_successfully"
        )
        self.assertEqual(services["migrate"]["depends_on"]["db"]["condition"], "service_healthy")
        backend = services["backend"]["depends_on"]
        self.assertEqual(backend["migrate"]["condition"], "service_completed_successfully")
        self.assertEqual(backend["db"]["condition"], "service_healthy")
        self.assertEqual(
            services["frontend"]["depends_on"]["backend"]["condition"], "service_healthy"
        )
        self.assertEqual(
            services["migrate"]["command"],
            ["python", "-m", "florabase.db.release_schema", "deploy"],
        )
        # The backend image's own command is the exact-head guard (release_schema serve).
        self.assertIsNone(services["backend"].get("command"))
        self.assertIsNone(services["backend"].get("entrypoint"))
        for name in ("prepare", "migrate"):
            self.assertEqual(services[name]["restart"], "no")
        for name in ("db", "backend", "frontend"):
            self.assertEqual(services[name]["restart"], "unless-stopped")

    def test_guards_are_in_place(self) -> None:
        prepare = " ".join(self.config["services"]["prepare"]["command"])
        for required in (
            "installation.env",
            "installation.pending",
            "pg_controldata",
            "Database system identifier",
            "is inside FLORABASE_DATA_DIR",
            "is inside FLORABASE_BACKUP_DIR",
            "must be an absolute path",
            "use an empty data folder",
        ):
            self.assertIn(required, prepare)
        db = " ".join(self.config["services"]["db"]["command"])
        self.assertIn("installation marker exists but the cluster is missing", db)
        self.assertIn("exec postgres", db)

    def test_owner_variables_are_optional_and_reach_only_migrate(self) -> None:
        services = self.config["services"]
        self.assertEqual(services["migrate"]["environment"]["FLORABASE_OWNER_LOGIN"], "")
        owner = {"FLORABASE_OWNER_LOGIN": "owner", "FLORABASE_OWNER_PASSWORD": "fixture-owner-pw"}
        result = compose_config(self.compose, {**ENV, **owner})
        self.assertEqual(result.returncode, 0, result.stderr)
        configured = json.loads(result.stdout)["services"]
        self.assertEqual(configured["migrate"]["environment"]["FLORABASE_OWNER_LOGIN"], "owner")
        for name in ("prepare", "db", "backend", "frontend"):
            self.assertNotIn("FLORABASE_OWNER_PASSWORD", configured[name].get("environment", {}))

    def test_production_settings(self) -> None:
        environment = self.config["services"]["backend"]["environment"]
        self.assertEqual(environment["FLORABASE_ENVIRONMENT"], "production")
        self.assertEqual(environment["FLORABASE_COOKIE_MODE"], "secure")
        self.assertEqual(environment["FLORABASE_CORS_ORIGINS"], "[]")
        self.assertEqual(
            environment["FLORABASE_ATTACHMENT_STORAGE_ROOT"], "/var/lib/florabase/data/media"
        )
        db = self.config["services"]["db"]
        self.assertNotIn("PGDATA", db["environment"])
        # Compose keeps the escaped $$ of literal shell variables in its rendered model.
        self.assertIn('PGDATA="/var/lib/postgresql/postgres/$$PG_MAJOR/docker"', db["command"][0])
        prepare = self.config["services"]["prepare"]["command"][0]
        self.assertIn('cluster="/data/postgres/$$major/docker"', prepare)

    def test_missing_required_value_fails_closed(self) -> None:
        for key in ENV:
            with self.subTest(key):
                result = compose_config(self.compose, {k: v for k, v in ENV.items() if k != key})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(key, result.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compose", default="docker compose", help="Compose command to test")
    args, rest = parser.parse_known_args()
    COMPOSE[:] = args.compose.split()
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for case in (Disclosure, StackContract):
        suite.addTests(loader.loadTestsFromTestCase(case))
    buffer = io.StringIO()
    stream = buffer if "-q" in rest else sys.stderr
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    if not result.wasSuccessful():
        sys.stderr.write(buffer.getvalue())
        raise SystemExit(1)
    print(
        "BETA_RUNTIME_OFFLINE_PASSED tests={} python={} compose={}".format(
            result.testsRun, sys.version.split()[0], " ".join(COMPOSE)
        )
    )


if __name__ == "__main__":
    main()
