# TAXONOMY-VISUAL-001 — final UX refinement ready for review

Review: **http://localhost:15278/#/taxonomy?view=tree&taxon=wfo-9000000008&branch=wfo-9000000007**.
[Current gallery: 38 captures](review/taxonomy-visual-001/final-ux/gallery.html) ·
[Measured browser evidence](review/taxonomy-visual-001/final-ux/browser-evidence.json) ·
[Raster dimensions/hashes](review/taxonomy-visual-001/final-ux/image-dimensions.json).
Earlier implementation milestones below are historical; this section is current.

## Implemented refinements

Search, **List / Tree explorer**, and Filters now share the right side of PageHeader.
List is the operator-facing name of Classification. The extra search/view rows and
persistent explanation were removed. Contextual search help retains the distinction
from explicit WFO candidate matching; source status, version and provenance remain.
Mobile has a full-width search row and a compact view/filter row.

The permanent inspector identity list was replaced with four interactive KPIs,
placed above the full source path. Shared OverflowMenu handles viewport positioning,
outside/toggle dismissal, Escape/focus return and switching KPIs. Rows show real
names, common names, covers/fallbacks, representation, credit/licence and canonical
identity links. The bounded scrolling surface reveals **24 identities at a time**
with explicit Show more counts; pagination keeps it open. Empty subsets are inspectable.
Opening a KPI does not change global filters or make a collection API request.

## Exact filter and KPI semantics

| Control                               | Meaning                                                                                                                                                                                                                                                     |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Representation                        | Existing server All/Living/Current/Historical eligibility. Living is a subset of Current; Historical has no Current evidence anywhere.                                                                                                                      |
| Record types                          | Existing server category OR. None selected means unrestricted. Global representation is not recalculated from selected category records.                                                                                                                    |
| Search                                | Existing server taxonomy/collection query, independent of matching and display preferences. Reset filters retains search.                                                                                                                                   |
| Family / Genus / Species              | Source-backed branch focus in both views, retaining ancestry. Choices depend on actual parentage; selecting a parent clears downstream choices. Changes diagram scope, not eligible identity counts. Missing/excluded focus is labelled and can be cleared. |
| Accepted placement                    | Resolved confirmed classification with no linked synonym evidence. Candidates never qualify.                                                                                                                                                                |
| Linked synonym placement              | Resolved classification plus actual synonym evidence; local identity names stay unchanged and accepted placement remains explicit.                                                                                                                          |
| Needs review / unlinked               | No resolved classification. Source absence may invalidate resolution without deleting the saved link. No branch is invented.                                                                                                                                |
| With / Without stored cover thumbnail | Filters eligible identities and reaggregates their node contributions. Remote-only/unavailable references have no stored thumbnail; **Without does not mean no cover relationship**. A general any-cover facet is deferred rather than inferred.            |
| List source ranks                     | Existing compression preference, now in Filters/URL state. Inspector always retains the full path.                                                                                                                                                          |
| Tree depth                            | Stops at an actual source rank; does not change eligibility/counts or invent missing ranks/edges.                                                                                                                                                           |
| Tree thumbnails                       | Image presentation only; does not change identities, taxonomy or inspector imagery.                                                                                                                                                                         |
| Represented branches only             | Fixed collection-pruned API constraint; no worldwide taxonomy browsing is implied.                                                                                                                                                                          |

For the selected taxon's eligible identity IDs, KPI subsets use the authoritative
**global** fields: all rows; `living_records > 0`; `current_records > 0`; and
`current_records == 0`. Counts come from the same subsets, never quantities of seeds,
plants or material. Status/media facets reaggregate this bounded incoming projection;
hierarchy/rank/photo preferences do not recategorize collection records.

Active chips label data facets and view-specific preferences. Shared Reset filters
clears them while retaining query, selected taxon and view. State allowlists `status`,
`media`, `ranks`, `photos`, existing `branch`/`through`, scope/categories/query,
selection/panel and identity return state. Reload and Back/Forward preserve them.
Excluded selection is explained rather than silently replaced.

## Fullscreen, API and component reuse

