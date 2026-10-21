import "../components/collection-page.css";
import "../components/collection-directory.css";
import "../components/collection-visual.css";
import "../components/directory-preview.css";
import "./supplier-refinement.css";
import { useCollectionPageReturnFocus } from "../components/useCollectionPageReturnFocus";
import { FieldLabel } from "../components/FieldLabel";
import { DirectoryTools } from "../components/DirectoryTools";
import { DirectoryResults } from "../components/DirectoryResults";
import { FormSections } from "../components/FormSections";
import { EditWorkspace } from "../components/EditWorkspace";
import { DetailEmptyState } from "../components/DetailEmptyState";
import { useEditRoute } from "../components/useEditRoute";
import { SavedViews } from "../saved-views/SavedViews";
import { useDirectoryView } from "../saved-views/useDirectoryView";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type MouseEventHandler,
  type RefObject,
  type SyntheticEvent,
} from "react";

import { PhotosSection } from "../photos/PhotosSection";
import { RecordVisual } from "../photos/RecordVisual";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { useCreationDisclosure } from "../components/useCreationDisclosure";
import {
  OverflowMenu,
  DirectorySearch,
  RecordPreview,
} from "../components/ReferenceUI";
import {
  Breadcrumbs,
  CollectionCard,
  DetailContext,
  DetailHeader,
  DetailTabs,
  WorkspaceIntro,
} from "../components/CollectionUI";
import {
  setRecordRoute,
  openCollectionPage,
  closeCollectionPage,
} from "../components/recordNavigation";
import {
  createSupplier,
  getSupplier,
  listSuppliers,
  setSupplierRetired,
  supplierValidationMessages,
  updateSupplier,
  type SupplierCreate,
  type SupplierDetailResponse,
  type SupplierListResponse,
  type SupplierResponse,
  type SupplierUpdate,
} from "./api";

type DirectoryState =
  | { status: "loading" }
  | { status: "ready"; suppliers: SupplierListResponse[] }
  | { status: "error" };
type DetailState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; supplier: SupplierDetailResponse }
  | { status: "error" };
type SaveState =
  | { status: "idle" }
  | { status: "saving" }
  | { status: "success"; message: string }
  | { status: "error"; messages: string[] };

interface SupplierFormState {
  name: string;
  kind: SupplierCreate["kind"];
  website: string;
  email: string;
  phone: string;
  notes: string;
}

type SupplierRecord = SupplierResponse | SupplierDetailResponse;

const supplierPage = {
  eyebrow: "Sourcing",
  title: "Suppliers",
  titleId: "suppliers-title",
  description:
    "Manage the sources from which collection material was directly acquired.",
};

const kindLabels: Record<SupplierResponse["kind"], string> = {
  seller: "Seller",
  nursery: "Nursery",
  supermarket: "Supermarket",
  person: "Person",
  exchange: "Exchange",
  other: "Other",
};

const lifecycleLabels: Record<string, string> = {
  active: "Active",
  exhausted: "Exhausted",
  discarded: "Discarded",
  lost: "Lost",
  transferred: "Transferred",
  completed: "Completed",
  dead: "Dead",
  reversed: "Reversed",
  reintegrated: "Reintegrated",
};

function dateLabel(
  date: {
    precision: string;
    year: number;
    month?: number | null;
    day?: number | null;
  } | null,
): string {
  if (!date) return "Date not recorded";
  const year = String(date.year).padStart(4, "0");
  if (date.precision === "year") return year;
  const month = String(date.month).padStart(2, "0");
  if (date.precision === "month") return `${year}-${month}`;
  return `${year}-${month}-${String(date.day).padStart(2, "0")}`;
}

function recordTitle(record: {
  label: string | null;
  botanical_identity: { display_label: string };
}): string {
  return record.label ?? record.botanical_identity.display_label;
}

function contactChannels(supplier: {
  website: string | null;
  email: string | null;
  phone: string | null;
}): string {
  const channels: string[] = [];
  if (supplier.website) channels.push("Website");
  if (supplier.email) channels.push("Email");
  if (supplier.phone) channels.push("Phone");
  return channels.length > 0 ? channels.join(" · ") : "Not recorded";
}

function blankSupplierForm(): SupplierFormState {
  return {
    name: "",
    kind: "seller",
    website: "",
    email: "",
    phone: "",
    notes: "",
  };
}

function supplierFormFrom(supplier: SupplierRecord): SupplierFormState {
  return {
    name: supplier.name,
    kind: supplier.kind,
    website: supplier.website ?? "",
    email: supplier.email ?? "",
    phone: supplier.phone ?? "",
    notes: supplier.notes ?? "",
  };
}

function supplierPayloadFrom(form: SupplierFormState): SupplierCreate {
  return {
    name: form.name,
    kind: form.kind,
    ...(form.website ? { website: form.website } : {}),
    ...(form.email ? { email: form.email } : {}),
    ...(form.phone ? { phone: form.phone } : {}),
    ...(form.notes ? { notes: form.notes } : {}),
  };
}

