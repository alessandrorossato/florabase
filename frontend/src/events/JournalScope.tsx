import { useMemo, type ReactNode } from "react";

import { createJournalScope, JournalScopeContext } from "./journalReader";

/** One record view's Journal scope; see journalReader.ts. */
export function JournalScope({
  version,
  children,
}: {
  /** The record's updated_at: a new version starts an empty scope. */
  version: string;
  children: ReactNode;
}) {
  const scope = useMemo(() => createJournalScope(version), [version]);
  return (
    <JournalScopeContext.Provider value={scope}>
      {children}
    </JournalScopeContext.Provider>
  );
}
