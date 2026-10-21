# MAPS-FOUNDATION-001 — Native ranges spatial review

**Operator visual/product review accepted; independently reviewed and canonically verified.** Updated 2026-10-21.

- Same candidate: `/home/alessandro/.codex/worktrees/c606/florabase`, `feat/maps-foundation-001`.
- HEAD and cached `origin/main`: `9a73d3f0434a3f8399de8746b010a5d8503937a4`; zero ahead/behind.
  No branch change, reset, merge or modification of primary main in this pass.
- All candidate changes remain **unstaged and uncommitted**. Backlog status is `verified` after the successful final-tree canonical gate.
- Review: <http://localhost:15174/#/native-ranges>, owner login `owner`. The existing Review-only
  credential is unchanged and supplied privately in chat; no plaintext password is stored here.
- Maps-owned `florabase-feature-review` retains the v4/80 synthetic fixture, owner and saved preset,
  database/media/dependencies, and revision `20261013_0042`. Supported startup resumes stopped services;
  no replacement, reset, reseed, removal or protected-environment operation was performed.
- The authenticated operator review is accepted. No material blocker or production correction was found.
  The Review remains running for inspection and the operator may use the same credential in another
  browser; credentials are not recorded in this document.
- [Current spatial evidence](review/maps-foundation-001/spatial/README.md) supersedes the layout in
  [the previous refinement](review/maps-foundation-001/refinement/README.md). Older evidence is retained.

## ARCHITECTURE AUDIT

The existing audit and local Natural Earth renderer remain the basis. This is the operator's next
product pass, not another architecture project. The delivered Seeds, Sowings and Plants toolbar
composition was inspected; Native ranges uses the same PageHeader/DirectoryTools search slot without
changing shared/global component behavior.

One concrete contract gap required a small authenticated **read-only API addition**: overview exposes
territory counts without unbounded contributor IDs, so it cannot correctly enumerate the Explore all
inspector from client data. A paged territory-identity projection now reuses the same canonical
coverage ancestry, representation scopes and filters. No schema migration, provider, dependency,
geometry asset or new geographic assertion was introduced. Both generated API artifacts are updated.

## DOMAIN BOUNDARIES

Ranges come only from explicit structured profile/place links. GBIF, taxonomy, scientific-name
similarity, Supplier, present Location, provenance and specimen quantities contribute none.

Each Botanical Identity counts once per territory. An explicit country record is distinguished from
map coverage derived from a broad recorded region. Both can coexist: the live Brazil inspector shows
one Basil identity with an explicit Brazil record and broad South America evidence. Custom places
never borrow a parent polygon. Unsupported boundaries remain valid textual evidence. Zero coverage
and unshaded land do not establish absence.

## CURRENT MAP RENDERERS

Native ranges retains lazy local Natural Earth SVG, fixed generalized extent and no tile requests.
Species distribution retains explicit-load Leaflet/GBIF evidence. Collection origins retains recorded
coordinate/provenance semantics. Neither other Maps phase is implemented by this pass.

## DESIGN DIRECTION

Header left: Explore eyebrow, title, short subtitle. Right: wide botanical search, Filters, Saved views,
Choose species. Scientific/common/cultivar search uses the existing durable query and never deletes
chosen IDs. Active chips expose removable restrictions. Modes now read **Explore all** and
**Compare species (N)**, with explicit independent species selection.

At wide desktop the map/inspector split is approximately 70/30. The map keeps its 2:1 geographic
aspect ratio; no stretch, new precision or oversized empty canvas. The permanent inspector is bounded
and scrollable. The comparison legend follows the canvas so five names never postpone the mobile map.
At ≤64rem named Map/Inspector controls switch mounted panes; state survives the switch.

| Overview KPI | Destination |
| --- | --- |
| Represented identities | Paged chooser, current scope; no implicit selection |
| With recorded range | Existing durable with-range filter plus chooser |
| Without structured range | Informational; no unsupported inverse-filter action |
| Mapped territories | Focuses the textual territory inspector |
| Exact recorded places | Opens paged evidence in the Data and limitations dialog |

Territory coverage lives in the inspector; species names/removal live directly in the legend.
About this map and per-identity Places actions expose evidence and limitations. Duplicate bottom
coverage/selection accordions have been removed. Evidence pagination retains the map and selection.

## SHARED MAP FOUNDATION

Proven shared components remain the small MapWorkspace shell, optional browser slot and MapLegend,
plus existing PageHeader, DirectoryTools, BotanicalName, TaskDialog and Saved Views integration.

