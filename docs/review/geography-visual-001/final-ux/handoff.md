# GEOGRAPHY-VISUAL-001 — Final UX review candidate

25 October 2026; final checks after the 24 October UX refinement. Source: `/home/alessandro/.codex/worktrees/5430/florabase`;
branch `feat/geography-visual-001`; base `e7ade78559803a35b738a669085799f55eb76258`.
Fetched `origin/main` before `make feature-init`. The supplied clean Codex-managed worktree is the
isolated feature source; the canonical workflow forbids creating a second feature worktree.

Implementation candidate, **not operator accepted or canonically verified**. The backlog status is
`implemented`. Everything remains unstaged and uncommitted. No push, PR, delivery or FULL gate.

## Audit and comparison with Locations

Read the current UI contract, development workflow, THEMES/CONTROLS handoffs and all three delivered
Maps handoffs. Inspected Geography, Locations, ProvenanceSite management, native-range assertions,
collection provenance editors, App routing, directory controls, Saved Views and map state contracts.

| Surface | Existing implementation | This candidate |
| --- | --- | --- |
| Shared grammar | PageHeader, DirectoryTools, ActionButton, QuickPreview, TaskDialog and theme tokens already work | Reuse them. No global CSS rewrite, shared token edit or new dependency |
| Places | Real recursive hierarchy; independent expand and select controls; canonical CLDR/local distinction; large detail-style preview title/actions | Preserve tree and edit rules; consistent strong row title, secondary code/path, compact preview typography/actions and explicit detail/site navigation |
| Locations reference | Physical hierarchy, status/usage metadata, directory selection, compact preview and explicit detail/edit/child actions | Reuse its layout/interaction grammar; do not reuse storage semantics as geographic provenance |
| Site directory | Separate legacy serif heading/row titles, coordinate status buried in metadata; notes and large actions in every preview | Shared UI typography, visible coordinate status, explicit unknown accuracy, compact actions; full notes and exact linked source records on site deep links |
| Tablet headers | Legacy column direction makes horizontal shared flex bases act as enormous heights | Scoped Geography header wrapping keeps natural height, with no shared shell edit |
| Exploration | Three delivered global map destinations; Geography had management tabs only | One global Geography entry, six internal destinations, compact local-evidence overview and the complete existing map workspaces |
| Geography Map mode | Maps all coordinate-bearing sites, including unlinked sites | Preserve `mode=map`; label it **Site map**, explain its management purpose and link to Collection origins |
| URL navigation | Geography passed fresh callback/fallback objects to its view hook on every parent render | Stabilize those arguments. Browser reproduction showed a changed query URL retaining old mode/search; the same transition now updates correctly |

Geography-specific CSS lives in `frontend/src/geography/geography.css`. Shared directory components,
Settings, design tokens and unrelated page shells are untouched. The operator explicitly authorized removing only the Maps subgroup and its three links from desktop Explore and mobile More. Geography is now their single global entry. Selection
continues to use the shared selected background/accent. A separate focus outline and pressed state
keep keyboard focus distinguishable from selection. Long names and paths wrap.

## Internal navigation and routes

One native-link navigation contains **Overview, Native ranges, Species distribution, Collection origins,
Places and Provenance sites**. The redundant management row is removed. Provenance sites now use one synchronized list/map/inspector; the existing List/Site map query state controls the narrow presentation. Desktop shows all three panes simultaneously. On narrow screens the single row scrolls horizontally;
active destinations are revealed, native keyboard focus scrolls into view, and focus has its own ring.

The canonical workspace prefix is `#/geography/`. `GeographyWorkspace` lazily mounts the **existing
complete screen** for the selected view. Each screen supplies its own existing search, Filters,
Saved Views, tools, inspectors and body through `GeographyHeader`, which renders one PageHeader and
one six-link navigation. Shared Florabase Breadcrumbs sit above the heading: Explore (group label, because no Explore landing route exists), linked Geography Overview and active view. There are no map forks or static map replacements. Existing SVG/Leaflet,
provider/cache/privacy components were not changed. Places/Sites reuse the same management instance
while navigating between directories, preserving expanded hierarchy state.

