import { HierarchyRow } from "../components/HierarchyRow";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type SyntheticEvent,
} from "react";
import { ActionButton, ActionLink } from "../components/Action";
import { LifecycleStatus } from "../components/WorkspaceUI";
import { DirectoryResults } from "../components/DirectoryResults";
import { DirectoryTools } from "../components/DirectoryTools";
import { FieldLabel } from "../components/FieldLabel";
import "../components/hierarchy.css";
import { Icon } from "../components/Icon";
import { GeographyHeader } from "../geography/GeographyHeader";
import { SavedViews } from "../saved-views/SavedViews";
import { useDirectoryView } from "../saved-views/useDirectoryView";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import {
  Breadcrumbs,
  DetailHeader,
  DetailLoading,
  DetailPage,
  DetailSummary,
} from "../components/CollectionUI";
import { DirectorySearch, OverflowMenu } from "../components/ReferenceUI";
import { TaskDialog } from "../components/TaskDialog";
import { useCreationDisclosure } from "../components/useCreationDisclosure";
import { ProvenanceSiteManager } from "../provenance-sites/ProvenanceSiteManager";
import {
  createGeographicPlace,
  deleteGeographicPlace,
  geographyConflictMessage,
  geographyValidationMessages,
  listGeographicPlaces,
  setGeographicPlaceRetired,
  updateGeographicPlace,
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
    <HierarchyRow selected={selectedId === place.id}>
      <button
        type="button"
        className="identity-list-item geography-directory-row ui-hierarchy-record"
        aria-pressed={selectedId === place.id}
        onClick={() => {
          onSelect(place.id);
        }}
      >
        <span className="geography-row-title">
          <strong>{place.name}</strong>
          <span className="record-state">
            {place.place_kind === "canonical" ? "Canonical" : "Local"}
          </span>
          <LifecycleStatus state={place.retired_at ? "retired" : "active"} />
        </span>
        <small>
          {showPath
            ? place.display_path
            : place.source_code
              ? `${place.source_code_type ?? "Reference"}: ${place.source_code}`
              : placeTypeLabel(place.place_type, place.place_kind)}
        </small>
      </button>
      <div className="ui-hierarchy-record-actions">
        <ActionLink
          className="ui-directory-quick-action"
          icon="document"
          title="Open details"
          aria-label={`Open details ${place.name}`}
          href={`#/geography/places?place=${place.id}`}
        >
          <span className="sr-only">Open details</span>
        </ActionLink>
        {place.place_kind === "custom" && (
          <ActionLink
            className="ui-directory-quick-action"
            icon="edit"
            title="Edit"
            aria-label={`Edit ${place.name}`}
            href={`#/geography/places?place=${place.id}&tab=edit`}
          >
            <span className="sr-only">Edit</span>
          </ActionLink>
        )}
      </div>
    </HierarchyRow>
  );
}

