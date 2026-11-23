# ADR: MOBILE-001 — Capacitor Android Shell, Transport Architecture, and PWA Preservation

- **Status:** Proposed (spike implemented in `MOBILE-001`; `MOBILE-002` decisions open for owner sign-off)
- **Date:** 2026-11-22
- **Related:** [ADR 0005: Authentication and sessions](decisions/0005-authentication-and-sessions.md), [Android build & emulator guide](mobile.md)

## 1. Context and Owner Decisions

Florabase is a self-hosted botanical records application with a React/TypeScript frontend (`frontend/`), a FastAPI backend (`backend/`), and PostgreSQL. The browser Progressive Web App (PWA) is already deployed and verified.

The following owner decisions are fixed constraints for mobile work:

1. **Native direction:** Capacitor with the existing React UI **bundled into the app** (not loaded from `server.url`). Android first; iOS later from the same UI codebase.
2. **PWA stays first-class:** One React UI codebase serves both the PWA and the native shell. There is no UI fork in `mobile/`. Native-only capabilities live behind capability detection with web fallbacks where applicable.
3. **Distribution (initial):** Signed APK published via GitHub Releases and tracked with Obtainium (release signing and CI lanes are deferred to a later task).
4. **Roadmap awareness:** An offline capture queue is planned for a later task; this ADR designs how it will coexist with PWA invariants without implementing it yet.

`MOBILE-001` proves the Capacitor Android toolchain, TLS/CA trust configuration, native runtime isolation, and network constraints with **zero** backend, auth, CORS, or web behaviour changes.

## 2. Shell Architecture Comparison

| Approach | Summary | Decision |
| --- | --- | --- |
| **Capacitor with bundled React UI** | Packages `frontend/dist` inside the APK, serves it from a local WebView origin (`https://localhost`), and bridges native APIs (Preferences, secure storage, camera, filesystem) via Capacitor plugins. | **Chosen.** Single UI codebase, instant offline boot, full control over Android `network_security_config.xml` (user-installed NAS CAs), works on Android and iOS, and needs no Google Play Services. |
| **TWA (Trusted Web Activity)** | Wraps a remote HTTPS origin in a full-screen Chromium custom tab. | **Rejected.** Android-only; requires Digital Asset Links hosted on each server domain (untenable for arbitrary self-hosted NAS origins); depends on Chrome/browser provider; cannot add native storage/camera/scanner plugins. |
| **Capacitor `server.url` (remote WebView)** | Points the WebView directly at the user's remote server URL. | **Rejected.** Cannot boot offline or change servers cleanly; mixes arbitrary remote server HTML with native Capacitor bridge privileges; fails owner decision #1. |
| **React Native / Kotlin / Flutter** | Separate native/cross-platform UI implementation. | **Rejected.** Forks the UI into a second codebase, violating owner decision #2 and multiplying maintenance effort across every botanical domain screen. |

## 3. Native Runtime Detection and PWA Preservation Rules

To keep the PWA byte-for-byte faithful and avoid shipping Capacitor runtime code to web users:

1. **Zero `@capacitor/*` imports in `frontend/package.json`:** Native runtime detection in `frontend/src/mobile/runtime.ts` reads the `window.Capacitor` global injected by Capacitor's `native-bridge.js` (`window.Capacitor?.isNativePlatform?.() === true`). `@capacitor/core` and `@capacitor/preferences` live strictly in `mobile/package.json` and never enter the web bundle.
2. **Lazy code-splitting for native UI:** `frontend/src/main.tsx` checks `isNativeShell()`.
   - **Web / PWA (`false`):** Calls `registerServiceWorker()` (`/sw.js`) and renders `<App />` + `<UpdateNotice />` identically to before. The dynamic `import("./mobile/NativeServerOnboarding")` chunk is never requested, downloaded, parsed, or executed by web browsers.
   - **Native (`true`):** Skips `registerServiceWorker()` and skips `<UpdateNotice />` (which polls `/release.json` for nginx image upgrades and does not apply to a bundled APK), mounting the native shell instead.
3. **Preservation invariants for all future `MOBILE-*` work:**
   - Never fork domain screens or styles into `mobile/`.
   - Keep `frontend/public/sw.js`, `manifest.webmanifest`, `frontend/nginx.conf` CSP, and existing `frontend/src/pwa/*.test.ts` unmodified and green.
   - Every native capability (secure token storage, camera capture, barcode/QR scanning, share/export) must sit behind a small capability interface in `frontend/src/mobile/` with a graceful web fallback.

## 4. Observed Login Blockers from the Bundled Origin (`MOBILE-001` Findings)

Testing against the unmodified Florabase backend (`d7e056b`) confirms **five concrete controls** that intentionally block the existing browser login flow from a bundled Capacitor WebView (`Origin: https://localhost` on Android, `capacitor://localhost` on iOS):

