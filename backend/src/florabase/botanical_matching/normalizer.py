"""Pure botanical name normalization, variant generation, and advisory authorship comparison."""

from __future__ import annotations

import re
import unicodedata

from florabase.botanical_matching.schemas import (
    AuthorshipRelation,
    LookupVariant,
    MatchBasis,
    NormalizedNameAnalysis,
    QueryRankShape,
)

HYBRID_SIGN = "\u00d7"

_RANK_ALIAS_MAP: dict[str, tuple[str, str]] = {
    "subsp.": ("subsp.", "subspecies"),
    "subsp": ("subsp.", "subspecies"),
    "ssp.": ("subsp.", "subspecies"),
    "ssp": ("subsp.", "subspecies"),
    "subspecies": ("subsp.", "subspecies"),
    "nothosubsp.": ("nothosubsp.", "nothosubspecies"),
    "nothosubsp": ("nothosubsp.", "nothosubspecies"),
    "nssp.": ("nothosubsp.", "nothosubspecies"),
    "nssp": ("nothosubsp.", "nothosubspecies"),
    "var.": ("var.", "variety"),
    "var": ("var.", "variety"),
    "variety": ("var.", "variety"),
    "nothovar.": ("nothovar.", "nothovariety"),
    "nothovar": ("nothovar.", "nothovariety"),
    "nvar.": ("nothovar.", "nothovariety"),
    "nvar": ("nothovar.", "nothovariety"),
    "subvar.": ("subvar.", "subvariety"),
    "subvar": ("subvar.", "subvariety"),
    "subvariety": ("subvar.", "subvariety"),
    "f.": ("f.", "form"),
    "f": ("f.", "form"),
    "fa.": ("f.", "form"),
    "fa": ("f.", "form"),
    "forma": ("f.", "form"),
    "form": ("f.", "form"),
    "subf.": ("subf.", "subform"),
    "subf": ("subf.", "subform"),
    "subforma": ("subf.", "subform"),
    "subform": ("subf.", "subform"),
    "convar.": ("convar.", "convar"),
    "convar": ("convar.", "convar"),
    "conv.": ("convar.", "convar"),
    "prol.": ("prole", "prole"),
    "prole": ("prole", "prole"),
    "lusus": ("lusus", "lusus"),
}

_INLINE_QUOTED_CULTIVAR_RE = re.compile(
    r"(?:\s+(?:cv\.?\s+)?['\u2018][^'\u2019]+['\u2019]"
    r"|\s+(?:cv\.?\s+)?[\"\u201c][^\"\u201d]+[\"\u201d])\s*$",
    flags=re.IGNORECASE,
)
_INLINE_CV_RE = re.compile(r"\s+\bcv\.?\s+.+$", flags=re.IGNORECASE)
_GENUS_TOKEN_RE = re.compile(r"^[A-Z][a-zA-Z-]+$")
_EPITHET_TOKEN_RE = re.compile(r"^[a-z][a-z-]+$")
_AUTHOR_SHORT_RE = re.compile(r"^(?:\(|[A-Z](?:\.|[a-z]*\.)$|[A-Z][a-z-]+$)")
_AUTH_PUNCT_SPACING_RE = re.compile(r"\s*([().&,])\s*")


def normalize_whitespace(text: str) -> str:
    nfkc = unicodedata.normalize("NFKC", text).replace("\u00a0", " ")
    return re.sub(r"\s+", " ", nfkc).strip()


def _strip_inline_cultivar(name: str) -> tuple[str, bool]:
    stripped = _INLINE_QUOTED_CULTIVAR_RE.sub("", name).strip()
    if stripped != name:
        return stripped, True
    stripped_cv = _INLINE_CV_RE.sub("", name).strip()
    if stripped_cv != name:
        return stripped_cv, True
    return name, False


def _looks_like_uninomial_author(token: str) -> bool:
    return (
        token.startswith("(")
        or token.endswith(".")
        or "&" in token
        or any(ch.isdigit() for ch in token)
    )


