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

2. **Request Lock, In-Flight Cancellation, Owner-Bound Capabilities & Epoch Fencing (`frontend/src/auth/api.ts`, `frontend/src/auth/AuthProvider.tsx`, `frontend/src/occurrence-map/EvidenceTiles.ts`, `frontend/src/occurrence-map/OccurrenceMapPanel.tsx`):**
   - `requestJson` enforces `AuthRequestLockedError` pre-fetch whenever the managed auth gate is locked (`attachAuthRequestGate` / `syncAuthRequestGate`).
   - `notifyProtectedUnauthorized(originatingEpoch)` centralizes managed HTTP 401 invalidation for both `requestJson` and protected binary/tile requests (`EvidenceTiles`): when `gate.managed && !gate.locked && gate.epoch === originatingEpoch`, it invokes `gate.onUnauthorized()` exactly once and returns `true`; locked or superseded epochs are ignored (`false`).
   - `isExpectedAuthCancellation(error)` identifies `AuthRequestLockedError`, `StaleAuthEpochError`, and `AbortError` so suspended effects treat local auth cancellation identically to abort rather than rendering false failure banners.
   - When `gate.managed` is active, `requestJson` binds each in-flight protected `fetch` to an epoch-scoped `AbortController` and verifies `staleForEpoch(originatingEpoch)` after response headers, after error-body parsing, on 204 responses, and after `response.json()`. Responses or delayed 401 errors from superseded epochs throw `StaleAuthEpochError` without altering the newer epoch's state or calling `onUnauthorized`. Unmanaged test callers retain their original `AbortSignal` reference.
   - **Owner-bound restoration & cross-owner request isolation barrier (`ProtectedRequestCapability` / `invalidateProtectedWorkspace`):**
     - `gate` tracks a monotonic `workspaceGeneration` and bound `ownerId`. `AuthProvider` distinguishes all five restoration boundaries explicitly:
       1. *Normal startup restoration (`restoreSession`):* starts with `invalidateProtectedWorkspace()`, then unlocks only with `ownerId: session.user_id`.
       2. *Same-owner recovery (`reauthenticate` with `session.user_id === retainedIdentity.user_id`):* preserves `workspaceKey`, `workspaceGeneration`, and `ownerId` so attached layers resume automatically when unlocked.
       3. *Different-owner authentication (`reauthenticate` with `session.user_id !== retainedIdentity.user_id`, or cold `logIn`):* synchronously executes `invalidateProtectedWorkspace()` **before** scheduling `setWorkspaceKey` or unlocking the gate for the replacement owner, advancing `workspaceGeneration`, clearing `ownerId`, revoking every active `ProtectedRequestCapability`, detaching old-owner invalidation subscriptions, and cancelling pending redraws, queued timers, and fetches so no former-owner layer can initiate any request even before React commits workspace teardown.
       4. *Explicit discard (`discardRetainedSession`):* synchronously executes `invalidateProtectedWorkspace()`, advances `workspaceKey`, and returns to cold unauthenticated state.
       5. *Logout (`logOut` / `cancelLogout`):* keeps same-owner generation while locked during logout request so `cancelLogout()` can resume if logout fails, and executes `invalidateProtectedWorkspace()` once logout is confirmed unauthenticated.
   - `EvidenceTiles` acquires a fail-closed `ProtectedRequestCapability` at construction time, captures `originatingEpoch = this.capability.getEpoch()` per tile load, ignores aborted/revoked/superseded 401s, triggers `this.capability.notifyUnauthorized(originatingEpoch)` on active current-epoch tile 401 before completing the job without duplicate notifications or unhandled rejections, aborts in-flight tiles and retry timers on lock or revocation, and redraws attached maps **only** when the same capability remains non-revoked for the unlocked owner and workspace generation.
   - `OccurrenceMapPanel` keeps `OccurrenceDensityMap` mounted while `.application-shell` is `hidden`/`inert` behind `#reauth-dialog`, ignores `isExpectedAuthCancellation(failure)`, and blocks `retryFailed` tile retries while unauthenticated.

