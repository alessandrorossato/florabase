import { PageHeader } from "../../components/ReferenceUI";
import { useState, type ReactNode } from "react";
import {
  DirectoryPage,
  DirectoryViewSwitcher,
  DirectoryRecords,
} from "../../components/DirectoryPage";
import {
  DirectoryTools,
  DirectorySearch,
} from "../../components/DirectoryTools";
import type { DirectoryView } from "../../components/directoryPresentation";

export function ScaffoldDirectoryExample({
  feedback,
}: { feedback?: ReactNode } = {}) {
  const [view, setView] = useState<DirectoryView>("list");
  const [query, setQuery] = useState("");
  return (
    <DirectoryPage
      titleId="ScaffoldDirectoryExample-title"
      header={
        <PageHeader
          title="ScaffoldDirectoryExample"
          titleId="ScaffoldDirectoryExample-title"
          eyebrow="Implement domain context"
          tools={
            <DirectoryTools
              name="ScaffoldDirectoryExample"
              search={
                <DirectorySearch
                  id="ScaffoldDirectoryExample-search"
                  label="Search records"
                  placeholder="Search records…"
                  value={query}
                  onChange={setQuery}
                />
              }
              presentation={
                <DirectoryViewSwitcher value={view} onChange={setView} />
              }
              filters={<p>TODO: compose typed domain filters here.</p>}
            />
          }
        />
      }
      feedback={feedback}
      content={
        <DirectoryRecords view={view} label="Implement domain records">
          <li>
            TODO: connect the owning domain's data, rows/cards and
            loading/error/empty states.
          </li>
        </DirectoryRecords>
      }
    />
  );
}
