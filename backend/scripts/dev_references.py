"""Provision and verify the primary DEV reference cache without touching PostgreSQL."""

# ruff: noqa: T201
import argparse
import fcntl
import hashlib
import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path

import httpx

from florabase.core.config import get_settings
from florabase.core.reference_index import open_reference_index
from florabase.native_range_enrichment.snapshot import download, install_archive
from florabase.native_range_enrichment.source import (
    SCHEMA,
    WcvpSource,
    WcvpVersion,
)
from florabase.native_range_enrichment.source import (
    SourceUnavailableError as WcvpUnavailable,
)
from florabase.taxonomy.source import SourceUnavailableError as WfoUnavailable
from florabase.taxonomy.source import WfoSource

CACHE = Path("/app/src/.source-cache")
WFO_DIGEST = "ac49e6348c71810a3f90ff5ba40e390faf95a6835155c13e80c79a8cc0528126"
WCVP_COUNTS = {"15": (1_441_152, 1_986_879), "16": (1_448_984, 1_995_338)}
PROBE = "Solanum lycopersicum"


def cache_path(path: Path | None) -> Path:
    if path is None or not path.is_relative_to(CACHE) or path.resolve() != path:
        raise ValueError(f"Expected a non-symlink reference path inside {CACHE}: {path}")
    return path


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check_integrity(connection: sqlite3.Connection) -> None:
    if [row[0] for row in connection.execute("PRAGMA integrity_check")] != ["ok"]:
        raise ValueError("SQLite integrity check failed")


def verify_wfo(path: Path) -> None:
    seal = path.with_suffix(".sha256")
    if seal.is_symlink() or not seal.is_file() or seal.stat().st_size != 65:
        raise ValueError("WFO seal is missing or invalid")
    if seal.read_text(encoding="ascii").strip() != WFO_DIGEST:
        raise ValueError("WFO seal does not match the reviewed 2026-06 index digest")
    source = WfoSource(path)
    metadata = source.metadata()
    with closing(source.connect()) as connection:
        check_integrity(connection)
    match = next(
        (
            candidate.taxon
            for candidate in source.search(PROBE)
            if candidate.taxon.scientific_name == PROBE
            and candidate.taxon.taxonomic_status == "accepted"
            and candidate.classification
        ),
        None,
    )
    if match is None:
        raise ValueError(f"WFO accepted-taxon probe failed for {PROBE}")
    print(f"WFO {metadata.version}: {match.scientific_name} ({match.source_taxon_id})")


def verify_wcvp(path: Path, version: WcvpVersion) -> None:
    source = WcvpSource(path, version, require_seal=version == "16")
    metadata = source.metadata()
    with closing(open_reference_index(path, SCHEMA, "WCVP")) as connection:
        check_integrity(connection)
        taxa, distributions = connection.execute(
            "SELECT (SELECT count(*) FROM taxa), (SELECT count(*) FROM distributions)"
        ).fetchone()
    if (taxa, distributions) != WCVP_COUNTS[version]:
        raise ValueError(f"WCVP v{version} does not contain the full reviewed release")
    match = next(
        (taxon for taxon in source.search(PROBE) if taxon.name == PROBE and taxon.eligible),
        None,
    )
    if match is None:
        raise ValueError(f"WCVP v{version} accepted-taxon probe failed for {PROBE}")
    print(
        f"WCVP v{version}: {taxa:,} taxa, {distributions:,} distributions, "
        f"{match.name} ({match.external_id}), archive SHA-256 {metadata.checksum}"
    )


def setup_wcvp(destination: Path) -> None:
    # Stage the index and local digest together so interruption cannot publish an unsealed index.
    if destination.parent.parent != CACHE or destination.suffix != ".sqlite":
        raise ValueError("WCVP v16 requires its own bundle directory directly inside the cache")
    fd = os.open(CACHE / ".dev-references.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if destination.parent.exists():
            verify_wcvp(destination, "16")
            print("Reused the existing WCVP v16 bundle.")
            return
        with tempfile.TemporaryDirectory(prefix=".wcvp-v16-", dir=CACHE) as staging:
            bundle = Path(staging)
            index = bundle / destination.name
            archive = os.environ.get("WCVP_ARCHIVE")
            retrieved_at = os.environ.get("WCVP_RETRIEVED_AT")
            if archive and retrieved_at:
                install_archive(cache_path(CACHE / archive), index, retrieved_at, "16")
            elif archive or retrieved_at:
                raise ValueError("Provide both WCVP_ARCHIVE and its actual WCVP_RETRIEVED_AT")
            else:
                download(index, "16")
            index.with_suffix(".sha256").write_text(digest(index) + "\n", encoding="ascii")
            verify_wcvp(index, "16")
            bundle.rename(destination.parent)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "setup", "verify"))
    args = parser.parse_args()
    try:
        settings = get_settings()
        wfo = cache_path(settings.wfo_snapshot_path)
        v16 = cache_path(settings.wcvp_v16_snapshot_path)
        v15 = cache_path(settings.wcvp_snapshot_path)
        if args.action == "status":
            for label, path in (
                ("WFO 2026-06", wfo),
                ("WCVP v16", v16),
                ("WCVP v15 (optional)", v15),
            ):
                state = "present (unverified)" if path.is_file() else "unavailable"
                print(f"{label}: {state} at {path}")
            return 0
        verify_wfo(wfo)
        if args.action == "setup":
            setup_wcvp(v16)
        else:
            verify_wcvp(v16, "16")
            if v15.exists():
                verify_wcvp(v15, "15")
            else:
                print("WCVP v15: optional index unavailable")
    except (
        OSError,
        ValueError,
        sqlite3.Error,
        httpx.HTTPError,
        WcvpUnavailable,
        WfoUnavailable,
    ) as error:
        print(f"DEV references: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
