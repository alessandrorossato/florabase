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

/** Only these full-page Collection tasks have a canonical parent entry. */
export function collectionPageParent(hash: string): string | null {
  const [pathname, query = ""] = hash.replace(/^#/, "").split("?", 2);
  const params = new URLSearchParams(query);
  if (pathname === "/harvests" && params.get("action") === "create") {
    const source = params.get("source");
    const sourceType = params.get("sourceType");
    return source && (sourceType === "plant" || sourceType === "plant_group")
      ? `#/${sourceType === "plant" ? "plants" : "plant-groups"}/${encodeURIComponent(source)}`
      : "#/harvests";
  }
  if (
    params.get("action") === "create" &&
    ["/seeds", "/sowings", "/plants"].includes(pathname)
  )
    return `#${pathname}`;
  if (
    pathname === "/sowings" &&
    params.get("action") === "start" &&
    params.get("seedLot")
  )
    return `#/seeds/${encodeURIComponent(params.get("seedLot") ?? "")}`;
  if (
    pathname === "/plants" &&
    params.get("action") === "from-sowing" &&
    params.get("sowing")
  )
    return `#/sowings/${encodeURIComponent(params.get("sowing") ?? "")}`;
  if (pathname === "/plants" && params.get("action") === "extract") {
    const source = params.get("source");
    return source ? `#/plant-groups/${encodeURIComponent(source)}` : "#/plants";
  }
  return null;
}

export function openCollectionPage(
  hash: string,
  parent = collectionPageParent(hash),
) {
  if (!parent) return;
  // A source operation returns to the same Details tab when entered there.
  if (
    /^#\/(seeds|sowings|plants|plant-groups)\/.+/.test(parent) &&
    window.location.hash.split("?", 1)[0] === parent
  )
    parent = window.location.hash;
  // Insert the directory/source entry before the task, without rewriting older history.
  if (window.location.hash !== parent)
    window.history.pushState(null, "", parent);
  window.history.replaceState(
    {
      ...window.history.state,
      collectionReturnFocus:
        hash.startsWith("#/harvests?action=create") && parent !== "#/harvests"
          ? "harvest"
          : parent.startsWith("#/plant-groups/")
            ? "extract"
            : ["#/seeds", "#/sowings", "#/plants", "#/harvests"].includes(
                  parent,
                )
              ? "create"
              : undefined,
    },
    "",
    parent,
  );
  window.history.pushState({ collectionPageParent: parent }, "", hash);
  window.dispatchEvent(
    new PopStateEvent("popstate", { state: { preserveRecordTask: true } }),
  );
}

export function closeCollectionPage(fallback: string) {
  const state: unknown = window.history.state;
  if (
    state &&
    typeof state === "object" &&
    "collectionPageParent" in state &&
    typeof state.collectionPageParent === "string" &&
    collectionPageParent(window.location.hash) !== null
  )
    window.history.back();
  else setRecordRoute(fallback, true);
}
