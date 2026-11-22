import { useEffect, useId, useState } from "react";

import { ApiError, isExpectedAuthCancellation, requestJson } from "../auth/api";
import { useAuth } from "../auth/context";
import type { SearchResponse } from "../collection/searchApi";
import { searchKindLabels } from "../collection/searchApi";
import { InfoDisclosure } from "../components/ContextualHelp";
import { DetailEmptyState } from "../components/DetailEmptyState";
import {
  BotanicalName,
  DirectorySearch,
  PageHeader,
} from "../components/ReferenceUI";
import type { BotanicalIdentityResponse } from "../botanical-identities/api";
import { ancestryHref, identityLineageHref } from "./useRecordedLineage";
import "../maps/maps.css";
import "./identity-lineage.css";

type Counts = NonNullable<BotanicalIdentityResponse["collection_counts"]>;
const countsOf = (item: BotanicalIdentityResponse): Counts =>
  item.collection_counts ?? {
    seed_lots: 0,
    sowings: 0,
    plants: 0,
    plant_groups: 0,
    vegetative_lots: 0,
    propagation_attempts: 0,
  };
const materialTotal = (c: Counts) =>
  c.seed_lots +
  c.sowings +
  c.plants +
  c.plant_groups +
  c.vegetative_lots +
  c.propagation_attempts;
const plural = (n: number, one: string, many: string) =>
  `${String(n)} ${n === 1 ? one : many}`;

/** Material counts of one identity in collection order, e.g. "3 seed lots · 2 sowings · 1 plant". */
function chain(c: Counts) {
  return (
    [
      c.seed_lots && plural(c.seed_lots, "seed lot", "seed lots"),
      c.sowings && plural(c.sowings, "sowing", "sowings"),
      c.plants + c.plant_groups &&
        plural(
          c.plants + c.plant_groups,
          "plant or group",
          "plants and groups",
        ),
      c.vegetative_lots + c.propagation_attempts &&
        plural(
          c.vegetative_lots + c.propagation_attempts,
          "cutting record",
          "cutting records",
        ),
    ]
      .filter(Boolean)
      // Counts only: a shared identity never implies recorded lineage, so no arrows here.
      .join(" · ")
  );
}

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
  const [identities, setIdentities] = useState<
    BotanicalIdentityResponse[] | null | "error"
  >(null);
  const trimmed = query.trim();

  useEffect(() => {
    if (!authorized) return;
    const controller = new AbortController();
    requestJson<BotanicalIdentityResponse[]>("/api/v1/botanical-identities", {
      capability,
      signal: controller.signal,
    })
      .then((list) => {
        setIdentities(Array.isArray(list) ? list : []);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || isExpectedAuthCancellation(error))
          return;
        if (error instanceof ApiError && error.status === 401) {
          sessionExpired();
          return;
        }
        setIdentities("error");
      });
    return () => {
      controller.abort();
    };
  }, [authorized, capability, sessionExpired]);

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
  const represented = Array.isArray(identities)
    ? identities
        .filter((item) => !item.merged_into_id)
        .filter((item) => materialTotal(countsOf(item)) > 0)
        .sort(
          (a, b) =>
            materialTotal(countsOf(b)) - materialTotal(countsOf(a)) ||
            a.display_label.localeCompare(b.display_label),
        )
    : [];
  const sum = (pick: (c: Counts) => number) =>
    represented.reduce((total, item) => total + pick(countsOf(item)), 0);
  return (
    <section
      className="ancestry-explorer lineage-home"
      aria-labelledby={titleId}
    >
      <PageHeader
        eyebrow="Explore"
        title="Lineage"
        titleId={titleId}
        description="Follow recorded material relationships for one record or across a whole botanical identity."
        tools={
          <DirectorySearch
            id={inputId}
            label="Find an identity or record"
            placeholder="Scientific name, label…"
            value={query}
            onChange={setQuery}
            hideLabel
          />
        }
      />
      {represented.length > 0 && (
        <div
          className="lineage-overview"
          aria-label="Collection material counts"
        >
          <span>
            <strong>{represented.length}</strong> Represented identities
          </span>
          <span>
            <strong>{sum((c) => c.seed_lots)}</strong> Seed lots
          </span>
          <span>
            <strong>{sum((c) => c.sowings)}</strong> Sowings
          </span>
          <span>
            <strong>{sum((c) => c.plants + c.plant_groups)}</strong> Plants and
            groups
          </span>
          <span>
            <strong>
              {sum((c) => c.vegetative_lots + c.propagation_attempts)}
            </strong>{" "}
            Cutting records
          </span>
        </div>
      )}
      <InfoDisclosure label="What lineage shows">
        <p>
          Choose a botanical identity to see every record of it arranged by its
          recorded relationships, or choose a Seed lot, Sowing, Plant or Plant
          group to explore its own ancestry and descendants. Only explicitly
          recorded relationships are drawn; a shared identity, Location or
          taxonomy never implies ancestry.
        </p>
      </InfoDisclosure>
      {trimmed.length < 2 ? (
        <section className="lineage-stage" aria-labelledby={`${titleId}-all`}>
          <h3 id={`${titleId}-all`}>Botanical identities in the collection</h3>
          {identities === null && <p role="status">Loading identities…</p>}
          {identities === "error" && (
            <p className="notice notice--error" role="alert">
              Florabase could not load the botanical identities.
            </p>
          )}
          {Array.isArray(identities) && represented.length === 0 && (
            <DetailEmptyState>
              No botanical identity has collection records yet.
            </DetailEmptyState>
          )}
          {represented.length > 0 && (
            <ul className="lineage-gallery">
              {represented.map((item) => (
                <li key={item.id}>
                  <a href={identityLineageHref(item.id)}>
                    {/* display_label keeps cultivars of one species apart. */}
                    <strong>
                      <BotanicalName
                        label={item.display_label}
                        scientificName={item.scientific_name}
                      />
                    </strong>
                    {item.common_name && <span>{item.common_name}</span>}
                    <small>{chain(countsOf(item))}</small>
                  </a>
                </li>
              ))}
            </ul>
          )}
        </section>
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