function PlaceTree({
  places,
  parentId,
  selectedId,
  onSelect,
  expanded,
  onToggle,
  depth = 0,
}: {
  places: GeographicPlaceResponse[];
  parentId: string | null;
  selectedId: string | null;
  onSelect: (id: string) => void;
  expanded: Set<string>;
  onToggle: (id: string) => void;
  depth?: number;
}) {
  const children = places.filter((place) => place.parent_id === parentId);
  if (children.length === 0) return null;
  return (
    <ul
      tabIndex={parentId ? undefined : 0}
      className={
        parentId
          ? `location-tree location-tree--nested${depth >= 3 ? " location-tree--compact-depth" : ""}`
          : "location-tree"
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
                  <Icon name="chevron-down" />
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
                depth={depth + 1}
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

export function GeographyScreen({
  initialSiteId,
  initialPlaceId,
  startCreating = false,
}: {
  initialSiteId?: string;
  initialPlaceId?: string;
  startCreating?: boolean;
}) {
  const auth = useAuth();
  const [directory, setDirectory] = useState<DirectoryState>({
    status: "loading",
  });
  const [attempt, setAttempt] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(
    initialPlaceId ?? null,
  );
  // Keep URL listeners mounted while App handles the same hash navigation.
  const clearSelection = useCallback(() => {
    setSelectedId(null);
  }, []);
  const initialView = useMemo(
    () => ({ mode: initialSiteId ? ("sites" as const) : ("places" as const) }),
    [initialSiteId],
  );
  const view = useDirectoryView("geography", clearSelection, initialView);
  const filter = view.state.q;
  const setFilter = (value: string) => {
    view.update("q", value);
  };
  const mode = view.state.mode;
  const updateView = view.update;
  const setMode = useCallback(
    (value: "places" | "sites" | "map") => {
      updateView("mode", value);
    },
    [updateView],
  );

  const [createName, setCreateName] = useState("");
  const [createParentId, setCreateParentId] = useState("");
  const [createType, setCreateType] = useState<
    "city_town" | "locality" | "other_named_area"
  >("other_named_area");
  const [save, setSave] = useState<SaveState>({ status: "idle" });
  const [editing, setEditing] = useState(
    Boolean(initialPlaceId) &&
      new URLSearchParams(window.location.hash.split("?", 2)[1] ?? "").get(
        "tab",
      ) === "edit",
  );
  const [siteCreating, setSiteCreating] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const initialExpansionApplied = useRef(false);
  const createNameInput = useRef<HTMLInputElement>(null);
  const createInitialParent = useRef("");
  const feedback = useRef<HTMLDivElement>(null);
  const {
    expanded: creationExpanded,
    triggerRef: creationTriggerRef,
    panelRef: creationPanelRef,
    open: openCreation,
    close: closeCreation,
  } = useCreationDisclosure();
  const dashboardCreationStarted = useRef(false);
  useEffect(() => {
    if (
      !startCreating ||
      directory.status !== "ready" ||
      dashboardCreationStarted.current
    )
      return;
    dashboardCreationStarted.current = true;
    setMode("places");
    createInitialParent.current = "";
    setCreateType("other_named_area");
    setCreateName("");
    setCreateParentId("");
    setSave({ status: "idle" });
    openCreation();
  }, [directory.status, openCreation, setMode, startCreating]);
  const pending = save.status === "saving";

  useEffect(() => {
    const controller = new AbortController();
    void listGeographicPlaces(controller.signal)
      .then((places) => {
        setDirectory({ status: "ready", places });
        if (!initialExpansionApplied.current) {
          initialExpansionApplied.current = true;
          const initial = new Set(
            places
              .filter(
                (place) =>
                  place.place_kind === "canonical" &&
                  place.source_code === "001" &&
                  place.parent_id === null,
              )
              .map((place) => place.id),
          );
          const byId = new Map(places.map((place) => [place.id, place]));
          let parent = initialPlaceId
            ? byId.get(initialPlaceId)?.parent_id
            : null;
          while (parent) {
            initial.add(parent);
            parent = byId.get(parent)?.parent_id ?? null;
          }
          setExpanded(initial);
        }
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
  }, [auth, attempt, initialPlaceId]);

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
    window.location.hash = `#/geography/places?place=${id}`;
    setExpanded((current) => {
      const next = new Set(current);
      const byId = new Map(places.map((place) => [place.id, place]));
      let parent = byId.get(id)?.parent_id;
      while (parent) {
        next.add(parent);
        parent = byId.get(parent)?.parent_id;
      }
      return next;
    });
    setEditing(false);
    setSave({ status: "idle" });
  }

  function beginCreate(parentId = "") {
    createInitialParent.current = parentId;
    setCreateName("");
    setCreateParentId(parentId);
    setCreateType("other_named_area");
    setSave({ status: "idle" });
    openCreation();
  }

  function dismissCreate() {
    if (pending) return;
    const dirty =
      createName !== "" ||
      createParentId !== createInitialParent.current ||
      createType !== "other_named_area";
    if (dirty && !window.confirm("Discard unsaved local place changes?"))
      return;
    setCreateName("");
    setCreateParentId("");
    setCreateType("other_named_area");
    setSave({ status: "idle" });
    closeCreation({ returnFocus: false });
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
        window.location.hash = `#/geography/places?place=${place.id}`;
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
    <section
      aria-labelledby={
        mode === "places" ? "geography-places-title" : "geography-sites-title"
      }
      className="workspace geography-workspace ui-hierarchy-workspace"
    >
      {initialPlaceId ? (
        <h2 className="sr-only" id="geography-places-title">
          Geographic place
        </h2>
      ) : (
        <GeographyHeader
          view={mode === "places" ? "places" : "sites"}
          description={
            mode === "places"
              ? "Manage hierarchical geographic places, canonical and local."
              : "Manage precise collection-origin sites and their recorded coordinates."
          }
          actions={
            initialSiteId || initialPlaceId ? (
              mode === "places" ? (
                <ActionButton
                  icon="add"
                  type="button"
                  ref={creationTriggerRef}
                  aria-haspopup="dialog"
                  onClick={() => {
                    beginCreate();
                  }}
                >
                  New local place
                </ActionButton>
              ) : (
                <ActionButton
                  icon="add"
                  type="button"
                  onClick={() => {
                    setSiteCreating(true);
                  }}
                >
                  New provenance site
                </ActionButton>
              )
            ) : undefined
          }
          tools={
            !initialSiteId &&
            !initialPlaceId && (
              <DirectoryTools
                name="Geography"
                search={
                  <DirectorySearch
                    hideLabel={!initialSiteId && !initialPlaceId}
                    id="geography-filter"
                    label={
                      mode === "places"
                        ? "Search places"
                        : "Search provenance sites"
                    }
                    placeholder={
                      mode === "places" ? "Place or path" : "Provenance site"
                    }
                    value={filter}
                    onChange={setFilter}
                    className="geography-search"
                  />
                }
                savedViews={
                  <SavedViews
                    presentation="dialog"
                    surface="geography"
                    state={view.savedState}
                  />
                }
                actions={
                  mode === "places" ? (
                    <ActionButton
                      icon="add"
                      type="button"
                      ref={creationTriggerRef}
                      aria-haspopup="dialog"
                      onClick={() => {
                        beginCreate();
                      }}
                    >
                      New local place
                    </ActionButton>
                  ) : (
                    <ActionButton
                      icon="add"
                      type="button"
                      onClick={() => {
                        setSiteCreating(true);
                      }}
                    >
                      New provenance site
                    </ActionButton>
                  )
                }
              />
            )
          }
        />
      )}

      {Boolean(initialSiteId) && (
        <DirectorySearch
          hideLabel={!initialSiteId && !initialPlaceId}
          id="geography-filter"
          label={
            mode === "places" ? "Search places" : "Search provenance sites"
          }
          placeholder={mode === "places" ? "Place or path" : "Provenance site"}
          value={filter}
          onChange={setFilter}
          className="geography-search"
        />
      )}
      {mode !== "places" && (
        <div
          className="geography-site-modes"
          role="group"
          aria-label="Provenance site view"
        >
          <button
            type="button"
            className="button--secondary"
            aria-pressed={mode === "sites"}
            onClick={() => {
              setMode("sites");
            }}
          >
            List
          </button>
          <button
            type="button"
            className="button--secondary"
            aria-pressed={mode === "map"}
            onClick={() => {
              setMode("map");
            }}
          >
            Site map
          </button>
        </div>
      )}
      {mode === "places" && (
        <>
          <div className="reference-split">
            {!initialPlaceId && (
              <div className="directory-column">
                <section
                  aria-labelledby="geography-directory-title"
                  className="identity-directory"
                >
                  <h3 className="sr-only" id="geography-directory-title">
                    Geography directory
                  </h3>
                  {directory.status === "ready" && !initialPlaceId && (
                    <DirectoryResults count={matches.length} />
                  )}
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
                  {directory.status === "ready" && places.length === 0 && (
                    <p className="empty-state">
                      No geographic places available. Canonical places must be
                      initialized before adding local children.
                    </p>
                  )}
                  {directory.status === "ready" &&
                    filter.trim() &&
                    matches.length === 0 && (
                      <p role="status">
                        No geographic places match this filter.
                      </p>
                    )}
                  {directory.status === "ready" &&
                    (filter.trim() ? (
                      <ul
                        className="identity-list"
                        aria-label="Matching places"
                        tabIndex={0}
                      >
                        {matches.map((place) => (
                          <li key={place.id} className="ui-hierarchy-match">
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
            )}
            {initialPlaceId && (
              <DetailPage as="section" aria-label="Geographic place detail">
                <ActionLink
                  icon="back"
                  href={`#/geography/places${filter ? `?q=${encodeURIComponent(filter)}` : ""}`}
                >
                  Back to places
                </ActionLink>
                {selected ? (
                  <>
                    <Breadcrumbs
                      items={[
                        { label: "Geography", href: "#/geography" },
                        {
                          label: "Places",
                          href: `#/geography/places${filter ? `?q=${encodeURIComponent(filter)}` : ""}`,
                        },
                        { label: selected.name },
                      ]}
                    />
                    <article
                      aria-label="Geographic place record"
                      className="geography-place-inspector"
                    >
                      <DetailHeader
                        eyebrow="Geographic place"
                        title={selected.name}
                        secondary={
                          <span className="record-path">
                            {selected.display_path}
                          </span>
                        }
                        status={
                          <span className="record-badges">
                            <LifecycleStatus
                              state={selected.retired_at ? "retired" : "active"}
                            />
                            <span className="record-state">
                              {selected.place_kind === "canonical"
                                ? "Canonical"
                                : "Local"}
                            </span>
                          </span>
                        }
                        secondaryActions={
                          <ActionButton
                            icon="add"
                            ref={creationTriggerRef}
                            aria-haspopup="dialog"
                            onClick={() => {
                              beginCreate();
                            }}
                          >
                            New local place
                          </ActionButton>
                        }
                        primaryActions={
                          !selected.retired_at ? (
                            <button
                              type="button"
                              onClick={() => {
                                beginCreate(selected.id);
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
                                  void deleteGeographicPlace(
                                    selected.id,
                                    csrfToken,
                                  )
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
                                            ? (geographyConflictMessage(
                                                error,
                                              ) ??
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
                      <div className="actions record-preview__actions">
                        {!initialPlaceId && (
                          <a
                            className="button-link button--secondary"
                            href={`#/geography?place=${selected.id}`}
                          >
                            Open details
                          </a>
                        )}
                        <a href={`#/geography?mode=sites&place=${selected.id}`}>
                          Associated provenance sites (
                          {selected.provenance_site_count})
                        </a>
                      </div>
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
                                )?.name ?? "Parent geographic place"}
                              </button>
                            </dd>
                          </div>
                        )}
                        {selected.source_code && selected.source_code_type && (
                          <div>
                            <dt>Reference code</dt>
                            <dd>
                              {selected.source_code_type}:{" "}
                              {selected.source_code}
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
                      <DetailSummary
                        id="place-summary-title"
                        label="Direct place relationships"
                        metrics={[
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
                          Canonical names and ancestry are read-only. Local
                          places can be added below.
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
                              <FieldLabel
                                required
                                htmlFor="edit-geographic-place-name"
                              >
                                Name
                              </FieldLabel>
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
                              <FieldLabel
                                required
                                htmlFor="edit-geographic-place-parent"
                              >
                                Parent geographic place
                              </FieldLabel>
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
                  </>
                ) : directory.status === "loading" ? (
                  <DetailLoading
                    eyebrow="Geographic place"
                    label="Loading geographic place…"
                    parents={[
                      { label: "Geography", href: "#/geography" },
                      { label: "Places", href: "#/geography/places" },
                    ]}
                    visual={false}
                  />
                ) : (
                  <div className="empty-state">
                    {directory.status === "error" ? (
                      <div role="alert">
                        <h3>Could not load geographic place</h3>
                        <button
                          type="button"
                          onClick={() => {
                            setDirectory({ status: "loading" });
                            setAttempt((value) => value + 1);
                          }}
                        >
                          Retry place
                        </button>
                      </div>
                    ) : (
                      <h3>Geographic place not found</h3>
                    )}
                  </div>
                )}
              </DetailPage>
            )}
          </div>
          {creationExpanded && (
            <TaskDialog
              title="New local place"
              dismissOnBackdrop
              onClose={dismissCreate}
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
                    <FieldLabel required htmlFor="new-geographic-place-name">
                      Name
                    </FieldLabel>
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
                    <FieldLabel required htmlFor="new-geographic-place-parent">
                      Parent geographic place
                    </FieldLabel>
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
                      onClick={dismissCreate}
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
      {mode !== "places" && directory.status !== "ready" && (
        <div
          className={
            directory.status === "error" ? "notice notice--error" : "notice"
          }
          role={directory.status === "error" ? "alert" : "status"}
        >
          <p>
            {directory.status === "loading"
              ? "Loading geography…"
              : "Florabase could not load geographic places for the site directory."}
          </p>
          {directory.status === "error" && (
            <button
              type="button"
              onClick={() => {
                setDirectory({ status: "loading" });
                setAttempt((value) => value + 1);
              }}
            >
              Retry directory
            </button>
          )}
        </div>
      )}
      {directory.status === "ready" && mode !== "places" && (
        <ProvenanceSiteManager
          startCreating={siteCreating}
          onCreationStarted={() => {
            setSiteCreating(false);
          }}
          showCreateAction={false}
          places={places}
          csrfToken={csrfToken}
          initialSiteId={initialSiteId}
          placeId={initialPlaceId}
          mode={mode === "map" ? "map" : "browse"}
          query={filter}
          onPlaceSelect={(id) => {
            window.location.hash = `#/geography/places?place=${id}`;
          }}
        />
      )}
    </section>
  );
}
