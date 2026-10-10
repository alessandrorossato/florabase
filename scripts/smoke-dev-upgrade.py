#!/usr/bin/env python3
"""Prove DEV upgrade image freshness/retry on UUID-scoped disposable Compose state."""

from __future__ import annotations

import json
import shutil
import tempfile
import uuid
from pathlib import Path

from smoke_lifecycle import SmokeLifecycle
from workflow_environment import (
    Environment,
    Repository,
    WorkflowError,
    code_heads,
    migration_graph,
    run,
)
from workflow_resources import Resources


def require(condition: bool, message: str) -> None:
    if not condition:
        raise WorkflowError(f"DEV upgrade smoke: {message}")


def operator_snapshot(repository: Repository) -> dict[str, object]:
    identifiers: list[str] = []
    volumes: list[str] = []
    for project in ("florabase", "florabase-feature-review", "florabase-preview", "florabase-prod"):
        identifiers.extend(
            run(
                ["docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={project}"],
                capture=True,
            ).splitlines()
        )
        volumes.extend(
            run(
                [
                    "docker",
                    "volume",
                    "ls",
                    "-q",
                    "--filter",
                    f"label=com.docker.compose.project={project}",
                ],
                capture=True,
            ).splitlines()
        )
    containers = (
        json.loads(run(["docker", "inspect", *identifiers], capture=True)) if identifiers else []
    )
    return {
        "primary": Repository(repository.primary).identity(),
        "containers": sorted(
            (item["Id"], item["State"]["StartedAt"], item["State"]["Running"], item["Mounts"])
            for item in containers
        ),
        "volumes": json.loads(run(["docker", "volume", "inspect", *sorted(volumes)], capture=True))
        if volumes
        else [],
    }


class FixtureEnvironment(Environment):
    def __init__(self, repository: Repository, project: str) -> None:
        super().__init__(repository, "dev")
        self.project = project
        self.commands: list[tuple[str, ...]] = []
        self.env_source = Path("/dev/null")

    def environment(self) -> dict[str, str]:
        environment = super().environment()
        environment.update(
            {
                "POSTGRES_DB": "upgrade_fixture",
                "POSTGRES_USER": "upgrade_fixture",
                "POSTGRES_PASSWORD": "local-fixture-only",
                "FLORABASE_DATABASE_URL": "postgresql+psycopg://upgrade_fixture:local-fixture-only@db:5432/upgrade_fixture",
                "POSTGRES_PORT": "0",
                "FRONTEND_PORT": "0",
                "BACKEND_PORT": "0",
            }
        )
        return environment

    def compose(self, *args: str, capture: bool = False) -> str:
        self.commands.append(args)
        return super().compose(*args, capture=capture)

    def prepare_initializer(self, *services: str) -> str:
        image = super().prepare_initializer(*services)
        self.commands.append(("initializer-preflight", image))
        return image

    def sql(self, query: str) -> str:
        return self.compose(
            "exec",
            "-T",
            "db",
            "sh",
            "-ec",
            'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "$1"',
            "fixture",
            query,
            capture=True,
        )

    def markers(self, *, seed: bool = False) -> None:
        if seed:
            command = "printf media > /state/attachments/.upgrade-marker; printf dependencies > /app/node_modules/.upgrade-marker; chown 0:0 /state/attachments/.upgrade-marker /app/node_modules/.upgrade-marker"
        else:
            command = 'test "$(cat /state/attachments/.upgrade-marker)" = media; test "$(cat /app/node_modules/.upgrade-marker)" = dependencies; test "$(stat -c %u:%g /state/attachments/.upgrade-marker)" = "$LOCAL_UID:$LOCAL_GID"; test "$(stat -c %u:%g /app/node_modules/.upgrade-marker)" = "$LOCAL_UID:$LOCAL_GID"; test "$(stat -c %a /state/attachments)" = 700'
        self.compose(
            "run", "--rm", "-T", "--no-deps", "--entrypoint", "sh", "dev-state-init", "-ec", command
        )


