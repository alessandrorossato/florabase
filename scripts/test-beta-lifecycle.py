#!/usr/bin/env python3
"""Real disposable Compose SIGTERM probe, including a late owned creation on shutdown."""

from __future__ import annotations

import json
import os
import signal
import sys
import tempfile
import threading
import time
from pathlib import Path

from workflow_resources import Disposable, Owner, Resources, docker


def main() -> None:
    root = Path.cwd()
    image = json.loads((root / "release/inputs.json").read_text())["base_images"]["python"]
    before = set(docker("ps", "-aq", "--no-trunc").splitlines())
    with tempfile.TemporaryDirectory(prefix="beta-signal-") as temporary:
        path = Path(temporary)
        owner = Owner.disposable("workflow-smoke", path)
        labels = owner.labels()
        config = {
            "services": {
                "job": {
                    "image": image,
                    "labels": labels,
                    "command": ["python", "-c", "import time; time.sleep(3)"],
                    "stop_grace_period": "1s",
                    "volumes": ["media:/media"],
                }
            },
            "networks": {"default": {"labels": labels}},
            "volumes": {"media": {"labels": labels}},
        }
        (path / "compose.json").write_text(json.dumps(config))
        command = [
            "docker",
            "compose",
            "--env-file",
            "/dev/null",
            "-p",
            owner.project,
            "-f",
            str(path / "compose.json"),
            "run",
            "--rm",
            "-T",
            "job",
        ]
        create = ["docker", "create"]
        for key, value in labels.items():
            create += ["--label", key + "=" + value]
        create += [image, "python", "-c", "pass"]
        wrapper = path / "creator.py"
        wrapper.write_text(
            "import signal,subprocess,sys,time\nfrom pathlib import Path\np=subprocess.Popen("
            + repr(command)
            + ")\ndef shutdown(n,f):\n subprocess.run("
            + repr(create)
            + ",check=True)\n Path("
            + repr(str(path / "late-created"))
            + ").touch()\n p.wait(timeout=15)\n raise SystemExit(143)\nsignal.signal(signal.SIGTERM,shutdown)\nwhile p.poll() is None: time.sleep(0.05)\n"
        )
        done = threading.Event()

        def interrupt() -> None:
            deadline = time.monotonic() + 30
            while not done.wait(0.05):
                if (
                    docker(
                        "ps",
                        "-q",
                        "--filter",
                        "label=io.florabase.workflow.owner=" + owner.identity,
                    )
                    or time.monotonic() > deadline
                ):
                    os.kill(os.getpid(), signal.SIGTERM)
                    return

        resources = Resources(owner)
        try:
            try:
                with Disposable(owner) as lifetime:
                    thread = threading.Thread(target=interrupt)
                    thread.start()
                    try:
                        lifetime.run([sys.executable, str(wrapper)])
                    finally:
                        done.set()
                        thread.join(timeout=2)
            except SystemExit as error:
                assert error.code == 143
            assert (path / "late-created").exists(), (
                "shutdown must actually create the late owned container"
            )
            assert not any(resources.inventory().values())
            resources.clean()
            assert before == set(docker("ps", "-aq", "--no-trunc").splitlines())
            print(
                "REAL_COMPOSE_SIGTERM_LATE_CREATION_CLEANUP_PASS foreign_inventory_unchanged=true"
            )
        finally:
            resources.clean()


if __name__ == "__main__":
    main()
