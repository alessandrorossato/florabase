# Florabase Android Mobile Shell (`mobile/`)

> Summary: Capacitor Android shell setup, emulator/device testing, release signing, Obtainium distribution, and troubleshooting.

Florabase's Progressive Web App (PWA) remains a first-class channel. The Android app under `mobile/` wraps the **same** React/TypeScript production bundle from `frontend/` using Capacitor — there is no forked UI codebase.

> **Status (`MOBILE-004`):** The Android app ships with Florabase branding (launcher, adaptive icon, splash, monochrome notification small icon), native file export/sharing via `@capacitor/filesystem` + `@capacitor/share` (scoped `FileProvider` cache), a full-screen original-photo viewer with share/save, Android `PrintManager` label printing, server-driven map runtime configuration (`GET /api/v1/system/info`), opt-in daily Schedule reminders via `@capacitor/local-notifications` (F-Droid-clean, zero push/Google Play Services), a native update banner pointing to Obtainium / GitHub Releases, deterministic SemVer-derived `versionCode`, and signed release APK builds (`make mobile-android-release` + opt-in GitHub Release workflow). See [ADR 0011](../decisions/0011-mobile-device-sessions.md) for the device-session transport and security design.

## Prerequisites

Install the following host tools before building the APK:

| Tool | Required version | Notes |
| --- | --- | --- |
| **Docker** | Current Docker Engine + Compose | Used by `make mobile-sync` to build `frontend/dist` with the repo's pinned Node 24 / pnpm 11 toolchain. |
| **Node.js** | `24.x` (`>=24 <25`, repo pins `24.19.0`) | Matches `frontend/package.json` and `frontend/Dockerfile`. |
| **pnpm** | `11.19.0` | Matches `packageManager` in `frontend/package.json` and `mobile/package.json`. |
| **JDK** | **JDK 21 LTS** (e.g. Eclipse Temurin 21) | Required by Android Gradle Plugin `8.13.0` and Gradle `8.14.3`. Set `JAVA_HOME`. |
| **Android SDK** | Platform API **36**, Build-Tools **36.0.0**, `platform-tools` | Set `ANDROID_HOME` (default `$HOME/Android/Sdk`). `minSdkVersion` is 24 (Android 7.0). |
| **Android Emulator** *(optional, for local testing)* | `emulator` + `system-images;android-36;default;x86_64` | Pure AOSP image (no Google Play Services required). Hardware acceleration (`/dev/kvm` on Linux) strongly recommended. |

### Installing Android SDK packages from the command line

With Android SDK Command-Line Tools extracted to `$HOME/Android/Sdk/cmdline-tools/latest`:

```bash
export JAVA_HOME=/path/to/jdk-21
export ANDROID_HOME="$HOME/Android/Sdk"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"

# Install required build and emulator packages (AOSP image, no Google Play Services)
android sdk install \
  "platform-tools" \
  "platforms;android-36" \
  "build-tools;36.0.0" \
  "emulator" \
  "system-images;android-36;default;x86_64"
```

(If your installation provides `sdkmanager` without the `android` wrapper, pass the same package IDs to `sdkmanager` after `sdkmanager --licenses`.)

## Building the debug APK from a clean checkout

From the repository root:

```bash
make mobile-android-debug
```

What this target runs:

1. `make mobile-sync MOBILE_DEBUG_HTTP=true`:
   - Builds `frontend/dist` inside the repository's quality frontend container with `VITE_MOBILE_ALLOW_DEBUG_HTTP=true` (enabling local debug HTTP URLs such as `http://10.0.2.2:5173`).
   - Runs `cd mobile && pnpm install --frozen-lockfile && pnpm exec cap sync android` from the `mobile/` package directory (so Corepack resolves the pinned `pnpm@11.19.0` from `mobile/package.json`) to copy `frontend/dist` and register Capacitor plugins (`@capacitor/app`, `@capacitor/filesystem`, `@capacitor/local-notifications`, `@capacitor/preferences`, `@capacitor/share`).
