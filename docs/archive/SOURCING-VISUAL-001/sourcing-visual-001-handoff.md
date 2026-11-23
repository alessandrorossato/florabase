# SOURCING-VISUAL-001 — Suppliers + Orders normalization handoff

Candidate: `/home/alessandro/Desktop/github/florabase-sourcing` (existing linked feature worktree)
Branch: `feat/sourcing-visual-001`
Synchronization points: preservation commit `f9eef43`, normal merge commit `c946acb`
`origin/main`: `927594724d6ccab7dc0d6621a72019e68011944f`
Merge base after synchronization: `927594724d6ccab7dc0d6621a72019e68011944f`
Divergence before this handoff commit: **2 ahead / 0 behind**. The reviewed corrections and this
document are committed on top; no new branch or worktree was created.

`origin/main` was merged normally into the feature branch. No reset, rebase, history rewrite,
force-push, discard or manual `main` change occurred. The only overlapping path was
`docs/progress.md`; Git merged it without conflict and both the Sourcing and Maps milestones remain.

## STATUS

- Suppliers normalization is retained with the provisional acceptance already recorded.
- Orders normalization is implemented against the accepted Collection architecture and
  ORDER-001 semantics; the merge added no backend contract or schema change.
- Post-merge review corrected real regressions in Orders search/filter behavior, Supplier
  Quick-Preview Edit focus/routing, direct-edit Back handling, creation focus and the shared
  `ReferencePicker` typed-query preservation. Each has focused regression coverage.
- Focused post-merge frontend checks (**157 passed / 7 files**), strict TypeScript, zero-warning
  ESLint and Prettier pass. Workflow helpers (**34/34**) and the Review fixture suite
  (**24 passed / 1 live-only skipped**) also pass.
- The Sourcing Preview is healthy on its isolated project at `15175` with fixture v4 and four
  Orders. Maps, Feature Review, UAT, DEV, Stable Preview and production were not touched.
- Canonical `make verify-full` remains the final local gate on the exact committed tree; delivery
  and finish are operator actions. Final handoff marker: **READY_FOR_DELIVERY**.

## SYNCHRONIZATION AND REVIEW

- The dirty candidate was preserved in `f9eef43` (23 intended files; no secrets, environment files,
  local databases or unrelated work). `origin/main` was fetched and merged in `c946acb` as a normal
  merge with **no conflicts**.
- `docs/progress.md` retains both milestones, including the Maps delivery. `docs/features.json`
  remains main's version with `MAPS-FOUNDATION-001`; this presentation increment adds no duplicate
  feature entry and continues to rely on `SUPPLIER-003` / `ORDER-001` as the domain sources of truth.
- `make sourcing-preview-status` succeeds after the merge: healthy frontend/backend/database,
  revision `20261013_0042`, fixture **v4 / ready / 79**, 9 Suppliers (1 retired), 4 Orders and 11
  SeedLots (6 with Supplier, 5 with Order). The live dataset was not reseeded.
- Review found and fixed these correctness/usability regressions:
  - Orders search no longer disables itself while the first filtered page is in flight, so a
    multi-character query keeps focus and all typed characters.
  - A missing Supplier filter UUID is again exact and visible as
    `Unavailable Supplier — <uuid>` in the picker and the active filter.
  - Supplier Quick-Preview Edit now returns to the preview (not the Details page) after save and
    restores focus to the remounted preview Edit control.
  - Browser Back out of a direct `?tab=edit` URL closes the inline editor in both Suppliers and
    Orders and restores the detail heading.
  - Successful Supplier creation focuses the loaded detail heading.
  - `ReferencePicker` preserves an in-progress typed query when its parent re-renders and rebuilds
    the `choices` array.
- ORDER-001 invariants were checked: optional Supplier, independent partial dates, optional exact
  price/currency pair, total-not-per-lot semantics, exact linked SeedLot counts, and unreferenced
  deletion only. The UI uses `aria-required` for the paired price/currency hints; the backend
  Pydantic contract rejects an unpaired value with 422, so the invariant is enforced server-side.
  The earlier wording that native validation alone prevents submission was inaccurate.

## ORDERS IMPLEMENTATION

### Directory and toolbar

