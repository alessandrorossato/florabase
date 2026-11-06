import { useEffect, useState } from "react";

import { listSavedViews } from "../saved-views/api";
import { savedViewsChanged } from "../saved-views/events";
import { savedViewHash, surfaceLabels } from "../saved-views/state";
import { workspaceOfHash, type WorkspaceId } from "./navigation";

export interface SavedViewLink {
  id: string;
  name: string;
  /** The ordinary directory URL rebuilt from the validated saved state. */
  href: string;
  surface: string;
  workspace: WorkspaceId;
}

/**
 * The owner's Saved Views as links for the Workbench panel and palette. Only
 * views the existing serializer accepts are listed; an incompatible view stays
 * in its directory's Saved views dialog, which explains it. No new API or route.
 */
export function useSavedViewLinks(): SavedViewLink[] {
  const [views, setViews] = useState<SavedViewLink[]>([]);
  const [version, setVersion] = useState(0);
  useEffect(() => {
    const refresh = () => {
      setVersion((value) => value + 1);
    };
    window.addEventListener(savedViewsChanged, refresh);
    return () => {
      window.removeEventListener(savedViewsChanged, refresh);
    };
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    Promise.resolve(listSavedViews(undefined, controller.signal))
      .then((list: unknown) => {
        if (!Array.isArray(list)) return;
        setViews(
          (list as Awaited<ReturnType<typeof listSavedViews>>).flatMap(
            (view) => {
              if (view.compatibility !== "supported") return [];
              const href = savedViewHash(
                view.surface,
                view.state_version,
                view.state,
              );
              if (!href) return [];
              return [
                {
                  id: view.id,
                  name: view.name,
                  href,
                  surface: surfaceLabels[view.surface],
                  workspace:
                    view.surface === "global_search"
                      ? "today"
                      : (workspaceOfHash(href)?.id ?? "today"),
                },
              ];
            },
          ),
        );
      })
      .catch(() => {
        // Without the list the panel simply omits Saved views; directories keep theirs.
      });
    return () => {
      controller.abort();
    };
  }, [version]);
  return views;
}