def _split_inline_authorship_and_structure(
    name: str,
) -> tuple[str, str | None, QueryRankShape, list[str], bool]:
    """Separate trailing botanical authorship while preserving rank & hybrid metadata."""
    tokens = [token for token in name.split(" ") if token]
    if not tokens:
        return name, None, "other", [], False

    idx = 0
    is_hybrid = False
    stem_tokens: list[str] = []

    if tokens[0] in {HYBRID_SIGN, "x", "X"} and len(tokens) > 1:
        is_hybrid = True
        stem_tokens.append(tokens[0])
        idx = 1

    first = tokens[idx]
    if first.startswith(HYBRID_SIGN) and len(first) > 1:
        is_hybrid = True
        genus_part = first[1:]
        if not _GENUS_TOKEN_RE.match(genus_part):
            return name, None, "other", [], True
        stem_tokens.append(first)
        idx += 1
    elif first.startswith(("x", "X")) and len(first) > 2 and first[1].isupper():
        is_hybrid = True
        stem_tokens.append(first)
        idx += 1
    elif _GENUS_TOKEN_RE.match(first):
        stem_tokens.append(first)
        idx += 1
    else:
        return name, None, "other", [], False

    # Genus-only or Genus + Author (e.g. "Salvia L.")
    if idx >= len(tokens):
        return " ".join(stem_tokens), None, "uninomial", [], is_hybrid

    if _looks_like_uninomial_author(tokens[idx]):
        return (
            " ".join(stem_tokens),
            " ".join(tokens[idx:]),
            "uninomial",
            [],
            is_hybrid,
        )

    # Optional interspecific hybrid marker before specific epithet
    if tokens[idx] in {HYBRID_SIGN, "x", "X"}:
        if idx + 1 >= len(tokens):
            return name, None, "other", [], True
        # Hybrid formula such as "Genus a x Genus b" stays unsplit
        if _GENUS_TOKEN_RE.match(tokens[idx + 1].lstrip(HYBRID_SIGN)):
            return name, None, "other", [], True
        is_hybrid = True
        stem_tokens.append(tokens[idx])
        idx += 1

    candidate_epithet = tokens[idx]
    if candidate_epithet.startswith(HYBRID_SIGN) and len(candidate_epithet) > 1:
        is_hybrid = True
        epithet_core = candidate_epithet[1:]
    else:
        epithet_core = candidate_epithet
    if not _EPITHET_TOKEN_RE.match(epithet_core):
        return name, None, "other", [], is_hybrid
    stem_tokens.append(candidate_epithet)
    idx += 1

    infraspecific_ranks: list[str] = []
    while idx < len(tokens):
        rank_info = _RANK_ALIAS_MAP.get(tokens[idx].casefold())
        if rank_info is None:
            break
        canonical_marker, normalized_rank = rank_info
        if idx + 1 >= len(tokens):
            break
        next_idx = idx + 1
        infra_tokens = [tokens[idx]]
        if tokens[next_idx] in {HYBRID_SIGN, "x", "X"} and next_idx + 1 < len(tokens):
            is_hybrid = True
            infra_tokens.append(tokens[next_idx])
            next_idx += 1
        infra_ep = tokens[next_idx]
        if infra_ep.startswith(HYBRID_SIGN) and len(infra_ep) > 1:
            is_hybrid = True
            infra_ep_core = infra_ep[1:]
        else:
            infra_ep_core = infra_ep
        if not _EPITHET_TOKEN_RE.match(infra_ep_core):
            break
        if canonical_marker.startswith("notho"):
            is_hybrid = True
        infraspecific_ranks.append(normalized_rank)
        infra_tokens.append(tokens[next_idx])
        stem_tokens.extend(infra_tokens)
        idx = next_idx + 1

    extracted_authorship: str | None = None
    if idx < len(tokens):
        tail = tokens[idx:]
        first_tail = tail[0]
        if _AUTHOR_SHORT_RE.match(first_tail) or any(ch.isupper() for ch in first_tail):
            extracted_authorship = " ".join(tail)
        else:
            return name, None, "other", infraspecific_ranks, is_hybrid

    if infraspecific_ranks:
        rank_shape: QueryRankShape = "hybrid_infraspecific" if is_hybrid else "infraspecific"
    else:
        rank_shape = "hybrid_binomial" if is_hybrid else "binomial"

    return (
        " ".join(stem_tokens),
        extracted_authorship,
        rank_shape,
        infraspecific_ranks,
        is_hybrid,
    )


def _canonicalize_ranks(text: str) -> tuple[str, bool]:
    changed = False
    out: list[str] = []
    for token in text.split(" "):
        info = _RANK_ALIAS_MAP.get(token.casefold())
        if info is not None and token != info[0]:
            out.append(info[0])
            changed = True
        else:
            out.append(token)
    return " ".join(out), changed


