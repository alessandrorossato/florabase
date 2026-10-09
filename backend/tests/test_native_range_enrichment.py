import json
import sqlite3
import time
from pathlib import Path
from zipfile import ZipFile

import httpx
import pytest
from pydantic import ValidationError

from florabase.native_range_enrichment.crosswalk import EQUIVALENT, classify
from florabase.native_range_enrichment.schemas import ApplyWrite
from florabase.native_range_enrichment.snapshot import (
    DISTRIBUTION_FIELDS,
    NAMES_FIELDS,
    build_index,
    csv_rows,
    install_archive,
)
from florabase.native_range_enrichment.source import (
    ARCHIVE_URL,
    SourceMetadata,
    SourceUnavailableError,
    Taxon,
    WcvpSource,
)


def name(
    identifier: str = "100", status: str = "Accepted", accepted: str = "100"
) -> dict[str, str]:
    return dict.fromkeys(NAMES_FIELDS, "") | {
        "plant_name_id": identifier,
        "taxon_name": "Fixture species",
        "taxon_authors": "A.Author",
        "taxon_rank": "Species",
        "taxon_status": status,
        "accepted_plant_name_id": accepted,
    }


def distribution(
    code: str = "BOL",
    introduced: str = "0",
    extinct: str = "0",
    doubtful: str = "0",
    identifier: str = "1",
) -> dict[str, str]:
    return dict.fromkeys(DISTRIBUTION_FIELDS, "") | {
        "plant_locality_id": identifier,
        "plant_name_id": "100",
        "area_code_l3": code,
        "area": "Fixture area",
        "introduced": introduced,
        "extinct": extinct,
        "location_doubtful": doubtful,
    }


@pytest.fixture
def source(tmp_path: Path) -> WcvpSource:
    path = tmp_path / "source.sqlite"
    build_index(
        path,
        [name(), name("101", "Synonym"), name("102", "Accepted", "102")],
        [
            distribution(),
            distribution("CZE", identifier="2"),
            distribution("BUL", "1", identifier="3"),
        ],
        SourceMetadata(retrieved_at="2026-10-09T00:00:00Z"),
    )
    return WcvpSource(path)


def test_source_literal_prefix_duplicate_names_and_synonym_context(source: WcvpSource) -> None:
    candidates = source.search("Fixture")
    assert len(candidates) == 3
    assert [c.external_id for c in candidates] == ["100", "101", "102"]
    assert candidates[1].accepted_name == "Fixture species"
    assert not candidates[1].eligible
    assert source.search("Fixture%") == []
    assert source.search("Fikture") == []
    assert source.taxon("100").eligible
    assert len(source.distribution("100")) == 3
    with pytest.raises(SourceUnavailableError):
        source.taxon("missing")


@pytest.mark.parametrize(
    ("code", "expected"),
    [(code, "equivalent") for code in EQUIVALENT]
    + [
        ("CZE", "unsupported_split"),
        ("BLT", "unsupported_split"),
        ("ITA", "partial"),
        ("BZN", "partial"),
        ("UNKNOWN", "unresolved"),
        ("bol", "unresolved"),
        ("", "unresolved"),
    ],
)
def test_literal_crosswalk_preserves_unknown_partial_and_split(code: str, expected: str) -> None:
    assertion = classify(distribution(code))
    assert assertion.mapping == expected
    assert assertion.original["area_code_l3"] == code
    assert assertion.place_ids == []  # Canonical IDs require exact source metadata, never names.


@pytest.mark.parametrize(
    ("introduced", "extinct", "doubtful", "status"),
    [
        ("0", "0", "0", "native"),
        ("1", "0", "0", "introduced"),
        ("0", "1", "0", "qualified"),
        ("0", "0", "1", "qualified"),
        ("1", "1", "1", "qualified"),
    ],
)
def test_source_qualifiers_are_preserved(
    introduced: str, extinct: str, doubtful: str, status: str
) -> None:
    row = distribution("BOL", introduced, extinct, doubtful)
    assertion = classify(row)
    assert assertion.status == status
    assert assertion.original == row


def test_source_missing_corrupt_and_wrong_version_do_not_create_files(
    tmp_path: Path, source: WcvpSource
) -> None:
    missing = tmp_path / "missing.sqlite"
    with pytest.raises(SourceUnavailableError):
        WcvpSource(missing).metadata()
    assert not missing.exists()
    assert source.path is not None
    with sqlite3.connect(source.path) as connection:
        metadata = source.metadata().model_dump()
        metadata["version"] = "16"
        connection.execute("UPDATE metadata SET payload=?", (json.dumps(metadata),))
    with pytest.raises(SourceUnavailableError):
        source.search("Fixture")
    missing.write_bytes(b"not sqlite")
    with pytest.raises(SourceUnavailableError):
        WcvpSource(missing).metadata()


