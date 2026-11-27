# ADR 0011: Mobile device sessions (Bearer transport) and native compatibility contract

Status: accepted. Amends [ADR 0005](0005-authentication-and-sessions.md) for the Capacitor Android
client introduced in [`MOBILE-001`](../archive/MOBILE-001/mobile-001-adr.md). Browser/PWA authentication remains
unchanged.

## Context

The Capacitor Android app bundles the React frontend locally and serves it from the WebView origin
`https://localhost` (and `capacitor://localhost` on future iOS builds). As verified in
[`MOBILE-001`](../archive/MOBILE-001/mobile-001-adr.md), the browser authentication model in
[ADR 0005](0005-authentication-and-sessions.md) (`__Host-florabase-session` cookie with
`SameSite=Strict`, synchronizer `X-CSRF-Token`, and `Origin == FLORABASE_CANONICAL_ORIGIN`)
intentionally prevents cross-origin cookie transmission and cannot authenticate a locally bundled
native WebView against an operator's remote self-hosted Florabase server.

Florabase's Progressive Web App (PWA) remains a first-class channel. Adding mobile sign-in must not
weaken browser CSRF defenses, weaken `SameSite=Strict`, introduce wildcard or credentialed CORS,
store secrets in WebView storage, or add deprecated/third-party Android security dependencies.

## Decision

### 1. Opaque Bearer device sessions (Option A)

- Extend the existing PostgreSQL `auth_sessions` table with `transport` (`'cookie'` or `'bearer'`,
  default `'cookie'`), `device_label` (nullable `VARCHAR(120)`, required non-blank for `'bearer'`
  and `NULL` for `'cookie'`), and nullable `csrf_digest` (`NULL` for `'bearer'`, 32-byte digest
  required for `'cookie'`), enforced by database `CHECK` constraints (`alembic` revision
  `20261123_0048`).
- `POST /api/v1/auth/device-sessions` authenticates an owner using the same Argon2id verification and
  shared `LoginThrottle` backoff state as `POST /api/v1/auth/login`, generates a 256-bit
  cryptographically random opaque token, stores only its SHA-256 digest in `auth_sessions`, and
  returns the token once with `Cache-Control: no-store` and no `Set-Cookie` header.
- The endpoint accepts **only `Content-Type: application/json`** (`415 Unsupported Media Type`
  otherwise) via `AuthSafetyMiddleware` (`STRICT_JSON_PATHS`), preventing cross-site simple HTML
  form `POST`s. Requests that also carry a browser session cookie are rejected (`401`).
- Native API requests authenticate with `Authorization: Bearer <token>` and `credentials: "omit"`.
  Because Bearer tokens are explicit non-ambient credentials, CSRF tokens and browser `Origin`
  equality checks are bypassed **only** when the authenticated actor's transport is `'bearer'`.
- **Strict transport isolation:**
  - Sending both a session cookie and an `Authorization` header on any authenticated request is
    rejected with `401 Unauthorized` and `WWW-Authenticate: Bearer`.
  - Invalid, malformed, expired, or revoked Bearer tokens return `401 Unauthorized` with
    `WWW-Authenticate: Bearer`.
  - A cookie session token replayed as `Bearer` is rejected (`401`); a Bearer token placed in the
    session cookie is rejected (`401`).
  - Browser-only endpoints (`POST /api/v1/auth/password`, `POST /api/v1/auth/csrf`,
    `POST /api/v1/auth/logout`) reject Bearer actors with `403 Forbidden`.
  - `DELETE /api/v1/auth/device-sessions/current` is Bearer-only (`403` for cookie actors).
- **Logging hygiene:** `Authorization` headers are never logged by `uvicorn.access`
  (`florabase/core/logging.py`), `AuthSafetyMiddleware`, `nginx.conf` (`florabase_auth`), or
  exception handlers.

### 2. Lifetimes, active-session cap, and revocation

- Device sessions have a **30-day idle timeout** (`2,592,000` seconds) and a **180-day absolute
  lifetime** (`15,552,000` seconds). Browser cookie lifetimes remain unchanged (24h idle / 30d
  absolute).
- Active Bearer device sessions are capped at **20 per user** (`device_session_max_active = 20`). To
  serialize concurrent device logins for the same user and prevent race conditions from exceeding the
  cap, `_issue_device_session` acquires the per-user lock first (`users` row `FOR NO KEY UPDATE` via
  `_locked_user`, matching `change_password`) before locking active Bearer rows in deterministic
  order (`ORDER BY auth_sessions.id FOR UPDATE`) and evicting the oldest-seen active session.
- Settings → Account lists active device sessions (`GET /api/v1/auth/device-sessions`) in both the
  PWA and the Android app for any authenticated user (scoped to `actor.user_id`; cross-user session
  IDs return `404`), showing device label, created timestamp, last-seen timestamp, and a "This
  device" badge when applicable, with per-device revocation
  (`DELETE /api/v1/auth/device-sessions/{session_id}`), current-device sign-out
  (`DELETE /api/v1/auth/device-sessions/current`), and revoke-all
  (`DELETE /api/v1/auth/device-sessions`).
