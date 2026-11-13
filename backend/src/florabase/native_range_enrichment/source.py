"""Read a locally provisioned pinned WCVP index; never fetch during an API request."""

import hashlib
import json
import sqlite3
from collections.abc import Sequence
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from stat import S_ISREG
from types import MappingProxyType
from typing import Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator

from florabase.core.config import Settings
from florabase.core.reference_index import (
    SchemaContract,
    UnsupportedIndexError,
    open_reference_index,
)

ARCHIVE_URL = "https://sftp.kew.org/pub/data-repositories/WCVP/Archive/wcvp_v15.zip"
ARCHIVE_SHA256 = "693e05b31ea6ce724c88ccf38bb964db2f22424b396f7ed1fd04fdb203af7e81"
VERSION = "15"
LICENSE = "https://creativecommons.org/licenses/by/3.0/"
CITATION = (
    "Govaerts R (ed.). 2026. WCVP: World Checklist of Vascular Plants. "
    "Facilitated by the Royal Botanic Gardens, Kew. [WWW document] "
    "URL https://doi.org/10.34885/rvc3-4d77 [accessed 06 Jan 2026]."
)


WcvpVersion = Literal["15", "16"]
DEFAULT_VERSION: WcvpVersion = "16"


@dataclass(frozen=True)
class Release:
    version: WcvpVersion
    archive_url: str
    checksum: str
    citation: str
    member_sizes: tuple[int, int, int]
    license: str = LICENSE


RELEASES = MappingProxyType(
    {
        "15": Release(
            "15",
            ARCHIVE_URL,
            ARCHIVE_SHA256,
            CITATION,
            (17_827, 298_218_467, 141_066_449),
        ),
        "16": Release(
            "16",
            "https://sftp.kew.org/pub/data-repositories/WCVP/wcvp.zip",
            "d32ea2b3a85e489b14e83bcc9eae7274532e1d113753f7be290d4b2dfde573fa",
            "Govaerts R (ed.). 2026. WCVP: World Checklist of Vascular Plants. "
            "Facilitated by the Royal Botanic Gardens, Kew. [WWW document] "
            "URL https://doi.org/10.34885/egs6-cp24 [accessed 04 Jun 2026].",
            (18_112, 300_826_661, 141_657_561),
        ),
    }
)


def reviewed_release(version: str) -> Release:
    try:
        return RELEASES[version]
    except KeyError as error:
        raise ValueError("Unreviewed WCVP version") from error


# The one layout native_range_enrichment.snapshot.build_index writes for every reviewed release.
SCHEMA: SchemaContract = frozenset(
    {
        ("table", "metadata", "metadata", "CREATE TABLE metadata(payload TEXT NOT NULL)"),
        (
            "table",
            "taxa",
            "taxa",
            "CREATE TABLE taxa(external_id TEXT PRIMARY KEY, name TEXT NOT NULL, "
            "authorship TEXT NOT NULL,rank TEXT NOT NULL, status TEXT NOT NULL, "
            "accepted_id TEXT NOT NULL, powo_id TEXT NOT NULL,reviewed TEXT NOT NULL, "
            "search_name TEXT NOT NULL COLLATE NOCASE)",
        ),
        ("index", "sqlite_autoindex_taxa_1", "taxa", None),
        (
            "table",
            "distributions",
            "distributions",
            "CREATE TABLE distributions(locality_id TEXT PRIMARY KEY, "
            "external_id TEXT NOT NULL, payload TEXT NOT NULL)",
        ),
        ("index", "sqlite_autoindex_distributions_1", "distributions", None),
        (
            "index",
            "taxa_search",
            "taxa",
            "CREATE INDEX taxa_search ON taxa(search_name, external_id)",
        ),
        (
            "index",
            "distribution_taxon",
            "distributions",
            "CREATE INDEX distribution_taxon ON distributions(external_id, locality_id)",
        ),
    }
)


class SourceUnavailableError(Exception):
    pass


class Taxon(BaseModel):
    model_config = ConfigDict(extra="forbid")
    external_id: str
    name: str
    authorship: str
    rank: str
    status: str
    accepted_id: str
    accepted_name: str | None = None
    powo_id: str
    reviewed: str

    @property
    def eligible(self) -> bool:
        return (
            self.status == "Accepted"
            and self.accepted_id == self.external_id
            and self.rank in {"Species", "Subspecies", "Variety", "Form"}
        )


