import { createContext, useContext, useMemo } from "react";

import type { ProtectedRequestCapability } from "../auth/api";
import { useAuth } from "../auth/context";
import { listEvents, type EventResponse, type EventTargetKind } from "./api";

export interface JournalScopeValue {
  read: (
    kind: EventTargetKind,
    id: string,
    capability: ProtectedRequestCapability,
  ) => Promise<EventResponse[]>;
  invalidate: (kind: EventTargetKind, id: string) => void;
}

export interface BoundJournalReader {
  read: (kind: EventTargetKind, id: string) => Promise<EventResponse[]>;
  invalidate: (kind: EventTargetKind, id: string) => void;
}

export const JournalScopeContext = createContext<JournalScopeValue | null>(
  null,
);

export function createJournalScope(version: string): JournalScopeValue {
  const revisions = new Map<string, number>();
  const byCapability = new WeakMap<
    ProtectedRequestCapability,
    Map<string, Promise<EventResponse[]>>
  >();
  return {
    read(kind, id, capability) {
      let entries = byCapability.get(capability);
      if (!entries) {
        entries = new Map();
        byCapability.set(capability, entries);
      }
      const targetKey = `${kind}:${id}`;
      const revision = revisions.get(targetKey) ?? 0;
      const key = `${targetKey}:${version}:${String(revision)}`;
      const hit = entries.get(key);
      if (hit) return hit;
      const promise = listEvents(kind, id, capability);
      entries.set(key, promise);
      const ownerEntries = entries;
      promise.catch(() => {
        if (ownerEntries.get(key) === promise) ownerEntries.delete(key);
      });
      return promise;
    },
    invalidate(kind, id) {
      const targetKey = `${kind}:${id}`;
      revisions.set(targetKey, (revisions.get(targetKey) ?? 0) + 1);
    },
  };
}

/** Reads a record's Journal through the enclosing JournalScope, or directly without one. */
export function useJournalReader(): BoundJournalReader {
  const { capability } = useAuth();
  const scope = useContext(JournalScopeContext);
  return useMemo(
    () => ({
      read: (kind, id) =>
        scope
          ? scope.read(kind, id, capability)
          : listEvents(kind, id, capability),
      invalidate: (kind, id) => {
        scope?.invalidate(kind, id);
      },
    }),
    [capability, scope],
  );
}
