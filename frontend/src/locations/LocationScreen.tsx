import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type SyntheticEvent,
} from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { useCreationDisclosure } from "../components/useCreationDisclosure";
import {
  createLocation,
  listLocations,
  locationConflictMessage,
  locationValidationMessages,
  setLocationRetired,
  updateLocation,
  type LocationCreate,
  type LocationResponse,
  type LocationUpdate,
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
  return {
    name: typeof name === "string" ? name : "",
    parent_id: typeof parentId === "string" && parentId ? parentId : undefined,
  };
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
  const excluded = selected
    ? new Set([selected.id, ...descendantsOf(selected.id, locations)])
    : new Set<string>();
  const candidates = locations.filter(
    (location) =>
      !excluded.has(location.id) &&
      (selected?.retired_at ? true : !location.retired_at),
  );
  return (
    <div className="field">
      <label htmlFor={id}>Parent location</label>
      <select
        id={id}
        name="parent_id"
        disabled={disabled}
        value={value}
        defaultValue={onChange ? undefined : (selected?.parent_id ?? "")}
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
      {selected && (
        <small>
          This location and its descendants are excluded to prevent cycles.
        </small>
      )}
    </div>
  );
}

function LocationTree({
  locations,
  parentId,
  selectedId,
  onSelect,
}: {
  locations: LocationResponse[];
  parentId: string | null;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const children = locations.filter(
    (location) => location.parent_id === parentId,
  );
  if (children.length === 0) return null;
  return (
    <ul
      className={
        parentId ? "location-tree location-tree--nested" : "location-tree"
      }
    >
      {children.map((location) => (
        <li key={location.id}>
          <button
            type="button"
            className="identity-list-item"
            aria-pressed={selectedId === location.id}
            onClick={() => {
              onSelect(location.id);
            }}
          >
            <span>
              {location.name}
              {location.retired_at && (
                <span className="record-state">Retired</span>
              )}
            </span>
            <small>{location.display_path}</small>
          </button>
          <LocationTree
            locations={locations}
            parentId={location.id}
            selectedId={selectedId}
            onSelect={onSelect}
          />
        </li>
      ))}
    </ul>
  );
}

export function LocationScreen() {
  const auth = useAuth();
  const [directory, setDirectory] = useState<DirectoryState>({
    status: "loading",
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [createNameValue, setCreateNameValue] = useState("");
  const [createParentId, setCreateParentId] = useState("");
  const [save, setSave] = useState<SaveState>({ status: "idle" });
  const [attempt, setAttempt] = useState(0);
  const createName = useRef<HTMLInputElement>(null);
  const feedback = useRef<HTMLDivElement>(null);
  const {
    expanded: creationExpanded,
    triggerRef: creationTriggerRef,
    panelRef: creationPanelRef,
    open: openCreation,
    close: closeCreation,
    focusFirst: focusCreation,
  } = useCreationDisclosure();
  const pending = save.status === "saving";

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
  const selected = locations.find(({ id }) => id === selectedId) ?? null;

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

  function submitCreate(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (pending) return;
    const form = event.currentTarget;
    void apply(
      () => createLocation(payloadFrom(form), csrfToken),
      (location) => {
        setCreateNameValue("");
        setCreateParentId("");
        closeCreation();
        return `${location.display_path} was created and selected.`;
      },
    );
  }

  function submitUpdate(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (!selected || pending) return;
    const payload: LocationUpdate = payloadFrom(event.currentTarget);
    void apply(
      () => updateLocation(selected.id, payload, csrfToken),
      (location) => `${location.display_path} was updated.`,
    );
  }

  return (
    <section aria-labelledby="locations-title" className="workspace">
      <div className="workspace-intro directory-heading">
        <div>
          <p className="eyebrow">Collection reference</p>
          <h2 id="locations-title">Locations</h2>
          <p>
            Maintain the physical places where collection material is stored or
            plants are cultivated.
          </p>
        </div>
        <button
          type="button"
          ref={creationTriggerRef}
          aria-expanded={creationExpanded}
          aria-controls="new-location-panel"
          onClick={() => {
            if (creationExpanded) {
              focusCreation();
              return;
            }
            setCreateNameValue("");
            setCreateParentId("");
            setSave({ status: "idle" });
            openCreation();
          }}
        >
          + New location
        </button>
      </div>
      <div className="directory-detail-grid">
        <div className="directory-column">
          <section
            aria-labelledby="location-directory-title"
            className="identity-directory"
          >
            <h3 id="location-directory-title">Location directory</h3>
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
            {locations.length > 0 && (
              <LocationTree
                locations={locations}
                parentId={null}
                selectedId={selectedId}
                onSelect={(id) => {
                  setSelectedId(id);
                  setSave({ status: "idle" });
                }}
              />
            )}
          </section>
          {creationExpanded && (
            <div
              id="new-location-panel"
              className="creation-panel"
              ref={creationPanelRef}
            >
              <form
                className="identity-form"
                aria-busy={pending}
                onSubmit={submitCreate}
              >
                <h3>Create a location</h3>
                <div className="field">
                  <label htmlFor="new-location-name">Name</label>
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
                  locations={locations.filter(
                    (location) => !location.retired_at,
                  )}
                  value={createParentId}
                  disabled={pending}
                  onChange={setCreateParentId}
                />
                <div className="actions">
                  <button type="submit" disabled={pending}>
                    {pending ? "Saving location…" : "Create location"}
                  </button>
                  <button
                    type="button"
                    className="button--secondary"
                    disabled={pending}
                    onClick={() => {
                      setCreateNameValue("");
                      setCreateParentId("");
                      setSave({ status: "idle" });
                      closeCreation();
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
        <div className="identity-panel" aria-live="polite">
          {selected ? (
            <article
              aria-labelledby="location-detail-title"
              className="identity-result"
            >
              <p className="eyebrow">Selected location</p>
              <h3 id="location-detail-title">{selected.name}</h3>
              <p className="location-path">{selected.display_path}</p>
              {selected.retired_at && (
                <p className="notice notice--duplicate">
                  This location is retired and remains available for historical
                  records.
                </p>
              )}
              {!selected.retired_at && (
                <button
                  className="button--secondary"
                  type="button"
                  disabled={pending}
                  onClick={() => {
                    setCreateParentId(selected.id);
                    setSave({ status: "idle" });
                    if (creationExpanded) createName.current?.focus();
                    else openCreation();
                  }}
                >
                  Create child here
                </button>
              )}
              <form
                key={`${selected.id}-${selected.updated_at}`}
                onSubmit={submitUpdate}
              >
                <h4>Edit location</h4>
                <div className="field">
                  <label htmlFor="edit-location-name">Name</label>
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
                <div className="actions">
                  <button type="submit" disabled={pending}>
                    Save location
                  </button>
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
                </div>
              </form>
            </article>
          ) : (
            <div className="empty-state">
              <h3>Select a location</h3>
              <p>Choose a location from the hierarchy to use or maintain it.</p>
            </div>
          )}
        </div>
      </div>
      <div aria-live="polite">
        {save.status === "saving" && (
          <p className="notice">Saving the location…</p>
        )}
        {save.status === "success" && (
          <p className="notice notice--success">{save.message}</p>
        )}
        {save.status === "validation" && (
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
        {save.status === "error" && (
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
