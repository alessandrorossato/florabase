import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type SyntheticEvent,
} from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { BotanicalProfilePanel } from "../botanical-profiles/BotanicalProfilePanel";
import {
  getIdentityCollection,
  type BotanicalIdentityCollectionResponse,
} from "../collection/api";
import {
  Breadcrumbs,
  CollectionCard,
  DetailHeader,
  DetailTabs,
} from "../components/CollectionUI";
import { useCreationDisclosure } from "../components/useCreationDisclosure";
import { EventFeed } from "../events/EventFeed";
import {
  conflictExistingId,
  createBotanicalIdentity,
  deleteBotanicalIdentity,
  getBotanicalIdentity,
  listBotanicalIdentities,
  updateBotanicalIdentity,
  validationMessages,
  type BotanicalIdentityCreate,
  type BotanicalIdentityResponse,
} from "./api";

type DirectoryState =
  | { status: "loading" }
  | { status: "ready"; identities: BotanicalIdentityResponse[] }
  | { status: "error" };
type CreateState =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "validation"; messages: string[] }
  | { status: "duplicate"; existingId: string | null }
  | { status: "loading-existing"; existingId: string }
  | { status: "error"; message: string }
  | { status: "created"; message: string };

function IdentityDetails({
  identity,
  csrfToken,
  initialTab,
  onSaved,
  onDeleted,
}: {
  identity: BotanicalIdentityResponse;
  csrfToken: string;
  initialTab?: string;
  onSaved: (identity: BotanicalIdentityResponse) => Promise<void>;
  onDeleted: () => Promise<void>;
}) {
  const tabs = ["overview", "seeds", "sowings", "plants", "events"] as const;
  type IdentityTab = (typeof tabs)[number];
  const [tab, setTab] = useState<IdentityTab>(
    initialTab && tabs.includes(initialTab as (typeof tabs)[number])
      ? (initialTab as IdentityTab)
      : "overview",
  );
  const [collection, setCollection] = useState<
    | { status: "loading" }
    | { status: "ready"; value: BotanicalIdentityCollectionResponse }
    | { status: "error" }
  >({ status: "loading" });
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({
    scientific_name: identity.scientific_name,
    cultivar_name: identity.cultivar_name ?? "",
    common_name: identity.common_name ?? "",
  });

  useEffect(() => {
    const controller = new AbortController();
    void getIdentityCollection(identity.id, controller.signal)
      .then((value) => {
        setCollection({ status: "ready", value });
      })
      .catch(() => {
        if (!controller.signal.aborted) setCollection({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [identity.id]);

  async function saveEdit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setMutationError(null);
    try {
      const updated = await updateBotanicalIdentity(
        identity.id,
        {
          scientific_name: editForm.scientific_name,
          cultivar_name: editForm.cultivar_name || null,
          common_name: editForm.common_name || null,
        },
        csrfToken,
      );
      await onSaved(updated);
      setEditing(false);
    } catch (error: unknown) {
      setMutationError(
        error instanceof ApiError && error.status === 409
          ? "Another botanical identity already uses that scientific name and cultivar."
          : "Florabase could not save this botanical identity.",
      );
    }
  }

  async function removeIdentity() {
    setDeleting(true);
    setMutationError(null);
    try {
      await deleteBotanicalIdentity(identity.id, csrfToken);
      await onDeleted();
    } catch (error: unknown) {
      setMutationError(
        error instanceof ApiError && error.status === 409
          ? "This botanical identity is used by collection records and cannot be deleted."
          : "Florabase could not delete this botanical identity.",
      );
      setConfirmDelete(false);
      setDeleting(false);
    }
  }

  const counts = collection.status === "ready" ? collection.value : null;
  const selectTab = (next: IdentityTab) => {
    setTab(next);
    window.history.replaceState(
      null,
      "",
      `#/identities/${identity.id}?tab=${next}`,
    );
  };
  return (
    <div className="identity-detail-stack">
      <Breadcrumbs
        items={[
          { label: "Botanical identities", href: "#/identities" },
          { label: identity.display_label },
        ]}
      />
      <DetailHeader
        eyebrow="Botanical identity"
        title={identity.display_label}
        secondary={identity.common_name}
        editLabel="Edit botanical identity"
        onEdit={() => {
          setEditForm({
            scientific_name: identity.scientific_name,
            cultivar_name: identity.cultivar_name ?? "",
            common_name: identity.common_name ?? "",
          });
          setMutationError(null);
          setEditing(true);
        }}
        overflow={
          <details className="overflow-menu">
            <summary aria-label="More botanical identity actions">…</summary>
            <button
              className="button--danger"
              type="button"
              onClick={() => {
                setConfirmDelete(true);
              }}
            >
              Delete
            </button>
          </details>
        }
      />
      {mutationError && (
        <div className="notice notice--error" role="alert">
          {mutationError}
        </div>
      )}
      {editing && (
        <form
          className="identity-form"
          onSubmit={(event) => void saveEdit(event)}
        >
          <h3>Edit botanical identity</h3>
          <div className="field">
            <label htmlFor="edit-scientific-name">Scientific name</label>
            <input
              id="edit-scientific-name"
              required
              maxLength={255}
              value={editForm.scientific_name}
              onChange={(event) => {
                const scientificName = event.currentTarget.value;
                setEditForm((value) => ({
                  ...value,
                  scientific_name: scientificName,
                }));
              }}
            />
          </div>
          <div className="field">
            <label htmlFor="edit-cultivar-name">Cultivar</label>
            <input
              id="edit-cultivar-name"
              maxLength={120}
              value={editForm.cultivar_name}
              onChange={(event) => {
                const cultivarName = event.currentTarget.value;
                setEditForm((value) => ({
                  ...value,
                  cultivar_name: cultivarName,
                }));
              }}
            />
          </div>
          <div className="field">
            <label htmlFor="edit-common-name">Common name</label>
            <input
              id="edit-common-name"
              maxLength={160}
              value={editForm.common_name}
              onChange={(event) => {
                const commonName = event.currentTarget.value;
                setEditForm((value) => ({
                  ...value,
                  common_name: commonName,
                }));
              }}
            />
          </div>
          <div className="actions">
            <button type="submit">Save changes</button>
            <button
              className="button--secondary"
              type="button"
              onClick={() => {
                setEditing(false);
              }}
            >
              Cancel
            </button>
          </div>
        </form>
      )}
      {confirmDelete && (
        <div
          aria-labelledby="delete-identity-title"
          aria-modal="true"
          className="dialog-backdrop"
          role="dialog"
        >
          <div className="dialog-card">
            <h3 id="delete-identity-title">Delete {identity.display_label}?</h3>
            <p>
              Only an unused identity can be deleted. Collection records are
              never cascaded.
            </p>
            <div className="actions">
              <button
                className="button--danger"
                disabled={deleting}
                type="button"
                onClick={() => void removeIdentity()}
              >
                {deleting ? "Deleting…" : "Delete botanical identity"}
              </button>
              <button
                className="button--secondary"
                type="button"
                onClick={() => {
                  setConfirmDelete(false);
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
      <DetailTabs
        tabs={tabs.map((id) => ({
          id,
          label: id[0].toUpperCase() + id.slice(1),
        }))}
        selected={tab}
        onSelect={(next) => {
          selectTab(next);
        }}
      />
      {collection.status === "loading" && (
        <p role="status">Loading collection context…</p>
      )}
      {collection.status === "error" && (
        <div className="notice notice--error">
          Florabase could not load this identity’s collection context.
        </div>
      )}
      {tab === "overview" && (
        <div
          className="detail-tab-panel"
          role="tabpanel"
          aria-labelledby="tab-overview"
        >
          {counts && (
            <div className="summary-grid identity-summary-grid">
              <CollectionCard
                eyebrow="Active"
                title={String(
                  counts.seed_lots.filter(
                    ({ lifecycle }) => lifecycle === "active",
                  ).length,
                )}
              >
                <button
                  className="link-button"
                  type="button"
                  onClick={() => {
                    selectTab("seeds");
                  }}
                >
                  Seed lots
                </button>
              </CollectionCard>
              <CollectionCard
                eyebrow="Current"
                title={String(counts.sowings.length)}
              >
                <button
                  className="link-button"
                  type="button"
                  onClick={() => {
                    selectTab("sowings");
                  }}
                >
                  Sowings
                </button>
              </CollectionCard>
              <CollectionCard
                eyebrow="Records"
                title={String(counts.plants.length)}
              >
                <button
                  className="link-button"
                  type="button"
                  onClick={() => {
                    selectTab("plants");
                  }}
                >
                  Plants
                </button>
              </CollectionCard>
              <CollectionCard
                eyebrow="Records"
                title={String(counts.plant_groups.length)}
              >
                <button
                  className="link-button"
                  type="button"
                  onClick={() => {
                    selectTab("plants");
                  }}
                >
                  Plant groups
                </button>
              </CollectionCard>
            </div>
          )}
          <article className="fact-card">
            <h3>Identity</h3>
            <dl>
              <div>
                <dt>Scientific name</dt>
                <dd>
                  <i>{identity.scientific_name}</i>
                </dd>
              </div>
              {identity.cultivar_name && (
                <div>
                  <dt>Cultivar</dt>
                  <dd>{identity.cultivar_name}</dd>
                </div>
              )}
              {identity.common_name && (
                <div>
                  <dt>Common name</dt>
                  <dd>{identity.common_name}</dd>
                </div>
              )}
            </dl>
          </article>
          <BotanicalProfilePanel identityId={identity.id} key={identity.id} />
          {counts && counts.events.length > 0 && (
            <section>
              <h3>Recent Events</h3>
              <EventFeed compact events={counts.events.slice(0, 4)} />
            </section>
          )}
          <p className="field-help">
            This hub groups records by their stored Botanical identity. It does
            not create or imply lineage.
          </p>
        </div>
      )}
      {counts && tab === "seeds" && (
        <div
          className="detail-tab-panel card-grid"
          role="tabpanel"
          aria-labelledby="tab-seeds"
        >
          {counts.seed_lots.length ? (
            counts.seed_lots.map((lot) => (
              <CollectionCard
                key={lot.id}
                eyebrow={lot.lifecycle}
                href={`#/seeds/${lot.id}`}
                title={lot.label ?? lot.botanical_identity.display_label}
              >
                <p>
                  {lot.quantity
                    ? `${lot.quantity.is_approximate ? "Approximately " : ""}${lot.quantity.value} ${lot.quantity.kind === "seed_count" ? "seeds" : (lot.quantity.unit ?? "weight")}`
                    : "Quantity not recorded"}
                </p>
                <p>{lot.location?.display_path ?? "Location not recorded"}</p>
              </CollectionCard>
            ))
          ) : (
            <div className="empty-state">
              <p>No SeedLots use this identity.</p>
            </div>
          )}
        </div>
      )}
      {counts && tab === "sowings" && (
        <div
          className="detail-tab-panel card-grid"
          role="tabpanel"
          aria-labelledby="tab-sowings"
        >
          {counts.sowings.length ? (
            counts.sowings.map((sowing) => (
              <CollectionCard
                key={sowing.id}
                eyebrow={sowing.lifecycle}
                href={`#/sowings/${sowing.id}`}
                title={sowing.label ?? "Unlabelled Sowing"}
              >
                <p>From {sowing.seed_lot.label ?? "unlabelled SeedLot"}</p>
                <p>
                  {sowing.location?.display_path ?? "Location not recorded"}
                </p>
              </CollectionCard>
            ))
          ) : (
            <div className="empty-state">
              <p>No Sowings originate from SeedLots with this identity.</p>
            </div>
          )}
        </div>
      )}
      {counts && tab === "plants" && (
        <div
          className="detail-tab-panel card-grid"
          role="tabpanel"
          aria-labelledby="tab-plants"
        >
          {counts.plants.length + counts.plant_groups.length ? (
            <>
              {counts.plants.map((plant) => (
                <CollectionCard
                  key={plant.id}
                  eyebrow="Plant"
                  href={`#/plants/${plant.id}`}
                  title={plant.label ?? plant.botanical_identity.display_label}
                >
                  <span className="record-state">{plant.lifecycle}</span>
                  <p>
                    {plant.location?.display_path ?? "Location not recorded"}
                  </p>
                </CollectionCard>
              ))}
              {counts.plant_groups.map((group) => (
                <CollectionCard
                  key={group.id}
                  eyebrow="Plant group"
                  href={`#/plant-groups/${group.id}`}
                  title={group.label ?? group.botanical_identity.display_label}
                >
                  <span className="record-state">{group.lifecycle}</span>
                  <p>
                    {group.location?.display_path ?? "Location not recorded"}
                  </p>
                </CollectionCard>
              ))}
            </>
          ) : (
            <div className="empty-state">
              <p>No Plants or Plant groups use this identity.</p>
            </div>
          )}
        </div>
      )}
      {counts && tab === "events" && (
        <div
          className="detail-tab-panel"
          role="tabpanel"
          aria-labelledby="tab-events"
        >
          {counts.events.length ? (
            <EventFeed events={counts.events} />
          ) : (
            <div className="empty-state">
              <p>
                No Events belong to Plants or Plant groups with this identity.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function BotanicalIdentityScreen({
  initialId,
  initialTab,
}: { initialId?: string; initialTab?: string } = {}) {
  const auth = useAuth();
  const [directory, setDirectory] = useState<DirectoryState>({
    status: "loading",
  });
  const [selected, setSelected] = useState<BotanicalIdentityResponse | null>(
    null,
  );
  const [filter, setFilter] = useState("");
  const [createState, setCreateState] = useState<CreateState>({
    status: "idle",
  });
  const [loadAttempt, setLoadAttempt] = useState(0);
  const feedbackRef = useRef<HTMLDivElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const {
    expanded: creationExpanded,
    triggerRef: creationTriggerRef,
    panelRef: creationPanelRef,
    open: openCreation,
    close: closeCreation,
    focusFirst: focusCreation,
  } = useCreationDisclosure();
  const pending =
    createState.status === "submitting" ||
    createState.status === "loading-existing";

  useEffect(() => {
    const controller = new AbortController();
    void listBotanicalIdentities(controller.signal)
      .then((value: unknown) => {
        if (!Array.isArray(value))
          throw new Error("Invalid identity directory response");
        const identities = value as BotanicalIdentityResponse[];
        setDirectory({ status: "ready", identities });
        setSelected((current) =>
          current === null
            ? (identities.find(({ id }) => id === initialId) ?? null)
            : (identities.find(({ id }) => id === current.id) ?? current),
        );
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
  }, [auth, initialId, loadAttempt]);

  useEffect(() => {
    if (["validation", "duplicate", "error"].includes(createState.status)) {
      feedbackRef.current?.focus();
    }
  }, [createState]);

  const filteredIdentities = useMemo(() => {
    if (directory.status !== "ready") return [];
    const query = filter.trim().toLocaleLowerCase();
    if (!query) return directory.identities;
    return directory.identities.filter((identity) =>
      [
        identity.display_label,
        identity.scientific_name,
        identity.cultivar_name,
        identity.common_name,
      ].some((value) => value?.toLocaleLowerCase().includes(query)),
    );
  }, [directory, filter]);

  if (
    auth.state.status !== "authenticated" &&
    auth.state.status !== "logging-out" &&
    auth.state.status !== "logout-failed"
  )
    return null;
  const csrfToken = auth.state.csrfToken;

  async function refreshAndSelect(
    identity: BotanicalIdentityResponse,
  ): Promise<void> {
    const identities = await listBotanicalIdentities();
    setDirectory({ status: "ready", identities });
    setSelected(identities.find(({ id }) => id === identity.id) ?? identity);
  }

  async function removeSelected(): Promise<void> {
    const identities = await listBotanicalIdentities();
    setDirectory({ status: "ready", identities });
    setSelected(null);
    window.history.replaceState(null, "", "#/identities");
  }

  async function submit(
    event: SyntheticEvent<HTMLFormElement, SubmitEvent>,
  ): Promise<void> {
    event.preventDefault();
    if (pending) return;
    const form = new FormData(event.currentTarget);
    const scientificName = form.get("scientific_name");
    const cultivarName = form.get("cultivar_name");
    const commonName = form.get("common_name");
    const payload: BotanicalIdentityCreate = {
      scientific_name: typeof scientificName === "string" ? scientificName : "",
      ...(typeof cultivarName === "string" && cultivarName !== ""
        ? { cultivar_name: cultivarName }
        : {}),
      ...(typeof commonName === "string" && commonName !== ""
        ? { common_name: commonName }
        : {}),
    };
    setCreateState({ status: "submitting" });
    try {
      const identity = await createBotanicalIdentity(payload, csrfToken);
      formRef.current?.reset();
      await refreshAndSelect(identity);
      setFilter("");
      setCreateState({
        status: "created",
        message: `${identity.display_label} was created and selected.`,
      });
      closeCreation();
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else if (error instanceof ApiError && error.status === 422) {
        setCreateState({
          status: "validation",
          messages: validationMessages(error),
        });
      } else if (error instanceof ApiError && error.status === 409) {
        setCreateState({
          status: "duplicate",
          existingId: conflictExistingId(error),
        });
      } else if (error instanceof ApiError && error.status === 403) {
        setCreateState({
          status: "error",
          message:
            "Florabase could not authorize this change. Refresh the page and try again.",
        });
      } else {
        setCreateState({
          status: "error",
          message:
            "Florabase could not save or refresh this botanical identity. Check the connection and try again.",
        });
      }
    }
  }

  async function selectExisting(existingId: string): Promise<void> {
    if (pending) return;
    const inDirectory =
      directory.status === "ready"
        ? directory.identities.find(({ id }) => id === existingId)
        : undefined;
    if (inDirectory) {
      setSelected(inDirectory);
      setFilter("");
      setCreateState({ status: "idle" });
      closeCreation();
      return;
    }
    setCreateState({ status: "loading-existing", existingId });
    try {
      const identity = await getBotanicalIdentity(existingId);
      await refreshAndSelect(identity);
      setFilter("");
      setCreateState({ status: "idle" });
      closeCreation();
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else if (error instanceof ApiError && error.status === 404) {
        setCreateState({
          status: "error",
          message:
            "The existing botanical identity could not be found. You can try creating it again.",
        });
      } else {
        setCreateState({
          status: "error",
          message:
            "Florabase could not load the existing botanical identity. Check the connection and try again.",
        });
      }
    }
  }

  return (
    <section aria-labelledby="botanical-identities-title" className="workspace">
      <div className="workspace-intro directory-heading">
        <div>
          <p className="eyebrow">Collection reference</p>
          <h2 id="botanical-identities-title">Botanical identities</h2>
          <p>
            Browse the botanical names used in this collection or add a new one.
          </p>
        </div>
        <button
          type="button"
          ref={creationTriggerRef}
          aria-expanded={creationExpanded}
          aria-controls="new-botanical-identity-panel"
          onClick={() => {
            if (creationExpanded) {
              focusCreation();
              return;
            }
            formRef.current?.reset();
            setCreateState({ status: "idle" });
            openCreation();
          }}
        >
          + New botanical identity
        </button>
      </div>
      <div className="directory-detail-grid">
        <div className="directory-column">
          <section
            aria-labelledby="identity-directory-title"
            className="identity-directory"
          >
            <h3 id="identity-directory-title">Identity directory</h3>
            <div className="field">
              <label htmlFor="identity-filter">
                Filter botanical identities
              </label>
              <input
                id="identity-filter"
                type="search"
                value={filter}
                onChange={(event) => {
                  setFilter(event.currentTarget.value);
                }}
                disabled={
                  directory.status !== "ready" ||
                  directory.identities.length === 0
                }
              />
            </div>
            {directory.status === "loading" && (
              <p aria-live="polite" className="notice">
                Loading botanical identities…
              </p>
            )}
            {directory.status === "error" && (
              <div className="notice notice--error" role="alert">
                <p>
                  Florabase could not load the botanical identity directory.
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setDirectory({ status: "loading" });
                    setLoadAttempt((attempt) => attempt + 1);
                  }}
                >
                  Retry directory
                </button>
              </div>
            )}
            {directory.status === "ready" &&
              directory.identities.length === 0 && (
                <div className="empty-state">
                  <p>No botanical identities yet.</p>
                </div>
              )}
            {directory.status === "ready" &&
              directory.identities.length > 0 &&
              filteredIdentities.length === 0 && (
                <p className="notice" role="status">
                  No botanical identities match this filter.
                </p>
              )}
            {filteredIdentities.length > 0 && (
              <ul className="identity-list">
                {filteredIdentities.map((identity) => (
                  <li key={identity.id}>
                    <button
                      type="button"
                      className="identity-list-item"
                      aria-pressed={selected?.id === identity.id}
                      onClick={() => {
                        setSelected(identity);
                        window.history.replaceState(
                          null,
                          "",
                          `#/identities/${identity.id}`,
                        );
                      }}
                    >
                      <span>{identity.display_label}</span>
                      {identity.common_name && (
                        <small>{identity.common_name}</small>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {creationExpanded && (
            <div
              id="new-botanical-identity-panel"
              className="creation-panel"
              ref={creationPanelRef}
            >
              <form
                aria-busy={createState.status === "submitting"}
                className="identity-form"
                ref={formRef}
                onSubmit={(event) => void submit(event)}
              >
                <h3>Create a botanical identity</h3>
                <div className="field">
                  <label htmlFor="scientific-name">Scientific name</label>
                  <input
                    id="scientific-name"
                    name="scientific_name"
                    required
                    maxLength={255}
                    disabled={pending}
                  />
                </div>
                <div className="field">
                  <label htmlFor="cultivar-name">Cultivar</label>
                  <input
                    id="cultivar-name"
                    name="cultivar_name"
                    maxLength={120}
                    aria-describedby="cultivar-hint"
                    disabled={pending}
                  />
                  <small id="cultivar-hint">
                    Enter the cultivar without quotation marks.
                  </small>
                </div>
                <div className="field">
                  <label htmlFor="common-name">Common name</label>
                  <input
                    id="common-name"
                    name="common_name"
                    maxLength={160}
                    disabled={pending}
                  />
                </div>
                <div className="actions">
                  <button type="submit" disabled={pending}>
                    {createState.status === "submitting"
                      ? "Creating botanical identity…"
                      : "Create botanical identity"}
                  </button>
                  <button
                    type="button"
                    className="button--secondary"
                    disabled={pending}
                    onClick={() => {
                      formRef.current?.reset();
                      setCreateState({ status: "idle" });
                      closeCreation();
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </form>

              <div aria-live="polite">
                {createState.status === "submitting" && (
                  <p className="notice">Saving the botanical identity…</p>
                )}
                {createState.status === "loading-existing" && (
                  <p className="notice">
                    Loading the existing botanical identity…
                  </p>
                )}
                {createState.status === "created" && (
                  <p className="notice notice--success">
                    {createState.message}
                  </p>
                )}
                {createState.status === "validation" && (
                  <div
                    className="notice notice--error"
                    role="alert"
                    ref={feedbackRef}
                    tabIndex={-1}
                  >
                    <h3>Check the botanical identity</h3>
                    <ul>
                      {createState.messages.map((message) => (
                        <li key={message}>{message}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {createState.status === "duplicate" && (
                  <div
                    className="notice notice--duplicate"
                    role="status"
                    ref={feedbackRef}
                    tabIndex={-1}
                  >
                    <h3>This botanical identity already exists</h3>
                    <p>No duplicate was created.</p>
                    {createState.existingId && (
                      <button
                        type="button"
                        onClick={() => {
                          const existingId = createState.existingId;
                          if (existingId) void selectExisting(existingId);
                        }}
                      >
                        Select existing botanical identity
                      </button>
                    )}
                  </div>
                )}
                {createState.status === "error" && (
                  <div
                    className="notice notice--error"
                    role="alert"
                    ref={feedbackRef}
                    tabIndex={-1}
                  >
                    <p>{createState.message}</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="identity-panel" aria-live="polite">
          {selected ? (
            <IdentityDetails
              identity={selected}
              csrfToken={csrfToken}
              initialTab={initialTab}
              onSaved={refreshAndSelect}
              onDeleted={removeSelected}
            />
          ) : (
            <div className="empty-state">
              <h3>Select a botanical identity</h3>
              <p>
                Choose a record from the directory to see its details and
                botanical profile.
              </p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
