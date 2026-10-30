import { IconButton } from "./Action";
/** Quiet metadata for the current filtered list, using only already-known counts. */
import type { ReactNode } from "react";

export function DirectoryResults({
  count,
  total,
  loadedOnly = false,
  actions,
  pagination,
}: {
  count: number;
  total?: number;
  loadedOnly?: boolean;
  actions?: ReactNode;
  pagination?: {
    page: number;
    pages: number;
    size: string;
    from: number;
    to: number;
    setPage: (page: number) => void;
    setSize: (size: string) => void;
  };
}) {
  const summary = (
    <p className="directory-results" aria-label="Directory results">
      {pagination
        ? `${String(count)} ${count === 1 ? "record" : "records"} matching · ${String(total ?? count)} total · ${String(pagination.from)}–${String(pagination.to)} shown`
        : total !== undefined && total !== count
          ? `${String(count)} of ${String(total)} records`
          : loadedOnly
            ? `${String(count)} shown`
            : `${String(count)} ${count === 1 ? "record" : "records"}`}
    </p>
  );
  if (pagination)
    return (
      <div className="directory-pagination">
        <p className="directory-results" aria-label="Directory results">
          <strong>
            {pagination.from}–{pagination.to}
          </strong>{" "}
          of {count} {count === 1 ? "record" : "records"}
          <span className="directory-pagination-total">
            {" "}
            · {total ?? count} total
          </span>
        </p>
        <div className="directory-pagination-controls">
          <label className="directory-pagination-size">
            <span>Per page</span>
            <select
              aria-label="Records per page"
              value={pagination.size}
              onChange={(event) => {
                pagination.setSize(event.target.value);
              }}
            >
              {["20", "50", "100", "all"].map((size) => (
                <option key={size} value={size}>
                  {size === "all" ? "All" : size}
                </option>
              ))}
            </select>
          </label>
          <nav aria-label="Pagination" className="directory-pagination-nav">
            <IconButton
              icon="chevron-down"
              label="Previous page"
              tooltip="Previous page"
              className="directory-pagination-back"
              disabled={pagination.page === 0}
              onClick={() => {
                pagination.setPage(pagination.page - 1);
              }}
            />
            <span
              className="directory-pagination-position"
              aria-label={`Page ${String(pagination.page + 1)} of ${String(pagination.pages)}`}
            >
              {pagination.page + 1}
              <span aria-hidden="true"> / </span>
              <span className="sr-only"> of </span>
              {pagination.pages}
            </span>
            <IconButton
              icon="chevron-down"
              label="Next page"
              tooltip="Next page"
              className="directory-pagination-forward"
              disabled={pagination.page + 1 >= pagination.pages}
              onClick={() => {
                pagination.setPage(pagination.page + 1);
              }}
            />
          </nav>
          {actions}
        </div>
      </div>
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
