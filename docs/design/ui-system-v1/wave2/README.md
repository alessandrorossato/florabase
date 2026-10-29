# UI System v1 — Wave 2: Activity + Sourcing

Base: `afcfbab334622d64cca2cdb2ea4c8f6a51ad957f` (PR #129), verified against freshly fetched
`origin/main` on 29 October 2026. Primary `main` was clean and synchronized. Canonical
`make feature-start BRANCH=feat/ui-system-v1-wave2` attached the existing isolated Codex worktree.

## Approval and independent QA status — 29 October 2026

The operator completed and **PASSED all six UAT scenarios** below and approved this exact Activity
and Sourcing candidate. The UI/UX scope is frozen. No further operator UAT or design reconsideration
is required unless independent QA finds a genuine blocking defect. The operator explicitly authorized
this local implementation commit before independent QA and canonical FULL; this supersedes the usual
commit ordering for this handoff only. The feature remains `implemented`, not `verified`.

The [independent QA handoff](independent-qa.md) records source identity, the PR #130 reconciliation
boundary, retained evidence and the one remaining canonical FULL gate. This task does not push,
create a PR, merge, run feature-finish, or change any environment.

## Compliance matrix before implementation

| Surface                      | Classification                                       | Actual difference / bounded adaptation                                                                                                                                                                                                                                                            |
| ---------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Journal                      | Needs shared-component adaptation                    | PageHeader, search, source-aware EventFeed, Record menu, house dialogs and Saved Views already comply. Replace duplicated Activity filter drawer/chips with DirectoryTools and compose through ActivityPage.                                                                                      |
| History                      | Needs shared-component adaptation                    | Read-only chronological facts, recorded/occurrence dates, precision, source links and paging already comply. Same shared Activity composition/filter adaptation; no sorting or history-semantic change.                                                                                           |
| Schedule List                | Needs shared-component adaptation                    | Existing target eligibility, grouped work rows, status transitions and guarded activity dialog comply. Share Activity composition and DirectoryTools, preserving immediate filters and target-clear semantics.                                                                                    |
| Schedule Calendar            | Genuine exception within shared Activity composition | Retain calendar-owned List/Calendar URL, month/date controls, day selection, overflow drawer and mobile agenda. No directory List/Gallery preference or Saved Views.                                                                                                                              |
| Suppliers directory          | Needs shared-component adaptation                    | Existing search-only DirectoryTools, Saved Views and truthful counts comply. Replace reserved empty preview column and row-only action with shared directory rows/cards, explicit Preview/Details/Edit, responsive overlay and List/Gallery presentation. No invented filters or bulk operations. |
| Orders directory             | Needs shared-component adaptation                    | Existing DirectoryTools, Supplier picker/filter, Saved Views, unknown/partial dates/prices and paging comply. Apply the same directory/overlay/presentation grammar while retaining exact transaction/physical-packet relationships.                                                              |
| Sourcing Details/Create/Edit | Already compliant                                    | Retain full-width detail/create, contextual EditWorkspace and direct editor fallback, independent validation, reconciliation, photo ownership and deletion/retirement safety.                                                                                                                     |

## Implementation batches

1. Activity: shared filters/composition; preserve all capability-owned state and controls.
2. Sourcing: shared List/Gallery, explicit record actions and overlay previews; keep forms/details.
3. Focused regressions, responsive/six-theme live Review, CI-004 impact plan and operator UAT handoff.

The original implementation handoff below records the pre-acceptance evidence. Operator acceptance
is now complete as recorded above; independent QA, reconciliation and canonical FULL remain pending.

## Delivered candidate

- ActivityPage now accepts the existing capability class and composes Journal, History and Schedule.
  ActivityPageHeader delegates search, filter drawer, dimension counts, chips, Saved Views and actions
  to DirectoryTools. The canonical filter state and Clear filters action remain capability-owned.
  Removed the duplicated Activity drawer and toolbar CSS. Chronology and calendar rendering are retained.
- Suppliers and Orders use DirectoryPage, DirectoryRecords, DirectoryRow/Card,
  DirectoryViewSwitcher, DirectoryRecordActions and DirectoryInspector. List is still the default;
  `view=list|gallery` uses the already-approved browser preference contract. A presentation change
  does not issue another domain request, reset search/Supplier scope/pagination, or enter Saved Views.
- Full-width directories replace the permanently reserved preview columns. The existing RecordPreview
  content opens in the close-first TaskDialog at every width. Three explicit record actions retain
  direct Details and contextual Edit; record names remain ordinary links. No bulk operation is added.
- Focus reconnects to the selected record after List/Gallery history remounts. Returning from contextual
  Edit restores its actual preview or row Edit action. Live mobile checks verified both Suppliers and
  Orders with the complete application router, including unchanged directory URL after Cancel.
- Existing Sourcing forms/details, Schedule activity dialogs and transition rules, history facts,
  Journal Record menu, target pickers and source/date semantics remain owned by their capabilities.
  No backend, schema, generated API, dependency, fixture implementation or unrelated product surface changed.

## Review and evidence

- **Application:** <http://localhost:15174/#/suppliers> (same Review also exposes Activity and Orders).
- **Evidence gallery:** <http://localhost:15285/>. The local gallery directory contains `captures.json`
  with source URLs, measured CSS dimensions, actual JPEG raster dimensions and SHA-256 digests.
- Source: `/home/alessandro/.codex/worktrees/bf7a/florabase`, branch
  `feat/ui-system-v1-wave2`, base `afcfbab334622d64cca2cdb2ea4c8f6a51ad957f`, approved implementation source; see the QA handoff for the committed identity.
  The environment's `review-status.txt` records exact source and healthy frontend/backend/database.
- Owner credentials are in the local owner-only `wave2-review-access.txt` beside the evidence directory,
  outside Git and outside the served gallery. This is a newly bootstrapped synthetic Review owner.
- Guarded canonical Feature Review project `florabase-feature-review`, database `florabase_review`,
  code/DB revision `20261013_0042`. Independent DB, media, dependency volumes and internal network;
  only frontend loopback port 15174 is published. DEV at 5173 and all foreign resources remain untouched.
- Explicit first-use v4 seed reports 80 baseline references; v5 reports 252 managed references,
  including 10 Suppliers, 12 Orders and 27 scheduled activities. Fixture extension and seeding use
  canonical guards, preserve edits and do not download botanical sources. No WCVP worktree was accessed.
- **154 settled captures:** all 144 primary combinations (Journal, History, Schedule List/Calendar,
  Suppliers List/Gallery, Orders List/Gallery × 1440/1024/390 CSS pixels × Botanical/Herbarium/Mineral
  Light/Dark) plus ten contextual captures: mobile Supplier/Order preview and contextual edit,
  mobile Journal filters/empty results, desktop Journal/History/Schedule drawers and calendar day drawer.
  All measured viewports are 844 CSS pixels high. JPEG raster dimensions are recorded independently.
- No primary capture has horizontal document overflow. Contact sheets for the three widths and
  contextual states were visually inspected. Six-theme contact sheets sample the same primary states.
  Earlier asynchronous resize captures and failed screenshot acquisitions were excluded and reacquired;
  only the final `wave2-evidence` gallery is acceptance evidence.
- Live read-only workflows also verified Journal immediate filtering/reset/empty results; keyboard
  Escape and preview focus return; pristine Supplier/Order edit cancellation and exact return route;
  calendar overflow/day drawer, November navigation and Today. No domain record was saved or deleted
  during browser review after isolated synthetic fixture initialization.

## Verification

| Check                                                            | Result                                                                                                                                     |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Untouched `main` archive baseline, five affected screen suites   | 97/97 passed                                                                                                                               |
| Final focused regression boundary, 12 existing test files        | 144/144 passed                                                                                                                             |
| Added Sourcing regressions                                       | Four new cases included above: canonical search/Supplier/pagination and history, remounted preview focus, row Edit and editor focus return |
| Complete frontend ESLint, zero warnings                          | Passed                                                                                                                                     |
| Strict frontend TypeScript (`tsc -b --pretty false`)             | Passed                                                                                                                                     |
| Complete frontend Prettier check                                 | Passed                                                                                                                                     |
| Production frontend Vite build, after strict typing              | Passed                                                                                                                                     |
| `make api-check`                                                 | Passed, no generated drift                                                                                                                 |
| `python3 scripts/check-features.py`                              | 120 valid features                                                                                                                         |
| `git diff --check`                                               | Passed                                                                                                                                     |
| Feature Review health                                            | Frontend/backend/database healthy; code and DB head match                                                                                  |
| CI-004 `make verification-plan`                                  | FULL: shared `components/ActivityPage.tsx` and `styles/sourcing-directory.css` are high-risk paths                                         |
| Canonical `make feature-verify`, integration and migration cycle | Pending independent QA and reconciliation with PR #130; operator visual acceptance has passed and one final FULL gate remains mandatory    |

The 12-file regression command covers GlobalEventsScreen, EventFeed, HistoryScreen, ScheduleScreen,
calendar projection, SupplierScreen, OrderScreen, OrderPicker, PurchaseContext, DirectoryPage,
DirectoryTools and SavedViews. Exact outputs are in the gallery's `baseline.txt`, `regressions.txt`,
`lint.txt`, `types.txt`, `format.txt`, `build.txt`, `api-check.txt` and `review-status.txt`.
The initial broad `make check` attempt did not complete: its format step read transient implementation
source while dependency bootstrap was finishing. It is not counted as a baseline or FULL pass.
Initial test/static failures were corrected and the final relevant checks above rerun successfully.

## Operator UAT

Use the synthetic Review, and use newly named UAT records for any mutations; retain seeded fixture
records so their guarded ledgers stay valid. Check the six themes through Settings → Appearance.

1. **Journal:** search real fixture excerpts, select multiple entry categories, remove chips, Reset
   filters while retaining search, Escape back to Filters, open a Saved View and follow a source link.
   Open Record and inspect the supported observation/action paths; cancel or use a new UAT record.
2. **History:** inspect occurrence versus recorded dates, year/month/unknown precision, primary and
   related record links; combine fact/record/year filters, clear a chip, restore a Saved View and use
   paging/Back/Forward. History remains read-only and never invents a lifecycle event.
3. **Schedule:** compare List and Calendar under the same query/status/target filters; navigate months,
   Today, selected dates, same-day overflow and the mobile agenda. Clear filters without losing period
   context. Inspect create/edit/complete/cancel and dirty dismissal. Completion with and without an
   explicitly linked Journal Event must retain their different meanings.
4. **Suppliers:** compare List/Gallery, reload and Back/Forward; search name/contact fields; open Preview,
   Escape, Details and row Edit. Cancel both pristine/dirty editors and verify focus. Review retired
   suppliers, usage counts, protected representative photos, exact linked acquisitions and creation.
   The directory intentionally has no unsupported Filters or bulk-selection controls.
5. **Orders:** retain Supplier scope, query and current page while toggling List/Gallery. Inspect exact,
   partial and unknown dates, known/unknown Supplier and price, independent physical seed-lot counts,
   preview and row Edit focus. Verify Saved Views exclude presentation. Inspect creation, paired
   price/currency validation, direct edit and purchase reconciliation with a new UAT Order/packet.
6. At desktop/tablet/mobile, inspect long supplier names, long notes, action reachability, filter drawer
   scroll, preview containment, keyboard navigation and browser history. Check all six palettes/modes.

## Remaining exceptions and acceptance limits

Calendar owns period/day/agenda controls and its existing `view=list|calendar`; timelines retain
chronological source evidence rather than directory Gallery. Schedule has no Saved Views integration;
Suppliers has search and Saved Views but no unsupported filters. Orders have no record photo contract,
so Gallery uses the existing neutral Order visual and truthful No image state. All five families keep
their domain-specific dialogs, permissions and independent save boundaries.

Physical devices/touch/soft keyboards, assistive technology, actual 125%/150% browser zoom, forced
colors, live network/storage failure injection and large-scale performance were not verified. Theme
coverage is complete for primary states; ten contextual states are risk-based samples, not every
possible dialog/state × width × theme. Automated suites cover loading, failure, validation, permissions,
history and transitions; the browser review did not execute destructive or persistent domain writes.
Operator functional/visual acceptance has passed all six scenarios. Independent correctness review,
reconciliation with PR #130 and canonical FULL remain open. Feature `UI-SYSTEM-WAVE2-001` remains
`implemented`, not `verified`. This approved candidate is being committed locally for independent QA;
no push, PR, merge or feature-finish is authorized in this task. The original UAT handoff marker was
`FLORABASE_UI_SYSTEM_V1_WAVE2_READY_FOR_OPERATOR_UAT`; current status is recorded in the QA handoff.
