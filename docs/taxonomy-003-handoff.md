# TAXONOMY-003 — implementation handoff

Implementation owner: Sol. Independent visual/product review and canonical verification completed by
Luna/operator on the final implementation and test fixes. TAXONOMY-003 is verified; delivery and
conservative finish remain tracked separately from product verification.

## WORKTREE

`/home/alessandro/.codex/worktrees/748b/florabase`, branch
`feat/taxonomy-003-collection-tree`, initialized by `make feature-init` from verified cached main
`a8ae74a75111b7a9ce1fd70862ba9be08bea4752`. Primary remained clean on that exact main commit.
The final verification receipt covers the reviewed source, tests and documentation. The changes are
still unstaged pending the authorized commit step.

## SOURCE

**GO** for classification only. Official World Flora Online Plant List ColDP archive securely retrieved
from Zenodo record `20782718`; complete archive and classification tables inspected before production
implementation. No WFO HTML scraping, TLS bypass, provider inference or collection transmission.
See [exact source audit](taxonomy-003-source.md) for fields, counts, publisher exporter evidence and
the one reviewed external non-taxonomic Code-parent boundary.

## SOURCE VERSION

Zenodo `2026-06`, published 2026-06-21; embedded `2026-06 01`. Actual archive retrieval
`2026-10-09T14:48:29Z`. Existing confirmations retain immutable reviewed release evidence in their
current relationship; another release/checksum never silently updates meaning.

## LICENSE

CC0, independently present in release and embedded metadata. WFO acknowledgment/release DOI retained.
No profile prose, cultivation, uses, warnings or imagery license is approved by this classification GO.

## CHECKSUM

Archive SHA-256 `75f1ad1f371978c9e46f3044152c07ed276fe57be9fb9a15b3621b19cf231987`;
132,643,291 bytes. Published MD5 independently matches actual download. Ignored provisioned SQLite
SHA-256 `d45d9b170cabf94f6efe56ba1f54b12b4afea970ed3867be541389d364ae215e`.

## SOURCE INDEX

`backend/src/.source-cache/wfo-2026-06.sqlite` and sibling `.sha256`, ignored and excluded from Docker
images. **413,069,312 bytes (394 MiB)**; optional setting `FLORABASE_WFO_SNAPSHOT_PATH`.
The complete release contains 1,663,770 names, 454,688 accepted concepts, 1,026,322 synonym usages.
Explicit provisioning streams the pinned archive into an unpublished index, validates schema/UTF-8/
IDs/duplicates/ranks/parent/accepted references/root reachability/cycles/bounds, then publishes.
No source archive is committed. Index integrity is checked once per artifact identity/process and
cached by path/stat/seal revision; changed or corrupt bytes fail closed. Runtime requests do not parse
the archive. Normal startup and identity/profile workflows have no required source dependency.

## LINK CONTRACT

One current WFO link per BotanicalIdentity. Candidate search is explicit, local, literal prefix,
2–200 characters and at most 25 candidates. Inspect name/authorship/rank/status/exact path, then
Confirm separately. Confirmation compares identity update timestamp, source checksum and expected
relationship version/absence while holding the identity lock. Unlink compares current link version.
A real two-session PostgreSQL race proves only one expected-absence confirmation succeeds.
Local names, GBIF/CoL/WCVP links, profiles and material Lineage remain unchanged. No fuzzy/name
association, ID crosswalk, automatic rename, canonical synonym history or reconciliation.

## HIERARCHY MODEL

Accepted concept direct parents come from `taxon.tsv`; source synonym usages reference their accepted
concept through `synonym.tsv`. Literal synonym evidence survives; advisory placement uses the accepted
path. Bare names without classified usage cannot be confirmed. Biological classification terminates
at exact Plantae `wfo-4100001250`; its raw external Code parent `wfo-9971000003` remains evidence.
No guessed roots/parents or fabricated Code node. Required eligible paths form a collection-pruned union.

## RANK PRESENTATION

All 29 observed ranks survive evidence, API and counts. Default UI emphasizes major, branching and
selected ranks; nonbranching intermediates may be compressed visually. Show every source rank and
full node-detail/identity paths preserve inspection. Higher ranks/families initially open; genera
collapsed. This is taxonomy, independently of evolutionary phylogeny and recorded collection Lineage.

## REPRESENTATION FILTERS

Shared `explore.service.filtered_projection`: All represented / Living / Current / Historical.
Reference-only identities are excluded. Living is Current; Historical has no Current evidence globally.
The same eligible projection feeds tree, search, totals, details and optional filtered related peers.

## CATEGORY FILTERS

Seeds / Sowings / Plants / Plant groups / Stored material, OR within selection; none unrestricted.
Categories qualify record evidence using the delivered EXPLORE-002 semantics. Living + Seeds is empty;
a dead record in a selected category does not make an identity globally Historical while Current
material remains elsewhere. URL repeats canonical `record` values; no hidden broadening.

## COUNTS

