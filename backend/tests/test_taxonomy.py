import copy
import hashlib
import json
import sqlite3
from pathlib import Path
from zipfile import ZipFile

import pytest

from florabase.taxonomy.snapshot import FIELDS, build_index, install, rows
from florabase.taxonomy.source import (
    CODE,
    ROOT,
    SourceUnavailableError,
    WfoMetadata,
    WfoSource,
    path,
)

META = WfoMetadata(retrieved_at="2026-10-09T14:48:29Z")
FAMILY = "wfo-4000000001"
GENUS = "wfo-4000000002"
SPECIES = "wfo-0000000001"
SECOND = "wfo-0000000002"
SYNONYM = "wfo-0000000003"
UNPLACED = "wfo-0000000004"
INTERMEDIATE = "wfo-4000000003"


def data() -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    names = [
        {"ID": ident, "scientificName": name, "authorship": "A.Author", "rank": rank}
        for ident, name, rank in [
            (ROOT, "Plantae", "kingdom"),
            (FAMILY, "Family", "family"),
            (GENUS, "Genus", "genus"),
            (INTERMEDIATE, "Section", "section"),
            (SPECIES, "Genus species", "species"),
            (SECOND, "Genus second", "species"),
            (SYNONYM, "Old species", "species"),
            (UNPLACED, "Unplaced species", "species"),
        ]
    ]
    concepts = [
        {"ID": ident, "nameID": ident, "parentID": parent}
        for ident, parent in [
            (ROOT, CODE),
            (FAMILY, ROOT),
            (GENUS, FAMILY),
            (INTERMEDIATE, GENUS),
            (SPECIES, INTERMEDIATE),
            (SECOND, GENUS),
        ]
    ]
    synonyms = [{"ID": SYNONYM + "-2026-06", "nameID": SYNONYM, "taxonID": SPECIES}]
    return names, concepts, synonyms


@pytest.fixture
def source(tmp_path: Path) -> WfoSource:
    destination = tmp_path / "source.sqlite"
    build_index(destination, *data(), META)
    return WfoSource(destination)


def test_hierarchy_exact_parent_synonym_intermediate_and_literal_search(source: WfoSource) -> None:
    nodes = source.hierarchy([SYNONYM, SECOND])
    assert set(nodes) == {ROOT, FAMILY, GENUS, INTERMEDIATE, SPECIES, SYNONYM, SECOND}
    assert [n.source_taxon_id for n in path(nodes, SYNONYM)] == [
        ROOT,
        FAMILY,
        GENUS,
        INTERMEDIATE,
        SPECIES,
    ]
    assert nodes[SYNONYM].taxonomic_status == "synonym"
    assert nodes[ROOT].parent_source_taxon_id == CODE
    assert source.search("Genus%") == []
    assert source.search("Genus_") == []
    assert source.search("GEnUS ")[0].taxon.source_taxon_id == GENUS
    assert source.search("Old")[0].classification[-1].source_taxon_id == SPECIES
    assert source.search("Unplaced")[0].classification == []
    assert path(nodes, "missing") == []
    assert source.metadata() == META