This pass proves a Native-specific spatial inspector, independent territory multi-selection,
labelled identity colors, stripe overlap, mobile mounted panels and exact/broad evidence presentation.
These are **not yet generic multi-map domain abstractions**. Native range counts and ancestor drawing
rules must not be reused as occurrence-density or material-origin rules.

## SPECIES DISTRIBUTION PLAN

Potential reuse: header composition, secondary chooser, responsive canvas/inspector structure,
focus restoration and a compact evidence dialog. Preserve explicit Load, restored-but-unloaded state,
provider links, quality policy and density meaning. A Leaflet inspector, resize and hover implementation
needs independent proof; Native SVG patterns do not establish a density-layer design.

## NATIVE RANGES PLAN

Operator acceptance of the spatial model comes next. No pan/zoom, higher-resolution geometry,
provider enrichment or geographic inference was added. Large counts continue to use overview bins;
color-coded comparison is deliberately bounded to five.

## COLLECTION ORIGINS PLAN

Potential reuse: header/panel composition, selected-place chips and restrained contextual evidence.
Keep recorded coordinate precision, missing coordinates, explicit material links and basemap privacy
separate. Native country stripes, canonical range ancestry and distinct-species counting do not prove
origin-marker semantics or a shared provider adapter.

## FIRST IMPLEMENTED SLICE

Five-layer comparison uses green `#287c67`, rust `#aa562d`, blue `#5467b2`, mauve `#9a477a`, ochre
`#81701f`. Surviving IDs retain colors during active comparison; removed slots may be reused. Reload
may allocate again. One contributor uses a solid color; 2–5 use equal-width diagonal SVG stripes
containing every contributing ID's color. Borders and inward-clipped selection/hover/focus remain
in independent inert layers above fills. Tiny countries may not show every stripe at world scale;
labels and the exact contributor inspector are the authoritative readable equivalent.

New chooser choices stop at five, including a guard and a disabled sixth checkbox. Existing URL/Saved
View selections of 6–20 remain intact, visible and removable in count-based compatibility mode.
The 20-ID API/v1 state contract is unchanged; invalid larger selections are rejected as a whole.

Click/Enter/Space toggles territories without Ctrl/Shift. Chips remove one; Clear territories removes
all and restores polygon focus. Hover/focus previews never commit a choice. Territory selection does
not mutate species. Chosen territory codes survive species/mode/filter changes, with neutral zero
coverage when needed. Reload, Back/Forward and Saved View navigation clear this transient state;
no new serialized fields. Union/intersection and panel choice are also transient.

The inspector defaults to a **distinct union**, with explicit Any/All intersection. Explore all reads
the full filtered representation scope, regardless of compared IDs. Compare adds only the chosen ID
bound. Results show scientific/common names, representation, matched territories, exact versus broad
records, identity links and Places actions. Search is explicitly labelled as filtering the current
50-row page. Two reads return total/page, plus one evidence read for a nonempty page; no per-row reads.

## ACCESSIBILITY

Named mode/panel controls, labelled scientific/common/cultivar and inspector searches, native checkbox
limit/deselection, focus-visible controls and a one-tab-stop SVG are retained. Arrows/Home/End navigate;
Enter/Space toggle; Escape dismisses previews. Textual territory buttons provide the same action,
including unavailable boundaries. Selected territories have a polite announcement outside mobile
hidden panes, pressed state, strong outlines and removable labelled chips. Colors have names/counts
and contributor-list equivalents; stripes have an explicit explanation.

Dialogs preserve focus containment and Done/Escape restoration. Chooser fallback targets the stable
header trigger if the original KPI disappears. Panel controls retain focus while switching mounted
content. Screen-reader-compatible markup and browser accessibility-tree/keyboard behavior were
inspected; **no actual screen reader was used**. Physical touch and true zoom remain operator checks.

## PRIVACY

No remote tiles, occurrences, geocoding, geolocation or new hidden network dependency. Attribution
is an outbound Natural Earth link. Credentials stay outside repository documentation. The Review
fixture and owner were preserved; UAT, DEV, Stable Preview and production were untouched.

## PERFORMANCE

Overview and identity pages retain existing query bounds. Inspector accepts 1–250 uppercase territory
codes, any/all matching, optional ≤20 UUIDs, existing filters, 0–100000 offset and ≤100 limit (UI 50).
Canonical ancestry is reused; geometry stays out of PostgreSQL. Integration tests assert three reads
for a populated inspector page, exact/broad deduplication, paging, scope/category/query/selected-ID
isolation and reference/custom exclusion.

