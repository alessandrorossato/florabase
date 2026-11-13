import importlib.util
import json
from collections.abc import Callable
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest
from test_native_range_enrichment import distribution
from test_native_range_enrichment import name as wcvp_name
from test_taxonomy import FAMILY, GENUS
from test_taxonomy import META as WFO_META

import florabase.native_range_enrichment.snapshot as wcvp_snapshot
import florabase.taxonomy.snapshot as wfo_snapshot
from florabase.botanical_matching import (
    ExistingLinkInput,
    IdentityMatchInput,
    discover_and_classify,
    format_match_report_markdown,
)
from florabase.native_range_enrichment.source import (
    RELEASES,
    WcvpSource,
    WcvpVersion,
)
from florabase.native_range_enrichment.source import (
    SourceMetadata as WcvpSourceMetadata,
)
from florabase.taxonomy.source import CHECKSUM as WFO_CHECKSUM
from florabase.taxonomy.source import CODE, ROOT, WfoSource


def _load_qualify_main() -> Callable[[list[str] | None], int]:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "botanical_match_qualify.py"
    spec = importlib.util.spec_from_file_location("botanical_match_qualify", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(Callable[[list[str] | None], int], module.main)


def _build_sources(tmp_path: Path) -> tuple[WfoSource, WcvpSource, WcvpSource]:
    wfo_names = [
        {"ID": ROOT, "scientificName": "Plantae", "authorship": "", "rank": "kingdom"},
        {"ID": FAMILY, "scientificName": "Lamiaceae", "authorship": "", "rank": "family"},
        {"ID": GENUS, "scientificName": "Salvia", "authorship": "L.", "rank": "genus"},
        {
            "ID": "wfo-0000000010",
            "scientificName": "Lavandula angustifolia",
            "authorship": "Mill.",
            "rank": "species",
        },
        {
            "ID": "wfo-0000000011",
            "scientificName": "Salvia officinalis",
            "authorship": "L.",
            "rank": "species",
        },
        {
            "ID": "wfo-0000000012",
            "scientificName": "Rosmarinus officinalis",
            "authorship": "L.",
            "rank": "species",
        },
        {
            "ID": "wfo-0000000013",
            "scientificName": "Salvia rosmarinus",
            "authorship": "Spenn.",
            "rank": "species",
        },
        # Homonyms for Achillea millefolium
        {
            "ID": "wfo-0000000020",
            "scientificName": "Achillea millefolium",
            "authorship": "L.",
            "rank": "species",
        },
        {
            "ID": "wfo-0000000021",
            "scientificName": "Achillea millefolium",
            "authorship": "Ledeb.",
            "rank": "species",
        },
        # Hybrid & infraspecific
        {
            "ID": "wfo-0000000030",
            "scientificName": "Salvia \u00d7 jamensis",
            "authorship": "J.Compton",
            "rank": "species",
        },
        {
            "ID": "wfo-0000000031",
            "scientificName": "Olea europaea subsp. europaea",
            "authorship": "",
            "rank": "subspecies",
        },
        {
            "ID": "wfo-0000000032",
            "scientificName": "Olea europaea",
            "authorship": "L.",
            "rank": "species",
        },
        # Unplaced
        {
            "ID": "wfo-0000000040",
            "scientificName": "Mystery unplaced",
            "authorship": "",
            "rank": "species",
        },
        # Cross-source disagreement: WFO accepts Verbena bonariensis; WCVP treats as synonym
        {
            "ID": "wfo-0000000050",
            "scientificName": "Verbena bonariensis",
            "authorship": "L.",
            "rank": "species",
        },
    ]
    wfo_concepts = [
        {"ID": ROOT, "nameID": ROOT, "parentID": CODE},
        {"ID": FAMILY, "nameID": FAMILY, "parentID": ROOT},
        {"ID": GENUS, "nameID": GENUS, "parentID": FAMILY},
        *[
            {"ID": item["ID"], "nameID": item["ID"], "parentID": GENUS}
            for item in wfo_names[3:]
            if item["ID"] not in {"wfo-0000000012", "wfo-0000000040"}
        ],
    ]
    wfo_synonyms = [
        {
            "ID": "wfo-0000000012-2026-06",
            "nameID": "wfo-0000000012",
            "taxonID": "wfo-0000000013",
        }
    ]
    wfo_path = tmp_path / "wfo.sqlite"
    wfo_snapshot.build_index(wfo_path, wfo_names, wfo_concepts, wfo_synonyms, WFO_META)

    def build_wcvp(version: WcvpVersion, rows: list[dict[str, str]]) -> Path:
        path = tmp_path / f"wcvp-{version}.sqlite"
        wcvp_snapshot.build_index(
            path,
            rows,
            [distribution() | {"plant_name_id": rows[0]["plant_name_id"]}],
            WcvpSourceMetadata.for_release(version, "2026-10-28T00:00:00Z"),
        )
        return path

    v16_rows = [
        wcvp_name("10", "Accepted", "10")
        | {"taxon_name": "Lavandula angustifolia", "taxon_authors": "Mill."},
        wcvp_name("11", "Accepted", "11")
        | {"taxon_name": "Salvia officinalis", "taxon_authors": "L."},
        wcvp_name("13", "Accepted", "13")
        | {"taxon_name": "Salvia rosmarinus", "taxon_authors": "Spenn."},
        wcvp_name("12", "Synonym", "13")
        | {"taxon_name": "Rosmarinus officinalis", "taxon_authors": "L."},
        wcvp_name("20", "Accepted", "20")
        | {"taxon_name": "Achillea millefolium", "taxon_authors": "L."},
        wcvp_name("21", "Synonym", "20")
        | {"taxon_name": "Achillea millefolium", "taxon_authors": "Ledeb."},
        wcvp_name("30", "Accepted", "30")
        | {"taxon_name": "Salvia \u00d7 jamensis", "taxon_authors": "J.Compton"},
        wcvp_name("31", "Accepted", "31")
        | {"taxon_name": "Olea europaea subsp. europaea", "taxon_rank": "Subspecies"},
        wcvp_name("32", "Accepted", "32") | {"taxon_name": "Olea europaea", "taxon_authors": "L."},
        wcvp_name("33", "Accepted", "33")
        | {"taxon_name": "Salvia", "taxon_rank": "Genus", "taxon_authors": "L."},
        wcvp_name("51", "Accepted", "51")
        | {"taxon_name": "Verbena inisa", "taxon_authors": "Schauer"},
        wcvp_name("50", "Synonym", "51")
        | {"taxon_name": "Verbena bonariensis", "taxon_authors": "L."},
    ]
    v15_rows = [
        wcvp_name("11", "Accepted", "11")
        | {"taxon_name": "Salvia officinalis", "taxon_authors": "L."},
        # v15 treated Salvia rosmarinus as synonym of Rosmarinus officinalis for conflict test
        wcvp_name("12", "Accepted", "12")
        | {"taxon_name": "Rosmarinus officinalis", "taxon_authors": "L."},
        wcvp_name("13", "Synonym", "12")
        | {"taxon_name": "Salvia rosmarinus", "taxon_authors": "Spenn."},
    ]

    return (
        WfoSource(wfo_path),
        WcvpSource(build_wcvp("16", v16_rows), version="16"),
        WcvpSource(build_wcvp("15", v15_rows), version="15"),
    )


def test_decision_matrix_scenarios_and_guardrails(tmp_path: Path) -> None:
    wfo, v16, _ = _build_sources(tmp_path)

    inputs = [
        IdentityMatchInput(scientific_name="Lavandula angustifolia", represented=True),
        IdentityMatchInput(
            scientific_name="Lavandula angustifolia",
            cultivar_name="Hidcote",
            represented=True,
        ),
        IdentityMatchInput(scientific_name="Rosmarinus officinalis", represented=True),
        IdentityMatchInput(scientific_name="Achillea millefolium", represented=True),
        IdentityMatchInput(scientific_name="Achillea millefolium L.", represented=False),
        IdentityMatchInput(scientific_name="Salvia x jamensis", represented=True),
        IdentityMatchInput(scientific_name="Salvia jamensis", represented=False),
        IdentityMatchInput(scientific_name="Olea europaea ssp. europaea", represented=True),
        IdentityMatchInput(scientific_name="Olea europea", represented=True),  # typo -> fuzzy
        IdentityMatchInput(scientific_name="Salvia", represented=False),
        IdentityMatchInput(scientific_name="Mystery unplaced", represented=False),
        IdentityMatchInput(scientific_name="Verbena bonariensis", represented=True),
        IdentityMatchInput(scientific_name="Completely unknown taxon", represented=False),
    ]

    report = discover_and_classify(inputs, wfo_source=wfo, wcvp_v16_source=v16)
    by_label = {
        (item.identity.scientific_name, item.identity.cultivar_name): item
        for item in report.results
    }

    # 1. Exact accepted match -> auto-eligible in both WFO and WCVP v16
    exact = by_label[("Lavandula angustifolia", None)]
    assert exact.overall_status == "ready_exact"
    assert exact.wfo.outcome == "auto_eligible"
    assert exact.wfo.auto_confirm_eligible is True
    assert exact.wcvp_v16.outcome == "auto_eligible"
    assert exact.wcvp_v16.auto_confirm_eligible is True
    assert exact.wfo.selected_candidate is not None
    assert exact.wfo.selected_candidate.external_id == "wfo-0000000010"
    assert exact.wcvp_v16.selected_candidate is not None
    assert exact.wcvp_v16.selected_candidate.external_id == "10"

    # 2. Cultivar species anchor -> explicit selection required
    cultivar = by_label[("Lavandula angustifolia", "Hidcote")]
    assert cultivar.overall_status == "needs_review"
    assert cultivar.wfo.outcome == "review_required"
    assert cultivar.wfo.auto_confirm_eligible is False
    assert "cultivar_species_anchor" in cultivar.wfo.reason_codes
    assert cultivar.wcvp_v16.outcome == "review_required"
    assert cultivar.wcvp_v16.auto_confirm_eligible is False

    # 3. Synonym handling preserves separate source contracts
    syn = by_label[("Rosmarinus officinalis", None)]
    assert syn.overall_status == "needs_review"
    assert syn.wfo.outcome == "review_required"
    assert "wfo_synonym_matched" in syn.wfo.reason_codes
    assert syn.wfo.selected_candidate is not None
    assert syn.wfo.selected_candidate.accepted_scientific_name == "Salvia rosmarinus"
    assert syn.wcvp_v16.outcome == "ineligible"
    assert syn.wcvp_v16.requires_operator_approval is True
    assert "wcvp_synonym_ineligible" in syn.wcvp_v16.reason_codes
    assert "resolved_accepted_target_available" in syn.wcvp_v16.reason_codes

    # 4. Homonyms never auto-select; authorship is advisory only
    hom = by_label[("Achillea millefolium", None)]
    assert hom.wfo.outcome == "ambiguous"
    assert hom.wfo.auto_confirm_eligible is False
    assert hom.wfo.selected_candidate is None
    assert len(hom.wfo.candidates) == 2
    assert hom.wcvp_v16.outcome == "ambiguous"
    assert hom.wcvp_v16.auto_confirm_eligible is False

    hom_auth = by_label[("Achillea millefolium L.", None)]
    assert hom_auth.wfo.outcome == "ambiguous"
    assert hom_auth.wfo.auto_confirm_eligible is False
    assert hom_auth.wfo.advisory_authorship_candidate_id == "wfo-0000000020"
    assert "authorship_advisory_disambiguation" in hom_auth.wfo.reason_codes

    # 5. Hybrid variants vs dropped hybrid sign
    hybrid_x = by_label[("Salvia x jamensis", None)]
    assert hybrid_x.wfo.outcome == "review_required"
    assert hybrid_x.wfo.confidence == "high"
    assert hybrid_x.wfo.auto_confirm_eligible is False
    assert "hybrid_notation_variant" in hybrid_x.wfo.reason_codes

    hybrid_drop = by_label[("Salvia jamensis", None)]
    assert hybrid_drop.wfo.outcome == "no_match"
    assert hybrid_drop.wfo.auto_confirm_eligible is False

    # 6. Rank token normalized (`ssp.` -> `subsp.`)
    infra = by_label[("Olea europaea ssp. europaea", None)]
    assert infra.wfo.outcome == "review_required"
    assert infra.wfo.confidence == "high"
    assert "rank_token_normalized" in infra.wfo.reason_codes
    assert infra.wcvp_v16.outcome == "review_required"
    assert infra.wcvp_v16.auto_confirm_eligible is False

    # 7. Fuzzy typo advisory never auto-confirms
    fuzzy = by_label[("Olea europea", None)]
    assert fuzzy.wfo.outcome == "review_required"
    assert fuzzy.wfo.confidence == "low"
    assert fuzzy.wfo.auto_confirm_eligible is False
    assert "fuzzy_advisory_only" in fuzzy.wfo.reason_codes
    assert fuzzy.wcvp_v16.outcome == "review_required"
    assert fuzzy.wcvp_v16.auto_confirm_eligible is False

    # 8. Rank above species (uninomial genus) -> ineligible in WCVP, review in WFO
    genus_only = by_label[("Salvia", None)]
    assert genus_only.wfo.outcome == "review_required"
    assert "rank_above_species" in genus_only.wfo.reason_codes
    assert genus_only.wcvp_v16.outcome == "ineligible"
    assert "wcvp_rank_ineligible" in genus_only.wcvp_v16.reason_codes

    # 9. Unplaced WFO taxon -> ineligible
    unplaced = by_label[("Mystery unplaced", None)]
    assert unplaced.overall_status == "ineligible"
    assert unplaced.wfo.outcome == "ineligible"
    assert "wfo_status_unplaced" in unplaced.wfo.reason_codes

    # 10. Cross-source conflict blocks auto-eligibility across providers
    conflict = by_label[("Verbena bonariensis", None)]
    assert conflict.overall_status == "conflict"
    assert conflict.wfo.outcome == "review_required"
    assert conflict.wfo.auto_confirm_eligible is False
    assert "cross_source_conflict" in conflict.wfo.reason_codes
    assert any(d.kind == "cross_source_accepted_name_conflict" for d in conflict.disagreements)

    # 11. Unmatched taxon
    unknown = by_label[("Completely unknown taxon", None)]
    assert unknown.overall_status == "unmatched"
    assert unknown.wfo.outcome == "no_match"
    assert unknown.wcvp_v16.outcome == "no_match"


def test_existing_links_synthetic_golden_and_v15_conflict(tmp_path: Path) -> None:
    wfo, v16, v15 = _build_sources(tmp_path)

    inputs = [
        # Existing official verified WFO/WCVP links matching exact candidates -> preserved
        IdentityMatchInput(
            scientific_name="Salvia officinalis",
            represented=True,
            existing_links={
                "wfo": ExistingLinkInput(
                    provider="wfo",
                    external_id="wfo-0000000011",
                    source_version="2026-06",
                    source_checksum=WFO_CHECKSUM,
                    scientific_name="Salvia officinalis",
                    authorship="L.",
                ),
                "wcvp": ExistingLinkInput(
                    provider="wcvp",
                    external_id="11",
                    source_version="16",
                    source_checksum=RELEASES["16"].checksum,
                    scientific_name="Salvia officinalis",
                    authorship="L.",
                ),
            },
        ),
        # Existing synthetic Golden link -> never treated as verified official evidence
        IdentityMatchInput(
            scientific_name="Lavandula angustifolia",
            represented=True,
            existing_links={
                "wfo": ExistingLinkInput(
                    provider="wfo",
                    external_id="wfo-0000000102",
                    source_version="2026-06",
                    source_checksum=WFO_CHECKSUM,
                    scientific_name="Lavandula angustifolia",
                    authorship="Golden",
                    synthetic_golden=True,
                )
            },
        ),
        # WCVP v15 vs v16 disagreement + GBIF conflict (read-only local snapshot, no HTTP)
        IdentityMatchInput(
            scientific_name="Salvia rosmarinus",
            represented=True,
            existing_links={
                "gbif": ExistingLinkInput(
                    provider="gbif",
                    external_id="999",
                    scientific_name="Rosmarinus oldname",
                    accepted_scientific_name="Rosmarinus oldname",
                    taxonomic_status="ACCEPTED",
                )
            },
        ),
    ]

    report = discover_and_classify(
        inputs,
        wfo_source=wfo,
        wcvp_v16_source=v16,
        wcvp_v15_source=v15,
    )
    by_name = {item.identity.scientific_name: item for item in report.results}

    preserved = by_name["Salvia officinalis"]
    assert preserved.overall_status == "already_verified"
    assert preserved.wfo.outcome == "already_linked"
    assert preserved.wfo.auto_confirm_eligible is False
    assert preserved.wcvp_v16.outcome == "already_linked"
    assert preserved.wcvp_v16.auto_confirm_eligible is False

    synthetic = by_name["Lavandula angustifolia"]
    assert synthetic.overall_status == "ready_exact"
    assert synthetic.wfo.existing_link_posture == "synthetic_golden"
    assert "synthetic_evidence_present" in synthetic.wfo.reason_codes
    assert report.providers[0].existing_synthetic_golden_count == 1

    v15_conflict = by_name["Salvia rosmarinus"]
    assert v15_conflict.overall_status == "conflict"
    assert v15_conflict.wfo.auto_confirm_eligible is False
    assert v15_conflict.wcvp_v16.auto_confirm_eligible is False
    assert any(d.kind == "wcvp_version_conflict" for d in v15_conflict.disagreements)
    assert any(d.kind == "existing_gbif_conflict" for d in v15_conflict.disagreements)


def test_missing_sources_fail_closed_and_cli_renders_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    wfo, v16, _ = _build_sources(tmp_path)
    assert wfo.path is not None
    assert v16.path is not None

    # Missing WCVP v16 fails closed cleanly without falling back to v15
    degraded = discover_and_classify(
        [IdentityMatchInput(scientific_name="Lavandula angustifolia")],
        wfo_source=wfo,
        wcvp_v16_source=WcvpSource(tmp_path / "missing-v16.sqlite", "16"),
    )
    source_info = {src.provider: src for src in degraded.sources}
    assert source_info["wfo"].available is True
    assert source_info["wcvp_v16"].available is False
    assert degraded.results[0].wfo.outcome == "auto_eligible"
    assert degraded.results[0].wcvp_v16.outcome == "source_unavailable"
    assert "Botanical Reference Matching Coverage" in format_match_report_markdown(degraded)

    input_file = tmp_path / "identities.json"
    input_file.write_text(
        json.dumps([{"scientific_name": "Lavandula angustifolia", "represented": True}]),
        encoding="utf-8",
    )
    out_file = tmp_path / "report.json"
    qualify_main = _load_qualify_main()
    rc = qualify_main(
        [
            "--input-json",
            str(input_file),
            "--wfo-path",
            str(wfo.path),
            "--wcvp-v16-path",
            str(v16.path),
            "--no-wcvp-v16-require-seal",
            "--format",
            "json",
            "--output",
            str(out_file),
            "--require-sources",
        ]
    )
    assert rc == 0
    capsys.readouterr()
    parsed = json.loads(out_file.read_text(encoding="utf-8"))
    assert parsed["total_identities"] == 1
    assert parsed["overall_status_counts"]["ready_exact"] == 1
    assert uuid4().hex  # keep uuid import exercised if needed


def test_formatting_divergence_and_stale_existing_link_paths(tmp_path: Path) -> None:
    wfo, v16, _ = _build_sources(tmp_path)
    report = discover_and_classify(
        [
            IdentityMatchInput(
                scientific_name="Salvia \u00d7 jamensis",
                represented=True,
                existing_links={
                    "wcvp": ExistingLinkInput(
                        provider="wcvp",
                        external_id="v16-different",
                        scientific_name="Salvia jamensis",
                        stale=True,
                    ),
                },
            ),
            IdentityMatchInput(scientific_name="Completely missing"),
        ],
        wfo_source=None,
        wcvp_v16_source=v16,
    )
    none_wfo = report.results[0]
    assert none_wfo.wfo.outcome == "source_unavailable"
    assert none_wfo.wcvp_v16.outcome == "review_required"
    assert "existing_link_stale" in none_wfo.wcvp_v16.reason_codes

    # Also test markdown formatting when zero exceptions exist.
    clean_only = discover_and_classify(
        [IdentityMatchInput(scientific_name="Lavandula angustifolia")],
        wfo_source=wfo,
        wcvp_v16_source=v16,
    )
    md = format_match_report_markdown(clean_only)
    assert "- None." in md

    # Stale link differing from candidate triggers review_required instead of auto_eligible
    stale_report = discover_and_classify(
        [
            IdentityMatchInput(
                scientific_name="Lavandula angustifolia",
                represented=True,
                existing_links={
                    "wfo": ExistingLinkInput(
                        provider="wfo",
                        external_id="wfo-old-id",
                        scientific_name="Lavandula spica",
                        stale=True,
                    ),
                },
            )
        ],
        wfo_source=wfo,
        wcvp_v16_source=v16,
    )
    stale_wfo = stale_report.results[0].wfo
    assert stale_wfo.outcome == "review_required"
    assert "existing_link_stale" in stale_wfo.reason_codes
    assert "existing_link_differs_from_candidate" in stale_wfo.reason_codes