function SupplierEssentialsFields({
  form,
  disabled,
  onChange,
}: {
  form: SupplierFormState;
  disabled: boolean;
  onChange: (patch: Partial<SupplierFormState>) => void;
}) {
  return (
    <>
      <div className="field">
        <FieldLabel required htmlFor="supplier-name">
          Name
        </FieldLabel>
        <input
          id="supplier-name"
          name="name"
          required
          maxLength={255}
          disabled={disabled}
          value={form.name}
          onChange={(event) => {
            onChange({ name: event.currentTarget.value });
          }}
        />
      </div>
      <div className="field">
        <FieldLabel required htmlFor="supplier-kind">
          Kind
        </FieldLabel>
        <select
          id="supplier-kind"
          name="kind"
          required
          disabled={disabled}
          value={form.kind}
          onChange={(event) => {
            onChange({
              kind: event.currentTarget.value as SupplierFormState["kind"],
            });
          }}
        >
          {Object.entries(kindLabels).map(([value, label]) => (
            <option value={value} key={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
    </>
  );
}

function SupplierContactFields({
  form,
  disabled,
  onChange,
}: {
  form: SupplierFormState;
  disabled: boolean;
  onChange: (patch: Partial<SupplierFormState>) => void;
}) {
  return (
    <>
      <div className="field">
        <label htmlFor="supplier-website">Website</label>
        <input
          id="supplier-website"
          name="website"
          type="url"
          maxLength={2048}
          disabled={disabled}
          value={form.website}
          onChange={(event) => {
            onChange({ website: event.currentTarget.value });
          }}
        />
      </div>
      <div className="field">
        <label htmlFor="supplier-email">Email</label>
        <input
          id="supplier-email"
          name="email"
          type="email"
          maxLength={320}
          disabled={disabled}
          value={form.email}
          onChange={(event) => {
            onChange({ email: event.currentTarget.value });
          }}
        />
      </div>
      <div className="field">
        <label htmlFor="supplier-phone">Phone</label>
        <input
          id="supplier-phone"
          name="phone"
          type="tel"
          maxLength={120}
          disabled={disabled}
          value={form.phone}
          onChange={(event) => {
            onChange({ phone: event.currentTarget.value });
          }}
        />
      </div>
      <div className="field">
        <label htmlFor="supplier-notes">Notes</label>
        <textarea
          id="supplier-notes"
          name="notes"
          maxLength={20000}
          rows={4}
          disabled={disabled}
          value={form.notes}
          onChange={(event) => {
            onChange({ notes: event.currentTarget.value });
          }}
        />
      </div>
    </>
  );
}

function SupplierPreview({
  supplier,
  onOpen,
  onEdit,
}: {
  supplier: SupplierListResponse;
  onOpen: () => void;
  onEdit: MouseEventHandler<HTMLButtonElement>;
}) {
  return (
    <RecordPreview
      visual={
        <RecordVisual
          photo={supplier.primary_photo ?? null}
          label={supplier.name}
          kind="supplier"
          className="quick-preview-media"
        />
      }
      type="Supplier"
      title={supplier.name}
      secondary={kindLabels[supplier.kind]}
      facts={[
        { label: "State", value: supplier.retired_at ? "Retired" : "Active" },
        {
          label: "Direct records",
          value: String(supplier.usage_counts.direct_records_total),
        },
        {
          label: "Seed lots",
          value: String(supplier.usage_counts.seed_lots_total),
        },
        { label: "Contact", value: contactChannels(supplier) },
      ]}
      actions={
        <>
          <a
            className="button-link"
            href={`#/suppliers/${supplier.id}`}
            onClick={onOpen}
          >
            Open details
          </a>
          <div
            className="preview-action-group"
            role="group"
            aria-label="Supplier actions"
          >
            <button
              className="button--secondary"
              type="button"
              data-supplier-preview-edit
              onClick={onEdit}
            >
              Edit
            </button>
          </div>
        </>
      }
    />
  );
}

function SupplierDetail({
  supplier,
  csrfToken,
  initialTab,
  headingRef,
  onEdit,
  onLifecycle,
}: {
  supplier: SupplierDetailResponse;
  csrfToken: string;
  initialTab?: string;
  headingRef?: RefObject<HTMLHeadingElement | null>;
  onEdit: MouseEventHandler<HTMLButtonElement>;
  onLifecycle: (
    action: () => Promise<SupplierResponse>,
    success: (value: SupplierResponse) => string,
  ) => void;
}) {
  const [tab, setTab] = useState(
    initialTab && ["overview", "photos", "material"].includes(initialTab)
      ? initialTab
      : "overview",
  );
  const [primaryPhoto, setPrimaryPhoto] = useState(supplier.primary_photo);
  const counts = supplier.usage_counts;
  const linkedTotal = counts.direct_records_total;
  const hasContact = Boolean(
    supplier.website ?? supplier.email ?? supplier.phone,
  );
  return (
    <article
      aria-label="Supplier detail"
      className="supplier-detail collection-detail"
    >
      <Breadcrumbs
        items={[
          { label: "Sourcing", href: "#/dashboard" },
          { label: "Suppliers", href: "#/suppliers" },
          { label: supplier.name },
        ]}
      />
      <DetailHeader
        headingRef={headingRef}
        visual={
          <div className="collection-primary-detail">
            <RecordVisual
              kind="supplier"
              label={supplier.name}
              photo={primaryPhoto ?? null}
            />
          </div>
        }
        eyebrow="Supplier"
        title={supplier.name}
        secondary={<span>{kindLabels[supplier.kind]}</span>}
        status={
          <span
            className={`lifecycle-badge lifecycle-badge--${supplier.retired_at ? "retired" : "active"}`}
          >
            {supplier.retired_at ? "Retired" : "Active"}
          </span>
        }
        editLabel="Edit supplier"
        onEdit={onEdit}
        overflow={
          <OverflowMenu ariaLabel="More supplier actions">
            <button
              className="button--secondary"
              type="button"
              onClick={() => {
                onLifecycle(
                  () =>
                    setSupplierRetired(
                      supplier.id,
                      !supplier.retired_at,
                      csrfToken,
                    ),
                  (value) =>
                    value.retired_at
                      ? `${value.name} was retired. Historical links are preserved.`
                      : `${value.name} was reactivated.`,
                );
              }}
            >
              {supplier.retired_at ? "Reactivate supplier" : "Retire supplier"}
            </button>
          </OverflowMenu>
        }
      />
      {supplier.retired_at && (
        <p className="record-empty">
          This supplier is retired. Existing acquisition history remains
          available.
        </p>
      )}
      <DetailTabs
        tabs={[
          { id: "overview", label: "Overview" },
          { id: "photos", label: "Photos" },
          { id: "material", label: `Linked material (${String(linkedTotal)})` },
        ]}
        selected={tab}
        onSelect={(next) => {
          setTab(next);
          window.history.replaceState(
            null,
            "",
            `#/suppliers/${supplier.id}?tab=${next}`,
          );
        }}
      />
      {tab === "overview" && (
        <div
          id="panel-overview"
          className="detail-tab-panel overview-grid supplier-overview collection-overview"
          role="tabpanel"
          aria-labelledby="tab-overview"
        >
          <section
            className="collection-summary"
            aria-labelledby="supplier-summary-title"
          >
            <h4 id="supplier-summary-title">At a glance</h4>
            <dl aria-label="Current Supplier state">
              <div>
                <dt>State</dt>
                <dd>
                  <span
                    className={`lifecycle-badge lifecycle-badge--${supplier.retired_at ? "retired" : "active"}`}
                  >
                    {supplier.retired_at ? "Retired" : "Active"}
                  </span>
                </dd>
              </div>
              <div>
                <dt>Kind</dt>
                <dd>{kindLabels[supplier.kind]}</dd>
              </div>
              <div>
                <dt>Direct records</dt>
                <dd>{counts.direct_records_total}</dd>
              </div>
            </dl>
          </section>
          <section
            className="supplier-fact-group"
            aria-labelledby="supplier-about-title"
          >
            <h4 id="supplier-about-title">About this supplier</h4>
            <dl>
              <div>
                <dt>Kind</dt>
                <dd>{kindLabels[supplier.kind]}</dd>
              </div>
              {supplier.website && (
                <div>
                  <dt>Website</dt>
                  <dd>
                    <a href={supplier.website} target="_blank" rel="noreferrer">
                      Visit supplier website
                    </a>
                  </dd>
                </div>
              )}
              {supplier.email && (
                <div>
                  <dt>Email</dt>
                  <dd>
                    <a href={`mailto:${supplier.email}`}>{supplier.email}</a>
                  </dd>
                </div>
              )}
              {supplier.phone && (
                <div>
                  <dt>Phone</dt>
                  <dd>{supplier.phone}</dd>
                </div>
              )}
              {supplier.notes && (
                <div>
                  <dt>Notes</dt>
                  <dd className="preserve-lines">{supplier.notes}</dd>
                </div>
              )}
            </dl>
            {!hasContact && !supplier.notes && (
              <p className="record-empty">No contact details recorded.</p>
            )}
          </section>
          <section
            className="supplier-fact-group"
            aria-labelledby="supplier-orders-title"
          >
            <h4 id="supplier-orders-title">Orders</h4>
            <p>Purchase transactions recorded for this Supplier.</p>
            <p>
              <a href={`#/orders?supplier_id=${supplier.id}`}>
                View Orders for this Supplier
              </a>
            </p>
          </section>
          <section
            className="supplier-fact-group supplier-overview-wide"
            aria-labelledby="recent-acquisitions-title"
          >
            <h4 id="recent-acquisitions-title">Recent acquisitions</h4>
            {supplier.recent_acquisitions.length === 0 ? (
              <DetailEmptyState>
                No directly linked acquisitions have a recorded acquisition
                date.
              </DetailEmptyState>
            ) : (
              <div className="card-grid">
                {supplier.recent_acquisitions.map((record) => {
                  const route =
                    record.record_type === "seed_lot"
                      ? "seeds"
                      : record.record_type === "plant"
                        ? "plants"
                        : "plant-groups";
                  return (
                    <CollectionCard
                      key={`${record.record_type}:${record.id}`}
                      eyebrow={
                        record.record_type === "seed_lot"
                          ? "SeedLot"
                          : record.record_type === "plant"
                            ? "Plant"
                            : "Plant group"
                      }
                      title={recordTitle(record)}
                      href={`#/${route}/${record.id}`}
                    >
                      <p>
                        <a
                          href={`#/identities/${record.botanical_identity.id}`}
                        >
                          {recordTitle(record) ===
                          record.botanical_identity.display_label
                            ? "View botanical identity"
                            : record.botanical_identity.display_label}
                        </a>
                      </p>
                      <p>
                        Acquired {dateLabel(record.acquired_on)} ·{" "}
                        {lifecycleLabels[record.lifecycle] ?? record.lifecycle}
                      </p>
                    </CollectionCard>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      )}
      {tab === "photos" && (
        <div
          id="panel-photos"
          className="detail-tab-panel"
          role="tabpanel"
          aria-labelledby="tab-photos"
        >
          <PhotosSection
            key={supplier.id}
            presentation="compact"
            target="supplier"
            targetId={supplier.id}
            targetLabel={supplier.name}
            primaryPhoto={primaryPhoto ?? null}
            onPrimaryChanged={setPrimaryPhoto}
          />
        </div>
      )}
      {tab === "material" && (
        <div
          id="panel-material"
          className="detail-tab-panel supplier-material"
          role="tabpanel"
          aria-labelledby="tab-material"
        >
          <section
            className="supplier-fact-group"
            aria-labelledby="supplier-seed-lots-title"
          >
            <h4 id="supplier-seed-lots-title">
              Seed lots ({supplier.seed_lots.length})
            </h4>
            {supplier.seed_lots.length === 0 ? (
              <DetailEmptyState>
                No Seed lots directly reference this supplier.
              </DetailEmptyState>
            ) : (
              <div className="card-grid">
                {supplier.seed_lots.map((record) => (
                  <CollectionCard
                    key={record.id}
                    eyebrow="SeedLot"
                    title={recordTitle(record)}
                    href={`#/seeds/${record.id}`}
                  >
                    <p>
                      <a href={`#/identities/${record.botanical_identity.id}`}>
                        {recordTitle(record) ===
                        record.botanical_identity.display_label
                          ? "View botanical identity"
                          : record.botanical_identity.display_label}
                      </a>
                    </p>
                    <p>
                      Acquired {dateLabel(record.acquisition_date)} ·{" "}
                      {lifecycleLabels[record.lifecycle]}
                    </p>
                  </CollectionCard>
                ))}
              </div>
            )}
          </section>
          <section
            className="supplier-fact-group"
            aria-labelledby="supplier-plants-title"
          >
            <h4 id="supplier-plants-title">
              Plants ({supplier.plants.length + supplier.plant_groups.length})
            </h4>
            {supplier.plants.length + supplier.plant_groups.length === 0 ? (
              <DetailEmptyState>
                No directly acquired Plants or Plant groups reference this
                supplier.
              </DetailEmptyState>
            ) : (
              <div className="card-grid">
                {[
                  ...supplier.plants.map((record) => ({
                    ...record,
                    recordType: "plant" as const,
                  })),
                  ...supplier.plant_groups.map((record) => ({
                    ...record,
                    recordType: "plant_group" as const,
                  })),
                ].map((record) => (
                  <CollectionCard
                    key={`${record.recordType}:${record.id}`}
                    eyebrow={
                      record.recordType === "plant" ? "Plant" : "Plant group"
                    }
                    title={recordTitle(record)}
                    href={`#/${record.recordType === "plant" ? "plants" : "plant-groups"}/${record.id}`}
                  >
                    <p>
                      <a href={`#/identities/${record.botanical_identity.id}`}>
                        {recordTitle(record) ===
                        record.botanical_identity.display_label
                          ? "View botanical identity"
                          : record.botanical_identity.display_label}
                      </a>
                    </p>
                    <p>
                      Collection entry {dateLabel(record.collection_entry_date)}{" "}
                      · {lifecycleLabels[record.lifecycle]}
                    </p>
                  </CollectionCard>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </article>
  );
}

export function SupplierScreen({
  initialId,
  initialTab,
  startCreating = false,
}: { initialId?: string; initialTab?: string; startCreating?: boolean } = {}) {
  const auth = useAuth();
  const [directory, setDirectory] = useState<DirectoryState>({
    status: "loading",
  });
  const [detail, setDetail] = useState<DetailState>(
    initialId ? { status: "loading" } : { status: "idle" },
  );
  const [detailRefresh, setDetailRefresh] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(
    initialId ?? null,
  );
  const [attempt, setAttempt] = useState(0);
  const [editing, setEditing] = useState(false);
  const [target, setTarget] = useState<SupplierRecord | null>(null);
  const [form, setForm] = useState<SupplierFormState>(blankSupplierForm);
  const [save, setSave] = useState<SaveState>({ status: "idle" });
  const view = useDirectoryView("suppliers", () => {
    setSelectedId(null);
    setEditing(false);
    setTarget(null);
  });
  const filter = view.state.q;
  const setFilter = (value: string) => {
    view.update("q", value);
  };
  const feedback = useRef<HTMLParagraphElement>(null);
  const detailHeading = useRef<HTMLHeadingElement>(null);
  const editTrigger = useRef<HTMLButtonElement>(null);
  const editBaseline = useRef(JSON.stringify(blankSupplierForm()));
  const directEditHandled = useRef(false);
  const restorePreviewEdit = useRef(false);
  const restoreDetailHeading = useRef(false);
  const {
    expanded: creationExpanded,
    triggerRef: creationTriggerRef,
    panelRef: creationPanelRef,
    open: openCreation,
    close: closeCreation,
  } = useCreationDisclosure();
  const pending = save.status === "saving";
  const refreshDirectory = () => {
    setAttempt((value) => value + 1);
  };

  const edit = useEditRoute({
    routeIsEdit: initialTab === "edit",
    canDismiss: () => {
      if (pending) return false;
      return (
        JSON.stringify(form) === editBaseline.current ||
        window.confirm("Discard unsaved supplier changes?")
      );
    },
    onDismiss: () => {
      setEditing(false);
      setTarget(null);
      setSave((current) =>
        current.status === "success" ? current : { status: "idle" },
      );
      if (!edit.modal && initialId) {
        if (restorePreviewEdit.current) return;
        restoreDetailHeading.current = true;
        setRecordRoute(`#/suppliers/${initialId}`, true);
      }
    },
  });

  const lastRouteId = useRef(initialId);
  useEffect(() => {
    if (lastRouteId.current === initialId) return;
    lastRouteId.current = initialId;
    if (edit.modal) return;
    const timeout = window.setTimeout(() => {
      setDetail((current) =>
        initialId
          ? current.status === "ready" && current.supplier.id === initialId
            ? current
            : { status: "loading" }
          : { status: "idle" },
      );
      if (initialId) setSelectedId(initialId);
    }, 0);
    return () => {
      window.clearTimeout(timeout);
    };
  }, [initialId, edit.modal]);

  const previousCreateRoute = useRef(startCreating);
  const contextualCreationStarted = useRef(false);
  useEffect(() => {
    if (previousCreateRoute.current && !startCreating && creationExpanded) {
      setEditing(false);
      setTarget(null);
      setSave({ status: "idle" });
      closeCreation();
    }
    previousCreateRoute.current = startCreating;
    if (!startCreating) contextualCreationStarted.current = false;
  }, [startCreating, creationExpanded, closeCreation]);

  useEffect(() => {
    const controller = new AbortController();
    void listSuppliers(controller.signal)
      .then((suppliers) => {
        setDirectory({ status: "ready", suppliers });
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
    if (!initialId) return;
    const controller = new AbortController();
    void getSupplier(initialId, controller.signal)
      .then((supplier) => {
        setDetail({ status: "ready", supplier });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else setDetail({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [auth, detailRefresh, initialId]);

  useEffect(() => {
    if (save.status === "error") feedback.current?.focus();
  }, [save]);

  useEffect(() => {
    if (save.status === "success") detailHeading.current?.focus();
  }, [save]);

  const suppliers = useMemo(
    () => (directory.status === "ready" ? directory.suppliers : []),
    [directory],
  );
  const selected = useMemo(
    () =>
      suppliers.find(({ id }) => id === selectedId) ??
      (detail.status === "ready" && detail.supplier.id === selectedId
        ? detail.supplier
        : null),
    [detail, selectedId, suppliers],
  );
  const visible = useMemo(() => {
    const query = filter.trim().toLocaleLowerCase();
    if (!query) return suppliers;
    return suppliers.filter((supplier) =>
      [supplier.name, supplier.website, supplier.email, supplier.phone].some(
        (value) => value?.toLocaleLowerCase().includes(query),
      ),
    );
  }, [filter, suppliers]);

  useEffect(() => {
    if (
      !startCreating ||
      directory.status !== "ready" ||
      contextualCreationStarted.current
    )
      return;
    contextualCreationStarted.current = true;
    setSelectedId(null);
    setTarget(null);
    setEditing(true);
    setForm(blankSupplierForm());
    editBaseline.current = JSON.stringify(blankSupplierForm());
    setSave({ status: "idle" });
    openCreation();
  }, [directory.status, openCreation, startCreating]);

  useEffect(() => {
    if (initialTab !== "edit") {
      directEditHandled.current = false;
      return;
    }
    if (edit.modal) {
      directEditHandled.current = true;
      return;
    }
    if (directEditHandled.current) return;
    const source =
      detail.status === "ready" && detail.supplier.id === initialId
        ? detail.supplier
        : (suppliers.find(({ id }) => id === initialId) ?? null);
    if (!source) return;
    directEditHandled.current = true;
    const timeout = window.setTimeout(() => {
      const values = supplierFormFrom(source);
      editBaseline.current = JSON.stringify(values);
      setTarget(source);
      setForm(values);
      setEditing(true);
    }, 0);
    return () => {
      window.clearTimeout(timeout);
    };
  }, [detail, edit.modal, initialId, initialTab, suppliers]);

  // Browser Back out of a direct edit URL closes the inline fallback instead of
  // leaving an editor mounted under a non-edit route.
  useEffect(() => {
    if (initialTab === "edit" || edit.modal || !editing || !target) return;
    const timeout = window.setTimeout(() => {
      setEditing(false);
      setTarget(null);
      if (initialId) restoreDetailHeading.current = true;
    }, 0);
    return () => {
      window.clearTimeout(timeout);
    };
  }, [edit.modal, editing, initialId, initialTab, target]);

  // Editing from Quick Preview changes the route, so restore focus once the
  // directory and its preview have rendered again.
  useEffect(() => {
    if (
      initialId ||
      editing ||
      edit.modal ||
      !restorePreviewEdit.current ||
      !selected
    )
      return;
    restorePreviewEdit.current = false;
    const frame = requestAnimationFrame(() => {
      document
        .querySelector<HTMLElement>("[data-supplier-preview-edit]")
        ?.focus();
    });
    return () => {
      cancelAnimationFrame(frame);
    };
  }, [edit.modal, editing, initialId, selected]);

  // A route change can mount the detail after save success; wait for its heading.
  useEffect(() => {
    if (!restoreDetailHeading.current || editing || edit.modal) return;
    if (detail.status !== "ready") return;
    restoreDetailHeading.current = false;
    const frame = requestAnimationFrame(() => {
      detailHeading.current?.focus();
    });
    return () => {
      cancelAnimationFrame(frame);
    };
  }, [detail, edit.modal, editing]);

  useCollectionPageReturnFocus(
    directory.status === "ready" && !editing && !edit.modal,
  );

  if (
    auth.state.status !== "authenticated" &&
    auth.state.status !== "logging-out" &&
    auth.state.status !== "logout-failed"
  )
    return null;
  const csrfToken = auth.state.csrfToken;

  function patchForm(patch: Partial<SupplierFormState>) {
    setForm((current) => ({ ...current, ...patch }));
  }

  async function apply(
    action: () => Promise<SupplierResponse>,
    success: (value: SupplierResponse) => string,
  ) {
    if (pending) return;
    setSave({ status: "saving" });
    try {
      const supplier = await action();
      const refreshed = await listSuppliers();
      setDirectory({ status: "ready", suppliers: refreshed });
      setSelectedId(supplier.id);
      setDetail((current) =>
        current.status === "ready" && current.supplier.id === supplier.id
          ? {
              status: "ready",
              supplier: { ...current.supplier, ...supplier },
            }
          : current,
      );
      if (initialId === supplier.id) setDetailRefresh((value) => value + 1);
      setSave({ status: "success", message: success(supplier) });
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else if (error instanceof ApiError && error.status === 422)
        setSave({
          status: "error",
          messages: supplierValidationMessages(error),
        });
      else if (error instanceof ApiError && error.status === 403)
        setSave({
          status: "error",
          messages: [
            "Florabase could not authorize this change. Refresh the page and try again.",
          ],
        });
      else
        setSave({
          status: "error",
          messages: [
            "Florabase could not save or refresh this supplier. Check the connection and try again.",
          ],
        });
    }
  }

  function startCreate() {
    openCollectionPage("#/suppliers?action=create");
    setSelectedId(null);
    setTarget(null);
    setEditing(true);
    setForm(blankSupplierForm());
    editBaseline.current = JSON.stringify(blankSupplierForm());
    setSave({ status: "idle" });
    openCreation();
  }

  function startEdit(
    supplier: SupplierRecord,
    trigger: HTMLButtonElement | null,
  ) {
    editTrigger.current = trigger;
    directEditHandled.current = true;
    restorePreviewEdit.current = !initialId;
    if (creationExpanded) closeCreation({ returnFocus: false });
    const values = supplierFormFrom(supplier);
    editBaseline.current = JSON.stringify(values);
    setSelectedId(supplier.id);
    setTarget(supplier);
    setForm(values);
    setEditing(true);
    edit.open(`#/suppliers/${supplier.id}?tab=edit`);
    setSave({ status: "idle" });
  }

  function submit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (pending) return;
    if (!form.name.trim()) {
      setSave({ status: "error", messages: ["Name cannot be blank."] });
      return;
    }
    const wasCreating = !target;
    const values = form;
    setSave({ status: "saving" });
    void (async () => {
      try {
        const payload: SupplierUpdate = supplierPayloadFrom(values);
        const supplier = target
          ? await updateSupplier(target.id, payload, csrfToken)
          : await createSupplier(payload, csrfToken);
        const refreshed = await listSuppliers();
        setDirectory({ status: "ready", suppliers: refreshed });
        setSelectedId(supplier.id);
        if (edit.modal) edit.close(true);
        else {
          setEditing(false);
          setTarget(null);
        }
        if (wasCreating) {
          restoreDetailHeading.current = true;
          setFilter("");
          closeCreation({ returnFocus: false });
        }
        setSave({
          status: "success",
          message: wasCreating
            ? `${supplier.name} was created and selected.`
            : `${supplier.name} was updated.`,
        });
        if (
          wasCreating ||
          (initialTab === "edit" && !restorePreviewEdit.current)
        )
          setRecordRoute(`#/suppliers/${supplier.id}`, true);
        if (!wasCreating && initialId === supplier.id)
          setDetailRefresh((value) => value + 1);
      } catch (error: unknown) {
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else if (error instanceof ApiError && error.status === 422)
          setSave({
            status: "error",
            messages: supplierValidationMessages(error),
          });
        else if (error instanceof ApiError && error.status === 403)
          setSave({
            status: "error",
            messages: [
              "Florabase could not authorize this change. Refresh the page and try again.",
            ],
          });
        else
          setSave({
            status: "error",
            messages: [
              "Florabase could not save or refresh this supplier. Check the connection and try again.",
            ],
          });
      }
    })();
  }

  const editor = editing ? (
    <EditWorkspace
      returnFocusTo={editTrigger}
      modal={edit.modal && Boolean(target)}
      title={target ? `Edit ${target.name}` : "Add supplier"}
      onClose={() => {
        edit.close();
      }}
    >
      <form className="supplier-form collection-form" onSubmit={submit}>
        <Breadcrumbs
          items={[
            { label: "Suppliers", href: "#/suppliers" },
            { label: target ? "Edit supplier" : "New supplier" },
          ]}
        />
        <DetailHeader
          eyebrow="Supplier"
          title={target ? `Edit ${target.name}` : "Add supplier"}
          secondary={
            target && (
              <DetailContext
                items={[{ label: "Kind", value: kindLabels[target.kind] }]}
              />
            )
          }
        />
        {save.status === "error" && (
          <div className="notice notice--error" role="alert" tabIndex={-1}>
            <h4>Check the supplier</h4>
            <ul>
              {save.messages.map((message) => (
                <li key={message}>{message}</li>
              ))}
            </ul>
          </div>
        )}
        <FormSections
          mode={target ? "edit" : "page"}
          disabled={pending}
          panels={[
            {
              id: "essentials",
              label: "Essentials",
              content: (
                <SupplierEssentialsFields
                  form={form}
                  disabled={pending}
                  onChange={patchForm}
                />
              ),
            },
            {
              id: "contact",
              label: "Contact and notes",
              content: (
                <SupplierContactFields
                  form={form}
                  disabled={pending}
                  onChange={patchForm}
                />
              ),
            },
          ]}
          submit={
            <button type="submit" disabled={pending}>
              {pending
                ? "Saving supplier…"
                : target
                  ? "Save supplier"
                  : "Add supplier"}
            </button>
          }
          cancel={
            <button
              type="button"
              className="button--secondary"
              disabled={pending}
              onClick={() => {
                if (target) {
                  edit.close();
                  return;
                }
                setEditing(false);
                setTarget(null);
                setSave({ status: "idle" });
                setForm(blankSupplierForm());
                closeCreation();
                closeCollectionPage("#/suppliers");
              }}
            >
              Cancel
            </button>
          }
        />
      </form>
    </EditWorkspace>
  ) : null;

  if (initialId)
    return (
      <section
        aria-labelledby="suppliers-title"
        className="workspace suppliers-workspace"
      >
        <div
          className="collection-context-page"
          inert={edit.modal}
          aria-hidden={edit.modal || undefined}
        >
          <WorkspaceIntro contextOnly {...supplierPage} />
          {detail.status === "loading" && (
            <p role="status">Loading supplier…</p>
          )}
          {detail.status === "error" && (
            <div className="notice notice--error" role="alert">
              <p>Florabase could not load this supplier.</p>
              <button
                type="button"
                onClick={() => {
                  setDetail({ status: "loading" });
                  setDetailRefresh((value) => value + 1);
                }}
              >
                Retry supplier
              </button>
            </div>
          )}
          {detail.status === "ready" &&
            (editing && !edit.modal ? (
              editor
            ) : (
              <SupplierDetail
                key={detail.supplier.id}
                supplier={detail.supplier}
                csrfToken={csrfToken}
                headingRef={detailHeading}
                initialTab={initialTab}
                onEdit={(event) => {
                  startEdit(detail.supplier, event.currentTarget);
                }}
                onLifecycle={(action, success) => void apply(action, success)}
              />
            ))}
          <div aria-live="polite">
            {save.status === "saving" && (
              <p className="notice">Saving the supplier…</p>
            )}
            {save.status === "success" && (
              <p className="notice notice--success" role="status">
                {save.message}
              </p>
            )}
            {save.status === "error" && !editing && (
              <p
                className="notice notice--error"
                role="alert"
                ref={feedback}
                tabIndex={-1}
              >
                {save.messages.join(" ")}
              </p>
            )}
          </div>
        </div>
        {edit.modal && editor}
      </section>
    );

  return (
    <section
      aria-labelledby="suppliers-title"
      className="workspace suppliers-workspace"
    >
      <div
        className="collection-context-page"
        inert={edit.modal}
        aria-hidden={edit.modal || undefined}
      >
        <WorkspaceIntro
          contextOnly={creationExpanded}
          {...supplierPage}
          tools={
            !creationExpanded && (
              <DirectoryTools
                name="Suppliers"
                search={
                  <DirectorySearch
                    hideLabel
                    id="supplier-filter"
                    label="Filter suppliers"
                    placeholder="Search supplier names"
                    value={filter}
                    onChange={setFilter}
                    disabled={directory.status !== "ready"}
                  />
                }
                savedViews={
                  <SavedViews
                    presentation="dialog"
                    surface="suppliers"
                    state={view.savedState}
                  />
                }
                actions={
                  <button
                    type="button"
                    ref={creationTriggerRef}
                    data-collection-return="create"
                    aria-expanded={creationExpanded}
                    aria-controls="new-supplier-panel"
                    onClick={() => {
                      if (editing) {
                        setEditing(false);
                        setTarget(null);
                        setSave({ status: "idle" });
                      }
                      startCreate();
                    }}
                  >
                    + New supplier
                  </button>
                }
              />
            )
          }
        />
        <div
          className={`supplier-master-detail operational-layout directory-preview-layout${creationExpanded ? " is-detail-view" : ""}`}
        >
          <section
            className="seed-master supplier-master"
            aria-labelledby="supplier-directory-title"
          >
            <h3 className="sr-only" id="supplier-directory-title">
              Supplier directory
            </h3>
            {directory.status === "ready" && (
              <DirectoryResults count={visible.length} />
            )}
            {directory.status === "loading" && (
              <p aria-live="polite" className="notice">
                Loading suppliers…
              </p>
            )}
            {directory.status === "error" && (
              <div className="notice notice--error" role="alert">
                <p>Florabase could not load the supplier directory.</p>
                <button
                  type="button"
                  onClick={() => {
                    setDirectory({ status: "loading" });
                    refreshDirectory();
                  }}
                >
                  Retry directory
                </button>
              </div>
            )}
            {directory.status === "ready" && suppliers.length === 0 && (
              <div className="empty-state">
                <h3>No suppliers yet</h3>
                <p>
                  Add a supplier to record where collection material was
                  acquired.
                </p>
              </div>
            )}
            {directory.status === "ready" &&
              suppliers.length > 0 &&
              visible.length === 0 && (
                <p className="notice" role="status">
                  No suppliers match this search.
                </p>
              )}
            {visible.length > 0 && (
              <ul
                className="seed-list supplier-list"
                aria-label="Suppliers"
                tabIndex={0}
              >
                {visible.map((supplier) => (
                  <li key={supplier.id}>
                    <button
                      type="button"
                      className="seed-row supplier-row"
                      aria-pressed={selectedId === supplier.id}
                      onClick={() => {
                        if (creationExpanded)
                          closeCreation({ returnFocus: false });
                        setSelectedId(supplier.id);
                        if (window.matchMedia("(max-width: 48rem)").matches)
                          setRecordRoute(`#/suppliers/${supplier.id}`);
                        setEditing(false);
                        setTarget(null);
                        setSave({ status: "idle" });
                      }}
                    >
                      <span className="seed-primary">
                        <RecordVisual
                          kind="supplier"
                          label={supplier.name}
                          photo={supplier.primary_photo ?? null}
                          compact
                        />
                        <span className="supplier-row__identity">
                          <strong>{supplier.name}</strong>
                          <small>{kindLabels[supplier.kind]}</small>
                        </span>
                      </span>
                      <span className="supplier-row__tracking">
                        <strong>
                          {supplier.usage_counts.direct_records_total}
                        </strong>{" "}
                        direct records
                      </span>
                      <span
                        className={`lifecycle-badge lifecycle-badge--${supplier.retired_at ? "retired" : "active"}`}
                      >
                        {supplier.retired_at ? "Retired" : "Active"}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section
            id={creationExpanded ? "new-supplier-panel" : undefined}
            className={
              creationExpanded
                ? "seed-detail-pane supplier-detail-pane seed-creation-panel"
                : "seed-detail-pane supplier-detail-pane"
            }
            ref={creationExpanded ? creationPanelRef : undefined}
            aria-label="Supplier detail and editor"
          >
            {editing && !edit.modal ? (
              editor
            ) : selected ? (
              <SupplierPreview
                supplier={selected}
                onOpen={() => {
                  setSave({ status: "idle" });
                }}
                onEdit={(event) => {
                  startEdit(selected, event.currentTarget);
                }}
              />
            ) : (
              <div className="empty-state seed-detail-empty">
                <h3>Select a supplier</h3>
                <p>
                  Choose a supplier for a Quick Preview, then open details to
                  inspect linked acquisitions.
                </p>
              </div>
            )}
          </section>
        </div>
        <div aria-live="polite">
          {save.status === "saving" && (
            <p className="notice">Saving the supplier…</p>
          )}
          {save.status === "success" && (
            <p className="notice notice--success" role="status">
              {save.message}
            </p>
          )}
          {save.status === "error" && !creationExpanded && (
            <p
              className="notice notice--error"
              role="alert"
              ref={feedback}
              tabIndex={-1}
            >
              {save.messages.join(" ")}
            </p>
          )}
        </div>
      </div>
      {edit.modal && editor}
    </section>
  );
}
