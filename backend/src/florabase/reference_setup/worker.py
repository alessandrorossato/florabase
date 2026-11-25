"""Supervised low-priority worker that provisions one pinned reference index atomically."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from types import FrameType
from typing import Literal

from florabase.core.reference_index import DEFAULT_DOWNLOAD_MAX_SECONDS
from florabase.native_range_enrichment import snapshot as wcvp_snapshot
from florabase.reference_setup.lock import (
    STAGING_PREFIX,
    DiskUsageFn,
    check_free_space,
    cleanup_stale_staging,
    reference_setup_lock,
    sync_directory,
    sync_file,
)
from florabase.reference_setup.state import (
    WCVP_V16_DIRNAME,
    WCVP_V16_FILENAME,
    WFO_FILENAME,
    ReferenceIndexKey,
    ReferenceSetupFailureReason,
    classify_failure,
    is_index_ready,
    managed_wcvp_v16_path,
    managed_wfo_path,
    required_free_bytes,
)
from florabase.taxonomy import snapshot as wfo_snapshot


@dataclass(frozen=True)
class ProvisionOutcome:
    status: Literal["ready", "failed"]
    reason: ReferenceSetupFailureReason | None = None


@contextmanager
def _scoped_temp_env(staging_dir: Path) -> Iterator[None]:
    previous_tmpdir = os.environ.get("TMPDIR")
    previous_sqlite_tmpdir = os.environ.get("SQLITE_TMPDIR")
    os.environ["TMPDIR"] = str(staging_dir)
    os.environ["SQLITE_TMPDIR"] = str(staging_dir)
    try:
        yield
    finally:
        if previous_tmpdir is None:
            os.environ.pop("TMPDIR", None)
        else:
            os.environ["TMPDIR"] = previous_tmpdir
        if previous_sqlite_tmpdir is None:
            os.environ.pop("SQLITE_TMPDIR", None)
        else:
            os.environ["SQLITE_TMPDIR"] = previous_sqlite_tmpdir


def _write_seal_file(index_path: Path) -> Path:
    with index_path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    seal_path = index_path.with_suffix(".sha256")
    with seal_path.open("w", encoding="ascii") as handle:
        handle.write(digest + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    seal_path.chmod(0o600)
    return seal_path


def _provision_wfo_staged(state_dir: Path, staging_dir: Path, max_seconds: float) -> None:
    staged_index = staging_dir / WFO_FILENAME
    wfo_snapshot.download(staged_index, staging_dir=staging_dir, max_seconds=max_seconds)
    staged_seal = staged_index.with_suffix(".sha256")
    if not is_index_ready("wfo", staged_index, require_seal=True):
        raise ValueError("Built WFO index failed verification")
    sync_file(staged_seal)
    sync_file(staged_index)
    final_index = managed_wfo_path(state_dir)
    final_seal = final_index.with_suffix(".sha256")
    os.replace(staged_seal, final_seal)
    os.replace(staged_index, final_index)
    sync_directory(state_dir)


def _provision_wcvp_v16_staged(state_dir: Path, staging_dir: Path, max_seconds: float) -> None:
    staged_bundle = staging_dir / WCVP_V16_DIRNAME
    staged_bundle.mkdir(mode=0o700)
    staged_index = staged_bundle / WCVP_V16_FILENAME
    wcvp_snapshot.download(staged_index, "16", staging_dir=staging_dir, max_seconds=max_seconds)
    # publish_index leaves a per-destination .lock file; drop it before publishing the bundle.
    (staged_bundle / f"{WCVP_V16_FILENAME}.lock").unlink(missing_ok=True)
    _write_seal_file(staged_index)
    sync_file(staged_index)
    sync_directory(staged_bundle)
    if not is_index_ready("wcvp_v16", staged_index, require_seal=True):
        raise ValueError("Built WCVP v16 index failed verification")
    final_bundle = state_dir / WCVP_V16_DIRNAME
    if final_bundle.is_symlink():
        final_bundle.unlink()
    elif final_bundle.exists():
        # Caller already verified no valid sealed index exists here; move invalid residue into
        # staging so it is deleted automatically after atomic rename of the verified bundle.
        final_bundle.rename(staging_dir / "replaced-invalid")
    staged_bundle.rename(final_bundle)
    sync_directory(state_dir)


def provision_index(
    key: ReferenceIndexKey,
    state_dir: Path,
    *,
    max_seconds: float = DEFAULT_DOWNLOAD_MAX_SECONDS,
    disk_usage: DiskUsageFn = shutil.disk_usage,
    required_bytes: int | None = None,
) -> ProvisionOutcome:
    """Download, verify, build, seal, and atomically publish one managed reference index."""
    final_path = managed_wfo_path(state_dir) if key == "wfo" else managed_wcvp_v16_path(state_dir)
    needed = required_free_bytes(key) if required_bytes is None else required_bytes
    try:
        with reference_setup_lock(state_dir):
            cleanup_stale_staging(state_dir)
            if is_index_ready(key, final_path, require_seal=True):
                return ProvisionOutcome(status="ready")
            check_free_space(state_dir, needed, disk_usage=disk_usage)
            with tempfile.TemporaryDirectory(
                prefix=f"{STAGING_PREFIX}{key}-",
                dir=state_dir,
            ) as staging_name:
                staging_dir = Path(staging_name)
                staging_dir.chmod(0o700)
                with _scoped_temp_env(staging_dir):
                    if key == "wfo":
                        _provision_wfo_staged(state_dir, staging_dir, max_seconds)
                    else:
                        _provision_wcvp_v16_staged(state_dir, staging_dir, max_seconds)
            if not is_index_ready(key, final_path, require_seal=True):
                return ProvisionOutcome(status="failed", reason="build")
            return ProvisionOutcome(status="ready")
    except SystemExit:
        raise
    except BaseException as error:
        return ProvisionOutcome(status="failed", reason=classify_failure(error))


def _lower_priority() -> None:
    with suppress(OSError):
        os.nice(10)


def _handle_sigterm(_signum: int, _frame: FrameType | None) -> None:
    raise SystemExit(143)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", choices=("wfo", "wcvp_v16"), required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument(
        "--max-seconds",
        type=float,
        default=DEFAULT_DOWNLOAD_MAX_SECONDS,
    )
    args = parser.parse_args(argv)
    signal.signal(signal.SIGTERM, _handle_sigterm)
    _lower_priority()
    outcome = provision_index(args.index, args.state_dir, max_seconds=args.max_seconds)
    payload: dict[str, str] = {"status": outcome.status}
    if outcome.reason is not None:
        payload["reason"] = outcome.reason
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()
    return 0 if outcome.status == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