The graph was not rebuilt. The same TaskDialog remains mounted inline normally and
becomes a full-viewport modal for immersion. Its new optional `modal` switch preserves
all existing callers' defaults. Native focus handling, modal semantics, Escape,
control layering and return focus are reused. DOM identity, camera and expansion
state survive fullscreen transitions; there is one graph instance.

Fullscreen requests the browser API first. The modal opens **after native entry**
so its top layer remains above the fullscreen host. Unavailable/denied API announces
an accessible viewport-dialog fallback. Visible Exit, Escape, external native exit,
exit failure and unmount/navigation cleanup are handled. Native exit failure shows
an explicit browser-exit instruction. No body scroll lock remains. Filters and KPI
popovers use shared nested Escape handling inside fullscreen; browser-owned native
exit events also restore the standard workspace. The inspector is
collapsible; mobile uses one bounded vertical workspace with a pannable canvas and
stacked inspector. No floating inspector obscures nodes.

This phase changes **frontend/UI only**. Existing
`GET /api/v1/explore/taxonomy/tree?include_covers=true` now supplies both views'
KPI/media metadata through the previously tested three-SELECT path and authenticated
thumbnail/cache endpoint. No schema, endpoint, migration, provider or generated
contract changed. No original/remote image is fetched. View/facet/display changes
avoid another projection request; scope/category/query changes still fetch.
The 5,000-eligible-identity boundary and graph's 240 nodes/48 thumbnails remain.
Client facets cannot bypass the API boundary; narrow server eligibility first.

Files: TaxonomyScreen, new TaxonomyFilters/TaxonomyKpis, extracted IdentityList,
pure facets, state/API client, existing TreeExplorer toolbar/photo preference,
refinement CSS and small optional OverflowMenu/TaskDialog extensions/maximize icon.
No dependency, global navigation destination or unrelated modal system was added.
Matching, confirmation/unlink, 409 recovery, exact source hierarchy and attribution
remain the previously approved implementation.

## Verification and measured evidence

- **42 unique frontend cases passed in nine affected files**: Screen, TreeExplorer,
  Kpis, Filters, facets, API, graph, ReferenceInteractions and DirectoryTools.
  Final fullscreen rerun: **2 passed**; the other 16 Screen cases were intentionally
  unselected. Tests exercise relationships and interactions, not snapshots.
- Targeted zero-warning ESLint, changed-file Prettier, strict TypeScript and production
  Vite build passed after final production changes (247 modules). Earlier long combined
  commands were terminated; the separate final build and scoped lint completed.
  Assertions, timeouts and validation were not weakened.
- Backend/API/provider contracts were unchanged in this refinement; previous 49 unit /
  six PostgreSQL cases were not repeated. No unrelated complete suites or canonical FULL.
- Browser: Basil KPI subsets **3/1/2/1**, real identity detail/return, dependent Salvia
  species, accepted+stored-thumbnail facet Back/Forward, unchanged zoomed camera
  through native fullscreen, all six themes at 1440/1024/390×844, bounded mobile popover,
  source absence/restore and no remaining body overflow lock.
- Final ready document is **1440×844 with no document scrolling**, search at **y=72**,
  workspace **y=217–820**. Fullscreen stage is **(0,0), exactly viewport width/height**.
  All 38 captures have no horizontal page overflow. Original full-page JPEG dimensions
  and hashes are recorded; normal mobile documents intentionally exceed 844px in height.

Same owned Review: port 15278, healthy, source available, schema `20261013_0042`.
The synthetic fixture remains **12 identities**, ten placed/two unresolved. Existing
operator confirmations and media relationships were preserved. Source absence showed
zero graph and all 12 local rows in a scrollable list (528px viewport/1002px content),
then was restored. No collection/confirmation/media-record writes occurred.
Credentials remain only in ignored owner-readable `.taxonomy-review/credentials.json`.

## Remaining boundary

The [impact plan](review/taxonomy-visual-001/final-ux/verification-impact.json) selects
**FULL** for `.gitignore` and shared UI primitives. It is a plan, not a gate receipt.
Independent QA and protected delivery are underway; no DEV/UAT/production or foreign
Review action occurred.

