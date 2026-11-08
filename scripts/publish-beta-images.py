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
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any

from beta_release import (
    INSTALL_BUNDLE,
    POSTGRES_REPOSITORY,
    POSTGRES_SBOM,
    REGISTRY_IMAGE,
    SOURCE,
    build_application_image,
    inputs,
    local_postgres_identity,
    locate_draft_release,
    manifest,
    prepare_release_assets,
    promote_image,
    read,
    release_asset_inventory,
    release_attestation_inputs,
    release_finalization_inputs,
    run,
    run_artifact_smoke,
    scan_images,
    software_bill_of_materials,
    validate_release_assets,
)
from workflow_resources import Disposable, Owner

REGISTRY = "ghcr.io"
WORKFLOW = ".github/workflows/beta-images.yml"
BUILDX_VERSION = "v0.38.1"
REPOSITORY = SOURCE.removeprefix("https://github.com/")
RegistryLookup = Callable[[str, str], str | None]
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
        "https://" + REGISTRY + "/token?" + query,
        headers={"Authorization": "Basic " + basic},
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
    return lookup_manifest("https://" + REGISTRY, repository, tag, token)


def lookup_manifest(origin: str, repository: str, tag: str, token: str = "") -> str | None:
    headers = {"Accept": ", ".join(MANIFEST_MEDIA_TYPES)}
    if token:
        headers["Authorization"] = "Bearer " + token
    reference = origin + "/v2/" + repository + "/manifests/" + tag
    request = urllib.request.Request(reference, headers=headers)
    open_manifest: Callable[..., Any] = urllib.request.urlopen
    if origin.startswith("http://127.0.0.1:"):
        open_manifest = urllib.request.build_opener(urllib.request.ProxyHandler({})).open
    try:
        with open_manifest(request, timeout=30) as response:
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


class Publication:
    """Record a failed or interrupted stage before doing work that can mutate the registry."""

    def __init__(self, output: Path, *, create: bool = True) -> None:
        self.path = output / "diagnostics/publication-state.json"
        if create:
            output.mkdir(parents=True, exist_ok=False, mode=0o700)
            self.path.parent.mkdir()
            self.state: dict[str, Any] = {"stages": {}, "promoted": {}}
        else:
            self.state = read(self.path)

    def save(self) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state, indent=2) + "\n")
        temporary.replace(self.path)

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        stage = {"status": "running"}
        self.state["stages"][name] = stage
        self.save()
        print(f"{name}: START", flush=True)
        try:
            yield
        except BaseException as error:
            stage.update(status="failed", error=str(error))
            self.save()
            print(f"{name}: FAIL ({error})", flush=True)
            raise
        else:
            stage["status"] = "passed"
            self.save()
            print(f"{name}: PASS", flush=True)


@contextmanager
def disposable_registry(root: Path) -> Iterator[tuple[str, int]]:
    """Start a uniquely owned registry, published only on this daemon's loopback."""
    owner = Owner.disposable("workflow-smoke", root)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = int(listener.getsockname()[1])
    host = f"127.0.0.1:{port}"
    with Disposable(owner):
        command = ["docker", "run", "-d", "--name", owner.project + "-registry"]
        for key, value in owner.labels().items():
            command.extend(["--label", key + "=" + value])
        subprocess.run(
            [*command, "-p", host + ":5000", REGISTRY_IMAGE],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 30
        # Never proxy the disposable registry through an operator's HTTP proxy.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        while True:
            try:
                with opener.open(f"http://{host}/v2/", timeout=2):
                    break
            except OSError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.25)
        yield host, port


@contextmanager
def pinned_builder(image: str, host: str) -> Iterator[str]:
    builder = "beta-" + uuid.uuid4().hex
    with tempfile.TemporaryDirectory(prefix="beta-builder-") as temporary:
        command = [
            "docker",
            "buildx",
            "create",
            "--name",
            builder,
            "--driver",
            "docker-container",
            "--driver-opt",
            "image=" + image,
        ]
        if host != REGISTRY:
            config = Path(temporary) / "buildkitd.toml"
            config.write_text(f'[registry."{host}"]\n  http = true\n  insecure = true\n')
            command.extend(["--driver-opt", "network=host", "--buildkitd-config", str(config)])
        try:
            subprocess.run(command, check=True)
            yield builder
        finally:
            subprocess.run(["docker", "buildx", "rm", builder], check=True)


