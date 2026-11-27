#!/usr/bin/env python3
"""Regression tests for the scoped offline documentation link and structure checker."""

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


def make_valid_docs_tree(root: Path) -> None:
    """Create a minimal valid docs/ layout passing all structure rules."""
    (root / "docs/operate").mkdir(parents=True)
    (root / "docs/develop/workflow").mkdir(parents=True)
    (root / "docs/archive/OLD-001").mkdir(parents=True)

    (root / "docs/README.md").write_text("# Docs\n", encoding="utf-8")
    (root / "docs/agent-map.md").write_text("# Agent map\n", encoding="utf-8")
    (root / "docs/progress.md").write_text("# Progress\n", encoding="utf-8")
    (root / "docs/features.json").write_text("{}\n", encoding="utf-8")

    # Minimal living target for all tombstones
    (root / "docs/operate/installation.md").write_text(
        "# Install\n\n> Summary: Install guide.\n", encoding="utf-8"
    )
    (root / "docs/operate/README.md").write_text(
        "# Operate\n\n- [Install](installation.md)\n", encoding="utf-8"
    )
    for tombstone in checker.TOMBSTONES:
        (root / tombstone).write_text(
            "# Moved\n\nSee [operate/installation.md](operate/installation.md).\n",
            encoding="utf-8",
        )

    # Split guide parent + child
    (root / "docs/develop/development-workflow.md").write_text(
        "# Workflow\n\n> Summary: Workflow index.\n\n- [Batches](workflow/batches.md)\n",
        encoding="utf-8",
    )
    (root / "docs/develop/README.md").write_text(
        "# Develop\n\n- [Workflow](development-workflow.md)\n", encoding="utf-8"
    )
    (root / "docs/develop/workflow/batches.md").write_text(
        "# Batches\n\n> Summary: Batch workflow.\n", encoding="utf-8"
    )

    # Archived doc (exempt from orphan/summary/size rules)
    (root / "docs/archive/OLD-001/handoff.md").write_text(
        "# Old handoff without summary\n" + ("x" * (45 * 1024)), encoding="utf-8"
    )


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


class Structure(unittest.TestCase):
    def test_valid_tree_passes_and_exempts_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_valid_docs_tree(root)
            errors, warnings = checker.check_structure(root, ())
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])

    def test_unexpected_top_level_doc_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_valid_docs_tree(root)
            (root / "docs/stray-guide.md").write_text("# Stray\n", encoding="utf-8")
            errors, _ = checker.check_structure(root, ())
            self.assertEqual(len(errors), 1)
            self.assertIn("docs/stray-guide.md", errors[0])
            self.assertIn("put it in a subfolder or docs/archive/<FEATURE-ID>/", errors[0])

    def test_orphan_living_doc_and_split_child_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_valid_docs_tree(root)
            (root / "docs/operate/unlisted.md").write_text(
                "# Unlisted\n\n> Summary: Orphan.\n", encoding="utf-8"
            )
            (root / "docs/develop/workflow/unlisted-split.md").write_text(
                "# Unlisted split\n\n> Summary: Orphan split.\n", encoding="utf-8"
            )
            errors, _ = checker.check_structure(root, ())
            self.assertEqual(len(errors), 2)
            self.assertTrue(any("docs/operate/unlisted.md" in e and "orphan" in e for e in errors))
            self.assertTrue(
                any("docs/develop/workflow/unlisted-split.md" in e and "orphan" in e for e in errors)
            )

    def test_missing_summary_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_valid_docs_tree(root)
            (root / "docs/operate/installation.md").write_text(
                "# Install\n\nNo summary line here.\n", encoding="utf-8"
            )
            errors, _ = checker.check_structure(root, ())
            self.assertEqual(len(errors), 1)
            self.assertIn("missing one-line '> Summary: ...'", errors[0])

    def test_size_warning_does_not_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_valid_docs_tree(root)
            (root / "docs/operate/installation.md").write_text(
                "# Install\n\n> Summary: Huge guide.\n\n" + ("a" * (41 * 1024)),
                encoding="utf-8",
            )
            errors, warnings = checker.check_structure(root, ())
            self.assertEqual(errors, [])
            self.assertEqual(len(warnings), 1)
            self.assertIn("docs/operate/installation.md", warnings[0])

    def test_missing_or_broken_tombstone_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_valid_docs_tree(root)
            (root / "docs/mobile.md").unlink()
            (root / "docs/security.md").write_text(
                "# Moved\n\nSee [missing](operate/missing.md).\n", encoding="utf-8"
            )
            errors, _ = checker.check_structure(root, ())
            self.assertEqual(len(errors), 2)
            self.assertTrue(any("docs/mobile.md: missing required tombstone" in e for e in errors))
            self.assertTrue(
                any("docs/security.md: tombstone has no valid local target link" in e for e in errors)
            )


if __name__ == "__main__":
    unittest.main()