def _hybrid_variants(stem: str) -> list[tuple[str, MatchBasis]]:
    """Generate ordered normalized hybrid keys plus downgraded marker-dropped fallback."""
    variants: list[tuple[str, MatchBasis]] = []
    tokens = [token for token in stem.split(" ") if token]
    if not tokens:
        return variants

    # 1) Canonical spaced U+00D7 for ASCII standalone 'x'/'X' or tight prefix
    normalized_tokens: list[str] = []
    saw_ascii_x = False
    for index, token in enumerate(tokens):
        if (token in {"x", "X"} and index > 0) or (token == "x" and index == 0 and len(tokens) > 1):
            normalized_tokens.append(HYBRID_SIGN)
            saw_ascii_x = True
        elif token.startswith(HYBRID_SIGN) and len(token) > 1:
            normalized_tokens.extend((HYBRID_SIGN, token[1:]))
        elif token.startswith(("x", "X")) and len(token) > 2 and index == 0 and token[1].isupper():
            normalized_tokens.extend((HYBRID_SIGN, token[1:]))
            saw_ascii_x = True
        else:
            normalized_tokens.append(token)

    spaced = " ".join(normalized_tokens)
    if spaced != stem:
        basis: MatchBasis = "hybrid_sign_normalized" if saw_ascii_x else "hybrid_spacing_normalized"
        variants.append((spaced, basis))

    # 2) Tight U+00D7 Genus/epithet variants (e.g. tight genus or tight epithet)
    if len(normalized_tokens) >= 2 and normalized_tokens[0] == HYBRID_SIGN:
        tight_genus = " ".join([HYBRID_SIGN + normalized_tokens[1], *normalized_tokens[2:]])
        if tight_genus != stem:
            variants.append((tight_genus, "hybrid_spacing_normalized"))
    for i in range(1, len(normalized_tokens) - 1):
        if normalized_tokens[i] == HYBRID_SIGN:
            tight_ep = " ".join(
                [
                    *normalized_tokens[:i],
                    HYBRID_SIGN + normalized_tokens[i + 1],
                    *normalized_tokens[i + 2 :],
                ]
            )
            if tight_ep != stem:
                variants.append((tight_ep, "hybrid_spacing_normalized"))

    # 3) ASCII 'x' equivalent when input used U+00D7
    ascii_tokens = ["x" if t == HYBRID_SIGN else t for t in normalized_tokens]
    ascii_x = " ".join(ascii_tokens)
    if ascii_x != stem and ascii_x != spaced:
        variants.append((ascii_x, "hybrid_sign_normalized"))

    # 4) Downgraded advisory fallback without hybrid marker (LOW confidence, not auto-confirmable)
    no_marker = " ".join(t for t in normalized_tokens if t != HYBRID_SIGN)
    if no_marker and no_marker != stem and no_marker != spaced:
        variants.append((no_marker, "hybrid_marker_dropped"))
    return variants


