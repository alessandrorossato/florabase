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
   - When `gate.managed` is active, `requestJson` binds each in-flight protected `fetch` to an epoch-scoped `AbortController` and verifies `staleForEpoch(originatingEpoch)` after response headers, after error-body parsing, on 204 responses, and after `response.json()`. Responses or delayed 401 errors from superseded epochs throw `StaleAuthEpochError` without altering the newer epoch's state or calling `onUnauthorized`. Unmanaged test callers retain their original `AbortSignal` reference.
   - `EvidenceTiles` subscribes to `subscribeAuthInvalidation` to abort in-flight tile fetches and clear scheduled `setTimeout` retry timers when locked, and checks `isProtectedRequestAuthorized()` + epoch equality before and during tile loading.
   - `OccurrenceMapPanel` unmounts `OccurrenceDensityMap` whenever `auth.state.status !== "authenticated"`.

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
  - `frontend/src/occurrence-map/OccurrenceMapPanel.test.tsx`
  - `docs/release/evidence/session-expiry-draft-recovery.md`

## Automated Frontend Verification

Executed inside the isolated `quality` container (`python3 ./scripts/workflow_environment.py quality compose -- run --rm --no-deps -T frontend ...`) after all code and test edits:

- `pnpm format:check` — passed (`All matched files use Prettier code style!`)
- `pnpm lint` (`eslint . --max-warnings 0`) — passed (`0` errors, `0` warnings)
- `pnpm typecheck` — passed (`0` errors)
- `pnpm test` — passed: **127 / 127 test files passed**, **1390 / 1390 tests passed** (0 failures, 0 skipped), including:
  - `src/auth/SessionRecovery.test.tsx` (8 tests): active-session 401 with modal `EditWorkspace`/`PlantScreen` draft retention, Escape/Tab modal trap, failed login lock retention & password clearing, same-user unlock with focus restoration and zero `PUT` auto-replay, zero `localStorage`/`sessionStorage` leaks, cross-user synchronous tree replacement (`MutationObserver` zero-transient-frame check), explicit discard & sign-out teardown, backend outage (`503` and network failure) recovery on manual retry, Scenarios A & B stale Epoch-1 200/401/body fencing, Scenario C cookie-op serialization, Scenario G `EvidenceTiles` abort + retry timer cancellation, and `BotanicalIdentityScreen` cross-domain draft retention.
  - `src/occurrence-map/OccurrenceMapPanel.test.tsx` (5 tests): density map suspension during reauthentication lock with zero requests while locked.
  - Existing auth, password-change (`AccountScreen.test.tsx`), `App.test.tsx`, `DashboardSearch.test.tsx`, and domain suites preserved green.

## Live Browser & Stack Verification (Disposable Compose + Headless Chromium)

Verified against an isolated disposable seeded Compose stack (`florabase-uat-preview-smoke-1b93a80c8eb8`, loopback HTTP Nginx -> FastAPI -> PostgreSQL, seeded via `scripts/uat_fixture.py seed`):

- **Modal stack & focus lock:** Editing a Plant record inside modal `EditWorkspace` (`dialog.edit-workspace-modal:modal === true`) with unsaved Label (`"Preview — Nursery aloe [unsaved draft]"`) and Notes (`"Unsaved G-CORE Step 10 browser note"`), revoking all server sessions (`DELETE FROM auth_sessions`), and clicking `Save changes` produced HTTP 401 and opened `#reauth-dialog` (`open === true`, `:modal === true`, focus inside `#reauth-dialog`, `.application-shell` direct child of `<main>` with `hidden`, `inert`, and `aria-hidden="true"`, underlying edit `<dialog>` still open, zero draft/secret entries in `localStorage`/`sessionStorage`).
- **Keyboard trap & failed attempt:** Real CDP `Escape` and repeated `Tab` presses left `#reauth-dialog` and underlying editor open with focus trapped inside `#reauth-dialog`. Submitting `"wrong-password-123"` kept `.application-shell` hidden/locked, cleared `#reauth-password`, and rendered the server rejection alert.
- **Zero protected traffic during lock:** CDP `Network.requestWillBeSent` confirmed `[]` non-auth `/api/v1/` requests between entering reauthentication lock and successful login.
- **Same-user unlock & manual save:** Reauthenticating as `"preview"` closed `#reauth-dialog`, restored `.application-shell` (`display: grid`, `inert: false`), kept `edit-workspace-modal` open as `:modal`, restored focus inside the edit dialog on `Save changes`, preserved both dirty Label and Notes fields, emitted zero automatic `PUT` replay on login, and persisted the updated Plant record on manual `Save changes`.
- **Backend outage & recovery (Scenario F):** Stopping the disposable `backend` container while editing `"Preview — Nursery aloe [outage draft]"` and clicking `Save changes` kept the session authenticated (no `#reauth-dialog`), displayed the actionable error alert, retained the dirty draft, and saved cleanly after restarting `backend` via manual retry.
- **Cross-user unlock (Scenario H):** With a synthetic second owner (`other-owner` / `Other Owner`) created strictly inside the isolated disposable DB, expiring `"preview"` with dirty draft `"Alice Cross-User Secret Draft"` and signing in as `other-owner` replaced the tree synchronously (`hasAliceDraft: false`, verified active session `"other-owner"` / `"Other Owner"`).
- **Explicit discard & logout:** Clicking `"Discard unsaved changes and sign out"` on `#reauth-dialog` destroyed `.application-shell` and the dirty `"Transient Discard Draft"`, rendering the cold login screen cleanly.
- **Runtime errors:** Zero browser runtime exceptions observed.

External local QA capture and script artifacts (not committed repository files):

- `brain/c05760e3-f1a8-437f-ab38-604f6939176e/scratch/ws_a/01_before_expiry_modal_editor.png` through `08_after_discard_cold_login.png` and `browser_results.json`.

## Cleanup Evidence

- Disposable stack retired with `ws_a_env.py down`: `RESOURCE_CLEANUP_PASSED project=florabase-uat-preview-smoke-1b93a80c8eb8 removed={"containers": 3, "images": 2, "networks": 1, "volumes": 2} residual_containers_networks_volumes=0 retained_images=0 shared_build_cache=retained`.

## Remaining Scope & Limitations

- Full backend pytest, PostgreSQL integration suite, production container build CI (`make ci` / `make feature-verify`), `docs/progress.md`, and `docs/features.json` were intentionally left untouched in this Workstream A source freeze step.
- Single-owner installations remain the supported product model (`ck_users_initial_owner_only`); multi-user browser switching was exercised by inserting a synthetic second owner row solely inside the temporary disposable database in addition to the mocked multi-user unit test.
