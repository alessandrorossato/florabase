#!/usr/bin/env python3
"""Protected CI publication only. Candidates are scanned and pulled before version promotion."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from beta_release import (
    POSTGRES_REPOSITORY,
    SOURCE,
    build_application_image,
    inputs,
    local_postgres_identity,
    manifest,
    prepare_release_assets,
    promote_image,
    registry_record,
    run,
    run_artifact_smoke,
    scan_images,
    software_bill_of_materials,
)

REGISTRY = "ghcr.io"
MANIFEST_MEDIA_TYPES = (
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
)
ABSENT_CODES = {"MANIFEST_UNKNOWN", "NAME_UNKNOWN"}


def registry_token(repository: str, actor: str, secret: str, actions: str = "pull,push") -> str:
    """Exchange the workflow credential for a registry token scoped to this repository.

    The pull,push scope is the one a push itself requests, so a package that does not exist yet
    is still authorized; the token is only used for read requests here.
    """
    query = urllib.parse.urlencode(
        {"service": REGISTRY, "scope": "repository:" + repository + ":" + actions}
    )
    basic = base64.b64encode((actor + ":" + secret).encode()).decode()
    request = urllib.request.Request(
        "https://" + REGISTRY + "/token?" + query, headers={"Authorization": "Basic " + basic}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            token = json.loads(response.read()).get("token")
    except urllib.error.HTTPError as error:
        error.close()
        raise ValueError(
            f"registry refused credentials for {repository} (HTTP {error.code})"
        ) from error
    except (OSError, ValueError, AttributeError) as error:
        raise ValueError(
            f"registry token request for {repository} failed: {type(error).__name__}"
        ) from error
    if not isinstance(token, str) or not token:
        raise ValueError(f"registry token response for {repository} is malformed")
    return token


def published_digest(
    repository: str,
    tag: str,
    actor: str,
    secret: str,
    actions: str = "pull,push",
) -> str | None:
    """Return the published index/manifest digest, or None only for a definite absence.

    Every other outcome (authorization, availability, network, malformed or inconsistent
    responses) raises, so an ambiguous lookup can never be mistaken for an unpublished tag.
    """
    if not re.fullmatch(r"[a-z0-9_./-]+", repository) or not re.fullmatch(r"[\w.-]+", tag):
        raise ValueError("invalid registry reference")
    token = registry_token(repository, actor, secret, actions)
    request = urllib.request.Request(
        "https://" + REGISTRY + "/v2/" + repository + "/manifests/" + tag,
        headers={"Authorization": "Bearer " + token, "Accept": ", ".join(MANIFEST_MEDIA_TYPES)},
    )
    reference = REGISTRY + "/" + repository + ":" + tag
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
            header = response.headers.get("Docker-Content-Digest", "")
            media_type = response.headers.get("Content-Type", "").split(";")[0].strip()
    except urllib.error.HTTPError as error:
        with error:
            try:
                document = json.loads(error.read())
            except ValueError:
                document = None
        errors = document.get("errors") if isinstance(document, dict) else None
        codes = (
            {item.get("code") for item in errors if isinstance(item, dict)}
            if isinstance(errors, list)
            else set()
        )
        if error.code == 404 and codes and codes <= ABSENT_CODES:
            return None
        raise ValueError(
            f"cannot determine whether {reference} exists (HTTP {error.code})"
        ) from error
    except (OSError, ValueError) as error:
        raise ValueError(
            f"cannot determine whether {reference} exists: {type(error).__name__}"
        ) from error
    digest = "sha256:" + hashlib.sha256(body).hexdigest()
    try:
        document = json.loads(body)
    except ValueError:
        document = None
    if (
        media_type not in MANIFEST_MEDIA_TYPES
        or not isinstance(document, dict)
        or document.get("schemaVersion") != 2
        or header != digest
    ):
        raise ValueError(f"registry returned a malformed manifest for {reference}")
    return digest


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
    builder_requested = False
    try:
        # Registry lookups distinguish a definite absence from every failure: authorization,
        # network, availability and malformed responses all refuse publication.
        actor, secret = os.environ["GITHUB_ACTOR"], os.environ["REGISTRY_TOKEN"]
        for service in ("backend", "frontend"):
            if published_digest(repository + "-" + service, version, actor, secret) is not None:
                raise ValueError("versioned image already exists; choose a new release")
        pg = locked["postgresql"]
        # Shared by every release: an existing tag must already be the pinned identity.
        published = published_digest(
            POSTGRES_REPOSITORY.removeprefix(REGISTRY + "/"), pg["version"], actor, secret
        )
        if published is not None and published != pg["index_digest"]:
            raise ValueError("published PostgreSQL tag differs from the pinned identity")
        postgres_published = published is not None
        builder_requested = True
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
                evidence_dir=output / "postgres-reproducibility",
            )
        # Every release re-verifies the published bytes (identity, gate, SBOM, smoke, attestation)
        # without rebuilding, so a superseded Alpine pin never blocks application releases.
        state["images"]["postgresql"] = POSTGRES_REPOSITORY + "@" + pg["index_digest"]
        checkpoint("postgresql_candidate_verified")
        for service in ("backend", "frontend"):
            image = "ghcr.io/" + repository + "-" + service
            candidate = image + ":candidate-" + builder
            metadata = output / (service + "-build.json")
            refs[service] = build_application_image(
                Path.cwd(),
                builder,
                service,
                candidate,
                version,
                sha,
                int(run("git", "show", "-s", "--format=%ct", "HEAD")),
                locked["sbom_generator"],
                metadata,
            )
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
        # The install bundle, source archive and release notes share one implementation with the
        # non-publishing rehearsal; the manifest binds all three bundle hashes.
        prepare_release_assets(Path.cwd(), output, version, sha)
        for service, ref in refs.items():
            if promote_image(ref, version) != registry_record(ref, "linux/amd64")["index_digest"]:
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
        if builder_requested:
            subprocess.run(["docker", "buildx", "rm", builder], check=False)
        subprocess.run(["docker", "logout", "ghcr.io"], check=False)


if __name__ == "__main__":
    main()
