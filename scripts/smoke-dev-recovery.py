#!/usr/bin/env python3
"""Real DEV recovery on unique disposable fixtures; never operates operator environments."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import cast

import compose_stacks
from smoke_lifecycle import SmokeLifecycle, overlay
from workflow_environment import (
    Environment,
    Repository,
    WorkflowError,
    code_heads,
    migration_graph,
    run,
)


def require(value: bool, message: str) -> None:
    if not value:
        raise WorkflowError(f"DEV recovery smoke: {message}")


def operator_snapshot(repo: Repository) -> dict[str, object]:
    projects = ("florabase", "florabase-feature-review", "florabase-preview", "florabase-prod")
    identifiers = []
    for project in projects:
        identifiers.extend(
            run(
                ["docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={project}"],
                capture=True,
            ).splitlines()
        )
    items = (
        json.loads(run(["docker", "inspect", *identifiers], capture=True)) if identifiers else []
    )
    return {
        "primary": Repository(repo.primary).identity(),
        "containers": sorted(
            (item["Id"], item["State"]["StartedAt"], item["State"]["Running"], item["Mounts"])
            for item in items
        ),
    }


class FixtureEnvironment(Environment):
    def environment(self) -> dict[str, str]:
        env = super().environment()
        env.update(
            {
                "POSTGRES_DB": "recovery_fixture",
                "POSTGRES_USER": "recovery_fixture",
                "POSTGRES_PASSWORD": "local-fixture-only",
                "FLORABASE_DATABASE_URL": "postgresql+psycopg://recovery_fixture:local-fixture-only@db:5432/recovery_fixture",
                "FRONTEND_PORT": "0",
                "BACKEND_PORT": "0",
                "POSTGRES_PORT": "0",
                "LOCAL_UID": "1000",
                "LOCAL_GID": "1000",
            }
        )
        return env


def old_baseline(source: Path) -> dict[str, object]:
    """The production source build as one standalone file, as trees before WF-09 tracked it."""
    files = compose_stacks.files(source, "prod")
    rendered = run(
        [
            "docker",
            "compose",
            "--project-directory",
            str(source),
            *[part for path in files for part in ("--file", str(path))],
            "config",
            "--no-interpolate",
            "--format",
            "json",
        ],
        capture=True,
    )
    baseline: dict[str, object] = json.loads(rendered)
    baseline.pop("name", None)
    # Rendering under the generator's `florabase-prod` name pins network/volume names; the old
    # source's own project must own them, never the production names.
    for kind in ("networks", "volumes"):
        for entry in cast(dict[str, dict[str, object]], baseline.get(kind, {})).values():
            entry.pop("name", None)
    services = cast(dict[str, object], baseline["services"])
    services.pop("dev-state-init", None)
    return baseline


def main() -> None:
    repository = Repository(Path.cwd())
    before = operator_snapshot(repository)
    project = f"florabase-dev-recovery-smoke-{uuid.uuid4().hex[:12]}"
    # This is a source fixture in a temporary directory, never another Git worktree.
    with tempfile.TemporaryDirectory(prefix="florabase recovery spaces ") as temporary:
        primary, old = Path(temporary) / "primary", Path(temporary) / "unavailable old source"
        primary.mkdir()
        for name in ("backend", "frontend"):
            shutil.copytree(
                repository.source / name,
                primary / name,
                ignore=shutil.ignore_patterns(
                    "node_modules",
                    "dist",
                    ".venv",
                    "__pycache__",
                    ".pytest_cache",
                    ".mypy_cache",
                    ".ruff_cache",
                    ".coverage",
                    "htmlcov",
                    "coverage",
                    "*.tsbuildinfo",
                ),
            )
        shutil.copy2(repository.source / "compose.dev.yaml", primary / "compose.dev.yaml")
        # WF-09: without the generator the fixture reads as a pre-WF-09 tree.
        (primary / "scripts").mkdir()
        shutil.copy2(
            repository.source / "scripts/compose_stacks.py", primary / "scripts/compose_stacks.py"
        )
        (primary / ".gitignore").write_text(".env\n")
        (primary / ".env").write_text(
            "POSTGRES_DB=recovery_fixture\nPOSTGRES_USER=recovery_fixture\n"
            "POSTGRES_PASSWORD=local-fixture-only\n"
            "FLORABASE_DATABASE_URL=postgresql+psycopg://recovery_fixture:local-fixture-only@db:5432/recovery_fixture\n"
            "FRONTEND_PORT=0\nBACKEND_PORT=0\nPOSTGRES_PORT=0\n"
        )
        for args in (
            ("init", "--initial-branch=main"),
            ("add", "."),
            (
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-m",
                "fixture",
            ),
        ):
            run(["git", "-C", str(primary), *args], capture=True)
        env = FixtureEnvironment(Repository(primary), "dev")
        env.project = project  # Internal fixture only; production CLI has no project override.
        require(env.project != "florabase", "refusing operator DEV project")
        require(not env.containers(), "fixture project unexpectedly exists")
        require(
            not run(
                ["docker", "volume", "ls", "-q", "--filter", f"name=^{project}_"], capture=True
            ),
            "fixture volumes already exist",
        )
        inherited_env_file = os.environ.pop("FLORABASE_ENV_FILE", None)
        env.env_source = primary / ".env"
        with SmokeLifecycle(env) as lifecycle:
            try:
                env.compose("build")
                shutil.copytree(primary, old, ignore=shutil.ignore_patterns(".git"))
                # Model a source from before ADR 0008: a standalone source-build compose.yaml, a
                # development override and tracked workflow overlays (compose.review.yaml).
                baseline = old_baseline(old)
                # Rendered by the generator; the old source itself predates WF-09 and lacks it.
                (old / "scripts/compose_stacks.py").unlink()
                (old / "compose.yaml").write_text(json.dumps(baseline))
                (old / "compose.review.yaml").write_text("services: {}\n")
                # Model the real older development override, including its tmpfs media and retained
                # durable attachment mount. Automatic Compose labels are the legacy identity evidence.
                (old / "compose.dev.yaml").write_text(
                    json.dumps(
                        {
                            "services": {
                                "db": {"ports": ["127.0.0.1::5432"]},
                                "backend": {
                                    "image": f"{project}-backend-development",
                                    "build": {"target": "development"},
                                    "user": "1000:1000",
                                    "command": ["sleep", "3600"],
                                    "environment": {
                                        "FLORABASE_ENVIRONMENT": "development",
                                        "FLORABASE_COOKIE_MODE": "loopback-development",
                                        "FLORABASE_ATTACHMENT_STORAGE_ROOT": "/tmp/florabase-attachments",
                                    },
                                    "volumes": [
                                        "./backend/src:/app/src",
                                        "./backend/alembic:/app/alembic",
                                    ],
                                    "tmpfs": [
                                        "/tmp/florabase-attachments:uid=1000,gid=1000,mode=0700"
                                    ],
                                    "healthcheck": {"test": ["CMD", "true"]},
                                },
                                "frontend": {
                                    "image": f"{project}-frontend-development",
                                    "build": {"target": "development"},
                                    "entrypoint": ["sleep", "3600"],
                                    "user": "1000:1000",
                                    "volumes": [
                                        "./frontend:/app",
                                        "frontend_node_modules:/app/node_modules",
                                    ],
                                    "healthcheck": {"test": ["CMD", "true"]},
                                },
                            },
                            "volumes": {"frontend_node_modules": {}},
                        }
                    )
                )
                old_env = FixtureEnvironment(Repository(primary), "dev")
                old_env.project, old_env.source, old_env.env_source = project, old, primary / ".env"
                # Ownership goes into the legacy override itself: a third Compose file would change
                # the legacy config_files identity, and the current DEV overlay names services the
                # old source does not define.
                legacy_path = old / "compose.dev.yaml"
                legacy = json.loads(legacy_path.read_text())
                owned = overlay(
                    json.loads(old_env.compose("config", "--format", "json", capture=True)),
                    lifecycle.owner,
                )
                for kind, entries in owned.items():
                    for name, value in entries.items():
                        target = legacy.setdefault(kind, {}).setdefault(name, {})
                        for key, item in value.items():
                            target[key] = {**target.get(key, {}), **item}
                legacy_path.write_text(json.dumps(legacy))
                old_env.compose("up", "-d", "--wait", "--wait-timeout", "120")
                env.upgrade()  # Only the fixture DB, using primary migrations.
                old_env.compose(
                    "exec",
                    "-T",
                    "backend",
                    "sh",
                    "-ec",
                    "printf temporary > /tmp/florabase-attachments/recovery-marker",
                )
                old_env.compose(
                    "exec",
                    "-T",
                    "--user",
                    "0:0",
                    "backend",
                    "sh",
                    "-ec",
                    "printf durable > /var/lib/florabase/attachments/durable-marker",
                )
                old_env.compose(
                    "exec",
                    "-T",
                    "--user",
                    "0:0",
                    "frontend",
                    "sh",
                    "-ec",
                    "printf dependencies > /app/node_modules/.recovery-marker",
                )
                old_env.compose(
                    "exec",
                    "-T",
                    "db",
                    "sh",
                    "-ec",
                    'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE TABLE recovery_state (value text); INSERT INTO recovery_state VALUES (\'preserved\');"',
                )
                original_ids = {item["Id"] for item in env.containers()}
                volumes_before = run(
                    [
                        "docker",
                        "volume",
                        "inspect",
                        *[
                            f"{project}_{key}"
                            for key in ("postgres_data", "attachment_data", "frontend_node_modules")
                        ],
                    ],
                    capture=True,
                )
                try:
                    env.status()
                except WorkflowError as error:
                    require("make dev-stop" in str(error), "status lacks supported recovery action")
                else:
                    raise WorkflowError("foreign-source status did not refuse")
                # Simulate a vanished Codex source. Recovery must use only the existing Docker identity.
                shutil.rmtree(old)
                env.stop()
                stopped = env.containers()
                require(
                    {item["Id"] for item in stopped} == original_ids,
                    "stop removed/replaced containers",
                )
                require(
                    all(not item["State"]["Running"] for item in stopped),
                    "containers still running",
                )
                require(
                    run(
                        [
                            "docker",
                            "volume",
                            "inspect",
                            *[
                                f"{project}_{key}"
                                for key in (
                                    "postgres_data",
                                    "attachment_data",
                                    "frontend_node_modules",
                                )
                            ],
                        ],
                        capture=True,
                    )
                    == volumes_before,
                    "stop changed volume identities",
                )
                env.stop()  # Idempotent; stopped backend tmpfs is never read again.
                try:
                    env.up()
                except WorkflowError:
                    env.compose("logs", "--no-color", "--tail=60")
                    raise
                require(
                    all(
                        item["Config"]["Labels"].get("io.florabase.source") == str(primary)
                        for item in env.containers()
                    ),
                    "primary source was not adopted",
                )
                for service, command in (
                    (
                        "backend",
                        "test $(cat /var/lib/florabase/attachments/recovery-marker) = temporary; test $(cat /var/lib/florabase/attachments/durable-marker) = durable",
                    ),
                    (
                        "frontend",
                        "test $(cat /app/node_modules/.recovery-marker) = dependencies; test $(id -u) != 0",
                    ),
                    (
                        "db",
                        'test "$(psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc \'SELECT value FROM recovery_state\')" = preserved',
                    ),
                ):
                    env.compose("exec", "-T", service, "sh", "-ec", command)
                head = code_heads(migration_graph(primary))[0]
                env.compose(
                    "exec",
                    "-T",
                    "db",
                    "sh",
                    "-ec",
                    'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "UPDATE alembic_version SET version_num = \'fixture_ahead\';"',
                )
                env.stop()
                for operation in (env.up, env.upgrade):
                    try:
                        operation()
                    except WorkflowError as error:
                        require(
                            "AHEAD OF OR INCOMPATIBLE" in str(error),
                            "ahead revision lacks clear refusal",
                        )
                    else:
                        raise WorkflowError("ahead-of-code fixture DB was accepted")
                    require(env.current() == ["fixture_ahead"], "DB was downgraded")
                    require(
                        not any(
                            item["State"]["Running"]
                            for item in env.containers()
                            if item["Config"]["Labels"]["com.docker.compose.service"]
                            in {"backend", "frontend"}
                        ),
                        "ahead DB started application",
                    )
                env.compose(
                    "exec",
                    "-T",
                    "db",
                    "sh",
                    "-ec",
                    f'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "UPDATE alembic_version SET version_num = \'{head}\';"',
                )
                require(
                    operator_snapshot(repository) == before,
                    "operator environments or primary Git changed",
                )
                print(
                    "DEV_RECOVERY_SMOKE_PASSED: absent old source, tmpfs+durable media, DB/dependencies, idempotent stop, primary restart, ahead refusal; operator DEV/Review/Preview/Prod unchanged"
                )
            finally:
                # Only this UUID project, proven absent before the fixture, is disposable.
                if inherited_env_file is not None:
                    os.environ["FLORABASE_ENV_FILE"] = inherited_env_file
    require(
        operator_snapshot(repository) == before, "operator state changed during fixture cleanup"
    )


if __name__ == "__main__":
    main()