class SourceMetadata(BaseModel):
    """Frozen release evidence; retains v15 field defaults for historical records."""

    model_config = ConfigDict(extra="forbid")
    provider: str = "kew_wcvp"
    version: str = VERSION
    archive_url: str = ARCHIVE_URL
    checksum: str = ARCHIVE_SHA256
    license: str = LICENSE
    citation: str = CITATION
    retrieved_at: str
    coverage: str = "complete"

    @classmethod
    def for_release(cls, version: WcvpVersion, retrieved_at: str) -> SourceMetadata:
        release = reviewed_release(version)
        return cls(
            version=release.version,
            archive_url=release.archive_url,
            checksum=release.checksum,
            license=release.license,
            citation=release.citation,
            retrieved_at=retrieved_at,
        )

    def reviewed_release(self) -> Release:
        release = reviewed_release(self.version)
        if (
            self.archive_url != release.archive_url
            or self.checksum != release.checksum
            or self.license != release.license
            or self.citation != release.citation
            or self.provider != "kew_wcvp"
            or self.coverage != "complete"
        ):
            raise ValueError("Source metadata does not match the reviewed release")
        return release

    @field_validator("retrieved_at")
    @classmethod
    def retrieval_timestamp(cls, value: str) -> str:
        timestamp = datetime.fromisoformat(value)
        if timestamp.tzinfo is None:
            raise ValueError("Source retrieval timestamp requires a timezone")
        return value


def file_identity(path: Path) -> tuple[int, int, int, int, int]:
    stat = path.lstat()
    if not S_ISREG(stat.st_mode):
        raise ValueError("WCVP index and seal must be regular files")
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


@lru_cache(maxsize=4)
def verify_index_seal(
    path: Path,
    index_identity: tuple[int, int, int, int, int],
    seal_identity: tuple[int, int, int, int, int],
) -> None:
    seal = path.with_suffix(".sha256")
    if seal_identity[2] != 65:
        raise SourceUnavailableError("The WCVP index provisioning seal is invalid.")
    expected = seal.read_text(encoding="ascii").strip()
    with path.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    if checksum != expected:
        raise SourceUnavailableError(
            "The WCVP index checksum does not match its provisioning seal."
        )
    if index_identity != file_identity(path) or seal_identity != file_identity(seal):
        raise SourceUnavailableError("The WCVP index changed during validation.")


class WcvpMatchedRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    taxon: Taxon
    accepted_taxon: Taxon | None = None


class WcvpExactBatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metadata: SourceMetadata
    matches: dict[str, list[WcvpMatchedRecord]]
    truncated_keys: frozenset[str] = Field(default_factory=frozenset)


_EXACT_BATCH_CHUNK: Final = 100
_ACCEPTED_FETCH_CHUNK: Final = 200
_MAX_LIMIT_PER_NAME: Final = 200
_MAX_PREFIX_KEYS: Final = 2000
_MAX_LIMIT_PER_PREFIX: Final = 25


