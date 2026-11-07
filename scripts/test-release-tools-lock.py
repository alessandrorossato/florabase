#!/usr/bin/env python3
"""Release-tool bootstrap regressions: clean prepare and a complete hashed dependency lock.

Standard library only. Needs network access like release-tools itself. It never relaxes hash
checking: the real bootstrap runs from an empty cache, then the lock is checked for closure.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from email.parser import Parser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "release/requirements.txt"
SUPPORTED_PYTHONS = ((3, 11), (3, 12), (3, 13), (3, 14))  # 3.12 is the GitHub Actions runner


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def locked() -> dict[str, tuple[str, list[str]]]:
    """name -> (version, hashes) from the lock; every entry must be pinned with hashes."""
    result: dict[str, tuple[str, list[str]]] = {}
    for block in re.split(r"\n(?=\S)", LOCK.read_text().strip()):
        head = block.splitlines()[0]
        match = re.fullmatch(r"([A-Za-z0-9._-]+)==([A-Za-z0-9.+!_-]+) \\", head)
        hashes = re.findall(r"--hash=sha256:([0-9a-f]{64})", block)
        if match is None or not hashes:
            raise AssertionError("lock entry must be name==version with sha256 hashes: " + head)
        result[normalize(match.group(1))] = (match.group(2), hashes)
    return result


def prepare(cache: Path) -> tuple[Path, Path]:
    """Run the real bootstrap from an empty private cache; return the venv python and cache dir."""
    environment = {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "PIP_"))}
    environment["FLORABASE_RELEASE_CACHE"] = str(cache)
    environment.pop("FLORABASE_RELEASE_OFFLINE", None)
    done = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/release-tools.py"),
            "-c",
            "import sys, jsonschema, referencing, attrs, rpds; print(sys.executable)",
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        raise AssertionError("release tool bootstrap failed:\n" + done.stdout + done.stderr)
    python = Path(done.stdout.strip().splitlines()[-1])
    return python, next(cache.glob("florabase-release-tools-*"))


def marker_environment(version: tuple[int, int]) -> dict[str, str]:
    major, minor = version
    return {
        "python_version": f"{major}.{minor}",
        "python_full_version": f"{major}.{minor}.0",
        "implementation_name": "cpython",
        "platform_python_implementation": "CPython",
        "sys_platform": "linux",
        "platform_system": "Linux",
        "os_name": "posix",
        "platform_machine": "x86_64",
        "extra": "",
    }


class ReleaseToolsLockTests(unittest.TestCase):
    pip_wheel: Path
    wheels: Path
    python: Path
    tmp: tempfile.TemporaryDirectory[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cache = Path(cls.tmp.name) / "empty-cache"
        cache.mkdir(mode=0o700)
        cls.python, prepared = prepare(cache)
        cls.pip_wheel = prepared / "pip.whl"
        cls.wheels = prepared / "wheels"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_clean_prepare_installs_the_hashed_lock(self) -> None:
        self.assertTrue(self.python.exists())
        self.assertIn("florabase-release-tools-", str(self.python))

    def test_lock_entries_are_pinned_and_hashed(self) -> None:
        entries = locked()
        for name in ("attrs", "jsonschema", "jsonschema-specifications", "referencing", "rpds-py"):
            self.assertIn(name, entries)
        text = LOCK.read_text()
        for forbidden in ("--no-deps", "--trusted-host", "--index-url", "git+", ">=", "<="):
            self.assertNotIn(forbidden, text)

    def test_every_requirement_of_every_locked_wheel_is_locked_for_supported_pythons(self) -> None:
        sys.path.insert(0, str(self.pip_wheel))
        try:
            from pip._vendor.packaging.markers import Marker
            from pip._vendor.packaging.requirements import Requirement
            from pip._vendor.packaging.version import Version
        finally:
            sys.path.remove(str(self.pip_wheel))
        entries = locked()
        wheels = sorted(self.wheels.glob("*.whl"))
        self.assertGreaterEqual(len(wheels), len(entries))
        checked = 0
        for wheel in wheels:
            with zipfile.ZipFile(wheel) as archive:
                metadata_name = next(
                    n for n in archive.namelist() if n.endswith(".dist-info/METADATA")
                )
                metadata: Any = Parser().parsestr(archive.read(metadata_name).decode())
            for line in metadata.get_all("Requires-Dist") or []:
                requirement = Requirement(line)
                for version in SUPPORTED_PYTHONS:
                    marker: Marker | None = requirement.marker
                    if marker is not None and not marker.evaluate(marker_environment(version)):
                        continue
                    with self.subTest(wheel=wheel.name, requires=line, python=version):
                        name = normalize(requirement.name)
                        self.assertIn(name, entries, "transitive dependency missing from lock")
                        pinned = Version(entries[name][0])
                        self.assertTrue(requirement.specifier.contains(pinned, prereleases=True))
                        checked += 1
        self.assertGreater(checked, 0)

    def test_marker_conditional_dependency_is_covered_on_python_312(self) -> None:
        """referencing needs typing-extensions below Python 3.13: the first release failure."""
        sys.path.insert(0, str(self.pip_wheel))
        try:
            from pip._vendor.packaging.markers import Marker
        finally:
            sys.path.remove(str(self.pip_wheel))
        referencing = next(self.wheels.glob("referencing-*.whl"))
        with zipfile.ZipFile(referencing) as archive:
            name = next(n for n in archive.namelist() if n.endswith(".dist-info/METADATA"))
            text = archive.read(name).decode()
        match = re.search(r"Requires-Dist: typing-extensions[^;\n]*; (.+)", text)
        self.assertIsNotNone(match)
        assert match is not None
        self.assertTrue(Marker(match.group(1)).evaluate(marker_environment((3, 12))))
        self.assertIn("typing-extensions", locked())


if __name__ == "__main__":
    unittest.main()
