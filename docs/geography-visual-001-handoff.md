# GEOGRAPHY-VISUAL-001 — Operator corrections review candidate

25 October 2026. Worktree `/home/alessandro/.codex/worktrees/5430/florabase`, branch
`feat/geography-visual-001`, base `e7ade78559803a35b738a669085799f55eb76258`.
Latest fetched main: `5778da7be03bc6030cb0ab3af03b9631bf4fa209` (Botanical Identities #121).
The candidate was not reset/rebased/merged. Feature remains `implemented`. The operator completed
the visual review and approved the current implementation for a local commit. Independent QA and
canonical FULL remain pending. No push, PR or merge is part of this handoff.

## Final operator decisions

- Restored three balanced summary cards: Native ranges, Species distribution and Collection origins.
  Short explanations, factual coverage, supporting metrics and optional exact-record disclosures
  remain; equal-height cards share one action style. Geographic records uses compact links below.
- Completely removed the six-view tab strip and its component. No replacement navigation bar exists.
  Overview is the navigation hub. All six views retain their canonical URLs; maps remain complete
  existing workspaces, reached from cards with an obvious breadcrumb return to Geography Overview.
- Sites use **LEFT list and inspector / RIGHT prominent map** (37/63 proportions, bounded by usable
  minimums). List, marker and inspector share the existing selected ID. Coordinate-less records remain
  discoverable/editable without a marker. Mobile List/Map adapts the same DOM and selection.
- Places use moderately rounded, bordered, spaced rows, inherited selected accent and separate focus.
  Restrained chevrons replace +/- boxes: right collapsed, down expanded, no affordance on leaves.
  Existing labelled ARIA expansion, separate selection, capped indentation and hierarchy rails remain.
- Shared breadcrumbs cover straightforward root pages and existing record paths. Group labels with
  no landing route are plain text; exact supported parent hrefs/IDs remain. Named Collection details
  use their existing record titles. Dashboard avoids a redundant breadcrumb. See the bounded
  [cross-application audit and follow-up](geography-breadcrumb-audit.md).

Cold direct entry was explicitly checked: Geography styles load from its shared header independently
of the removed navigation component. No page needs a prior Places/Sites visit to acquire its styling.

## Routes, filters and return navigation

| Canonical entry | Supported older entry | Behavior |
| --- | --- | --- |
| `#/geography/overview`, bare `#/geography` | — | Hub with real summary cards and record links |
| `#/geography/native-ranges` | `#/native-ranges` | Complete reference map, species comparison and inspector |
| `#/geography/species-distribution` | `#/species-distribution` | Complete observed-occurrence workspace |
| `#/geography/origins` | `#/map` | Complete Collection origins analytical workspace |
| `#/geography/places` | Existing root management queries | Hierarchy and exact selected-place routes |
| `#/geography/sites` | `#/geography?mode=sites` | Shared site navigation/inspector/map |
| `#/geography/sites?mode=map` | `#/geography?mode=map` | Same selection; narrow map presentation, all sites accessible |
| `#/geography/<site-id>` | unchanged | Exact site details and supported source links |

Legacy entries are render aliases without redirects. The original query string, identity IDs,
comparison IDs, mode, filters, scope, unknown parameters and native history remain under the existing
state hooks. Version 1 Saved View surfaces, schemas and stored legacy paths are unchanged. Geography
breadcrumb uses the same canonical route helper as Overview. Native anchors keep modified clicks
browser-owned. Tests and browser checks cover hub return, direct entry, reload and Back/Forward.

## Preserved data and workflow boundaries

Native ranges remain explicit structured botanical assertions; occurrences remain provider evidence;
provenance remains operator-recorded collection origin. Supplier, physical Location, name matching,
ancestry and GBIF observations never create a native-range assertion or collection origin.

Overview still uses four authenticated local reads and independent loading/error/retry/empty states.
No engine, provider request, raster scan or fabricated map/image is mounted there. Unknown occurrence
counts remain **Not checked here**; eligible links are not downloaded observations. Direct-record
counts are qualified **at mapped sites**, distinct from quantities, with historical records retained.

Canonical CLDR names/ancestry stay read-only; local create/edit, parent/cycle/retirement/deletion and
usage constraints stay server authoritative. Exact associated-site scope is direct, not descendant or
name matching. Coordinates retain decimal WGS84 values, nullable pairs and recorded/unknown accuracy.
Existing source/notes/edit/detail actions remain. There is no site subtype field to invent.
Coordinate-less sites retain authoritative usage totals but lack exact linked-record IDs in the
existing API: the UI explains that limit instead of guessing links.

New local place retains the previous guarded TaskDialog: clean backdrop/Escape/Cancel dismissal,
inside-click safety, actual-trigger focus return, native focus containment and pending protection.
Dirty name/type/parent changes use the established discard confirmation; declining retains the draft.
A preset Create local child parent is the clean baseline. No global dialog mechanism changed.

Site management reuses the existing ProvenanceMap, local Natural Earth context, accuracy circles and
explicit online opt-in. No map engine or provider/cache/privacy logic was forked or altered. Collection
origins remains a separate analytical workspace and its contextual links remain available.

## Breadcrumb audit and integration

Shared Breadcrumbs was extracted without changing its caller API; CollectionUI still re-exports it.
PageHeader applies the common owning-group/current-page path to ordinary root workspaces. Record and
`action=` task routes keep their explicit paths. Exact supported links are not rewritten. SeedLot,
Sowing and Plant/PlantGroup details add their existing record title; Harvest, Location, Identity and
Media detail paths gain their actual group where previously absent. No sidebar macrocategory changed.

Contextual operation/wizard and embedded module paths retain their existing explicit return contracts.
They have a dedicated bounded follow-up in the audit; they do not trigger a global workflow refactor.

Main #121 adds the delivered identity hub, collection media/context and Saved View work. Read-only
IdentityMaps audit confirms its three exact legacy map links remain supported here. Before a later
canonical gate/delivery, reconcile its overlapping Collection files and Saved View state with this
candidate, preserving both. This review does not claim main was merged or their combined API tested.
The separate IA-NAV-001 worktree was not edited. The earlier operator-approved Maps subgroup removal
remains localized: Geography is still the sole global geographic destination.

## Viewport fit and evidence

[Current gallery, before/after links and machine-readable results](review/geography-visual-001/operator-corrections/README.md).
The prior [final UX handoff](review/geography-visual-001/final-ux/handoff.md), initial and unified
navigation galleries remain historical evidence. Their flat overview, tabs and middle-map layouts
are explicitly superseded by these operator decisions.

Six palette/mode combinations were checked at 1440×844, 1024×844 and 390×844. The measured desktop
map panel spans y=233–837 and tablet y=273–829 in Botanical Light: title/breadcrumb/actions, list,
map and selected-record primary inspector coexist within the requested viewport. Lists intentionally
scroll when long. The long-name mapped inspector has 362px visible/413px content on desktop and
314px visible/525px content on tablet; remaining metadata/counts use its keyboard-focusable panel
scroll rather than document scrolling. Mobile uses deliberate document flow for list/details and
optional Map presentation; a complete long inspector requires vertical scrolling. Typography is
not reduced to force fit. The full JSON records theme/size geometry and no horizontal overflow.

Ordinary captures use retained authenticated synthetic data. Regional map evidence uses existing
Fit/Zoom out controls, not an engine change. Large-list response doubles are labelled, browser-only
and never persisted. They are not a backend-scale benchmark. All completed browser runs report no
page errors or attempted external requests. Emulation is not physical-device or true browser zoom
verification.

## Verification and review runtime

Exact completed test/static/build results are recorded in the gallery verification JSON. The baseline
was 17 tests/3 files. Because PageHeader/Breadcrumbs are shared, the affected verification includes the
full frontend suite, plus focused route/tree/site/breadcrumb regressions. Backend/API/schema and
provider implementations were not changed, so backend/integration, API regeneration and migrations
were not rerun. Canonical FULL is explicitly deferred; no receipt or verified status is claimed.

[Open existing isolated Geography review](http://localhost:15276/#/geography/overview).
Login `geography-review`; the operator-only password note is outside the repository at
`/tmp/geography-5430-owner-password` (0600). Existing candidate-owned DB/backend/frontend containers,
volumes, media and network are preserved. Loopback ports 15276/18276 remain; PostgreSQL is unpublished.
No protected DEV/Review/UAT or other agent environment was reset, reseeded or taken over.

Live GBIF/online imagery, real screen reader/touch devices, true browser zoom and real-large-collection
performance remain deferred. The audit identifies contextual breadcrumb follow-ups and main #121
reconciliation before delivery. No push, PR, merge, feature-finish or canonical FULL is authorized.

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


GEOGRAPHY_COMMITTED_READY_FOR_QA
