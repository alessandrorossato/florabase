import { ActionLink } from "../components/Action";
import { useRef, useState } from "react";
import type { ProvenanceMapRecord, ProvenanceMapSite } from "./api";
import {
  identityGroups,
  recordHref,
  recordKey,
  recordTypeLabel,
} from "./model";

const PAGE_SIZE = 25;

export function OriginRecords({ records }: { records: ProvenanceMapRecord[] }) {
  const [limit, setLimit] = useState(PAGE_SIZE);
  return (
    <>
      <ul className="origins-records">
        {records.slice(0, limit).map((record) => (
          <li key={recordKey(record)}>
            <a href={recordHref(record)}>
              {record.label ?? record.botanical_identity.display_label}
            </a>
            <span>
              {recordTypeLabel(record)} ·{" "}
              <span
                className={`lifecycle-badge lifecycle-badge--${record.is_active ? "active" : "historical"}`}
              >
                {record.lifecycle.charAt(0).toUpperCase() +
                  record.lifecycle.slice(1)}
              </span>
            </span>
          </li>
        ))}
      </ul>
      {records.length > limit && (
        <button
          type="button"
          className="button--secondary"
          onClick={() => {
            setLimit(limit + PAGE_SIZE);
          }}
        >
          Show more records ({records.length - limit} remaining)
        </button>
      )}
    </>
  );
}

function OriginIdentities({ records }: { records: ProvenanceMapRecord[] }) {
  const [identityQuery, setIdentityQuery] = useState("");
  const [identityLimit, setIdentityLimit] = useState(PAGE_SIZE);
  const groups = identityGroups(records);
  const matches = groups.filter(({ identity }) =>
    identity.display_label
      .toLocaleLowerCase()
      .includes(identityQuery.trim().toLocaleLowerCase()),
  );
  return (
    <>
      {groups.length > 5 && (
        <label className="field">
          Find a linked identity
          <input
            type="search"
            value={identityQuery}
            onChange={(event) => {
              setIdentityQuery(event.currentTarget.value);
              setIdentityLimit(PAGE_SIZE);
            }}
          />
        </label>
      )}
      <div className="origins-identities">
        {matches.slice(0, identityLimit).map(({ identity, records: items }) => (
          <details key={identity.id} open={groups.length === 1 || undefined}>
            <summary>
              {identity.display_label}
              <small>
                {items.length} {items.length === 1 ? "record" : "records"}
              </small>
            </summary>
            <a
              className="origins-identity-link"
              href={`#/identities/${identity.id}`}
            >
              Botanical identity: {identity.display_label}
            </a>
            <OriginRecords records={items} />
          </details>
        ))}
      </div>
      {matches.length === 0 && <p>No linked identities match this search.</p>}
      {matches.length > identityLimit && (
        <button
          type="button"
          className="button--secondary"
          onClick={() => {
            setIdentityLimit(identityLimit + PAGE_SIZE);
          }}
        >
          Show more identities
        </button>
      )}
    </>
  );
}