3. **Native Top-Layer Modal Stacking & Workspace Locking (`frontend/src/App.tsx`):**
   - Retained `ApplicationShell` uses `isPresentationRetainedState(state)` directly inside `<Fragment key={auth.workspaceKey ?? 0}>`, preserving the `main > .application-shell` CSS selector without wrapping `.application-shell` in extra elements.
   - Note on baseline dialog architecture: `ModalDialog.tsx` does not exist on this codebase; `EditWorkspace.tsx` wraps `TaskDialog.tsx` using native `<dialog>.showModal()`. Neither `TaskDialog.tsx`, `EditWorkspace.tsx`, `LoginForm.tsx`, nor `WorkbenchShell.tsx` required modification.
   - `ReauthenticationDialog` renders a native modal `<TaskDialog id="reauth-dialog" dismissOnBackdrop={false}>` with a no-op `onClose` so Escape, Tab, and backdrop clicks cannot dismiss `#reauth-dialog` or the underlying editor.
   - `ReauthenticationDialog`'s parent `useLayoutEffect` sets `hidden`, `inert`, and `aria-hidden="true"` on `.application-shell` while locked and removes them during unmount cleanup before `TaskDialog` restores focus into the previously active editor control (`lastWorkspaceFocus` captured via `onFocusCapture`).

4. **Domain & Geographic Recovery Alignment (`frontend/src/`):**
   - Updated domain screens and panels (`PlantScreen.tsx`, `BotanicalIdentityScreen.tsx`, `BotanicalProfilePanel.tsx`, `BotanicalNativeRangeManager.tsx`, `NativeRangeEnrichmentPanel.tsx`, `EventJournal.tsx`, `PhotosSection.tsx`, `SeedLotScreen.tsx`, `SowingScreen.tsx`, `OrderScreen.tsx`, `SupplierScreen.tsx`, `LocationScreen.tsx`, `GeographyScreen.tsx`, `Cuttings/Cuttings.tsx`) to use `isPresentationRetainedState(auth.state)` for DOM retention, `activeCsrfToken(auth.state)` for mutation guards, stabilized `sessionExpired` effect dependencies so unlocking does not trigger spurious effect resets/re-fetches over dirty drafts, and idle saving-state resets on 401.
   - **Finding F1 (`frontend/src/species-distribution/SpeciesDistributionScreen.tsx`):** `SelectedIdentity` and `SpeciesDistributionScreen` now depend on `[authorized, ..., sessionExpired]` (`auth.state.status === "authenticated"`) rather than the mutable `auth` object, suspend effects when locked, treat `isExpectedAuthCancellation` (`AuthRequestLockedError`, `StaleAuthEpochError`, `AbortError`) and HTTP `401` as non-error suspension/expiry instead of triggering false error views (`_leaflet_pos` mid-zoom teardown avoided cleanly), keep loaded identity/map/directory state intact during lock, clear `failedQuery` on successful directory refresh and retry actions, and preserve genuine HTTP `404` / network error reporting.
   - **Finding F3 (`frontend/src/botanical-identities/IdentityMaps.tsx`):** Replaced `[identity.id, attempt, auth]` with `[authorized, identity.id, attempt, sessionExpired]`, suspended summary reads while locked, treated HTTP `401` and `isExpectedAuthCancellation` rejections inside `Promise.allSettled` as non-clobbering cancellations so previously valid summaries stay intact without false unavailability banners, resumed cleanly upon same-owner unlock, and preserved real partial/complete failure reporting.

## Changed Files

- Core auth & application shell:
  - `frontend/src/auth/context.ts`
  - `frontend/src/auth/api.ts`
  - `frontend/src/auth/AuthProvider.tsx`
  - `frontend/src/App.tsx`
- Occurrence map, Species Distribution & Identity Maps:
  - `frontend/src/occurrence-map/EvidenceTiles.ts`
  - `frontend/src/occurrence-map/OccurrenceMapPanel.tsx`
  - `frontend/src/species-distribution/SpeciesDistributionScreen.tsx`
  - `frontend/src/botanical-identities/IdentityMaps.tsx`
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
  - `frontend/src/species-distribution/SpeciesDistributionScreen.test.tsx`
  - `frontend/src/botanical-identities/IdentityMaps.test.tsx`
  - `docs/release/evidence/session-expiry-draft-recovery.md`

