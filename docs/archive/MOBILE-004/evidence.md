# MOBILE-004 Verification Evidence — Android Local Schedule Reminders

- **Feature ID:** `MOBILE-004` (release class: `post-1.0` in [scope-v1.json](../../release/scope-v1.json))
- **Branch:** `feat/mobile-004-notifications` (base `origin/main` `c83d8163`, `v0.1.0-beta.10`)
- **Writer:** `neon-mobile-004`
- **Database / Backend changes:** None (zero Alembic migrations, zero OpenAPI drift).

## 1. Web / PWA isolation & bundle delta

- Zero `@capacitor/*` dependencies in `frontend/package.json`.
- `frontend/src/settings/AccountScreen.tsx` lazily imports `NativeRemindersSettings` strictly behind `isNativeShell()`; verified in `AccountScreen.test.tsx` that the Reminders section is absent and `LocalNotifications` is never touched on web.
- Zero occurrences of `LocalNotifications` or `schedule-reminders` in the web entry bundle `frontend/dist/assets/index-*.js`.
- Measured production `pnpm build` delta vs base `origin/main`:
  - `frontend/dist/assets/index-*.js`: `300,950 B → 301,059 B` (**+109 B raw / +63 B gzip**, `91,662 B → 91,725 B`)
  - `frontend/dist/assets/index-*.css`: `230,086 B → 230,086 B` (**+0 B raw / +0 B gzip**)
  - Native-only lazy chunks: `reminders-*.js` (`13.67 kB`), `NativeApp-*.js` (`21.00 kB`), `NativeRemindersSettings-*.js` (loaded only inside Capacitor WebView).

## 2. Plugin, permissions, Gradle graph & asset determinism

- **Plugin:** `@capacitor/local-notifications@8.3.1` pinned in `mobile/package.json` + `mobile/pnpm-lock.yaml`.
- **Resolved Gradle `releaseRuntimeClasspath` (`./gradlew :app:dependencies --configuration releaseRuntimeClasspath`):**
  - `:capacitor-local-notifications` depends solely on `org.jetbrains.kotlin:kotlin-stdlib`, `:capacitor-android`, and `androidx.appcompat:appcompat:1.7.1`.
  - Zero Google Play Services, Firebase, FCM, or ML Kit artifacts anywhere in the resolved graph.
- **Merged release `AndroidManifest.xml` (`./gradlew :app:processReleaseMainManifest` + `adb shell dumpsys package`):**
  - Active permissions: `INTERNET`, `POST_NOTIFICATIONS`, `RECEIVE_BOOT_COMPLETED`, `WAKE_LOCK`, and `io.github.alessandrorossato.florabase.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION`.
  - `SCHEDULE_EXACT_ALARM` stripped via `tools:node="remove"`; `USE_EXACT_ALARM` absent.
  - `com.capacitorjs.plugins.localnotifications.LocalNotificationRestoreReceiver` registered with `android:exported="false"`, `android:directBootAware="true"`, and intent filters for `BOOT_COMPLETED`, `LOCKED_BOOT_COMPLETED`, `QUICKBOOT_POWERON`, and `MY_PACKAGE_REPLACED`.
  - `android:allowBackup="false"` and `loggingBehavior: "none"` preserved.
- **Monochrome small icon:** `drawable-{mdpi,hdpi,xhdpi,xxhdpi,xxxhdpi}/ic_stat_florabase.png` generated deterministically from `frontend/public/icons/florabase-512.png` by `scripts/generate-mobile-assets.py` (`MOBILE_ASSETS_DETERMINISTIC_OK`).

## 3. APK builds (debug + signed release)

- **`make mobile-android-release` (throwaway PKCS12 keystore, `FLORABASE_ANDROID_CERT_SHA256` pin verified):**
  - Built `mobile/android/app/build/outputs/apk/release/florabase-0.1.0-beta.10.apk` (`versionName 0.1.0-beta.10`, `versionCode 100310`), passed `:app:lintVitalRelease` and `apksigner verify --print-certs`, and installed cleanly via `adb install -r` on Android 16 emulator.
- **`make mobile-android-debug`:**
  - Built `mobile/android/app/build/outputs/apk/debug/app-debug.apk` and installed cleanly on Android 16 emulator (`florabase_api36`).

## 4. Live Android 16 AOSP emulator E2E acceptance (`florabase_api36`)

Tested against an isolated per-worktree UAT instance (`florabase-uat-branch-feat-mobile-004-notifications`, golden SMOKE dataset at `http://10.0.2.2:15182`, plus 3 planned Schedule activities: 2 due today + 1 due tomorrow alongside 7 existing overdue items; UAT instance removed cleanly afterward):