def _build_fuzzy_prefixes(stem: str) -> list[str]:
    cleaned = [t for t in stem.split(" ") if t and t not in {HYBRID_SIGN, "x", "X"}]
    if not cleaned:
        return []
    first = cleaned[0].lstrip(HYBRID_SIGN).casefold()
    if len(cleaned) == 1:
        return [first[:4]] if len(first) >= 4 else [first]
    second = cleaned[1].lstrip(HYBRID_SIGN).casefold()
    prefixes: list[str] = []
    if len(second) >= 3:
        prefixes.append(f"{first} {second[:3]}")
    prefixes.append(f"{first} {second[:1]}" if second else f"{first} ")
    seen: set[str] = set()
    unique: list[str] = []
    for p in prefixes:
        if p and p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def analyze_identity_name(
    scientific_name: str, cultivar_name: str | None = None
) -> NormalizedNameAnalysis:
    """Analyze a botanical identity name cleanly without mutating user-authored strings."""
    normalized_raw = normalize_whitespace(scientific_name)
    normalized_cultivar = normalize_whitespace(cultivar_name) if cultivar_name else None
    has_cultivar = bool(normalized_cultivar)

    without_cultivar, inline_cultivar = _strip_inline_cultivar(normalized_raw)
    stem, extracted_author, rank_shape, infraspecific_ranks, is_hybrid = (
        _split_inline_authorship_and_structure(without_cultivar)
    )
    canonical_rank_stem, rank_changed = _canonicalize_ranks(stem)

    variants: list[LookupVariant] = []
    seen_keys: set[str] = set()

    def add_variant(text: str, basis: MatchBasis) -> None:
        key = text.strip().casefold()
        if key and key not in seen_keys:
            seen_keys.add(key)
            variants.append(LookupVariant(query_key=key, match_basis=basis))

    literal_trim = scientific_name.strip()
    exact_basis: MatchBasis = (
        "exact_literal" if normalized_raw == literal_trim else "normalized_whitespace"
    )
    add_variant(normalized_raw, exact_basis)

    if rank_changed:
        if inline_cultivar:
            add_variant(canonical_rank_stem, "inline_cultivar_stripped")
        elif extracted_author:
            add_variant(canonical_rank_stem, "inline_authorship_stripped")
        else:
            add_variant(canonical_rank_stem, "rank_token_normalized")

    if inline_cultivar:
        add_variant(without_cultivar, "inline_cultivar_stripped")
    if extracted_author:
        add_variant(stem, "inline_authorship_stripped")

    target_stems = (
        [canonical_rank_stem] if canonical_rank_stem == stem else [canonical_rank_stem, stem]
    )
    for target_stem in target_stems:
        for candidate_variant, h_basis in _hybrid_variants(target_stem):
            effective_basis = h_basis
            if extracted_author and h_basis != "hybrid_marker_dropped":
                effective_basis = "inline_authorship_stripped"
            if inline_cultivar and h_basis != "hybrid_marker_dropped":
                effective_basis = "inline_cultivar_stripped"
            add_variant(candidate_variant, effective_basis)

    # Sort variants deterministically by priority while preserving primary exact check first.
    priority_order: dict[MatchBasis, int] = {
        "exact_literal": 0,
        "normalized_whitespace": 1,
        "rank_token_normalized": 2,
        "hybrid_sign_normalized": 3,
        "hybrid_spacing_normalized": 4,
        "inline_authorship_stripped": 5,
        "inline_cultivar_stripped": 6,
        "hybrid_marker_dropped": 7,
        "fuzzy_genus_fallback": 8,
        "none": 9,
    }
    variants.sort(key=lambda item: priority_order[item.match_basis])

    return NormalizedNameAnalysis(
        raw_scientific_name=scientific_name,
        normalized_scientific_name=normalized_raw,
        canonical_stem=canonical_rank_stem if rank_changed else stem,
        extracted_authorship=extracted_author,
        cultivar_name=normalized_cultivar,
        has_cultivar=has_cultivar,
        inline_cultivar_syntax=inline_cultivar,
        detected_rank_shape=rank_shape,
        infraspecific_ranks=infraspecific_ranks,
        rank_marker_canonicalized=rank_changed,
        is_hybrid=is_hybrid,
        fuzzy_prefixes=_build_fuzzy_prefixes(canonical_rank_stem),
        lookup_variants=variants,
    )


def normalize_authorship_text(value: str) -> str:
    collapsed = normalize_whitespace(value)
    collapsed = _AUTH_PUNCT_SPACING_RE.sub(r"\1", collapsed)
    return collapsed.strip().casefold()


def compare_authorship(
    query_authorship: str | None, candidate_authorship: str | None
) -> AuthorshipRelation:
    """Compare optional query authorship against a provider candidate author string."""
    if not query_authorship or not query_authorship.strip():
        return "not_provided"
    if not candidate_authorship or not candidate_authorship.strip():
        return "mismatch"
    raw_q = normalize_whitespace(query_authorship)
    raw_c = normalize_whitespace(candidate_authorship)
    if raw_q == raw_c:
        return "exact"
    if normalize_authorship_text(raw_q) == normalize_authorship_text(raw_c):
        return "compatible_normalized"
    return "mismatch"


def semantic_comparison_key(scientific_name: str) -> str:
    """Canonicalize minor hybrid/rank punctuation for cross-source name equality checks."""
    cleaned = normalize_whitespace(scientific_name)
    cleaned, _ = _canonicalize_ranks(cleaned)
    tokens: list[str] = []
    for index, token in enumerate(cleaned.split(" ")):
        if token in {HYBRID_SIGN, "x", "X"} and (index > 0 or len(cleaned.split(" ")) > 1):
            tokens.append(HYBRID_SIGN)
        elif token.startswith(HYBRID_SIGN) and len(token) > 1:
            tokens.extend((HYBRID_SIGN, token[1:]))
        else:
            tokens.append(token)
    return " ".join(tokens).casefold()
