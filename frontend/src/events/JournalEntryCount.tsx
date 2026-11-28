import type { EventTargetKind } from "./api";
import { useJournalEntryCount } from "./useJournalEntryCount";

/** The Journal entry count as text, "…" until it has loaded. */
export function JournalEntryCount({
  target,
  id,
}: {
  target: EventTargetKind;
  id: string;
}) {
  const count = useJournalEntryCount(target, id);
  return <>{count === null ? "…" : String(count)}</>;
}
