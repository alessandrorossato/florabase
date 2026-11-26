"""Managed directory locking, permissions, stale-staging cleanup, and disk pre-checks."""

from __future__ import annotations

import fcntl
import os
import shutil
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Final, NamedTuple, Protocol

from florabase.reference_setup.state import DiskSpaceError

LOCK_FILENAME: Final = ".reference-setup.lock"
STAGING_PREFIX: Final = ".staging-"


class DiskUsageResult(Protocol):
    @property
    def free(self) -> int: ...


class DiskUsage(NamedTuple):
    total: int
    used: int
    free: int


DiskUsageFn = Callable[[Path], DiskUsageResult]


def ensure_managed_dir(managed_dir: Path) -> None:
    """Ensure ``managed_dir`` exists as a private 0700 real directory owned by the backend user."""
    if managed_dir.is_symlink():
        raise OSError("Managed reference directory must not be a symlink")
    if not managed_dir.exists():
        managed_dir.parent.mkdir(parents=True, exist_ok=True)
        managed_dir.mkdir(mode=0o700, exist_ok=True)
    if managed_dir.is_symlink() or not managed_dir.is_dir():
        raise OSError("Managed reference directory is not a regular directory")
    managed_dir.chmod(0o700)


def sync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def sync_file(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def cleanup_stale_staging(managed_dir: Path) -> int:
    """Remove leftover ``.staging-*`` entries inside ``managed_dir`` (caller must hold lock)."""
    removed = 0
    if not managed_dir.is_dir():
        return 0
    for entry in managed_dir.iterdir():
        if not entry.name.startswith(STAGING_PREFIX):
            continue
        if entry.is_symlink() or not entry.is_dir():
            entry.unlink(missing_ok=True)
        else:
            shutil.rmtree(entry)
        removed += 1
    return removed


def check_free_space(
    managed_dir: Path,
    required_bytes: int,
    *,
    disk_usage: DiskUsageFn = shutil.disk_usage,
) -> None:
    """Refuse to download when free disk space is below ``required_bytes``."""
    free_bytes = disk_usage(managed_dir).free
    if free_bytes < required_bytes:
        free_mib = free_bytes // (1024 * 1024)
        required_mib = (required_bytes + (1024 * 1024) - 1) // (1024 * 1024)
        raise DiskSpaceError(
            f"Insufficient free space ({free_mib} MiB available, {required_mib} MiB required)"
        )


@contextmanager
def reference_setup_lock(managed_dir: Path) -> Iterator[None]:
    """Hold an exclusive inter-process ``fcntl`` lock in ``managed_dir`` for a whole build."""
    ensure_managed_dir(managed_dir)
    lock_path = managed_dir / LOCK_FILENAME
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
