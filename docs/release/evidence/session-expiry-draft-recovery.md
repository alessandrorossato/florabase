# Session Expiry Draft Recovery & Reauthentication (Workstream A)

## Scope & Branch Identity

- Branch: `fix/session-expiry-draft-recovery`
- Base commit: `fdc75e83fa8818cab791ed82cbba65f4f97db7ae`
- Writer identity: `hydrogen-b-session-recovery` (`0d09f6e4c3cb`)
- Objective: Resolve G-CORE Step 10 so an HTTP 401 session expiration during active editing preserves in-memory unsaved edits behind a modal reauthentication dialog, while enforcing all SECURITY-002 and ENG-01 security invariants.

## Architecture & State Transitions

1. **Authentication & Recovery State (`frontend/src/auth/context.ts`, `frontend/src/auth/AuthProvider.tsx`):**
   - Extended `AuthState` on `"unauthenticated"` and `"submitting-login"` with an optional `retainedIdentity?: RetainedOwnerIdentity` (`user_id`, `login_name`, `display_name`).
   - Added `workspaceKey`, `reauthenticate(payload)`, and `discardRetainedSession()` to `AuthContextValue`, while preserving `status === "unauthenticated"` semantics for ENG-01 password-change revocation (`AccountScreen.test.tsx`).
   - On active-session expiration (`expireAuthenticatedSession`), the client immediately clears the active CSRF token and previous authority, increments the authentication epoch (`authEpochRef`), locks the protected request gate (`syncAuthRequestGate({ locked: true, advanceEpoch: true })`), and enters unauthenticated reauthentication state retaining only non-secret display identity.
   - `cookieOpQueue` (`enqueueCookieOp`) serializes all cookie-mutating operations (`logIn`, `reauthenticate`, `discardRetainedSession`, `logOut`, and `submitPassword`) so concurrent calls cannot interleave or corrupt the active session.
   - On `reauthenticate` (`POST /api/v1/auth/login` -> `GET /api/v1/auth/session` / `csrf_token`):
     - **Same `user_id`:** Unlocks the auth gate at a new epoch with the fresh CSRF token while keeping `workspaceKey` unchanged so the live retained React tree and dirty form controls remain intact. Failed saves are never auto-replayed.
     - **Different `user_id`:** Increments `workspaceKey` synchronously in the same commit as setting authenticated state (`<Fragment key={auth.workspaceKey ?? 0}>`), destroying the prior owner's React subtree without any transient frame exposing old-owner content.
   - Explicit `discardRetainedSession()` and `logOut()` advance `workspaceKey`, lock the auth gate, and replace the retained tree with the cold login screen.
   - No form drafts, CSRF tokens, or credentials are ever written to `localStorage` or `sessionStorage`.

2. **Request Lock, In-Flight Cancellation & Epoch Fencing (`frontend/src/auth/api.ts`, `frontend/src/occurrence-map/EvidenceTiles.ts`, `frontend/src/occurrence-map/OccurrenceMapPanel.tsx`):**
   - `requestJson` enforces `AuthRequestLockedError` pre-fetch whenever the managed auth gate is locked (`attachAuthRequestGate` / `syncAuthRequestGate`).
   - `notifyProtectedUnauthorized(originatingEpoch)` centralizes managed HTTP 401 invalidation for both `requestJson` and protected binary/tile requests (`EvidenceTiles`): when `gate.managed && !gate.locked && gate.epoch === originatingEpoch`, it invokes `gate.onUnauthorized()` exactly once and returns `true`; locked or superseded epochs are ignored (`false`).
   - When `gate.managed` is active, `requestJson` binds each in-flight protected `fetch` to an epoch-scoped `AbortController` and verifies `staleForEpoch(originatingEpoch)` after response headers, after error-body parsing, on 204 responses, and after `response.json()`. Responses or delayed 401 errors from superseded epochs throw `StaleAuthEpochError` without altering the newer epoch's state or calling `onUnauthorized`. Unmanaged test callers retain their original `AbortSignal` reference.
   - `EvidenceTiles` captures `const originatingEpoch = getProtectedAuthEpoch()` at tile load start, ignores aborted or superseded-epoch 401 responses, and on an active current-epoch un-aborted tile HTTP 401 invokes `notifyProtectedUnauthorized(originatingEpoch)` before marking the job done without throwing unhandled rejections, retrying while locked, or issuing duplicate notifications across concurrent sibling tiles; `subscribeAuthInvalidation` immediately cancels in-flight tile fetches and queued retry timers, suspends `retryFailed()`, and redraws cleanly once reauthentication restores the session while attached.
   - `OccurrenceMapPanel` keeps `OccurrenceDensityMap` mounted while `.application-shell` is `hidden`/`inert` behind `#reauth-dialog` (avoiding mid-transition Leaflet teardown failures) and blocks `retryFailed` tile retries until `auth.state.status === "authenticated"`.