- Reuses `WorkspaceIntro` + `DirectoryTools` + `RecordPreview` so Orders follows the accepted
  Collection directory language rather than a separate Sourcing layout.
- Search keeps its accessible name `Search Orders` but hides the visible caption. The search input,
  `Filters`, `Saved views` and `+ New Order` form one toolbar row at desktop width.
- The Orders `PageHeader` is normalized at the shared column breakpoint: the title and toolbar no
  longer reserve their desktop `flex-basis` as empty vertical space when the header stacks.
- Compact rows use the botanical serif identity, a document/receipt visual placeholder, supplier
  and date metadata, exact/partial total facts, and linked SeedLot count.
- At `<= 64rem` the row amount moves below the identity so a narrow directory column cannot force
  one-character-per-line wrapping. At `<= 48rem` the directory and Quick Preview stack.

### Supplier filter

- Uses the shared `ReferencePicker`, scoped to the filter drawer.
- The popup is constrained to the control width; long Supplier names wrap inside the menu instead
  of overflowing the drawer.
- The menu opens on an explicit click. Escape closes the menu first, then a second Escape closes the
  drawer. Picker focus remains in the input after the picker closes.
- The controlled value stays aligned when the filter is cleared or choices arrive after a
  preselected Supplier.

### Create and Edit

- Creation is route-driven through `#/orders?action=create`; `/orders` is the canonical Collection
  parent, so Back/Cancel returns to the directory without rebuilding a second flow.
- Contextual Edit uses `useEditRoute`; `OrderScreen` is no longer remounted by route key, so the
  directory, Quick Preview, detail and modal keep their state across navigation.
- Direct `?tab=edit` links use the inline `EditWorkspace` fallback and replace the URL after
  close/save instead of leaving the editor stranded. Cancel and save return focus to the detail
  heading rather than the detached editor controls.
- The ordinary New Order form is a compact two-column desktop layout. At 1440×844 the modal hugs
  the form, is approximately 533px high, and keeps the footer visible. Conditional date parts and
  validation can grow it up to the shared `88dvh` cap, with the form grid scrolling independently.
- On mobile the shared full-screen edit canvas remains: one column, scrollable fields, fixed footer
  above the safe area.
- The Supplier picker does not auto-open merely because the dialog focused it. Click, typing and
  keyboard navigation still open it.
- Date precision is still a full `PartialDate` control. Its visible `Precision` sublabel is hidden;
  the select retains the accessible name `Order date precision`. Unknown dates, year/month/day
  precision and independent Order/SeedLot acquisition dates remain intact.
- Total price remains optional as an exact amount + three-letter currency pair. Neither field is
  required alone; entering one makes the other required. The helper text states that this is the
  total transaction price, never a per-lot allocation.
- Supplier remains optional. Order reference and notes are editable without fabricating provenance
  or inventory.

### Dismissal and focus

- Pristine backdrop click closes the modal.
- Dirty backdrop click, Cancel and Escape are routed through the dirty-aware close handler and
  require explicit discard confirmation.
- Clicks inside the dialog and inside picker menus never dismiss the dialog.
- New Order and contextual Edit restore the opener trigger after a normal Cancel/Close.
- A saved Edit refreshes the detail and moves focus to the refreshed record heading, avoiding a
  focus target that was detached during the refetch.
- Editing from Quick Preview changes the route; after returning to the directory, focus is restored
  to the remounted Quick Preview Edit control.

### Details dashboard

- Detail route replaces the directory with the breadcrumb, record identity, Supplier link, linked
  SeedLot count, `Add seed lot`, `Link existing seed lot`, and `Edit Order`.
- `Overview` shows exact or partial Order date, optional exact total, physical SeedLot count, the
  total-not-per-lot statement, transaction reference/notes, optional Supplier/date independence
  guidance, and the explicit unlink/delete reconciliation copy.
- `Seed lots` shows each linked physical SeedLot as its own card with identity, acquisition date and
  lifecycle fact. It links to the SeedLot record and never presents synthetic inventory.
- `Add seed lot` preserves the SeedLot creation context; `Link existing seed lot` uses the existing
  link flow.
- Delete is disabled while any physical SeedLot is linked; the confirmation dialog explains that
  only Orders without linked lots can be deleted. Unlinking removes only the Order association.