1. **CORS disabled in production (and mismatched on direct FastAPI):**
   - `backend/src/florabase/core/config.py` (`validate_secure_production_settings`) explicitly rejects any non-empty `FLORABASE_CORS_ORIGINS` when `FLORABASE_ENVIRONMENT=production` (`"Production authentication requires same-origin CORS configuration"`).
   - `backend/src/florabase/main.py` only mounts `CORSMiddleware` when `settings.cors_origins` is non-empty.
   - Observed against direct FastAPI (`:8000`) with `Origin: https://localhost`: `OPTIONS /api/v1/auth/login` returns `400 Disallowed CORS origin` (or `405` when `CORSMiddleware` is not mounted), and `GET /api/v1/health` returns `200` with no `Access-Control-Allow-Origin` header, so WebView `fetch()` cannot read the response.
2. **Mixed Content in debug against HTTP dev servers:**
   - Capacitor Android defaults to `server.androidScheme: "https"`, so WebView runs at `https://localhost`. WebView `fetch()` to `http://10.0.2.2:5173` is blocked as mixed content unless native HTTP is used.
3. **Strict `Origin` check on auth endpoints (`require_origin`):**
   - `backend/src/florabase/auth/dependencies.py` (`require_origin`) requires exactly one ASCII `Origin` header matching `settings.canonical_origin` (`FLORABASE_CANONICAL_ORIGIN`) using `secrets.compare_digest`.
   - Observed against both Vite proxy (`:5173`) and FastAPI (`:8000`): `POST /api/v1/auth/login` with `Origin: https://localhost` **and** with no `Origin` header both fail with `HTTP 403 {"detail": "Request forbidden"}`. The same guard protects `POST /api/v1/auth/csrf` and every `require_csrf` mutation.
4. **`SameSite=Strict` + `__Host-` session cookie:**
   - `backend/src/florabase/auth/api.py` (`_session_response`) sets `__Host-florabase-session` with `Secure`, `HttpOnly`, `SameSite=Strict`, and `Path=/` (in dev, `florabase-session-dev` with `SameSite=Strict`).
   - Because `https://localhost` is cross-site to `https://<nas-hostname>` (and `http://10.0.2.2:5173`), WebView `fetch()` will not attach a `SameSite=Strict` cookie across origins even if CORS headers were added.
5. **CSRF synchronizer token coupled to cookies + `Origin`:**
   - `require_csrf` requires both `require_origin` and `X-CSRF-Token` bound to the cookie session, which cannot be satisfied from a different origin without weakening the browser CSRF contract.

*(For the unauthenticated `GET /api/v1/health` connectivity probe in `MOBILE-001`, the onboarding screen calls Capacitor's built-in `CapacitorHttp` plugin, which uses Android's `HttpURLConnection` directly — honoring `network_security_config.xml` without touching backend CORS or attempting cookie auth.)*

## 5. Recommended Transport & Authentication Architecture for `MOBILE-002`

Two candidate transports exist for `MOBILE-002`:

### Option A (Recommended): Opaque Bearer Device-Session Token + Scoped App-Origin CORS (`allow_credentials=False`)

- **How it works:**
  - Leave the existing browser/PWA cookie + CSRF + `require_origin` path **100% unchanged** (`__Host-florabase-session`, `SameSite=Strict`, `FLORABASE_CANONICAL_ORIGIN`, zero cross-origin credentials).
  - Introduce dedicated device-session endpoints (e.g. `POST /api/v1/auth/device/login`, `POST /api/v1/auth/device/logout`, `GET /api/v1/auth/device/sessions`, `DELETE /api/v1/auth/device/sessions/{id}`) that authenticate with login name + password (sharing the existing Argon2id verification and PostgreSQL login throttling) and return an opaque 256-bit random bearer token.
  - Store only the **SHA-256 digest** of the bearer token in PostgreSQL (alongside device label, platform, `last_seen_at`, idle/absolute expiry, and `revoked_at`), following the same opaque-session principle as [ADR 0005](decisions/0005-authentication-and-sessions.md) — no JWTs, immediate server-side revocation, automatic revocation on password change or account disablement.
  - On Android (and later iOS), persist the opaque bearer token in **hardware/OS-backed encrypted storage** (Android Keystore-backed EncryptedSharedPreferences / Capacitor secure storage plugin), never in `localStorage` or plain Preferences.
  - Attach `Authorization: Bearer <token>` on API calls from the native shell.
  - On the backend, update `require_authenticated_actor` / `require_csrf` cleanly:
    - If a request carries `Authorization: Bearer <token>` **and** a session cookie simultaneously, reject with `400`/`401` (no ambiguous dual-auth).
    - Cookie-authenticated requests keep the exact existing `require_origin` + `X-CSRF-Token` + `SameSite=Strict` checks with zero relaxation.
    - Bearer-authenticated requests do **not** use ambient browser cookies, so CSRF does not apply; they resolve the device session via constant-time hash lookup and enforce the same `AuthenticatedActor` / `require_owner` authorization rules.
  - **CORS for the bundled app origin:** Allow **only** the fixed native shell origins (`https://localhost` for Android, `capacitor://localhost` for iOS) with `allow_credentials=False`, `allow_headers=["Authorization", "Content-Type", "Idempotency-Key"]`, and explicit methods.
