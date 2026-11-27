import { useContext, useEffect, useState } from "react";

import type { EventTargetKind } from "./api";
import { JournalScopeContext, useJournalReader } from "./journalReader";

/**
 * A record's Journal entry count, read through the surrounding JournalScope so it shares the
 * one Journal request with the Almanac and the Journal tab. Renders "…" until loaded.
 */
export function useJournalEntryCount(
  target: EventTargetKind,
  id: string,
): number | null {
  const reader = useJournalReader();
  const scope = useContext(JournalScopeContext);
  // A new or edited Journal entry invalidates the scope; read the count again then.
  const [revision, setRevision] = useState(0);
  useEffect(
    () =>
      scope?.subscribe?.((kind, changedId) => {
        if (kind === target && changedId === id)
          setRevision((value) => value + 1);
      }),
    [id, scope, target],
  );
  const key = `${target}:${id}`;
  const [result, setResult] = useState<{ key: string; count: number } | null>(
    null,
  );
  useEffect(() => {
    const controller = new AbortController();
    void reader
      .read(target, id)
      .then((events) => {
        if (!controller.signal.aborted && Array.isArray(events))
          setResult({ key, count: events.length });
      })
      .catch(() => {
        // The Almanac and Journal tab report Journal failures; the count stays hidden.
      });
    return () => {
      controller.abort();
    };
  }, [id, key, reader, revision, target]);
  return result?.key === key ? result.count : null;
}
