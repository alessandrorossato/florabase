"""Pinned optional local reference index. No runtime provider access."""

import hashlib
import json
import sqlite3
from collections.abc import Sequence
from contextlib import closing
from functools import lru_cache
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from florabase.core.reference_index import (
    SchemaContract,
    UnsupportedIndexError,
    open_reference_index,
)

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


# The one layout taxonomy.snapshot.build_index writes (metadata format_version 1).
SCHEMA: Final[SchemaContract] = frozenset(
    {
        ("table", "metadata", "metadata", "CREATE TABLE metadata(payload TEXT NOT NULL)"),
        (
            "table",
            "taxa",
            "taxa",
            "CREATE TABLE taxa(source_taxon_id TEXT PRIMARY KEY, parent_source_taxon_id TEXT, "
            "scientific_name TEXT NOT NULL, authorship TEXT NOT NULL, rank TEXT NOT NULL, "
            "taxonomic_status TEXT NOT NULL, accepted_source_taxon_id TEXT, "
            "search_name TEXT NOT NULL)",
        ),
        ("index", "sqlite_autoindex_taxa_1", "taxa", None),
        (
            "index",
            "search_taxa",
            "taxa",
            "CREATE INDEX search_taxa ON taxa(search_name,authorship,source_taxon_id)",
        ),
    }
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


class WfoExactBatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metadata: WfoMetadata
    matches: dict[str, list[WfoCandidate]]
    truncated_keys: frozenset[str] = Field(default_factory=frozenset)
    path_errors: dict[str, str] = Field(default_factory=dict)


_EXACT_BATCH_CHUNK: Final = 100
_MAX_LIMIT_PER_NAME: Final = 200
_MAX_PREFIX_KEYS: Final = 2000
_MAX_LIMIT_PER_PREFIX: Final = 25


@lru_cache(maxsize=4)
def verified_index(path: Path, modified: int, size: int, seal_modified: int) -> None:
    # Cache by immutable artifact identity; reprovision/corruption invalidates the check.
    seal = path.with_suffix(".sha256").read_text().strip()
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != seal:
            raise SourceUnavailableError("The WFO source index checksum is invalid.")


def _normalize_batch_keys(names: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    keys: list[str] = []
    for raw in names:
        key = raw.strip().casefold()
        if key and key not in seen:
            seen.add(key)
            keys.append(key)
    return keys


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
        try:
            return open_reference_index(self.path, SCHEMA, "WFO")
        except UnsupportedIndexError as error:
            raise SourceUnavailableError(
                "The WFO source index is not a supported index built by Florabase's WFO builder."
            ) from error

    def _read_metadata(self, db: sqlite3.Connection) -> WfoMetadata:
        row = db.execute("SELECT payload FROM metadata").fetchone()
        if row is None:
            raise ValueError("Missing metadata")
        result = WfoMetadata.model_validate_json(row[0])
        if result != WfoMetadata(retrieved_at=result.retrieved_at):
            raise ValueError("Unreviewed source metadata")
        return result

    def _hierarchy_on(
        self, db: sqlite3.Connection, identifiers: Sequence[str]
    ) -> dict[str, WfoTaxon]:
        if not identifiers:
            return {}
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

    def metadata(self) -> WfoMetadata:
        try:
            with closing(self.connect()) as db:
                return self._read_metadata(db)
        except (OSError, ValueError, sqlite3.Error) as error:
            raise SourceUnavailableError(
                "The WFO taxonomy source is unavailable or invalid."
            ) from error

    def hierarchy(self, identifiers: Sequence[str]) -> dict[str, WfoTaxon]:
        try:
            with closing(self.connect()) as db:
                self._read_metadata(db)
                return self._hierarchy_on(db, identifiers)
        except (OSError, ValueError, sqlite3.Error) as error:
            raise SourceUnavailableError("The WFO hierarchy cannot be read.") from error

    def search(self, query: str) -> list[WfoCandidate]:
        prefix = query.strip().casefold()
        try:
            with closing(self.connect()) as db:
                self._read_metadata(db)
                rows = db.execute(
                    "SELECT source_taxon_id FROM taxa WHERE search_name >= ? AND search_name < ? "
                    "ORDER BY search_name, authorship, source_taxon_id LIMIT 25",
                    (prefix, prefix + chr(0x10FFFF)),
                ).fetchall()
                ids = [row[0] for row in rows]
                nodes = self._hierarchy_on(db, ids)
                return [WfoCandidate(taxon=nodes[i], classification=path(nodes, i)) for i in ids]
        except (OSError, ValueError, sqlite3.Error) as error:
            raise SourceUnavailableError("The WFO source cannot be searched.") from error

    def exact_matches_with_context(
        self, names: Sequence[str], *, limit_per_name: int = 50
    ) -> WfoExactBatchResult:
        if not 1 <= limit_per_name <= _MAX_LIMIT_PER_NAME:
            raise ValueError(f"limit_per_name must be between 1 and {_MAX_LIMIT_PER_NAME}")
        keys = _normalize_batch_keys(names)
        try:
            with closing(self.connect()) as db:
                metadata = self._read_metadata(db)
                if not keys:
                    return WfoExactBatchResult(metadata=metadata, matches={})
                ids_by_key: dict[str, list[str]] = {key: [] for key in keys}
                truncated: set[str] = set()
                all_ids: list[str] = []
                seen_ids: set[str] = set()
                for offset in range(0, len(keys), _EXACT_BATCH_CHUNK):
                    chunk = keys[offset : offset + _EXACT_BATCH_CHUNK]
                    placeholders = ",".join("?" for _ in chunk)
                    rows = db.execute(
                        f"WITH ranked AS ("
                        f"SELECT search_name, source_taxon_id, "
                        f"ROW_NUMBER() OVER ("
                        f"PARTITION BY search_name ORDER BY authorship, source_taxon_id"
                        f") AS row_num "
                        f"FROM taxa WHERE search_name IN ({placeholders})"
                        f") "
                        f"SELECT search_name, source_taxon_id FROM ranked "
                        f"WHERE row_num <= ? ORDER BY search_name, row_num",
                        (*chunk, limit_per_name + 1),
                    ).fetchall()
                    for row in rows:
                        key = str(row["search_name"])
                        taxon_id = str(row["source_taxon_id"])
                        bucket = ids_by_key.setdefault(key, [])
                        if len(bucket) >= limit_per_name:
                            truncated.add(key)
                            continue
                        bucket.append(taxon_id)
                        if taxon_id not in seen_ids:
                            seen_ids.add(taxon_id)
                            all_ids.append(taxon_id)
                nodes = self._hierarchy_on(db, all_ids)
        except (OSError, ValueError, sqlite3.Error) as error:
            raise SourceUnavailableError("The WFO source cannot be searched.") from error

        matches: dict[str, list[WfoCandidate]] = {}
        path_errors: dict[str, str] = {}
        for key in keys:
            candidates: list[WfoCandidate] = []
            for taxon_id in ids_by_key.get(key, ()):
                classification, error_message = safe_path(nodes, taxon_id)
                if error_message is not None:
                    path_errors[taxon_id] = error_message
                candidates.append(
                    WfoCandidate(taxon=nodes[taxon_id], classification=classification)
                )
            matches[key] = candidates
        return WfoExactBatchResult(
            metadata=metadata,
            matches=matches,
            truncated_keys=frozenset(truncated),
            path_errors=path_errors,
        )

    def exact_matches(
        self, names: Sequence[str], *, limit_per_name: int = 50
    ) -> dict[str, list[WfoCandidate]]:
        return self.exact_matches_with_context(names, limit_per_name=limit_per_name).matches

    def prefix_candidates(
        self, prefixes: Sequence[str], *, limit_per_prefix: int = 15
    ) -> WfoExactBatchResult:
        if not 1 <= limit_per_prefix <= _MAX_LIMIT_PER_PREFIX:
            raise ValueError(f"limit_per_prefix must be between 1 and {_MAX_LIMIT_PER_PREFIX}")
        keys = _normalize_batch_keys(prefixes)[:_MAX_PREFIX_KEYS]
        try:
            with closing(self.connect()) as db:
                metadata = self._read_metadata(db)
                if not keys:
                    return WfoExactBatchResult(metadata=metadata, matches={})
                ids_by_prefix: dict[str, list[str]] = {key: [] for key in keys}
                truncated: set[str] = set()
                all_ids: list[str] = []
                seen_ids: set[str] = set()
                for prefix in keys:
                    rows = db.execute(
                        "SELECT source_taxon_id FROM taxa "
                        "WHERE search_name >= ? AND search_name < ? "
                        "ORDER BY search_name, authorship, source_taxon_id LIMIT ?",
                        (prefix, prefix + chr(0x10FFFF), limit_per_prefix + 1),
                    ).fetchall()
                    if len(rows) > limit_per_prefix:
                        truncated.add(prefix)
                    for row in rows[:limit_per_prefix]:
                        taxon_id = str(row["source_taxon_id"])
                        ids_by_prefix[prefix].append(taxon_id)
                        if taxon_id not in seen_ids:
                            seen_ids.add(taxon_id)
                            all_ids.append(taxon_id)
                nodes = self._hierarchy_on(db, all_ids)
        except (OSError, ValueError, sqlite3.Error) as error:
            raise SourceUnavailableError("The WFO source cannot be searched.") from error

        matches: dict[str, list[WfoCandidate]] = {}
        path_errors: dict[str, str] = {}
        for prefix in keys:
            candidates: list[WfoCandidate] = []
            for taxon_id in ids_by_prefix[prefix]:
                classification, error_message = safe_path(nodes, taxon_id)
                if error_message is not None:
                    path_errors[taxon_id] = error_message
                candidates.append(
                    WfoCandidate(taxon=nodes[taxon_id], classification=classification)
                )
            matches[prefix] = candidates
        return WfoExactBatchResult(
            metadata=metadata,
            matches=matches,
            truncated_keys=frozenset(truncated),
            path_errors=path_errors,
        )


def safe_path(nodes: dict[str, WfoTaxon], identifier: str) -> tuple[list[WfoTaxon], str | None]:
    """Return classification path plus any hierarchy error instead of failing the batch."""
    try:
        return path(nodes, identifier), None
    except SourceUnavailableError as error:
        return [], str(error)


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
