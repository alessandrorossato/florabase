"""Small, Docker-free checks for the isolated Review adapter."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location(
    "media_review", Path(__file__).with_name("live-review.py")
)
assert SPEC is not None
assert SPEC.loader is not None
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)


class ReviewTests(unittest.TestCase):
    def test_foreign_host_identities_refuse_before_docker(self) -> None:
        environment = review.MediaReview()
        for role, project in (
            ("dev", review.PROJECT),
            ("review", "florabase-feature-review"),
            ("review", "florabase-ui-audit-bc88"),
        ):
            with self.subTest(role=role, project=project):
                environment.role, environment.project = role, project
                try:
                    environment.require_review_seed()
                except review.workflow.WorkflowError:
                    pass
                else:
                    raise AssertionError("Foreign host environment accepted")

    def test_fixture_specialization_preserves_canonical_source(self) -> None:
        original = (review.SOURCE / "scripts/uat_fixture.py").read_bytes()
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(review, "STATE", Path(directory)),
        ):
            review.prepare_runtime()
            adapted = (Path(directory) / "uat_fixture.py").read_text()
            assert f'r"{review.PROJECT}"' in adapted
            assert f'"{review.DATABASE}"' in adapted
            assert '"http://localhost:15280"' in adapted
            assert (Path(directory) / "review_dataset_v5.py").read_bytes() == (
                review.SOURCE / "scripts/review_dataset_v5.py"
            ).read_bytes()
            compile(adapted, "adapted-v4", "exec")
        assert (review.SOURCE / "scripts/uat_fixture.py").read_bytes() == original

    def test_missing_credentials_for_retained_owner_refuse_without_replacement(self) -> None:
        environment = Mock()
        environment.compose.return_value = "1"
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(review, "STATE", Path(directory)),
            patch.object(review, "MediaReview", return_value=environment),
            patch.object(review, "prepare_runtime"),
            patch.object(sys, "argv", ["live-review.py", "seed"]),
        ):
            try:
                review.main()
            except review.workflow.WorkflowError:
                pass
            else:
                raise AssertionError("Retained owner credentials replaced")
            assert not (Path(directory) / "credentials.json").exists()
            environment.fixture.assert_not_called()

    def test_fresh_owner_credentials_are_private_and_not_printed(self) -> None:
        environment = Mock()
        environment.compose.return_value = "0"
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(review, "STATE", Path(directory)),
            patch.object(review, "MediaReview", return_value=environment),
            patch.object(review, "prepare_runtime"),
            patch.object(sys, "argv", ["live-review.py", "seed"]),
            patch("builtins.print") as output,
        ):
            review.main()
            path = Path(directory) / "credentials.json"
            credentials = json.loads(path.read_text())
            assert path.stat().st_mode & 0o777 == 0o600
            assert credentials["login"] == "media-review"
            assert credentials["password"] not in str(output.call_args)
            environment.fixture.assert_called_once_with("seed", path.read_text())


if __name__ == "__main__":
    unittest.main()