- Changing the owner password (browser-cookie-only in `MOBILE-002`) revokes **all** sessions for the
  user — both browser sessions and all active mobile device sessions.

### 3. Automatic scoped native CORS (no operator env flag)

- `NativeAppCorsMiddleware` (`backend/src/florabase/core/cors.py`) is enabled automatically in all
  environments, including `Environment.PRODUCTION`, without relaxing the existing `config.py` guard
  that forbids non-empty generic `FLORABASE_CORS_ORIGINS` in production.
- It matches **only** the exact Capacitor WebView origins `https://localhost` and
  `capacitor://localhost`, with:
  - **No `Access-Control-Allow-Credentials`** (`allow_credentials=False`).
  - Methods restricted to `GET, POST, PUT, PATCH, DELETE, OPTIONS`.
  - Request headers restricted to `Authorization, Content-Type, X-Request-Id`.
  - Exposed headers restricted to `Content-Disposition, Retry-After`.
- **Why allowing `https://localhost` in CORS is harmless for desktop browsers:** A web page running on
  a desktop browser at `https://localhost` receives neither ambient cookies (`allow_credentials` is
  never set and `__Host-florabase-session` is `SameSite=Strict`) nor any authenticated state unless
  it already possesses a valid 256-bit Bearer device token. Florabase's mobile device tokens are
  generated only on mobile sign-in and stored exclusively in Android Keystore on the device — they
  never exist in desktop browsers or web storage. Furthermore, `POST /api/v1/auth/device-sessions`
  rejects non-JSON content types (`415`) and rejects requests carrying a session cookie (`401`), so
  `https://localhost` cannot perform credentialed CSRF or extract browser session state.

### 4. Server/client compatibility contract

- `GET /api/v1/health` remains untouched for container healthchecks.
- Unauthenticated `GET /api/v1/system/info` (`Cache-Control: no-store`) returns:
  - `server_version`: backend release version.
  - `api_version`: integer (`1`).
  - `min_client_version`: SemVer floor (`"0.1.0-beta.8"`).
  - `capabilities`: feature capability list (currently `["device-auth"]`).
- No secrets, database details, or host origins are included.
- The mobile app embeds its own version from `frontend/package.json` at build time and compares
  SemVer including pre-release precedence (`0.1.0-beta.8 < 0.1.0-beta.10 < 0.1.0`), refusing sign-in
  with an explicit message when either the server or the app must be updated.

### 5. Android Keystore storage and permanent application ID

- `SecureTokenPlugin.java` under `mobile/android/` uses Android's `AndroidKeyStore` directly with a
  non-exportable `AES/GCM/NoPadding` 256-bit key (`PURPOSE_ENCRYPT | PURPOSE_DECRYPT`) and stores
  only the Base64-encoded `IV || ciphertext || authTag` in app-private `SharedPreferences`
  (`MODE_PRIVATE`, with `android:allowBackup="false"` in `AndroidManifest.xml`).
- Deprecated `androidx.security:security-crypto` / `EncryptedSharedPreferences` and third-party
  storage plugins are not used.
- Tokens are never stored in `localStorage`, `sessionStorage`, IndexedDB, Capacitor `Preferences`,
  logs, or crash output. `mobile/capacitor.config.ts` sets `loggingBehavior: "none"` so Capacitor's
  native bridge never logs `SecureToken.set` arguments to Android `logcat` (even in debug builds).
  If key invalidation or corruption prevents decryption, `get()` wipes the key and stored entry and
  returns `{ token: null }`, cleanly returning the user to sign-in.
- `SecureTokenPlugin.getDeviceLabel()` reads `android.os.Build.MODEL` (read-only) to prefill the
  editable 1–120 character device name on sign-in.
- The Android `applicationId`, Gradle `namespace`, Capacitor `appId`, and Java package are permanently
  set to **`io.github.alessandrorossato.florabase`**.
- Debug-only WebView mixed content (`MIXED_CONTENT_ALWAYS_ALLOW` for local `http://10.0.2.2` testing)
  is strictly gated behind `BuildConfig.DEBUG` in `MainActivity.java`; release builds enforce
  `allowMixedContent: false` and `cleartextTrafficPermitted="false"`, verified by
  `scripts/test-beta-runtime.py`.

### 6. Protected files and inline images on native

- Inline protected images (`useProtectedImage` / `requestProtectedBlob`) work end-to-end over
  `Authorization: Bearer` + `Blob` object URLs.
- Browser-tab/download helpers (`openProtectedTab` and `downloadProtectedFile`) are disabled in the
  native shell in `MOBILE-002` with a clear notice ("Opening/downloading files is not yet available
  in the app — coming soon.") rather than relying on silent WebView blob-download failures. Native
  file share/save arrives in a later mobile increment.

## Consequences

- Browser/PWA authentication, cookie flags, CSRF rotation, and production CORS guards remain
  byte-for-byte unchanged.
- Android app users can connect to a self-hosted Florabase server, persist their session securely in
  Android Keystore across restarts, browse/edit records and inline photos, sign out, and revoke
  devices from either the PWA or the app.
- The same Bearer device-session contract supports a future offline capture queue and iOS
  (`capacitor://localhost` + Keychain) without backend protocol changes.
