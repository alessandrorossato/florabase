"""LINEAGE-003-owned isolated Review on 15176; canonical Review guards with its own identities.

Runs beside Feature Review (15174) without touching it: own Compose project, database, media,
dependency volumes and network. Up, seed, status, stop and guarded remove reuse the canonical
workflow implementation unchanged; only the process-local identities differ.
"""
# ruff: noqa: T201 -- Explicit local Review CLI reports status and the credential path only.

from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[3]
PROJECT = "florabase-lineage-003-review"
PORT = "15176"
DATABASE = "florabase_lineage_review"
STATE = SOURCE / ".source-cache" / PROJECT  # Ignored by Git; credentials stay local (0600).
sys.path.insert(0, str(SOURCE / "scripts"))
import workflow_environment as workflow  # noqa: E402

FIXTURE = "scripts/uat_fixture.py"
# The canonical fixture's identity guard names Feature Review; this copy names only this Review.
IDENTITIES = {
    'r"florabase-feature-review"': f'r"{PROJECT}"',
    '"http://localhost:15174"': f'"http://localhost:{PORT}"',
    '"florabase_review"': f'"{DATABASE}"',
}


def prepare_fixture() -> Path:
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    text = (SOURCE / FIXTURE).read_text()
    for before, after in IDENTITIES.items():
        if before not in text:
            raise workflow.WorkflowError(f"fixture identity contract changed: {before}")
        text = text.replace(before, after)
    path = STATE / "uat_fixture.py"
    path.write_text(text)
    return path


class LineageReview(workflow.Environment):
    def __init__(self) -> None:
        # Process-local identities; every ownership, migration and seed check stays canonical.
        workflow.REVIEW_PROJECT = PROJECT
        workflow.PORTS["review"] = PORT
        super().__init__(workflow.Repository(SOURCE), "review")
        self.env_source = Path("/dev/null")

    def environment(self) -> dict[str, str]:
        return {
            **super().environment(),
            "POSTGRES_DB": DATABASE,
            "POSTGRES_USER": DATABASE,
            "FLORABASE_DATABASE_URL": (
                f"postgresql+psycopg://{DATABASE}:local-isolated-only-password@db:5432/{DATABASE}"
            ),
        }

    def command(self, *args: str) -> list[str]:
        # Canonical seed mounts the fixture by path; substitute the identity-specialized copy.
        canonical = f"{self.source / FIXTURE}:/review/uat_fixture.py:ro"
        local = f"{STATE / 'uat_fixture.py'}:/review/uat_fixture.py:ro"
        return super().command(*(local if arg == canonical else arg for arg in args))

    def bootstrap(self) -> Path:
        """Create the synthetic owner once, with a generated local-only password."""
        self.validate()
        self.require_owner()
        STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = STATE / "credentials.json"
        if path.exists():
            return path
        owners = self.compose(
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
            raise workflow.WorkflowError("credentials missing for an existing owner; refused")
        login, password = "lineage-review", secrets.token_urlsafe(24)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            json.dump({"login": login, "password": password}, stream)
        subprocess.run(
            [
                *self.command("run", "--rm", "-T", "--no-deps", "backend"),
                "python",
                "-m",
                "florabase.auth.bootstrap",
                login,
                "--display-name",
                "Lineage Review (synthetic)",
                "--password-stdin",
            ],
            input=(password + "\n").encode(),
            env=self.environment(),
            check=True,
        )
        return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["up", "seed", "status", "stop", "remove"])
    action = parser.parse_args().action
    environment = LineageReview()
    try:
        if action != "status":
            if action != "stop":
                helper = SOURCE / "scripts/feature_worktree.py"
                workflow.run([sys.executable, str(helper), "require-writer"])
            with workflow.machine_lock(PROJECT, f"{PROJECT} lifecycle"):
                if action == "up":
                    environment.up()
                elif action == "seed":
                    prepare_fixture()
                    path = environment.bootstrap()
                    environment.seed()
                    print(f"Synthetic owner credential file (do not publish): {path}")
                else:
                    environment.stop(
                        remove=action == "remove",
                        confirm=os.environ.get("CONFIRM_REMOVE_REVIEW", ""),
                    )
        else:
            environment.status()
    except (workflow.WorkflowError, workflow.ResourceError, subprocess.CalledProcessError) as error:
        print(f"lineage review: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
