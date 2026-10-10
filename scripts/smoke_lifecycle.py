#!/usr/bin/env python3
"""Attach registered positive ownership/cleanup to existing disposable real workflow fixtures."""

from __future__ import annotations

import json
import tempfile
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any

from workflow_environment import Environment
from workflow_resources import Disposable, Owner


def overlay(config: dict[str, Any], owner: Owner) -> dict[str, Any]:
    labels = {
        key: value for key, value in owner.labels().items() if key != "com.docker.compose.project"
    }
    result: dict[str, Any] = {"services": {}, "networks": {}, "volumes": {}}
    for name, service in config["services"].items():
        value: dict[str, Any] = {"labels": labels}
        if service.get("build"):
            value["build"] = {"labels": owner.labels()}
        result["services"][name] = value
    for kind in ("networks", "volumes"):
        for name, value in config.get(kind, {}).items():
            if value.get("external"):
                raise ValueError("disposable smoke may not mount external state")
            result[kind][name] = {"labels": labels}
    return result


class SmokeLifecycle(AbstractContextManager["SmokeLifecycle"]):
    def __init__(self, env: Environment) -> None:
        self.env = env
        self.owner = Owner.smoke_fixture(env.project, env.source)
        self.lifetime = Disposable(self.owner)
        self.temporary: tempfile.TemporaryDirectory[str] | None = None

    def __enter__(self) -> SmokeLifecycle:
        self.lifetime.__enter__()  # BEFORE configuration/bootstrap/build creates any resources.
        try:
            config = json.loads(self.env.compose("config", "--format", "json", capture=True))
            self.temporary = tempfile.TemporaryDirectory(prefix="florabase-smoke-ownership-")
            path = Path(self.temporary.name) / "ownership.json"
            path.write_text(json.dumps(overlay(config, self.owner)))
            self.env.workflow_overlay = path
        except BaseException:
            self.__exit__()
            raise
        return self

    def __exit__(self, *exception: object) -> None:
        try:
            self.lifetime.__exit__(*exception)
        finally:
            self.env.workflow_overlay = None
            if self.temporary:
                self.temporary.cleanup()
