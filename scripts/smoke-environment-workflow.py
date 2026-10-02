#!/usr/bin/env python3
"""Real linked-worktree Compose acceptance, using only fresh isolated resources.

Refuses an existing Review project/volume. Never creates another worktree, changes primary
Git state, or starts/stops/writes DEV. Preview is tested from a Git archive of origin/main.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

from workflow_environment import (
    Environment,
    Repository,
    WorkflowError,
    code_heads,
    migration_graph,
    run,
)


def assert_equal(actual: object, expected: object, message: str) -> None:
    if actual != expected:
        raise WorkflowError(f"smoke assertion failed: {message}: {actual!r} != {expected!r}")


def dev_snapshot(dev: Environment) -> dict[str, object]:
    containers = dev.containers()
    return {
        "git_head": dev.repo.git("rev-parse", "HEAD"),
        "git_branch": dev.repo.git("branch", "--show-current"),
        "git_status": dev.repo.git("status", "--porcelain"),
        "containers": [
            (item["Id"], item["State"]["StartedAt"], item["Mounts"]) for item in containers
        ],
        "revisions": dev.current()
        if any(
            item["State"].get("Running")
            and item["Config"]["Labels"].get("com.docker.compose.service") == "db"
            for item in containers
        )
        else None,
    }


def main() -> None:
    repo = Repository(Path.cwd())
    if repo.source == repo.primary:
        raise WorkflowError("run smoke from the existing linked feature worktree")
    review, dev = Environment(repo, "review"), Environment(repo, "dev")
    existing = run(
        [
            "docker",
            "volume",
            "ls",
            "-q",
            "--filter",
            f"name=^{review.project}_",
        ],
        capture=True,
    )
    if review.containers() or existing:
        raise WorkflowError(
            "smoke needs a fresh Review project; preserve/remove existing Review explicitly first"
        )
    repo.initialize()
    before = dev_snapshot(dev)
    assert_equal(before["git_branch"], "main", "primary remains main")
    graph = migration_graph(repo.source)
    base_head = code_heads(graph)[0]
    migration = repo.source / "backend/alembic/versions/workflow_smoke.py"
    if migration.exists():
        raise WorkflowError("temporary smoke migration already exists; refusing overwrite")
    migration.write_text(
        f"revision: str = 'workflow_smoke'\ndown_revision: str = {base_head!r}\n"
        "branch_labels = None\ndepends_on = None\n"
        "def upgrade() -> None:\n    pass\n\ndef downgrade() -> None:\n    pass\n"
    )
    preview_project = "florabase-preview-smoke"
    with tempfile.TemporaryDirectory(prefix="florabase-stable-smoke-") as temporary:
        stable = Path(temporary)
        archive = subprocess.run(
            ["git", "archive", "origin/main"], cwd=repo.source, check=True, stdout=subprocess.PIPE
        ).stdout
        archive_path = stable / "source.tar"
        archive_path.write_bytes(archive)
        with tarfile.open(archive_path) as source:
            source.extractall(stable, filter="data")
        preview_env = {
            **os.environ,
            "POSTGRES_DB": "florabase_preview",
            "POSTGRES_USER": "florabase_preview",
            "POSTGRES_PASSWORD": "local-preview-only-password",
            "FLORABASE_DATABASE_URL": "postgresql+psycopg://florabase_preview:local-preview-only-password@db:5432/florabase_preview",
            "FLORABASE_PREVIEW_REF": "origin/main",
            "FLORABASE_PREVIEW_SHA": repo.git("rev-parse", "origin/main"),
        }
        preview_command = [
            "docker",
            "compose",
            "--env-file",
            "/dev/null",
            "--project-name",
            preview_project,
            "--project-directory",
            str(stable),
            "-f",
            str(stable / "compose.yaml"),
            "-f",
            str(stable / "compose.preview.yaml"),
        ]
        if run(
            [
                "docker",
                "ps",
                "-aq",
                "--filter",
                f"label=com.docker.compose.project={preview_project}",
            ],
            capture=True,
        ) or run(
            [
                "docker",
                "volume",
                "ls",
                "-q",
                "--filter",
                f"name=^{preview_project}_",
            ],
            capture=True,
        ):
            migration.unlink()
            raise WorkflowError("preview-smoke resources already exist; refusing to adopt them")
        try:
            review.up()
            assert_equal(
                review.current(), ["workflow_smoke"], "dirty migration used only in Review"
            )
            assert_equal(
                code_heads(migration_graph(dev.source)), [base_head], "DEV still sees stable head"
            )
            uid = review.compose("exec", "-T", "frontend", "id", "-u", capture=True)
            if uid == "0":
                raise WorkflowError("frontend runtime is root")
            review.compose(
                "exec",
                "-T",
                "frontend",
                "sh",
                "-ec",
                "test -w /app/node_modules/.bin; printf preserved > /app/node_modules/.workflow-smoke",
            )
            review.compose(
                "exec",
                "-T",
                "backend",
                "sh",
                "-ec",
                "printf preserved > /var/lib/florabase/attachments/.workflow-smoke",
            )
            review.compose(
                "exec",
                "-T",
                "db",
                "sh",
                "-ec",
                'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE TABLE workflow_smoke_state (value text); INSERT INTO workflow_smoke_state VALUES (\'preserved\');"',
            )
            config = json.loads(review.compose("config", "--format", "json", capture=True))
            for key in ("postgres_data", "attachment_data", "frontend_node_modules"):
                assert_equal(
                    config["volumes"][key]["name"],
                    f"{review.project}_{key}",
                    "isolated review volume",
                )
            assert_equal(
                config["networks"]["internal"]["name"],
                f"{review.project}_internal",
                "isolated review network",
            )
            # Reproduce root-owned dependency state as an automated regression fixture.
            review.compose(
                "run",
                "--rm",
                "-T",
                "--no-deps",
                "--user",
                "0:0",
                "--entrypoint",
                "sh",
                "frontend",
                "-ec",
                "chown -R 0:0 /app/node_modules/.bin",
            )
            review.stop()
            assert_equal(dev_snapshot(dev), before, "DEV untouched by review startup and stop")
            # Use a source fixture mount to change package+lockfile without touching feature files.
            changed_frontend = stable / "changed-frontend"
            shutil.copytree(
                repo.source / "frontend",
                changed_frontend,
                ignore=shutil.ignore_patterns(
                    "node_modules", "dist", ".pnpm-store", "coverage", "*.tsbuildinfo"
                ),
            )
            review.compose("run", "--rm", "-T", "--no-deps", "dev-state-init")
            fixture_mount = f"{changed_frontend}:/app"
            review.compose(
                "run",
                "--rm",
                "-T",
                "--no-deps",
                "-v",
                fixture_mount,
                "frontend",
                "pnpm",
                "add",
                "--lockfile-only",
                "--save-dev",
                "--save-exact",
                "picocolors@1.1.1",
            )
            review.compose(
                "run",
                "--rm",
                "-T",
                "--no-deps",
                "-v",
                fixture_mount,
                "frontend",
                "node",
                "-e",
                "if(require('picocolors/package.json').version!=='1.1.1')process.exit(1)",
            )
            review.up()
            review.compose(
                "exec",
                "-T",
                "frontend",
                "sh",
                "-ec",
                "test -w /app/node_modules/.bin; test $(cat /app/node_modules/.workflow-smoke) = preserved",
            )
            review.compose(
                "exec",
                "-T",
                "backend",
                "sh",
                "-ec",
                "test $(cat /var/lib/florabase/attachments/.workflow-smoke) = preserved",
            )
            value = review.compose(
                "exec",
                "-T",
                "db",
                "sh",
                "-ec",
                'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT value FROM workflow_smoke_state;"',
                capture=True,
            )
            assert_equal(value, "preserved", "Review DB survives stop/restart")
            run([*preview_command, "config", "--quiet"], env=preview_env)
            run([*preview_command, "build"], env=preview_env)
            run(
                [*preview_command, "up", "-d", "--wait", "--wait-timeout", "120", "db"],
                env=preview_env,
            )
            run(
                [*preview_command, "run", "--rm", "-T", "backend", "alembic", "upgrade", "head"],
                env=preview_env,
            )
            run([*preview_command, "up", "-d", "--wait", "--wait-timeout", "180"], env=preview_env)
            stable_head = code_heads(migration_graph(stable))
            assert_equal(stable_head, [base_head], "stable archive excludes dirty migration")
            # Validate all canonical topologies without exposing interpolated secrets.
            Environment(repo, "prod").compose("config", "--quiet")
            run(
                [
                    "docker",
                    "compose",
                    "--env-file",
                    "/dev/null",
                    "-f",
                    str(repo.source / "compose.integration.yaml"),
                    "config",
                    "--quiet",
                ]
            )
            assert_equal(dev_snapshot(dev), before, "DEV untouched by review and stable preview")
            print(
                f"REAL COMPOSE SMOKE PASSED: dirty Review head workflow_smoke; stable head {base_head}; non-root frontend UID {uid}; fresh bootstrap, root-owned .bin repair, changed dependency/lockfile bootstrap, DB/media/dependency persistence and all topology checks passed"
            )
        finally:
            # These names were proved absent before this smoke created them.
            review.stop(remove=True, confirm=review.project)
            run([*preview_command, "down", "--volumes", "--remove-orphans"], env=preview_env)
            migration.unlink(missing_ok=True)
        assert_equal(dev_snapshot(dev), before, "cleanup leaves DEV unchanged")
        assert_equal(review.containers(), [], "review containers removed")
        assert_equal(
            run(
                [
                    "docker",
                    "volume",
                    "ls",
                    "-q",
                    "--filter",
                    f"label=com.docker.compose.project={review.project}",
                ],
                capture=True,
            ),
            "",
            "review volumes removed only by explicit remove",
        )


if __name__ == "__main__":
    main()