export function OriginInspector({
  sites,
  selected,
  onSelect,
  onClear,
}: {
  sites: ProvenanceMapSite[];
  selected: ProvenanceMapSite | null;
  onSelect: (id: string) => void;
  onClear: () => void;
}) {
  const root = useRef<HTMLElement>(null);
  const clear = () => {
    const id = selected?.id ?? "";
    onClear();
    requestAnimationFrame(() => {
      const destination =
        root.current?.querySelector<HTMLElement>(`[data-site-id="${id}"]`) ??
        root.current?.querySelector<HTMLElement>("input");
      destination?.focus();
    });
  };
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const matches = sites.filter((site) =>
    `${site.name} ${site.geographic_place_path ?? ""}`
      .toLocaleLowerCase()
      .includes(query.trim().toLocaleLowerCase()),
  );
  const groups = identityGroups(selected?.records ?? []);
  return (
    <aside
      ref={root}
      className="origins-inspector"
      aria-label="Provenance site inspector"
      onKeyDown={(event) => {
        if (
          event.key === "Escape" &&
          selected &&
          !(event.target instanceof HTMLInputElement)
        ) {
          event.preventDefault();
          clear();
        }
      }}
    >
      {selected ? (
        <>
          <button type="button" className="button--quiet" onClick={clear}>
            ← All visible sites
          </button>
          <section key={selected.id} aria-labelledby="origin-site-title">
            <p className="eyebrow">Selected provenance site</p>
            <h3 tabIndex={-1} id="origin-site-title">
              {selected.name}
            </h3>
            <p className="origins-place">
              {selected.geographic_place_path ?? "No named geographic place"}
            </p>
            <dl className="detail-list detail-list--compact">
              <div>
                <dt>Coordinates · WGS84</dt>
                <dd>
                  {selected.latitude}, {selected.longitude}
                </dd>
              </div>
              <div>
                <dt>Recorded accuracy</dt>
                <dd>
                  {selected.coordinate_accuracy_m === null
                    ? "Not recorded"
                    : `± ${selected.coordinate_accuracy_m} m`}
                </dd>
              </div>
            </dl>
            <p className="origins-site-counts">
              <strong>{selected.usage.total}</strong> directly linked{" "}
              {selected.usage.total === 1 ? "record" : "records"} ·{" "}
              <strong>{groups.length}</strong> botanical{" "}
              {groups.length === 1 ? "identity" : "identities"}
            </p>
            <p className="field-help">
              {selected.usage.seed_lots} SeedLots · {selected.usage.plants}{" "}
              Plants · {selected.usage.plant_groups} PlantGroups
            </p>
            <ActionLink icon="edit" href={`#/geography/${selected.id}`}>
              Manage provenance site
            </ActionLink>
            {selected.records.length === 0 && (
              <p className="notice">
                No directly linked eligible collection records. This site still
                has recorded coordinates.
              </p>
            )}
            <OriginIdentities key={selected.id} records={selected.records} />
          </section>
        </>
      ) : (
        <>
          <h3>Recorded origin sites</h3>
          <p>
            Select a marker or a site to inspect its directly linked material.
          </p>
          <label className="field">
            Find a visible site
            <input
              type="search"
              value={query}
              onChange={(event) => {
                setQuery(event.currentTarget.value);
                setPage(0);
              }}
            />
          </label>
          <p className="field-help">
            {matches.length} of {sites.length} visible sites
          </p>
          <ul className="origins-sites">
            {matches
              .slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
              .map((site) => (
                <li key={site.id}>
                  <button
                    type="button"
                    className="button--quiet"
                    data-site-id={site.id}
                    onClick={() => {
                      onSelect(site.id);
                      requestAnimationFrame(() => {
                        root.current
                          ?.querySelector<HTMLElement>("#origin-site-title")
                          ?.focus();
                      });
                    }}
                  >
                    <strong>{site.name}</strong>
                    <span>
                      {site.geographic_place_path ??
                        "No named geographic place"}
                    </span>
                    <small>
                      {site.usage.total} linked{" "}
                      {site.usage.total === 1 ? "record" : "records"} ·{" "}
                      {identityGroups(site.records).length} identities
                    </small>
                  </button>
                </li>
              ))}
          </ul>
          {matches.length === 0 && (
            <p>No visible sites match this site search.</p>
          )}
          {matches.length > PAGE_SIZE && (
            <div className="actions">
              <button
                type="button"
                className="button--secondary"
                disabled={page === 0}
                onClick={() => {
                  setPage(page - 1);
                }}
              >
                Previous sites
              </button>
              <button
                type="button"
                className="button--secondary"
                disabled={(page + 1) * PAGE_SIZE >= matches.length}
                onClick={() => {
                  setPage(page + 1);
                }}
              >
                Next sites
              </button>
            </div>
          )}
        </>
      )}
    </aside>
  );
}
