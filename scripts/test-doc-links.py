#!/usr/bin/env python3
"""Regression tests for the scoped offline documentation link checker."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "doc_links", Path(__file__).with_name("check-doc-links.py")
)
assert spec and spec.loader
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class Links(unittest.TestCase):
    def test_targets_fragments_and_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "target.md").write_text("# Hello world\n# Hello world\n")
            (root / "a.md").write_text(
                "[ok](target.md#hello-world-1)\n[web](https://example.com/x)\n```\n[ignored](missing)\n```\n[bad](target.md#absent)\n[missing](nope.md)\n"
            )
            errors = checker.check(root, ("a.md", "absent.md"))
            self.assertEqual(len(errors), 3)
            self.assertTrue(any("missing anchor" in error for error in errors))
            self.assertTrue(any("missing local target" in error for error in errors))
            self.assertTrue(any("missing document" in error for error in errors))

    def test_reference_parentheses_and_code_heading(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a (b).md").write_text("# `Café` plant\n# `Café` plant\n")
            (root / "a.md").write_text(
                "[one][ref] [two](<a (b).md#café-plant-1>) `[ignored](missing)`\n[undefined][literal]\n[ref]: <a (b).md#café-plant>\n"
            )
            self.assertEqual(checker.check(root, ("a.md",)), [])

    def test_fence_info_and_slug_collisions(self):
        text = "# Name\n# Name-1\n# Name\n```\n```python\n[ignored](missing)\n```\n"
        self.assertEqual(checker.anchors(text), {"name", "name-1", "name-2"})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.md").write_text(text)
            self.assertEqual(checker.check(root, ("a.md",)), [])

    def test_escape_and_percent_encoded_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "space name.md").write_text("# A heading\n")
            (root / "a.md").write_text("[ok](space%20name.md#a-heading)\n[bad](../outside)\n")
            self.assertEqual(len(checker.check(root, ("a.md",))), 1)


if __name__ == "__main__":
    unittest.main()
