"""Unit tests for automatic background reference index provisioning (REF-SETUP-001)."""

from __future__ import annotations

import asyncio
import hashlib
import http.server
import io
import json
import logging
import signal
import subprocess
import sys
import tarfile
import threading
import time
from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID
from zipfile import ZipFile

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from florabase.auth.dependencies import AuthenticatedActor, require_authenticated_actor
from florabase.core.config import (
    CookieMode,
    Environment,
    ReferencesSetupMode,
    Settings,
    get_settings,
)
from florabase.core.reference_index import (
    ReferenceDownloadContentTypeError,
    ReferenceDownloadSizeError,
    ReferenceDownloadTimeoutError,
    download_archive,
)
from florabase.db import release_schema
from florabase.main import create_app
from florabase.native_range_enrichment import snapshot as wcvp_snapshot
from florabase.native_range_enrichment import source as wcvp_source
from florabase.reference_setup.lock import (
    LOCK_FILENAME,
    STAGING_PREFIX,
    DiskUsage,
    check_free_space,
    cleanup_stale_staging,
    ensure_managed_dir,
    reference_setup_lock,
)
from florabase.reference_setup.runner import (
    ReferenceSetupCoordinator,
    _parse_worker_outcome,
    _worker_environment,
)
from florabase.reference_setup.state import (
    PREPARING_UNAVAILABLE_MESSAGE,
    DiskSpaceError,
    classify_failure,
    get_runtime_status,
    managed_wcvp_v16_path,
    managed_wfo_path,
    mark_index_failed,
    mark_index_preparing,
    required_free_bytes,
    reset_runtime_state,
    resolve_wcvp_v16_target,
    resolve_wfo_target,
)
from florabase.reference_setup.worker import ProvisionOutcome, provision_index
from florabase.reference_setup.worker import main as worker_main
from florabase.taxonomy import snapshot as wfo_snapshot
from florabase.taxonomy import source as wfo_source

TEST_TIMESTAMP = "2026-10-28T20:31:34+00:00"


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    media_dir = tmp_path / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    media_dir.chmod(0o700)
    data: dict[str, object] = {
        "environment": Environment.TEST,
        "database_url": "postgresql+psycopg://test:test@db/test",
        "cookie_mode": CookieMode.SECURE,
        "attachment_storage_root": media_dir,
        "references_state_dir": tmp_path / "state" / "reference",
        "references_setup": ReferencesSetupMode.OFF,
        "wfo_snapshot_path": None,
        "wcvp_v16_snapshot_path": None,
        "wcvp_snapshot_path": None,
    }
    data.update(overrides)
    return Settings.model_validate(data)


def _build_valid_wfo(destination: Path) -> None:
    names = [
        {
            "ID": wfo_source.ROOT,
            "scientificName": "Plantae",
            "authorship": "",
            "rank": "kingdom",
        },
        {
            "ID": "wfo-0000000001",
            "scientificName": "Solanum lycopersicum",
            "authorship": "L.",
            "rank": "species",
        },
    ]
    concepts = [
        {"ID": wfo_source.ROOT, "nameID": wfo_source.ROOT, "parentID": wfo_source.CODE},
        {"ID": "wfo-0000000001", "nameID": "wfo-0000000001", "parentID": wfo_source.ROOT},
    ]
    wfo_snapshot.build_index(
        destination,
        names,
        concepts,
        [],
        wfo_source.WfoMetadata(retrieved_at=TEST_TIMESTAMP),
    )


def _build_valid_wcvp_v16(destination: Path, *, with_seal: bool = True) -> None:
    names = [
        {
            "plant_name_id": "100",
            "taxon_name": "Solanum lycopersicum",
            "taxon_authors": "L.",
            "taxon_rank": "Species",
            "taxon_status": "Accepted",
            "accepted_plant_name_id": "100",
            "powo_id": "100-1",
            "reviewed": "Y",
        }
    ]
    distributions = [
        {
            "plant_locality_id": "1",
            "plant_name_id": "100",
            "continent_code_l1": "8",
            "continent": "Southern America",
            "region_code_l2": "83",
            "region": "Western South America",
            "area_code_l3": "PER",
            "area": "Peru",
            "introduced": "0",
            "extinct": "0",
            "location_doubtful": "0",
        }
    ]
    wcvp_snapshot.build_index(
        destination,
        names,
        distributions,
        wcvp_source.SourceMetadata.for_release("16", TEST_TIMESTAMP),
    )
    if with_seal:
        with destination.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        seal = destination.with_suffix(".sha256")
        seal.write_text(digest + "\n", encoding="ascii")
        seal.chmod(0o600)


