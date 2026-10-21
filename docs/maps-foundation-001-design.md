# MAPS-FOUNDATION-001 — cartographic foundation

Design recorded before implementation, 2026-10-18. Base: `a36c6cffb938c5ed20f93942e1eac1070897962c`.
Scope: audit all three Maps workspaces; implement Native ranges only; plan reuse after operator review.
The initial rail/pane layout below is historical; the operator refinement at the end supersedes that presentation.
This is a presentation increment, with no domain/API/schema/geometry/dependency changes.

## Current-state audit

Inspected UI contract, product roadmap, domain model, Species distribution, Native ranges,
EXPLORE-002 handoff, geography contract and all five requested frontend capability directories.
The roadmap's frozen navigation and domain distinctions remain binding. Historical handoff
performance/UAT results describe their original candidate, not this change.

| Dimension | Species distribution | Native ranges | Collection origins |
| --- | --- | --- | --- |
| Renderer | Leaflet 1.9.4; GBIF hex-density raster over configured basemap | Bundled SVG, 720×360 equirectangular, 179 Natural Earth paths | Leaflet 1.9.4; one marker per coordinate-bearing ProvenanceSite; optional accuracy circle |
| Data | Authenticated local represented-identity directory; explicit exact GBIF link; summary/tile proxy after Load | Existing authenticated overview, selection and exact-place projections; local lazy geometry | Existing authenticated site/linked-record projection; client-side filters |
| Precision | Quality-filtered observation records; bin counts unavailable; coordinates may be uncertain/generalized | Exact stored GeographicPlace; ISO drawing units, M49 descendant drawing union; custom/CLDR-only and missing small units explicitly unmapped | Explicit WGS84 pair and optional recorded accuracy; never a named-place centroid |
| Viewport | Starts at [20,0], zoom 2; zoom 1–16; recreated for identity | Fixed world extent; no pan/zoom or polygon selection | Fits visible sites, selects at zoom ≥10 with flyTo, single site at zoom 10 |
| State | q/scope/one identity in URL and v1 Saved View; Load/viewport/errors/page transient | q/scope/mode/≤20 identities/record OR-set/withRange in URL and v1 Saved View; page/geometry transient | q/seed_lots/plants in URL and Saved View; selected site and viewport transient |
| Filters | Local debounced search and representation scope | Same representation, literal search, categories, with-range; selection persists through exclusions | Record type and identity text; linked records/counts recomputed from visible matches |
| Accessibility | Named map region; textual counts/quality; real Load/Retry controls | Named static image, exact lists/counts; checked species and pressed mode | Keyboard markers and site buttons; linked-record detail; visible-area privacy note |
| Failures | Missing link, unsupported provider, no eligible records, summary failure, tile failure distinct | Identity/overview/comparison and asset retry; missing/excluded IDs; no ranges; partial/unavailable drawing | API retry; no sites, no coordinates, no filter matches; no dedicated tile-error handling |
| Cost | Local bounded pages; lazy Leaflet/tile renderer after Load; external per-viewport tiles | 50-row pages; ≤250 coverage units; ≤20 comparison IDs; 150 kB geometry lazy chunk | Full site projection and marker rebuild on visible-site changes; no new clustering in this slice |

Current weaknesses: filters and caveats occupy the first viewport; Native ranges gives the browser
roughly a third of the canvas and puts the entire comparison selection before the map. Its continuous
green ramp has only endpoint text, single-species view lacks a selectable territory equivalent, and
map/list cannot cross-highlight. Collection origins already synchronizes marker/list selection but
inherits administrative card layout. Species distribution puts readiness and list material before
the visualization. These require different evidence inspectors, not a common data model.

## Three evidence contracts

1. **Observed occurrences:** MAP-002's exact provider identifier and fixed quality policy only.
   Density is recording effort, not abundance or native/endemic status. No eligible observations
   never proves absence. Opening/selecting/searching/restoring a view must not trigger Load.
2. **Recorded native ranges:** existing profile-owned exact links only. A territory count is distinct
   BotanicalIdentity coverage, unioned within identity by the existing API. Broad drawing descendants
   are not stored assertions. Exact broad + precise + custom relationships remain separately readable.
3. **Recorded material origins:** explicit sites and direct collection links only. Supplier, storage
   Location, names, ancestry and occurrence density cannot manufacture coordinates or origin links.

## Engine assessment

Retain both engines. The existing SVG is sufficient for the bounded territory comparison and local
availability requirement. Leaflet already handles raster zoom/tile attribution and precise site
selection. No requirement here demonstrates a benefit from MapLibre's additional renderer, style
pipeline, migration and accessibility burden. Do not add a dependency for visual consistency.
This decision evaluates the checked-in implementations, not a claim about latest library versions.
World overview retains its generalized equirectangular boundaries: no area-normalized comparison,
precise local inspection or small-island completeness is implied. Zoom/higher resolution is a later
specific requirement, not part of this proof.

## Interaction and layout specification