Distinct BotanicalIdentities once per ancestor, independently of multiple retained collection records,
quantities, accepted/synonym names or occurrence records. Filter-respecting represented, Living,
Current and Historical counts. Synthetic baseline: **6 represented / 2 Living / 5 Current / 1 Historical**;
5 placed, 1 unresolved. Lamiaceae: 3 identities, 2 genera; Ocimum: 2 identities. Basil has several
collection record categories and still contributes one identity.

## UNRESOLVED IDENTITIES

Unlinked, stale identity revision, release/checksum mismatch, changed placement or unavailable source
remain visible with a contextual source-link action. No name guessing or dropped collection identities.
A filtered selected node can become visibly ineligible; no filter is broadened to restore it.
Missing/corrupt optional source leaves ordinary startup and stored identity/profile data usable.

## RELATED IN MY COLLECTION

Read-only classification labels: Same source taxon, Same genus, Same family, Same order, deterministic
within each priority. Peers are represented identities. Identity UI clearly uses All represented and
unrestricted categories; API supports the same scope/category/search filters as tree. No genetic
relatedness percentages, evolutionary distance or closest-relative claim.

## BOTANICALIDENTITY BREADCRUMB

Overview displays the complete valid confirmed path, View in Taxonomy and related peers. Reference →
Taxonomy owns explicit source review. Breadcrumbs navigate to exact source node URL state. Source
absence/mismatch does not block identity detail or manual profile editing.

## API

Authenticated GET tree/node/detail and identity taxonomy/candidates. Owner/Origin/CSRF protected
PUT exact-link confirmation and version-checked DELETE. Generated OpenAPI and TypeScript declarations
updated; `make api-check` passes. See [contract](collection-taxonomy.md) for routes, errors and bounds.
5,000 eligible identities, 100,000 fetched source nodes, depth 64, index 1 GB; explicit bound errors,
without silent truncation. No provider dataset or canonical full taxonomy is returned/copied.

## QUERY COUNTS / PERFORMANCE

PostgreSQL tree/node projection uses **2 SELECTs** regardless of identity/ancestor count (1 for empty
collection). SQLite uses **3 constant statements**: 2 metadata reads plus 1 recursive indexed path union.
Actual runtime SQLite 3.40.1 EXPLAIN confirms indexed source-ID lookups in recursive and final joins.
No per-identity PostgreSQL or per-ancestor source query. No repeated archive/full-index parsing.

| Measurement                                   | Identities | Nodes | Response bytes | Build time |
| --------------------------------------------- | ---------: | ----: | -------------: | ---------: |
| Offline index, PostgreSQL synthetic stress    |        500 |     5 |        358,833 |     299 ms |
| Complete WFO index, UAT All represented, warm |          6 |    23 |         13,226 |     887 ms |
| Complete WFO index, UAT Living                |          2 |    13 |          6,699 |     852 ms |
| Complete WFO index, UAT Current               |          5 |    16 |          9,715 |     554 ms |
| Complete WFO index, UAT Historical            |          1 |    10 |          5,145 |     470 ms |

The earlier **34.48 s** first projection and **6.93 s** checksum-only run occurred under concurrent
build/check load. Independent review repeated the request with no image/build process running. Host
context was still pressured: load average **3.78**, **1.7 GiB available RAM**, **1.9 GiB of 2 GiB
swap used**, and **1.1 GB disk available**; other long-running services included the separate
Florabase performance stack. After restarting only the UAT backend container, first Taxonomy
navigation rendered the six-identity collection in **8.84 s**; the immediate same-process page reload
took **1.07 s**. A separate read-only measurement against the same UAT database/index counted **2
PostgreSQL SELECTs and 3 SQLite statements** on both requests: **1.84 s** for its first process
projection with the index already in the OS page cache, then **22 ms** warm. It returned **6
identities, 23 required nodes, one unresolved identity and 13,226 UTF-8 bytes of serialized model JSON**.
The UI receives only those 23 required nodes (12 at major-rank initial presentation), never 1.6 million
source names. This run did not reproduce a many-tens-of-seconds first navigation; the 34.48 s
build-load outlier disappeared, while the host was not fully idle enough to call the result an
unpressured baseline. Integrity validation is once per artifact identity/process and repeats after a
backend restart; ordinary warm requests do not repeat the hash. Provisioning elapsed time and peak
memory were not separately instrumented. Full source audit took 75.58 s.

## MIGRATION

`20261009_0040` after actual `0039`, only `wfo_links`: identity FK/PK, UUIDv7 version, WFO ID check,
JSONB object evidence and UTC timestamp. Empty downgrade/reupgrade tested. Exclusive writer lock
and refusal with confirmed links preserve review evidence. No startup migrations, canonical taxonomy
copy, Saved View migration or unrelated domain schema.

## SAVED VIEWS DECISION

VIEW-001 audited and deliberately deferred: stable shareable filter/selected-node URL satisfies this
increment. No expansion/scroll/hover or source internals stored. No generic adapter or migration for
symmetry. Existing Saved Views retain their contracts.

