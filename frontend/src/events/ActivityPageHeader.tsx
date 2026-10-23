import { ActionButton } from "../components/Action";
import { useId, useState, type ReactNode } from "react";
import { TaskDialog } from "../components/TaskDialog";
import { PageHeader, DirectorySearch } from "../components/ReferenceUI";
import "../collection/dashboard.css";

export function ActivityPageHeader({
  name,
  titleId,
  subtitle,
  query,
  onSearch,
  filterCount,
  resetFilters,
  savedViews,
  primaryAction,
  summary,
  children,
}: {
  name: "Journal" | "History" | "Schedule";
  titleId: string;
  subtitle: string;
  query: string;
  onSearch: (value: string) => void;
  filterCount: number;
  resetFilters: () => void;
  savedViews?: ReactNode;
  primaryAction?: ReactNode;
  summary: ReactNode;
  children: ReactNode;
}) {
  const id = useId();
  const [open, setOpen] = useState(false);
  return (
    <>
      <PageHeader
        eyebrow="Activity"
        title={name}
        titleId={titleId}
        description={subtitle}
        tools={
          <div
            className="dashboard-toolbar activity-toolbar"
            role="group"
            aria-label={`${name} toolbar`}
          >
            <DirectorySearch
              id={`${id}-search`}
              label={`Search ${name}`}
              placeholder={`Search ${name.toLowerCase()}…`}
              value={query}
              onChange={onSearch}
              maxLength={200}
              hideLabel
              className="dashboard-search-field"
            />
            <ActionButton
              icon="filter"
              type="button"
              className="button--secondary"
              aria-haspopup="dialog"
              aria-expanded={open}
              aria-controls={open ? `${id}-filters` : undefined}
              onClick={() => {
                setOpen(true);
              }}
            >
              Filters{filterCount ? ` (${String(filterCount)})` : ""}
            </ActionButton>
            {savedViews}
            {primaryAction}
          </div>
        }
      />
      {filterCount > 0 && (
        <div
          className="activity-filter-summary"
          role="group"
          aria-label="Active filters"
        >
          {summary}
          <button
            className="button--quiet"
            type="button"
            onClick={resetFilters}
          >
            Clear filters
          </button>
        </div>
      )}
      {open && (
        <TaskDialog
          id={`${id}-filters`}
          title={`${name} filters`}
          className="dashboard-filter-drawer activity-filter-drawer"
          dismissOnBackdrop
          onClose={() => {
            setOpen(false);
          }}
        >
          <div className="section-heading">
            <h3>Filters</h3>
            <ActionButton
              icon="close"
              type="button"
              className="button--quiet"
              onClick={() => {
                setOpen(false);
              }}
            >
              Close
            </ActionButton>
          </div>
          <div className="dashboard-drawer-fields">{children}</div>
          <div className="dashboard-drawer-actions">
            {filterCount > 0 && (
              <button
                type="button"
                className="button--secondary"
                onClick={resetFilters}
              >
                Reset filters
              </button>
            )}
            <ActionButton
              variant="secondary"
              type="button"
              onClick={() => {
                setOpen(false);
              }}
            >
              Done
            </ActionButton>
          </div>
        </TaskDialog>
      )}
    </>
  );
}
