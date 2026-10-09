# Collection phylogeny — PHYLOGENY-001

**Planned; source gate blocked on 2026-10-09.** There is no implemented Phylogeny workspace,
OTT relationship, API, migration or provisioned Florabase source in this increment. The
[source audit](phylogeny-001-source.md) verifies Open Tree's actual release/artifact and records
the unmet exact data-rights boundary. This document preserves the requested product contract for
implementation after source GO; it must not be read as documentation of delivered behavior.

## Three independent meanings

- **Taxonomy:** classification, provided by the independently verified TAXONOMY-003 WFO workspace.
- **Phylogeny:** inferred/synthesised evolutionary relationships from a separately reviewed source.
- **Collection Lineage:** explicit material ancestry, such as SeedLot → Sowing → Plant.

Family, genus, classification parent IDs, shared scientific names and recorded material ancestry
must not generate evolutionary evidence. A source topology is not an evolutionary time estimate.

## Mapping and collection eligibility

Future implementation must retain one explicitly reviewed current OTT mapping per BotanicalIdentity,
with source version/checksum and immutable review evidence. Existing WFO or GBIF/CoL XR links do not
infer an OTT link. Name resolution only proposes candidates; confirmation is a separate operator
action after inspecting exact ID, names, rank, synonym context, taxonomy and match diagnostics.
Stale source/identity/link versions require re-review rather than overwrite. No automatic local
rename, merge, synonym history or reconciliation belongs in this feature.

Reuse the exact [EXPLORE-001 representation matrix](species-distribution.md) and
[EXPLORE-002 category semantics](native-ranges-explore.md): All represented / Living / Current /
Historical; Seeds / Sowings / Plants / Plant groups / Stored material with OR category selection.
Historical still means globally no Current representation, including in unselected categories.
Reference-only identities are excluded. One BotanicalIdentity contributes once regardless of record
count; mapped and unresolved identities both remain discoverable.

Multiple cultivar identities explicitly reviewed against one source species should share a
species-oriented tip with separate collection identity detail; they must not acquire invented
source branches. Infraspecific nodes need their own exact source resolution. Unlinked, ambiguous,
absent, stale and unsafe placements remain **Unresolved phylogeny** with specific reasons.

## Source projection and scientific presentation

Build only the induced/pruned collection topology and necessary internal ancestors. Use actual
synthetic relationships, preserving multi-child polytomies and relevant support/conflict evidence.
The source audit found long unary paths: compression must retain original path evidence and must
not describe a composite displayed edge using only one node's support. Unnamed synthetic nodes
retain their IDs; labels must not be fabricated from neighbouring taxonomy.

Distinguish explicit phylogeny support, explicit taxonomy support, mixed support and unavailable
evidence according to reviewed provider fields. `terminal`, missing annotations or a study count
must not be promoted into confidence/support. Conflicting input trees and broken placements remain
visible. Use a cladogram with clearly topological spacing; no invented branch lengths, genetic
relatedness percentages or divergence dates. MRCA, if later approved, means a shared node in this
pinned synthetic topology, separately from taxonomic MRCA and dating.

Related in my collection may describe shared synthetic nodes and contributing identities; it must
coexist with TAXONOMY-003's Same genus / Same family labels. Selecting/filtering/focusing a tree
must never silently change either source relationships or eligible collection identities.

## Intended workspace and runtime

The requested Explore destination is **Phylogeny**, alongside Botanical identities, Taxonomy,
Media and Geography, outside the existing Maps subgroup. No navigation change has been made.
Functional UI would provide a rooted collapsible tree, selectable internal nodes, companion
node/identity detail, search/focus, a textual relationship list and visible unresolved section.
Hundreds of tips must be navigable without requiring complete expansion or massive horizontal
scroll. Mobile needs focused/drill-down/list navigation, keyboard access and honest selection;
review at 1440×844, 1024×844 and 390×844 after implementation.

Show exact source release, provisioning/retrieval date and relevant node provenance. Normal page
loads must be local and authenticated. Explicit bounded provisioning/refresh may send reviewed
OTT IDs only after explaining that external retrieval; it must retain a pinned content-hashed
artifact and preserve previous evidence on failure/version change. The full synthetic tree belongs
in optional reference data, not canonical PostgreSQL by default. Missing/corrupt/uninstalled source
must leave startup, Taxonomy and collection workflows healthy and existing mappings intact.

Tree/node read APIs, mapping confirmation, artifact publication, bounds, query counts, source
lookups, construction latency, payload size and rendering performance remain implementation work.
No arbitrary provider proxy or unauthenticated collection endpoint. Minimal mapping migration, if
needed, must follow actual Alembic head (currently 0040); no 0041 migration is reserved or created.

**Saved Views remain undecided at the source gate.** Audit stable scope/category/search/node state
after a real workspace exists; do not persist pan/zoom, hover or every expansion. A canonical URL
may suffice, following the independently accepted Taxonomy pattern. No new Saved View surface.

## Verification and UAT boundary

After source GO, implementation must cover exact pinned source/checksum validation, malformed and
invalid topology, duplicate/missing IDs, annotation parsing, exact/ambiguous/synonym/no-match and
stale mappings, cultivar/species sharing, deterministic induced trees, necessary ancestors,
polytomies, support distinctions, all scopes/categories and unresolved identity preservation.
Normal tests must be offline. PostgreSQL must exercise migration, concurrency/auth/stale guards and
bounded query counts; frontend coverage must exercise navigation, selection, source labels,
filters/search, responsiveness, keyboard/focus and loading/error/empty/unavailable states.

Only then transition UAT through its actual owner's guarded retirement, start/seed/status from
this worktree, and prepare real approved source-ID examples covering related and separated taxa,
cultivar/infraspecific, historical, seed-only, multi-category and unresolved identities. Operator
UAT and Luna's independent QA/canonical gate follow. The existing `748b` Taxonomy Preview is
preserved because this source-blocked increment has no replacement UI to review.

TAXONOMY-001/002, BOTANY-003/004 and ENRICHMENT-002 retain their planned ownership. The broad
cross-application visual/product review remains the later checkpoint in the roadmap.
