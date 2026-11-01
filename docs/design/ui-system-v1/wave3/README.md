# Wave 3 — Collection implementation and operator refinement handoff

**Current candidate (31 October 2026):** the [same-family consolidation specification](../consolidation/README.md), compliance matrix, evidence gallery and UAT checklist supersede the historical page-specific handoffs below. QA reconciliation is already included; operator acceptance and canonical FULL remain pending.

29 October 2026. Branch `feat/ui-system-v1-wave3`, isolated Codex checkout `548f`,
base `5b2e2a1` (merged Wave 1 #129 plus enrichment #130). Wave 2 remains unmerged;
its worktree, environments and implementation are not changed. This is a partial
implementation handoff, not Wave 3 UAT acceptance or delivery readiness.

**Current operator decision (30 October): not accepted.** The refinement candidate below
supersedes the previous UAT-ready handoff; no QA, FULL or delivery is authorized yet.

## Implemented scope

- Harvest deletion and Remove inventory tracking place Cancel first, matching
  TaskDialog's existing initial-focus behavior. Destructive actions use danger styling.
  Pending dismissal locks, retryable errors and stable More-trigger focus return remain.
- Location creation captures its initial payload, including prefilled parent and scopes.
  Cancel and Escape protect changed drafts; pristine forms close immediately.
- Inventory/disposition and seed conversion retain initial controlled drafts and use
  one page-owned dismissal guard for their Cancel/Escape paths. Conversion backdrop
  dismissal also uses that guard through the existing EditWorkspace callback.
- No shared component contract, API, schema, migration, domain mutation or new bulk operation.
  UI-SYSTEM-001 remains `in_progress`.

## Compliance update

| Surface              | Batch 1 status                                                  | Remaining scope                                                |
| -------------------- | --------------------------------------------------------------- | -------------------------------------------------------------- |
| SeedLots             | Existing approved implementation retained                       | Targeted later integration regressions                         |
| Sowings              | Unchanged                                                       | Batch 2 List/Gallery, explicit actions, overlay and typography |
| Plants / PlantGroups | Existing approved implementation retained                       | Targeted later integration regressions                         |
| Harvests             | Safe destructive confirmation implemented                       | Batch 3 directory adaptation                                   |
| Stored material      | Safe tracking confirmation and changed-draft guards implemented | Batch 3 exact inventory destination and integration            |
| Locations            | Creation dirty-dismiss protection implemented                   | Batch 4 direct-detail loading/error/missing recovery           |

## Checks and limits

The initial focused baseline passed 44 tests across HarvestScreen, StoredMaterial
and Conversion. The first changed-tree run passed 49 domain tests and 19 selected
Location tests (99 unrelated App tests excluded by name filter), and strict TypeScript.
Initial targeted ESLint identified one unnecessary async test callback, corrected
without changing behavior assertions. Final targeted results are recorded in progress.md.
Tests cover Enter on initial Cancel, danger styling, pending/error retention, focus
return, unchanged-form cancellation, rejected dirty dismissal and accepted discard.

One isolated reusable Quality project is used: `florabase-quality-8b4474e4d89f`.
No live Review was provisioned and no existing Review/DEV/UAT environment was modified.
There is no new Review URL or screenshot gallery for this partial handoff.
No canonical gate, production build, backend/integration checks or browser visual
acceptance is claimed. Real browser native confirmation, backdrop interaction,
all six themes, 1440/1024/390/320 widths, actual zoom, physical devices and assistive
technology remain to be exercised in the later owned Review environment.

## UAT checklist for continuation

- Open both destructive dialogs by keyboard; Cancel is focused, Enter cancels with
  no mutation, Escape returns to More. Pending Escape/Cancel cannot dismiss; server
  failure remains actionable without losing the selected record.
- Close pristine Location, inventory, disposition and conversion tasks immediately.
- Change Location name, parent or scope; reject discard and retain all input, then
  accept discard. Include prefilled Create child and reopening the create task.
- Change inventory state/quantity/storage or disposition/date/notes; repeat rejection
  and accepted discard. Preserve precision, units, collected amounts and remainder.
- Change conversion target/quantity/remainder; test Cancel, Escape and backdrop.
  Declining discard must retain the complete draft and focus containment.
- Test save pending/failure/success without altering existing domain eligibility.

## Continuation boundary

After Wave 2 protected delivery, fetch main and inspect its final shared contracts
before reconciling this branch. Implement Batches 2–4 only then. Page-owned files
currently have no overlap with Wave 2's committed product changes; progress.md is
an expected append-only reconciliation point. Do not duplicate TaskDialog,
EditWorkspace or directory abstractions. Do not push, create a PR, merge or finish
before operator acceptance. No Wave 3 completion marker is appropriate yet.

## Final focused evidence

- Domain suites: HarvestScreen **16**, StoredMaterial **24**, Conversion **10**;
  selected Location App cases **19**. **69 distinct tests passed** across scoped
  runs. The final StoredMaterial rerun passed 24/24 after its test-only lint fix.
- `pnpm typecheck`: passed on the final frontend tree.
- Affected-file `pnpm exec eslint ... --max-warnings 0`: passed.
- All nine changed TSX files formatted by Prettier; final seven plus Harvest test
  checked, StoredMaterial test formatter reported unchanged.
- `python3 scripts/check-features.py`: 120 valid. `git diff --check`: passed.
- Commands ran through `python3 scripts/workflow_environment.py quality compose --
run --rm --no-deps frontend ...`; test commands used the three named domain files
  and `pnpm test src/App.test.tsx -t '[Ll]ocation'`.
- Two test-callback lint errors were corrected. One attempted Compose invocation
  with unsupported `--no-build` failed before tests; the supported invocation passed.
  The selected App run emitted JSDOM's native-confirm-not-implemented warning in
  an existing case; real native-confirm acceptance remains explicitly unverified.

Product files changed: `HarvestScreen.tsx`, `StoredMaterial.tsx`,
`InventoryDialog.tsx`, `ConversionDialog.tsx`, `LocationScreen.tsx`.
Regression files changed: `HarvestScreen.test.tsx`, `StoredMaterial.test.tsx`,
`Conversion.test.tsx`, `App.test.tsx`. Shared components changed: **none**.
Documentation changes: this handoff and the progress milestone. The operator accepted
Batch 1 for a standalone local implementation checkpoint. The recorded 69-test
evidence is preserved; no verified status, canonical receipt or final Wave 3 UAT
acceptance is claimed. Wave 2 was subsequently merged as PR #131 at
`76c0911dbf7ca5dc5f64b1a8d1de8c57c676c70e`; this worktree reconciled it in merge
`13c3233f9d2136dc09958d7fca51962996c422f1`, retaining checkpoint
`36698698b00916870dca27feb44b10ee2f3a7723`.

## Wave 3 integration regression and Review follow-up (2026-10-29)

The first combined test run reported 72 passed and 10 failed. Diagnosis found
three Sowing tests and six Harvest tests used partial accessible-name queries
that now also matched explicit Preview/Details/Edit controls; the Sowing editor
test also expected the former inline preview instead of the approved modal
overlay. The Stored Material directory test expected a Harvest-only link rather
than the exact inventory destination (`?inventory=<id>`), which its existing
route already supports. These expectations/selectors were corrected without
changing domain behavior. A selected Location deep-link assertion was also
updated for the new explicit missing-record state and return link.

Verification after correction: focused Wave 3 suites **83/83**; preserved Batch 1
safety baseline **69/69**; strict TypeScript, affected-file ESLint, Prettier and
feature-registry checks passed. The Wave 2 Review owner retired that environment
through its owning worktree. The canonical Review was then provisioned for this
source (`13c3233`) and the operator completed the owner bootstrap interactively.
The UI confirms `Signed in as owner`; no credential was read or recorded. The
canonical Review seeder reported fixture version **4**, ready, **80 baseline
records**, and preserved owner/existing edits. The post-seed lifecycle status
reported healthy frontend/backend/database and current migration head
`20261013_0042`. A fresh read-only status retry also confirmed ownership, source,
health and fixture counts; the initial attempt had been denied by the Docker socket.

Visual review was performed in the signed-in browser at CSS viewport widths
1440×900, 1024×900 and 390×844. All six combinations of Botanical, Herbarium and
Mineral with Light and Dark were inspected at 1440×900 for Harvests, Stored
material and Locations. Sowings Gallery was inspected across the six themes at
1440×900 and at 1024×900 and 390×844 in Botanical Light; Sowings List and Gallery
were both checked in Botanical Light. Harvests and Stored material were also
checked at 1024×900 and 390×844; Locations at all three widths. Loading indicators
were observed for each theme on Harvests, Stored material and Locations. The
nonexistent Location route displayed its missing-record state and return link.
All four routes had no horizontal document overflow at the three CSS widths.
The screenshots were emitted inline in this review session; no screenshot binary
or standalone HTML gallery was saved in the repository.

The harvest deletion dialog placed Cancel in initial focus; Escape dismissed it
without deleting the record. The Location draft prompt appeared on Cancel after
editing the name; declining retained the text and form, then accepting discarded
the temporary draft. Harvest Preview Escape returned focus to its originating
Quick Preview action. Stored Material navigation reached the exact inventory
`?inventory=<id>` and scrolled its target into view. Existing focused regressions
cover retryable Location errors and Batch 1 pending/error dismissal guards; a live
service failure was not injected. Viewport screenshots are browser-emulated CSS
sizes, not physical devices. No screen reader or actual browser zoom was tested.
No canonical FULL gate, push, PR, delivery or cleanup was performed.

## Current Collection compliance matrix

Implementation, focused regressions and the browser visual pass are reviewed.
This matrix records the current source contract and the in-session visual evidence.

| Surface                       | Current family and shared UI                                                                                                                                                  | Confirmed behavior and domain contracts                                                                                                                                                                                              | Remaining visual checks / risk                                                                                                                                          | Likely files                                                                         | Priority / effort | Evidence                                                                        |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ----------------- | ------------------------------------------------------------------------------- |
| Sowings                       | Directory; List default, Gallery optional; DirectoryTools, DirectoryRecords, DirectoryRow/Card, DirectoryRecordActions, DirectoryInspector, Saved Views and presentation hook | Lifecycle/filter/search, bulk selection, exact SeedLot identity, germination, lineage and descendants remain domain-owned; explicit preview/detail/edit paths; preview Escape returns focus                                          | Layout checked at 1440/1024/390; all six themes at 1440; Gallery only at 1024/390. Retry states and screen-reader use remain test/operator checks.                      | `frontend/src/sowings/SowingScreen.tsx`, `directory.css`, `SowingScreen.test.tsx`    | P1 / M            | 33 focused tests; inline screenshots in this review session                     |
| Harvests                      | Historical directory List; DirectoryRecordActions and DirectoryInspector                                                                                                      | Occurrences remain historical except supported correction/delete; no bulk selection; source, material, notes, Events, media and exact quantities retain existing flows; Preview Escape focus return; Delete Cancel initially focused | Layout checked at all three widths; all six themes at 1440; loading and no-photo content visible. Physical device/zoom/AT not exercised.                                | `frontend/src/harvests/HarvestScreen.tsx`, `directory.css`, `HarvestScreen.test.tsx` | P1 / M            | 16 Harvest tests; preview and dialog interactions; inline screenshots           |
| Stored Material               | Existing directory/table with filters, Saved Views and bulk controls                                                                                                          | Link targets exact inventory via `?inventory=<id>`; exact item scroll/focus; quantity, disposition, partial and unknown stock semantics unchanged                                                                                    | Layout checked at all three widths; all six themes at 1440; loading visible; live retryable service failure not injected.                                               | `frontend/src/harvests/StoredMaterial.tsx`, `StoredMaterial.test.tsx`                | P1 / S            | 24 directory tests and Batch 1 dialog checks; inline screenshots                |
| Locations                     | Existing native hierarchy and detail/editor flows                                                                                                                             | Tree, search, scope and operations unchanged; detail distinguishes loading, retryable error and missing record with return route; edited draft prompts on dismissal and remains after rejecting discard                              | Layout checked at all three widths; all six themes at 1440; loading and missing state visible. Retryable error is covered by focused tests, not live failure injection. | `frontend/src/locations/LocationScreen.tsx`, `frontend/src/App.test.tsx`             | P1 / S            | 19 selected Location App tests; dirty-dismiss browser check; inline screenshots |
| SeedLots, Plants, PlantGroups | Existing directories; approved Wave 1 composition retained                                                                                                                    | Shared nonmodal Preview and photo-source strip refinement follow the operator’s all-gallery clarification; domain behavior unchanged                                                                                                 | Mixed Plants photo/placeholder row and loaded preview checked in all six themes; device/AT/zoom limits remain                                                           | Shared DirectoryPage, directory.css, RecordVisual; consumer tests                    | P1 / S            | Included in 377 passing regressions; inline visual evidence                     |

Batches 1–4 initially changed no shared components. The final operator refinement
updates shared DirectoryInspector, photographic card alignment and source caption
presentation as documented below. No confirmed domain regression remains. The initial failures were stale
queries or stale preview/destination expectations and now pass against the
documented interaction contracts.

## Review fixture and UAT checklist

- Review: [http://localhost:15174](http://localhost:15174), sourced from this
  worktree. Owner bootstrap confirmed in the visible signed-in state without
  credential access. Canonical synthetic fixture v4 reports ready with 80
  baseline records; earlier post-seed health showed frontend/backend/database
  healthy and Alembic head `20261013_0042`. The final read-only lifecycle check
  confirmed those same health, ownership and fixture signals.
- Responsive/theme coverage: CSS widths 1440×900, 1024×900, 390×844; six theme
  combinations at 1440×900 on each in-scope surface. Sowings Gallery additionally
  at 1024 and 390 in Botanical Light. Screenshots are inline evidence in the
  review conversation; they were not archived as files, so there is no standalone
  screenshot-gallery URL.
- Interaction checks: Harvest Preview and Escape focus return; deletion dialog
  initial Cancel focus and safe Escape; Location dirty Cancel prompt, reject
  discard retaining draft, then accept discard; exact Stored Material inventory
  link and scroll target; Location loading and missing-record/return states.
- Existing regression suites verify retryable Location failures, pending/save
  errors and dirty-dismiss flows. A real backend outage was not induced. Browser
  zoom was not changed; screenshots use emulated viewport sizes. Physical devices
  and screen-reader/assistive-technology testing remain unverified.

Operator UAT scenarios:

1. In Sowings, switch List/Gallery; search/filter and restore a Saved View; preview
   a row; confirm selection, lineage, descendants and existing lifecycle actions.
2. In Harvests, open an old occurrence, inspect source/material/related history,
   preview with keyboard, then cancel deletion with keyboard and confirm no record
   or Event was removed.
3. In Stored material, follow a row and verify its exact inventory item, quantity
   semantics, storage location and scroll target; test correction, disposition,
   label printing and supported bulk actions without changing synthetic baseline.
4. In Locations, expand/collapse the hierarchy, search and open a detail; verify
   loading, retryable error and missing-record recovery; reject and then accept
   dirty-draft discard for a temporary new location.
5. Repeat the high-value layouts in 1440/1024/390 widths and six themes; use
   keyboard-only navigation and check focus visibility, Escape, long names and
   missing images. Report device and assistive-technology gaps separately.

## Final operator refinement candidate — 30 October 2026

The operator clarified that the photo strip/preview concerns affect **all** galleries.
DirectoryInspector therefore defaults to the shared nonmodal side panel for Seeds,
Sowings, Plants/groups, Harvests and Suppliers/Orders. Page domain mutations and
navigation remain unchanged. Existing modal support remains explicit for isolated
consumers/tests; editing and destructive tasks still use TaskDialog. Desktop and
tablet panels occupy their own column. Mobile panels stack above the directory,
scroll independently and never cover it. Close/Escape return focus to the latest
connected trigger; Tab is not trapped and other records remain interactive.

Confirmed defects and causes:

- At an actual 840px viewport Harvest Preview rendered only its heading and Close
  button: a legacy <=1024px rule hid the nested QuickPreview. The same family has
  a <=768px rule hiding detail panes. The side-panel styles explicitly show their
  content and pane at every breakpoint. This was reproduced before editing and
  verified with a loaded photograph after the fix.
- Source captions were absolutely positioned while preview RecordVisual had no
  positioned containing block. The panel now anchors captions to the visual;
  gallery captions retain accessible text plus a native source title without the
  dark source badge. Preview source text has no filled strip. The existing
  direct-photo → source-photo → identity-cover → placeholder fallback is preserved.
- Photo-title galleries aligned cards at row start, allowing photo and placeholder
  card bottoms to diverge. Shared cards now stretch within each row; existing
  flex-owned actions stay at the bottom. Sowings use compact placeholders and
  avoid reserved blank photo-title spacing without adding a heavy footer.

Locations reuses Geography management's recursive presentation: chevrons rotate
with expanded state, root hierarchy is keyboard focusable, branch rows share its
spacing/borders, and indentation compacts from the same depth. Location-only
counts, search ancestor retention, scope semantics, expansion overrides, retired
states, parent protections and actions are preserved.

Shared impact: DirectoryPage/DirectoryInspector, directory.css, RecordVisual source
label/title. Page adaptations: Sowings/Harvests preview calls and scoped Sowing CSS;
Locations hierarchy/icon/CSS. SeedLots, Plants and Sourcing product code is unchanged;
their shared preview consumers and regression expectations follow the new contract.

Verification: **377/377 tests across 11 files**, including the full 118-case App
suite, 33 Sowings, 17 Harvests, 24 Stored Material, 10 Conversion, shared directory,
RecordVisual, SeedLots, Plants, Suppliers and Orders. The original 69 Batch 1 safety
cases are included and pass (the safety boundary now has one additional Harvest
photo/record-switch regression). New checks cover nonmodal interaction, untrapped
Tab, latest-trigger Escape return, direct/source photo selection and source-title
fallback, plus Location chevron/expanded/root keyboard semantics. The first
Collection iteration had one stale Harvest dialog-role expectation; it was updated
for the approved nonmodal contract. TypeScript and final affected lint/format
results are recorded in progress.md.

The owned Review remains http://localhost:15174. Canonical extended Review seed
added v5 **252 managed references** while preserving v4/80, owner and edits. Counts
include 16 Sowings, 5 Harvests, 4 inventories, 18 Locations and 17 assets (v5 only).
No DEV/UAT/foreign environment was changed. Browser evidence is inline in the
review conversation; no external image archive is claimed. Evidence includes the
before blank Harvest dialog, loaded photo side preview, switching records while
open, Escape focus return, Sowing gallery beside preview, compact cards and the
expanded Location hierarchy. Earlier modal screenshots are historical evidence.

Revised operator scenarios:

1. In Plants Gallery, compare a photographed record and a placeholder in the same
   row: no source badge strip, readable title/scientific name and aligned card
   bottoms/actions. Hover the photo for source provenance; repeat in other galleries.
2. Open a photo Preview in Plants and Harvests; confirm photo and source caption
   stay in their image box. Select a different record without closing the panel.
   Tab to the list; Escape/Close returns to the latest Preview trigger. Details
   remains explicit. Include narrow-screen loading and failed-image fallback.
3. In Sowings List/Gallery, retain search/Saved Views and selection; verify lineage,
   germination and descendant operations. At 390px the preview stacks above the
   directory without covering it; at tablet/desktop it sits beside the list.
4. Compare Locations with Geography management: expand/collapse branches by keyboard,
   search a deep child, clear filters and inspect counts/scopes. Exercise parent
   protection, retired records and dirty new-location dismissal as before.
5. Repeat destructive Cancel/Enter/Escape, dirty-draft rejection/discard, exact
   Stored Material inventory navigation and quantity/disposition/conversion flows.

Physical devices, actual browser zoom, screen readers and live service-failure
injection remain unverified. Operator acceptance is pending; no FULL, commit,
push, PR, merge or feature-finish occurred in this refinement pass.

Final checks: strict TypeScript, zero-warning affected ESLint, all affected
Prettier checks, 121-feature validation and diff whitespace passed. No test/static
failure remains. Six settled 1440px mixed photo/placeholder gallery + side-preview
captures cover all six themes with loaded photos, no open modal and no horizontal
page overflow. The measured three-card row had identical bottoms (580.015625px)
and action baselines (579.015625px). Additional 1024px side-column and 390px stacked
preview/hierarchy captures establish the responsive adaptation; the earlier floating
panel trial was replaced with an inline stack so it cannot obscure the directory.
The final source-marker/health refresh confirms the same owned source and healthy
frontend/backend/database at migration head 20261013_0042.

## Global workspace refinement — 30 October 2026

Current handoff supersedes the earlier refinement handoff. Operator acceptance is
still pending. No canonical verification receipt or release readiness is claimed.

Shared architecture: DirectoryTrigger is the native keyboard Preview surface;
DirectoryRecordActions retains Details/Edit. DirectoryInspector stays mounted
while switching records, focuses/dismisses without scrolling, and remains nonmodal.
QuickPreview's opt-in compact body/footer split leaves specialized previews alone.
The existing StatusBadge/Icon system supplies semantic binary indicators.
`directory-workspace.css` bounds eligible directory results; identity/tools/chips
stay outside that scrollport. Desktop/tablet reserve the inspector column even
when closed. Mobile stacks a compact photo/name/action panel above results, with
full metadata available through Details. Below 30rem viewport height, page flow
is the deliberate accessibility fallback rather than an unusable results region.

### Updated compliance matrix

| Surface            | Current behavior / reuse                                                                    | Preserved contracts and exception                                                                          | Evidence                                                                                    |
| ------------------ | ------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Seeds              | Shared bounded List/Gallery, native surface Preview, compact Active check, Details/Edit     | Stock precision, physical packet identity, bulk limits, Saved Views and start-sowing destination unchanged | SeedLotScreen suite; 40-record browser scroll, six themes, photo/gallery and 320px captures |
| Plants / groups    | Same shared workspace; persistent preview during detail refresh                             | Individual/group identity, group lineage, bulk and forms unchanged; Dashboard unchanged                    | PlantScreen and App suites; responsive sweep                                                |
| Sowings            | Opted into shared workspace; persistent preview, List/Gallery surface actions               | Germination, lineage, descendants, quantity and Saved Views unchanged                                      | 34 Sowing tests, including inspector/scroll persistence; responsive sweep                   |
| Harvests           | Historical directory bounded by shared rules; compact source-aware Preview                  | History and corrections remain exact; no invented binary lifecycle                                         | 17 Harvest tests including photo/switch; responsive sweep                                   |
| Suppliers / Orders | Shared workspace, surface/photo Preview; explicit Details/Edit; native modified title links | Retired/order states remain truthful; supplier filters, ordering, paging, URL and editors unchanged        | 13 Supplier / 19 Order tests plus App; responsive sweep                                     |
| Stored Material    | Deliberate operational exception: exact inventory destination and selection retained        | Never substitutes Harvest/plant navigation for inventory identity; precision/disposition/conversion intact | 24 Stored Material + 10 Conversion tests                                                    |
| Locations          | Earlier Geography-style tree refinement retained; no record-row Preview conversion          | Counts/scopes, ancestors, protected parents and editing guards retained                                    | App hierarchy/loading/error/dirty-state cases and earlier tree captures                     |
| Other workspaces   | Journal/History/Schedule, Geography, Maps, Taxonomy and Media remain specialized            | No Activity conceptual redesign or foreign-worktree changes                                                | Consumer inventory and complete diff review                                                 |

### Diagnosis and verification

The first broad run exposed old tests that treated a narrow-screen record click as
Details. These now explicitly use Details before asserting the same domain flows;
no domain assertion was removed to mask a failure. A real Sourcing focus defect
was corrected: after removal of the eye button, focus reconnection must locate the
current native record trigger on its record container. Plants/Sowings retain the
list-record identity during detail fetch so switching does not remount the panel.

Real browser geometry exposed two layout defects that component tests cannot
measure: absolutely positioned screen-reader labels enlarged the outer scroll
region, and gallery grid rows compressed into the bounded height. Containing the
labels within results/visuals and using content-sized gallery rows fixes both.
The earlier photographic-preview cause remains fixed: the source caption needed
its own positioned image box, and narrow Harvest Preview incorrectly mounted the
hidden legacy dialog rather than the visible inspector.

Final focused run: **381/381 tests in 11 files**, including all original **69
Batch 1 safety cases** (covered in the combined domain suites), full 118-case App,
34 Sowings, 17 Harvests, 24 Stored Material and 10 Conversion. Shared regressions
cover native keyboard Preview, separate Details/Edit, no eye action, truthful
binary/richer lifecycle indicators, Sourcing modified links, and persistent
inspector/list scroll state. Existing history/Saved Views, selection, dirty-dismiss
and destructive safety assertions remain. Strict TypeScript, affected-file ESLint
with zero warnings, Prettier, API drift, 121-feature validation and diff whitespace
pass. The impact planner selects **FULL** for the shared component changes; it is
explicitly deferred until operator acceptance. No FULL or feature-verify was run.
After adding the Supplier trigger's exact Active/Retired focus description,
strict TypeScript, Supplier ESLint/formatting and all 13 Supplier tests passed again.
The final responsive stylesheet formatting check also passed.

### Current visual evidence index

Evidence is emitted inline in the review conversation; no downloadable screenshot
archive is claimed. Earlier modal/floating-panel captures are historical, not the
current implementation. Representative current observations:

- Desktop 1440x900, Seeds List, 40 records: results scrollTop 3089.5 while header top
  remains 63.046875 and inspector top 189.046875; outer shell stays 900px with
  scrollTop 0. Switching distant records retains the viewport position.
- Desktop Gallery/photo: content-sized rows, loaded protected photo, compact
  495px inspector with a separate visible footer and independently scrolling body.
- Botanical, Herbarium and Mineral, each Light/Dark at 1440px: all six loaded the
  photo, had no eye action and no document horizontal overflow; panels approximately
  493–495px. Theme restored to Mineral Dark.
- 1024px: Seeds, Plants, Sowings, Suppliers, Orders and Harvests retain bounded
  results and adjacent inspector without horizontal overflow.
- 390px and targeted 320x844: compact inline preview, visible record results and
  accessible footer; final 320px list is approximately 148px high with Preview open.
  At this width long identity is intentionally compact; Details supplies full data.
- Native keyboard, Escape/free Tab, focus return and explicit actions are covered
  by focused regressions; real browser scroll measurements supplement simulated
  component scroll persistence. Initial defective geometry captures were excluded.

Owned Review health confirms frontend/backend/database healthy, this worktree as
source, migration head 20261013_0042, v4/80 fixture ready. The canonical v5 extended
fixture previously provisioned 252 managed references remains available. No seed
reset, owner/password access, DEV/UAT mutation or foreign-resource cleanup occurred.

Actual 125%/150% browser zoom, physical devices and screen readers were **not**
exercised; viewport resizing is not equivalent to zoom. Live service outage
injection remains unverified; deterministic loading/error/retry cases pass in tests.
The owner browser session expired after the final Seeds scroll/Escape/reopen
check, during an additional Supplier spot-check. The operator must sign in again
for live UAT; credentials were not accessed or recorded. This does not invalidate
the completed responsive/theme observations or focused test results.

### Revised operator UAT

1. Scroll a long Seeds/Plants/Sowings directory; open distant records by surface
   and keyboard. Header/tools stay visible, inspector stays in place; close/reopen
   and switch List/Gallery without unexpected list jumps.
2. Compare mixed photo/placeholder cards and compact photographic Preview. Scroll
   long Preview metadata while its footer remains accessible; use Details for the
   full record. Check photo source/failed-image fallback.
3. Use explicit Details and Edit, browser Back/Forward and Saved Views. On Sourcing,
   use Ctrl/Cmd-click title for the native destination; ordinary surface/title click
   previews. Confirm actions never accidentally select/open a different record.
4. Enter bulk selection and Ctrl/Cmd-select Collection records; selection wins over
   Preview. Verify existing bulk preview/apply limits and exact inventory links.
5. Hover/focus a record with Active check; hear/read the full status description.
   Verify completed/exhausted/retired/cancelled states retain their exact labels.
6. At 1440/1024/390/320 and all six themes, check filter chips, long names, footer
   access, mobile scrolling, visible keyboard focus and free Tab/Escape. Manually
   exercise real zoom and assistive technology before final accessibility acceptance.
7. Recheck Locations hierarchy/counts/scopes/protected parents; destructive Cancel,
   initial safe focus and dirty-draft rejection/discard; Stored Material exact
   inventory/quantity/conversion; Sowing lineage. Specialized workspaces retain
   their own navigation model.

All changes remain uncommitted. Batch 1 checkpoint 3669869 and reconciliation
13c3233 remain intact. No push, PR, merge, feature-finish or operator acceptance.

## Operator annotations — scrollbar, empty inspector and full-record highlighting

The four annotations on Seeds/Plants are addressed by a limited shared-style
adaptation and restored existing empty-state branches:

1. Results and compact Preview bodies use thin scrollbars with the current
   theme's border-strong thumb and a transparent track; native scrolling remains.
2. Selection/hover belongs to the complete row/card, including Details/Edit.
   Its native Preview trigger stays transparent. Keyboard focus outlines the
   complete record; action buttons retain their own focus. The Tooltip wrapper
   means descendant selectors are required, not a direct-child button selector.
3. Seeds Gallery uses the same quiet, right-aligned icon actions as Plants,
   without a separate heavy action strip or button frames.
4. Existing Select-a-record placeholders render again in the reserved Collection
   inspector column when visible records exist and none is selected. Seeds,
   Plants/groups and Sowings recover their original domain-specific guidance.
   Empty placeholders remain hidden on mobile so they do not consume list space.

Bulk selection takes visual precedence over a previewed record: unchecked records
are not highlighted just because they had been previewed. Sowings now supplies
`selected` to DirectoryItem rather than a discarded data attribute, so its whole
record highlight follows preview and bulk state correctly. No domain operation,
selection membership rule, route or API changed.

Updated evidence: inline 1317x900 Seeds Gallery placeholder, selected Seeds List,
Seeds Gallery quiet actions, and selected Plants Gallery. Computed styles verify
transparent record/action children over the same selected parent in all six themes,
with no horizontal overflow. Keyboard Escape returns a 2px whole-record focus
outline and removes selected styling. Checked/unchecked bulk states were exercised
in the browser. Mobile 390px keeps the empty inspector hidden; 320px open Preview
leaves approximately 149px of results; 1024px also has no horizontal overflow.
Review remains owned and healthy at http://localhost:15174; viewport restored and
Mineral Dark restored. Operator completed login interactively; no credential access.

Additional operator checks: hover/select the whole Seeds row and card, including
its action area; compare Seeds/Plants Gallery action placement; close Preview to
recover the placeholder; check/uncheck a previewed record in bulk mode; verify
keyboard focus remains distinct from preview/bulk highlighting.

Annotation verification: **382/382 tests in 11 files**, including the original
69 Batch 1 safety cases. New Seed regression covers placeholder/whole-record
selection/bulk deselection/close restoration; Plants and Sowings assertions cover
whole-record selected state and idle guidance. Strict TypeScript, zero-warning
affected ESLint, Prettier, 121-feature graph and whitespace pass. Existing API
no-drift evidence is preserved; no contract changes required a repeat. FULL remains
deferred, source uncommitted, and operator acceptance pending.

## Follow-up: lifecycle text and aligned directory start

Operator requested Active text again: Seeds, Plants/groups, Sowings and Suppliers
now use the existing textual StatusBadge. Sowing Failed/Abandoned use semantic
red danger tokens; Completed retains its distinct lifecycle styling.
Collection count/Select records moved into DirectoryTools actions for Seeds,
Plants/groups and Sowings, removing the separate results-status row. The existing
placeholder/inspector now starts beside the first visible result. Domain state,
bulk safety and action callbacks are preserved.
DirectoryTools offers opt-in stableFilterSummary for these three consumers: one
constant-height chip lane, horizontal overflow for many filters, and an empty
noninteractive lane when filters are absent. Other consumers retain their previous
conditional summary. This prevents filter changes from adding/removing a row.
New live browser evidence remains pending because browser control was unavailable
in this follow-up; previous captures describe the preceding implementation.

Follow-up checks: 382/382 combined focused tests pass, including Batch 1; strict
TypeScript, affected ESLint/Prettier, feature graph121 and whitespace pass. Operator
visual review of the new alignment remains pending. No FULL/delivery actions.

## Follow-up: pagination, useful totals and photographic card flow

Supersedes the preceding toolbar-count placement. Seeds, Plants/groups and Sowings
place count, page controls and Select records above the shared list/inspector grid.
Default page size is 20; options are 50, 100 and All. Current active lifecycle
filter remains the default. Summary explicitly distinguishes filtered count,
complete loaded directory count and displayed interval. Pagination is browser-local,
not persisted in Saved Views; filters reset the page, and size changes return to
page one. Bulk choices cover only the displayed page; existing 100-record safety
and canonical filter/route semantics remain. Shared tests exercise 45 records,
last-page bounds, All, page-size reset and filtering from a later page.

Collection subtitles now use short product copy on Seeds, Plants/groups, Sowings,
Harvests and Locations. Photo-card titles no longer use absolute positioning over
the identity container: title, Active and scientific name occupy separate normal
flow rows. This removes the photographed Basil card collision.

Live 1317x900 evidence: Plants shows 20 of 24 matching / 26 total; Seeds shows
1–20 then 21–40 of 40 matching / 43 total. Seeds list/placeholder tops both
237.046875px; Plants both 291.0390625px. Basil photo-card title bottom 470.7109375,
Active top/bottom 474.7109375/500.703125, scientific name top 504.703125: no overlap.
Inline screenshots show paging and corrected photo card. No horizontal overflow.
At 320/390px, toolbar+paging+Preview would starve results; deliberate narrow-phone
page-flow fallback keeps a bounded 16rem–50dvh results region (measured 422px at
320x844) and allows workspace scrolling. Larger screens keep stable columns.
This supersedes the earlier narrow-phone fixed-header assertion. Actual physical
mobile, browser zoom and screen-reader checks remain outstanding.

383/383 tests across 11 focused files pass, including original Batch 1 safety
cases. Final mobile/accessible-arrow adjustment additionally passed shared16/16,
TypeScript, affected ESLint/Prettier. Graph121 and whitespace pass; API contracts
unchanged, prior API drift evidence retained. Owned Review healthy, same worktree,
migration 20261013_0042 and baseline fixture ready. No FULL/delivery actions.
UAT: test Next/Previous, 20/50/100/All, filtered versus global totals, filtering on
page two, per-page bulk selection, full photo names/status/scientific labels and
narrow-phone workspace/list scrolling.

## Pagination visual polish — operator annotation follow-up

Reference: Carbon Design System pagination guidelines
(https://www.carbondesignsystem.com/building-blocks/core/components/pagination/guidelines).
Adapts its grouped size/current-page/ghost-chevron pattern using existing Florabase
IconButton/Tooltip, native select and semantic tokens; no dependency or new UI framework.

DirectoryResults paginated variant now has a quiet range/count summary on the left
and one right-aligned control cluster: Per page, previous/position/next, Select
records. No primary navigation buttons or space-between gaps separating every item.
Current page is compact visually with a complete accessible label; chevrons retain
Previous/Next page labels, tooltips, keyboard operation and disabled boundary states.
Mobile uses a two-row grid without horizontal overflow, including the All option.
Nonpaginated DirectoryResults consumers retain their previous rendering.

Live inline evidence: 1317x900 Seeds List first/second page, normal and bulk mode;
320px compact two-row controls, no overflowing arrow labels. Counts show 1–20 then
21–40 of 40 records / 43 total. Final screenshots supersede the earlier wide-spaced
pager. The bulk toolbar/domain operations, 20/50/100/All choices and filtered/global
count semantics remain intact. Viewport restored after review.

383/383 focused tests pass in 11 files, including original Batch 1 cases. Updated
summary/parent-layout expectations reflect the new grouped composition while
preserving pagination and bulk assertions. Strict TypeScript, affected zero-warning
ESLint, formatting, graph121 and whitespace pass; final CSS/shared recheck recorded
in progress. No FULL, commit, push, PR, merge or cleanup. Operator acceptance pending.

## Final UAT correction — Sourcing row parity (2026-10-30)

The operator's Supplier screenshot issue also reproduced on Orders. Both pages used a
custom composition where thumbnails, title links, facts and action wrappers did not
follow the compact Seeds row rhythm. Record titles are now part of the accessible
Quick Preview trigger beside the thumbnail; the preview is nonmodal, and Details/Edit
remain separate direct actions. Supplier Active uses the existing compact status
indicator with an accessible “Active” name; retired remains an explicit text state.
Direct-record counts now use a bounded metadata column. Shared directory primitives
were reused; no shared component was changed. Gallery card identity/actions were
retained and use the same trigger structure.

Sowings was independently checked in List and Gallery: no missing propagation was
confirmed. It already has stable toolbar/count/pager controls, internal scrolling,
nonmodal inspector, row/card Quick Preview, direct Details/Edit, lifecycle labels,
selection and existing germination/lineage operations. The 34-case Sowing suite
remains green. No Sowings code or domain semantics changed.

Review was refreshed through its owning feature workflow. Post-refresh status reports
healthy frontend/backend/database, code and DB head `20261013_0042`, fixture v4 ready
with 80 records, source bound to this worktree and URL `http://localhost:15174`.
Before/after visual comparison was performed at the available 1320x900 browser size
in Mineral Dark and Mineral Light. Suppliers List, Orders List/Gallery, and Sowings
List/Gallery were inspected; supplier row preview opens the side inspector, while
the separate Details action routes directly to the record. Current Review appearance
was restored to Dark, Mineral.

Responsive captures at exactly 1440, 1024 and 390 CSS pixels were not available in
the connected browser control, which exposes no viewport override; no claim is made
for those exact dimensions in this correction. Keyboard opening and separate action
behavior are covered by tests; screen-reader/physical-device/zoom acceptance remains
operator UAT. Focused suites: **145/145** across Suppliers, Orders, Sowings, Seeds and
shared directory tests. Strict TypeScript, affected ESLint, Prettier, feature graph
(123), and `git diff --check` pass. FULL, push, PR, merge and feature-finish remain
out of scope; operator acceptance is still pending.

## 1 November — final interaction contract correction

The operator-confirmed [final contract and current compliance matrix](../consolidation/final-interaction-correction/README.md)
supersede the earlier Quick Preview and action-menu decisions in this document. All eight
record directories and Locations/Geography Places now use direct Details/Edit with eligible
creation-only menus and no inspector columns. Existing full record Overview/tabs, domain
operations, Batch 1 guards and Schedule reconciliation remain intact. Dedicated Details
rendering, direct editor initialization and identity Edit-history defects were corrected.

Current evidence and verification: [gallery](../consolidation/final-interaction-correction/evidence/index.html),
[checks](../consolidation/final-interaction-correction/verification.txt),
and [operator UAT checklist](../consolidation/final-interaction-correction/README.md#operator-uat-checklist).
Earlier pass counts and screenshots remain historical evidence. Final operator acceptance and
canonical verification remain pending; no protected delivery was run.
