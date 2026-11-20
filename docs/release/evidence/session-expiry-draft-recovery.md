# Evidence: Session Expiry Draft Recovery & Protected Request Boundary (`fix/session-expiry-draft-recovery`)

## Provenance & Inventory

- **Branch**: `fix/session-expiry-draft-recovery`
- **Base commit**: `fdc75e83fa8818cab791ed82cbba65f4f97db7ae`
- **Historical ancestors**: `173b9f6` -> `6bca8c8` -> `a622ad84060b82496665f4ac29b9f3248472808b`
- **Reviewed predecessor (`BATCH07_PROTECTED_JSON_BOUNDARY_FINAL_SECURITY_QA`)**: `9bd4548be506263392e673aa9bb4bef7f5b7f258` (tree `93687f2a23697bdf9c229696e4bfdd1e62e0c6f8`)
- **Reviewed P2.1/P2.2 approval predecessor (`BATCH07_AUTH_FINAL_SECURITY_APPROVAL`)**: `fd5c542683c8e5b95a977bd590a25cbbd0454549` (tree `a8206073a743f7410d1aef9316ec8ee4e83a8d61`)
- **Writer claim**: `hydrogen-b-session-recovery` / `0d09f6e4c3cb`

### Reviewed Git Inventories (Kept Distinct)

| Range | Total paths | Production | Tests / Harness | Evidence doc |
| --- | ---: | ---: | ---: | ---: |
| Cumulative base (`fdc75e83`) -> predecessor (`9bd4548`) | 188 | 119 | 68 (67 test files + `frontend/src/test/auth.ts`) | 1 |
| Predecessor corrective delta (`a622ad84` -> `9bd4548`) | 186 | 117 | 68 | 1 |
| P2.1/P2.2/P2.3 initial correction delta (`9bd4548` -> `fd5c542`) | 6 | 3 (`auth/api.ts`, `auth/AuthProvider.tsx`, `photos/useProtectedImage.ts`) | 2 (`auth/SessionRecovery.test.tsx`, `occurrence-map/EvidenceTiles.test.ts`) | 1 (`docs/release/evidence/session-expiry-draft-recovery.md`) |
| Final P2.3 private-issuance delta (`fd5c542` -> successor HEAD) | 5 | 2 (`auth/AuthProvider.tsx`, `auth/api.ts`) | 2 (`auth/SessionRecovery.test.tsx`, `occurrence-map/EvidenceTiles.test.ts`) | 1 (`docs/release/evidence/session-expiry-draft-recovery.md`) |
| Cumulative base (`fdc75e83`) -> successor HEAD | 188 | 119 | 68 | 1 |

### Scope Rulings & Workstream B Overlap

- **Domain API coverage**: `32` domain API modules enforce mandatory `ProtectedRequestCapability` propagation.
- **`frontend/src/shell/WorkbenchShell.test.tsx`**: Explicitly authorized by SOL as a narrow test-allowlist addition wrapping existing renders in the real `AuthProvider` fixture without changing assertions.
- **`frontend/src/App.tsx` and `frontend/src/ui-pages/Cuttings/Cuttings.tsx`**: Covered by earlier Workstream A scope (`173b9f6`) and unchanged since `a622ad84`. Historical Cuttings writer ownership is preserved; the corrective Cuttings production scope remains limited to `frontend/src/ui-pages/Cuttings/api.ts`.
- **Workstream B overlap**: Strictly `frontend/src/orders/OrderScreen.test.tsx` and `frontend/src/ui-pages/Cuttings/Cuttings.test.tsx` only. Workstream B does not modify `Cuttings.tsx`, `OrderScreen.tsx`, or `order.css`. Opus independently verified a scratch merge of Workstream A and Workstream B (`45/45` passing across both test suites and `styles.test.ts`).

## Security & Lifecycle Architecture

1. **Suspension & epoch advancement vs. permanent revocation**:
   - **Temporary suspension & epoch advancement**: On HTTP `401` session expiry lock or `logout-failed`, the gate locks and advances the auth epoch, suspending protected dispatches and aborting in-flight requests while preserving the identical workspace `ProtectedRequestCapability` object and loaded protected image object URLs across same-owner recovery.
   - **Permanent revocation**: On owner switch, logout, explicit discard, cold login, restoration, and provider teardown/replacement, capabilities are permanently revoked (`record.revoke()`), never revived across `A -> B -> A` owner transitions, and immediately trigger synchronous `subscribePermanentRevocation` cleanup.
2. **P2.1 — Serialized restoration and CSRF rotation (`AuthProvider.tsx`, `auth/api.ts`)**:
   - Session restoration (`getSession` + `recoverCsrf`) executes inside the shared module-level lifecycle queue (`enqueueAuthCookieOperation`), which starts idle work immediately and serializes any concurrent or replacement lifecycle operations.
   - Read-only `getSession(controller.signal)` settles immediately on unmount abort; server-mutating `recoverCsrf()` runs without an unmount abort signal so any already-dispatched CSRF rotation settles inside the lifecycle queue barrier before replacement restoration probes or rotates CSRF state.
   - Retired providers fail closed before enqueuing new lifecycle work and never publish tokens, unlock the workspace, or issue capabilities.