## ACCESSIBILITY / RESPONSIVE

Browser review at **1440×844, 1024×844, 390×844**: desktop/tablet tree + detail, mobile stacked; no
horizontal overflow. Native keyboard Enter/Space selection/expansion, semantic `aria-expanded`,
`aria-pressed`, visible Selected text/border and **3 px focus outline** verified. Checkboxes corrected
to intrinsic width to avoid global text-input sizing. Full mobile path/identities/related list remain
readable. Family/genus detail, unresolved identity action, identity breadcrumb and actual source
synonym inspection reviewed. Broad cross-application visual redesign remains deferred.

## TESTS

Focused offline tests: **96 passed**, `--no-cov` (21 taxonomy source tests plus EXPLORE-001/002,
external botanical provider/service and native-range enrichment regressions).
Focused real PostgreSQL suite: **58 passed**, 18 existing Alembic path-separator deprecation warnings:
taxonomy projection/link/API/performance/concurrency, empty/populated migration, Species distribution,
Native ranges, external botanical API, native-range enrichment/view migration and identity constraints.
UAT workflow: **19 passed**. Full backend Ruff/format and strict mypy **327 files** pass; fixture
syntax/import/modern-Python lint and formatting checked under the existing script conventions.
Frontend: **85 final tests passed** across taxonomy, complete App/navigation/identity, external
botanical panel and Lineage; **19 independent Species distribution/Native ranges regressions passed**
(104 distinct frontend tests). Earlier taxonomy tests were rerun after the source-reload guard and
actual Collection taxonomy heading/Explore eyebrow assertion were corrected. The earlier dashboard/
Geography timing failures cleared in the separate reproduction without weakening tests or timeouts.
ESLint, strict TypeScript and Prettier pass. API generation/drift, feature graph **98 valid**, backend
and frontend runtime container builds and production assets pass. `git diff --check` passes.

Independent final `make feature-verify` passed after review adjustments: **895 backend tests at
90.03% coverage**, **541 frontend tests across 56 files**, and **699 PostgreSQL integration tests**;
workflow helpers, Ruff/Prettier/ESLint, strict mypy across **329 files**, TypeScript, API drift,
production backend/frontend builds, migration cycle `0039 → 0040 → 0039 → 0040`, whitespace and
worktree receipt all passed. The existing UX-004 tab expectation was updated to include Taxonomy.
TAXONOMY-003 is verified; broad cross-application visual redesign remains deferred.

## UAT

Previous actual owner: `/home/alessandro/.codex/worktrees/16cc/florabase`. Retired only through
`make uat-preview-remove CONFIRM_REMOVE_UAT_PREVIEW=florabase-uat-preview` in that owner.
Current owner is this `748b` worktree. `make uat-preview-up` migrated the fresh isolated database to
0040; its initial frontend health deadline failed during dependency initialization/concurrent builds.
Without changing timeouts, subsequent status confirmed **frontend/backend/db healthy**, correct live
source and **0040**, proxy health **HTTP 200**. Explicit seed and repeat seed use the guarded workflow;
44 version-4 manifest records, no duplicate baseline or overwrite of operator edits.

[UAT Preview](http://localhost:15174/#/taxonomy), **preview / preview** (synthetic UAT only).

| Synthetic identity     | Exact WFO name ID | Coverage                                                     |
| ---------------------- | ----------------- | ------------------------------------------------------------ |
| Ocimum basilicum L.    | wfo-0000253230    | Living; seeds/sowing/plant/group/stored material; count once |
| Ocimum tenuiflorum L.  | wfo-0000253537    | seed-only Current; same genus as basil                       |
| Salvia officinalis L.  | wfo-0000301765    | Current; second genus in Lamiaceae                           |
| Aloe vera (L.) Burm.f. | wfo-0000758976    | Living; Asphodelaceae/Asparagales                            |
| Raphanus sativus L.    | wfo-0000402430    | exhausted-seed Historical; Brassicaceae/Brassicales          |
| Lavandula angustifolia | unlinked          | Current unresolved; never guessed into tree                  |

Operator scenarios: expand higher ranks/family/genus/species; verify basil count once; compare four
scopes; exercise all five categories and multi-category OR; inspect Lamiaceae/Ocimum; follow basil's
related Holy basil/sage and full breadcrumb back to taxonomy; inspect unresolved lavender; review
390×844. Explicit candidate search/inspection is available; confirming/replacing/unlinking is a
separate action. Browser review inspected a real source synonym without modifying fixture links.

## ROADMAP

TAXONOMY-003 is **verified**. TAXONOMY-001, TAXONOMY-002, PHYLOGENY-001, BOTANY-003, BOTANY-004
and ENRICHMENT-002 remain **planned**. No
profile enrichment workaround, automatic refresh, historical synonym management or phylogenetic
product was added. Broader operator visual/product review remains a future checkpoint.