- Keep the existing PageHeader. Use its tools slot for compact Saved Views; put search, scope and
  an inline Filters disclosure in a compact wrapping toolbar. Show active dimensions in its summary.
  Secondary scope/category definitions live inside it; essential evidence meaning remains visible.
- A small map-specific `MapWorkspace` composes a primary map/evidence area and a species browser.
  Wide layout gives the map flexible remaining width and browser about 18rem. Main map comes first
  in reading order. No global directory, navigation or PageHeader modifications.
- At ≤64rem, an explicit Map & evidence / Species list switch shows one pane at a time. Both remain
  mounted so switching alone never refetches or resets selection. The persistent switch retains
  keyboard focus; selecting species keeps the browser available for multiple selection. The operator
  switches back to inspect. The switch is presentation-only, outside URL/Saved Views.
- Comparison map precedes the selected-species list; exclude/remove/view-only remain explicit.
  Single species preserves its identity/edit links and exact-place list. Overview retains its three
  compact summary counts. Long results use document flow, not a trapped scrolling rail.
- Territory inspection is distinct from species selection. Click a covered polygon or a native HTML
  territory button to set the same inspection state; show name, exact count and available comparison
  contributors. Clear inspection never clears species. A dark outline and pressed/text state identify
  selection independently of color. No centroid labels or new geographic facts.
- Keyboard: one SVG territory tab stop, arrows/Home/End move through covered units, Enter/Space
  inspect; full HTML territory buttons provide an ordinary keyboard/touch equivalent. Polygon titles
  provide hover labels. Uncovered background is noninteractive; no implied absence.

## Visual encoding and shared foundation

Use UI Foundation typography/spacing/surfaces; scientific-name spans italicize scientific names only,
leaving cultivar names roman. Border-led layout, quiet water/background, neutral unmapped land.
Map-specific semantic aliases are scoped to `.maps-workspace`/`.native-ranges`, never global tokens.
Count bins use a small discrete botanical sequential palette derived from existing primary/surface
tokens. Legend and fills use the same scale function, with numeric inclusive bin labels; no imaginary
1–1 gradient. Single species is binary recorded coverage, comparison/overview count identities.
No coverage uses a separate neutral swatch with an explicit absence caveat.

Share only a presentation shell and legend structure now, used across Native ranges modes. Keep
scale computation, geometry lookup, contributor semantics and territory inspector in Native ranges.
Do not create common provider adapters, generic selection stores or a new map framework. Future
screens can reuse shell/legend positioning without inheriting this choropleth's scale or semantics.

## Accessibility, privacy and performance

Native HTML controls, visible focus, ≥44px list/control targets, meaningful SVG group/description and
keyboard instructions. Exact paths, broad/partial/custom qualifiers, unavailable boundaries and count
lists remain available without interpreting color or using the map. Errors and loading retain retry
and existing authentication boundaries. Avoid live announcements on hover; announce committed
inspection. No new motion. Touch does not require hover. Actual screen-reader/zoom review remains
operator work if no isolated browser review slot is available.

Native ranges makes same-origin authenticated reads and a bundled geometry import only. Attribution
is an outbound link, not a fetch. Species distribution must retain explicit Load before both density
and basemap mount. Collection origins keeps its direct basemap disclosure: provider receives IP and
visible tile area, not Florabase record names/metadata. No geolocation/geocoding/prefetch added.

Reuse cancellation/debounce and API bounds. Keep geometry separate and lazy. No additional request
for inspection/switching. No client recreation of server coverage aggregation. Build chunk sizes and
test results will be recorded for this candidate; no device-performance claim from historical data.

## Bounded implementation order and reuse plan

1. **This slice:** compact Native ranges controls, map-first shell, explicit mobile pane switch,
   precise shared legend, territory/list inspection, map-first comparison, tests and evidence.
2. **After operator acceptance:** Species distribution adopts the shell and compact searchable
   single-choice browser. Inspector places local readiness/GBIF link/explicit Load next to the canvas;
   loaded summary, quality and source details become contextual. Retain unloaded restoration and all
   distinct missing-link/unsupported/zero-record/summary/tile-error states. Legend is the existing GBIF
   qualitative raster density scale, not Native ranges numeric bins. Test external-request boundary.
3. **Then:** Collection origins adopts the shell, compact type/search controls and site inspector.
   Preserve existing filtered-record semantics, exact coordinates/accuracy and list/marker callback.
   Review tile failure and reduced-motion behavior as renderer-specific improvements; Leaflet
   invalidateSize is required when revealing a hidden mobile map. Do not mount a second map instance.

Only step 1 is implemented here. The other two screens remain unchanged.

## Risks, integration and review boundary

- Current Feature Review belongs to COLLECTION-VISUAL-002. Canonical workflow supports **one** Review
  project/port. No launch, stop, seed, adoption or replacement here; no persistent environment touched.
  Local tests/builds and design artifacts are the available evidence until an explicit slot is free.
- New styles are scoped; existing normalization selectors must be checked for specificity. Shared
  docs/features and progress may conflict with the other candidate: merge entries by ID/milestone,
  preserving both, with no broad reformat. Harvests/Locations and shared primitives stay untouched.
