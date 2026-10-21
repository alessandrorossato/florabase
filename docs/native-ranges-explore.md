# Native ranges (EXPLORE-002)

## Pre-implementation domain audit

At base `aa6c1bf2d6554cc877dec407e14d04f1e048997f`, GEOGRAPHY-001 uses the pinned
CLDR 48.2.1 snapshot: 287 immutable canonical nodes in one World-rooted tree.
World, continents and applicable intermediate/subregions use `source_code_type=un_m49`
(including `001` World and `005` South America); country/territory nodes use
`source_code_type=iso_3166_1_alpha_2` (`IT`, `BR`, `TH`, etc.). There are exactly 29 M49 nodes, 250 ISO nodes and 8 `cldr_territory` nodes
(`AC`, `CP`, `DG`, `EA`, `IC`, `QO`, `TA`, `XK`). These CLDR-only codes are not
mislabelled ISO/M49 or silently crosswalked; exact CLDR-only ranges remain unmapped.
ISO territory ancestry may traverse the CLDR grouping `QO` on its way to World.
Source metadata is
mandatory for canonical nodes. Display paths follow the stored parent relationships.
See [the geography source contract](geography-data.md).

Custom places extend this tree as `city_town`, `locality` or `other_named_area`.
They have no source codes or polygon geometry, may be renamed/reparented/retired, and
retain their exact identity. A custom descendant does not inherit its parent's boundary.

GEOGRAPHY-002 owns `BotanicalIdentity → BotanicalProfile → BotanicalProfileNativeRange
→ GeographicPlace`. The relationship's composite primary key prevents duplicate exact
links. It allows disjoint places and broad plus precise places together. Neither
ancestor replacement nor descendant native assertions occur. The existing
`BotanicalNativeRangeManager` in identity Reference details uses authenticated
list/add/remove endpoints. Adding the first range creates a meaningful profile;
removing the last range removes only an otherwise empty profile. Text, including
operator-authored `origin_distribution`, remains independent. Place deletion is FK
protected. Revision `0022` owns this domain; EXPLORE-002 will not change it.

EXPLORE-001's existing SQL projection derives exact represented identities, Living,
Current and Historical scopes. It includes managed active inventory even with unknown
remainder. Its literal scientific/common/cultivar search and lifecycle rules are reused.
Collection origins uses ProvenanceSites and occurrence maps use explicit GBIF evidence;
neither supplies native-range facts.

## Geometry source review and selection (before implementation)

