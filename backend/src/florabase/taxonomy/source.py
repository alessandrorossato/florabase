"""Pinned optional local reference index. No runtime provider access."""

import hashlib
import json
import sqlite3
from collections.abc import Sequence
from contextlib import closing
from functools import lru_cache
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict

VERSION: Final = "2026-06"
ARCHIVE_URL = "https://zenodo.org/api/records/20782718/files/wfo_plantlist_2026-06.zip/content"
CHECKSUM: Final = "75f1ad1f371978c9e46f3044152c07ed276fe57be9fb9a15b3621b19cf231987"
ROOT = "wfo-4100001250"
CODE = "wfo-9971000003"
RANKS = frozenset(
    [
        "species",
        "variety",
        "subspecies",
        "form",
        "genus",
        "section",
        "subvariety",
        "unranked",
        "subgenus",
        "family",
        "prole",
        "tribe",
        "subtribe",
        "series",
        "subsection",
        "subfamily",
        "subform",
        "order",
        "lusus",
        "subseries",
        "suborder",
        "subclass",
        "class",
        "supertribe",
        "phylum",
        "convar",
        "superorder",
        "subkingdom",
        "kingdom",
    ]
)


class SourceUnavailableError(Exception):
    pass


class WfoMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["wfo"] = "wfo"
    version: str = VERSION
    checksum: str = CHECKSUM
    archive_url: str = ARCHIVE_URL
    license: str = "https://creativecommons.org/publicdomain/zero/1.0/"
    citation: str = "World Flora Online (2026). World Flora Online Plant List 2026-06. https://doi.org/10.5281/zenodo.20782718"
    retrieved_at: str
    format_version: Literal[1] = 1


class WfoTaxon(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_taxon_id: str
    parent_source_taxon_id: str | None
    scientific_name: str
    authorship: str
    rank: str
    taxonomic_status: Literal["accepted", "synonym", "unplaced"]
    accepted_source_taxon_id: str | None


class WfoCandidate(BaseModel):
    taxon: WfoTaxon
    classification: list[WfoTaxon]


@lru_cache(maxsize=4)
def verified_index(path: Path, modified: int, size: int, seal_modified: int) -> None:
    # Cache by immutable artifact identity; reprovision/corruption invalidates the check.
    seal = path.with_suffix(".sha256").read_text().strip()
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != seal:
            raise SourceUnavailableError("The WFO source index checksum is invalid.")


class WfoSource:
    def __init__(self, path: Path | None):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        if self.path is None or not self.path.is_file() or self.path.stat().st_size > 1_000_000_000:
            raise SourceUnavailableError("The reviewed WFO taxonomy source is not installed.")
        try:
            stat = self.path.stat()
            verified_index(
                self.path,
                stat.st_mtime_ns,
                stat.st_size,
                self.path.with_suffix(".sha256").stat().st_mtime_ns,
            )
        except OSError as error:
            raise SourceUnavailableError(
                "The WFO source index validation seal is missing."
            ) from error
        connection = sqlite3.connect(f"{self.path.resolve().as_uri()}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    def metadata(self) -> WfoMetadata:
        try:
            with closing(self.connect()) as db:
                row = db.execute("SELECT payload FROM metadata").fetchone()
                if row is None:
                    raise ValueError("Missing metadata")
                result = WfoMetadata.model_validate_json(row[0])
                if result != WfoMetadata(retrieved_at=result.retrieved_at):
                    raise ValueError("Unreviewed source metadata")
                return result
        except (OSError, ValueError, sqlite3.Error) as error:
            raise SourceUnavailableError(
                "The WFO taxonomy source is unavailable or invalid."
            ) from error

    def hierarchy(self, identifiers: Sequence[str]) -> dict[str, WfoTaxon]:
        self.metadata()
        try:
            with closing(self.connect()) as db:
                rows = db.execute(
                    "WITH RECURSIVE wanted(id) AS ("
                    "SELECT value FROM json_each(?) UNION "
                    "SELECT CASE WHEN t.taxonomic_status='synonym' "
                    "THEN t.accepted_source_taxon_id ELSE t.parent_source_taxon_id END "
                    "FROM taxa t JOIN wanted w ON t.source_taxon_id=w.id) "
                    "SELECT t.* FROM taxa t JOIN wanted w ON w.id=t.source_taxon_id",
                    (json.dumps(list(identifiers)),),
                ).fetchall()
                if len(rows) > 100_000:
                    raise ValueError("Hierarchy exceeds collection bound")
                return {
                    row["source_taxon_id"]: WfoTaxon.model_validate(
                        {k: row[k] for k in WfoTaxon.model_fields}
                    )
                    for row in rows
                }
        except (OSError, ValueError, sqlite3.Error) as error:
            raise SourceUnavailableError("The WFO hierarchy cannot be read.") from error

    def search(self, query: str) -> list[WfoCandidate]:
        self.metadata()
        prefix = query.strip().casefold()
        try:
            with closing(self.connect()) as db:
                rows = db.execute(
                    "SELECT source_taxon_id FROM taxa WHERE search_name >= ? AND search_name < ? "
                    "ORDER BY search_name, authorship, source_taxon_id LIMIT 25",
                    (prefix, prefix + chr(0x10FFFF)),
                ).fetchall()
            ids = [row[0] for row in rows]
            nodes = self.hierarchy(ids)
            return [WfoCandidate(taxon=nodes[i], classification=path(nodes, i)) for i in ids]
        except (OSError, ValueError, sqlite3.Error) as error:
            raise SourceUnavailableError("The WFO source cannot be searched.") from error


def path(nodes: dict[str, WfoTaxon], identifier: str) -> list[WfoTaxon]:
    """Accepted biological path; retain synonym evidence separately and raw Code parent."""
    taxon = nodes.get(identifier)
    if taxon is None or taxon.taxonomic_status == "unplaced":
        return []
    current = taxon.accepted_source_taxon_id if taxon.taxonomic_status == "synonym" else identifier
    result: list[WfoTaxon] = []
    seen: set[str] = set()
    while current:
        if current in seen or len(result) >= 64:
            raise SourceUnavailableError("The WFO hierarchy is cyclic or exceeds its depth bound.")
        seen.add(current)
        node = nodes.get(current)
        if node is None or node.taxonomic_status != "accepted":
            raise SourceUnavailableError("The WFO hierarchy has an unresolved parent.")
        result.append(node)
        if current == ROOT:
            if node.parent_source_taxon_id != CODE or node.rank != "kingdom":
                raise SourceUnavailableError("The reviewed WFO root boundary has changed.")
            return list(reversed(result))
        current = node.parent_source_taxon_id
    raise SourceUnavailableError("The WFO hierarchy does not reach its reviewed root.")