def _tsv_table(fields: list[str], rows: list[dict[str, str]]) -> bytes:
    lines = ["\t".join(fields)]
    for row in rows:
        lines.append("\t".join(row.get(field, "") for field in fields))
    return ("\n".join(lines) + "\n").encode("utf-8")


def _make_synthetic_wfo_zip() -> tuple[bytes, dict[str, int]]:
    buf = io.BytesIO()
    name_tsv = _tsv_table(
        wfo_snapshot.FIELDS["name.tsv"],
        [
            {
                "ID": wfo_source.ROOT,
                "scientificName": "Plantae",
                "rank": "kingdom",
                "uninomial": "Plantae",
                "code": "ICN",
            },
            {
                "ID": "wfo-0000000001",
                "scientificName": "Solanum lycopersicum",
                "authorship": "L.",
                "rank": "species",
                "genus": "Solanum",
                "specificEpithet": "lycopersicum",
                "code": "ICN",
                "publishedInYear": "1753",
            },
        ],
    )
    taxon_tsv = _tsv_table(
        wfo_snapshot.FIELDS["taxon.tsv"],
        [
            {"ID": wfo_source.ROOT, "nameID": wfo_source.ROOT, "parentID": wfo_source.CODE},
            {"ID": "wfo-0000000001", "nameID": "wfo-0000000001", "parentID": wfo_source.ROOT},
        ],
    )
    synonym_tsv = _tsv_table(wfo_snapshot.FIELDS["synonym.tsv"], [])
    metadata_json = json.dumps(
        {"version": "2026-06 01", "issued": "2026-06-21", "license": "cc0"}
    ).encode("utf-8")
    members = {
        "name.tsv": name_tsv,
        "taxon.tsv": taxon_tsv,
        "synonym.tsv": synonym_tsv,
        "reference.tsv": b"",
        "typematerial.tsv": b"",
        "metadata.json": metadata_json,
    }
    with ZipFile(buf, "w") as archive:
        for filename, content in members.items():
            archive.writestr(filename, content)
    return buf.getvalue(), {name: len(content) for name, content in members.items()}


def _make_synthetic_wcvp_zip() -> tuple[bytes, tuple[int, int, int]]:
    buf = io.BytesIO()
    readme = b"README WCVP v16 test"
    name_row = dict.fromkeys(wcvp_snapshot.NAMES_FIELDS, "")
    name_row.update(
        {
            "plant_name_id": "100",
            "taxon_rank": "Species",
            "taxon_status": "Accepted",
            "taxon_name": "Solanum lycopersicum",
            "taxon_authors": "L.",
            "accepted_plant_name_id": "100",
            "powo_id": "100-1",
            "reviewed": "Y",
        }
    )
    names_csv = (
        "|".join(wcvp_snapshot.NAMES_FIELDS)
        + "\n"
        + "|".join(name_row[field] for field in wcvp_snapshot.NAMES_FIELDS)
        + "\n"
    ).encode("utf-8")
    dist_row = {
        "plant_locality_id": "1",
        "plant_name_id": "100",
        "continent_code_l1": "8",
        "continent": "Southern America",
        "region_code_l2": "83",
        "region": "Western South America",
        "area_code_l3": "PER",
        "area": "Peru",
        "introduced": "0",
        "extinct": "0",
        "location_doubtful": "0",
    }
    dist_csv = (
        "|".join(wcvp_snapshot.DISTRIBUTION_FIELDS)
        + "\n"
        + "|".join(dist_row[field] for field in wcvp_snapshot.DISTRIBUTION_FIELDS)
        + "\n"
    ).encode("utf-8")
    with ZipFile(buf, "w") as archive:
        archive.writestr("README_WCVP.xlsx", readme)
        archive.writestr("wcvp_names.csv", names_csv)
        archive.writestr("wcvp_distribution.csv", dist_csv)
    return buf.getvalue(), (len(readme), len(names_csv), len(dist_csv))


