import pytest

from florabase.botanical_matching.normalizer import (
    HYBRID_SIGN,
    analyze_identity_name,
    compare_authorship,
    semantic_comparison_key,
)


def test_clean_binomial_and_whitespace_normalization() -> None:
    clean = analyze_identity_name("Achillea millefolium")
    assert clean.detected_rank_shape == "binomial"
    assert clean.has_cultivar is False
    assert clean.inline_cultivar_syntax is False
    assert clean.extracted_authorship is None
    assert clean.lookup_variants[0].query_key == "achillea millefolium"
    assert clean.lookup_variants[0].match_basis == "exact_literal"
    assert clean.fuzzy_prefixes == ["achillea mil", "achillea m"]

    spaced = analyze_identity_name("  Achillea\u00a0  millefolium  ")
    assert spaced.lookup_variants[0].query_key == "achillea millefolium"
    assert spaced.lookup_variants[0].match_basis == "normalized_whitespace"


@pytest.mark.parametrize(
    ("raw_name", "expected_key", "expected_ranks"),
    [
        ("Olea europaea ssp. europaea", "olea europaea subsp. europaea", ["subspecies"]),
        ("Olea europaea subspecies sylvestris", "olea europaea subsp. sylvestris", ["subspecies"]),
        ("Brassica oleracea var capitata", "brassica oleracea var. capitata", ["variety"]),
        ("Anemone nemorosa fa. alba", "anemone nemorosa f. alba", ["form"]),
        (
            f"Mentha {HYBRID_SIGN} piperita nvar. citrata",
            f"mentha {HYBRID_SIGN} piperita nothovar. citrata",
            ["nothovariety"],
        ),
    ],
)
def test_infraspecific_rank_canonicalization(
    raw_name: str, expected_key: str, expected_ranks: list[str]
) -> None:
    analysis = analyze_identity_name(raw_name)
    assert analysis.rank_marker_canonicalized is True
    assert analysis.infraspecific_ranks == expected_ranks
    assert analysis.detected_rank_shape in {"infraspecific", "hybrid_infraspecific"}
    bases = {variant.query_key: variant.match_basis for variant in analysis.lookup_variants}
    assert expected_key in bases
    assert bases[expected_key] == "rank_token_normalized"


def test_hybrid_variants_and_downgraded_drop_fallback() -> None:
    ascii_hybrid = analyze_identity_name("Salvia x jamensis")
    assert ascii_hybrid.is_hybrid is True
    assert ascii_hybrid.detected_rank_shape == "hybrid_binomial"
    ordered = [(v.query_key, v.match_basis) for v in ascii_hybrid.lookup_variants]
    assert ordered[0] == ("salvia x jamensis", "exact_literal")
    assert (f"salvia {HYBRID_SIGN} jamensis", "hybrid_sign_normalized") in ordered
    assert ordered[-1] == ("salvia jamensis", "hybrid_marker_dropped")

    intergeneric = analyze_identity_name(f"{HYBRID_SIGN}Heucherella tiarelloides")
    assert intergeneric.is_hybrid is True
    bases = {v.query_key: v.match_basis for v in intergeneric.lookup_variants}
    assert bases[f"{HYBRID_SIGN} heucherella tiarelloides"] == "hybrid_spacing_normalized"
    assert bases["x heucherella tiarelloides"] == "hybrid_sign_normalized"
    assert bases["heucherella tiarelloides"] == "hybrid_marker_dropped"

    # Epithet starting with 'x' must never be mistaken for hybrid marker.
    xanthina = analyze_identity_name("Rosa xanthina")
    assert xanthina.is_hybrid is False
    assert [v.query_key for v in xanthina.lookup_variants] == ["rosa xanthina"]


