import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { DirectorySearch, PageHeader } from "../components/ReferenceUI";
import { OccurrenceMapPanel } from "../occurrence-map/OccurrenceMapPanel";
import { SavedViews } from "../saved-views/SavedViews";
import { useDirectoryView } from "../saved-views/useDirectoryView";
import {
  getRepresentedIdentity,
  listRepresentedIdentities,
  type IdentityPage,
  type RepresentedIdentity,
  type Scope,
} from "./api";
import "./species-distribution.css";

const scopes: { value: Scope; label: string }[] = [
  { value: "all", label: "All represented" },
  { value: "living", label: "Living" },
  { value: "current", label: "Current" },
  { value: "historical", label: "Historical" },
];
const eligibility = {
  available: "Occurrence map available",
  not_linked: "External taxon not linked",
  incompatible: "External link unavailable/incompatible",
};

function Representation({ identity }: { identity: RepresentedIdentity }) {
  return (
    <span className="distribution-context">
      <strong>
        {identity.representation === "living"
          ? "Living"
          : identity.representation === "current"
            ? "Current"
            : "Historical"}
      </strong>
      <span>
        {identity.current_records} current · {identity.retained_records}{" "}
        retained records
      </span>
    </span>
  );
}

function SelectedIdentity({ id, scope }: { id: string; scope: Scope }) {
  const auth = useAuth();
  const [identity, setIdentity] = useState<RepresentedIdentity | null>(null);
  const [error, setError] = useState<"missing" | "error" | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    void getRepresentedIdentity(id, scope, controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) {
          setIdentity(value);
          setError(null);
        }
      })
      .catch((failure: unknown) => {
        if (controller.signal.aborted) return;
        if (failure instanceof ApiError && failure.status === 401)
          auth.sessionExpired();
        else
          setError(
            failure instanceof ApiError && failure.status === 404
              ? "missing"
              : "error",
          );
      });
    return () => {
      controller.abort();
    };
  }, [id, scope, attempt, auth]);
  if (error)
    return (
      <div role="alert" className="notice notice--error">
        <p>
          {error === "missing"
            ? "The selected identity is missing or no longer represented in your collection."
            : "Could not load the selected identity."}
        </p>
        <p className="field-help">Selected identity: {id}</p>
        {error === "error" && (
          <button
            type="button"
            onClick={() => {
              setError(null);
              setAttempt((value) => value + 1);
            }}
          >
            Retry selected identity
          </button>
        )}
      </div>
    );
  if (!identity) return <p role="status">Loading selected species…</p>;
  return (
    <>
      <h3>{identity.display_label}</h3>
      {identity.common_name && <p>{identity.common_name}</p>}
      <Representation identity={identity} />
      <p>
        <a href={`#/identities/${identity.id}?tab=reference`}>
          Botanical identity details and external taxon link
        </a>
      </p>
      {!identity.matches_scope ? (
        <p role="status" className="notice">
          The selected identity no longer matches this collection scope. Change
          the scope or clear the selection.
        </p>
      ) : identity.occurrence_eligibility !== "available" ? (
        <div className="empty-state">
          <h4>{eligibility[identity.occurrence_eligibility]}</h4>
          <p>
            Occurrence distribution is unavailable until this BotanicalIdentity
            is linked to a supported external taxon. This does not mean the
            species has no occurrence records.
          </p>
        </div>
      ) : (
        <OccurrenceMapPanel
          key={`${identity.id}:${identity.external_taxon_id ?? ""}`}
          identityId={identity.id}
          link={{
            provider: "gbif",
            external_id: identity.external_taxon_id ?? "",
          }}
        />
      )}
    </>
  );
}

