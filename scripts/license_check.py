#!/usr/bin/env python3
"""Audit installed PyPI and npm dependency licences for AGPL-3.0-or-later compatibility."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import re
import sys
from pathlib import Path

FORBIDDEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("GPL-2.0-only", re.compile(r"\bGPL[- ]?2(?:\.0)?-only\b", re.IGNORECASE)),
    ("SSPL", re.compile(r"\bSSPL\b|Server Side Public License", re.IGNORECASE)),
    ("BUSL", re.compile(r"\bBUSL\b|Business Source License", re.IGNORECASE)),
    (
        "non-commercial",
        re.compile(r"\bCC[- ]?BY[- ]?NC\b|non[- ]?commercial", re.IGNORECASE),
    ),
)


def check_licence(licence: str) -> str | None:
    """Return the first forbidden rule name matched by licence, or None."""
    for rule, pattern in FORBIDDEN_PATTERNS:
        if pattern.search(licence):
            return rule
    return None


def pypi_licence(dist: importlib.metadata.Distribution) -> str:
    meta = dist.metadata
    expr = (meta.get("License-Expression") or "").strip()
    if expr:
        return expr
    classifiers = [
        line.split(" :: ", 1)[1].strip()
        for line in meta.get_all("Classifier") or []
        if line.startswith("License :: ")
    ]
    if classifiers:
        return "; ".join(sorted(set(classifiers)))
    raw = (meta.get("License") or "").strip()
    if raw:
        return raw.splitlines()[0].strip()[:120]
    return "UNKNOWN"


def collect_pypi() -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    for dist in importlib.metadata.distributions():
        name = (dist.metadata.get("Name") or "").strip()
        version = dist.version
        if not name or (name.lower(), version) in seen:
            continue
        seen.add((name.lower(), version))
        rows.append((name, version, pypi_licence(dist)))
    return sorted(rows, key=lambda item: (item[0].lower(), item[1]))


def npm_licence(package_json: dict[str, object]) -> str:
    raw = package_json.get("license")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    if isinstance(raw, dict):
        kind = raw.get("type")
        if isinstance(kind, str) and kind.strip():
            return kind.strip()
    raw_list = package_json.get("licenses")
    if isinstance(raw_list, list):
        parts = []
        for entry in raw_list:
            if isinstance(entry, str) and entry.strip():
                parts.append(entry.strip())
            elif isinstance(entry, dict) and isinstance(entry.get("type"), str):
                parts.append(str(entry["type"]).strip())
        if parts:
            return " OR ".join(parts)
    return "UNKNOWN"


def collect_npm(node_modules: Path) -> list[tuple[str, str, str]]:
    pnpm_root = node_modules / ".pnpm"
    search_root = pnpm_root if pnpm_root.is_dir() else node_modules
    if not search_root.is_dir():
        raise FileNotFoundError(f"npm dependencies directory not found: {search_root}")
    rows: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    for pkg_file in sorted(search_root.rglob("package.json")):
        if pkg_file.parent.name == "node_modules":
            continue
        try:
            data = json.loads(pkg_file.read_text(encoding="utf-8"))
        except OSError, json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        name = data.get("name")
        version = data.get("version")
        if not isinstance(name, str) or not isinstance(version, str) or not name or not version:
            continue
        # Only inspect top-level installed package manifests under a node_modules/<pkg>
        # or node_modules/@scope/<pkg> directory.
        parent = pkg_file.parent
        grand = parent.parent
        if grand.name != "node_modules" and not (
            grand.name.startswith("@") and grand.parent.name == "node_modules"
        ):
            continue
        key = (name, version)
        if key in seen:
            continue
        seen.add(key)
        rows.append((name, version, npm_licence(data)))
    return sorted(rows, key=lambda item: (item[0].lower(), item[1]))


def report(ecosystem: str, rows: list[tuple[str, str, str]]) -> int:
    print(f"== {ecosystem} dependency licences ({len(rows)} packages) ==")
    violations: list[tuple[str, str, str, str]] = []
    for name, version, licence in rows:
        print(f"  {name}=={version}: {licence}")
        hit = check_licence(licence)
        if hit is not None:
            violations.append((name, version, licence, hit))
    if violations:
        print(f"\nForbidden {ecosystem} licences detected:", file=sys.stderr)
        for name, version, licence, rule in violations:
            print(f"  - {name}=={version}: {licence} (matched {rule})", file=sys.stderr)
        return 1
    print(f"{ecosystem} licence check passed ({len(rows)} packages, 0 forbidden).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pypi", action="store_true", help="Inspect installed Python packages")
    group.add_argument("--npm", type=Path, help="Inspect installed npm packages under node_modules")
    args = parser.parse_args()
    if args.pypi:
        return report("PyPI", collect_pypi())
    return report("npm", collect_npm(args.npm))


if __name__ == "__main__":
    raise SystemExit(main())
