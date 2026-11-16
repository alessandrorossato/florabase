#!/usr/bin/env python3
"""Exercise report and confirmed cleanup on uniquely owned Docker fixtures only."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from workflow_resources import Owner

ROOT = Path(__file__).resolve().parent.parent


def run(*args: str, env: dict[str, str] | None = None) -> str:
    return subprocess.run(args, check=True, text=True, capture_output=True, env=env).stdout.strip()


def labels(values: dict[str, str]) -> list[str]:
    return [part for key, value in values.items() for part in ("--label", f"{key}={value}")]


def snapshot(project: str) -> dict[str, list[tuple[str, dict[str, str], bool | None]]]:
    result: dict[str, list[tuple[str, dict[str, str], bool | None]]] = {}
    for kind, command, inspection in (
        ("containers", ("ps", "-aq", "--no-trunc"), ("inspect",)),
        ("volumes", ("volume", "ls", "-q"), ("volume", "inspect")),
    ):
        ids = run(
            "docker", *command, "--filter", f"label=com.docker.compose.project={project}"
        ).splitlines()
        objects = [json.loads(run("docker", *inspection, item))[0] for item in ids]
        result[kind] = sorted(
            (
                str(item.get("Id") or item.get("Name")),
                (item.get("Config", {}) if kind == "containers" else item).get("Labels") or {},
                item.get("State", {}).get("Running") if kind == "containers" else None,
            )
            for item in objects
        )
    return result


def main() -> None:
    suffix = uuid.uuid4().hex[:12]
    projects = ["florabase", "florabase-uat-preview", "florabase-preview", "florabase-prod"]
    before = {project: snapshot(project) for project in projects}
    created_containers: list[str] = []
    created_volumes: list[str] = []
    with tempfile.TemporaryDirectory(prefix="florabase-wf06-") as temporary:
        root = Path(temporary)
        env = dict(os.environ, FLORABASE_LOCK_DIR=str(root / "locks"), AGENT_ID="operator")
        source = root / "missing-source"
        metadata = root / "missing-metadata"
        disposable = Owner.disposable("integration", source)
        quality = Owner.quality(source, metadata)
        uat = f"florabase-uat-branch-wf06{suffix}"

        def volume(name: str, values: dict[str, str]) -> None:
            if run("docker", "volume", "ls", "-q", "--filter", f"name=^{name}$"):
                raise RuntimeError("fixture collision")
            run("docker", "volume", "create", *labels(values), name)
            created_volumes.append(name)

        def container(values: dict[str, str], mount: str = "") -> None:
            command = [
                "docker",
                "run",
                "-d",
                "--pull=never",
                "--network",
                "none",
                "--tmpfs",
                "/var/lib/postgresql",
                *labels(values),
            ]
            if mount:
                command += ["--mount", f"type=volume,src={mount},dst=/fixture"]
            command += ["--entrypoint", "/bin/sh", "postgres:18.6-alpine", "-c", "sleep 300"]
            created_containers.append(run(*command))

        try:
            for owner in (disposable, quality):
                volume(owner.project + "_data", owner.labels())
                container(owner.labels(), owner.project + "_data")
            uat_labels = {
                "com.docker.compose.project": uat,
                "io.florabase.source": str(source),
                "io.florabase.uat.instance": "wf06" + suffix,
                "io.florabase.uat.port": "15180",
                "io.florabase.uat.profile": "smoke",
            }
            for key in ("postgres_data", "attachment_data", "frontend_node_modules"):
                volume(uat + "_" + key, {**uat_labels, "com.docker.compose.volume": key})
            container(
                {
                    "com.docker.compose.project": uat,
                    "io.florabase.source": str(source),
                    "io.florabase.role": "uat-instance",
                    "io.florabase.sha": "a" * 40,
                    "com.docker.compose.project.working_dir": str(source),
                    "com.docker.compose.service": "backend",
                },
                uat + "_postgres_data",
            )
            for index, project in enumerate((*projects, "florabase")):
                fixture = f"wf06-protected-{suffix}-{index}"
                protected_labels = {
                    "com.docker.compose.project": project,
                    "io.florabase.smoke.fixture": fixture,
                }
                volume(fixture, protected_labels)
                container(protected_labels, fixture)
            (root / "locks").mkdir()
            (root / "locks" / f"{disposable.project}.ended.json").write_text(
                json.dumps(disposable.labels())
            )
            expected = {
                disposable.project: "remove-disposable",
                quality.project: "remove-quality",
                uat: "stop-uat",
            }
            before_fixtures = {project: snapshot(project) for project in (*expected, *projects)}
            report = json.loads(
                run(sys.executable, str(ROOT / "scripts/workflow_cleanup.py"), env=env)
            )
            by_project = {item["project"]: item for item in report}
            assert {project: by_project[project]["action"] for project in expected} == expected
            assert {
                project: snapshot(project) for project in (*expected, *projects)
            } == before_fixtures
            wrong = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/workflow_cleanup.py"),
                    "--project",
                    disposable.project,
                    "--confirm",
                    "wrong",
                ],
                env=env,
                capture_output=True,
                check=False,
            )
            assert wrong.returncode != 0
            assert {
                project: snapshot(project) for project in (*expected, *projects)
            } == before_fixtures
            for project in expected:
                run(
                    sys.executable,
                    str(ROOT / "scripts/workflow_cleanup.py"),
                    "--project",
                    project,
                    "--confirm",
                    by_project[project]["token"],
                    env=env,
                )
            assert (
                not snapshot(disposable.project)["containers"]
                and not snapshot(disposable.project)["volumes"]
            )
            assert (
                not snapshot(quality.project)["containers"]
                and not snapshot(quality.project)["volumes"]
            )
            assert snapshot(uat)["volumes"] == before_fixtures[uat]["volumes"]
            assert [
                (identifier, item_labels)
                for identifier, item_labels, _ in snapshot(uat)["containers"]
            ] == [
                (identifier, item_labels)
                for identifier, item_labels, _ in before_fixtures[uat]["containers"]
            ]
            assert not json.loads(run("docker", "inspect", created_containers[2]))[0]["State"][
                "Running"
            ]
            assert {project: snapshot(project) for project in projects} == {
                project: before_fixtures[project] for project in projects
            }
            print("WF06_SYNTHETIC_SMOKE_PASSED")
        finally:
            remaining = set(run("docker", "ps", "-aq", "--no-trunc").splitlines())
            for identifier in created_containers:
                if identifier in remaining:
                    run("docker", "rm", "-f", identifier)
            remaining_volumes = set(run("docker", "volume", "ls", "-q").splitlines())
            for name in created_volumes:
                if name in remaining_volumes:
                    run("docker", "volume", "rm", name)
            assert not (
                set(created_containers) & set(run("docker", "ps", "-aq", "--no-trunc").splitlines())
            )
            assert not (
                set(created_volumes) & set(run("docker", "volume", "ls", "-q").splitlines())
            )
            assert {project: snapshot(project) for project in projects} == before


if __name__ == "__main__":
    main()
