"""Explicit provisioning CLI for the reviewed archive; independent of application startup."""

import argparse
import csv
import hashlib
import io
import json
import os
import sqlite3
import tempfile
import time
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

import httpx

from florabase.native_range_enrichment.source import (
    ARCHIVE_SHA256,
    ARCHIVE_URL,
    SourceMetadata,
    Taxon,
)

NAMES_FIELDS = [
    "plant_name_id",
    "ipni_id",
    "taxon_rank",
    "taxon_status",
    "family",
    "genus_hybrid",
    "genus",
    "species_hybrid",
    "species",
    "infraspecific_rank",
    "infraspecies",
    "parenthetical_author",
    "primary_author",
    "publication_author",
    "place_of_publication",
    "volume_and_page",
    "first_published",
    "nomenclatural_remarks",
    "geographic_area",
    "lifeform_description",
    "climate_description",
    "taxon_name",
    "taxon_authors",
    "accepted_plant_name_id",
    "basionym_plant_name_id",
    "replaced_synonym_author",
    "homotypic_synonym",
    "parent_plant_name_id",
    "powo_id",
    "hybrid_formula",
    "reviewed",
]
DISTRIBUTION_FIELDS = [
    "plant_locality_id",
    "plant_name_id",
    "continent_code_l1",
    "continent",
    "region_code_l2",
    "region",
    "area_code_l3",
    "area",
    "introduced",
    "extinct",
    "location_doubtful",
]
MAX_ARCHIVE_BYTES = 100_000_000


def csv_rows(archive: ZipFile, name: str, fields: list[str]) -> Iterator[dict[str, str]]:
    with archive.open(name) as stream:
        reader = csv.reader(
            io.TextIOWrapper(stream, encoding="utf-8-sig"), delimiter="|", quoting=csv.QUOTE_NONE
        )
        if next(reader) != fields:
            raise ValueError("Unreviewed WCVP schema")
        for row in reader:
            if len(row) != len(fields) or any(len(value) > 20_000 for value in row):
                raise ValueError("Malformed WCVP row")
            yield dict(zip(fields, row, strict=True))


def build_index(
    destination: Path,
    names: Iterable[dict[str, str]],
    distributions: Iterable[dict[str, str]],
    metadata: SourceMetadata,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix="wcvp-", suffix=".sqlite", dir=destination.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with sqlite3.connect(temporary) as connection:
            connection.executescript(
                "CREATE TABLE metadata(payload TEXT NOT NULL);"
                "CREATE TABLE taxa(external_id TEXT PRIMARY KEY, name TEXT NOT NULL, "
                "authorship TEXT NOT NULL,"
                "rank TEXT NOT NULL, status TEXT NOT NULL, accepted_id TEXT NOT NULL, "
                "powo_id TEXT NOT NULL,"
                "reviewed TEXT NOT NULL, search_name TEXT NOT NULL COLLATE NOCASE);"
                "CREATE TABLE distributions(locality_id TEXT PRIMARY KEY, "
                "external_id TEXT NOT NULL, payload TEXT NOT NULL);"
            )
            connection.execute("INSERT INTO metadata VALUES (?)", (metadata.model_dump_json(),))
            for row in names:
                taxon = Taxon(
                    external_id=row["plant_name_id"],
                    name=row["taxon_name"],
                    authorship=row["taxon_authors"],
                    rank=row["taxon_rank"],
                    status=row["taxon_status"],
                    accepted_id=row["accepted_plant_name_id"],
                    powo_id=row["powo_id"],
                    reviewed=row["reviewed"],
                )
                if not taxon.external_id or not taxon.name:
                    raise ValueError("Missing WCVP identifier/name")
                connection.execute(
                    "INSERT INTO taxa VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        taxon.external_id,
                        taxon.name,
                        taxon.authorship,
                        taxon.rank,
                        taxon.status,
                        taxon.accepted_id,
                        taxon.powo_id,
                        taxon.reviewed,
                        taxon.name.casefold(),
                    ),
                )
            for row in distributions:
                if any(
                    row[f] not in {"0", "1"} for f in ("introduced", "extinct", "location_doubtful")
                ):
                    raise ValueError("Unreviewed WCVP distribution flags")
                connection.execute(
                    "INSERT INTO distributions VALUES (?, ?, ?)",
                    (row["plant_locality_id"], row["plant_name_id"], json.dumps(row)),
                )
            connection.executescript(
                "CREATE INDEX taxa_search ON taxa(search_name, external_id);"
                "CREATE INDEX distribution_taxon ON distributions(external_id, locality_id);"
            )
            if connection.execute(
                "SELECT 1 FROM distributions d LEFT JOIN taxa t ON t.external_id=d.external_id "
                "WHERE t.external_id IS NULL LIMIT 1"
            ).fetchone():
                raise ValueError("Distribution refers to a missing taxon")
        if temporary.stat().st_size > 2_000_000_000:
            raise ValueError("WCVP index exceeds disk bound")
        temporary.chmod(0o600)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def install_archive(archive_path: Path, destination: Path, retrieved_at: str) -> None:
    if archive_path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("WCVP archive exceeds size bound")
    with archive_path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != ARCHIVE_SHA256:
            raise ValueError("WCVP archive checksum does not match reviewed version 15")
    with ZipFile(archive_path) as archive:
        expected = {
            "README_WCVP.xlsx": 17_827,
            "wcvp_names.csv": 298_218_467,
            "wcvp_distribution.csv": 141_066_449,
        }
        members = archive.infolist()
        if len(members) != 3 or {m.filename: m.file_size for m in members} != expected:
            raise ValueError("Unexpected WCVP archive contents")
        if any(m.flag_bits & 1 or m.is_dir() for m in members):
            raise ValueError("Unsupported WCVP archive member")
        # The exact reviewed checksum pins README/version/schema.
        # Members are streamed, never extracted.
        build_index(
            destination,
            csv_rows(archive, "wcvp_names.csv", NAMES_FIELDS),
            csv_rows(archive, "wcvp_distribution.csv", DISTRIBUTION_FIELDS),
            SourceMetadata(retrieved_at=retrieved_at),
        )


def download(destination: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="florabase-wcvp-") as directory:
        archive = Path(directory) / "wcvp.zip"
        size = 0
        started = time.monotonic()
        with (
            httpx.Client(timeout=httpx.Timeout(60, connect=10), follow_redirects=False) as client,
            client.stream("GET", ARCHIVE_URL, headers={"Accept": "application/zip"}) as response,
        ):
            response.raise_for_status()
            if response.headers.get("content-type", "").split(";")[0] not in {
                "application/zip",
                "application/octet-stream",
            }:
                raise ValueError("Unexpected archive content type")
            with archive.open("wb") as output:
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > MAX_ARCHIVE_BYTES or time.monotonic() - started > 240:
                        raise ValueError("WCVP download exceeds size bound")
                    output.write(chunk)
        install_archive(archive, destination, datetime.now(UTC).isoformat())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--archive", type=Path, help="Already downloaded exact official archive")
    parser.add_argument(
        "--retrieved-at", help="Actual archive retrieval timestamp (required with --archive)"
    )
    args = parser.parse_args()
    if args.archive:
        if not args.retrieved_at:
            parser.error("--archive requires the actual --retrieved-at timestamp")
        install_archive(args.archive, args.destination, args.retrieved_at)
    else:
        download(args.destination)


if __name__ == "__main__":
    main()
