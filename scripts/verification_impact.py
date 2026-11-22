#!/usr/bin/env python3
"""Versioned, fail-closed local verification plans from the exact complete feature tree."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

MAP_PATH = Path(__file__).with_name("verification-impact.json")
BACKEND_TEST_ROOT = Path("backend/tests")
BACKEND_INTEGRATION_ROOT = Path("backend/tests/integration")
FRONTEND_ROOT = Path("frontend")
BACKEND_SKIP_DIRS = frozenset(
    {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".git"}
)
FRONTEND_RECURSIVE_SKIP_DIRS = frozenset({"node_modules", ".git"})
FRONTEND_TOP_SKIP_DIRS = frozenset({".pnpm-store", "dist", "coverage"})
FRONTEND_TEST_RE = re.compile(r".*\.(test|spec)\.[cm]?[jt]sx?$")
TEST_LAYERS = ("backend", "integration", "frontend")
STATIC = ["format-check", "lint", "typecheck", "api-check"]
WORKFLOW = [
    "test-workflow-helpers",
    "test-feature-workflow",
    "test-agent-workflow",
    "test-preview-workflow",
    "test-environment-workflow",
    "test-uat-preview",
    "test-verification-impact",
    "test-workflow-resources",
    "test-ui-page",
    "workflow-check",
]
TIER_ORDER: dict[str, int] = {
    "docs": 0,
    "affected": 1,
    "product-frontend": 2,
    "product": 3,
    "full": 4,
}


def plan_tier(plan: dict[str, Any]) -> str:
    mode = plan.get("mode")
    docs_only = plan.get("docs_only")
    expected: str | None = None
    if mode == "full" and docs_only is False:
        expected = "full"
    elif mode == "product" and docs_only is False:
        expected = "product"
    elif mode == "product-frontend" and docs_only is False:
        expected = "product-frontend"
    elif mode == "affected" and isinstance(docs_only, bool):
        expected = "docs" if docs_only else "affected"
    if expected is None:
        raise ValueError(
            f"invalid verification plan tier state: mode={mode!r}, docs_only={docs_only!r}"
        )
    declared = plan.get("tier")
    if declared is not None and declared != expected:
        raise ValueError(
            f"mismatched verification plan tier: declared={declared!r}, expected={expected!r}"
        )
    return expected


def fingerprint_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "feature_fingerprint", Path(__file__).with_name("feature-tree-fingerprint.py")
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def changed_paths(base: str) -> list[str]:
    return sorted(changed_path_modes(base))


def changed_path_modes(base: str) -> dict[str, set[str]]:
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
            metadata, raw_path = record.split(b"\t", 1)
            mode, kind, blob = metadata.decode().split()
            if kind != "blob":
                raise ValueError("submodules cannot be safely classified")
            before[raw_path.decode("utf-8", "surrogateescape")] = (mode, blob)
    after = {entry["path"]: (entry["mode"], entry["blob"]) for entry in fp.working_entries()}
    changed: dict[str, set[str]] = {
        path: set() for path in before.keys() | after.keys() if before.get(path) != after.get(path)
    }
    for revision in ([base, "HEAD"], ["--cached", base], []):
        raw = subprocess.run(
            ["git", "diff", "--raw", "--no-renames", "-z", *revision],
            check=True,
            stdout=subprocess.PIPE,
        ).stdout
        records = iter(raw.split(b"\0")[:-1])
        for metadata in records:
            path = next(records).decode("utf-8", "surrogateescape")
            old_mode, new_mode, _, _, status = metadata[1:].decode().split()
            if status == "U":
                raise ValueError(f"unmerged path cannot be safely classified: {path}")
            changed.setdefault(path, set()).update({old_mode, new_mode} - {"000000"})
    for path, modes in changed.items():
        for inventory in (before, after):
            if path in inventory:
                modes.add(inventory[path][0])
    return changed


def is_backend_test_name(name: str) -> bool:
    return name.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py"))


def is_frontend_test_name(name: str) -> bool:
    return bool(FRONTEND_TEST_RE.fullmatch(name))


def test_layer_for(path: str) -> str | None:
    candidate = Path(path)
    name = candidate.name
    if path.startswith("backend/tests/integration/"):
        return "integration" if is_backend_test_name(name) else None
    if path.startswith("backend/tests/"):
        return "backend" if is_backend_test_name(name) else None
    if path.startswith("frontend/"):
        parts = candidate.parts[1:]
        if (parts and parts[0] in FRONTEND_TOP_SKIP_DIRS) or any(
            part in FRONTEND_RECURSIVE_SKIP_DIRS for part in parts
        ):
            return None
        return "frontend" if is_frontend_test_name(name) else None
    return None


def _is_safe_relative(value: object, *, directory: bool) -> bool:
    if not isinstance(value, str) or not value or value.startswith("/"):
        return False
    if directory and not value.endswith("/"):
        return False
    if not directory and value.endswith("/"):
        return False
    return ".." not in Path(value).parts


def discover_tests_in_dir(directory: Path, layer: str) -> list[str]:
    if directory.is_symlink():
        raise ValueError(f"symlinked test directory is not supported: {directory.as_posix()}")
    if not directory.is_dir():
        return []
    matcher = is_frontend_test_name if layer == "frontend" else is_backend_test_name
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(directory, followlinks=False):
        current = Path(dirpath)
        kept: list[str] = []
        for name in sorted(dirnames):
            if layer == "frontend":
                if name in FRONTEND_RECURSIVE_SKIP_DIRS or (
                    current == FRONTEND_ROOT and name in FRONTEND_TOP_SKIP_DIRS
                ):
                    continue
            elif name in BACKEND_SKIP_DIRS or (
                layer == "backend" and current == BACKEND_TEST_ROOT and name == "integration"
            ):
                continue
            candidate = current / name
            if candidate.is_symlink():
                raise ValueError(
                    f"symlinked test directory is not supported: {candidate.as_posix()}"
                )
            kept.append(name)
        dirnames[:] = kept
        for filename in sorted(filenames):
            if matcher(filename):
                found.append((current / filename).as_posix())
    return found


def discover_repo_tests() -> dict[str, list[str]]:
    return {
        "backend": discover_tests_in_dir(BACKEND_TEST_ROOT, "backend"),
        "integration": discover_tests_in_dir(BACKEND_INTEGRATION_ROOT, "integration"),
        "frontend": discover_tests_in_dir(FRONTEND_ROOT, "frontend"),
    }


def load_map() -> dict[str, Any]:
    data = cast(dict[str, Any], json.loads(MAP_PATH.read_text()))
    if data["version"] != 2 or not data["scopes"] or not data["rules"]:
        raise ValueError("unsupported or empty impact map")
    for legacy_key in ("product_prefixes", "product_tests"):
        if legacy_key in data:
            raise ValueError(f"legacy impact map key is not supported: {legacy_key}")
    prefix_requirements: tuple[tuple[str, str | None], ...] = (
        ("full_prefixes", None),
        ("product_backend_prefixes", "backend/"),
        ("product_frontend_prefixes", "frontend/"),
    )
    for prefix_key, required_root in prefix_requirements:
        prefixes = data.get(prefix_key)
        if (
            not isinstance(prefixes, list)
            or not prefixes
            or any(
                not isinstance(prefix, str)
                or not prefix
                or (required_root is not None and not prefix.startswith(required_root))
                for prefix in prefixes
            )
        ):
            raise ValueError(f"invalid {prefix_key}")
    test_requirements: tuple[tuple[str, frozenset[str] | None], ...] = (
        ("full_tests", None),
        ("product_backend_tests", frozenset({"backend", "integration"})),
        ("product_frontend_tests", frozenset({"frontend"})),
    )
    for test_key, allowed_layers in test_requirements:
        entries = data.get(test_key)
        if not isinstance(entries, list) or any(
            not _is_safe_relative(entry, directory=False)
            or test_layer_for(entry) is None
            or (allowed_layers is not None and test_layer_for(entry) not in allowed_layers)
            for entry in entries
        ):
            raise ValueError(f"invalid {test_key}")
    suffixes = data["documentation_suffixes"]
    if (
        not isinstance(suffixes, list)
        or not suffixes
        or any(
            not isinstance(suffix, str) or not re.fullmatch(r"\.[a-z0-9]+", suffix)
            for suffix in suffixes
        )
    ):
        raise ValueError("invalid documentation suffixes")
    owned_dirs: dict[str, list[str]] = {layer: [] for layer in TEST_LAYERS}
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
        for layer in TEST_LAYERS:
            suites = scope.get(layer)
            if not isinstance(suites, list) or any(
                not _is_safe_relative(entry, directory=False) or test_layer_for(entry) != layer
                for entry in suites
            ):
                raise ValueError(f"invalid {layer} suites in {name}")
            dirs_key = f"{layer}_dirs"
            dirs = scope.get(dirs_key)
            if not isinstance(dirs, list) or any(
                not _is_safe_relative(entry, directory=True) for entry in dirs
            ):
                raise ValueError(f"invalid {dirs_key} in {name}")
            for directory in dirs:
                if layer == "backend" and (
                    not directory.startswith("backend/tests/")
                    or directory == "backend/tests/"
                    or directory.startswith("backend/tests/integration/")
                ):
                    raise ValueError(f"invalid backend test directory in {name}: {directory}")
                if layer == "integration" and (
                    not directory.startswith("backend/tests/integration/")
                    or directory == "backend/tests/integration/"
                ):
                    raise ValueError(f"invalid integration test directory in {name}: {directory}")
                if layer == "frontend" and (
                    not directory.startswith("frontend/src/") or directory == "frontend/src/"
                ):
                    raise ValueError(f"invalid frontend test directory in {name}: {directory}")
                owned_dirs[layer].append(directory)
    for layer, directories in owned_dirs.items():
        ordered = sorted(directories)
        for index in range(len(ordered) - 1):
            if ordered[index + 1].startswith(ordered[index]):
                raise ValueError(
                    f"overlapping {layer} test directory ownership: "
                    f"{ordered[index]} and {ordered[index + 1]}"
                )
    for rule in data["rules"]:
        if rule["scope"] not in data["scopes"] or rule["layer"] not in {"backend", "frontend"}:
            raise ValueError("invalid impact rule")
    return data


def test_scopes_for(path: str, data: dict[str, Any]) -> list[tuple[str, str]]:
    layer = test_layer_for(path)
    if layer is None:
        return []
    rule_layer = "backend" if layer in {"backend", "integration"} else "frontend"
    matches: list[tuple[str, str]] = []
    for name, scope in data["scopes"].items():
        if "suite_scope" in scope:
            continue
        if path in scope[layer] or any(path.startswith(d) for d in scope[f"{layer}_dirs"]):
            matches.append((name, rule_layer))
    return matches


def is_test_owned(path: str, data: dict[str, Any]) -> bool:
    for prefix_key, test_key in (
        ("full_prefixes", "full_tests"),
        ("product_backend_prefixes", "product_backend_tests"),
        ("product_frontend_prefixes", "product_frontend_tests"),
    ):
        if any(path.startswith(prefix) for prefix in data[prefix_key]) or path in set(
            data[test_key]
        ):
            return True
    return bool(test_scopes_for(path, data))


def validate_test_inventory(data: dict[str, Any], paths: Sequence[str] = ()) -> None:
    discovered = discover_repo_tests()
    candidates = {path for files in discovered.values() for path in files}
    for path in paths:
        if test_layer_for(path) is not None and Path(path).is_file():
            candidates.add(path)
    unowned = sorted(path for path in candidates if not is_test_owned(path, data))
    if unowned:
        raise ValueError(
            "unowned test files (place in an owned scope directory or register in "
            f"scripts/verification-impact.json): {', '.join(unowned)}"
        )


def plan_paths(
    paths: list[str],
    base: str,
    *,
    force_full: bool = False,
    non_static_paths: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    data = load_map()
    validate_test_inventory(data, paths)
    full_tests = set(data["full_tests"])
    product_backend_tests = set(data["product_backend_tests"])
    product_frontend_tests = set(data["product_frontend_tests"])
    reasons: list[str] = []
    product_reasons: list[str] = []
    direct: set[str] = set()
    layers: set[str] = set()
    generated = False
    product_backend = False
    product_frontend = False
    docs_only = True
    for path in sorted(set(paths)):
        if any(path.startswith(prefix) for prefix in data["full_prefixes"]) or path in full_tests:
            reasons.append(f"high-risk path: {path}")
            docs_only = False
            continue
        if (
            any(path.startswith(prefix) for prefix in data["product_backend_prefixes"])
            or path in product_backend_tests
        ):
            product_backend = True
            product_reasons.append(f"shared product path: {path}")
            layers.update(("backend", "frontend"))
            docs_only = False
            continue
        if (
            any(path.startswith(prefix) for prefix in data["product_frontend_prefixes"])
            or path in product_frontend_tests
        ):
            product_frontend = True
            product_reasons.append(f"shared frontend product path: {path}")
            layers.add("frontend")
            docs_only = False
            continue
        if path in data["generated_paths"]:
            generated = True
            layers.update(("backend", "frontend"))
            docs_only = False
            continue
        if path in data["documentation_paths"] or any(
            path.startswith(prefix) for prefix in data["documentation_prefixes"]
        ):
            if path in non_static_paths or (
                path not in data["documentation_paths"]
                and Path(path).suffix.lower() not in data["documentation_suffixes"]
            ):
                reasons.append(f"executable or unclassified documentation path: {path}")
                docs_only = False
            else:
                direct.add("documentation")
            continue
        docs_only = False
        matches = [
            (rule["scope"], rule["layer"])
            for rule in data["rules"]
            if rule.get("path") == path or ("prefix" in rule and path.startswith(rule["prefix"]))
        ]
        matches.extend(test_scopes_for(path, data))
        if not matches:
            reasons.append(f"unclassified path: {path}")
        for scope, rule_layer in matches:
            direct.add(scope)
            layers.add(rule_layer)
    if generated and not product_backend and not direct.difference({"documentation"}):
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
    product_wide = not full and (product_backend or (product_frontend and "backend" in layers))
    product_fe_wide = not full and not product_wide and product_frontend
    suites: dict[str, list[str]] = {}
    for layer in TEST_LAYERS:
        required = layer == "frontend" or "backend" in layers
        if full or product_wide:
            suites[layer] = ["ALL"]
        elif product_fe_wide:
            suites[layer] = ["ALL"] if layer == "frontend" else []
        elif required:
            selected: set[str] = set()
            for scope in affected:
                target = data["scopes"][data["scopes"][scope].get("suite_scope", scope)]
                selected.update(target[layer])
                for directory in target[f"{layer}_dirs"]:
                    selected.update(discover_tests_in_dir(Path(directory), layer))
                    selected.update(
                        path
                        for path in paths
                        if test_layer_for(path) == layer
                        and path.startswith(directory)
                        and Path(path).is_file()
                    )
            suites[layer] = sorted(selected)
        else:
            suites[layer] = []
        # A missing mapped suite is a policy error, never permission to skip it.
        if not full and not product_wide and not product_fe_wide:
            missing = [path for path in suites[layer] if not Path(path).is_file()]
            if missing:
                raise ValueError(f"missing mapped suites: {missing}")
    explicit_tests = (
        full_tests
        | product_backend_tests
        | product_frontend_tests
        | {
            p
            for scope in data["scopes"].values()
            if "suite_scope" not in scope
            for layer in TEST_LAYERS
            for p in scope[layer]
        }
    )
    missing_explicit = [
        path for path in sorted(set(paths) & explicit_tests) if not Path(path).is_file()
    ]
    if missing_explicit:
        raise ValueError(f"missing mapped suites: {missing_explicit}")
    mode = (
        "full"
        if full
        else "product"
        if product_wide
        else "product-frontend"
        if product_fe_wide
        else "affected"
    )
    is_docs_only = docs_only and not full and not product_wide and not product_fe_wide
    tier = (
        "full"
        if full
        else "product"
        if product_wide
        else "product-frontend"
        if product_fe_wide
        else "docs"
        if is_docs_only
        else "affected"
    )
    return {
        "version": 1,
        "base": base,
        "tier": tier,
        "mode": mode,
        "impact_map_version": data["version"],
        "impact_map_digest": hashlib.sha256(MAP_PATH.read_bytes()).hexdigest(),
        "changed_paths": sorted(set(paths)),
        "changed_scopes": sorted(direct),
        "affected_scopes": sorted(
            affected | ({"documentation"} if "documentation" in direct else set())
        ),
        "escalation_reasons": sorted(reasons),
        "product_reasons": sorted(product_reasons),
        "docs_only": is_docs_only,
        **suites,
        "workflow": WORKFLOW if full else [],
        "static": ["feature-graph", "whitespace"] + (STATIC if full or not is_docs_only else []),
        "migration": "full-cycle"
        if full
        else "affected-cycle"
        if any(p.startswith("backend/alembic/") for p in paths)
        else "skip",
        "builds": ["backend", "frontend"]
        if full or product_wide or layers == {"backend", "frontend"}
        else ["backend"]
        if "backend" in layers
        else ["frontend"]
        if product_fe_wide or "frontend" in layers
        else [],
        "remote_ci": "scoped-impact",
    }


def make_plan(base: str, *, force_full: bool = False) -> dict[str, Any]:
    resolved = subprocess.run(
        ["git", "rev-parse", "--verify", f"{base}^{{commit}}"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()
    changes = changed_path_modes(resolved)
    return plan_paths(
        list(changes),
        resolved,
        force_full=force_full,
        non_static_paths=frozenset(path for path, modes in changes.items() if modes != {"100644"}),
    )


def describe(plan: dict[str, Any]) -> str:
    lines = [
        f"Verification base: {plan['base']}",
        f"Tier: {plan_tier(plan)}",
        f"Mode: {plan['mode']}",
        f"Changed scopes: {', '.join(plan['changed_scopes']) or 'none'}",
        f"Affected scopes: {', '.join(plan['affected_scopes']) or 'none'}",
    ]
    lines += [f"Product reason: {reason}" for reason in plan.get("product_reasons", [])]
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
        f"Migration: {plan['migration']}",
        "Remote PR CI: docs skips product suites/builds/rehearse; affected and product-frontend "
        "run selected suites and builds; product, full and main run complete suites and both "
        "builds",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        plan = make_plan(args.base, force_full=args.full)
    except ValueError as error:
        print(f"verification impact: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    print(json.dumps(plan, sort_keys=True, indent=2) if args.json else describe(plan))


if __name__ == "__main__":
    main()
