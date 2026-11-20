import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useAuth } from "../auth/context";
import {
  listBotanicalIdentities,
  type BotanicalIdentityResponse,
} from "../botanical-identities/api";
import { RecordIdentities, RecordIdentityWriter } from "./recordPresentation";

// Reuse each directory's existing reference metadata. Only activity workspaces
// and Sowings need their own single read; no per-row request or cross-session cache.
export function RecordPresentationProvider({
  children,
  fetchIdentities,
}: {
  children: ReactNode;
  fetchIdentities: boolean;
}) {
  const { state, capability } = useAuth();
  const authorized =
    state.status === "authenticated" && capability.isAuthorized();
  const [identities, setIdentities] = useState<
    ReadonlyMap<string, BotanicalIdentityResponse>
  >(new Map());
  const publish = useCallback((items: BotanicalIdentityResponse[]) => {
    setIdentities(new Map(items.map((item) => [item.id, item])));
  }, []);
  useEffect(() => {
    if (!authorized || !fetchIdentities) return;
    const controller = new AbortController();
    void listBotanicalIdentities(capability, controller.signal)
      .then((items) => {
        if (!controller.signal.aborted) publish(items);
      })
      .catch(() => {
        /* Summary names and placeholders remain usable. */
      });
    return () => {
      controller.abort();
    };
  }, [authorized, capability, fetchIdentities, publish]);
  return (
    <RecordIdentities value={identities}>
      <RecordIdentityWriter value={publish}>{children}</RecordIdentityWriter>
    </RecordIdentities>
  );
}
