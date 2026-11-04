import { createContext, useContext } from "react";

import { listEvents, type EventResponse, type EventTargetKind } from "./api";

/**
 * One Journal request per record view (M6A finding R2). The Overview Almanac and the Journal
 * tab both read a Plant's or Plant group's events; inside a JournalScope the second reader
 * reuses the first response instead of repeating the request. The API and what each reader
 * shows are unchanged:
 * - the scope lives exactly as long as the record view, so leaving the record (for example
 *   to record a harvest) and returning reads fresh events;
 * - entries are keyed by the record version, so a record change reads fresh events;
 * - every Journal mutation invalidates before re-reading (EventJournal).
 * Outside a scope, readers fetch directly as before.
 */
export interface JournalScopeValue {
  read: (kind: EventTargetKind, id: string) => Promise<EventResponse[]>;
  invalidate: (kind: EventTargetKind, id: string) => void;
}

export const JournalScopeContext = createContext<JournalScopeValue | null>(
  null,
);

export function createJournalScope(version: string): JournalScopeValue {
  const entries = new Map<string, Promise<EventResponse[]>>();
  return {
    read(kind, id) {
      const key = `${kind}:${id}:${version}`;
      const hit = entries.get(key);
      if (hit) return hit;
      const promise = listEvents(kind, id);
      entries.set(key, promise);
      promise.catch(() => {
        if (entries.get(key) === promise) entries.delete(key);
      });
      return promise;
    },
    invalidate(kind, id) {
      entries.delete(`${kind}:${id}:${version}`);
    },
  };
}

const direct: JournalScopeValue = {
  read: (kind, id) => listEvents(kind, id),
  invalidate: () => undefined,
};

/** Reads a record's Journal through the enclosing JournalScope, or directly without one. */
export function useJournalReader(): JournalScopeValue {
  return useContext(JournalScopeContext) ?? direct;
}
