# Evidence: Session Expiry Draft Recovery & Protected Request Boundary (`fix/session-expiry-draft-recovery`)

## Provenance & Scope

- **Branch**: `fix/session-expiry-draft-recovery`
- **Base commit**: `fdc75e83fa8818cab791ed82cbba65f4f97db7ae`
- **Reviewed prior ancestor**: `a622ad84060b82496665f4ac29b9f3248472808b` (tree `68c7f57ddb1d0f686ff85a65001219b1e5ebeb6e`)
- **Writer claim**: `hydrogen-b-session-recovery` / `0d09f6e4c3cb`
- **Scope**: Complete SOL-cleared (`BATCH07_PROTECTED_JSON_BOUNDARY_SCOPE_CLEARANCE`) opaque capability propagation across all protected JSON requests, protected browser-managed resources (`blob:` media/thumbnails, `window.open` original image tabs, CSV/template downloads, occurrence density tiles), permanent capability revocation across lock / `logout-failed` / owner changes, and R2 screen boundary completion.

### Changed Files Summary (vs `fdc75e83fa8818cab791ed82cbba65f4f97db7ae`)

- **Production source & prototype fixture (`frontend/src/`)**: `118` core production source files (`auth/`, `photos/useProtectedImage.ts`, `occurrence-map/EvidenceTiles.ts`, all `31` domain API modules, and workspace/R2/component UI callers including `ScheduleUxPrototype.tsx`) plus `1` prototype fixture file (`frontend/src/ui-pages/ScheduleUxPrototype/fixtures.ts`).
- **Tests & test harness (`frontend/src/`)**: `68` files (`frontend/src/test/auth.ts` test helper + `67` `.test.ts`/`.test.tsx` suites).
- **Documentation**: `docs/release/evidence/session-expiry-draft-recovery.md`.
- **Workstream B isolation note**: Only `frontend/src/ui-pages/Cuttings/Cuttings.tsx` and `frontend/src/orders/OrderScreen.tsx` intersect with Workstream B directories; edits are confined strictly to capability/auth boundary wiring. Workstream B mobile directory layout fixes and mobile stylesheets (`cuttings-directory.css`, `order.css`) are completely untouched.

## Security & Boundary Design Summary

1. **Opaque module-issued capability (`ProtectedRequestCapability`)**:
   - `frontend/src/auth/api.ts` mints opaque capability tokens backed by a module-private `WeakMap` tied to an active session generation/epoch, owner identity, and controller registry.
   - Forged objects, missing capabilities, stale prior-epoch capabilities, and capabilities belonging to locked (`locked` / `unauthenticated` / `logout-failed`) or previous-owner sessions fail synchronously before `fetch()`, `window.open()`, or `IntersectionObserver` loads execute.
   - `A -> B -> A` re-login under the original owner issues a fresh session epoch and never revives capabilities from Epoch 1; late Epoch-1 response bodies are rejected before reaching component state, and pre/post invalidation callbacks stay isolated.
2. **Pre-dispatch & in-flight cancellation**:
   - `requestJson`, `requestProtectedBlob`, `downloadProtectedFile`, and `openProtectedTab` validate both capability authorization (`capability.isAuthorized()`) and caller `AbortSignal` before dispatching `fetch()`, ensuring aborted React StrictMode/effect runs never trigger false `401` session invalidation.
   - Active in-flight `AbortController` instances register with the capability boundary and abort immediately on session lock, `logout-failed`, unmount cleanup, or owner switch.
3. **Browser-managed protected resources**:
   - **Images (`useProtectedImage`)**: `frontend/src/photos/useProtectedImage.ts` returns `[mediaTarget, media]` and fetches image payloads via `requestProtectedBlob`, managing `IntersectionObserver` deferral (`RecordVisual`), object URL lifecycle revocation on unmount/owner switch, and HTTP `401` lock propagation without raw `/api/v1/...` `<img>` URLs.
   - **Popup tab (`openProtectedTab`)**: `MediaScreen.tsx` `"Open original image"` allocates the popup window synchronously on click, surfaces blocker alerts if suppressed, fetches protected bytes into a `blob:` URL, closes the blank popup window cleanly on `401`, and revokes blob URLs appropriately.
   - **Downloads (`downloadProtectedFile`)**: `ImportExportScreen.tsx` exports/templates/examples fetch binary bytes via `requestProtectedBlob`, parse RFC 5987 `filename*` and quoted `filename` headers, preserve UTF-8 BOM/CRLF bytes, enforce a single-active-download mutex, and abort on sign-out without raw `<a href="/api/v1/...">` elements.
   - **Occurrence map tiles (`EvidenceTiles`)**: Leaflet `GridLayer` tile fetches require an authorized capability, suspend and cancel pending tiles on invalidation/`logout-failed`, clear prior owner tiles on cross-owner unlock, and lock the session cleanly on HTTP `401`.