Strict production build passes. Native JS approximately **38.38 kB / 10.86 kB gzip**, CSS **15.21 kB /
2.78 kB gzip**; lazy geometry remains **150.83 / 60.46 kB gzip**. No dependency or asset change.

## RESPONSIVE EVIDENCE

Authenticated 1440×844, 1024×844 and 390×844 inspections show useful first-viewport maps, wrapped
long names, a readable five-species legend, panel switching, retained selection and no horizontal
overflow. At desktop the map and inspector are visible together. At smaller widths the explicit
switch gives direct access to the inspector without scrolling past five legend entries.

The preserved live fixture has six represented identities, four with ranges and two without, and
at most two contributors per territory. Authenticated evidence covers five chosen identities and
real two-way overlap. Labelled renderer-only fixtures separately show **1, 2, 3 and 5 contributors in
the same Brazil polygon**, generated from the actual component without editing Review data. These
must not be described as authenticated five-way botanical evidence. See the evidence README for
measurements, captures and limitations. Viewport overrides are not browser zoom; 125/150% true zoom
and physical-device checks remain operator acceptance items.

## TESTS

- Baseline before this pass: **30 tests / 4 files**.
- Final Native ranges/maps: **39 tests / 4 files**.
- Related Saved Views, occurrence/distribution/origin isolation and directory components:
  **101 tests / 11 files**. Total affected frontend coverage: **140 tests / 15 files**.
- Backend Native ranges unit tests: **6 passed**; isolated PostgreSQL Native ranges integration:
  **10 passed**, including authenticated API bounds and no provider calls.
- Scoped zero-warning ESLint, Prettier check, strict TypeScript/Vite production build, backend Ruff
  lint/format, strict mypy, OpenAPI/TypeScript drift check pass.
- Feature graph and final whitespace/index/source checks are recorded in the evidence handoff.

Coverage includes search, modes, five/sixth handling, color stability, 1/2/3/5 stripe membership,
territory multi-toggle/remove/clear, distinct union/intersection, broad/exact/custom boundaries,
inspector retry/authentication, keyboard/focus, retained zero coverage, mounted panel state, exact
place pagination, legacy Saved Views and actual Back/Forward. No tests or guards were weakened.
An earlier combined host run stopped with exit 143 before a result; completed scoped container runs
above supersede it. Intermediate assertions were adapted to the new dialog/inspector interactions.
No canonical `make feature-verify`, full repository gate, delivery or production certification claimed.

## CONFLICT / INTEGRATION RISKS

The candidate includes earlier unstaged Maps work plus this pass's narrow read API, generated artifacts,
UI/tests/docs. Main alignment remains cached at PR #113 `9a73d3f`; this pass did not reconcile a newer
remote. Before a later authorized delivery, inspect then-current main and run the required gate on the
final tree. No staging, commit, push, PR, finish or DEV upgrade was performed.

## ACCEPTANCE AND REMAINING OPERATOR CHECKS

Operator accepted the palette, map-first hierarchy, search scope, inspector density, five-layer cap,
selected-state behavior and mobile map/list panels against the live authenticated fixture and synthetic
geometry evidence. The remaining device checks are true browser zoom at 125%/150%, an actual screen
reader session and physical touch-target inspection. Existing viewport captures are not presented as
true zoom or device evidence. These are recorded as follow-up acceptance checks, not claims already
performed. No actual screen reader was used.

## DELIVERY AND NEXT MAPS SLICES

The final canonical `make feature-verify` passed on the accepted candidate: **943 backend unit tests,
797 frontend tests across 70 files, and 736 PostgreSQL integration tests**. Workflow guards, format,
lint, strict typing, generated API drift, production backend/frontend builds, migration full-cycle,
feature graph and whitespace checks passed. The migration cycle verified revision `20261013_0042` in
all four states; no schema migration is part of this feature. A final verification will follow the
handoff/backlog result update before staging. This feature proves the first Native ranges slice only.
Species distribution and Collection origins remain planned and must be implemented as separate
increments under their explicit-load and recorded-coordinate/privacy contracts. Larger Saved Views
remain intact; unshaded land, broad drawing coverage and tiny stripe fragments are not evidence of
absence or precise country assertions. No live fixture rows were edited; three- and five-contributor
examples remain labelled renderer-only geometry fixtures.