def test_settings_defaults_and_path_resolution(tmp_path: Path) -> None:
    reset_runtime_state()
    default = _settings(tmp_path)
    assert default.references_setup is ReferencesSetupMode.OFF

    wfo_path, wfo_managed = resolve_wfo_target(default)
    assert wfo_managed is True
    assert wfo_path == managed_wfo_path(default.references_state_dir)

    wcvp_path, wcvp_managed, wcvp_seal = resolve_wcvp_v16_target(default)
    assert wcvp_managed is True
    assert wcvp_seal is True  # Always enforced for managed directory.
    assert wcvp_path == managed_wcvp_v16_path(default.references_state_dir)

    manual_wfo = tmp_path / "manual" / "wfo.sqlite"
    manual_wcvp = tmp_path / "manual" / "wcvp.sqlite"
    manual = _settings(
        tmp_path,
        references_setup=ReferencesSetupMode.AUTO,
        wfo_snapshot_path=manual_wfo,
        wcvp_v16_snapshot_path=manual_wcvp,
        wcvp_v16_require_seal=False,
    )
    assert resolve_wfo_target(manual) == (manual_wfo, False)
    assert resolve_wcvp_v16_target(manual) == (manual_wcvp, False, False)

    with pytest.raises(ValidationError):
        _settings(tmp_path, references_setup="invalid")
    with pytest.raises(ValidationError):
        _settings(tmp_path, references_state_dir=Path("relative/path"))
    with pytest.raises(ValidationError):
        _settings(tmp_path, references_state_dir=Path("/"))
    with pytest.raises(ValidationError):
        _settings(tmp_path, references_state_dir=Path("/var/lib/../tmp"))


def test_runtime_status_modes_and_ready_setup_off(tmp_path: Path) -> None:
    reset_runtime_state()
    off_settings = _settings(tmp_path, references_setup=ReferencesSetupMode.OFF)
    status = get_runtime_status(off_settings)
    assert status.mode is ReferencesSetupMode.OFF
    assert status.wfo.state == "off"
    assert status.wfo.status == "off"
    assert status.wfo.available is False
    assert status.wcvp_v16.state == "off"
    assert status.wcvp_v16.status == "off"
    assert status.wcvp_v16.available is False

    # Existing valid sealed managed indexes keep working with setup=off.
    _build_valid_wfo(managed_wfo_path(off_settings.references_state_dir))
    _build_valid_wcvp_v16(managed_wcvp_v16_path(off_settings.references_state_dir), with_seal=True)
    ready_off = get_runtime_status(off_settings)
    assert ready_off.wfo.state == "ready"
    assert ready_off.wfo.status == "ready (setup off)"
    assert ready_off.wfo.available is True
    assert ready_off.wcvp_v16.state == "ready"
    assert ready_off.wcvp_v16.status == "ready (setup off)"
    assert ready_off.wcvp_v16.available is True

    # Removing WCVP v16 seal fails closed for the managed directory.
    managed_wcvp_v16_path(off_settings.references_state_dir).with_suffix(".sha256").unlink()
    unsealed = get_runtime_status(off_settings)
    assert unsealed.wcvp_v16.state == "off"
    assert unsealed.wcvp_v16.available is False

    # Manual mode reports "manual" regardless of auto/off.
    manual_wfo = tmp_path / "ro" / "wfo.sqlite"
    _build_valid_wfo(manual_wfo)
    manual_settings = _settings(
        tmp_path,
        references_setup=ReferencesSetupMode.AUTO,
        wfo_snapshot_path=manual_wfo,
    )
    mark_index_failed("wcvp_v16", "network")
    mixed = get_runtime_status(manual_settings)
    assert mixed.wfo.state == "manual"
    assert mixed.wfo.status == "manual"
    assert mixed.wfo.available is True
    assert mixed.wcvp_v16.state == "failed"
    assert mixed.wcvp_v16.status == "failed: network"
    assert mixed.wcvp_v16.reason == "network"