def check_toolchain() -> None:
    if run("docker", "buildx", "version").split()[1:2] != [BUILDX_VERSION]:
        raise ValueError(f"release requires Docker Buildx {BUILDX_VERSION}")
    if run("docker", "version", "--format", "{{.Server.Os}}/{{.Server.Arch}}") != "linux/amd64":
        raise ValueError("release requires native linux/amd64 Docker")
    if (
        os.environ.get("DOCKER_HOST")
        or os.environ.get("DOCKER_CONTEXT", "default") != "default"
        or os.environ.get("BUILDX_BUILDER")
        or run("docker", "context", "show") != "default"
        or run(
            "docker",
            "context",
            "inspect",
            "default",
            "--format",
            "{{.Endpoints.docker.Host}}",
        )
        != "unix:///var/run/docker.sock"
    ):
        raise ValueError("release requires the default local Docker socket and no builder override")


def inspect_versions(lookup: RegistryLookup, version: str, pg: dict[str, Any]) -> bool:
    for service in ("backend", "frontend"):
        if lookup(f"{REPOSITORY}-{service}", version) is not None:
            raise ValueError(f"{service} versioned image already exists; refuse to resume")
    published = lookup(POSTGRES_REPOSITORY.removeprefix(REGISTRY + "/"), pg["version"])
    if published is not None and published != pg["index_digest"]:
        raise ValueError("published PostgreSQL tag differs from the pinned identity")
    return published is not None


def copy_smoke_artifact(root: Path, artifact: Path, manifest_path: Path) -> None:
    artifact.mkdir()
    for name in (
        "manifest.schema.json",
        "inputs.json",
        "requirements.txt",
        "bootstrap.json",
    ):
        shutil.copyfile(root / "release" / name, artifact / name)
    for name in (
        "release-tools.py",
        "smoke-beta-images.py",
        "beta_release.py",
        "disposable_workflow.py",
        "workflow_resources.py",
    ):
        shutil.copyfile(root / "scripts" / name, artifact / name)
    shutil.copyfile(manifest_path, artifact / manifest_path.name)


def release_create_command(request: dict[str, Any], assets: Path) -> list[str]:
    return [
        "gh",
        "release",
        "create",
        request["tag"],
        *[str(assets / name) for name in request["assets"]],
        "--verify-tag",
        "--target",
        request["target_commitish"],
        "--draft",
        "--prerelease",
        "--title",
        request["title"],
        "--notes-file",
        str(assets / "RELEASE.md"),
    ]