| Scenario | Observed evidence | Result |
| --- | --- | --- |
| **A. Startup & sign-in (no prompt)** | Connected to `http://10.0.2.2:15182`, signed in as `golden-owner`; `dumpsys package` confirmed `POST_NOTIFICATIONS: granted=false` (zero startup prompt); `Settings -> Account` rendered `Reminders` below `Connected devices`, defaulted off / `08:00` / include overdue on. | PASS |
| **B. Permission denied** | Toggled Reminders on → Android 16 system dialog appeared → tapped `DON'T ALLOW` (`permission_deny_button`) → toggle stayed off and panel displayed `Notifications are disabled in Android. To turn reminders on, open Android Settings → Apps → Florabase → Notifications...`. | PASS |
| **C. Schedule, Doze/inexact delivery & lock-screen privacy** | Granted `POST_NOTIFICATIONS`, set time +2 min ahead, enabled Reminders. `CapacitorStorage.xml` persisted `florabase.reminders.plan` with ONLY `updatedAt`, `timeZone: "Europe/Rome"`, and per-day counts (zero titles/tokens). `dumpsys alarm` showed two inexact `RTC_WAKEUP` `TimedNotificationPublisher` alarms (`window=+1h0m0s0ms`, `flags=0x20`). Notification `id=41000` fired on channel `schedule-reminders` (`importance=3`, `vis=PRIVATE` / `vis=0`, `color=0xff153a2c`, `groupKey=florabase-schedule-reminders`, monochrome `ic_stat_florabase` icon), count-only collapsed summary and sanitized titles in `InboxStyle` (`android.textLines`) only; zero notes, target names, locations, or server URL in `dumpsys notification --noredact`. | PASS |
| **Measured inexact alarm latency** | Observed on active/idle Android 16 AOSP emulator (`setAndAllowWhileIdle`, no `SCHEDULE_EXACT_ALARM`): **+55 s** (run 1), **+60 s** (run 2, process killed), **+90 s** (run 3, process killed) — well within inexact Doze tolerances for a daily digest. | Measured |
| **D. Warm tap deep link** | App backgrounded (`KEYCODE_HOME`) → tapped notification in shade → opened directly to `#/schedule?window=today` (`Status: Planned / Active`, `Date window: Today`) and auto-cancelled `id=41000`. | PASS |
| **G. Activity completion updates plan** | Completed "Water alpine seedlings" in Schedule Today → `florabase.reminders.plan` updated immediately (`dueCount: 2 -> 1`, `overdueCount: 7`) and the next fired notification reflected `1 activity due today · 7 overdue` with only `"Inspect propagation dome"` in `android.textLines`. | PASS |
| **E. Cold-start tap deep link** | Killed app process (`pidof` empty) before alarm fired → alarm fired while process was dead → tapped notification → cold-started `MainActivity` and landed directly on `#/schedule?window=today`. | PASS |
| **F. Expired session tap + 401 cancellation** | Revoked mobile device sessions on server (`DELETE /api/v1/auth/device-sessions`, `revoked_count=1`) while notification was in shade → tapped notification → app received `401`, cleared all live pending alarms (`0` in `dumpsys alarm`, empty `NOTIFICATION_STORE.xml`) and `florabase.reminders.plan`, landed on Login while preserving `#/schedule?window=today` → signed back in → continued straight to `#/schedule?window=today` and rescheduled tomorrow's single-activity digest (`id=41001`, route `#/schedule/01a21cdc-9876-719f-a562-7719065b9ff5`). | PASS |
| **H. APK update survival (`MY_PACKAGE_REPLACED`)** | Ran `adb install -r app-debug.apk` without opening the app → `dumpsys alarm` retained the live pending `TimedNotificationPublisher` alarm for `2026-11-28 13:07:00.000` immediately. | PASS |
| **I. Reboot survival (`BOOT_COMPLETED`)** | Ran `adb reboot`, waited for `sys.boot_completed=1`, unlocked keyguard without opening the app → `dumpsys alarm` restored the live pending `TimedNotificationPublisher` alarm for `2026-11-28 13:07:00.000`. | PASS |
| **J. Logout cleanup** | Launched app and clicked **Sign out** → returned to Login with `0` pending Florabase alarms in `dumpsys alarm`, `0` delivered notifications in `dumpsys notification`, empty `NOTIFICATION_STORE.xml`, and `florabase.reminders.plan` removed from `CapacitorStorage.xml`. | PASS |

*(Review screenshots captured during emulator verification are retained locally outside Git per `AGENTS.md`: default-off card, Android 16 permission dialog, permission-denied notice, enabled card with last-updated timestamp, expanded notification shade with monochrome icon, warm-tap Schedule Today, cold-start Schedule Today, expired-session login, and post-login Schedule Today.)*

## 5. Automated tests & canonical gate

- **Focused frontend checks:** `pnpm format`, `pnpm typecheck`, `pnpm lint` (0 errors, 0 warnings), Vitest (`src/mobile/`, `src/settings/AccountScreen.test.tsx`, `src/schedule/api.test.ts`, `src/pwa/` — **17 files, 127 tests passed**), `mobile` `pnpm run typecheck` passed.
- **Workflow & release contract:** `make workflow-check` passed (`test-beta-images` 82 OK, lock 4 OK, `test-beta-runtime` 21 OK incl. `test_mobile_local_notifications_contract`, Dependabot policy, Ruff, strict mypy across workflow/app scripts, `MOBILE_ASSETS_DETERMINISTIC_OK`), `scripts/check-features.py` (205 valid), `scripts/check-doc-links.py` (398 documents).
- **Canonical local gate:** `make feature-verify AGENT_ID=neon-mobile-004` (FULL tier, due to `scripts/` updates) executed on the frozen committed HEAD.
