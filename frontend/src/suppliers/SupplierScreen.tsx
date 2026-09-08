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
  Breadcrumbs,
  CollectionCard,
  DetailHeader,
  DetailTabs,
} from "../components/CollectionUI";
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
  | { status: "validation"; messages: string[] }
  | { status: "error"; message: string };

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

function SupplierHub({
  supplier,
  editing,
  pending,
  csrfToken,
  onEdit,
  onSubmitUpdate,
  onCancelEdit,
  onLifecycle,
  initialTab,
}: {
  supplier: SupplierDetailResponse;
  editing: boolean;
  pending: boolean;
  csrfToken: string;
  onEdit: () => void;
  onSubmitUpdate: (event: SyntheticEvent<HTMLFormElement, SubmitEvent>) => void;
  onCancelEdit: () => void;
  onLifecycle: (
    action: () => Promise<SupplierResponse>,
    success: (value: SupplierResponse) => string,
  ) => void;
  initialTab?: string;
}) {
  const [tab, setTab] = useState(
    initialTab && ["overview", "material"].includes(initialTab)
      ? initialTab
      : "overview",
  );
  const counts = supplier.usage_counts;
  const linkedTotal = counts.direct_records_total;
  return (
    <article
      aria-label="Supplier detail"
      className="identity-result supplier-hub"
    >
      <Breadcrumbs
        items={[
          { label: "Suppliers", href: "#/suppliers" },
          { label: supplier.name },
        ]}
      />
      <DetailHeader
        eyebrow="Supplier"
        title={supplier.name}
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
          <details className="overflow-menu">
            <summary aria-label="More supplier actions">…</summary>
            <button
              className="button--secondary"
              type="button"
              disabled={pending}
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
          </details>
        }
      />
      {supplier.retired_at && (
        <p className="notice notice--duplicate">
          This supplier is retired. Existing acquisition history remains
          available.
        </p>
      )}
      <DetailTabs
        tabs={[
          { id: "overview", label: "Overview" },
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
          className="detail-tab-panel"
          role="tabpanel"
          aria-labelledby="tab-overview"
        >
          <div
            className="summary-grid supplier-counts"
            aria-label="Direct supplier usage"
          >
            <section className="fact-card">
              <p className="card-type">Direct records</p>
              <h4>{counts.direct_records_total}</h4>
              <p>{counts.direct_records_active} current</p>
            </section>
            <section className="fact-card">
              <p className="card-type">SeedLots</p>
              <h4>{counts.seed_lots_total}</h4>
              <p>{counts.seed_lots_active} active</p>
            </section>
            <section className="fact-card">
              <p className="card-type">Plants</p>
              <h4>{counts.plants_total + counts.plant_groups_total}</h4>
              <p>
                {counts.plants_total} individual · {counts.plant_groups_total}{" "}
                groups
              </p>
            </section>
          </div>
          <div className="overview-grid">
            <section aria-labelledby="supplier-about-title">
              <h4 id="supplier-about-title">About this supplier</h4>
              <dl>
                <div>
                  <dt>Kind</dt>
                  <dd>{kindLabels[supplier.kind]}</dd>
                </div>
                <div>
                  <dt>Website</dt>
                  <dd>
                    {supplier.website ? (
                      <a
                        href={supplier.website}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Visit supplier website
                      </a>
                    ) : (
                      "Not recorded"
                    )}
                  </dd>
                </div>
                <div>
                  <dt>Email</dt>
                  <dd>
                    {supplier.email ? (
                      <a href={`mailto:${supplier.email}`}>{supplier.email}</a>
                    ) : (
                      "Not recorded"
                    )}
                  </dd>
                </div>
                <div>
                  <dt>Phone</dt>
                  <dd>{supplier.phone ?? "Not recorded"}</dd>
                </div>
                <div>
                  <dt>Notes</dt>
                  <dd className="preserve-lines">
                    {supplier.notes ?? "Not recorded"}
                  </dd>
                </div>
              </dl>
            </section>
            <section aria-labelledby="recent-acquisitions-title">
              <h4 id="recent-acquisitions-title">Recent acquisitions</h4>
              {supplier.recent_acquisitions.length === 0 ? (
                <div className="empty-state compact-empty-state">
                  <p>
                    No directly linked acquisitions have a recorded acquisition
                    date.
                  </p>
                </div>
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
                            {record.botanical_identity.display_label}
                          </a>
                        </p>
                        <p>
                          Acquired {dateLabel(record.acquired_on)} ·{" "}
                          {lifecycleLabels[record.lifecycle] ??
                            record.lifecycle}
                        </p>
                      </CollectionCard>
                    );
                  })}
                </div>
              )}
            </section>
          </div>
        </div>
      )}
      {tab === "material" && (
        <div
          className="detail-tab-panel supplier-material"
          role="tabpanel"
          aria-labelledby="tab-material"
        >
          <section aria-labelledby="supplier-seed-lots-title">
            <h4 id="supplier-seed-lots-title">
              SeedLots ({supplier.seed_lots.length})
            </h4>
            {supplier.seed_lots.length === 0 ? (
              <p className="empty-state compact-empty-state">
                No SeedLots directly reference this supplier.
              </p>
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
                        {record.botanical_identity.display_label}
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
          <section aria-labelledby="supplier-plants-title">
            <h4 id="supplier-plants-title">
              Plants ({supplier.plants.length + supplier.plant_groups.length})
            </h4>
            {supplier.plants.length + supplier.plant_groups.length === 0 ? (
              <p className="empty-state compact-empty-state">
                No directly acquired Plants or Plant groups reference this
                supplier.
              </p>
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
                        {record.botanical_identity.display_label}
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
      {editing && (
        <form
          key={`${supplier.id}-${supplier.updated_at}`}
          onSubmit={onSubmitUpdate}
        >
          <h4>Edit supplier</h4>
          <SupplierFields supplier={supplier} disabled={pending} />
          <div className="actions">
            <button type="submit" disabled={pending}>
              Save supplier
            </button>
            <button
              className="button--secondary"
              type="button"
              disabled={pending}
              onClick={onCancelEdit}
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </article>
  );
}

function payloadFrom(form: HTMLFormElement): SupplierCreate {
  const data = new FormData(form);
  const value = (name: string) => {
    const item = data.get(name);
    return typeof item === "string" ? item : "";
  };
  return {
    name: value("name"),
    kind: value("kind") as SupplierCreate["kind"],
    ...(value("website") ? { website: value("website") } : {}),
    ...(value("email") ? { email: value("email") } : {}),
    ...(value("phone") ? { phone: value("phone") } : {}),
    ...(value("notes") ? { notes: value("notes") } : {}),
  };
}

function SupplierFields({
  supplier,
  disabled,
}: {
  supplier?: SupplierResponse;
  disabled: boolean;
}) {
  return (
    <>
      <div className="field">
        <label htmlFor={supplier ? "edit-supplier-name" : "new-supplier-name"}>
          Name
        </label>
        <input
          id={supplier ? "edit-supplier-name" : "new-supplier-name"}
          name="name"
          required
          maxLength={255}
          disabled={disabled}
          defaultValue={supplier?.name}
        />
      </div>
      <div className="field">
        <label htmlFor={supplier ? "edit-supplier-kind" : "new-supplier-kind"}>
          Kind
        </label>
        <select
          id={supplier ? "edit-supplier-kind" : "new-supplier-kind"}
          name="kind"
          required
          disabled={disabled}
          defaultValue={supplier?.kind ?? "seller"}
        >
          {Object.entries(kindLabels).map(([value, label]) => (
            <option value={value} key={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label
          htmlFor={supplier ? "edit-supplier-website" : "new-supplier-website"}
        >
          Website
        </label>
        <input
          id={supplier ? "edit-supplier-website" : "new-supplier-website"}
          name="website"
          type="url"
          maxLength={2048}
          disabled={disabled}
          defaultValue={supplier?.website ?? ""}
        />
      </div>
      <div className="field">
        <label
          htmlFor={supplier ? "edit-supplier-email" : "new-supplier-email"}
        >
          Email
        </label>
        <input
          id={supplier ? "edit-supplier-email" : "new-supplier-email"}
          name="email"
          type="email"
          maxLength={320}
          disabled={disabled}
          defaultValue={supplier?.email ?? ""}
        />
      </div>
      <div className="field">
        <label
          htmlFor={supplier ? "edit-supplier-phone" : "new-supplier-phone"}
        >
          Phone
        </label>
        <input
          id={supplier ? "edit-supplier-phone" : "new-supplier-phone"}
          name="phone"
          type="tel"
          maxLength={120}
          disabled={disabled}
          defaultValue={supplier?.phone ?? ""}
        />
      </div>
      <div className="field">
        <label
          htmlFor={supplier ? "edit-supplier-notes" : "new-supplier-notes"}
        >
          Notes
        </label>
        <textarea
          id={supplier ? "edit-supplier-notes" : "new-supplier-notes"}
          name="notes"
          maxLength={20000}
          rows={4}
          disabled={disabled}
          defaultValue={supplier?.notes ?? ""}
        />
      </div>
    </>
  );
}

export function SupplierScreen({
  initialId,
  initialTab,
}: { initialId?: string; initialTab?: string } = {}) {
  const auth = useAuth();
  const [directory, setDirectory] = useState<DirectoryState>({
    status: "loading",
  });
  const [selectedId, setSelectedId] = useState<string | null>(
    initialId ?? null,
  );
  const [detail, setDetail] = useState<DetailState>(
    initialId ? { status: "loading" } : { status: "idle" },
  );
  const [detailRefresh, setDetailRefresh] = useState(0);
  const [filter, setFilter] = useState("");
  const [save, setSave] = useState<SaveState>({ status: "idle" });
  const [attempt, setAttempt] = useState(0);
  const [editing, setEditing] = useState(false);
  const createForm = useRef<HTMLFormElement>(null);
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
    if (!selectedId) return;
    const controller = new AbortController();
    void getSupplier(selectedId, controller.signal)
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
  }, [auth, detailRefresh, selectedId]);

  useEffect(() => {
    if (save.status === "validation" || save.status === "error")
      feedback.current?.focus();
  }, [save]);

  const suppliers = useMemo(
    () => (directory.status === "ready" ? directory.suppliers : []),
    [directory],
  );
  const selected = suppliers.find(({ id }) => id === selectedId) ?? null;
  const visible = useMemo(() => {
    const query = filter.trim().toLocaleLowerCase();
    if (!query) return suppliers;
    return suppliers.filter((supplier) =>
      [supplier.name, supplier.website, supplier.email, supplier.phone].some(
        (value) => value?.toLocaleLowerCase().includes(query),
      ),
    );
  }, [filter, suppliers]);

  if (
    auth.state.status !== "authenticated" &&
    auth.state.status !== "logging-out" &&
    auth.state.status !== "logout-failed"
  )
    return null;
  const csrfToken = auth.state.csrfToken;

  async function apply(
    action: () => Promise<SupplierResponse>,
    success: (supplier: SupplierResponse) => string,
  ) {
    setSave({ status: "saving" });
    try {
      const supplier = await action();
      const refreshed = await listSuppliers();
      setDirectory({ status: "ready", suppliers: refreshed });
      setSelectedId(supplier.id);
      setDetail({ status: "loading" });
      setDetailRefresh((value) => value + 1);
      setEditing(false);
      setSave({ status: "success", message: success(supplier) });
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else if (error instanceof ApiError && error.status === 422)
        setSave({
          status: "validation",
          messages: supplierValidationMessages(error),
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
            "Florabase could not save or refresh this supplier. Check the connection and try again.",
        });
    }
  }

  function submitCreate(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (pending) return;
    const form = event.currentTarget;
    void apply(
      () => createSupplier(payloadFrom(form), csrfToken),
      (supplier) => {
        createForm.current?.reset();
        setFilter("");
        closeCreation();
        return `${supplier.name} was created and selected.`;
      },
    );
  }

  function submitUpdate(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (!selected || pending) return;
    const payload: SupplierUpdate = payloadFrom(event.currentTarget);
    void apply(
      () => updateSupplier(selected.id, payload, csrfToken),
      (supplier) => `${supplier.name} was updated.`,
    );
  }

  return (
    <section aria-labelledby="suppliers-title" className="workspace">
      <div className="workspace-intro directory-heading">
        <div>
          <p className="eyebrow">Collection reference</p>
          <h2 id="suppliers-title">Suppliers</h2>
          <p>
            Maintain who supplied collection material, separately from its
            geographic provenance and current Location.
          </p>
        </div>
        <button
          type="button"
          ref={creationTriggerRef}
          aria-expanded={creationExpanded}
          aria-controls="new-supplier-panel"
          onClick={() => {
            if (creationExpanded) {
              focusCreation();
              return;
            }
            createForm.current?.reset();
            setSave({ status: "idle" });
            openCreation();
          }}
        >
          + New supplier
        </button>
      </div>
      <div className="directory-detail-grid">
        <div className="directory-column">
          <section
            aria-labelledby="supplier-directory-title"
            className="identity-directory"
          >
            <h3 id="supplier-directory-title">Supplier directory</h3>
            <div className="field">
              <label htmlFor="supplier-filter">Filter suppliers</label>
              <input
                id="supplier-filter"
                type="search"
                value={filter}
                disabled={
                  directory.status !== "ready" || suppliers.length === 0
                }
                onChange={(event) => {
                  setFilter(event.currentTarget.value);
                }}
              />
            </div>
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
                    setAttempt((value) => value + 1);
                  }}
                >
                  Retry directory
                </button>
              </div>
            )}
            {directory.status === "ready" && suppliers.length === 0 && (
              <div className="empty-state">
                <p>No suppliers yet.</p>
              </div>
            )}
            {directory.status === "ready" &&
              suppliers.length > 0 &&
              visible.length === 0 && (
                <p className="notice" role="status">
                  No suppliers match this filter.
                </p>
              )}
            {visible.length > 0 && (
              <ul className="identity-list">
                {visible.map((supplier) => (
                  <li key={supplier.id}>
                    <button
                      type="button"
                      className="identity-list-item"
                      aria-pressed={selectedId === supplier.id}
                      onClick={() => {
                        setSelectedId(supplier.id);
                        setDetail({ status: "loading" });
                        setDetailRefresh((value) => value + 1);
                        window.history.replaceState(
                          null,
                          "",
                          `#/suppliers/${supplier.id}`,
                        );
                        setEditing(false);
                        setSave({ status: "idle" });
                      }}
                    >
                      <span>
                        {supplier.name}{" "}
                        {supplier.retired_at && (
                          <span className="record-state">Retired</span>
                        )}
                      </span>
                      <small>
                        {kindLabels[supplier.kind]}
                        {` · ${String(supplier.usage_counts.direct_records_total)} direct records`}
                        {supplier.usage_counts.direct_records_active > 0
                          ? ` · ${String(supplier.usage_counts.direct_records_active)} current`
                          : ""}
                      </small>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
          {creationExpanded && (
            <div
              id="new-supplier-panel"
              className="creation-panel"
              ref={creationPanelRef}
            >
              <form
                className="identity-form"
                ref={createForm}
                aria-busy={pending}
                onSubmit={submitCreate}
              >
                <h3>Create a supplier</h3>
                <SupplierFields disabled={pending} />
                <div className="actions">
                  <button type="submit" disabled={pending}>
                    {pending ? "Saving supplier…" : "Create supplier"}
                  </button>
                  <button
                    type="button"
                    className="button--secondary"
                    disabled={pending}
                    onClick={() => {
                      createForm.current?.reset();
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
          {selectedId && detail.status === "loading" ? (
            <p className="notice" aria-live="polite">
              Loading supplier hub…
            </p>
          ) : selectedId && detail.status === "error" ? (
            <div className="notice notice--error" role="alert">
              <p>Florabase could not load this supplier’s linked material.</p>
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
          ) : detail.status === "ready" ? (
            <SupplierHub
              key={detail.supplier.id}
              supplier={detail.supplier}
              editing={editing}
              pending={pending}
              csrfToken={csrfToken}
              initialTab={initialTab}
              onEdit={() => {
                setEditing(true);
              }}
              onSubmitUpdate={submitUpdate}
              onCancelEdit={() => {
                setEditing(false);
              }}
              onLifecycle={(action, success) => {
                void apply(action, success);
              }}
            />
          ) : (
            <div className="empty-state">
              <h3>Select a supplier</h3>
              <p>Choose a record from the directory to view or maintain it.</p>
            </div>
          )}
        </div>
      </div>
      <div aria-live="polite">
        {save.status === "saving" && (
          <p className="notice">Saving the supplier…</p>
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
            <h3>Check the supplier</h3>
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
