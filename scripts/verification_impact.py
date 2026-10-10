#!/usr/bin/env python3
"""Versioned, fail-closed local verification plans from the exact complete feature tree."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path
from typing import Any, cast

MAP_PATH = Path(__file__).with_name("verification-impact.json")
STATIC = ["format-check", "lint", "typecheck", "api-check"]
WORKFLOW = [
    "test-workflow-helpers",
    "test-feature-workflow",
    "test-preview-workflow",
    "test-environment-workflow",
    "test-uat-preview",
    "test-verification-impact",
    "test-workflow-resources",
    "workflow-check",
]


def fingerprint_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "feature_fingerprint", Path(__file__).with_name("feature-tree-fingerprint.py")
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def changed_paths(base: str) -> list[str]:
    """Compare final file modes/blobs with base, including all tracked/untracked work.

    Comparing inventories (rather than rename heuristics) retains old and new rename paths,
    deleted paths, staged additions and committed changes. Index/HEAD differences also
    participate even when an unstaged edit masks their final content.
    """
    fp = fingerprint_module()
    base_tree = subprocess.run(
        ["git", "ls-tree", "-r", "-z", base], check=True, stdout=subprocess.PIPE
    ).stdout
    before: dict[str, tuple[str, str]] = {}
    for record in base_tree.split(b"\0"):
        if record:
            metadata, path = record.split(b"\t", 1)
            mode, kind, blob = metadata.decode().split()
            if kind != "blob":
                raise ValueError("submodules cannot be safely classified")
            before[path.decode("utf-8", "surrogateescape")] = (mode, blob)
    after = {entry["path"]: (entry["mode"], entry["blob"]) for entry in fp.working_entries()}
    changed = {path for path in before.keys() | after.keys() if before.get(path) != after.get(path)}
    for revision in ([base, "HEAD"], ["--cached", base], []):
        raw = subprocess.run(
            ["git", "diff", "--name-only", "--no-renames", "-z", *revision],
            check=True,
            stdout=subprocess.PIPE,
        ).stdout
        changed.update(path.decode("utf-8", "surrogateescape") for path in raw.split(b"\0") if path)
    return sorted(changed)


def load_map() -> dict[str, Any]:
    data = cast(dict[str, Any], json.loads(MAP_PATH.read_text()))
    if data["version"] != 1 or not data["scopes"] or not data["rules"]:
        raise ValueError("unsupported or empty impact map")
    for name, scope in data["scopes"].items():
        if any(item not in data["scopes"] for item in scope["affects"]):
            raise ValueError(f"unknown impact dependency in {name}")
        if "suite_scope" in scope:
            if (
                scope["suite_scope"] not in data["scopes"]
                or "suite_scope" in data["scopes"][scope["suite_scope"]]
            ):
                raise ValueError(f"invalid regression suite reference in {name}")
            continue
        for layer in ("backend", "integration", "frontend"):
            if not isinstance(scope[layer], list):
                raise ValueError(f"invalid {layer} suites in {name}")
    for rule in data["rules"]:
        if rule["scope"] not in data["scopes"] or rule["layer"] not in {"backend", "frontend"}:
            raise ValueError("invalid impact rule")
    return data


def plan_paths(paths: list[str], base: str, *, force_full: bool = False) -> dict[str, Any]:
    data = load_map()
    reasons: list[str] = []
    direct: set[str] = set()
    layers: set[str] = set()
    generated = False
    docs_only = True
    for path in sorted(set(paths)):
        if any(path.startswith(prefix) for prefix in data["full_prefixes"]):
            reasons.append(f"high-risk path: {path}")
            docs_only = False
            continue
        if path in data["generated_paths"]:
            generated = True
            layers.update(("backend", "frontend"))
            docs_only = False
            continue
        if path in data["documentation_paths"] or any(
            path.startswith(p) for p in data["documentation_prefixes"]
        ):
            direct.add("documentation")
            continue
        docs_only = False
        matches = [
            rule
            for rule in data["rules"]
            if rule.get("path") == path or ("prefix" in rule and path.startswith(rule["prefix"]))
        ]
        if not matches:
            reasons.append(f"unclassified path: {path}")
        for rule in matches:
            direct.add(rule["scope"])
            layers.add(rule["layer"])
    if generated and not direct.difference({"documentation"}):
        reasons.append("generated contract without classified owning production scope")
    if force_full:
        reasons.append("operator requested full verification")
    affected = direct.difference({"documentation"})
    pending = list(affected)
    while pending:
        for target in data["scopes"][pending.pop()]["affects"]:
            if target not in affected:
                affected.add(target)
                pending.append(target)
    full = bool(reasons)
    suites: dict[str, list[str]] = {}
    for layer in ("backend", "integration", "frontend"):
        required = layer == "frontend" or "backend" in layers
        suites[layer] = (
            ["ALL"]
            if full
            else sorted(
                {
                    p
                    for scope in affected
                    for p in data["scopes"][data["scopes"][scope].get("suite_scope", scope)][layer]
                }
            )
            if required
            else []
        )
        # A newly added test in a classified feature module must run too. This selects exact
        # changed test paths; it neither learns dependencies nor mutates the versioned policy.
        if not full and layer == "frontend":
            changed_tests = {
                path
                for path in paths
                if re.fullmatch(r"frontend/src/.*\.(test|spec)\.[cm]?[jt]sx?", path)
                and Path(path).is_file()
            }
            suites[layer] = sorted(set(suites[layer]) | changed_tests)
        # A missing mapped suite is a policy error, never permission to skip it.
        if not full:
            missing = [path for path in suites[layer] if not Path(path).is_file()]
            if missing:
                raise ValueError(f"missing mapped suites: {missing}")
    mode = "full" if full else "affected"
    return {
        "version": 1,
        "base": base,
        "mode": mode,
        "impact_map_version": data["version"],
        "impact_map_digest": hashlib.sha256(MAP_PATH.read_bytes()).hexdigest(),
        "changed_paths": sorted(set(paths)),
        "changed_scopes": sorted(direct),
        "affected_scopes": sorted(
            affected | ({"documentation"} if "documentation" in direct else set())
        ),
        "escalation_reasons": sorted(reasons),
        "docs_only": docs_only and not full,
        **suites,
        "workflow": WORKFLOW if full else [],
        "static": ["feature-graph", "whitespace"] + (STATIC if full or not docs_only else []),
        "migration": full or any(p.startswith("backend/alembic/") for p in paths),
        "migration_cycle": any(
            p.startswith(("backend/alembic/", "backend/src/florabase/db/"))
            or p
            in {
                "scripts/verify-migration-cycle.sh",
                "scripts/disposable_workflow.py",
                "compose.integration.yaml",
            }
            for p in paths
        ),
        "builds": ["backend", "frontend"]
        if full or layers == {"backend", "frontend"}
        else ["backend"]
        if "backend" in layers
        else ["frontend"]
        if "frontend" in layers
        else [],
        "remote_ci": "full",
    }


def make_plan(base: str, *, force_full: bool = False) -> dict[str, Any]:
    resolved = subprocess.run(
        ["git", "rev-parse", "--verify", f"{base}^{{commit}}"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()
    return plan_paths(changed_paths(resolved), resolved, force_full=force_full)


def describe(plan: dict[str, Any]) -> str:
    lines = [
        f"Verification base: {plan['base']}",
        f"Mode: {plan['mode']}",
        f"Changed scopes: {', '.join(plan['changed_scopes']) or 'none'}",
        f"Affected scopes: {', '.join(plan['affected_scopes']) or 'none'}",
    ]
    lines += [f"FULL reason: {reason}" for reason in plan["escalation_reasons"]]
    for key in ("backend", "integration", "frontend", "workflow", "static", "builds"):
        values = plan[key]
        summary = ", ".join(values) or "skipped"
        if key in {"backend", "integration", "frontend"} and len(values) > 6:
            summary = (
                f"{len(values)} explicit files: "
                + ", ".join(Path(value).name for value in values[:6])
                + ", … (full list in JSON plan)"
            )
        lines.append(f"{key.title()}: {summary}")
    lines += [
        f"Migration: {'base → head → base → head (or no revisions)' if plan['migration'] else 'skipped'}",
        "Remote PR CI: full",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    plan = make_plan(args.base, force_full=args.full)
    print(json.dumps(plan, sort_keys=True, indent=2) if args.json else describe(plan))


if __name__ == "__main__":
    main()