- **Security impact on the existing browser cookie+CSRF+Origin path:**
  - **Zero weakening.** Because `allow_credentials=False` is set for the native origins, browsers will never send `__Host-florabase-session` cross-origin even if a malicious process ran on `https://localhost`, and `SameSite=Strict` + `require_origin` + `X-CSRF-Token` remain intact for every browser session.
  - **Clean device lifecycle:** Mobile sessions can have a longer idle lifetime suitable for greenhouse/field use while being individually viewable and revocable from Settings -> Account on the web UI (if a phone is lost, revoke that device without invalidating desktop sessions).
  - **WebView `fetch()` compatibility:** Native `fetch()` works natively for 25 MiB multipart photo uploads, `AbortController`, protected image blob fetching (`useProtectedImage`), and Chrome DevTools network inspection.
- **Residual risk & mitigation:**
  - In WebView `fetch()`, the bearer token is held in JS memory to set the `Authorization` header. Risk of exfiltration via XSS is mitigated by the bundled static UI (no user-supplied scripts, strict CSP, React escaping) and by never persisting the token in Web Storage.

### Option B (Not Recommended): `CapacitorHttp` Patching + Cookies

- **How it works:** Enable Capacitor's global `CapacitorHttp` fetch/XHR patch so requests bypass WebView CORS and rely on Android's native `CookieManager` to store and replay `__Host-florabase-session`.
- **Why rejected:**
  1. **Origin guard conflict:** `require_origin` still rejects missing or mismatched `Origin` headers. Working around it requires either spoofing `Origin: <serverUrl>` from the client (an anti-pattern that undermines `Origin` trust) or relaxing `require_origin` on cookie routes (weakening browser CSRF defense-in-depth).
  2. **Transport fragility:** Global `CapacitorHttp` interception of `window.fetch` has recurring incompatibilities with multipart `FormData` binary uploads (Florabase supports 25 MiB photo attachments), `Blob` responses (`useProtectedImage`), `AbortSignal`, and DevTools visibility.
  3. **Mismatched session model:** Reusing browser cookies forces mobile devices into the 24-hour browser idle timeout and prevents per-device naming or selective revocation without conflating browser tabs and phones.
  4. **Cookie jar edge cases:** Synchronizing `__Host-` + `SameSite=Strict` cookies across WebView and native `HttpURLConnection` cookie stores across Android WebView updates is brittle.

**Recommendation:** Adopt **Option A (Opaque Bearer Device-Session Token + `allow_credentials=False` CORS for `https://localhost` and `capacitor://localhost`)** in `MOBILE-002`, formally amending [ADR 0005](decisions/0005-authentication-and-sessions.md).

## 6. App / Server Version Compatibility Model

