# UI System v1 consolidation — operator UAT

**Current contract:** [Final interaction correction](final-interaction-correction/README.md)
supersedes earlier Preview and action-menu decisions. Direct Details/Edit, creation-only menus,
textual semantic statuses and full-width directories await final operator UAT. Earlier galleries
below are historical evidence of their named checkpoints, not proof of the current interaction contract.

31 October 2026. Candidate awaiting operator acceptance; no canonical FULL or delivery.
This specification supersedes earlier page-specific Wave 3 layout refinements.

## Source and ownership

Work remains in `548f`, branch `feat/ui-system-v1-wave3`, on
`4b8c038f2373c37c5645125b22c06f019698b66b`, with the existing uncommitted implementation
preserved. Independent QA `9d31` is clean at `d09fd86118ecc9a17a9aef27e099d8a182ae073d`
and is already an ancestor. Schedule reconciliation is retained. The local and remotely
checked main reference is `fbce3c4cfad26bdfa3297d53a1e65a7ec6a0ad65`; no integration or
history rewrite was needed.

Review: <http://localhost:15174>. Ownership and health identify this exact worktree;
frontend/backend/database are healthy, database/code head `20261013_0042`, fixture v4 ready
(80 managed baseline records). Source mounts reflect dirty changes live. Existing extended
fixtures and operator edits were retained. Credentials were entered interactively and were
not read or recorded. DEV, UAT, foreign worktrees and Docker resources were not modified.

## Page families

| Family                      | Implemented pages                                                                                                                                                               | Common contract                                                                                           | Intentional distinction                                                                          |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| A — Record directories      | Seeds, Sowings, Plants/PlantGroups, Harvests, Stored material, Suppliers, Orders, Botanical identities                                                                          | Page identity, tools, filters, result/pagination lane, row/card slots, actions, nonmodal inspector        | Domain summaries, eligibility and mutations remain page-owned                                    |
| A — Asset directory variant | Media                                                                                                                                                                           | Existing PageHeader, DirectoryTools, selection/action and semantic-token vocabulary                       | Asset grid/viewer and media editing are preserved; a physical-record row is inappropriate        |
| B — Hierarchical explorers  | Locations, Geography Places                                                                                                                                                     | Recursive branch spacing/indentation, chevrons, selected branch, focus and responsive inspector placement | Location scopes/direct-inclusive counts/protected parents; canonical/local Geography permissions |
| C — Activity workspaces     | Journal, History, Schedule                                                                                                                                                      | Existing ActivityPage/PageHeader, tools, actions and dialogs                                              | Recording, factual chronology and date-based planning remain distinct                            |
| D — Specialized workspaces  | Taxonomy Tree Explorer, Maps, Geography overview/native ranges/distribution/origins, provenance map/site hybrid, Dashboard, labels/QR, import/export/enrichment tools, Settings | Appropriate existing page/dialog/control primitives                                                       | Tree, map, overview, transfer and configuration interactions remain specialized                  |

## Canonical directory layout

1. Breadcrumb, title and concise subtitle.
2. Peer tabs, when the page has peer directories.
3. Search, optional List/Gallery switch, supported filters, Saved Views and primary action.
4. Active-filter lane with stable space on Collection pages.
5. Results, matching/global totals, range, page size, previous/next and selection controls.
6. Record scrollport and optional persistent inspector.

Harvests and Stored material now place their independent tools below their shared peer tabs.
Record harvest is available in both toolbars. Their filters and Saved Views remain separate.
Directories without filters or bulk selection do not reserve fictitious controls.

`DirectoryWorkspace`, in the existing `DirectoryPage` module, owns the common content grid.
The results lane spans both columns. Desktop uses `minmax(0, 1fr)` and an inspector constrained
to `clamp(18rem, 30%, 25rem)`. At 64rem and below the inspector stacks above records, bounded
to 25dvh with a usable minimum. Both panes start after pagination. Record lists scroll internally where viewport
space allows. One inspector content scrollport includes metadata and operations, preventing
large action footers from reducing the record content to zero height. Short/narrow screens
use natural page flow when retaining all chrome would make records unusable.

Normal directories no longer carry the legacy `*-master-detail`, `operational-layout` or
`reference-split` geometry classes. Full detail/create/edit compositions retain their existing
layout classes and domain safeguards. Existing semantic pane wrappers remain compatibility
hosts for page-owned forms; they do not select different directory proportions.

## Row, card, status and action contracts

`DirectoryRecordContent` has typed `visual`, `name`, `secondary`, `summary` and `status` slots:

`[3rem visual] [primary name/status + secondary metadata] [domain summary] [sibling actions]`

