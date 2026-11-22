import { useEffect, useId, useState } from "react";

import { ApiError, isExpectedAuthCancellation, requestJson } from "../auth/api";
import { useAuth } from "../auth/context";
import type { SearchResponse } from "../collection/searchApi";
import { searchKindLabels } from "../collection/searchApi";
import { InfoDisclosure } from "../components/ContextualHelp";
import { DetailEmptyState } from "../components/DetailEmptyState";
import { PageHeader } from "../components/ReferenceUI";
import { ancestryHref, identityLineageHref } from "./useRecordedLineage";
import "./identity-lineage.css";

type Hit = SearchResponse["groups"][number]["items"][number];

/** Material kinds with a recorded ancestry; identities open their whole-identity view. */
const kinds = [
  "botanical_identity",
  "plant",
  "plant_group",
  "seed_lot",
  "sowing",
] as const;
type LineageSearchKind = (typeof kinds)[number];

function lineageTarget(hit: Hit) {
  const kind = hit.kind as LineageSearchKind;
  return kind === "botanical_identity"
    ? identityLineageHref(hit.id)
    : ancestryHref(kind, hit.id);
}

type Answer =
  | { query: string; status: "ready"; groups: SearchResponse["groups"] }
  | { query: string; status: "error" };

/** Explore → Lineage: find an identity or a record, then open its recorded lineage. */
export function LineageHome() {
  const auth = useAuth();
  const { capability, sessionExpired } = auth;
  const authorized =
    auth.state.status === "authenticated" && capability.isAuthorized();
  const titleId = useId();
  const inputId = useId();
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const trimmed = query.trim();

  useEffect(() => {
    if (!authorized || trimmed.length < 2) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams({ q: trimmed, limit: "8" });
      for (const kind of kinds) params.append("kind", kind);
      requestJson<SearchResponse>(`/api/v1/search?${params.toString()}`, {
        capability,
        signal: controller.signal,
      })
        .then((response) => {
          setAnswer({
            query: trimmed,
            status: "ready",
            // Identities first: they open the whole-identity view.
            groups: response.groups
              .filter((group) => group.items.length > 0)
              .sort(
                (a, b) =>
                  Number(b.kind === "botanical_identity") -
                  Number(a.kind === "botanical_identity"),
              ),
          });
        })
        .catch((error: unknown) => {
          if (controller.signal.aborted || isExpectedAuthCancellation(error))
            return;
          if (error instanceof ApiError && error.status === 401) {
            sessionExpired();
            return;
          }
          setAnswer({ query: trimmed, status: "error" });
        });
    }, 180);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [authorized, capability, sessionExpired, trimmed]);

  const current = answer?.query === trimmed ? answer : null;
  return (
    <section className="ancestry-explorer" aria-labelledby={titleId}>
      <PageHeader
        eyebrow="Explore"
        title="Lineage"
        titleId={titleId}
        description="Follow recorded material relationships for one record or across a whole botanical identity."
      />
      <InfoDisclosure label="What lineage shows">
        <p>
          Choose a botanical identity to see every record of it arranged by its
          recorded relationships, or choose a Seed lot, Sowing, Plant or Plant
          group to explore its own ancestry and descendants. Only explicitly
          recorded relationships are drawn; a shared identity, Location or
          taxonomy never implies ancestry.
        </p>
      </InfoDisclosure>
      <form
        role="search"
        className="lineage-home__search"
        onSubmit={(event) => {
          event.preventDefault();
        }}
      >
        <label htmlFor={inputId}>Find an identity or record</label>
        <input
          id={inputId}
          type="search"
          value={query}
          autoComplete="off"
          placeholder="Scientific name, label…"
          onChange={(event) => {
            setQuery(event.target.value);
          }}
        />
      </form>
      {trimmed.length < 2 ? (
        <p className="ancestry-origin">Type at least two characters.</p>
      ) : !current ? (
        <p role="status">Searching…</p>
      ) : current.status === "error" ? (
        <p className="notice notice--error" role="alert">
          Florabase could not search the collection.
        </p>
      ) : current.groups.length === 0 ? (
        <DetailEmptyState>No identity or record matches.</DetailEmptyState>
      ) : (
        <div className="lineage-home__results">
          {current.groups.map((group) => (
            <section
              key={group.kind}
              className="ancestry-section"
              aria-labelledby={`${titleId}-${group.kind}`}
            >
              <h3 id={`${titleId}-${group.kind}`}>
                {group.kind === "botanical_identity"
                  ? "Botanical identities"
                  : `${searchKindLabels[group.kind]} records`}
              </h3>
              <ul className="lineage-home__hits">
                {group.items.map((hit) => (
                  <li key={hit.id}>
                    <a href={lineageTarget(hit)}>{hit.title}</a>
                    {hit.context && <span>{hit.context}</span>}
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </section>
  );
}
