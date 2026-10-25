import { GeographyHeader } from "../geography/GeographyHeader";
import { ActionButton } from "../components/Action";
import {
  DirectoryFilterSelect,
  DirectoryTools,
} from "../components/DirectoryTools";
import {
  useCallback,
  useEffect,
  useState,
  useRef,
  type ReactNode,
  type MouseEvent,
} from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { BotanicalName, DirectorySearch } from "../components/ReferenceUI";
import { TaskDialog } from "../components/TaskDialog";
import { MapWorkspace } from "../maps/MapWorkspace";
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

function SelectedIdentity({
  id,
  scope,
  onClear,
}: {
  id: string;
  scope: Scope;
  onClear: () => void;
}) {
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
        <ActionButton
          icon="clear-selection"
          type="button"
          className="button--secondary"
          onClick={onClear}
        >
          Clear selection
        </ActionButton>
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
  const inspector = (
    <section className="distribution-inspector" aria-label="Selected species">
      <h3>
        <BotanicalName
          label={identity.display_label}
          scientificName={identity.scientific_name}
        />
      </h3>
      {identity.common_name && <p>{identity.common_name}</p>}
      <Representation identity={identity} />
      <p>
        <a href={`#/identities/${identity.id}?tab=reference`}>
          Botanical identity details and external taxon link
        </a>
      </p>

      <p className="field-help">
        {identity.external_taxon_id ? (
          <>
            Linked GBIF taxon: <code>{identity.external_taxon_id}</code>
          </>
        ) : (
          eligibility[identity.occurrence_eligibility]
        )}
      </p>
      <ActionButton
        icon="clear-selection"
        type="button"
        className="button--secondary"
        onClick={onClear}
      >
        Clear selection
      </ActionButton>
    </section>
  );
  if (!identity.matches_scope)
    return (
      <MapWorkspace browserLabel="Inspector" browser={inspector}>
        <div className="distribution-map-placeholder">
          <p role="status">
            The selected identity no longer matches this collection scope.
            Change the scope or clear the selection.
          </p>
        </div>
      </MapWorkspace>
    );
  if (identity.occurrence_eligibility !== "available")
    return (
      <MapWorkspace browserLabel="Inspector" browser={inspector}>
        <div className="distribution-map-placeholder">
          <h3>{eligibility[identity.occurrence_eligibility]}</h3>
          <p>
            Occurrence distribution is unavailable until this BotanicalIdentity
            is linked to a supported external taxon. This does not mean the
            species has no occurrence records.
          </p>
          <a
            className="button-link button--secondary"
            href={`#/identities/${identity.id}?tab=source`}
          >
            Link botanical source
          </a>
        </div>
      </MapWorkspace>
    );
  return (
    <OccurrenceMapPanel
      key={`${identity.id}:${identity.external_taxon_id ?? ""}`}
      identityId={identity.id}
      identityLabel={
        <BotanicalName
          label={identity.display_label}
          scientificName={identity.scientific_name}
        />
      }
      link={{ provider: "gbif", external_id: identity.external_taxon_id ?? "" }}
      inspector={inspector}
    />
  );
}