def run_pipeline(
    root: Path,
    output: Path,
    remote_lookup: RegistryLookup | None = None,
    remote_gate: Callable[[], None] | None = None,
) -> Publication:
    """Share the full pre-promotion path. Without protected callbacks, all writes are local."""
    publication = Publication(output)
    diagnostics = publication.path.parent
    assets = output / "assets"
    state = publication.state
    with ExitStack() as resources:
        with publication.stage("PREPARE"):
            locked = inputs(root, publication=True)
            sha = run("git", "rev-parse", "HEAD")
            if run("git", "status", "--porcelain"):
                raise ValueError("release preparation requires a clean source tree")
            version, pg = locked["version"], locked["postgresql"]
            state.update(
                source_sha=sha,
                version=version,
                mode="protected" if remote_lookup else "local",
            )
            if remote_lookup is not None:
                state.update(
                    run_id=os.environ["GITHUB_RUN_ID"],
                    run_attempt=os.environ["GITHUB_RUN_ATTEMPT"],
                )
            assets.mkdir()
            check_toolchain()
        with publication.stage("VALIDATE"):
            if remote_lookup is None:
                host, _ = resources.enter_context(disposable_registry(root))

                def local_lookup(repository: str, tag: str) -> str | None:
                    return lookup_manifest("http://" + host, repository, tag)

                lookup: RegistryLookup = local_lookup
            else:
                host = REGISTRY
                lookup = remote_lookup
            if remote_gate is not None:
                remote_gate()
            postgres_published = inspect_versions(lookup, version, pg)
            if remote_lookup is None and postgres_published:
                raise ValueError(
                    "disposable registry must exercise first-time PostgreSQL publication"
                )
            state.update(registry=host, postgres_preexisting=postgres_published)

        with publication.stage("CANDIDATES"):
            builder = resources.enter_context(pinned_builder(locked["buildkit"], host))
            pg_repository = host + "/" + pg["repository"].removeprefix(REGISTRY + "/")
            if not postgres_published:
                # Both modes build into a separate scratch registry, prove the pin, then copy
                # the exact index to a candidate tag in the destination registry.
                with disposable_registry(root) as (_, port):
                    local_postgres_identity(
                        root,
                        port=port,
                        destination=pg_repository + ":candidate-" + builder,
                        manage_registry=False,
                        evidence_dir=diagnostics / "postgres-reproducibility",
                    )
            pg_ref = pg_repository + "@" + pg["index_digest"]
            refs = {"postgresql": pg_ref}
            state["images"] = refs
            publication.save()
            app_refs: dict[str, str] = {}
            for service in ("backend", "frontend"):
                app_refs[service] = build_application_image(
                    root,
                    builder,
                    service,
                    f"{host}/{REPOSITORY}-{service}:candidate-{builder}",
                    version,
                    sha,
                    int(run("git", "show", "-s", "--format=%ct", "HEAD")),
                    locked["sbom_generator"],
                    diagnostics / (service + "-build.json"),
                )
                refs[service] = app_refs[service]
                publication.save()
            value = manifest(
                root,
                app_refs,
                local=False,
                registry_host=host,
                postgres_reference=pg_ref,
            )
            manifest_path = assets / "release-manifest.json"
            manifest_path.write_text(json.dumps(value, indent=2) + "\n")

        with publication.stage("SCAN/SMOKE"):
            for ref in refs.values():
                subprocess.run(["docker", "pull", "--platform", "linux/amd64", ref], check=True)
            scan_images(refs, diagnostics / "scans", locked["scanner"])
            software_bill_of_materials(pg_ref, assets / POSTGRES_SBOM, locked["scanner"])
            artifact = diagnostics / "smoke-artifact"
            copy_smoke_artifact(root, artifact, manifest_path)
            with (diagnostics / "image-smoke.log").open("w") as log:
                run_artifact_smoke(
                    artifact,
                    local=False,
                    log=log,
                    postgres_image=pg_ref,
                    registry_host=host,
                )

        with publication.stage("VALIDATE ASSETS"):
            inventory = prepare_release_assets(root, assets, version, sha)
            if read(manifest_path) != value:
                raise ValueError("release manifest changed after the artifact smoke")
            request = release_finalization_inputs(value, sha, inventory)
            attestation = release_attestation_inputs(
                value,
                refs,
                manifest_path,
                sha,
                WORKFLOW,
                {name: inventory[name][1] for name in INSTALL_BUNDLE},
                host,
            )
            if attestation["release_manifest_sha256"] != inventory[manifest_path.name][1]:
                raise ValueError("attestation manifest bytes differ from the release inventory")
            state.update(release=request, attestation=attestation)
            # Exercise the real draft asset verifier against the exact upload contract.
            validate_release_assets(
                {
                    "draft": True,
                    "assets": [
                        {"name": name, "size": size, "digest": digest}
                        for name, (size, digest) in inventory.items()
                    ],
                },
                assets,
                inventory,
            )
            release_create_command(request, assets)
            if remote_gate is not None:
                remote_gate()
            if inspect_versions(lookup, version, pg) != postgres_published:
                raise ValueError(
                    "PostgreSQL version state changed during preparation; refuse promotion"
                )

        with publication.stage("PROMOTE"):
            promotion = [(name, version) for name in ("backend", "frontend")]
            if not postgres_published:
                promotion.append(("postgresql", pg["version"]))
            for service, tag in promotion:
                repository = refs[service].split("@", 1)[0].split("/", 1)[1]
                if lookup(repository, tag) is not None:
                    raise ValueError(
                        f"{service} version tag appeared before promotion; refuse to resume"
                    )
                state["promotion_in_progress"] = service
                publication.save()
                state["promoted"][service] = promote_image(refs[service], tag, host)
                del state["promotion_in_progress"]
                publication.save()
            if lookup(pg_repository.split("/", 1)[1], pg["version"]) != pg["index_digest"]:
                raise ValueError("promoted PostgreSQL tag does not match the pinned index")
    return publication