4. **Session states & CSRF guard**:
   - `activeCsrfToken(state)` replaces ad-hoc `"csrfToken" in auth.state` checks across UI callers so only live authorized authenticated states expose mutating tokens.
   - `logout-failed` suspends protected reads/tiles and blocks CSRF mutations while retaining explicit user sign-out retry recovery.
5. **Strict test-helper isolation**:
   - `frontend/src/test/auth.ts` (`acquireTestAuth`, `renderWithTestAuth`) is excluded from production source and verified absent from the Vite production bundle.

## Automated & Static Verification

Executed in the worktree (`frontend/`):

- `pnpm format` & `pnpm format:check`: **PASS** (`All matched files use Prettier code style!`)
- `pnpm lint` (`eslint . --max-warnings 0`): **PASS** (`0` warnings, `0` errors)
- `pnpm typecheck` (`tsc -b --pretty false`): **PASS**
- `pnpm test` (`vitest run --configLoader runner`): **PASS** — `Test Files 127 passed (127)`, `Tests 1410 passed (1410)` (`267.71s`)
- `pnpm build` (`tsc -b && vite build`): **PASS** (`built in 302ms`)
- **Production bundle & static boundary audit**:
  - Grep of `frontend/dist/assets/*.js` for `acquireTestAuth|renderWithTestAuth|issueTestRequestCapability|defaultTestSession`: **0 matches**
  - `git grep` across non-test `frontend/src/`:
    - `src="/api/v1`: **0**
    - `href="/api/v1`: **0**
    - `"csrfToken" in`: **0**
    - `test/auth` / `acquireTestAuth` / `issueTestRequestCapability` imports: **0**
    - Direct `fetch(` outside `frontend/src/auth/api.ts`: **1** (`frontend/src/App.tsx:453`, unauthenticated `/api/v1/health` probe)

## Live Disposable Stack & Headless Chromium E2E Verification

Executed against a seeded disposable Docker Compose preview stack (`florabase-uat-preview-smoke-b39231c75236`, built from this worktree, served over `http://localhost:47957`) using headless Chromium CDP (`ws_a_final_e2e.mjs`):

1. **Modal Draft Recovery Across HTTP `401` (`#/plants`)**:
   - Edited a plant label, revoked server sessions in PostgreSQL (`DELETE FROM auth_sessions`), submitted save -> backend returned `401` -> `#reauth-dialog` opened synchronously.
   - Wrong password kept workspace locked with `0` non-auth requests leaked.
   - Same-owner re-authentication restored the open modal with the unsaved draft intact and zero `PUT` auto-replay; manual `"Save changes"` succeeded (`PUT 200`).
2. **Protected Media & Popup Tab (`#/media`)**:
   - Uploaded PNG via `/api/v1/media-assets/local`, rendered protected detail image (`blobImgs: 1`, `rawApiImgs: 0`, `rawApiLinks: 0`).
   - Clicked `"Open original image"` -> protected `/content` fetch returned `200` and launched a `blob:` popup tab.
3. **Protected CSV Export (`#/import-export`)**:
   - Clicked `"Download Botanical identities CSV"` -> `/api/v1/exports/botanical-identities.csv` returned `200`; `exportDomLinks: 0`.
4. **R2 Screen Smoke (`#/native-ranges`, `#/taxonomy`)**:
   - Both views rendered cleanly under real session capability propagation (`consoleErrors: []`).
5. **Occurrence Tiles `401` & Cross-Owner Reset (`#/species-distribution` & `#/identities/<id>?tab=maps`)**:
   - Zoomed occurrence map after DB session revocation -> `sdUnauthorizedTiles: 3` (`401`) -> `#reauth-dialog` locked immediately -> same-owner unlock recovered cleanly.
   - Navigated to Identity Maps tab, opened occurrence map, revoked sessions, zoomed (`401`), and unlocked as `other-owner` -> `leakedTilesAfterOwnerSwitch: 0`.
6. **Service-Outage (`503`) Note**:
   - Real backend HTTP `401` invalidation and recovery were exercised end-to-end against PostgreSQL/FastAPI above; HTTP `503` transient backend unavailability and retry paths (distinct from `401` invalidation) are covered by Vitest unit/integration tests (`App.test.tsx`, `SessionRecovery.test.tsx`, `EvidenceTiles.test.ts`).
7. **Clean Resource Retirement**:
   - Stack retired via disposable harness (`ws_a_env.py down`) and verified via `make workflow-resources`: `RESOURCE_CLEANUP_PASSED` (`removed={"containers": 3, "images": 2, "networks": 1, "volumes": 2}`, `residual_containers_networks_volumes=0`, `retained_images=0`).

- **External local scratch artifacts (not repository files)**: `brain/c05760e3-f1a8-437f-ab38-604f6939176e/scratch/ws_a_final_e2e/` (`01_plant_draft_recovered_saved.png`, `02_media_protected_blob_and_original.png`, `03_cross_owner_clean_workspace.png`, `e2e_results.json`).
