import { Icon } from "./Icon";
import { ActionButton, IconButton } from "./Action";
import { useId, useState, type ReactNode } from "react";
import { DirectorySearch } from "./ReferenceUI";
import { TaskDialog } from "./TaskDialog";

export interface ActiveDirectoryFilter {
  label: string;
  value: string;
  onRemove: () => void;
}

/** Existing directory state stays with the page; this owns only the filter surface. */
export function DirectoryTools({
  name,
  search,
  savedViews,
  actions,
  filters,
  onReset,
  activeFilters = [],
  context,
}: {
  name: string;
  search?: ReactNode;
  savedViews?: ReactNode;
  actions?: ReactNode;
  filters?: ReactNode;
  onReset?: () => void;
  activeFilters?: ActiveDirectoryFilter[];
  context?: ReactNode;
}) {
  const id = useId();
  const [open, setOpen] = useState(false);
  return (
    <>
      <div
        className="directory-tools"
        role="group"
        aria-label={`${name} toolbar`}
      >
        {search}
        {filters && (
          <ActionButton
            icon="filter"
            type="button"
            className="button--secondary"
            aria-haspopup="dialog"
            aria-expanded={open}
            aria-controls={open ? id : undefined}
            onClick={() => {
              setOpen(true);
            }}
          >
            Filters
            {activeFilters.length ? ` (${String(activeFilters.length)})` : ""}
          </ActionButton>
        )}
        {savedViews}
        {actions}
      </div>
      {context && <div className="directory-context">{context}</div>}
      {activeFilters.length > 0 && (
        <div
          className="directory-filter-summary"
          role="group"
          aria-label="Active filters"
        >
          {activeFilters.map((filter) => (
            <button
              type="button"
              className="button--quiet control-action"
              key={filter.label}
              aria-label={`Remove ${filter.label.toLowerCase()} filter`}
              onClick={filter.onRemove}
            >
              <span>
                {filter.label}: {filter.value}
              </span>
              <Icon name="close" />
            </button>
          ))}
        </div>
      )}
      {open && (
        <TaskDialog
          id={id}
          title={`${name} filters`}
          className="directory-filter-drawer"
          dismissOnBackdrop
          onClose={() => {
            setOpen(false);
          }}
        >
          <div className="section-heading">
            <h3>Filters</h3>
            <IconButton
              icon="close"
              label="Close"
              tooltip={`Close ${name} filters`}
              visibleLabel="Close"
              className="button--quiet"
              onClick={() => {
                setOpen(false);
              }}
            />
          </div>
          <div className="directory-filter-fields">{filters}</div>
          <p className="field-help">
            Filters apply as you choose. Search stays unchanged.
          </p>
          <div className="actions">
            {activeFilters.length > 0 && onReset && (
              <button
                type="button"
                className="button--secondary"
                onClick={onReset}
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

export function DirectoryFilterSelect<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: readonly { value: T; label: string }[];
  onChange: (value: T) => void;
}) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <select
        id={id}
        value={value}
        onChange={(event) => {
          onChange(event.currentTarget.value as T);
        }}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

// Re-export the established search grammar for directory consumers.
export { DirectorySearch };
