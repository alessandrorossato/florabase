import { IdentityTaskLink } from "./IdentityTaskLink";
import {
  identitySections,
  identitySection,
  identityAnchor,
  type IdentitySection,
} from "./identitySections";
import { IdentityMaps } from "./IdentityMaps";
import { IdentityMedia } from "./IdentityMedia";
import { identityDirectory } from "./identityNavigation";
import { IdentityReferenceSummary } from "./IdentityReferenceSummary";
import "../components/collection-directory.css";
import { ActionButton, ActionLink } from "../components/Action";
import { IdentitySourceAction } from "./IdentitySourceAction";
import { TaskDialog } from "../components/TaskDialog";
import { EditWorkspace } from "../components/EditWorkspace";
import { useEditRoute } from "../components/useEditRoute";
import "./botanical-identities.css";
import { FieldLabel } from "../components/FieldLabel";
import { DirectoryTools } from "../components/DirectoryTools";
import { DirectoryResults } from "../components/DirectoryResults";
import { SavedViews } from "../saved-views/SavedViews";
import { useDirectoryView } from "../saved-views/useDirectoryView";
import { FormSections } from "../components/FormSections";
import { usePublishRecordIdentities } from "../components/recordPresentation";
import {
  useCallback,
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
import { Breadcrumbs, DetailTabs } from "../components/CollectionUI";
import {
  PageHeader,
  FormSection,
  FormActions,
  DirectorySearch,
  QuickPreview,
  OverflowMenu,
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
import { IdentityTaxonomyPanel } from "../taxonomy/IdentityTaxonomyPanel";
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

function IdentityDetails({
  identity,
  csrfToken,
  initialTab,
  onSaved,
  onDeleted,
  adjacent,
  directoryHref,
}: {
  identity: BotanicalIdentityResponse;
  csrfToken: string;
  directoryHref: string;
  initialTab?: string;
  adjacent: {
    previous?: BotanicalIdentityResponse;
    next?: BotanicalIdentityResponse;
  };
  onSaved: (identity: BotanicalIdentityResponse) => Promise<void>;
  onDeleted: () => Promise<void>;
}) {
  type IdentityTab = IdentitySection;
  const [tab, setTab] = useState<IdentityTab>(() =>
    identitySection(initialTab),
  );
  const [lastRouteTab, setLastRouteTab] = useState(initialTab);
  if (lastRouteTab !== initialTab) {
    setLastRouteTab(initialTab);
    if (initialTab !== "edit") setTab(identitySection(initialTab));
  }
  const [editorSection, setEditorSection] = useState("identity");
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
  const editorContainer = useRef<HTMLElement>(null);
  const sectionStates = useRef<
    Record<string, { dirty: boolean; pending: boolean }>
  >({});
  const profileState = useCallback((dirty: boolean, pending: boolean) => {
    sectionStates.current.profile = { dirty, pending };
  }, []);
  const rangeState = useCallback((dirty: boolean, pending: boolean) => {
    sectionStates.current.range = { dirty, pending };
  }, []);
  const mediaState = useCallback((dirty: boolean, pending: boolean) => {
    sectionStates.current.media = { dirty, pending };
  }, []);
  const [sourceAction, setSourceAction] = useState<"sowing" | "harvest" | null>(
    null,
  );
  const [savedMessage, setSavedMessage] = useState<string | null>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    titleRef.current?.focus({ preventScroll: true });
    window.scrollTo({ top: 0 });
  }, []);
  useEffect(() => {
    if (editing)
      requestAnimationFrame(() =>
        (editorSection === "identity"
          ? editPanel.current?.querySelector<HTMLInputElement>("input")
          : editorContainer.current?.querySelector<HTMLElement>(
              `[data-form-panel="${editorSection}"] textarea, [data-form-panel="${editorSection}"] select, [data-form-panel="${editorSection}"] button`,
            )
        )?.focus(),
      );
  }, [editing, editorSection]);
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

  const isDirty = () =>
    editForm.scientific_name !== identity.scientific_name ||
    editForm.cultivar_name !== (identity.cultivar_name ?? "") ||
    editForm.common_name !== (identity.common_name ?? "") ||
    Object.values(sectionStates.current).some((state) => state.dirty);
  const edit = useEditRoute({
    routeIsEdit: initialTab === "edit",
    canDismiss: () =>
      !saving &&
      !Object.values(sectionStates.current).some((state) => state.pending) &&
      (!isDirty() ||
        window.confirm(
          "Discard unsaved botanical identity changes in all sections?",
        )),
    onDismiss: () => {
      setEditing(false);
      sectionStates.current = {};
      setMutationError(null);
      if (!edit.modal) selectTab(tab);
    },
  });
  useEffect(() => {
    if (!editing) return;
    const warn = (event: BeforeUnloadEvent) => {
      if (
        saving ||
        isDirty() ||
        Object.values(sectionStates.current).some((state) => state.pending)
      )
        event.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => {
      window.removeEventListener("beforeunload", warn);
    };
  });

  useEffect(() => {
    if (
      !["overview", "media", "history"].includes(tab) ||
      loadedCollectionIdentity.current === identity.id
    )
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
      setEditForm({
        scientific_name: updated.scientific_name,
        cultivar_name: updated.cultivar_name ?? "",
        common_name: updated.common_name ?? "",
      });
      setSavedMessage("Botanical identity saved.");
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
          ? "This botanical identity has collection records, a cover image, or retained native-range source evidence and cannot be deleted."
          : "Florabase could not delete this botanical identity.",
      );
      setConfirmDelete(false);
      setDeleting(false);
    }
  }

  const counts = collection.status === "ready" ? collection.value : null;
  useEffect(() => {
    const anchor = identityAnchor(initialTab);
    if (anchor)
      requestAnimationFrame(() =>
        document.getElementById(anchor)?.scrollIntoView({ block: "start" }),
      );
  }, [initialTab, counts]);

  const selectTab = (next: IdentityTab) => {
    setTab(next);
    window.location.hash = `#/identities/${identity.id}?tab=${next}`;
  };
  const openIdentityEditor = (section = "identity") => {
    setEditorSection(section);
    setEditForm({
      scientific_name: identity.scientific_name,
      cultivar_name: identity.cultivar_name ?? "",
      common_name: identity.common_name ?? "",
    });
    setMutationError(null);
    setEditErrors([]);
    setSavedMessage(null);
    setEditing(true);
    edit.open(`#/identities/${identity.id}?tab=edit`);
  };
  const identityActions = (
    <div className="actions identity-header-actions">
      <OverflowMenu label="+ Add to collection" ariaLabel="Add to collection">
        <div className="identity-add-items">
          <IdentityTaskLink
            href={`#/seeds?action=create&identity=${identity.id}`}
          >
            Add seed lot
          </IdentityTaskLink>
          <button
            type="button"
            onClick={() => {
              setSourceAction("sowing");
            }}
          >
            Start sowing
          </button>
          <IdentityTaskLink
            href={`#/plants?action=create&identity=${identity.id}&kind=plant`}
          >
            Add plant
          </IdentityTaskLink>
          <IdentityTaskLink
            href={`#/plants?action=create&identity=${identity.id}&kind=group`}
          >
            Add plant group
          </IdentityTaskLink>
          <button
            type="button"
            onClick={() => {
              setSourceAction("harvest");
            }}
          >
            Record harvest
          </button>
        </div>
      </OverflowMenu>
      <ActionButton
        aria-label="Edit botanical identity"
        icon="edit"
        className="button--secondary"
        ref={editTrigger}
        type="button"
        onClick={() => {
          openIdentityEditor();
        }}
      >
        <span className="identity-edit-label--full">
          Edit botanical identity
        </span>
        <span className="identity-edit-label--short">Edit</span>
      </ActionButton>
    </div>
  );
  return (
    <div
      className={`identity-detail-stack${editing ? " identity-detail-stack--editing" : ""}`}
    >
      <Breadcrumbs
        items={[
          { label: "Botanical identities", href: directoryHref },
          { label: identity.display_label },
        ]}
      />
      {!(editing && !edit.modal) && (
        <nav
          aria-label="Adjacent botanical identities"
          className="identity-record-navigation"
        >
          {adjacent.previous ? (
            <a
              title={adjacent.previous.display_label}
              aria-label={`Previous identity: ${adjacent.previous.display_label}`}
              href={`#/identities/${adjacent.previous.id}?tab=${tab}`}
            >
              ← Previous{" "}
              <span className="identity-record-navigation__name">
                · <IdentityName identity={adjacent.previous} />
              </span>
            </a>
          ) : (
            <span />
          )}
          {adjacent.next && (
            <a
              title={adjacent.next.display_label}
              aria-label={`Next identity: ${adjacent.next.display_label}`}
              href={`#/identities/${adjacent.next.id}?tab=${tab}`}
            >
              Next →{" "}
              <span className="identity-record-navigation__name">
                · <IdentityName identity={adjacent.next} />
              </span>
            </a>
          )}
        </nav>
      )}
      {sourceAction && (
        <IdentitySourceAction
          key={sourceAction}
          identityId={identity.id}
          kind={sourceAction}
          dialogOnly
          onDismiss={() => {
            setSourceAction(null);
          }}
        />
      )}
      <div className="identity-detail-layout">
        {tab === "overview" && !(editing && !edit.modal) ? (
          <section
            className="identity-summary"
            aria-labelledby="identity-summary-title"
          >
            <div className="identity-summary-row">
              <a
                className="identity-header-visual"
                href={`#/identities/${identity.id}?tab=media`}
                aria-label="View identity media"
              >
                <IdentityImage identity={identity} />
              </a>
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

                {!(editing && !edit.modal) && identityActions}
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
            {!(editing && !edit.modal) && identityActions}
          </section>
        )}
        <div className="identity-detail-main">
          {mutationError && !editing && (
            <div className="notice notice--error" role="alert">
              {mutationError}
            </div>
          )}
          {editing && (
            <EditWorkspace
              modal={edit.modal}
              title="Edit botanical identity"
              onClose={() => {
                edit.close();
              }}
              returnFocusTo={editTrigger}
            >
              <section
                className="identity-editor"
                ref={editorContainer}
                aria-label={`Edit botanical identity: ${identity.display_label}`}
              >
                <div className="identity-editor-heading">
                  <div>
                    <p
                      className="identity-editor-context"
                      title={identity.display_label}
                    >
                      Editing · <IdentityName identity={identity} />
                    </p>
                    <h3>Edit botanical identity</h3>
                  </div>
                  <button
                    type="button"
                    className="button--secondary"
                    disabled={saving}
                    onClick={() => {
                      edit.close();
                    }}
                  >
                    Close editor
                  </button>
                </div>
                {mutationError && (
                  <div className="notice notice--error" role="alert">
                    {mutationError}
                  </div>
                )}
                {savedMessage && <p role="status">{savedMessage}</p>}
                <p className="field-help">
                  Each section keeps its own existing save action. Switching
                  sections preserves your unsaved values.
                </p>
                <FormSections
                  initialPanelId={editorSection}
                  mode="edit"
                  error={
                    editErrors.length ? { messages: editErrors } : undefined
                  }
                  errorFields={[
                    {
                      match: /scientific name/i,
                      selector: "#edit-scientific-name",
                    },
                    { match: /cultivar/i, selector: "#edit-cultivar-name" },
                    { match: /common name/i, selector: "#edit-common-name" },
                  ]}
                  label="Botanical identity edit sections"
                  disabled={saving}
                  panels={[
                    {
                      id: "identity",
                      label: "Identity",
                      content: (
                        <div className="field--full">
                          <form
                            className="identity-form"
                            ref={editPanel}
                            aria-busy={saving}
                            onSubmit={(event) => void saveEdit(event)}
                          >
                            <FormSection title="Botanical name">
                              <div className="field field--full">
                                <FieldLabel
                                  required
                                  htmlFor="edit-scientific-name"
                                >
                                  Scientific name
                                </FieldLabel>
                                <input
                                  aria-invalid={
                                    Boolean(
                                      editFieldError("Scientific name"),
                                    ) || undefined
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
                                    const scientificName =
                                      event.currentTarget.value;
                                    setEditForm((value) => ({
                                      ...value,
                                      scientific_name: scientificName,
                                    }));
                                  }}
                                />
                                <FieldHelp id="edit-identity-help">
                                  This stable collection-local identity can be
                                  shared by records without implying that those
                                  records share a lineage.
                                </FieldHelp>
                                {editFieldError("Scientific name") && (
                                  <p
                                    className="field-error"
                                    id="edit-scientific-name-error"
                                  >
                                    {editFieldError("Scientific name")}
                                  </p>
                                )}
                              </div>
                              <div className="field">
                                <label htmlFor="edit-cultivar-name">
                                  Cultivar
                                </label>
                                <input
                                  id="edit-cultivar-name"
                                  aria-invalid={
                                    Boolean(editFieldError("Cultivar")) ||
                                    undefined
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
                                    const cultivarName =
                                      event.currentTarget.value;
                                    setEditForm((value) => ({
                                      ...value,
                                      cultivar_name: cultivarName,
                                    }));
                                  }}
                                />
                                {editFieldError("Cultivar") && (
                                  <p
                                    className="field-error"
                                    id="edit-cultivar-name-error"
                                  >
                                    {editFieldError("Cultivar")}
                                  </p>
                                )}
                              </div>
                              <div className="field">
                                <label htmlFor="edit-common-name">
                                  Common name
                                </label>
                                <input
                                  id="edit-common-name"
                                  aria-invalid={
                                    Boolean(editFieldError("Common name")) ||
                                    undefined
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
                                    const commonName =
                                      event.currentTarget.value;
                                    setEditForm((value) => ({
                                      ...value,
                                      common_name: commonName,
                                    }));
                                  }}
                                />
                                {editFieldError("Common name") && (
                                  <p
                                    className="field-error"
                                    id="edit-common-name-error"
                                  >
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
                                  setEditForm({
                                    scientific_name: identity.scientific_name,
                                    cultivar_name: identity.cultivar_name ?? "",
                                    common_name: identity.common_name ?? "",
                                  });
                                  setEditErrors([]);
                                  setMutationError(null);
                                }}
                              >
                                Reset identity changes
                              </button>
                              <button type="submit" disabled={saving}>
                                {saving ? "Saving…" : "Save changes"}
                              </button>
                            </FormActions>
                          </form>
                        </div>
                      ),
                    },
                    {
                      id: "reference",
                      label: "Reference",
                      content: (
                        <div className="field--full">
                          <BotanicalProfilePanel
                            identityId={identity.id}
                            includeNativeRange={false}
                            startEditing
                            onEditStateChange={profileState}
                          />
                        </div>
                      ),
                    },
                    {
                      id: "native-range",
                      label: "Native range",
                      content: (
                        <div className="field--full">
                          <BotanicalNativeRangeManager
                            identityId={identity.id}
                            onEditStateChange={rangeState}
                          />
                        </div>
                      ),
                    },
                    {
                      id: "media",
                      label: "Media",
                      content: (
                        <div className="field--full">
                          <BotanicalIdentityCover
                            csrfToken={csrfToken}
                            onEditStateChange={mediaState}
                            identityId={identity.id}
                            identityLabel={identity.display_label}
                          />
                        </div>
                      ),
                    },
                  ]}
                  cancel={null}
                  submit={null}
                />
              </section>
            </EditWorkspace>
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
                  className="button--secondary"
                  type="button"
                  disabled={deleting}
                  onClick={() => {
                    setConfirmDelete(false);
                  }}
                >
                  Cancel
                </button>
                <button
                  className="button--danger"
                  disabled={deleting}
                  type="button"
                  onClick={() => void removeIdentity()}
                >
                  {deleting ? "Deleting…" : "Delete botanical identity"}
                </button>
              </div>
            </PhotoDialog>
          )}
          {!editing && (
            <div className="identity-detail-tabs">
              <DetailTabs
                tabs={identitySections.map((id) => ({
                  id,
                  label: id[0].toUpperCase() + id.slice(1),
                }))}
                selected={tab}
                onSelect={selectTab}
              />
            </div>
          )}
          {!editing && (
            <>
              {["overview", "history", "media"].includes(tab) &&
                collection.status === "loading" && (
                  <p role="status">Loading collection context…</p>
                )}
              {["overview", "history", "media"].includes(tab) &&
                collection.status === "error" && (
                  <div className="notice notice--error" role="alert">
                    <p>
                      Florabase could not load this identity’s collection
                      context.
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
                  <section
                    className="identity-linked-records"
                    id="identity-footprint"
                    aria-label="Linked collection records"
                  >
                    <h3>Collection footprint</h3>
                    <div className="identity-hub-counts">
                      {counts &&
                        [
                          {
                            kind: "seeds" as const,
                            label: "Seed lots",
                            records: counts.seed_lots,
                          },
                          {
                            kind: "sowings" as const,
                            label: "Sowings",
                            records: counts.sowings,
                          },
                          {
                            kind: "plants" as const,
                            label: "Plants",
                            records: counts.plants,
                          },
                          {
                            kind: "groups" as const,
                            label: "Plant groups",
                            records: counts.plant_groups,
                          },
                          {
                            kind: "harvests" as const,
                            label: "Harvests",
                            records: counts.harvests,
                          },
                        ].map(({ kind, label, records }) => {
                          const active =
                            kind === "harvests"
                              ? null
                              : records.filter(
                                  (r) =>
                                    "lifecycle" in r &&
                                    r.lifecycle === "active",
                                ).length;
                          return (
                            <a
                              key={kind}
                              href={identityDirectory(kind, identity.id)}
                              aria-label={`View all ${label}: ${String(records.length)} recorded${active === null ? "" : `, ${String(active)} active`}`}
                            >
                              <strong>{records.length}</strong> {label}
                              {active !== null && (
                                <small>{active} active</small>
                              )}
                            </a>
                          );
                        })}
                    </div>
                    <p className="field-help">
                      Counts are records, including history. Plant groups are
                      separate; harvests do not indicate stored remainder.
                    </p>
                  </section>
                  <div className="identity-overview-facts">
                    <IdentityReferenceSummary id={identity.id} />
                    <IdentityTaxonomyPanel
                      key={`taxonomy-${identity.id}`}
                      identityId={identity.id}
                      updatedAt={identity.updated_at}
                      summary
                    />
                  </div>
                  {counts?.events.length === 0 && (
                    <section className="identity-recent-history">
                      <h3>Recent history</h3>
                      <p>
                        No events recorded for linked Plants or Plant groups.
                      </p>
                    </section>
                  )}
                  {counts && counts.events.length > 0 && (
                    <section className="identity-recent-history">
                      <h3>Recent history</h3>
                      <EventFeed
                        compact
                        journal
                        identityContextId={identity.id}
                        events={counts.events.slice(0, 4)}
                      />
                      <a href={`#/identities/${identity.id}?tab=history`}>
                        View full history
                      </a>
                    </section>
                  )}
                  {counts && (
                    <section
                      className="identity-next-action identity-hub-section"
                      aria-label="Suggested next action"
                    >
                      <h3>Next step</h3>
                      {counts.seed_lots.some(
                        (lot) => lot.lifecycle === "active",
                      ) ? (
                        <>
                          <p>
                            Active seed material is available. Choose the actual
                            packet when starting a sowing.
                          </p>
                          <IdentitySourceAction
                            identityId={identity.id}
                            kind="sowing"
                          />
                        </>
                      ) : counts.plants.length + counts.plant_groups.length >
                        0 ? (
                        <>
                          <p>
                            Record harvested material against its actual Plant
                            or Plant group.
                          </p>
                          <IdentitySourceAction
                            identityId={identity.id}
                            kind="harvest"
                          />
                        </>
                      ) : (
                        <>
                          <p>
                            Add seed material, or use Add to collection to
                            record a directly acquired Plant or Plant group.
                          </p>
                          <IdentityTaskLink
                            className="button-link button--secondary"
                            href={`#/seeds?action=create&identity=${identity.id}`}
                          >
                            Add seed lot
                          </IdentityTaskLink>
                        </>
                      )}
                    </section>
                  )}
                  <details className="identity-record-metadata">
                    <summary>Record metadata</summary>
                    <dl>
                      <dt>Created</dt>
                      <dd>{new Date(identity.created_at).toLocaleString()}</dd>
                      <dt>Last updated</dt>
                      <dd>{new Date(identity.updated_at).toLocaleString()}</dd>
                    </dl>
                  </details>
                  <section
                    className="identity-danger-zone"
                    aria-labelledby="identity-danger-title"
                  >
                    <div>
                      <h3 id="identity-danger-title">Danger zone</h3>
                      <p>
                        Only an unused identity can be deleted. Collection
                        records, cover media and retained native-range source
                        evidence can block deletion. Linked records are never
                        deleted.
                      </p>
                    </div>
                    <button
                      type="button"
                      className="button--secondary button--danger"
                      onClick={() => {
                        setMutationError(null);
                        setConfirmDelete(true);
                      }}
                    >
                      Delete botanical identity
                    </button>
                  </section>
                </div>
              )}
              {tab === "reference" && (
                <section
                  id="panel-reference"
                  className="detail-tab-panel identity-text-reference"
                  role="tabpanel"
                  aria-labelledby="tab-reference"
                >
                  <BotanicalProfilePanel
                    identityId={identity.id}
                    includeNativeRange={false}
                    onEditRequest={() => {
                      openIdentityEditor("reference");
                    }}
                  />
                </section>
              )}
              {tab === "taxonomy" && (
                <section
                  id="panel-taxonomy"
                  className="detail-tab-panel identity-taxonomy"
                  role="tabpanel"
                  aria-labelledby="tab-taxonomy"
                >
                  <p className="field-help">
                    The local Botanical Identity remains your stable collection
                    name. External classifications are linked references, with
                    their own source and confirmation.
                  </p>
                  <IdentityTaxonomyPanel
                    identityId={identity.id}
                    updatedAt={identity.updated_at}
                  />
                  <section id="identity-source">
                    <ExternalBotanicalDataPanel
                      identityId={identity.id}
                      csrfToken={csrfToken}
                      scientificName={identity.scientific_name}
                      view="source"
                    />
                  </section>
                </section>
              )}
              {tab === "maps" && (
                <section
                  id="panel-maps"
                  className="detail-tab-panel"
                  role="tabpanel"
                  aria-labelledby="tab-maps"
                >
                  <IdentityMaps
                    identity={identity}
                    csrfToken={csrfToken}
                    onEditRange={() => {
                      openIdentityEditor("native-range");
                    }}
                  />
                </section>
              )}
              {tab === "media" && (
                <section
                  id="panel-media"
                  className="detail-tab-panel"
                  role="tabpanel"
                  aria-labelledby="tab-media"
                >
                  <IdentityMedia
                    identity={identity}
                    csrfToken={csrfToken}
                    collection={counts}
                  />
                </section>
              )}
              {counts && tab === "history" && (
                <div
                  id="panel-history"
                  className="detail-tab-panel"
                  role="tabpanel"
                  aria-labelledby="tab-history"
                >
                  <h3>Recorded history</h3>
                  <p>
                    Observations and operational facts, including Harvests, from
                    linked Plants and Plant groups. Dates retain their recorded
                    precision.
                  </p>
                  <p className="field-help">
                    Sowing and germination records remain in their source
                    directories. This view does not infer earlier lifecycle
                    facts from current state or include planned work.
                  </p>
                  <div className="actions">
                    <a href={identityDirectory("sowings", identity.id)}>
                      View all Sowings
                    </a>
                    <a href={identityDirectory("harvests", identity.id)}>
                      View all Harvests
                    </a>
                  </div>
                  {counts.events.length ? (
                    <EventFeed
                      journal
                      identityContextId={identity.id}
                      expandNotes
                      events={counts.events}
                    />
                  ) : (
                    <div className="detail-empty-message">
                      <p>
                        No events belong to plants or plant groups with this
                        identity.
                      </p>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export function BotanicalIdentityScreen({
  initialId,
  initialTab,
  startCreating = false,
}: { initialId?: string; initialTab?: string; startCreating?: boolean } = {}) {
  const auth = useAuth();
  const [narrowPreview, setNarrowPreview] = useState(false);
  const [directory, setDirectory] = useState<DirectoryState>({
    status: "loading",
  });
  usePublishRecordIdentities(
    directory.status === "ready" ? directory.identities : undefined,
  );
  const [selected, setSelected] = useState<BotanicalIdentityResponse | null>(
    null,
  );
  const view = useDirectoryView("botanical_identities", () => {
    setSelected(null);
  });
  const filter = view.state.q;
  const setFilter = (value: string) => {
    view.update("q", value);
  };

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
  const dashboardCreationStarted = useRef(false);
  useEffect(() => {
    if (
      !startCreating ||
      directory.status !== "ready" ||
      dashboardCreationStarted.current
    )
      return;
    dashboardCreationStarted.current = true;
    formRef.current?.reset();
    setCreateState({ status: "idle" });
    openCreation();
  }, [directory.status, openCreation, startCreating]);
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
        className="workspace identity-reference-page"
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
            key={detail.id}
            identity={detail}
            directoryHref={`#/identities${filter ? `?q=${encodeURIComponent(filter)}` : ""}`}
            adjacent={{
              previous:
                directory.identities[
                  directory.identities.findIndex(({ id }) => id === detail.id) -
                    1
                ],
              next: directory.identities[
                directory.identities.findIndex(({ id }) => id === detail.id) + 1
              ],
            }}
            csrfToken={csrfToken}
            initialTab={initialTab}
            onSaved={refreshAndSelect}
            onDeleted={removeSelected}
          />
        ) : (
          <div className="empty-state">
            <h2>Botanical identity not found</h2>
            <ActionLink icon="back" href="#/identities">
              Back to botanical identities
            </ActionLink>
          </div>
        )}
      </section>
    );

  const preview = (
    <QuickPreview>
      {selected ? (
        <>
          <IdentityImage key={selected.id} identity={selected} />
          <h3>
            <IdentityName identity={selected} />
          </h3>
          {selected.common_name && <p>{selected.common_name}</p>}
          <IdentityStats identity={selected} />
          <div className="identity-preview-actions">
            <a className="button-link" href={`#/identities/${selected.id}`}>
              Open details
            </a>
            <div
              className="preview-action-group"
              role="group"
              aria-label="Record maintenance"
            >
              <ActionLink
                icon="edit"
                className="button-link button--secondary"
                href={`#/identities/${selected.id}?tab=edit`}
              >
                Edit
              </ActionLink>
            </div>
            <div
              className="identity-preview-creation"
              role="group"
              aria-label="Collection creation"
            >
              <a
                className="button-link button--secondary"
                href={`#/seeds?action=create&identity=${selected.id}`}
              >
                Add seed lot
              </a>
              <a
                className="button-link button--secondary"
                href={`#/plants?action=create&identity=${selected.id}&kind=plant`}
              >
                Add plant
              </a>
              <IdentitySourceAction
                key={`sowing-${selected.id}`}
                identityId={selected.id}
                kind="sowing"
              />
              <IdentitySourceAction
                key={`harvest-${selected.id}`}
                identityId={selected.id}
                kind="harvest"
              />
            </div>
          </div>
        </>
      ) : (
        <div className="preview-empty">
          <h3>Select a botanical identity</h3>
          <p>
            A quick look at its name and collection. Open details for its full
            story.
          </p>
        </div>
      )}
    </QuickPreview>
  );

  return (
    <section
      aria-labelledby="botanical-identities-title"
      className="workspace identity-reference-page"
    >
      <PageHeader
        title="Botanical identities"
        titleId="botanical-identities-title"
        eyebrow="Explore"
        description="Manage the botanical identities that connect collection records and reference data."
        tools={
          <DirectoryTools
            name="Botanical identities"
            search={
              <DirectorySearch
                hideLabel
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
            }
            savedViews={
              <SavedViews
                presentation="dialog"
                surface="botanical_identities"
                state={view.savedState}
              />
            }
            actions={
              <ActionButton
                icon="add"
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
                New botanical identity
              </ActionButton>
            }
          />
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
            <h3 className="sr-only" id="identity-directory-title">
              Identity directory
            </h3>

            {directory.status === "ready" && (
              <DirectoryResults count={filteredIdentities.length} />
            )}
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
              <ul
                className="identity-cards"
                ref={directoryRef}
                aria-label="Botanical identities"
                tabIndex={0}
              >
                {filteredIdentities.map((identity) => (
                  <li key={identity.id}>
                    <button
                      type="button"
                      className="identity-card"
                      aria-pressed={selected?.id === identity.id}
                      onClick={() => {
                        setSelected(identity);
                        setNarrowPreview(
                          window.matchMedia("(max-width: 68rem)").matches,
                        );
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
                      <FieldLabel required htmlFor="scientific-name">
                        Scientific name
                      </FieldLabel>
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

        {narrowPreview && selected ? (
          <TaskDialog
            title="Botanical identity preview"
            className="identity-preview-dialog"
            onClose={() => {
              setNarrowPreview(false);
            }}
          >
            <button
              type="button"
              className="button--secondary"
              onClick={() => {
                setNarrowPreview(false);
              }}
            >
              Close preview
            </button>
            {preview}
          </TaskDialog>
        ) : (
          preview
        )}
      </div>
    </section>
  );
}