## Automated Frontend Verification

Executed inside the isolated `quality` container (`python3 ./scripts/workflow_environment.py quality compose -- run --rm --no-deps -T frontend ...`) after all code and test edits:

- `pnpm format:check` — passed (`All matched files use Prettier code style!`)
- `pnpm lint` (`eslint . --max-warnings 0`) — passed (`0` errors, `0` warnings)
- `pnpm typecheck` (`tsc -b --pretty false`) — passed (`0` errors)
- `pnpm test` — passed: **127 / 127 test files passed**, **1398 / 1398 tests passed** (0 failures, 0 skipped), including:
  - `src/auth/SessionRecovery.test.tsx` (10 tests): active-session 401 with modal `EditWorkspace`/`PlantScreen` draft retention, Escape/Tab modal trap, failed login lock retention & password clearing, same-user unlock with focus restoration and zero `PUT` auto-replay, zero `localStorage`/`sessionStorage` leaks, cross-user synchronous tree replacement (`MutationObserver` zero-transient-frame check), explicit discard & sign-out teardown, backend outage (`503` and network failure) recovery on manual retry, Scenarios A & B stale Epoch-1 200/401/body fencing, Scenario C cookie-op serialization, Scenario G `EvidenceTiles` abort + retry timer cancellation, tile-only HTTP 401 (with zero prior JSON API 401) triggering `#reauth-dialog` over an open dirty modal `PlantScreen` editor, deterministic F2 pre-commit race test proving attached former-owner `EvidenceTiles` cannot borrow Bob's session even when teardown is delayed (while same-owner recovery redraws automatically), and `BotanicalIdentityScreen` cross-domain draft retention.
  - `src/occurrence-map/EvidenceTiles.test.ts` (7 tests): tile caching, backoff retries & cancellation on `404`/`502`/`503`, current-epoch tile HTTP 401 notifying `notifyProtectedUnauthorized` once across concurrent sibling tiles and cancelling queued retries, stale-epoch and aborted-tile 401 ignoring, `204`/`404`/`409`/`503` preservation, and owner-bound capability isolation across same-owner unlock vs `invalidateProtectedWorkspace` owner switch.
  - `src/occurrence-map/OccurrenceMapPanel.test.tsx` (6 tests): density map mount retention across reauthentication lock with zero requests while locked, and local `AuthRequestLockedError` non-error handling.
  - `src/species-distribution/SpeciesDistributionScreen.test.tsx` (11 tests): loaded occurrence map and directory retention across locked recovery, non-error cancellation of `AuthRequestLockedError` / `StaleAuthEpochError`, clearing obsolete `failedQuery` on successful restoration/refresh, same-owner directory & map recovery, and genuine HTTP/network failure preservation.
  - `src/botanical-identities/IdentityMaps.test.tsx` (4 tests): preserving valid geographic summary status across locked recovery and `AuthRequestLockedError`/`401` cancellations, automatic refresh upon restoration, and genuine partial/complete failure reporting.
  - Existing auth, password-change, `App.test.tsx`, `DashboardSearch.test.tsx`, and domain suites preserved green.

## Live Browser & Stack Verification (Disposable Compose + Headless Chromium)

Verified on headless Chromium against isolated disposable seeded Compose stacks built from the final tree (`florabase-uat-preview-smoke-3ce7aa5e8575` for Scenarios A–D; `florabase-uat-preview-smoke-3408fe9b578a` for Scenario E):

1. **Scenarios A & B — Species Distribution zoom tile-only 401 & same-owner recovery (`#/species-distribution?identity=<id>`):**
   - Rendered represented identity with live seeded GBIF occurrence density map (`6 Represented identities`, `.leaflet-container` + `.leaflet-control-zoom-in`).
   - Revoked server sessions (`DELETE FROM auth_sessions`) and clicked `.leaflet-control-zoom-in` during settled state: recorded tile-only HTTP `401` (`jsonApiCalls: []`), `#reauth-dialog` opened (`:modal === true`), `.application-shell` became `hidden`/`inert`, loaded map stayed mounted (`mapMounted: true`), zero `[role="alert"]` errors appeared, and zero `_leaflet_pos` or other JS runtime/console errors occurred across Leaflet's zoom transition.
   - Reauthenticating as `"preview"` closed `#reauth-dialog`, restored the directory and map cleanly, loaded `12` fresh post-login tile responses (`[200, 204, 404]`), and left zero `[role="alert"]` banners.