- Small polygons remain hard touch targets; the companion buttons are required. Native SVG keyboard
  behavior and screen-reader support require real browser acceptance, beyond jsdom.
- Mobile hides one pane with CSS rather than unmounting; current local requests remain bounded.
  Responsive behavior must be inspected at 1440×844, 1024×844, 390×844 and actual browser zoom once
  Review is available. Static/layout evidence does not certify the authenticated live application.
- No canonical feature-verify, stage, commit, push or delivery. Independent reviewer owns final gate.

Implementation results and exact verification are recorded in [the handoff](maps-foundation-001-handoff.md).

## Native ranges proof after authenticated review — 2026-10-19

The [live review](review/maps-foundation-001/live/README.md) proves the presentation shell in
overview, one-species and multi-species modes, pane/inspection preservation, keyboard focus and
existing Saved Views/URL integration against real persisted synthetic records. Compact controls
and below-map supporting explanations were refined from actual mobile measurements. Native
ranges retains responsibility for exact places, boundary omissions, count bins and contributors.

Only shell placement and legend structure are reusable evidence today. Species distribution still
needs explicit-load/unloaded-restoration validation and Leaflet resize handling; Collection origins
needs its own coordinate/accuracy, marker-list, basemap privacy and hidden-pane sizing checks.
No generic provider, viewport or evidence-model abstraction has been proven by this slice.
The earlier Review-slot limitation above is historical: the operator approved guarded replacement
and the running Review now belongs to Maps. True zoom and screen-reader acceptance remain pending.

## Operator layout and interaction refinement — 2026-10-19

The existing renderer and scientific decisions remain. The operator requested an overview first:
right-side header controls, actionable grounded KPIs, a large central map and secondary exploration.
Native ranges therefore uses MapWorkspace's canvas-only composition and the existing TaskDialog
for its paged, searchable multi-species chooser. The selected count and compact comparison names
remain visible; details use explicit disclosures instead of long initial lists. KPI drill-down is
transient except the existing with-range filter. No inverse/no-range API behavior is invented.

Hover/focus preview is separate from committed inspection. SVG fills, fixed boundaries and inward-
clipped selected/hover/focus emphasis are separate ordered layers, preventing later neighboring
fills from erasing selection or emphasis from painting into adjacent land. These SVG details stay
Native ranges-owned. Later map phases may reuse layout, chooser placement and grounded drill-down
patterns, but require their own provider, explicit-load, coordinate and Leaflet sizing validation.
See the [current handoff](maps-foundation-001-handoff.md) and
[authenticated evidence](review/maps-foundation-001/refinement/README.md).

## Operator spatial workspace refinement — 2026-10-20

This supersedes the earlier rail/full-width-canvas and bottom-disclosure layout proposals. It retains
both renderer decisions, all evidence contracts and the same dirty candidate.

The operator requests geographic exploration rather than a species directory before a map. The
existing Collection PageHeader search slot now holds the durable botanical query; Filters, Saved
views and Choose species remain beside it. Explore all uses every matching represented identity;
Compare uses explicit choices, with five stable labelled colors. Larger v1 selections retain every
ID in a count-based compatibility view. No migration or silent truncation.

A roughly 70/30 map/inspector layout preserves the map's 2:1 geographic ratio. The comparison legend
follows the map, preventing five names from consuming the first mobile viewport. At ≤64rem mounted
Map/Inspector panels switch explicitly. The inspector replaces bottom territory disclosures;
comparison names/removal are directly in the legend, while one About/Places evidence path replaces
multiple low-priority accordions. Exact-place pagination does not remount the map.

Equal-width diagonal SVG stripes encode all 2–5 contributing colors; one ID is solid. Stripe IDs are
unique per map and territory. Existing fill, border and inward-clipped emphasis layers remain intact.
This avoids last-layer-wins and retains selected/hover/focus geometry. World-scale tiny countries
cannot display every stripe; counts and the exact contributor list remain necessary equivalents.

Territory clicks/Enter/Space toggle independently from species. Chips remove one or clear all.
The default inspector is a distinct union; explicit All provides intersection over the same coverage
relation. Selection survives ordinary mode/filter/species changes, including neutral zero coverage,
but remains transient on navigation/reload and does not expand Saved View v1.

A demonstrated API gap required a bounded authenticated territory-identity read: overview contains
counts, not complete contributor metadata. The new endpoint reuses canonical coverage ancestry and
existing representation/filter rules, pages identities and enriches only that page with exact/broad
record evidence. Two reads plus one for a nonempty page, no N+1, geometry or provider requests.
This is a presentation read, not a new geographic assertion or inventory count. Generated API
artifacts are updated; database schema, fixture and other maps are unchanged.

Proven reuse remains composition and accessibility patterns. Native stripe/ancestor/identity-count
semantics are not shared occurrence-density or material-origin abstractions. See the
[current handoff](maps-foundation-001-handoff.md) and
[spatial evidence](review/maps-foundation-001/spatial/README.md) for completed checks and limits.
