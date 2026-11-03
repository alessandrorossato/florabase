#!/usr/bin/env python3
"""Build and smoke local candidates; retire exact owned images, never publish."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from beta_release import inputs, manifest, run, run_artifact_smoke, scan_images
from workflow_resources import Disposable, Owner


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--security-dir", type=Path)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    locked = inputs(root)
    owner = Owner.disposable("verification-build", root)
    refs = {}
    build_metadata: dict[str, Any] = {}
    with (
        Disposable(owner),
        tempfile.TemporaryDirectory(prefix="beta-build-metadata-") as metadata_dir,
    ):
        for service in ("backend", "frontend"):
            tag = owner.project + "-" + service
            command = [
                "docker",
                "build",
                "--platform",
                "linux/amd64",
                "--metadata-file",
                str(Path(metadata_dir) / (service + ".json")),
                "--target",
                "runtime",
                "--tag",
                tag,
                "--build-arg",
                "VERSION=" + locked["version"],
                "--build-arg",
                "REVISION=" + run("git", "rev-parse", "HEAD"),
                "--build-arg",
                "SOURCE_DATE_EPOCH=" + run("git", "show", "-s", "--format=%ct", "HEAD"),
            ]
            for key, value in owner.labels().items():
                command.extend(["--label", key + "=" + value])
            subprocess.run([*command, str(root / service)], check=True)
            refs[service] = tag
            build_metadata[service] = json.loads(
                (Path(metadata_dir) / (service + ".json")).read_text()
            )
        candidate_manifest = manifest(root, refs, local=True)
        args.evidence.write_text(json.dumps(candidate_manifest, indent=2) + "\n")
        with tempfile.TemporaryDirectory(prefix="florabase-artifact-only-") as temporary:
            artifact = Path(temporary)
            shutil.copyfile(
                root / "release/manifest.schema.json", artifact / "manifest.schema.json"
            )
            shutil.copyfile(Path("release/inputs.json"), artifact / "inputs.json")
            for name in (
                "smoke-beta-images.py",
                "beta_release.py",
                "disposable_workflow.py",
                "workflow_resources.py",
            ):
                shutil.copyfile(root / "scripts" / name, artifact / name)
            shutil.copyfile(args.evidence, artifact / "candidate.json")
            run_artifact_smoke(artifact, local=True)
        if args.security_dir:
            args.security_dir.mkdir(parents=True, exist_ok=True)
            (args.security_dir / "build-metadata.json").write_text(
                json.dumps(build_metadata, indent=2) + "\n"
            )
            scan_images(
                {**refs, "postgresql": locked["postgresql"]["reference"]},
                args.security_dir,
                locked["scanner"],
            )
    print("LOCAL_BETA_CANDIDATE_PASSED (not registry publication or host approval)")


if __name__ == "__main__":
    main()