- The detail is a full-width dashboard rather than a narrow preview, and the tab route is
  shareable through `?tab=seed-lots`.

### Review follow-up: linking and field focus boundaries

- `Link existing seed lot` is now a 46rem maximum-width dialog, centered by the native dialog
  geometry. Its list is capped at `min(22rem, 42dvh)` and scrolls internally, so the search, footer
  and Cancel action remain reachable instead of extending the dialog past the viewport.
- Each eligible lot is one selectable row rather than a heavy filled button: a white bordered card
  with the lot identity, source/Supplier metadata, and an `Already linked to an Order` status chip.
  The footer keeps pagination on the left and Cancel on the right.
- The link dialog dismisses on a true backdrop click and on Escape. The follow-up
  `Review purchase context` dialog uses the same backdrop behavior, while its existing `pending`
  guard prevents a dismissal during Apply.
- The Edit Order form grid now reserves six pixels of inline focus-ring clearance (with matching
  negative margin so the column geometry is unchanged) and uses inline scroll padding. The shared
  input rule draws a 3px outline at a 2px offset, so the previous edge fields could have their outer
  ring clipped by the grid's scroll box. Currency and Notes now measure inside the clip boundary.
- At 1440×900 the link dialog measured 736×684px with a 352px scrolling list; at 390×844 it measured
  339×690px with the footer visible and no horizontal overflow.

### Shared support changes

- Added `/orders` as a recognized Collection parent and return-focus target.
- Added an `order` visual kind with a neutral receipt/document placeholder.
- Added `ReferencePicker` controlled-value synchronization, explicit click opening and an
  `openOnFocus={false}` option for dialogs. Existing pickers keep their focus-opening default. A
  parent re-render that rebuilds `choices` no longer clears an in-progress typed query.
- `App` passes the Orders `initialTab` and no longer remounts `OrderScreen` or `SupplierScreen` by
  route record id. The same change required explicit post-route focus/close handling: Quick-Preview
  Edit returns to its remounted trigger, direct-edit Back closes the inline editor, and successful
  Supplier creation focuses the loaded detail heading.

## VERIFICATION

### Post-merge focused frontend checks

Command (quality Compose profile):

```bash
python3 ./scripts/workflow_environment.py quality compose -- \
  run --rm --no-deps frontend pnpm test \
  src/orders/OrderScreen.test.tsx \
  src/orders/PurchaseContext.test.tsx \
  src/suppliers/SupplierScreen.test.tsx \
  src/seed-lots/ReferencePicker.test.tsx \
  src/components/recordNavigation.test.ts \
  src/App.test.tsx \
  src/photos/RecordVisual.test.tsx
```

Result: **157 passed / 7 files**. Coverage includes directory/search/filter behavior, long Supplier
names, create/edit payload semantics, partial dates, amount/currency pairing, dirty dismissal,
backdrop coordinates, picker Escape order and typed-query preservation, direct-edit fallback,
Back-out-of-edit, creation and refresh focus, Supplier Quick-Preview Edit return routing, detail
tabs, linked SeedLots, deletion guards, route parents and App transitions.

### Static checks on changed frontend files

- `pnpm exec tsc -b --pretty false` — pass.
- `pnpm exec eslint <changed TS/TSX files> --max-warnings 0` — pass, zero warnings. The route
  departure effects use the repository's existing deferred-update pattern to satisfy
  `react-hooks/set-state-in-effect`.
- `pnpm exec prettier --check <changed frontend files>` — pass.

### Workflow and environment checks

- Workflow helper suite: **34 tests OK**, including the isolated Sourcing role/removal-token test.
- Review fixture suite: **24 passed / 1 live-only skipped**, including deterministic
  `FLORABASE_WORKFLOW_MODE=review` setup and Sourcing identity/refusal coverage.
- `make sourcing-preview-status` — healthy, revision `20261013_0042`, fixture
  **v4 / ready / 79**.
- UAT fixture volumes were verified still present and untouched; the live UAT smoke was not run.

### Final gate

- `make verify-full` is the canonical final local gate and must run on the exact committed tree;
  its receipt is required by `make feature-deliver`.
- Post-merge full frontend regression: **820 passed / 70 files**. The earlier pre-sync run was
  **790 passed / 68 files**. The final Unix gate supersedes and extends both with backend,
  integration, API-drift, migration, build and health stages.

