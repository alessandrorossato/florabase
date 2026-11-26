"""Non-blocking background coordinator for automatic reference index provisioning."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Final

from florabase.core.config import ReferencesSetupMode, Settings
from florabase.core.reference_index import DEFAULT_DOWNLOAD_MAX_SECONDS
from florabase.reference_setup.state import (
    RETRY_INTERVAL_SECONDS,
    ReferenceIndexKey,
    ReferenceSetupFailureReason,
    is_index_ready,
    mark_index_failed,
    mark_index_preparing,
    mark_index_ready,
    reset_runtime_state,
    resolve_wcvp_v16_target,
    resolve_wfo_target,
)
from florabase.reference_setup.worker import ProvisionOutcome, worker_staging_dir

logger = logging.getLogger(__name__)

_SCRUBBED_WORKER_ENV: Final[frozenset[str]] = frozenset(
    {
        "FLORABASE_DB_PASSWORD",
        "PGPASSWORD",
        "FLORABASE_DATABASE_URL",
        "FLORABASE_OWNER_LOGIN",
        "FLORABASE_OWNER_PASSWORD",
    }
)
_VALID_REASONS: Final[dict[str, ReferenceSetupFailureReason]] = {
    "network": "network",
    "checksum": "checksum",
    "size": "size",
    "build": "build",
    "disk": "disk",
}
_SHUTDOWN_GRACE_SECONDS: Final[float] = 5.0

WorkerRunner = Callable[[ReferenceIndexKey, Path, float], Awaitable[ProvisionOutcome]]


def _worker_environment(staging_dir: Path) -> dict[str, str]:
    environment = {k: v for k, v in os.environ.items() if k not in _SCRUBBED_WORKER_ENV}
    # SQLite and tempfile read these once per process: set them before the worker starts so
    # sort and temp files always land in staging, inside the disk pre-check.
    environment["TMPDIR"] = str(staging_dir)
    environment["SQLITE_TMPDIR"] = str(staging_dir)
    return environment


def _parse_worker_outcome(returncode: int, stdout: bytes) -> ProvisionOutcome:
    text = stdout.decode("utf-8", errors="replace").strip()
    if text:
        last_line = text.splitlines()[-1]
        try:
            data = json.loads(last_line)
        except ValueError:
            data = None
        if isinstance(data, dict):
            status = data.get("status")
            reason = data.get("reason")
            if status == "ready" and returncode == 0:
                return ProvisionOutcome(status="ready")
            if isinstance(reason, str) and reason in _VALID_REASONS:
                return ProvisionOutcome(status="failed", reason=_VALID_REASONS[reason])
    if returncode == 0:
        return ProvisionOutcome(status="ready")
    return ProvisionOutcome(status="failed", reason="build")


class ReferenceSetupCoordinator:
    """Supervises sequential background provisioning in FastAPI lifespan."""

    def __init__(
        self,
        settings: Settings,
        *,
        retry_interval_seconds: float = RETRY_INTERVAL_SECONDS,
        max_download_seconds: float = DEFAULT_DOWNLOAD_MAX_SECONDS,
        worker_runner: WorkerRunner | None = None,
    ) -> None:
        self._settings = settings
        self._retry_interval_seconds = retry_interval_seconds
        self._max_download_seconds = max_download_seconds
        self._worker_runner = worker_runner
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._active_process: asyncio.subprocess.Process | None = None
        # Pinned upstream content changed: retrying cannot help until a restart.
        self._no_retry: set[ReferenceIndexKey] = set()

    def _pending_managed_targets(self) -> list[tuple[ReferenceIndexKey, Path]]:
        """Blocking: may hash whole indexes, so call it only through ``asyncio.to_thread``."""
        pending: list[tuple[ReferenceIndexKey, Path]] = []
        wfo_path, wfo_managed = resolve_wfo_target(self._settings)
        if wfo_managed and not is_index_ready("wfo", wfo_path, require_seal=True):
            pending.append(("wfo", wfo_path))
        wcvp_path, wcvp_managed, wcvp_require_seal = resolve_wcvp_v16_target(self._settings)
        if wcvp_managed and not is_index_ready(
            "wcvp_v16", wcvp_path, require_seal=wcvp_require_seal
        ):
            pending.append(("wcvp_v16", wcvp_path))
        return [target for target in pending if target[0] not in self._no_retry]

    def start(self) -> None:
        """Start the background loop in ``auto`` mode; does no I/O so start-up never waits."""
        reset_runtime_state()
        if self._settings.references_setup is not ReferencesSetupMode.AUTO:
            return
        self._no_retry.clear()
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop(), name="florabase-reference-setup")

    async def stop(self) -> None:
        """Stop any pending retry wait and cleanly terminate an active worker subprocess."""
        self._stop_event.set()
        process = self._active_process
        if process is not None and process.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=_SHUTDOWN_GRACE_SECONDS)
            except TimeoutError:
                with contextlib.suppress(ProcessLookupError):
                    process.kill()
                await process.wait()
        task = self._task
        self._task = None
        if task is not None:
            if not task.done():
                task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def _run_subprocess(
        self, key: ReferenceIndexKey, state_dir: Path, max_seconds: float
    ) -> ProvisionOutcome:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "florabase.reference_setup.worker",
            "--index",
            key,
            "--state-dir",
            str(state_dir),
            "--max-seconds",
            str(max_seconds),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_worker_environment(worker_staging_dir(state_dir, key)),
        )
        self._active_process = process
        try:
            stdout, _stderr = await process.communicate()
        finally:
            if self._active_process is process:
                self._active_process = None
        returncode = 1 if process.returncode is None else process.returncode
        return _parse_worker_outcome(returncode, stdout)

    async def _provision_one(self, key: ReferenceIndexKey, target_path: Path) -> bool:
        mark_index_preparing(key)
        runner = self._worker_runner or self._run_subprocess
        try:
            outcome = await runner(
                key,
                self._settings.references_state_dir,
                self._max_download_seconds,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            outcome = ProvisionOutcome(status="failed", reason="build")

        if self._stop_event.is_set():
            return False

        if outcome.status == "ready" and await asyncio.to_thread(
            is_index_ready, key, target_path, require_seal=True
        ):
            mark_index_ready(key)
            logger.info("Reference index %s is ready", key)
            return True

        reason: ReferenceSetupFailureReason = outcome.reason or "build"
        mark_index_failed(key, reason)
        if reason == "checksum":
            self._no_retry.add(key)
            logger.warning(
                "Reference index %s provisioning failed (checksum); not retrying until restart",
                key,
            )
            return False
        retry_hours = max(1, round(self._retry_interval_seconds / 3600.0))
        logger.warning(
            "Reference index %s provisioning failed (%s); will retry in %d h",
            key,
            reason,
            retry_hours,
        )
        return False

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            pending = await asyncio.to_thread(self._pending_managed_targets)
            if not pending or self._stop_event.is_set():
                return
            for key, _path in pending:
                mark_index_preparing(key)
            retry_needed = False
            for key, target_path in pending:
                if self._stop_event.is_set():
                    return
                ok = await self._provision_one(key, target_path)
                if not ok and key not in self._no_retry:
                    retry_needed = True
            if not retry_needed or self._stop_event.is_set():
                return
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._retry_interval_seconds,
                )
            except TimeoutError:
                continue
