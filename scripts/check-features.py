#!/usr/bin/env python3
"""Validate the small, machine-readable Florabase feature graph."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def fail(message: str) -> None:
    print(f"feature graph: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
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
    print(f"feature graph: {len(by_id)} features valid")


if __name__ == "__main__":
    main()
