# Unified Geography navigation and Overview refinement

Historical accepted-navigation evidence. The [final UX refinement](../final-ux/README.md) supersedes
this phase's Overview cards, Places spacing and separate site presentation.
The [handoff for this phase](unified-handoff.md) is preserved alongside the evidence.

Current candidate: `/home/alessandro/.codex/worktrees/5430/florabase`, branch
`feat/geography-visual-001`, base `e7ade78559803a35b738a669085799f55eb76258`.
[Open review](http://localhost:15276/#/geography/overview).
[Current handoff](../../../geography-visual-001-handoff.md).
[Preserved initial evidence](../README.md) and [initial handoff](../initial-handoff.md).

The operator explicitly authorized removing the global Maps subgroup and its three children.
Geography remains under Explore; other global categories are unchanged. One internal navigation
contains Overview, Native ranges, Species distribution, Collection origins, Places and Provenance
sites. Site map is a local List/Site map mode within Provenance sites. All three real map screens
reuse their full existing controls, renderers and data behavior through one Geography header.

## Current visual evidence

[Browser matrix](browser-matrix.json): **126 presentation checks** = seven views × three viewports ×
six appearances. **57 curated PNGs** cover all seven presentations at every viewport in Botanical
Light, all six Overview appearances at every viewport, additional desktop maps/sites and dark mobile
native-range views. Exact viewport dimensions are 1440×844, 1024×844 and 390×844; scrolled mobile
captures retain 390×844. The matrix and dimension report enumerate every image.

| Full workspace, Botanical Light | Desktop | Tablet | Mobile |
| --- | --- | --- | --- |
| Compact Overview | [1440](overview-1440-botanical-light.png) | [1024](overview-1024-botanical-light.png) | [390](overview-390-botanical-light.png) |
| Native ranges, one exact identity | [1440](native-1440-botanical-light.png) | [1024](native-1024-botanical-light.png) | [390](native-390-botanical-light.png) |
| Species distribution, unlinked identity | [1440](distribution-1440-botanical-light.png) | [1024](distribution-1024-botanical-light.png) | [390](distribution-390-botanical-light.png) |
| Collection origins | [1440](origins-1440-botanical-light.png) | [1024](origins-1024-botanical-light.png) | [390](origins-390-botanical-light.png) |
| Places hierarchy and preview | [1440](places-1440-botanical-light.png) | [1024](places-1024-botanical-light.png) | [390](places-390-botanical-light.png) |
| Provenance sites and preview | [1440](sites-1440-botanical-light.png) | [1024](sites-1024-botanical-light.png) | [390](sites-390-botanical-light.png) |
| Local Site map mode | [1440](site-map-1440-botanical-light.png) | [1024](site-map-1024-botanical-light.png) | [390](site-map-390-botanical-light.png) |

| Additional Overview appearances | Desktop | Tablet | Mobile |
| --- | --- | --- | --- |
| Botanical Dark | [1440](overview-1440-botanical-dark.png) | [1024](overview-1024-botanical-dark.png) | [390](overview-390-botanical-dark.png) |
| Herbarium Light | [1440](overview-1440-herbarium-light.png) | [1024](overview-1024-herbarium-light.png) | [390](overview-390-herbarium-light.png) |
| Herbarium Dark | [1440](overview-1440-herbarium-dark.png) | [1024](overview-1024-herbarium-dark.png) | [390](overview-390-herbarium-dark.png) |
| Mineral Light | [1440](overview-1440-mineral-light.png) | [1024](overview-1024-mineral-light.png) | [390](overview-390-mineral-light.png) |
| Mineral Dark | [1440](overview-1440-mineral-dark.png) | [1024](overview-1024-mineral-dark.png) | [390](overview-390-mineral-dark.png) |

Scrolled mobile details: [Places preview](places-preview-390-botanical-light.png),
[Site preview](sites-preview-390-botanical-light.png),
[Overview record access](overview-records-390-botanical-light.png).

All ordinary captures use the existing authenticated synthetic review fixture: two identities,
two provenance sites (one coordinate-less), retained historical material and one explicitly synthetic
structured native-range assertion. This is UI evidence, not a botanical claim. No external taxon IDs,
photos or occurrence observations were invented. The occurrence workspace truthfully shows an
unlinked identity; its full provider/cache behavior is also covered by affected regression tests.
The Overview mounts no map engine and labels unknown occurrence totals **Not checked here**.
Direct-record coverage is explicitly **at mapped sites**, not all material or physical quantities.

Origins/Site map regional captures use the existing Fit and Zoom out controls after marker loading
and zoom animations complete. Automatic single-site fitting remains unchanged (zoom 12); the regional
evidence uses zoom 5 to show local generalized Natural Earth context. Online imagery remains off.
These are viewport emulations, not browser zoom or physical-device checks.

All 126 initial presentation checks have one Geography content heading, one six-link navigation,
no Maps subgroup, visible active destinations, and no page or checked-container horizontal overflow.
The completed matrix records zero page errors and zero attempted third-party requests.

## Compatibility and interactions

[Interaction report](interactions.json) records real authenticated browser checks:

- Legacy and canonical Native ranges, Species distribution and Collection origins entries preserve
  exact identity/search/filter query strings through reload.
- Origins category filters and same-view Back/Forward restore visible search state; the reproduced
  stale-search defect now has a stable reset callback and a focused regression.
- Overview's exact identity link opens the real Native SVG in species comparison mode.
- Ctrl-click is not intercepted and leaves selection unchanged; independently opening its native
  canonical href mounts Origins. Headless shell does not create native browser tabs, so physical
  Ctrl-click tab creation remains a browser-level review limit.
- The occurrence workspace's existing exact Reference link and Back retain the selected identity
  without provider traffic. The botanical workstream's existing source-tab contract remains tested.
- Site map remains available locally, with List returning to the directory.
- Existing owner-private Geography v1 Saved View restoration retains the legacy management route.
- Mobile keyboard focus reveals Places from the scrolled navigation; More contains Geography and
  omits all three former global map entries.

Prior initial-phase browser evidence additionally preserves hierarchy selection/expansion, coordinate
precision, local/canonical restrictions, source record navigation, edit dialogs and focus return.
The shared framing change retains these implementations; current App/Site tests exercise them again.
The earlier gallery's labelled empty/error/1000-row doubles remain historical renderer evidence;
current Overview tests verify loading, independent failure/retry, empty state and session expiry.

New canonical routes use `#/geography/{native-ranges,species-distribution,origins,places,sites}`.
Bare Geography opens Overview. Old `#/native-ranges`, `#/species-distribution`, `#/map`, management
queries and exact site URLs remain render aliases without redirects. Queries and unknown parameters
are retained; v1 Saved View schemas and stored paths are unchanged. See the handoff route table.

Read-only audit of botanical-identity branch `859028a` confirmed IdentityMaps' exact old map links
remain valid. IA-NAV must reconcile the explicitly approved localized Maps removal in App and the
small shared directory-state alias adapter. No other worktree was edited.

## Verification and stopping boundary

- Baseline: **51 passed in 2 files** before refinement.
- Final focused selection: **225 passed in 15 files**, no failures/skips. See
  [portable test report](test-results.json). Covers App/lazy/transition, unified route and state
  regression, overview, all three existing map screens, Site manager, Saved Views and occurrence
  panel/density/tile cache and privacy regressions.
- Strict TypeScript, full zero-warning ESLint, full frontend formatting and production build are
  recorded in [static verification](verification.json).
- Feature graph: **112 valid**. Whitespace and empty-index checks passed.
- [Image dimensions](image-dimensions.json) independently verifies every curated PNG against its
  manifest and requested viewport.

No backend, API, schema, dependency, renderer or provider contract changed. Backend/integration,
API regeneration and canonical FULL verification were not run in this review phase. Operator
acceptance, true zoom, actual screen-reader/touch-device use, real large-collection performance,
native tab creation and live-provider availability remain unclaimed. Coordinate-less site APIs
still lack exact linked-record IDs; that limitation is explicit rather than replaced by guesses.

All changes remain unstaged/uncommitted. No receipt, push, PR, protected delivery or cleanup action.

GEOGRAPHY_UNIFIED_NAVIGATION_REVIEW_READY
