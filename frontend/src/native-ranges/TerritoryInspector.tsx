import { useEffect, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { BotanicalName, DirectorySearch } from "../components/ReferenceUI";
import {
  listTerritoryIdentities,
  type Filters,
  type TerritoryIdentityPage,
  type Territory,
  type RangeIdentity,
} from "./api";
import { matchingContributors } from "./comparison";

export function TerritoryInspector({
  territories,
  codes,
  toggle,
  clear,
  filters,
  identities,
  comparisonIds,
  evidence,
  unavailableCodes = [],
  scopeLabel,
}: {
  unavailableCodes?: string[];
  scopeLabel?: string;
  territories: (Territory & { identity_ids?: string[] })[];
  codes: string[];
  toggle: (code: string) => void;
  clear: () => void;
  filters?: Filters;
  identities?: RangeIdentity[];
  comparisonIds?: string[];
  evidence?: (id: string) => void;
}) {
  const [search, setSearch] = useState("");
  const [territorySearch, setTerritorySearch] = useState("");
  const [match, setMatch] = useState<"any" | "all">("any");
  const [offset, setOffset] = useState(0);
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    key: string;
    data?: TerritoryIdentityPage;
    failed?: boolean;
  } | null>(null);
  const auth = useAuth();
  const key = JSON.stringify({
    codes,
    filters,
    comparisonIds,
    match,
    offset,
    attempt,
  });
  useEffect(() => {
    const request = JSON.parse(key) as {
      codes: string[];
      filters?: Filters;
      comparisonIds?: string[];
      match: "any" | "all";
      offset: number;
    };
    const requestFilters = request.filters;
    if (!request.codes.length || !requestFilters) return;
    const abort = new AbortController();
    const timer = window.setTimeout(() => {
      void listTerritoryIdentities(
        requestFilters,
        request.codes,
        request.match,
        request.comparisonIds,
        request.offset,
        abort.signal,
      ).then(
        (data) => {
          if (!abort.signal.aborted) setResult({ key, data });
        },
        (error: unknown) => {
          if (abort.signal.aborted) return;
          if (error instanceof ApiError && error.status === 401)
            auth.sessionExpired();
          else setResult({ key, failed: true });
        },
      );
    }, 150);
    return () => {
      clearTimeout(timer);
      abort.abort();
    };
  }, [key, auth]);
  const current = result?.key === key ? result : null;
  const selected = territories.filter((unit) =>
    codes.includes(unit.source_code),
  );
  const matchingIds = matchingContributors(territories, codes, match);
  const local =
    identities?.filter((identity) => matchingIds.includes(identity.id)) ?? [];
  const data = current?.data;
  const items = filters ? data?.items : local;
  const visible = items?.filter((identity) =>
    `${identity.display_label} ${identity.common_name ?? ""}`
      .toLocaleLowerCase()
      .includes(search.toLocaleLowerCase()),
  );
  function changeSelection(code: string) {
    setOffset(0);
    toggle(code);
  }
  return (
    <aside
      className="native-territory-inspector"
      aria-label="Territory inspector"
    >
      <h3>
        {scopeLabel ??
          (comparisonIds ? "Compared species" : "Explore all identities")}
      </h3>
      <p className="field-help">
        {scopeLabel
          ? "Only this identity’s recorded native-range assertions."
          : comparisonIds
            ? "Within the chosen comparison and active filters."
            : "Within the active collection scope and filters."}
      </p>
      {selected.length ? (
        <>
          <div
            className="native-territory-chips"
            aria-label="Selected territories"
          >
            {selected.map((unit) => (
              <button
                className="button--secondary"
                type="button"
                key={unit.source_code}
                aria-label={`Remove territory ${unit.name}`}
                onClick={() => {
                  changeSelection(unit.source_code);
                }}
              >
                {unit.name} ×
              </button>
            ))}
            <button
              type="button"
              className="button--quiet"
              onClick={() => {
                setOffset(0);
                clear();
              }}
            >
              Clear territories
            </button>
          </div>
          {codes.length > 1 && (
            <label className="native-match">
              Match territories
              <select
                aria-label="Match territories"
                value={match}
                onChange={(event) => {
                  setMatch(event.currentTarget.value as "any" | "all");
                  setOffset(0);
                }}
              >
                <option value="any">Present in any selected territory</option>
                <option value="all">Present in all selected territories</option>
              </select>
            </label>
          )}
          <p role="status" aria-live="polite">
            {selected.map((unit) => unit.name).join(", ")} ·{" "}
            {filters && !data
              ? "Checking identities…"
              : `${String(data?.total ?? local.length)} distinct Botanical Identities`}{" "}
            · {match === "any" ? "union" : "intersection"}
          </p>
          <p className="field-help">
            Drawing coverage may derive from a broad recorded region; it is not
            a new exact-country assertion.
          </p>
          <DirectorySearch
            id="native-inspector-search"
            label="Find matching identities on this page"
            value={search}
            onChange={setSearch}
            placeholder="Filter these results"
          />
          {current?.failed ? (
            <div role="alert">
              <p>Could not load territory identities.</p>
              <button
                type="button"
                onClick={() => {
                  setAttempt((value) => value + 1);
                }}
              >
                Retry territory identities
              </button>
            </div>
          ) : !items ? (
            <p>Loading matching identities…</p>
          ) : (
            <ul className="native-inspector-identities">
              {visible?.map((identity) => (
                <li key={identity.id}>
                  <a href={`#/identities/${identity.id}?tab=reference`}>
                    <BotanicalName
                      label={identity.display_label}
                      scientificName={identity.scientific_name}
                    />
                  </a>
                  {identity.common_name && <span>{identity.common_name}</span>}
                  <small>
                    {identity.representation === "living"
                      ? "Living"
                      : identity.representation === "current"
                        ? "Current"
                        : "Historical"}{" "}
                    collection records
                  </small>
                  {data ? (
                    (
                      data.items.find((item) => item.id === identity.id)
                        ?.matching_territories ?? []
                    ).map((unit) => (
                      <small key={unit.source_code}>
                        {unit.name}:{" "}
                        {unit.exact_recorded
                          ? "explicit country/territory record"
                          : "drawing coverage only"}
                        {unit.broad_recorded_places.length > 0 &&
                          ` · broad record: ${unit.broad_recorded_places.join(", ")}`}
                      </small>
                    ))
                  ) : (
                    <small>
                      {selected
                        .filter((unit) =>
                          unit.identity_ids?.includes(identity.id),
                        )
                        .map((unit) => unit.name)
                        .join(", ")}{" "}
                      · drawing coverage
                    </small>
                  )}
                  {evidence && (
                    <button
                      type="button"
                      className="button--quiet"
                      onClick={() => {
                        evidence(identity.id);
                      }}
                    >
                      Recorded places for {identity.display_label}
                    </button>
                  )}
                </li>
              ))}
              {visible?.length === 0 && (
                <li>
                  No matching identities in these results. No species absence is
                  established.
                </li>
              )}
            </ul>
          )}
          {data && data.total > 50 && (
            <nav className="actions" aria-label="Territory identity pages">
              <button
                type="button"
                disabled={!offset}
                onClick={() => {
                  setOffset(offset - 50);
                }}
              >
                Previous
              </button>
              <span>Page {offset / 50 + 1}</span>
              <button
                type="button"
                disabled={offset + 50 >= data.total || offset >= 100000}
                onClick={() => {
                  setOffset(offset + 50);
                }}
              >
                Next
              </button>
            </nav>
          )}
        </>
      ) : (
        <p>
          Select one or more shaded territories, or use the territory chooser
          below. Each click toggles one territory.
        </p>
      )}
      <label className="native-territory-search">
        Find a territory
        <input
          type="search"
          value={territorySearch}
          onChange={(event) => {
            setTerritorySearch(event.currentTarget.value);
          }}
        />
      </label>
      <ul className="native-territory-options" aria-label="Territory chooser">
        {territories
          .filter((unit) =>
            unit.name
              .toLocaleLowerCase()
              .includes(territorySearch.toLocaleLowerCase()),
          )
          .map((unit) => (
            <li key={unit.source_code}>
              <button
                type="button"
                className="button--secondary native-territory-choice"
                aria-pressed={codes.includes(unit.source_code)}
                onClick={() => {
                  changeSelection(unit.source_code);
                }}
              >
                <span>
                  {unit.name}
                  {unavailableCodes.includes(unit.source_code) && (
                    <small> · boundary unavailable</small>
                  )}
                </span>
                <strong>
                  {unit.identity_count}{" "}
                  {unit.identity_count === 1 ? "identity" : "identities"}
                </strong>
              </button>
            </li>
          ))}
      </ul>
    </aside>
  );
}