def test_cultivar_preservation_and_inline_cultivar_detection() -> None:
    separate = analyze_identity_name("Lavandula angustifolia", "Hidcote")
    assert separate.has_cultivar is True
    assert separate.cultivar_name == "Hidcote"
    assert separate.inline_cultivar_syntax is False
    assert separate.lookup_variants[0].query_key == "lavandula angustifolia"
    assert separate.lookup_variants[0].match_basis == "exact_literal"

    quoted = analyze_identity_name("Lavandula angustifolia 'Hidcote'")
    assert quoted.inline_cultivar_syntax is True
    assert quoted.canonical_stem == "Lavandula angustifolia"
    bases = {v.query_key: v.match_basis for v in quoted.lookup_variants}
    assert bases["lavandula angustifolia"] == "inline_cultivar_stripped"

    cv_syntax = analyze_identity_name("Salvia nemorosa cv. Caradonna")
    assert cv_syntax.inline_cultivar_syntax is True
    assert cv_syntax.canonical_stem == "Salvia nemorosa"

    cv_quoted = analyze_identity_name("Lavandula angustifolia cv. 'Hidcote'")
    assert cv_quoted.inline_cultivar_syntax is True
    assert cv_quoted.canonical_stem == "Lavandula angustifolia"
    assert cv_quoted.detected_rank_shape == "binomial"


@pytest.mark.parametrize(
    ("raw_name", "expected_stem", "expected_author", "expected_shape"),
    [
        ("Lavandula angustifolia Mill.", "Lavandula angustifolia", "Mill.", "binomial"),
        (
            f"Citrus {HYBRID_SIGN} limon (L.) Osbeck",
            f"Citrus {HYBRID_SIGN} limon",
            "(L.) Osbeck",
            "hybrid_binomial",
        ),
        (
            "Olea europaea subsp. europaea Mill.",
            "Olea europaea subsp. europaea",
            "Mill.",
            "infraspecific",
        ),
        ("Salvia L.", "Salvia", "L.", "uninomial"),
        ("Salvia", "Salvia", None, "uninomial"),
        (
            f"Salvia officinalis {HYBRID_SIGN} Salvia pratensis",
            f"Salvia officinalis {HYBRID_SIGN} Salvia pratensis",
            None,
            "other",
        ),
    ],
)
def test_inline_authorship_and_structure_detection(
    raw_name: str,
    expected_stem: str,
    expected_author: str | None,
    expected_shape: str,
) -> None:
    analysis = analyze_identity_name(raw_name)
    assert analysis.canonical_stem == expected_stem
    assert analysis.extracted_authorship == expected_author
    assert analysis.detected_rank_shape == expected_shape
    if expected_author is not None:
        bases = {v.query_key: v.match_basis for v in analysis.lookup_variants}
        assert bases[expected_stem.casefold()] == "inline_authorship_stripped"


def test_authorship_comparison_and_semantic_key() -> None:
    assert compare_authorship(None, "L.") == "not_provided"
    assert compare_authorship("L.", "") == "mismatch"
    assert compare_authorship("L.", "L.") == "exact"
    assert compare_authorship("(L.) Mill.", "( L. )Mill.") == "compatible_normalized"
    assert compare_authorship("Mill.", "L.") == "mismatch"

    assert semantic_comparison_key("Salvia x jamensis") == semantic_comparison_key(
        f"Salvia {HYBRID_SIGN}jamensis"
    )
    assert semantic_comparison_key("Olea europaea ssp. europaea") == semantic_comparison_key(
        "Olea europaea subsp. europaea"
    )


def test_edge_cases_and_malformed_hybrid_or_author_forms() -> None:
    empty = analyze_identity_name("   ")
    assert empty.lookup_variants == []
    assert empty.fuzzy_prefixes == []
    assert empty.detected_rank_shape == "other"

    trailing_x = analyze_identity_name("Salvia x")
    assert trailing_x.detected_rank_shape == "other"
    assert trailing_x.extracted_authorship is None

    infra_hybrid = analyze_identity_name(f"Mentha {HYBRID_SIGN} piperita var. x citrata L.")
    assert infra_hybrid.is_hybrid is True
    assert infra_hybrid.detected_rank_shape == "hybrid_infraspecific"
    assert infra_hybrid.canonical_stem == f"Mentha {HYBRID_SIGN} piperita var. x citrata"
    assert infra_hybrid.extracted_authorship == "L."

    tight_infra_hybrid = analyze_identity_name(f"Salvia officinalis subsp. {HYBRID_SIGN}alba")
    assert tight_infra_hybrid.is_hybrid is True
    assert tight_infra_hybrid.detected_rank_shape == "hybrid_infraspecific"

    uninomial = analyze_identity_name("Salvia")
    assert uninomial.fuzzy_prefixes == ["salv"]
    assert analyze_identity_name("weird_name").detected_rank_shape == "other"
    assert compare_authorship("L.", "  ") == "mismatch"
    assert compare_authorship("A.(B.)", "A.( B. )") == "compatible_normalized"
