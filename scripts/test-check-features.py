#!/usr/bin/env python3
"""Pin the feature-graph checker's rules, including the release-scope manifest (DOC-02).

The real scripts/check-features.py runs as a subprocess against fixture graphs and manifests,
so the test covers its exit status and message, not its internals.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CHECKER = ROOT / "scripts" / "check-features.py"
REQUIRED = (
    "id",
    "category",
    "description",
    "acceptance_criteria",
    "dependencies",
    "priority",
    "status",
)
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
MANIFEST = "docs/release/scope-v1.json"


def feature(feature_id: str, **changes: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "id": feature_id,
        "category": "test",
        "description": "fixture",
        "acceptance_criteria": ["one criterion"],
        "dependencies": [],
        "priority": "P1",
        "status": "planned",
    }
    entry.update(changes)
    return entry


def graph(*features: Any) -> dict[str, Any]:
    return {"allowed_statuses": ["planned", "verified"], "features": list(features)}


def scope(document: Any, **membership: str) -> dict[str, Any]:
    """A manifest that is consistent with the graph, with the given classes replaced."""
    classes: dict[str, str] = {}
    features = document.get("features") if isinstance(document, dict) else None
    for entry in features if isinstance(features, list) else []:
        if isinstance(entry, dict) and isinstance(entry.get("id"), str):
            verified = entry.get("status") == "verified"
            classes[entry["id"]] = "baseline" if verified else "post-1.0"
    classes.update(membership)
    return {"version": 1, "release": "1.0.0", "classes": list(CLASSES), "membership": classes}


def check(
    document: Any | None,
    *,
    raw: str | None = None,
    hash_seed: str | None = None,
    manifest: Any | None = None,
    raw_manifest: str | None = None,
    arguments: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    """Run the checker; unless one is given, the manifest matches the graph."""
    env = dict(os.environ)
    if hash_seed is not None:
        env["PYTHONHASHSEED"] = hash_seed
    with tempfile.TemporaryDirectory() as directory:
        if document is not None or raw is not None:
            docs = Path(directory) / "docs"
            docs.mkdir()
            text = raw if raw is not None else json.dumps(document)
            (docs / "features.json").write_text(text, encoding="utf-8")
            if raw_manifest is None and manifest is None:
                manifest = scope(document)
            if raw_manifest != "":
                (docs / "release").mkdir()
                (Path(directory) / MANIFEST).write_text(
                    raw_manifest if raw_manifest is not None else json.dumps(manifest),
                    encoding="utf-8",
                )
        return subprocess.run(
            [sys.executable, str(CHECKER), *arguments],
            cwd=directory,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )


class CheckFeaturesTest(unittest.TestCase):
    def assert_fails(
        self, result: subprocess.CompletedProcess[str], message: str, *, prefix: bool = False
    ) -> None:
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")
        if prefix:
            self.assertTrue(result.stderr.startswith(f"feature graph: {message}"), result.stderr)
        else:
            self.assertEqual(result.stderr, f"feature graph: {message}\n")

    def test_valid_graph_passes_and_reports_the_count(self) -> None:
        result = check(graph(feature("A"), feature("B", dependencies=["A"], status="verified")))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "feature graph: 2 features valid\n")

    def test_unknown_keys_are_ignored(self) -> None:
        document = graph(feature("A", notes="anything", extra=1))
        document["priority_scheme"] = {"P1": "fixture"}
        self.assertEqual(check(document).returncode, 0)

    def test_missing_or_malformed_file_fails(self) -> None:
        # The message ends with the operating system or JSON error text.
        self.assert_fails(check(None), "cannot read docs/features.json: ", prefix=True)
        self.assert_fails(
            check(None, raw="{not json"), "cannot read docs/features.json: ", prefix=True
        )

    def test_top_level_must_be_an_object(self) -> None:
        # Today this is an uncaught AttributeError, not a checker message.
        # Only the refusal is pinned.
        for raw in ("[]", "null"):
            with self.subTest(raw=raw):
                result = check(None, raw=raw)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")

    def test_top_level_shape(self) -> None:
        for statuses in (None, "planned", ["planned", 1]):
            document = graph(feature("A"))
            document["allowed_statuses"] = statuses
            with self.subTest(statuses=statuses):
                self.assert_fails(check(document), "allowed_statuses must be a list of strings")
        document = graph()
        document["features"] = {"A": feature("A")}
        self.assert_fails(check(document), "features must be a list")
        del document["features"]
        self.assert_fails(check(document), "features must be a list")

    def test_unchecked_content_is_accepted(self) -> None:
        # Not validated today: an empty status list and the type of each acceptance criterion.
        empty = graph()
        empty["allowed_statuses"] = []
        self.assertEqual(check(empty).stdout, "feature graph: 0 features valid\n")
        self.assertEqual(check(graph(feature("A", acceptance_criteria=[1, ""]))).returncode, 0)

    def test_feature_shape_and_id(self) -> None:
        self.assert_fails(check(graph("A")), "every feature must be an object")
        for bad in (None, "", 7):
            with self.subTest(id=bad):
                self.assert_fails(
                    check(graph(feature("A", id=bad))), "every feature needs a non-empty id"
                )
        self.assert_fails(check(graph(feature("A"), feature("A"))), "duplicate feature id A")

    def test_each_required_key(self) -> None:
        for key in REQUIRED:
            if key == "id":
                continue
            entry = feature("A")
            del entry[key]
            with self.subTest(key=key):
                self.assert_fails(check(graph(entry)), f"A is missing {key}")

    def test_missing_keys_are_listed_sorted(self) -> None:
        expected = ", ".join(sorted(key for key in REQUIRED if key != "id"))
        for seed in ("0", "1", "2", "3", "4"):
            with self.subTest(seed=seed):
                result = check(graph({"id": "A"}), hash_seed=seed)
                self.assert_fails(result, f"A is missing {expected}")

    def test_status_must_be_allowed(self) -> None:
        self.assert_fails(check(graph(feature("A", status="done"))), "A has an unsupported status")

    def test_dependencies_shape(self) -> None:
        for bad in ("A", [1], None):
            with self.subTest(dependencies=bad):
                self.assert_fails(
                    check(graph(feature("A", dependencies=bad))),
                    "A dependencies must be a list of ids",
                )

    def test_acceptance_criteria_required(self) -> None:
        for bad in ([], "text", None):
            with self.subTest(criteria=bad):
                self.assert_fails(
                    check(graph(feature("A", acceptance_criteria=bad))),
                    "A needs acceptance criteria",
                )

    def test_missing_dependency(self) -> None:
        self.assert_fails(
            check(graph(feature("A", dependencies=["B"]))), "A depends on missing feature B"
        )

    def test_cycles(self) -> None:
        self.assert_fails(
            check(graph(feature("A", dependencies=["A"]))), "dependency cycle includes A"
        )
        loop = graph(
            feature("A", dependencies=["B"]),
            feature("B", dependencies=["C"]),
            feature("C", dependencies=["A"]),
        )
        self.assert_fails(check(loop), "dependency cycle includes A")

    def test_repository_graph_passes(self) -> None:
        document = json.loads((ROOT / "docs" / "features.json").read_text(encoding="utf-8"))
        result = check(document, raw_manifest=(ROOT / MANIFEST).read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_manifest_missing_or_malformed_fails(self) -> None:
        # An empty raw manifest means no file is written.
        document = graph(feature("A"))
        for raw in ("", "{not json"):
            with self.subTest(raw=raw):
                self.assert_fails(
                    check(document, raw_manifest=raw), f"cannot read {MANIFEST}: ", prefix=True
                )
        for raw in ("[]", "null"):
            with self.subTest(raw=raw):
                self.assert_fails(
                    check(document, raw_manifest=raw), "scope manifest must be an object"
                )

    def test_manifest_header(self) -> None:
        document = graph(feature("A"))
        expected = {
            "version": "scope manifest version must be 1",
            "release": "scope manifest release must be 1.0.0",
            "classes": f"scope manifest classes must be exactly {', '.join(CLASSES)}",
            "membership": "scope manifest membership must be an object",
        }
        bad_values: dict[str, tuple[Any, ...]] = {
            "version": (2, "1", True, 1.0),
            "release": ("1.0.1", 1),
            "classes": (CLASSES[:-1], [*CLASSES, "extra"], CLASSES[::-1], "baseline"),
            "membership": (["A"], "A"),
        }
        for key, message in expected.items():
            manifest = scope(document)
            del manifest[key]
            with self.subTest(key=key, value="absent"):
                self.assert_fails(check(document, manifest=manifest), message)
            for value in bad_values[key]:
                manifest[key] = value
                with self.subTest(key=key, value=value):
                    self.assert_fails(check(document, manifest=manifest), message)

    def test_every_feature_needs_a_class(self) -> None:
        document = graph(feature("A"), feature("C"), feature("B"))
        manifest = scope(document)
        del manifest["membership"]["C"]
        self.assert_fails(check(document, manifest=manifest), "scope manifest is missing C")
        manifest["membership"] = {}
        self.assert_fails(check(document, manifest=manifest), "scope manifest is missing A, B, C")

    def test_unknown_identifier_fails(self) -> None:
        document = graph(feature("A"))
        self.assert_fails(
            check(document, manifest=scope(document, Z="post-1.0", B="tooling")),
            "scope manifest names unknown feature B, Z",
        )

    def test_repeated_key_fails(self) -> None:
        document = graph(feature("A"))
        header = '"version": 1, "release": "1.0.0", "classes": ' + json.dumps(CLASSES)
        repeated = (
            '{%s, "membership": {"A": "post-1.0", "A": "post-1.0"}}' % header,
            '{%s, "membership": {"A": "tooling"}, "membership": {"A": "post-1.0"}}' % header,
        )
        for raw, key in zip(repeated, ("A", "membership")):
            with self.subTest(key=key):
                self.assert_fails(
                    check(document, raw_manifest=raw),
                    f"cannot read {MANIFEST}: duplicate key {key}",
                )

    def test_class_must_be_supported(self) -> None:
        document = graph(feature("A"))
        for bad in ("1.0", "Baseline", "", None, ["tooling"]):
            with self.subTest(release_class=bad):
                manifest = scope(document)
                manifest["membership"]["A"] = bad
                self.assert_fails(
                    check(document, manifest=manifest), "A has an unsupported release class"
                )

    def test_every_class_is_accepted(self) -> None:
        for release_class in CLASSES:
            status = "planned" if release_class == "post-1.0" else "verified"
            document = graph(feature("A", status=status))
            with self.subTest(release_class=release_class):
                result = check(document, manifest=scope(document, A=release_class))
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_status_and_class_must_agree(self) -> None:
        for status in ("planned", "in_progress", "implemented"):
            document = graph(feature("A", status=status))
            document["allowed_statuses"] = [status, "verified"]
            with self.subTest(status=status):
                self.assert_fails(
                    check(document, manifest=scope(document, A="baseline")),
                    "A is baseline but not verified",
                )
        document = graph(feature("A", status="verified"))
        self.assert_fails(
            check(document, manifest=scope(document, A="post-1.0")),
            "A is post-1.0 but verified",
        )

    def test_release_candidate_readiness(self) -> None:
        document = graph(
            feature("A"),
            feature("B", status="in_progress"),
            feature("C", status="implemented"),
            feature("D", status="verified"),
            feature("E"),
        )
        document["allowed_statuses"] = ["planned", "in_progress", "implemented", "verified"]
        manifest = scope(
            document, A="certify", B="release-work", C="certify", D="certify", E="tooling"
        )
        # Without the flag the open entries are reported and the check passes.
        result = check(document, manifest=manifest)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "feature graph: 5 features valid\n"
            "feature graph: not ready for a release candidate: A, B\n",
        )
        self.assert_fails(
            check(document, manifest=manifest, arguments=("--release-candidate",)),
            "release candidate blocked by A, B",
        )
        ready = scope(document, A="tooling", B="tooling", C="certify", D="certify", E="tooling")
        result = check(document, manifest=ready, arguments=("--release-candidate",))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "feature graph: 5 features valid\n")

    def test_graph_rules_run_before_the_manifest(self) -> None:
        self.assert_fails(
            check(graph(feature("A", status="done")), raw_manifest=""),
            "A has an unsupported status",
        )

    def test_unknown_arguments_fail(self) -> None:
        for arguments in (("--rc",), ("--release-candidate", "--release-candidate")):
            with self.subTest(arguments=arguments):
                self.assert_fails(
                    check(graph(feature("A")), arguments=arguments),
                    "usage: check-features.py [--release-candidate]",
                )


class FeatureShowTest(unittest.TestCase):
    LOOKUP = Path(__file__).resolve().with_name("feature-show.py")

    def run_lookup(
        self, document: dict[str, object], manifest: dict[str, object], *arguments: str
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs/release").mkdir(parents=True)
            (root / "docs/features.json").write_text(json.dumps(document), encoding="utf-8")
            (root / "docs/release/scope-v1.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            return subprocess.run(
                [sys.executable, str(self.LOOKUP), *arguments],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )

    def test_show_exact_and_prefix_and_missing(self) -> None:
        doc = graph(
            feature("MOBILE-001", category="mobile", status="implemented"),
            feature("MOBILE-002", category="mobile", status="in_progress", dependencies=["MOBILE-001"]),
            feature("DOCS-001", category="documentation", status="verified"),
        )
        doc["allowed_statuses"] = ["planned", "in_progress", "implemented", "verified"]
        man = scope(doc, **{"MOBILE-001": "post-1.0", "MOBILE-002": "post-1.0", "DOCS-001": "baseline"})

        exact = self.run_lookup(doc, man, "--show", "MOBILE-002")
        self.assertEqual(exact.returncode, 0, exact.stderr)
        self.assertIn("MOBILE-002 [in_progress | post-1.0 | P1 | mobile]", exact.stdout)
        self.assertIn("deps: MOBILE-001", exact.stdout)
        self.assertNotIn("MOBILE-001 [", exact.stdout)

        prefix = self.run_lookup(doc, man, "--show", "MOBILE-")
        self.assertEqual(prefix.returncode, 0, prefix.stderr)
        self.assertIn("MOBILE-001 [implemented | post-1.0 | P1 | mobile]", prefix.stdout)
        self.assertIn("MOBILE-002 [in_progress | post-1.0 | P1 | mobile]", prefix.stdout)
        self.assertNotIn("DOCS-001", prefix.stdout)

        missing = self.run_lookup(doc, man, "--show", "NOPE-999")
        self.assertEqual(missing.returncode, 1)
        self.assertIn("no feature matching 'NOPE-999'", missing.stderr)

    def test_list_all_and_by_status(self) -> None:
        doc = graph(
            feature("A-001", status="in_progress"),
            feature("B-001", status="verified"),
        )
        doc["allowed_statuses"] = ["planned", "in_progress", "implemented", "verified"]
        man = scope(doc, **{"A-001": "best-effort", "B-001": "baseline"})

        listed = self.run_lookup(doc, man, "--list", "--status", "in_progress")
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertIn("A-001", listed.stdout)
        self.assertIn("best-effort", listed.stdout)
        self.assertNotIn("B-001", listed.stdout)


if __name__ == "__main__":
    unittest.main()