3. **Native Top-Layer Modal Stacking & Workspace Locking (`frontend/src/App.tsx`):**
   - Retained `ApplicationShell` uses `isPresentationRetainedState(state)` directly inside `<Fragment key={auth.workspaceKey ?? 0}>`, preserving the `main > .application-shell` CSS selector without wrapping `.application-shell` in extra elements.
   - Note on baseline dialog architecture: `ModalDialog.tsx` does not exist on this codebase; `EditWorkspace.tsx` wraps `TaskDialog.tsx` using native `<dialog>.showModal()`. Neither `TaskDialog.tsx`, `EditWorkspace.tsx`, `LoginForm.tsx`, nor `WorkbenchShell.tsx` required modification.
   - `ReauthenticationDialog` renders a native modal `<TaskDialog id="reauth-dialog" dismissOnBackdrop={false}>` with a no-op `onClose` so Escape, Tab, and backdrop clicks cannot dismiss `#reauth-dialog` or the underlying editor.
   - `ReauthenticationDialog`'s parent `useLayoutEffect` sets `hidden`, `inert`, and `aria-hidden="true"` on `.application-shell` while locked and removes them during unmount cleanup before `TaskDialog` restores focus into the previously active editor control (`lastWorkspaceFocus` captured via `onFocusCapture`).

4. **Domain Editor Guard Alignment (`frontend/src/`):**
   - Updated domain screens and panels (`PlantScreen.tsx`, `BotanicalIdentityScreen.tsx`, `BotanicalProfilePanel.tsx`, `BotanicalNativeRangeManager.tsx`, `NativeRangeEnrichmentPanel.tsx`, `EventJournal.tsx`, `PhotosSection.tsx`, `SeedLotScreen.tsx`, `SowingScreen.tsx`, `OrderScreen.tsx`, `SupplierScreen.tsx`, `LocationScreen.tsx`, `GeographyScreen.tsx`, `Cuttings/Cuttings.tsx`) to use `isPresentationRetainedState(auth.state)` for DOM retention, `activeCsrfToken(auth.state)` for mutation guards, stabilized `sessionExpired` effect dependencies so unlocking does not trigger spurious effect resets/re-fetches over dirty drafts, and idle saving-state resets on 401.

## Changed Files

- Core auth & application shell:
  - `frontend/src/auth/context.ts`
  - `frontend/src/auth/api.ts`
  - `frontend/src/auth/AuthProvider.tsx`
  - `frontend/src/App.tsx`
- Occurrence map & tile cancellation:
  - `frontend/src/occurrence-map/EvidenceTiles.ts`
  - `frontend/src/occurrence-map/OccurrenceMapPanel.tsx`
- Domain screens & panels:
  - `frontend/src/plants/PlantScreen.tsx`
  - `frontend/src/botanical-identities/BotanicalIdentityScreen.tsx`
  - `frontend/src/botanical-profiles/BotanicalProfilePanel.tsx`
  - `frontend/src/botanical-profiles/BotanicalNativeRangeManager.tsx`
  - `frontend/src/botanical-profiles/NativeRangeEnrichmentPanel.tsx`
  - `frontend/src/events/EventJournal.tsx`
  - `frontend/src/photos/PhotosSection.tsx`
  - `frontend/src/seed-lots/SeedLotScreen.tsx`
  - `frontend/src/sowings/SowingScreen.tsx`
  - `frontend/src/orders/OrderScreen.tsx`
  - `frontend/src/suppliers/SupplierScreen.tsx`
  - `frontend/src/locations/LocationScreen.tsx`
  - `frontend/src/geographic-places/GeographyScreen.tsx`
  - `frontend/src/ui-pages/Cuttings/Cuttings.tsx`
- Regression tests & evidence:
  - `frontend/src/auth/SessionRecovery.test.tsx` (new)
  - `frontend/src/occurrence-map/EvidenceTiles.test.ts`
  - `frontend/src/occurrence-map/OccurrenceMapPanel.test.tsx`
  - `docs/release/evidence/session-expiry-draft-recovery.md`

## Automated Frontend Verification

Executed inside the isolated `quality` container (`python3 ./scripts/workflow_environment.py quality compose -- run --rm --no-deps -T frontend ...`) after all code and test edits:

- `pnpm format:check` — passed (`All matched files use Prettier code style!`)
- `pnpm lint` (`eslint . --max-warnings 0`) — passed (`0` errors, `0` warnings)
- `pnpm typecheck` — passed (`0` errors)
- `pnpm test` — passed: **127 / 127 test files passed**, **1393 / 1393 tests passed** (0 failures, 0 skipped), including:
  - `src/auth/SessionRecovery.test.tsx` (9 tests): active-session 401 with modal `EditWorkspace`/`PlantScreen` draft retention, Escape/Tab modal trap, failed login lock retention & password clearing, same-user unlock with focus restoration and zero `PUT` auto-replay, zero `localStorage`/`sessionStorage` leaks, cross-user synchronous tree replacement (`MutationObserver` zero-transient-frame check), explicit discard & sign-out teardown, backend outage (`503` and network failure) recovery on manual retry, Scenarios A & B stale Epoch-1 200/401/body fencing, Scenario C cookie-op serialization, Scenario G `EvidenceTiles` abort + retry timer cancellation, tile-only HTTP 401 (with zero prior JSON API 401) triggering `#reauth-dialog` over an open dirty modal `PlantScreen` editor with same-user recovery and different-user synchronous teardown, and `BotanicalIdentityScreen` cross-domain draft retention.
  - `src/occurrence-map/EvidenceTiles.test.ts` (6 tests): tile caching, backoff retries & cancellation on `404`/`502`/`503`, current-epoch tile HTTP 401 notifying `notifyProtectedUnauthorized` once across concurrent sibling tiles and cancelling queued retries, stale-epoch tile HTTP 401 ignored after epoch advance, aborted/unloaded tile HTTP 401 ignored without triggering invalidation, and non-401 (`204`/`404`/`409`/`503`) preservation.
  - `src/occurrence-map/OccurrenceMapPanel.test.tsx` (5 tests): density map mount retention across reauthentication lock without issuing protected tile requests or retries while locked.
  - Existing auth, password-change (`AccountScreen.test.tsx`), `App.test.tsx`, `DashboardSearch.test.tsx`, and domain suites preserved green.

## Live Browser & Stack Verification (Disposable Compose + Headless Chromium)

1. **Modal form & session lifecycle suite (`florabase-uat-preview-smoke-30ea309a00fc`, re-verified after P2 fix):**
   Verified against an isolated disposable seeded Compose stack (`florabase-uat-preview-smoke-30ea309a00fc`, loopback HTTP Nginx -> FastAPI -> PostgreSQL, seeded via `scripts/uat_fixture.py seed`; initial pre-remediation pass also ran against `florabase-uat-preview-smoke-1b93a80c8eb8`):
   - **Modal stack & focus lock:** Editing a Plant record inside modal `EditWorkspace` (`dialog.edit-workspace-modal:modal === true`) with unsaved Label (`"Preview — Nursery aloe [unsaved draft]"`) and Notes (`"Unsaved G-CORE Step 10 browser note"`), revoking all server sessions (`DELETE FROM auth_sessions`), and clicking `Save changes` produced HTTP 401 and opened `#reauth-dialog` (`open === true`, `:modal === true`, focus inside `#reauth-dialog`, `.application-shell` direct child of `<main>` with `hidden`, `inert`, and `aria-hidden="true"`, underlying edit `<dialog>` still open, zero draft/secret entries in `localStorage`/`sessionStorage`).
   - **Keyboard trap & failed attempt:** Real CDP `Escape` and repeated `Tab` presses left `#reauth-dialog` and underlying editor open with focus trapped inside `#reauth-dialog`. Submitting `"wrong-password-123"` kept `.application-shell` hidden/locked, cleared `#reauth-password`, and rendered the server rejection alert.
   - **Zero protected traffic during lock:** CDP `Network.requestWillBeSent` confirmed `[]` non-auth `/api/v1/` requests between entering reauthentication lock and successful login.
   - **Same-user unlock & manual save:** Reauthenticating as `"preview"` closed `#reauth-dialog`, restored `.application-shell` (`display: grid`, `inert: false`), kept `edit-workspace-modal` open as `:modal`, restored focus inside the edit dialog on `Save changes`, preserved both dirty Label and Notes fields, emitted zero automatic `PUT` replay on login, and persisted the updated Plant record on manual `Save changes`.
   - **Backend outage & recovery (Scenario F):** Stopping the disposable `backend` container while editing `"Preview — Nursery aloe [outage draft]"` and clicking `Save changes` kept the session authenticated (no `#reauth-dialog`), displayed the actionable error alert, retained the dirty draft, and saved cleanly after restarting `backend` via manual retry.
   - **Cross-user unlock (Scenario H):** With a synthetic second owner (`other-owner` / `Other Owner`) created strictly inside the isolated disposable DB, expiring `"preview"` with dirty draft `"Alice Cross-User Secret Draft"` and signing in as `other-owner` replaced the tree synchronously (`hasAliceDraft: false`, verified active session `"other-owner"` / `"Other Owner"`).
   - **Explicit discard & logout:** Clicking `"Discard unsaved changes and sign out"` on `#reauth-dialog` destroyed `.application-shell` and the dirty `"Transient Discard Draft"`, rendering the cold login screen cleanly.
   - **Runtime errors:** Zero browser runtime exceptions observed.

