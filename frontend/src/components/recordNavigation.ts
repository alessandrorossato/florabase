/** Keep hash routes readable by App and in browser history without remounting a task. */
export function setRecordRoute(hash: string, replace = false) {
  if (replace) window.history.replaceState(null, "", hash);
  else window.history.pushState(null, "", hash);
  window.dispatchEvent(
    new PopStateEvent("popstate", { state: { preserveRecordTask: true } }),
  );
}

/** A local detail transition retains its directory controls and return-focus target. */
export function isRecordTaskNavigation(event: Event): boolean {
  if (!(event instanceof PopStateEvent)) return false;
  const state: unknown = event.state;
  return Boolean(
    state &&
    typeof state === "object" &&
    "preserveRecordTask" in state &&
    state.preserveRecordTask === true,
  );
}

/** Enter a filtered directory as a fresh task, even when its URL is already open. */
export function openDirectoryRoute(hash: string) {
  if (window.location.hash !== hash) window.history.pushState(null, "", hash);
  window.dispatchEvent(
    new PopStateEvent("popstate", { state: { resetDirectory: true } }),
  );
}

export function isFreshDirectoryNavigation(event: Event): boolean {
  if (!(event instanceof PopStateEvent)) return false;
  const state: unknown = event.state;
  return Boolean(
    state &&
    typeof state === "object" &&
    "resetDirectory" in state &&
    state.resetDirectory === true,
  );
}
