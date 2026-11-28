import { useEffect, useState } from "react";

import { ApiError, isExpectedAuthCancellation } from "../auth/api";
import { useAuth } from "../auth/context";
import { listPhotos, type PhotoTarget } from "./api";

/**
 * How many photos a record has, for the Photos tab's count badge. `revision` re-reads the
 * count (pass the selected tab so leaving Photos after an upload refreshes it). Null while
 * loading or when the list could not be read: the badge is then simply not shown.
 */
export function usePhotoCount(
  target: PhotoTarget,
  id: string | null,
  revision?: string,
): number | null {
  const auth = useAuth();
  const { capability, sessionExpired } = auth;
  const authorized =
    auth.state.status === "authenticated" && capability.isAuthorized();
  const key = `${target}:${id ?? ""}`;
  const [result, setResult] = useState<{ key: string; count: number } | null>(
    null,
  );
  useEffect(() => {
    if (!authorized || !id) return;
    const controller = new AbortController();
    void listPhotos(target, id, capability, controller.signal)
      .then((photos) => {
        if (!controller.signal.aborted && Array.isArray(photos))
          setResult({ key, count: photos.length });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || isExpectedAuthCancellation(error))
          return;
        if (error instanceof ApiError && error.status === 401) sessionExpired();
      });
    return () => {
      controller.abort();
    };
  }, [authorized, capability, id, key, revision, sessionExpired, target]);
  return id && result?.key === key ? result.count : null;
}