| Canonical entry | Supported older entry | Meaning |
| --- | --- | --- |
| `#/geography/overview` or bare `#/geography` | — | Compact evidence overview; bare global entry now opens Overview |
| `#/geography/native-ranges` | `#/native-ranges` | Full structured reference map, species comparison, territory inspector |
| `#/geography/species-distribution` | `#/species-distribution` | Full single-identity occurrence workspace |
| `#/geography/origins` | `#/map` | Full Collection origins workspace |
| `#/geography/places` | `#/geography?mode=places` and legacy q-only state | Existing hierarchy and Places directory |
| `#/geography/sites` | `#/geography?mode=sites` | Existing Provenance sites directory |
| `#/geography/sites?mode=map` | `#/geography?mode=map` | Shared site workspace; narrow map presentation, all sites remain selectable |
| `#/geography/places?place=<id>` | `#/geography?place=<id>` | Exact selected place; ancestors expand |
| `#/geography/sites?place=<id>` | `#/geography?mode=sites&place=<id>` | Sites directly related to that exact place |
| `#/geography/<site-id>` | unchanged | Exact site details and supported source-record links |

Old entries are **render aliases**, not redirects: their URLs and query strings remain intact.
The router normalizes only the selected workspace; a small directory-path adapter lets the existing
state parser read both prefixes. State writers retain the current URL prefix and unknown parameters.
Exact `identity` IDs (including legacy multi-identity Native ranges), `mode`, search, filters and
scope keep their existing validation and semantics. Native internal anchors preserve reload,
Back/Forward and modified-click behavior. Canonical directory mode defaults do not overwrite explicit
legacy `mode` query state.

Saved View surface names, version 1 schemas, serialized keys and stored legacy paths are unchanged.
Restoring a prior map Saved View renders the corresponding full screen under Geography. Geography
Saved Views still persist only `q` and `mode`; place-scoped context does not offer a misleading Save
action. The Overview has no invented Saved View type. Bounded example links are labelled as examples.

Real browser reproduction also found the Origins URL listener being rebound by an inline reset
callback: same-view URL changes could show stale search. A stable callback now preserves the listener;
a focused regression and browser Back/Forward check cover it.

## Three evidence destinations

The overview makes four authenticated local reads: native-range overview and a bounded identity
page, represented-identity readiness, and the existing provenance map projection. The three compact divider-led evidence rows
load and fail independently, show truthful empty states and offer retry while their navigation stays
available. Requests abort on departure; 401 uses the existing session-expiry flow. No map engine,
geometry, external imagery, provider cache refresh or provider request is mounted/started there.

- **Native ranges:** represented identity coverage, recorded named areas and missing structured
  ranges, plus exact Botanical Identity/Reference and species-scoped map links. Only existing explicit
  profile/place assertions count. Broad-derived drawing coverage remains distinct from exact records;
  custom/unsupported places do not acquire invented boundaries.
- **Species distribution:** represented identities and compatible confirmed taxon-link availability.
  The overview explicitly labels occurrence counts **Not checked here**. A ready link is not a downloaded occurrence dataset or a coverage claim. Open the existing workspace
  to explicitly load/refresh GBIF. Local cache behavior, attribution, eligibility, privacy, quality and
  failure handling remain unchanged. Density is neither abundance nor evidence of native status.
- **Collection origins:** coordinate-bearing sites and distinct `(record_type,id)` direct records **at mapped sites**,
  coordinate-less site count, exact example site and source-material links. Historical records remain.
  Counts are records, not quantities. The dedicated map, local Natural Earth context, explicit optional
  online detail and configured privacy/attribution controls are reused unchanged.

## Geographic data workflows and preserved contracts

Local places still require an existing non-retired parent; cycle, retirement, deletion and usage
constraints remain server authoritative. Canonical CLDR names/ancestry are read-only. Selection and
creation reveal existing ancestors without flattening relationships. Parent/site navigation selects
exact IDs and reveals the corresponding branch.

