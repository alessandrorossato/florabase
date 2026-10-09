"""Explicit installation from an already downloaded reviewed official archive."""

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sqlite3
import tempfile
from collections.abc import Iterable, Iterator
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

from florabase.taxonomy.source import CHECKSUM, CODE, RANKS, ROOT, WfoMetadata

FIELDS = {
    "name.tsv": [
        "ID",
        "alternativeID",
        "basionymID",
        "scientificName",
        "authorship",
        "rank",
        "uninomial",
        "genus",
        "infragenericEpithet",
        "specificEpithet",
        "infraspecificEpithet",
        "code",
        "referenceID",
        "publishedInYear",
        "link",
    ],
    "taxon.tsv": [
        "ID",
        "alternativeID",
        "nameID",
        "parentID",
        "accordingToID",
        "scrutinizer",
        "scrutinizerID",
        "scrutinizerDate",
        "referenceID",
        "extinct",
        "link",
    ],
    "synonym.tsv": ["ID", "taxonID", "nameID", "accordingToID", "referenceID", "link"],
}
MEMBERS = {
    "name.tsv": 380612911,
    "reference.tsv": 321277092,
    "synonym.tsv": 121225634,
    "taxon.tsv": 96789455,
    "typematerial.tsv": 55447515,
    "metadata.json": 109295,
}


def rows(archive: ZipFile, member: str) -> Iterator[dict[str, str]]:
    reader = csv.DictReader(
        io.TextIOWrapper(archive.open(member), encoding="utf-8", errors="strict", newline=""),
        delimiter="\t",
        strict=True,
    )
    if reader.fieldnames != FIELDS[member]:
        raise ValueError("Unexpected WFO schema")
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise ValueError("Malformed WFO row")
        yield row


def identifier(value: str) -> str:
    if re.fullmatch(r"wfo-[0-9]{10}", value) is None:
        raise ValueError("Invalid or missing WFO identifier")
    return value


