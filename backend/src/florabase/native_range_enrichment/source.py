"""Read a locally provisioned pinned WCVP index; never fetch during an API request."""

import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator

ARCHIVE_URL = "https://sftp.kew.org/pub/data-repositories/WCVP/Archive/wcvp_v15.zip"
ARCHIVE_SHA256 = "693e05b31ea6ce724c88ccf38bb964db2f22424b396f7ed1fd04fdb203af7e81"
VERSION = "15"
LICENSE = "https://creativecommons.org/licenses/by/3.0/"
CITATION = (
    "Govaerts R (ed.). 2026. WCVP: World Checklist of Vascular Plants. "
    "Facilitated by the Royal Botanic Gardens, Kew. [WWW document] "
    "URL https://doi.org/10.34885/rvc3-4d77 [accessed 06 Jan 2026]."
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
    model_config = ConfigDict(extra="forbid")
    provider: str = "kew_wcvp"
    version: str = VERSION
    archive_url: str = ARCHIVE_URL
    checksum: str = ARCHIVE_SHA256
    license: str = LICENSE
    citation: str = CITATION
    retrieved_at: str
    coverage: str = "complete"

    @field_validator("retrieved_at")
    @classmethod
    def retrieval_timestamp(cls, value: str) -> str:
        timestamp = datetime.fromisoformat(value)
        if timestamp.tzinfo is None:
            raise ValueError("Source retrieval timestamp requires a timezone")
        return value


class WcvpSource:
    def __init__(self, path: Path | None):
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        if self.path is None or not self.path.is_file() or self.path.stat().st_size > 2_000_000_000:
            raise SourceUnavailableError("The reviewed WCVP snapshot is not installed.")
        connection = sqlite3.connect(f"{self.path.resolve().as_uri()}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    def metadata(self) -> SourceMetadata:
        try:
            with closing(self._connect()) as connection:
                row = connection.execute("SELECT payload FROM metadata").fetchone()
                if row is None:
                    raise ValueError("Missing metadata")
                metadata = SourceMetadata.model_validate_json(row[0])
                if (
                    metadata.version != VERSION
                    or metadata.checksum != ARCHIVE_SHA256
                    or metadata.archive_url != ARCHIVE_URL
                    or metadata.license != LICENSE
                    or metadata.citation != CITATION
                    or metadata.provider != "kew_wcvp"
                    or metadata.coverage != "complete"
                ):
                    raise ValueError("Snapshot does not match reviewed release")
                return metadata
        except (OSError, sqlite3.Error, ValueError) as error:
            raise SourceUnavailableError("The WCVP snapshot is unavailable or invalid.") from error

    def search(self, query: str) -> list[Taxon]:
        self.metadata()
        # Literal indexed prefix search. No fuzzy match or implicit link.
        prefix = (
            query.strip().casefold().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        try:
            with closing(self._connect()) as connection:
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

    def taxon(self, external_id: str) -> Taxon:
        self.metadata()
        try:
            with closing(self._connect()) as connection:
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
        self.metadata()
        try:
            with closing(self._connect()) as connection:
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