Sites retain exact decimal WGS84 values, nullable paired coordinates, recorded/unknown accuracy,
place relationship and notes. Full notes are visible on the exact site route and remain in the
existing editor. There is no separate structured site source field to fabricate; existing operator
notes remain notes. Usage counts are existing server counts. Site edit, create, delete conflicts,
CSRF and coordinate validation are unchanged.

SeedLot and direct Plant/PlantGroup provenance editors retain their explicit operator confirmation.
Neither Supplier, physical Location, scientific-name matching, ancestry nor a native range creates
collection provenance. Source links reuse the existing origins projection and record-link helper,
including retained historical material. Nothing changes the direct-origin qualification of derived
Sowings, extracted Plants or other descendants.

Structured native-range creation/deletion remains in the Botanical Identity Native range module.
Existing operator assertions and assisted enrichment review/source evidence remain unchanged. No
unapproved provider import, automatic range inference, source assertion, polygon upload or broad API
extension was added.

## Missing link contracts and integration dependencies

The site directory API returns usage **counts**, not linked record IDs. The existing origins
projection supplies exact direct-record IDs only for coordinate-bearing sites. Site details reuse
those IDs. Sites without coordinates explicitly explain that exact links are unavailable, retain
truthful usage totals and offer the Collection origins workspace. This limitation was reported before
implementation; no scientific-name search or guessed material link is used as a substitute.

Place-to-site scope is exact/direct, not a recursive descendant filter. There is no new place-scoped
native-range identity listing contract, global provenance filter or completeness endpoint. Geography
and origins remain unpaginated existing APIs; this candidate adds no real-large-collection performance
claim. The overview does not download or scan occurrence rasters for readiness.

The operator explicitly approved the localized global Maps removal despite IA-NAV-001. Future IA-NAV
integration must retain Geography as the single geographic entry and reconcile the same App routing,
Explore and mobile More lines; this is not authorization to redesign other macroareas. Shared directory
state parsing now recognizes canonical Geography aliases; review those few lines if IA-NAV changes
route handling. No IA-NAV worktree was touched.

Read-only audit of `feat/botanical-identities-visual-001` at `859028a` found IdentityMaps links to
`#/native-ranges?mode=species&identity=<id>`, `#/species-distribution?identity=<id>` and `#/map`.
All remain supported, including exact IDs. Its `#/geography` link reaches the Overview, with Places
first-class alongside it. `tab=source`, `tab=reference` and native-range module links remain unchanged.
Fetched `origin/main` remains `e7ade78`; no rebase, other checkout edit or protected delivery action.
Recheck integration state before later acceptance/verification/delivery.

## Review environment