### Not run here

- The disposable guarded UAT live-dataset smoke (live-only by design).
- Native browser-window resizing in this follow-up; the visual pass recorded below used same-origin
  iframe proxies.

## VISUAL REVIEW

The final visual pass used same-origin iframes at exact CSS viewport sizes because the available
desktop browser window could not be resized natively. This is **iframe proxy evidence**, not a claim
of native 1440×844 / 1024×844 / 390×844 window capture.

Observed states:

- **1440×844 directory:** title, description and toolbar align; search, Filters, Saved views and
  New Order stay on one line; directory and Quick Preview share the full width without horizontal
  overflow.
- **1024×844 directory:** the shared PageHeader stacks title and toolbar without the previous empty
  256px/608px flex-basis bands; all controls fit one row. The directory column and preview remain
  side by side; row amounts sit below identity and none of the four fixture titles collapse to
  one-character lines.
- **390×844 directory:** search is full width, the three actions wrap below it, rows stack amount
  below identity, and the mobile navigation remains visible.
- **1440×844 New Order:** two-column form, menu closed on open, footer visible, measured dialog
  height approximately 533px. Entering a price without a currency marks Currency required through
  `aria-required`; an unpaired value is rejected by the backend with 422 without hiding the footer.
- **1440×844 Edit Order:** selected Supplier label, complete date parts, price/currency, notes and
  footer fit within the dialog; no precision sublabel is visible.
- **390×844 New Order:** full-screen canvas, single-column fields, form panel scrolls independently,
  footer remains visible above the bottom edge.
- **1440 Filter drawer:** drawer is 448px wide; Supplier control and menu are 398px wide; the
  deliberately long Supplier name wraps to a 60px option without horizontal overflow. Escape
  closes the picker first and the drawer second.
- **1440 Details:** Overview shows the full dashboard sections and disabled Delete for a linked
  Order; Seed lots shows two independent physical-lot cards and the shareable
  `?tab=seed-lots` route.
- **1440×900 Link existing seed lot:** the dialog is centered at 736×684px; the lot list is 352px
  tall with internal scrolling, the footer is visible, and each row wraps its identity and
  source/Supplier metadata without horizontal overflow.
- **390×844 Link existing seed lot:** dialog 339×690px, list 352px, footer visible, no horizontal
  overflow; the same row layout collapses cleanly.
- **Edit Order focus boundary:** the grid's 6px inline padding and negative margin leave the Currency
  and Notes outer focus rings inside the scroll-box clip boundary while preserving the field
  geometry.

The Link dialog's true backdrop click and Escape dismissal were exercised live through the rendered
dialog at 1440; no screenshot capture was available in this follow-up, so its geometry is recorded
from DOM measurements. Pristine/dirty New Order and Edit backdrop behavior, Cancel/Escape
confirmation, direct-link edit fallback and every 1024×844 modal state remain covered by component
tests rather than re-captured live. Direct URL reload and full-viewport zoom remain operator checks
rather than claimed live captures.

## ENVIRONMENT

Sourcing Preview remains isolated:

- Project: `florabase-sourcing-preview`
- Endpoint: `http://localhost:15175` (loopback only)
- Compose: `compose.yaml` + `compose.dev.yaml` + `compose.review.yaml` + `compose.sourcing.yaml`
- Containers: frontend, backend and database all healthy; backend `/api/v1/health` returns
  `{"status":"ok"}`
- Database revision: `20261013_0042 (head)`
- Fixture: **v4 / ready / 79 records**
- Coverage: 9 Suppliers (1 retired), 4 Orders, 11 SeedLots, 6 SeedLots with Supplier, 5 SeedLots
  with Order
- Owner: local synthetic `owner` account; no production identity

No Feature Review (`15174`), persistent UAT, DEV (`5173`), production or Maps environment was
started, stopped, seeded, reset or removed. No volume deletion occurred.

A blank 0-Linked-SeedLot synthetic Order was created during visual interaction and then deleted
through the UI; the dataset returned to the four fixture Orders and the fixture marker remained
`v4 / ready / 79`. No Supplier, SeedLot or media record was changed.

`python3 scripts/sourcing_preview.py status` now succeeds because `origin/main` is an ancestor of
`HEAD`; the earlier guard failure was only the pre-merge divergence.

