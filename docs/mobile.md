# Florabase Android Mobile Shell (`mobile/`)

Florabase's Progressive Web App (PWA) remains a first-class channel. The Android app under `mobile/` wraps the **same** React/TypeScript production bundle from `frontend/` using Capacitor — there is no forked UI codebase.

> **Status (`MOBILE-002`):** The Android app supports connecting to a self-hosted Florabase server, checking compatibility via `GET /api/v1/system/info`, signing in with an opaque Bearer device session stored in Android Keystore, browsing/editing the collection with inline photos, and managing connected devices from Settings → Account. See [ADR 0011](decisions/0011-mobile-device-sessions.md) for the device-session transport and security design.

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
   - Runs `pnpm --dir mobile install --frozen-lockfile`.
   - Runs `pnpm --dir mobile exec cap sync android` to copy `frontend/dist` and register Capacitor plugins (`@capacitor/app`, `@capacitor/preferences`).
2. Runs `./gradlew assembleDebug` inside `mobile/android/`.

Output APK path (gitignored):

```text
mobile/android/app/build/outputs/apk/debug/app-debug.apk
```

To sync without enabling debug local-HTTP mode (matching release JS validation):

```bash
make mobile-sync
```

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

- [ADR 0011: Mobile device sessions](decisions/0011-mobile-device-sessions.md)
- [MOBILE-001 Architecture Decision Record](mobile-001-adr.md)
- [ADR 0005: Authentication and sessions](decisions/0005-authentication-and-sessions.md)
- [PWA and deployment guide](deployment.md)
