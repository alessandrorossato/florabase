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
from typing import Any

from beta_release import (
    INSTALL_BUNDLE,
    POSTGRES_REPOSITORY,
    SOURCE,
    inputs,
    local_postgres_identity,
    manifest,
    registry_record,
    release_asset_inventory,
    run,
    run_artifact_smoke,
    scan_images,
    software_bill_of_materials,
)


def require_publication_identity(sha: str) -> None:
    if (
        os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("GITHUB_REF") != "refs/heads/main"
        or sha != os.environ.get("GITHUB_SHA")
        or os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
        or os.environ.get("GITHUB_REPOSITORY") != SOURCE.removeprefix("https://github.com/")
        or os.environ.get("GITHUB_WORKFLOW_REF")
        != SOURCE.removeprefix("https://github.com/")
        + "/.github/workflows/beta-images.yml@refs/heads/main"
        or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
        or os.environ.get("APPROVED_SHA") != sha
        or run("git", "status", "--porcelain")
    ):
        raise ValueError("publication only runs in protected manual CI at the workflow commit")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    locked = inputs(Path.cwd(), publication=True)
    sha = run("git", "rev-parse", "HEAD")
    require_publication_identity(sha)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    repository = os.environ["GITHUB_REPOSITORY"].lower()
    subprocess.run(["python3", "scripts/beta-release-checks.py"], check=True)
    state: dict[str, Any] = {
        "source_sha": sha,
        "version": locked["version"],
        "run_id": os.environ["GITHUB_RUN_ID"],
        "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
        "phase": "preflight",
        "images": {},
    }

    def checkpoint(phase: str) -> None:
        state["phase"] = phase
        (output / "publication-state.json").write_text(json.dumps(state, indent=2) + "\n")

    checkpoint("preflight")
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
        pg = locked["postgresql"]
        postgres_published = False
        if POSTGRES_REPOSITORY.removeprefix("ghcr.io/" + owner + "/") in existing:
            # Shared by every release: an existing tag must already be the pinned identity, and
            # only a definite "not found" may count as absent (auth/network errors fail closed).
            tagged = subprocess.run(
                [
                    "docker",
                    "buildx",
                    "imagetools",
                    "inspect",
                    POSTGRES_REPOSITORY + ":" + pg["version"],
                    "--format",
                    "{{json .Manifest}}",
                ],
                text=True,
                capture_output=True,
            )
            if tagged.returncode == 0:
                if json.loads(tagged.stdout)["digest"] != pg["index_digest"]:
                    raise ValueError("published PostgreSQL tag differs from the pinned identity")
                postgres_published = True
            elif not re.search(r"not found|manifest unknown", tagged.stderr, re.IGNORECASE):
                raise ValueError("cannot determine the published PostgreSQL tag; refusing")
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
        if not postgres_published:
            # First publication of this identity: build in a disposable loopback registry,
            # refuse unless it reproduces the pins, and only then copy the exact bytes to GHCR.
            local_postgres_identity(
                Path.cwd(),
                destination=POSTGRES_REPOSITORY + ":candidate-" + builder + "-postgres",
            )
        # Every release re-verifies the published bytes (identity, gate, SBOM, smoke, attestation)
        # without rebuilding, so a superseded Alpine pin never blocks application releases.
        state["images"]["postgresql"] = POSTGRES_REPOSITORY + "@" + pg["index_digest"]
        checkpoint("postgresql_candidate_verified")
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
            state["images"][service] = refs[service]
            checkpoint(service + "_candidate_pushed")
        value = manifest(Path.cwd(), refs, local=False)
        manifest_path = output / "release-manifest.json"
        manifest_path.write_text(json.dumps(value, indent=2) + "\n")
        # Scan the exact pushed bytes, including secrets, before promoting version tags.
        scan_refs = {**refs, "postgresql": POSTGRES_REPOSITORY + "@" + pg["index_digest"]}
        for ref in scan_refs.values():
            subprocess.run(["docker", "pull", "--platform", "linux/amd64", ref], check=True)
        scan_images(scan_refs, output, locked["scanner"])
        # The derived image has no in-index SBOM attestation (it would break reproducibility).
        software_bill_of_materials(
            scan_refs["postgresql"], output / "postgresql-sbom.cdx.json", locked["scanner"]
        )
        checkpoint("security_passed")
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
        checkpoint("smoke_passed")
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
        # The install bundle: an operator needs only these three assets and the manifest, never a
        # checkout. The attested manifest records their SHA-256 (install_bundle), each file is
        # also attested, and the controller refuses a bundle that differs from the manifest.
        for name in INSTALL_BUNDLE:
            shutil.copyfile(Path("deploy/beta") / name, output / name)
        (output / "RELEASE.md").write_text(
            f"Florabase {version}\n\nSource: {SOURCE}/commit/{sha}\n\nUse release-manifest.json digest references; the pair and PostgreSQL passed native amd64 registry-pull smoke and the pinned Trivy gate (HIGH/CRITICAL vulnerabilities and secrets); that gate is a single scanner, and findings it does not report are recorded in docs/security/beta-distribution-001/postgresql-image.md at this source revision. PostgreSQL is the Florabase-built {pg['version']} image ({pg['reference']}): the official {pg['upstream']['reference']} without its gosu executable, which stays in an unchanged upstream layer but is absent from the container filesystem; it is identical in every release. Install with the attached {', '.join(INSTALL_BUNDLE)} and release-manifest.json as described in docs/installation.md at this source revision. This is a prerelease: no stable or latest tag is published. Never overwrite this release or delete its image identities.\n"
        )
        release_asset_inventory(output)
        for service, ref in refs.items():
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
            checkpoint(service + "_version_promoted")
        if not postgres_published:
            subprocess.run(
                [
                    "docker",
                    "buildx",
                    "imagetools",
                    "create",
                    "--prefer-index=false",
                    "--tag",
                    POSTGRES_REPOSITORY + ":" + pg["version"],
                    scan_refs["postgresql"],
                ],
                check=True,
            )
        promoted = json.loads(
            run(
                "docker",
                "buildx",
                "imagetools",
                "inspect",
                POSTGRES_REPOSITORY + ":" + pg["version"],
                "--format",
                "{{json .Manifest}}",
            )
        )
        if promoted["digest"] != pg["index_digest"]:
            raise ValueError("promotion changed the PostgreSQL identity")
        checkpoint("postgresql_version_promoted")
        checkpoint("pair_promoted_requires_attestation_and_release")
        with Path(os.environ["GITHUB_OUTPUT"]).open("a") as outputs:
            for service, ref in {**refs, "postgresql": scan_refs["postgresql"]}.items():
                name, digest = ref.split("@")
                outputs.write(f"{service}_name={name}\n{service}_digest={digest}\n")
    finally:
        subprocess.run(["docker", "buildx", "rm", builder], check=False)
        subprocess.run(["docker", "logout", "ghcr.io"], check=False)


if __name__ == "__main__":
    main()
