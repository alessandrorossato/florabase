/* global self, caches, fetch, Response, URL */
/**
 * Florabase Progressive Web App Service Worker
 *
 * Scope: /
 * Policy: STRICT ONLINE-FIRST
 *
 * Cache Invariants:
 * 1. NEVER cache /api/* responses (authenticated records, botanical identities, photos, etc.).
 * 2. NEVER cache authentication, CSRF or session endpoints.
 * 3. NEVER cache mutation requests (POST, PUT, PATCH, DELETE).
 * 4. NEVER cache deployment-specific or dynamic runtime configs (/runtime-config.js, /release.json).
 * 5. NEVER perform cross-origin caching.
 * 6. Navigations are strictly NETWORK-FIRST. When network is unavailable, an offline fallback
 *    page (/offline.html) is served with zero private collection data.
 * 7. Precaches strictly public, static application-shell assets (offline fallback, manifest, icons).
 */

const CACHE_NAME = "florabase-shell-v1";

const PRECACHE_ASSETS = [
  "/offline.html",
  "/offline.css",
  "/offline.js",
  "/manifest.webmanifest",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/icon-maskable-192.png",
  "/icons/icon-maskable-512.png",
  "/icons/apple-touch-icon.png",
  "/icons/icon.svg",
  "/favicon.ico",
  "/favicon.svg",
];

// Upstream-unavailable statuses typically produced by a reverse proxy during upgrades or outages.
const UNAVAILABLE_STATUSES = new Set([502, 503, 504]);

function offlineFallback(upstreamResponse) {
  return caches.match("/offline.html").then((fallback) => {
    if (fallback) return fallback;
    if (upstreamResponse) return upstreamResponse;
    return new Response("Florabase cannot be reached", {
      status: 503,
      statusText: "Service Unavailable",
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  });
}

// Install: precache the offline fallback and static shell metadata
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_ASSETS))
      .then(() => self.skipWaiting()),
  );
});

// Activate: purge stale caches and claim clients safely without force-reloading
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== CACHE_NAME)
            .map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

// Fetch: enforce online-first policy
self.addEventListener("fetch", (event) => {
  const request = event.request;

  // 1. Only intercept GET requests; mutations are never intercepted or cached
  if (request.method !== "GET") {
    return;
  }

  const url = new URL(request.url);

  // 2. Never intercept cross-origin requests
  if (url.origin !== self.location.origin) {
    return;
  }

  // 3. Security invariant: Never intercept or cache API endpoints
  if (url.pathname.startsWith("/api/")) {
    return;
  }

  // 4. Runtime configurations & health check: always bypass service worker cache
  if (
    url.pathname === "/runtime-config.js" ||
    url.pathname === "/release.json" ||
    url.pathname === "/appearance.js" ||
    url.pathname === "/healthz"
  ) {
    return;
  }

  // 5. Navigation requests: STRICT NETWORK-FIRST. Navigation responses are never stored.
  // When online: fetches live application bundle from server.
  // When offline, or while a reverse proxy reports the upstream unavailable (502/503/504, e.g.
  // during an explicit upgrade): serves the static /offline.html fallback (no private data).
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) =>
          UNAVAILABLE_STATUSES.has(response.status)
            ? offlineFallback(response)
            : response,
        )
        .catch(() => offlineFallback(null)),
    );
    return;
  }

  // 6. Precached shell assets (icons, manifest, offline fallback files):
  // Network-first with cache fallback to ensure fresh updates are never masked.
  if (
    url.pathname.startsWith("/icons/") ||
    url.pathname === "/manifest.webmanifest" ||
    url.pathname === "/offline.html" ||
    url.pathname === "/offline.css" ||
    url.pathname === "/offline.js" ||
    url.pathname === "/favicon.ico" ||
    url.pathname === "/favicon.svg"
  ) {
    const networkWithCache = fetch(request).then((response) => {
      if (response && response.status === 200 && !response.redirected) {
        const responseClone = response.clone();
        const write = caches
          .open(CACHE_NAME)
          .then((cache) => cache.put(request, responseClone));
        return { response, write };
      }
      if (response && UNAVAILABLE_STATUSES.has(response.status)) {
        return caches.match(request).then((cached) => ({
          response: cached || response,
          write: Promise.resolve(),
        }));
      }
      return { response, write: Promise.resolve() };
    });
    event.waitUntil(
      networkWithCache.then(({ write }) => write).catch(() => undefined),
    );
    event.respondWith(
      networkWithCache
        .then(({ response }) => response)
        .catch(() =>
          caches.match(request).then((cached) => cached || Response.error()),
        ),
    );
    return;
  }

  // For any other static requests (e.g., /assets/*.js, /assets/*.css):
  // Let the browser handle normally via network and HTTP caching.
});
