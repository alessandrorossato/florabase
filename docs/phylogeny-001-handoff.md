# PHYLOGENY-001 — blocked source-audit handoff

Implementation owner: Sol. **SOURCE_BLOCKED**; no implementation/visual-review handoff is claimed.
The exact data-rights approval prerequisite in the operator request stopped product implementation.
See [source evidence and reopening criterion](phylogeny-001-source.md) and the
[preserved product contract](collection-phylogeny.md).

## WORKTREE AT SOURCE-GATE STOP

`/home/alessandro/.codex/worktrees/4aaf/florabase`, branch
`feat/phylogeny-001-collection-tree`, initialized through `make feature-init` from clean detached
HEAD and cached origin/main **33f5592b4bdd288a67f72e7dd1177d3d98bfb56c**. Primary remains clean
on that main commit. No additional worktree was created. At that source-gate stop, the seven-file
documentation change was unstaged; this document records the blocked handoff before independent
verification and protected delivery.

## SOURCE / SOURCE VERSION / LICENSE / CHECKSUM

Open Tree of Life actual current API and downloaded synthetic artifact: **opentree16.1**,
OTT **3.7draft3** / configuration **ott3.7.3**, annotation completion **2025-12-20 00:55:58**
(upstream timezone unspecified). Release-page June 2025 text is inconsistent with artifact/API.
Securely retrieved **41,608,973-byte** archive; measured SHA-256
`c447c83e49f0cf61fa96d9a02c6135b809abf315ad384fdb26b88359a28da12c`.
Current conditional CC0 notice, old synthetic-artifact CC0 declaration and actual mixed/missing
input-license metadata are all recorded; no exact-release production license GO.

## DATA-RIGHTS REVIEW

Nine pinned input snapshots referenced by prospective fixture taxa: three CC0, one empty license,
five missing license fields. This does not prove synthetic topology is prohibited. The **2017
producer declaration expressly supports synthetic/OTT artifact CC0**, but a current exact scope
for this release plus its required derived support/conflict annotation representation was not
established against the pre-existing-terms caveat. The audit distinguishes approval of minimal
derived relationships/IDs from redistribution of original input trees. Reopen on authoritative
current scope/credits or a separately reviewed exact licensed alternative; no blind waiver,
article-license substitution or inferred removal of input effects. No maintainer message was sent.

## TAXON MAPPING

Actual archive verifies six source examples; explicit non-approximate TNRS returned basil/Holy
basil/sage candidates. These are **not** durable reviewed links. No WFO↔OTT crosswalk approved;
BotanicalIdentity, WFO, CoL XR/GBIF, OTT taxon and synthetic node IDs remain distinct. Future
confirmation must show exact candidate context/diagnostics and compare source/identity/link versions.
Cultivars sharing one species tip preserve separate local identities; no automatic species fallback.

## TREE SEMANTICS / SUPPORT / UNCERTAINTY

Actual six-example induced API response: 6 tips, 156 nodes, 145 unary nodes, depth 59, 27 supporting
tree references; sampled structure valid with unique IDs, no polytomy in this particular response.
It is not full-global-tree validation. Node-info paths show mixed/taxonomy evidence and conflicts;
basil has 69 ancestors, sage 65. Do not copy Taxonomy's depth-64 bound. Empty annotation and
`terminal` alone do not establish support. Polytomies remain multi-child; compressed paths need
all intervening evidence. No production projection or node detail implemented.

## BRANCH-LENGTH POLICY / MRCA POLICY

ID-labelled full and sampled induced tree have no branch lengths: intended rendering is topological
cladogram, without distance/time/percentage claims. MRCA may mean a pinned synthetic shared node
only after separate product review; no dating or MRCA UI implemented.

## COLLECTION FILTERS / UNRESOLVED IDENTITIES / RELATED-IN-COLLECTION

Intended contract reuses exact shared EXPLORE-001/002 scopes/category OR eligibility. Distinct local
identities contribute once; same OTT taxon can group separately retained identities. Unlinked,
ambiguous, missing, stale and unsafe taxa stay visible unresolved. Phylogenetic shared-node context
must coexist with unchanged Taxonomy relationships and material Lineage. None implemented here.

## API / PERFORMANCE

No Florabase API/generated artifact changes. Explicit official probes used only fixed public source
examples, never the database collection. Local full-index and bounded explicit induced provisioning
were evaluated; normal reads must be local in either case. Sample induced payload **3,667 bytes**,
two node-info paths **191,730 bytes**; no PostgreSQL/query/index/render or latency benchmark claimed.
Host disk had roughly 327 MiB free and swap was full; no image builds were attempted. This limit is
separate from the rights blocker. No source/reference artifact installed.

## MIGRATION / SAVED VIEWS DECISION

No migration or new canonical state; head remains **20261009_0040**. Expected future mapping-only
revision must be checked against actual head, not preallocated here. Saved Views remain undecided
until implementation; the stable-URL pattern was audited, with transient state excluded.

## UI / ACCESSIBILITY / TESTS

No new UI, route, mapping controls or visual/accessibility review claimed. The planned contract
records rooted tree/detail/list/search, mobile focus/drill-down, keyboard states and target widths.
Existing isolated offline baseline **54 passed** (`--no-cov`): `test_taxonomy.py`,
`test_taxonomy_service.py`, `test_taxonomy_api.py`, `test_native_ranges_explore.py`,
`test_species_distribution.py`. Installed UAT development image, current source read-only, network
disabled, tmpfs scratch, no database/application volume. Feature graph **98 valid**.
No new parser/mapping/tree/frontend/integration suite exists at the stopped source gate.
Pinned Prettier reports all seven changed documentation files formatted; `git diff --check` and
feature-graph checks pass. Results from the subsequent independent canonical gate are recorded in
the current [progress milestone](progress.md#2026-10-09--phylogeny-001-source-audit-blocked-before-implementation).
At the source-gate stop, canonical verification, staging, commit and delivery had not yet run. The
subsequent independent verification and protected-delivery outcome belong to this audit's final
delivery report; they do not change the source-gate decision or feature status.

## UAT

Read-only `make uat-preview-status` identifies actual owner
`/home/alessandro/.codex/worktrees/748b/florabase`, frontend/backend/db healthy and schema **0040**.
It correctly exits with source mismatch for `4aaf`. No retirement, takeover, seed/reset, DEV,
Stable Preview or production mutation. Existing [Taxonomy Preview](http://localhost:15174/#/taxonomy)
remains available; this is not a Phylogeny UAT environment. Real OTT IDs are audit examples only.

## ROADMAP

Existing PHYLOGENY-001 retained as **planned**; no replacement ID or successful-implementation
status. TAXONOMY-003 remains independently verified and unchanged. TAXONOMY-001/002,
BOTANY-003/004 and ENRICHMENT-002 retain planned boundaries. SCHEDULE-001 is not introduced or
reprioritized. Broad application visual/product review remains deferred.

SOURCE_BLOCKED