3. **P2.2 — Synchronous object URL revocation (`photos/useProtectedImage.ts`, `auth/api.ts`)**:
   - `ProtectedRequestCapability` exposes `subscribePermanentRevocation(listener)` invoked synchronously inside `record.revoke()` (and immediately if already revoked).
   - `useProtectedImage` binds every created `blob:` URL to `subscribePermanentRevocation` with idempotent release, revoking former-owner object URLs synchronously before replacement workspace unlock rather than waiting for React passive-effect cleanup, while preserving loaded images during temporary same-owner locks and preventing stale blob completions from creating or leaking URLs after revocation.
4. **P2.3 — Lexically private gate attachment & capability issuance (`AuthProvider.tsx`, `auth/api.ts`)**:
   - Removed all unrestricted gate/issuance module exports: `attachAuthRequestGate`, `acquireWorkspaceCapability`, `getActiveAuthProviderId`, `syncAuthRequestGate`, `invalidateProtectedWorkspace`, `enqueueAuthCookieOperation`, and `revokedAuthCapability`.
   - Co-located the `AuthProvider` React component implementation and the module-private gate/controller machinery (`attachAuthRequestGate`, `issueWorkspaceCapabilityForProvider`, `AuthProviderGateController`, `ManagedWorkspaceCapabilityHandle`, `enqueueAuthCookieOperation`, `revokedAuthCapability`) inside `frontend/src/auth/AuthProvider.tsx`.
   - Reduced `frontend/src/auth/api.ts` to an explicit public compatibility facade re-exporting only the public non-issuance request/auth functions, error classes, and types from `./AuthProvider`.
   - No callable module export or public `AuthContextValue` property can attach a gate controller or independently establish protected-request issuance authority; retired provider controllers remain permanently unauthorized.
5. **Protected browser-managed resources & accepted original-tab behavior**:
   - Images render exclusively from `blob:` URLs via `useProtectedImage`; CSV exports/templates/examples use `downloadProtectedFile` with RFC 5987 `filename*` parsing, binary byte fidelity, and single-active-download mutex; occurrence map tiles use `EvidenceTiles`.
   - `openProtectedTab` (`"Open original image"`) allocates a popup tab synchronously on click, nulls `opener`, navigates to a `blob:` URL, and closes the tab on any auth lock occurring within its 60-second cleanup window (accepted by SOL as bounded cleanup behavior).

## Historical, Independent, and Author-Reported Evidence

### Historical Controls (`173b9f6`, `6bca8c8`, `a622ad84`)

- Earlier Workstream A commits established retained draft editing across HTTP `401`, tile-only HTTP `401` locking, and initial owner-bound workspace barriers.
- **Unconfirmed historical R1 calibration candidates**: The two earlier R1 calibration candidate events remain **unconfirmed**; current barriers and positive controls close R1 by construction and regression evidence (`QA-1` and mutation controls) without establishing what occurred in those two historical candidate events.

### Independently Executed QA on Predecessor `9bd4548` (Opus)

- Retained externally (not committed repository files) in `florabase-worktrees/_batch-07-coordination/claude-ws-a-final-qa-9bd4548/`.
- Verified `128` test suites / `1414` passing tests (`127`/`1410` repository tests + 4 independent regressions `QA-1`..`QA-4`), all `4` boundary mutation controls killed, all `5` R2 screens (`NativeRangesScreen`, `TerritoryInspector`, `TaxonomyScreen`, `DashboardSearch`, `SavedViews`) passing in disposable Chromium, legitimate original-image opening, byte-identical CSV downloads, zero former-owner calls in exact Identity Maps attribution runs, clean distributed bundle inspection, and combined Workstream A+B overlap (`45/45`).
- Earlier author-reported pre-commit browser screenshots/logs from the `9bd4548` pass (local scratch `brain/c05760e3-f1a8-437f-ab38-604f6939176e/scratch/ws_a_final_e2e/`) are historical author-reported artifacts of unproven commit provenance and are superseded by Opus's independent `9bd4548` QA and the successor checks below.

### Author-Executed Verification on Final P2.3 Private-Issuance Successor (`fd5c542` -> successor HEAD)

- **Focused & independent regressions**:
  - `SessionRecovery.test.tsx` (`16/16`, including runtime exported-surface audit, negative control against forbidden exports, and real-`AuthProvider` P2.3 lifecycle coverage), `EvidenceTiles.test.ts` (`7/7`, adapted to real `<AuthProvider>` without weakening assertions), and Opus's independent `QA-1`..`QA-6` (`claude-ws-a-delta-qa-fd5c542/IndependentBoundaryQA.test.tsx`, `6/6`): **3 files / 29 tests passed, 0 errors**.
  - Broader affected regression run (`12` repository suites covering `SessionRecovery`, `EvidenceTiles`, `App`, `App.lazy`, `RecordVisual`, `MediaScreen`, `ImportExportScreen`, `SavedViews`, `DashboardSearch`, `NativeRangesScreen`, `TaxonomyScreen`, `OccurrenceMapPanel` + Opus `QA-1`..`QA-6`): **13 files / 286 tests passed**.
