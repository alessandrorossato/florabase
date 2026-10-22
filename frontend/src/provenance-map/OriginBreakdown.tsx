import { useState } from "react";
import { TaskDialog } from "../components/TaskDialog";
import type { ProvenanceMapSite } from "./api";
import { identityGroups, uniqueRecords } from "./model";
import { OriginRecords } from "./OriginInspector";

export type Breakdown = "sites" | "records" | "identities";
const titles = {
  sites: "Visible mapped sites",
  records: "Directly linked collection records",
  identities: "Botanical identities represented",
};

export function OriginBreakdown({
  kind,
  sites,
  onClose,
  onSelect,
}: {
  kind: Breakdown;
  sites: ProvenanceMapSite[];
  onClose: () => void;
  onSelect: (id: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const text = query.trim().toLocaleLowerCase();
  const records = uniqueRecords(sites).filter((record) =>
    `${record.label ?? ""} ${record.botanical_identity.display_label}`
      .toLocaleLowerCase()
      .includes(text),
  );
  const groups = identityGroups(records);
  const matchingSites = sites.filter((site) =>
    `${site.name} ${site.geographic_place_path ?? ""}`
      .toLocaleLowerCase()
      .includes(text),
  );
  const count =
    kind === "sites"
      ? matchingSites.length
      : kind === "identities"
        ? groups.length
        : records.length;
  return (
    <TaskDialog
      title={titles[kind]}
      onClose={onClose}
      dismissOnBackdrop
      className="origins-breakdown"
    >
      <div className="section-heading">
        <h3>{titles[kind]}</h3>
        <button type="button" className="button--quiet" onClick={onClose}>
          Close
        </button>
      </div>
      <p className="field-help">
        Current map filters · record counts describe distinct records, not
        material quantities.
      </p>
      <label className="field">
        Search breakdown
        <input
          type="search"
          value={query}
          onChange={(event) => {
            setQuery(event.currentTarget.value);
            setPage(0);
          }}
        />
      </label>
      <p role="status">
        {count}{" "}
        {kind === "sites"
          ? "sites"
          : kind === "identities"
            ? "identities"
            : "records"}
      </p>
      {kind === "records" ? (
        <OriginRecords key={query} records={records} />
      ) : (
        <ul className="origins-sites">
          {(kind === "sites" ? matchingSites : groups)
            .slice(page * 25, (page + 1) * 25)
            .map((item) =>
              "identity" in item ? (
                <li key={item.identity.id}>
                  <a href={`#/identities/${item.identity.id}`}>
                    {item.identity.display_label}
                  </a>
                  <span>{item.records.length} directly linked records</span>
                </li>
              ) : (
                <li key={item.id}>
                  <button
                    type="button"
                    className="button--quiet"
                    onClick={() => {
                      onSelect(item.id);
                      onClose();
                    }}
                  >
                    <strong>{item.name}</strong>
                    <span>
                      {item.geographic_place_path ??
                        "No named geographic place"}
                    </span>
                    <small>{item.usage.total} directly linked records</small>
                  </button>
                </li>
              ),
            )}
        </ul>
      )}
      {kind !== "records" && count > 25 && (
        <div className="actions">
          <button
            type="button"
            className="button--secondary"
            disabled={page === 0}
            onClick={() => {
              setPage(page - 1);
            }}
          >
            Previous
          </button>
          <button
            type="button"
            className="button--secondary"
            disabled={(page + 1) * 25 >= count}
            onClick={() => {
              setPage(page + 1);
            }}
          >
            Next
          </button>
        </div>
      )}
      <button type="button" onClick={onClose}>
        Done
      </button>
    </TaskDialog>
  );
}
