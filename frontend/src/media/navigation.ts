import { readDirectoryState, saveDirectoryState } from "../saved-views/state";

export function mediaOffset(hash: string): number {
  const value = new URLSearchParams(hash.split("?", 2)[1]).get("offset");
  const offset = Number(value);
  return value &&
    /^\d+$/.test(value) &&
    Number.isSafeInteger(offset) &&
    offset >= 0 &&
    offset <= 2147483647 &&
    offset % 24 === 0
    ? offset
    : 0;
}

/** Only existing Media filters and its bounded API offset travel between views. */
export function mediaDirectoryHash(hash = window.location.hash): string {
  const query = hash.split("?", 2)[1] ?? "";
  const filters = saveDirectoryState(
    "media",
    readDirectoryState("media", `#/media?${query}`),
  );
  const params = new URLSearchParams(filters as Record<string, string>);
  const offset = mediaOffset(hash);
  if (offset) params.set("offset", String(offset));
  return `#/media${params.size ? `?${params}` : ""}`;
}

export function mediaDetailHash(id: string): string {
  return mediaDirectoryHash().replace(
    "#/media",
    `#/media/${encodeURIComponent(id)}`,
  );
}

export function mediaFocusId(): string | undefined {
  const state: unknown = window.history.state;
  return state &&
    typeof state === "object" &&
    "mediaFocus" in state &&
    typeof state.mediaFocus === "string"
    ? state.mediaFocus
    : undefined;
}

export function rememberMediaCard(id: string) {
  window.history.replaceState({ ...window.history.state, mediaFocus: id }, "");
}

export function navigateMedia(hash: string, focusId?: string, replace = false) {
  window.history[replace ? "replaceState" : "pushState"](
    focusId ? { mediaFocus: focusId } : null,
    "",
    hash,
  );
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function subscribeMediaRoute(sync: () => void) {
  window.addEventListener("hashchange", sync);
  window.addEventListener("popstate", sync);
  return () => {
    window.removeEventListener("hashchange", sync);
    window.removeEventListener("popstate", sync);
  };
}