def main() -> None:
    repository = Repository(Path.cwd())
    before = operator_snapshot(repository)
    project = f"florabase-dev-upgrade-smoke-{uuid.uuid4().hex[:12]}"
    frontend_image = f"{project}-frontend-development"
    with tempfile.TemporaryDirectory(prefix="florabase upgrade spaces ") as temporary:
        source = Path(temporary)
        for name in ("backend", "frontend"):
            shutil.copytree(
                repository.source / name,
                source / name,
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
        for name in ("compose.yaml", "compose.dev.yaml"):
            shutil.copy2(repository.source / name, source / name)
        # A disposable source repository, never a worktree/commit in the operator repository.
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
            run(["git", "-C", str(source), *args], capture=True)
        env = FixtureEnvironment(Repository(source), project)
        require(
            project.startswith("florabase-dev-upgrade-smoke-") and project != "florabase",
            "unsafe project",
        )
        volume_names = [
            f"{project}_{name}"
            for name in ("postgres_data", "attachment_data", "frontend_node_modules")
        ]
        require(not env.containers(), "project already exists")
        require(
            not run(
                ["docker", "volume", "ls", "-q", "--filter", f"name=^{project}_"], capture=True
            ),
            "volumes already exist",
        )
        require(
            not run(["docker", "image", "ls", "-q", frontend_image], capture=True),
            "image already exists",
        )
        with SmokeLifecycle(env) as lifetime:
            graph = migration_graph(source)
            head = code_heads(graph)[0]
            require(len(graph[head]) == 1, "fixture needs one previous revision")
            previous = graph[head][0]
            # The real dependency stage predates installation of the initializer executable.
            run(
                [
                    "docker",
                    "build",
                    "--target",
                    "dependencies",
                    *[
                        part
                        for key, value in lifetime.owner.labels().items()
                        for part in ("--label", f"{key}={value}")
                    ],
                    "--tag",
                    frontend_image,
                    str(source / "frontend"),
                ]
            )
            stale_id = run(
                ["docker", "image", "inspect", "--format", "{{.Id}}", frontend_image], capture=True
            )
            run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--entrypoint",
                    "sh",
                    frontend_image,
                    "-ec",
                    "! command -v florabase-dev-state-init",
                ]
            )
            env.compose("build", "backend")
            env.start_database()
            env.compose("run", "--rm", "-T", "--no-deps", "backend", "alembic", "upgrade", previous)
            require(env.current() == [previous], "fixture not one revision behind")
            env.sql(
                "CREATE TABLE upgrade_fixture_state (value text NOT NULL); INSERT INTO upgrade_fixture_state VALUES ('preserved');"
            )
            env.markers(seed=True)
            volume_before = run(["docker", "volume", "inspect", *volume_names], capture=True)
            db_id = env.compose("ps", "-q", "db", capture=True)
            dockerfile = source / "frontend/Dockerfile"
            original = dockerfile.read_text()
            dockerfile.write_text("FROM invalid fixture syntax\n")
            try:
                env.upgrade_state()
            except WorkflowError:
                require(env.current() == [previous], "build failure mutated DB")
                require(
                    env.sql("SELECT value FROM upgrade_fixture_state") == "preserved",
                    "build failure lost DB data",
                )
                print("BUILD_FAILURE_BEFORE_MIGRATION_PASSED")
            else:
                raise WorkflowError("invalid initializer Dockerfile unexpectedly built")
            finally:
                dockerfile.write_text(original)
            for image_state in ("stale", "retry-at-head", "absent"):
                if image_state == "absent":
                    image = json.loads(
                        run(["docker", "image", "inspect", frontend_image], capture=True)
                    )[0]
                    Resources(lifetime.owner).prove(image, "images")
                    require(
                        not Resources(lifetime.owner).users("ancestor", str(image["Id"])),
                        "fixture image has a container user",
                    )
                    run(["docker", "image", "rm", frontend_image])
                env.commands.clear()
                env.upgrade_state()  # Exactly the orchestration used by the supported CLI.
                commands = list(env.commands)
                build = commands.index(("build", "backend", "dev-state-init"))
                probe = next(
                    index
                    for index, command in enumerate(commands)
                    if command[:1] == ("initializer-preflight",)
                )
                migrate = next(
                    index for index, command in enumerate(commands) if "alembic" in command
                )
                initialize = commands.index(("run", "--rm", "-T", "--no-deps", "dev-state-init"))
                require(
                    build < probe < migrate < initialize, "runtime preparation/migration ordering"
                )
                require(env.current() == [head], "DB failed to reach head")
                require(
                    env.sql("SELECT value FROM upgrade_fixture_state") == "preserved",
                    "DB marker lost",
                )
                env.markers()
                require(
                    run(["docker", "volume", "inspect", *volume_names], capture=True)
                    == volume_before,
                    "persistent volumes replaced",
                )
                require(
                    env.compose("ps", "-q", "db", capture=True) == db_id, "DB container recreated"
                )
                current_id = run(
                    ["docker", "image", "inspect", "--format", "{{.Id}}", frontend_image],
                    capture=True,
                )
                require(current_id != stale_id, "stale image still in use")
                print(
                    f"UPGRADE_{image_state.upper()}_PASSED: {previous} -> {head}; DB/media/dependencies intact"
                )
                env.markers(seed=True)  # Retry must repair ownership idempotently again.
        require(
            operator_snapshot(repository) == before,
            "operator environments/volumes or primary Git changed",
        )
    print(
        "DEV_UPGRADE_SMOKE_PASSED: stale/absent images, pending migration, at-head retry, failed build, executable preflight, persistent state; fixture cleaned; operator state unchanged"
    )


if __name__ == "__main__":
    main()