All eight directories use these slots. Names wrap without moving actions out of their area;
zero quantities remain present. Gallery stacks the same slots, uses one shared 12rem minimum
card width, stretches cards within a row and aligns actions at the bottom. Photos and compact
placeholders retain their intended treatments; image source captions do not create a footer
band. Preview photos use containment and remain truthful to their source.

`StatusBadge` is reused for compact semantic checks, accessible names and descriptions.
Only genuinely binary inactive states may use crosses. Rich terminal states retain precise
text: exhausted, completed, retired, reversed, failed, abandoned, depleted and unknown are
not rewritten as inactive. Preview/Details retain the full state. Harvests are historical
occurrences and Botanical identities have no invented lifecycle indicator.

The record button opens inspection. Sibling Details/Edit and eligible domain actions bypass
inspection; the redundant eye control is absent. Existing command buttons keep their route
ownership; native route links (including exact inventory and identity actions) retain modifier
navigation. Ctrl/Cmd-assisted existing bulk selection takes precedence over inspection.
Domain operations retain their existing guards and relationships.

`DirectoryInspector` provides nonmodal focus/Escape behavior and a shared idle placeholder.
The directory remains interactive. Initial focus goes to Close for an explicit Preview
request; programmatic identity selection after creation preserves creation-trigger focus.
Escape restores the current connected trigger or directory fallback, and nested dialogs own
Escape first. Tree explorers retain persistent selected-branch panels rather than introducing
record-directory dismissal semantics. Locations no longer navigates automatically at tablet
widths; Open details remains explicit, matching Geography selection.

## Compliance matrix

| Surface                          | Shared implementation                                                                  | Preserved domain behavior                                                                                  | Evidence                                                                    |
| -------------------------------- | -------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Seeds                            | Workspace, typed row/card, compact Active, common pagination/actions/inspector         | Quantity precision/unknown stock, lifecycle, Start sowing, bulk eligibility                                | `seeds-*`, `seeds-photo-preview-*`, `seeds-page-two-*`, `seeds-selection-*` |
| Sowings                          | Same workspace/slots, icon operations, common gallery and inspector                    | Germination, quantities, lifecycle, source lineage, Plant creation and reversal guards                     | `sowings-*`, `sowings-rich-lifecycle-*`                                     |
| Plants/PlantGroups               | Same row/card and inspector composition                                                | Individual/group distinction, tracking quantities, lineage, harvest operations                             | `plants-*`, `plants-photo-preview-*`                                        |
| Harvests                         | Historical row now uses the same slots, typography and actions                         | Occurrence-date precision, material aggregation, source links, owned Event and deletion guards             | `harvests-*`                                                                |
| Stored material                  | Compact slots, bounded path summary, row-click preview, direct exact-inventory Details | Unknown/approximate quantities, depleted state, storage, disposition, seed conversion, labels              | `stored-material-*`, interaction smoke exact `inventory` URL                |
| Suppliers                        | Same row/metadata/actions; parallel Sourcing CSS removed                               | Kind, direct-record counts, retained retired state, contextual maintenance and associations                | `suppliers-*`                                                               |
| Orders                           | Same row/summary/actions, same workspace geometry                                      | Supplier/date/price unknowns, amount/currency, related packets, server pagination and All-page aggregation | `orders-*`                                                                  |
| Botanical identities             | Same row slots, pagination and nonmodal inspector at every width                       | Scientific typography, collection counts, Details/Edit and four association/creation operations            | `identities-*`                                                              |
| Locations/Geography Places       | Shared `hierarchy.css`, same responsive panel and branch grammar                       | Direct/inclusive counts, scopes, canonical/local permissions, parent protections                           | `locations-*`, `geography-places-*`, two new Location width regressions     |
| Media/Activity/specialized pages | Existing compatible primitives retained                                                | Specialized viewer/calendar/map/tree and operational flows                                                 | Complete frontend cross-consumer regression; intentional exceptions above   |

## Shared impact and removed duplication

- Extended the existing `DirectoryPage` module with `DirectoryWorkspace`,
  `DirectoryRecordContent` and `DirectoryInspectorPlaceholder`; no competing design system.
- Reused `DirectoryRecords`, Row/Card/Trigger/Actions, DirectoryTools, DirectoryResults,
  RecordVisual, StatusBadge and existing dialogs. Domain data/API/filter/save ownership did
  not move into the shared framework.
- Replaced four independent local-pagination state/calculation copies in Suppliers,
  Botanical identities, Harvests and Stored material with `useDirectoryPagination`.
  Orders retains its actual server-pagination implementation, including fetching all pages.
- Deleted `styles/sourcing-directory.css` and `sowings/directory.css`; their geometry,
  row content and gallery/action overrides are now shared.