def test_shared_download_archive_handles_zenodo_duplicate_headers_and_rejects_bad_responses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_client = httpx.Client
    payload = b"PK\x03\x04exact-bytes"
    seen_accept: list[str] = []

    def ok_handler(request: httpx.Request) -> httpx.Response:
        seen_accept.append(request.headers.get("accept", ""))
        return httpx.Response(
            200,
            headers=[
                ("content-type", "application/octet-stream"),
                ("content-type", "application/octet-stream"),
                ("content-length", str(len(payload))),
            ],
            content=payload,
        )

    def make_client(
        handler: Callable[[httpx.Request], httpx.Response],
    ) -> Callable[..., httpx.Client]:
        def client(*, timeout: httpx.Timeout, follow_redirects: bool) -> httpx.Client:
            assert follow_redirects is False
            return original_client(
                transport=httpx.MockTransport(handler),
                timeout=timeout,
                follow_redirects=follow_redirects,
            )

        return client

    monkeypatch.setattr(httpx, "Client", make_client(ok_handler))
    out = tmp_path / "ok.zip"
    size = download_archive(
        "https://example.invalid/archive.zip",
        out,
        max_bytes=len(payload),
        exact_bytes=len(payload),
        max_seconds=30.0,
        accept="*/*",
        label="WFO",
    )
    assert size == len(payload)
    assert out.read_bytes() == payload
    assert seen_accept == ["*/*"]

    # Reject mixed content-type (duplicate valid + text/html).
    def bad_ct(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers=[
                ("content-type", "application/octet-stream"),
                ("content-type", "text/html"),
            ],
            content=payload,
        )

    monkeypatch.setattr(httpx, "Client", make_client(bad_ct))
    with pytest.raises(ReferenceDownloadContentTypeError):
        download_archive(
            "https://example.invalid/archive.zip",
            tmp_path / "ct.zip",
            max_bytes=1024,
            label="WFO",
        )

    # Fast-fail on Content-Length mismatch before streaming.
    def wrong_cl(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/zip", "content-length": "999"},
            content=payload,
        )

    monkeypatch.setattr(httpx, "Client", make_client(wrong_cl))
    with pytest.raises(ReferenceDownloadSizeError):
        download_archive(
            "https://example.invalid/archive.zip",
            tmp_path / "cl.zip",
            max_bytes=1024,
            exact_bytes=len(payload),
            label="WFO",
        )

    # Custom max_seconds wall-clock cap is enforced.
    monkeypatch.setattr(httpx, "Client", make_client(ok_handler))
    times = iter([0.0, 11.0])
    monkeypatch.setattr(time, "monotonic", lambda: next(times))
    with pytest.raises(ReferenceDownloadTimeoutError):
        download_archive(
            "https://example.invalid/archive.zip",
            tmp_path / "slow.zip",
            max_bytes=len(payload),
            max_seconds=10.0,
            label="WFO",
        )


def test_wfo_download_sends_wildcard_accept_and_verifies_checksum_before_parse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_client = httpx.Client
    bad_bytes = b"not-a-zip-but-exact-size"
    seen_headers: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append((str(request.url), request.headers.get("accept", "")))
        return httpx.Response(
            200,
            headers=[
                ("content-type", "application/octet-stream"),
                ("content-type", "application/octet-stream"),
            ],
            content=bad_bytes,
        )

    def client(*, timeout: httpx.Timeout, follow_redirects: bool) -> httpx.Client:
        assert follow_redirects is False
        return original_client(
            transport=httpx.MockTransport(handler),
            timeout=timeout,
            follow_redirects=follow_redirects,
        )

    monkeypatch.setattr(httpx, "Client", client)
    monkeypatch.setattr(wfo_snapshot, "ARCHIVE_BYTES", len(bad_bytes))

    dest = tmp_path / "wfo-2026-06.sqlite"
    with pytest.raises(ValueError, match="checksum"):
        wfo_snapshot.download(dest, staging_dir=tmp_path, max_seconds=30.0)
    assert seen_headers == [(wfo_source.ARCHIVE_URL, "*/*")]
    assert not dest.exists()
    assert not dest.with_suffix(".sha256").exists()


