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
import { BotanicalNativeRangeManager } from "../botanical-profiles/BotanicalNativeRangeManager";
import {
  getIdentityCollection,
  type BotanicalIdentityCollectionResponse,
} from "../collection/api";
import {
  Breadcrumbs,
  CollectionCard,
  DetailTabs,
} from "../components/CollectionUI";
import {
  PageHeader,
  FormSection,
  FormActions,
  DirectorySearch,
  OverflowMenu,
  QuickPreview,
} from "../components/ReferenceUI";
import {
  IdentityImage,
  IdentityName,
  IdentityStats,
  IdentityCardContext,
} from "./IdentitySummary";
import { PhotoDialog } from "../photos/PhotosSection";
import { FieldHelp } from "../components/ContextualHelp";
import { useCreationDisclosure } from "../components/useCreationDisclosure";
import { EventFeed } from "../events/EventFeed";
import { BotanicalIdentityCover } from "../photos/BotanicalIdentityCover";
import { ExternalBotanicalDataPanel } from "./ExternalBotanicalDataPanel";
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

const tabs = [
  "overview",
  "reference",
  "seeds",
  "sowings",
  "plants",
  "events",
] as const;

function displayDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(
    new Date(value),
  );
}

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
  type IdentityTab = (typeof tabs)[number];
  type ReferenceModule = "profile" | "native-range" | "source" | "occurrences";
  const [tab, setTab] = useState<IdentityTab>(
    initialTab && tabs.includes(initialTab as (typeof tabs)[number])
      ? (initialTab as IdentityTab)
      : initialTab === "collection"
        ? "seeds"
        : "overview",
  );
  const [referenceModule, setReferenceModule] =
    useState<ReferenceModule>("profile");
  const [collection, setCollection] = useState<
    | { status: "idle" }
    | { status: "loading" }
    | { status: "ready"; value: BotanicalIdentityCollectionResponse }
    | { status: "error" }
  >({ status: "idle" });
  const loadedCollectionIdentity = useRef<string | null>(null);
  const [collectionAttempt, setCollectionAttempt] = useState(0);
  const [editing, setEditing] = useState(initialTab === "edit");
  const [saving, setSaving] = useState(false);
  const editTrigger = useRef<HTMLButtonElement>(null);
  const editPanel = useRef<HTMLFormElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    titleRef.current?.focus({ preventScroll: true });
    window.scrollTo({ top: 0 });
  }, []);
  useEffect(() => {
    if (editing) editPanel.current?.querySelector("input")?.focus();
  }, [editing]);
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [editErrors, setEditErrors] = useState<string[]>([]);
  const editFieldError = (label: string) =>
    editErrors.find((message) => message.startsWith(label));
  const [editForm, setEditForm] = useState({
    scientific_name: identity.scientific_name,
    cultivar_name: identity.cultivar_name ?? "",
    common_name: identity.common_name ?? "",
  });

  useEffect(() => {
    if (tab === "reference" || loadedCollectionIdentity.current === identity.id)
      return;
    const controller = new AbortController();
    setCollection({ status: "loading" });
    void getIdentityCollection(identity.id, controller.signal)
      .then((value) => {
        loadedCollectionIdentity.current = identity.id;
        setCollection({ status: "ready", value });
      })
      .catch(() => {
        if (!controller.signal.aborted) setCollection({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [identity.id, tab, collectionAttempt]);

  async function saveEdit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) return;
    setSaving(true);
    setEditErrors([]);
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
      editTrigger.current?.focus();
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 422)
        setEditErrors(validationMessages(error));
      setMutationError(
        error instanceof ApiError && error.status === 409
          ? "Another botanical identity already uses that scientific name and cultivar."
          : error instanceof ApiError && error.status === 422
            ? validationMessages(error).join(" ")
            : "Florabase could not save this botanical identity.",
      );
    } finally {
      setSaving(false);
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
          ? "This botanical identity has collection records or a cover image. Remove those references before deleting it."
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
  const openIdentityEditor = () => {
    setEditForm({
      scientific_name: identity.scientific_name,
      cultivar_name: identity.cultivar_name ?? "",
      common_name: identity.common_name ?? "",
    });
    setMutationError(null);
    setEditErrors([]);
    setEditing(true);
  };
  const identityActions = (
    <div className="actions identity-header-actions">
      <a
        className="button-link"
        href={`#/seeds?action=create&identity=${identity.id}`}
      >
        Add seed lot
      </a>
      <button
        className="button--secondary"
        ref={editTrigger}
        type="button"
        onClick={openIdentityEditor}
      >
        Edit botanical identity
      </button>
      <OverflowMenu label="…" ariaLabel="More botanical identity actions">
        <button
          className="button--danger"
          type="button"
          onClick={() => {
            setConfirmDelete(true);
          }}
        >
          Delete
        </button>
      </OverflowMenu>
    </div>
  );
  return (
    <div className="identity-detail-stack">
      <Breadcrumbs
        items={[
          { label: "Botanical identities", href: "#/identities" },
          { label: identity.display_label },
        ]}
      />
      <div className="identity-detail-layout">
        {tab === "overview" ? (
          <section
            className="identity-summary"
            aria-labelledby="identity-summary-title"
          >
            <div className="identity-summary-row">
              <BotanicalIdentityCover
                integrated
                csrfToken={csrfToken}
                identityId={identity.id}
                identityLabel={identity.display_label}
              />
              <div className="entity-hero-copy">
                <p className="eyebrow">Botanical identity</p>
                <h2
                  id="identity-summary-title"
                  ref={titleRef}
                  tabIndex={-1}
                  className="entity-title"
                >
                  <IdentityName identity={identity} />
                </h2>
                {identity.common_name && (
                  <p className="entity-common-name">{identity.common_name}</p>
                )}
                <IdentityStats identity={identity} />
                {identityActions}
              </div>
            </div>
          </section>
        ) : (
          <section
            className="identity-work-header"
            aria-labelledby="identity-summary-title"
          >
            <IdentityImage identity={identity} />
            <div className="identity-work-header__copy">
              <p className="eyebrow">Botanical identity</p>
              <h2
                id="identity-summary-title"
                ref={titleRef}
                tabIndex={-1}
                className="identity-work-title"
              >
                <IdentityName identity={identity} />
              </h2>
              {identity.common_name && <p>{identity.common_name}</p>}
            </div>
            {identityActions}
          </section>
        )}
        <div className="identity-detail-main">
          {mutationError && (
            <div className="notice notice--error" role="alert">
              {mutationError}
            </div>
          )}
          {editing && (
            <form
              className="identity-form"
              ref={editPanel}
              aria-busy={saving}
              onSubmit={(event) => void saveEdit(event)}
            >
              <h3>Edit botanical identity</h3>
              <FormSection title="Botanical name">
                <div className="field field--full">
                  <label htmlFor="edit-scientific-name">Scientific name</label>
                  <input
                    aria-invalid={
                      Boolean(editFieldError("Scientific name")) || undefined
                    }
                    aria-describedby={
                      editFieldError("Scientific name")
                        ? "edit-identity-help edit-scientific-name-error"
                        : "edit-identity-help"
                    }
                    id="edit-scientific-name"
                    disabled={saving}
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
                  <FieldHelp id="edit-identity-help">
                    This stable collection-local identity can be shared by
                    records without implying that those records share a lineage.
                  </FieldHelp>
                  {editFieldError("Scientific name") && (
                    <p className="field-error" id="edit-scientific-name-error">
                      {editFieldError("Scientific name")}
                    </p>
                  )}
                </div>
                <div className="field">
                  <label htmlFor="edit-cultivar-name">Cultivar</label>
                  <input
                    id="edit-cultivar-name"
                    aria-invalid={
                      Boolean(editFieldError("Cultivar")) || undefined
                    }
                    aria-describedby={
                      editFieldError("Cultivar")
                        ? "edit-cultivar-name-error"
                        : undefined
                    }
                    disabled={saving}
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
                  {editFieldError("Cultivar") && (
                    <p className="field-error" id="edit-cultivar-name-error">
                      {editFieldError("Cultivar")}
                    </p>
                  )}
                </div>
                <div className="field">
                  <label htmlFor="edit-common-name">Common name</label>
                  <input
                    id="edit-common-name"
                    aria-invalid={
                      Boolean(editFieldError("Common name")) || undefined
                    }
                    aria-describedby={
                      editFieldError("Common name")
                        ? "edit-common-name-error"
                        : undefined
                    }
                    disabled={saving}
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
                  {editFieldError("Common name") && (
                    <p className="field-error" id="edit-common-name-error">
                      {editFieldError("Common name")}
                    </p>
                  )}
                </div>
              </FormSection>
              <FormActions>
                <button
                  className="button--secondary"
                  type="button"
                  disabled={saving}
                  onClick={() => {
                    setEditing(false);
                    editTrigger.current?.focus();
                  }}
                >
                  Cancel
                </button>
                <button type="submit" disabled={saving}>
                  {saving ? "Saving…" : "Save changes"}
                </button>
              </FormActions>
            </form>
          )}
          {confirmDelete && (
            <PhotoDialog
              title={`Delete ${identity.display_label}?`}
              onClose={() => {
                if (!deleting) setConfirmDelete(false);
              }}
            >
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
            </PhotoDialog>
          )}
          <div className="identity-detail-tabs">
            <DetailTabs
              tabs={["overview", "collection", "reference", "events"].map(
                (id) => ({
                  id,
                  label: id[0].toUpperCase() + id.slice(1),
                }),
              )}
              selected={
                ["seeds", "sowings", "plants"].includes(tab)
                  ? "collection"
                  : tab
              }
              onSelect={(next) => {
                selectTab(
                  next === "collection" ? "seeds" : (next as IdentityTab),
                );
              }}
            />
          </div>
          {tab !== "reference" && collection.status === "loading" && (
            <p role="status">Loading collection context…</p>
          )}
          {tab !== "reference" && collection.status === "error" && (
            <div className="notice notice--error" role="alert">
              <p>
                Florabase could not load this identity’s collection context.
              </p>
              <button
                type="button"
                onClick={() => {
                  setCollectionAttempt((n) => n + 1);
                }}
              >
                Retry collection
              </button>
            </div>
          )}
          {tab === "overview" && (
            <div
              id="panel-overview"
              className="detail-tab-panel"
              role="tabpanel"
              aria-labelledby="tab-overview"
            >
              <article className="content-section">
                <h3>Record details</h3>
                <dl>
                  <div>
                    <dt>Created</dt>
                    <dd>{displayDate(identity.created_at)}</dd>
                  </div>
                  <div>
                    <dt>Last updated</dt>
                    <dd>{displayDate(identity.updated_at)}</dd>
                  </div>
                </dl>
              </article>
              {counts && counts.events.length > 0 && (
                <section>
                  <h3>Recent events</h3>
                  <EventFeed compact events={counts.events.slice(0, 4)} />
                </section>
              )}
            </div>
          )}
          {tab === "reference" && (
            <section
              id="panel-reference"
              className="detail-tab-panel identity-reference-stack"
              role="tabpanel"
              aria-labelledby="tab-reference"
            >
              <h3 className="reference-title">Reference</h3>
              <DetailTabs
                label="Reference sections"
                tabs={[
                  { id: "profile", label: "Profile" },
                  { id: "native-range", label: "Native range" },
                  { id: "source", label: "Botanical source" },
                  { id: "occurrences", label: "Occurrences" },
                ]}
                selected={referenceModule}
                onSelect={(next) => {
                  setReferenceModule(next);
                }}
              />
              <div
                id={`panel-${referenceModule}`}
                className="reference-module-panel"
                role="tabpanel"
                aria-labelledby={`tab-${referenceModule}`}
              >
                {referenceModule === "profile" && (
                  <BotanicalProfilePanel
                    identityId={identity.id}
                    includeNativeRange={false}
                    key={identity.id}
                  />
                )}
                {referenceModule === "native-range" && (
                  <BotanicalNativeRangeManager identityId={identity.id} />
                )}
                {referenceModule === "source" && (
                  <ExternalBotanicalDataPanel
                    key={`source-${identity.id}`}
                    csrfToken={csrfToken}
                    identityId={identity.id}
                    scientificName={identity.scientific_name}
                    view="source"
                  />
                )}
                {referenceModule === "occurrences" && (
                  <ExternalBotanicalDataPanel
                    key={`occurrences-${identity.id}`}
                    csrfToken={csrfToken}
                    identityId={identity.id}
                    scientificName={identity.scientific_name}
                    view="occurrences"
                  />
                )}
              </div>
            </section>
          )}
          {["seeds", "sowings", "plants"].includes(tab) && (
            <section
              id="panel-collection"
              role="tabpanel"
              aria-labelledby="tab-collection"
            >
              <DetailTabs
                label="Collection sections"
                tabs={[
                  { id: "seeds", label: "Seeds" },
                  { id: "sowings", label: "Sowings" },
                  { id: "plants", label: "Plants / Plant groups" },
                ]}
                selected={tab}
                onSelect={selectTab}
              />
              {counts && tab === "seeds" && (
                <div
                  id="panel-seeds"
                  className="detail-tab-panel"
                  role="tabpanel"
                  aria-labelledby="tab-seeds"
                >
                  <div className="contextual-workflow">
                    <div>
                      <p className="eyebrow">Next step</p>
                      <h3>Add seed material</h3>
                    </div>
                    <a
                      className="button-link"
                      href={`#/seeds?action=create&identity=${identity.id}`}
                    >
                      Add seed lot
                    </a>
                  </div>
                  {counts.seed_lots.length ? (
                    <div className="card-grid">
                      {counts.seed_lots.map((lot) => (
                        <CollectionCard
                          key={lot.id}
                          eyebrow={lot.lifecycle}
                          href={`#/seeds/${lot.id}`}
                          title={
                            lot.label ?? lot.botanical_identity.display_label
                          }
                        >
                          <p>
                            {lot.quantity
                              ? `${lot.quantity.is_approximate ? "Approximately " : ""}${lot.quantity.value} ${lot.quantity.kind === "seed_count" ? "seeds" : (lot.quantity.unit ?? "weight")}`
                              : "Quantity not recorded"}
                          </p>
                          <p>
                            {lot.location?.display_path ??
                              "Location not recorded"}
                          </p>
                        </CollectionCard>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-state">
                      <p>No seed lots use this identity.</p>
                    </div>
                  )}
                </div>
              )}
              {counts && tab === "sowings" && (
                <div
                  id="panel-sowings"
                  className="detail-tab-panel"
                  role="tabpanel"
                  aria-labelledby="tab-sowings"
                >
                  <section
                    className="workflow-launcher"
                    aria-labelledby="identity-start-sowing"
                  >
                    <div>
                      <p className="eyebrow">Next step</p>
                      <h3 id="identity-start-sowing">Start a sowing</h3>
                      <p>Choose the source seed lot.</p>
                    </div>
                    {counts.seed_lots.some(
                      ({ lifecycle }) => lifecycle === "active",
                    ) ? (
                      <div className="workflow-choice-list">
                        {counts.seed_lots
                          .filter(({ lifecycle }) => lifecycle === "active")
                          .map((lot) => (
                            <article className="workflow-choice" key={lot.id}>
                              <p>
                                <strong>
                                  {lot.label ?? "Unlabelled seed lot"}
                                </strong>
                              </p>
                              <p>
                                {lot.quantity
                                  ? `${lot.quantity.is_approximate ? "~" : ""}${lot.quantity.value} ${lot.quantity.kind === "seed_count" ? "seeds" : (lot.quantity.unit ?? "weight")}`
                                  : "Quantity unknown"}{" "}
                                · {lot.lifecycle}
                              </p>
                              <p>
                                {lot.location?.display_path ??
                                  "Storage not recorded"}
                                {lot.supplier ? ` · ${lot.supplier.name}` : ""}
                              </p>
                              <a
                                className="button-link"
                                href={`#/sowings?action=start&seedLot=${lot.id}`}
                              >
                                Start sowing
                              </a>
                            </article>
                          ))}
                      </div>
                    ) : (
                      <div className="empty-state">
                        <p>
                          Record an active seed lot before starting a sowing.
                        </p>
                        <a
                          className="button-link"
                          href={`#/seeds?action=create&identity=${identity.id}`}
                        >
                          Create seed lot
                        </a>
                      </div>
                    )}
                  </section>
                  <section className="record-section">
                    <h3>Recorded sowings</h3>
                    {counts.sowings.length ? (
                      <div className="card-grid">
                        {counts.sowings.map((sowing) => (
                          <CollectionCard
                            key={sowing.id}
                            eyebrow={sowing.lifecycle}
                            href={`#/sowings/${sowing.id}`}
                            title={sowing.label ?? "Unlabelled sowing"}
                          >
                            <p>
                              From{" "}
                              {sowing.seed_lot.label ?? "unlabelled seed lot"}
                            </p>
                            <p>
                              {sowing.location?.display_path ??
                                "Location not recorded"}
                            </p>
                          </CollectionCard>
                        ))}
                      </div>
                    ) : (
                      <div className="empty-state">
                        <p>No recorded sowings for this identity.</p>
                      </div>
                    )}
                  </section>
                </div>
              )}
              {counts && tab === "plants" && (
                <div
                  id="panel-plants"
                  className="detail-tab-panel"
                  role="tabpanel"
                  aria-labelledby="tab-plants"
                >
                  <section
                    className="contextual-workflow"
                    aria-labelledby="identity-add-plant"
                  >
                    <div>
                      <p className="eyebrow">Next step</p>
                      <h3 id="identity-add-plant">
                        Add to the living collection
                      </h3>
                      <p>
                        Choose explicit propagation lineage or preserve a
                        legitimate direct/acquired origin.
                      </p>
                    </div>
                    <div className="actions">
                      <a
                        className="button-link button--secondary"
                        href={`#/plants?action=create&identity=${identity.id}&kind=plant`}
                      >
                        Direct / acquired plant
                      </a>
                      <a
                        className="button-link button--secondary"
                        href={`#/plants?action=create&identity=${identity.id}&kind=group`}
                      >
                        Direct / acquired plant group
                      </a>
                    </div>
                  </section>
                  <h3>From a sowing</h3>
                  {counts.sowings.length > 0 && (
                    <div className="source-choice-grid">
                      {counts.sowings.map((sowing) => (
                        <article className="source-choice" key={sowing.id}>
                          <p>
                            <strong>
                              {sowing.label ?? "Unlabelled sowing"}
                            </strong>{" "}
                            · {sowing.lifecycle}
                          </p>
                          <p>
                            From{" "}
                            {sowing.seed_lot.label ?? "unlabelled seed lot"}
                          </p>
                          <div className="actions">
                            <a
                              href={`#/plants?action=from-sowing&sowing=${sowing.id}&kind=plant`}
                            >
                              Create plant
                            </a>
                            <a
                              href={`#/plants?action=from-sowing&sowing=${sowing.id}&kind=group`}
                            >
                              Create plant group
                            </a>
                          </div>
                        </article>
                      ))}
                    </div>
                  )}
                  {counts.sowings.length === 0 && (
                    <div className="empty-state">
                      <p>
                        No source sowings are recorded yet. Start from a seed
                        lot to preserve propagation lineage.
                      </p>
                    </div>
                  )}
                  <h3>Plants and plant groups</h3>
                  {counts.plants.length + counts.plant_groups.length ? (
                    <div className="card-grid">
                      {counts.plants.map((plant) => (
                        <CollectionCard
                          key={plant.id}
                          eyebrow="Plant"
                          href={`#/plants/${plant.id}`}
                          title={
                            plant.label ??
                            plant.botanical_identity.display_label
                          }
                        >
                          <span className="record-state">
                            {plant.lifecycle}
                          </span>
                          <p>
                            {plant.location?.display_path ??
                              "Location not recorded"}
                          </p>
                        </CollectionCard>
                      ))}
                      {counts.plant_groups.map((group) => (
                        <CollectionCard
                          key={group.id}
                          eyebrow="Plant group"
                          href={`#/plant-groups/${group.id}`}
                          title={
                            group.label ??
                            group.botanical_identity.display_label
                          }
                        >
                          <span className="record-state">
                            {group.lifecycle}
                          </span>
                          <p>
                            {group.location?.display_path ??
                              "Location not recorded"}
                          </p>
                        </CollectionCard>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-state">
                      <p>No plants or plant groups use this identity.</p>
                    </div>
                  )}
                </div>
              )}
            </section>
          )}
          {counts && tab === "events" && (
            <div
              id="panel-events"
              className="detail-tab-panel"
              role="tabpanel"
              aria-labelledby="tab-events"
            >
              {counts.events.length ? (
                <EventFeed events={counts.events} />
              ) : (
                <div className="empty-state">
                  <p>
                    No events belong to plants or plant groups with this
                    identity.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
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
  const directoryRef = useRef<HTMLUListElement>(null);
  const previousDetail = useRef(initialId);
  useEffect(() => {
    if (previousDetail.current && !initialId)
      directoryRef.current
        ?.querySelector<HTMLButtonElement>('[aria-pressed="true"]')
        ?.focus();
    previousDetail.current = initialId;
  }, [initialId]);
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
  const dismissCreation = () => {
    if (pending) return;
    formRef.current?.reset();
    setCreateState({ status: "idle" });
    closeCreation();
  };

  useEffect(() => {
    const controller = new AbortController();
    void listBotanicalIdentities(controller.signal)
      .then((value: unknown) => {
        if (!Array.isArray(value))
          throw new Error("Invalid identity directory response");
        const identities = value as BotanicalIdentityResponse[];
        setDirectory({ status: "ready", identities });
        setSelected(
          (previous) =>
            identities.find(({ id }) => id === previous?.id) ?? null,
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

  const fieldError = (label: string) =>
    createState.status === "validation"
      ? createState.messages.find((message) => message.startsWith(label))
      : undefined;

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
    window.location.hash = "/identities";
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
      if (window.matchMedia("(max-width: 68rem)").matches)
        window.location.hash = `/identities/${identity.id}`;
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

  const detail =
    directory.status === "ready"
      ? directory.identities.find(({ id }) => id === initialId)
      : null;
  if (initialId)
    return (
      <section
        className="identity-reference-page"
        aria-label="Botanical identity detail"
      >
        {directory.status === "loading" ? (
          <p role="status">Loading botanical identity…</p>
        ) : directory.status === "error" ? (
          <div role="alert">
            <p>Florabase could not load this botanical identity.</p>
            <button
              onClick={() => {
                setDirectory({ status: "loading" });
                setLoadAttempt((n) => n + 1);
              }}
            >
              Retry
            </button>
          </div>
        ) : detail ? (
          <IdentityDetails
            key={`${detail.id}:${initialTab ?? "overview"}`}
            identity={detail}
            csrfToken={csrfToken}
            initialTab={initialTab}
            onSaved={refreshAndSelect}
            onDeleted={removeSelected}
          />
        ) : (
          <div className="empty-state">
            <h2>Botanical identity not found</h2>
            <a href="#/identities">Back to botanical identities</a>
          </div>
        )}
      </section>
    );

  return (
    <section
      aria-labelledby="botanical-identities-title"
      className="workspace identity-reference-page"
    >
      <PageHeader
        title="Botanical identities"
        titleId="botanical-identities-title"
        description="A botanical index of your collection. Find a name, explore its records, and grow its story."
        actions={
          <button
            type="button"
            ref={creationTriggerRef}
            aria-expanded={creationExpanded}
            aria-haspopup="dialog"
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
        }
      />
      {createState.status === "created" && (
        <p role="status" className="notice notice--success">
          {createState.message}
        </p>
      )}
      <div className="reference-split">
        <div className="directory-column">
          <section
            aria-labelledby="identity-directory-title"
            className="identity-directory"
          >
            <h3 id="identity-directory-title">Identity directory</h3>
            <DirectorySearch
              id="identity-filter"
              label="Search botanical identities"
              placeholder="Search names and cultivars"
              value={filter}
              onChange={setFilter}
              disabled={
                directory.status !== "ready" ||
                directory.identities.length === 0
              }
            />
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
              <ul className="identity-cards" ref={directoryRef}>
                {filteredIdentities.map((identity) => (
                  <li key={identity.id}>
                    <button
                      type="button"
                      className="identity-card"
                      aria-pressed={selected?.id === identity.id}
                      onClick={() => {
                        setSelected(identity);
                        if (window.matchMedia("(max-width: 68rem)").matches)
                          window.location.hash = `/identities/${identity.id}`;
                      }}
                    >
                      <IdentityImage key={identity.id} identity={identity} />
                      <span className="identity-card-copy">
                        <strong>
                          <IdentityName identity={identity} />
                        </strong>
                        {identity.common_name && (
                          <span>{identity.common_name}</span>
                        )}
                        <IdentityCardContext identity={identity} />
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {creationExpanded && (
            <PhotoDialog
              className="identity-create-dialog"
              title="Create a botanical identity"
              onClose={dismissCreation}
            >
              <div
                id="new-botanical-identity-panel"
                className="identity-create-dialog__body"
                ref={creationPanelRef}
              >
                <form
                  aria-busy={createState.status === "submitting"}
                  className="identity-form"
                  ref={formRef}
                  onSubmit={(event) => void submit(event)}
                >
                  <FormSection title="Botanical name">
                    <div className="field field--full">
                      <label htmlFor="scientific-name">Scientific name</label>
                      <input
                        aria-describedby={
                          fieldError("Scientific name")
                            ? "new-identity-help scientific-name-error"
                            : "new-identity-help"
                        }
                        id="scientific-name"
                        aria-invalid={
                          Boolean(fieldError("Scientific name")) || undefined
                        }
                        name="scientific_name"
                        required
                        maxLength={255}
                        disabled={pending}
                      />
                      <FieldHelp id="new-identity-help">
                        This stable collection-local identity can be shared by
                        records without implying that those records share a
                        lineage.
                      </FieldHelp>
                      {fieldError("Scientific name") && (
                        <p id="scientific-name-error" className="field-error">
                          {fieldError("Scientific name")}
                        </p>
                      )}
                    </div>
                    <div className="field">
                      <label htmlFor="cultivar-name">Cultivar</label>
                      <input
                        id="cultivar-name"
                        name="cultivar_name"
                        maxLength={120}
                        aria-invalid={
                          Boolean(fieldError("Cultivar")) || undefined
                        }
                        aria-describedby={
                          fieldError("Cultivar")
                            ? "cultivar-hint cultivar-name-error"
                            : "cultivar-hint"
                        }
                        disabled={pending}
                      />
                      <small id="cultivar-hint">
                        Enter the cultivar without quotation marks.
                      </small>
                      {fieldError("Cultivar") && (
                        <p id="cultivar-name-error" className="field-error">
                          {fieldError("Cultivar")}
                        </p>
                      )}
                    </div>
                    <div className="field">
                      <label htmlFor="common-name">Common name</label>
                      <input
                        id="common-name"
                        aria-invalid={
                          Boolean(fieldError("Common name")) || undefined
                        }
                        aria-describedby={
                          fieldError("Common name")
                            ? "common-name-error"
                            : undefined
                        }
                        name="common_name"
                        maxLength={160}
                        disabled={pending}
                      />
                      {fieldError("Common name") && (
                        <p id="common-name-error" className="field-error">
                          {fieldError("Common name")}
                        </p>
                      )}
                    </div>
                  </FormSection>
                  <FormActions>
                    <button
                      type="button"
                      className="button--secondary"
                      disabled={pending}
                      onClick={dismissCreation}
                    >
                      Cancel
                    </button>
                    <button type="submit" disabled={pending}>
                      {createState.status === "submitting"
                        ? "Creating botanical identity…"
                        : "Create botanical identity"}
                    </button>
                  </FormActions>
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
            </PhotoDialog>
          )}
        </div>

        <QuickPreview>
          {selected ? (
            <>
              <IdentityImage key={selected.id} identity={selected} />
              <h3>
                <IdentityName identity={selected} />
              </h3>
              {selected.common_name && <p>{selected.common_name}</p>}
              <IdentityStats identity={selected} />
              <div className="actions quick-preview-actions">
                <a className="button-link" href={`#/identities/${selected.id}`}>
                  Open details
                </a>
                <a
                  className="button-link button--secondary"
                  href={`#/seeds?action=create&identity=${selected.id}`}
                >
                  Add seed lot
                </a>
                <a href={`#/identities/${selected.id}?tab=edit`}>Edit</a>
              </div>
            </>
          ) : (
            <div className="preview-empty">
              <h3>Select a botanical identity</h3>
              <p>
                A quick look at its name and collection. Open details for its
                full story.
              </p>
            </div>
          )}
        </QuickPreview>
      </div>
    </section>
  );
}