2. Runs `./gradlew assembleDebug` inside `mobile/android/`.

Output APK path (gitignored):

```text
mobile/android/app/build/outputs/apk/debug/app-debug.apk
```

To sync without enabling debug local-HTTP mode (matching release JS validation):

```bash
make mobile-sync
```

## Branding assets (`make mobile-assets`)

Android launcher icons, adaptive icons (`#f8f5e7` background matching the PWA maskable icon), monochrome status-bar notification small icons (`drawable-*/ic_stat_florabase.png`), splash screens (`#153a2c` background matching `manifest.webmanifest`), and theme colors are derived deterministically from `frontend/public/icons/florabase-maskable-512.png` and `frontend/public/icons/florabase-512.png` by `scripts/generate-mobile-assets.py`.

To regenerate them reproducibly using the pinned Pillow toolchain:

```bash
make mobile-assets
```

Do not hand-edit generated Android PNGs directly; update the canonical icons under `frontend/public/icons/` and rerun `make mobile-assets`.

## Version naming and `versionCode` formula

`mobile/android/app/build.gradle` reads both `versionName` and `versionCode` from a single source of truth (`scripts/mobile_version.py`), which derives them from `frontend/package.json`:

```text
versionCode = major * 10_000_000 + minor * 100_000 + patch * 1_000 + stageOffset
```

- Bounds: `major` 0–209, `minor` 0–99, `patch` 0–99.
- `stageOffset`: `-alpha.N` → `N` (`1..299`), `-beta.N` → `300 + N` (`301..599`), `-rc.N` → `600 + N` (`601..899`), stable → `900`.
- Examples: `0.1.0-beta.9` → `100309`, `0.1.0-beta.10` → `100310`, `0.1.0-rc.1` → `100601`, `0.1.0` → `100900`, `0.1.1` → `101900`, `1.0.0-rc.1` → `10000601`, `1.0.0` → `10000900`.

Invalid SemVer strings or out-of-range components fail the build immediately rather than producing a colliding `versionCode`.

## Release signing, keystore setup, and GitHub Releases

> **CRITICAL BACKUP WARNING:** Your Android signing keystore is the permanent cryptographic identity of `io.github.alessandrorossato.florabase`. **If you lose the keystore or its passwords, Android will reject all future APK updates and every Obtainium / sideload user will have to uninstall and reinstall the app (losing their local server link and device session).** Never commit the keystore to Git. Keep an encrypted offline backup in at least two independent locations (for example, your password manager and an encrypted offline drive).

### 1. Create the release keystore once

Run this once on a trusted machine outside the repository (for example in `~/.config/florabase-signing/`):

```bash
mkdir -p ~/.config/florabase-signing && chmod 700 ~/.config/florabase-signing
keytool -genkeypair -v \
  -keystore ~/.config/florabase-signing/florabase-release.p12 \
  -storetype PKCS12 \
  -keyalg RSA \
  -keysize 4096 \
  -validity 10000 \
  -alias florabase-release \
  -dname "CN=Florabase, OU=Mobile, O=Florabase"
chmod 600 ~/.config/florabase-signing/florabase-release.p12
```

### 2. Record the signing certificate SHA-256 fingerprint

Read the certificate SHA-256 fingerprint once:

```bash
keytool -list -v \
  -keystore ~/.config/florabase-signing/florabase-release.p12 \
  -alias florabase-release | grep -i "SHA256:"
```

Save the 64-character hex digest (colons optional) as the optional GitHub Actions **repository variable** `FLORABASE_ANDROID_CERT_SHA256` (Settings → Secrets and variables → Actions → Variables). When set, both `make mobile-android-release` and CI compare `apksigner verify --print-certs` against this fingerprint and fail if a wrong or rotated key is used.

### 3. Build and verify a signed release APK locally