- **Negative control (accidental re-export detection)**:
  - `MUTANT_REEXPORT_KILLED`: temporarily adding `export` to `attachAuthRequestGate` in `AuthProvider.tsx` was immediately caught and failed by `SessionRecovery.test.tsx` P2.3.
- **Formatting, lint, typing, build & bundle audit (`frontend/`)**:
  - `pnpm format:check`: **PASS** (`All matched files use Prettier code style!`)
  - `pnpm lint` (`eslint . --max-warnings 0`): **PASS** (`0` warnings, `0` errors)
  - `pnpm typecheck` (`tsc -b --pretty false`): **PASS**
  - `pnpm build` (`tsc -b && vite build`): **PASS**
  - `dist/assets/*.js` grep for `acquireTestAuth|renderWithTestAuth|issueTestRequestCapability|defaultTestSession|getActiveAuthProviderId|attachAuthRequestGate`: **0 matches** (`CLEAN_DIST`).
  - Export inventory across `auth/api.ts`, `auth/AuthProvider.tsx`, and `auth/context.ts`: zero exported gate attachment or capability issuance symbols; all gate/issuance functions remain module-private inside `AuthProvider.tsx`.

### Author-Executed Verification on Prior `fd5c542` Candidate (P2.1, P2.2, P2.3)

- **Focused & independent regressions**:
  - `SessionRecovery.test.tsx`: `16/16` passed (including strengthened StrictMode test and deterministic `P2.1`, `P2.2`, and `P2.3` regressions).
  - `EvidenceTiles.test.ts`: `7/7` passed.
  - Opus independent `IndependentBoundaryQA.test.tsx` (`QA-1`..`QA-4`) executed against the successor source: `4/4` passed (`131ms`).
- **Targeted mutation controls for P2.1, P2.2, P2.3**:
  - `MUTANT_P2.1_KILLED`: passing unmount `controller.signal` to `recoverCsrf` was caught by the `P2.1` test.
  - `MUTANT_P2.2_KILLED`: omitting `subscribePermanentRevocation` in `useProtectedImage.ts` was caught by the `P2.2` test.
  - `MUTANT_P2.3_KILLED`: allowing a retired provider controller to mint capabilities while a replacement provider is active was caught by the `P2.3` test.
- **Complete frontend verification on stable successor source (`frontend/`)**:
  - `pnpm format` & `pnpm format:check`: **PASS** (`All matched files use Prettier code style!`)
  - `pnpm lint` (`eslint . --max-warnings 0`): **PASS** (`0` warnings, `0` errors)
  - `pnpm typecheck` (`tsc -b --pretty false`): **PASS**
  - `pnpm test` (`vitest run --configLoader runner`): **PASS** (`Test Files 127 passed (127)`, `Tests 1413 passed (1413)`, `Duration 317.32s`)
  - `pnpm build` (`tsc -b && vite build`): **PASS** (`built in 385ms`)
- **Production bundle & capability issuance audit**:
  - Grep of `frontend/dist/assets/*.js` for `acquireTestAuth|renderWithTestAuth|issueTestRequestCapability|defaultTestSession|getActiveAuthProviderId`: **0 matches** (`CLEAN_DIST`).
  - Non-test `frontend/src/` issuance inventory: `attachAuthRequestGate` is called only in `AuthProvider.tsx`; `acquireWorkspaceCapability` exists only on the private `AuthProviderGateController` and is called only in `AuthProvider.tsx`.
- **Affected disposable Chromium protected-media verification (author-reported, successor source)**:
  - Executed against a seeded disposable Compose preview stack (`florabase-uat-preview-smoke-854591b1003a`, built from successor source, retired immediately after).
  - Verified protected image upload + `blob:` rendering (`rawApiImgs: 0`, `rawApiLinks: 0`), `"Open original image"` opening a `blob:` tab (`/content` HTTP `200`), loaded `blob:` URL remaining readable during temporary same-owner lock (`readableWhileLocked: true`) and after same-owner unlock (`readableAfterSameOwner: true`), and former-owner `blob:` URL immediately revoked and unreadable after cross-owner switch (`readableAfterOwnerSwitch: false`, `consoleErrors: []`).
  - Stack retired cleanly via `ws_a_env.py down` and verified via `make workflow-resources`: `RESOURCE_CLEANUP_PASSED` (`removed={"containers": 3, "images": 2, "networks": 1, "volumes": 2}`, `residual_containers_networks_volumes=0`, `retained_images=0`).

## Deferred Combined-Candidate Chromium Checks

Per SOL's ruling, the following browser checks remain deferred to combined-candidate verification (covered by unit tests and code review here):

- Offscreen lazy image loading (`IntersectionObserver` deferral).
- Browser popup-blocked behavior for `"Open original image"`.
- Real external-image network loading against a controlled external origin (`no-referrer` + opt-in).
