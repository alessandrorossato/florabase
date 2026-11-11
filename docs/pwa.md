# Install Florabase as an app (PWA-001)

Florabase can be installed on phones, tablets and desktops as a standalone app that opens in its
own window with its icon. It stays an **online-only client for your own server**: it does not
store collection records on the device, works without push notifications or background sync, and
never edits data offline.

## Requirements

- Florabase must be served over **HTTPS** on its canonical origin, for example through the
  reverse proxy or Tailscale Serve described in [installation](installation.md). Browsers only
  allow installation and service workers on secure origins; `http://127.0.0.1` and `localhost`
  work for local testing.
- Install from the same origin you sign in on. An installed app belongs to the exact origin
  (scheme, host and port) it was installed from.

## Install

| Platform                           | Browser                                                   | How to install                                                                                 | Notes                                                                                                                                                                             |
| ---------------------------------- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Android                            | Chrome, Edge, Samsung Internet                            | Open Florabase, then use **Install app** (or menu ⋮ → **Add to Home screen** → **Install**).   | Installs a full app with the adaptive (maskable) icon and standalone window.                                                                                                      |
| Android                            | Firefox                                                   | Menu → **Install** / **Add to Home screen**.                                                   | Adds a home-screen shortcut; window behavior depends on the Firefox version.                                                                                                      |
| iPhone / iPad                      | Safari (iOS/iPadOS 16.4+ also other browsers' Share menu) | Share → **Add to Home Screen** → **Add**.                                                      | Uses the 180×180 Apple touch icon and opens standalone. The Home Screen app keeps **its own cookies**: sign in once inside the installed app even if Safari is already signed in. |
| Windows / macOS / Linux / ChromeOS | Chrome, Edge                                              | Install icon in the address bar, or menu → **Cast, save and share** → **Install page as app**. | Opens in an app window; uninstall from the app window menu.                                                                                                                       |
| macOS 14+                          | Safari                                                    | File → **Add to Dock**.                                                                        | Standalone window with the Florabase icon.                                                                                                                                        |
| Desktop                            | Firefox                                                   | Not installable.                                                                               | Use Florabase as a normal tab.                                                                                                                                                    |

The app opens at `/`, the same entry point as the browser. Existing record links and hash routes
(for example `/#/plants/...`) keep working, and a sign-in is requested whenever the server session
is missing or expired. Signing out ends the server session exactly as in the browser.

## What runs on the device

Florabase registers one service worker, `/sw.js`, with scope `/`. Chromium-based browsers require a
service worker with a fetch handler before they offer installation; the worker is kept minimal:

| Request                                                                                  | Handling                                                                                                                                                                                                                                                                                                    |
| ---------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/api/*` (records, search, auth/session, CSRF, photos, attachments, exports)             | **Never intercepted, never cached.**                                                                                                                                                                                                                                                                        |
| `POST`, `PUT`, `PATCH`, `DELETE` and any non-`GET` request                               | Never intercepted.                                                                                                                                                                                                                                                                                          |
| Cross-origin requests (map tiles, external botanical sources)                            | Never intercepted.                                                                                                                                                                                                                                                                                          |
| `/runtime-config.js`, `/release.json`, `/appearance.js`, `/healthz`                      | Never intercepted.                                                                                                                                                                                                                                                                                          |
| Application bundles (`/assets/*`)                                                        | Never intercepted; ordinary HTTP caching applies.                                                                                                                                                                                                                                                           |
| Page navigations                                                                         | **Network first, never stored.** If the network fails, or the reverse proxy answers 502/503/504 (for example during an upgrade), a static **"Florabase cannot be reached"** page with a **Retry** button is shown instead. Every other response, including sign-in and errors, is passed through unchanged. |
| `/offline.html`, `/offline.css`, `/offline.js`, `/manifest.webmanifest`, icons, favicons | Precached at install; refreshed from the network first, cache used only when offline.                                                                                                                                                                                                                       |

The cache (`florabase-shell-v<N>`) therefore only ever contains those public, identical-for-everyone
files. Sessions remain server-side in the `HttpOnly` cookie described in [security](security.md);
nothing is written to `localStorage`, IndexedDB or Cache Storage on behalf of a user, and
cookie, `SameSite`, Origin and CSRF protections are unchanged. While offline the app shows no
collection content at all, so there is nothing stale or private to expose.

Nginx serves `/sw.js` with `Cache-Control: no-cache, no-store, must-revalidate`, the manifest,
`/offline.{html,css,js}` and `/index.html` with `no-cache`, and icons and favicons with a one-day
cache.

## Updates

**Frontend releases.** The server is authoritative. `index.html` is revalidated on every launch and
navigation, and hashed bundles are never served by the service worker, so closing and reopening the
installed app (or reloading a tab) always loads the release the server is running. A window that
stays open across an upgrade keeps running the release it loaded; Florabase checks `/release.json`
when the window becomes visible, when connectivity returns and every 15 minutes, and then shows a
small notice: _"A new version of Florabase is available. Save any open changes, then reload to use
it."_ Florabase never reloads by itself, so unsaved form changes are not lost; **Later** hides the
notice. Development servers without `/release.json` show no notice.

**Service worker updates.** Browsers re-check `/sw.js` on navigation (and the registration uses
`updateViaCache: "none"`). A changed worker installs, activates immediately and removes caches from
older shell versions. Because it does not serve application code or data, activating it changes
nothing in open windows and never reloads them.

**Server unavailable or upgrading.** Requests already made by an open window fail like any other
network error and show the app's normal error states; nothing is queued for later. New launches or
reloads show the "cannot be reached" page until the server answers again, then **Retry** opens the
current release. If an old window navigates to a section whose bundle no longer exists after an
upgrade, reload the app.

## Uninstall and remove

- Uninstall like any other app (long-press the icon on Android/iOS; app window menu on desktop).
  On iOS this also deletes the Home Screen app's separate cookies.
- To clear the service worker from a browser: site settings → **Clear data** (Chrome/Edge/Android),
  or Settings → Safari → Advanced → Website Data (iOS).
- To withdraw the service worker from every client in a future release, ship a `/sw.js` whose
  `install` handler calls `self.skipWaiting()` and whose `activate` handler deletes all
  `florabase-shell-*` caches and calls `self.registration.unregister()`, and stop calling
  `registerServiceWorker()`. Browsers pick it up on the next navigation because `/sw.js` is never
  HTTP-cached. Florabase keeps working without a service worker; only installability is lost.

## Verification and limits

Automated checks (`frontend/src/pwa/`) validate the manifest and icon files, HTML metadata, Nginx
headers, release-update notice, registration, and run the shipped `sw.js` against synthetic
install, activate and fetch events. Real-browser checks of the production image are recorded in
[progress](progress.md). Real Android and iOS device installation has **not** been verified yet;
iOS behavior above follows Apple's documented Home Screen web app model.
