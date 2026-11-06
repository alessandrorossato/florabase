/**
 * A one-time request to open a record's own entry form ("?entry=new"), used by the Record
 * sheet and palette. The record's form is reused; nothing here creates data. The request is
 * read purely during render and removed from the address once the form has opened, so Back,
 * reload and later remounts do not reopen it.
 */
const param = "entry";

function split(hash: string): [string, URLSearchParams] {
  const index = hash.indexOf("?");
  return index < 0
    ? [hash, new URLSearchParams()]
    : [hash.slice(0, index), new URLSearchParams(hash.slice(index + 1))];
}

export function entryHref(href: string): string {
  const [path, params] = split(href);
  params.set(param, "new");
  return `${path}?${params.toString()}`;
}

export function hasEntryRequest(hash = window.location.hash): boolean {
  return split(hash)[1].get(param) === "new";
}

export function clearEntryRequest(): void {
  const [path, params] = split(window.location.hash);
  if (params.get(param) !== "new") return;
  params.delete(param);
  const query = params.toString();
  window.history.replaceState(
    window.history.state,
    "",
    `${window.location.pathname}${window.location.search}${path}${query ? `?${query}` : ""}`,
  );
}
