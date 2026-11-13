import sqlite3
from pathlib import Path

import pytest
from test_native_range_enrichment import distribution
from test_native_range_enrichment import name as wcvp_name
from test_taxonomy import FAMILY, GENUS
from test_taxonomy import META as WFO_META

import florabase.native_range_enrichment.snapshot as wcvp_snapshot
import florabase.taxonomy.snapshot as wfo_snapshot
from florabase.native_range_enrichment.source import (
    SourceMetadata as WcvpSourceMetadata,
)
from florabase.native_range_enrichment.source import (
    SourceUnavailableError as WcvpUnavailableError,
)
from florabase.native_range_enrichment.source import (
    WcvpSource,
    WcvpVersion,
)
from florabase.taxonomy.source import (
    CODE,
    ROOT,
    WfoSource,
)
from florabase.taxonomy.source import (
    SourceUnavailableError as WfoUnavailableError,
)


def _large_wfo_fixture(tmp_path: Path) -> Path:
    """Create a synthetic WFO index with >30 shared-prefix taxa and homonyms."""
    names = [
        {"ID": ROOT, "scientificName": "Plantae", "authorship": "", "rank": "kingdom"},
        {"ID": FAMILY, "scientificName": "Lamiaceae", "authorship": "", "rank": "family"},
        {"ID": GENUS, "scientificName": "Salvia", "authorship": "L.", "rank": "genus"},
        # 30 infraspecifics/related taxa starting with "Salvia " before an exact target would fall
        # past LIMIT 25 if prefix ordering placed them ahead (or multiple exact homonyms >25).
        *[
            {
                "ID": f"wfo-000000{1000 + idx}",
                "scientificName": f"Salvia aa_{idx:02d}",
                "authorship": "A.Auth",
                "rank": "species",
            }
            for idx in range(30)
        ],
        # Two exact homonyms + one unplaced taxon + one non-root broken taxon
        {
            "ID": "wfo-0000002001",
            "scientificName": "Salvia officinalis",
            "authorship": "L.",
            "rank": "species",
        },
        {
            "ID": "wfo-0000002002",
            "scientificName": "Salvia officinalis",
            "authorship": "Mill.",
            "rank": "species",
        },
        {
            "ID": "wfo-0000002003",
            "scientificName": "Salvia unplaced",
            "authorship": "",
            "rank": "species",
        },
        {
            "ID": "wfo-0000002004",
            "scientificName": "Salvia synonym",
            "authorship": "Old.",
            "rank": "species",
        },
    ]
    concepts = [
        {"ID": ROOT, "nameID": ROOT, "parentID": CODE},
        {"ID": FAMILY, "nameID": FAMILY, "parentID": ROOT},
        {"ID": GENUS, "nameID": GENUS, "parentID": FAMILY},
        *[
            {
                "ID": f"wfo-000000{1000 + idx}",
                "nameID": f"wfo-000000{1000 + idx}",
                "parentID": GENUS,
            }
            for idx in range(30)
        ],
        {"ID": "wfo-0000002001", "nameID": "wfo-0000002001", "parentID": GENUS},
    ]
    synonyms = [
        {
            "ID": "wfo-0000002002-2026-06",
            "nameID": "wfo-0000002002",
            "taxonID": "wfo-0000002001",
        },
        {
            "ID": "wfo-0000002004-2026-06",
            "nameID": "wfo-0000002004",
            "taxonID": "wfo-0000002001",
        },
    ]
    path = tmp_path / "wfo.sqlite"
    wfo_snapshot.build_index(path, names, concepts, synonyms, WFO_META)
    return path


def _large_wcvp_fixture(tmp_path: Path, version: WcvpVersion = "16") -> Path:
    rows = [
        wcvp_name("200", "Accepted", "200")
        | {"taxon_name": "Salvia officinalis", "taxon_authors": "L."},
        wcvp_name("201", "Synonym", "200")
        | {"taxon_name": "Salvia officinalis", "taxon_authors": "Pall."},
        wcvp_name("202", "Synonym", "200")
        | {"taxon_name": "Rosmarinus officinalis", "taxon_authors": "L."},
        *[
            wcvp_name(str(300 + idx), "Accepted", str(300 + idx))
            | {"taxon_name": f"Genus spec{idx:03d}"}
            for idx in range(120)
        ],
    ]
    path = tmp_path / f"wcvp-{version}.sqlite"
    wcvp_snapshot.build_index(
        path,
        rows,
        [distribution() | {"plant_name_id": "200"}],
        WcvpSourceMetadata.for_release(version, "2026-10-28T00:00:00Z"),
    )
    return path


