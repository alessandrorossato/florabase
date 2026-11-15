#!/usr/bin/env python3
"""Validate the small, machine-readable Florabase feature graph."""

from __future__ import annotations

import json
import sys
from pathlib import Path

MANIFEST = Path("docs/release/scope-v1.json")
CLASSES = [
    "baseline",
    "certify",
    "release-work",
    "best-effort",
    "tooling",
    "record",
    "internal",
    "post-1.0",
]


def fail(message: str) -> None:
    print(f"feature graph: {message}", file=sys.stderr)
    raise SystemExit(1)


def unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    # json keeps the last value of a repeated key; a repeated identifier must fail instead.
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key}")
        result[key] = value
    return result


def check_scope(by_id: dict[str, dict[str, object]], release_candidate: bool) -> list[str]:
    """Validate the release-scope manifest; return the entries that block a candidate."""
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"), object_pairs_hook=unique_keys)
    except (OSError, ValueError) as error:
        fail(f"cannot read {MANIFEST}: {error}")
    if not isinstance(manifest, dict):
        fail("scope manifest must be an object")
    if type(manifest.get("version")) is not int or manifest["version"] != 1:
        fail("scope manifest version must be 1")
    if manifest.get("release") != "1.0.0":
        fail("scope manifest release must be 1.0.0")
    if manifest.get("classes") != CLASSES:
        fail(f"scope manifest classes must be exactly {', '.join(CLASSES)}")
    membership = manifest.get("membership")
    if not isinstance(membership, dict):
        fail("scope manifest membership must be an object")
    missing = sorted(by_id.keys() - membership.keys())
    if missing:
        fail(f"scope manifest is missing {', '.join(missing)}")
    unknown = sorted(membership.keys() - by_id.keys())
    if unknown:
        fail(f"scope manifest names unknown feature {', '.join(unknown)}")
    blocking: list[str] = []
    for feature_id, feature in by_id.items():
        release_class = membership[feature_id]
        status = feature["status"]
        if release_class not in CLASSES:
            fail(f"{feature_id} has an unsupported release class")
        if release_class == "baseline" and status != "verified":
            fail(f"{feature_id} is baseline but not verified")
        if release_class == "post-1.0" and status == "verified":
            fail(f"{feature_id} is post-1.0 but verified")
        if release_class in ("certify", "release-work") and status in ("planned", "in_progress"):
            blocking.append(feature_id)
    if blocking and release_candidate:
        fail(f"release candidate blocked by {', '.join(blocking)}")
    return blocking


def main() -> None:
    arguments = sys.argv[1:]
    if arguments not in ([], ["--release-candidate"]):
        fail("usage: check-features.py [--release-candidate]")
    path = Path("docs/features.json")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot read {path}: {error}")

    statuses = document.get("allowed_statuses")
    features = document.get("features")
    if not isinstance(statuses, list) or not all(isinstance(item, str) for item in statuses):
        fail("allowed_statuses must be a list of strings")
    if not isinstance(features, list):
        fail("features must be a list")

    by_id: dict[str, dict[str, object]] = {}
    required = {"id", "category", "description", "acceptance_criteria", "dependencies", "priority", "status"}
    for feature in features:
        if not isinstance(feature, dict):
            fail("every feature must be an object")
        feature_id = feature.get("id")
        if not isinstance(feature_id, str) or not feature_id:
            fail("every feature needs a non-empty id")
        if feature_id in by_id:
            fail(f"duplicate feature id {feature_id}")
        missing = sorted(required - feature.keys())
        if missing:
            fail(f"{feature_id} is missing {', '.join(missing)}")
        if feature.get("status") not in statuses:
            fail(f"{feature_id} has an unsupported status")
        if not isinstance(feature.get("dependencies"), list) or not all(
            isinstance(item, str) for item in feature["dependencies"]
        ):
            fail(f"{feature_id} dependencies must be a list of ids")
        if not isinstance(feature.get("acceptance_criteria"), list) or not feature[
            "acceptance_criteria"
        ]:
            fail(f"{feature_id} needs acceptance criteria")
        by_id[feature_id] = feature

    for feature_id, feature in by_id.items():
        for dependency in feature["dependencies"]:
            if dependency not in by_id:
                fail(f"{feature_id} depends on missing feature {dependency}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(feature_id: str) -> None:
        if feature_id in visiting:
            fail(f"dependency cycle includes {feature_id}")
        if feature_id in visited:
            return
        visiting.add(feature_id)
        for dependency in by_id[feature_id]["dependencies"]:
            visit(dependency)
        visiting.remove(feature_id)
        visited.add(feature_id)

    for feature_id in by_id:
        visit(feature_id)
    blocking = check_scope(by_id, bool(arguments))
    print(f"feature graph: {len(by_id)} features valid")
    if blocking:
        print(f"feature graph: not ready for a release candidate: {', '.join(blocking)}")


if __name__ == "__main__":
    main()
