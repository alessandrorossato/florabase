#!/usr/bin/env python3
"""Read-only compact lookup for docs/features.json and docs/release/scope-v1.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

FEATURES_PATH = Path("docs/features.json")
SCOPE_PATH = Path("docs/release/scope-v1.json")


def load_data(root: Path = Path(".")) -> tuple[list[dict[str, Any]], dict[str, str]]:
    features_doc = json.loads((root / FEATURES_PATH).read_text(encoding="utf-8"))
    scope_doc = json.loads((root / SCOPE_PATH).read_text(encoding="utf-8"))
    features = features_doc.get("features", [])
    membership = scope_doc.get("membership", {})
    if not isinstance(features, list) or not isinstance(membership, dict):
        raise ValueError("unexpected features.json or scope-v1.json structure")
    return features, membership


def format_entry(entry: dict[str, Any], release_class: str) -> str:
    fid = entry["id"]
    status = entry.get("status", "?")
    priority = entry.get("priority", "?")
    category = entry.get("category", "?")
    desc = entry.get("description", "")
    deps = ", ".join(entry.get("dependencies", [])) or "none"
    lines = [
        f"{fid} [{status} | {release_class} | {priority} | {category}]",
        f"  {desc}",
        f"  deps: {deps}",
        "  criteria:",
    ]
    for item in entry.get("acceptance_criteria", []):
        lines.append(f"    - {item}")
    return "\n".join(lines)


def format_row(entry: dict[str, Any], release_class: str) -> str:
    desc = str(entry.get("description", "")).replace("\n", " ").strip()
    if len(desc) > 90:
        desc = desc[:87].rstrip() + "..."
    return (
        f"{entry['id']:<28} {entry.get('status', '?'):<12} "
        f"{release_class:<13} {entry.get('priority', '?'):<3} {desc}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Florabase feature lookup.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--show", metavar="ID_OR_PREFIX", help="Exact feature ID or ID prefix.")
    group.add_argument("--list", action="store_true", help="List features (optionally by status).")
    parser.add_argument("--status", default="", help="Filter --list by status.")
    args = parser.parse_args(argv)

    try:
        features, membership = load_data()
    except (OSError, ValueError) as error:
        print(f"feature lookup: {error}", file=sys.stderr)
        return 1

    if args.show is not None:
        query = args.show.strip()
        if not query:
            print("feature lookup: ID is required", file=sys.stderr)
            return 2
        query_lower = query.lower()
        exact = [entry for entry in features if str(entry.get("id", "")).lower() == query_lower]
        matches = exact or [
            entry for entry in features if str(entry.get("id", "")).lower().startswith(query_lower)
        ]
        if not matches:
            print(f"feature lookup: no feature matching '{query}'", file=sys.stderr)
            return 1
        print("\n\n".join(format_entry(e, membership.get(e["id"], "unclassified")) for e in matches))
        return 0

    status_filter = args.status.strip()
    matched = [
        entry
        for entry in features
        if not status_filter or entry.get("status") == status_filter
    ]
    if not matched:
        print(f"feature lookup: no features with status '{status_filter}'", file=sys.stderr)
        return 1
    for entry in matched:
        print(format_row(entry, membership.get(entry["id"], "unclassified")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
