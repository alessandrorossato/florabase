"""Run with python3 -m unittest discover -s scripts -p test_ui_page.py."""

import tempfile
import unittest
from pathlib import Path

from ui_page import scaffold


class ScaffoldTests(unittest.TestCase):
    def test_both_compositions_and_no_implicit_route_or_api(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, archetype in [
                ("InventoryExample", "directory"),
                ("ActivityExample", "activity"),
            ]:
                paths = scaffold(root, name, archetype)
                self.assertEqual(len(paths), 3)
                source = paths[0].read_text()
                self.assertIn(
                    "DirectoryPage" if archetype == "directory" else "ActivityPage",
                    source,
                )
                self.assertNotIn("fetch(", source)
                self.assertFalse((root / "frontend/src/App.tsx").exists())
                before = paths[0].read_bytes()
                with self.assertRaises(FileExistsError):
                    scaffold(root, name, archetype)
                self.assertEqual(paths[0].read_bytes(), before)

    def test_symlinked_output_cannot_escape_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "frontend/src"
            source.mkdir(parents=True)
            outside = root / "outside"
            outside.mkdir()
            (source / "ui-pages").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                scaffold(root, "Escape", "directory")
            self.assertEqual(list(outside.iterdir()), [])

    def test_invalid_input_and_dry_run_do_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in [
                "../Outside",
                "/Absolute",
                "lowercase",
                "A/B",
                "A;touch",
                "A" * 65,
            ]:
                with self.assertRaises(ValueError):
                    scaffold(root, name, "directory")
            with self.assertRaises(ValueError):
                scaffold(root, "Calendar", "unimplemented")
            self.assertEqual(
                len(scaffold(root, "Inventory", "directory", dry_run=True)), 3
            )
            self.assertFalse((root / "frontend").exists())


if __name__ == "__main__":
    unittest.main()
