"""Path resolution, validation, failure classification, and runtime state for reference setup."""

from __future__ import annotations

import errno
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Final, Literal

import httpx
from pydantic import BaseModel, ConfigDict

from florabase.core.config import ReferencesSetupMode, Settings
from florabase.core.reference_index import (
    ReferenceDownloadContentTypeError,
    ReferenceDownloadSizeError,
    ReferenceDownloadTimeoutError,
)

ReferenceIndexKey = Literal["wfo", "wcvp_v16"]
ReferenceSetupState = Literal["off", "preparing", "ready", "failed", "manual"]
ReferenceSetupFailureReason = Literal["network", "checksum", "size", "build", "disk"]

WFO_FILENAME: Final = "wfo-2026-06.sqlite"
WCVP_V16_DIRNAME: Final = "wcvp-v16"
WCVP_V16_FILENAME: Final = "index.sqlite"

WFO_EXPECTED_ARCHIVE_BYTES: Final = 132_643_291
WFO_EXPECTED_INDEX_BYTES: Final = 413_069_312
WCVP_V16_EXPECTED_ARCHIVE_BYTES: Final = 88_179_649
WCVP_V16_EXPECTED_INDEX_BYTES: Final = 952_799_232
FREE_SPACE_HEADROOM: Final = 1.2
RETRY_INTERVAL_SECONDS: Final[float] = 6.0 * 3600.0

PREPARING_UNAVAILABLE_MESSAGE: Final = "Reference data is being prepared in the background."


class DiskSpaceError(OSError):
    """Managed reference directory lacks enough free space for safe staged provisioning."""


class ReferenceSetupIndexStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: ReferenceSetupState
    status: str
    reason: ReferenceSetupFailureReason | None = None
    available: bool


class SystemReferencesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: ReferencesSetupMode
    wfo: ReferenceSetupIndexStatus
    wcvp_v16: ReferenceSetupIndexStatus


def managed_wfo_path(state_dir: Path) -> Path:
    return state_dir / WFO_FILENAME


def managed_wcvp_v16_path(state_dir: Path) -> Path:
    return state_dir / WCVP_V16_DIRNAME / WCVP_V16_FILENAME


def required_free_bytes(key: ReferenceIndexKey) -> int:
    if key == "wfo":
        return int((WFO_EXPECTED_ARCHIVE_BYTES + WFO_EXPECTED_INDEX_BYTES) * FREE_SPACE_HEADROOM)
    return int(
        (WCVP_V16_EXPECTED_ARCHIVE_BYTES + WCVP_V16_EXPECTED_INDEX_BYTES) * FREE_SPACE_HEADROOM
    )


def _normalize_path(path: Path) -> Path:
    return Path(*path.parts)


def resolve_wfo_target(settings: Settings) -> tuple[Path, bool]:
    """Return ``(effective_path, is_managed)`` for WFO 2026-06."""
    managed = _normalize_path(managed_wfo_path(settings.references_state_dir))
    if settings.wfo_snapshot_path is None:
        return managed, True
    configured = _normalize_path(settings.wfo_snapshot_path)
    return configured, configured == managed


def resolve_wcvp_v16_target(settings: Settings) -> tuple[Path, bool, bool]:
    """Return ``(effective_path, is_managed, require_seal)`` for WCVP v16."""
    managed = _normalize_path(managed_wcvp_v16_path(settings.references_state_dir))
    if settings.wcvp_v16_snapshot_path is None:
        return managed, True, True
    configured = _normalize_path(settings.wcvp_v16_snapshot_path)
    is_managed = configured == managed
    require_seal = True if is_managed else settings.wcvp_v16_require_seal
    return configured, is_managed, require_seal


def is_index_ready(key: ReferenceIndexKey, path: Path, *, require_seal: bool = True) -> bool:
    """Return True iff ``path`` passes full metadata, schema and seal verification."""
    if key == "wfo":
        from florabase.taxonomy.source import SourceUnavailableError, WfoSource

        try:
            WfoSource(path).metadata()
        except SourceUnavailableError:
            return False
        return True

    from florabase.native_range_enrichment.source import (
        SourceUnavailableError as WcvpUnavailableError,
    )
    from florabase.native_range_enrichment.source import WcvpSource

    try:
        WcvpSource(path, "16", require_seal=require_seal).metadata()
    except WcvpUnavailableError:
        return False
    return True


