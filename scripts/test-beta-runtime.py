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
# 10.0.2.2 is Android Emulator's universal host-loopback alias (equivalent to 127.0.0.1).
DISCLOSURE_PATTERNS = {
    "private or CGNAT IPv4": r"\b(?!10\.0\.2\.2\b)(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01])|"
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
        for allowed in (
            "https://<node>.<tailnet>.ts.net",
            "127.0.0.1:8080",
            "10.0.2.2:5173",
            "@sha256:abc",
        ):
            self.assertFalse(any(re.search(p, allowed) for p in DISCLOSURE_PATTERNS.values()))
        self.assertRegex("10.0.2." + "3", DISCLOSURE_PATTERNS["private or CGNAT IPv4"])

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


def compose_config(
    compose: Path, env: dict[str, str] | None = None, ambient: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    clean = {k: v for k, v in os.environ.items() if not k.startswith(("COMPOSE_", "FLORABASE_"))}
    clean.update(env or {})
    clean.update(ambient or {})
    return subprocess.run(
        COMPOSE + ["--env-file", "/dev/null", "--file", str(compose), "config", "--format", "json"],
        capture_output=True,
        text=True,
        env=clean,
    )


EXPECTED_IMAGES = {
    "db": "ghcr.io/alessandrorossato/florabase-postgres:latest",
    "backend": "ghcr.io/alessandrorossato/florabase-backend:latest",
    "frontend": "ghcr.io/alessandrorossato/florabase-frontend:latest",
}


class StackContract(unittest.TestCase):
    """The production compose.yaml stays directly usable, minimal, image-only, non-root and guarded."""

    compose: Path
    config: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.compose = ROOT / "compose.yaml"
        result = compose_config(cls.compose)
        if result.returncode:
            raise AssertionError(result.stderr)
        cls.config = json.loads(result.stdout)

    def test_minimal_shape_services_and_latest_images(self) -> None:
        template = self.compose.read_text()
        self.assertLessEqual(len(template.splitlines()), 60)
        self.assertNotIn("&", template, "compose.yaml must stay flat with no YAML anchors")
        self.assertNotIn("entrypoint:", template, "no inline entrypoints in compose.yaml")
        self.assertNotIn("sh -", template, "no inline shell scripts in compose.yaml")
        self.assertNotIn("healthcheck:", template, "healthchecks live in the images")
        self.assertNotIn("${", template, "compose.yaml uses plain values without interpolation")
        self.assertNotRegex(template, r"@[A-Z]+@", "compose.yaml has no template slots")
        self.assertIn("docs/installation.md", template)
        services = self.config["services"]
        self.assertEqual(set(services), {"db", "backend", "frontend"})
        expected = {
            "db": (EXPECTED_IMAGES["db"], "florabase-db"),
            "backend": (EXPECTED_IMAGES["backend"], "florabase-backend"),
            "frontend": (EXPECTED_IMAGES["frontend"], "florabase-frontend"),
        }
        for name, service in services.items():
            with self.subTest(name):
                image, container_name = expected[name]
                self.assertNotIn("build", service)
                self.assertEqual(service["image"], image)
                self.assertEqual(service["container_name"], container_name)
                self.assertEqual(service["restart"], "unless-stopped")
                self.assertIsNone(
                    service.get("user"), "no container overrides image USER or runs root"
                )

    def test_private_exposure_and_no_custom_networks(self) -> None:
        self.assertNotIn("networks:", self.compose.read_text())
        self.assertEqual(set(self.config.get("networks", {})), {"default"})
        for name, service in self.config["services"].items():
            with self.subTest(name):
                self.assertEqual(set(service.get("networks", {})), {"default"})
                if name == "frontend":
                    self.assertEqual(
                        [(p["host_ip"], p["published"], p["target"]) for p in service["ports"]],
                        [("127.0.0.1", "8080", 8080)],
                    )
                else:
                    self.assertFalse(service.get("ports"), "only the frontend publishes")

    def test_hostile_bind_variables_cannot_widen_publication(self) -> None:
        """Ambient values a Compose manager might inject keep the loopback-only port."""
        for ambient in (
            {"FLORABASE_BIND_ADDRESS": "0.0.0.0", "APP_BIND_ADDRESS": "0.0.0.0"},
            {"FLORABASE_BIND_ADDRESS": "::"},
            {"FLORABASE_HTTP_PORT": "0.0.0.0:8080"},
        ):
            with self.subTest(ambient=ambient):
                result = compose_config(self.compose, ambient=ambient)
                self.assertEqual(result.returncode, 0, result.stderr)
                ports = json.loads(result.stdout)["services"]["frontend"]["ports"]
                self.assertEqual({p["host_ip"] for p in ports}, {"127.0.0.1"})

    def test_plain_bind_mounts_and_no_host_path_env_vars(self) -> None:
        services = self.config["services"]
        targets = {
            "db": {"/var/lib/postgresql": "/volume1/docker/florabase/data"},
            "backend": {
                "/var/lib/florabase/data": "/volume1/docker/florabase/data",
                "/var/lib/florabase/backup": "/volume1/docker/florabase/backup",
            },
            "frontend": {},
        }
        for name, service in services.items():
            with self.subTest(name):
                mounts = service.get("volumes", [])
                self.assertEqual({m["target"]: m["source"] for m in mounts}, targets[name])
                for mount in mounts:
                    self.assertEqual(mount["type"], "bind")
                env = service.get("environment", {})
                self.assertNotIn("FLORABASE_DATA_DIR", env)
                self.assertNotIn("FLORABASE_BACKUP_DIR", env)
        self.assertNotIn("volumes", self.config)

    def test_startup_ordering_and_guarded_entrypoints(self) -> None:
        services = self.config["services"]
        self.assertEqual(services["backend"]["depends_on"]["db"]["condition"], "service_healthy")
        self.assertEqual(
            services["frontend"]["depends_on"]["backend"]["condition"], "service_healthy"
        )
        self.assertEqual(services["backend"]["command"], ["florabase-start"])
        self.assertIsNone(services["db"].get("command"))
        self.assertIsNone(services["db"].get("entrypoint"))
        self.assertIsNone(services["frontend"].get("command"))

    def test_guards_live_in_image_scripts_and_dockerfiles(self) -> None:
        pg_entrypoint = (ROOT / "postgres/florabase-postgres-entrypoint.sh").read_text()
        for required in (
            "florabase-postgres-refuse-root",
            "installation.env",
            "installation.pending",
            "pg_controldata",
            "Database system identifier",
            "database folder is missing or empty",
            "belongs to another PostgreSQL cluster",
            "use an empty data folder",
            "docs/installation.md",
            "FLORABASE_DB_PASSWORD",
            "change-me",
        ):
            self.assertIn(required, pg_entrypoint)
        pg_dockerfile = (ROOT / "postgres/Dockerfile").read_text()
        for required in (
            "PGDATA=/var/lib/postgresql/postgres/18/docker",
            "POSTGRES_DB=florabase",
            "POSTGRES_USER=florabase",
            "HEALTHCHECK",
            "USER 70:70",
            'CMD ["postgres", "-c", "timezone=UTC"]',
        ):
            self.assertIn(required, pg_dockerfile)

        backend_start = (ROOT / "backend/florabase-start.sh").read_text()
        for required in (
            "florabase.db.release_schema wait-db",
            "florabase.db.release_schema deploy",
            "unset FLORABASE_OWNER_LOGIN FLORABASE_OWNER_PASSWORD",
            "exec python -m florabase.db.release_schema serve",
        ):
            self.assertIn(required, backend_start)
        release_schema = (ROOT / "backend/src/florabase/db/release_schema.py").read_text()
        for required in (
            "the data and backup folders are the same",
            "the backup folder is inside the data folder",
            "the data folder is inside the backup folder",
            "check_mountinfo_nesting",
            "reject_placeholder_config",
            "placeholder 'change-me'",
            "PLACEHOLDER_CANONICAL_ORIGIN",
            "upgrade-failed.env",
            "pg_isready",
        ):
            self.assertIn(required, release_schema)

    def test_plain_environment_defaults(self) -> None:
        services = self.config["services"]
        for name in ("db", "backend", "frontend"):
            self.assertEqual(services[name]["environment"]["TZ"], "Europe/Rome")
        self.assertEqual(services["db"]["environment"]["FLORABASE_DB_PASSWORD"], "change-me")
        self.assertEqual(services["backend"]["environment"]["FLORABASE_DB_PASSWORD"], "change-me")
        self.assertEqual(
            services["backend"]["environment"]["FLORABASE_CANONICAL_ORIGIN"],
            "https://florabase.example.org",
        )
        for name in ("db", "backend", "frontend"):
            self.assertNotIn("FLORABASE_OWNER_LOGIN", services[name].get("environment", {}))
            self.assertNotIn("FLORABASE_OWNER_PASSWORD", services[name].get("environment", {}))

    def test_production_constants_live_in_backend_runtime_image(self) -> None:
        backend_env = self.config["services"]["backend"]["environment"]
        for constant in (
            "FLORABASE_ENVIRONMENT",
            "FLORABASE_DATABASE_URL",
            "FLORABASE_COOKIE_MODE",
            "FLORABASE_CORS_ORIGINS",
            "FLORABASE_ATTACHMENT_STORAGE_ROOT",
            "PGPASSWORD",
        ):
            self.assertNotIn(constant, backend_env)
        db_env = self.config["services"]["db"]["environment"]
        for constant in ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "PGDATA"):
            self.assertNotIn(constant, db_env)
        backend_dockerfile = (ROOT / "backend/Dockerfile").read_text()
        for required in (
            "FLORABASE_ENVIRONMENT=production",
            "FLORABASE_DATABASE_URL=postgresql+psycopg://florabase@db:5432/florabase",
            "FLORABASE_COOKIE_MODE=secure",
            "FLORABASE_CORS_ORIGINS=[]",
            "FLORABASE_ATTACHMENT_STORAGE_ROOT=/var/lib/florabase/data/media",
            'ENTRYPOINT ["florabase-backend-entrypoint"]',
            'CMD ["python", "-m", "florabase.db.release_schema", "serve"]',
        ):
            self.assertIn(required, backend_dockerfile)


class MobileReleaseContract(unittest.TestCase):
    def test_release_android_disables_mixed_content_cleartext_and_backup(self) -> None:
        capacitor_config = (ROOT / "mobile/capacitor.config.ts").read_text()
        self.assertIn('appId: "io.github.alessandrorossato.florabase"', capacitor_config)
        self.assertIn("allowMixedContent: false", capacitor_config)
        self.assertIn('loggingBehavior: "none"', capacitor_config)
        self.assertNotIn("org.florabase.app", capacitor_config)

        gradle = (ROOT / "mobile/android/app/build.gradle").read_text()
        self.assertIn('namespace = "io.github.alessandrorossato.florabase"', gradle)
        self.assertIn('applicationId "io.github.alessandrorossato.florabase"', gradle)
        self.assertNotIn("org.florabase.app", gradle)
        self.assertNotIn("security-crypto", gradle)
        self.assertNotIn("play-services", gradle)

        manifest = (ROOT / "mobile/android/app/src/main/AndroidManifest.xml").read_text()
        self.assertIn('android:allowBackup="false"', manifest)
        self.assertIn('android:networkSecurityConfig="@xml/network_security_config"', manifest)

        nsc = (ROOT / "mobile/android/app/src/main/res/xml/network_security_config.xml").read_text()
        self.assertIn('cleartextTrafficPermitted="false"', nsc)
        self.assertIn('<certificates src="system"', nsc)
        self.assertIn('<certificates src="user"', nsc)

        main_activity = (
            ROOT
            / "mobile/android/app/src/main/java/io/github/alessandrorossato/florabase/MainActivity.java"
        ).read_text()
        self.assertIn("if (BuildConfig.DEBUG &&", main_activity)
        self.assertIn("MIXED_CONTENT_ALWAYS_ALLOW", main_activity)
        self.assertIn("registerPlugin(SecureTokenPlugin.class)", main_activity)
        self.assertIn("registerPlugin(WebPrintPlugin.class)", main_activity)
        self.assertIn('new File(getCacheDir(), "shared")', main_activity)

        web_print = (
            ROOT
            / "mobile/android/app/src/main/java/io/github/alessandrorossato/florabase/WebPrintPlugin.java"
        ).read_text()
        self.assertIn("android.print.PrintManager", web_print)
        self.assertIn("createPrintDocumentAdapter", web_print)
        self.assertNotIn("com.google", web_print)

        # FileProvider exposes only the dedicated cache/shared/ subfolder.
        file_paths = (ROOT / "mobile/android/app/src/main/res/xml/file_paths.xml").read_text()
        self.assertIn('<cache-path name="shared" path="shared/" />', file_paths)
        self.assertNotIn("external-path", file_paths)
        self.assertNotIn('path="."', file_paths)

        # Branding colors and splash theme are wired to Florabase tokens.
        ic_bg = (
            ROOT / "mobile/android/app/src/main/res/values/ic_launcher_background.xml"
        ).read_text()
        self.assertIn("#F8F5E7", ic_bg)
        colors = (ROOT / "mobile/android/app/src/main/res/values/colors.xml").read_text()
        self.assertIn("#153A2C", colors)
        styles = (ROOT / "mobile/android/app/src/main/res/values/styles.xml").read_text()
        self.assertIn("windowSplashScreenBackground", styles)
        self.assertIn("@color/splash_background", styles)
        self.assertFalse(
            (ROOT / "mobile/android/app/src/main/res/drawable/ic_launcher_background.xml").exists()
        )

        # Confirm old placeholder package and Capacitor example tests are removed.
        self.assertFalse((ROOT / "mobile/android/app/src/main/java/org/florabase/app").exists())
        self.assertEqual(list((ROOT / "mobile/android").rglob("Example*Test.java")), [])

        # Confirm zero @capacitor/* packages in frontend/package.json and FOSS-only plugins in mobile.
        frontend_pkg = json.loads((ROOT / "frontend/package.json").read_text())
        for section in ("dependencies", "devDependencies"):
            for dep in frontend_pkg.get(section, {}):
                self.assertFalse(
                    dep.startswith("@capacitor/"),
                    f"frontend/package.json must not depend on {dep}",
                )
        mobile_pkg = json.loads((ROOT / "mobile/package.json").read_text())
        mobile_deps = mobile_pkg.get("dependencies", {})
        self.assertIn("@capacitor/filesystem", mobile_deps)
        self.assertIn("@capacitor/share", mobile_deps)

    def test_release_signing_gradle_has_no_hardcoded_secrets_and_uses_version_helper(self) -> None:
        gradle = (ROOT / "mobile/android/app/build.gradle").read_text()
        self.assertIn("scripts/mobile_version.py", gradle)
        for env_name in (
            "FLORABASE_ANDROID_KEYSTORE",
            "FLORABASE_ANDROID_STORE_PASSWORD",
            "FLORABASE_ANDROID_KEY_ALIAS",
            "FLORABASE_ANDROID_KEY_PASSWORD",
        ):
            self.assertIn(env_name, gradle)
        self.assertNotRegex(gradle, r"""storePassword\s+['"][^'"]+['"]""")
        self.assertNotRegex(gradle, r"""keyPassword\s+['"][^'"]+['"]""")
        self.assertNotRegex(gradle, r"""keyAlias\s+['"][^'"]+['"]""")
        self.assertNotRegex(gradle, r"""storeFile\s+file\(['"][^'"]+['"]\)""")
        for forbidden in ("firebase", "mlkit", "com.google.gms"):
            self.assertNotIn(forbidden, gradle.lower())

        # Release script must refuse to run without signing env vars and never leak values.
        release_script = (ROOT / "scripts/mobile-android-release.sh").read_text()
        self.assertIn("set +x", release_script)
        self.assertIn("FLORABASE_ANDROID_CERT_SHA256", release_script)
        self.assertIn("apksigner", release_script)
        clean_env = {k: v for k, v in os.environ.items() if not k.startswith("FLORABASE_ANDROID_")}
        proc = subprocess.run(
            ["bash", str(ROOT / "scripts/mobile-android-release.sh")],
            cwd=ROOT,
            env=clean_env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("FLORABASE_ANDROID_KEYSTORE", proc.stderr)
        self.assertIn("docs/mobile.md", proc.stderr)

    def test_mobile_version_code_helper_examples_and_bounds(self) -> None:
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import mobile_version
        finally:
            sys.path.pop(0)

        expected_pairs = [
            ("0.1.0-alpha.1", 100_001),
            ("0.1.0-beta.8", 100_308),
            ("0.1.0-beta.9", 100_309),
            ("0.1.0-beta.10", 100_310),
            ("0.1.0-rc.1", 100_601),
            ("0.1.0", 100_900),
            ("0.1.1", 101_900),
            ("1.0.0-rc.1", 10_000_601),
            ("1.0.0", 10_000_900),
            ("1.0.1", 10_001_900),
        ]
        codes = [mobile_version.compute_version_code(ver) for ver, _ in expected_pairs]
        self.assertEqual(codes, [code for _, code in expected_pairs])
        self.assertEqual(codes, sorted(codes))
        self.assertEqual(len(codes), len(set(codes)))

        for bad in (
            "",
            "v0.1.0",
            "1.0",
            "0.1.0-beta.0",
            "0.1.0-beta.01",
            "0.1.0-dev.1",
            "0.1.0-beta.300",
            "210.0.0",
            "0.100.0",
            "0.0.100",
        ):
            with self.assertRaises(ValueError, msg=f"expected failure for {bad!r}"):
                mobile_version.compute_version_code(bad)

        # CLI matches frontend/package.json.
        cli = subprocess.run(
            [sys.executable, str(ROOT / "scripts/mobile_version.py"), "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        parsed = json.loads(cli.stdout)
        frontend_version = json.loads((ROOT / "frontend/package.json").read_text())["version"]
        self.assertEqual(parsed["versionName"], frontend_version)
        self.assertEqual(
            parsed["versionCode"], mobile_version.compute_version_code(frontend_version)
        )

    def test_mobile_release_workflow_contract(self) -> None:
        workflow = (ROOT / ".github/workflows/mobile-android-release.yml").read_text()
        self.assertIn("workflow_run:", workflow)
        self.assertIn('workflows: ["Protected Florabase release"]', workflow)
        self.assertIn("types: [completed]", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", workflow)
        self.assertIn("github.event.workflow_run.head_sha", workflow)
        self.assertNotIn("pull_request", workflow)
        self.assertNotRegex(workflow, r"(?m)^\s+push:\s*$")
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertEqual(workflow.count("contents: write"), 1)
        self.assertIn("scripts/mobile_version.py", workflow)
        self.assertIn("scripts/mobile-android-release.sh --skip-sync", workflow)
        self.assertIn("FLORABASE_ANDROID_CERT_SHA256", workflow)
        self.assertIn('gh release upload "$TAG" "$apk" "$sha" --clobber', workflow)
        self.assertIn("set +x", workflow)
        self.assertIn("if: always()", workflow)
        self.assertIn('rm -f "${RUNNER_TEMP}/florabase-release.keystore"', workflow)

        # Every GitHub Action must be pinned to a full 40-char commit SHA.
        uses_refs = re.findall(r"^\s*(?:-\s+)?uses:\s*([^\s#]+)", workflow, re.M)
        self.assertGreaterEqual(len(uses_refs), 3)
        for ref in uses_refs:
            self.assertRegex(
                ref,
                r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}$",
                f"unpinned workflow action: {ref}",
            )

        # No secret variable may ever be echoed to stdout/stderr.
        self.assertNotRegex(
            workflow,
            r"(?i)(echo|printf)\s+[^\n]*(ANDROID_STORE_PASSWORD|ANDROID_KEY_PASSWORD|ANDROID_KEY_ALIAS)",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compose", default="docker compose", help="Compose command to test")
    args, rest = parser.parse_known_args()
    COMPOSE[:] = args.compose.split()
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for case in (Disclosure, StackContract, MobileReleaseContract):
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
