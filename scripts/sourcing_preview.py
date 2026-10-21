#!/usr/bin/env python3
"""Persistent, per-worktree Sourcing Preview for visual review of the Sourcing slice.

This environment reuses the supported Review runtime (compose.yaml + compose.dev.yaml +
compose.review.yaml) plus a tiny `compose.sourcing.yaml` endpoint overlay, but owns an
independent project, network, database, media volume and dependency volume, and publishes
only `127.0.0.1:15175`. It never reads, starts, stops, removes or resets Feature Review
(15174), DEV (5173), UAT (15174), Stable Preview (15173) or production.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

from workflow_environment import (
    SOURCING_PROJECT,
    Environment,
    Repository,
    WorkflowError,
    code_heads,
    migration_graph,
    run,
)

# Source-independent runtime images; live backend/frontend source is bind-mounted by compose.dev.
IMAGES = ("backend", "frontend")


class SourcingPreview(Environment):
    def __init__(self, repository: Repository) -> None:
        super().__init__(repository, "sourcing")

    def require_context(self) -> None:
        """Refuse to run Sourcing Preview from the primary checkout or an unexpected project."""
        if (
            self.repository.source == self.repository.primary
            or self.repository.metadata == self.repository.common
        ):
            raise WorkflowError("Sourcing Preview requires the current linked feature worktree")
        if self.project != SOURCING_PROJECT:
            raise WorkflowError("unexpected Sourcing Preview project; refused")
        self.repository.initialize()

    def project_images(self) -> dict[str, str]:
        return {service: f"{self.project}-{service}-development" for service in IMAGES}

    def missing_images(self) -> list[str]:
        missing: list[str] = []
        for service, image in self.project_images().items():
            try:
                run(["docker", "image", "inspect", image], capture=True)
            except WorkflowError:
                missing.append(service)
        return missing

    def dataset_status(self, *, capture: bool = False) -> str:
        program = "\n".join(
            [
                "import json",
                "from sqlalchemy import func, select",
                "from sqlalchemy.orm import Session",
                "from florabase.db.session import get_engine",
                "from florabase.orders.model import Order",
                "from florabase.seed_lots.model import SeedLot",
                "from florabase.suppliers.model import Supplier",
                "with Session(get_engine()) as database:",
                "    counts = {",
                "        'suppliers': database.scalar(select(func.count()).select_from(Supplier)),",
                "        'suppliers_retired': database.scalar(",
                "            select(func.count()).select_from(Supplier).where(",
                "                Supplier.retired_at.is_not(None))),",
                "        'orders': database.scalar(select(func.count()).select_from(Order)),",
                "        'seed_lots': database.scalar(select(func.count()).select_from(SeedLot)),",
                "        'seed_lots_with_supplier': database.scalar(",
                "            select(func.count()).select_from(SeedLot).where(",
                "                SeedLot.supplier_id.is_not(None))),",
                "        'seed_lots_with_order': database.scalar(",
                "            select(func.count()).select_from(SeedLot).where(",
                "                SeedLot.order_id.is_not(None))),",
                "    }",
                "    print(json.dumps(counts, sort_keys=True))",
            ]
        )
        return self.compose("exec", "-T", "backend", "python", "-c", program, capture=capture)

    def up(self, *, rebuild: bool = False) -> None:
        self.require_context()
        self.validate()
        self.require_owner()
        missing = self.missing_images()
        if rebuild or missing:
            reason = "explicit --rebuild" if rebuild else f"missing images: {','.join(missing)}"
            print(f"Building Sourcing Preview images ({reason}); shared BuildKit cache is reused.")
            self.compose("build")
        else:
            print("Sourcing Preview images present; skipping rebuild (pass --rebuild to force).")
        self.start_database()
        self.compose("run", "--rm", "-T", "--no-deps", "dev-state-init")
        self.upgrade()
        self.compose("up", "-d", "--wait", "--wait-timeout", "180")
        print("SOURCING PREVIEW READY")
        self.status()

    def bootstrap_owner(
        self, login: str, password: str | None, *, display_name: str | None = None
    ) -> None:
        self.require_context()
        self.validate()
        self.require_owner()
        command = [
            *self.command("run", "--rm", "-T", "--no-deps", "backend"),
            "python",
            "-m",
            "florabase.auth.bootstrap",
            login,
        ]
        if display_name:
            command.extend(["--display-name", display_name])
        if password is None:
            # Interactive terminal prompt; stdout/stderr stay attached to the operator.
            try:
                subprocess.run(command, check=True, env=self.environment())
            except (OSError, subprocess.CalledProcessError) as error:
                raise WorkflowError("interactive owner bootstrap failed") from error
            return
        command.append("--password-stdin")
        try:
            subprocess.run(
                command,
                check=True,
                text=False,
                input=(password + "\n").encode(),
                env=self.environment(),
            )
        except (OSError, subprocess.CalledProcessError) as error:
            raise WorkflowError(
                "owner bootstrap failed; the Sourcing database must be running and ownerless"
            ) from error
        print("Sourcing Preview owner bootstrapped (local-only synthetic account).")

    def require_seed_preconditions(self) -> None:
        self.require_context()
        self.validate()
        self.require_owner()
        if self.current() != code_heads(migration_graph(self.source)):
            raise WorkflowError(
                "Sourcing Preview database must be at this source's code head before seeding"
            )

    def seed(self) -> None:
        self.require_seed_preconditions()
        super().seed()

    def status(self) -> None:
        self.require_context()
        super().status()
        containers = self.containers()
        running = {
            item["Config"].get("Labels", {}).get("com.docker.compose.service")
            for item in containers
            if item["State"].get("Running")
        }
        print(f"Published endpoint: {self.url} (loopback only)")
        if {"db", "backend", "frontend"} <= running:
            print(f"Dataset coverage: {self.dataset_status(capture=True)}")
        else:
            print("Dataset coverage: unavailable (Sourcing Preview is not fully running)")

    def remove(self, confirm: str) -> None:
        if confirm != self.project:
            raise WorkflowError(
                f"remove deletes ONLY {self.project} DB/media/dependencies; set "
                f"CONFIRM_REMOVE_SOURCING={self.project}"
            )
        self.require_context()
        super().stop(remove=True, confirm=confirm)


def compose_passthrough(preview: SourcingPreview, command: list[str]) -> None:
    if not command or command[0].startswith("-"):
        raise WorkflowError("provide a Compose subcommand; project/files/config are fixed")
    if command[0] == "down" and any(item in command for item in ("-v", "--volumes")):
        raise WorkflowError("use sourcing-preview-remove with its exact project confirmation")
    if command[0] in {"up", "down", "start", "stop", "restart", "kill", "rm"}:
        raise WorkflowError("use the sourcing-preview lifecycle actions instead of raw cleanup")
    preview.require_context()
    preview.validate()
    preview.require_owner()
    preview.compose(*command)


def dispatch(preview: SourcingPreview, action: str, args: argparse.Namespace) -> None:
    if action == "up":
        preview.up(rebuild=args.rebuild)
    elif action == "status":
        preview.status()
    elif action == "seed":
        preview.seed()
    elif action == "bootstrap-owner":
        password = args.password
        if args.password_file and password is not None:
            raise WorkflowError("provide only one password source")
        if args.password_file:
            password = Path(args.password_file).read_text().splitlines()[0]
        if args.password_stdin:
            if password is not None:
                raise WorkflowError("provide only one password source")
            password = sys.stdin.readline().rstrip("\r\n")
        preview.bootstrap_owner(args.login, password, display_name=args.display_name)
    elif action == "stop":
        preview.require_context()
        preview.stop()
    elif action == "remove":
        preview.remove(args.confirm)
    elif action == "compose":
        if not args.cmd:
            raise WorkflowError('provide CMD="<compose arguments>" for the compose action')
        compose_passthrough(preview, shlex.split(args.cmd))
    else:
        raise WorkflowError(f"unsupported action: {action}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=["up", "status", "seed", "bootstrap-owner", "stop", "remove", "compose"],
    )
    parser.add_argument("--rebuild", action="store_true", help="force an image build on `up`")
    parser.add_argument("--login", default="owner")
    parser.add_argument("--display-name")
    parser.add_argument("--password")
    parser.add_argument("--password-file")
    parser.add_argument("--password-stdin", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--cmd", default="", help="compose passthrough arguments")
    args = parser.parse_args()
    try:
        preview = SourcingPreview(Repository(Path.cwd()))
        dispatch(preview, args.action, args)
    except (WorkflowError, ValueError, KeyError, OSError) as error:
        print(f"sourcing preview: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