## GIT SYNCHRONIZATION RECORD

`origin/main` had advanced by one commit (`9275947`, Maps `#116`) after this branch's base. That
commit added Maps documentation, tests, images, progress/feature entries and generated API
declarations, with no migration. The Sourcing candidate adds no backend contract or schema change.

Synchronization used the conservative path:

1. Preserved the reviewed candidate as `f9eef43` after a secret scan and intended-file audit.
2. Merged `origin/main` with a normal merge commit, `c946acb`; no rebase, reset, stash, history
   rewrite or force-push.
3. Git merged `docs/progress.md` without conflict; both the Sourcing and Maps milestones are
   present. `docs/features.json` retains `MAPS-FOUNDATION-001` and all prior entries.
4. The merged tree keeps main's generated OpenAPI/schema artifacts; `make api-check` is part of the
   final gate and no regeneration was needed by inspection.
5. Post-merge focused checks and static checks pass as recorded above; the canonical gate remains
   the final exact-tree authority.

The merge did not hide or discard either milestone, and the branch is now **2 ahead / 0 behind**
before the reviewed corrections and documentation commit.

## WORKTREE STATE AND FILES

The synchronized and reviewed tree is committed on `feat/sourcing-visual-001`; only intentional
source, test, script and documentation files are staged for the final local commit. No secret,
environment file, database, backup, upload, cache or unrelated file is included.

Primary files:

- `frontend/src/orders/OrderScreen.tsx` — Orders directory, preview, forms, dashboard, dismissal and
  focus behavior.
- `frontend/src/orders/orders.css` — scoped directory, row, modal, dashboard, drawer, link-dialog,
  responsive and danger styles.
- `frontend/src/orders/OrderScreen.test.tsx` — Orders behavior, ORDER-001 and modal/filter tests.
- `frontend/src/orders/PurchaseContext.tsx` / `.test.tsx` — Link existing seed lot row layout,
  internal list scrolling, backdrop/Escape dismissal and purchase-context review.
- `frontend/src/seed-lots/ReferencePicker.tsx` / `.test.tsx` — controlled-value sync, click opening,
  `openOnFocus` and Escape/focus coverage.
- `frontend/src/components/recordNavigation.ts` / `.test.ts` — `/orders` parent and return focus.
- `frontend/src/App.tsx` / `App.test.tsx` — Orders tab routing and no-remount transitions.
- `frontend/src/photos/RecordVisual.tsx` — `order` placeholder.
- `frontend/src/suppliers/SupplierScreen.tsx` / `.test.tsx` and
  `frontend/src/suppliers/supplier-refinement.css` — provisionally accepted Suppliers work.
- `scripts/sourcing_preview.py`, `scripts/workflow_environment.py`, `scripts/uat_fixture.py`,
  `compose.sourcing.yaml`, `Makefile`, `docs/development-workflow.md`, `docs/progress.md` —
  isolated Sourcing Preview and fixture support.
- `docs/sourcing-visual-001-handoff.md` — this handoff.

## UNRESOLVED / LIMITS / DEFERRED

- `make verify-full`, protected delivery and `make feature-finish` run after this document is
  committed; their results and final PR/merge identifiers are reported in the operator handoff.
- The disposable guarded UAT live-dataset smoke is live-only and was not run in this pass.
- Visual viewport evidence is iframe-proxy evidence; native window resizing and actual browser zoom
  remain operator checks.
- Link-dialog backdrop and Escape dismissal were exercised live at 1440; pristine/dirty New Order
  and Edit dismissal, direct-link fallback and 1024×844 modal states remain unit-tested rather than
  re-captured live in this follow-up.
- Direct-edit browser Back now closes the editor instead of leaving it stranded, but an unsaved
  draft is still discarded by the browser traversal without a custom prompt; the in-app Cancel,
  Escape and backdrop paths retain dirty confirmation.
- Cosmetic dead CSS remains in `.orders-page` / `.order-list li` after the markup class change; it
  has no observed behavioral effect and is deferred.
- Orders still enables Edit from a record detail when the Supplier list failed to load; saving does
  not fabricate a Supplier and the existing form/error paths remain authoritative. Deferred.

READY_FOR_DELIVERY
