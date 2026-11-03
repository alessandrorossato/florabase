#!/usr/bin/env python3
"""Build paired beta candidates and validate immutable release evidence (no deployment)."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import IO, Any

from disposable_workflow import migration_head
from workflow_resources import Disposable, Owner

DIGEST = re.compile(r"sha256:[a-f0-9]{64}")
SHA = re.compile(r"[a-f0-9]{40}")
SOURCE = "https://github.com/alessandrorossato/florabase"


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected an object: {path}")
    return value


def check_platform(screen: dict[str, Any]) -> None:
    host = screen.get("host") or {}
    if (
        screen.get("status") != "approved"
        or screen.get("candidate_platform") != "linux/amd64"
        or not screen.get("operator")
        or not screen.get("screened_at")
        or not screen.get("evidence")
        or host.get("os") != "linux"
        or host.get("architecture") != "amd64"
        or host.get("runtime") != "docker"
        or not host.get("engine_version")
        or not re.match(r"(?:v)?(?:[2-9]|[1-9][0-9]+)\.", host.get("compose_version", ""))
        or not host.get("identity")
    ):
        raise ValueError(
            "PUBLICATION BLOCKED: intended-host Linux/amd64 Docker/Compose evidence and operator selection are required"
        )


def inputs(root: Path, publication: bool = False) -> dict[str, Any]:
    value = read(root / "release/inputs.json")
    version = value["version"]
    if not re.fullmatch(r"0\.1\.0-beta\.[1-9][0-9]*", version):
        raise ValueError("invalid beta version")
    if value["platforms"] != ["linux/amd64"]:
        raise ValueError("only the native amd64 candidate is supported by this workflow")
    if read(root / "frontend/package.json")["version"] != version:
        raise ValueError("frontend version mismatch")
    if f'__version__ = "{version}"' not in (root / "backend/src/florabase/__init__.py").read_text():
        raise ValueError("API version mismatch")
    if f'version = "{version}"' not in (root / "backend/pyproject.toml").read_text():
        raise ValueError("backend package version mismatch")
    for area in ("backend", "frontend"):
        if (root / area / "LICENSE").read_bytes() != (root / "LICENSE").read_bytes():
            raise ValueError("image license must match repository license")
    for name, ref in value["base_images"].items():
        dockerfile = root / ("backend" if name == "python" else "frontend") / "Dockerfile"
        if (
            "@" not in ref
            or not DIGEST.fullmatch(ref.split("@")[-1])
            or ref not in dockerfile.read_text()
        ):
            raise ValueError("base image identity drift")
    for tool in ("scanner", "buildkit", "sbom_generator", "dockerfile_frontend"):
        ref = value[tool]
        if "@" not in ref or not DIGEST.fullmatch(ref.split("@")[-1]):
            raise ValueError("mutable release tool input: " + tool)
    for area in ("backend", "frontend"):
        if (
            not (root / area / "Dockerfile")
            .read_text()
            .startswith("# syntax=" + value["dockerfile_frontend"] + "\n")
        ):
            raise ValueError("Dockerfile compiler identity drift")
    pg = value["postgresql"]
    if (
        pg["platform"] != "linux/amd64"
        or not DIGEST.fullmatch(pg["index_digest"])
        or not DIGEST.fullmatch(pg["platform_digest"])
        or pg["reference"] != f"{pg['repository']}:{pg['version']}@{pg['index_digest']}"
        or not DIGEST.fullmatch(value["scanner"].split("@")[-1])
    ):
        raise ValueError("invalid pinned release input")
    if publication:
        check_platform(read(root / "release/platform.json"))
    return value


def registry_record(reference: str, platform: str) -> dict[str, str]:
    if not re.fullmatch(r"ghcr\.io/[a-z0-9_./-]+@sha256:[a-f0-9]{64}", reference):
        raise ValueError("application registry references must use GHCR digests")
    descriptor = json.loads(
        run(
            "docker", "buildx", "imagetools", "inspect", reference, "--format", "{{json .Manifest}}"
        )
    )
    digest = reference.split("@")[1]
    if platform != "linux/amd64" or descriptor["digest"] != digest:
        raise ValueError("registry digest mismatch")
    native = [
        m
        for m in descriptor["manifests"]
        if m.get("platform", {}).get("os") == "linux"
        and m.get("platform", {}).get("architecture") == "amd64"
    ]
    if (
        len(native) != 1
        or not DIGEST.fullmatch(native[0]["digest"])
        or native[0]["digest"] == digest
        or any(
            m.get("platform", {}).get("architecture") not in {"amd64", "unknown"}
            or m.get("platform", {}).get("os") not in {"linux", "unknown"}
            for m in descriptor["manifests"]
        )
    ):
        raise ValueError("expected one native platform descriptor")
    return {
        "reference": reference,
        "index_digest": digest,
        "platform_digest": native[0]["digest"],
        "platform": platform,
    }


def validate_manifest(value: dict[str, Any], local: bool = False) -> None:
    if not local:
        schema_path = Path(__file__).with_name("manifest.schema.json")
        if not schema_path.exists():
            schema_path = Path(__file__).resolve().parents[1] / "release/manifest.schema.json"
        validator = importlib.import_module("jsonschema")
        try:
            validator.Draft202012Validator(read(schema_path)).validate(value)
        except validator.ValidationError as error:
            raise ValueError(
                "release manifest violates published schema: " + error.message
            ) from error
        if value["images"]["backend"]["reference"] == value["images"]["frontend"]["reference"]:
            raise ValueError("release pair must have distinct references")
    if not local:
        for field in ("index_digest", "platform_digest"):
            if value["images"]["backend"][field] == value["images"]["frontend"][field]:
                raise ValueError("release images must have distinct " + field)
        trusted_path = Path(__file__).with_name("inputs.json")
        if not trusted_path.exists():
            trusted_path = Path(__file__).resolve().parents[1] / "release/inputs.json"
        if value["build_inputs"] != read(trusted_path):
            raise ValueError("manifest build inputs differ from trusted release inputs")
    if (
        value["schema_version"] != 1
        or value["platforms"] != ["linux/amd64"]
        or not re.fullmatch(r"0\.1\.0-beta\.[1-9][0-9]*", value["version"])
        or not SHA.fullmatch(value["source"]["revision"])
        or value["source"]["url"] != SOURCE
        or not re.fullmatch(r"[A-Za-z0-9_]+", value["alembic_head"])
        or value["distribution"] != ("local-candidate" if local else "registry-candidate")
        or set(value["images"]) != {"backend", "frontend"}
        or (not local and value["source"].get("dirty") is not False)
        or value["build_inputs"]["postgresql"] != value["postgresql"]
        or value["build_inputs"]["version"] != value["version"]
        or value["build_inputs"]["platforms"] != value["platforms"]
    ):
        raise ValueError("invalid release manifest identity")
    for image in value["images"].values():
        if image["platform"] != "linux/amd64":
            raise ValueError("inconsistent image platform")
        if local:
            if not DIGEST.fullmatch(image["reference"]):
                raise ValueError("local candidates must select exact image IDs")
        elif (
            not re.fullmatch(r"ghcr\.io/[a-z0-9_./-]+@sha256:[a-f0-9]{64}", image["reference"])
            or image["reference"].split("@")[1] != image["index_digest"]
            or not DIGEST.fullmatch(image["platform_digest"])
        ):
            raise ValueError("invalid immutable image identity")
    pg = value["postgresql"]
    if (
        pg["repository"] != "docker.io/library/postgres"
        or pg["platform"] != "linux/amd64"
        or not DIGEST.fullmatch(pg["index_digest"])
        or not DIGEST.fullmatch(pg["platform_digest"])
        or pg["reference"] != f"{pg['repository']}:{pg['version']}@{pg['index_digest']}"
    ):
        raise ValueError("invalid PostgreSQL identity")


def manifest(root: Path, refs: dict[str, str], local: bool) -> dict[str, Any]:
    locked = inputs(root, publication=not local)
    revision = run("git", "-C", str(root), "rev-parse", "HEAD")
    if not SHA.fullmatch(revision):
        raise ValueError("invalid source revision")
    images: dict[str, Any] = {}
    for service, reference in refs.items():
        if local:
            image = json.loads(run("docker", "image", "inspect", reference))[0]
            images[service] = {"reference": image["Id"], "platform": "linux/amd64"}
        else:
            images[service] = registry_record(reference, "linux/amd64")
    result = {
        "schema_version": 1,
        "distribution": "local-candidate" if local else "registry-candidate",
        "version": locked["version"],
        "source": {
            "url": SOURCE,
            "revision": revision,
            "dirty": bool(run("git", "-C", str(root), "status", "--porcelain")),
        },
        "platforms": locked["platforms"],
        "alembic_head": migration_head(
            [
                (str(p), p.read_text())
                for p in sorted((root / "backend/alembic/versions").glob("*.py"))
            ]
        ),
        "postgresql": locked["postgresql"],
        "images": images,
        "build_inputs": locked,
        "workflow": {
            "run_id": os.environ.get("GITHUB_RUN_ID"),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        },
    }
    if not local and result["source"]["dirty"]:
        raise ValueError("publication requires a clean accepted commit")
    validate_manifest(result, local)
    return result


def run_artifact_smoke(artifact: Path, local: bool, log: IO[str] | None = None) -> None:
    """Let the artifact child unwind its resource owner when the parent is interrupted."""
    command = [
        "python3",
        "smoke-beta-images.py",
        "--manifest",
        "candidate.json" if local else "release-manifest.json",
    ]
    if local:
        command.append("--local")
    process = subprocess.Popen(
        command, cwd=artifact, stdout=log, stderr=subprocess.STDOUT if log else None
    )
    try:
        status = process.wait()
    except BaseException:
        process.terminate()
        try:
            process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        raise
    if status:
        raise subprocess.CalledProcessError(status, command)


def saved_descriptors(
    saved: tarfile.TarFile, configuration_digest: str, reference: str | None = None
) -> dict[str, Any]:
    """Retain hash-checked OCI descriptors binding the exported bytes to native/config IDs."""

    def document(name: str) -> dict[str, Any]:
        member = saved.extractfile(name)
        if member is None:
            raise ValueError("missing saved-image descriptor: " + name)
        data = member.read()
        if (
            name.startswith("blobs/sha256/")
            and hashlib.sha256(data).hexdigest() != name.split("/")[-1]
        ):
            raise ValueError("saved-image descriptor digest mismatch")
        result = json.loads(data)
        if not isinstance(result, dict):
            raise ValueError("invalid saved-image descriptor")
        return result

    def blob(digest: str) -> dict[str, Any]:
        if not DIGEST.fullmatch(digest):
            raise ValueError("invalid descriptor digest")
        return document("blobs/sha256/" + digest.removeprefix("sha256:"))

    if "index.json" not in saved.getnames():
        # Classic Docker saves config/layers without OCI descriptors. Registry release
        # inputs still have an authoritative index/native manifest to bind those bytes.
        if not reference or "@" not in reference:
            raise ValueError("OCI image store required for local descriptor retention")
        repository, index_digest = reference.split("@")

        def registry_blob(digest: str) -> dict[str, Any]:
            if not DIGEST.fullmatch(digest):
                raise ValueError("invalid registry descriptor digest")
            data = subprocess.check_output(
                ["docker", "buildx", "imagetools", "inspect", repository + "@" + digest, "--raw"]
            )
            # The CLI terminates its raw JSON output with a display newline.
            candidates = (data, data.removesuffix(b"\n"))
            payload = next(
                (
                    value
                    for value in candidates
                    if "sha256:" + hashlib.sha256(value).hexdigest() == digest
                ),
                None,
            )
            if payload is None:
                raise ValueError("registry descriptor digest mismatch")
            result = json.loads(payload)
            if not isinstance(result, dict):
                raise ValueError("invalid registry descriptor")
            return result

        index = registry_blob(index_digest)
        blob = registry_blob
    else:
        roots = document("index.json")["manifests"]
        if len(roots) != 1:
            raise ValueError("expected one exported image index")
        index_digest = roots[0]["digest"]
        index = blob(index_digest)
    native = [
        m
        for m in index["manifests"]
        if m.get("platform") == {"os": "linux", "architecture": "amd64"}
    ]
    if len(native) != 1:
        raise ValueError("expected one exported native platform")
    platform_digest = native[0]["digest"]
    platform = blob(platform_digest)
    if platform["config"]["digest"] != configuration_digest:
        raise ValueError("native manifest/config identity mismatch")
    return {
        "index_digest": index_digest,
        "platform_digest": platform_digest,
        "configuration_digest": configuration_digest,
        "index": index,
        "native_manifest": platform,
    }


def validate_scan(
    report: dict[str, Any], configuration_digest: str, service: str | None = None
) -> None:
    """A successful process alone cannot authorize an empty, stale or suppressed scan."""
    results = report.get("Results")
    if (
        report.get("SchemaVersion") != 2
        or report.get("ArtifactType") != "container_image"
        or report.get("Metadata", {}).get("ImageID") != configuration_digest
        or not isinstance(results, list)
        or not any(r.get("Class") == "os-pkgs" and r.get("Packages") for r in results)
        or report.get("ExperimentalModifiedFindings")
    ):
        raise ValueError("incomplete or mismatched security report")
    expected = {
        "backend": (
            "python-pkg",
            {"fastapi", "florabase-backend", "pillow", "psycopg-binary", "sqlalchemy"},
        ),
        "frontend": ("alpine", {"nginx"}),
        "postgresql": ("gobinary", {"github.com/tianon/gosu", "stdlib"}),
    }
    if service in expected:
        kind, packages = expected[service]
        observed = {
            package["Name"].lower()
            for result in results
            if result.get("Type") == kind
            for package in result.get("Packages", [])
        }
        if not packages <= observed:
            raise ValueError("incomplete security package inventory: " + str(service))
    for result in results:
        if (
            result.get("ExperimentalModifiedFindings")
            or result.get("Misconfigurations")
            or result.get("Secrets")
            or result.get("Vulnerabilities")
        ):
            raise ValueError("security report contains blocking findings")


def validate_release_assets(release: dict[str, Any], output: Path) -> None:
    """Require a complete private draft, including byte-bound evidence, before publication."""
    files = {p.name: p for p in output.iterdir() if p.is_file()}
    assets = release.get("assets", [])
    if release.get("draft") is not True or len(assets) != len(files):
        raise ValueError("incomplete draft release")
    if {a["name"] for a in assets} != set(files):
        raise ValueError("draft release asset names differ")
    for asset in assets:
        data = files[asset["name"]].read_bytes()
        if (
            asset.get("size") != len(data)
            or asset.get("digest") != "sha256:" + hashlib.sha256(data).hexdigest()
        ):
            raise ValueError("draft release asset digest/size mismatch")


def scan_images(refs: dict[str, str], output: Path, scanner: str) -> None:
    """Scan exact local bytes, retain every verdict, and retire owned scanner containers."""
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    owner = Owner.disposable("workflow-smoke", output)
    failures: list[str] = []
    with Disposable(owner), tempfile.TemporaryDirectory(prefix="florabase-scan-cache-") as cache:
        for service, ref in refs.items():
            inspected = json.loads(run("docker", "image", "inspect", ref))[0]
            identity = {
                "reference": ref,
                "image_inspect_id": inspected["Id"],
                "descriptor": inspected.get("Descriptor"),
                "repo_digests": inspected.get("RepoDigests"),
                "os": inspected["Os"],
                "architecture": inspected["Architecture"],
            }
            (output / (service + "-identity.json")).write_text(
                json.dumps(identity, indent=2) + "\n"
            )
            archive = output / (service + ".tar")
            subprocess.run(
                [
                    "docker",
                    "save",
                    "--output",
                    str(archive),
                    run("docker", "image", "inspect", "--format", "{{.Id}}", ref),
                ],
                check=True,
            )
            command = ["docker", "run", "--rm", "--user", f"{os.getuid()}:{os.getgid()}"]
            for key, value in owner.labels().items():
                command.extend(["--label", key + "=" + value])
            command.extend(
                [
                    "--mount",
                    f"type=bind,src={output},dst=/artifacts",
                    "--mount",
                    f"type=bind,src={cache},dst=/cache",
                    scanner,
                    "image",
                    "--quiet",
                    "--ignorefile",
                    "/dev/null",
                    "--show-suppressed",
                    "--cache-dir",
                    "/cache",
                    "--input",
                    "/artifacts/" + archive.name,
                    "--scanners",
                    "vuln,secret",
                    "--severity",
                    "HIGH,CRITICAL",
                    "--exit-code",
                    "1",
                    "--format",
                    "json",
                    "--output",
                    "/artifacts/" + service + "-security.json",
                ]
            )
            with tarfile.open(archive) as saved:
                manifest_member = saved.extractfile("manifest.json")
                if manifest_member is None:
                    raise ValueError("Docker save manifest missing")
                saved_manifest = json.load(manifest_member)
                config_member = saved.extractfile(saved_manifest[0]["Config"])
                if config_member is None:
                    raise ValueError("Docker save configuration missing")
                identity["configuration_digest"] = (
                    "sha256:" + hashlib.sha256(config_member.read()).hexdigest()
                )
                descriptors = saved_descriptors(saved, identity["configuration_digest"], ref)
                inspected_digest = (inspected.get("Descriptor") or {}).get("digest")
                if inspected_digest and inspected_digest != descriptors["index_digest"]:
                    raise ValueError("exported image index differs from inspected identity")
                if "@" in ref and ref.split("@")[-1] != descriptors["index_digest"]:
                    raise ValueError(
                        "exported image index differs from selected registry reference"
                    )
                (output / (service + "-descriptors.json")).write_text(
                    json.dumps(descriptors, indent=2) + "\n"
                )
            (output / (service + "-identity.json")).write_text(
                json.dumps(identity, indent=2) + "\n"
            )
            report_path = output / (service + "-security.json")
            if report_path.exists():
                raise ValueError(
                    "refuse to overwrite original security report: " + str(report_path)
                )
            try:
                result = subprocess.run(command, check=False)
                try:
                    validate_scan(read(report_path), identity["configuration_digest"], service)
                except (ValueError, OSError, TypeError, KeyError, AttributeError) as error:
                    failures.append(service + ": " + str(error))
                if result.returncode:
                    failures.append(service + ": scanner exit " + str(result.returncode))
            finally:
                archive.unlink(missing_ok=True)
    if failures:
        raise ValueError(
            "SECURITY GATE BLOCKED: "
            + ", ".join(failures)
            + "; inspect retained reports, never promote"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "manifest"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--publication", action="store_true")
    parser.add_argument("--local", action="store_true")
    parser.add_argument("--backend")
    parser.add_argument("--frontend")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    inputs(args.root, args.publication)
    if args.command == "manifest":
        if not args.backend or not args.frontend or not args.output:
            parser.error("manifest requires --backend, --frontend and --output")
        result = manifest(
            args.root, {"backend": args.backend, "frontend": args.frontend}, args.local
        )
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("BETA_RELEASE_INPUTS_PASSED")


if __name__ == "__main__":
    main()
