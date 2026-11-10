import { HierarchyRow } from "../components/HierarchyRow";
import {
  useEffect,
  useId,
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
import "../harvests/collection-visual.css";
import { SavedViews } from "../saved-views/SavedViews";
import { useDirectoryView } from "../saved-views/useDirectoryView";
import { ReferencePicker } from "../seed-lots/ReferencePicker";
import "./hierarchy.css";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import {
  Breadcrumbs,
  DetailHeader,
  DetailPage,
  DetailLoading,
  SpecimenLabel,
} from "../components/CollectionUI";
import {
  DirectorySearch,
  OverflowMenu,
  PageHeader,
} from "../components/ReferenceUI";
import { TaskDialog } from "../components/TaskDialog";
import { useCreationDisclosure } from "../components/useCreationDisclosure";
import {
  createLocation,
  deleteLocation,
  listLocations,
  locationConflictMessage,
  locationValidationMessages,
  setLocationRetired,
  updateLocation,
  type LocationCreate,
  type LocationResponse,
  type LocationUpdate,
  type LocationUsageScope,
} from "./api";

type DirectoryState =
  | { status: "loading" }
  | { status: "ready"; locations: LocationResponse[] }
  | { status: "error" };
type SaveState =
  | { status: "idle" }
  | { status: "saving" }
  | { status: "success"; message: string }
  | { status: "validation"; messages: string[] }
  | { status: "error"; message: string };

function payloadFrom(form: HTMLFormElement): LocationCreate {
  const data = new FormData(form);
  const name = data.get("name");
  const parentId = data.get("parent_id");
  const usageScopes = data
    .getAll("usage_scopes")
    .filter(
      (value): value is LocationUsageScope =>
        value === "plants" ||
        value === "sowings" ||
        value === "seed_lots" ||
        value === "harvest_inventory" ||
        value === "vegetative_lots" ||
        value === "propagation_attempts",
    );
  return {
    name: typeof name === "string" ? name : "",
    parent_id: typeof parentId === "string" && parentId ? parentId : undefined,
    usage_scopes: usageScopes,
  };
}

const scopeLabels: Record<LocationUsageScope, string> = {
  plants: "Plants",
  sowings: "Sowings",
  seed_lots: "Seed lots",
  harvest_inventory: "Stored material",
  vegetative_lots: "Vegetative lots",
  propagation_attempts: "Rooting attempts",
};

const allScopes: LocationUsageScope[] = [
  "plants",
  "sowings",
  "seed_lots",
  "harvest_inventory",
  "vegetative_lots",
  "propagation_attempts",
];

const recordKinds = [
  "plants",
  "plant_groups",
  "sowings",
  "seed_lots",
  "harvest_inventory",
  "vegetative_lots",
  "propagation_attempts",
] as const;
const recordLabels = {
  plants: "Plants",
  plant_groups: "Plant groups",
  sowings: "Sowings",
  seed_lots: "Seed lots",
  harvest_inventory: "Stored material",
  vegetative_lots: "Vegetative lots",
  propagation_attempts: "Rooting attempts",
};

function CompactUsage({
  location,
  comparison = false,
}: {
  location: LocationResponse;
  comparison?: boolean;
}) {
  const occupied = recordKinds.filter(
    (kind) => (location.usage_including_descendants[kind]?.total ?? 0) > 0,
  );
  return (
    <span className="location-compact-usage">
      {occupied.length === 0 ? (
        <small>No collection records</small>
      ) : (
        occupied.map((kind) => {
          const direct = location.direct_usage[kind]?.total ?? 0;
          const inclusive =
            location.usage_including_descendants[kind]?.total ?? 0;
          return (
            <span
              key={kind}
              aria-label={`${recordLabels[kind]}: ${String(inclusive)} including sublocations, ${String(direct)} directly here`}
            >
              {recordLabels[kind]} <strong>{inclusive}</strong>
              {inclusive !== direct && " incl."}
              {comparison && <small> · {direct} directly here</small>}
            </span>
          );
        })
      )}
    </span>
  );
}

function CollectionUsage({ location }: { location: LocationResponse }) {
  return (
    <section className="record-section" aria-labelledby="location-usage-title">
      <h4 id="location-usage-title">Collection usage</h4>
      <p className="field-help">
        Record counts. Totals include retained historical records; active counts
        are shown in parentheses.
      </p>
      <table className="location-usage-table">
        <thead>
          <tr>
            <th scope="col">Record type</th>
            <th scope="col">Directly here</th>
            <th scope="col">Including sublocations</th>
          </tr>
        </thead>
        <tbody>
          {recordKinds.map((kind) => (
            <tr key={kind}>
              <th scope="row">{recordLabels[kind]}</th>
              {[
                location.direct_usage,
                location.usage_including_descendants,
              ].map((usage, index) => (
                <td key={index}>
                  {usage[kind]?.total ?? 0} total ({usage[kind]?.active ?? 0}{" "}
                  active)
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="field-help">
        Including sublocations counts this location and every location beneath
        it.
      </p>
      <div className="actions">
        <a href="#/plants">Browse plants and groups</a>
        <a href="#/sowings">Browse sowings</a>
        <a href="#/seeds">Browse seed lots</a>
        <a href="#/harvests?tab=stored-material">Browse stored material</a>
      </div>
    </section>
  );
}

function scopesOf(location: LocationResponse): LocationUsageScope[] {
  return location.usage_scopes;
}

function ScopeFields({
  selected,
  disabled,
}: {
  selected?: LocationResponse;
  disabled: boolean;
}) {
  const selectedScopes = selected ? scopesOf(selected) : allScopes;
  const helpId = useId();
  return (
    <fieldset
      className="scope-fields"
      disabled={disabled}
      aria-describedby={helpId}
    >
      <FieldLabel as="legend" required>
        Used for
      </FieldLabel>
      <p className="field-help" id={helpId}>
        Choose at least one. Scopes are explicit and do not inherit.
      </p>
      {allScopes.map((scope) => (
        <label key={scope}>
          <input
            type="checkbox"
            name="usage_scopes"
            value={scope}
            defaultChecked={selectedScopes.includes(scope)}
          />{" "}
          {scopeLabels[scope]}
        </label>
      ))}
    </fieldset>
  );
}

function descendantsOf(id: string, locations: LocationResponse[]): Set<string> {
  const descendants = new Set<string>();
  let changed = true;
  while (changed) {
    changed = false;
    for (const location of locations) {
      if (
        location.parent_id &&
        (location.parent_id === id || descendants.has(location.parent_id)) &&
        !descendants.has(location.id)
      ) {
        descendants.add(location.id);
        changed = true;
      }
    }
  }
  return descendants;
}

function ParentField({
  id,
  locations,
  selected,
  value,
  disabled,
  onChange,
}: {
  id: string;
  locations: LocationResponse[];
  selected?: LocationResponse;
  value?: string;
  disabled: boolean;
  onChange?: (value: string) => void;
}) {
  const [parentValue, setParentValue] = useState(selected?.parent_id ?? "root");
  const excluded = selected
    ? new Set([selected.id, ...descendantsOf(selected.id, locations)])
    : new Set<string>();
  const candidates = locations.filter(
    (location) =>
      !excluded.has(location.id) &&
      (selected?.retired_at ? true : !location.retired_at),
  );
  if (selected)
    return (
      <div className="location-parent-field">
        <input
          type="hidden"
          name="parent_id"
          value={parentValue === "root" ? "" : parentValue}
        />
        <input type="hidden" name="parent_choice" value={parentValue} />
        <ReferencePicker
          label="Parent location"
          choices={[
            { id: "root", label: "No parent (root location)" },
            ...candidates.map((location) => ({
              id: location.id,
              label: `${location.display_path}${location.retired_at ? " (retired)" : ""}`,
            })),
          ]}
          value={parentValue}
          onChange={setParentValue}
          disabled={disabled}
          help="This location and its descendants are excluded to prevent cycles."
        />
      </div>
    );
  return (
    <div className="field">
      <label htmlFor={id}>Parent location</label>
      <select
        id={id}
        name="parent_id"
        disabled={disabled}
        value={value}
        defaultValue={onChange ? undefined : ""}
        onChange={
          onChange
            ? (event) => {
                onChange(event.currentTarget.value);
              }
            : undefined
        }
      >
        <option value="">No parent (root location)</option>
        {candidates.map((location) => (
          <option value={location.id} key={location.id}>
            {location.display_path}
            {location.retired_at ? " (retired)" : ""}
          </option>
        ))}
      </select>
    </div>
  );
}

function LocationTree({
  locations,
  parentId,
  selectedId,
  onSelect,
  expanded,
  onToggle,
  depth = 0,
}: {
  locations: LocationResponse[];
  parentId: string | null;
  selectedId: string | null;
  onSelect: (id: string) => void;
  expanded: Set<string>;
  onToggle: (id: string) => void;
  depth?: number;
}) {
  const children = locations.filter(
    (location) => location.parent_id === parentId,
  );
  if (children.length === 0) return null;
  return (
    <ul
      tabIndex={parentId ? undefined : 0}
      aria-label={parentId ? undefined : "Location hierarchy"}
      className={
        !parentId
          ? "location-tree"
          : `location-tree location-tree--nested${depth >= 3 ? " location-tree--compact-depth" : ""}`
      }
    >
      {children.map((location) => {
        const hasChildren = locations.some(
          (item) => item.parent_id === location.id,
        );
        const isExpanded = expanded.has(location.id);
        return (
          <li key={location.id}>
            <div className="location-tree-node">
              {hasChildren ? (
                <button
                  type="button"
                  className="location-tree-toggle"
                  aria-label={`${isExpanded ? "Collapse" : "Expand"} ${location.name}`}
                  aria-expanded={isExpanded}
                  onClick={() => {
                    onToggle(location.id);
                  }}
                >
                  <Icon name="chevron-down" />
                </button>
              ) : (
                <span className="location-tree-spacer" aria-hidden="true" />
              )}
              <HierarchyRow selected={selectedId === location.id}>
                <button
                  type="button"
                  className="identity-list-item location-directory-row ui-hierarchy-record"
                  title={location.display_path}
                  aria-pressed={selectedId === location.id}
                  onClick={() => {
                    onSelect(location.id);
                  }}
                >
                  <span>
                    <strong className="location-record-name">
                      {location.name}
                    </strong>
                    <LifecycleStatus
                      state={location.retired_at ? "retired" : "active"}
                    />
                  </span>
                  {depth >= 3 && (
                    <small
                      className="location-path"
                      title={location.display_path}
                    >
                      Within{" "}
                      {
                        locations.find((item) => item.id === location.parent_id)
                          ?.name
                      }
                    </small>
                  )}
                  <CompactUsage location={location} />
                </button>
                <div className="ui-hierarchy-record-actions">
                  <ActionLink
                    className="ui-directory-quick-action"
                    icon="document"
                    title="Open details"
                    aria-label={`Open details ${location.name}`}
                    href={`#/locations/${location.id}`}
                  >
                    <span className="sr-only">Open details</span>
                  </ActionLink>
                  <ActionLink
                    className="ui-directory-quick-action"
                    icon="edit"
                    title="Edit"
                    aria-label={`Edit ${location.name}`}
                    href={`#/locations/${location.id}?tab=edit`}
                  >
                    <span className="sr-only">Edit</span>
                  </ActionLink>
                </div>
              </HierarchyRow>
            </div>
            {hasChildren && isExpanded && (
              <LocationTree
                locations={locations}
                parentId={location.id}
                selectedId={selectedId}
                onSelect={onSelect}
                expanded={expanded}
                onToggle={onToggle}
                depth={depth + 1}
              />
            )}
          </li>
        );
      })}
    </ul>
  );
}

export function LocationScreen({
  initialId,
  startCreating = false,
}: { initialId?: string; startCreating?: boolean } = {}) {
  const auth = useAuth();
  const [directory, setDirectory] = useState<DirectoryState>({
    status: "loading",
  });
  const [selectedId, setSelectedId] = useState<string | null>(
    initialId ?? null,
  );
  const [createNameValue, setCreateNameValue] = useState("");
  const [createParentId, setCreateParentId] = useState("");
  const [save, setSave] = useState<SaveState>({ status: "idle" });
  const [attempt, setAttempt] = useState(0);
  const [editing, setEditing] = useState(
    Boolean(initialId) &&
      new URLSearchParams(window.location.hash.split("?", 2)[1] ?? "").get(
        "tab",
      ) === "edit",
  );
  const view = useDirectoryView("locations", () => {
    setSelectedId(null);
  });
  const query = view.state.q;
  const setQuery = (value: string) => {
    view.update("q", value);
  };
  const stateFilter = view.state.state;
  const scopeFilter = view.state.scope;
  const setScopeFilter = (value: LocationUsageScope | "all") => {
    view.update("scope", value);
  };

  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [filterExpansion, setFilterExpansion] = useState<{
    key: string;
    overrides: Map<string, boolean>;
  }>({ key: "", overrides: new Map() });
  const createName = useRef<HTMLInputElement>(null);
  const editForm = useRef<HTMLFormElement>(null);
  const createForm = useRef<HTMLFormElement>(null);
  const createBaseline = useRef("");
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
    setCreateNameValue("");
    setCreateParentId("");
    setSave({ status: "idle" });
    openCreation();
  }, [directory.status, openCreation, startCreating]);
  const pending = save.status === "saving";
  useEffect(() => {
    if (creationExpanded && createForm.current)
      createBaseline.current = JSON.stringify(payloadFrom(createForm.current));
  }, [creationExpanded]);
  function dismissCreate() {
    if (pending) return;
    if (
      createForm.current &&
      JSON.stringify(payloadFrom(createForm.current)) !==
        createBaseline.current &&
      !window.confirm("Discard unsaved Location changes?")
    )
      return;
    setCreateNameValue("");
    setCreateParentId("");
    setSave({ status: "idle" });
    closeCreation({ returnFocus: false });
  }

  useEffect(() => {
    const controller = new AbortController();
    void listLocations(controller.signal)
      .then((locations) => {
        setDirectory({ status: "ready", locations });
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
    if (save.status === "validation" || save.status === "error")
      feedback.current?.focus();
  }, [save]);

  const locations = useMemo(
    () => (directory.status === "ready" ? directory.locations : []),
    [directory],
  );
  const search = query.trim().toLocaleLowerCase();
  const matching = locations.filter(
    (location) =>
      (stateFilter === "all" ||
        Boolean(location.retired_at) === (stateFilter === "retired")) &&
      (scopeFilter === "all" || location.usage_scopes.includes(scopeFilter)) &&
      (!search ||
        location.name.toLocaleLowerCase().includes(search) ||
        location.display_path.toLocaleLowerCase().includes(search)),
  );
  const hierarchyFilter = Boolean(search || scopeFilter !== "all");
  const filterActive = hierarchyFilter || stateFilter !== "all";
  const autoExpandMatches = hierarchyFilter || stateFilter === "retired";
  const filterKey = `${stateFilter}:${scopeFilter}:${search}`;
  const byId = new Map(locations.map((location) => [location.id, location]));
  const visibleIds = new Set(matching.map((location) => location.id));
  const revealedAncestors = new Set<string>();
  if (filterActive) {
    for (const match of matching) {
      let parentId = match.parent_id;
      while (parentId) {
        visibleIds.add(parentId);
        revealedAncestors.add(parentId);
        parentId = byId.get(parentId)?.parent_id ?? null;
      }
    }
  }
  const shownLocations = filterActive
    ? locations.filter((location) => visibleIds.has(location.id))
    : locations;
  const selected =
    locations.find(
      ({ id }) =>
        id === selectedId && (Boolean(initialId) || visibleIds.has(id)),
    ) ?? null;
  const effectiveExpanded = autoExpandMatches
    ? new Set(revealedAncestors)
    : expanded;
  if (autoExpandMatches && filterExpansion.key === filterKey) {
    for (const [id, isOpen] of filterExpansion.overrides) {
      if (isOpen) effectiveExpanded.add(id);
      else effectiveExpanded.delete(id);
    }
  }

  if (
    auth.state.status !== "authenticated" &&
    auth.state.status !== "logging-out" &&
    auth.state.status !== "logout-failed"
  )
    return null;
  const csrfToken = auth.state.csrfToken;

  async function apply(
    action: () => Promise<LocationResponse>,
    success: (location: LocationResponse) => string,
  ) {
    setSave({ status: "saving" });
    try {
      const location = await action();
      const refreshed = await listLocations();
      setDirectory({ status: "ready", locations: refreshed });
      setSelectedId(location.id);
      setEditing(false);
      setSave({ status: "success", message: success(location) });
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else if (error instanceof ApiError && error.status === 422)
        setSave({
          status: "validation",
          messages: locationValidationMessages(error),
        });
      else if (error instanceof ApiError && error.status === 409)
        setSave({
          status: "error",
          message:
            locationConflictMessage(error) ??
            "Florabase could not apply that hierarchy change.",
        });
      else if (error instanceof ApiError && error.status === 403)
        setSave({
          status: "error",
          message:
            "Florabase could not authorize this change. Refresh the page and try again.",
        });
      else
        setSave({
          status: "error",
          message:
            "Florabase could not save or refresh this location. Check the connection and try again.",
        });
    }
  }

  async function removeSelected() {
    if (!selected || pending) return;
    if (
      !window.confirm(`Delete ${selected.display_path}? This cannot be undone.`)
    )
      return;
    setSave({ status: "saving" });
    try {
      await deleteLocation(selected.id, csrfToken);
      const refreshed = await listLocations();
      setDirectory({ status: "ready", locations: refreshed });
      setSelectedId(null);
      setEditing(false);
      setSave({
        status: "success",
        message: `${selected.display_path} was deleted.`,
      });
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else if (error instanceof ApiError && error.status === 409)
        setSave({
          status: "error",
          message:
            locationConflictMessage(error) ??
            "This Location cannot be deleted safely.",
        });
      else
        setSave({
          status: "error",
          message: "Florabase could not delete this Location.",
        });
    }
  }

  function submitCreate(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (pending) return;
    const form = event.currentTarget;
    void apply(
      () => createLocation(payloadFrom(form), csrfToken),
      (location) => {
        setCreateNameValue("");
        setCreateParentId("");
        closeCreation({ returnFocus: false });
        window.location.hash = `#/locations/${location.id}`;
        return `${location.display_path} was created and selected.`;
      },
    );
  }

  function dismissEdit() {
    if (pending) return;
    if (selected && editForm.current) {
      const payload = payloadFrom(editForm.current);
      const dirty =
        payload.name !== selected.name ||
        (payload.parent_id ?? "") !== (selected.parent_id ?? "") ||
        [...(payload.usage_scopes ?? [])].sort().join(",") !==
          [...selected.usage_scopes].sort().join(",");
      if (dirty && !window.confirm("Discard unsaved Location changes?")) return;
    }
    setEditing(false);
  }

  function submitUpdate(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (!selected || pending) return;
    if (!new FormData(event.currentTarget).get("parent_choice")) {
      setSave({
        status: "validation",
        messages: ["Choose a Parent location or No parent (root location)."],
      });
      return;
    }
    const payload: LocationUpdate = payloadFrom(event.currentTarget);
    void apply(
      () => updateLocation(selected.id, payload, csrfToken),
      (location) => `${location.display_path} was updated.`,
    );
  }

  return (
    <section
      aria-labelledby={initialId ? undefined : "locations-title"}
      className="workspace locations-workspace ui-hierarchy-workspace"
    >
      {!initialId && (
        <PageHeader
          title="Locations"
          titleId="locations-title"
          eyebrow="Collection"
          directory
          description="Where your collection lives."
          tools={
            <DirectoryTools
              onReset={() => {
                view.replace({ ...view.state, state: "all", scope: "all" });
              }}
              name="Locations"
              search={
                <DirectorySearch
                  hideLabel
                  id="location-search"
                  label="Search locations"
                  placeholder="Name or path"
                  value={query}
                  onChange={setQuery}
                />
              }
              savedViews={
                <SavedViews
                  presentation="dialog"
                  surface="locations"
                  state={view.savedState}
                />
              }
              filters={
                <>
                  <div className="field">
                    <label htmlFor="location-state">State</label>
                    <select
                      id="location-state"
                      value={stateFilter}
                      onChange={(event) => {
                        view.update(
                          "state",
                          event.currentTarget.value as typeof stateFilter,
                        );
                      }}
                    >
                      <option value="active">Active</option>
                      <option value="retired">Retired</option>
                      <option value="all">All</option>
                    </select>
                  </div>
                  <div className="field location-scope-filter">
                    <label htmlFor="location-scope">Usage scope</label>
                    <select
                      id="location-scope"
                      value={scopeFilter}
                      onChange={(event) => {
                        setScopeFilter(
                          event.currentTarget.value as typeof scopeFilter,
                        );
                      }}
                    >
                      <option value="all">All locations</option>
                      <option value="seed_lots">Seeds</option>
                      <option value="sowings">Sowings</option>
                      <option value="plants">Plants</option>
                      <option value="harvest_inventory">Stored material</option>
                      <option value="vegetative_lots">Vegetative lots</option>
                      <option value="propagation_attempts">
                        Rooting attempts
                      </option>
                    </select>
                  </div>
                </>
              }
              activeFilters={[
                ...(stateFilter !== "all"
                  ? [
                      {
                        label: "State",
                        value: stateFilter === "active" ? "Active" : "Retired",
                        onRemove: () => {
                          view.update("state", "all");
                        },
                      },
                    ]
                  : []),
                ...(scopeFilter !== "all"
                  ? [
                      {
                        label: "Usage scope",
                        value: {
                          seed_lots: "Seeds",
                          sowings: "Sowings",
                          plants: "Plants",
                          harvest_inventory: "Stored material",
                          vegetative_lots: "Vegetative lots",
                          propagation_attempts: "Rooting attempts",
                        }[scopeFilter],
                        onRemove: () => {
                          setScopeFilter("all");
                        },
                      },
                    ]
                  : []),
              ]}
              actions={
                <ActionButton
                  icon="add"
                  type="button"
                  ref={creationTriggerRef}
                  aria-haspopup="dialog"
                  onClick={() => {
                    setCreateNameValue("");
                    setCreateParentId("");
                    setSave({ status: "idle" });
                    openCreation();
                  }}
                >
                  New location
                </ActionButton>
              }
            />
          }
        />
      )}
      <div className={initialId ? "location-detail-layout" : "reference-split"}>
        {!initialId && (
          <div className="directory-column">
            <section
              aria-labelledby="location-directory-title"
              className="identity-directory"
            >
              <h3 className="sr-only" id="location-directory-title">
                Location directory
              </h3>

              {directory.status === "ready" && (
                <DirectoryResults count={matching.length} />
              )}
              {directory.status === "loading" && (
                <p aria-live="polite" className="notice">
                  Loading locations…
                </p>
              )}
              {directory.status === "error" && (
                <div className="notice notice--error" role="alert">
                  <p>Florabase could not load the location directory.</p>
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
              {directory.status === "ready" && locations.length === 0 && (
                <div className="empty-state">
                  <p>No locations yet.</p>
                </div>
              )}
              {locations.length > 0 && matching.length === 0 && (
                <p role="status" className="empty-state">
                  No locations match this search and scope.
                </p>
              )}
              {locations.length > 0 && matching.length > 0 && (
                <LocationTree
                  locations={shownLocations}
                  parentId={null}
                  selectedId={selectedId}
                  onSelect={(id) => {
                    setSelectedId(id);
                    window.location.hash = `#/locations/${id}`;
                    setEditing(false);
                    setSave({ status: "idle" });
                  }}
                  expanded={effectiveExpanded}
                  onToggle={(id) => {
                    if (autoExpandMatches) {
                      const wasOpen = effectiveExpanded.has(id);
                      setFilterExpansion((current) => {
                        const overrides = new Map(
                          current.key === filterKey
                            ? current.overrides
                            : undefined,
                        );
                        overrides.set(id, !wasOpen);
                        return { key: filterKey, overrides };
                      });
                    } else {
                      setExpanded((current) => {
                        const next = new Set(current);
                        if (next.has(id)) next.delete(id);
                        else next.add(id);
                        return next;
                      });
                    }
                  }}
                />
              )}
            </section>
          </div>
        )}
        {initialId && (
          <div className="record-detail-container" aria-live="polite">
            {selected ? (
              <DetailPage
                aria-label="Location detail"
                className="location-detail"
              >
                <Breadcrumbs
                  items={[
                    { label: "Locations", href: "#/locations" },
                    { label: selected.name },
                  ]}
                />
                <DetailHeader
                  label={
                    <SpecimenLabel
                      kind="Location"
                      name="Location overview"
                      rows={[
                        {
                          label: "State",
                          value: selected.retired_at ? "Retired" : "Active",
                        },
                        {
                          label: "Parent",
                          value: selected.parent_id ? (
                            <a href={`#/locations/${selected.parent_id}`}>
                              {
                                locations.find(
                                  (location) =>
                                    location.id === selected.parent_id,
                                )?.name
                              }
                            </a>
                          ) : (
                            "Root location"
                          ),
                        },
                        {
                          label: "Children",
                          value: locations.filter(
                            (location) => location.parent_id === selected.id,
                          ).length,
                        },
                      ]}
                    />
                  }
                  eyebrow="Location"
                  title={selected.name}
                  secondary={
                    <span className="record-path">{selected.display_path}</span>
                  }
                  status={
                    <div className="record-badges">
                      <LifecycleStatus
                        state={selected.retired_at ? "retired" : "active"}
                      >
                        {selected.retired_at ? "Retired" : "Active"}
                      </LifecycleStatus>
                      <span
                        aria-label="Usage scopes"
                        className="record-scope-badges"
                      >
                        {selected.usage_scopes.map((scope) => (
                          <span className="location-scope" key={scope}>
                            {scopeLabels[scope]}
                          </span>
                        ))}
                      </span>
                    </div>
                  }
                  primaryActions={
                    !selected.retired_at ? (
                      <button
                        type="button"
                        disabled={pending}
                        onClick={() => {
                          setCreateParentId(selected.id);
                          setSave({ status: "idle" });
                          if (creationExpanded) createName.current?.focus();
                          else openCreation();
                        }}
                      >
                        Create child
                      </button>
                    ) : undefined
                  }
                  editLabel="Edit location"
                  onEdit={() => {
                    setEditing(true);
                  }}
                  overflow={
                    <OverflowMenu ariaLabel="More location actions">
                      <div className="overflow-actions">
                        <button
                          className="button--secondary"
                          type="button"
                          disabled={pending}
                          onClick={() =>
                            void apply(
                              () =>
                                setLocationRetired(
                                  selected.id,
                                  !selected.retired_at,
                                  csrfToken,
                                ),
                              (location) =>
                                location.retired_at
                                  ? `${location.display_path} was retired.`
                                  : `${location.display_path} was reactivated.`,
                            )
                          }
                        >
                          {selected.retired_at
                            ? "Reactivate location"
                            : "Retire location"}
                        </button>
                        <button
                          className="button--danger"
                          type="button"
                          disabled={pending}
                          onClick={() => void removeSelected()}
                        >
                          Delete location
                        </button>
                      </div>
                    </OverflowMenu>
                  }
                />
                {selected.retired_at && (
                  <p className="record-empty">
                    Retired location remains available for historical records.
                  </p>
                )}
                <div className="record-detail-grid location-overview-grid">
                  <section
                    className="record-section"
                    aria-labelledby="location-hierarchy-title"
                  >
                    <h4 id="location-hierarchy-title">Hierarchy</h4>
                    <dl className="record-facts">
                      <div>
                        <dt>Parent</dt>
                        <dd>
                          {selected.parent_id ? (
                            <a href={`#/locations/${selected.parent_id}`}>
                              {locations.find(
                                (location) =>
                                  location.id === selected.parent_id,
                              )?.name ?? "Parent location"}
                            </a>
                          ) : (
                            "Root location"
                          )}
                        </dd>
                      </div>
                      <div>
                        <dt>Full path</dt>
                        <dd>{selected.display_path}</dd>
                      </div>
                    </dl>
                    <h5>
                      Child locations (
                      {
                        locations.filter(
                          (location) => location.parent_id === selected.id,
                        ).length
                      }
                      )
                    </h5>
                    {locations.some(
                      (location) => location.parent_id === selected.id,
                    ) ? (
                      <ul className="record-link-list">
                        {locations
                          .filter(
                            (location) => location.parent_id === selected.id,
                          )
                          .map((child) => (
                            <li key={child.id}>
                              <a href={`#/locations/${child.id}`}>
                                {child.name}
                              </a>
                              <span className="record-list-meta">
                                {child.usage_scopes
                                  .map((scope) => scopeLabels[scope])
                                  .join(" · ")}
                                {child.retired_at ? " · Retired" : ""}
                              </span>
                            </li>
                          ))}
                      </ul>
                    ) : (
                      <p className="record-empty">No child locations.</p>
                    )}
                  </section>
                  <CollectionUsage location={selected} />
                  <section className="record-section location-enabled-scopes">
                    <h4>Enabled scopes</h4>
                    <p>
                      {selected.usage_scopes
                        .map((scope) => scopeLabels[scope])
                        .join(" · ")}
                    </p>
                    <p className="field-help">
                      Explicit assignment scopes. Scopes do not inherit from
                      parent locations.
                    </p>
                  </section>
                </div>
              </DetailPage>
            ) : directory.status === "loading" ? (
              <DetailLoading
                eyebrow="Location"
                label="Loading Location detail…"
                parents={[{ label: "Locations", href: "#/locations" }]}
                className="location-detail"
                visual={false}
              />
            ) : (
              <div className="empty-state">
                {directory.status === "error" ? (
                  <div role="alert">
                    <h3>Could not load Location</h3>
                    <button
                      type="button"
                      onClick={() => {
                        setDirectory({ status: "loading" });
                        setAttempt((value) => value + 1);
                      }}
                    >
                      Retry Location
                    </button>
                  </div>
                ) : (
                  <h3>Location not found</h3>
                )}
                <a href="#/locations">Return to Locations</a>
              </div>
            )}
          </div>
        )}
      </div>
      {editing && selected && (
        <TaskDialog
          title="Edit location"
          dismissOnBackdrop
          onClose={() => {
            dismissEdit();
          }}
        >
          <form
            ref={editForm}
            className="location-edit-form"
            key={`${selected.id}-${selected.updated_at}`}
            onSubmit={submitUpdate}
          >
            <h4>Edit location</h4>
            <div className="field">
              <FieldLabel required htmlFor="edit-location-name">
                Name
              </FieldLabel>
              <input
                id="edit-location-name"
                name="name"
                required
                maxLength={255}
                disabled={pending}
                defaultValue={selected.name}
              />
            </div>
            <ParentField
              id="edit-location-parent"
              locations={locations}
              selected={selected}
              disabled={pending}
            />
            <ScopeFields selected={selected} disabled={pending} />
            {save.status === "validation" && (
              <div
                className="notice notice--error"
                role="alert"
                ref={feedback}
                tabIndex={-1}
              >
                <h4>Check the location</h4>
                <ul>
                  {save.messages.map((message) => (
                    <li key={message}>{message}</li>
                  ))}
                </ul>
              </div>
            )}
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
                Save location
              </button>
              <button
                className="button--secondary"
                type="button"
                disabled={pending}
                onClick={() => {
                  dismissEdit();
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        </TaskDialog>
      )}
      {creationExpanded && (
        <TaskDialog
          title={createParentId ? "New child location" : "New location"}
          onClose={dismissCreate}
        >
          <div ref={creationPanelRef}>
            <form
              ref={createForm}
              className="identity-form"
              aria-busy={pending}
              onSubmit={submitCreate}
            >
              <h3>Create a location</h3>
              <div className="field">
                <FieldLabel required htmlFor="new-location-name">
                  Name
                </FieldLabel>
                <input
                  id="new-location-name"
                  name="name"
                  required
                  maxLength={255}
                  disabled={pending}
                  ref={createName}
                  value={createNameValue}
                  onChange={(event) => {
                    setCreateNameValue(event.currentTarget.value);
                  }}
                />
              </div>
              <ParentField
                id="new-location-parent"
                locations={locations.filter((location) => !location.retired_at)}
                value={createParentId}
                disabled={pending}
                onChange={setCreateParentId}
              />
              <ScopeFields disabled={pending} />
              {save.status === "validation" && (
                <div
                  className="notice notice--error"
                  role="alert"
                  ref={feedback}
                  tabIndex={-1}
                >
                  <h4>Check the location</h4>
                  <ul>
                    {save.messages.map((message) => (
                      <li key={message}>{message}</li>
                    ))}
                  </ul>
                </div>
              )}
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
                  {pending ? "Saving location…" : "Create location"}
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
          <p className="notice">Saving the location…</p>
        )}
        {save.status === "success" && (
          <p className="notice notice--success">{save.message}</p>
        )}
        {!creationExpanded && !editing && save.status === "validation" && (
          <div
            className="notice notice--error"
            role="alert"
            ref={feedback}
            tabIndex={-1}
          >
            <h3>Check the location</h3>
            <ul>
              {save.messages.map((message) => (
                <li key={message}>{message}</li>
              ))}
            </ul>
          </div>
        )}
        {!creationExpanded && !editing && save.status === "error" && (
          <div
            className="notice notice--error"
            role="alert"
            ref={feedback}
            tabIndex={-1}
          >
            <p>{save.message}</p>
          </div>
        )}
      </div>
    </section>
  );
}