Candidate `feat/taxonomy-visual-001` retains approved commit `fee51be` and is reconciled
with latest `origin/main` `3902b92146f3afc21184e658dae64385e33f4926` (Geography PR #122)
by merge commit `ccd8014`. Both progress histories and the Taxonomy, Geography and
general route assertions are retained. The merged `App.test.tsx` suite passed **116/116**.
CI-004 remains a separate delivery; no CI-004 branch or changes were cherry-picked.
The first canonical FULL attempt caught an invalid `list.append()` return-value
assignment in a Taxonomy API test; it is corrected with an explicitly typed fake
search function and no checks were weakened. The exact final tree still needs a
fresh canonical FULL receipt before protected delivery. Feature status stays
**implemented**, not verified, until that receipt passes.
Minimap, worldwide taxonomy, new providers, remote image acquisition, a general
any-cover facet and phylogeny remain deferred.

`TAXONOMY_INDEPENDENT_QA_IN_PROGRESS`

---

# Tree Explorer extension — implementation ready for independent review

Review: **http://localhost:15278/#/taxonomy?view=tree&taxon=wfo-9000000008&branch=wfo-9000000007**.
[Current Tree gallery](review/taxonomy-visual-001/tree/gallery.html) ·
[Browser evidence](review/taxonomy-visual-001/tree/browser-evidence.json) ·
[Performance](review/taxonomy-visual-001/tree/performance.json).
The original Classification handoff follows below as historical evidence.

## Candidate and concurrency boundary

Same `feat/taxonomy-visual-001` worktree, approved feature commit `fee51be`, reconciled
with delivered main by merge commit `ccd8014`. Geography PR #122 is included through
`origin/main`; CI-004 remains separate. App navigation regressions pass **116/116**.
Canonical verification, protected delivery and feature-finish remain pending. No
IA design, DEV, UAT, production or foreign Review was modified.

## Implemented architecture and reuse

- `graph.ts` indexes exact source IDs/parents, derives ancestry, lays out bounded
  visible subtrees and provides pure camera/edge math. Intermediate ranks remain
  real nodes, including subfamily and tribe; names never supply parentage.
- `TreeExplorer.tsx` uses HTML node controls over restrained SVG Bézier edges.
  Source data, expansion, memoized layout, camera and URL selection are separate.
  No graph package or dependency was added. SVG alone would complicate readable
  controls/accessibility; a graph framework adds unnecessary bundle and maintenance.
- `TaxonomyScreen.tsx` retains Classification and the same inspector/matching editor.
  A compact view switch uses `view=tree`; `branch` and `through` preserve diagram
  focus/depth. Existing scope, category OR filters, query, selected taxon, identity
  return state and Back/Forward remain shared. Branch/rank changes do not refetch
  the projection or change eligible identities. Search/scope/category changes do.
- Tree cards select independently from disclosure. Selected ancestry is highlighted.
  Collapsing even a focused branch retains selection and inspector, with Reveal
  selection. Family/genus/species choices use source ancestry. Missing ranks are
  never fabricated or compressed into an invented edge. Rank depth stops at that
  actual rank; if absent it does not invent a cutoff node.
- Mouse drag/trackpad scroll pan; Ctrl/meta+scroll and two-pointer pinch zoom;
  zoom buttons, Fit to view, Reset view and branch focus are explicit. Camera uses
  readable initial magnification for small/long views; Fit deliberately shows the
  whole displayed hierarchy. The diagram's arrows pan, +/− zoom and Home/0 fit.
  Roving node arrows browse real parents/children/visible nodes; Enter/Space select.
  Disclosure remains a separate native button. Pointer capture starts after drag
  threshold and suppresses accidental selection after a drag.
- `tree-explorer.css` uses semantic tokens for all six themes. Desktop has a bounded
  canvas and scrolling right inspector; Hide details returns canvas width. Tablet
  retains this option. Mobile stacks a 26rem canvas and inspector with page vertical
  scrolling; local pan/zoom does not create page horizontal overflow. Existing Inspect
  selection/Back to hierarchy links remain. No floating panel obscures nodes.

## Covers and API contract

The existing authenticated `GET /api/v1/taxonomy/tree` gains optional
`include_covers=false`. Tree mode opts in; Classification keeps the default.
`TaxonomyIdentity.cover` is nullable and includes asset ID, protected thumbnail URL,
credit, licence/link and source URL where recorded. Backend schema/OpenAPI and
frontend generated declarations were updated together. No schema migration,
provider call, source install or taxonomy write was added.

`service.add_covers` performs one metadata SELECT for eligible identities after the
existing projection: **three PostgreSQL SELECTs with covers, two without**. It joins
active media and stored active attachments; remote-only covers have an honest icon
fallback until a local copy exists. Local uploads and saved external copies use the
same existing authenticated thumbnail endpoint/cache key; no original-size image
or remote URL is loaded. Cover metadata does not bypass media access controls.

For each graph node, the first eligible descendant with a stored cover, ordered by
stable identity ID, is representative. Shared taxon nodes are never duplicated for
cultivars. Tooltip/alt explicitly label the photograph as a descendant representative,
not an official genus/family image. The inspector lists individual identities and
covers with credit/licence/media links. Missing/failed images use the shared icon.
Identity counts never substitute physical plant/seed quantities.

## Bounds and measurement

Default expansion is only three source levels plus selected ancestry. At most
**240 nodes** enter layout; viewport overscan culls node DOM, images are capped at
**48 graph thumbnails** at useful zoom. Inspector identities reveal 24 at a time;
additional covers load only when explicitly revealed. Identical thumbnail URLs reuse
browser caching. The existing backend **5,000 eligible identity** boundary remains.
A capped diagram explains the limit and offers collapse/focus rather than loading
worldwide taxonomy. No render-triggered provider/network traversal is added.

`graph.fixture.ts` builds **5,000 identities / 5,183 source nodes** deterministically.
Fifteen indexing+bounded-layout iterations measured **14.2 ms median /
37.5 ms p95**, against a 100 ms target on this host (Node 24/Vitest).
This is CPU transformation/layout evidence, not GPU frame timing or physical-device
certification. Component tests verify camera changes do not recalculate layout and
thumbnail URLs remain protected/stable; DOM/image bounds and pointer/keyboard math
are exercised. Very large overviews intentionally require focus or progressive
expansion for readable text. Optional minimap and deeper rendering optimization
remain deferred until actual collection use demonstrates their value.

## Source, Review and fallback

The ownership-checked project remains `florabase-taxonomy-review-02b45056`, loopback
port 15278, schema `20261013_0042`; credentials remain only in ignored owner-readable
`.taxonomy-review/credentials.json`. Original eight identities and operator-confirmed
links were preserved. `enhance.py` added four explicitly synthetic identities,
including two unresolved identities, instead of undoing operator confirmations.
Current totals are **12 represented / 10 placed / 2 unresolved; Living 5, Current 9,
Historical 3**. Three Basil identities share one species; three cover references
share two credited small local assets. [Photo sources](review/taxonomy-visual-001/media/README.md).
All source IDs/version/citation remain explicitly synthetic.

The actual Review source was disabled and re-enabled through its guarded helper.
Unavailable-source Tree mode draws no invented nodes, explains absence and retains
all local identities, saved link evidence and the canonical review workflow.
Retry source restored the graph. No WFO download/install was required. Existing
explicit matching/confirmation/unlink and 409 authoritative refresh remain covered
by the original tests and the current Taxonomy screen suite. We did not replay
write-based conflict scenarios against newly operator-confirmed links.

## Focused verification and evidence

| Check                                                           | Extension result                                                                                                                                                                                                                |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TaxonomyScreen, TreeExplorer, graph and performance             | **28 passed**, four focused files                                                                                                                                                                                               |
| Taxonomy offline service/API/provider suites                    | **49 passed**, existing Starlette warning                                                                                                                                                                                       |
| Isolated PostgreSQL Taxonomy suite                              | **6 passed**, owned disposable cleanup confirmed                                                                                                                                                                                |
| Frontend TypeScript, full zero-warning ESLint, production build | Passed after final production changes                                                                                                                                                                                           |
| Backend Taxonomy strict mypy, changed Ruff, helper Ruff         | Passed                                                                                                                                                                                                                          |
| OpenAPI export and generated TypeScript drift                   | Passed                                                                                                                                                                                                                          |
| Feature graph / whitespace                                      | 113 valid features / passed                                                                                                                                                                                                     |
| Browser                                                         | Selection, independent disclosure, focused collapse/reveal, progressive expansion, actual mouse pan, zoom, mobile keyboard pan, historical filter, rank-depth distinction, identity return, Back/Forward, source absent/restore |
| Responsive / themes                                             | All six themes at 1440×844, 1024×844, 390×844; no horizontal page overflow; gallery includes all ten requested scenarios                                                                                                        |

The final browser capture is `36-final-graph-inspector-dark-1440.jpg`.
Capture manifest records actual document geometry; a scrollbar can reduce client
width by 15px. JPEG raster files are preserved directly from the browser.
Physical touch, assistive technology and prolonged real collection usage remain
independent QA. Pinch/drag/wheel are additionally exercised in component tests.

The [candidate-base impact plan](review/taxonomy-visual-001/tree/verification-impact-candidate-base.json)
selects **FULL** because `.gitignore` is a high-risk path. The
[latest-main comparison](review/taxonomy-visual-001/tree/verification-impact.json)
also selects FULL and includes Geography/shared-shell differences because this
candidate has not incorporated PR #122. These are plans only: **canonical FULL was
not run**, as explicitly requested. Luna must reconcile current main, review the
final tree and execute final canonical/required checks after operator acceptance.
Previously recorded unrelated App/SeedLot suites were not repeated.

Deferred: optional minimap, Saved Views for taxonomy, worldwide browsing, taxonomic
relationship editing, new providers, remote image acquisition, phylogeny/distance,
new backend grouping or collection semantics. No such feature is implied by this
classification graph.

`TAXONOMY_TREE_EXPLORER_IMPLEMENTATION_READY_FOR_REVIEW`

---

# TAXONOMY-VISUAL-001 — implementation handoff

Implementation is ready for operator review and independent QA. Changes are
**unstaged and uncommitted**. Canonical FULL verification, delivery and protected
environment upgrades have not run.

## Inspect the candidate

- **Review:** http://localhost:15278/#/taxonomy?taxon=wfo-9000000008
- **Credentials:** the ignored, owner-readable
  `/home/alessandro/.codex/worktrees/taxonomy-visual-001/florabase/.taxonomy-review/credentials.json`.
  Account display: **Taxonomy Review (synthetic)**. No password is published here.
- **Gallery:** [32 actual browser captures](review/taxonomy-visual-001/gallery.html).
- **Scenario guide:** [Review tools and reproduction](review/taxonomy-visual-001/README.md).
- **Evidence:** [capture dimensions](review/taxonomy-visual-001/capture-manifest.json),
  [responsive measurements](review/taxonomy-visual-001/browser-evidence.json),
  [live browser checks](review/taxonomy-visual-001/browser-interactions.json).

This Review has its own project `florabase-taxonomy-review-02b45056`, network,
PostgreSQL, media and frontend dependencies. Frontend and backend both bind this
candidate. Only the frontend is published, on loopback. Its database remains at
`20261013_0042`; this feature adds no migration. Restarting the owned application
retained the fixture and existing sessions. Other Review, DEV, UAT and production
environments were not modified.

The tiny source is **illustrative synthetic data, not an authoritative WFO
installation**. The visible version and citation state that fact. Fixture IDs are
confined to the explicit Review tools and fixture. Production startup does not
import them; no WFO archive was downloaded and no provider integration was added.

## Delivered behavior and reuse

| Surface             | Implemented behavior                                                                                                                     | Existing mechanism reused                                                                             |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Header and controls | Explore / Taxonomy, compact heading, collection search, source status, Filters drawer and removable active filters                       | PageHeader, Breadcrumbs, DirectoryTools, DirectorySearch, shared actions/icons and semantic tokens    |
| Classification      | Separate disclosure and selection; selected accent; bounded hierarchy; expand/collapse; optional intermediate ranks                      | Existing collection-pruned tree response and hierarchy projection                                     |
| Inspector           | Name, authorship, rank, source ID/version, full classification path, distinct counts, represented genera and exact identity links        | Existing tree taxon/count/identity fields; no new endpoint                                            |
| Needs review        | Unlinked or stale identities inside the workspace; authoritative selected-identity read; retained record count; explicit source matching | Existing identity GET and canonical IdentityTaxonomyPanel                                             |
| Confirmation        | Literal source-prefix search, candidate inspection, explicit confirm/replace/unlink; local names unchanged                               | Existing candidates, taxonomy GET, PUT/DELETE link APIs and owner/Origin/CSRF/version/checksum guards |
| Source absence      | Local identities stay accessible; saved confirmation evidence can be inspected; matching pauses; Retry only rechecks configuration       | Existing source_available/message and selected identity taxonomy evidence                             |
| Navigation          | Source breadcrumbs, exact identity routes, narrow canonical taxonomy_return context; tabs and contextual editing retain return context   | Existing hash router, identity hub and EditWorkspace safeguards                                       |

No second write implementation, new provider, shared token change, global sidebar
change, database migration, pagination mechanism or Saved Views contract was added.

The collection filters retain All represented, Living, Current and Historical.
Record categories retain Seeds, Sowings, Plants, Plant groups and Stored material.
Selected categories use OR; none means unrestricted. Living is included in Current;
Historical requires no Current evidence anywhere for that identity. Counts describe
eligible distinct Botanical Identities, not physical quantities. Living + Seeds is
empty. Search remains collection search, separate from explicitly submitted source
candidate search. Filters, search, selected taxon and review identity survive the
supported URL/back/forward/reload paths.

## Confirmed corrections

1. **Prefix normalization:** Pydantic strips surrounding whitespace before the
   meaningful 2–200-character validation. Empty, whitespace-only and padded
   one-character values are rejected; padded valid and 200-character prefixes are
   accepted; 201-character normalized prefixes are rejected. Source search retains
   literal-prefix semantics and its maximum of 25 candidates. The client also
   rejects a whitespace-only prefix before requesting candidates.
2. **Concurrent identity edits:** 409 blocks another confirmation. Refresh reads
   the actual Botanical Identity, displays its updated fields, clears submitted
   search/results/inspection, reloads source/link evidence and requires a new
   explicit search, inspection and confirmation. It never automatically resubmits.
3. **Source recheck coherence:** changing source availability/version/checksum
   invalidates the selected editor's old source state and candidate review. Retry
   can restore matching in the open inspector. Successful confirmation refreshes
   counts/queue while retaining the inspected identity and success message.
4. **Responsive/interaction defects found in review:** scoped rules prevent the
   shared button hover fill from obscuring selected text, remove the tablet
   heading's unwanted vertical gap and prevent the phone source-status overflow.
   Mobile search and labelled Filters share one row. All six themes use the
   delivered semantic palette and focus controls.

## Populated scenarios and visual evidence

The baseline fixture has eight represented identities: six placed, two unresolved,
five Living, seven Current, one Historical and three placed families. It includes
kingdom, phylum, class, orders, families, subfamily, tribes, genera and species.
Rosemary retains its local Rosmarinus name while its confirmed source synonym is
associated with accepted Salvia rosmarinus. Lavender is unlinked; Thyme is stale.

- **Available:** 18 captures cover Botanical, Herbarium and Mineral, each in
  Light/Dark at exact CSS viewports 1440×844, 1024×844 and 390×844. The measured
  document width does not exceed the viewport. Tree and inspector remain adjacent
  at desktop/tablet widths and stack on the phone. Full paths remain available
  when intermediate tree ranks are compressed.
- **Absent:** six further Light/Dark captures at the three widths show all eight
  local identities and Rosemary's saved synonym evidence. No classification is
  invented, and source candidate search is unavailable. Retry restores the selected
  editor after the fixture source is re-enabled.
- **Matching/conflict:** actual browser captures show candidate evidence, blocked
  confirmation after a real stale-write 409, refreshed identity with candidates
  cleared, and successful renewed explicit confirmation. Canonical unlink was then
  exercised to restore two unresolved links. Lavender's common name retains the
  deliberately visible synthetic concurrent-edit label; its scientific name and
  cultivar were not changed by linking. Repeat seeding preserves this edit.
- Additional captures show synonym placement, the selected inspector, mobile
  inspector jump and phone Filters drawer. Browser checks cover empty Living +
  Seeds, reload, Back/Forward, exact identity return navigation, Escape/focus return
  and focus-moving inspector/hierarchy jumps.

The 32 files retain the browser's original JPEG bytes. The tool exports smaller
rasters than the requested CSS viewport; the manifest records both dimensions.
They were not resized or re-encoded. Some paths/evidence exceed one viewport;
the document can scroll and the hierarchy has its own bounded scroll area, as in
the approved design. Native nested lists/buttons retain Tab and Enter/Space
operation; this is not an ARIA tree with an invented arrow-key model.

## Focused verification

| Check                                                                                  | Result                                                                                                                                                   |
| -------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Offline backend: test_taxonomy.py, test_taxonomy_api.py, test_taxonomy_service.py      | **48 passed**; one existing Starlette TestClient deprecation warning                                                                                     |
| PostgreSQL: `./scripts/test-integration.sh backend/tests/integration/test_taxonomy.py` | **5 passed**; disposable stack cleanup verified, no residual owned resources                                                                             |
| Affected frontend: App, lazy navigation, transitions, SeedLotScreen and Taxonomy       | **177 passed** in five files                                                                                                                             |
| Final Taxonomy rerun after source-retry correction                                     | **15 passed**, including the additional regression; **178 unique affected cases overall**                                                                |
| TypeScript, complete frontend zero-warning ESLint, changed-file Prettier               | Passed; final Taxonomy lint rerun passed                                                                                                                 |
| Backend Ruff check/format and strict Taxonomy mypy                                     | Passed; seven Taxonomy source modules typed                                                                                                              |
| Backend OpenAPI export `--check` and openapi-typescript `--check`                      | Passed; generated contracts unchanged                                                                                                                    |
| Review helper Ruff and source/ownership self-check                                     | Passed; synonym, unplaced name and five foreign-runtime guards                                                                                           |
| Live authenticated HTTP scenarios                                                      | Passed: source ready/absent, saved synonym evidence, blank prefix 422, stale identity 409, authoritative GET, renewed search, confirm and guarded unlink |
| Production frontend/backend Docker builds                                              | Passed in independently owned disposable image builds; cleanup verified                                                                                  |
| Final frontend production build after the last source correction                       | Passed                                                                                                                                                   |
| Feature graph and whitespace                                                           | 113 valid features; `git diff --check` passed                                                                                                            |

The initial affected run exposed an obsolete eyebrow assertion and timing failures
under concurrent load; the corrected affected run passed. The test now checks the
approved Taxonomy breadcrumb and still checks the other workspace headings. No
timeouts, validation, permissions or error handling were weakened.

## Integration dependencies and remaining acceptance

Latest explicitly fetched `origin/main` remains
`5778da7be03bc6030cb0ab3af03b9631bf4fa209` (identity hub, PR #121).
This candidate started there and contains no unmerged Geography work.
Dependencies are TAXONOMY-003, THEMES-001, CONTROLS-001 and
BOTANICAL-IDENTITIES-VISUAL-001. Their delivered APIs/primitives are used as present
on that baseline; existing feature statuses were preserved. TAXONOMY-VISUAL-001 is
**implemented**, not verified.

The independently owned local Geography branch was inspected by Git reference
only: `feat/geography-visual-001` at
`e501d7c2f068451e11808731e1bb87aa05e03a23`, not an ancestor of fetched main. It is
not required for this feature. Its shared Breadcrumbs/PageHeader changes will need
normal combined QA when delivered. Taxonomy's explicit breadcrumb and empty eyebrow
avoid the Geography helper's automatic group breadcrumb path. Both branches edit
App.test.tsx, docs/features.json and docs/progress.md, so integrate those additions
carefully and rerun relevant combined navigation checks. No Geography checkout or
environment was changed, and no claim is made about its independent QA/delivery.

Operator visual acceptance and independent QA remain pending. Real assistive
technology, physical touch, browser zoom/forced colors, full-dataset latency and
large-source runtime performance have not been established by viewport emulation
or the tiny fixture. Existing bounded collection and 25-candidate limits remain.
The browser connection interruption was resolved and actual captures were completed.

Canonical FULL verification, staging, commits, push, PR, delivery, primary main
changes and protected upgrades were deliberately not performed. Accepted-name
reconciliation remains TAXONOMY-001, synonym/name-history management TAXONOMY-002,
and phylogeny/MRCA/genetic distances/divergence concepts remain deferred.

TAXONOMY_VISUAL_IMPLEMENTATION_READY_FOR_REVIEW
