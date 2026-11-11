/**
 * Detects when the server has been upgraded to a different frontend release.
 *
 * Production images publish an unauthenticated `/release.json` (`Cache-Control: no-store`) with the
 * image version and revision. The watcher records the release that served this page and compares it
 * when the app becomes visible again, when connectivity returns, and periodically while visible.
 * It never reloads the page: the caller only shows a notice so unsaved form changes stay intact.
 * Development servers without `/release.json` (or answering with the SPA HTML) are ignored.
 */

export const RELEASE_URL = "/release.json";
export const RELEASE_CHECK_INTERVAL_MS = 15 * 60 * 1000;

export async function fetchReleaseFingerprint(
  fetchImpl: typeof fetch = fetch,
): Promise<string | null> {
  try {
    const response = await fetchImpl(RELEASE_URL, {
      cache: "no-store",
      credentials: "omit",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) return null;
    const body: unknown = await response.json();
    if (typeof body !== "object" || body === null) return null;
    const { version, revision } = body as Record<string, unknown>;
    if (typeof version !== "string" || version === "") return null;
    return `${version}+${typeof revision === "string" ? revision : ""}`;
  } catch {
    return null;
  }
}

export interface ReleaseWatcherOptions {
  onUpdateAvailable: () => void;
  fetchImpl?: typeof fetch;
  intervalMs?: number;
}

/** Starts watching for a new release; returns a function that stops watching. */
export function watchForNewRelease({
  onUpdateAvailable,
  fetchImpl = fetch,
  intervalMs = RELEASE_CHECK_INTERVAL_MS,
}: ReleaseWatcherOptions): () => void {
  let baseline: string | null = null;
  let announced = false;
  let stopped = false;
  let inFlight = false;
  // A function call keeps TypeScript from narrowing `stopped` across the await below.
  const isStopped = () => stopped;

  const check = async () => {
    if (stopped || announced || inFlight) return;
    inFlight = true;
    try {
      const current = await fetchReleaseFingerprint(fetchImpl);
      if (isStopped() || current === null) return;
      if (baseline === null) {
        baseline = current;
      } else if (current !== baseline) {
        announced = true;
        onUpdateAvailable();
      }
    } finally {
      inFlight = false;
    }
  };

  const checkWhenVisible = () => {
    if (document.visibilityState === "visible") void check();
  };

  void check();
  document.addEventListener("visibilitychange", checkWhenVisible);
  window.addEventListener("online", checkWhenVisible);
  const timer = window.setInterval(checkWhenVisible, intervalMs);

  return () => {
    stopped = true;
    document.removeEventListener("visibilitychange", checkWhenVisible);
    window.removeEventListener("online", checkWhenVisible);
    window.clearInterval(timer);
  };
}