def test_lock_permissions_stale_staging_and_disk_precheck(tmp_path: Path) -> None:
    state_dir = tmp_path / "state" / "reference"
    ensure_managed_dir(state_dir)
    assert (state_dir.stat().st_mode & 0o777) == 0o700

    # Refuses symlink as managed dir.
    link_dir = tmp_path / "link-ref"
    link_dir.symlink_to(state_dir)
    with pytest.raises(OSError, match="symlink"):
        ensure_managed_dir(link_dir)

    # Stale staging cleanup deletes only .staging-* entries.
    stale = state_dir / f"{STAGING_PREFIX}wfo-old"
    stale.mkdir()
    (stale / "partial.sqlite").write_bytes(b"partial")
    keep = state_dir / "keep.txt"
    keep.write_text("ok")
    with reference_setup_lock(state_dir):
        assert (state_dir / LOCK_FILENAME).exists()
        assert cleanup_stale_staging(state_dir) == 1
    assert not stale.exists()
    assert keep.exists()

    # Inter-process lock contention verified via subprocess.
    with reference_setup_lock(state_dir):
        probe = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import fcntl, sys; "
                    f"f = open({str(state_dir / LOCK_FILENAME)!r}, 'r+'); "
                    "fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)"
                ),
            ],
            check=False,
            capture_output=True,
        )
        assert probe.returncode != 0

    # Free-space pre-check rejects before any network call.
    def tiny_disk(_path: Path) -> DiskUsage:
        return DiskUsage(total=100, used=90, free=10)

    with pytest.raises(DiskSpaceError):
        check_free_space(state_dir, required_free_bytes("wfo"), disk_usage=tiny_disk)

    network_called = False

    def fail_if_called(*_args: object, **_kwargs: object) -> None:
        nonlocal network_called
        network_called = True
        raise AssertionError("network must not be touched when disk space is insufficient")

    with patch.object(wfo_snapshot, "download", side_effect=fail_if_called):
        outcome = provision_index("wfo", state_dir, disk_usage=tiny_disk)
    assert outcome == ProvisionOutcome(status="failed", reason="disk")
    assert network_called is False


def test_provision_index_stages_atomically_and_never_overwrites_valid_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_dir = tmp_path / "state" / "reference"
    wfo_zip, wfo_members = _make_synthetic_wfo_zip()
    wfo_checksum = hashlib.sha256(wfo_zip).hexdigest()
    wcvp_zip, wcvp_sizes = _make_synthetic_wcvp_zip()
    wcvp_checksum = hashlib.sha256(wcvp_zip).hexdigest()

    monkeypatch.setattr(wfo_snapshot, "ARCHIVE_BYTES", len(wfo_zip))
    monkeypatch.setattr(wfo_snapshot, "CHECKSUM", wfo_checksum)
    monkeypatch.setattr(wfo_snapshot, "MEMBERS", wfo_members)
    monkeypatch.setattr(wfo_source, "CHECKSUM", wfo_checksum)

    test_release = wcvp_source.Release(
        "16",
        wcvp_source.RELEASES["16"].archive_url,
        wcvp_checksum,
        wcvp_source.RELEASES["16"].citation,
        wcvp_sizes,
    )
    monkeypatch.setattr(
        wcvp_source,
        "RELEASES",
        {"15": wcvp_source.RELEASES["15"], "16": test_release},
    )

    original_client = httpx.Client
    downloads: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        downloads.append(str(request.url))
        if str(request.url) == wfo_source.ARCHIVE_URL:
            return httpx.Response(
                200,
                headers=[
                    ("content-type", "application/octet-stream"),
                    ("content-type", "application/octet-stream"),
                ],
                content=wfo_zip,
            )
        return httpx.Response(
            200,
            headers={"content-type": "application/zip"},
            content=wcvp_zip,
        )

    def client(*, timeout: httpx.Timeout, follow_redirects: bool) -> httpx.Client:
        return original_client(
            transport=httpx.MockTransport(handler),
            timeout=timeout,
            follow_redirects=follow_redirects,
        )

    monkeypatch.setattr(httpx, "Client", client)

    wfo_outcome = provision_index("wfo", state_dir, required_bytes=1024)
    assert wfo_outcome == ProvisionOutcome(status="ready")
    assert managed_wfo_path(state_dir).is_file()
    assert managed_wfo_path(state_dir).with_suffix(".sha256").is_file()
    assert not any(p.name.startswith(STAGING_PREFIX) for p in state_dir.iterdir())
    assert (
        wfo_source.WfoSource(managed_wfo_path(state_dir)).search("Solanum")[0].taxon.scientific_name
        == "Solanum lycopersicum"
    )

    wcvp_outcome = provision_index("wcvp_v16", state_dir, required_bytes=1024)
    assert wcvp_outcome == ProvisionOutcome(status="ready")
    assert managed_wcvp_v16_path(state_dir).is_file()
    assert managed_wcvp_v16_path(state_dir).with_suffix(".sha256").is_file()
    assert not (managed_wcvp_v16_path(state_dir).parent / "index.sqlite.lock").exists()
    assert not any(p.name.startswith(STAGING_PREFIX) for p in state_dir.iterdir())
    assert (
        wcvp_source.WcvpSource(managed_wcvp_v16_path(state_dir), "16", require_seal=True)
        .search("Solanum")[0]
        .name
        == "Solanum lycopersicum"
    )

    # Re-running against valid sealed indexes must not touch the network or overwrite files.
    downloads.clear()
    wfo_inode = managed_wfo_path(state_dir).stat().st_ino
    wcvp_inode = managed_wcvp_v16_path(state_dir).stat().st_ino
    assert provision_index("wfo", state_dir, required_bytes=1024) == ProvisionOutcome(
        status="ready"
    )
    assert provision_index("wcvp_v16", state_dir, required_bytes=1024) == ProvisionOutcome(
        status="ready"
    )
    assert downloads == []
    assert managed_wfo_path(state_dir).stat().st_ino == wfo_inode
    assert managed_wcvp_v16_path(state_dir).stat().st_ino == wcvp_inode


