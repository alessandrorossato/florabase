/** Quiet metadata for the current filtered list, using only already-known counts. */
export function DirectoryResults({
  count,
  total,
  loadedOnly = false,
}: {
  count: number;
  total?: number;
  loadedOnly?: boolean;
}) {
  return (
    <p className="directory-results" aria-label="Directory results">
      {total !== undefined && total !== count
        ? `${String(count)} of ${String(total)} records`
        : loadedOnly
          ? `${String(count)} shown`
          : `${String(count)} ${count === 1 ? "record" : "records"}`}
    </p>
  );
}