def protected_state(output: Path) -> Publication:
    sha = run("git", "rev-parse", "HEAD")
    require_publication_identity(sha)
    publication = Publication(output, create=False)
    state = publication.state
    if (
        state["mode"] != "protected"
        or state["source_sha"] != sha
        or state["run_id"] != os.environ["GITHUB_RUN_ID"]
        or state["run_attempt"] != os.environ["GITHUB_RUN_ATTEMPT"]
        or state["stages"].get("PROMOTE", {}).get("status") != "passed"
        or "RELEASE" in state["stages"]
    ):
        raise ValueError("refuse to finalize without a fresh successful protected promotion")
    return publication


def record_attestation(output: Path, outcome: str) -> None:
    publication = protected_state(output)
    if "ATTEST" in publication.state["stages"]:
        raise ValueError("refuse to record attestation twice")
    with publication.stage("ATTEST"):
        if outcome != "passed":
            raise ValueError("one or more protected attestation steps failed")


def finalize_release(output: Path) -> None:
    publication = protected_state(output)
    assets = output / "assets"
    state = publication.state
    sha = state["source_sha"]
    if state["stages"].get("ATTEST", {}).get("status") != "passed":
        raise ValueError("refuse to finalize without successful protected attestation")
    with publication.stage("RELEASE"):
        manifest_value = read(assets / "release-manifest.json")
        inventory = release_asset_inventory(assets)
        request = release_finalization_inputs(manifest_value, sha, inventory)
        if request != state["release"]:
            raise ValueError("release inventory changed after promotion")
        subprocess.run(release_create_command(request, assets), check=True)
        draft = locate_draft_release(REPOSITORY, request["tag"], sha)
        validate_release_assets(draft, assets, inventory)
        subprocess.run(
            [
                "gh",
                "api",
                "--method",
                "PATCH",
                f"repos/{REPOSITORY}/releases/{draft['id']}",
                "-F",
                "draft=false",
                "-F",
                "prerelease=true",
            ],
            check=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--finalize", action="store_true")
    action.add_argument("--attestation-outcome", choices=("passed", "failed"))
    args = parser.parse_args()
    root = Path.cwd()
    output = args.output.resolve()
    if output.is_relative_to(root):
        raise ValueError("release output must be outside the source checkout")
    if args.finalize:
        finalize_release(output)
        return
    if args.attestation_outcome:
        record_attestation(output, args.attestation_outcome)
        return
    sha = run("git", "rev-parse", "HEAD")
    require_publication_identity(sha)
    actor, secret = os.environ["GITHUB_ACTOR"], os.environ["REGISTRY_TOKEN"]

    def lookup(repository: str, tag: str) -> str | None:
        return published_digest(repository, tag, actor, secret)

    def gate() -> None:
        subprocess.run(["python3", "scripts/beta-release-checks.py", "--identity-only"], check=True)

    subprocess.run(
        ["docker", "login", REGISTRY, "--username", actor, "--password-stdin"],
        input=secret,
        text=True,
        check=True,
    )
    try:
        publication = run_pipeline(root, output, lookup, gate)
        with Path(os.environ["GITHUB_OUTPUT"]).open("a") as outputs:
            for service, subject in publication.state["attestation"]["subjects"].items():
                outputs.write(
                    f"{service}_name={subject['name']}\n{service}_digest={subject['digest']}\n"
                )
    finally:
        subprocess.run(["docker", "logout", REGISTRY], check=True)


if __name__ == "__main__":
    main()