- Removed obsolete qualified layout/row rules from shared directory and Harvest styling,
  plus duplicate Geography chevron/row presentation. Identity actions and split geometry
  now use the common directory contract. Detail/editor styles remain scoped to their domain compositions.
- `styles/directory-system.css` is the common Family A geometry/slot contract;
  `components/hierarchy.css` is the Family B presentation contract.

## Verification and visual evidence

[Evidence gallery](evidence/index.html), [capture matrix](evidence/matrix.json),
[interaction smoke](evidence/interaction-smoke.json),
[scroll persistence](evidence/scroll-smoke.json),
[mobile inspector reachability](evidence/mobile-inspector-scroll.json).

The complete frontend regression passed **1097/1097 in 100 files** after consolidation and
Location width coverage. The final Harvest/Stored peer adjustment passed **171/171** in
HarvestScreen, StoredMaterial, Conversion and App. Final identity/style/static results are
recorded in [verification.txt](verification.txt) and the progress milestone. Final cross-consumer
regression after the mobile inspector and Stored Active corrections passed **397/397 in 13 files**;
TypeScript, full frontend ESLint, Prettier and production build pass. No canonical FULL was run.

The **95 unique captures** cover all eight directories in six themes at 1440px; List and all five supported
galleries at 1440/1024/390 in Mineral Dark; Locations/Geography at the same three widths;
photo previews, richer lifecycle, multiple pages, All/selection, inspector persistence and
720×450 short-viewport stress. This is a paired coverage strategy, not the full Cartesian
product of every theme, width and state. Matrix measurements record document overflow and,
for 79 directory comparisons, overlapping record/inspector bounds. All recorded overflow and
overlap checks are false. Capture widths describe the configured CSS viewport; raster dimensions
are recorded separately because the browser can normalize screenshots around scrollbars.

The first visual comparison found legacy flex bases expanding headers vertically and legacy
row assignments overlapping tablet inspectors. Both were corrected before final captures. The final mobile comparison also exposed a zero-height
Stored inspector body: a shrinking grid track combined with legacy hidden-metadata rules. The
shared minimum track and narrow-page flow now retain scrollable metadata and operations;
all affected tablet/mobile and reduced-height captures were refreshed. Live mobile scrolling
reached 318px in a 147px content pane and exposed the direct inventory Details action.
The initial full test pass also identified one real focus regression after identity creation;
`focusOnOpen` now preserves the creation trigger. Other changed expectations concern explicitly
approved compact statuses, stable placeholders, native inventory Details and retired CSS classes.

Browser smoke confirms record Preview/Escape/focus return and direct Details on all eight
directories. Seeds page two reads `21–40 of 40 records · 43 total`; All renders 40 active rows.
Scrolling its record list from 0 to 920.5px preserved the same inspector. No record mutation was
performed by these smoke journeys. Harvest deletion confirmation initially focused Cancel, and
Escape returned to More actions. An unsaved Seed label was not persisted. The integrated browser
did not expose a controllable native JavaScript confirmation, so rejecting dirty-draft dismissal
is covered by automated regressions and remains an explicit manual UAT check.

Physical devices, screen readers, actual browser zoom, native touch/virtual-keyboard behavior,
native dirty-confirm rejection and full theme×width×state coverage remain manual UAT limitations. 720×450 simulates reduced
space; it does not certify browser zoom. Operator acceptance, independent final correctness
review and the policy-selected FULL gate are still required for protected delivery.

## Operator UAT checklist

- Compare List rows across all eight directories: thumbnail/name/status, metadata, summary,
  direct actions, density, full-row selection and inspector alignment.
- Compare photo/no-photo and long-name cards in the five galleries; inspect both photo previews.
- Switch 20/50/100/All and Next/Previous; combine filters and Saved Views, verify matching/global
  totals, checked records and current-page bulk safety limits.
- Open another record while inspecting, scroll lists and inspectors independently, use Tab/Enter
  and Escape, and invoke direct Details/Edit and native modified links.
- Verify Seeds stock/Start sowing; Sowings germination/conversion/lineage; Plants/groups tracking;
  historical Harvests; exact inventory quantities/storage/disposition/conversion/labels;
  Supplier/Order relationships and unknown values; identity associations.
- Expand/collapse/select Locations and Geography at desktop/tablet/mobile; inspect direct and
  inclusive counts, scopes, protected parents and canonical/local operations; use explicit Details.
- Exercise dirty Escape/Cancel and destructive Cancel-first confirmation, including error/retry
  and pending safeguards, without accepting destructive changes merely for visual review.
- Review six themes, 1440/1024/390, actual zoom, physical touch devices and assistive technology.

No push, PR, main merge, feature-finish, resource deletion or delivery commit has been performed.
