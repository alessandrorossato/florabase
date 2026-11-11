"""Docker-free checks for the isolated LINEAGE-003 Review adapter: python3 test-review.py."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "lineage_review", Path(__file__).with_name("review.py")
)
assert SPEC is not None and SPEC.loader is not None
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)


class ReviewTests(unittest.TestCase):
    def test_fixture_copy_names_only_this_review(self) -> None:
        canonical = (review.SOURCE / review.FIXTURE).read_text()
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(review, "STATE", Path(directory)),
        ):
            copy = review.prepare_fixture().read_text()
        for before, after in review.IDENTITIES.items():
            self.assertNotIn(before, copy)
            self.assertIn(after, copy)
        self.assertEqual(copy.count("\n"), canonical.count("\n"))
        self.assertEqual((review.SOURCE / review.FIXTURE).read_text(), canonical)

    def test_identities_and_mount_substitution_never_name_feature_review(self) -> None:
        environment = review.LineageReview()
        self.assertEqual(environment.project, review.PROJECT)
        self.assertEqual(environment.url, f"http://localhost:{review.PORT}")
        self.assertEqual(environment.environment()["POSTGRES_DB"], review.DATABASE)
        mount = f"{environment.source / review.FIXTURE}:/review/uat_fixture.py:ro"
        command = environment.command("run", "--volume", mount, "backend")
        self.assertIn(f"{review.STATE / 'uat_fixture.py'}:/review/uat_fixture.py:ro", command)
        self.assertNotIn(mount, command)
        self.assertNotIn("florabase-feature-review", command)
        # Guarded removal requires this exact project, never Feature Review's name.
        with self.assertRaises(review.workflow.WorkflowError):
            environment.stop(remove=True, confirm="florabase-feature-review")


if __name__ == "__main__":
    unittest.main()