def test_worker_sigterm_leaves_no_partial_publish_and_cleans_staging(tmp_path: Path) -> None:
    """Real worker subprocess terminated mid-download via SIGTERM publishes nothing."""
    state_dir = tmp_path / "state" / "reference"
    started = threading.Event()
    release_server = threading.Event()

    class SlowHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", "132643291")
            self.end_headers()
            try:
                self.wfile.write(b"PK\x03\x04partial")
                self.wfile.flush()
            except OSError:
                return
            started.set()
            release_server.wait(timeout=15)

        def log_message(self, fmt: str, *args: object) -> None:
            return

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), SlowHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    bootstrap = (
        "import sys; "
        "from florabase.taxonomy import snapshot, source; "
        f"url = 'http://127.0.0.1:{port}/wfo.zip'; "
        "snapshot.ARCHIVE_URL = url; source.ARCHIVE_URL = url; "
        "from florabase.reference_setup import worker; "
        "raise SystemExit(worker.main())"
    )
    proc = subprocess.Popen(
        [
            sys.executable,
            "-c",
            bootstrap,
            "--index",
            "wfo",
            "--state-dir",
            str(state_dir),
            "--max-seconds",
            "60",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        assert started.wait(timeout=10), "worker did not start downloading"
        proc.send_signal(signal.SIGTERM)
        exit_code = proc.wait(timeout=10)
        assert exit_code != 0
    finally:
        release_server.set()
        server.shutdown()
        server.server_close()

    # No partial index or seal may exist, and staging directory is cleaned up.
    assert not managed_wfo_path(state_dir).exists()
    assert not managed_wfo_path(state_dir).with_suffix(".sha256").exists()
    assert not any(p.name.startswith(STAGING_PREFIX) for p in state_dir.iterdir())


def test_coordinator_off_retry_logging_and_stop(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    reset_runtime_state()
    off_settings = _settings(tmp_path, references_setup=ReferencesSetupMode.OFF)

    async def run_off() -> None:
        coordinator = ReferenceSetupCoordinator(off_settings)
        coordinator.start()
        assert coordinator.is_running is False
        await coordinator.stop()

    asyncio.run(run_off())
    assert not off_settings.references_state_dir.exists()

    # Failure -> single sanitized warning -> retry after interval -> succeeds -> stops idle loop.
    auto_settings = _settings(tmp_path, references_setup=ReferencesSetupMode.AUTO)
    attempts: dict[str, int] = {"wfo": 0, "wcvp_v16": 0}

    async def fake_worker(key: str, state_dir: Path, _max_seconds: float) -> ProvisionOutcome:
        attempts[key] += 1
        if attempts[key] == 1:
            return ProvisionOutcome(status="failed", reason="network")
        if key == "wfo":
            _build_valid_wfo(managed_wfo_path(state_dir))
        else:
            _build_valid_wcvp_v16(managed_wcvp_v16_path(state_dir), with_seal=True)
        return ProvisionOutcome(status="ready")

    async def run_retry() -> None:
        coordinator = ReferenceSetupCoordinator(
            auto_settings,
            retry_interval_seconds=0.05,
            worker_runner=fake_worker,
        )
        coordinator.start()
        assert coordinator.is_running is True
        deadline = time.monotonic() + 5.0
        while coordinator.is_running and time.monotonic() < deadline:
            await asyncio.sleep(0.02)
        assert coordinator.is_running is False  # Zero idle loop once ready.
        await coordinator.stop()

    with caplog.at_level(logging.WARNING, logger="florabase.reference_setup.runner"):
        asyncio.run(run_retry())

    assert attempts == {"wfo": 2, "wcvp_v16": 2}
    warnings = [
        record.getMessage() for record in caplog.records if record.levelno == logging.WARNING
    ]
    assert len(warnings) == 2
    assert any("wfo" in msg and "network" in msg for msg in warnings)
    assert any("wcvp_v16" in msg and "network" in msg for msg in warnings)
    for msg in warnings:
        assert "http" not in msg.lower()
        assert "zenodo" not in msg.lower()
        assert "kew" not in msg.lower()

    final = get_runtime_status(auto_settings)
    assert final.wfo.state == "ready"
    assert final.wcvp_v16.state == "ready"


def test_system_references_api_requires_auth_and_keeps_system_info_unchanged(
    tmp_path: Path,
) -> None:
    reset_runtime_state()
    settings = _settings(
        tmp_path,
        environment=Environment.PRODUCTION,
        canonical_origin="https://florabase.example",
        cookie_mode=CookieMode.SECURE,
        references_setup=ReferencesSetupMode.OFF,
    )
    with patch("florabase.main.get_settings", return_value=settings):
        app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app, base_url="https://florabase.example") as client:
        # /api/v1/system/info remains unauthenticated and unchanged.
        info = client.get("/api/v1/system/info")
        assert info.status_code == 200
        assert set(info.json()) == {
            "server_version",
            "api_version",
            "min_client_version",
            "capabilities",
        }

        # /api/v1/system/references rejects unauthenticated callers.
        unauth = client.get("/api/v1/system/references")
        assert unauth.status_code == 401

        app.dependency_overrides[require_authenticated_actor] = lambda: AuthenticatedActor(
            user_id=UUID("00000000-0000-7000-8000-000000000001"),
            login_name="owner",
            display_name="Owner",
            owner=True,
            session=MagicMock(),
            transport="cookie",
        )
        authed = client.get("/api/v1/system/references")
        assert authed.status_code == 200
        assert authed.headers["cache-control"] == "no-store"
        body = authed.json()
        assert body == {
            "mode": "off",
            "wfo": {"state": "off", "status": "off", "reason": None, "available": False},
            "wcvp_v16": {"state": "off", "status": "off", "reason": None, "available": False},
        }
        # No filesystem paths or upstream URLs leak in diagnostics.
        assert str(tmp_path) not in authed.text
        assert "zenodo" not in authed.text.lower()
        assert "kew" not in authed.text.lower()


def test_preparing_state_changes_unavailable_messages(tmp_path: Path) -> None:
    reset_runtime_state()
    settings = _settings(tmp_path, references_setup=ReferencesSetupMode.AUTO)
    mark_index_preparing("wfo")
    mark_index_preparing("wcvp_v16")
    with pytest.raises(wfo_source.SourceUnavailableError, match=PREPARING_UNAVAILABLE_MESSAGE):
        wfo_source.WfoSource.from_settings(settings).metadata()
    with pytest.raises(wcvp_source.SourceUnavailableError, match=PREPARING_UNAVAILABLE_MESSAGE):
        wcvp_source.WcvpSource.from_settings(settings, "16").metadata()
    reset_runtime_state()


def test_classify_failure_categories() -> None:
    assert classify_failure(DiskSpaceError("no space")) == "disk"
    assert classify_failure(ReferenceDownloadSizeError("too big")) == "size"
    assert classify_failure(ReferenceDownloadTimeoutError("timeout")) == "network"
    assert classify_failure(ReferenceDownloadContentTypeError("html")) == "network"
    assert classify_failure(ValueError("WFO archive checksum differs")) == "checksum"
    assert classify_failure(ValueError("Unexpected WFO schema")) == "build"


@pytest.mark.parametrize(
    "module_name",
    [
        "florabase.taxonomy.source",
        "florabase.native_range_enrichment.source",
        "florabase.reference_setup.worker",
        "florabase.reference_setup.runner",
    ],
)
def test_standalone_module_imports_have_no_cycles(module_name: str) -> None:
    result = subprocess.run(
        [sys.executable, "-c", f"import {module_name}"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_worker_cli_env_scrubbing_and_coordinator_stop_terminates_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Worker env scrubs DB and owner secrets.
    monkeypatch.setenv("FLORABASE_DB_PASSWORD", "super-secret")
    monkeypatch.setenv("PGPASSWORD", "super-secret")
    monkeypatch.setenv("FLORABASE_OWNER_PASSWORD", "owner-secret")
    monkeypatch.setenv("FLORABASE_DATABASE_URL", "postgresql://u:p@db/db")
    scrubbed = _worker_environment()
    assert "FLORABASE_DB_PASSWORD" not in scrubbed
    assert "PGPASSWORD" not in scrubbed
    assert "FLORABASE_OWNER_PASSWORD" not in scrubbed
    assert "FLORABASE_DATABASE_URL" not in scrubbed

    # Outcome parser covers valid ready, valid failed reason, and malformed fallback.
    assert _parse_worker_outcome(0, b'{"status": "ready"}\n') == ProvisionOutcome(status="ready")
    assert _parse_worker_outcome(1, b'{"status": "failed", "reason": "disk"}\n') == (
        ProvisionOutcome(status="failed", reason="disk")
    )
    assert _parse_worker_outcome(1, b"not-json\n") == ProvisionOutcome(
        status="failed", reason="build"
    )
    assert _parse_worker_outcome(0, b"") == ProvisionOutcome(status="ready")

    # worker.main() in-process against already-ready index returns 0 with JSON ready.
    state_dir = tmp_path / "state" / "reference"
    _build_valid_wfo(managed_wfo_path(state_dir))
    rc = worker_main(["--index", "wfo", "--state-dir", str(state_dir), "--max-seconds", "30"])
    assert rc == 0
    assert json.loads(capsys.readouterr().out.strip()) == {"status": "ready"}

    # Coordinator stop() terminates a running child subprocess cleanly on shutdown.
    async def run_stop_with_child() -> None:
        settings = _settings(tmp_path, references_setup=ReferencesSetupMode.AUTO)
        coordinator = ReferenceSetupCoordinator(settings)
        child = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            "import time; time.sleep(60)",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        coordinator._active_process = child
        await coordinator.stop()
        assert child.returncode is not None

    asyncio.run(run_stop_with_child())


def test_backup_and_deploy_paths_ignore_state_reference(tmp_path: Path) -> None:
    """state/reference/ never enters attachment archives and never breaks deploy() guards."""
    data_dir = tmp_path / "data"
    media_dir = data_dir / "media"
    state_dir = data_dir / "state"
    ref_dir = state_dir / "reference"
    backup_root = tmp_path / "backup"
    backup_dir = backup_root / "pre-upgrade"
    for d in (media_dir, state_dir, backup_dir):
        d.mkdir(parents=True)

    # Populate state/reference/ with valid sealed indexes.
    _build_valid_wfo(managed_wfo_path(ref_dir))
    _build_valid_wcvp_v16(managed_wcvp_v16_path(ref_dir), with_seal=True)
    # Populate one attachment object in media/objects/.
    obj_dir = media_dir / "objects" / "ab"
    obj_dir.mkdir(parents=True)
    (obj_dir / ("ab" + "0" * 30)).write_bytes(b"image-bytes")

    # 1. Attachment archive must exclude state/reference/ completely.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    try:
        import attachment_artifacts
    finally:
        sys.path.pop(0)

    members = [
        p.relative_to(media_dir).as_posix()
        for p in attachment_artifacts.iter_archive_paths(media_dir)
    ]
    assert members == ["objects", "objects/ab", "objects/ab/" + "ab" + "0" * 30]
    assert not any("reference" in m or "sqlite" in m for m in members)

    # Verify tar output bytes also contain no reference files.
    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode="w") as tf:
        for path in attachment_artifacts.iter_archive_paths(media_dir):
            tf.add(path, arcname=path.relative_to(media_dir).as_posix(), recursive=False)
    tar_buf.seek(0)
    with tarfile.open(fileobj=tar_buf, mode="r") as tf:
        names = tf.getnames()
    assert not any("reference" in n or "sqlite" in n for n in names)

    # 2. release_schema.read_marker / check_upgrade_failed ignore state/reference/.
    release_schema.check_upgrade_failed(state_dir)
    assert release_schema.read_marker(state_dir) is None
    release_schema.write_marker(
        state_dir,
        {"FLORABASE_PG_MAJOR": "18", "FLORABASE_PG_SYSTEM_ID": "123456789"},
    )
    marker = release_schema.read_marker(state_dir)
    assert marker is not None
    assert marker["FLORABASE_PG_MAJOR"] == "18"
    assert managed_wfo_path(ref_dir).is_file()
    assert managed_wcvp_v16_path(ref_dir).is_file()
