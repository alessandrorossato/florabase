import { useId, type ReactNode } from "react";
import { PageHeader } from "../components/ReferenceUI";
import {
  DirectoryTools,
  DirectorySearch,
  type ActiveDirectoryFilter,
} from "../components/DirectoryTools";

/** Activity owns its filter semantics; the shared directory controls own the surface. */
export function ActivityPageHeader({
  name,
  titleId,
  subtitle,
  query,
  onSearch,
  resetFilters,
  savedViews,
  primaryAction,
  activeFilters,
  children,
}: {
  name: "Journal" | "History" | "Schedule";
  titleId: string;
  subtitle: string;
  query: string;
  onSearch: (value: string) => void;
  resetFilters: () => void;
  savedViews?: ReactNode;
  primaryAction?: ReactNode;
  activeFilters: ActiveDirectoryFilter[];
  children: ReactNode;
}) {
  const id = useId();
  return (
    <PageHeader
      eyebrow="Activity"
      title={name}
      titleId={titleId}
      description={subtitle}
      tools={
        <DirectoryTools
          name={name}
          search={
            <DirectorySearch
              id={`${id}-search`}
              label={`Search ${name}`}
              placeholder={`Search ${name.toLowerCase()}…`}
              value={query}
              onChange={onSearch}
              maxLength={200}
              hideLabel
            />
          }
          context={
            activeFilters.length > 0 && (
              <button
                type="button"
                className="button--quiet"
                onClick={resetFilters}
              >
                Clear filters
              </button>
            )
          }
          filters={<div className="activity-filter-fields">{children}</div>}
          activeFilters={activeFilters}
          onReset={resetFilters}
          savedViews={savedViews}
          actions={primaryAction}
        />
      }
    />
  );
}
