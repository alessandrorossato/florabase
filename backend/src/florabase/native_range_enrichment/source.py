"""Read a locally provisioned pinned WCVP index; never fetch during an API request."""

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Literal

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


WcvpVersion = Literal["15", "16"]


@dataclass(frozen=True)
class Release:
    version: WcvpVersion
    archive_url: str
    checksum: str
    citation: str
    member_sizes: tuple[int, int, int]
    crosswalk_version: str
    license: str = LICENSE


RELEASES = MappingProxyType(
    {
        "15": Release(
            "15",
            ARCHIVE_URL,
            ARCHIVE_SHA256,
            CITATION,
            (17_827, 298_218_467, 141_066_449),
            "wcvp15-wgsrpd2-cldr48.2.1-v1",
        ),
        "16": Release(
            "16",
            "https://sftp.kew.org/pub/data-repositories/WCVP/wcvp.zip",
            "d32ea2b3a85e489b14e83bcc9eae7274532e1d113753f7be290d4b2dfde573fa",
            "Govaerts R (ed.). 2026. WCVP: World Checklist of Vascular Plants. "
            "Facilitated by the Royal Botanic Gardens, Kew. [WWW document] "
            "URL https://doi.org/10.34885/egs6-cp24 [accessed 04 Jun 2026].",
            (18_112, 300_826_661, 141_657_561),
            "wcvp16-wgsrpd2-cldr48.2.1-v1",
        ),
    }
)


def reviewed_release(version: str) -> Release:
    try:
        return RELEASES[version]
    except KeyError as error:
        raise ValueError("Unreviewed WCVP version") from error


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


class WcvpSource:
    def __init__(self, path: Path | None, version: WcvpVersion = "15"):
        self.path = path
        self.release = reviewed_release(version)

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
                if metadata.reviewed_release() != self.release:
                    raise ValueError("Snapshot does not match the selected release")
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
