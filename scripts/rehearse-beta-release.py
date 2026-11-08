#!/usr/bin/env python3
"""Exercise protected beta image stages against an owned local OCI registry only."""

from __future__ import annotations

import argparse
import atexit
import base64
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from beta_release import (
    REGISTRY_IMAGE,
    build_application_image,
    inputs,
    local_postgres_identity,
    manifest,
    prepare_release_assets,
    promote_image,
    release_attestation_inputs,
    release_finalization_inputs,
    require_pinned_postgres,
    run,
    run_artifact_smoke,
    scan_images,
    software_bill_of_materials,
)
from workflow_resources import Disposable, Owner

_publisher_spec = importlib.util.spec_from_file_location(
    "publisher", Path(__file__).with_name("publish-beta-images.py")
)
if _publisher_spec is None or _publisher_spec.loader is None:
    raise RuntimeError("could not load protected publisher preflight")
_publisher = importlib.util.module_from_spec(_publisher_spec)
_publisher_spec.loader.exec_module(_publisher)
published_digest = _publisher.published_digest
PREVIOUS_BUILDKit = (
    "moby/buildkit:buildx-stable-1@sha256:"
    "cec9f139f45e93c5c69c60f8b07cfad9f43f4ef6b6a6cd917527fea5ff2e3dea"
)


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def verify_ghcr_read_only(locked: dict[str, Any]) -> dict[str, Any]:
    token = os.environ.get("GITHUB_TOKEN")
    actor = os.environ.get("GITHUB_ACTOR")
    if not token or not actor:
        return {"status": "not_run", "reason": "GitHub Actions read-only token unavailable"}
    version = locked["version"]
    observations: dict[str, Any] = {"status": "passed", "scope": "pull only", "tags": {}}
    for name in ("backend", "frontend"):
        digest = published_digest(
            "alessandrorossato/florabase-" + name,
            version,
            actor,
            token,
            actions="pull",
        )
        if digest is not None:
            raise ValueError("versioned GHCR image already exists; rehearsal refuses reuse")
        observations["tags"][name] = {"version": version, "status": "absent"}
    pg = locked["postgresql"]
    digest = published_digest(
        "alessandrorossato/florabase-postgres",
        pg["version"],
        actor,
        token,
        actions="pull",
    )
    if digest is not None and digest != pg["index_digest"]:
        raise ValueError("GHCR PostgreSQL version tag differs from the pinned identity")
    observations["tags"]["postgresql"] = {
        "version": pg["version"],
        "status": "absent" if digest is None else "present_and_matches_pin",
        "digest": digest,
    }
    return observations