[Open isolated Geography review](http://localhost:15276/#/geography/overview).
Login: `geography-review`. Its generated password is retained only in the operator-readable,
mode-0600 file `/tmp/geography-5430-owner-password`; it is absent from repository evidence.

The separately named `florabase-geography-5430` project owns its DB, media and network. Backend uses
this worktree's read-only source/migrations over the existing compatible development image;
frontend is this worktree's Vite source and locked local dependencies, served by detached container
`florabase-geography-5430-frontend` with restart policy `unless-stopped`. DB revision is
`20261013_0042`. The original temporary Compose file is no longer retained; the existing containers retain their configuration.
Only loopback ports 15276 (frontend) and 18276 (backend) are used. PostgreSQL has no published port.
The first attempted 15176/18176 pair was occupied and startup refused; no existing listener was stopped.

The fixture was created through authenticated APIs in this new database only: canonical geography,
two nested local places, one coordinate-bearing site, one coordinate-less site, two identities,
two SeedLots (including historical material), one explicitly synthetic profile/range. No external
taxon ID, provider occurrence or scientific evidence was fabricated. DEV, UAT, Review, Sourcing,
Stable Preview, the primary checkout and other worktrees retain their data and ownership.

This is a candidate-owned manual review runtime, not a new supported lifecycle role. Do not run the
fixed `feature-review-*` helpers to take ownership of another worktree's retained Review. Temporary
runtime files are outside the delivered implementation; no environment/workflow mechanism is added.

## Verification and visual evidence

Current verification, screenshots and interaction evidence are indexed in
[the final UX review gallery](review/geography-visual-001/final-ux/README.md).
The [initial handoff](review/geography-visual-001/initial-handoff.md), [unified-navigation handoff](review/geography-visual-001/refinement/unified-handoff.md) and both earlier galleries are retained
as historical evidence; their old grouped navigation/sidebar descriptions are superseded here.
Final UX evidence covers the requested viewports and all three palettes in Light/Dark, the compact
Overview, shared breadcrumbs, expanded Places hierarchy/preview, New local place dialog, mapped and
coordinate-less Sites and narrow presentation. Exact completed counts and machine-readable reports
are in the final gallery. Earlier phase totals remain historical; they are not final-tree evidence.

The New local place dialog uses existing TaskDialog backdrop/Escape semantics and one guarded
callback for backdrop, native cancel and Cancel. Pending requests cannot dismiss. Dirty name/type/
parent changes use the established native discard confirmation. A preselected Create local child
parent is the clean baseline, not a spurious dirty draft. Declining keeps all fields; accepting
resets the draft. Native modal trapping and return to the actual invoking control remain intact.
No global dialog or shared dirty-state mechanism was changed.

Places reuse the established selected inset accent; expansion remains a separate labelled button.
Indentation is capped after two nested offsets, with full ancestry and direct parent navigation in
the preview. Canonical/local status is stated once in the preview header; metadata avoids repeating
the full ancestor path. Existing authoritative child/native-range/site/material counts and exact
associated-site links remain. This is presentation work, not a changed tree/domain model.

Site management reuses the existing ProvenanceMap with coordinate-bearing points only. All matching
sites stay in the same list in both presentations; selecting an unlocated site retains its inspector
and Edit action without an invented marker. List, marker and inspector share selectedId. Desktop has
three simultaneous panes; tablet uses list/map with inspector below; mobile List/Map adapts the same
DOM and selection. Edit/detail actions are prominent above metadata. Backend records have no separate
site subtype: the inspector identifies Provenance site without fabricating a classification.
Existing decimal coordinate values, accuracy circles, local generalized context, explicit online
opt-in and external privacy behavior are unchanged. No new map engine or automatic provider request.

The final focused regression selection covers App/lazy/transition, map screens and aliases, breadcrumbs,
Overview, site selection/coordinate-less records, New local place dismissal/draft/pending protection,
Saved Views and occurrence/cache/privacy/tile behavior. Static checks and build are reported in the
final gallery. The host experienced memory pressure: interrupted worker/capture attempts are not
counted as passing evidence. Completed sequential runs supersede them; no global timeout or assertion
was weakened.

No backend/domain/API/schema change was made, so backend/integration, migration-cycle and API
regeneration suites were not rerun. The new Review database was migrated normally to existing head;
that is startup evidence, not a new migration acceptance claim. The canonical FULL gate is explicitly
reserved for after operator acceptance. No receipt or verified status is claimed.

Remaining acceptance: operator visual/product review; true browser zoom; actual screen-reader and
physical touch-device checks; real large-collection performance; live GBIF/online imagery availability.
Provider-offline, cache and tile handling remain covered by the delivered map behavior and affected
regressions; this task does not perform provider traffic to manufacture new live evidence.

## Future concepts — not delivered

- Assisted native-range import: first approve a licensed botanical source, exact identity matching,
  source assertions and review/apply/undo behavior. The operator must confirm assertions explicitly.
- Provider refresh: define source/version/acquisition metadata, stale-state and provenance retention
  before extending the existing approved enrichment flow.
- User-provided boundaries/GeoJSON: validate size, coordinate reference system, geometry, topology,
  attribution and record ownership; never silently replace named-area or provenance evidence.
- Data completeness: introduce an agreed denominator and unknown/not-applicable meanings; current
  availability counts are not a new completeness score.
- Geographic cross-filtering/comparison: define exact ID, descendant, evidence type and Saved View
  contracts before linking broader result sets.
- Physical collection layout mapping belongs under **Locations**, with its own storage/layout model;
  it must not infer or overwrite biological provenance.

GEOGRAPHY_FINAL_UX_REVIEW_READY