def _normalize_batch_keys(names: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    keys: list[str] = []
    for raw in names:
        key = raw.strip().casefold()
        if key and key not in seen:
            seen.add(key)
            keys.append(key)
    return keys


class WcvpSource:
    def __init__(
        self,
        path: Path | None,
        version: WcvpVersion = DEFAULT_VERSION,
        *,
        require_seal: bool = False,
    ):
        self.path = path
        self.release = reviewed_release(version)
        self.require_seal = require_seal

    @classmethod
    def from_settings(cls, settings: Settings, version: WcvpVersion = DEFAULT_VERSION) -> Self:
        if version == "16":
            return cls(
                settings.wcvp_v16_snapshot_path,
                version,
                require_seal=settings.wcvp_v16_require_seal,
            )
        return cls(settings.wcvp_snapshot_path, version)

    def _connect(self) -> sqlite3.Connection:
        if self.path is None or not self.path.is_file() or self.path.stat().st_size > 2_000_000_000:
            raise SourceUnavailableError("The reviewed WCVP snapshot is not installed.")
        if self.require_seal:
            try:
                verify_index_seal(
                    self.path,
                    file_identity(self.path),
                    file_identity(self.path.with_suffix(".sha256")),
                )
            except (OSError, ValueError) as error:
                raise SourceUnavailableError(
                    "The WCVP index provisioning seal is unavailable."
                ) from error
        try:
            return open_reference_index(self.path, SCHEMA, "WCVP")
        except UnsupportedIndexError as error:
            raise SourceUnavailableError(
                "The WCVP snapshot is not a supported index built by Florabase's WCVP builder."
            ) from error

    def _read_metadata(self, connection: sqlite3.Connection) -> SourceMetadata:
        row = connection.execute("SELECT payload FROM metadata").fetchone()
        if row is None:
            raise ValueError("Missing metadata")
        metadata = SourceMetadata.model_validate_json(row[0])
        if metadata.reviewed_release() != self.release:
            raise ValueError("Snapshot does not match the selected release")
        return metadata

    def _fetch_accepted_taxa(
        self, connection: sqlite3.Connection, taxa: Sequence[Taxon]
    ) -> dict[str, Taxon]:
        accepted_map: dict[str, Taxon] = {
            taxon.external_id: taxon for taxon in taxa if taxon.accepted_id == taxon.external_id
        }
        missing_ids: list[str] = []
        seen_ids: set[str] = set(accepted_map)
        for taxon in taxa:
            if taxon.accepted_id and taxon.accepted_id not in seen_ids:
                seen_ids.add(taxon.accepted_id)
                missing_ids.append(taxon.accepted_id)
        for offset in range(0, len(missing_ids), _ACCEPTED_FETCH_CHUNK):
            chunk = missing_ids[offset : offset + _ACCEPTED_FETCH_CHUNK]
            placeholders = ",".join("?" for _ in chunk)
            rows = connection.execute(
                f"SELECT t.*, a.name AS accepted_name FROM taxa t "
                f"LEFT JOIN taxa a ON a.external_id=t.accepted_id "
                f"WHERE t.external_id IN ({placeholders})",
                chunk,
            ).fetchall()
            for row in rows:
                resolved = Taxon.model_validate({k: row[k] for k in Taxon.model_fields})
                accepted_map[resolved.external_id] = resolved
        return accepted_map

    def metadata(self) -> SourceMetadata:
        try:
            with closing(self._connect()) as connection:
                return self._read_metadata(connection)
        except (OSError, sqlite3.Error, ValueError) as error:
            raise SourceUnavailableError("The WCVP snapshot is unavailable or invalid.") from error

    def search(self, query: str) -> list[Taxon]:
        # Literal indexed prefix search. No fuzzy match or implicit link.
        prefix = (
            query.strip().casefold().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        try:
            with closing(self._connect()) as connection:
                self._read_metadata(connection)
                rows = connection.execute(
                    "SELECT t.*, a.name AS accepted_name FROM taxa t "
                    "LEFT JOIN taxa a ON a.external_id=t.accepted_id "
                    "WHERE t.search_name LIKE ? ESCAPE '\\' "
                    "ORDER BY t.search_name, t.external_id LIMIT 25",
                    (prefix + "%",),
                ).fetchall()
                return [
                    Taxon.model_validate({k: row[k] for k in Taxon.model_fields}) for row in rows
                ]
        except (OSError, sqlite3.Error, ValueError) as error:
            raise SourceUnavailableError("The WCVP snapshot cannot be searched.") from error

    def exact_matches_with_context(
        self, names: Sequence[str], *, limit_per_name: int = 50
    ) -> WcvpExactBatchResult:
        if not 1 <= limit_per_name <= _MAX_LIMIT_PER_NAME:
            raise ValueError(f"limit_per_name must be between 1 and {_MAX_LIMIT_PER_NAME}")
        keys = _normalize_batch_keys(names)
        try:
            with closing(self._connect()) as connection:
                metadata = self._read_metadata(connection)
                if not keys:
                    return WcvpExactBatchResult(metadata=metadata, matches={})
                taxa_by_key: dict[str, list[Taxon]] = {key: [] for key in keys}
                truncated: set[str] = set()
                all_taxa: list[Taxon] = []
                for offset in range(0, len(keys), _EXACT_BATCH_CHUNK):
                    chunk = keys[offset : offset + _EXACT_BATCH_CHUNK]
                    placeholders = ",".join("?" for _ in chunk)
                    rows = connection.execute(
                        f"WITH ranked AS ("
                        f"SELECT external_id, search_name, "
                        f"ROW_NUMBER() OVER ("
                        f"PARTITION BY search_name ORDER BY external_id"
                        f") AS row_num "
                        f"FROM taxa WHERE search_name IN ({placeholders})"
                        f") "
                        f"SELECT t.*, a.name AS accepted_name, r.search_name AS matched_key "
                        f"FROM ranked r "
                        f"JOIN taxa t ON t.external_id = r.external_id "
                        f"LEFT JOIN taxa a ON a.external_id = t.accepted_id "
                        f"WHERE r.row_num <= ? "
                        f"ORDER BY r.search_name, r.row_num",
                        (*chunk, limit_per_name + 1),
                    ).fetchall()
                    for row in rows:
                        key = str(row["matched_key"]).casefold()
                        bucket = taxa_by_key.setdefault(key, [])
                        if len(bucket) >= limit_per_name:
                            truncated.add(key)
                            continue
                        taxon = Taxon.model_validate({k: row[k] for k in Taxon.model_fields})
                        bucket.append(taxon)
                        all_taxa.append(taxon)
                accepted_map = self._fetch_accepted_taxa(connection, all_taxa)
        except (OSError, sqlite3.Error, ValueError) as error:
            raise SourceUnavailableError("The WCVP snapshot cannot be searched.") from error

        matches = {
            key: [
                WcvpMatchedRecord(
                    taxon=taxon,
                    accepted_taxon=accepted_map.get(taxon.accepted_id),
                )
                for taxon in taxa_by_key.get(key, ())
            ]
            for key in keys
        }
        return WcvpExactBatchResult(
            metadata=metadata,
            matches=matches,
            truncated_keys=frozenset(truncated),
        )

    def exact_matches(
        self, names: Sequence[str], *, limit_per_name: int = 50
    ) -> dict[str, list[Taxon]]:
        result = self.exact_matches_with_context(names, limit_per_name=limit_per_name)
        return {key: [item.taxon for item in items] for key, items in result.matches.items()}

    def prefix_candidates(
        self, prefixes: Sequence[str], *, limit_per_prefix: int = 15
    ) -> WcvpExactBatchResult:
        if not 1 <= limit_per_prefix <= _MAX_LIMIT_PER_PREFIX:
            raise ValueError(f"limit_per_prefix must be between 1 and {_MAX_LIMIT_PER_PREFIX}")
        keys = _normalize_batch_keys(prefixes)[:_MAX_PREFIX_KEYS]
        try:
            with closing(self._connect()) as connection:
                metadata = self._read_metadata(connection)
                if not keys:
                    return WcvpExactBatchResult(metadata=metadata, matches={})
                taxa_by_prefix: dict[str, list[Taxon]] = {key: [] for key in keys}
                truncated: set[str] = set()
                all_taxa: list[Taxon] = []
                for prefix in keys:
                    escaped = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                    rows = connection.execute(
                        "SELECT t.*, a.name AS accepted_name FROM taxa t "
                        "LEFT JOIN taxa a ON a.external_id=t.accepted_id "
                        "WHERE t.search_name LIKE ? ESCAPE '\\' "
                        "ORDER BY t.search_name, t.external_id LIMIT ?",
                        (escaped + "%", limit_per_prefix + 1),
                    ).fetchall()
                    if len(rows) > limit_per_prefix:
                        truncated.add(prefix)
                    for row in rows[:limit_per_prefix]:
                        taxon = Taxon.model_validate({k: row[k] for k in Taxon.model_fields})
                        taxa_by_prefix[prefix].append(taxon)
                        all_taxa.append(taxon)
                accepted_map = self._fetch_accepted_taxa(connection, all_taxa)
        except (OSError, sqlite3.Error, ValueError) as error:
            raise SourceUnavailableError("The WCVP snapshot cannot be searched.") from error

        matches = {
            prefix: [
                WcvpMatchedRecord(
                    taxon=taxon,
                    accepted_taxon=accepted_map.get(taxon.accepted_id),
                )
                for taxon in taxa_by_prefix[prefix]
            ]
            for prefix in keys
        }
        return WcvpExactBatchResult(
            metadata=metadata,
            matches=matches,
            truncated_keys=frozenset(truncated),
        )

    def taxon(self, external_id: str) -> Taxon:
        try:
            with closing(self._connect()) as connection:
                self._read_metadata(connection)
                row = connection.execute(
                    "SELECT t.*, a.name AS accepted_name FROM taxa t "
                    "LEFT JOIN taxa a ON a.external_id=t.accepted_id WHERE t.external_id=?",
                    (external_id,),
                ).fetchone()
                if row is None:
                    raise SourceUnavailableError(
                        "The selected WCVP taxon is missing from the snapshot."
                    )
                return Taxon.model_validate({k: row[k] for k in Taxon.model_fields})
        except (OSError, sqlite3.Error, ValueError) as error:
            raise SourceUnavailableError("The WCVP taxon cannot be read.") from error

    def distribution(self, external_id: str) -> list[dict[str, str]]:
        try:
            with closing(self._connect()) as connection:
                self._read_metadata(connection)
                rows = connection.execute(
                    "SELECT payload FROM distributions WHERE external_id=? "
                    "ORDER BY locality_id LIMIT 501",
                    (external_id,),
                ).fetchall()
                if len(rows) > 500:
                    raise SourceUnavailableError(
                        "Taxon distribution exceeds the bounded review limit."
                    )
                return [dict(json.loads(row[0])) for row in rows]
        except (OSError, sqlite3.Error, ValueError) as error:
            raise SourceUnavailableError("The WCVP distribution cannot be read.") from error