2. **Tile-only HTTP 401 browser reproduction (`florabase-uat-preview-smoke-30ea309a00fc`, after P2 fix):**
   With a synthetic `ExternalTaxonLink` (GBIF) and `ExternalProviderCache` (`occurrence-v1:`) entry seeded strictly inside the disposable database for the first `BotanicalIdentity`, navigated to `#/identities/<id>?tab=maps` and expanded `Inspect occurrence evidence`, waited for initial tiles to settle, revoked server sessions (`DELETE FROM auth_sessions`), and clicked `.leaflet-control-zoom-in`:
   - **Tile-only 401 trigger:** CDP network capture recorded `3` HTTP `401` responses strictly on `/api/v1/botanical-identities/<id>/occurrence-map/tiles/...` with zero JSON API requests (`jsonApiCallsBeforeLock: []`) between revoke and lock activation.
   - **Lock & zero retry traffic:** `#reauth-dialog` opened immediately (`reauthModal: true`), `.application-shell` became `hidden`, `inert`, and `aria-hidden="true"`, and `eventsWhileLocked` was `[]` (no retries or additional protected requests while locked).
   - **Same-user unlock & tile recovery:** Reauthenticating as `"preview"` restored `.application-shell`, kept `.leaflet-container` mounted (`mapRestored: true`), and loaded `8` fresh post-login tile responses cleanly with zero console or runtime exceptions.

External local QA capture and script artifacts (not committed repository files):

- `brain/c05760e3-f1a8-437f-ab38-604f6939176e/scratch/ws_a/01_before_expiry_modal_editor.png` through `08_after_discard_cold_login.png` and `browser_results.json`.
- `brain/c05760e3-f1a8-437f-ab38-604f6939176e/scratch/ws_a_tile401/01_map_before_tile_401.png` through `03_map_recovered_after_reauth.png`.

## Cleanup Evidence

- Both disposable stacks were cleanly retired with `ws_a_env.py down`:
  - `RESOURCE_CLEANUP_PASSED project=florabase-uat-preview-smoke-1b93a80c8eb8 removed={"containers": 3, "images": 2, "networks": 1, "volumes": 2} residual_containers_networks_volumes=0 retained_images=0 shared_build_cache=retained`
  - `RESOURCE_CLEANUP_PASSED project=florabase-uat-preview-smoke-30ea309a00fc removed={"containers": 3, "images": 2, "networks": 1, "volumes": 2} residual_containers_networks_volumes=0 retained_images=0 shared_build_cache=retained`
- Post-cleanup `make workflow-resources` showed zero residual containers, networks, or volumes from the disposable stacks.

## Remaining Scope & Limitations

- Full backend pytest, PostgreSQL integration suite, production container build CI (`make ci` / `make feature-verify`), `docs/progress.md`, and `docs/features.json` were intentionally left untouched in this Workstream A source freeze step.
- Single-owner installations remain the supported product model (`ck_users_initial_owner_only`); multi-user browser switching was exercised by inserting a synthetic second owner row solely inside the temporary disposable database in addition to the mocked multi-user unit test.
- Note on out-of-scope route screens (`SpeciesDistributionScreen.tsx` / `IdentityMaps.tsx`): `SpeciesDistributionScreen.tsx` (unchanged outside approved remediation paths) includes `auth` in its `useEffect` dependency list (`[id, scope, attempt, auth]` and `[q, scope, offset, queryKey, auth]`); if a zoom-triggered tile `401` locks `auth` during an active Leaflet zoom transition on `#/geography/species-distribution?identity=<id>`, the screen re-runs `getRepresentedIdentity`, catches `AuthRequestLockedError` as an error state, and unmounts `OccurrenceMapPanel` mid-transition, which triggers Leaflet's internal `_leaflet_pos` transition-end callback error even though `#reauth-dialog` still engages safely. On `#/identities/<id>?tab=maps`, `IdentityMaps.tsx` (`[identity.id, attempt, auth]`) similarly marks geographic summary checks errored when `auth` changes, while keeping `<ExternalBotanicalDataPanel>` and `<OccurrenceMapPanel>` mounted without errors.
