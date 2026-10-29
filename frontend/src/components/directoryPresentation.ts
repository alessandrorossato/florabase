import { useCallback, useEffect, useState } from "react";

export type DirectoryView = "list" | "gallery";
export const directoryViewDefaults = {
  seed_lots: "list",
  sowings: "list",
  plants: "gallery",
  botanical_identities: "gallery",
  suppliers: "list",
  orders: "list",
} as const satisfies Record<string, DirectoryView>;
export type PresentationSurface = keyof typeof directoryViewDefaults;
export const directoryPreferenceKey = (surface: PresentationSurface) =>
  `florabase.directory-view.v1.${surface}`;

export function readDirectoryPresentation(
  surface: PresentationSurface,
  hash = window.location.hash,
): DirectoryView {
  const value = new URLSearchParams(hash.split("?", 2)[1]).get("view");
  if (value === "list" || value === "gallery") return value;
  try {
    const preference = window.localStorage.getItem(
      directoryPreferenceKey(surface),
    );
    if (preference === "list" || preference === "gallery") return preference;
  } catch {
    // Browser preference storage can be unavailable; URL state still works.
  }
  return directoryViewDefaults[surface];
}

export function directoryPresentationHash(hash: string, view: DirectoryView) {
  const [path, query] = hash.split("?", 2);
  const params = new URLSearchParams(query);
  params.set("view", view);
  return `${path || "#/"}?${params}`;
}

/** Presentation only: canonical filters, selection and Saved Views remain page-owned. */
export function useDirectoryPresentation(surface: PresentationSurface) {
  const [view, setView] = useState<DirectoryView>(() =>
    readDirectoryPresentation(surface),
  );
  useEffect(() => {
    const sync = () => {
      setView(readDirectoryPresentation(surface));
    };
    window.addEventListener("hashchange", sync);
    window.addEventListener("popstate", sync);
    return () => {
      window.removeEventListener("hashchange", sync);
      window.removeEventListener("popstate", sync);
    };
  }, [surface]);
  const select = useCallback(
    (next: DirectoryView) => {
      const previous = new URLSearchParams(
        window.location.hash.split("?", 2)[1],
      ).get("view");
      // Keep the current entry restorable when its mode came from a default/preference.
      if (previous !== "list" && previous !== "gallery") {
        window.history.replaceState(
          window.history.state,
          "",
          directoryPresentationHash(window.location.hash, view),
        );
      }
      const hash = directoryPresentationHash(window.location.hash, next);
      if (hash !== window.location.hash)
        window.history.pushState(window.history.state, "", hash);
      try {
        window.localStorage.setItem(directoryPreferenceKey(surface), next);
      } catch {
        // The in-memory choice and URL remain usable without storage.
      }
      setView(next);
    },
    [surface, view],
  );
  return { view, select };
}
