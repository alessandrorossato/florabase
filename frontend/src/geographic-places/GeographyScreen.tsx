import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type SyntheticEvent,
} from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { DetailHeader } from "../components/CollectionUI";
import {
  DirectorySearch,
  OverflowMenu,
  PageHeader,
  QuickPreview,
  StatStrip,
} from "../components/ReferenceUI";
import { TaskDialog } from "../components/TaskDialog";
import { useCreationDisclosure } from "../components/useCreationDisclosure";
import { ProvenanceSiteManager } from "../provenance-sites/ProvenanceSiteManager";
import {
  createGeographicPlace,
  geographyConflictMessage,
  geographyValidationMessages,
  listGeographicPlaces,
  setGeographicPlaceRetired,
  updateGeographicPlace,
  deleteGeographicPlace,
  type GeographicPlaceResponse,
} from "./api";

type DirectoryState =
  | { status: "loading" }
  | { status: "ready"; places: GeographicPlaceResponse[] }
  | { status: "error" };
type SaveState =
  | { status: "idle" }
  | { status: "saving" }
  | { status: "success"; message: string }
  | { status: "error"; message: string };

function formString(data: FormData, name: string): string {
  const value = data.get(name);
  return typeof value === "string" ? value : "";
}

function placeTypeLabel(
  type: GeographicPlaceResponse["place_type"],
  kind: GeographicPlaceResponse["place_kind"],
): string {
  switch (type) {
    case "city_town":
      return "City or town";
    case "locality":
      return "Locality";
    case "other_named_area":
      return "Other named area";
    default:
      return kind === "canonical" ? "Canonical CLDR place" : "Local place";
  }
}

function descendantsOf(id: string, places: GeographicPlaceResponse[]) {
  const descendants = new Set<string>();
  let changed = true;
  while (changed) {
    changed = false;
    for (const place of places) {
      if (
        place.parent_id &&
        (place.parent_id === id || descendants.has(place.parent_id)) &&
        !descendants.has(place.id)
      ) {
        descendants.add(place.id);
        changed = true;
      }
    }
  }
  return descendants;
}

function PlaceButton({
  place,
  selectedId,
  onSelect,
  showPath = false,
}: {
  place: GeographicPlaceResponse;
  showPath?: boolean;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <button
      type="button"
      className="identity-list-item"
      aria-pressed={selectedId === place.id}
      onClick={() => {
        onSelect(place.id);
      }}
    >
      <span>
        {place.name}
        <span className="record-state">
          {place.place_kind === "canonical" ? "Canonical" : "Local"}
        </span>
        {place.retired_at && <span className="record-state">Retired</span>}
      </span>
      {showPath && <small>{place.display_path}</small>}
    </button>
  );
}

function PlaceTree({
  places,
  parentId,
  selectedId,
  onSelect,
  expanded,
  onToggle,
}: {
  places: GeographicPlaceResponse[];
  parentId: string | null;
  selectedId: string | null;
  onSelect: (id: string) => void;
  expanded: Set<string>;
  onToggle: (id: string) => void;
}) {
  const children = places.filter((place) => place.parent_id === parentId);
  if (children.length === 0) return null;
  return (
    <ul
      className={
        parentId ? "location-tree location-tree--nested" : "location-tree"
      }
    >
      {children.map((place) => {
        const hasChildren = places.some((item) => item.parent_id === place.id);
        return (
          <li key={place.id}>
            <div className="location-tree-node">
              {hasChildren ? (
                <button
                  type="button"
                  className="location-tree-toggle"
                  aria-label={`${expanded.has(place.id) ? "Collapse" : "Expand"} ${place.name}`}
                  aria-expanded={expanded.has(place.id)}
                  onClick={() => {
                    onToggle(place.id);
                  }}
                >
                  {expanded.has(place.id) ? "−" : "+"}
                </button>
              ) : (
                <span className="location-tree-spacer" aria-hidden="true" />
              )}
              <PlaceButton
                place={place}
                selectedId={selectedId}
                onSelect={onSelect}
              />
            </div>
            {expanded.has(place.id) && (
              <PlaceTree
                places={places}
                parentId={place.id}
                selectedId={selectedId}
                onSelect={onSelect}
                expanded={expanded}
                onToggle={onToggle}
              />
            )}
          </li>
        );
      })}
    </ul>
  );
}