def build_index(
    destination: Path,
    names: Iterable[dict[str, str]],
    concepts: Iterable[dict[str, str]],
    synonyms: Iterable[dict[str, str]],
    metadata: WfoMetadata,
) -> None:
    timestamp = datetime.fromisoformat(metadata.retrieved_at)
    if timestamp.tzinfo is None:
        raise ValueError("Retrieval timestamp requires a timezone")
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(dir=destination.parent, suffix=".sqlite")
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        with sqlite3.connect(temporary) as db:
            # Unpublished temporary artifact; validation failures preserve the working source.
            db.executescript(
                "PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;"
                "CREATE TABLE metadata(payload TEXT NOT NULL);"
                "CREATE TABLE taxa(source_taxon_id TEXT PRIMARY KEY, "
                "parent_source_taxon_id TEXT, scientific_name TEXT NOT NULL, "
                "authorship TEXT NOT NULL, "
                "rank TEXT NOT NULL, taxonomic_status TEXT NOT NULL, "
                "accepted_source_taxon_id TEXT, "
                "search_name TEXT NOT NULL);"
                "CREATE TABLE concepts(id TEXT PRIMARY KEY, parent TEXT NOT NULL);"
                "CREATE TABLE synonyms(id TEXT PRIMARY KEY, name TEXT UNIQUE NOT NULL, "
                "accepted TEXT NOT NULL);"
            )
            db.execute("INSERT INTO metadata VALUES (?)", (metadata.model_dump_json(),))
            for row in names:
                ident = identifier(row["ID"])
                name = row["scientificName"]
                if not name or len(name) > 1000 or row["rank"] not in RANKS:
                    raise ValueError("Unexpected WFO name or rank")
                if any(ord(c) < 32 or ord(c) == 127 for c in name + row["authorship"]):
                    raise ValueError("WFO name contains control characters")
                db.execute(
                    "INSERT INTO taxa VALUES (?,NULL,?,?,?,'unplaced',NULL,?)",
                    (ident, name, row["authorship"], row["rank"], name.casefold()),
                )
            for row in concepts:
                ident, parent = identifier(row["ID"]), identifier(row["parentID"])
                if ident != row["nameID"] or ident == parent:
                    raise ValueError("Unexpected WFO concept or self-parent")
                db.execute("INSERT INTO concepts VALUES (?,?)", (ident, parent))
            for row in synonyms:
                name, accepted = identifier(row["nameID"]), identifier(row["taxonID"])
                if row["ID"] != name + "-2026-06" or name == accepted:
                    raise ValueError("Malformed WFO synonym reference")
                db.execute("INSERT INTO synonyms VALUES (?,?,?)", (row["ID"], name, accepted))
            for sql in (
                "SELECT 1 FROM concepts c LEFT JOIN taxa t ON "
                "t.source_taxon_id=c.id WHERE t.source_taxon_id IS NULL",
                "SELECT 1 FROM concepts c LEFT JOIN concepts p ON "
                "p.id=c.parent WHERE p.id IS NULL AND NOT (c.id='"
                + ROOT
                + "' AND c.parent='"
                + CODE
                + "')",
                "SELECT 1 FROM synonyms s LEFT JOIN concepts c ON "
                "c.id=s.accepted LEFT JOIN taxa t ON t.source_taxon_id=s.name "
                "WHERE c.id IS NULL OR t.source_taxon_id IS NULL",
                "SELECT 1 FROM synonyms s JOIN concepts c ON c.id=s.name",
            ):
                if db.execute(sql + " LIMIT 1").fetchone():
                    raise ValueError("WFO has an invalid parent, name or accepted reference")
            root = db.execute(
                "SELECT scientific_name,rank FROM taxa JOIN concepts ON id=source_taxon_id "
                "WHERE id=? AND parent=?",
                (ROOT, CODE),
            ).fetchone()
            if root != ("Plantae", "kingdom"):
                raise ValueError("Reviewed WFO root boundary is missing")
            parents = dict(db.execute("SELECT id,parent FROM concepts"))
            done = {CODE}
            for node in parents:
                seen: set[str] = set()
                current = node
                while current not in done:
                    if current in seen or current not in parents or len(seen) >= 64:
                        raise ValueError("WFO has a cycle, orphan or unsupported depth")
                    seen.add(current)
                    current = parents[current]
                done.update(seen)
            db.execute(
                "UPDATE taxa SET "
                "taxonomic_status='accepted',accepted_source_taxon_id=source_taxon_id, "
                "parent_source_taxon_id=(SELECT parent FROM concepts WHERE id=source_taxon_id) "
                "WHERE source_taxon_id IN (SELECT id FROM concepts)"
            )
            db.execute(
                "UPDATE taxa SET taxonomic_status='synonym', "
                "accepted_source_taxon_id=(SELECT accepted FROM synonyms WHERE "
                "name=source_taxon_id) "
                "WHERE source_taxon_id IN (SELECT name FROM synonyms)"
            )
            db.executescript(
                "DROP TABLE concepts; DROP TABLE synonyms;"
                "CREATE INDEX search_taxa ON taxa(search_name,authorship,source_taxon_id);"
            )
        if temporary.stat().st_size > 1_000_000_000:
            raise ValueError("WFO index exceeds disk bound")
        temporary.chmod(0o600)
        with temporary.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        os.replace(temporary, destination)
        seal = destination.with_suffix(".sha256")
        seal.write_text(digest + "\n")
        seal.chmod(0o600)
    finally:
        temporary.unlink(missing_ok=True)


def install(archive_path: Path, destination: Path, retrieved_at: str) -> None:
    if archive_path.stat().st_size != 132643291:
        raise ValueError("Unexpected WFO archive size")
    with archive_path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != CHECKSUM:
            raise ValueError("WFO archive checksum differs from reviewed release")
    with ZipFile(archive_path) as archive:
        members = archive.infolist()
        if len(members) != len(MEMBERS) or {m.filename: m.file_size for m in members} != MEMBERS:
            raise ValueError("Unexpected WFO archive members")
        if any(m.is_dir() or m.flag_bits & 1 for m in members):
            raise ValueError("Unsupported WFO archive member")
        metadata = json.loads(archive.read("metadata.json"))
        if (metadata.get("version"), metadata.get("issued"), metadata.get("license")) != (
            "2026-06 01",
            "2026-06-21",
            "cc0",
        ):
            raise ValueError("Unexpected WFO release metadata")
        build_index(
            destination,
            rows(archive, "name.tsv"),
            rows(archive, "taxon.tsv"),
            rows(archive, "synonym.tsv"),
            WfoMetadata(retrieved_at=retrieved_at),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--retrieved-at", required=True)
    args = parser.parse_args()
    install(args.archive, args.destination, args.retrieved_at)


if __name__ == "__main__":
    main()
