import { useState } from "react";

/** Pages that offer the optional photo popup; each remembers its own choice. */
export type HoverPhotoPage = "native-ranges" | "collection-origins";

const storageKey = (page: HoverPhotoPage) =>
  `florabase.map-hover-photos.${page}.v1`;

function readPreference(page: HoverPhotoPage) {
  try {
    return window.localStorage.getItem(storageKey(page)) === "true";
  } catch {
    return false;
  }
}

/**
 * "Photos on hover" for one map page. Off by default, so nobody downloads thumbnails they
 * did not ask for; the choice is remembered on this device only.
 */
export function useHoverPhotos(
  page: HoverPhotoPage,
): [boolean, (value: boolean) => void] {
  const [enabled, setEnabled] = useState(() => readPreference(page));
  return [
    enabled,
    (value: boolean) => {
      setEnabled(value);
      try {
        window.localStorage.setItem(storageKey(page), String(value));
      } catch {
        /* The choice still applies for this visit. */
      }
    },
  ];
}
