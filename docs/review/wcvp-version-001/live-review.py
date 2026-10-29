"""WCVP-owned Review adapter; no stop, remove, reset or foreign-resource operations."""
# ruff: noqa: T201 -- Explicit local Review CLI reports status and credential path only.

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[3]
PROJECT = "florabase-wcvp-version-001-review"
PORT = "15281"
DATABASE = "florabase_wcvp_review"
STATE = SOURCE / ".source-cache" / PROJECT
sys.path.insert(0, str(SOURCE / "scripts"))
import workflow_environment as workflow  # noqa: E402


def prepare_runtime() -> None:
    STATE.mkdir(mode=0o700, exist_ok=True)
    original = (SOURCE / "scripts/uat_fixture.py").read_text()
    replacements = {
        'r"florabase-feature-review"': f'r"{PROJECT}"',
        '"http://localhost:15174"': f'"http://localhost:{PORT}"',
        '"florabase_review"': f'"{DATABASE}"',
    }
    for before, after in replacements.items():
        assert before in original, f"Fixture identity contract changed: {before}"
        original = original.replace(before, after)
    (STATE / "uat_fixture.py").write_text(original)
    (STATE / "runtime.py").write_text(
        Path(__file__).with_name("live-runtime.py").read_text().replace("__SOURCE__", str(SOURCE))
    )


class WcvpReview(workflow.Environment):
    def __init__(self) -> None:
        # These process-local identities retain every existing ownership/seed check.
        workflow.REVIEW_PROJECT = PROJECT
        workflow.PORTS["review"] = PORT
        super().__init__(workflow.Repository(SOURCE), "review")
        self.env_source = Path("/dev/null")
        self.workflow_overlay = Path(__file__).with_name("compose.yaml")

    def environment(self) -> dict[str, str]:
        return {
            **super().environment(),
            "POSTGRES_DB": DATABASE,
            "POSTGRES_USER": DATABASE,
            "FLORABASE_DATABASE_URL": (
                f"postgresql+psycopg://{DATABASE}:local-isolated-only-password@db:5432/{DATABASE}"
            ),
        }

    def fixture(self, action: str, credentials: str | None = None) -> None:
        self.require_review_seed()
        prepare_runtime()
        import subprocess

        subprocess.run(
            self.command(
                "run",
                "--rm",
                "-T",
                "--no-deps",
                "--volume",
                f"{STATE}:/review:ro",
                "--env",
                "FLORABASE_WORKFLOW_MODE=review",
                "--env",
                f"FLORABASE_REVIEW_PROJECT={PROJECT}",
                "--env",
                f"FLORABASE_REVIEW_SOURCE={SOURCE}",
                "backend",
                "python",
                "/review/runtime.py",
                action,
            ),
            env=self.environment(),
            input=credentials,
            text=True,
            check=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["up", "seed", "status", "check"])
    args = parser.parse_args()
    environment = WcvpReview()
    if args.action == "up":
        environment.up()
        return
    environment.validate()
    environment.require_owner()
    if args.action == "status":
        environment.status()
        environment.fixture("check")
    elif args.action == "check":
        environment.fixture("check")
    else:
        prepare_runtime()
        path = STATE / "credentials.json"
        if not path.exists():
            environment.require_review_seed()
            owners = environment.compose(
                "exec",
                "-T",
                "db",
                "psql",
                "-U",
                DATABASE,
                "-d",
                DATABASE,
                "-X",
                "-qAt",
                "-c",
                "SELECT count(*) FROM users",
                capture=True,
            )
            if owners.strip() != "0":
                raise workflow.WorkflowError(
                    "Credentials missing for retained owner; explicit recovery required"
                )
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w") as stream:
                json.dump({"login": "wcvp-review", "password": secrets.token_urlsafe(24)}, stream)
        environment.fixture("seed", path.read_text())
        print(f"Synthetic owner credential reference (do not publish): {path}")


if __name__ == "__main__":
    main()