def test_wfo_batched_exact_matches_single_connection_and_non_truncation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = WfoSource(_large_wfo_fixture(tmp_path))
    connect_calls = 0
    original_connect = source.connect

    def tracked_connect() -> sqlite3.Connection:
        nonlocal connect_calls
        connect_calls += 1
        return original_connect()

    monkeypatch.setattr(source, "connect", tracked_connect)

    # Query >110 names (spans chunking boundary) including mixed case and duplicates
    queries = (
        [f"Salvia aa_{idx:02d}" for idx in range(30)]
        + [f"Extra binomial {i}" for i in range(95)]
        + ["  SALVIA OFFICINALIS ", "Salvia unplaced", "Salvia synonym"]
    )
    batch = source.exact_matches_with_context(queries, limit_per_name=50)

    assert connect_calls == 1
    assert [c.taxon.source_taxon_id for c in batch.matches["salvia officinalis"]] == [
        "wfo-0000002001",
        "wfo-0000002002",
    ]
    assert batch.matches["salvia unplaced"][0].taxon.taxonomic_status == "unplaced"
    assert batch.matches["salvia unplaced"][0].classification == []
    assert batch.matches["salvia synonym"][0].classification[-1].source_taxon_id == "wfo-0000002001"
    assert batch.truncated_keys == frozenset()

    # Exact bucket truncation signal when limit_per_name=1 on 2 homonyms
    truncated = source.exact_matches_with_context(["Salvia officinalis"], limit_per_name=1)
    assert truncated.truncated_keys == frozenset({"salvia officinalis"})
    assert len(truncated.matches["salvia officinalis"]) == 1

    # Existing search API stays compatible and still caps at 25 prefix rows
    assert len(source.search("Salvia")) == 25


@pytest.mark.parametrize("version", ["15", "16"])
def test_wcvp_batched_exact_matches_single_connection_and_accepted_lookup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, version: WcvpVersion
) -> None:
    source = WcvpSource(_large_wcvp_fixture(tmp_path, version), version=version)
    connect_calls = 0
    original_connect = source._connect

    def tracked_connect() -> sqlite3.Connection:
        nonlocal connect_calls
        connect_calls += 1
        return original_connect()

    monkeypatch.setattr(source, "_connect", tracked_connect)

    names = [f"Genus spec{idx:03d}" for idx in range(120)] + [
        "Salvia officinalis",
        "Rosmarinus officinalis",
        "Missing taxon",
    ]
    batch = source.exact_matches_with_context(names, limit_per_name=50)

    assert connect_calls == 1
    assert batch.metadata.version == version
    assert [item.taxon.external_id for item in batch.matches["salvia officinalis"]] == [
        "200",
        "201",
    ]
    synonym_hit = batch.matches["rosmarinus officinalis"][0]
    assert synonym_hit.taxon.external_id == "202"
    assert synonym_hit.accepted_taxon is not None
    assert synonym_hit.accepted_taxon.name == "Salvia officinalis"
    assert synonym_hit.accepted_taxon.authorship == "L."
    assert synonym_hit.accepted_taxon.eligible is True
    assert batch.matches["missing taxon"] == []

    # Backward-compatible exact_matches wrapper
    simple = source.exact_matches(["Salvia officinalis"])
    assert [t.external_id for t in simple["salvia officinalis"]] == ["200", "201"]


def test_batched_lookups_reject_untrusted_schema_and_missing_seal(tmp_path: Path) -> None:
    bad_sqlite = tmp_path / "bad.sqlite"
    with sqlite3.connect(bad_sqlite) as db:
        db.execute("CREATE VIEW taxa AS SELECT '1' AS source_taxon_id")
    bad_sqlite.with_suffix(".sha256").write_text("0" * 64 + "\n")
    with pytest.raises(WfoUnavailableError):
        WfoSource(bad_sqlite).exact_matches(["Salvia"])

    unsealed_v16 = _large_wcvp_fixture(tmp_path, "16")
    with pytest.raises(WcvpUnavailableError):
        WcvpSource(unsealed_v16, "16", require_seal=True).exact_matches(["Salvia officinalis"])


def test_source_batch_bounds_empty_inputs_and_prefix_truncation(tmp_path: Path) -> None:
    wfo_source = WfoSource(_large_wfo_fixture(tmp_path))
    wcvp_source = WcvpSource(_large_wcvp_fixture(tmp_path, "16"), "16")

    empty_wfo = wfo_source.exact_matches_with_context([])
    assert empty_wfo.matches == {}
    empty_wfo_prefix = wfo_source.prefix_candidates([])
    assert empty_wfo_prefix.matches == {}
    empty_wcvp = wcvp_source.exact_matches_with_context([])
    assert empty_wcvp.matches == {}
    empty_wcvp_prefix = wcvp_source.prefix_candidates([])
    assert empty_wcvp_prefix.matches == {}

    with pytest.raises(ValueError, match="limit_per_name"):
        wfo_source.exact_matches_with_context(["Salvia"], limit_per_name=0)
    with pytest.raises(ValueError, match="limit_per_prefix"):
        wfo_source.prefix_candidates(["salvia"], limit_per_prefix=0)
    with pytest.raises(ValueError, match="limit_per_name"):
        wcvp_source.exact_matches_with_context(["Salvia"], limit_per_name=0)
    with pytest.raises(ValueError, match="limit_per_prefix"):
        wcvp_source.prefix_candidates(["salvia"], limit_per_prefix=0)

    wfo_prefix = wfo_source.prefix_candidates(["salvia aa_"], limit_per_prefix=2)
    assert wfo_prefix.truncated_keys == frozenset({"salvia aa_"})
    assert len(wfo_prefix.matches["salvia aa_"]) == 2

    wcvp_prefix = wcvp_source.prefix_candidates(["genus spec"], limit_per_prefix=2)
    assert wcvp_prefix.truncated_keys == frozenset({"genus spec"})
    assert len(wcvp_prefix.matches["genus spec"]) == 2

    with pytest.raises(WfoUnavailableError):
        WfoSource(tmp_path / "missing-wfo.sqlite").prefix_candidates(["salvia"])
    with pytest.raises(WcvpUnavailableError):
        WcvpSource(tmp_path / "missing-wcvp.sqlite", "16").prefix_candidates(["salvia"])
