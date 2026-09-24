/** Keep hash routes readable by App and in browser history without remounting a task. */
export function setRecordRoute(hash: string, replace = false) {
  if (replace) window.history.replaceState(null, "", hash);
  else window.history.pushState(null, "", hash);
  window.dispatchEvent(new PopStateEvent("popstate"));
}