def classify_failure(error: BaseException) -> ReferenceSetupFailureReason:
    """Map provisioning exceptions into a bounded, secret-free diagnostic category."""
    if isinstance(error, DiskSpaceError):
        return "disk"
    if isinstance(error, OSError) and error.errno == errno.ENOSPC:
        return "disk"
    if isinstance(error, ReferenceDownloadSizeError):
        return "size"
    if isinstance(
        error,
        (
            httpx.HTTPError,
            ReferenceDownloadTimeoutError,
            ReferenceDownloadContentTypeError,
            TimeoutError,
        ),
    ):
        return "network"
    detail = str(error).lower()
    if "checksum" in detail:
        return "checksum"
    if "size" in detail or "disk bound" in detail:
        return "size"
    if isinstance(error, (ValueError, sqlite3.Error, OSError)):
        return "build"
    return "build"


@dataclass
class _IndexRuntimeEntry:
    state: Literal["idle", "preparing", "failed"] = "idle"
    reason: ReferenceSetupFailureReason | None = None


class _RuntimeStateStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._entries: dict[ReferenceIndexKey, _IndexRuntimeEntry] = {
            "wfo": _IndexRuntimeEntry(),
            "wcvp_v16": _IndexRuntimeEntry(),
        }

    def reset(self) -> None:
        with self._lock:
            self._entries = {
                "wfo": _IndexRuntimeEntry(),
                "wcvp_v16": _IndexRuntimeEntry(),
            }

    def mark_preparing(self, key: ReferenceIndexKey) -> None:
        with self._lock:
            self._entries[key] = _IndexRuntimeEntry(state="preparing", reason=None)

    def mark_ready(self, key: ReferenceIndexKey) -> None:
        with self._lock:
            self._entries[key] = _IndexRuntimeEntry(state="idle", reason=None)

    def mark_failed(self, key: ReferenceIndexKey, reason: ReferenceSetupFailureReason) -> None:
        with self._lock:
            self._entries[key] = _IndexRuntimeEntry(state="failed", reason=reason)

    def snapshot(self, key: ReferenceIndexKey) -> _IndexRuntimeEntry:
        with self._lock:
            entry = self._entries[key]
            return _IndexRuntimeEntry(state=entry.state, reason=entry.reason)


_runtime_store = _RuntimeStateStore()


def reset_runtime_state() -> None:
    _runtime_store.reset()


def mark_index_preparing(key: ReferenceIndexKey) -> None:
    _runtime_store.mark_preparing(key)


def mark_index_ready(key: ReferenceIndexKey) -> None:
    _runtime_store.mark_ready(key)


def mark_index_failed(key: ReferenceIndexKey, reason: ReferenceSetupFailureReason) -> None:
    _runtime_store.mark_failed(key, reason)


def is_index_preparing(key: ReferenceIndexKey) -> bool:
    return _runtime_store.snapshot(key).state == "preparing"


def _status_for_index(
    key: ReferenceIndexKey,
    *,
    mode: ReferencesSetupMode,
    path: Path,
    is_managed: bool,
    require_seal: bool,
) -> ReferenceSetupIndexStatus:
    available = is_index_ready(key, path, require_seal=require_seal)
    if not is_managed:
        return ReferenceSetupIndexStatus(
            state="manual",
            status="manual",
            reason=None,
            available=available,
        )
    if available:
        label = "ready (setup off)" if mode is ReferencesSetupMode.OFF else "ready"
        return ReferenceSetupIndexStatus(
            state="ready",
            status=label,
            reason=None,
            available=True,
        )
    if mode is ReferencesSetupMode.OFF:
        return ReferenceSetupIndexStatus(
            state="off",
            status="off",
            reason=None,
            available=False,
        )
    entry = _runtime_store.snapshot(key)
    if entry.state == "failed" and entry.reason is not None:
        return ReferenceSetupIndexStatus(
            state="failed",
            status=f"failed: {entry.reason}",
            reason=entry.reason,
            available=False,
        )
    return ReferenceSetupIndexStatus(
        state="preparing",
        status="preparing",
        reason=None,
        available=False,
    )


def get_runtime_status(settings: Settings) -> SystemReferencesResponse:
    """Compute read-only status for WFO and WCVP v16 without touching the network."""
    wfo_path, wfo_managed = resolve_wfo_target(settings)
    wcvp_path, wcvp_managed, wcvp_require_seal = resolve_wcvp_v16_target(settings)
    return SystemReferencesResponse(
        mode=settings.references_setup,
        wfo=_status_for_index(
            "wfo",
            mode=settings.references_setup,
            path=wfo_path,
            is_managed=wfo_managed,
            require_seal=True,
        ),
        wcvp_v16=_status_for_index(
            "wcvp_v16",
            mode=settings.references_setup,
            path=wcvp_path,
            is_managed=wcvp_managed,
            require_seal=wcvp_require_seal,
        ),
    )
