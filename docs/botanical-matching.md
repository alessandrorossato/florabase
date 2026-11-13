# Botanical Reference Matching — Slice 1A Foundation

`BOTANICAL-MATCH-001 / Slice 1A` provides the deterministic, strictly read-only local candidate
discovery and classification engine for **WFO `2026-06`** and **WCVP `v16`** (while preserving
optional historical **WCVP `v15`** inspection).

Slice 1A performs **no database writes**, creates **no migrations**, executes **no remote GBIF/CoL
network calls**, never mutates `BotanicalIdentity`, profiles, or native ranges, and never alters
existing `WfoSource` or `WcvpSource` SQLite index schemas or seal checks.

## Module Overview

- [`normalizer.py`](../backend/src/florabase/botanical_matching/normalizer.py):
  - Pure string normalization (`NFKC`, unicode whitespace collapsing).
  - Separates cultivars (`cultivar_name` and inline `'Cultivar'` / `cv. Cultivar` detection).
  - Extracts inline authorship conservatively as **advisory only** (`extracted_authorship`).
  - Canonicalizes infraspecific rank markers (`ssp.` → `subsp.`, `var` → `var.`, `fa.` → `f.`,
    `nvar.` → `nothovar.`, etc.) and hybrid markers/spacing (`x`, `X`, `×`, `×Genus`, `×epithet`).
  - Emits ordered exact-lookup query variants plus bounded 4-character fuzzy prefixes (never empty
    strings) for fallback advisory suggestions only.
- [`taxonomy/source.py`](../backend/src/florabase/taxonomy/source.py) and
  [`native_range_enrichment/source.py`](../backend/src/florabase/native_range_enrichment/source.py):
  - Add `exact_matches_with_context`, `exact_matches`, and `prefix_candidates` using a **single
    read-only SQLite connection** per batch, chunked `IN (...)` queries (`100` keys/chunk;
    WCVP accepted-target fetches `200` IDs/chunk), bounded per-key results (`ROW_NUMBER()` in
    WFO/WCVP), and explicit `truncated_keys` / `path_errors`.
  - Keep `SCHEMA`, SHA-256 seal checks (`require_seal`), `search()`, `hierarchy()`, `taxon()`,
    `distribution()`, and WCVP `v15` historical support unchanged.
- [`classifier.py`](../backend/src/florabase/botanical_matching/classifier.py):
  - Classifies per-provider outcomes (`auto_eligible`, `review_required`, `ambiguous`, `ineligible`,
    `no_match`, `already_linked`, `source_unavailable`) with confidence tiers (`exact`, `high`,
    `medium`, `low`, `none`) and explicit reason codes.
  - Enforces all safety policies:
    - Existing verified/manual links on the current dataset version/checksum are preserved (`already_linked`).
    - Synthetic Golden links (`authorship == "Golden"`, `synthetic_golden=True`, `"Golden ..."` WCVP
      names) are flagged with `synthetic_evidence_present` and never treated as verified official proof.
    - Cultivar identities require explicit operator selection of the species/parent anchor
      (`cultivar_species_anchor` for explicit `cultivar_name`; `inline_cultivar_syntax` when inline
      `'Cultivar'` / `cv.` syntax is stripped from `scientific_name`).
    - Authorship is advisory: homonyms are never auto-resolved by authorship, and single-candidate
      authorship mismatches require review (`authorship_mismatch`).
    - WCVP synonyms remain `ineligible` on direct link confirmation (`wcvp_synonym_ineligible`) while
      exposing `resolved_accepted_target_available`; WFO synonyms require review (`wfo_synonym_matched`).
    - Fuzzy-only matches never qualify for `auto_eligible` (`fuzzy_advisory_only`, `low` confidence).
    - Cross-source disagreements (`wfo` vs `wcvp_v16`), WCVP `v15` vs `v16` disagreements, and
      conflicts with local GBIF `ExternalTaxonLink` records downgrade any `auto_eligible` outcome to
      `review_required` and elevate `overall_status` to `conflict`.
- [`discovery.py`](../backend/src/florabase/botanical_matching/discovery.py):
  - `discover_and_classify(...)`: executes bounded batched local discovery and cross-source classification.
  - `load_collection_match_inputs(...)` / `match_collection_identities(...)`: loads active
    (non-merged tombstone) `BotanicalIdentity` rows, collection representation flags (`SeedLot` /
    `Plant`), and existing `WfoLink`, `WcvpLink`, and `ExternalTaxonLink(provider='gbif')` rows in
    bounded O(1) read-only ORM `SELECT` statements.
  - `build_match_report(...)` and `format_match_report_markdown(...)`: produce coverage counts and
    ranked exception categories with representative examples.

## Read-Only Qualification Command

[`backend/scripts/botanical_match_qualify.py`](../backend/scripts/botanical_match_qualify.py) runs
this pipeline read-only against JSON inputs (`--input-json`) or a configured PostgreSQL database
(`--database-url`, executing inside `SET TRANSACTION READ ONLY`) using local official SQLite
indexes without copying reference files or mutating database state.

Example in an isolated Quality Compose container with a `:ro` reference cache mount:

```bash
python3 ./scripts/workflow_environment.py quality compose -- run --rm -T --no-deps \
  -v /path/to/.source-cache:/ref-cache:ro \
  -v /tmp/match-io:/io \
  backend python scripts/botanical_match_qualify.py \
  --input-json /io/identities.json \
  --wfo-path /ref-cache/wfo-2026-06.sqlite \
  --wcvp-v16-path /ref-cache/wcvp-v16/index.sqlite \
  --wcvp-v16-require-seal \
  --require-sources \
  --format markdown
```

## Follow-Up Requirements for Persistence & Approval Increments (Slice 1B / Slice 2)

Future slices building on Slice 1A should implement:

1. **Match Proposal & Batch Audit Persistence (Alembic Migration)**:
   - Persist reviewable match runs/proposals keyed by identity, target provider (`wfo`, `wcvp`, `gbif`),
     candidate taxon ID, pinned source version/checksum, reason codes, confidence, and
     `identity_updated_at` stale-write guard, without storing derived/synthetic Golden state as official evidence.
2. **Explicit Operator Approval, Bulk Apply, & Rollback APIs**:
   - Accept batch selection/confirmation only for eligible candidates; require explicit operator
     choice for homonyms (`ambiguous`), cultivars (`cultivar_species_anchor`), synonyms, cross-source
     conflicts, and all GBIF suggestions; preserve existing verified/manual links unless explicitly
     replaced; record pre-apply link state for transactional rollback; refresh OpenAPI + generated TS client.
3. **Optional Opt-In GBIF Reconciliation & Golden Enrichment Workflow**:
   - Trigger remote GBIF lookup only from explicit operator/CLI jobs (never on `GET` requests or
     ordinary page loads).
   - Provide an explicit, reproducible Golden COMPREHENSIVE enrichment step offline from
     baseline fixtures so Golden reset reproducibility remains deterministic.
4. **Review & Conflict Resolution UI**:
   - Accessible review queue (`PageHeader` / `DirectoryTools`) exposing provider side-by-side status,
     reason codes, authorship advisories, WFO vs WCVP v16 conflicts, and bulk confirm of clean
     `auto_eligible` rows only after explicit operator review.
