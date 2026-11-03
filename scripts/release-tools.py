#!/usr/bin/env python3
"""Hash-verified isolated release tools; works without system pip or ensurepip."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import urllib.request
import venv
from pathlib import Path

from workflow_resources import FileLock


def secure_cache(cache: Path) -> None:
    """Refuse pre-planted/shared trees before touching locks or executing cached Python.

    Other users may write /tmp but cannot replace children of an owned 0700 directory.
    Same-UID processes are trusted, as with the checked-out release tools themselves.
    """
    for parent in reversed(cache.absolute().parents):
        if not parent.exists():
            parent.mkdir(mode=0o700)
        info = parent.lstat()
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid not in {0, os.getuid()}
            or (info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX)
        ):
            raise ValueError("unsafe release cache ancestor: " + str(parent))
    cache.mkdir(mode=0o700, exist_ok=True)
    info = cache.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("unsafe release cache: require an owned, private real directory")
    for directory, dirs, files in os.walk(cache, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            info = path.lstat()
            if info.st_uid != os.getuid():
                raise ValueError("unsafe release cache owner: " + str(path))
            if stat.S_ISLNK(info.st_mode):
                resolved = path.resolve(strict=True)
                interpreter_link = (
                    path.parent == cache / "venv/bin"
                    and path.name.startswith("python")
                    and resolved == Path(sys.executable).resolve()
                )
                if not interpreter_link and not resolved.is_relative_to(cache.resolve()):
                    raise ValueError("unsafe release cache symlink: " + str(path))
            elif (
                not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode))
                or info.st_mode & 0o022
            ):
                raise ValueError("unsafe release cache entry: " + str(path))


def main() -> None:
    os.umask(0o077)
    root = Path(__file__).resolve().parents[1]
    contract = (
        root / "release"
        if (root / "release/requirements.txt").exists()
        else Path(__file__).resolve().parent
    )
    lock = contract / "requirements.txt"
    bootstrap = json.loads((contract / "bootstrap.json").read_text())
    identity = hashlib.sha256(
        lock.read_bytes() + json.dumps(bootstrap).encode() + sys.version.encode() + b"private-v2"
    ).hexdigest()[:16]
    cache = (
        Path(os.environ.get("FLORABASE_RELEASE_CACHE", tempfile.gettempdir()))
        / f"florabase-release-tools-{os.getuid()}-{identity}"
    )
    secure_cache(cache)
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
        env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "PIP_"))}
        env.update(
            PIP_CACHE_DIR=str(cache / "pip-cache"),
            PIP_DISABLE_PIP_VERSION_CHECK="1",
        )
        pip = [
            python,
            "-I",
            "-c",
            "import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module('pip',run_name='__main__')",
            str(wheel),
        ]
        command = [
            *pip,
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
                    *pip,
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
    secure_cache(cache)
    env["PATH"] = str(environment / "bin") + os.pathsep + env.get("PATH", "")
    os.execve(python, [python, "-E", "-s", *sys.argv[1:]], env)


if __name__ == "__main__":
    main()
