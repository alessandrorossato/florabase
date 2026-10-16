/** Quiet metadata for the current filtered list, using only already-known counts. */
import type { ReactNode } from "react";

export function DirectoryResults({
  count,
  total,
  loadedOnly = false,
  actions,
}: {
  count: number;
  total?: number;
  loadedOnly?: boolean;
  actions?: ReactNode;
}) {
  const summary = (
    <p className="directory-results" aria-label="Directory results">
      {total !== undefined && total !== count
        ? `${String(count)} of ${String(total)} records`
        : loadedOnly
          ? `${String(count)} shown`
          : `${String(count)} ${count === 1 ? "record" : "records"}`}
    </p>
  );
  return actions ? (
    <div className="directory-status">
      {summary}
      {actions}
    </div>
  ) : (
    summary
  );
}
