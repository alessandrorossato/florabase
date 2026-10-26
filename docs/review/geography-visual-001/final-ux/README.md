# Geography final UX review

Historical evidence. [Operator corrections](../operator-corrections/README.md) supersede the flat
Overview, persistent tabs, rectangular Places and middle-map layout.
[This phase's handoff](handoff.md) is preserved.

[Open isolated review](http://localhost:15276/#/geography/overview) ·
[Current handoff](../../../geography-visual-001-handoff.md).
Source: `/home/alessandro/.codex/worktrees/5430/florabase`, `feat/geography-visual-001`.
Base and freshly fetched `origin/main`: `e7ade78559803a35b738a669085799f55eb76258`.
The accepted six-view IA and single global Geography entry are preserved.

## Final composition

Shared Florabase Breadcrumbs precede the Geography heading and existing six-view navigation.
Explore is a group label: the router has no Explore landing page to invent a link to. Geography
links through the same typed canonical route helper as the internal navigation. The final item
identifies the current view, including supported legacy map entry points.

Overview uses three compact divider-led evidence rows and simple record links. There are no large
cards, decorative imagery or map engines on Overview. Counts come from the existing local APIs;
unknown occurrence totals stay **Not checked here**. Record counts at mapped sites remain qualified,
not material quantities or invented completeness scores. Loading, independent failure/retry, empty
states, exact record links and session expiry remain tested.

Places retain recursive hierarchy with capped indentation, separate labelled expand and select
controls, the existing leading selected accent and a compact contextual preview. Canonical/local
status, ancestry, direct parent, create-child action, exact associated sites and authoritative counts
remain. Canonical names/ancestry stay read-only.

Provenance sites share one list, map and inspector with a single selected ID. Desktop shows three
panes simultaneously; tablet places the inspector below list/map; mobile List/Site map changes the
presentation of the same DOM and selection. Both presentations retain coordinate-less rows and
Edit. Only actual coordinate pairs become markers. Coordinates, recorded accuracy, usage counts,
notes and existing detail/source links retain their API semantics. There is no site subtype field
to fabricate. Management remains distinct from Collection origins analysis.

## Screenshots and viewport matrix

[Matrix](browser-matrix.json): **162 checks**, nine presentations × three sizes × six appearances.
The nine presentations include all six views, mapped and coordinate-less site selection, narrow
Site map and contextual New local place. **69 curated exact-viewport captures** plus two explicitly
labelled large-result doubles make **71 screenshots**. [Dimension report](image-dimensions.json)
independently verifies PNG sizes. Ordinary captures use existing authenticated synthetic review
records; values reflect the current database, including any operator edits since earlier reviews.
No record, taxon link or provider evidence was created to manufacture a screenshot.

| Botanical Light | 1440×844 | 1024×844 | 390×844 |
| --- | --- | --- | --- |
| Compact Overview and breadcrumb | [Desktop](overview-1440-botanical-light.png) | [Tablet](overview-1024-botanical-light.png) | [Mobile](overview-390-botanical-light.png) |
| Native ranges | [Desktop](native-1440-botanical-light.png) | [Tablet](native-1024-botanical-light.png) | [Mobile](native-390-botanical-light.png) |
| Species distribution | [Desktop](distribution-1440-botanical-light.png) | [Tablet](distribution-1024-botanical-light.png) | [Mobile](distribution-390-botanical-light.png) |
| Collection origins | [Desktop](origins-1440-botanical-light.png) | [Tablet](origins-1024-botanical-light.png) | [Mobile](origins-390-botanical-light.png) |
| Expanded Places and preview | [Desktop](places-1440-botanical-light.png) | [Tablet](places-1024-botanical-light.png) | [Mobile](places-390-botanical-light.png) |
| Unified sites, mapped selection | [Desktop](sites-mapped-1440-botanical-light.png) | [Tablet](sites-mapped-1024-botanical-light.png) | [Mobile](sites-mapped-390-botanical-light.png) |
| Coordinate-less selection | [Desktop](sites-unmapped-1440-botanical-light.png) | [Tablet](sites-unmapped-1024-botanical-light.png) | [Mobile](sites-unmapped-390-botanical-light.png) |
| Same sites, Map presentation | [Desktop](site-map-1440-botanical-light.png) | [Tablet](site-map-1024-botanical-light.png) | [Mobile](site-map-390-botanical-light.png) |
| Contextual New local place dialog | [Desktop](new-place-1440-botanical-light.png) | [Tablet](new-place-1024-botanical-light.png) | [Mobile](new-place-390-botanical-light.png) |

| Other appearances | Desktop Overview | Tablet Overview | Mobile Overview | Selected site |
| --- | --- | --- | --- | --- |
| Botanical Dark | [1440](overview-1440-botanical-dark.png) | [1024](overview-1024-botanical-dark.png) | [390](overview-390-botanical-dark.png) | [Mapped](sites-mapped-1440-botanical-dark.png) |
| Herbarium Light | [1440](overview-1440-herbarium-light.png) | [1024](overview-1024-herbarium-light.png) | [390](overview-390-herbarium-light.png) | [Coordinate-less](sites-unmapped-1440-herbarium-light.png) |
| Herbarium Dark | [1440](overview-1440-herbarium-dark.png) | [1024](overview-1024-herbarium-dark.png) | [390](overview-390-herbarium-dark.png) | [Mapped](sites-mapped-1440-herbarium-dark.png) |
| Mineral Light | [1440](overview-1440-mineral-light.png) | [1024](overview-1024-mineral-light.png) | [390](overview-390-mineral-light.png) | [Coordinate-less](sites-unmapped-1440-mineral-light.png) |
| Mineral Dark | [1440](overview-1440-mineral-dark.png) | [1024](overview-1024-mineral-dark.png) | [390](overview-390-mineral-dark.png) | [Mapped](sites-mapped-1440-mineral-dark.png) |

Scrolled mobile views retain 390×844:
[Places preview](places-details-390-botanical-light.png),
[mapped inspector](sites-mapped-details-390-botanical-light.png),
[coordinate-less inspector](sites-unmapped-details-390-botanical-light.png),
[record access](overview-details-390-botanical-light.png).
The manifest also lists mobile Site map/dialog and dark Native captures across all palettes.

Matrix assertions cover one Geography content heading, one six-link internal navigation, current
breadcrumb, absent Maps subgroup, visible active navigation and no document/checked-container
horizontal overflow. The completed run records no page errors or attempted external requests.
The browser prefers reduced motion. Regional Origins/site captures use existing Fit/Zoom out
controls; map engines and automatic single-site fitting are unchanged. Captures are browser
emulation, not physical-device, real browser zoom or live-provider evidence.

## Dialog and selection checks

[Interaction report](interactions.json), **7 completed browser groups**:

- Capped Place hierarchy preserves separate expansion and selection, canonical preview and parent context.
- Clean contextual creation retains inside clicks, traps keyboard focus and dismisses on backdrop,
  returning to the actual Create local child control. Its preset parent is a clean baseline.
- Dirty name/type/parent changes use the established native discard confirmation. Real backdrop,
  Escape and Cancel checks retain fields when declined and restore focus after accepted dismissal.
  No review record is submitted. Unit regressions also block every dismissal while a request is pending.
- List selection highlights the same real marker and inspector; marker activation selects the row.
  Coordinate-less selection clears marker highlight, remains inspectable and opens its existing editor.
- Mobile List/Map changes presentation without remounting or losing coordinate-less selection.
- Breadcrumb navigation from an exact legacy Native identity preserves Back/Forward, reload and
  unknown query parameters.
- [1000-site desktop](large-sites-renderer-double-1440.png) and
  [1000-site mobile](large-sites-renderer-double-390.png) are explicitly **browser-only response
  doubles**: ten coordinate-bearing double markers, 990 coordinate-less rows, exact search and
  bounded list scrolling. No rows are persisted and no real backend scale/performance claim is made.

All completed interaction groups report zero page errors and third-party requests.

## Verification and stopping boundary

See [portable test totals](test-results.json) and [verification](verification.json).
Baseline: **17 passed/3 files**. Final affected selection: **231 unique tests passed/15 files**, no failures/skips in the retained
passing results; totals consolidate the completed focused runs.
It includes App/lazy/transition, all three real map screens, canonical and legacy state, shared
breadcrumbs, Overview, Place workflows, clean/dirty/pending dialog dismissal, synchronized site
selection, coordinate-less sites, Saved Views and occurrence/cache/privacy/tile regressions.

TypeScript, full zero-warning ESLint, full frontend formatting and production build are recorded
in the verification report. Feature graph: **112 valid**. Whitespace and empty-index checks passed.
A temporary thread-based single-worker run reduces process overhead under host memory pressure;
no assertions or global timeouts were weakened. The shared test helper waits for actual cold
Geography imports using the existing lazy-workspace query convention. Interrupted workers/captures, an obsolete eyebrow assertion and a cold StrictMode import wait
are superseded by completed focused results, not counted as passes.

No backend/API/schema/dependency change, canonical FULL gate, staging, commit, push, PR, merge or
feature-finish. No other environment or worktree was modified. Protected-review runtime data is
preserved; this candidate-owned runtime remains on loopback 15276/18276. Physical touch, actual
screen-reader use, true zoom, live GBIF/online imagery availability and real-large-collection
performance remain deferred. Coordinate-less exact source-record links remain an explicit API gap.

GEOGRAPHY_FINAL_UX_REVIEW_READY