export function SpeciesDistributionScreen() {
  const auth = useAuth();
  const [offset, setOffset] = useState(0);
  const [navigation, setNavigation] = useState(0);
  const reset = useCallback(() => {
    setOffset(0);
    setNavigation((value) => value + 1);
  }, []);
  const view = useDirectoryView("species_distribution", reset);
  const { q, scope, identity: selectedId } = view.state;
  const [result, setResult] = useState<{
    key: string;
    page: IdentityPage;
  } | null>(null);
  const [failedQuery, setFailedQuery] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const queryKey = JSON.stringify([q, scope, offset, navigation, attempt]);
  const page = result?.key === queryKey ? result.page : null;
  const failed = failedQuery === queryKey;
  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      void listRepresentedIdentities(q, scope, offset, controller.signal)
        .then((value) => {
          if (!controller.signal.aborted)
            setResult({ key: queryKey, page: value });
        })
        .catch((failure: unknown) => {
          if (controller.signal.aborted) return;
          if (failure instanceof ApiError && failure.status === 401)
            auth.sessionExpired();
          else setFailedQuery(queryKey);
        });
    }, 150);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [q, scope, offset, queryKey, auth]);
  return (
    <section
      className="workspace species-distribution"
      aria-labelledby="distribution-title"
    >
      <PageHeader
        title="Species distribution"
        titleId="distribution-title"
        eyebrow="Explore"
        description="Explore occurrence-density evidence for species represented in your collection."
        actions={null}
      />
      <p className="field-help">
        Occurrence records show observed presence and do not establish native
        range.
      </p>
      <SavedViews surface="species_distribution" state={view.savedState} />
      <div
        role="group"
        aria-label="Collection representation scope"
        className="distribution-scopes"
      >
        {scopes.map((item) => (
          <button
            type="button"
            key={item.value}
            aria-pressed={scope === item.value}
            className={scope === item.value ? "" : "button--secondary"}
            onClick={() => {
              setOffset(0);
              view.update("scope", item.value);
            }}
          >
            {item.label}
          </button>
        ))}
      </div>
      <p className="field-help">
        Living includes active Plants and Plant groups. Current also includes
        active seeds, sowings and managed stored material. Historical has
        retained evidence with no current material.
      </p>
      <DirectorySearch
        id="distribution-search"
        label="Search species"
        placeholder="Scientific name, common name or cultivar"
        value={q}
        onChange={(value) => {
          setOffset(0);
          view.update("q", value.slice(0, 200));
        }}
      />
      <div className="distribution-workspace">
        <section
          className="distribution-browser"
          aria-labelledby="represented-title"
        >
          <h3 id="represented-title">Botanical identities</h3>
          {failed ? (
            <div role="alert">
              <p>Could not load represented identities.</p>
              <button
                type="button"
                onClick={() => {
                  setAttempt((value) => value + 1);
                }}
              >
                Retry identities
              </button>
            </div>
          ) : !page ? (
            <p role="status">Loading represented identities…</p>
          ) : (
            <>
              <p className="directory-results" role="status">
                {page.total} represented identities · {page.occurrence_ready}{" "}
                occurrence-ready
              </p>
              <p className="field-help">
                Occurrence-ready means a confirmed GBIF link exists; it does not
                guarantee occurrence records.
              </p>
              {!page.items.length ? (
                <p className="empty-state">
                  No represented identities match these filters.
                </p>
              ) : (
                <ul className="distribution-identities">
                  {page.items.map((identity) => (
                    <li key={identity.id}>
                      <button
                        type="button"
                        className="distribution-choice button--secondary"
                        aria-pressed={selectedId === identity.id}
                        onClick={() => {
                          view.update("identity", identity.id);
                        }}
                      >
                        <strong>{identity.display_label}</strong>
                        {identity.common_name && (
                          <span>{identity.common_name}</span>
                        )}
                        <Representation identity={identity} />
                        <span className="field-help">
                          {eligibility[identity.occurrence_eligibility]}
                          {selectedId === identity.id ? " · Selected" : ""}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              {(offset > 0 || offset + page.items.length < page.total) && (
                <nav
                  className="actions"
                  aria-label="Represented identity pages"
                >
                  <button
                    type="button"
                    className="button--secondary"
                    disabled={offset === 0}
                    onClick={() => {
                      setOffset((value) => Math.max(0, value - 50));
                    }}
                  >
                    Previous
                  </button>
                  <span>Page {Math.floor(offset / 50) + 1}</span>
                  <button
                    type="button"
                    className="button--secondary"
                    disabled={
                      offset + page.items.length >= page.total ||
                      offset >= 100000
                    }
                    onClick={() => {
                      setOffset((value) => value + 50);
                    }}
                  >
                    Next
                  </button>
                </nav>
              )}
            </>
          )}
        </section>
        <section
          className="distribution-selected"
          aria-label="Selected species"
        >
          {selectedId ? (
            <>
              <button
                type="button"
                className="button--secondary"
                onClick={() => {
                  view.update("identity", "");
                }}
              >
                Clear selection
              </button>
              <SelectedIdentity
                key={`${selectedId}:${scope}:${q}:${String(navigation)}`}
                id={selectedId}
                scope={scope}
              />
            </>
          ) : (
            <div className="empty-state">
              <h3>Select a species</h3>
              <p>
                Choose a represented BotanicalIdentity, then explicitly load its
                occurrence map.
              </p>
            </div>
          )}
        </section>
      </div>
    </section>
  );
}