def copy_smoke_artifact(root: Path, output: Path, value: dict[str, Any]) -> Path:
    artifact = Path(tempfile.mkdtemp(prefix="beta-rehearsal-artifact-"))
    for name in ("manifest.schema.json",):
        shutil.copyfile(root / "release" / name, artifact / name)
    shutil.copyfile(root / "release/inputs.json", artifact / "inputs.json")
    shutil.copyfile(root / "release/requirements.txt", output / "requirements.txt")
    shutil.copyfile(root / "release/bootstrap.json", output / "bootstrap.json")
    shutil.copyfile(root / "scripts/release-tools.py", output / "release-tools.py")
    for name in (
        "smoke-beta-images.py",
        "beta_release.py",
        "disposable_workflow.py",
        "workflow_resources.py",
    ):
        shutil.copyfile(root / "scripts" / name, artifact / name)
        shutil.copyfile(root / "scripts" / name, output / name)
    (artifact / "release-manifest.json").write_text(json.dumps(value, indent=2) + "\n")
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path.cwd()
    locked = inputs(root, publication=True)
    sha = run("git", "rev-parse", "HEAD")
    if run("git", "status", "--porcelain"):
        raise ValueError("release rehearsal requires a clean source tree")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report: dict[str, Any] = {
        "mode": "non-publishing",
        "source_sha": sha,
        "version": locked["version"],
        "github_hosted": os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted",
        "stages": {},
        "remote_boundaries": {
            "actual_ghcr_writes": "not run; the job token has packages:read only",
            "github_attestations": "inputs checked; no attestation action invoked",
            "release_api_finalization": "inputs checked; no Release API mutation invoked",
        },
    }
    report_path = output / "rehearsal-report.json"

    def retain_report() -> None:
        report.setdefault("outcome", "failed")
        report_path.write_text(json.dumps(report, indent=2) + "\n")

    atexit.register(retain_report)
    report["stages"]["ghcr_read_only_auth_and_absence"] = verify_ghcr_read_only(locked)
    if (
        report["github_hosted"]
        and report["stages"]["ghcr_read_only_auth_and_absence"]["status"] != "passed"
    ):
        raise ValueError("GitHub-hosted rehearsal requires successful read-only GHCR preflight")
    registry_port = free_port()
    registry_host = f"127.0.0.1:{registry_port}"
    run_key = (
        os.environ.get("GITHUB_RUN_ID", "local") + "-" + os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    )
    candidate = "rehearsal-" + sha[:12] + "-" + run_key
    owner = Owner.disposable("workflow-smoke", root)
    registry_name = owner.project + "-registry"
    builder = "beta-rehearsal-" + uuid.uuid4().hex[:12]
    builder_created = False
    with Disposable(owner):
        command = ["docker", "run", "-d", "--name", registry_name]
        for key, label_value in owner.labels().items():
            command.extend(["--label", key + "=" + label_value])
        subprocess.run(
            [*command, "-p", f"127.0.0.1:{registry_port}:5000", REGISTRY_IMAGE],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 30
        while True:
            try:
                with urllib.request.urlopen(f"http://{registry_host}/v2/", timeout=2):
                    break
            except OSError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.25)
        with tempfile.TemporaryDirectory(prefix="beta-rehearsal-builder-") as temporary:
            config = Path(temporary) / "buildkitd.toml"
            config.write_text(f'[registry."{registry_host}"]\n  http = true\n  insecure = true\n')
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
                    "--driver-opt",
                    "network=host",
                    "--buildkitd-config",
                    str(config),
                    "--use",
                ],
                check=True,
            )
            builder_created = True
            try:
                inspect = run("docker", "buildx", "inspect", "--bootstrap", "--builder", builder)
                report["tooling"] = {
                    "docker": run("docker", "version", "--format", "{{.Server.Version}}"),
                    "buildx": run("docker", "buildx", "version"),
                    "builder": inspect,
                    "dockerfile_frontend": locked["dockerfile_frontend"],
                    "buildkit_input": locked["buildkit"],
                }
                report["stages"]["toolchain"] = "passed"

                pg_repository = f"{registry_host}/" + locked["postgresql"][
                    "repository"
                ].removeprefix("ghcr.io/")
                pg_builds: list[dict[str, str]] = []
                for number in (1, 2):
                    evidence = output / f"postgres-builder-{number}"
                    identity = local_postgres_identity(
                        root,
                        port=registry_port,
                        manage_registry=False,
                        evidence_dir=evidence,
                    )
                    pg_builds.append(identity)
                    for item in evidence.iterdir():
                        item.replace(output / f"postgres-builder-{number}-{item.name}")
                    evidence.rmdir()
                if pg_builds[0] != pg_builds[1]:
                    raise ValueError(
                        "independent clean PostgreSQL builders produced different identities"
                    )
                report["stages"]["postgresql_clean_rebuilds"] = {
                    "status": "passed",
                    "builds": pg_builds,
                }
                # Re-run the exact builder image used by the failed beta.3 workflow. This is
                # diagnostic only; acceptance remains the immutable release/inputs.json pin.
                legacy_evidence = output / "postgres-builder-previous-toolchain"
                legacy_identity = local_postgres_identity(
                    root,
                    port=registry_port,
                    manage_registry=False,
                    evidence_dir=legacy_evidence,
                    buildkit_image=PREVIOUS_BUILDKit,
                )
                legacy_evidence_file = legacy_evidence / "postgres-oci-evidence.json"
                fixed_evidence_file = output / "postgres-builder-1-postgres-oci-evidence.json"
                legacy_oci = json.loads(legacy_evidence_file.read_text())
                fixed_oci = json.loads(fixed_evidence_file.read_text())
                component_diff: dict[str, Any] = {
                    "previous_buildkit": PREVIOUS_BUILDKit,
                    "previous_identity": legacy_identity,
                    "pinned_buildkit_identity": pg_builds[0],
                    "index_digest_equal": legacy_oci["index_digest"] == fixed_oci["index_digest"],
                    "platform_digest_equal": legacy_oci["platform_digest"]
                    == fixed_oci["platform_digest"],
                    "config_digest_equal": legacy_oci["configuration_digest"]
                    == fixed_oci["configuration_digest"],
                    "layer_digests_equal": [
                        left.get("digest") == right.get("digest")
                        for left, right in zip(
                            legacy_oci["layer_descriptors"],
                            fixed_oci["layer_descriptors"],
                            strict=False,
                        )
                    ],
                    "layer_counts_equal": len(legacy_oci["layer_descriptors"])
                    == len(fixed_oci["layer_descriptors"]),
                }
                component: str | None = None
                raw_key: str | None = None
                if legacy_oci["platform_digest"] != fixed_oci["platform_digest"]:
                    component, raw_key = "platform_manifest", "platform_manifest"
                    if legacy_oci["configuration_digest"] != fixed_oci["configuration_digest"]:
                        component, raw_key = "configuration", "configuration"
                    else:
                        layer_mismatch = next(
                            (
                                index
                                for index, (left_layer, right_layer) in enumerate(
                                    zip(
                                        legacy_oci["layer_descriptors"],
                                        fixed_oci["layer_descriptors"],
                                        strict=False,
                                    )
                                )
                                if left_layer != right_layer
                            ),
                            None,
                        )
                        if layer_mismatch is not None:
                            component = f"layer[{layer_mismatch}]"
                elif legacy_oci["index_digest"] != fixed_oci["index_digest"]:
                    component, raw_key = "oci_index", "index"
                if component and raw_key:
                    left = legacy_oci["raw_documents_base64"][raw_key]
                    right = fixed_oci["raw_documents_base64"][raw_key]
                    left_bytes, right_bytes = base64.b64decode(left), base64.b64decode(right)
                    offset = next(
                        (
                            i
                            for i, pair in enumerate(zip(left_bytes, right_bytes, strict=False))
                            if pair[0] != pair[1]
                        ),
                        min(len(left_bytes), len(right_bytes)),
                    )
                    component_diff["first_differing_component"] = component
                    component_diff["first_component_byte_difference"] = {
                        "offset": offset,
                        "previous_byte": left_bytes[offset] if offset < len(left_bytes) else None,
                        "pinned_builder_byte": right_bytes[offset]
                        if offset < len(right_bytes)
                        else None,
                        "previous_length": len(left_bytes),
                        "pinned_builder_length": len(right_bytes),
                    }
                (legacy_evidence / "comparison-with-pinned-builder.json").write_text(
                    json.dumps(component_diff, indent=2) + "\n"
                )
                report["stages"]["previous_buildkit_diagnostic"] = component_diff
                for item in legacy_evidence.iterdir():
                    item.replace(output / ("postgres-previous-toolchain-" + item.name))
                legacy_evidence.rmdir()
                try:
                    for identity in pg_builds:
                        require_pinned_postgres(identity, locked["postgresql"])
                except ValueError as error:
                    report["stages"]["postgresql_registry_identity"] = {
                        "status": "failed",
                        "builds": pg_builds,
                        "error": str(error),
                    }
                    raise
                pg_reference = pg_repository + "@" + pg_builds[0]["index_digest"]
                report["stages"]["postgresql_registry_identity"] = {
                    "status": "passed",
                    "builds": pg_builds,
                }

                refs: dict[str, str] = {}
                epoch = int(run("git", "show", "-s", "--format=%ct", "HEAD"))
                for service in ("backend", "frontend"):
                    image = f"{registry_host}/alessandrorossato/florabase-{service}"
                    ref = build_application_image(
                        root,
                        builder,
                        service,
                        image + ":" + candidate,
                        locked["version"],
                        sha,
                        epoch,
                        locked["sbom_generator"],
                        output / f"{service}-build.json",
                    )
                    refs[service] = ref
                report["stages"]["application_production_builds"] = "passed"

                value = manifest(
                    root,
                    refs,
                    local=False,
                    registry_host=registry_host,
                    postgres_reference=pg_reference,
                )
                manifest_path = output / "release-manifest.json"
                manifest_path.write_text(json.dumps(value, indent=2) + "\n")
                report["stages"]["manifest_schema_and_identity"] = "passed"

                scan_refs = {**refs, "postgresql": pg_reference}
                for reference in scan_refs.values():
                    subprocess.run(
                        ["docker", "pull", "--platform", "linux/amd64", reference], check=True
                    )
                scan_images(scan_refs, output, locked["scanner"])
                software_bill_of_materials(
                    pg_reference, output / "postgresql-sbom.cdx.json", locked["scanner"]
                )
                report["stages"]["vulnerability_secret_scans"] = "passed"
                report["stages"]["postgresql_sbom"] = "passed"

                artifact = copy_smoke_artifact(root, output, value)
                try:
                    with (output / "image-smoke.log").open("w") as log:
                        run_artifact_smoke(
                            artifact,
                            local=False,
                            log=log,
                            postgres_image=pg_reference,
                            registry_host=registry_host,
                        )
                finally:
                    shutil.rmtree(artifact)
                report["stages"]["image_only_migration_login_media_smoke"] = "passed"

                assets = prepare_release_assets(root, output, locked["version"], sha)
                install_hashes = {name: assets[name][1] for name in value["install_bundle"]}
                if install_hashes != value["install_bundle"]:
                    raise ValueError("install asset bytes differ from the release manifest")
                asset_inventory = {
                    name: {"size": size, "sha256": digest}
                    for name, (size, digest) in assets.items()
                }
                (output / "release-asset-inventory.json").write_text(
                    json.dumps(asset_inventory, indent=2, sort_keys=True) + "\n"
                )
                report["release_asset_inventory"] = asset_inventory
                report["install_bundle"] = install_hashes
                report["release_api_inputs"] = release_finalization_inputs(value, sha, assets)
                report["stages"]["install_bundle_and_asset_inventory"] = "passed"

                promoted: dict[str, str] = {}
                for service, reference in refs.items():
                    promoted[service] = promote_image(reference, locked["version"], registry_host)
                promoted["postgresql"] = promote_image(
                    pg_reference, locked["postgresql"]["version"], registry_host
                )
                report["stages"]["disposable_version_tag_promotion"] = {
                    "status": "passed",
                    "digests": promoted,
                }
                report["attestation_inputs"] = release_attestation_inputs(
                    value,
                    {**refs, "postgresql": pg_reference},
                    manifest_path,
                    sha,
                    ".github/workflows/beta-images.yml",
                    install_hashes,
                    registry_host,
                )
                report["stages"]["release_and_attestation_inputs"] = "passed"
            finally:
                if builder_created:
                    subprocess.run(["docker", "buildx", "rm", builder], check=False)
    report["outcome"] = "passed"
    retain_report()
    print("BETA_RELEASE_REHEARSAL_PASSED", flush=True)


if __name__ == "__main__":
    main()
