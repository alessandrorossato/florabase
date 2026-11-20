# Batch 07 Workstream B: Mobile Directory & Native Zoom UX Remediation

Date: 18 November 2026
Branch: `fix/mobile-directory-ux-defects`
Base commit: `c555baabe916e3fea1ef2c8f834c747ced5aa926`
Writer: `hydrogen-b-mobile-ux`

## Environment and dataset

Browser verification ran against an isolated disposable Compose stack owned by this worktree
(`florabase-uat-preview-smoke-3102a08fef19`, `http://localhost:40369`), seeded with `uat_fixture`
(v4, 66 baseline records) plus 2 vegetative material lots and 2 rooting propagation attempts created
via the authenticated `/api/v1/vegetative-lots` and `/api/v1/vegetative-lots/{id}/propagation-attempts`
endpoints so both Cuttings surfaces (`Material lots` and `Rooting attempts`) were populated across List
and Gallery views.

Viewport and zoom coverage used headless Snap Chromium (`157.0.8103.38`):

- Standard viewports via CDP metrics: `1440×844` (DPR 1), `1440×700` (DPR 1), `1024×844` (DPR 1), and
  `390×844` (DPR 2, `mobile: true`).
- Genuine Chromium native 200% zoom via a disposable unpacked MV3 extension calling
  `chrome.tabs.setZoom(tabId, 2)` with zero CDP `Emulation.setDeviceMetricsOverride`:
  - `1440×844` window → `720×350` CSS px (`devicePixelRatio: 2`)
  - `1440×988` window → `720×422` CSS px (`devicePixelRatio: 2`)
  - `2048×1200` window → `1024×528` CSS px (`devicePixelRatio: 2`, desktop sidebar open)
  - `2880×1800` window → `1440×828` CSS px (`devicePixelRatio: 2`, desktop sidebar open)

## Root causes, fixes, and before/after measurements

### 1. Cuttings mobile collision between secondary metadata and `Details`

- **Root cause:** `frontend/src/styles/directory-system.css` pulled
  `.ui-directory-row--composed > .ui-directory-record-actions` up by
  `margin-block-start: calc(-1 * var(--control-height-touch, 2.75rem))` at `@media (max-width: 48rem)`,
  assuming `.ui-record-summary` reserved `padding-inline-end: calc(3 * var(--control-height-touch, 2.75rem))`.
  Cuttings (`Material lots` and `Rooting attempts`) omits `summary`, and
  `frontend/src/ui-pages/Cuttings/cuttings-directory.css` also applied `grid-column: 2` to
  `.ui-record-secondary` inside the single-column `.ui-record-identity` grid, squeezing
  `.ui-record-title` and `.ui-record-secondary` side-by-side so `Details` collided directly with
  `.ui-record-secondary`.
- **Fix:** Scoped the negative pull-up in `frontend/src/styles/directory-system.css` to
  `> .ui-directory-row--composed:has(.ui-record-summary)`, removed
  `.ui-record-secondary { grid-column: 2; }` at `@media (max-width: 48rem)` in
  `frontend/src/ui-pages/Cuttings/cuttings-directory.css`, and kept
  `margin-block-start: 0` on `.cuttings-directory .ui-directory-records--list > .ui-directory-row--composed > .ui-directory-record-actions`.
- **Measured result (`390×844` List view):**
  - Cuttings `Material lots`: `2/2` rows collided before (`overlap: 99.8×32` px) → `0/2` after.
  - Cuttings `Rooting attempts`: `2/2` rows collided before (`overlap: 99.2×32` px) → `0/2` after.
  - Cuttings Gallery views (`lots` and `attempts`): `0` overlaps before and after.

### 2. Unnecessary mobile top gap above search in Cuttings and Orders

- **Root cause:** At `@media (max-width: 48rem)`, `frontend/src/styles/directory-workspace.css` set
  `.application-shell:has(.ui-directory-records), .application-shell:has(.harvest-directory) { display: grid; grid-template-columns: minmax(0, 1fr); }`
  with `min-block-size: 100dvh`, while `grid-template-rows: auto` only applied inside
  `@media (max-width: 48rem) and (max-height: 30rem)`. On short populated directories (`Orders`,
  Cuttings `Material lots`, Cuttings `Rooting attempts`), implicit `auto` grid rows stretched row 1
  (`.wb-sidebar`) vertically to absorb unused `100dvh` height, pushing `.app-content` and the search
  box down by `45.6–88.4` px compared to `Plants`.
- **Fix:** Added `grid-template-rows: auto;` and `align-content: start;` inside
  `@media (max-width: 48rem)` in `frontend/src/styles/directory-workspace.css`.
  Accessible page headings (`<h2 id="cuttings-title">Cuttings</h2>` and
  `<h2 id="orders-title">Orders</h2>` inside `.page-header--directory .page-identity`) remain
  preserved in the DOM.
- **Measured result (`390×844`):**

