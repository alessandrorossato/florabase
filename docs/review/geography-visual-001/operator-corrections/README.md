# Geography operator corrections — final review evidence

[Open review](http://localhost:15276/#/geography/overview) ·
[Current handoff](../../../geography-visual-001-handoff.md) ·
[Shared breadcrumb audit and follow-up](../../../geography-breadcrumb-audit.md).

Source `/home/alessandro/.codex/worktrees/5430/florabase`, `feat/geography-visual-001`, base `e7ade78`.
Latest inspected main `5778da7` includes Botanical Identities #121 and is integrated into this
candidate. The overlap preserves both Collection/Saved View implementations.
No IA-NAV design worktree or protected environment was edited.

## Before and after

The operator decisions supersede previous passing layouts. Earlier review evidence is preserved.
Counts in historical references reflect their capture's retained data, not a fabricated comparison.

| Correction | Before/reference | Current after |
| --- | --- | --- |
| Restore balanced three cards | [Accepted three-card reference](../refinement/overview-1440-botanical-light.png), [rejected flat rows](../final-ux/overview-1440-botanical-light.png) | [Restored Overview](overview-1440-botanical-light.png) |
| Remove tabs everywhere | [Native ranges with tabs](../final-ux/native-1440-botanical-light.png) | [Full Native ranges, breadcrumb return](native-1440-botanical-light.png) |
| Rounded Places and chevrons | [Rectangular rows](../final-ux/places-1440-botanical-light.png) | [Expanded hierarchy and preview](places-1440-botanical-light.png), [selected row and focus](places-selection-focus-1440.png) |
| LEFT list/inspector, RIGHT edge map | [Map in the middle](../final-ux/sites-mapped-1440-botanical-light.png) | [Two-column mapped selection](sites-mapped-1440-botanical-light.png), [coordinate-less selection](sites-unmapped-1440-botanical-light.png) |
| Mobile selection | [Previous mobile](../final-ux/site-map-390-botanical-light.png) | [List/details](sites-unmapped-details-390-botanical-light.png), [Map presentation](site-map-390-botanical-light.png) |
| Shared breadcrumbs outside Geography | [Seeds reference from delivered main #121](before-seeds-main-5778da7.jpg) | [Collection / Seeds](breadcrumb-seeds-1440.png), [named SeedLot](breadcrumb-seedlot-detail-1440.png), [Sourcing / Orders](breadcrumb-orders-1440.png), [identity detail](breadcrumb-identity-detail-1440.png) |
| Standard desktop fit | [Three-pane layout](../final-ux/sites-mapped-1440-botanical-light.png) | [Map and inspector together](sites-mapped-1440-botanical-light.png) |

The imported before-Seeds JPEG is a provenance-labelled Git blob from main `5778da7`, with that
workstream's fixture. It is not represented as a same-database before screenshot.

## Current viewport and theme matrix

[Machine-readable matrix](browser-matrix.json): **162 Geography checks** (nine presentations × three
sizes × six palette/mode combinations), plus **56 global breadcrumb checks** (18 root destinations
at all three sizes plus two named details). **84 ordinary captures** are curated from those checks, with three additional deep-selection/focus
captures. Two labelled large-list doubles make **89 current PNGs**. The separate before JPEG is not a
new candidate capture. [Independent image dimensions](image-dimensions.json) verifies every file.

| Botanical Light | 1440×844 | 1024×844 | 390×844 |
| --- | --- | --- | --- |
| Three-card Overview | [Desktop](overview-1440-botanical-light.png) | [Tablet](overview-1024-botanical-light.png) | [Mobile](overview-390-botanical-light.png) |
| Native ranges | [Desktop](native-1440-botanical-light.png) | [Tablet](native-1024-botanical-light.png) | [Mobile](native-390-botanical-light.png) |
| Species distribution | [Desktop](distribution-1440-botanical-light.png) | [Tablet](distribution-1024-botanical-light.png) | [Mobile](distribution-390-botanical-light.png) |
| Collection origins | [Desktop](origins-1440-botanical-light.png) | [Tablet](origins-1024-botanical-light.png) | [Mobile](origins-390-botanical-light.png) |
| Rounded Places / chevrons | [Desktop](places-1440-botanical-light.png) | [Tablet](places-1024-botanical-light.png) | [Mobile](places-390-botanical-light.png) |
| Mapped site selection | [Desktop](sites-mapped-1440-botanical-light.png) | [Tablet](sites-mapped-1024-botanical-light.png) | [Mobile](sites-mapped-390-botanical-light.png) |
| Coordinate-less site | [Desktop](sites-unmapped-1440-botanical-light.png) | [Tablet](sites-unmapped-1024-botanical-light.png) | [Mobile](sites-unmapped-390-botanical-light.png) |
| Same sites, Map presentation | [Desktop](site-map-1440-botanical-light.png) | [Tablet](site-map-1024-botanical-light.png) | [Mobile](site-map-390-botanical-light.png) |
| Preserved New local place | [Desktop](new-place-1440-botanical-light.png) | [Tablet](new-place-1024-botanical-light.png) | [Mobile](new-place-390-botanical-light.png) |

| Other appearances | Overview | Rounded Places | Right-edge map | Mobile Map |
| --- | --- | --- | --- | --- |
| Botanical Dark | [View](overview-1440-botanical-dark.png) | [View](places-1440-botanical-dark.png) | [View](sites-mapped-1440-botanical-dark.png) | [View](site-map-390-botanical-dark.png) |
| Herbarium Light | [View](overview-1440-herbarium-light.png) | [View](places-1440-herbarium-light.png) | [View](sites-mapped-1440-herbarium-light.png) | [View](site-map-390-herbarium-light.png) |
| Herbarium Dark | [View](overview-1440-herbarium-dark.png) | [View](places-1440-herbarium-dark.png) | [View](sites-mapped-1440-herbarium-dark.png) | [View](site-map-390-herbarium-dark.png) |
| Mineral Light | [View](overview-1440-mineral-light.png) | [View](places-1440-mineral-light.png) | [View](sites-mapped-1440-mineral-light.png) | [View](site-map-390-mineral-light.png) |
| Mineral Dark | [View](overview-1440-mineral-dark.png) | [View](places-1440-mineral-dark.png) | [View](sites-mapped-1440-mineral-dark.png) | [View](site-map-390-mineral-dark.png) |

The JSON enumerates all captures, including global roots, named details and scrolled mobile panels.
Assertions verify absent Geography tabs and Maps group, one content heading, correct breadcrumb,
equal desktop/tablet card heights, right-edge map geometry and no document/checked horizontal
overflow. Overview mounts no engine. Cold entry explicitly checks that card styling loads without
visiting management first. Completed runs have zero page errors and attempted external requests.

## What fits and what scrolls

The fit report is in [interactions](interactions.json). At 1440×844, the site map and LEFT rail occupy
y=233–837; at 1024×844 they occupy y=273–829. Breadcrumb, title/actions, search, list, usable map and
selected primary inspector are visible together without document scrolling. Map typography and
controls retain normal sizes. Card heights match within one pixel on desktop/tablet.

The deliberately long mapped-site fixture needs intentional panel scrolling: desktop list
176px visible/241px content and inspector 362px/413px; tablet list 176px/303px and inspector 314px/525px.
Deep Place selections can require intentional tree-panel scrolling; [selection/focus proof](selection-proof.json)
and [desktop](places-selection-focus-1440.png), [tablet](places-selection-focus-1024.png),
[mobile](places-selection-focus-390.png) captures show the selected row and distinct focus.
The inspector is natively keyboard focusable, with a distinct focus ring and Edit/detail actions
above metadata. Long lists retain focusable row controls and scrollbars. A complete long inspector
is not claimed to fit without scrolling. Mobile uses a bounded list followed by complete inspector
in document flow; Map presentation preserves selection. See the scrolled
[mapped inspector](sites-mapped-details-390-botanical-light.png),
[coordinate-less inspector](sites-unmapped-details-390-botanical-light.png),
[Places preview](places-details-390-botanical-light.png) and
[record links](overview-details-390-botanical-light.png).

## Interactions and data boundaries

[Six completed browser groups](interactions.json) verify:

- Overview cards mount real maps and breadcrumbs return to the hub; exact legacy identity/query,
  Back and reload are preserved without tabs.
- Rounded tree rows retain independent chevron disclosure/selection, canonical context and clean/
  dirty New local place safety with actual-trigger focus return. The draft is discarded, not saved.
- Left list/right map/inspector synchronize both ways. Coordinate-less records retain Edit without
  a fabricated marker. The overflow inspector accepts keyboard focus.
- Mobile List/Map keeps the same selected record and inspector; geometry/scroll extents are recorded.
- Shared Sourcing breadcrumb has no fake Dashboard parent link.
- [Desktop 1000-site renderer](large-sites-renderer-double-1440.png) and
  [mobile renderer](large-sites-renderer-double-390.png) are explicitly browser-only response doubles:
  ten coordinate-bearing markers, 990 coordinate-less rows, exact search and bounded list scrolling.
  Nothing is persisted; this is not a real backend performance claim.

Ordinary images use retained authenticated synthetic review data. No record, taxon link or provider
observation was fabricated. Unknown occurrences stay unknown. Local regional map captures use the
existing Fit/Zoom out controls; engines, accuracy, explicit online opt-in and privacy are unchanged.
The browser prefers reduced motion. Screen emulation is not a physical-device, screen-reader or true
browser zoom check. No live GBIF download or online imagery opt-in was invoked.

## Verification and stopping point

[Verification record](verification.json) and [portable frontend totals](test-results.json) contain
completed command results. **Full frontend: 919 tests/79 files passed**, with 47 repeated focused
confirmations after lint-only cleanup. Baseline: 17 tests in three files. The full frontend suite was selected
because breadcrumb/PageHeader changes reach Collection, Activity, Explore, Sourcing and Tools;
focused regressions cover shared group/record paths and the new Geography navigation/layout.

Those files record the Geography visual pass before PR #121 integration. The integrated branch then
passed **356 focused tests in 12 files**, including App, Geography, Identity maps and deep links,
identity-scoped Saved Views, and SeedLot/Sowing/Plant routes. Its feature graph validates **113** entries.
The canonical receipt will cover the final merged tree.

TypeScript, ESLint, formatting, feature graph and production build are reported exactly. Backend/
integration, schema/API regeneration and canonical FULL were not run: this increment changes only UI
and docs. Earlier interrupted/edit-invalidated runs are not counted as final passing evidence.

The [breadcrumb audit](../../../geography-breadcrumb-audit.md) identifies contextual task/module
follow-ups and main #121 reconciliation before delivery. Sidebar ownership is unchanged; Geography
remains the single geographic entry. No other worktree or protected dataset was modified.
The operator has approved the current implementation for a local commit. Independent QA and the
canonical gate remain pending; this feature handoff does not include a push, PR or merge.

GEOGRAPHY_COMMITTED_READY_FOR_QA
