import { useCallback, useEffect, useState, type SetStateAction } from "react";
import {
  isFreshDirectoryNavigation,
  isRecordTaskNavigation,
} from "../components/recordNavigation";
import {
  defaults,
  directoryRoutes,
  readDirectoryState,
  saveDirectoryState,
  type DirectoryStates,
  type DirectorySurface,
} from "./state";

/** Narrow URL extension for the controls a directory already owns. */
export function useDirectoryView<S extends DirectorySurface>(
  surface: S,
  onNavigate?: () => void,
  fallback?: Partial<DirectoryStates[S]>,
) {
  const [state, setState] = useState<DirectoryStates[S]>(() =>
    readDirectoryState(surface, window.location.hash, fallback),
  );
  const replace = useCallback(
    (next: DirectoryStates[S], typing = false) => {
      const saved = saveDirectoryState(surface, next);
      if (saved) {
        const [path, query = ""] = window.location.hash.split("?", 2);
        const params = new URLSearchParams(query);
        for (const field of Object.keys(defaults[surface]))
          params.delete(field);
        for (const [field, fieldValue] of Object.entries(saved))
          params.set(field, String(fieldValue));
        const hash = `${path || `#/${directoryRoutes[surface].split("?", 2)[0]}`}${params.size ? `?${params}` : ""}`;
        if (hash !== window.location.hash) {
          if (typing) window.history.replaceState(null, "", hash);
          else window.history.pushState(null, "", hash);
        }
      }
      setState(next);
    },
    [surface],
  );

  useEffect(() => {
    const sync = (event: Event) => {
      const [path, query = ""] = window.location.hash.split("?", 2);
      if (path !== `#/${directoryRoutes[surface].split("?", 2)[0]}`) return;
      const stored =
        new URLSearchParams(query).get("tab") === "stored-material";
      if (
        (surface === "stored_material" && !stored) ||
        (surface === "harvests" && stored)
      )
        return;
      if (isRecordTaskNavigation(event)) {
        // Return to the same task without discarding its canonical filters or focus.
        replace(state, true);
        return;
      }
      const next = readDirectoryState(surface, window.location.hash, fallback);
      if (
        !isFreshDirectoryNavigation(event) &&
        JSON.stringify(next) === JSON.stringify(state)
      )
        return;
      setState(next);
      onNavigate?.();
    };
    window.addEventListener("hashchange", sync);
    window.addEventListener("popstate", sync);
    return () => {
      window.removeEventListener("hashchange", sync);
      window.removeEventListener("popstate", sync);
    };
  }, [surface, onNavigate, fallback, state, replace]);

  const update = useCallback(
    <K extends keyof DirectoryStates[S]>(
      key: K,
      value: SetStateAction<DirectoryStates[S][K]>,
    ) => {
      const nextValue =
        typeof value === "function"
          ? (
              value as (current: DirectoryStates[S][K]) => DirectoryStates[S][K]
            )(state[key])
          : value;
      const next = { ...state, [key]: nextValue };
      replace(next, key === "q" && Boolean(state[key]));
    },
    [state, replace],
  );
  return {
    state,
    update,
    replace,
    savedState: saveDirectoryState(surface, state),
  };
}