2. **Scenario D — Identity Maps summary preservation & recovery (`#/identities/<id>?tab=maps`):**
   - Expanded `Inspect occurrence evidence` with all three summaries loaded (`2 structured entries recorded`, `GBIF`, `17 eligible mapped observations`).
   - Revoked sessions and clicked `.leaflet-control-zoom-in` -> `2` tile-only `401`s opened `#reauth-dialog` while loaded summaries remained intact with zero `"unavailable"` alerts.
   - Reauthenticating as `"preview"` restored tile loading and refreshed all summaries with zero false error notices.

3. **Scenario C — Different-owner reauthentication while former-owner map is attached (`#/identities/<id>?tab=maps`):**
   - With a synthetic second owner (`other-owner` / `Other Owner`) created strictly inside the disposable database and `"preview"`'s occurrence map mounted and expired behind `#reauth-dialog`, signed in as `other-owner`.
   - Captured HTTP trace across `POST /api/v1/auth/login`, `GET /api/v1/auth/session`, auth restoration, and teardown: **`tileRequestsAfterSwitch: []`** — zero former-owner tile requests were initiated using the replacement session; the replacement owner (`other-owner` / `Other Owner`) landed on a clean closed inspection workspace (`inspectionSectionExists: false`, `mapCount: 0`, `alerts: []`).

4. **Scenario E — Modal dirty Plant editor lifecycle (`#/plants`, `ws_a_browser_test.mjs`):**
   - Editing a Plant inside `dialog.edit-workspace-modal` with unsaved Label and Notes, revoking server sessions, and clicking `Save changes` opened `#reauth-dialog` (`:modal === true`, `.application-shell` `hidden`/`inert`), trapped Escape/Tab focus cleanly, cleared failed passwords while staying locked, emitted `[]` non-auth protected requests while locked, restored editor focus and dirty values for same-user login without auto-replaying `PUT`, persisted manual save with rotated CSRF, preserved drafts across backend `503`/outage without locking, cleared Alice's draft on `other-owner` switch, and tore down `.application-shell` on `"Discard unsaved changes and sign out"`.
   - **Runtime errors:** Zero browser runtime or console errors across all Scenarios A–E.

External local QA capture and script artifacts (not committed repository files):

- `brain/c05760e3-f1a8-437f-ab38-604f6939176e/scratch/ws_a_final_browser/01_species_distribution_tile401_locked.png` through `05_identity_maps_cross_owner_clean.png` and `final_browser_results.json`.
- `brain/c05760e3-f1a8-437f-ab38-604f6939176e/scratch/ws_a/01_before_expiry_modal_editor.png` through `08_after_discard_cold_login.png` and `browser_results.json`.

## Cleanup Evidence

- Disposable stacks retired cleanly with `ws_a_env.py down`:
  - `RESOURCE_CLEANUP_PASSED project=florabase-uat-preview-smoke-3ce7aa5e8575 removed={"containers": 3, "images": 2, "networks": 1, "volumes": 2} residual_containers_networks_volumes=0 retained_images=0 shared_build_cache=retained`
  - `RESOURCE_CLEANUP_PASSED project=florabase-uat-preview-smoke-3408fe9b578a removed={"containers": 3, "images": 2, "networks": 1, "volumes": 2} residual_containers_networks_volumes=0 retained_images=0 shared_build_cache=retained`
- Post-cleanup `make workflow-resources` showed zero residual containers, networks, or volumes from owned disposable stacks.

## Remaining Scope & Limitations

- Full backend pytest, PostgreSQL integration suite, production container build CI (`make ci` / `make feature-verify`), `docs/progress.md`, and `docs/features.json` remain intentionally untouched during Workstream A source freeze until operator/QA handoff.
- Single-owner installations remain the supported product model (`ck_users_initial_owner_only`); multi-user browser switching was exercised by inserting a synthetic second owner row solely inside the temporary disposable database in addition to the mocked multi-user unit/integration tests.
