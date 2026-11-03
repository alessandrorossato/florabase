#!/usr/bin/env python3
"""Protected CI publication only. Candidates are scanned and pulled before version promotion."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from beta_release import (
    SOURCE,
    inputs,
    manifest,
    registry_record,
    run,
    run_artifact_smoke,
    scan_images,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    locked = inputs(Path.cwd(), publication=True)
    sha = run("git", "rev-parse", "HEAD")
    if (
        os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("GITHUB_REF") != "refs/heads/main"
        or sha != os.environ.get("GITHUB_SHA")
        or os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
    ):
        raise ValueError("publication only runs in protected manual CI at the workflow commit")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    repository = os.environ["GITHUB_REPOSITORY"].lower()
    if not re.fullmatch(r"[a-z0-9_.-]+/[a-z0-9_.-]+", repository):
        raise ValueError("invalid repository")
    refs = {}
    version = locked["version"]
    builder = "beta-" + os.environ["GITHUB_RUN_ID"] + "-" + os.environ["GITHUB_RUN_ATTEMPT"]
    subprocess.run(
        [
            "docker",
            "login",
            "ghcr.io",
            "--username",
            os.environ["GITHUB_ACTOR"],
            "--password-stdin",
        ],
        input=os.environ["REGISTRY_TOKEN"],
        text=True,
        check=True,
    )
    try:
        # Enumerate successfully: auth/network errors must never be treated as an absent version.
        owner = repository.split("/")[0]
        packages = json.loads(
            run(
                "gh",
                "api",
                "--paginate",
                "--slurp",
                f"/users/{owner}/packages?package_type=container&per_page=100",
            )
        )
        existing = {p["name"] for page in packages for p in page}
        for service in ("backend", "frontend"):
            package = repository.split("/")[1] + "-" + service
            if package in existing:
                tags = json.loads(
                    run(
                        "gh",
                        "api",
                        "--paginate",
                        "--slurp",
                        f"/users/{owner}/packages/container/{package}/versions?per_page=100",
                    )
                )
                if any(
                    version in item["metadata"]["container"]["tags"]
                    for page in tags
                    for item in page
                ):
                    raise ValueError("versioned image already exists; choose a new release")
        subprocess.run(
            [
                "docker",
                "buildx",
                "create",
                "--name",
                builder,
                "--driver",
                "docker-container",
                "--driver-opt",
                "image=" + locked["buildkit"],
                "--use",
            ],
            check=True,
        )
        for service in ("backend", "frontend"):
            image = "ghcr.io/" + repository + "-" + service
            candidate = image + ":candidate-" + builder
            metadata = output / (service + "-build.json")
            subprocess.run(
                [
                    "docker",
                    "buildx",
                    "build",
                    "--builder",
                    builder,
                    "--platform",
                    "linux/amd64",
                    "--target",
                    "runtime",
                    "--push",
                    "--provenance=mode=max",
                    "--attest=type=sbom,generator=" + locked["sbom_generator"],
                    "--metadata-file",
                    str(metadata),
                    "--tag",
                    candidate,
                    "--build-arg",
                    "VERSION=" + version,
                    "--build-arg",
                    "REVISION=" + sha,
                    "--build-arg",
                    "SOURCE=" + SOURCE,
                    "--build-arg",
                    "SOURCE_DATE_EPOCH=" + run("git", "show", "-s", "--format=%ct", "HEAD"),
                    service,
                ],
                check=True,
            )
            digest = json.loads(metadata.read_text())["containerimage.digest"]
            refs[service] = image + "@" + digest
        value = manifest(Path.cwd(), refs, local=False)
        manifest_path = output / "release-manifest.json"
        manifest_path.write_text(json.dumps(value, indent=2) + "\n")
        # Scan the exact pushed bytes, including secrets, before promoting version tags.
        scan_refs = {**refs, "postgresql": locked["postgresql"]["reference"]}
        for ref in scan_refs.values():
            subprocess.run(["docker", "pull", "--platform", "linux/amd64", ref], check=True)
        scan_images(scan_refs, output, locked["scanner"])
        # Tools travel with the artifact; runtime execution has no local checkout or source bind.
        with tempfile.TemporaryDirectory(prefix="beta-artifact-only-") as temporary:
            artifact = Path(temporary)
            shutil.copyfile(Path("release/manifest.schema.json"), artifact / "manifest.schema.json")
            shutil.copyfile(Path("release/manifest.schema.json"), output / "manifest.schema.json")
            shutil.copyfile(Path("release/requirements.txt"), output / "requirements.txt")
            shutil.copyfile(Path("release/bootstrap.json"), output / "bootstrap.json")
            shutil.copyfile(Path("scripts/release-tools.py"), output / "release-tools.py")
            shutil.copyfile(Path("release/inputs.json"), artifact / "inputs.json")
            shutil.copyfile(Path("release/inputs.json"), output / "inputs.json")
            for name in (
                "smoke-beta-images.py",
                "beta_release.py",
                "disposable_workflow.py",
                "workflow_resources.py",
            ):
                shutil.copyfile(Path("scripts") / name, artifact / name)
                shutil.copyfile(Path("scripts") / name, output / name)
            shutil.copyfile(manifest_path, artifact / manifest_path.name)
            with (output / "image-smoke.log").open("w") as log:
                run_artifact_smoke(artifact, local=False, log=log)
        subprocess.run(
            [
                "git",
                "archive",
                "--format=tar.gz",
                "--prefix=florabase-" + version + "/",
                "--output",
                str(output / ("florabase-" + version + "-source.tar.gz")),
                sha,
            ],
            check=True,
        )
        for ref in refs.values():
            subprocess.run(
                [
                    "docker",
                    "buildx",
                    "imagetools",
                    "create",
                    "--prefer-index=false",
                    "--tag",
                    ref.split("@")[0] + ":" + version,
                    ref,
                ],
                check=True,
            )

            promoted = json.loads(
                run(
                    "docker",
                    "buildx",
                    "imagetools",
                    "inspect",
                    ref.split("@")[0] + ":" + version,
                    "--format",
                    "{{json .Manifest}}",
                )
            )
            if promoted["digest"] != registry_record(ref, "linux/amd64")["index_digest"]:
                raise ValueError("promotion changed immutable image identity")
        (output / "RELEASE.md").write_text(
            f"Florabase {version}\n\nSource: {SOURCE}/commit/{sha}\n\nUse release-manifest.json digest references; the pair passed native amd64 registry-pull smoke and HIGH/CRITICAL vulnerability and secret checks. PostgreSQL is separately pinned. This is image distribution, not real-host deployment or beta admission. Never overwrite this release or delete its image identities.\n"
        )
    finally:
        subprocess.run(["docker", "buildx", "rm", builder], check=False)
        subprocess.run(["docker", "logout", "ghcr.io"], check=False)


if __name__ == "__main__":
    main()