export function GeographyScreen({ initialSiteId }: { initialSiteId?: string }) {
  const auth = useAuth();
  const [directory, setDirectory] = useState<DirectoryState>({
    status: "loading",
  });
  const [attempt, setAttempt] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [mode, setMode] = useState<"places" | "sites" | "map">(
    initialSiteId ? "sites" : "places",
  );
  const [createName, setCreateName] = useState("");
  const [createParentId, setCreateParentId] = useState("");
  const [createType, setCreateType] = useState<
    "city_town" | "locality" | "other_named_area"
  >("other_named_area");
  const [save, setSave] = useState<SaveState>({ status: "idle" });
  const [editing, setEditing] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const createNameInput = useRef<HTMLInputElement>(null);
  const feedback = useRef<HTMLDivElement>(null);
  const {
    expanded: creationExpanded,
    triggerRef: creationTriggerRef,
    panelRef: creationPanelRef,
    open: openCreation,
    close: closeCreation,
  } = useCreationDisclosure();
  const pending = save.status === "saving";

  useEffect(() => {
    const controller = new AbortController();
    void listGeographicPlaces(controller.signal)
      .then((places) => {
        setDirectory({ status: "ready", places });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else setDirectory({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [auth, attempt]);

  useEffect(() => {
    if (save.status === "error") feedback.current?.focus();
  }, [save]);

  const places = useMemo(
    () => (directory.status === "ready" ? directory.places : []),
    [directory],
  );
  const selected = places.find((place) => place.id === selectedId) ?? null;
  const matches = filter.trim()
    ? places.filter((place) =>
        [place.display_path, place.source_code].some((value) =>
          value
            ?.toLocaleLowerCase()
            .includes(filter.trim().toLocaleLowerCase()),
        ),
      )
    : places;

  if (
    auth.state.status !== "authenticated" &&
    auth.state.status !== "logging-out" &&
    auth.state.status !== "logout-failed"
  )
    return null;
  const csrfToken = auth.state.csrfToken;

  async function apply(
    action: () => Promise<GeographicPlaceResponse>,
    message: (place: GeographicPlaceResponse) => string,
  ) {
    setSave({ status: "saving" });
    try {
      const place = await action();
      const refreshed = await listGeographicPlaces();
      setDirectory({ status: "ready", places: refreshed });
      setExpanded((current) => {
        const next = new Set(current);
        const byId = new Map(refreshed.map((item) => [item.id, item]));
        let parentId = place.parent_id;
        while (parentId) {
          next.add(parentId);
          parentId = byId.get(parentId)?.parent_id ?? null;
        }
        return next;
      });
      setSelectedId(place.id);
      setEditing(false);
      setSave({ status: "success", message: message(place) });
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else if (error instanceof ApiError && error.status === 422)
        setSave({
          status: "error",
          message: geographyValidationMessages(error).join(" "),
        });
      else if (error instanceof ApiError && error.status === 409)
        setSave({
          status: "error",
          message:
            geographyConflictMessage(error) ??
            "Florabase could not apply that hierarchy change.",
        });
      else if (error instanceof ApiError && error.status === 403)
        setSave({
          status: "error",
          message:
            "Florabase could not authorize this change. Refresh and try again.",
        });
      else
        setSave({
          status: "error",
          message:
            "Florabase could not save or refresh this geographic place. Check the connection.",
        });
    }
  }

  function selectPlace(id: string) {
    setSelectedId(id);
    setEditing(false);
    setSave({ status: "idle" });
  }

  function submitCreate(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (pending || !createParentId) return;
    void apply(
      () =>
        createGeographicPlace(
          {
            name: createName,
            parent_id: createParentId,
            place_type: createType,
          },
          csrfToken,
        ),
      (place) => {
        setCreateName("");
        setCreateParentId("");
        closeCreation({ returnFocus: false });
        return `${place.display_path} was created and selected.`;
      },
    );
  }

  function submitUpdate(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (selected?.place_kind !== "custom" || pending) return;
    const data = new FormData(event.currentTarget);
    void apply(
      () =>
        updateGeographicPlace(
          selected.id,
          {
            name: formString(data, "name"),
            parent_id: formString(data, "parent_id"),
            place_type: formString(data, "place_type") as
              "city_town" | "locality" | "other_named_area",
          },
          csrfToken,
        ),
      (place) => `${place.display_path} was updated.`,
    );
  }

  const excluded = selected
    ? new Set([selected.id, ...descendantsOf(selected.id, places)])
    : new Set<string>();
  const parentOptions = places.filter(
    (place) => !place.retired_at && !excluded.has(place.id),
  );

  return (
    <section aria-labelledby="geography-title" className="workspace">
      <PageHeader
        title="Geography"
        titleId="geography-title"
        description="Named geographic areas and precise stored collection origins."
        actions={
          mode === "places" ? (
            <button
              type="button"
              ref={creationTriggerRef}
              aria-haspopup="dialog"
              onClick={() => {
                setCreateName("");
                setCreateParentId("");
                setSave({ status: "idle" });
                openCreation();
              }}
            >
              New local place
            </button>
          ) : null
        }
      />
      <DirectorySearch
        id="geography-filter"
        label="Search geography"
        placeholder="Place, path, or provenance site"
        value={filter}
        onChange={setFilter}
        className="geography-search"
      />
      <nav aria-label="Geography views" className="geography-view-nav">
        <button
          type="button"
          aria-pressed={mode !== "map"}
          onClick={() => {
            setMode("places");
          }}
        >
          Browse
        </button>
        <button
          type="button"
          aria-pressed={mode === "map"}
          onClick={() => {
            setMode("map");
          }}
        >
          Map
        </button>
      </nav>
      {mode !== "map" && (
        <nav aria-label="Browse geography" className="geography-subnav">
          <button
            type="button"
            aria-pressed={mode === "places"}
            onClick={() => {
              setMode("places");
            }}
          >
            Places
          </button>
          <button
            type="button"
            aria-pressed={mode === "sites"}
            onClick={() => {
              setMode("sites");
            }}
          >
            Provenance sites
          </button>
        </nav>
      )}
      {mode === "places" && (
        <>
          <div className="reference-split">
            <div className="directory-column">
              <section
                aria-labelledby="geography-directory-title"
                className="identity-directory"
              >
                <h3 id="geography-directory-title">Geography directory</h3>
                {directory.status === "loading" && (
                  <p className="notice">Loading geography…</p>
                )}
                {directory.status === "error" && (
                  <div className="notice notice--error" role="alert">
                    <p>Florabase could not load the geography directory.</p>
                    <button
                      type="button"
                      onClick={() => {
                        setDirectory({ status: "loading" });
                        setAttempt((value) => value + 1);
                      }}
                    >
                      Retry directory
                    </button>
                  </div>
                )}
                {directory.status === "ready" &&
                  filter.trim() &&
                  matches.length === 0 && (
                    <p role="status">No geographic places match this filter.</p>
                  )}
                {directory.status === "ready" &&
                  (filter.trim() ? (
                    <ul className="identity-list">
                      {matches.map((place) => (
                        <li key={place.id}>
                          <PlaceButton
                            place={place}
                            selectedId={selectedId}
                            onSelect={selectPlace}
                            showPath
                          />
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <PlaceTree
                      places={places}
                      parentId={null}
                      selectedId={selectedId}
                      onSelect={selectPlace}
                      expanded={expanded}
                      onToggle={(id) => {
                        setExpanded((current) => {
                          const next = new Set(current);
                          if (next.has(id)) next.delete(id);
                          else next.add(id);
                          return next;
                        });
                      }}
                    />
                  ))}
              </section>
            </div>
            <QuickPreview>
              {selected ? (
                <article
                  aria-label="Geographic place preview"
                  className="geography-place-inspector"
                >
                  <DetailHeader
                    eyebrow={
                      selected.place_kind === "canonical"
                        ? "Canonical geographic place"
                        : "Local geographic place"
                    }
                    title={selected.name}
                    secondary={
                      <span className="record-path">
                        {selected.display_path}
                      </span>
                    }
                    status={
                      <span className="record-badges">
                        <span
                          className={`lifecycle-badge lifecycle-badge--${selected.retired_at ? "retired" : "active"}`}
                        >
                          {selected.retired_at
                            ? "Retired"
                            : selected.place_kind === "canonical"
                              ? "Canonical"
                              : "Local"}
                        </span>
                      </span>
                    }
                    primaryActions={
                      !selected.retired_at ? (
                        <button
                          type="button"
                          onClick={() => {
                            setCreateParentId(selected.id);
                            setSave({ status: "idle" });
                            if (creationExpanded)
                              createNameInput.current?.focus();
                            else openCreation();
                          }}
                        >
                          Create local child
                        </button>
                      ) : undefined
                    }
                    editLabel="Edit geographic place"
                    onEdit={
                      selected.place_kind === "custom"
                        ? () => {
                            setEditing(true);
                          }
                        : undefined
                    }
                    overflow={
                      selected.place_kind === "custom" ? (
                        <OverflowMenu ariaLabel="More geographic place actions">
                          <button
                            className="button--secondary"
                            type="button"
                            disabled={pending}
                            onClick={() =>
                              void apply(
                                () =>
                                  setGeographicPlaceRetired(
                                    selected.id,
                                    !selected.retired_at,
                                    csrfToken,
                                  ),
                                (place) =>
                                  place.retired_at
                                    ? `${place.display_path} was retired.`
                                    : `${place.display_path} was reactivated.`,
                              )
                            }
                          >
                            {selected.retired_at
                              ? "Reactivate local place"
                              : "Retire local place"}
                          </button>
                          <button
                            className="button--danger"
                            type="button"
                            disabled={pending}
                            onClick={() => {
                              setSave({ status: "saving" });
                              void deleteGeographicPlace(selected.id, csrfToken)
                                .then(async () => {
                                  const refreshed =
                                    await listGeographicPlaces();
                                  setDirectory({
                                    status: "ready",
                                    places: refreshed,
                                  });
                                  setSelectedId(null);
                                  setSave({
                                    status: "success",
                                    message:
                                      "The local geographic place was deleted.",
                                  });
                                })
                                .catch((error: unknown) => {
                                  if (
                                    error instanceof ApiError &&
                                    error.status === 401
                                  ) {
                                    auth.sessionExpired();
                                    return;
                                  }
                                  setSave({
                                    status: "error",
                                    message:
                                      error instanceof ApiError &&
                                      error.status === 409
                                        ? (geographyConflictMessage(error) ??
                                          "This place is still in use.")
                                        : "Florabase could not delete this geographic place.",
                                  });
                                });
                            }}
                          >
                            Delete local place
                          </button>
                        </OverflowMenu>
                      ) : undefined
                    }
                  />
                  <dl className="record-facts">
                    <div>
                      <dt>Type</dt>
                      <dd>
                        {placeTypeLabel(
                          selected.place_type,
                          selected.place_kind,
                        )}
                      </dd>
                    </div>
                    {selected.parent_id && (
                      <div>
                        <dt>Parent</dt>
                        <dd>
                          <button
                            type="button"
                            className="text-link"
                            onClick={() => {
                              if (selected.parent_id)
                                selectPlace(selected.parent_id);
                            }}
                          >
                            {places.find(
                              (place) => place.id === selected.parent_id,
                            )?.display_path ?? "Parent geographic place"}
                          </button>
                        </dd>
                      </div>
                    )}
                    {selected.source_code && selected.source_code_type && (
                      <div>
                        <dt>Reference code</dt>
                        <dd>
                          {selected.source_code_type}: {selected.source_code}
                        </dd>
                      </div>
                    )}
                    <div>
                      <dt>Child places</dt>
                      <dd>
                        {
                          places.filter(
                            (place) => place.parent_id === selected.id,
                          ).length
                        }
                      </dd>
                    </div>
                  </dl>
                  {selected.retired_at && (
                    <p className="record-empty">
                      Retired place; retained for historical provenance.
                    </p>
                  )}
                  <StatStrip
                    label="Direct place relationships"
                    items={[
                      {
                        label: "Collection references",
                        value: selected.direct_usage_count,
                      },
                      {
                        label: "Provenance sites",
                        value: selected.provenance_site_count,
                      },
                      {
                        label: "Native ranges",
                        value: selected.native_range_count,
                      },
                    ]}
                  />
                  {selected.place_kind === "canonical" && (
                    <p className="record-empty">
                      Canonical names and ancestry are read-only. Local places
                      can be added below.
                    </p>
                  )}
                  {editing && selected.place_kind === "custom" && (
                    <TaskDialog
                      title="Edit local place"
                      onClose={() => {
                        setEditing(false);
                      }}
                    >
                      <form
                        key={`${selected.id}-${selected.updated_at}`}
                        onSubmit={submitUpdate}
                      >
                        <h4>Edit local place</h4>
                        <div className="field">
                          <label htmlFor="edit-geographic-place-name">
                            Name
                          </label>
                          <input
                            id="edit-geographic-place-name"
                            name="name"
                            required
                            maxLength={255}
                            defaultValue={selected.name}
                            disabled={pending}
                          />
                        </div>
                        <div className="field">
                          <label htmlFor="edit-geographic-place-type">
                            Local place type
                          </label>
                          <select
                            id="edit-geographic-place-type"
                            name="place_type"
                            defaultValue={
                              selected.place_type ?? "other_named_area"
                            }
                            disabled={pending}
                          >
                            <option value="city_town">City or town</option>
                            <option value="locality">Locality</option>
                            <option value="other_named_area">
                              Other named area
                            </option>
                          </select>
                        </div>
                        <div className="field">
                          <label htmlFor="edit-geographic-place-parent">
                            Parent geographic place
                          </label>
                          <select
                            id="edit-geographic-place-parent"
                            name="parent_id"
                            required
                            defaultValue={selected.parent_id ?? ""}
                            disabled={pending}
                          >
                            {parentOptions.map((place) => (
                              <option value={place.id} key={place.id}>
                                {place.display_path}
                              </option>
                            ))}
                          </select>
                          <small>
                            This place and its descendants are excluded to
                            prevent cycles.
                          </small>
                        </div>
                        {save.status === "error" && (
                          <div
                            className="notice notice--error"
                            role="alert"
                            ref={feedback}
                            tabIndex={-1}
                          >
                            {save.message}
                          </div>
                        )}
                        <div className="actions">
                          <button type="submit" disabled={pending}>
                            Save local place
                          </button>
                          <button
                            className="button--secondary"
                            type="button"
                            disabled={pending}
                            onClick={() => {
                              setEditing(false);
                            }}
                          >
                            Cancel
                          </button>
                        </div>
                      </form>
                    </TaskDialog>
                  )}
                </article>
              ) : (
                <div className="empty-state">
                  <h3>Select a geographic place</h3>
                  <p>
                    Choose any known level—from a broad region to a local place.
                  </p>
                </div>
              )}
            </QuickPreview>
          </div>
          {creationExpanded && (
            <TaskDialog
              title="New local place"
              onClose={() => {
                closeCreation({ returnFocus: false });
              }}
            >
              <div ref={creationPanelRef}>
                <form
                  className="identity-form"
                  aria-busy={pending}
                  onSubmit={submitCreate}
                >
                  <h3>Create a local place</h3>
                  <p>
                    Local places extend CLDR reference geography and have no
                    fabricated standard code.
                  </p>
                  <div className="field">
                    <label htmlFor="new-geographic-place-name">Name</label>
                    <input
                      id="new-geographic-place-name"
                      required
                      maxLength={255}
                      disabled={pending}
                      ref={createNameInput}
                      value={createName}
                      onChange={(event) => {
                        setCreateName(event.currentTarget.value);
                      }}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="new-geographic-place-type">
                      Local place type
                    </label>
                    <select
                      id="new-geographic-place-type"
                      value={createType}
                      disabled={pending}
                      onChange={(event) => {
                        setCreateType(
                          event.currentTarget.value as typeof createType,
                        );
                      }}
                    >
                      <option value="city_town">City or town</option>
                      <option value="locality">Locality</option>
                      <option value="other_named_area">Other named area</option>
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="new-geographic-place-parent">
                      Parent geographic place
                    </label>
                    <select
                      id="new-geographic-place-parent"
                      required
                      disabled={pending}
                      value={createParentId}
                      onChange={(event) => {
                        setCreateParentId(event.currentTarget.value);
                      }}
                    >
                      <option value="">Choose a parent</option>
                      {places
                        .filter((place) => !place.retired_at)
                        .map((place) => (
                          <option value={place.id} key={place.id}>
                            {place.display_path}
                          </option>
                        ))}
                    </select>
                  </div>
                  {save.status === "error" && (
                    <div
                      className="notice notice--error"
                      role="alert"
                      ref={feedback}
                      tabIndex={-1}
                    >
                      {save.message}
                    </div>
                  )}
                  <div className="actions">
                    <button type="submit" disabled={pending || !createParentId}>
                      {pending ? "Saving local place…" : "Create local place"}
                    </button>
                    <button
                      type="button"
                      className="button--secondary"
                      disabled={pending}
                      onClick={() => {
                        setCreateName("");
                        setCreateParentId("");
                        setSave({ status: "idle" });
                        closeCreation({ returnFocus: false });
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              </div>
            </TaskDialog>
          )}
          <div aria-live="polite">
            {save.status === "saving" && (
              <p className="notice">Saving the geographic place…</p>
            )}
            {save.status === "success" && (
              <p className="notice notice--success">{save.message}</p>
            )}
            {!creationExpanded && !editing && save.status === "error" && (
              <div
                className="notice notice--error"
                role="alert"
                ref={feedback}
                tabIndex={-1}
              >
                {save.message}
              </div>
            )}
          </div>
        </>
      )}
      {directory.status === "ready" && mode !== "places" && (
        <ProvenanceSiteManager
          places={places}
          csrfToken={csrfToken}
          initialSiteId={initialSiteId}
          mode={mode === "map" ? "map" : "browse"}
          query={filter}
          onPlaceSelect={(id) => {
            setSelectedId(id);
            setMode("places");
          }}
        />
      )}
    </section>
  );
}