@pytest.mark.parametrize(
    "problem",
    [
        "duplicate_name",
        "missing_id",
        "duplicate_concept",
        "missing_parent",
        "self_parent",
        "cycle",
        "orphan",
        "rank",
        "accepted",
        "synonym_id",
        "synonym_self",
        "missing_name",
        "root",
        "control",
        "timestamp",
    ],
)
def test_provisioning_fails_closed_without_replacing_source(tmp_path: Path, problem: str) -> None:
    names, concepts, synonyms = copy.deepcopy(data())
    metadata = META
    if problem == "duplicate_name":
        names.append(names[0])
    elif problem == "missing_id":
        names[1]["ID"] = ""
    elif problem == "duplicate_concept":
        concepts.append(concepts[0])
    elif problem == "missing_parent":
        concepts[1]["parentID"] = "wfo-9999999999"
    elif problem == "self_parent":
        concepts[1]["parentID"] = FAMILY
    elif problem == "cycle":
        concepts[1]["parentID"] = SPECIES
    elif problem == "orphan":
        concepts[1]["parentID"] = CODE
    elif problem == "rank":
        names[1]["rank"] = "made_up"
    elif problem == "accepted":
        synonyms[0]["taxonID"] = "wfo-9999999999"
    elif problem == "synonym_id":
        synonyms[0]["ID"] = "other"
    elif problem == "synonym_self":
        synonyms[0]["taxonID"] = SYNONYM
    elif problem == "missing_name":
        concepts[1]["nameID"] = "wfo-9999999999"
    elif problem == "root":
        concepts[0]["parentID"] = "wfo-9999999999"
    elif problem == "control":
        names[1]["scientificName"] = "Bad\x01name"
    elif problem == "timestamp":
        metadata = META.model_copy(update={"retrieved_at": "2026-10-09"})
    destination = tmp_path / "source.sqlite"
    destination.write_bytes(b"existing source")
    with pytest.raises((ValueError, sqlite3.IntegrityError)):
        build_index(destination, names, concepts, synonyms, metadata)
    assert destination.read_bytes() == b"existing source"
    assert list(tmp_path.iterdir()) == [destination]


def test_missing_corrupt_wrong_release_schema_and_encoding(tmp_path: Path) -> None:
    with pytest.raises(SourceUnavailableError):
        WfoSource(None).metadata()
    p = tmp_path / "corrupt.sqlite"
    p.write_bytes(b"corrupt")
    with pytest.raises(SourceUnavailableError):
        WfoSource(p).metadata()
    with pytest.raises(ValueError, match="size"):
        install(p, tmp_path / "out", META.retrieved_at)
    archive = tmp_path / "wrong.zip"
    with ZipFile(archive, "w") as z:
        z.writestr("name.tsv", "wrong\n")
    with ZipFile(archive) as z, pytest.raises(ValueError, match="schema"):
        list(rows(z, "name.tsv"))
    with ZipFile(archive, "w") as z:
        z.writestr("name.tsv", "\t".join(FIELDS["name.tsv"]).encode() + b"\n\xff")
    with ZipFile(archive) as z, pytest.raises(UnicodeDecodeError):
        list(rows(z, "name.tsv"))
    assert json.loads(META.model_dump_json())["version"] == "2026-06"


@pytest.mark.parametrize(
    ("field", "value"), [("version", "2025-12"), ("checksum", "0" * 64), ("license", "unreviewed")]
)
def test_unreviewed_index_metadata_is_unavailable(tmp_path: Path, field: str, value: str) -> None:
    destination = tmp_path / "source.sqlite"
    build_index(destination, *data(), META.model_copy(update={field: value}))
    with pytest.raises(SourceUnavailableError):
        WfoSource(destination).metadata()


def test_wrong_archive_checksum_and_index_corruption(tmp_path: Path) -> None:
    archive = tmp_path / "wrong.zip"
    with archive.open("wb") as stream:
        stream.truncate(132643291)
    with pytest.raises(ValueError, match="checksum"):
        install(archive, tmp_path / "out.sqlite", META.retrieved_at)
    destination = tmp_path / "source.sqlite"
    build_index(destination, *data(), META)
    source = WfoSource(destination)
    assert source.metadata() == META
    with sqlite3.connect(destination) as db:
        db.execute("UPDATE taxa SET scientific_name='Altered'")
    with pytest.raises(SourceUnavailableError, match="checksum"):
        source.metadata()
    # A sealed SQLite artifact with an incompatible schema also fails closed.
    with sqlite3.connect(destination) as db:
        db.execute("DROP TABLE metadata")
    destination.with_suffix(".sha256").write_text(
        hashlib.sha256(destination.read_bytes()).hexdigest()
    )
    with pytest.raises(SourceUnavailableError):
        source.metadata()