export function SpeciesDistributionScreen() {
  const auth = useAuth();
  const [chooserOpen, setChooserOpen] = useState(false);
  const [preview, setPreview] = useState<RepresentedIdentity | null>(null);
  const chooserTrigger = useRef<HTMLButtonElement>(null);
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
  function choose(event: MouseEvent<HTMLButtonElement>) {
    chooserTrigger.current = event.currentTarget;
    setChooserOpen(true);
  }
  function search(id: string, label: string): ReactNode {
    return (
      <DirectorySearch
        id={id}
        label={label}
        hideLabel
        placeholder="Scientific name, common name or cultivar"
        value={q}
        onChange={(value) => {
          setOffset(0);
          view.update("q", Array.from(value).slice(0, 200).join(""));
        }}
      />
    );
  }
  return (
    <section
      className="workspace species-distribution"
      aria-labelledby="geography-species-distribution-title"
    >
      <GeographyHeader
        view="species-distribution"
        description="Observed occurrence evidence for your collection."
        actions={null}
        tools={
          <DirectoryTools
            name="Species distribution"
            search={search("distribution-search", "Search species")}
            savedViews={
              <SavedViews
                surface="species_distribution"
                state={view.savedState}
                presentation="dialog"
              />
            }
            actions={
              <button
                type="button"
                className="button--secondary"
                aria-haspopup="dialog"
                aria-expanded={chooserOpen}
                onClick={choose}
              >
                Choose species
              </button>
            }
            activeFilters={
              scope === "all"
                ? []
                : [
                    {
                      label: "Representation",
                      value:
                        scopes.find((item) => item.value === scope)?.label ??
                        scope,
                      onRemove: () => {
                        setOffset(0);
                        view.update("scope", "all");
                      },
                    },
                  ]
            }
            filters={
              <>
                <DirectoryFilterSelect
                  label="Collection representation"
                  value={scope}
                  options={scopes}
                  onChange={(value) => {
                    setOffset(0);
                    view.update("scope", value);
                  }}
                />
                <p className="field-help">
                  Living includes active Plants and Plant groups. Current also
                  includes active seeds, sowings and managed stored material.
                  Historical has retained evidence with no current material.
                </p>
              </>
            }
          />
        }
      />
      <div
        className="distribution-overview"
        aria-label="Collection occurrence readiness"
      >
        <button type="button" className="button--quiet" onClick={choose}>
          <strong>{page ? page.total : "—"}</strong> Represented identities
        </button>
        <button type="button" className="button--quiet" onClick={choose}>
          <strong>{page ? page.occurrence_ready : "—"}</strong> Eligible GBIF
          links
        </button>
        <span>
          {scopes.find((item) => item.value === scope)?.label}
          {q ? ` · Matching “${q}”` : ""}
        </span>
      </div>
      {failed && (
        <p role="alert">
          Could not load represented identities.{" "}
          <button
            type="button"
            onClick={() => {
              setAttempt((value) => value + 1);
            }}
          >
            Retry identities
          </button>
        </p>
      )}
      <p className="field-help">
        Occurrence records show observed presence and do not establish native
        range.
      </p>
      {selectedId ? (
        <SelectedIdentity
          key={`${selectedId}:${scope}:${q}:${String(navigation)}`}
          id={selectedId}
          scope={scope}
          onClear={() => {
            view.update("identity", "");
          }}
        />
      ) : (
        <MapWorkspace
          browserLabel="Inspector"
          browser={
            <section>
              <h3>Observed occurrences</h3>
              <p>
                Explore one Botanical Identity at a time. A confirmed GBIF link
                allows loading; it does not guarantee records.
              </p>
              <p>
                No occurrence evidence has been loaded. Search and species
                previews stay within Florabase.
              </p>
            </section>
          }
        >
          <div className="distribution-map-placeholder">
            <h3>Select a species</h3>
            <p>
              Choose a represented BotanicalIdentity, then explicitly load its
              occurrence map.
            </p>
            <button type="button" onClick={choose}>
              Browse botanical identities
            </button>
          </div>
        </MapWorkspace>
      )}
      {chooserOpen && (
        <TaskDialog
          title="Choose species"
          dismissOnBackdrop
          onClose={() => {
            setChooserOpen(false);
            setPreview(null);
          }}
          returnFocusTo={chooserTrigger}
          className="distribution-chooser"
        >
          <div className="section-heading">
            <h3>Choose one species</h3>
            <ActionButton
              icon="close"
              type="button"
              className="button--quiet"
              onClick={() => {
                setChooserOpen(false);
                setPreview(null);
              }}
            >
              Close
            </ActionButton>
          </div>
          {search("distribution-chooser-search", "Search botanical identities")}
          <p className="field-help">
            One identity at a time · selecting does not load external evidence.
          </p>
          <div className="distribution-preview" aria-label="Species preview">
            {preview ? (
              <>
                <BotanicalName
                  label={preview.display_label}
                  scientificName={preview.scientific_name}
                />{" "}
                · {eligibility[preview.occurrence_eligibility]}
              </>
            ) : (
              "Hover or focus a species to preview its readiness."
            )}
          </div>
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
                  Occurrence-ready means a confirmed GBIF link exists; it does
                  not guarantee occurrence records.
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
                          onMouseEnter={() => {
                            setPreview(identity);
                          }}
                          onMouseLeave={() => {
                            setPreview(null);
                          }}
                          onFocus={() => {
                            setPreview(identity);
                          }}
                          onBlur={() => {
                            setPreview(null);
                          }}
                          onClick={() => {
                            view.update("identity", identity.id);
                            setChooserOpen(false);
                            setPreview(null);
                          }}
                        >
                          <strong>
                            <BotanicalName
                              label={identity.display_label}
                              scientificName={identity.scientific_name}
                            />
                          </strong>
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
        </TaskDialog>
      )}
    </section>
  );
}
