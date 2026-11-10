/**
 * Service worker registration for the online-first Florabase PWA (PWA-001).
 *
 * `/sw.js` exists only so supporting browsers treat Florabase as installable and can show a static
 * "cannot be reached" page instead of a browser error. It never serves application code or data,
 * so its own updates activate immediately without reloading or disturbing open forms; frontend
 * release updates are announced separately by `UpdateNotice`.
 */
export async function registerServiceWorker(
  container: ServiceWorkerContainer | undefined = "serviceWorker" in navigator
    ? navigator.serviceWorker
    : undefined,
): Promise<ServiceWorkerRegistration | null> {
  if (container === undefined) return null;
  try {
    // updateViaCache "none" keeps the browser from serving a stale /sw.js from its HTTP cache.
    return await container.register("/sw.js", {
      scope: "/",
      updateViaCache: "none",
    });
  } catch {
    // Registration is progressive enhancement; the app works normally without it.
    return null;
  }
}