Self-hosted servers and mobile APKs upgrade on **independent schedules** (a user's phone may update via Obtainium before their home NAS container is upgraded, or vice versa).

Currently:
- `GET /api/v1/health` (`backend/src/florabase/api/health.py`) returns only `{"status": "ok"}`.
- `/release.json` is an nginx-only static file built into the frontend container image (`frontend/Dockerfile`); it is absent in dev and is not an API contract.

### Proposed contract for `MOBILE-002`

Expose a small, unauthenticated JSON contract (either by extending `GET /api/v1/health` backwards-compatibly or adding `GET /api/v1/system/compatibility` — see Open Decisions below):

```json
{
  "status": "ok",
  "server_version": "0.2.0",
  "api_version": 1,
  "min_client_version": "0.1.0",
  "capabilities": ["device_auth_v1"]
}
```

Rules:
- **`api_version`** (integer): Major wire-protocol version (`1` for `/api/v1`). Bumped only on breaking API changes.
- **`min_client_version`** (SemVer): Lowest mobile app version supported by this server. If `appVersion < min_client_version`, the app blocks write flows and displays a clear prompt to update the APK (GitHub Releases / Obtainium).
- **`capabilities`** (string list): Additive feature tokens (e.g. `"device_auth_v1"`, later `"offline_outbox_v1"`). Allows a newer app to detect an older server cleanly (e.g. *"Your Florabase server does not yet support mobile app sign-in; upgrade your server to vX.Y"*) instead of failing with opaque 404s.
- **Unauthenticated disclosure check:** Keep the payload minimal (no database versions, internal paths, user counts, or hostnames) so it passes Florabase's security disclosure checks.

## 7. F-Droid & FOSS Distribution Constraints

Even though initial distribution is a signed APK on GitHub Releases + Obtainium, keeping the Android project F-Droid-clean from day one avoids expensive rewrites later:

1. **Zero Google Play Services / proprietary SDKs:** No `com.google.gms:*`, no Firebase/FCM, no ML Kit, no Play Integrity, no proprietary analytics or crash reporters.
   - In `MOBILE-001`, the default Capacitor template's `com.google.gms:google-services` Gradle plugin classpath and `google-services.json` hook were explicitly removed from `mobile/android/build.gradle` and `mobile/android/app/build.gradle`.
   - Local emulator verification runs on a pure AOSP image (`system-images;android-36;default;x86_64`) without Google APIs.
2. **FOSS native plugins only:** Future QR/label scanning must use FOSS decoders (e.g. ZXing / CameraX + open-source decoder), never Google ML Kit Barcode Scanning.
3. **Reproducible / clean source builds:** Pin all npm/pnpm and Gradle dependencies; commit no prebuilt `.aar`/`.jar` binaries; keep release keystore material strictly outside the repository.

## 8. Shared-Layer Offline Capture Outbox (Roadmap Design — Not Implemented in `MOBILE-001`)

Florabase's PWA service worker (`frontend/public/sw.js`) enforces strict security invariants:
- **Never** cache `/api/*` responses (no private collection data in Cache Storage).
- **Never** cache auth, CSRF, or session endpoints.
- **Never** intercept or cache HTTP mutations (`POST`, `PUT`, `PATCH`, `DELETE`).
- `/offline.html` stays strictly static with zero private data.

When the offline capture queue is built in a later milestone, it **must not weaken `sw.js`**:

1. **Leave `sw.js` untouched:** Do not use Background Sync in `sw.js` or cache API reads/mutations inside the service worker.
2. **Own the outbox in the shared application layer (`frontend/src/offline-outbox/`):**
   - Store only **explicitly queued outgoing capture items** (e.g. a field observation note, quick harvest/cutting draft, or captured plant photo waiting for upload), behind a small storage adapter:
     - **PWA:** IndexedDB (same-origin, user-visible queue badge and review/discard controls).
     - **Native app:** IndexedDB + Capacitor Filesystem (or SQLite) for larger photo blobs so OS memory pressure does not drop queued photos.
   - **Idempotency:** Every queued item carries a client-generated UUIDv7 `Idempotency-Key` header so retries after flaky greenhouse connectivity never create duplicate records on the backend.
   - **Explicit flush & conflict UX:** Flush runs in application code when connectivity returns (and manually via a "Sync now" action), surfacing per-item validation/conflict errors rather than failing silently.
   - **Session boundary:** Logout, device revocation, or password change wipes or locks the outbox so queued photos/notes cannot leak across accounts.

## 9. Open Decisions for `MOBILE-002` (For Owner Sign-Off)

1. **Confirm Option A (Opaque Bearer Device-Session Token + scoped `allow_credentials=False` CORS)** as an amendment to [ADR 0005](decisions/0005-authentication-and-sessions.md).
2. **CORS configuration policy in production:** Should `https://localhost` and `capacitor://localhost` (strictly `allow_credentials=False`, never wildcard) be enabled automatically when mobile device auth is enabled, or gated behind an explicit environment opt-in such as `FLORABASE_ENABLE_MOBILE_AUTH=true`?
3. **Device session lifetimes & limits:** Proposed defaults: 30-day idle expiry, 180-day absolute expiry (vs 24h / 30d for browser cookies), optional max active devices per user, and mandatory revocation on password change.
4. **Compatibility endpoint shape:** Extend `GET /api/v1/health` with optional `server_version`, `api_version`, `min_client_version`, and `capabilities` fields, or keep `/api/v1/health` minimal (`{"status": "ok"}`) and add a separate `GET /api/v1/system/info` endpoint?
5. **Android Keystore plugin choice:** Choose the maintained FOSS Capacitor plugin (or small in-repo Kotlin/Java Capacitor plugin backed directly by AndroidX `EncryptedSharedPreferences` / Keystore — zero third-party native dependency risk) for storing the device bearer token.
6. **Android application ID:** `MOBILE-001` uses `org.florabase.app` as a placeholder; confirm the permanent `applicationId` before signing the first distributed APK (changing `applicationId` later breaks upgrades in Obtainium and F-Droid).
