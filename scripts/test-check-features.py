#!/usr/bin/env python3
"""Pin the feature-graph checker's rules before its schema changes (DOC-02 step 1).

The real scripts/check-features.py runs as a subprocess against fixture graphs, so the test
covers its exit status and message, not its internals.
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


def check(
    document: Any | None, *, raw: str | None = None, hash_seed: str | None = None
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    if hash_seed is not None:
        env["PYTHONHASHSEED"] = hash_seed
    with tempfile.TemporaryDirectory() as directory:
        if document is not None or raw is not None:
            docs = Path(directory) / "docs"
            docs.mkdir()
            text = raw if raw is not None else json.dumps(document)
            (docs / "features.json").write_text(text, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(CHECKER)],
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
        self.assertEqual(check(document).returncode, 0)


if __name__ == "__main__":
    unittest.main()
