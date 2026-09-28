"""Isolation guard tests; no Docker or application database is contacted."""

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "perf_measure", Path(__file__).with_name("measure.py")
)
measure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measure)


class IsolationTests(unittest.TestCase):
    def config(self, **service_changes):
        services = {name: {"tmpfs": ["/disposable"]} for name in ("db", "backend")}
        services["db"].update(service_changes)
        return {"name": "florabase-perf", "services": services}

    def test_rejects_durable_volumes_before_starting(self):
        import json

        with patch.object(
            measure,
            "compose",
            return_value=json.dumps(self.config(volumes=[{"source": "operator_data"}])),
        ) as compose:
            with self.assertRaisesRegex(RuntimeError, "isolation"):
                measure.start()
            self.assertEqual(compose.call_count, 1)

    def test_rejects_published_database_before_starting(self):
        import json

        with patch.object(
            measure, "compose", return_value=json.dumps(self.config(ports=[5432]))
        ) as compose:
            with self.assertRaisesRegex(RuntimeError, "isolation"):
                measure.start()
            self.assertEqual(compose.call_count, 1)

    def test_rejects_existing_project_without_replacing_data(self):
        import json

        with patch.object(
            measure,
            "compose",
            side_effect=[json.dumps(self.config()), "existing-container"],
        ) as compose:
            with self.assertRaisesRegex(RuntimeError, "already exist"):
                measure.start()
            self.assertEqual(compose.call_count, 2)
            compose.assert_called_with("ps", "--all", "-q")

    def test_rejects_wrong_project(self):
        import json

        config = self.config()
        config["name"] = "florabase"
        with patch.object(
            measure, "compose", return_value=json.dumps(config)
        ) as compose:
            with self.assertRaisesRegex(RuntimeError, "Unexpected project"):
                measure.start()
            self.assertEqual(compose.call_count, 1)


if __name__ == "__main__":
    unittest.main()