Selected: Natural Earth **1:110m Admin 0 map units**, dataset **5.1.1**, from the
maintainer's pinned repository release **v5.1.2**:
[official GeoJSON](https://github.com/nvkelso/natural-earth-vector/blob/v5.1.2/geojson/ne_110m_admin_0_map_units.geojson).
The official [download page](https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-0-details/)
and downloaded VERSION file identify the dataset as 5.1.1. The repository tag and
dataset version are deliberately recorded separately. The source has 183 features,
861,911 bytes, SHA-256 `718ac51d68ed2bf5de4f563fff2e2e045db706c1d3222805f3e317140a64213b`.

[Terms](https://www.naturalearthdata.com/about/terms-of-use/): public domain,
modification/redistribution allowed, attribution optional. Florabase nevertheless
credits Natural Earth and keeps a source/license notice with the derived asset.
Natural Earth is maintained by its upstream community; updates here require explicit
review and regeneration, never a runtime fetch.

Alternatives: 1:110m countries can combine overseas territories with sovereign
states, obscuring ISO territory presentation. Map units provide separate French
Guiana geometry and can combine the four GB subunits by stable ISO code. 1:50m/10m
would improve small islands at increased parse/render cost; this world overview
uses the smaller bounded source and explicitly reports unavailable boundaries.
No live geometry/geocoding service is needed.

Mapping uses upstream `ISO_A2_EH`, the source's explicit ISO mapping, only when it
matches a canonical territory code. Repeated codes (GB, PG) combine their drawing
paths into one map unit. Invalid `-99` codes remain uncounted neutral background.
No display-name matching, fuzzy matching or invented disputed-territory crosswalk.
M49 geometry is derived solely from canonical descendant ISO territories. Descendants
are rendering primitives; the authoritative list retains the exact stored macroregion.

Natural Earth follows [de facto boundaries](https://www.naturalearthdata.com/about/disputed-boundaries-policy/).
The low-resolution source omits small territories and some disputed units lack ISO
mapping. Boundaries express the source's cartographic choices, not Florabase's political
or botanical assertions. Broad geometry can be partial; unavailable territory boundaries
and custom ranges remain explicit. No centroid/point substitute is used.

The derived asset will strip unrelated attributes, retain code-indexed SVG paths in a
simple world projection, and load only with Native ranges. It remains application
presentation data, never database/domain data. Geometry attribution does not attribute
operator-authored botanical facts to Natural Earth.

## Workspace and evidence semantics

`#/native-ranges` has one Explore all / Compare species workspace. It uses
the EXPLORE-001 All represented, Living, Current and Historical scopes and literal
scientific/common/cultivar text search. A small optional With native range only filter
never changes representation rules. Reference-only identities are excluded; represented
identities with no structured range remain discoverable by default.

The default overview reports represented/with-range/without-range counts over the
whole filtered dataset, independent of pagination. The choropleth and its ranked
territory companion list count **distinct BotanicalIdentities per territory drawing
unit**. SQL forms canonical territory ancestry once, joins the exact native-range
relationships, and counts distinct identity IDs. One identity contributes at most one,
even when both South America and Brazil are stored. With A = South America,
B = Brazil and C = South America + Brazil, Brazil gets **3**, Argentina **2**.
Counts never describe plants, quantity, occurrences, completeness or abundance.

A separately paginated Exact recorded places list reports distinct identities explicitly
linked to each stored place. These are exact relationship counts, not inferred descendants;
adding these counts together would double-count overlapping ranges. Custom and unsupported
canonical places stay here even when they cannot be drawn. Broad labels and partial-boundary
counts preserve the stored precision. No text prose is parsed or mapped.

Selected species shows its exact current structured places, hierarchy paths, broad/precise/custom
status, and available boundary union. Its map uses all recorded relationships even when the
exact-place list spans pages. Selected IDs persist independently of search/page; coverage eligibility uses every active filter. Missing/unrepresented
UUIDs and filter mismatches stay explicit and clearable. No-range, no-boundary, local-asset failure,
loading and API errors have readable states and retry where applicable. Edit recorded range
opens the existing identity Reference native-range module via `?tab=native-range`, with the
original manager and add/remove semantics. This Explore surface does not write domain data.
View occurrence distribution navigates to the separate explicit-load MAP-002 workspace.

## API and query bounds

All endpoints require the existing authenticated local reader:

- `GET /api/v1/explore/native-ranges/identities`: `q`, `scope`, repeated `record`, `with_range`, `offset`, `limit`.
  Two SELECTs: filtered total plus ordered page, including native-range count per identity.
- `GET /api/v1/explore/native-ranges/overview`: same filters/bounds. Four SELECTs:
  identity summary counts, exact-place total, territory coverage, exact-place page with paths.
- `GET /api/v1/explore/native-ranges/identities/{uuid}`: the same filters, exact-place `offset`, `limit`.
  Four SELECTs when represented; one SELECT for missing/unrepresented 404. A filter mismatch is
  reported in the identity instead of silently selecting another one.

`q` is at most 200 Unicode characters, `offset` 0–100000, `limit` 1–100 (default 50).
Ordering matches Species distribution (lower scientific name, cultivar null first, UUID).
Exact places sort by descending explicit-identity count, lower hierarchy path, UUID.
Territory coverage is structurally bounded to the 250 immutable canonical ISO territory nodes,
including unavailable geometry; no collection records or polygons are returned. Path recursion
walks ancestors for the set of range places once per query, never per row. Query count does not
grow with identity/range count; PostgreSQL regressions measure both page sizes 1 and 50 and
full lifecycle/inventory parity. Geometry never enters PostgreSQL; no new domain table or PostGIS.

The inspector adds `GET /api/v1/explore/native-ranges/territories/identities`: repeated uppercase
ISO `territory` (1–250), `match=any|all`, optional repeated UUID `identity` (≤20), and the existing
filters and pagination. A bounded read was necessary because overview intentionally exposes counts
without unbounded contributor arrays. Two reads return a distinct total/page; one extra read enriches
nonempty pages with exact-versus-broad evidence. The same canonical ancestor CTE powers rendering
coverage and these results. No per-row reads, geometry queries, provider I/O, table or migration.
OpenAPI and TypeScript artifacts are regenerated together.

## URL, Saved Views and migration

Canonical state: `scope`, `q`, `mode=overview|species`, sorted UUID set `identity` (maximum 20),
canonical category set `record`, boolean `withRange`.
Defaults are omitted. Example:
`#/native-ranges?scope=living&mode=species&identity=<uuid>`.
Refresh and Back/Forward restore local controls and explicit selection. Pagination is transient.
Private `native_ranges` Saved Views use state version 1 and the same strict adapter. Opening,
including reopening the same view, resets pagination and rebuilds from current local data.
Geometry, hover, map internals, errors, scroll and offsets are never persisted. Unknown/invalid
saved fields are incompatible; invalid manual URL fields fall back safely.

Alembic `20261008_0038` only extends `ck_saved_views_surface`. Downgrade takes an exclusive
writer lock and refuses while Native ranges views exist. Compatible `0037 → 0038 → 0037 → 0038`
preserves other views. GEOGRAPHY-002 and provider contracts remain untouched.

## Presentation, accessibility and privacy

MAPS-FOUNDATION-001 follows the delivered Seeds/Sowings/Plants PageHeader grammar: Explore eyebrow,
Native ranges title, short subtitle, and a wide scientific/common/cultivar search beside Filters,
Saved views and Choose species. Search uses the same durable collection query and never removes
explicitly chosen IDs. The chooser is paged and allows five color layers; deselection stays available.

Explore all shows the complete filtered representation scope, independent of the comparison set.
Compare species uses only the explicitly chosen IDs that match those same filters. Compact overview
KPIs open the chooser, focus the territory inspector, or open exact-place evidence. The no-range KPI
remains informational; no inverse filter or artificial destination is invented.

The wide workspace allocates approximately 70% to the undistorted 2:1 local map and 30% to a permanent,
scrollable inspector. The comparison legend follows the map, with one labelled color, scientific name,
Places action and Remove control per identity. Palette: green `#287c67`, rust `#aa562d`, blue `#5467b2`,
mauve `#9a477a`, ochre `#81701f`. Surviving IDs retain their colors while the comparison is active;
removed colors can be reused. Refresh may allocate colors again. One contributor uses a solid fill;
2–5 use equal-width diagonal SVG stripes containing every contributor's color. Names/counts and
inspector results provide a non-color equivalent. Tiny polygons cannot display every stripe at world
scale; inspect their contributor list rather than infer finer precision from a swatch.

Click, Enter or Space toggles a territory; no modifier is required. Multiple territories remain
selected independently from species. Removable chips and Clear territories expose persistent choices.
Changing species, mode or filters retains the chosen territory codes, including neutral zero-coverage
units, until explicit removal. Names for retained zero-coverage units are display labels, not new
range evidence. Back/Forward, Saved View navigation and reload clear this transient inspector state.
Territory IDs, union/intersection choice, panel, preview and scroll do not extend Saved View v1.

The inspector defaults to the distinct union of identities covering any chosen territory. Its explicit
Any/All control offers intersection over the same canonical coverage relation. Explore all reads the
whole filtered collection; Compare passes the explicit selection as an additional bound. Results show
matched territories and distinguish explicit country records from drawing coverage inherited from
broad recorded places. Broad and exact links may both be displayed without double-counting. The
inspector search filters the labelled current page; Next/Previous retain the server-side scope.

The SVG keeps one roving territory tab stop, arrows/Home/End navigation, transient hover/focus previews
and Escape dismissal. Shared borders and inward-clipped selected/hover/focus outlines remain separate
inert paint layers above fills. A polite selected-territory announcement sits outside mobile panels.
At ≤64rem Map/Inspector controls switch mounted panes, preserving chosen territories and focus on the
switch. The textual chooser also includes canonical places whose boundaries are unavailable.

About this map opens one bounded evidence dialog for methodology, unsupported boundaries and paged
exact broad/precise/custom places. Places beside each compared identity opens its exact evidence.
Paging this evidence keeps the map and geographic selection mounted. There are no duplicate bottom
coverage/selection accordions. Dialog Escape/Done restore the invoking control, with a stable chooser
fallback if query changes replace the original KPI.

No new tiles, geolocation, provider calls, geocoding or geographic precision are introduced. Natural
Earth attribution remains beside the canvas. Loading, failure, no-range, missing/excluded identity,
unsupported/custom place and authentication boundaries remain explicit. Actual screen-reader,
physical-touch and true browser-zoom certification remain operator acceptance items.
See the [design](maps-foundation-001-design.md), [current spatial evidence](review/maps-foundation-001/spatial/README.md)
and [handoff](maps-foundation-001-handoff.md). Acceptance and canonical verification remain separate.

## Operator UAT refinement: comparison and record categories

Exactly one selected species retains the exact places, map and identity/edit/occurrence links above.
Color comparison uses up to five distinct eligible selected identities per territory, with labelled
contributors including unavailable boundaries. Per-identity overlap is unioned before aggregation.
The API and Saved View v1 still accept up to 20 IDs: restored sets of 6–20 use count-based coverage,
retain every ID and expose explicit removal. No truncation or schema migration is introduced.
New chooser selections stop at five, while deselection and Clear selection remain available. There is no query-wide selection. Missing/unrepresented IDs remain explicit;
filter-excluded IDs remain selected but contribute no coverage. An empty eligible subset is explained.

Collection status remains single-select. **Collection records** uses OR across `seed_lot`, `sowing`,
`plant`, `plant_group`, `stored_material`; no chosen categories means all types. Each uses only the
existing exact authoritative FK relationship. All requires retained category evidence; Current
requires an active record in a selected category; Living requires an active Plant/PlantGroup in a
selected category (Living + Seeds is empty). Historical requires retained selected-category evidence
and **globally no Current representation**, including current records in unselected categories.
Search and With native range only then restrict the same set used by directory, overview, counts
and selected coverage. Representation badges/counts still describe the identity's global collection
status, not an invented category-specific lifecycle.

`GET /api/v1/explore/native-ranges/selection` accepts repeated UUID `identity` (maximum 20), `q`,
`scope`, repeated enum `record` (maximum 5), `with_range`. Two SELECTs return bounded selected
metadata with `matches_filters`, missing IDs and up to 250 territory counts with distinct contributor
IDs. Single-species detail accepts the same filters and retains four SELECTs. Query counts do not
grow with selection size. Overview does not fetch unbounded contributor arrays.

URL parameters repeat `identity` and `record`; IDs are lowercase, deduplicated and sorted; categories
follow the canonical domain order. Invalid/oversized manual selection is rejected as a whole with
visible feedback, without arbitrary truncation/substitution. Saved v1 state stores arrays of stable
IDs/categories; the previous singular UUID v1 form remains readable and normalises to one ID.
Defaults and transient paging/geometry/errors remain omitted. No migration beyond 0038 is added.

Desktop Explore: Botanical identities, Media, Geography, then lightweight **Maps** text followed
by Species distribution, Native ranges, Collection origins. Maps has no disclosure/action/route.
Geography stays outside Maps because it manages GeographicPlace and ProvenanceSite reference data.
Mobile retains the same destinations in a flat menu. Routes and SavedView identifiers are unchanged.

Future provider-backed native ranges and the later whole-application review are planning only;
see [the official Kew candidate audit](native-range-enrichment-audit.md) and [roadmap](product-roadmap.md).