```bash
export FLORABASE_ANDROID_KEYSTORE="$HOME/.config/florabase-signing/florabase-release.p12"
export FLORABASE_ANDROID_STORE_PASSWORD="<store-password>"
export FLORABASE_ANDROID_KEY_ALIAS="florabase-release"
export FLORABASE_ANDROID_KEY_PASSWORD="<key-password>"
# Optional certificate pin check:
# export FLORABASE_ANDROID_CERT_SHA256="<sha256-hex>"

make mobile-android-release
```

`make mobile-android-release` always rebuilds `frontend/dist` with `VITE_MOBILE_ALLOW_DEBUG_HTTP=false` (so a previous debug build can never leak into a release APK), builds `./gradlew assembleRelease`, verifies the APK with `apksigner verify --print-certs`, checks `FLORABASE_ANDROID_CERT_SHA256` if set, and writes:

```text
mobile/android/app/build/outputs/apk/release/florabase-<version>.apk
mobile/android/app/build/outputs/apk/release/florabase-<version>.apk.sha256
```

If any of the four signing variables are missing, `make mobile-android-release` refuses to emit a release APK and prints which variables are missing. Unsigned local `./gradlew assembleRelease` and debug `make mobile-android-debug` builds continue to work without signing variables.

### 4. Configure GitHub Actions secrets for automatic release APK attachment

Encode the keystore to single-line base64 without echoing it to shell history or logs:

```bash
base64 -w 0 ~/.config/florabase-signing/florabase-release.p12 | pbcopy   # or xclip / wl-copy
```

In GitHub (**Settings → Secrets and variables → Actions → Secrets**), add:

| Secret | Value |
| --- | --- |
| `ANDROID_KEYSTORE_BASE64` | Base64-encoded `.p12` / `.jks` keystore file |
| `ANDROID_STORE_PASSWORD` | Keystore store password |
| `ANDROID_KEY_ALIAS` | Key alias (e.g. `florabase-release`) |
| `ANDROID_KEY_PASSWORD` | Key password |

And optionally under **Variables**:

| Variable | Value |
| --- | --- |
| `FLORABASE_ANDROID_CERT_SHA256` | Expected Signer #1 certificate SHA-256 fingerprint |

The opt-in workflow [`.github/workflows/mobile-android-release.yml`](../../.github/workflows/mobile-android-release.yml) runs automatically after **Protected Florabase release** (`beta-images.yml`) succeeds (checking out `workflow_run.head_sha`, asserting that tag `v<version>` points at that exact commit and has a published GitHub Release), or manually via `workflow_dispatch` with an existing `tag` input. It never runs on pull requests and never modifies the container image release pipeline.

## Installing and updating with Obtainium

