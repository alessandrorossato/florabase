# SOURCING-VISUAL-001 — Suppliers + Orders normalization handoff

Candidate: `/home/alessandro/Desktop/github/florabase-sourcing` (linked feature worktree)
Branch: `feat/sourcing-visual-001`
HEAD: `9a73d3f0434a3f8399de8746b010a5d8503937a4`
`origin/main`: `927594724d6ccab7dc0d6621a72019e68011944f`
Merge base: `9a73d3f0434a3f8399de8746b010a5d8503937a4`
Divergence: **0 ahead / 1 behind**. No new branch, commit, push, PR or delivery was created in
this pass.

All implementation, tests, CSS and documentation changes remain unstaged or untracked. No
`make feature-verify`, `make feature-deliver` or `make feature-finish` was run. The candidate is
ready for Sourcing visual review, not for delivery.

## STATUS

- Suppliers normalization is retained with the provisional acceptance already recorded.
- Orders normalization is implemented against the accepted Collection architecture and
  ORDER-001 semantics.
- Focused behavior tests (**122 / 4 files**), full frontend regression (**790 / 68 files**), strict
  TypeScript, zero-warning ESLint, Prettier, production build and whitespace checks pass.
- The Sourcing Preview is healthy on its isolated project and retains fixture v4 with four Orders.
- Git synchronization is intentionally not performed. See **GIT DIVERGENCE** for the proposed
  non-destructive plan.
- Final handoff marker: **READY_FOR_SOURCING_REVIEW**.

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
  `openOnFocus={false}` option for dialogs. Existing pickers keep their focus-opening default.
- `App` passes the Orders `initialTab` and no longer remounts `OrderScreen` or `SupplierScreen` by
  route record id.

## VERIFICATION

### Current focused frontend checks

Command:

```bash
cd frontend
npx vitest run --configLoader runner \
  src/orders/OrderScreen.test.tsx \
  src/seed-lots/ReferencePicker.test.tsx \
  src/components/recordNavigation.test.ts \
  src/App.test.tsx
```

Result: **122 passed / 4 files**. Coverage includes directory/search/filter behavior, long Supplier
names, create/edit payload semantics, partial dates, amount/currency pairing, dirty dismissal,
backdrop coordinates, picker Escape order, direct-edit fallback and heading focus, modal focus
restoration, detail tabs, linked SeedLots, deletion guards, route parents and App transitions.

Follow-up evidence for the linking and focus-boundary changes: `PurchaseContext.test.tsx` plus
`OrderScreen.test.tsx` **22 passed / 2 files**, including the selectable linked-lot row, backdrop
dismissal and Escape dismissal.

### Full frontend regression

`npm test -- --reporter=dot` in the final clean run: **790 passed / 68 files** (574 seconds). This
includes the shared-picker, responsive-layout, direct-edit focus and link-dialog corrections.

### Static and build checks

- `npx tsc -b --pretty false` — pass.
- `npx eslint <changed TS/TSX files> --max-warnings 0` — pass, zero warnings.
- `npx prettier --write <changed frontend files>` — applied; no remaining formatting issues.
- `npx vite build` — production build pass.
- `git diff --check` — pass.

### Workflow and environment checks already recorded for this candidate

- Workflow helper suite: **33/33 OK**.
- Review fixture suite: **22 passed / 1 live-only skipped**.
- UAT fixture guard subset: **12 passed** under a simulated UAT identity.

These checks predate the final Orders-only frontend edits and are reported as candidate environment
evidence, not as a new full backend gate.

### Not run

- Canonical `make feature-verify` or any full backend, PostgreSQL integration, migration-cycle,
  API-drift or production-compose gate.
- Python Ruff and strict mypy: those tools are unavailable in the running preview runtime image.
- The disposable guarded UAT live-dataset smoke.
- Native browser-window resizing; visual viewport evidence used same-origin iframes. See below.

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
  height approximately 533px. Entering a price without a currency marks Currency required and
  native validation prevents submission without hiding the footer.
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

`python3 scripts/sourcing_preview.py status` currently exits 1 in this checkout because its context
guard requires `origin/main` to be an ancestor of `HEAD`, and `HEAD` is behind by the Maps commit.
The containers and dataset were therefore inspected with read-only Docker/API queries. This is a
guard/divergence limitation, not a preview failure, and it should disappear after an approved
synchronization.

## GIT DIVERGENCE AND SAFE SYNCHRONIZATION PLAN

`origin/main` advanced by one commit (`9275947`, Maps `#116`) after this branch's base. The commit
adds Maps documentation, tests, images, `docs/progress.md` / `docs/features.json` entries and
generated backend/frontend API declarations. It adds no migration. The local Sourcing work does not
change backend contracts, the OpenAPI document or migrations.

The only likely textual overlap is `docs/progress.md`; both sides append independent milestones.
No `rebase`, `reset`, `stash`, history rewrite, force-push or automatic synchronization was
performed.

Proposed non-destructive plan, requiring separate operator approval:

1. Preserve and review the current dirty/untracked candidate first. Do not synchronize over it.
2. Merge `origin/main` into `feat/sourcing-visual-001` with a normal merge. Do not rebase or rewrite
   the feature branch.
3. Resolve `docs/progress.md` by retaining both the Maps milestone and this Sourcing milestone.
   Preserve both sides' feature entries.
4. Run `make api-check`; only if it reports drift, run `make api-generate` and commit both generated
   artifacts. No backend source change is expected from the Sourcing work.
5. Re-run the focused frontend checks, full frontend suite, TypeScript, ESLint, Prettier, production
   build, `git diff --check`, and the Sourcing Preview status guard.
6. Only then consider canonical `make feature-verify` and the operator's protected delivery flow.

The merge must not be used to hide or discard either milestone. The branch should remain the
candidate until the operator explicitly authorizes synchronization.

## WORKTREE STATE AND FILES

All changes are unstaged or untracked. No commit contains any of the Sourcing work.

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

## UNRESOLVED / LIMITS

- The branch is one commit behind `origin/main`; synchronization is intentionally pending approval.
- `make feature-verify` was not run and no verification receipt exists for this tree.
- Python lint/type checks and live UAT smoke were not run in this runtime.
- Visual viewport evidence is iframe-proxy evidence; native window resizing and actual browser zoom
  remain operator checks.
- Link-dialog backdrop and Escape dismissal were exercised live at 1440; pristine/dirty New Order
  and Edit dismissal, direct-link fallback and 1024×844 modal states remain unit-tested rather than
  re-captured live in this final pass.

READY_FOR_SOURCING_REVIEW
