#!/usr/bin/env python3
"""Hash-verified isolated release tools; works without system pip or ensurepip."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import venv
from pathlib import Path

from workflow_resources import FileLock


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    contract = (
        root / "release"
        if (root / "release/requirements.txt").exists()
        else Path(__file__).resolve().parent
    )
    lock = contract / "requirements.txt"
    bootstrap = json.loads((contract / "bootstrap.json").read_text())
    identity = hashlib.sha256(
        lock.read_bytes() + json.dumps(bootstrap).encode() + sys.version.encode()
    ).hexdigest()[:16]
    cache = (
        Path(os.environ.get("FLORABASE_RELEASE_CACHE", tempfile.gettempdir()))
        / f"florabase-release-tools-{os.getuid()}-{identity}"
    )
    cache.mkdir(parents=True, exist_ok=True)
    with FileLock(cache / "lock", "release dependency preparation"):
        wheel = cache / "pip.whl"
        if not wheel.exists():
            if os.environ.get("FLORABASE_RELEASE_OFFLINE") == "1":
                raise RuntimeError(
                    "offline release tooling unavailable: verified pip wheel missing"
                )
            with urllib.request.urlopen(bootstrap["url"], timeout=30) as response:
                data = response.read()
            if hashlib.sha256(data).hexdigest() != bootstrap["sha256"]:
                raise RuntimeError("pip bootstrap hash mismatch")
            wheel.write_bytes(data)
        if hashlib.sha256(wheel.read_bytes()).hexdigest() != bootstrap["sha256"]:
            raise RuntimeError("cached pip bootstrap hash mismatch")
        environment = cache / "venv"
        if not (environment / "bin/python").exists():
            venv.EnvBuilder(with_pip=False).create(environment)
        python = str(environment / "bin/python")
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in {"PYTHONPATH", "PYTHONHOME"} and not k.startswith("PIP_")
        }
        env.update(
            PYTHONPATH=str(wheel),
            PIP_CACHE_DIR=str(cache / "pip-cache"),
            PIP_DISABLE_PIP_VERSION_CHECK="1",
        )
        command = [
            python,
            "-m",
            "pip",
            "--isolated",
            "install",
            "--require-hashes",
            "--only-binary=:all:",
            "--cache-dir",
            str(cache / "pip-cache"),
            "--find-links",
            str(cache / "wheels"),
            "-r",
            str(lock),
        ]
        wheels = cache / "wheels"
        wheels.mkdir(exist_ok=True)
        if os.environ.get("FLORABASE_RELEASE_OFFLINE") != "1":
            subprocess.run(
                [
                    python,
                    "-m",
                    "pip",
                    "--isolated",
                    "download",
                    "--require-hashes",
                    "--only-binary=:all:",
                    "--cache-dir",
                    str(cache / "pip-cache"),
                    "--dest",
                    str(wheels),
                    "-r",
                    str(lock),
                ],
                env=env,
                check=True,
            )
        command.append("--no-index")
        subprocess.run(command, env=env, check=True)
    env.pop("PYTHONPATH", None)
    env["PATH"] = str(environment / "bin") + os.pathsep + env.get("PATH", "")
    os.execve(python, [python, *sys.argv[1:]], env)


if __name__ == "__main__":
    main()