| Surface | Before `appContent.top` / `search.top` | After `appContent.top` / `search.top` | Reference (`Plants`) |
| --- | --- | --- | --- |
| Orders (List) | `178.5` px / `187.5` px | `117` px / `126` px | `117` px / `126` px |
| Cuttings — Material lots (List) | `162.6` px / `171.6` px | `117` px / `126` px | `117` px / `126` px |
| Cuttings — Rooting attempts (List) | `205.4` px / `214.4` px | `117` px / `126` px | `117` px / `126` px |
| Orders / Cuttings (Gallery) | `117` px / `126` px | `117` px / `126` px | `117` px / `126` px |

### 3. `RECENT` and `Sign out` visibility at desktop widths and native 200% zoom

- **Independent reproduction:** Measured `.wb-panel`, `RECENT` (`.wb-group`), and `Sign out`
  (`.wb-sign-out`) geometry and keyboard `Tab` traversal on both 2-link Sourcing (`#/orders`) and
  8-link Collection (`#/cuttings`, `#/plants`) panels:
  - `1440×844` (DPR 1): `.wb-panel` does not overflow (`scrollHeight: 844 === clientHeight: 844`);
    `RECENT` (`278.5..351.5` px on Orders, `538.5..653.5` px on Cuttings) and `Sign out` (`792..832` px)
    are inside `.wb-panel` and viewport (`inPanel: true`, `inViewport: true`); `Tab` reaches `Sign out`
    in 7 steps.
  - `1024×844` (DPR 1): `scrollHeight: 844 === clientHeight: 844`; `RECENT` and `Sign out`
    (`792..832` px) stay unclipped (`inPanel: true`, `inViewport: true`) on both Orders (8 `Tab` steps)
    and 8-link Collection Cuttings (14 `Tab` steps).
  - `1440×700` (DPR 1) on 8-link Cuttings: `.wb-panel` scrolls (`overflow-y: auto`, `scrollHeight: 841 >
    clientHeight: 700`), and `Tab` scrolls `panelScrollTop` to `141`, bringing `Sign out` to
    `648..688` px (`inPanel: true`, `inViewport: true`).
  - Native 200% zoom `2048×1200` (`1024×528` CSS px, DPR 2): `.wb-panel` scrolls cleanly (`scrollHeight:
    581..883 > clientHeight: 529`); `Tab` scrolls `panelScrollTop` (`52` on Orders, `270` on Plants,
    `342` on Cuttings) and reaches `Sign out` (`kbReached: true`, `inPanel: true`, `inViewport: true`).
  - Native 200% zoom `2880×1800` (`1440×828` CSS px, DPR 2): Orders & Plants fit without scrolling;
    8-link Cuttings (`scrollHeight: 883 > clientHeight: 829`) scrolls `panelScrollTop` to `54` on `Tab`
    (`kbReached: true`, `inPanel: true`, `inViewport: true`).
- **Disposition:** No clipping or keyboard inaccessibility was observed. Per instructions,
  `frontend/src/shell/workbench.css` was **not modified**.

## Cross-viewport and Batch 05 regression checks

- Horizontal overflow (`documentElement.scrollWidth > documentElement.clientWidth`): `false` across
  all checked routes (`Plants`, `Orders`, `Cuttings` lots and attempts) and all viewports (`1440×844`,
  `1440×700`, `1024×844`, `390×844`, and native 200% zoom at `1440×844`, `1440×988`, `2048×1200`, and
  `2880×1800`).
- Runtime errors during final browser verification: `consoleErrors: []`, `pageErrors: []`.
- External local QA artifact captures and JSON geometry reports (stored outside the claimed worktree; not committed repository files):
  - `brain/c05760e3-f1a8-437f-ab38-604f6939176e/scratch/ws_b/before/` (`report.json` and PNG screenshots)
  - `brain/c05760e3-f1a8-437f-ab38-604f6939176e/scratch/ws_b/after/` (`report.json` and PNG screenshots)

## Frontend checks

Run inside the Workstream B Quality `frontend` container after the final edit:

- `pnpm format:check` — passed (Prettier)
- `pnpm lint` — passed (`eslint . --max-warnings 0`)
- `pnpm typecheck` — passed (`tsc -b`)
- `pnpm test` (`vitest`) — passed: **126/126** test files, **1382/1382** tests, including new
  regressions in `src/appearance/styles.test.ts`, `src/ui-pages/Cuttings/Cuttings.test.tsx`, and
  `src/orders/OrderScreen.test.tsx`.

## Cleanup and remaining findings

- Owned disposable stack retired via `ws_b_env.py down`:
  `RESOURCE_CLEANUP_PASSED project=florabase-uat-preview-smoke-3102a08fef19 removed={"containers": 3, "images": 2, "networks": 1, "volumes": 2} residual_containers_networks_volumes=0 retained_images=0`.
- Temporary unpacked MV3 extension directories under `~/snap/chromium/common/` were deleted in test
  cleanup.
- No remaining defects within Workstream B scope. `F-06` and other Batch 07 workstreams remain out of
  scope here.
