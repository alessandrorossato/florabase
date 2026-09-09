#!/usr/bin/env python3
"""Manage Florabase's isolated, persistent local stable-preview environment."""

# ruff: noqa: T201 -- this command-line operator helper intentionally reports state to stdout.

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import IO, Any

PROJECT = "florabase-preview"
DEV_PROJECT = "florabase"
PREVIEW_DATABASE = "florabase_preview"
PREVIEW_USER = "florabase_preview"
PREVIEW_PASSWORD = "local-preview-only-password"
PREVIEW_URL = "http://localhost:15173"
DEFAULT_REF = "origin/main"


class PreviewError(RuntimeError):
    pass


class Commands:
    def run(
        self,
        command: list[str],
        *,
        capture: bool = False,
        env: dict[str, str] | None = None,
        check: bool = True,
        stdin: IO[bytes] | None = None,
        stdout: IO[bytes] | None = None,
    ) -> str:
        try:
            result = subprocess.run(
                command,
                check=check,
                text=stdout is None and stdin is None,
                stdout=stdout if stdout is not None else (subprocess.PIPE if capture else None),
                stdin=stdin,
                env=env,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            raise PreviewError(f"command failed: {' '.join(command)}") from error
        if capture and isinstance(result.stdout, str):
            return result.stdout.strip()
        return ""


class Preview:
    def __init__(
        self,
        repository: Path,
        preview_path: Path,
        commands: Commands | None = None,
        *,
        sleep: Any = time.sleep,
        urlopen: Any = urllib.request.urlopen,
    ) -> None:
        self.repository = repository.resolve()
        self.preview_path = preview_path.resolve()
        self.commands = commands or Commands()
        self.sleep = sleep
        self.urlopen = urlopen
        self.ref = DEFAULT_REF
        self.sha = ""

    def require_safe_path(self) -> None:
        if self.preview_path == self.repository or self.repository in self.preview_path.parents:
            raise PreviewError("preview path must be outside the primary worktree")

    def git(self, *args: str, at_preview: bool = False, capture: bool = False) -> str:
        worktree = self.preview_path if at_preview else self.repository
        return self.commands.run(["git", "-C", str(worktree), *args], capture=capture)

    def require_registered_preview(self) -> None:
        records = self.git("worktree", "list", "--porcelain", capture=True).split("\n\n")
        expected = f"worktree {self.preview_path}"
        matching = [record.splitlines() for record in records if record.startswith(expected + "\n")]
        if len(matching) != 1 or any(line.startswith("prunable") for line in matching[0]):
            raise PreviewError(
                f"preview path is not a healthy registered Git worktree: {self.preview_path}"
            )

    def resolve_and_prepare_worktree(self, ref: str) -> str:
        self.require_safe_path()
        self.git("fetch", "origin")
        try:
            sha = self.git("rev-parse", "--verify", f"{ref}^{{commit}}", capture=True)
        except PreviewError as error:
            raise PreviewError(f"could not resolve preview ref: {ref}") from error
        if not sha:
            raise PreviewError(f"could not resolve preview ref: {ref}")

        if self.preview_path.exists():
            if not (self.preview_path / ".git").exists():
                raise PreviewError(
                    f"preview path exists but is not a Git worktree: {self.preview_path}"
                )
            # Repair only this explicitly selected linked worktree if it was safely moved on disk.
            self.git("worktree", "repair", str(self.preview_path))
            self.require_registered_preview()
            top = self.git("rev-parse", "--show-toplevel", at_preview=True, capture=True)
            if Path(top).resolve() != self.preview_path:
                raise PreviewError(f"unexpected Git worktree at preview path: {top}")
            dirty = self.git("status", "--porcelain=v1", at_preview=True, capture=True)
            if dirty:
                raise PreviewError(
                    "preview worktree has local changes; refusing revision update: "
                    f"{self.preview_path}"
                )
            self.git("switch", "--detach", sha, at_preview=True)
        else:
            self.git("worktree", "add", "--detach", str(self.preview_path), sha)
            self.require_registered_preview()

        actual = self.git("rev-parse", "HEAD", at_preview=True, capture=True)
        if actual != sha:
            raise PreviewError(f"preview worktree did not reach resolved SHA {sha}")
        self.ref = ref
        self.sha = sha
        return sha

    def require_worktree(self) -> None:
        self.require_safe_path()
        if not (self.preview_path / ".git").exists():
            raise PreviewError(
                f"preview worktree does not exist: {self.preview_path}; run make preview"
            )
        self.sha = self.git("rev-parse", "HEAD", at_preview=True, capture=True)

    def preview_environment(self) -> dict[str, str]:
        return {
            **os.environ,
            "POSTGRES_DB": PREVIEW_DATABASE,
            "POSTGRES_USER": PREVIEW_USER,
            "POSTGRES_PASSWORD": PREVIEW_PASSWORD,
            "FLORABASE_DATABASE_URL": (
                f"postgresql+psycopg://{PREVIEW_USER}:{PREVIEW_PASSWORD}@db:5432/{PREVIEW_DATABASE}"
            ),
            "FLORABASE_CANONICAL_ORIGIN": PREVIEW_URL,
            "APP_BIND_ADDRESS": "127.0.0.1",
            "APP_PORT": "15173",
            "FLORABASE_PREVIEW_REF": self.ref,
            "FLORABASE_PREVIEW_SHA": self.sha,
        }

    def compose_command(self, *args: str) -> list[str]:
        return [
            "docker",
            "compose",
            "--project-name",
            PROJECT,
            "--project-directory",
            str(self.preview_path),
            "--file",
            str(self.preview_path / "compose.yaml"),
            "--file",
            str(self.repository / "compose.preview.yaml"),
            *args,
        ]

    def compose(
        self,
        *args: str,
        capture: bool = False,
        check: bool = True,
        stdin: IO[bytes] | None = None,
        stdout: IO[bytes] | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> str:
        environment = self.preview_environment()
        environment.update(extra_env or {})
        return self.commands.run(
            self.compose_command(*args),
            capture=capture,
            check=check,
            env=environment,
            stdin=stdin,
            stdout=stdout,
        )

    def dev_compose(
        self,
        *args: str,
        capture: bool = False,
        stdin: IO[bytes] | None = None,
        stdout: IO[bytes] | None = None,
    ) -> str:
        command = [
            "docker",
            "compose",
            "--project-name",
            DEV_PROJECT,
            "--project-directory",
            str(self.repository),
            "--file",
            str(self.repository / "compose.yaml"),
            "--file",
            str(self.repository / "compose.dev.yaml"),
            *args,
        ]
        return self.commands.run(
            command, capture=capture, env=os.environ.copy(), stdin=stdin, stdout=stdout
        )

    def validate_compose_config(self) -> None:
        raw = self.compose("config", "--format", "json", capture=True)
        try:
            config = json.loads(raw)
            services = config["services"]
            volumes = config["volumes"]
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            raise PreviewError(
                "could not validate rendered preview Compose configuration"
            ) from error
        if services["db"].get("ports") or services["backend"].get("ports"):
            raise PreviewError("preview PostgreSQL and backend must not publish host ports")
        ports = services["frontend"].get("ports", [])
        if len(ports) != 1:
            raise PreviewError("preview frontend must publish exactly one host port")
        port = ports[0]
        if not (
            str(port.get("published")) == "15173"
            and str(port.get("target")) == "8080"
            and port.get("host_ip") == "127.0.0.1"
        ):
            raise PreviewError("preview frontend port must be 127.0.0.1:15173 -> 8080")
        if "postgres_data" not in volumes:
            raise PreviewError("preview Compose configuration has no persistent PostgreSQL volume")
        if volumes["postgres_data"].get("name") != f"{PROJECT}_postgres_data":
            raise PreviewError("preview PostgreSQL volume is not isolated by the preview project")
        networks = config.get("networks", {})
        if networks.get("internal", {}).get("name") != f"{PROJECT}_internal":
            raise PreviewError("preview network is not isolated by the preview project")
        expected_contexts = {
            "backend": str(self.preview_path / "backend"),
            "frontend": str(self.preview_path / "frontend"),
        }
        for service, expected_context in expected_contexts.items():
            actual_context = services[service].get("build", {}).get("context")
            if Path(str(actual_context)).resolve() != Path(expected_context).resolve():
                raise PreviewError(
                    f"preview {service} build context does not resolve inside the preview worktree"
                )
        backend_environment = services["backend"].get("environment", {})
        expected = {
            "FLORABASE_ENVIRONMENT": "development",
            "FLORABASE_CANONICAL_ORIGIN": PREVIEW_URL,
            "FLORABASE_COOKIE_MODE": "loopback-development",
        }
        if any(backend_environment.get(key) != value for key, value in expected.items()):
            raise PreviewError("preview backend local origin/cookie configuration is inconsistent")

    def database_revisions(self, *, development: bool = False) -> list[str]:
        compose = self.dev_compose if development else self.compose
        table = compose(
            "exec",
            "-T",
            "db",
            "sh",
            "-c",
            'psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --tuples-only '
            "--no-align --command \"SELECT to_regclass('public.alembic_version');\"",
            capture=True,
        )
        if not table.strip():
            return []
        raw = compose(
            "exec",
            "-T",
            "db",
            "sh",
            "-c",
            'psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --tuples-only '
            '--no-align --command "SELECT version_num FROM alembic_version ORDER BY version_num;"',
            capture=True,
        )
        return [value for value in raw.splitlines() if value]

    def ensure_revisions_upgradeable(self, revisions: list[str]) -> None:
        if not revisions:
            return
        code = """
import os
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.script.revision import RangeNotAncestorError, ResolutionError
script = ScriptDirectory.from_config(Config('alembic.ini'))
heads = script.get_heads()
for current in os.environ['FLORABASE_SOURCE_REVISIONS'].split(','):
    try:
        script.get_revision(current)
        valid = current in heads or any(
            any(item.revision == current for item in script.iterate_revisions(head, current))
            for head in heads
        )
    except (ResolutionError, RangeNotAncestorError):
        valid = False
    if not valid:
        raise SystemExit(f'database revision {current} cannot be upgraded by selected preview code')
"""
        self.compose(
            "run",
            "--rm",
            "--no-deps",
            "-e",
            "FLORABASE_SOURCE_REVISIONS",
            "backend",
            "python",
            "-c",
            code,
            extra_env={"FLORABASE_SOURCE_REVISIONS": ",".join(revisions)},
        )

    def migrate_forward(self) -> list[str]:
        revisions = self.database_revisions()
        try:
            self.ensure_revisions_upgradeable(revisions)
        except PreviewError as error:
            raise PreviewError(
                "selected ref cannot safely use the current preview database; choose another ref "
                "or replace preview data through the supported import workflow"
            ) from error
        self.compose("run", "--rm", "backend", "alembic", "upgrade", "head")
        return self.database_revisions()

    def owner_exists(self) -> bool:
        raw = self.compose(
            "exec",
            "-T",
            "db",
            "sh",
            "-c",
            'psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --tuples-only '
            '--no-align --command "SELECT EXISTS (SELECT 1 FROM users WHERE owner);"',
            capture=True,
        )
        return raw.strip() == "t"

    def wait_for_readiness(self, timeout: int = 60) -> None:
        deadline = time.monotonic() + timeout
        last_error = "no response"
        for path in ("/healthz", "/api/v1/ready"):
            while time.monotonic() < deadline:
                try:
                    with self.urlopen(f"{PREVIEW_URL}{path}", timeout=3) as response:
                        if 200 <= response.status < 300:
                            break
                        last_error = f"HTTP {response.status} from {path}"
                except (OSError, urllib.error.URLError) as error:
                    last_error = str(error)
                self.sleep(1)
            else:
                self.compose("ps", "--all", check=False)
                raise PreviewError(
                    f"preview readiness failed: {last_error}; inspect logs with: "
                    f"docker compose --project-name {PROJECT} --project-directory "
                    f"{self.preview_path} --file {self.preview_path / 'compose.yaml'} --file "
                    f"{self.repository / 'compose.preview.yaml'} logs --tail=100"
                )

    def start(self, ref: str) -> None:
        self.resolve_and_prepare_worktree(ref)
        if not (self.preview_path / "compose.yaml").is_file():
            raise PreviewError("selected preview revision has no compose.yaml")
        self.validate_compose_config()
        self.compose("build", "backend", "frontend")
        self.compose("up", "--detach", "--wait", "--wait-timeout", "120", "db")
        revisions = self.migrate_forward()
        try:
            self.compose("up", "--detach", "--wait", "--wait-timeout", "120", "--remove-orphans")
            self.wait_for_readiness()
        except PreviewError:
            self.compose("ps", "--all", check=False)
            raise
        print("Florabase preview ready")
        print(f"Ref: {self.ref}")
        print(f"SHA: {self.sha}")
        print(f"URL: {PREVIEW_URL}")
        print(f"Compose project: {PROJECT}")
        revision_label = ",".join(revisions) or "unversioned"
        print(f"Database: persistent isolated preview database ({revision_label})")
        if not self.owner_exists():
            print("Owner: none; create one with: make preview-bootstrap-owner LOGIN=owner")

    def bootstrap_owner(self, login: str) -> None:
        self.require_worktree()
        if not login or any(character.isspace() for character in login):
            raise PreviewError("LOGIN must be a non-empty login name without whitespace")
        self.compose("run", "--rm", "backend", "python", "-m", "florabase.auth.bootstrap", login)

    def stop(self) -> None:
        self.require_worktree()
        self.compose("down", "--remove-orphans")
        print(f"Stopped {PROJECT}; persistent database volume was preserved")

    def remove(self) -> None:
        self.require_worktree()
        dirty = self.git("status", "--porcelain=v1", at_preview=True, capture=True)
        if dirty:
            raise PreviewError("preview worktree has local changes; refusing removal")
        self.stop()
        self.git("worktree", "remove", str(self.preview_path))
        print(f"Removed preview worktree; {PROJECT}_postgres_data was preserved")

    def import_development(self, confirm: str, confirm_database: str) -> None:
        self.require_worktree()
        if confirm != "yes" or confirm_database != PREVIEW_DATABASE:
            raise PreviewError(
                "import replaces preview data only; re-run with CONFIRM_REPLACE_PREVIEW=yes "
                f"CONFIRM_DATABASE={PREVIEW_DATABASE}"
            )
        self.validate_compose_config()
        self.compose("build", "backend")
        self.compose("up", "--detach", "--wait", "--wait-timeout", "120", "db")
        source_database = self.dev_compose(
            "exec", "-T", "db", "sh", "-c", 'printf "%s" "$POSTGRES_DB"', capture=True
        )
        target_database = self.compose(
            "exec", "-T", "db", "sh", "-c", 'printf "%s" "$POSTGRES_DB"', capture=True
        )
        if not source_database or source_database == PREVIEW_DATABASE:
            raise PreviewError("development source database identity is unsafe or ambiguous")
        if target_database != PREVIEW_DATABASE:
            raise PreviewError("preview restore target database identity does not match the guard")
        source_revisions = self.database_revisions(development=True)
        if not source_revisions:
            raise PreviewError(
                "development source has no Alembic revision; preview data was not replaced"
            )
        try:
            self.ensure_revisions_upgradeable(source_revisions)
        except PreviewError as error:
            raise PreviewError(
                "development database is newer or incompatible with the selected preview ref; "
                "preview data was not replaced"
            ) from error

        temporary_dir = Path(tempfile.mkdtemp(prefix="florabase-preview-import-"))
        dump = temporary_dir / "development.dump"
        try:
            with dump.open("wb") as output:
                self.dev_compose(
                    "exec",
                    "-T",
                    "db",
                    "sh",
                    "-c",
                    'pg_dump --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" '
                    "--format=custom --no-owner --no-privileges",
                    stdout=output,
                )
            if not dump.is_file() or dump.stat().st_size == 0:
                raise PreviewError("development database dump is empty")
            with dump.open("rb") as source:
                self.dev_compose("exec", "-T", "db", "pg_restore", "--list", stdin=source)
            self.compose("stop", "backend", "frontend", check=False)
            self.compose(
                "exec",
                "-T",
                "db",
                "sh",
                "-c",
                'dropdb --if-exists --force --username "$POSTGRES_USER" "$POSTGRES_DB" && '
                'createdb --username "$POSTGRES_USER" --owner "$POSTGRES_USER" "$POSTGRES_DB"',
            )
            with dump.open("rb") as source:
                self.compose(
                    "exec",
                    "-T",
                    "db",
                    "sh",
                    "-c",
                    'pg_restore --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" '
                    "--no-owner --no-privileges",
                    stdin=source,
                )
            revisions = self.migrate_forward()
            self.compose("up", "--detach", "--wait", "--wait-timeout", "120", "--remove-orphans")
            self.wait_for_readiness()
        finally:
            shutil.rmtree(temporary_dir)
        print("Development data imported into the isolated preview database")
        print(f"Preview revisions: {','.join(revisions) or 'unversioned'}")
        print(f"URL: {PREVIEW_URL}")

    def status(self) -> None:
        print(f"Worktree: {self.preview_path}")
        if (self.preview_path / ".git").exists():
            sha = self.git("rev-parse", "HEAD", at_preview=True, capture=True)
            dirty = bool(self.git("status", "--porcelain=v1", at_preview=True, capture=True))
            print(f"SHA: {sha}")
            print(f"Git: {'dirty' if dirty else 'clean'} (detached preview worktree)")
        else:
            print("Git: preview worktree absent")
        print(f"Compose project: {PROJECT}")
        print(f"URL: {PREVIEW_URL}")
        raw = self.commands.run(
            [
                "docker",
                "ps",
                "--all",
                "--filter",
                f"label=com.docker.compose.project={PROJECT}",
                "--format",
                "{{json .}}",
            ],
            capture=True,
            check=False,
        )
        containers = []
        for line in raw.splitlines():
            try:
                containers.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        if containers:
            for container in containers:
                print(
                    "Service: "
                    f"{container.get('Names', 'unknown')} — {container.get('Status', 'unknown')}"
                )
        else:
            print("Services: none")
        if containers and containers[0].get("ID"):
            labels_raw = self.commands.run(
                [
                    "docker",
                    "inspect",
                    "--format",
                    "{{json .Config.Labels}}",
                    str(containers[0]["ID"]),
                ],
                capture=True,
                check=False,
            )
            try:
                labels = json.loads(labels_raw)
            except json.JSONDecodeError:
                labels = {}
            if labels.get("io.florabase.preview.ref"):
                print(f"Ref: {labels['io.florabase.preview.ref']}")
        volume = self.commands.run(
            ["docker", "volume", "inspect", f"{PROJECT}_postgres_data", "--format", "{{.Name}}"],
            capture=True,
            check=False,
        )
        print(f"Database volume: {volume or 'absent'}")
        if (self.preview_path / ".git").exists() and any(
            "db" in str(container.get("Names", "")) and "Up" in str(container.get("Status", ""))
            for container in containers
        ):
            self.sha = self.git("rev-parse", "HEAD", at_preview=True, capture=True)
            try:
                revisions = self.database_revisions()
                print(f"Alembic: {','.join(revisions) or 'unversioned'}")
            except PreviewError:
                print("Alembic: unavailable")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--path",
        default="../florabase-preview",
        help="preview worktree path relative to repository",
    )
    subcommands = result.add_subparsers(dest="command", required=True)
    start = subcommands.add_parser("start")
    start.add_argument("--ref", default=DEFAULT_REF)
    bootstrap = subcommands.add_parser("bootstrap-owner")
    bootstrap.add_argument("--login", default="owner")
    subcommands.add_parser("stop")
    subcommands.add_parser("remove")
    status = subcommands.add_parser("status")
    status.set_defaults(no_worktree_required=True)
    import_dev = subcommands.add_parser("import-dev")
    import_dev.add_argument("--confirm", default="")
    import_dev.add_argument("--confirm-database", default="")
    return result


def main() -> int:
    args = parser().parse_args()
    repository = Path(__file__).resolve().parents[1]
    requested_path = Path(args.path)
    preview_path = requested_path if requested_path.is_absolute() else repository / requested_path
    preview = Preview(repository, preview_path)
    try:
        if args.command == "start":
            preview.start(args.ref)
        elif args.command == "bootstrap-owner":
            preview.bootstrap_owner(args.login)
        elif args.command == "stop":
            preview.stop()
        elif args.command == "remove":
            preview.remove()
        elif args.command == "status":
            preview.status()
        elif args.command == "import-dev":
            preview.import_development(args.confirm, args.confirm_database)
    except PreviewError as error:
        print(f"preview: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