[Obtainium](https://obtainium.imranr.dev/) tracks Florabase's signed GitHub Release APKs directly without Google Play Services:

1. Tap **Add App** in Obtainium.
2. **App Source URL:** `https://github.com/alessandrorossato/florabase`
3. **Filter APKs by Regular Expression:** `^florabase-.*\.apk$`
4. For beta releases (`v0.1.0-beta.*`), enable **Include prereleases**.
5. Tap **Add** and install the verified APK.

When your Florabase server is upgraded to a version newer than the installed APK, the app displays a non-blocking banner prompting you to update from Obtainium or GitHub Releases. If the server's `min_client_version` exceeds the app version, sign-in is blocked until you update.

## Runtime map configuration and file actions in the app

- **Map basemap opt-in:** The Android app reads `runtime_config` (`map_online_enabled`, `map_tile_url`, `map_attribution`) directly from `GET /api/v1/system/info` without executing remote scripts. Defaults stay strictly offline unless the server operator sets `FLORABASE_MAP_ONLINE_ENABLED=true` (and optionally `FLORABASE_MAP_TILE_URL` / `FLORABASE_MAP_ATTRIBUTION` — see [deployment guide](deployment.md#provenance-map-basemap)). Network-supplied attribution HTML is sanitized to plain text and `https://` links before Leaflet renders it.
- **CSV exports & attachments:** Downloads are fetched with Bearer auth, written exclusively inside the app's private cache subfolder (`cache/shared/`, the only path exposed by `file_paths.xml`), and handed to the Android share sheet so you can save or send them. Ephemeral shared files are wiped automatically on the next app start.
- **Original photos:** Tapping **Open original image** in Media opens a full-screen in-app viewer (revoking the blob URL on close, auth invalidation, and unmount) with a **Share / Save** button that reuses the already-fetched bytes without re-downloading.
- **Label printing:** Tapping **Print** on the Labels screen invokes Android's built-in `PrintManager` (`WebPrintPlugin.java`) to open Android's Print / Save-as-PDF preview using Florabase's print stylesheet.

## Reminders (local Schedule notifications)

The Android app can schedule **local** daily digest reminders for planned Schedule activities using `@capacitor/local-notifications` with zero server push, zero Firebase/FCM, and zero Google Play Services (fully F-Droid-compatible). The web/PWA experience is completely unchanged (no permission prompts and no Reminders panel).

### Behaviour and controls

- **Opt-in per device:** Located in **Settings → Account → Reminders** (directly below **Connected devices**, shown only in the Android app). Defaults: **off**, daily time **08:00** (device local wall-clock time), **Include overdue activities** **on**.
- **One daily digest (next 14 days):** Rather than firing one alarm per activity, Florabase schedules at most one digest per day over the next 14 local calendar days (`[today, today+13]`) that has planned work due:
  - Multiple items due: `"3 activities due today · 1 overdue"` → tapping opens `#/schedule?window=today`.
  - Single item due (with no overdue shown): `"1 activity due today"` → tapping opens `#/schedule/<id>` directly.
  - Overdue-only today (when *Include overdue* is on and `today_count === 0`): `"2 overdue activities"` → tapping opens `#/schedule?window=overdue`.
  - Days with nothing due receive no notification; if today's chosen time has already passed, today is skipped so opening the app never triggers an immediate catch-up alarm.
- **When reminders update (and staleness):** There is no background network service. The pending set (IDs `41000..41099`, never touching other notification IDs) is recomputed serially whenever you open the app while signed in, resume it to the foreground, create/edit/complete/cancel a Schedule activity in the app, or change Reminders settings. The settings panel explicitly states *"Reminders update when you open the app · Last updated <time>"*.
- **Inexact alarms & Doze:** All reminders are scheduled with `isExactNotification: false` and `allowWhileIdle: true` (`AlarmManager.setAndAllowWhileIdle`). `SCHEDULE_EXACT_ALARM` is explicitly stripped from the merged manifest (`tools:node="remove"`), so Android never prompts for "Alarms & reminders" exact-alarm access. Under Android 14–16 Doze, delivery may be batched by a few minutes (typically 0–15 min in deep Doze).
- **DST and time zones:** Each day's trigger is computed from that calendar day's local wall-clock time (never `today + n × 24h`). On a DST spring-forward day when the chosen time does not exist (e.g. `02:30` on the last Sunday of March in `Europe/Rome`), Florabase schedules the next valid instant immediately after the gap (`03:00`). On a fall-back day when the chosen time occurs twice (e.g. `02:30` on the last Sunday of October), Florabase picks the first valid occurrence. Changing the device time zone triggers a recompute on next resume.
- **Reboot and app updates:** Pending reminders survive both device reboots (`BOOT_COMPLETED` / `QUICKBOOT_POWERON`) and APK updates from Obtainium or sideloading (`MY_PACKAGE_REPLACED` on `LocalNotificationRestoreReceiver`, `android:exported="false"`).

### Permissions and revocation

- **Merged permissions:** `INTERNET`, `POST_NOTIFICATIONS` (Android 13+ runtime permission), `RECEIVE_BOOT_COMPLETED`, and `WAKE_LOCK` (no `SCHEDULE_EXACT_ALARM` or `USE_EXACT_ALARM`).
- **When asked:** `POST_NOTIFICATIONS` is requested **only** when you toggle Reminders on — never at startup or during background recomputes.
- **If denied or revoked later:** If you deny the prompt or later disable notifications in Android Settings, the Reminders panel displays the disabled state with step-by-step instructions (**Android Settings → Apps → Florabase → Notifications**), clears pending reminders, and stops attempting to schedule until you re-enable notifications.

### Privacy and loss of trust

- **Lock screen:** Channel `schedule-reminders` (`IMPORTANCE_DEFAULT`) is created with `VISIBILITY_PRIVATE`. The collapsed notification contains **only the count** (title `"3 activities due today · 1 overdue"`, body `"Open Schedule to review today's work"`), while up to 5 plain-text activity titles (control characters stripped, ≤60 characters each) appear only in the expanded `InboxStyle` view:
  - **With Android's *"Hide sensitive content"* enabled on the lock screen:** Android redacts the notification to its system placeholder (*"Sensitive notification content hidden"*) until unlocked.
  - **With Android's *"Show all notification content"* enabled on the lock screen:** the collapsed lock-screen card shows counts only; titles appear only when expanded.
- **No sensitive fields:** Notification titles, bodies, and `extra` payloads (`{ route, v: 1 }`) never contain target names, locations, activity notes, server URLs, or authentication tokens. The cached plan summary in Capacitor Preferences (`florabase.reminders.plan`) stores only `updatedAt`, `timeZone`, and per-day counts — never activity titles.
- **Cleared on loss of trust or switch-off:** Signing out, session revocation (`401`), changing or forgetting the server URL, failing the server's `min_client_version` check, or switching Reminders off immediately cancels all pending **and** removes all delivered Florabase reminders in ID range `41000..41099` and wipes `florabase.reminders.plan`. Pending reminders are preserved across transient offline (`unreachable`) launches.
- **Deep links across expired sessions:** Tapping a reminder opens `#/schedule?window=today` (or `#/schedule/<id>` / `#/schedule?window=overdue`) on both cold and warm start. If your device session expired in the meantime, Florabase lands on the sign-in screen and continues straight to the target Schedule view as soon as you sign back in.

> **Generated files:** Never commit `mobile/android/local.properties`, `*.apk`, `*.aab`, `*.keystore`, `*.jks`, or Gradle `build/` outputs. Gradle resolves the SDK via `ANDROID_HOME` without needing a checked-in `local.properties`.

## Running on the Android emulator

### 1. Create and boot an AVD

```bash
avdmanager create avd \
  --name florabase_api36 \
  --package "system-images;android-36;default;x86_64" \
  --device pixel_6

emulator -avd florabase_api36 -no-snapshot-save
```

Wait until the device finishes booting (`adb wait-for-device` and `adb shell getprop sys.boot_completed` returns `1`).

### 2. Start the local Florabase dev server

From the primary checkout:

```bash
make dev-up
```

Verify the dev server responds on the host:

```bash
curl -s http://127.0.0.1:5173/api/v1/health
# {"status":"ok"}
```

### 3. Install and launch the debug APK

```bash
adb install -r mobile/android/app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n io.github.alessandrorossato.florabase/.MainActivity
```

### Reaching the host dev server: the `10.0.2.2` note

Inside the Android emulator, `localhost` and `127.0.0.1` refer to the **emulator itself**, not your workstation. The Android emulator provides a special router alias:

- **`http://10.0.2.2:5173`** reaches `127.0.0.1:5173` on the host (Vite dev server proxying `/api` to FastAPI).
- **`http://10.0.2.2:8000`** reaches `127.0.0.1:8000` on the host (FastAPI directly).

Enter `http://10.0.2.2:5173` in the onboarding **Server URL** field and tap **Connect**. Once `/api/v1/health` and `/api/v1/system/info` pass compatibility checks, sign in with your owner credentials and an editable device name (prefilled from `Build.MODEL`).

**Token storage and revocation:**

- The Bearer device token is encrypted with a non-exportable AES-256-GCM key in `AndroidKeyStore` (`SecureTokenPlugin.java`) and stored in app-private `SharedPreferences` (`android:allowBackup="false"`). It is never written to `localStorage`, `sessionStorage`, IndexedDB, or Capacitor `Preferences`.
- Signed-in devices can be viewed and revoked individually or all at once from **Settings → Account → Connected devices** in either the web/PWA or Android app. Changing your password in the web app revokes all browser and mobile device sessions immediately.

**Cleartext HTTP policy (debug vs release):**

- **Debug APKs** (`make mobile-android-debug`) include `mobile/android/app/src/debug/res/xml/network_security_config.xml`, set `VITE_MOBILE_ALLOW_DEBUG_HTTP=true`, and enable WebView mixed content strictly inside `if (BuildConfig.DEBUG)` in `MainActivity.java`, allowing plain `http://` **only** for `10.0.2.2`, loopback, and private RFC1918 / `.local` LAN hosts. Public `http://` hosts are still rejected.
- **Release APKs** use `mobile/android/app/src/main/res/xml/network_security_config.xml` (`cleartextTrafficPermitted="false"`), set `allowMixedContent: false` in `mobile/capacitor.config.ts`, omit the debug mixed-content branch (`BuildConfig.DEBUG == false`), and build with `VITE_MOBILE_ALLOW_DEBUG_HTTP=false`. This release invariant is checked automatically by `make test-beta-runtime`.

## Trusting a self-signed or private NAS CA on Android

Self-hosted Florabase installations on a home NAS or LAN often terminate HTTPS with a private Certificate Authority (for example, a Synology/TrueNAS internal CA, `mkcert`, or Step CA).

Florabase's Android network security config (`mobile/android/app/src/main/res/xml/network_security_config.xml`) trusts:

- `<certificates src="system" />` — standard Android system CAs (Let's Encrypt, etc.), and
- `<certificates src="user" />` — CA certificates explicitly installed by the device owner in Android Settings.

It **never** disables TLS verification, never accepts arbitrary self-signed certificates, and never permits cleartext traffic in release builds.

### Steps to trust your NAS CA on Android

1. **Export the CA root certificate** (not the private key!) from your NAS or CA tool in PEM (`.crt` / `.pem`) or DER (`.cer`) format.
   - Ensure the server's leaf certificate includes a valid **Subject Alternative Name (SAN)** matching the hostname or IP you will enter in Florabase, and is signed by that root CA (not a bare non-CA leaf cert).
2. **Copy the CA certificate** to the Android device (USB transfer, local file share, or `adb push my-nas-ca.crt /sdcard/Download/`).
3. **Install it as a user CA certificate in Android Settings:**
   - Open **Settings -> Security & privacy -> More security & privacy -> Encryption & credentials -> Install a certificate -> CA certificate**.
   - *(On some OEM skins such as Samsung One UI: **Settings -> Security and privacy -> Other security settings -> Install from device storage -> CA certificate**.)*
   - Confirm the Android warning ("Install anyway"), select your `.crt` / `.pem` file, and give it a recognizable name (e.g. `Home NAS CA`).
4. **Verify in Florabase:** Open the Florabase Android app and enter `https://<your-nas-hostname>`. The health check will succeed using your user-installed CA.

If the CA is missing or the leaf cert does not match the hostname, onboarding surfaces a distinct **Certificate not trusted** error pointing back to this guide.

## Debugging tips

- **Inspect WebView logs:** `adb logcat | grep -E "Capacitor|chromium|florabase"`
- **Chrome DevTools remote debugging:** Open `chrome://inspect/#devices` in Chromium/Chrome on the host while the debug APK is running on an emulator or USB-connected device.
- **Verify native runtime isolation:** In the Capacitor WebView, `window.Capacitor.isNativePlatform()` is `true`; `/sw.js` service worker registration and `/release.json` update polling are skipped automatically.

## Related documents

- [ADR 0011: Mobile device sessions](../decisions/0011-mobile-device-sessions.md)
- [MOBILE-001 Architecture Decision Record](../archive/MOBILE-001/mobile-001-adr.md)
- [ADR 0005: Authentication and sessions](../decisions/0005-authentication-and-sessions.md)
- [PWA and deployment guide](deployment.md)