def test_index_rejects_duplicate_ids_unknown_flags_and_missing_taxon_atomically(
    tmp_path: Path, source: WcvpSource
) -> None:
    assert source.path is not None
    before = source.path.read_bytes()
    for names, distributions in [
        ([name(), name()], []),
        ([name()], [distribution(introduced="2")]),
        ([], [distribution()]),
        ([name()], [distribution(), distribution()]),
    ]:
        with pytest.raises((ValueError, sqlite3.IntegrityError)):
            build_index(
                source.path,
                names,
                distributions,
                SourceMetadata(retrieved_at="2026-10-09T00:00:00Z"),
            )
        assert source.path.read_bytes() == before
        assert source.taxon("100").eligible
    assert not list(tmp_path.glob("wcvp-*.sqlite"))


def test_archive_checksum_and_schema_fail_closed(tmp_path: Path) -> None:
    archive = tmp_path / "bad.zip"
    with ZipFile(archive, "w") as z:
        z.writestr("../../unsafe", "not a source")
        z.writestr("wcvp_names.csv", "wrong|schema\n1|2\n")
    with pytest.raises(ValueError, match="checksum"):
        install_archive(archive, tmp_path / "index.sqlite", "2026-10-09T00:00:00Z")
    with ZipFile(archive) as z, pytest.raises(ValueError, match="schema"):
        list(csv_rows(z, "wcvp_names.csv", NAMES_FIELDS))
    with ZipFile(archive, "w") as z:
        z.writestr("wcvp_names.csv", "|".join(NAMES_FIELDS) + "\n1|2\n")
    with ZipFile(archive) as z, pytest.raises(ValueError, match="Malformed"):
        list(csv_rows(z, "wcvp_names.csv", NAMES_FIELDS))
    assert not (tmp_path / "index.sqlite").exists()


def test_taxon_status_rank_and_exact_accepted_id_required() -> None:
    for status, rank, accepted in [
        ("Synonym", "Species", "1"),
        ("Accepted", "Genus", "1"),
        ("Accepted", "Species", "2"),
        ("Unplaced", "Species", ""),
    ]:
        assert not Taxon(
            external_id="1",
            name="Name",
            authorship="Author",
            rank=rank,
            status=status,
            accepted_id=accepted,
            powo_id="",
            reviewed="",
        ).eligible
    with pytest.raises(ValidationError):
        ApplyWrite(selected_place_ids=[])


@pytest.mark.parametrize(
    "failure", ["timeout", "oversize", "redirect", "content_type", "checksum", "elapsed"]
)
def test_fixed_download_failure_preserves_previous_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    from florabase.native_range_enrichment import snapshot

    destination = tmp_path / "index.sqlite"
    destination.write_bytes(b"previous usable index")
    original_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == ARCHIVE_URL
        if failure == "timeout":
            raise httpx.ReadTimeout("source unavailable", request=request)
        if failure == "redirect":
            return httpx.Response(302, headers={"location": "https://example.invalid/unreviewed"})
        if failure == "content_type":
            return httpx.Response(200, headers={"content-type": "text/html"}, content=b"error")
        return httpx.Response(
            200, headers={"content-type": "application/zip"}, content=b"invalid zip"
        )

    def client(*, timeout: httpx.Timeout, follow_redirects: bool) -> httpx.Client:
        assert follow_redirects is False
        assert timeout.connect == 10
        assert timeout.read == 60
        return original_client(
            transport=httpx.MockTransport(handler),
            timeout=timeout,
            follow_redirects=follow_redirects,
        )

    monkeypatch.setattr(httpx, "Client", client)
    if failure == "oversize":
        monkeypatch.setattr(snapshot, "MAX_ARCHIVE_BYTES", 1)
    if failure == "elapsed":
        times = iter([0.0, 241.0])
        monkeypatch.setattr(time, "monotonic", lambda: next(times))
    with pytest.raises((httpx.HTTPError, ValueError)):
        snapshot.download(destination)
    assert destination.read_bytes() == b"previous usable index"


def test_source_rejects_distribution_above_review_bound(tmp_path: Path) -> None:
    path = tmp_path / "source.sqlite"
    build_index(
        path,
        [name()],
        [distribution(identifier=str(i)) for i in range(501)],
        SourceMetadata(retrieved_at="2026-10-09T00:00:00Z"),
    )
    with pytest.raises(SourceUnavailableError, match="review limit"):
        WcvpSource(path).distribution("100")


def test_csv_invalid_utf8_and_source_timestamp_fail_closed(tmp_path: Path) -> None:
    archive = tmp_path / "bad.zip"
    with ZipFile(archive, "w") as z:
        z.writestr("wcvp_names.csv", b"\xff")
    with ZipFile(archive) as z, pytest.raises(UnicodeDecodeError):
        list(csv_rows(z, "wcvp_names.csv", NAMES_FIELDS))
    with pytest.raises(ValidationError):
        SourceMetadata(retrieved_at="2026-10-09T00:00:00")
